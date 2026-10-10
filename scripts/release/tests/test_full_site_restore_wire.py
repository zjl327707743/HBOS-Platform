from __future__ import annotations

import importlib
import io
import json
from pathlib import Path
import socket
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from full_site_restore.common import HOST, ORIGIN, SITE, RestoreError
from full_site_restore import forward, relay, wire


class FakeSocket:
    def __init__(self, raw=b""):
        self.raw = raw
        self.timeouts = []
        self.connected = None
        self.closed = False

    def settimeout(self, value):
        self.timeouts.append(value)

    def connect(self, address):
        self.connected = address

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self.raw)

    def close(self):
        self.closed = True


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"{}", *, read_hook=None):
        self.status = status
        self.headers = headers if headers is not None else [("Content-Type", "application/json"), ("Content-Length", str(len(body)))]
        self.stream = io.BytesIO(body)
        self.closed = False
        self.read_hook = read_hook

    def getheaders(self):
        return self.headers

    def read(self, size):
        if self.read_hook:
            self.read_hook()
        return self.stream.read(size)

    def close(self):
        self.closed = True

    def verify_eof(self):
        if self.stream.read(1):
            raise RestoreError("FORWARD_UPSTREAM_REJECTED")


class FakeConnection:
    def __init__(self, response, *, failure=None, response_hook=None):
        self.sock = FakeSocket()
        self.response = response
        self.failure = failure
        self.response_hook = response_hook
        self.closed = False
        self.headers = []
        self.request = None
        self.body = None
        self.response_calls = 0

    def set_debuglevel(self, value):
        self.debuglevel = value

    def connect(self):
        if self.failure:
            raise self.failure

    def putrequest(self, method, target, **options):
        self.request = (method, target, options)

    def putheader(self, name, value):
        self.headers.append((name, value))

    def endheaders(self, body):
        self.body = body

    def getresponse(self):
        self.response_calls += 1
        if self.response_hook:
            self.response_hook()
        return self.response

    def close(self):
        self.closed = True


class PartialStream(io.BytesIO):
    def read(self, count=-1):
        return super().read(min(count, 3))


class NoIO:
    def read(self, _count):
        raise AssertionError("disabled main read stdin")

    def write(self, _value):
        raise AssertionError("disabled main wrote stdout")


