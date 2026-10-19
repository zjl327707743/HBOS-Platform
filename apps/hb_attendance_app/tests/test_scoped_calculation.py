"""Exercise the actual existing calculator with a recording bounded database."""
import ast
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from hb_attendance_app.hbos_attendance import policy_registry, rotation_schedule


class Row(dict):
    __getattr__=dict.get


class ScopedCalculationTest(unittest.TestCase):
    def calculate(self, protected):
        source=Path(__file__).parents[1]/'hb_attendance_app/hbos_attendance/api.py'
        function=next(node for node in ast.parse(source.read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='_regenerate_attendance_impl')
        self.reads=[];self.sql=[];self.generated=[]
        class DB:
            def get_all(inner,doctype,filters=None,**kwargs):
                self.reads.append((doctype,filters))
                return [Row(name='EMP-A',employee_number='A',department='D-A')] if doctype=='Employee' else []
            def sql(inner,query,args=None,**kwargs):
                self.sql.append((query,args))
                if query.startswith('select employee,attendance_date') and protected:
                    return [Row(employee='EMP-A',attendance_date='2026-10-15')]
                return []
        import datetime
        namespace=dict(frappe=SimpleNamespace(db=DB()),verified_rest_dates=lambda **kwargs:{},ADMIN_NUMS=set(),SAFETY_NUMS=set(),FOOD_NUMS=set(),LATE_EXEMPT_NUMS=set(),FOUR_SHIFT_NUMS=set(),EXEMPT_NUMS=set(),_is_exempt=lambda _:False)
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
        def generate(end,**kwargs):self.generated.append((end,kwargs))
        with patch('hb_attendance_app.hbos_attendance.rotation_schedule.generate_rotation_schedule',side_effect=generate):
            namespace['_regenerate_attendance_impl']('2026-10-14','2026-10-16',employee_scope=[Row(name='EMP-A',company='C-A',department='D-A')])

    def test_every_source_and_delete_is_employee_bounded_and_schedule_dates_stay_requested(self):
        self.calculate(False)
        for doctype,filters in self.reads:
            key={'Employee':'name','HBOS Shift Rule':'department'}.get(doctype,'employee')
            self.assertEqual(filters[key],['in',['D-A'] if key=='department' else ['EMP-A']])
        for query,args in self.sql:
            if 'Employee Checkin' in query:self.assertIn('ec.employee in %s',query)
            if query.startswith('DELETE'):
                self.assertIn('employee in %s',query)
                self.assertIn('modified is null',query)
                self.assertEqual(args,('2026-10-14','2026-10-16',('EMP-A',)))
        self.assertEqual(self.generated,[('2026-10-16',dict(employees=['EMP-A'],start_date='2026-10-14'))])

    def test_generated_rows_record_company_and_a_protected_native_day_is_never_replaced(self):
        self.calculate(False)
        inserted=[(query,args) for query,args in self.sql if query.startswith('INSERT')]
        self.assertTrue(inserted)
        self.assertTrue(all('company)' in query for query,args in inserted))
        self.assertTrue(all(args[-1]=='C-A' for query,args in inserted))
        self.calculate(True)
        inserted=[args for query,args in self.sql if query.startswith('INSERT')]
        self.assertFalse(any('2026-10-15' in args for args in inserted))

    def test_policy_lookup_context_resets_even_when_the_calculation_fails(self):
        self.assertIsNone(policy_registry._employee_bound.get())
        with self.assertRaises(RuntimeError):
            with policy_registry.employee_bound(['EMP-A']):
                self.assertEqual(policy_registry._employee_bound.get(),('EMP-A',))
                raise RuntimeError('native failure')
        self.assertIsNone(policy_registry._employee_bound.get())
