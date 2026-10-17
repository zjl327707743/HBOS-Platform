"""One-time synthetic runtime audit; never whitelisted or shipped to product."""
import os,re,json,unittest,importlib.util,time
import frappe
from pathlib import Path

def run():
    marker=os.environ.get('HBOS_REPORT_SCOPE_TEST_ID','')
    assert os.environ.get('GITHUB_ACTIONS')=='true' and re.fullmatch(r'[0-9]+-[0-9]+',marker)
    assert frappe.local.site=='report-scope-'+marker+'.localhost'
    assert str(frappe.conf.hbos_report_scope_ci)==marker
    assert os.environ.get('HBOS_FRAPPE_SMOKE')=='1'
    assert all(os.environ.get(k)=='0' for k in ['HBOS_AI_ENABLED','HBOS_AI_ALLOW_PII','HBOS_FEISHU_SYNC_ENABLED','HBOS_DELICLOUD_SYNC_ENABLED'])
    frappe.set_user('Administrator')
    print('[OWNER-AUDIT] installed_apps='+json.dumps(frappe.get_installed_apps()))
    domain=os.environ['OWNER_AUDIT_DOMAIN']
    if domain=='inventory': return inventory()
    if domain=='attendance': return attendance()
    users={'r7c-mgr@test.local':['LIMS Manager'],'test-hbos-m2-analyst@test.local':['LIMS Analyst'],'r7c-an@test.local':['LIMS Analyst'],'test-hbos-m2-reviewer@test.local':['LIMS Reviewer'],'r7c-qc1@test.local':['LIMS Reviewer'],'r7c-qc2@test.local':['LIMS Reviewer'],'r7c-qa1@test.local':['LIMS QA'],'r7c-qa2@test.local':['LIMS QA'],'r7audit@test.local':['System Manager']}
    for user,roles in users.items():
        assert not frappe.db.exists('User',user), 'Never reuse existing user'
        frappe.get_doc(dict(doctype='User',email=user,first_name='Synthetic CI',enabled=1,send_welcome_email=0,user_type='System User',roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True)
        frappe.db.commit()
        time.sleep(8)
    for i in range(3):
        frappe.get_doc(dict(doctype='HBOS Test Item',item_code='CLOUD-TEST-'+str(i),item_name='Synthetic CI '+str(i),item_category='理化检验',significant_digits=2)).insert(ignore_permissions=True)
    frappe.get_doc(dict(doctype='HBOS Sample Type',sample_type_code='CLOUD-TYPE',sample_type_name='原料')).insert(ignore_permissions=True)
    frappe.get_doc(dict(doctype='HBOS Lab Department',department_code='CLOUD-LAB',department_name='理化检验组')).insert(ignore_permissions=True)
    frappe.db.commit()
    root=Path('/home/frappe/frappe-bench/apps/hb_lims_app/tests')
    names=['test_lims_guards_runtime','test_lims_result_sod_runtime','test_lims_coa_snapshot_runtime','test_lims_break_glass_runtime','test_lims_spec_version_runtime','test_audit_transaction_runtime','test_lims_audit_integrity_runtime']
    summary=[]
    for name in names:
        frappe.set_user('Administrator')
        spec=importlib.util.spec_from_file_location(name,root/(name+'.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        if name=='test_lims_audit_integrity_runtime':
            # Fresh synthetic Site has no historical v1 rows. Establish independent
            # committed fixtures; never change audit_log(commit=True) no-op semantics.
            from hb_lims_app.hbos_lims import lims_service as svc
            svc.audit_log('修改','HBOS Sample','TEST-HBOS-P002-AUDIT-SENTINEL',action_text='Synthetic independent v2 anchor fixture')
            legacy=svc.audit_log('修改','HBOS Sample','CLOUD-LEGACY-AUDIT',action_text='Synthetic historical v1 fixture')
            legacy_payload=frappe.get_doc('HBOS Audit Log',legacy).as_dict()
            frappe.db.set_value('HBOS Audit Log',legacy,dict(checksum_version='',checksum=svc._checksum(legacy_payload,version='1')),update_modified=False)
            frappe.db.commit()
            print('[OWNER-AUDIT] integrity-fixture='+json.dumps(dict(v2_sentinel=True,synthetic_v1=True,production_code_unchanged=True)))
        suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        summary.append(dict(name=name,run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped)))
        print('[OWNER-AUDIT] '+json.dumps(summary[-1]))
    print('[OWNER-AUDIT] summary='+json.dumps(summary))
    assert all(x['run']>0 and not(x['failures'] or x['errors'] or x['skips']) for x in summary), 'Runtime suite incomplete or failed'
    return dict(ok=True,suites=summary)

import secrets,gzip
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import HTTPCookieProcessor, Request, build_opener
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


def sql_fixture(doctype, values):
    now=frappe.utils.now_datetime()
    values={'creation':now,'modified':now,'owner':'Administrator','modified_by':'Administrator','docstatus':0,**values}
    columns=','.join('`'+k+'`' for k in values)
    frappe.db.sql('INSERT INTO `tab'+doctype+'` ('+columns+') VALUES ('+','.join(['%s']*len(values))+')',tuple(values.values()))

def make_user(email,role):
    assert not frappe.db.exists('User',email)
    password=secrets.token_urlsafe(32)
    frappe.get_doc(dict(doctype='User',email=email,first_name='Synthetic Cloud Audit',enabled=1,user_type='System User',send_welcome_email=0,new_password=password,roles=[dict(role=r) for r in (role if isinstance(role,list) else [role])])).insert(ignore_permissions=True)
    frappe.db.commit()
    return password

def attendance():
    from hb_attendance_app.hbos_attendance.report_scope_runtime_checks import run as existing
    result=existing()
    print('[OWNER-AUDIT] attendance-existing='+json.dumps(result))
    user='cloud-prepared@example.invalid';password=make_user(user,'HR User')
    prefix='CLOUD-ATT';company=prefix+'-COMPANY'
    sql_fixture('Company',dict(name=company,company_name=company,abbr='CAT',default_currency='CNY',country='China',is_group=0))
    deps=[]
    for x in ['A','B']:
        d=frappe.get_doc(dict(doctype='Department',department_name=prefix+'-'+x,company=company,is_group=0)).insert(ignore_permissions=True)
        deps.append(d.name)
        sql_fixture('Employee',dict(name=prefix+'-EMP-'+x,employee_name='Synthetic '+x,employee_number=prefix+x,status='Active',department=d.name,company=company))
    report='月度考勤汇总';prepared='CLOUD-PREPARED-ATT';marker='SYNTHETIC-HIDDEN-DEPARTMENT-B'
    sql_fixture('Prepared Report',dict(name=prepared,report_name=report,status='Completed',filters='{}',owner=user))
    from frappe.core.doctype.prepared_report.prepared_report import create_json_gz_file
    create_json_gz_file({'columns':[{'fieldname':'employee','label':'Employee','fieldtype':'Data'}],'result':[{'employee':marker}]},'Prepared Report',prepared,report)
    file=frappe.db.get_value('File',dict(attached_to_doctype='Prepared Report',attached_to_name=prepared),['name','file_url'],as_dict=True)
    frappe.get_doc(dict(doctype='User Permission',user=user,allow='Employee',for_value=prefix+'-EMP-A',apply_to_all_doctypes=1,hide_descendants=1)).insert(ignore_permissions=True)
    frappe.db.commit();frappe.clear_cache(user=user)
    frappe.set_user(user)
    from hb_attendance_app.hbos_attendance.report_scope import require_unrestricted_employee_read
    try:require_unrestricted_employee_read()
    except frappe.PermissionError:pass
    else:raise AssertionError('Prepared-cache fixture must be restricted; visible='+json.dumps(frappe.get_list('Employee',pluck='name',limit_page_length=0)))
    origin=str(frappe.conf.hbos_portal_origin);client=Client(origin).login(user,password)
    status,payload,_=client.call('frappe.auth.get_logged_user')
    assert status==200 and payload.get('message')==user, 'Fresh HTTP identity prerequisite'
    status,payload,text=client.call('frappe.client.get_list',dict(doctype='Employee',fields=json.dumps(['name']),limit_page_length=200))
    assert status==200 and prefix+'-EMP-A' in text and prefix+'-EMP-B' not in text, 'Fresh HTTP native Employee scope prerequisite'
    print('[OWNER-AUDIT] prepared-prerequisites='+json.dumps(dict(identity=True,employee_a_visible=True,employee_b_hidden=True)))
    # Download cached output generated before restriction, without executing SQL again.
    try:
        response=client.opener.open(Request('http://127.0.0.1:8000'+quote(file.file_url,safe='/'),headers=client.headers),timeout=30)
    except HTTPError as error:
        response=error
    with response:
        body=response.read();status=response.code
    assert status in (200,403), 'Unexpected attachment HTTP status '+str(status)
    leaked=marker.encode() in gzip.decompress(body) if status==200 else False
    print('[OWNER-AUDIT] '+json.dumps(dict(case='prepared_report_file_after_scope_revocation',http=status,leaked=leaked)))
    assert not leaked, 'Restricted HR can download stale all-employee Prepared Report attachment'
    return dict(ok=True)

def inventory():
    from hb_inventory_app.hbos_inventory import warehouse_scope
    reports=['货位明细表','库级盘点三对账','按批号查货位','效期预警']
    user='cloud-stock-a@example.invalid';password=make_user(user,['Stock User','Item Manager'])
    company='CLOUD-STOCK-COMPANY'
    sql_fixture('Company',dict(name=company,company_name=company,abbr='CST',default_currency='CNY',country='China',is_group=0))
    warehouses=[]
    for i,x in enumerate(['A','B']):
        name='CLOUD-WH-'+x
        sql_fixture('Warehouse',dict(name=name,warehouse_name=name,company=company,is_group=0,disabled=0,lft=2*i+1,rgt=2*i+2))
        warehouses.append(name)
        item='CLOUD-ITEM-'+x;batch='CLOUD-BATCH-'+x;bundle='CLOUD-BUNDLE-'+x
        sql_fixture('Item',dict(name=item,item_code=item,item_name='Synthetic '+x,stock_uom='Nos',is_stock_item=1,has_batch_no=1))
        sql_fixture('Batch',dict(name=batch,batch_id=batch,item=item,expiry_date=frappe.utils.add_days(frappe.utils.today(),10),hbos_supplier_batch_no='CLOUD-SUPPLIER-'+x))
        sql_fixture('Serial and Batch Bundle',dict(name=bundle,docstatus=1,is_cancelled=0,is_rejected=0,item_code=item,warehouse=name))
        sql_fixture('Serial and Batch Entry',dict(name='CLOUD-ENTRY-'+x,parent=bundle,parenttype='Serial and Batch Bundle',parentfield='entries',idx=1,docstatus=1,item_code=item,batch_no=batch,warehouse=name,qty=i+1,is_cancelled=0))
    frappe.get_doc(dict(doctype='User Permission',user=user,allow='Warehouse',for_value=warehouses[0],apply_to_all_doctypes=1)).insert(ignore_permissions=True)
    frappe.db.commit();frappe.clear_cache(user=user);frappe.set_user(user)
    assert warehouse_scope.resolve_scope({})==[warehouses[0]], 'Real Warehouse User Permission fixture invalid'
    origin=str(frappe.conf.hbos_portal_origin);client=Client(origin).login(user,password)
    checks=[]
    failures=[]
    for name in reports:
        for filters,allowed in [({},True),({'warehouse':warehouses[0]},True),({'warehouse':warehouses[0],'include_children':1},True),({'warehouse':warehouses[1]},False),({'warehouse':warehouses[1],'include_children':1},False)]:
            status,payload,text=client.call('frappe.desk.query_report.run',dict(report_name=name,filters=json.dumps(filters),ignore_prepared_report=1))
            assert 'CLOUD-BATCH-B' not in text and 'CLOUD-SUPPLIER-B' not in text,'Cross-Warehouse data leak'
            print('[OWNER-AUDIT] report-case='+json.dumps(dict(report=name,filters=filters,http=status,expected_allowed=allowed,messages=payload.get('_server_messages','')[:1200])))
            if allowed:
                if status!=200 or 'CLOUD-BATCH-A' not in text: failures.append(dict(report=name,http=status,case='positive'))
            elif status!=403:failures.append(dict(report=name,http=status,case='negative'))
            checks.append(dict(report=name,filter=filters,http=status))
    # Pure Stock User lacks upstream Batch report rights; preserve that negative.
    frappe.set_user('Administrator')
    pure='cloud-pure-stock@example.invalid';pure_password=make_user(pure,'Stock User')
    pure_client=Client(origin).login(pure,pure_password)
    for report in reports[2:]:
        status,_,text=pure_client.call('frappe.desk.query_report.run',dict(report_name=report,filters='{}',ignore_prepared_report=1))
        assert status==403 and 'CLOUD-BATCH-' not in text, 'Native Batch role denial must remain'
        checks.append(dict(case='pure_stock_user_batch_denied',report=report,http=status))
    frappe.set_user(user)
    print('[OWNER-AUDIT] inventory='+json.dumps(checks))
    # Record actual upstream constraints and native submit/cancel rights, without posting stock.
    for doctype in ['Stock Reconciliation','Stock Entry']:
        print('[OWNER-AUDIT] rights='+json.dumps(dict(doctype=doctype,submit=bool(frappe.has_permission(doctype,'submit',user=user)),cancel=bool(frappe.has_permission(doctype,'cancel',user=user)))))
    import inspect
    from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
    for name in ['validate_warehouse','validate_source_and_target_warehouse']:
        method=getattr(StockEntry,name,None)
        if method:print('[OWNER-AUDIT] upstream-'+name+'='+inspect.getsource(method))
    assert not failures, 'Native report validation failed: '+json.dumps(failures)
    return dict(ok=True,checks=checks,stock_posting='NOT_RUN',export='NOT_RUN')
