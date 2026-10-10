"""Explicit, private landing of pinned backup bytes; never a restore runner.

Only explicit landing and journal APIs create or append files. Import is inert. All
paths are fixed below ROOT; callers cannot supply another output destination.
Archive ownership and mode are validated, but host files intentionally remain
owned by the current euid and private. Container UID/mode restoration is a
separate admission gate.
"""
from __future__ import annotations

from contextlib import ExitStack
import ctypes
import fcntl
from dataclasses import dataclass
import copy
import hashlib
import io
import os
from pathlib import Path
import stat
import sys
import tarfile
import threading

from . import inputs
from .common import ROOT, RestoreError

MAX_LANDING_ENTRIES = 128
MAX_FROZEN_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 256 * 1024 * 1024
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _fail(code: str) -> None:
    raise RestoreError(code)


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _snapshot(value: os.stat_result) -> tuple:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns,
            value.st_mode, value.st_uid, value.st_gid, value.st_nlink)


def _move_no_replace(source_parent: int, source_name: str, destination_parent: int,
                     destination_name: str) -> None:
    """Atomically move into the private cleanup slot without overwriting it.

    Darwin's RENAME_EXCL and Linux's RENAME_NOREPLACE are required. There is no
    unsafe rename fallback when the platform does not expose the primitive.
    The slot must remain under trusted same-euid control: POSIX does not offer
    compare-inode-unlink against another malicious process of the same uid.
    """
    try:
        library = ctypes.CDLL(None, use_errno=True)
        if sys.platform == "darwin":
            operation = library.renameatx_np
            flags = 0x00000004  # macOS SDK sys/stdio.h: RENAME_EXCL.
        elif sys.platform.startswith("linux"):
            operation = library.renameat2
            flags = 1  # Linux RENAME_NOREPLACE.
        else:
            _fail("LANDING_ATOMIC_MOVE_UNAVAILABLE")
        operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        operation.restype = ctypes.c_int
        if operation(source_parent, os.fsencode(source_name), destination_parent,
                     os.fsencode(destination_name), flags) != 0:
            _fail("LANDING_ATOMIC_MOVE_FAILED")
    except RestoreError:
        raise
    except (AttributeError, OSError, TypeError, ValueError, UnicodeError):
        raise RestoreError("LANDING_ATOMIC_MOVE_UNAVAILABLE") from None


