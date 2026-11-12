"""Separate native DB connections arbitrate synthetic concurrent accounts."""
from __future__ import annotations

import json
import subprocess
import sys
import frappe


def resolve_worker(identity: dict):
    from unittest.mock import patch
    from hbos_portal.auth import feishu, onboarding
    from hbos_portal.auth.change_integration import synthetic_settings
    with patch.object(feishu, 'load_settings', return_value=synthetic_settings()):
        user, created = onboarding.resolve_verified_login(synthetic_settings(), identity)
        return {'user': user, 'created': created}


def commit_worker(value: dict):
    from inspect import unwrap
    from unittest.mock import patch
    from types import SimpleNamespace
    from werkzeug.test import EnvironBuilder
    from werkzeug.wrappers import Request
    from frappe.auth import CookieManager
    from hbos_portal.auth import accounts, feishu, operations, security
    from hbos_portal.auth.change_integration import synthetic_settings
    frappe.conf.hbos_portal_origin = 'https://hbos.example.test'
    frappe.set_user(value['user']);frappe.local.session.sid=value['sid']
    row=security.record(value['user'])
    frappe.local.session.data=frappe._dict(csrf_token='synthetic-csrf',hbos_security_version=row.security_version)
    frappe.local.request=Request(EnvironBuilder(method='POST',base_url='https://hbos.example.test',json={},
        headers={'Origin':'https://hbos.example.test','X-Requested-With':'XMLHttpRequest','X-Frappe-CSRF-Token':'synthetic-csrf'}).get_environ())
    frappe.local.cookie_manager=CookieManager();frappe.local.request_ip='127.0.0.1'
    frappe.local.login_manager=SimpleNamespace(login_as=lambda u:None,logout=lambda *a,**kw:None)
    try:
        with patch.object(feishu,'load_settings',return_value=synthetic_settings()), patch('frappe.enqueue',return_value=None):
            assert unwrap(accounts.reauthenticate)(password=value['password']).get('verified')
            result=operations.commit_change(operation=value['operation'],confirm=1)
            return {'completed':bool(result['completed'])}
    except (feishu.FeishuLoginError,frappe.UniqueValidationError,frappe.DuplicateEntryError,frappe.PermissionError) as exc:
        frappe.db.rollback()
        return {'completed':False,'code':getattr(exc,'code','identity_conflict')}


def redeem_worker(value: dict):
    from inspect import unwrap
    from unittest.mock import patch
    from werkzeug.test import EnvironBuilder
    from werkzeug.wrappers import Request
    from frappe.auth import CookieManager
    from hbos_portal.auth import feishu, operations
    from hbos_portal.auth.change_integration import synthetic_settings
    frappe.conf.hbos_portal_origin = 'https://hbos.example.test'
    frappe.set_user('Guest')
    frappe.local.session.sid = 'Guest'
    frappe.local.request = Request(EnvironBuilder(method='POST', base_url='https://hbos.example.test', json={},
        headers={'Origin': 'https://hbos.example.test', 'X-Requested-With': 'XMLHttpRequest'}).get_environ())
    frappe.local.cookie_manager = CookieManager()
    frappe.local.request_ip = '127.0.0.1'
    try:
        with patch.object(feishu, 'load_settings', return_value=synthetic_settings()):
            unwrap(operations.redeem_invitation)(operation=value['operation'], invitation=value['invitation'])
            frappe.db.commit()
            return {'accepted': True}
    except (frappe.AuthenticationError, frappe.PermissionError, frappe.QueryDeadlockError, frappe.QueryTimeoutError):
        frappe.db.rollback()
        return {'accepted': False}


def race(identities: list[dict], *, committing=False, redeeming=False) -> list[dict]:
    if not frappe.conf.get('hbos_account_test_site') or not frappe.conf.get('hbos_custody_test_site'):
        raise RuntimeError('Parallel account tests require an explicitly isolated Site')
    frappe.db.commit()
    code = '''import json,os,sys,frappe
os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site=sys.argv[1]);frappe.connect()
try:
 from hbos_portal.auth.concurrency_integration import resolve_worker,commit_worker,redeem_worker
 worker={'commit':commit_worker,'redeem':redeem_worker,'resolve':resolve_worker}[sys.argv[2]]
 print(json.dumps(worker(json.load(sys.stdin))))
finally:frappe.destroy()
'''
    action = 'redeem' if redeeming else 'commit' if committing else 'resolve'
    children = [subprocess.Popen([sys.executable, '-c', code, frappe.local.site, action], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in identities]
    for child, value in zip(children, identities):
        child.stdin.write(json.dumps(value).encode()); child.stdin.close(); child.stdin = None
    results = []
    for child in children:
        output, error = child.communicate(timeout=35)
        if child.returncode:
            # Protected test-site diagnostic only; never a published report.
            from pathlib import Path
            Path(frappe.get_site_path('private', 'concurrency-failure.log')).write_bytes(error)
            raise AssertionError('A separate native SQL account worker failed')
        results.append(json.loads(output))
    frappe.db.commit()
    return results
