"""Read-only, bounded validation of explicitly pinned backup inputs.

This module never extracts archives, opens SQL connections, copies inputs, or
returns configuration, SQL, filenames, credentials or personal data. A caller
must use the same pinned bytes again for any separately reviewed landing step.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import tarfile
import zlib

from .common import APP_NAMES, DATABASE_SHA256, SITE, RestoreError

COMPONENTS = ("database", "site_config", "public_files", "private_files", "auth_files")
MAX_JSON_BYTES = 256 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_INPUT_BYTES = 128 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_PAYLOAD_BYTES = 256 * 1024 * 1024
MAX_TOTAL_PAYLOAD_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 10_000
MAX_TOTAL_MEMBERS = 20_000
MAX_PATH_BYTES = 1024
CHUNK_BYTES = 1024 * 1024
AUTH_NAMES = frozenset(("hbos_feishu_app_secret", "hbos_feishu_tenant_key",
                        "hbos_knowledge_gateway_token"))
REQUIRED_AUTH_NAMES = AUTH_NAMES - {"hbos_knowledge_gateway_token"}
FINGERPRINT_KEYS = frozenset(("database_fingerprint", "user_fingerprint", "credential_fingerprint",
                              "role_fingerprint", "permission_fingerprint", "identity_fingerprint",
                              "business_association_fingerprint"))
BEFORE_KEYS = FINGERPRINT_KEYS | {"site", "installed_apps", "user_count", "identity_table_present",
                                 "business_counts", "encryption_key_present", "legacy_feishu_social_keys",
                                 "csrf_enabled"}
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _fail(code: str) -> None:
    raise RestoreError(code)


def _sha(value: object) -> bool:
    return type(value) is str and _SHA.fullmatch(value) is not None


def _snapshot(value: os.stat_result) -> tuple:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns,
            value.st_mode, value.st_uid, value.st_gid, value.st_nlink)


@contextmanager
def _staging_directory(path: Path):
    """Anchor every ancestor with directory FDs; never follow a path link."""
    if not isinstance(path, Path) or path.anchor != "/" or not path.is_absolute() or ".." in path.parts:
        _fail("INPUT_PATH_INVALID")
    descriptors: list[int] = []
    entries: list[tuple[int, str, int]] = []
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open("/", flags)
        descriptors.append(descriptor)
        for name in path.parts[1:]:
            child = os.open(name, flags, dir_fd=descriptor)
            descriptors.append(child)
            entries.append((descriptor, name, child))
            descriptor = child
        before = os.fstat(descriptor)
        if not stat.S_ISDIR(before.st_mode) or stat.S_IMODE(before.st_mode) != 0o700 or before.st_uid != os.geteuid():
            _fail("STAGING_PERMISSIONS_INVALID")
        yield descriptor
        if _snapshot(os.fstat(descriptor)) != _snapshot(before):
            _fail("STAGING_CHANGED")
        for parent, name, child in entries:
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            anchored = os.fstat(child)
            if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != (anchored.st_dev, anchored.st_ino):
                _fail("STAGING_CHANGED")
    except RestoreError:
        raise
    except (OSError, ValueError, AttributeError):
        raise RestoreError("INPUT_PATH_INVALID") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


@contextmanager
def _input_file(directory: int, name: str, limit: int):
    descriptor = None
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_uid != os.geteuid() or stat.S_IMODE(before.st_mode) != 0o600):
            _fail("INPUT_FILE_IDENTITY_INVALID")
        if before.st_size < 1 or before.st_size > limit:
            _fail("INPUT_SIZE_INVALID")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            yield stream, before
        after = os.fstat(descriptor)
        entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if _snapshot(before) != _snapshot(after) or _snapshot(entry) != _snapshot(before):
            _fail("INPUT_CHANGED")
    except RestoreError:
        raise
    except (OSError, ValueError):
        raise RestoreError("INPUT_FILE_INVALID") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_bytes(stream, limit: int) -> bytes:
    result = io.BytesIO()
    count = 0
    while chunk := stream.read(min(CHUNK_BYTES, limit - count + 1)):
        count += len(chunk)
        if count > limit:
            _fail("INPUT_SIZE_INVALID")
        result.write(chunk)
    return result.getvalue()


def _fingerprint(stream, limit: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    while chunk := stream.read(CHUNK_BYTES):
        count += len(chunk)
        if count > limit:
            _fail("INPUT_SIZE_INVALID")
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest(), count


def _json_object(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("INPUT_JSON_INVALID")
            result[key] = value
        return result

    def constant(_value):
        _fail("INPUT_JSON_INVALID")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
        if type(value) is not dict:
            _fail("INPUT_JSON_INVALID")
        # Refuse nonfinite values produced by finite-looking overflow literals.
        def check(item, depth=0):
            if depth > 32:
                _fail("INPUT_JSON_INVALID")
            if type(item) is float and not math.isfinite(item):
                _fail("INPUT_JSON_INVALID")
            if type(item) in (dict, list):
                for child in item.values() if type(item) is dict else item:
                    check(child, depth + 1)
        check(value)
        return value
    except RestoreError:
        raise
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        raise RestoreError("INPUT_JSON_INVALID") from None


def _validate_before(value: dict) -> None:
    if set(value) != BEFORE_KEYS or value.get("site") != SITE:
        _fail("BEFORE_SCHEMA_INVALID")
    if any(not _sha(value[key]) for key in FINGERPRINT_KEYS) or value["database_fingerprint"] != DATABASE_SHA256:
        _fail("BEFORE_SCHEMA_INVALID")
    apps = value["installed_apps"]
    if type(apps) is not list or any(type(app) is not str for app in apps) or len(apps) != len(APP_NAMES) or set(apps) != set(APP_NAMES):
        _fail("BEFORE_SCHEMA_INVALID")
    for key in ("identity_table_present", "encryption_key_present", "csrf_enabled"):
        if type(value[key]) is not bool:
            _fail("BEFORE_SCHEMA_INVALID")
    for key in ("user_count", "legacy_feishu_social_keys"):
        if type(value[key]) is not int or not 0 <= value[key] <= 10_000_000:
            _fail("BEFORE_SCHEMA_INVALID")
    counts = value["business_counts"]
    if (type(counts) is not dict or not set(counts) <= {"Employee", "Employee Checkin", "Attendance"}
            or any(type(count) is not int or not 0 <= count <= 10_000_000 for count in counts.values())):
        _fail("BEFORE_SCHEMA_INVALID")
    if not value["encryption_key_present"] or not value["csrf_enabled"] or value["legacy_feishu_social_keys"]:
        _fail("BEFORE_SECURITY_GATE_INVALID")


def _expanded_gzip(stream, *, collect: bool = False):
    count = 0
    digest = hashlib.sha256()
    result = io.BytesIO() if collect else None
    try:
        with gzip.GzipFile(fileobj=stream, mode="rb") as source:
            while chunk := source.read(min(CHUNK_BYTES, MAX_EXPANDED_BYTES - count + 1)):
                count += len(chunk)
                if count > MAX_EXPANDED_BYTES:
                    _fail("GZIP_EXPANSION_LIMIT")
                digest.update(chunk)
                if result is not None:
                    result.write(chunk)
    except RestoreError:
        raise
    except (OSError, EOFError, zlib.error):
        raise RestoreError("GZIP_INVALID") from None
    if count == 0:
        _fail("GZIP_INVALID")
    return result.getvalue() if result is not None else {"expanded_bytes": count, "expanded_sha256": digest.hexdigest()}


def _canonical_member(name: str, is_directory: bool, component: str) -> str:
    try:
        if type(name) is not str or len(name.encode("utf-8")) > MAX_PATH_BYTES:
            _fail("TAR_PATH_INVALID")
        if is_directory and name.endswith("/"):
            name = name[:-1]
        if component != "auth_files" and name.startswith("./"):
            name = name[2:]
        if (not name or name.startswith("/") or "\\" in name or any(ord(char) < 32 or ord(char) == 127 for char in name)
                or any(part in ("", ".", "..") for part in name.split("/"))):
            _fail("TAR_PATH_INVALID")
        if component == "auth_files":
            if is_directory or name not in AUTH_NAMES:
                _fail("TAR_PATH_INVALID")
        else:
            prefix = SITE + ("/public/files" if component == "public_files" else "/private/files")
            if not (name == prefix and is_directory or name.startswith(prefix + "/")):
                _fail("TAR_PATH_INVALID")
        return name
    except UnicodeError:
        raise RestoreError("TAR_PATH_INVALID") from None


def _tar_string(field: bytes) -> str:
    value, separator, padding = field.partition(b"\0")
    if separator and padding.strip(b"\0"):
        _fail("TAR_HEADER_INVALID")
    try:
        return value.decode("utf-8")
    except UnicodeError:
        raise RestoreError("TAR_HEADER_INVALID") from None


def _pax_record(raw: bytes) -> dict:
    """Only finite mtime metadata is accepted; no path/type/owner overrides."""
    result = {}
    cursor = 0
    while cursor < len(raw):
        space = raw.find(b" ", cursor, min(len(raw), cursor + 20))
        if space < 0 or not re.fullmatch(rb"[1-9][0-9]*", raw[cursor:space]):
            _fail("TAR_PAX_INVALID")
        length = int(raw[cursor:space])
        end = cursor + length
        if end > len(raw) or end <= space + 3 or raw[end - 1:end] != b"\n":
            _fail("TAR_PAX_INVALID")
        record = raw[space + 1:end - 1]
        key, separator, value = record.partition(b"=")
        if not separator or key != b"mtime" or key in result or not re.fullmatch(rb"[0-9]{1,12}(?:\.[0-9]{1,12})?", value):
            _fail("TAR_PAX_INVALID")
        try:
            number = Decimal(value.decode("ascii"))
            if not 0 <= number < 4_102_444_800:
                _fail("TAR_PAX_INVALID")
        except (InvalidOperation, UnicodeError):
            raise RestoreError("TAR_PAX_INVALID") from None
        result[key] = value
        cursor = end
    if not result:
        _fail("TAR_PAX_INVALID")
    return result


def _validate_headers(payload: bytes, member: tarfile.TarInfo, component: str, canonical: str) -> None:
    cursor = member.offset
    metadata_count = 0
    while cursor < member.offset_data:
        block = payload[cursor:cursor + 512]
        if len(block) != 512:
            _fail("TAR_HEADER_INVALID")
        header = tarfile.TarInfo.frombuf(block, "utf-8", "strict")
        if cursor == member.offset_data - 512:
            if header.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
                _fail("TAR_TYPE_INVALID")
            raw_name = _tar_string(block[:100])
            prefix = _tar_string(block[345:500])
            if prefix:
                raw_name = prefix + "/" + raw_name
            if _canonical_member(raw_name, member.isdir(), component) != canonical:
                _fail("TAR_HEADER_INVALID")
            cursor += 512
        else:
            if header.type != tarfile.XHDTYPE or metadata_count or not 0 < header.size <= 4096:
                _fail("TAR_PAX_INVALID")
            data_start = cursor + 512
            data_end = data_start + header.size
            padded_end = data_start + ((header.size + 511) // 512) * 512
            if padded_end >= member.offset_data or any(payload[data_end:padded_end]):
                _fail("TAR_PAX_INVALID")
            _pax_record(payload[data_start:data_end])
            if set(member.pax_headers) != {"mtime"}:
                _fail("TAR_PAX_INVALID")
            metadata_count += 1
            cursor = padded_end
    if cursor != member.offset_data or (member.pax_headers and not metadata_count):
        _fail("TAR_HEADER_INVALID")


def _archive_metadata(stream, component: str) -> dict:
    magic = stream.read(2)
    stream.seek(0)
    if magic == b"\x1f\x8b":
        payload = _expanded_gzip(stream, collect=True)
    elif component == "auth_files":
        _fail("GZIP_INVALID")
    else:
        payload = _read_bytes(stream, MAX_EXPANDED_BYTES)
    if len(payload) < 1024 or len(payload) % 512:
        _fail("TAR_INVALID")
    seen = set()
    directory_paths = set()
    file_paths = set()
    files = []
    count = 0
    logical_bytes = 0
    cursor = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:", errorlevel=2) as archive:
            for member in archive:
                count += 1
                if count > MAX_MEMBERS:
                    _fail("TAR_MEMBER_LIMIT")
                if payload[cursor + 156:cursor + 157] == tarfile.XGLTYPE:
                    _fail("TAR_PAX_INVALID")
                if member.offset != cursor or member.sparse is not None or not (member.isfile() or member.isdir()):
                    _fail("TAR_TYPE_INVALID")
                if member.uid != 1000 or member.gid != 1000:
                    _fail("TAR_OWNER_INVALID")
                allowed_modes = {0o700, 0o750, 0o755} if member.isdir() else {0o600, 0o640, 0o644}
                if member.mode not in allowed_modes or component == "auth_files" and member.mode != 0o600:
                    _fail("TAR_MODE_INVALID")
                if type(member.size) is not int or not 0 <= member.size <= MAX_MEMBER_BYTES or member.isdir() and member.size:
                    _fail("TAR_SIZE_INVALID")
                canonical = _canonical_member(member.name, member.isdir(), component)
                if canonical in seen:
                    _fail("TAR_DUPLICATE_PATH")
                # A file can never be the ancestor of another member.
                ancestors = {str(parent) for parent in Path(canonical).parents if str(parent) != "."}
                if ancestors & file_paths or member.isfile() and any(item.startswith(canonical + "/") for item in seen):
                    _fail("TAR_PATH_CONFLICT")
                seen.add(canonical)
                _validate_headers(payload, member, component, canonical)
                logical_bytes += member.size
                if logical_bytes > MAX_ARCHIVE_PAYLOAD_BYTES:
                    _fail("TAR_PAYLOAD_LIMIT")
                end = member.offset_data + member.size
                cursor = member.offset_data + ((member.size + 511) // 512) * 512
                if cursor > len(payload) or any(payload[end:cursor]):
                    _fail("TAR_INVALID")
                if member.isfile():
                    file_paths.add(canonical)
                    digest = hashlib.sha256(memoryview(payload)[member.offset_data:end]).hexdigest()
                    files.append({"member": count, "bytes": member.size, "sha256": digest})
                else:
                    directory_paths.add(canonical)
    except RestoreError:
        raise
    except (tarfile.TarError, UnicodeError, ValueError, OverflowError, RecursionError, OSError, KeyError, IndexError):
        raise RestoreError("TAR_INVALID") from None
    if len(payload) - cursor < 1024 or any(memoryview(payload)[cursor:]):
        _fail("TAR_TRAILER_INVALID")
    if component == "auth_files" and (not REQUIRED_AUTH_NAMES <= file_paths or not 2 <= len(file_paths) <= 3):
        _fail("AUTH_ARCHIVE_INVALID")
    return {"members": count, "files": len(files), "directories": len(directory_paths),
            "payload_bytes": logical_bytes, "expanded_bytes": len(payload), "file_hashes": files}


def validate_backup_inputs(manifest_path: Path, expected: dict, expected_before_sha256: str,
                           expected_manifest_sha256: str | None = None) -> dict:
    """Validate exactly five sibling inputs against externally pinned hashes.

    ``manifest`` is a strict object mapping the five COMPONENTS to absolute
    sibling paths; ``before.json`` is also in that 0700 staging directory.
    ``expected`` maps each component to exactly ``sha256`` and ``bytes``.
    Only aggregate metadata and indexed member hashes are returned. This is
    validation-only, not a durable landing/extraction or SQL restore capability.
    """
    if (type(expected) is not dict or set(expected) != set(COMPONENTS)
            or not _sha(expected_before_sha256)
            or expected_manifest_sha256 is not None and not _sha(expected_manifest_sha256)):
        _fail("INPUT_EXPECTATION_INVALID")
    for component in COMPONENTS:
        item = expected[component]
        limit = MAX_JSON_BYTES if component == "site_config" else MAX_INPUT_BYTES
        if (type(item) is not dict or set(item) != {"sha256", "bytes"} or not _sha(item["sha256"])
                or type(item["bytes"]) is not int or not 0 < item["bytes"] <= limit):
            _fail("INPUT_EXPECTATION_INVALID")
    if (not isinstance(manifest_path, Path) or manifest_path.anchor != "/"
            or not manifest_path.is_absolute() or ".." in manifest_path.parts):
        _fail("INPUT_PATH_INVALID")
    staging = manifest_path.parent
    result = {"status": "VALIDATED_ONLY", "landing": "NOT_IMPLEMENTED", "components": {}}
    # Keep every admitted descriptor until the entire validation completes.
    # A component changed while a later component is checked must still fail.
    with _staging_directory(staging) as directory, ExitStack() as opened:
        stream, _metadata = opened.enter_context(_input_file(directory, manifest_path.name, MAX_MANIFEST_BYTES))
        raw = _read_bytes(stream, MAX_MANIFEST_BYTES)
        result["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        if expected_manifest_sha256 is not None and result["manifest_sha256"] != expected_manifest_sha256:
            _fail("MANIFEST_HASH_MISMATCH")
        manifest = _json_object(raw)
        if set(manifest) != set(COMPONENTS):
            _fail("MANIFEST_SCHEMA_INVALID")
        names = {manifest_path.name, "before.json"}
        component_names = {}
        for component, path in manifest.items():
            if type(path) is not str:
                _fail("MANIFEST_SCHEMA_INVALID")
            candidate = Path(path)
            if (candidate.anchor != "/" or not candidate.is_absolute() or candidate.parent != staging or ".." in candidate.parts
                    or str(candidate) != path or candidate.name in names):
                _fail("MANIFEST_PATH_INVALID")
            names.add(candidate.name)
            component_names[component] = candidate.name
        stream, _metadata = opened.enter_context(_input_file(directory, "before.json", MAX_JSON_BYTES))
        raw = _read_bytes(stream, MAX_JSON_BYTES)
        if hashlib.sha256(raw).hexdigest() != expected_before_sha256:
            _fail("BEFORE_HASH_MISMATCH")
        _validate_before(_json_object(raw))
        result["before_sha256"] = expected_before_sha256
        total_bytes = 0
        total_members = 0
        for component in COMPONENTS:
            limit = MAX_JSON_BYTES if component == "site_config" else MAX_INPUT_BYTES
            stream, metadata = opened.enter_context(_input_file(directory, component_names[component], limit))
            digest, count = _fingerprint(stream, limit)
            if digest != expected[component]["sha256"] or count != expected[component]["bytes"] or count != metadata.st_size:
                _fail("COMPONENT_HASH_MISMATCH")
            summary = {"sha256": digest, "bytes": count}
            if component == "database":
                summary.update(_expanded_gzip(stream))
            elif component == "site_config":
                config = _json_object(_read_bytes(stream, MAX_JSON_BYTES))
                database = config.get("db_name")
                key = config.get("encryption_key")
                try:
                    database_sha = hashlib.sha256(database.encode("utf-8")).hexdigest() if type(database) is str else None
                except UnicodeError:
                    raise RestoreError("SITE_CONFIG_GATE_INVALID") from None
                if (type(database) is not str or not 0 < len(database) <= 256
                        or database_sha != DATABASE_SHA256
                        or type(key) is not str or not key):
                    _fail("SITE_CONFIG_GATE_INVALID")
                summary.update({"database_sha256": DATABASE_SHA256, "encryption_key_present": True})
            else:
                summary.update(_archive_metadata(stream, component))
                total_bytes += summary["payload_bytes"]
                total_members += summary["members"]
                if total_bytes > MAX_TOTAL_PAYLOAD_BYTES or total_members > MAX_TOTAL_MEMBERS:
                    _fail("TAR_TOTAL_LIMIT")
            result["components"][component] = summary
    return result
