import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


class ShiftOverviewEmptyDepartmentTest(unittest.TestCase):
    def test_legacy_hr_overview_omits_missing_department_without_crashing_named_department_sort(self):
        path=Path(__file__).parents[1]/'hb_attendance_app/hbos_attendance/page/hbos_shift_management/shift_management_data.py'
        function=next(node for node in ast.parse(path.read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='get_shift_overview')
        function.decorator_list=[]
        def get_all(doctype,**kwargs):
            return [SimpleNamespace(department=None),SimpleNamespace(department='D1')] if doctype=='Employee' else []
        fake=SimpleNamespace(db=SimpleNamespace(get_all=get_all),utils=SimpleNamespace(nowtime=lambda:'12:00:00',today=lambda:'2026-10-19'),get_meta=lambda _:SimpleNamespace(get_field=lambda _:SimpleNamespace(options='行政班')))
        namespace=dict(frappe=fake,_require_hr_read=lambda:None,_fmt_rule=lambda row:row,_group_rule_versions=lambda rows:{},_bindable_family_rows=lambda *args:[],_to_secs=lambda _:0)
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),'exec'),namespace)
        result=namespace['get_shift_overview']()
        self.assertEqual(result['departments'],['D1'])
        self.assertEqual(result['dept_employee_count'],{'D1':1})
