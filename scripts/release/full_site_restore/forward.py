"""Explicitly gated, one-request clone loopback forwarder; import has no I/O.

Only an outer owned-resource gate may invoke the fixed runtime entry point.
The enable flag is necessary but is not evidence of ownership or authorization.
No listener, Docker operation, database connection, or redirect handling exists.
"""
from __future__ import annotations

import http.client
import io
import math
import re
import socket
import sys
import time
from typing import BinaryIO, Callable

from .common import SITE, RestoreError
from . import relay, wire

UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 8080
READ_CHUNK_BYTES = 64 * 1024


def _reject(code="FORWARD_UPSTREAM_REJECTED"):
    raise RestoreError(code) from None


class _HeaderReader:
    """Limit raw headers while HTTPResponse parses them, before buffering."""

    def __init__(self, source):
        self.source = source
        self.bytes = 0
        self.lines = 0
        self.done = False

    def readline(self, size=-1):
        if self.done:
            return self.source.readline(size)
        remaining = relay.MAX_HEADER_BYTES - self.bytes
        bound = min(size, remaining + 1) if size >= 0 else remaining + 1
        line = self.source.readline(bound)
        if type(line) is not bytes or not line or not line.endswith(b"\r\n"):
            _reject()
        self.bytes += len(line)
        self.lines += 1
        if self.bytes > relay.MAX_HEADER_BYTES:
            _reject()
        if self.lines == 1:
            if not re.fullmatch(rb"HTTP/1\.[01] [0-9]{3}(?: [\x20-\x7e]{0,256})?\r\n", line):
                _reject()
        else:
            if line == b"\r\n":
                self.done = True
            elif self.lines > relay.MAX_HEADERS + 1:
                _reject()
            else:
                name, separator, value = line[:-2].partition(b":")
                if (not separator or not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]{1,64}", name)
                        or any(byte < 32 or byte >= 127 for byte in value)):
                    # EmailMessage otherwise silently ignores malformed fields
                    # and can hide subsequent headers from the relay validator.
                    _reject()
        return line

    def __getattr__(self, name):
        return getattr(self.source, name)


class _BoundedResponse(http.client.HTTPResponse):
    def __init__(self, connection_socket, *args, deadline, clock, **kwargs):
        self._completed_fp = None
        super().__init__(connection_socket, *args, **kwargs)
        self.fp.close()
        raw = _DeadlineRaw(connection_socket.makefile("rb", buffering=0),
                           connection_socket, deadline, clock)
        self.fp = _HeaderReader(io.BufferedReader(raw, buffer_size=relay.MAX_HEADER_BYTES))

    def _close_conn(self):
        # HTTPResponse normally closes and discards its BufferedReader exactly
        # at Content-Length. Retain it until the required Connection-close EOF
        # check, including bytes already prefetched beyond that declared body.
        if self.fp is not None:
            if self._completed_fp is not None:
                _reject()
            self._completed_fp = self.fp
            self.fp = None

    def verify_eof(self):
        source = self.fp if self.fp is not None else self._completed_fp
        if source is None or source.read(1) != b"":
            _reject()

    def close(self):
        try:
            super().close()
        finally:
            if self._completed_fp is not None:
                self._completed_fp.close()
                self._completed_fp = None

    def _read_status(self):
        version, status, reason = super()._read_status()
        if status < 200 or version not in {"HTTP/1.0", "HTTP/1.1"}:
            _reject()
        return version, status, reason


class _DeadlineRaw(io.RawIOBase):
    """Absolute deadline per recv, including slow-drip header readline reads."""

    def __init__(self, source, connection_socket, deadline, clock):
        self.source = source
        self.connection_socket = connection_socket
        self.deadline = deadline
        self.clock = clock

    def readable(self):
        return True

    def readinto(self, buffer):
        self.connection_socket.settimeout(_remaining(self.clock, self.deadline, relay.READ_TIMEOUT_SECONDS))
        result = self.source.readinto(buffer)
        _remaining(self.clock, self.deadline, relay.READ_TIMEOUT_SECONDS)
        return result

    def close(self):
        if not self.closed:
            self.source.close()
        super().close()


class _LoopbackConnection(http.client.HTTPConnection):
    def configure_deadline(self, deadline, clock):
        self.response_class = lambda *args, **kwargs: _BoundedResponse(
            *args, deadline=deadline, clock=clock, **kwargs)

    def connect(self):
        # Use AF_INET and a numeric literal directly: no getaddrinfo, environment
        # proxy selection, alternate address, or tunnel can choose a destination.
        if self.host != UPSTREAM_HOST or self.port != UPSTREAM_PORT or self._tunnel_host is not None:
            _reject()
        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            connection_socket.settimeout(self.timeout)
            connection_socket.connect((UPSTREAM_HOST, UPSTREAM_PORT))
        except Exception:
            connection_socket.close()
            _reject()
        self.sock = connection_socket


def _deadline(clock: Callable[[], float], total_deadline):
    try:
        now = clock()
    except Exception:
        _reject("FORWARD_DEADLINE_REJECTED")
    if type(now) not in (int, float) or not math.isfinite(now):
        _reject("FORWARD_DEADLINE_REJECTED")
    if total_deadline is not None and (type(total_deadline) not in (int, float) or not math.isfinite(total_deadline)):
        _reject("FORWARD_DEADLINE_REJECTED")
    deadline = now + relay.TOTAL_TIMEOUT_SECONDS
    if total_deadline is not None:
        deadline = min(deadline, total_deadline)
    if deadline <= now:
        _reject("FORWARD_DEADLINE_REJECTED")
    return deadline


