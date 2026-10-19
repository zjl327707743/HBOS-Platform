"""Role policy invariants; real transactions are exercised on the isolated Site."""
import unittest
from unittest.mock import patch

from tests import test_iam_policy as base
from tests.test_iam_policy import Attr, PermissionDenied, Invalid, rule
from hbos_portal.iam import role_access as roles


class RolePolicyTest(unittest.TestCase):
    store = base.IAMPolicyTest.store
    def setUp(self):
        base.IAMPolicyTest.setUp(self)
        self.stack.enter_context(patch.object(roles, 'frappe', self.fake))
        self.fake.conf.hbos_iam_roles_enabled = 1
        self.employee = self.db.employees[0]

    def resolved(self, key='clerk'):
        return dict(reason='', role=key, release='release-1', source_mode='direct',
                    features=[dict(operation_id='attendance.read',scope_binding='SELF'),
                              dict(operation_id='attendance.department.records.read',scope_binding='RESPONSIBLE_DEPARTMENTS')],
                    responsibilities=[dict(scope_type='DEPARTMENT',scope_ref='D1',include_descendants=0)])

    def test_self_and_department_actions_stay_paired(self):
        context=self.resolved()
        for op,kind,ref,expected in [('attendance.read','SELF','',True),('attendance.read','DEPARTMENT','D1',False),
                ('attendance.department.records.read','SELF','',False),('attendance.department.records.read','DEPARTMENT','D1',True),
                ('attendance.department.records.read','DEPARTMENT','D2',False),('attendance.company.read','COMPANY','C',False)]:
            with self.subTest(op=op,kind=kind,ref=ref):
                self.assertEqual(roles.decide(self.employee,op,kind,ref,resolved=context)['allowed'],expected)

    def test_legacy_deny_suspension_and_expiry_are_not_removed_by_role(self):
        context=self.resolved()
        for rows,enabled in [([rule('attendance.read',effect='deny')],1),([],0),
                             ([rule('attendance.read',valid_until='2020-01-01')],1)]:
            with self.subTest(rows=rows,enabled=enabled):
                self.store('User','a',rows,enabled=enabled)
                self.assertFalse(roles.decide(self.employee,'attendance.read','SELF','',resolved=context)['allowed'])

    def test_unknown_operations_duplicate_rows_and_self_scope_escalation_fail(self):
        allowed=dict(operation_id='attendance.read',scope_binding='SELF')
        for rows in [[dict(operation_id='unknown',scope_binding='SELF')],[allowed,allowed],
                     [dict(operation_id='attendance.read',scope_binding='RESPONSIBLE_COMPANIES')],
                     [dict(operation_id='attendance.company.read',scope_binding='RESPONSIBLE_COMPANIES')]]:
            with self.subTest(rows=rows),self.assertRaises((PermissionDenied,Invalid)):
                roles.normalize_features(rows,'staff',publishing=True)
        self.assertEqual(roles.normalize_features([allowed],'staff',publishing=True),[allowed])

    def test_unintegrated_visible_features_cannot_publish(self):
        # The finite V1 list may be fully integrated. A future executor still
        # remains visible and unpublishable until its integration bit changes.
        key='attendance.import.execute'
        label,group,scope,_=roles.OPERATIONS[key]
        with patch.dict(roles.OPERATIONS,{key:(label,group,scope,False)}):
            row=next(row for row in roles.registry('admin') if row['operation_id']==key)
            self.assertFalse(row['integrated'])
            with self.assertRaises(PermissionDenied):
                roles.normalize_features([roles.feature_dict(row)],'admin',publishing=True)

    def test_draft_is_not_an_authorization_source_and_revocation_is_live(self):
        context=self.resolved()
        self.assertTrue(roles.decide(self.employee,'attendance.read','SELF','',resolved=context)['allowed'])
        context['draft_features']=[]
        self.assertTrue(roles.decide(self.employee,'attendance.read','SELF','',resolved=context)['allowed'])
        context.update(features=[],release='release-2')
        self.assertFalse(roles.decide(self.employee,'attendance.read','SELF','',resolved=context)['allowed'])

    def test_role_opt_out_uses_exact_legacy_evaluator(self):
        self.fake.conf.hbos_iam_roles_enabled=0
        self.assertIsNone(roles.resolve(self.employee))
        self.assertTrue(roles.policy.evaluate('a','attendance','attendance.read','SELF','')['allowed'])

    def test_company_binding_only_expands_to_that_companys_department(self):
        context=self.resolved('admin')
        context['features']=[dict(operation_id='attendance.company.read',scope_binding='RESPONSIBLE_COMPANIES')]
        context['responsibilities']=[dict(scope_type='COMPANY',scope_ref='C',include_descendants=0)]
        self.assertTrue(roles.decide(self.employee,'attendance.company.read','DEPARTMENT','D1',resolved=context)['allowed'])
        self.assertFalse(roles.decide(self.employee,'attendance.company.read','COMPANY','OTHER',resolved=context)['allowed'])

    def test_unset_role_association_preserves_old_personal_rule_source(self):
        self.store('User','a',[rule('app.enter'),rule('attendance.read')])
        with patch.object(roles,'require_available'),patch.object(roles,'assignments',return_value=[]):
            self.assertTrue(roles.preserves_legacy_personal(self.employee))
            self.assertIsNone(roles.resolve(self.employee))

    def test_unmanaged_native_HR_is_not_silently_migrated_by_a_department_default(self):
        self.db.policies.clear()
        original=self.db.sql
        self.db.sql=lambda query,*a,**k:[Attr(role='HR User')] if 'tabHas Role' in query else original(query,*a,**k)
        with patch.object(roles,'require_available'),patch.object(roles,'assignments',return_value=[]):
            self.assertTrue(roles.preserves_legacy_personal(self.employee))
            self.assertIsNone(roles.resolve(self.employee))
