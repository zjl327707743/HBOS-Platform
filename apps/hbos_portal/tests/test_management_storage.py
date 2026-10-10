"""Policy storage/security contracts; native database acceptance is separate."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from hbos_portal.authorization.errors import ContractError
from hbos_portal.organization.frappe_management_repository import (
    FrappeManagementPolicyRepository, LockedManagementPolicyLoader, ManagementPolicyStore, validate_policy_sources,
)
from hbos_portal.organization.frappe_repository import FrappeRelationRepository
from hbos_portal.organization.management_policy import management_policy_digest, parse_management_policy
from hbos_portal.organization.management_storage import (
    POLICY, POLICY_PROVIDER, POLICY_REVISION, PolicyApprovalPin, PinnedPolicyApprovalVerifier,
    policy_data, policy_from_record, policy_record, stored_time, validate_policy_record,
)
from hbos_portal.organization.storage_schema import canonical_json, digest, revision_key
from hbos_portal.organization.write_guard import _controlled_write, is_controlled_write
from tests.test_management_policy import policy_payload, rule
from tests.test_organization_source_adapter import STAMP, snapshot, sources

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
DB_HASH = hashlib.sha256(b'synthetic-db').hexdigest()
SUBJECT, APPROVER, OPERATOR = 'SYNTHETIC-USER', 'SYNTHETIC-OWNER', 'Administrator'


def policy(*, status='active', revision=1, generation=1, subject=SUBJECT):
    payload = policy_payload(subject_user=subject, status=status, revision=revision, authority_generation=generation,
        rules=[rule(company_id='COMPANY-A', person_scope=dict(source_type='Employee', company_id='COMPANY-A', department_ids=['DEPT-A']))])
    row = parse_management_policy(payload, site_id='synthetic-site', source_provider=POLICY_PROVIDER)
    payload['approval'] = dict(approval_ref='SYNTHETIC-APPROVAL', approved_by=APPROVER,
        approved_at_utc='2026-10-09T00:00:00Z', approved_revision=revision,
        approved_authority_generation=generation, content_digest=management_policy_digest(row))
    return parse_management_policy(payload, site_id='synthetic-site', source_provider=POLICY_PROVIDER)


def pin(row, **changes):
    data = dict(site_id=row.site_id, database_sha256=DB_HASH, policy_id=row.policy_id, revision=row.revision,
        authority_generation=row.authority_generation, subject_user=row.subject_user,
        content_digest=management_policy_digest(row), approval_json=canonical_json(policy_data(row)['approval']), source_ref='SYNTHETIC-OWNER-RECORD')
    data.update(changes)
    return PolicyApprovalPin(**data)


def native_snapshot(rows=None):
    if rows is None:
        rows = sources()
        for user in (APPROVER, OPERATOR):
            rows['User'].append(dict(name=user, enabled=1, user_type='System User', modified=STAMP))
    return snapshot(rows)


class MemoryPolicyRepository:
    enabled=True
    expected_site='synthetic-site'
    expected_database_sha256=DB_HASH
    def __init__(self):
        self.rows={}; self.versions={}; self.locked=False; self.fail=False
        self.session=types.SimpleNamespace(user=OPERATOR)
        self.relations=self
    @contextmanager
    def transaction(self):
        before=deepcopy((self.rows,self.versions))
        try: yield
        except BaseException:
            self.rows,self.versions=before
            raise
        finally: self.locked=False
    def lock_writer(self): self.locked=True
    def native(self):
        if not self.locked: raise ContractError('SOURCE_TRANSACTION_REQUIRED','policy')
        return types.SimpleNamespace(session=self.session)
    def get_current(self,key): return self.rows.get(key)
    def current_for_subject(self,subject): return tuple(row for row in self.rows.values() if row.subject_user==subject)
    def save(self,row,**options):
        self.rows[row.policy_id]=row
        if self.fail: raise RuntimeError('synthetic failure after head write')
        self.versions[row.policy_id,row.revision]=(row,options)


class PolicyContractTests(unittest.TestCase):
    def assert_code(self,code,action):
        with self.assertRaises(ContractError) as caught: action()
        self.assertEqual(caught.exception.code,code)

    def test_canonical_policy_record_roundtrip_and_precise_utc(self):
        row=policy(); record=policy_record(row)
        self.assertEqual(policy_from_record(row.policy_id,record.get),row)
        self.assertTrue(record['valid_from_utc'].endswith('.000000'))
        self.assertEqual(record['content_digest'],management_policy_digest(row))

    def test_metadata_snapshot_and_provider_tampering_rejected(self):
        row=policy(); record=policy_record(row)
        for key,value in (('site_id','other'),('subject_user','other'),('status','revoked'),('revision',True),('content_digest','0'*64),('policy_json','{}')):
            changed={**record,key:value}
            with self.subTest(key=key),self.assertRaises(ContractError): policy_from_record(row.policy_id,changed.get)
        self.assert_code('POLICY_PROVIDER_MISMATCH',lambda:policy_record(replace(row,source_provider='other')))
        self.assert_code('POLICY_STORAGE_MISMATCH',lambda:policy_from_record('other',record.get))

    def test_raw_approval_strings_cannot_replace_preverified_pin(self):
        row=policy()
        self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:PinnedPolicyApprovalVerifier().verify(row,database_sha256=DB_HASH,now_utc=NOW))
        verifier=PinnedPolicyApprovalVerifier([pin(row)])
        self.assertEqual(verifier.verify(row,database_sha256=DB_HASH,now_utc=NOW),'SYNTHETIC-OWNER-RECORD')

    def test_approval_pin_binds_site_database_revision_generation_and_full_content(self):
        row=policy()
        for key,value in (('site_id','other'),('database_sha256','0'*64),('revision',2),('revision',True),('authority_generation',2),('subject_user','other'),('content_digest','0'*64),('approval_json','{}'),('source_ref','')):
            verifier=PinnedPolicyApprovalVerifier([pin(row,**{key:value})])
            with self.subTest(key=key): self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:verifier.verify(row,database_sha256=DB_HASH,now_utc=NOW))

    def test_duplicate_or_mismatched_approval_pins_do_not_pass(self):
        row=policy()
        self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:PinnedPolicyApprovalVerifier([pin(row),pin(row)]).verify(row,database_sha256=DB_HASH,now_utc=NOW))
        changed=replace(row,approval=replace(row.approval,approved_by=SUBJECT))
        self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:PinnedPolicyApprovalVerifier([pin(changed)]).verify(changed,database_sha256=DB_HASH,now_utc=NOW))

    def test_source_validation_checks_subject_approver_and_exact_organization(self):
        row=policy(); validate_policy_sources(row,native_snapshot())
        for target in (SUBJECT,APPROVER):
            rows=sources()
            for user in (APPROVER,OPERATOR): rows['User'].append(dict(name=user,enabled=1,user_type='System User',modified=STAMP))
            next(user for user in rows['User'] if user['name']==target)['enabled']=0
            self.assert_code('POLICY_SOURCE_UNAVAILABLE',lambda:validate_policy_sources(row,native_snapshot(rows)))
        rows=sources();rows['Department'][1]['disabled']=1
        # Include users so the organization, rather than the approver, is tested.
        expanded=deepcopy(rows)
        for user in (APPROVER,OPERATOR): expanded['User'].append(dict(name=user,enabled=1,user_type='System User',modified=STAMP))
        self.assert_code('DISABLED_ORGANIZATION',lambda:validate_policy_sources(row,native_snapshot(expanded)))


class PolicyStoreTests(unittest.TestCase):
    assert_code = PolicyContractTests.assert_code
    def setUp(self):
        self.repo=MemoryPolicyRepository()
        self.row=policy()
        self.verifier=PinnedPolicyApprovalVerifier([pin(self.row)])
        self.patch=patch('hbos_portal.organization.frappe_management_repository.FrappeLockedSourceLoader',return_value=lambda:native_snapshot())
        self.patch.start()
    def tearDown(self): self.patch.stop()
    def store(self,**options):
        args=dict(clock=lambda:NOW,operator_users=[OPERATOR],approval_verifier=self.verifier,enabled=True);args.update(options)
        return ManagementPolicyStore(self.repo,**args)
    def write(self,row=None,expected=0,**options):
        return self.store(**options).write(row or self.row,expected_revision=expected,reason='合成政策运维验收')

    def test_default_closed_before_dependency_access(self):
        self.assert_code('POLICY_WRITES_DISABLED',lambda:self.write(enabled=False))
        self.assertEqual(self.repo.rows,{})
    def test_administrator_requires_explicit_operator_and_verified_pin(self):
        self.assert_code('POLICY_OPERATOR_DENIED',lambda:self.write(operator_users=[]))
        self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:self.write(approval_verifier=None))
        self.assertEqual(self.repo.rows,{})
    def test_operator_configuration_cannot_be_a_string_or_guest_list(self):
        for value in ('Administrator',{'Administrator':True},[True],['Guest'],[' Administrator']):
            self.assert_code('INVALID_POLICY_OPERATORS',lambda:self.store(operator_users=value))
    def test_disabled_native_operator_cannot_write_even_with_valid_pin(self):
        rows=sources()
        for user in (APPROVER,OPERATOR): rows['User'].append(dict(name=user,enabled=int(user!=OPERATOR),user_type='System User',modified=STAMP))
        with patch('hbos_portal.organization.frappe_management_repository.FrappeLockedSourceLoader',return_value=lambda:native_snapshot(rows)):
            self.assert_code('POLICY_OPERATOR_DENIED',lambda:self.write())
        self.assertEqual(self.repo.rows,{})
    def test_write_is_transaction_pending_and_records_operator_reason_source(self):
        result=self.write()
        self.assertTrue(result.transaction_pending);self.assertEqual(result.authorization_effect,'none')
        saved,options=self.repo.versions[self.row.policy_id,1]
        self.assertEqual(options['actor'],OPERATOR)
        self.assertEqual(options['approval_source_ref'],'SYNTHETIC-OWNER-RECORD')
        self.assertEqual(len(self.repo.rows),1)
    def test_expected_revision_generation_and_subject_are_checked(self):
        self.write()
        for changed,expected,code in ((policy(revision=2,generation=2),0,'POLICY_REVISION_CONFLICT'),(policy(revision=2,generation=1),1,'POLICY_GENERATION_CONFLICT'),(policy(revision=2,generation=2,subject='other'),1,'POLICY_SUBJECT_IMMUTABLE')):
            self.assert_code(code,lambda:self.write(changed,expected))
        self.assertEqual(self.repo.rows[self.row.policy_id],self.row)
    def test_revoke_preserves_history_but_restore_requires_new_pinned_approval(self):
        self.write();revoked=replace(self.row,status='revoked',revision=2,authority_generation=2)
        self.write(revoked,1,approval_verifier=None)
        self.assertEqual(len(self.repo.versions),2)
        restored=policy(revision=3,generation=3)
        self.assert_code('POLICY_APPROVAL_REQUIRED',lambda:self.write(restored,2))
        self.write(restored,2,approval_verifier=PinnedPolicyApprovalVerifier([pin(restored)]))
        self.assertEqual(len(self.repo.versions),3)
    def test_revoke_still_works_after_policy_source_is_disabled(self):
        self.write()
        rows=sources();rows['User']=[dict(name=OPERATOR,enabled=1,user_type='System User',modified=STAMP)]
        rows['Department'][1]['disabled']=1
        with patch('hbos_portal.organization.frappe_management_repository.FrappeLockedSourceLoader',return_value=lambda:native_snapshot(rows)):
            self.write(replace(self.row,status='revoked',revision=2,authority_generation=2),1,approval_verifier=None)
        self.assertEqual(self.repo.rows[self.row.policy_id].status,'revoked')
    def test_failed_history_write_rolls_back_head(self):
        self.repo.fail=True
        with self.assertRaises(RuntimeError):self.write()
        self.assertEqual(self.repo.rows,{})
    def test_naive_clock_invalid_version_expired_policy_and_site_denied(self):
        self.assert_code('TIMEZONE_REQUIRED',lambda:self.write(clock=lambda:datetime(2026,10,10)))
        self.assert_code('INVALID_VERSION',lambda:self.write(expected=True))
        self.assert_code('POLICY_EXPIRED',lambda:self.write(clock=lambda:datetime(2026,12,1,tzinfo=timezone.utc)))
        self.assert_code('POLICY_SITE_MISMATCH',lambda:self.write(replace(self.row,site_id='other')))
    def test_loader_requires_root_lock_native_session_and_approval(self):
        self.write();loader=LockedManagementPolicyLoader(self.repo,clock=lambda:NOW,approval_verifier=self.verifier,enabled=True)
        self.assert_code('SOURCE_TRANSACTION_REQUIRED',loader)
        with self.repo.transaction():
            self.repo.lock_writer();self.repo.session.user=SUBJECT
            self.assertEqual(loader(),(self.row,))
            self.repo.session.user='Guest';self.assert_code('MANAGEMENT_DENIED',loader)
    def test_loader_never_resurrects_a_revoked_head_and_is_default_closed(self):
        self.write();revoked=replace(self.row,status='revoked',revision=2,authority_generation=2);self.write(revoked,1)
        self.assert_code('POLICY_READS_DISABLED',LockedManagementPolicyLoader(self.repo,clock=lambda:NOW))
        with self.repo.transaction():
            self.repo.lock_writer();self.repo.session.user=SUBJECT
            loader=LockedManagementPolicyLoader(self.repo,clock=lambda:NOW,enabled=True)
            self.assertEqual(loader(),(revoked,))


class NativeRepositoryContractTests(unittest.TestCase):
    def setUp(self):
        self.native=types.SimpleNamespace(local=types.SimpleNamespace(site='synthetic-site'),conf={},db=Mock(),get_doc=Mock())
        self.relations=FrappeRelationRepository(native=self.native,enabled=True)
        self.repo=FrappeManagementPolicyRepository(self.relations,enabled=True,expected_site='synthetic-site',expected_database_sha256=DB_HASH)
        self.row=policy();self.record=policy_record(self.row)
        self.key=revision_key(POLICY,self.row.policy_id,1)
        self.version=dict(record_key=self.key,policy=self.row.policy_id,revision=1,previous_revision=0,snapshot_json=canonical_json(self.record),snapshot_digest=digest(self.record),actor=OPERATOR,reason='合成',approval_source_ref='SYNTHETIC',recorded_at_utc=stored_time(NOW))
        def query(sql,values=None,as_dict=False):
            if sql.startswith('SELECT DATABASE()'):return [('synthetic-db','REPEATABLE-READ')]
            if 'information_schema.tables' in sql:return [('tab'+POLICY,'InnoDB'),('tab'+POLICY_REVISION,'InnoDB')]
            if 'tabHBOS Organization Write Lock' in sql:return [('relations-v1',)]
            if 'tab'+POLICY_REVISION in sql:return [dict(self.version)]
            if 'tab'+POLICY in sql:return [dict(self.record)]
            raise AssertionError(sql)
        self.native.db.sql.side_effect=query
    def locked(self):
        @contextmanager
        def scope():
            with self.relations.transaction():
                self.relations.lock_writer();yield
        return scope()
    def test_repository_requires_enabled_target_and_transaction(self):
        with self.assertRaises(ContractError): FrappeManagementPolicyRepository(self.relations).get_current(self.row.policy_id)
        with self.assertRaises(ContractError):self.repo.get_current(self.row.policy_id)
        with self.locked():
            self.assertEqual(self.repo.get_current(self.row.policy_id),self.row)
            self.repo.expected_database_sha256='0'*64
            with self.assertRaises(ContractError):self.repo.get_current(self.row.policy_id)
    def test_database_isolation_and_engine_cannot_silently_downgrade(self):
        original=self.native.db.sql.side_effect
        for gate in ('database_type','isolation','engine'):
            def query(sql,*args,**kwargs):
                if gate=='isolation' and sql.startswith('SELECT DATABASE()'):return [('synthetic-db','READ-COMMITTED')]
                if gate=='engine' and 'information_schema.tables' in sql:return [('tab'+POLICY,'MyISAM'),('tab'+POLICY_REVISION,'InnoDB')]
                return original(sql,*args,**kwargs)
            self.native.conf={'db_type':'postgres'} if gate=='database_type' else {}
            self.native.db.sql.side_effect=query
            with self.subTest(gate=gate),self.locked(),self.assertRaises(ContractError):self.repo.get_current(self.row.policy_id)
        self.native.conf={};self.native.db.sql.side_effect=original
    def test_subject_query_uses_parameterized_current_heads_and_locked_revision(self):
        with self.locked():self.repo.current_for_subject("x'; DROP TABLE x;--")
        calls=self.native.db.sql.call_args_list
        selects=[call for call in calls if 'subject_user=%s' in call.args[0]]
        self.assertEqual(selects[0].args[1],("x'; DROP TABLE x;--",))
        self.assertIn('ORDER BY name FOR UPDATE',selects[0].args[0]);self.assertNotIn('DROP',selects[0].args[0]);self.assertNotIn("status='active'",selects[0].args[0])
        self.native.db.commit.assert_not_called()
    def test_missing_or_tampered_current_revision_refuses_head(self):
        self.version['snapshot_digest']='0'*64
        with self.locked(),self.assertRaises(ContractError):self.repo.get_current(self.row.policy_id)
    def test_native_schema_has_physical_keys_no_permissions_or_rpc(self):
        base=Path(__file__).resolve().parents[1]/'hbos_portal/hbos_portal/doctype'
        for kind in (POLICY,POLICY_REVISION):
            slug=kind.lower().replace(' ','_');data=json.loads((base/slug/(slug+'.json')).read_text())
            self.assertEqual(data['engine'],'InnoDB');self.assertEqual(data['permissions'],[])
            self.assertEqual(data['autoname'],'field:record_key')
            self.assertEqual(next(field for field in data['fields'] if field['fieldname']=='record_key')['unique'],1)
            self.assertEqual(data['allow_import'],0);self.assertEqual(data['allow_rename'],0)
    def test_locked_capability_expires_at_transaction_end_or_after_site_change(self):
        with self.locked():
            self.assertEqual(self.repo.get_current(self.row.policy_id),self.row)
            self.native.local.site='other-site'
            with self.assertRaises(ContractError):self.repo.get_current(self.row.policy_id)
            self.native.local.site='synthetic-site'
        with self.assertRaises(ContractError):self.repo.get_current(self.row.policy_id)
    def test_active_history_requires_approval_source_audit_reference(self):
        self.version['approval_source_ref']=None
        with self.locked(),self.assertRaises(ContractError):self.repo.get_current(self.row.policy_id)
    def test_policy_controller_flags_partial_write_delete_rename_and_revision_overwrite_denied(self):
        class Document:
            def __init__(self,data):self.__dict__.update(data);self.writes=0
            def get(self,key):return getattr(self,key,None)
            def is_new(self):return True
            def db_insert(self,*args,**kwargs):self.writes+=1
            def db_update(self,*args,**kwargs):self.writes+=1
        def throw(message,error):raise error(message)
        native=types.SimpleNamespace(throw=throw,PermissionError=PermissionError)
        with patch.dict(sys.modules,{'frappe':native,'frappe.model':types.ModuleType('frappe.model'),'frappe.model.document':types.SimpleNamespace(Document=Document)}):
            module=importlib.import_module('hbos_portal.organization.protected_policy_document')
        with patch.object(module,'frappe',native):
            doc=module.ProtectedPolicyDocument(dict(doctype=POLICY,name=self.row.policy_id,**self.record,flags={'ignore_validate':True,'ignore_permissions':True}))
            for method in (doc.validate,doc.db_insert,doc.db_update,doc.db_set,doc.on_trash,doc.before_rename):
                with self.assertRaises(PermissionError):method()
            with _controlled_write(POLICY,self.row.policy_id):doc.db_insert()
            self.assertEqual(doc.writes,1);self.assertFalse(is_controlled_write(POLICY,self.row.policy_id))
            doc=module.ProtectedPolicyDocument(dict(doctype=POLICY_REVISION,name=self.key,**self.version))
            with _controlled_write(POLICY_REVISION,self.key),self.assertRaises(PermissionError):doc.db_update()


if __name__=='__main__':unittest.main()
