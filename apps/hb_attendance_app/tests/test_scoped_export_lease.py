import sys
import types
import unittest
from unittest.mock import patch
from hb_attendance_app.hbos_attendance.portal import export_scope

class ExportLeaseTest(unittest.TestCase):
    def file(self,**changes):
        fields=dict(attached_to_doctype='Report',attached_to_name='月度考勤汇总',owner='A',is_private=1,is_new=lambda:True)
        return types.SimpleNamespace(**(fields|changes))

    def test_a_doc_flag_or_private_file_owner_cannot_replace_a_server_export_lease(self):
        doc=self.file(hbos_export_authorized=True)
        self.assertFalse(export_scope.authorizes_new_file(doc,'before_insert'))
        with patch.dict(sys.modules,{'frappe':types.SimpleNamespace(session=types.SimpleNamespace(user='A'))}),export_scope.execution(dict(kind='monthly',actor='A')):
            self.assertTrue(export_scope.authorizes_new_file(doc,'before_insert'))
            self.assertFalse(export_scope.authorizes_new_file(self.file(owner='B'),'before_insert'))
            self.assertFalse(export_scope.authorizes_new_file(self.file(is_private=0),'before_insert'))
            self.assertFalse(export_scope.authorizes_new_file(self.file(attached_to_name='unrelated'),'before_insert'))
            self.assertFalse(export_scope.authorizes_new_file(self.file(is_new=lambda:False),'before_validate'))
            self.assertFalse(export_scope.authorizes_new_file(doc,'on_trash'))
        self.assertFalse(export_scope.authorizes_new_file(doc,'before_insert'))

    def test_exception_or_worker_boundary_does_not_keep_the_file_creation_lease(self):
        with self.assertRaises(RuntimeError):
            with export_scope.execution(dict(kind='roster',actor='A')):
                self.assertIsNotNone(export_scope.active('roster'))
                raise RuntimeError('native export failure')
        self.assertIsNone(export_scope.active())
        self.assertFalse(export_scope.authorizes_new_file(self.file(),'before_insert'))
