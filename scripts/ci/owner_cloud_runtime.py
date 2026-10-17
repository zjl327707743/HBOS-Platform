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
    print('[OWNER-AUDIT] versions='+json.dumps(frappe.get_versions()))
    users={'r7c-mgr@test.local':['LIMS Manager'],'test-hbos-m2-analyst@test.local':['LIMS Analyst'],'r7c-an@test.local':['LIMS Analyst'],'test-hbos-m2-reviewer@test.local':['LIMS Reviewer'],'r7c-qc2@test.local':['LIMS Reviewer'],'r7c-qa1@test.local':['LIMS QA'],'r7c-qa2@test.local':['LIMS QA'],'r7audit@test.local':['System Manager']}
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
        suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        summary.append(dict(name=name,run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped)))
        print('[OWNER-AUDIT] '+json.dumps(summary[-1]))
    print('[OWNER-AUDIT] summary='+json.dumps(summary))
    assert all(x['run']>0 and not(x['failures'] or x['errors'] or x['skips']) for x in summary), 'Runtime suite incomplete or failed'
    return dict(ok=True,suites=summary)
