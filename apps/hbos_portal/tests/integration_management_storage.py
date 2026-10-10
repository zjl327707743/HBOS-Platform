"""Explicit exact-Preview CLI policy acceptance. No RPC or production import.

prepare reloads two fixed schemas after a private backup check. test creates
only exact generated synthetic records and finally removes them. No real pins,
operators, application configuration, passwords, roles or Employee.save writes.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.frappe_management_repository import (
    FrappeManagementPolicyRepository, LockedManagementPolicyLoader, ManagementPolicyStore,
)
from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.management_policy import evaluate_management_policy, management_policy_digest, parse_management_context, parse_management_policy
from hbos_portal.organization.management_storage import (
    POLICY, POLICY_PROVIDER, POLICY_REVISION, PolicyApprovalPin, PinnedPolicyApprovalVerifier, policy_data, policy_record,
)
from hbos_portal.organization.storage_schema import LOCK_KEY, WRITE_LOCK, canonical_json, revision_key
if __package__:
    from .integration_organization_storage import SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check, verify_backup
else:
    from integration_organization_storage import SITE, DB_HASH, KINDS, check_target, native_fingerprints, preflight, schema_check, verify_backup

POLICY_KINDS=(POLICY,POLICY_REVISION)
NOW=datetime(2026,10,10,tzinfo=timezone.utc)


def policy_presence(native):
    return {kind:bool(native.db.sql('SELECT 1 FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s',('tab'+kind,))) for kind in POLICY_KINDS}


def policy_schema_check(native):
    result={}
    for kind in POLICY_KINDS:
        table='tab'+kind
        engine=native.db.sql('SELECT engine FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name=%s',(table,))
        indexes=native.db.sql(f'SHOW INDEX FROM `{table}`',as_dict=True)
        unique={row['Column_name'] for row in indexes if not row['Non_unique']}
        times=dict(native.db.sql('SELECT column_name, datetime_precision FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name=%s AND column_name LIKE %s',(table,'%\\_utc')))
        meta=native.get_meta(kind)
        if len(engine)!=1 or engine[0][0]!='InnoDB' or not {'name','record_key'}<=unique or not times or set(times.values())!={6}:
            raise RuntimeError('POLICY_SCHEMA_MISMATCH')
        if meta.permissions or meta.allow_import or meta.allow_rename:
            raise RuntimeError('POLICY_GENERAL_PERMISSION')
        result[kind]={'engine':'InnoDB','unique_columns':sorted(unique),'utc_precision':times,'permissions':[]}
    return result


def repository(native):
    relations=FrappeRelationRepository(native=native,enabled=True)
    return FrappeManagementPolicyRepository(relations,enabled=True,expected_site=SITE,expected_database_sha256=DB_HASH)


def verifier(policy):
    # Explicit SYNTHETIC pin built in this isolated acceptance harness only.
    pin=PolicyApprovalPin(SITE,DB_HASH,policy.policy_id,policy.revision,policy.authority_generation,
        policy.subject_user,management_policy_digest(policy),canonical_json(policy_data(policy)['approval']),'SYNTHETIC-PREVIEW-ONLY')
    return PinnedPolicyApprovalVerifier((pin,))


class NativePolicyCases(unittest.TestCase):
    native=None
    def setUp(self):
        f=self.native;f.db.rollback();self.before=native_fingerprints(f)
        self.prefix='MP-CHECK-'+uuid4().hex[:12]
        self.subject=self.prefix.lower()+'-manager@example.invalid'
        self.approver=self.prefix.lower()+'-owner@example.invalid'
        self.company=self.prefix+'-CO';self.department=self.prefix+'-DEPT';self.policy_id=str(uuid4())
        for user in (self.subject,self.approver):
            f.db.sql("INSERT INTO `tabUser` (name,email,enabled,user_type,modified) VALUES (%s,%s,1,'System User',NOW(6))",(user,user))
        f.db.sql('INSERT INTO `tabCompany` (name,modified) VALUES (%s,NOW(6))',(self.company,))
        f.db.sql('INSERT INTO `tabDepartment` (name,company,is_group,disabled,modified) VALUES (%s,%s,0,0,NOW(6))',(self.department,self.company))
        self.repo=repository(f);self.repo.relations.initialize_write_lock();f.db.commit()
        f.set_user('Administrator')
        self.active=self.make_policy()
    def tearDown(self):
        f=self.native;f.db.rollback();f.set_user('Administrator')
        f.db.sql('DELETE FROM `tabHBOS Organization Management Policy Revision` WHERE policy=%s',(self.policy_id,))
        f.db.sql('DELETE FROM `tabHBOS Organization Management Policy` WHERE name=%s',(self.policy_id,))
        for user in (self.subject,self.approver):f.db.sql('DELETE FROM `tabUser` WHERE name=%s',(user,))
        f.db.sql('DELETE FROM `tabDepartment` WHERE name=%s',(self.department,))
        f.db.sql('DELETE FROM `tabCompany` WHERE name=%s',(self.company,))
        f.db.sql('DELETE FROM `tabHBOS Organization Write Lock` WHERE name=%s',(LOCK_KEY,))
        f.db.commit()
        self.assertEqual(native_fingerprints(f),self.before)
        self.assertTrue(all(f.db.count(kind)==0 for kind in (*KINDS,*POLICY_KINDS)))
        f.db.rollback()
    def make_policy(self,revision=1,generation=1,status='active'):
        payload=dict(policy_id=self.policy_id,subject_user=self.subject,status=status,revision=revision,
            authority_generation=generation,schema_version=1,valid_from_utc='2026-10-09T00:00:00Z',valid_until_utc='2026-11-01T00:00:00Z',approval=None,
            rules=[dict(rule_id='synthetic-position-rule',operation_schema_version=1,operation_ids=['hbos.organization.position.create'],company_id=self.company,
                target_department_ids=[self.department],include_children=False,assignment_until_limit_utc=None,person_scope=None)])
        row=parse_management_policy(payload,site_id=SITE,source_provider=POLICY_PROVIDER)
        payload['approval']=dict(approval_ref='SYNTHETIC-PREVIEW-APPROVAL',approved_by=self.approver,approved_at_utc='2026-10-09T00:00:00Z',
            approved_revision=revision,approved_authority_generation=generation,content_digest=management_policy_digest(row))
        return parse_management_policy(payload,site_id=SITE,source_provider=POLICY_PROVIDER)
    def write(self,row=None,expected=0,repo=None,pins=True):
        row=row or self.active
        return ManagementPolicyStore(repo or self.repo,clock=lambda:NOW,operator_users=('Administrator',),
            approval_verifier=verifier(row) if pins else None,enabled=True).write(row,expected_revision=expected,reason='管理政策隔离合成验收')
    def load(self):
        f=self.native;f.set_user(self.subject)
        try:
            with self.repo.relations.transaction():
                self.repo.relations.lock_writer()
                return LockedManagementPolicyLoader(self.repo,clock=lambda:NOW,approval_verifier=verifier(self.active),enabled=True)()
        finally:f.set_user('Administrator')
    def context(self):
        return parse_management_context(dict(operation_id='hbos.organization.position.create',operation_schema_version=1,now_utc=NOW.isoformat(),
            expected_revision=0,organization_status='active',position_before=None,position_after=dict(record_id=str(uuid4()),company_id=self.company,department_id=self.department,
            title='合成岗位候选',designation_id=None,status='active',revision=1),assignment_before=None,assignment_after=None,person=None),
            site_id=SITE,policy_provider_id=POLICY_PROVIDER,actor_user=self.subject,actor_enabled=True)
    def assert_code(self,code,action):
        with self.assertRaises(ContractError) as caught:action()
        self.assertEqual(caught.exception.code,code)
    def external(self,action):
        def worker():
            import frappe
            frappe.init(site=SITE,sites_path='.');frappe.connect()
            try:
                check_target(frappe,DB_HASH);frappe.db.rollback();frappe.set_user('Administrator')
                frappe.db.sql('SET SESSION innodb_lock_wait_timeout=2')
                result=action(frappe,repository(frappe));frappe.db.commit();return result
            finally:frappe.db.rollback();frappe.destroy()
        with ThreadPoolExecutor(max_workers=1) as pool:return pool.submit(worker).result(timeout=15)

    def test_active_policy_requires_verified_pin_and_native_sources(self):
        self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:self.write(pins=False))
        self.assertEqual(self.native.db.count(POLICY),0)
        self.write();heads=self.load()
        result=evaluate_management_policy(heads,self.context(),enabled=True)
        self.assertTrue(result.matched);self.assertEqual(result.authorization_effect,'none');self.assertFalse(result.runtime_verified)
    def test_administrator_without_explicit_operator_configuration_denied(self):
        store=ManagementPolicyStore(self.repo,clock=lambda:NOW,approval_verifier=verifier(self.active),enabled=True)
        self.assert_code('POLICY_OPERATOR_DENIED',lambda:store.write(self.active,expected_revision=0,reason='无运维资格拒绝验证'))
        self.assertEqual(self.native.db.count(POLICY),0)
    def test_immutable_revisions_restore_approval_and_subject_no_rebinding(self):
        self.write();self.native.db.commit()
        revoked=replace(self.active,status='revoked',revision=2,authority_generation=2)
        self.write(revoked,1,pins=False)
        restored=self.make_policy(3,3)
        self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:self.write(restored,2,pins=False))
        self.write(restored,2)
        self.assertEqual(self.native.db.count(POLICY_REVISION),3)
        self.assert_code('POLICY_SUBJECT_IMMUTABLE',lambda:self.write(replace(restored,subject_user=self.approver,revision=4,authority_generation=4),3))
    def test_revision_failure_rolls_back_head_in_same_transaction(self):
        self.write();self.native.db.commit();candidate=replace(self.active,status='revoked',revision=2,authority_generation=2)
        original=self.native.get_doc
        def get_doc(*args,**kwargs):
            doc=original(*args,**kwargs)
            if args and isinstance(args[0],dict) and args[0].get('doctype')==POLICY_REVISION:
                def fail(*a,**kw):raise RuntimeError('synthetic revision insertion failure')
                doc.insert=fail
            return doc
        with patch.object(self.native,'get_doc',side_effect=get_doc),self.assertRaises(RuntimeError):self.write(candidate,1,pins=False)
        self.assertEqual(self.native.db.get_value(POLICY,self.policy_id,'revision'),1)
        self.assertEqual(self.native.db.count(POLICY_REVISION),1)
    def test_actual_orm_flags_partial_write_delete_rename_and_history_overwrite_rejected(self):
        self.write()
        doc=self.native.get_doc(POLICY,self.policy_id);doc.flags.ignore_validate=True;doc.status='revoked'
        for action in (lambda:doc.save(ignore_permissions=True),doc.db_update,lambda:doc.db_set('status','revoked'),
                lambda:self.native.delete_doc(POLICY,self.policy_id,ignore_permissions=True),lambda:self.native.rename_doc(POLICY,self.policy_id,str(uuid4()),force=True)):
            with self.assertRaises(self.native.PermissionError):action()
        history=self.native.get_doc(POLICY_REVISION,revision_key(POLICY,self.policy_id,1));history.flags.ignore_validate=True
        with self.assertRaises(self.native.PermissionError):history.save(ignore_permissions=True)
        self.assertEqual(self.native.db.get_value(POLICY,self.policy_id,'status'),'active')
    def test_physical_revision_identity_unique_constraint(self):
        self.write()
        key=revision_key(POLICY,self.policy_id,1)
        point='policy_unique_probe';self.native.db.savepoint(point)
        with self.assertRaises(Exception) as caught:
            self.native.db.sql('INSERT INTO `tabHBOS Organization Management Policy Revision` (name,record_key) VALUES (%s,%s)',('synthetic-duplicate-'+uuid4().hex,key))
        self.assertTrue(self.native.db.is_unique_key_violation(caught.exception))
        self.native.db.rollback(save_point=point)
        self.assertEqual(self.native.db.count(POLICY_REVISION),1)
    def test_disabled_source_blocks_active_policy_but_revocation_remains_possible(self):
        self.write();self.native.db.sql('UPDATE `tabDepartment` SET disabled=1,modified=NOW(6) WHERE name=%s',(self.department,))
        self.assert_code('DISABLED_ORGANIZATION',self.load)
        self.write(replace(self.active,status='revoked',revision=2,authority_generation=2),1,pins=False)
        self.assertEqual(self.load()[0].status,'revoked')
    def test_revoke_first_overrides_established_repeatable_read_snapshot(self):
        self.write();self.native.db.commit()
        self.assertEqual(self.native.db.sql('SELECT status FROM `tabHBOS Organization Management Policy` WHERE name=%s',(self.policy_id,))[0][0],'active')
        revoked=replace(self.active,status='revoked',revision=2,authority_generation=2)
        self.external(lambda f,repo:self.write(revoked,1,repo=repo,pins=False))
        self.assertEqual(self.native.db.sql('SELECT status FROM `tabHBOS Organization Management Policy` WHERE name=%s',(self.policy_id,))[0][0],'active')
        self.assert_code('RELATION_TRANSACTION_RETRY_REQUIRED',self.load)
        self.native.db.rollback()
        result=evaluate_management_policy(self.load(),self.context(),enabled=True)
        self.assertFalse(result.matched)
    def test_reader_root_lock_blocks_revoke_then_next_read_refuses(self):
        self.write();self.native.db.commit()
        with self.repo.relations.transaction():
            self.repo.relations.lock_writer();self.assertEqual(self.load()[0].status,'active')
            revoked=replace(self.active,status='revoked',revision=2,authority_generation=2)
            def attempt(f,repo):
                try:self.write(revoked,1,repo=repo,pins=False)
                except Exception as error:
                    current=error
                    while current is not None:
                        if '1205' in str(current):return 'BLOCKED_BY_ROOT'
                        current=current.__cause__
                    raise
                return 'UNEXPECTED_WRITE'
            self.assertEqual(self.external(attempt),'BLOCKED_BY_ROOT')
        self.native.db.commit()
        self.external(lambda f,repo:self.write(revoked,1,repo=repo,pins=False))
        self.assertFalse(evaluate_management_policy(self.load(),self.context(),enabled=True).matched)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=('preflight','prepare','test'),default='preflight')
    parser.add_argument('--expected-database-sha256',required=True)
    parser.add_argument('--backup-stem')
    args=parser.parse_args()
    import frappe
    frappe.init(site=SITE,sites_path='.');frappe.connect()
    try:
        frappe.db.sql('START TRANSACTION READ ONLY')
        report=check_target(frappe,args.expected_database_sha256);report['preflight']=preflight(frappe)
        report['policy_tables_present']=policy_presence(frappe)
        if not all(report['preflight']['tables_present'].values()):raise RuntimeError('RELATION_SCHEMA_REQUIRED')
        if any(frappe.db.count(kind) for kind in KINDS):raise RuntimeError('RELATION_TABLES_NOT_EMPTY')
        if any(frappe.db.count(kind) for kind,present in report['policy_tables_present'].items() if present):raise RuntimeError('POLICY_TABLES_NOT_EMPTY')
        frappe.db.rollback()
        if args.phase=='prepare':
            if any(report['policy_tables_present'].values()):raise RuntimeError('POLICY_SCHEMA_ALREADY_PRESENT')
            report['backup']=verify_backup(frappe,args.backup_stem);before=native_fingerprints(frappe)
            frappe.set_user('Administrator')
            for kind in POLICY_KINDS:frappe.reload_doc('hbos_portal','doctype',kind.lower().replace(' ','_'),force=True)
            frappe.db.commit();report['schema']=policy_schema_check(frappe)
            if native_fingerprints(frappe)!=before:raise RuntimeError('NATIVE_PRESERVATION_FAILED')
            report['native_preservation']='PASS'
        elif args.phase=='test':
            report['schema']=policy_schema_check(frappe);report['relation_schema']=schema_check(frappe)
            before=native_fingerprints(frappe);NativePolicyCases.native=frappe
            suite=unittest.defaultTestLoader.loadTestsFromTestCase(NativePolicyCases)
            names=[test.id().rsplit('.',1)[1] for test in suite]
            result=unittest.TextTestRunner(verbosity=2).run(suite)
            report['tests_run']=result.testsRun;report['test_names']=names;report['test_status']='PASS' if result.wasSuccessful() else 'FAIL'
            report['native_preservation']='PASS' if native_fingerprints(frappe)==before else 'FAIL'
            report['tables_empty']=all(frappe.db.count(kind)==0 for kind in (*KINDS,*POLICY_KINDS))
            report['limits']='Policy store/current-head shared-lock proof only; relation management bridge, HTTP, real approval and business grants NOT_RUN.'
            if not result.wasSuccessful() or not report['tables_empty'] or report['native_preservation']!='PASS':raise SystemExit(1)
        print(json.dumps(report,ensure_ascii=False,default=str))
    finally:frappe.db.rollback();frappe.destroy()


if __name__=='__main__':main()