def _relative(value: str, *, root: bool = False) -> None:
    if root and value == "":
        return
    if (type(value) is not str or not value or value.startswith("/") or "\\" in value
            or any(part in ("", ".", "..") for part in value.split("/"))
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        _fail("LANDING_RELATIVE_PATH_INVALID")


def _freeze_inputs(manifest_path: Path, expected: dict, before_sha: str,
                   manifest_sha: str) -> dict[str, bytes]:
    """Reopen all sources together, freezing only the previously pinned bytes."""
    result = {}
    with inputs._staging_directory(manifest_path.parent) as directory, ExitStack() as opened:
        stream, _ = opened.enter_context(inputs._input_file(directory, manifest_path.name,
                                                            inputs.MAX_MANIFEST_BYTES))
        manifest_raw = inputs._read_bytes(stream, inputs.MAX_MANIFEST_BYTES)
        if hashlib.sha256(manifest_raw).hexdigest() != manifest_sha:
            _fail("MANIFEST_HASH_MISMATCH")
        manifest = inputs._json_object(manifest_raw)
        stream, _ = opened.enter_context(inputs._input_file(directory, "before.json",
                                                            inputs.MAX_JSON_BYTES))
        before_raw = inputs._read_bytes(stream, inputs.MAX_JSON_BYTES)
        if hashlib.sha256(before_raw).hexdigest() != before_sha:
            _fail("BEFORE_HASH_MISMATCH")
        result["before"] = before_raw
        for component in inputs.COMPONENTS:
            limit = inputs.MAX_JSON_BYTES if component == "site_config" else inputs.MAX_INPUT_BYTES
            stream, metadata = opened.enter_context(inputs._input_file(
                directory, Path(manifest[component]).name, limit))
            raw = inputs._read_bytes(stream, limit)
            pin = expected[component]
            if (len(raw) != pin["bytes"] or metadata.st_size != len(raw)
                    or hashlib.sha256(raw).hexdigest() != pin["sha256"]):
                _fail("COMPONENT_HASH_MISMATCH")
            result[component] = raw
    return result


@dataclass(repr=False)
class _Entry:
    parent: int
    name: str
    descriptor: int
    identity: tuple[int, int]
    directory: bool
    expected_bytes: int | None = None
    expected_sha256: str | None = None


class OwnedLanding:
    """Opaque capability for files created by this call, including safe cleanup.

    Nothing is serialized except ``public_summary``. Retained directory and file
    descriptors keep identities anchored. Cleanup refuses a replaced identity,
    hardlinked file, changed private ownership/mode, or any unregistered child.
    """

    def __init__(self, parent: int, anchors: list[tuple[int, str, int]]):
        self._parent = parent
        self._anchors = anchors
        self._entries: list[_Entry] = []
        self._directories: dict[str, int] = {}
        self._summary: dict = {}
        self._closed = False
        self._cleaned = False
        self._uid = os.geteuid()
        self._unanchored_created = False
        self._cleanup_entry: _Entry | None = None
        self._journal_lock = threading.RLock()

    def __repr__(self) -> str:
        return "<OwnedLanding private capability>"

    def public_summary(self) -> dict:
        if self._closed:
            return {"status": "LANDING_CLEANED" if self._cleaned else "LANDING_CAPABILITY_CLOSED",
                    "files_removed": self._cleaned}
        # Rebuild rather than expose nested internal mutable objects.
        return copy.deepcopy(self._summary)

    def journal_directory_fd(self, *, create: bool = False) -> int:
        """Duplicate only the fixed registered private journal directory FD."""
        if type(create) is not bool:
            _fail("LANDING_JOURNAL_INVALID")
        with self._journal_lock:
            self.verify_private_tree()
            try:
                if create:
                    descriptor = self._directory("runtime/journal")
                else:
                    descriptor = self._directories["runtime/journal"]
                return os.dup(descriptor)
            except (OSError, KeyError):
                raise RestoreError("LANDING_JOURNAL_UNAVAILABLE") from None

    def _journal_entry(self) -> _Entry:
        parent = self._directories.get("runtime/journal")
        entries = [entry for entry in self._entries if entry.parent == parent
                   and entry.name == "events.jsonl" and not entry.directory and entry.descriptor >= 0]
        if len(entries) != 1:
            _fail("LANDING_JOURNAL_UNAVAILABLE")
        return entries[0]

    def journal_create_log(self) -> None:
        """Explicit, exclusive creation; never rewrite an existing journal."""
        with self._journal_lock:
            self.verify_private_tree()
            try:
                self._directory("runtime/journal")
                self._write("runtime/journal/events.jsonl", b"")
                # Persist each newly created namespace link, including ROOT.
                for relative in ("runtime/journal", "runtime", ""):
                    os.fsync(self._directories[relative])
                os.fsync(self._parent)
            except OSError:
                raise RestoreError("LANDING_JOURNAL_CREATE_FAILED") from None

    def journal_read_log(self) -> bytes:
        with self._journal_lock:
            self.verify_private_tree()
            entry = self._journal_entry()
            if entry.expected_bytes is None or entry.expected_bytes > 1024 * 1024:
                _fail("LANDING_JOURNAL_INVALID")
            try:
                data = os.pread(entry.descriptor, entry.expected_bytes + 1, 0)
                self._check_entry(entry)
            except OSError:
                raise RestoreError("LANDING_JOURNAL_READ_FAILED") from None
            if len(data) != entry.expected_bytes or hashlib.sha256(data).hexdigest() != entry.expected_sha256:
                _fail("LANDING_JOURNAL_INVALID")
            return data

    def journal_append_bytes(self, payload: bytes) -> None:
        """Append a bounded line; retain and recheck the exact existing prefix.

        A short/crashed append never returns success or updates the registered
        hash. A changed payload then refuses ordinary cleanup and is retained
        for private review. The journal layer owns schema and chain validation.
        """
        if type(payload) is not bytes or not 1 <= len(payload) <= 32 * 1024 or not payload.endswith(b"\n"):
            _fail("LANDING_JOURNAL_INVALID")
        with self._journal_lock:
            self.verify_private_tree()
            entry = self._journal_entry()
            locked = False
            try:
                fcntl.flock(entry.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                old = self.journal_read_log()
                if len(old) + len(payload) > 1024 * 1024:
                    _fail("LANDING_JOURNAL_LIMIT")
                os.lseek(entry.descriptor, 0, os.SEEK_END)
                view = memoryview(payload)
                while view:
                    written = os.write(entry.descriptor, view)
                    if written <= 0:
                        _fail("LANDING_JOURNAL_APPEND_FAILED")
                    view = view[written:]
                os.fsync(entry.descriptor)
                expected = old + payload
                before = os.fstat(entry.descriptor)
                current = os.pread(entry.descriptor, len(expected) + 1, 0)
                after = os.fstat(entry.descriptor)
                named = os.stat(entry.name, dir_fd=entry.parent, follow_symlinks=False)
                if (current != expected or _snapshot(before) != _snapshot(after)
                        or _snapshot(named) != _snapshot(after)):
                    _fail("LANDING_JOURNAL_APPEND_FAILED")
                entry.expected_bytes = len(expected)
                entry.expected_sha256 = hashlib.sha256(expected).hexdigest()
                self._check_entry(entry)
            except OSError:
                raise RestoreError("LANDING_JOURNAL_APPEND_FAILED") from None
            finally:
                if locked:
                    try:
                        fcntl.flock(entry.descriptor, fcntl.LOCK_UN)
                    except OSError:
                        raise RestoreError("LANDING_JOURNAL_UNLOCK_FAILED") from None

    def _check_anchors(self) -> None:
        try:
            for parent, name, descriptor in self._anchors:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                anchored = os.fstat(descriptor)
                if not stat.S_ISDIR(current.st_mode) or _identity(current) != _identity(anchored):
                    _fail("LANDING_ANCESTOR_CHANGED")
        except OSError:
            raise RestoreError("LANDING_ANCESTOR_CHANGED") from None

    def _register_directory(self, parent: int, name: str, relative: str) -> int:
        if len(self._entries) >= MAX_LANDING_ENTRIES:
            _fail("LANDING_ENTRY_LIMIT")
        os.mkdir(name, 0o700, dir_fd=parent)
        self._unanchored_created = True
        descriptor = None
        try:
            descriptor = os.open(name, _DIR_FLAGS, dir_fd=parent)
            metadata = os.fstat(descriptor)
            self._entries.append(_Entry(parent, name, descriptor, _identity(metadata), True))
            self._unanchored_created = False
            os.fchmod(descriptor, 0o700)
            self._directories[relative] = descriptor
            return descriptor
        except BaseException:
            # mkdir succeeded but an entry could not be anchored. Do not delete
            # an object whose identity has not been registered.
            if descriptor is not None and not any(entry.descriptor == descriptor for entry in self._entries):
                os.close(descriptor)
            raise

    def _directory(self, relative: str) -> int:
        _relative(relative, root=True)
        if relative in self._directories:
            return self._directories[relative]
        parts = relative.split("/")
        parent_relative = "/".join(parts[:-1])
        parent = self._directory(parent_relative)
        return self._register_directory(parent, parts[-1], relative)

    def _write(self, relative: str, payload: bytes) -> None:
        _relative(relative)
        if len(self._entries) >= MAX_LANDING_ENTRIES:
            _fail("LANDING_ENTRY_LIMIT")
        parent_relative, name = relative.rsplit("/", 1)
        parent = self._directory(parent_relative)
        descriptor = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=parent)
        self._unanchored_created = True
        try:
            metadata = os.fstat(descriptor)
        except BaseException:
            os.close(descriptor)
            raise
        self._entries.append(_Entry(parent, name, descriptor, _identity(metadata), False))
        self._unanchored_created = False
        os.fchmod(descriptor, 0o600)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                _fail("LANDING_WRITE_FAILED")
            view = view[written:]
        os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        count = 0
        while chunk := os.read(descriptor, inputs.CHUNK_BYTES):
            count += len(chunk)
            digest.update(chunk)
        if count != len(payload) or digest.hexdigest() != hashlib.sha256(payload).hexdigest():
            _fail("LANDING_HASH_MISMATCH")
        entry = self._entries[-1]
        entry.expected_bytes = len(payload)
        entry.expected_sha256 = hashlib.sha256(payload).hexdigest()
        self._check_entry(entry)

    def _check_entry(self, entry: _Entry) -> None:
        try:
            anchored = os.fstat(entry.descriptor)
            current = os.stat(entry.name, dir_fd=entry.parent, follow_symlinks=False)
        except OSError:
            raise RestoreError("LANDING_IDENTITY_CHANGED") from None
        kind = stat.S_ISDIR if entry.directory else stat.S_ISREG
        mode = 0o700 if entry.directory else 0o600
        if (not kind(current.st_mode) or not kind(anchored.st_mode)
                or _identity(current) != entry.identity or _identity(anchored) != entry.identity
                or current.st_uid != self._uid or anchored.st_uid != self._uid
                or stat.S_IMODE(current.st_mode) != mode or stat.S_IMODE(anchored.st_mode) != mode
                or not entry.directory and (current.st_nlink != 1 or anchored.st_nlink != 1)):
            _fail("LANDING_IDENTITY_CHANGED")
        if not entry.directory and entry.expected_sha256 is not None:
            if anchored.st_size != entry.expected_bytes:
                _fail("LANDING_PAYLOAD_CHANGED")
            digest = hashlib.sha256()
            offset = 0
            try:
                while offset < entry.expected_bytes:
                    chunk = os.pread(entry.descriptor, min(inputs.CHUNK_BYTES, entry.expected_bytes - offset), offset)
                    if not chunk:
                        _fail("LANDING_PAYLOAD_CHANGED")
                    offset += len(chunk)
                    digest.update(chunk)
                after = os.fstat(entry.descriptor)
                after_entry = os.stat(entry.name, dir_fd=entry.parent, follow_symlinks=False)
            except OSError:
                raise RestoreError("LANDING_PAYLOAD_CHANGED") from None
            if (_snapshot(anchored) != _snapshot(after) or _snapshot(after_entry) != _snapshot(after)
                    or digest.hexdigest() != entry.expected_sha256):
                _fail("LANDING_PAYLOAD_CHANGED")

    def verify_private_tree(self) -> None:
        if self._closed or self._unanchored_created or os.geteuid() != self._uid:
            _fail("LANDING_CAPABILITY_INVALID")
        self._check_anchors()
        expected: dict[int, set[str]] = {}
        for entry in self._entries:
            if entry.descriptor < 0:
                continue
            self._check_entry(entry)
            expected.setdefault(entry.parent, set()).add(entry.name)
        for entry in self._entries:
            if entry.directory and entry.descriptor >= 0:
                try:
                    children = set(os.listdir(entry.descriptor))
                except OSError:
                    raise RestoreError("LANDING_IDENTITY_CHANGED") from None
                if children != expected.get(entry.descriptor, set()):
                    _fail("LANDING_UNREGISTERED_CHILD")

    def cleanup(self) -> dict:
        """Atomically quarantine, recheck, then remove only registered identities.

        Private isolation prevents deleting a replacement raced into its source
        name. As with the rest of this capability, its 0700 cleanup slot requires
        trusted same-euid control; arbitrary same-uid interference inside that
        slot cannot be prevented by portable filesystem APIs.
        """
        if self._closed:
            if self._cleaned:
                return {"status": "LANDING_ALREADY_CLEANED", "removed_entries": 0}
            _fail("LANDING_CAPABILITY_INVALID")
        try:
            self.verify_private_tree()
            count = sum(entry.descriptor >= 0 for entry in self._entries)
            root_entry = self._entries[0]
            slot_entry = self._cleanup_entry
            if slot_entry is None or slot_entry.descriptor < 0:
                # mkdir/open for the slot failed before any payload existed,
                # or a previous cleanup removed its slot but not the root.
                if any(entry is not root_entry and entry.descriptor >= 0 for entry in self._entries):
                    _fail("LANDING_CLEANUP_FAILED")
                self._check_entry(root_entry)
                if os.listdir(root_entry.descriptor):
                    _fail("LANDING_UNREGISTERED_CHILD")
                os.rmdir(root_entry.name, dir_fd=root_entry.parent)
                os.close(root_entry.descriptor)
                root_entry.descriptor = -1
                self._closed = self._cleaned = True
                self._close_anchors()
                return {"status": "LANDING_CLEANED", "removed_entries": count}
            slot = slot_entry.descriptor
            for index, entry in reversed(list(enumerate(self._entries))):
                if entry.descriptor < 0:
                    continue
                if entry is root_entry or entry is slot_entry:
                    continue
                self._check_entry(entry)
                destination = "entry-" + str(index)
                _move_no_replace(entry.parent, entry.name, slot, destination)
                # Only the moved identity may be deleted. A raced replacement
                # stays in the private slot and causes a refused cleanup.
                entry.parent = slot
                entry.name = destination
                self._check_entry(entry)
                if entry.directory:
                    if os.listdir(entry.descriptor):
                        _fail("LANDING_UNREGISTERED_CHILD")
                    os.rmdir(entry.name, dir_fd=entry.parent)
                else:
                    os.unlink(entry.name, dir_fd=entry.parent)
                os.close(entry.descriptor)
                entry.descriptor = -1
            for entry in (slot_entry, root_entry):
                self._check_entry(entry)
                if os.listdir(entry.descriptor):
                    _fail("LANDING_UNREGISTERED_CHILD")
                os.rmdir(entry.name, dir_fd=entry.parent)
                os.close(entry.descriptor)
                entry.descriptor = -1
            self._closed = True
            self._cleaned = True
            self._close_anchors()
            return {"status": "LANDING_CLEANED", "removed_entries": count}
        except RestoreError:
            raise
        except (OSError, ValueError, TypeError):
            raise RestoreError("LANDING_CLEANUP_FAILED") from None

    def close(self) -> dict:
        """Release descriptors without deleting anything after refused cleanup.

        This explicitly does not report cleanup PASS; its caller must retain the
        failed cleanup audit and handle owned leftovers through separate review.
        """
        if self._closed:
            return self.public_summary()
        for entry in reversed(self._entries):
            if entry.descriptor >= 0:
                os.close(entry.descriptor)
                entry.descriptor = -1
        self._close_anchors()
        self._closed = True
        return self.public_summary()

    def _close_anchors(self) -> None:
        for _, _, descriptor in reversed(self._anchors):
            os.close(descriptor)
        # Root / descriptor is not itself an ancestor tuple.
        if self._anchors:
            os.close(self._anchors[0][0])
        else:
            os.close(self._parent)
        self._anchors = []


def _new_landing() -> OwnedLanding:
    if (not isinstance(ROOT, Path) or not ROOT.is_absolute() or ROOT.anchor != "/"
            or ".." in ROOT.parts or len(ROOT.parts) < 3):
        _fail("LANDING_ROOT_INVALID")
    anchors = []
    descriptor = os.open("/", _DIR_FLAGS)
    capability = None
    try:
        for name in ROOT.parent.parts[1:]:
            child = os.open(name, _DIR_FLAGS, dir_fd=descriptor)
            anchors.append((descriptor, name, child))
            descriptor = child
        capability = OwnedLanding(descriptor, anchors)
        capability._check_anchors()
        root_descriptor = capability._register_directory(descriptor, ROOT.name, "")
        capability._directories[""] = root_descriptor
        capability._check_entry(capability._entries[0])
        capability._register_directory(root_descriptor, ".owned-cleanup", ".owned-cleanup")
        capability._cleanup_entry = capability._entries[-1]
        return capability
    except BaseException:
        cleanup_failed = False
        if capability is not None and capability._entries:
            try:
                capability.cleanup()
            except (RestoreError, OSError):
                cleanup_failed = True
                capability.close()
        else:
            for _, _, child in reversed(anchors):
                os.close(child)
            if anchors:
                os.close(anchors[0][0])
            else:
                os.close(descriptor)
        if capability is not None and capability._unanchored_created or cleanup_failed:
            raise RestoreError("LANDING_FAILURE_CLEANUP_REFUSED") from None
        raise


def land_backup_inputs(manifest_path: Path, expected: dict, expected_before_sha256: str,
                       expected_manifest_sha256: str | None = None) -> OwnedLanding:
    """Explicitly create a fresh private ROOT from one fully validated batch.

    Initial validation and a second simultaneous no-follow read must match all
    pins. All bytes are frozen before ROOT creation, then archives are decoded
    again exclusively from those immutable bytes. No SQL is executed, key is
    decrypted, chown is called, or existing destination is touched.
    """
    capability = None
    try:
        validated = inputs.validate_backup_inputs(manifest_path, expected, expected_before_sha256,
                                                   expected_manifest_sha256)
        pins = {key: {field: value[field] for field in ("sha256", "bytes")}
                for key, value in validated["components"].items()}
        if sum(value["bytes"] for value in pins.values()) > MAX_FROZEN_BYTES:
            _fail("LANDING_BYTE_LIMIT")
        if sum(validated["components"][key]["expanded_bytes"]
               for key in ("public_files", "private_files", "auth_files")) > MAX_ARCHIVE_EXPANDED_BYTES:
            _fail("LANDING_BYTE_LIMIT")
        frozen = _freeze_inputs(manifest_path, pins, expected_before_sha256,
                                validated["manifest_sha256"])
        archive_payloads = {}
        for component in ("public_files", "private_files", "auth_files"):
            stream = io.BytesIO(frozen[component])
            summary = inputs._archive_metadata(stream, component)
            if summary != {key: value for key, value in validated["components"][component].items()
                            if key not in ("sha256", "bytes")}:
                _fail("LANDING_ARCHIVE_CHANGED")
            raw = frozen[component]
            archive_payloads[component] = (inputs._expanded_gzip(io.BytesIO(raw), collect=True)
                                           if raw.startswith(b"\x1f\x8b") else raw)
        # Refuse descriptor/resource exhaustion before creating any destination.
        archive_members = sum(validated["components"][component]["members"]
                              for component in archive_payloads)
        if archive_members + 32 > MAX_LANDING_ENTRIES:
            _fail("LANDING_ENTRY_LIMIT")
        capability = _new_landing()
        capability._write("input/database.sql.gz", frozen["database"])
        capability._write("input/site_config.json", frozen["site_config"])
        capability._write("input/before.json", frozen["before"])
        # Preserve all five exact original artifacts, including original tar
        # mode/UID metadata for a separately admitted container-volume step.
        capability._write("input/public_files.tar", frozen["public_files"])
        capability._write("input/private_files.tar", frozen["private_files"])
        capability._write("input/auth_files.tar.gz", frozen["auth_files"])
        capability._write("sites/frontend/site_config.json", frozen["site_config"])
        for component, payload in archive_payloads.items():
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:", errorlevel=2) as archive:
                for member in archive:
                    canonical = inputs._canonical_member(member.name, member.isdir(), component)
                    relative = "sites/frontend/private/" + canonical if component == "auth_files" else "sites/" + canonical
                    if member.isdir():
                        capability._directory(relative)
                    else:
                        raw = payload[member.offset_data:member.offset_data + member.size]
                        capability._write(relative, raw)
        capability.verify_private_tree()
        capability._summary = {
            "status": "LANDED_PRIVATE_BYTES_ONLY", "sql_restore": "NOT_RUN",
            "container_uid_mode_restore": "NOT_RUN", "archive_uid_gid": "1000:1000_VALIDATED",
            "host_uid_matches_archive": os.geteuid() == 1000,
            "host_mode": {"directories": "0700", "files": "0600"},
            "created_files": sum(not entry.directory for entry in capability._entries),
            "created_directories": sum(entry.directory for entry in capability._entries),
            "before_sha256": expected_before_sha256, "manifest_sha256": validated["manifest_sha256"],
            "components": {key: {field: value[field] for field in ("sha256", "bytes")}
                           for key, value in validated["components"].items()},
        }
        return capability
    except BaseException as error:
        cleanup_failed = False
        if capability is not None:
            try:
                capability.cleanup()
            except (RestoreError, OSError):
                cleanup_failed = True
                capability.close()
        if cleanup_failed:
            raise RestoreError("LANDING_FAILURE_CLEANUP_REFUSED") from None
        if isinstance(error, RestoreError):
            raise error from None
        if isinstance(error, FileExistsError):
            raise RestoreError("LANDING_COLLISION") from None
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise error
        raise RestoreError("LANDING_FAILED") from None
