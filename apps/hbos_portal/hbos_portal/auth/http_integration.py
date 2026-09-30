"""Real WSGI login requests on a fresh isolated Site; no live provider calls."""
from __future__ import annotations

import json
import secrets
from urllib.parse import urlsplit
import requests
import frappe


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
