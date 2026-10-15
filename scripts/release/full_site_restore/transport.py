"""Bounded host HTTP codecs and fixed Docker stdio child component.

Import is inert. The production facade is hard gated by LifecycleRegistry and
does not bind a socket. The private child component is independently testable;
it is not ownership admission, a Docker exec receipt, or container-child reap
proof. Killing/reaping the host CLI cannot prove the container exec has exited.
"""
from __future__ import annotations

import math
import os
import re
import selectors
import subprocess
import threading
import time

from .common import RestoreError
from . import relay, wire
from .lifecycle import LifecycleRegistry
from .ownership import ResourceRecord

MAX_STDERR_BYTES = 4096
MAX_HTTP_REQUEST_BYTES = relay.MAX_HEADER_BYTES + relay.MAX_TARGET_BYTES + relay.MAX_REQUEST_BODY_BYTES + 128
_REASONS = {200: "OK", 204: "No Content", 301: "Moved Permanently", 302: "Found",
    303: "See Other", 307: "Temporary Redirect", 308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
    405: "Method Not Allowed", 409: "Conflict", 413: "Content Too Large",
    415: "Unsupported Media Type", 429: "Too Many Requests", 500: "Internal Server Error",
    502: "Bad Gateway", 503: "Service Unavailable"}


def _fail(code="HOST_TRANSPORT_REJECTED"):
    raise RestoreError(code) from None


def decode_http_request(frame: bytes) -> relay.AllowedRequest:
    """One complete HTTP/1.1 request, never a socket reader or keepalive parser."""
    if type(frame) is not bytes or len(frame) > MAX_HTTP_REQUEST_BYTES:
        _fail()
    head, separator, body = frame.partition(b"\r\n\r\n")
    if not separator or len(head) > relay.MAX_HEADER_BYTES + relay.MAX_TARGET_BYTES + 32:
        _fail()
    try:
        lines = head.decode("ascii", errors="strict").split("\r\n")
    except UnicodeError:
        _fail()
    first = lines.pop(0).split(" ")
    if len(first) != 3 or first[2] != "HTTP/1.1" or len(lines) > relay.MAX_HEADERS:
        _fail()
    headers = []
    for line in lines:
        key, colon, value = line.partition(":")
        if not colon or line.startswith((" ", "\t")):
            _fail()
        # Only ordinary SP after the colon; controls and invalid names are then
        # rejected by the shared request policy, including duplicates and TE.
        headers.append((key, value.lstrip(" ")))
    values = {key.lower(): value for key, value in headers}
    length = values.get("content-length")
    if length is not None and (not re.fullmatch(r"0|[1-9][0-9]{0,8}", length) or int(length) != len(body)):
        _fail()
    if first[0] == "POST" and length is None:
        _fail()
    if first[0] == "GET" and body:
        _fail()
    return relay.validate_request(first[0], first[1], headers, body)


def encode_http_response(response: relay.AllowedResponse) -> bytes:
    if type(response) is not relay.AllowedResponse or type(response.headers) is not tuple:
        _fail()
    checked = relay.validate_response(response.status, list(response.headers), response.body)
    lines = ["HTTP/1.1 " + str(checked.status) + " " + _REASONS[checked.status]]
    lines.extend(key + ": " + value for key, value in checked.headers)
    lines.append("connection: close")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii") + checked.body


def _reap_host_child(process):
    """Signal only the Popen child; never infer container exec exit from this."""
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0.25)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=0.25)
        else:
            process.wait(timeout=0.25)
    except Exception:
        _fail("HOST_CHILD_REAP_UNCONFIRMED")


