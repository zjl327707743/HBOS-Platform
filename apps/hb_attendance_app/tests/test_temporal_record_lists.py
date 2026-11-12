import ast
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

class Row(dict):
    __getattr__=dict.get

class TemporalRecordListTest(unittest.TestCase):
    def select(self,key,start,end,department='D-A',references=''):
        from hb_attendance_app.hbos_attendance.portal import role_scope
        employee=Row(name='EMP-A',department='D-A',company='C-A',creation='2026-10-01 00:00:00')
        roster=role_scope.HistoricalEmployees();roster.append(employee)
        metadata=Row(name='RECORD-A',employee='EMP-A',department=department,event_start=start,event_end=end,overtime_dates=references)
        queries=[]
        def sql(query,*args,**kwargs):
            queries.append(query)
            return [] if 'tabVersion' in query else [metadata]
        fake=types.SimpleNamespace(conf={'hbos_iam_role_native_clock_zone':'Asia/Shanghai'},db=types.SimpleNamespace(sql=sql,get_value=lambda *a,**k:'C-A'),get_meta=lambda _:Row(track_changes=True))
        fake_utils=types.SimpleNamespace(get_datetime=lambda value:datetime.fromisoformat(value) if isinstance(value,str) else value,get_system_timezone=lambda:'Asia/Shanghai')
        source=Path(__file__).parents[1]/'hb_attendance_app/hbos_attendance/portal/record_lists.py'
        nodes=ast.parse(source.read_text()).body
        specs=next(node for node in nodes if isinstance(node,ast.Assign))
        helper=next(node for node in nodes if isinstance(node,ast.FunctionDef) and node.name=='approved_sources')
        function=next(node for node in nodes if isinstance(node,ast.FunctionDef) and node.name=='selection')
        namespace=dict(frappe=fake,role_scope=role_scope,personal=types.SimpleNamespace(bounded_request=lambda *a:(datetime(2026,10,14).date(),datetime(2026,10,14).date(),1,20)),_clean_filters=lambda _: {},datetime=datetime,time=__import__('datetime').time)
        exec(compile(ast.Module(body=[specs,helper,function],type_ignores=[]),str(source),'exec'),namespace)
        with patch.object(role_scope,'frappe',fake),patch.object(role_scope,'context',return_value=dict(departments=['D-A'],scope_label='D-A')),patch.object(role_scope,'historical_employees',return_value=roster),patch.dict(sys.modules,{'frappe.utils':fake_utils}):
            result=namespace['selection'](key,{'doctype':'SOURCE','filters':[]},None)
        self.assertTrue(all('event_start' in query or 'tabVersion' in query for query in queries))
        return result

    def test_full_event_interval_is_proved_before_exposing_a_record_that_overlaps_the_query(self):
        result=self.select('feishu-leave','2026-09-30','2026-10-14')
        self.assertEqual(result['filters']['name'],['in',['']])
        self.assertFalse(result['coverage']['complete'])
        proved=self.select('feishu-leave','2026-10-13','2026-10-14')
        self.assertEqual(proved['filters']['name'],['in',['RECORD-A']])

    def test_declared_department_conflict_is_not_silently_relabelled(self):
        result=self.select('feishu-overtime','2026-10-14 18:00:00','2026-10-14 20:00:00','D-B')
        self.assertFalse(result['coverage']['complete'])
        self.assertEqual(result['filters']['name'],['in',['']])

    def test_rest_leave_requires_the_referenced_overtime_day_to_have_proven_attribution(self):
        result=self.select('feishu-rest-leave','2026-10-14','2026-10-14',references='2026-09-30')
        self.assertFalse(result['coverage']['complete'])
        proved=self.select('feishu-rest-leave','2026-10-14','2026-10-14',references='2026-10-13')
        self.assertEqual(proved['filters']['name'],['in',['RECORD-A']])