class RestoreWireTest(unittest.TestCase):
    def ping(self):
        return relay.validate_request("GET", "/api/method/frappe.ping", [("Host", HOST)], b"")

    def login(self):
        return relay.validate_request("POST", "/api/method/login", [("Host", HOST), ("Origin", ORIGIN), ("Content-Type", "application/x-www-form-urlencoded"), ("Cookie", "sid=SYNTHETIC-CLONE-SID")], b"usr=synthetic%40example.invalid&pwd=DO_NOT_PRINT%252F")

    def raw_frame(self, metadata, body=b"", *, raw_metadata=None):
        raw = json.dumps(metadata).encode() if raw_metadata is None else raw_metadata
        return wire.MAGIC + struct.pack("!II", len(raw), len(body)) + raw + body

    def request_metadata(self):
        return {"version": 1, "kind": "request", "method": "GET", "target": "/api/method/frappe.ping", "headers": [["Host", HOST]]}

    def rejected(self, callback, expected=None):
        with self.assertRaises(RestoreError) as error:
            callback()
        if expected:
            self.assertEqual(str(error.exception), expected)
        self.assertNotIn("DO_NOT_PRINT", str(error.exception))
        self.assertNotIn("SYNTHETIC-CLONE-SID", str(error.exception))

    def run_forward(self, response=None, *, request=None, failure=None, clock=None, deadline=None, response_hook=None):
        connection = FakeConnection(response or FakeResponse(), failure=failure, response_hook=response_hook)
        calls = []

        def factory(*args, **kwargs):
            calls.append((args, kwargs))
            return connection

        result = forward.forward_request(request or self.ping(), enabled=True, connection_factory=factory,
                                         clock=clock or (lambda: 0.0), total_deadline=deadline)
        return result, connection, calls

    def test_request_roundtrip_keeps_password_bytes_and_private_repr(self):
        for request in (self.ping(), self.login()):
            decoded = wire.decode_request(wire.encode_request(request))
            self.assertEqual(decoded, request)
            self.assertNotIn("DO_NOT_PRINT", repr(decoded))
            self.assertNotIn("SYNTHETIC-CLONE-SID", repr(decoded))

    def test_response_roundtrip_preserves_multiple_cookies_in_order(self):
        response = relay.validate_response(200, [("Content-Type", "application/json"), ("Set-Cookie", "sid=SYNTHETIC-NEW-SID; Path=/; HttpOnly"), ("Set-Cookie", "user_id=synthetic; Path=/")], b"{}")
        decoded = wire.decode_response(wire.encode_response(response))
        self.assertEqual(decoded, response)
        self.assertEqual(len([h for h in decoded.headers if h[0] == "set-cookie"]), 2)
        self.assertNotIn("SYNTHETIC-NEW-SID", repr(decoded))

    def test_partial_reads_are_supported_without_relaxing_eof(self):
        self.assertEqual(wire.read_request(PartialStream(wire.encode_request(self.ping()))), self.ping())
        self.rejected(lambda: wire.read_request(PartialStream(wire.encode_request(self.ping()) + b"x")), "WIRE_FRAME_REJECTED")

    def test_single_frame_rejects_truncation_concatenation_and_trailing_bytes(self):
        frame = wire.encode_request(self.ping())
        for candidate in (b"", frame[:2], frame[:-1], frame + b"x", frame + frame):
            with self.subTest(length=len(candidate)):
                self.rejected(lambda: wire.decode_request(candidate), "WIRE_FRAME_REJECTED")
        response = wire.encode_response(relay.validate_response(200, [], b""))
        self.rejected(lambda: wire.decode_response(response + response), "WIRE_FRAME_REJECTED")

    def test_prefix_rejects_magic_and_oversized_lengths_before_reading_body(self):
        for candidate in (b"WRONG!!\n" + struct.pack("!II", 1, 0), wire.MAGIC + struct.pack("!II", 0, 0), wire.MAGIC + struct.pack("!II", wire.MAX_METADATA_BYTES + 1, 0), wire.MAGIC + struct.pack("!II", 1, relay.MAX_REQUEST_BODY_BYTES + 1)):
            self.rejected(lambda: wire.decode_request(candidate), "WIRE_FRAME_REJECTED")
        self.rejected(lambda: wire.decode_response(wire.MAGIC + struct.pack("!II", 1, relay.MAX_RESPONSE_BODY_BYTES + 1)), "WIRE_FRAME_REJECTED")

    def test_duplicate_json_keys_nonfinite_utf8_and_deep_json_are_rejected(self):
        for raw in (b'{"version":1,"version":1}', b'{"version":NaN}', b'\xff', b"[" * 1500 + b"]" * 1500):
            self.rejected(lambda: wire.decode_request(self.raw_frame(None, raw_metadata=raw)), "WIRE_FRAME_REJECTED")

    def test_metadata_exact_schema_kind_types_and_header_pair_types(self):
        for replacement in ({"version": True}, {"kind": "response"}, {"headers": {"Host": HOST}}, {"headers": [["Host", HOST, "extra"]]}, {"headers": [["Host", 1]]}, {"body": "DO_NOT_PRINT"}):
            metadata = self.request_metadata()
            metadata.update(replacement)
            self.rejected(lambda: wire.decode_request(self.raw_frame(metadata)), "WIRE_FRAME_REJECTED")

    def test_wire_policy_rejects_arbitrary_rpc_duplicate_host_and_cmd(self):
        for replacement in ({"target": "/api/method/frappe.client.get_list"}, {"target": "/api/method/frappe.ping?cmd=x"}, {"headers": [["Host", HOST], ["host", HOST]]}, {"headers": [["Host", HOST], ["X-Frappe-Site-Name", "original"]]}):
            metadata = self.request_metadata()
            metadata.update(replacement)
            self.rejected(lambda: wire.decode_request(self.raw_frame(metadata)), "RELAY_REQUEST_REJECTED")

    def test_wire_rejects_forged_route_id_and_unapproved_static(self):
        forged = relay.AllowedRequest("GET", "native_password_login", self.ping().target, self.ping().headers, b"")
        self.rejected(lambda: wire.encode_request(forged), "WIRE_FRAME_REJECTED")
        static = relay.validate_request("GET", "/assets/a.js", [("Host", HOST)], b"", approved_static_paths=frozenset({"/assets/a.js"}))
        self.rejected(lambda: wire.encode_request(static), "RELAY_REQUEST_REJECTED")

    def test_invalid_stream_and_frame_types_are_rejected(self):
        class InvalidStream:
            def read(self, _count):
                return bytearray(b"x")
        self.rejected(lambda: wire.read_request(InvalidStream()), "WIRE_FRAME_REJECTED")
        self.rejected(lambda: wire.decode_request(bytearray()), "WIRE_FRAME_REJECTED")

    def test_module_reload_does_not_open_socket_or_make_http_request(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")), patch.object(forward.http.client.HTTPConnection, "connect", side_effect=AssertionError("network forbidden")):
            importlib.reload(wire)
            importlib.reload(forward)

    def test_forward_is_disabled_by_default_and_requires_exact_boolean(self):
        for enabled in (False, 1, "yes", None):
            with patch.object(forward, "_LoopbackConnection", side_effect=AssertionError("network forbidden")):
                self.rejected(lambda: forward.forward_request(self.ping(), enabled=enabled), "FORWARD_NOT_ENABLED")

    def test_fixed_loopback_site_host_no_proxy_target_and_close(self):
        with patch.dict("os.environ", {"HTTP_PROXY": "http://DO_NOT_PRINT.invalid", "ALL_PROXY": "http://DO_NOT_PRINT.invalid"}):
            result, connection, calls = self.run_forward()
        self.assertEqual(result.body, b"{}")
        self.assertEqual(calls, [(("127.0.0.1", 8080), {"timeout": 2})])
        self.assertEqual(connection.request, ("GET", "/api/method/frappe.ping", {"skip_host": True, "skip_accept_encoding": True}))
        self.assertEqual(dict(connection.headers)["host"], HOST)
        self.assertEqual(dict(connection.headers)["x-frappe-site-name"], SITE)
        self.assertEqual(dict(connection.headers)["connection"], "close")
        self.assertEqual(connection.debuglevel, 0)
        self.assertTrue(connection.closed)
        self.assertTrue(connection.response.closed)

    def test_login_forward_preserves_form_and_separate_cookie_headers(self):
        response = FakeResponse(headers=[("Content-Type", "application/json"), ("Set-Cookie", "sid=SYNTHETIC-NEW-SID; Path=/; HttpOnly"), ("Set-Cookie", "user_id=synthetic; Path=/")])
        result, connection, _ = self.run_forward(response, request=self.login())
        self.assertEqual(connection.body, self.login().body)
        self.assertEqual(len([pair for pair in result.headers if pair[0] == "set-cookie"]), 2)

    def test_response_transport_metadata_stripped_and_unknown_headers_denied(self):
        result, _, _ = self.run_forward(FakeResponse(headers=[("Content-Type", "application/json"), ("Date", "Thu, 01 Jan 1970 00:00:00 GMT"), ("Server", "synthetic-nginx"), ("Connection", "close")]))
        self.assertNotIn("server", dict(result.headers))
        for name, value in (("X-Unknown", "x"), ("Connection", "keep-alive"), ("Content-Encoding", "gzip"), ("Content-Encoding", "identity"), ("Transfer-Encoding", "chunked"), ("Server", "x" * 257)):
            self.rejected(lambda: self.run_forward(FakeResponse(headers=[("Content-Type", "application/json"), (name, value)])))

    def test_redirects_are_returned_without_following_and_external_denied(self):
        result, connection, _ = self.run_forward(FakeResponse(302, [("Location", "/desk")], b""))
        self.assertEqual(result.status, 302)
        self.assertEqual(connection.response_calls, 1)
        self.rejected(lambda: self.run_forward(FakeResponse(302, [("Location", "http://127.0.0.1:5178/login")], b"")))

    def test_upstream_native_error_body_is_never_returned(self):
        result, _, _ = self.run_forward(FakeResponse(500, body=b"DO_NOT_PRINT traceback SQL secret"))
        self.assertEqual(result.body, b'{"error":"RESTORE_RELAY_UPSTREAM_REJECTED"}')

    def test_forward_revalidates_request_before_connection(self):
        forged = relay.AllowedRequest("GET", "native_ping", "/api/resource/User", self.ping().headers, b"")
        with patch.object(forward, "_LoopbackConnection", side_effect=AssertionError("network forbidden")):
            self.rejected(lambda: forward.forward_request(forged, enabled=True), "RELAY_REQUEST_REJECTED")

    def test_connect_exception_is_fixed_code_and_closes_connection(self):
        connection = FakeConnection(FakeResponse(), failure=OSError("DO_NOT_PRINT password"))
        self.rejected(lambda: forward.forward_request(self.ping(), enabled=True, connection_factory=lambda *a, **k: connection, clock=lambda: 0), "FORWARD_UPSTREAM_REJECTED")
        self.assertTrue(connection.closed)

    def test_partial_declared_body_and_oversized_response_are_denied(self):
        for declared, body in (("3", b"{}"), ("1", b"{}"), (str(relay.MAX_RESPONSE_BODY_BYTES + 1), b""), ("-1", b""), ("00", b"")):
            self.rejected(lambda: self.run_forward(FakeResponse(headers=[("Content-Type", "application/json"), ("Content-Length", declared)], body=body)))
        self.rejected(lambda: self.run_forward(FakeResponse(headers=[("Content-Type", "application/json")], body=b"x" * (relay.MAX_RESPONSE_BODY_BYTES + 1))))

    def test_header_count_byte_duplicate_and_control_bounds_apply_upstream(self):
        for headers in ([ ("Set-Cookie", f"user_id=a{i}; Path=/") for i in range(33)], [("Date", "a"), ("date", "b")], [("Content-Type", "application/json"), ("Server", "x\r\nInjected:y")], [("Content-Type", "application/json"), ("Set-Cookie", "sid=a; Path=/; HttpOnly; Domain=localhost")]):
            self.rejected(lambda: self.run_forward(FakeResponse(headers=headers)))

    def test_connect_read_and_total_deadlines_shrink_to_remaining(self):
        result, connection, calls = self.run_forward(deadline=0.75)
        self.assertEqual(calls[0][1]["timeout"], 0.75)
        self.assertTrue(all(timeout == 0.75 for timeout in connection.sock.timeouts))
        now = [0.0]
        connection = FakeConnection(FakeResponse(), response_hook=lambda: now.__setitem__(0, 10.0))
        self.rejected(lambda: forward.forward_request(self.ping(), enabled=True, connection_factory=lambda *a, **k: connection, clock=lambda: now[0]), "FORWARD_DEADLINE_REJECTED")
        self.assertTrue(connection.closed)

    def test_deadline_expires_during_body_read_and_closes_response(self):
        now = [0.0]
        response = FakeResponse(read_hook=lambda: now.__setitem__(0, 10.0))
        self.rejected(lambda: self.run_forward(response, clock=lambda: now[0]), "FORWARD_DEADLINE_REJECTED")
        self.assertTrue(response.closed)

    def test_invalid_deadlines_rejected_before_factory(self):
        for deadline in (0, -1, True, float("inf"), float("nan"), "10"):
            self.rejected(lambda: self.run_forward(deadline=deadline), "FORWARD_DEADLINE_REJECTED")

    def test_clock_exception_is_fixed_code_without_private_message(self):
        def clock():
            raise RuntimeError("DO_NOT_PRINT private clock failure")
        self.rejected(lambda: self.run_forward(clock=clock), "FORWARD_DEADLINE_REJECTED")

    def test_body_timeout_is_fixed_code_and_closes_connection(self):
        def fail_read():
            raise TimeoutError("DO_NOT_PRINT timeout details")
        response = FakeResponse(read_hook=fail_read)
        self.rejected(lambda: self.run_forward(response), "FORWARD_UPSTREAM_REJECTED")
        self.assertTrue(response.closed)

    def test_loopback_connect_uses_numeric_ipv4_without_dns(self):
        sock = FakeSocket()
        with patch.object(socket, "socket", return_value=sock) as factory, patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")):
            connection = forward._LoopbackConnection("127.0.0.1", 8080, timeout=2)
            connection.connect()
        factory.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        self.assertEqual(sock.connected, ("127.0.0.1", 8080))
        for host, port in (("host.docker.internal", 8080), ("127.0.0.1", 5178), ("::1", 8080)):
            with patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
                self.rejected(lambda: forward._LoopbackConnection(host, port, timeout=2).connect())

    def test_http_response_raw_headers_bounded_before_parser_allocates(self):
        for raw in (b"HTTP/1.1 200 OK\r\n" + b"X-A: a\r\n" * 33 + b"\r\n", b"HTTP/1.1 200 OK\r\nX-A: " + b"x" * relay.MAX_HEADER_BYTES + b"\r\n\r\n", b"HTTP/1.1 100 Continue\r\n\r\nHTTP/1.1 200 OK\r\n\r\n", b"HTTP/1.1 200 OK\r\nX-A: partial", b"HTTP/1.1 200 OK\n\n", b"HTTP/99.99 200 OK\r\n\r\n"):
            response = forward._BoundedResponse(FakeSocket(raw), deadline=10, clock=lambda: 0)
            self.rejected(response.begin)
            response.close()

    def test_bounded_response_parses_valid_header_and_body_with_total_deadline(self):
        sock = FakeSocket(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}")
        response = forward._BoundedResponse(sock, deadline=1.5, clock=lambda: 0)
        response.begin()
        self.assertEqual(response.read(), b"{}")
        self.assertTrue(all(value == 1.5 for value in sock.timeouts))
        response.verify_eof()
        response.close()

    def test_raw_malformed_header_cannot_hide_subsequent_unknown_field(self):
        for raw_headers in (b"Bad-Line\r\nX-Evil: hidden\r\n", b" X-Folded: hidden\r\n", b"Bad Name: x\r\n", b"Name:\tvalue\r\n", b"Name: x\x00y\r\n"):
            raw = b"HTTP/1.1 200 OK\r\n" + raw_headers + b"Content-Length: 2\r\n\r\n{}"
            response = forward._BoundedResponse(FakeSocket(raw), deadline=10, clock=lambda: 0)
            self.rejected(response.begin, "FORWARD_UPSTREAM_REJECTED")
            response.close()

    def test_real_http_parser_rejects_bytes_after_declared_content_length(self):
        for tail in (b"X", b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}"):
            raw = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}" + tail
            response = forward._BoundedResponse(FakeSocket(raw), deadline=10, clock=lambda: 0)
            response.begin()
            self.assertEqual(response.read(64 * 1024), b"{}")
            self.rejected(response.verify_eof, "FORWARD_UPSTREAM_REJECTED")
            response.close()

    def test_forward_with_real_http_response_parser_checks_eof_and_closed_sock(self):
        for tail in (b"", b"X"):
            raw = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}" + tail
            socket_fixture = FakeSocket(raw)
            response = forward._BoundedResponse(socket_fixture, deadline=10, clock=lambda: 0)
            response.begin()
            connection = FakeConnection(response)
            connection.sock = socket_fixture
            # The real HTTPConnection clears sock for Connection: close while
            # the response owns its file reference. Retain the original socket.
            def response_hook():
                connection.sock = None
            connection.response_hook = response_hook
            if tail:
                self.rejected(lambda: forward.forward_request(self.ping(), enabled=True, connection_factory=lambda *a, **k: connection, clock=lambda: 0), "FORWARD_UPSTREAM_REJECTED")
            else:
                result = forward.forward_request(self.ping(), enabled=True, connection_factory=lambda *a, **k: connection, clock=lambda: 0)
                self.assertEqual(result.body, b"{}")
            self.assertTrue(connection.closed)

    def test_raw_deadline_prevents_slow_drip_header_read(self):
        now = [0.0]
        class DripSource(io.BytesIO):
            def readinto(self, buffer):
                now[0] += 0.6
                return super().readinto(memoryview(buffer)[:1])
        raw = forward._DeadlineRaw(DripSource(b"HTTP/1.1 200 OK\r\n\r\n"), FakeSocket(), 1.0, lambda: now[0])
        reader = io.BufferedReader(raw)
        self.rejected(reader.readline, "FORWARD_DEADLINE_REJECTED")
        reader.close()

    def test_main_requires_exact_flag_and_never_reads_when_disabled(self):
        for args in ([], ["--enable"], ["--owned-runtime-enabled", "--url", "http://original"], ("--owned-runtime-enabled",)):
            self.assertEqual(forward.main(args, stdin=NoIO(), stdout=NoIO()), 2)

    def test_main_complete_frame_outputs_one_response_only(self):
        output = io.BytesIO()
        calls = []
        def operation(request, **kwargs):
            calls.append((request, kwargs))
            return relay.validate_response(200, [("Content-Type", "application/json")], b"{}")
        self.assertEqual(forward.main(["--owned-runtime-enabled"], stdin=io.BytesIO(wire.encode_request(self.ping())), stdout=output, forwarder=operation), 0)
        self.assertEqual(calls, [(self.ping(), {"enabled": True})])
        self.assertEqual(wire.decode_response(output.getvalue()).body, b"{}")

    def test_main_invalid_frame_or_error_outputs_no_secrets_or_partial_response(self):
        for frame in (wire.encode_request(self.ping()) + b"extra", b"invalid"):
            output = io.BytesIO()
            self.assertEqual(forward.main(["--owned-runtime-enabled"], stdin=io.BytesIO(frame), stdout=output, forwarder=lambda *a, **k: self.fail("called for bad frame")), 3)
            self.assertEqual(output.getvalue(), b"")
        output = io.BytesIO()
        def fail(*args, **kwargs):
            raise RuntimeError("DO_NOT_PRINT original password")
        self.assertEqual(forward.main(["--owned-runtime-enabled"], stdin=io.BytesIO(wire.encode_request(self.login())), stdout=output, forwarder=fail), 3)
        self.assertEqual(output.getvalue(), b"")


if __name__ == "__main__":
    unittest.main()
