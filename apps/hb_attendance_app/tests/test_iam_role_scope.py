import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch

sys.modules.setdefault('frappe',types.SimpleNamespace())
from hb_attendance_app.hbos_attendance.portal import role_scope


class Attr(dict):
    __getattr__=dict.get


class TemporalAttributionTest(unittest.TestCase):
    def setUp(self):
        self.versions=[]
        self.fake=types.SimpleNamespace(conf={'hbos_iam_role_native_clock_zone':'Asia/Shanghai'},get_meta=lambda _:Attr(track_changes=1),db=Attr(sql=lambda *a,**k:self.versions))
        self.patch=patch.object(role_scope,'frappe',self.fake);self.patch.start();self.addCleanup(self.patch.stop)
        self.timezone='Asia/Shanghai'
        self.utils=patch.dict(sys.modules,{'frappe.utils':types.SimpleNamespace(get_datetime=lambda value:datetime.fromisoformat(value) if isinstance(value,str) else value,get_system_timezone=lambda:self.timezone)})
        self.utils.start();self.addCleanup(self.utils.stop)
        self.employee=Attr(name='synthetic',creation='2026-10-01 00:00:00',department='D2',company='C')
        self.versions=[Attr(creation='2026-10-18 12:00:00',data='{"changed":[["department","D1","D2"]]}')]

    def period(self,start,end):
        return role_scope._historical_department(self.employee,datetime.fromisoformat(start),datetime.fromisoformat(end))

    def test_tracked_transfer_does_not_move_old_history_to_current_department(self):
        self.assertEqual(self.period('2026-10-14 00:00:00','2026-10-14 23:59:59'),('D1','C'))
        self.assertEqual(self.period('2026-10-19 00:00:00','2026-10-19 23:59:59'),('D2','C'))

    def test_period_crossing_transfer_is_not_silently_relabelled(self):
        self.assertIsNone(self.period('2026-10-14 00:00:00','2026-10-19 23:59:59'))

    def test_history_before_native_employee_creation_or_missing_tracking_is_unproved(self):
        self.employee.creation='2026-10-15 00:00:00'
        self.assertIsNone(self.period('2026-10-14 00:00:00','2026-10-14 23:59:59'))
        self.fake.get_meta=lambda _:Attr(track_changes=0)
        self.assertIsNone(self.period('2026-10-19 00:00:00','2026-10-19 23:59:59'))

    def test_inconsistent_version_chain_does_not_grant_old_history(self):
        self.employee.department='D3'
        self.assertIsNone(self.period('2026-10-14 00:00:00','2026-10-14 23:59:59'))

    def test_native_clock_is_compared_to_business_midnight_as_an_instant(self):
        self.fake.conf['hbos_iam_role_native_clock_zone']='Asia/Kolkata'
        self.timezone='Asia/Kolkata'
        self.versions=[Attr(creation='2026-10-18 23:30:00',data='{"changed":[["department","D1","D2"]]}')]
        self.assertEqual(self.period('2026-10-18 00:00:00','2026-10-18 23:59:59'),('D1','C'))
        self.assertIsNone(self.period('2026-10-19 00:00:00','2026-10-19 23:59:59'))

    def test_unplanned_site_timezone_change_refuses_history(self):
        self.timezone='Asia/Kolkata'
        self.assertIsNone(self.period('2026-10-19 00:00:00','2026-10-19 23:59:59'))

    def test_scoped_report_context_is_private_fixed_and_always_reset(self):
        params={}
        self.assertIsNone(role_scope.report_predicate('a',params))
        with self.assertRaises(RuntimeError):
            with role_scope.report_execution('results',[Attr(name='SYNTHETIC')]):
                self.assertEqual(role_scope.report_predicate('a',params),'a.employee in %(iam_employees)s')
                self.assertEqual(params['iam_employees'],('SYNTHETIC',))
                raise RuntimeError('executor failed')
        self.assertIsNone(role_scope.report_predicate('a',{}))
        with self.assertRaises(ValueError):
            with role_scope.report_execution('staging',[]):pass
