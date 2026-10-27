"""Read-only DTO contracts. These mocks do not replace scoped Site/HTTP UAT."""
import json
import types
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from .test_feishu_auth_contract import _fake_whitelist
from .test_account_recovery import Flags as _ExistingProofFlags
from hbos_portal.iam import audit, people, role_access


class Denied(Exception):
    pass


class Invalid(Exception):
    pass


def throw(message, kind=Invalid):
    raise kind(message)


class AuditReadDTOTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.event = dict(name='event-1', actor='manager', subject_type='Employee', subject_name='E1',
                          operation='save_assignment', version=2, result='success', reason='', occurred_at='2026-10-27 10:00:00',
                          before_json=json.dumps({'role_key': 'staff', 'password': 'synthetic-never-return', 'nested': {'token': 'synthetic-never-return'}}),
                          after_json=json.dumps({'role_key': 'clerk', 'changes': [{'scope_ref': 'D1', 'proof': 'synthetic-never-return', 'cookie': 'synthetic-never-return'}]}))
        def sql(query, params=None, **kwargs):
            self.calls.append((query, dict(params) if isinstance(params, dict) else params))
            if 'from `tabEmployee`' in query:
                return [dict(name='E1', user_id='u1')]
            if 'from `tabHBOS IAM App Role`' in query:
                return [types.SimpleNamespace(name='role-1')]
            if 'count(*)' in query:
                return [(1,)]
            return [dict(self.event)]
        self.fake = types.SimpleNamespace(throw=throw, ValidationError=Invalid, PermissionError=Denied, db=types.SimpleNamespace(sql=Mock(side_effect=sql)))
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(audit, 'frappe', self.fake))
        self.require = self.stack.enter_context(patch.object(audit.guards, 'require_capability'))
        self.stack.enter_context(patch.object(audit.guards, 'managed_departments', return_value=['D1']))
        self.stack.enter_context(patch.object(audit.guards, 'platform_root', return_value=False))
        self.roles_enabled = self.stack.enter_context(patch.object(audit.policy, 'enabled_flag', return_value=False))

    def test_filters_apply_after_parenthesized_scope_for_both_count_and_page(self):
        result = audit.list_events(page=2, page_size=10, date_from='2026-10-01', date_to='2026-10-27', operation='save_assignment', result='success')
        self.assertEqual(1, result['total'])
        count_sql, count_params = self.calls[-2]; page_sql, page_params = self.calls[-1]
        predicate = count_sql.split(' where ', 1)[1]
        self.assertIn(') and occurred_at >= %(date_from)s', predicate)
        self.assertIn('date_add(%(date_to)s, interval 1 day)', predicate)
        self.assertIn('operation=%(operation)s and result=%(result)s', predicate)
        self.assertIn(' where ' + predicate + ' order by', page_sql)
        for params in (count_params, page_params):
            self.assertEqual('2026-10-27', params['date_to'])
            self.assertEqual('save_assignment', params['operation'])
            self.assertNotIn('E2', params.values())
        self.assertEqual(10, page_params['offset'])

    def test_filter_values_are_parameters_and_do_not_change_scope(self):
        value = "x' OR 1=1 --"
        audit.list_events(operation=value)
        for sql, params in self.calls[-2:]:
            self.assertNotIn(value, sql)
            self.assertEqual(value, params['operation'])
            self.assertIn('(subject_type=', sql)

    def test_invalid_dates_ranges_and_filter_types_fail_before_database_access(self):
        for args in [dict(date_from='2026-02-30'), dict(date_to='20261027'), dict(date_from='2026-10-28',date_to='2026-10-27'), dict(operation=['x']), dict(result='x\n')]:
            with self.subTest(args=args), self.assertRaises(Invalid):
                audit.list_events(**args)
        self.fake.db.sql.assert_not_called()

    def test_partial_subject_filters_are_rejected_for_root_too(self):
        with patch.object(audit.guards, 'platform_root', return_value=True):
            with self.assertRaises(Invalid): audit.list_events(subject_type='Employee')
            with self.assertRaises(Invalid): audit.list_events(subject_name='E1')

    def test_invalid_subject_types_are_rejected_before_database_access(self):
        for kind, name in [(['Employee'], 'E1'), ('Employee', ['E1']), ('Employee', 'E1\n'), ('Employee', 'x' * 141)]:
            with self.subTest(kind=kind, name=name), self.assertRaises(Invalid):
                audit.list_events(subject_type=kind, subject_name=name)
        self.fake.db.sql.assert_not_called()

    def test_detail_reuses_audit_visibility_and_redacts_nested_secret_keys(self):
        result = audit.get_event('event-1')
        self.assertEqual('staff', result['before']['role_key'])
        self.assertEqual('D1', result['after']['changes'][0]['scope_ref'])
        self.assertNotIn('synthetic-never-return', json.dumps(result))
        self.assertNotIn('before_json', result)
        self.assertNotIn('after_json', result)
        self.require.assert_any_call('iam.audit.read')

    def test_detail_denies_an_employee_outside_managed_departments(self):
        self.event['subject_name'] = 'E2'
        with self.assertRaises(Denied): audit.get_event('event-1')
        self.assertEqual(2, len(self.calls))  # event + authorized-subject resolution only

    def test_people_read_does_not_authorize_audit_and_denial_precedes_database(self):
        self.require.side_effect = Denied('audit capability missing')
        with self.assertRaises(Denied): audit.get_event('event-1')
        self.fake.db.sql.assert_not_called()

    def test_role_detail_rechecks_every_management_company_and_role_read(self):
        self.roles_enabled.return_value = True
        self.event.update(subject_type=role_access.ROLE, subject_name='role-1')
        def require(cap, **kwargs):
            if kwargs.get('company') == 'C2': raise Denied('company outside delegation')
        self.require.side_effect = require
        with patch.object(role_access, 'document', return_value=types.SimpleNamespace(app_id='attendance')), patch.object(role_access, 'management_companies', return_value=['C1', 'C2']):
            with self.assertRaises(Denied): audit.get_event('event-1')
        self.require.assert_any_call('iam.roles.read', company='C1', app_id='attendance')
        self.require.assert_any_call('iam.audit.read', company='C2')

    def test_unknown_and_malformed_detail_fail_without_returning_raw_content(self):
        self.fake.db.sql.return_value = []
        self.fake.db.sql.side_effect = None
        with self.assertRaises(Denied): audit.get_event('unknown')
        for name in ['', None, ['event-1'], 'x' * 141]:
            with self.subTest(name=name), self.assertRaises(Denied): audit.get_event(name)

    def test_corrupt_snapshot_has_no_partial_detail_response(self):
        self.event['before_json'] = '{not-json'
        with self.assertRaises(Invalid): audit.get_event('event-1')


