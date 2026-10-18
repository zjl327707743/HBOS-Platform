"""Disposable GitHub Runner: real Frappe -> HTTP FastAPI -> synthetic HTTP upstream.

Copy this file only into the one-time Site as hbos_portal._owner_production_audit.
No whitelist, production hooks, auth stubs, existing Site or real Feishu credentials.
The host bootstrap copies both production service directories to
/tmp/owner-production-services and installs their declared requirements in the
separate /tmp/owner-production-venv before calling run() in the bench virtualenv.
All fixture listeners bind loopback only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from datetime import date
from http.cookiejar import CookieJar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener

import frappe


SERVICE_ROOT = Path(os.environ.get('OWNER_PRODUCTION_SERVICES', '/tmp/owner-production-services'))
SERVICE_PYTHON = os.environ.get('OWNER_PRODUCTION_PYTHON', '/tmp/owner-production-venv/bin/python')
METHODS = ('get_board', 'get_ai_analysis')
ENDPOINTS = ('/production/monthly', '/production/yesterday', '/production/ai-analysis')


def _guard() -> str:
    marker = os.environ.get('HBOS_REPORT_SCOPE_TEST_ID', '')
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert re.fullmatch(r'[0-9]+-[0-9]+', marker)
    assert frappe.local.site == 'report-scope-' + marker + '.localhost'
    assert str(frappe.conf.hbos_report_scope_ci) == marker
    assert os.environ.get('HBOS_FRAPPE_SMOKE') == '1'
    assert os.environ.get('OWNER_AUDIT_DOMAIN') == 'production'
    assert all(os.environ.get(key) == '0' for key in (
        'HBOS_AI_ENABLED', 'HBOS_AI_ALLOW_PII', 'HBOS_FEISHU_SYNC_ENABLED',
        'HBOS_DELICLOUD_SYNC_ENABLED',
    ))
    assert not frappe.conf.get('hbos_production_service_url'), 'Refuse existing service configuration'
    assert not frappe.conf.get('hbos_production_service_token'), 'Refuse existing service credential'
    assert str(SERVICE_ROOT) == '/tmp/owner-production-services'
    assert SERVICE_ROOT.is_dir() and SERVICE_ROOT.resolve() == SERVICE_ROOT
    assert SERVICE_PYTHON == '/tmp/owner-production-venv/bin/python' and Path(SERVICE_PYTHON).is_file()
    for service in ('hbos_production', 'hbos_production_ai'):
        assert (SERVICE_ROOT / service / 'app/main.py').is_file()
        assert not (SERVICE_ROOT / service / '.env').exists(), 'No existing service environment'
    return marker


class Browser:
    """Real Frappe Session and CSRF, with no cookie or response-body logging."""

    def __init__(self, origin: str):
        self.headers = {
            'Host': origin.split('//', 1)[1], 'Origin': origin,
            'X-Requested-With': 'XMLHttpRequest',
        }
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))

    def call(self, method: str, params=None, *, post=False, timeout=75):
        encoded = urlencode(params or {}).encode()
        url = 'http://127.0.0.1:8000/api/method/' + method
        request = Request(
            url if post or not encoded else url + '?' + encoded.decode(),
            data=encoded if post else None, headers=self.headers,
        )
        try:
            response = self.opener.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read().decode('utf-8')
            try:
                body = json.loads(raw)
            except ValueError:
                body = {}
            return response.code, body.get('message', body), raw

    def production(self, method='get_board', *, refresh=False, **kwargs):
        return self.call('hbos_portal.api.production.' + method,
                         {'refresh': 1} if refresh else {}, **kwargs)

    def login(self, user: str, password: str):
        self.headers.pop('X-Frappe-CSRF-Token', None)
        status, _, _ = self.call('login', {'usr': user, 'pwd': password}, post=True)
        assert status == 200, 'Synthetic native login failed'
        status, payload, _ = self.call('hbos_portal.auth.accounts.get_request_security')
        assert status == 200 and payload.get('csrf_token'), 'Native CSRF unavailable'
        self.headers['X-Frappe-CSRF-Token'] = payload['csrf_token']
        return self


class Upstream:
    def __init__(self, contract, marker: str):
        self.contract = contract
        self.marker = 'SYNTHETIC-PRODUCTION-' + marker
        self.app_id = 'cli_synthetic_owner'
        self.secret = secrets.token_urlsafe(32)
        self.tenant_token = secrets.token_urlsafe(32)
        self.mode = 'ok'
        self.version = 1
        self.lock = threading.Lock()
        self.counts = {'auth': 0, 'read': 0, 'write': 0, 'model': 0}

    def count(self, name: str):
        with self.lock:
            self.counts[name] += 1

    def records(self, table: str):
        today = date.today()
        c = self.contract
        fields = []
        if table == next(iter(c.DETAIL_TABLES.values())):
            fields = [dict(产品名称='4BMA', 批号=self.marker + '-' + str(i),
                           收料日期=today.isoformat(), 收率=0.93, 产量=37)
                      for i in range(self.version)]
        elif table == c.PLAN_TABLE:
            fields = [{'产品名称': '4BMA', '1日': 10}]
        elif table == c.TARGET_TABLE:
            fields = [dict(产品名称='4BMA', 目标收率=0.9)]
        elif table == c.AI_TABLE:
            fields = [dict(产品='4BMA', 工序='Synthetic step', 结论摘要=self.marker,
                           评级='数据不足', 分析日期=today.isoformat())]
        else:
            for source in c.ANOMALY_SOURCES:
                if source.table_id == table:
                    fields = [{source.content_field: self.marker,
                               source.date_field: today.isoformat(),
                               source.closure_field: 'Synthetic resolved cause'}]
        return [{'record_id': 'synthetic-' + str(i), 'fields': value}
                for i, value in enumerate(fields)]

    def handler(self):
        state = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, status, payload):
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_POST(self):
                if self.path == '/open-apis/auth/v3/tenant_access_token/internal':
                    state.count('auth')
                    body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                    if body != {'app_id': state.app_id, 'app_secret': state.secret}:
                        return self.send(403, {'code': 403})
                    return self.send(200, {'code': 0, 'tenant_access_token': state.tenant_token,
                                           'expire': 7200})
                state.count('model' if self.path.startswith('/v1/') else 'write')
                self.send(405, {'code': 405})

            def do_PUT(self):
                state.count('write')
                self.send(405, {'code': 405})

            do_PATCH = do_PUT
            do_DELETE = do_PUT

            def do_GET(self):
                path = urlsplit(self.path).path
                match = re.fullmatch('/open-apis/bitable/v1/apps/[^/]+/tables/([^/]+)/records', path)
                if not match:
                    return self.send(404, {'code': 404})
                if self.headers.get('Authorization') != 'Bearer ' + state.tenant_token:
                    return self.send(401, {'code': 401})
                state.count('read')
                if state.mode == 'error':
                    return self.send(502, {'code': 502})
                if state.mode == 'invalid_json':
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'not-json')
                    return
                if state.mode == 'timeout':
                    # Exercise the unchanged real 60s Frappe proxy timeout.
                    time.sleep(65)
                self.send(200, {'code': 0, 'data': {
                    'items': state.records(match.group(1)), 'has_more': False,
                }})

        return Handler


def _http(url, headers=None):
    try:
        response = build_opener(ProxyHandler({})).open(Request(url, headers=headers or {}), timeout=10)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read().decode()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {}
        return response.code, payload, raw


def _load_contract():
    spec = importlib.util.spec_from_file_location(
        'owner_synthetic_production_contract', SERVICE_ROOT / 'hbos_production/app/contract.py',
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_user(email: str, role: str):
    assert not frappe.db.exists('User', email), 'Never reuse an existing fixture user'
    password = secrets.token_urlsafe(32)
    frappe.get_doc(dict(doctype='User', email=email, first_name='Synthetic Production',
                        enabled=1, user_type='System User', send_welcome_email=0,
                        new_password=password, roles=[dict(role=role)])).insert(ignore_permissions=True)
    frappe.db.commit()
    return password


def run():
    marker = _guard()
    frappe.set_user('Administrator')
    from hbos_portal.production.access import PRODUCTION_ROLES
    from hbos_portal.production.provider import get_provider
    assert PRODUCTION_ROLES == (), 'Production roles must remain empty'
    access = get_provider().access_context()
    assert access['can_enter'] is True and access['scopes'] == {}
    checks = []
    def passed(case, **details):
        checks.append(dict(case=case, passed=True, **details))
        print('[PRODUCTION-E2E] ' + json.dumps(checks[-1]), flush=True)

    # Hash the executed service sources; ensure the fixture never edits production code.
    source_files = sorted(SERVICE_ROOT.glob('*/app/*.py'))
    source_hashes = {str(p.relative_to(SERVICE_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in source_files}
    upstream = Upstream(_load_contract(), marker)
    server = ThreadingHTTPServer(('127.0.0.1', 0), upstream.handler())
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    upstream_url = 'http://127.0.0.1:' + str(server.server_port)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        service_port = probe.getsockname()[1]
    service_url = 'http://127.0.0.1:' + str(service_port)
    token = secrets.token_urlsafe(32)
    wrong = secrets.token_urlsafe(32)
    secret_values = [token, wrong, upstream.secret, upstream.tenant_token]
    # The separate services receive only their synthetic credentials, never the
    # disposable Site's DB or Administrator password, nor a host proxy setting.
    env = {key: value for key, value in os.environ.items()
           if key in ('PATH', 'LANG', 'LC_ALL', 'TZ')}
    env.update(HBOS_FEISHU_APP_ID=upstream.app_id, HBOS_FEISHU_APP_SECRET=upstream.secret,
               HBOS_FEISHU_BASE=upstream_url, HBOS_PRODUCTION_CORS_ORIGINS='',
               HBOS_PRODUCTION_SERVICE_TOKEN=token, HBOS_PRODUCTION_CACHE_TTL='3600',
               HBOS_AI_ENABLED='0', HBOS_AI_DRY_RUN='1', NO_PROXY='127.0.0.1,localhost')
    process = None
    log_path = SERVICE_ROOT / 'synthetic-service-output.txt'
    log = log_path.open('w')

    def stop():
        nonlocal process
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            process = None

    def start(expected_token=token):
        nonlocal process
        stop()
        service_env = dict(env, HBOS_PRODUCTION_SERVICE_TOKEN=expected_token)
        process = subprocess.Popen([
            SERVICE_PYTHON, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
            '--port', str(service_port), '--no-access-log',
        ], cwd=SERVICE_ROOT / 'hbos_production', env=service_env, stdout=log, stderr=log)
        for _ in range(100):
            assert process.poll() is None, 'Synthetic FastAPI process exited'
            try:
                if _http(service_url + '/health')[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.1)
        raise AssertionError('Synthetic FastAPI did not become ready')

    def no_credentials(raw, surface):
        assert all(value not in raw for value in secret_values), 'Credential in ' + surface

    def no_browser_exposure(raw, surface='browser response'):
        no_credentials(raw, surface)
        assert service_url not in raw and upstream_url not in raw, 'Internal service origin in ' + surface

    def denied(client, case):
        before = dict(upstream.counts)
        for method in METHODS:
            status, body, raw = client.production(method)
            no_browser_exposure(raw)
            assert 'rows' not in raw and upstream.marker not in raw, case + ': data leaked'
            assert (status in (401, 403) or (status == 200 and body.get('ok') is False
                    and body.get('error', {}).get('code') in ('UNAUTHENTICATED', 'FORBIDDEN'))), case
        assert upstream.counts == before, case + ': upstream reached before authorization'
        passed(case, endpoints=len(METHODS), upstream_not_reached=True)

    def allowed(client, *, refresh=False):
        status, body, raw = client.production(refresh=refresh)
        no_browser_exposure(raw)
        assert status == 200 and body.get('ok') is True, 'Authorized board request failed'
        data = body['data']
        row = next(row for row in data['rows'] if row['label'] == '4BMA')
        assert row['target'] == 10 and row['yieldRate'] == 0.93
        assert data['dataAsOf'] and data['month'] == date.today().strftime('%Y-%m')
        return row, data

    def provider_failure(client, case, *, retryable=True):
        status, body, raw = client.production(refresh=True)
        no_browser_exposure(raw)
        assert status == 200 and body.get('ok') is False, case
        error = body.get('error', {})
        assert error.get('code') == 'PROVIDER_ERROR' and error.get('retryable') is retryable, case
        assert 'rows' not in raw and upstream.marker not in raw, case + ': stale success returned'
        passed(case, semantic_error='PROVIDER_ERROR', no_data=True)

    try:
        start()
        origin = str(frappe.conf.hbos_portal_origin)
        admin_password = os.environ.get('OWNER_AUDIT_ADMIN_PASSWORD')
        assert admin_password, 'Bootstrap must pass its new Site synthetic admin password privately'
        secret_values.append(admin_password)
        admin = Browser(origin).login('Administrator', admin_password)
        guest = Browser(origin)
        employee_name = 'production-employee-' + marker + '@example.invalid'
        employee_password = _make_user(employee_name, 'Employee')
        employee = Browser(origin).login(employee_name, employee_password)
        # Respect original User creation throttling in this new Site.
        time.sleep(8)
        manager_name = 'production-platform-' + marker + '@example.invalid'
        manager_password = _make_user(manager_name, 'System Manager')
        manager = Browser(origin).login(manager_name, manager_password)
        secret_values.extend([employee_password, manager_password])

        status, body, raw = admin.production()
        assert status == 200 and body.get('ok') is False
        assert body.get('error', {}).get('code') == 'SERVICE_NOT_CONFIGURED'
        no_browser_exposure(raw)
        passed('frappe_service_not_configured', no_data=True)
        denied(guest, 'guest_rpc_denied')
        denied(employee, 'employee_rpc_denied')
        denied(manager, 'system_manager_rpc_denied')

        for headers, case in [({}, 'missing_token'), ({'X-HBOS-Service-Token': wrong}, 'wrong_token'),
                              ({'Origin': origin}, 'browser_origin_without_token')]:
            for path in ENDPOINTS:
                status, _, raw = _http(service_url + path, headers)
                assert status == 401 and 'rows' not in raw
                no_browser_exposure(raw)
            passed(case, endpoints=len(ENDPOINTS), http=401)

        # Real site_config file, then wait for Frappe's unchanged 60s config-cache TTL.
        # No monkeypatch, extra whitelisted setter, auth bypass or server config endpoint.
        from frappe.installer import update_site_config
        update_site_config('hbos_production_service_url', service_url)
        update_site_config('hbos_production_service_token', token)
        deadline = time.monotonic() + 75
        while True:
            status, body, raw = admin.production()
            no_browser_exposure(raw)
            if status == 200 and body.get('ok') is True:
                break
            assert body.get('error', {}).get('code') == 'SERVICE_NOT_CONFIGURED', 'Unexpected config transition'
            assert time.monotonic() < deadline, 'Frappe site-config cache did not expire'
            time.sleep(2)
        row, data = allowed(admin)
        assert row['done'] == 1 and upstream.counts['auth'] > 0 and upstream.counts['read'] > 0
        passed('administrator_real_frappe_fastapi_upstream_chain', native_session=True,
               actual_http=True, real_aggregation=True, scopes_empty=True)
        status, body, raw = admin.production('get_ai_analysis')
        assert status == 200 and body.get('ok') and upstream.marker in raw
        no_browser_exposure(raw)
        passed('administrator_reads_existing_ai_results', triggers_analysis=False)

        # Warm data must never be served to a separate or newly logged-out session.
        denied(employee, 'employee_denied_after_admin_cache_warm')
        denied(manager, 'system_manager_denied_after_admin_cache_warm')
        status, _, _ = admin.call('logout', post=True)
        assert status == 200
        denied(admin, 'same_browser_logout_denied')
        admin.login(employee_name, employee_password)
        denied(admin, 'same_browser_switched_to_employee_denied')
        admin = Browser(origin).login('Administrator', admin_password)

        # A native user disable takes effect on its real current session too.
        frappe.set_user('Administrator')
        frappe.get_doc('User', manager_name).update({'enabled': 0}).save(ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(user=manager_name)
        status, identity, _ = manager.call('frappe.auth.get_logged_user')
        assert status in (401, 403) or (status == 200 and identity != manager_name), 'Disabled native session remains authenticated'
        denied(manager, 'disabled_system_manager_session_denied')

        upstream.version = 2
        assert allowed(admin)[0]['done'] == 1, 'Ordinary request should use same-day cache'
        assert allowed(admin, refresh=True)[0]['done'] == 2, 'Refresh must reach actual upstream'
        passed('manual_refresh_reaches_upstream', before=1, after=2, data_as_of=True)

        # Check both service auth and Frappe's treatment of rejected upstream credentials.
        start(wrong)
        provider_failure(admin, 'frappe_wrong_service_token', retryable=False)
        start('')
        for path in ENDPOINTS:
            status, _, raw = _http(service_url + path, {'X-HBOS-Service-Token': token})
            assert status == 503 and 'rows' not in raw
            no_browser_exposure(raw)
        passed('fastapi_service_token_unconfigured', endpoints=len(ENDPOINTS), http=503)
        provider_failure(admin, 'frappe_service_unconfigured_upstream')

        upstream.mode = 'error'
        start()
        provider_failure(admin, 'frappe_upstream_502')
        upstream.mode = 'invalid_json'
        start()
        provider_failure(admin, 'frappe_upstream_invalid_json')
        upstream.mode = 'timeout'
        start()
        started = time.monotonic()
        provider_failure(admin, 'frappe_real_proxy_timeout')
        elapsed = time.monotonic() - started
        assert 50 <= elapsed < 75, 'Real unchanged 60s proxy timeout was not exercised'
        passed('proxy_timeout_duration', seconds=round(elapsed, 1))
        stop()
        upstream.mode = 'ok'
        provider_failure(admin, 'frappe_connection_refused')
        start()
        assert allowed(admin, refresh=True)[0]['done'] == 2
        passed('service_recovers_after_failures')

        # Exercise the real AI entrypoint disabled, with a fully synthetic configured upstream.
        ai_env = dict(env, HBOS_AI_BASE_URL=upstream_url + '/v1', HBOS_AI_API_KEY=wrong,
                      HBOS_AI_MODEL='synthetic-never-called')
        ai_env.pop('HBOS_AI_ENABLED', None)
        ai_env.pop('HBOS_AI_DRY_RUN', None)
        before = dict(upstream.counts)
        script = (
            'from app import config,main,writer\n'
            'assert config.AI_ENABLED is False and config.DRY_RUN is True\n'
            'assert main.main()==0\n'
            'records=[{"产品":"SYNTHETIC","工序":"SYNTHETIC","数据指纹":"SYNTHETIC"}]\n'
            'writer.write_results(records,"SYNTHETIC",dry_run=config.DRY_RUN)\n'
        )
        result = subprocess.run([SERVICE_PYTHON, '-c', script],
                                cwd=SERVICE_ROOT / 'hbos_production_ai', env=ai_env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        assert result.returncode == 0, 'Disabled AI / dry-run writer contract failed'
        # This PIPE contains server stdout/stderr, never a Portal response.
        # httpx INFO logs include request URLs during the dry-run writer's read;
        # the same credential prohibition still applies to every output surface.
        no_credentials(result.stdout, 'AI server output')
        passed('ai_server_output_credential_scan', credential_hits=0,
               internal_origin_in_server_diagnostics=upstream_url in result.stdout)
        assert upstream.counts['model'] == before['model'] == 0
        assert upstream.counts['write'] == before['write'] == 0
        passed('ai_defaults_disabled_and_dry_run', model_calls=0, upstream_writes=0)

        stop()
        log.flush()
        # Server logs prohibit credentials. Browser bundles additionally prohibit
        # internal origins, just like the real RPC responses checked above.
        no_credentials(log_path.read_text(), 'FastAPI server log')
        for row in frappe.get_all('Error Log', fields=['error'], limit_page_length=0):
            no_credentials(row.error or '', 'Frappe server error log')
        assets = Path(frappe.get_app_path('hbos_portal', 'public', 'portal'))
        bundles = list(assets.rglob('*.js'))
        assert bundles, 'Actual built frontend assets are required'
        for bundle in bundles:
            no_browser_exposure(bundle.read_text(), 'browser bundle')
        passed('secrets_absent_from_errors_logs_browser_bundles', bundles=len(bundles))
        assert source_hashes == {str(p.relative_to(SERVICE_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in source_files}, 'Fixture modified production service source'
        assert PRODUCTION_ROLES == ()
        assert upstream.counts['write'] == upstream.counts['model'] == 0
        passed('original_sources_and_default_deny_preserved', source_files=len(source_files))
        result = dict(ok=True, domain='production', passed=len(checks), failed=0, skipped=0,
                      checks=checks, upstream=dict(upstream.counts), service_source_sha256=source_hashes)
        print('[PRODUCTION-E2E] summary=' + json.dumps(result), flush=True)
        return result
    finally:
        stop()
        server.shutdown()
        server.server_close()
        log.close()
        # Only this new Site's disposable backend directory is cleaned here.
        log_path.unlink(missing_ok=True)
