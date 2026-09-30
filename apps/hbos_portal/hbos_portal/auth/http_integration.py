"""Real WSGI login requests on a fresh isolated Site; no live provider calls."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit
import requests
import frappe


def _path() -> Path:
    return Path(frappe.get_site_path('private', 'hbos-http-synthetic.json'))


def prepare() -> dict:
    """Keep the existing CI fixture contract alongside the new JSON checks."""
    if not frappe.conf.get('hbos_account_test_site') or _path().exists():
        raise RuntimeError('Requires designated test Site and no outstanding owned fixture')
    original = frappe.in_test
    frappe.in_test = True
    try:
        user = 'account-http-' + secrets.token_hex(6) + '@example.test'
        password = secrets.token_urlsafe(40)
        frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'HTTP合成验证',
            'user_type': 'Website User', 'enabled': 1, 'send_welcome_email': 0}).insert(ignore_permissions=True)
        from frappe.utils.password import update_password
        update_password(user, password)
        frappe.db.commit()
        fd = os.open(_path(), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump({'user': user, 'password': password}, handle)
        return {'created': True, 'scope': 'synthetic_test_site_only'}
    finally:
        frappe.in_test = original


def change_enabled(enabled: int = 0) -> dict:
    if not frappe.conf.get('hbos_account_test_site'):
        raise RuntimeError('Not a test Site')
    fixture = json.loads(_path().read_text())
    doc = frappe.get_doc('User', fixture['user'])
    if doc.first_name != 'HTTP合成验证' or not doc.name.endswith('@example.test'):
        raise RuntimeError('Unexpected fixture')
    doc.enabled = int(enabled)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {'enabled': doc.enabled}


def cleanup() -> dict:
    if not frappe.conf.get('hbos_account_test_site') or not _path().exists():
        raise RuntimeError('Not an owned test fixture')
    fixture = json.loads(_path().read_text())
    doc = frappe.get_doc('User', fixture['user'])
    if doc.first_name != 'HTTP合成验证' or not doc.name.endswith('@example.test'):
        raise RuntimeError('Unexpected fixture')
    original = frappe.in_test
    frappe.in_test = True
    try:
        frappe.delete_doc('User', doc.name, force=True, ignore_permissions=True)
        frappe.db.commit()
        _path().unlink()
        return {'removed': True}
    finally:
        frappe.in_test = original


def run(transport: str = '') -> dict:
    if not frappe.conf.get('hbos_account_test_site') or not frappe.conf.get('hbos_custody_test_site'):
        raise RuntimeError('HTTP auth tests require a fresh designated isolated Site')
    origin=str(frappe.conf.get('hbos_portal_origin') or '').rstrip('/')
    destination=transport or origin
    if urlsplit(destination).hostname not in {'127.0.0.1','localhost',frappe.local.site}:
        raise RuntimeError('HTTP auth tests may target only the explicit isolated Site or loopback')
    suffix=secrets.token_hex(6);user='http-change-'+suffix+'@example.test';alias='http'+suffix;password=secrets.token_urlsafe(40)
    from frappe.utils.password import update_password
    frappe.set_user('Administrator')
    frappe.get_doc({'doctype':'User','email':user,'username':alias,'first_name':'合成 HTTP 账号','enabled':1,'user_type':'Website User','send_welcome_email':0}).insert(ignore_permissions=True)
    update_password(user,password);frappe.db.commit()
    client=requests.Session();client.trust_env=False
    headers={'Origin':origin,'Host':urlsplit(origin).netloc,'X-Requested-With':'XMLHttpRequest'}
    prefix='/api/method/hbos_portal.auth.accounts.'
    def post(method,data,custom=None):
        security=client.get(destination+prefix+'get_request_security',headers=headers,timeout=10).json()['message']
        return client.post(destination+prefix+method,json=data,headers={**headers,**({'X-Frappe-CSRF-Token':security['csrf_token']} if security.get('csrf_token') else {}),**(custom or {})},timeout=10)
    checks=[]
    try:
        response=post('password_login',{'username':alias,'password':'synthetic-wrong'})
        assert response.status_code in (401,403,417)
        checks.append('real_http_wrong_password_rejected')
        response=post('password_login',{'username':alias,'password':password},{'Origin':'https://other.invalid'})
        assert response.status_code in (400,403,417)
        checks.append('real_http_password_login_checks_origin')
        response=post('password_login',{'username':alias,'password':password})
        assert response.status_code==200 and response.json()['message']['logged_in']
        actual=client.get(destination+'/api/method/frappe.auth.get_logged_user',headers=headers,timeout=10)
        assert actual.status_code==200 and actual.json()['message']==user
        checks.append('real_http_pinyin_style_username_json_login_issues_native_session')
        response=post('reauthenticate',{'password':password},{'X-Frappe-CSRF-Token':'synthetic-wrong'})
        assert response.status_code in (400,403,417)
        checks.append('real_http_authenticated_post_checks_native_csrf')
        response=post('reauthenticate',{'password':password})
        assert response.status_code==200 and response.json()['message']['verified']
        checks.append('real_http_same_account_password_stepup')
        token=client.get(destination+prefix+'get_request_security',headers=headers,timeout=10).json()['message']['csrf_token']
        response=client.post(destination+'/api/method/logout',json={},headers={**headers,'X-Frappe-CSRF-Token':token},timeout=10)
        assert response.status_code==200
        actual=client.get(destination+'/api/method/frappe.auth.get_logged_user',headers=headers,timeout=10)
        assert actual.status_code!=200 or actual.json().get('message')!=user
        checks.append('real_http_logout_removes_native_identity')
        return {'status':'PASS','checks':checks,'scope':'isolated_native_wsgi_http','owner_oauth':'NOT_TESTED'}
    finally:
        client.close();frappe.set_user('Administrator')
        from hbos_portal.auth.accounts import revoke_sessions
        revoke_sessions(user);frappe.flags.hbos_owned_test_cleanup=True
        frappe.delete_doc('User',user,force=True,ignore_permissions=True);frappe.db.commit();frappe.flags.hbos_owned_test_cleanup=False