class OwnEmployeeDTOTest(unittest.TestCase):
    def test_position_comes_only_from_current_users_resolved_employee(self):
        employee = types.SimpleNamespace(name='E1', employee_number='00101', department='D1', designation='合成检验员')
        with patch.object(people.policy, 'get_current_user', return_value='current-user'), patch.object(people.policy, 'resolve_employee', return_value=employee) as resolve, patch.object(people.temporary_passwords, 'status', return_value={'pending': False}):
            result = people.get_my_employee_status()
        resolve.assert_called_once_with('current-user', required=False)
        self.assertEqual('合成检验员', result['position'])
        self.assertEqual('00101', result['employee_number'])
        self.assertEqual('E1', result['employee_id'])

    def test_unlinked_and_conflicted_identity_do_not_expose_position(self):
        fake = types.SimpleNamespace(PermissionError=Denied)
        for value, status in [(None, 'unlinked'), (Denied('conflict'), 'conflict')]:
            with self.subTest(status=status), patch.object(people, 'frappe', fake), patch.object(people.policy, 'get_current_user', return_value='current-user'), patch.object(people.policy, 'resolve_employee', side_effect=value if isinstance(value, Exception) else None, return_value=value), patch.object(people.temporary_passwords, 'status', return_value={'pending': False}):
                result = people.get_my_employee_status()
                self.assertEqual(status, result['status'])
                self.assertIsNone(result['position'])