def _remaining(clock, deadline, ceiling):
    try:
        now = clock()
    except Exception:
        _reject("FORWARD_DEADLINE_REJECTED")
    if type(now) not in (int, float) or not math.isfinite(now) or deadline <= now:
        _reject("FORWARD_DEADLINE_REJECTED")
    return min(ceiling, deadline - now)


def _upstream_headers(status, headers):
    # Framework Date/Server and an exact Connection: close are transport
    # metadata only. Every other returned field still crosses the relay policy.
    values = relay._checked_headers(headers, "FORWARD_UPSTREAM_REJECTED", response=True)
    forwarded = []
    declared = None
    for key, value in values:
        if key in {"transfer-encoding", "content-encoding"}:
            _reject()
        if key == "connection":
            if value.lower() != "close":
                _reject()
        elif key in {"date", "server"}:
            if len(value) > 256:
                _reject()
        else:
            if key == "content-length":
                if not re.fullmatch(r"0|[1-9][0-9]{0,8}", value):
                    _reject()
                declared = int(value)
                if declared > relay.MAX_RESPONSE_BODY_BYTES:
                    _reject()
            forwarded.append((key, value))
    relay.validate_response(status, [(key, value) for key, value in forwarded if key != "content-length"], b"")
    return forwarded, declared


def forward_request(request: relay.AllowedRequest, *, enabled: bool = False,
                    total_deadline: float | None = None,
                    connection_factory=None, clock=None) -> relay.AllowedResponse:
    """Forward one policy-valid request to fixed clone nginx, with no redirect.

    The factory and clock injection points are for offline tests. The runtime
    main never accepts their values, an upstream address, or arbitrary headers.
    """
    if type(enabled) is not bool or not enabled:
        _reject("FORWARD_NOT_ENABLED")
    request = wire.revalidate_request(request)
    connection_factory = _LoopbackConnection if connection_factory is None else connection_factory
    clock = time.monotonic if clock is None else clock
    deadline = _deadline(clock, total_deadline)
    connection = None
    response = None
    try:
        headers = [*request.headers, ("x-frappe-site-name", SITE), ("connection", "close")]
        relay._checked_headers(headers, "FORWARD_UPSTREAM_REJECTED")
        connection = connection_factory(UPSTREAM_HOST, UPSTREAM_PORT,
                                        timeout=_remaining(clock, deadline, relay.CONNECT_TIMEOUT_SECONDS))
        if type(connection) is _LoopbackConnection:
            connection.configure_deadline(deadline, clock)
        connection.set_debuglevel(0)
        connection.connect()
        if connection.sock is None:
            _reject()
        active_socket = connection.sock
        active_socket.settimeout(_remaining(clock, deadline, relay.READ_TIMEOUT_SECONDS))
        connection.putrequest(request.method, request.target, skip_host=True, skip_accept_encoding=True)
        for name, value in headers:
            connection.putheader(name, value)
        connection.endheaders(request.body)
        active_socket.settimeout(_remaining(clock, deadline, relay.READ_TIMEOUT_SECONDS))
        response = connection.getresponse()
        checked_headers, declared = _upstream_headers(response.status, response.getheaders())
        chunks = []
        size = 0
        while True:
            active_socket.settimeout(_remaining(clock, deadline, relay.READ_TIMEOUT_SECONDS))
            chunk = response.read(min(READ_CHUNK_BYTES, relay.MAX_RESPONSE_BODY_BYTES - size + 1))
            _remaining(clock, deadline, relay.READ_TIMEOUT_SECONDS)
            if type(chunk) is not bytes:
                _reject()
            if not chunk:
                break
            size += len(chunk)
            if size > relay.MAX_RESPONSE_BODY_BYTES or (declared is not None and size > declared):
                _reject()
            chunks.append(chunk)
        if declared is not None and size != declared:
            _reject()
        response.verify_eof()
        _remaining(clock, deadline, relay.READ_TIMEOUT_SECONDS)
        result = relay.validate_response(response.status, checked_headers, b"".join(chunks))
        _remaining(clock, deadline, relay.READ_TIMEOUT_SECONDS)
        return result
    except RestoreError:
        raise
    except Exception:
        _reject()
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def main(argv=None, *, stdin: BinaryIO | None = None,
         stdout: BinaryIO | None = None, forwarder=None) -> int:
    # No parser accepts a caller-controlled endpoint, header, Site, or command.
    args = sys.argv[1:] if argv is None else argv
    if type(args) is not list or args != ["--owned-runtime-enabled"]:
        return 2
    source = sys.stdin.buffer if stdin is None else stdin
    destination = sys.stdout.buffer if stdout is None else stdout
    operation = forward_request if forwarder is None else forwarder
    try:
        request = wire.read_request(source)
        response = operation(request, enabled=True)
        frame = wire.encode_response(response)
        result = destination.write(frame)
        if result != len(frame):
            return 3
        destination.flush()
        return 0
    except Exception:
        # Never write a traceback, exception text, credentials, or native body.
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
