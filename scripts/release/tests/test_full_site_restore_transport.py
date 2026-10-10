from __future__ import annotations

import importlib
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from full_site_restore.common import HOST, ORIGIN, RestoreError
from full_site_restore import relay, wire, transport
from full_site_restore.lifecycle import LifecycleRegistry

_REAL_POPEN = subprocess.Popen


class RestoreHostTransportTest(unittest.TestCase):
    def request(self):
        return relay.validate_request("GET", "/api/method/frappe.ping", [("Host", HOST)], b"")

    def exchange(self, script, *, seconds=2):
        children = []
        def spawn(argv, **kwargs):
            self.assertEqual(argv, relay.build_exec_argv("a" * 64, ("b" * 64,)) + ("--owned-runtime-enabled",))
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["env"], {})
            child = _REAL_POPEN([sys.executable, "-B", "-c", script], **kwargs)
            children.append(child)
            return child
        try:
            with patch.object(transport.subprocess, "Popen", side_effect=spawn):
                return transport._exchange_child("a" * 64, ("b" * 64,), wire.encode_request(self.request()),
                    remaining_seconds=seconds, enabled=True)
        finally:
            for child in children:
                self.assertIsNotNone(child.poll(), "synthetic host child must be reaped")

    def test_http_get_and_post_exact_framing(self):
        frame = ("GET /api/method/frappe.ping HTTP/1.1\r\nHost: " + HOST + "\r\n\r\n").encode()
        self.assertEqual(transport.decode_http_request(frame).route_id, "native_ping")
        body = b"usr=synthetic&pwd=SYNTHETIC"
        frame = ("POST /api/method/login HTTP/1.1\r\nHost: " + HOST + "\r\nOrigin: " + ORIGIN
            + "\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: " + str(len(body))
            + "\r\n\r\n").encode() + body
        self.assertEqual(transport.decode_http_request(frame).body, body)

    def test_http_smuggling_bad_grammar_and_second_request_rejected(self):
        good = ("GET /login HTTP/1.1\r\nHost: " + HOST + "\r\n").encode()
        for tail in (b"\r\nGET /login HTTP/1.1\r\n\r\n", b"Content-Length: 1\r\n\r\n",
            b"Bad-Line\r\n\r\n", b" Accept: x\r\n\r\n", b"Accept: a\nX: b\r\n\r\n",
            b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n", b"Connection: keep-alive\r\n\r\n",
            b"Host: duplicate\r\n\r\n", b"Accept:\tvalue\r\n\r\n"):
            with self.subTest(tail_kind=tail[:10]):
                with self.assertRaises(RestoreError):
                    transport.decode_http_request(good + tail)

    def test_http_post_without_length_and_bad_versions_rejected(self):
        for frame in (("POST /api/method/login HTTP/1.1\r\nHost: " + HOST + "\r\n\r\nusr=a&pwd=b").encode(),
            ("GET /login HTTP/1.0\r\nHost: " + HOST + "\r\n\r\n").encode(),
            ("GET  /login HTTP/1.1\r\nHost: " + HOST + "\r\n\r\n").encode(), b"GET /login HTTP/1.1\n\n"):
            with self.assertRaises(RestoreError):
                transport.decode_http_request(frame)

    def test_http_limits_and_types_rejected(self):
        for frame in (bytearray(), b"x" * (transport.MAX_HTTP_REQUEST_BYTES + 1),
            b"GET /login HTTP/1.1\r\n" + b"Accept: x\r\n" * 33 + b"\r\n"):
            with self.assertRaises(RestoreError):
                transport.decode_http_request(frame)

    def test_http_response_multiple_cookies_close_and_redaction(self):
        response = relay.validate_response(200, [("Content-Type", "application/json"),
            ("Set-Cookie", "sid=SYNTHETIC; Path=/; HttpOnly"), ("Set-Cookie", "user_image=; Path=/")], b"{}")
        frame = transport.encode_http_response(response)
        self.assertEqual(frame.count(b"set-cookie:"), 2)
        self.assertEqual(frame.count(b"connection: close"), 1)
        self.assertTrue(frame.endswith(b"\r\n\r\n{}"))
        error = relay.validate_response(500, [("Content-Type", "text/plain")], b"SYNTHETIC-SECRET")
        self.assertNotIn(b"SYNTHETIC-SECRET", transport.encode_http_response(error))

    def test_http_response_forgery_is_revalidated(self):
        for headers in (None, [], (("Location", "https://evil.invalid"),), (("Content-Type",),)):
            with self.assertRaises(RestoreError):
                transport.encode_http_response(relay.AllowedResponse(200, headers, b""))

    def test_default_facade_no_popen_or_listener(self):
        with patch.object(transport.subprocess, "Popen", side_effect=AssertionError("no process")):
            facade = transport.OwnedRelayTransport(LifecycleRegistry())
            for callback in (facade.admit_listener,
                lambda: facade.exchange(self.request(), fresh_backend_metadata={})):
                with self.assertRaisesRegex(RestoreError, "LIFECYCLE_SERVICE_NOT_READY"):
                    callback()

    def test_facade_rejects_fake_registry_or_subclass(self):
        class Child(LifecycleRegistry):
            pass
        for registry in (None, object(), Child()):
            with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_REGISTRY_REQUIRED"):
                transport.OwnedRelayTransport(registry)

    def test_disabled_child_and_invalid_time_never_spawn(self):
        with patch.object(transport.subprocess, "Popen", side_effect=AssertionError("no process")):
            with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_DISABLED"):
                transport._exchange_child("a" * 64, ("b" * 64,), b"", remaining_seconds=2)
            for seconds in (0, -1, float("inf"), float("nan"), True, "2", 10**999):
                with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_DEADLINE_EXPIRED"):
                    transport._exchange_child("a" * 64, ("b" * 64,), b"", remaining_seconds=seconds, enabled=True)

    def test_bad_frame_and_original_id_rejected_before_spawn(self):
        with patch.object(transport.subprocess, "Popen", side_effect=AssertionError("no process")):
            for identity, frame in (("a" * 64, b"bad"), ("b" * 64, wire.encode_request(self.request()))):
                with self.assertRaises(RestoreError):
                    transport._exchange_child(identity, ("b" * 64,), frame, remaining_seconds=2, enabled=True)

    def test_synthetic_real_pipe_roundtrip_and_close_stdin(self):
        response = wire.encode_response(relay.validate_response(200, [("Content-Type", "application/json")], b'{"message":"pong"}'))
        script = "import sys; data=sys.stdin.buffer.read(); assert data.startswith(b'HBOSRF1'); sys.stdout.buffer.write(" + repr(response) + ")"
        self.assertEqual(self.exchange(script).body, b'{"message":"pong"}')

    def test_synthetic_slow_child_deadline_reaped(self):
        with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_DEADLINE_EXPIRED"):
            self.exchange("import time; time.sleep(30)", seconds=0.05)

    def test_response_validation_crossing_deadline_is_withheld(self):
        response = wire.encode_response(relay.validate_response(204, [], b""))
        original = wire.decode_response
        clock = [0.0]
        def decode(frame):
            result = original(frame)
            clock[0] = 11.0
            return result
        with patch.object(transport.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(wire, "decode_response", side_effect=decode):
            with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_DEADLINE_EXPIRED"):
                self.exchange("import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(" + repr(response) + ")", seconds=10)

    def test_synthetic_stderr_quota_reaped_and_not_exposed(self):
        with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_STDERR_LIMIT") as error:
            self.exchange("import sys; sys.stderr.buffer.write(b'SYNTHETIC-SECRET'*1024); sys.stderr.flush()")
        self.assertNotIn("SYNTHETIC", str(error.exception))

    def test_synthetic_stdout_quota_reaped(self):
        with patch.object(wire, "MAX_RESPONSE_FRAME_BYTES", 512):
            with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_OUTPUT_LIMIT"):
                self.exchange("import sys; sys.stdout.buffer.write(b'x'*1024); sys.stdout.flush()")

    def test_synthetic_failure_and_extra_frame_rejected(self):
        with self.assertRaisesRegex(RestoreError, "HOST_TRANSPORT_CHILD_FAILED"):
            self.exchange("import sys; sys.stdin.buffer.read(); sys.stderr.write('SYNTHETIC-SECRET'); sys.exit(1)")
        response = wire.encode_response(relay.validate_response(204, [], b""))
        with self.assertRaisesRegex(RestoreError, "WIRE_FRAME_REJECTED"):
            self.exchange("import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(" + repr(response + b"extra") + ")")

    def test_reload_is_inert(self):
        with patch.object(transport.subprocess, "Popen", side_effect=AssertionError("no process")), \
             patch("socket.socket", side_effect=AssertionError("no socket")):
            importlib.reload(transport)


if __name__ == "__main__":
    unittest.main()