def _exchange_child(new_backend_id, original_ids, request_frame: bytes, *,
                    remaining_seconds: float, enabled=False) -> relay.AllowedResponse:
    """Fixed low-level subprocess component. Production facade cannot enable it.

    Tests replace Popen with a synthetic local child. No target, shell, env,
    callback or command arguments can be supplied to this component.
    """
    if enabled is not True:
        _fail("HOST_TRANSPORT_DISABLED")
    try:
        if type(remaining_seconds) not in (int, float):
            _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
        budget = float(remaining_seconds)
        if not math.isfinite(budget) or budget <= 0:
            _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
    except (OverflowError, ValueError):
        _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
    wire.decode_request(request_frame)
    argv = relay.build_exec_argv(new_backend_id, original_ids) + ("--owned-runtime-enabled",)
    deadline = time.monotonic() + min(budget, relay.TOTAL_TIMEOUT_SECONDS)
    process = None
    output = bytearray()
    stderr_bytes = 0
    offset = 0
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, close_fds=True, bufsize=0, env={})
        with selectors.DefaultSelector() as selector:
            streams = ((process.stdin, selectors.EVENT_WRITE, "stdin"),
                       (process.stdout, selectors.EVENT_READ, "stdout"),
                       (process.stderr, selectors.EVENT_READ, "stderr"))
            for stream, event, kind in streams:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, event, kind)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
                for key, _mask in selector.select(min(remaining, 0.1)):
                    if time.monotonic() >= deadline:
                        _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
                    try:
                        if key.data == "stdin":
                            written = os.write(key.fd, memoryview(request_frame)[offset:offset + 65536])
                            if written <= 0:
                                _fail()
                            offset += written
                            if offset == len(request_frame):
                                selector.unregister(key.fileobj)
                                key.fileobj.close()
                        else:
                            data = os.read(key.fd, 65536)
                            if not data:
                                selector.unregister(key.fileobj)
                                key.fileobj.close()
                            elif key.data == "stdout":
                                if len(output) + len(data) > wire.MAX_RESPONSE_FRAME_BYTES:
                                    _fail("HOST_TRANSPORT_OUTPUT_LIMIT")
                                output.extend(data)
                            else:
                                stderr_bytes += len(data)
                                if stderr_bytes > MAX_STDERR_BYTES:
                                    _fail("HOST_TRANSPORT_STDERR_LIMIT")
                    except BlockingIOError:
                        continue
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
            if process.wait(timeout=remaining) != 0 or stderr_bytes:
                _fail("HOST_TRANSPORT_CHILD_FAILED")
            result = wire.decode_response(bytes(output))
            if time.monotonic() >= deadline:
                _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
            return result
    except RestoreError:
        raise
    except subprocess.TimeoutExpired:
        _fail("HOST_TRANSPORT_DEADLINE_EXPIRED")
    except Exception:
        _fail()
    finally:
        if process is not None:
            try:
                _reap_host_child(process)
            finally:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        try:
                            stream.close()
                        except Exception:
                            pass


class OwnedRelayTransport:
    """Closed production facade. No listener, creation or callback admission."""
    def __init__(self, registry):
        if type(registry) is not LifecycleRegistry:
            _fail("HOST_TRANSPORT_REGISTRY_REQUIRED")
        self.registry = registry
        self._lock = threading.Lock()

    def admit_listener(self):
        self.registry.require_service_ready()
        _fail("HOST_LISTENER_NOT_IMPLEMENTED")

    def exchange(self, request, *, fresh_backend_metadata):
        # Never bind/spawn first and validate afterwards. Current service gate
        # is hard closed even when callers supply REAL-shaped proof DTOs.
        self.registry.require_service_ready()
        if not self._lock.acquire(blocking=False):
            _fail("HOST_TRANSPORT_BUSY")
        try:
            record = self.registry.obtain_precheck_backend()
            baseline = self.registry.baseline
            fresh = ResourceRecord.from_inspect(fresh_backend_metadata, expected=record.spec,
                original_ids=baseline.container_ids, original_names=baseline.container_names,
                original_volume_names=baseline.volume_names, db_id=record.db_id)
            if fresh.container_id != record.container_id or fresh.metadata_sha256 != record.metadata_sha256:
                _fail("HOST_TRANSPORT_RESOURCE_CHANGED")
            wire.encode_request(request)
            # Precheck records admit sleep only. Real service records, persisted
            # operation receipts and container exec PID/exit capture are absent.
            _fail("HOST_TRANSPORT_CONTAINER_EXEC_REGISTRATION_NOT_IMPLEMENTED")
        finally:
            self._lock.release()
