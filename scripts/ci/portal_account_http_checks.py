"""Live standard-login/session checks; secrets stay in process memory."""
from __future__ import annotations

import argparse
import json
import secrets
import subprocess

from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor


class Client:
    def __init__(self):
        self.headers = {}
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, url, *, data=None, json=None, headers=None, timeout=20):
        values = dict(self.headers)
        values.update(headers or {})
        body = None
        if json is not None:
            values["Content-Type"] = "application/json"
            body = __import__("json").dumps(json).encode()
        elif data is not None:
            body = urlencode(data).encode()
        request = Request(url, data=body, headers=values)
        try:
            response = self.opener.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        text = response.read().decode()
        from types import SimpleNamespace
        return SimpleNamespace(status_code=response.code, text=text, json=lambda: __import__("json").loads(text))

    get = request
    post = request

parser = argparse.ArgumentParser()
parser.add_argument("--container", required=True)
parser.add_argument("--site", required=True)
parser.add_argument("--origin", required=True)
parser.add_argument("--transport", required=True)
args = parser.parse_args()


def execute(function: str, kwargs=None):
    command = ["docker", "exec", "-w", "/home/frappe/frappe-bench", args.container, "bench", "--site", args.site, "execute", "hbos_portal.auth.http_integration." + function]
    if kwargs:
        command += ["--kwargs", json.dumps(kwargs)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Synthetic fixture operation failed: " + function)


execute("prepare")
checks = []
try:
    raw = subprocess.check_output(["docker", "exec", args.container, "cat", "sites/" + args.site + "/private/hbos-http-synthetic.json"])
    fixture = json.loads(raw)
    host = args.origin.split("//", 1)[1]
    sessions = []

    def login(password):
        client = Client()
        client.headers.update({"Host": host, "Origin": args.origin, "X-Requested-With": "XMLHttpRequest"})
        response = client.post(args.transport + "/api/method/login", data={"usr": fixture["user"], "pwd": password}, timeout=20)
        if response.status_code != 200:
            raise AssertionError("Standard password login failed")
        security = client.get(args.transport + "/api/method/hbos_portal.auth.accounts.get_request_security", timeout=20).json()["message"]
        client.headers["X-Frappe-CSRF-Token"] = security["csrf_token"]
        sessions.append(client)
        return client

    def call(client, method, payload=None):
        return client.post(args.transport + "/api/method/" + method, json=payload or {}, timeout=20)

    def require_success(response, label):
        if response.status_code != 200:
            try:
                kind = response.json().get("exc_type", "unknown")
            except (ValueError, AttributeError):
                kind = "non_json_response"
            # Never emit response bodies, passwords, cookies or reset keys.
            raise AssertionError(f"{label}: HTTP {response.status_code}, {kind}")

    first = login(fixture["password"])
    other = login(fixture["password"])
    prefix = "hbos_portal.auth.accounts."
    assert first.get(args.transport + "/api/method/" + prefix + "get_security").json()["message"]["user"] == fixture["user"]
    checks.append("standard_password_login_resolves_same_user")
    for path in ("/hbos/profile", "/hbos/knowledge", "/hbos/twin"):
        response = first.get(args.transport + path, timeout=20)
        assert response.status_code == 200 and "/assets/hbos_portal/portal/assets/" in response.text
    checks.append("compiled_same_site_assets_and_deep_routes")
    assert call(first, prefix + "set_password", {"new_password": secrets.token_urlsafe(40)}).status_code != 200
    checks.append("session_alone_cannot_set_password")
    assert call(first, "frappe.core.doctype.user.user.update_password", {"new_password": secrets.token_urlsafe(40)}).status_code != 200
    checks.append("legacy_password_api_cannot_bypass_stepup")
    alien = dict(first.headers)
    first.headers["Origin"] = "https://untrusted.example.test"
    assert call(first, prefix + "reauthenticate", {"password": fixture["password"]}).status_code != 200
    first.headers.update(alien)
    checks.append("foreign_origin_rejected")
    require_success(call(first, prefix + "reauthenticate", {"password": fixture["password"]}), "Native reauthentication")
    new_password = secrets.token_urlsafe(40)
    require_success(call(first, prefix + "set_password", {"new_password": new_password}), "Same User password rotation")
    assert other.get(args.transport + "/api/method/" + prefix + "get_security").status_code != 200
    checks.append("password_rotation_invalidates_other_real_session")
    login(new_password)
    execute("change_enabled", {"enabled": 0})
    for client in sessions:
        assert client.get(args.transport + "/api/method/" + prefix + "get_security").status_code != 200
    denied = Client().post(args.transport + "/api/method/login", headers={"Host": host, "Origin": args.origin}, data={"usr": fixture["user"], "pwd": new_password}, timeout=20)
    assert denied.status_code != 200
    checks.append("disabled_user_rejects_password_and_all_real_sessions")
    print(json.dumps({"status": "PASS", "checks": checks, "scope": "synthetic_test_site_only", "owner_login": "NOT_TESTED"}))
finally:
    execute("cleanup")
