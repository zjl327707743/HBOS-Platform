"""Bounded single-message stdio framing; importing this module performs no I/O.

The caller must impose a deadline on a pipe read and close its request stdin.
These codecs never infer ownership, enable a listener, or authorize execution.
"""
from __future__ import annotations

import io
import json
import struct
from typing import BinaryIO

from .common import RestoreError
from . import relay

MAGIC = b"HBOSRF1\n"
MAX_METADATA_BYTES = 64 * 1024
PREFIX_BYTES = len(MAGIC) + 8
MAX_REQUEST_FRAME_BYTES = PREFIX_BYTES + MAX_METADATA_BYTES + relay.MAX_REQUEST_BODY_BYTES
MAX_RESPONSE_FRAME_BYTES = PREFIX_BYTES + MAX_METADATA_BYTES + relay.MAX_RESPONSE_BODY_BYTES


def _reject():
    raise RestoreError("WIRE_FRAME_REJECTED") from None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject()
        result[key] = value
    return result


def _bad_constant(_value):
    _reject()


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    # Reserve at most the already-validated length. A hostile short-read stream
    # cannot turn an 8 MiB frame into millions of retained tiny bytes objects.
    result = bytearray(count)
    offset = 0
    remaining = count
    while remaining:
        try:
            data = stream.read(remaining)
        except Exception:
            _reject()
        if type(data) is not bytes or not data or len(data) > remaining:
            _reject()
        result[offset:offset + len(data)] = data
        offset += len(data)
        remaining -= len(data)
    return bytes(result)


def _read_frame(stream: BinaryIO, *, kind: str, maximum_body: int):
    prefix = _read_exact(stream, PREFIX_BYTES)
    if prefix[:len(MAGIC)] != MAGIC:
        _reject()
    metadata_length, body_length = struct.unpack("!II", prefix[len(MAGIC):])
    if not 1 <= metadata_length <= MAX_METADATA_BYTES or body_length > maximum_body:
        _reject()
    raw_metadata = _read_exact(stream, metadata_length)
    body = _read_exact(stream, body_length)
    try:
        extra = stream.read(1)
    except Exception:
        _reject()
    if type(extra) is not bytes or extra:
        _reject()
    try:
        metadata = json.loads(raw_metadata.decode("utf-8", errors="strict"),
                              object_pairs_hook=_pairs, parse_constant=_bad_constant)
    except Exception:
        _reject()
    expected = {"version", "kind", "method", "target", "headers"} if kind == "request" else {"version", "kind", "status", "headers"}
    if type(metadata) is not dict or set(metadata) != expected or type(metadata["version"]) is not int or metadata["version"] != 1 or metadata["kind"] != kind:
        _reject()
    headers = metadata["headers"]
    if type(headers) is not list or len(headers) > relay.MAX_HEADERS:
        _reject()
    checked = []
    for pair in headers:
        if type(pair) is not list or len(pair) != 2 or any(type(value) is not str for value in pair):
            _reject()
        checked.append(tuple(pair))
    return metadata, checked, body


def revalidate_request(request: relay.AllowedRequest) -> relay.AllowedRequest:
    if type(request) is not relay.AllowedRequest or type(request.headers) is not tuple:
        _reject()
    validated = relay.validate_request(request.method, request.target, list(request.headers), request.body)
    if validated.route_id != request.route_id:
        _reject()
    return validated


def _pack(metadata: dict, body: bytes) -> bytes:
    try:
        raw = json.dumps(metadata, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    except Exception:
        _reject()
    if not 1 <= len(raw) <= MAX_METADATA_BYTES:
        _reject()
    return MAGIC + struct.pack("!II", len(raw), len(body)) + raw + body


def encode_request(request: relay.AllowedRequest) -> bytes:
    request = revalidate_request(request)
    return _pack({"version": 1, "kind": "request", "method": request.method,
                  "target": request.target, "headers": request.headers}, request.body)


def read_request(stream: BinaryIO) -> relay.AllowedRequest:
    metadata, headers, body = _read_frame(stream, kind="request", maximum_body=relay.MAX_REQUEST_BODY_BYTES)
    return relay.validate_request(metadata["method"], metadata["target"], headers, body)


def decode_request(frame: bytes) -> relay.AllowedRequest:
    if type(frame) is not bytes or len(frame) > MAX_REQUEST_FRAME_BYTES:
        _reject()
    return read_request(io.BytesIO(frame))


def encode_response(response: relay.AllowedResponse) -> bytes:
    if type(response) is not relay.AllowedResponse or type(response.headers) is not tuple:
        _reject()
    response = relay.validate_response(response.status, list(response.headers), response.body)
    return _pack({"version": 1, "kind": "response", "status": response.status,
                  "headers": response.headers}, response.body)


def read_response(stream: BinaryIO) -> relay.AllowedResponse:
    metadata, headers, body = _read_frame(stream, kind="response", maximum_body=relay.MAX_RESPONSE_BODY_BYTES)
    return relay.validate_response(metadata["status"], headers, body)


def decode_response(frame: bytes) -> relay.AllowedResponse:
    if type(frame) is not bytes or len(frame) > MAX_RESPONSE_FRAME_BYTES:
        _reject()
    return read_response(io.BytesIO(frame))
