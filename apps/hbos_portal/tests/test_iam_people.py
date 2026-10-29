from __future__ import annotations

import types
import unittest
from unittest.mock import Mock, patch

from .test_feishu_auth_contract import _fake_whitelist
from .test_account_recovery import Flags as _ExistingProofFlags
from hbos_portal.iam import people


class Rejected(Exception):
    pass


def reject(message, *args):
    raise Rejected(message)


class EmployeeLifecycleContractTest(unittest.TestCase):
    def fake(self):
        return types.SimpleNamespace(local=types.SimpleNamespace(response={}), throw=reject, ValidationError=Rejected)

    def test_explicit_ownership_keeps_leading_zeros_and_never_uses_name(self):
        employee = types.SimpleNamespace(employee_number='00101', company='Company A', employee_name='同名')
        good = dict(employee_number='00101', company='Company A', account_user_id='user@example.test', reference='企业人事核验凭据编号及确认来源')
        with patch.object(people, 'frappe', self.fake()):
            people.check_evidence(employee, 'user@example.test', good)
            for key, value in [('employee_number', 101), ('employee_number', '101'), ('company', 'Company B'), ('account_user_id', 'other@example.test'), ('reference', '已核验')]:
                with self.subTest(key=key), self.assertRaises(Rejected):
                    people.check_evidence(employee, 'user@example.test', dict(good, **{key: value}))
            with self.assertRaises(Rejected):
                people.check_evidence(employee, 'user@example.test', dict(name='同名', confirmed=True))

    def test_person_version_includes_user_and_password_generation(self):
        employee = {'name': 'EMP-1', 'modified': 'v1', 'user_id': 'u'}
        user = {'modified': 'u1', 'enabled': 1, 'hbos_password_generation': 1}
        first = people.person_version(employee, user)
        self.assertNotEqual(first, people.person_version(employee, dict(user, hbos_password_generation=2)))
        self.assertNotEqual(first, people.person_version(employee, dict(user, enabled=0)))

    def test_new_employee_rejects_account_fields_and_no_fake_dates(self):
        with patch.object(people, 'frappe', self.fake()):
            for fields in [{'user_id': 'someone'}, {'date_of_birth': '2000-01-01', 'create_user_automatically': 1}]:
                with self.assertRaises(Rejected): people.create_employee(fields, 'v', 'request-1')

    def test_scoped_list_count_and_page_share_department_predicate(self):
        calls = []
        def query(sql, values, **kwargs):
            calls.append((sql, values)); return [(0,)] if 'count(*)' in sql else []
        fake = self.fake(); fake.db = types.SimpleNamespace(sql=query)
        with patch.object(people, 'frappe', fake), patch.object(people.guards, 'require_capability'), patch.object(people.guards, 'managed_departments', return_value=['Dept A']):
            result = people.list_people(page=2, page_size=10, search='001', account_status='active')
            self.assertEqual(0, result['total'])
            self.assertEqual(2, len(calls))
            for sql, values in calls:
                self.assertIn('e.department in %(departments)s', sql)
                self.assertEqual(('Dept A',), values['departments'])
                self.assertNotIn('Attendance', sql); self.assertNotIn('Checkin', sql)
            self.assertIn('limit %(limit)s offset %(start)s', calls[1][0])

    def test_native_link_rejects_manager_role_growth_and_desk_promotion(self):
        before = {'roles': [], 'user_type': 'Website User'}
        with patch.object(people, 'frappe', self.fake()), patch.object(people, 'side_effect_snapshot', return_value={'roles': ['HR Manager'], 'user_type': 'System User'}):
            with self.assertRaises(Rejected): people._check_side_effects('u', before)
        with patch.object(people, 'frappe', self.fake()), patch.object(people, 'side_effect_snapshot', return_value={'roles': ['Employee'], 'user_type': 'System User'}):
            with self.assertRaises(Rejected): people._check_side_effects('u', before)

    def test_native_user_save_keeps_managed_website_user_out_of_desk(self):
        class Row(dict):
            __getattr__ = dict.get
            __setattr__ = dict.__setitem__
        before = Row(user_type='Website User', enabled=0, roles=[])
        doc = Row(name='u', user_type='System User', enabled=1, roles=[Row(role='Employee')])
        doc.get_doc_before_save = lambda: before
        fake = self.fake()
        fake.conf = {'hbos_iam_enabled': 1}; fake.flags = {}; fake.db = types.SimpleNamespace(set_value=Mock()); fake.clear_cache = Mock()
        with patch.object(people, 'frappe', fake), patch.object(people.guards, '_managed_user', return_value=True):
            people.on_native_user_update(doc)
            self.assertEqual('Website User', doc.user_type)
            self.assertEqual(0, doc.enabled)
            fake.db.set_value.assert_called_once_with('User', 'u', {'user_type': 'Website User', 'enabled': 0}, update_modified=False)
            fake.clear_cache.assert_called_once_with(user='u')
            fake.db.set_value.reset_mock()
            before.user_type = 'System User'; doc.user_type = 'System User'
            people.on_native_user_update(doc)
            fake.db.set_value.assert_not_called()  # existing business types retained


def native_link_side_effect_check(employee_id, user_id):
    """Explicit C02 helper: only isolated synthetic Site, no automatic execution."""
    import frappe
    if not frappe.conf.get('hbos_iam_test_site') or frappe.session.user != 'Administrator':
        frappe.throw('Only the owned isolated synthetic Site may run this check.', frappe.PermissionError)
    before = people.side_effect_snapshot(user_id)
    employee = frappe.get_doc('Employee', employee_id)
    frappe.db.savepoint('iam_native_link_check')
    try:
        effect = people.link_native_employee(employee, user_id)
        if effect['after']['user_type'] == 'System User' and before['user_type'] != 'System User':
            raise AssertionError('unexpected Desk promotion')
        if set(effect['after']['roles']) - set(before['roles']) - {'Employee', 'Employee Self Service'}:
            raise AssertionError('unexpected role growth')
        return {'employee_key_preserved': employee.name == employee_id, 'before': before, 'after': effect['after']}
    finally:
        frappe.db.rollback(save_point='iam_native_link_check')
