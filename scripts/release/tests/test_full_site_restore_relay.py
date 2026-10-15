from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from full_site_restore.common import BENCH, DOCKER, HOST, ORIGIN, RestoreError
from full_site_restore import relay


class RestoreRelayPolicyTest(unittest.TestCase):
    def request(self, method="GET", target="/api/method/frappe.ping", *, extra=(), body=b"", static=frozenset()):
        return relay.validate_request(method, target, [("Host", HOST), *extra], body, approved_static_paths=static)

    def login(self, body=b"usr=synthetic-user&pwd=SYNTHETIC-PASSWORD", *, extra=()):
        return self.request("POST", "/api/method/login", extra=(("Origin", ORIGIN), ("Content-Type", "application/x-www-form-urlencoded"), *extra), body=body)

    def reject_request(self, callback):
        with self.assertRaises(RestoreError) as error:
            callback()
        self.assertEqual(str(error.exception), "RELAY_REQUEST_REJECTED")

    def reject_response(self, status=200, headers=None, body=b"{}"):
        with self.assertRaises(RestoreError) as error:
            relay.validate_response(status, headers if headers is not None else [("Content-Type", "application/json")], body)
        self.assertEqual(str(error.exception), "RELAY_RESPONSE_REJECTED")

    def test_fixed_get_routes_are_zero_argument_and_immutable(self):
        for target in ("/api/method/frappe.ping", "/api/method/frappe.auth.get_logged_user", "/login", "/desk"):
            request = self.request(target=target)
            self.assertEqual(request.target, target)
            self.assertEqual(dict(request.headers)["content-length"], "0")
            self.assertEqual(dict(request.headers)["accept-encoding"], "identity")
            with self.assertRaises(FrozenInstanceError):
                request.method = "POST"

    def test_arbitrary_rpc_version_aliases_and_desk_data_are_denied(self):
        for target in ("/api/method/frappe.client.get_count", "/api/method/frappe.client.get_count?doctype=User", "/api/method/frappe.client.get_list", "/api/v1/method/frappe.ping", "/api/v2/method/frappe.ping", "/api/resource/User", "/desk/User", "/app", "/api/method/logout", "/api/method/login"):
            with self.subTest(target=target):
                self.reject_request(lambda: self.request(target=target))

    def test_targets_reject_encoding_and_authority_ambiguities(self):
        for target in ("/api/method/frappe.ping?", "/api/method/frappe.ping?cmd=frappe.client.get_list", "/api/method/frappe%2Eping", "/%252fapi/method/frappe.ping", "/api//method/frappe.ping", "/api/../method/frappe.ping", "/api/./method/frappe.ping", "http://127.0.0.1:8080/api/method/frappe.ping", "//169.254.169.254/latest/meta-data", "/api\\method/frappe.ping", "/api/method/frappe.ping#x", "/api/method/frappe.ping\x00", "/api/method/frappe.ping\r\nHost:x", "/Ａpi/method/frappe.ping", "/" + "x" * relay.MAX_TARGET_BYTES):
            with self.subTest(target=target):
                self.reject_request(lambda: self.request(target=target))

    def test_only_fixed_methods_and_empty_get_body(self):
        for method in ("get", "CONNECT", "HEAD", "OPTIONS", "PUT", "PATCH", "DELETE", True, None):
            self.reject_request(lambda: self.request(method=method))
        self.reject_request(lambda: self.request(body=b"cmd=frappe.client.get_list"))
        self.reject_request(lambda: self.request(body=bytearray()))
        self.reject_request(lambda: self.request(extra=(("Content-Type", "application/json"),)))

    def test_static_paths_require_exact_immutable_manifest_and_safe_extensions(self):
        target = "/assets/frappe/dist/css/desk.bundle.css"
        self.reject_request(lambda: self.request(target=target))
        request = self.request(target=target, static=frozenset({target}))
        self.assertEqual(request.route_id, "approved_static_asset")
        for manifest in ({target}, [target], (target,), frozenset({"/assets/../private/x.css"}), frozenset({"/assets/x%252F.css"}), frozenset({"/assets/private.html"}), frozenset({"/private/x.js"}), frozenset({"/assets/source.map"})):
            self.reject_request(lambda: self.request(target=target, static=manifest))
        self.reject_request(lambda: self.request(target=target + "?v=1", static=frozenset({target})))

    def test_host_origin_site_forwarding_and_proxy_injection_are_denied(self):
        for headers in ([], [("Host", "127.0.0.1:5178")], [("Host", HOST), ("host", HOST)], [("Host", HOST), ("Origin", "http://evil.invalid")], [("Host", HOST), ("X-Frappe-Site-Name", "frontend")], [("Host", HOST), ("X-Forwarded-Host", "127.0.0.1:8080")], [("Host", HOST), ("Forwarded", "host=evil.invalid")], [("Host", HOST), ("Authorization", "Basic synthetic")], [("Host", HOST), ("Sec-Fetch-Site", "cross-site")], [("Host", HOST), ("Referer", "http://127.0.0.1:5178/login")]):
            self.reject_request(lambda: relay.validate_request("GET", "/login", headers, b""))

    def test_smuggling_override_upgrade_duplicate_and_crlf_headers_are_denied(self):
        for extra in ((("Transfer-Encoding", "chunked"),), (("Connection", "upgrade"),), (("Upgrade", "websocket"),), (("X-HTTP-Method-Override", "GET"),), (("Content-Length", "0"), ("content-length", "0")), (("Content-Length", "00"),), (("Content-Length", "1"),), (("Content-Length", "+0"),), (("Content-Length", "０"),), (("Accept", "a\r\nX-Frappe-Site-Name:frontend"),), (("Host ", HOST),)):
            self.reject_request(lambda: self.request(extra=extra))

    def test_same_site_cross_origin_fetch_is_rejected(self):
        # Different localhost names may share a site but never this exact origin.
        for method, target, body, extra in (
            ("GET", "/login", b"", ()),
            ("POST", "/api/method/login", b"usr=synthetic&pwd=synthetic", (("Origin", ORIGIN), ("Content-Type", "application/x-www-form-urlencoded"))),
        ):
            self.reject_request(lambda: self.request(method, target, extra=extra + (("Sec-Fetch-Site", "same-site"),), body=body))
        for fetch_site in ("none", "same-origin"):
            self.assertEqual(self.request(target="/login", extra=(("Sec-Fetch-Site", fetch_site),)).route_id, "native_login_outline")

    def test_login_requires_exact_origin_content_type_and_form_keys(self):
        self.assertEqual(self.login().route_id, "native_password_login")
        self.reject_request(lambda: self.request("POST", "/api/method/login", extra=(("Content-Type", "application/x-www-form-urlencoded"),), body=b"usr=a&pwd=b"))
        for content_type in ("application/json", "text/plain", "multipart/form-data", "application/x-www-form-urlencoded; charset=latin1"):
            self.reject_request(lambda: self.request("POST", "/api/method/login", extra=(("Origin", ORIGIN), ("Content-Type", content_type)), body=b"usr=a&pwd=b"))
        for body in (b"usr=a&pwd=b&cmd=frappe.client.get_list", b"usr=a&usr=b", b"pwd=a&pwd=b", b"usr=a&pwd=b&pwd=c", b"u%73r=a&pwd=b", b"usr=a&pwd=", b"usr=&pwd=b", b"usr=a;pwd=b", b'{"usr":"a","pwd":"b"}', b"usr=a&pwd=%", b"usr=a&pwd=%GG", b"usr=a&pwd=%FF", b"usr=a&pwd=%0D%0A", b"usr=a&pwd=%00", b"usr=a&pwd=\xff", b"usr=a&pwd=" + b"x" * 1025):
            with self.subTest(body_size=len(body)):
                self.reject_request(lambda: self.login(body))

    def test_login_keeps_literal_password_and_hides_credentials_in_repr(self):
        body = b"usr=synthetic%40example.invalid&pwd=SYNTH%252F%26password"
        request = self.login(body, extra=(("Cookie", "sid=SYNTHETIC-CLONE-SID; full_name=Synthetic; user_id=synthetic"),))
        self.assertEqual(request.body, body)
        self.assertEqual(dict(request.headers)["cookie"], "sid=SYNTHETIC-CLONE-SID")
        self.assertNotIn("SYNTHETIC-CLONE-SID", repr(request))
        self.assertNotIn("SYNTH%252F", repr(request))
        self.assertNotIn("synthetic%40", repr(request))

    def test_cookie_names_duplicates_and_values_are_bounded(self):
        for cookie in ("sid=a; sid=b", "session=a", "cmd=a", "sid=a,b", 'sid="a"', "sid=a\\b", "sid=a b", "sid=", "sid=" + "x" * 1025, "user_id=u; unknown=x"):
            self.reject_request(lambda: self.request(extra=(("Cookie", cookie),)))
        request = self.request(extra=(("Cookie", "full_name=Synthetic; system_user=yes"),))
        self.assertNotIn("cookie", dict(request.headers))

    def test_native_language_and_empty_image_are_presentation_only(self):
        request = self.request(extra=(("Cookie", "sid=SYNTHETIC; user_lang=zh; user_image="),))
        self.assertEqual(dict(request.headers)["cookie"], "sid=SYNTHETIC")
        response = relay.validate_response(200, [("Set-Cookie", "user_image=; Path=/"),
            ("Set-Cookie", "user_lang=zh; Path=/")], b"")
        self.assertEqual(len([value for key, value in response.headers if key == "set-cookie"]), 2)
        for name in ("sid", "user_id", "full_name", "user_lang", "system_user"):
            self.reject_request(lambda: self.request(extra=(("Cookie", name + "="),)))
            self.reject_response(headers=[("Content-Type", "application/json"),
                ("Set-Cookie", name + "=; Path=/; HttpOnly")])

    def test_native_json_redirects_use_exact_clone_locations(self):
        for location in ("/desk", "/login", ORIGIN + "/desk"):
            body = ('{"home_page":"' + location + '","nested":{"redirect_to":"/login"}}').encode()
            self.assertEqual(relay.validate_response(200, [("Content-Type", "application/json")], body).body, body)
        for body in (b'{"home_page":"https://evil.invalid"}', b'{"redirect_to":"/update-password"}',
            b'{"nested":[{"redirect_to":"//evil.invalid"}]}', b'{"home_page":null}',
            b'{"home_page":"/desk","home_page":"/login"}', b'{"value":NaN}', b'{'):
            self.reject_response(body=body)

    def test_json_structure_is_finite_and_errors_stay_redacted(self):
        self.reject_response(body=b'[' * 34 + b'0' + b']' * 34)
        self.reject_response(body=b'[' + b'0,' * 16384 + b'0]')
        response = relay.validate_response(500, [("Content-Type", "application/json")], b'{BAD-SYNTHETIC-SECRET')
        self.assertNotIn(b"SYNTHETIC", response.body)

    def test_request_body_header_count_and_byte_limits(self):
        self.reject_request(lambda: self.login(b"x" * (relay.MAX_REQUEST_BODY_BYTES + 1)))
        self.reject_request(lambda: self.request(extra=tuple(("Accept", "x") for _ in range(relay.MAX_HEADERS))))
        self.reject_request(lambda: self.request(extra=(("User-Agent", "x" * (relay.MAX_HEADER_VALUE_BYTES + 1)),)))
        self.reject_request(lambda: self.request(extra=tuple((name, "x" * relay.MAX_HEADER_VALUE_BYTES) for name in ("Accept", "Accept-Language", "User-Agent", "Referer"))))
        self.reject_request(lambda: relay.validate_request("GET", "/login", (("Host", HOST),), b""))
        self.reject_request(lambda: relay.validate_request("GET", "/login", [["Host", HOST]], b""))
        self.reject_request(lambda: relay.validate_request("GET", "/login", [("Host", 1)], b""))
        self.reject_request(lambda: self.request(extra=(("User-Agent", "非ASCII"),)))

    def test_response_is_immutable_private_no_store_and_static_csp(self):
        body = b'{"message":"SYNTHETIC-PRIVATE-IDENTITY"}'
        response = relay.validate_response(200, [("Content-Type", "application/json"), ("Cache-Control", "public, max-age=3600"), ("Content-Security-Policy", "default-src *")], body)
        headers = dict(response.headers)
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["content-security-policy"], relay.HTML_CSP)
        self.assertEqual(headers["content-length"], str(len(body)))
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertNotIn("SYNTHETIC-PRIVATE-IDENTITY", repr(response))
        with self.assertRaises(FrozenInstanceError):
            response.status = 302
        self.assertIn("default-src 'none'", relay.HTML_CSP)
        self.assertIn("form-action 'self'", relay.HTML_CSP)
        self.assertNotIn("unsafe-inline", relay.HTML_CSP)

    def test_multiple_native_set_cookies_remain_separate_and_secrets_hidden(self):
        response = relay.validate_response(200, [("Content-Type", "application/json"), ("Set-Cookie", "sid=SYNTHETIC-NEW-SID; Path=/; HttpOnly"), ("Set-Cookie", "full_name=Synthetic; Path=/; SameSite=Lax"), ("Set-Cookie", "user_id=synthetic; Path=/; SameSite=Strict")], b"{}")
        cookies = [value for key, value in response.headers if key == "set-cookie"]
        self.assertEqual(len(cookies), 3)
        self.assertTrue(cookies[0].endswith("SameSite=Lax"))
        self.assertNotIn("SYNTHETIC-NEW-SID", repr(response))
        deletion = relay.validate_response(200, [("Set-Cookie", "sid=; Path=/; HttpOnly; Max-Age=0")], b"")
        self.assertEqual(len([v for k, v in deletion.headers if k == "set-cookie"]), 1)

    def test_cookie_domain_path_and_attribute_ambiguities_are_denied(self):
        for cookie in ("sid=a; Path=/; HttpOnly; Domain=localhost", "sid=a; Path=/; HttpOnly; Domain=hbos-restore.localhost", "sid=a; Path=/; HttpOnly; Domain=.localhost", "sid=a; Path=/desk; HttpOnly", "sid=a; HttpOnly", "sid=a; Path=/", "sid=a; Path=/; path=/; HttpOnly", "sid=a; Path=/; HttpOnly; SameSite=None", "sid=a; Path=/; HttpOnly; Unknown=x", "sid=a; Path=/; HttpOnly=true", "sid=a; Path=/; HttpOnly; Max-Age=bad", "sid=a; Path=/; HttpOnly; Expires=bad", "sid=a; Path=/; HttpOnly\r\nLocation:http://evil.invalid", "session=a; Path=/", "sid=a,full_name=b; Path=/; HttpOnly", "sid=; Path=/; HttpOnly"):
            with self.subTest(cookie_kind=cookie.split(";", 1)[0].split("=", 1)[0]):
                self.reject_response(headers=[("Content-Type", "application/json"), ("Set-Cookie", cookie)])
        self.reject_response(headers=[("Content-Type", "application/json"), ("Set-Cookie", "sid=a; Path=/; HttpOnly"), ("set-cookie", "sid=b; Path=/; HttpOnly")])

    def test_redirects_require_fixed_clone_locations_and_reject_external(self):
        for location in ("/login", "/desk", ORIGIN + "/login", ORIGIN + "/desk"):
            response = relay.validate_response(302, [("Location", location)], b"")
            self.assertEqual(dict(response.headers)["location"], location)
        for location in ("http://127.0.0.1:5178/login", "http://host.docker.internal:8080/login", "https://evil.invalid/desk", "//evil.invalid/desk", "/desk?cmd=x", "/%2564esk", "/api/resource/User", ORIGIN + "@evil.invalid/desk", "/desk#external", "/desk\r\nSet-Cookie:sid=a"):
            self.reject_response(302, [("Location", location)], b"")
        self.reject_response(302, [], b"")
        self.reject_response(200, [("Location", "/desk")], b"")

    def test_response_status_body_and_headers_are_strict(self):
        for status in (True, "200", 101, 199, 205, 300, 304, 600):
            self.reject_response(status)
        self.reject_response(204, [], b"x")
        self.reject_response(body=b"x" * (relay.MAX_RESPONSE_BODY_BYTES + 1))
        self.reject_response(body=bytearray(b"{}"))
        for headers in ([("Content-Type", "application/json"), ("Connection", "close")], [("Content-Type", "application/json"), ("Transfer-Encoding", "chunked")], [("Content-Type", "application/json"), ("Upgrade", "websocket")], [("Content-Type", "application/json"), ("Content-Encoding", "gzip")], [("Content-Type", "application/json"), ("Access-Control-Allow-Origin", "*")], [("Content-Type", "application/json"), ("content-type", "text/html")], [("Content-Type", "application/json"), ("Content-Length", "1")], [("Content-Type", "application/x-unknown")], [("Content-Type", "application/json\r\nServer:evil")]):
            self.reject_response(headers=headers)
        self.reject_response(headers=[("Content-Type", "text/html; charset=utf-7")])
        self.reject_response(headers=[("Content-Type", "application/json; charset=utf-8; charset=latin1")])
        self.reject_response(headers=[("Content-Type", "application/json"), *[(name, "x" * relay.MAX_HEADER_VALUE_BYTES) for name in ("Cache-Control", "Pragma", "Content-Security-Policy", "Referrer-Policy")]])

    def test_upstream_error_details_cannot_escape_in_response_body(self):
        response = relay.validate_response(500, [("Content-Type", "text/html; charset=utf-8")], b"<pre>SYNTHETIC-PRIVATE-PASSWORD SQL traceback</pre>")
        self.assertNotIn(b"SYNTHETIC-PRIVATE-PASSWORD", response.body)
        self.assertNotIn(b"traceback", response.body)
        self.assertEqual(dict(response.headers)["content-type"], "application/json")
        self.assertEqual(dict(response.headers)["content-length"], str(len(response.body)))

    def test_argv_is_fixed_non_shell_proposal_and_rejects_original_or_mutable_ids(self):
        new_id, source_id = "a" * 64, "b" * 64
        argv = relay.build_exec_argv(new_id, frozenset({source_id}))
        self.assertEqual(argv, (DOCKER, "exec", "-i", "--user", "1000:1000", new_id, BENCH + "/env/bin/python", "-B", "/run/hbos-restore/forward.py"))
        self.assertIs(type(argv), tuple)
        for target, originals in ((source_id, (source_id,)), (new_id[:12], (source_id,)), (new_id.upper(), (source_id,)), ("a" * 64 + ";sh", (source_id,)), (new_id, [source_id]), (new_id, ()), (new_id, ("short",)), (new_id, (source_id, source_id))):
            with self.assertRaises(RestoreError) as error:
                relay.build_exec_argv(target, originals)
            self.assertEqual(str(error.exception), "RELAY_RESOURCE_REJECTED")

    def test_policy_has_no_real_http_socket_or_subprocess_action(self):
        with patch("socket.socket", side_effect=AssertionError("No socket allowed")), patch("subprocess.run", side_effect=AssertionError("No subprocess allowed")), patch("subprocess.Popen", side_effect=AssertionError("No subprocess allowed")):
            self.request()
            self.login()
            relay.validate_response(200, [("Content-Type", "application/json")], b"{}")
            relay.build_exec_argv("a" * 64, ("b" * 64,))
        self.assertEqual(relay.TRANSPORT_STATE, "NOT_IMPLEMENTED")
        self.assertEqual(relay.MAX_CONCURRENT_REQUESTS, 1)
        self.assertLessEqual(relay.CONNECT_TIMEOUT_SECONDS, relay.TOTAL_TIMEOUT_SECONDS)
        self.assertLessEqual(relay.READ_TIMEOUT_SECONDS, relay.TOTAL_TIMEOUT_SECONDS)


if __name__ == "__main__":
    unittest.main()
