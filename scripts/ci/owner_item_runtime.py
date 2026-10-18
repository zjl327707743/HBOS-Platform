"""Synthetic Item ACL integration; runner-only, not a whitelisted product API."""
import os,re,json,secrets
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor,Request,build_opener
import frappe
class Client:
    """Real loopback HTTP; never print cookies, passwords or response bodies."""
    def __init__(self, origin):
        self.headers = {"Host": origin.split("//", 1)[1], "Origin": origin,
                        "X-Requested-With": "XMLHttpRequest"}
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def call(self, method, params=None, *, post=False):
        url = "http://127.0.0.1:8000/api/method/" + method
        encoded = urlencode(params or {}).encode()
        request = Request(url if post or not encoded else url + "?" + encoded.decode(),
                          data=encoded if post else None, headers=self.headers)
        try:
            response = self.opener.open(request, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            text = response.read().decode("utf-8")
            try:
                payload = json.loads(text)
            except ValueError:
                payload = {}
            return response.code, payload, text

    def login(self, user, password):
        status, _, _ = self.call("login", {"usr": user, "pwd": password}, post=True)
        if status != 200:
            raise AssertionError(f"Synthetic standard login failed: HTTP {status}")
        status, payload, _ = self.call("hbos_portal.auth.accounts.get_request_security")
        token = payload.get("message", {}).get("csrf_token")
        if status != 200 or not token:
            raise AssertionError("Synthetic session security token was not issued")
        self.headers["X-Frappe-CSRF-Token"] = token
        return self


def run():
    marker=os.environ.get('HBOS_REPORT_SCOPE_TEST_ID','')
    assert os.environ.get('GITHUB_ACTIONS')=='true' and re.fullmatch(r'[0-9]+-[0-9]+',marker)
    assert frappe.local.site=='report-scope-'+marker+'.localhost' and str(frappe.conf.hbos_report_scope_ci)==marker
    assert all(os.environ.get(k)=='0' for k in ['HBOS_AI_ENABLED','HBOS_AI_ALLOW_PII','HBOS_FEISHU_SYNC_ENABLED','HBOS_DELICLOUD_SYNC_ENABLED'])
    frappe.set_user('Administrator')
    user='item-reader@example.invalid';password=secrets.token_urlsafe(32)
    assert not frappe.db.exists('User',user)
    frappe.get_doc(dict(doctype='User',email=user,first_name='Synthetic Item Reader',enabled=1,user_type='System User',send_welcome_email=0,new_password=password,roles=[dict(role='Stock User')])).insert(ignore_permissions=True)
    now=frappe.utils.now_datetime()
    for name in ['CLOUD-ITEM-A','CLOUD-ITEM-B']:
        frappe.db.sql('INSERT INTO `tabItem` (name,item_code,item_name,owner,modified_by,creation,modified,docstatus,disabled,stock_uom,hbos_storage_condition) VALUES (%s,%s,%s,%s,%s,%s,%s,0,0,%s,%s)',(name,name,name+' synthetic','Administrator','Administrator',now,now,'Nos','Synthetic dry storage'))
    frappe.get_doc(dict(doctype='User Permission',user=user,allow='Item',for_value='CLOUD-ITEM-A',apply_to_all_doctypes=1)).insert(ignore_permissions=True)
    frappe.db.commit();frappe.clear_cache(user=user)
    origin=str(frappe.conf.hbos_portal_origin);guest=Client(origin);client=Client(origin).login(user,password)
    checks=[]
    def call(method,params,allowed=True,visible=None,forbidden=None):
        status,payload,text=client.call(method,params)
        assert status==(200 if allowed else 403),(method,status,payload.get('exc_type'))
        if visible:assert visible in text,(method,'missing positive record')
        if forbidden:assert forbidden not in text,(method,'cross-Item data leak')
        checks.append(dict(method=method,http=status))
        print('[OWNER-ITEM] check='+json.dumps(checks[-1]))
    fields=json.dumps(['name','item_name','item_group','stock_uom','hbos_product_kind','hbos_workshop','hbos_storage_condition','hbos_shelf_life_type','hbos_shelf_life_months','has_batch_no','disabled'])
    params=dict(doctype='Item',fields=fields,limit_page_length=201,order_by='name asc')
    call('frappe.client.get_list',params,visible='CLOUD-ITEM-A',forbidden='CLOUD-ITEM-B')
    call('frappe.client.get_list',{**params,'or_filters':json.dumps([['name','like','%CLOUD-ITEM%'],['item_name','like','%CLOUD-ITEM%']])},visible='CLOUD-ITEM-A',forbidden='CLOUD-ITEM-B')
    call('frappe.client.get',dict(doctype='Item',name='CLOUD-ITEM-A'),visible='Synthetic dry storage')
    call('frappe.client.get',dict(doctype='Item',name='CLOUD-ITEM-B'),False,forbidden='CLOUD-ITEM-B synthetic')
    status,_,text=guest.call('frappe.client.get',dict(doctype='Item',name='CLOUD-ITEM-A'))
    assert status==403 and 'Synthetic dry storage' not in text
    checks.append(dict(case='guest_denied',http=status))
    # Current session loses all Item role permissions; no new login or mocked ACL.
    u=frappe.get_doc('User',user);u.set('roles',[]);u.save(ignore_permissions=True);frappe.db.commit();frappe.clear_cache(user=user)
    call('frappe.client.get_list',params,False,forbidden='Synthetic dry storage')
    call('frappe.client.get',dict(doctype='Item',name='CLOUD-ITEM-A'),False,forbidden='Synthetic dry storage')
    status,payload,_=client.call('frappe.auth.get_logged_user')
    assert status==403 or (status==200 and payload.get('message')==user), 'Unexpected session after role revocation'
    checks.append(dict(case='role_revocation_session',http=status,invalidated=status==403))
    print('[OWNER-ITEM] check='+json.dumps(checks[-1]))
    # Frappe may invalidate the current session after a role change. Test logout
    # independently on a new genuine authenticated session, without restoring roles.
    client=Client(origin).login(user,password)
    status,payload,_=client.call('frappe.auth.get_logged_user')
    assert status==200 and payload.get('message')==user, 'Logout precondition requires an authenticated session'
    status,_,_=client.call('logout',post=True)
    assert status==200, 'Logout request failed'
    status,_,_=client.call('frappe.auth.get_logged_user')
    assert status==403, 'Session remained authenticated after logout'
    checks.append(dict(case='logout_session_invalidated',http=status))
    call('frappe.client.get',dict(doctype='Item',name='CLOUD-ITEM-A'),False,forbidden='Synthetic dry storage')
    # Regress the unchanged baseline provider/route contracts and LIMS release projection.
    import importlib
    os.environ['HBOS_PORTAL_INTEGRATION_CHECKS']='1'
    os.environ['HBOS_G1_INTEGRATION_CHECKS']='1'
    os.environ['HBOS_G3_INTEGRATION_CHECKS']='1'
    modules=['hbos_portal.integration_checks','hb_attendance_app.hbos_attendance.portal.integration_checks','hb_inventory_app.hbos_inventory.portal.integration_checks','hb_lims_app.hbos_lims.portal.integration_checks','hb_attendance_app.hbos_attendance.g1_integration_checks','hb_lims_app.hbos_lims.g3_integration_checks']
    for module in modules:
        frappe.set_user('Administrator')
        result=importlib.import_module(module).run()
        print('[OWNER-ITEM] baseline='+json.dumps(dict(module=module,result=result),default=str))

    print('[OWNER-ITEM] '+json.dumps(dict(ok=True,checks=checks,source='native Frappe HTTP + MariaDB + User Permission',owner_environment='NOT_TOUCHED')))
    return dict(ok=True,checks=checks)
