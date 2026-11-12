import sys
import types
import unittest
from unittest.mock import patch
from hb_attendance_app.hbos_attendance.portal import import_scope


class ImportFileLeaseTest(unittest.TestCase):
    def file(self, **changes):
        values=dict(attached_to_doctype='HBOS Attendance Import Log',attached_to_name='batch-A',owner='A',is_private=1,is_new=lambda:True)
        return types.SimpleNamespace(**(values|changes))

    def test_source_lease_is_exact_actor_target_new_private_doc_and_method(self):
        self.assertFalse(import_scope.authorizes_new_file(self.file(hbos_import_authorized=True),'before_insert'))
        with patch.dict(sys.modules,{'frappe':types.SimpleNamespace(session=types.SimpleNamespace(user='A'))}),import_scope.new_file('A',('HBOS Attendance Import Log','batch-A')):
            self.assertTrue(import_scope.authorizes_new_file(self.file(),'before_insert'))
            for change in (dict(owner='B'),dict(attached_to_name='batch-B'),dict(is_private=0),dict(is_new=lambda:False)):
                self.assertFalse(import_scope.authorizes_new_file(self.file(**change),'before_validate'))
            self.assertFalse(import_scope.authorizes_new_file(self.file(),'on_trash'))
        self.assertFalse(import_scope.authorizes_new_file(self.file(),'before_insert'))

    def test_scope_cannot_authorize_an_unrelated_file_and_does_not_survive_failure(self):
        with self.assertRaises(ValueError):
            with import_scope.new_file('A',('User','A')):pass
        with self.assertRaises(RuntimeError):
            with import_scope.new_file('A',('Page','hbos-shift-management')):
                raise RuntimeError('native write failed')
        self.assertIsNone(import_scope._current.get())
