"""Native-path service guards with in-memory metadata, not real HTTP/worker evidence."""
from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PORTAL = Path(__file__).resolve().parents[2] / "hbos_portal"
if str(PORTAL) not in sys.path:
    sys.path.insert(0, str(PORTAL))
sys.modules.setdefault("frappe", types.SimpleNamespace())
from hb_attendance_app.hbos_attendance.portal import permissions as boundary


class Attr(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class Denied(Exception):
    pass


class AttendanceBypassTest(unittest.TestCase):
    def setUp(self):
        self.reports = {
            "Attendance Base": Attr(name="Attendance Base", ref_doctype="Attendance", module="HR", reference_report=""),
            "Attendance Wrapped": Attr(name="Attendance Wrapped", ref_doctype="", module="Custom", reference_report="Attendance Base"),
            "Attendance Twice": Attr(name="Attendance Twice", ref_doctype="", module="Custom", reference_report="Attendance Wrapped"),
            "Ordinary": Attr(name="Ordinary", ref_doctype="ToDo", module="Core", reference_report=""),
        }
        self.prepared = {
            "PR-ATT": Attr(name="PR-ATT", report_name="Attendance Twice", owner="employee"),
            "PR-HR": Attr(name="PR-HR", report_name="Attendance Base", owner="legacy-hr"),
            "PR-OTHER": Attr(name="PR-OTHER", report_name="Ordinary", owner="employee"),
        }
        self.files = [Attr(name="F-OTHER", file_url="/private/files/shared.json.gz", attached_to_doctype="ToDo", attached_to_name="TODO-1")]
        self.files += [Attr(name=f"F-ALIAS-{i}", file_url="/private/files/shared.json.gz", attached_to_doctype="ToDo", attached_to_name="TODO-1") for i in range(22)]
        self.files += [Attr(name="F-ATT", file_url="/private/files/shared.json.gz", attached_to_doctype="Prepared Report", attached_to_name="PR-ATT")]
        self.calls = []
        def get_value(kind, name, fields="name", **kwargs):
            row = {"Report": self.reports, "Prepared Report": self.prepared, "File": {row.name: row for row in self.files}}.get(kind, {}).get(name) if isinstance(name, str) else None
            if not row:
                return None
            return Attr({field: row.get(field) for field in fields}) if isinstance(fields, list) else row.get(fields)
        def get_all(kind, filters=None, fields=None, **kwargs):
            self.calls.append((kind, filters, kwargs))
            rows = list(self.reports.values()) if kind == "Report" else self.files if kind == "File" else []
            return [row for row in rows if all(row.get(key) == value for key, value in (filters or {}).items())]
        def throw(message, kind=Denied):
            raise kind(message)
        self.fake = types.SimpleNamespace(conf=Attr(hbos_iam_enabled=1), session=Attr(user="employee"), local=Attr(request=Attr(path="/api/method"), form_dict=Attr(), job=Attr(user="employee")), db=Attr(get_value=get_value, escape=lambda value: "'" + value.replace("'", "''") + "'"), get_all=get_all, throw=throw, PermissionError=Denied)
        self.patcher = patch.object(boundary, "frappe", self.fake)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        def legacy(user=None, **kwargs):
            return (user or self.fake.session.user) in {"legacy-hr", "Administrator"}
        self.hr = patch.object(boundary, "legacy_hr", side_effect=legacy)
        self.hr.start()
        self.addCleanup(self.hr.stop)

    def request(self, path, **args):
        self.fake.local.request.path = path
        self.fake.local.form_dict = Attr(args)
        boundary.check_request()

    def doc(self, **values):
        return Attr(values, get_doc_before_save=lambda: None)

    def test_prepared_and_file_permissions_follow_wrappers_and_every_shared_url_alias(self):
        self.assertFalse(boundary.prepared_report_has_permission(self.prepared["PR-ATT"]))
        self.assertFalse(boundary.file_has_permission(self.files[0]))
        self.assertTrue(boundary.prepared_report_has_permission(self.prepared["PR-OTHER"]))
        self.assertTrue(boundary.file_has_permission(Attr(file_url="/private/files/ordinary.txt", attached_to_doctype="ToDo")))
        self.assertTrue(all(options.get("limit_page_length") == 0 for kind, _, options in self.calls if kind == "File"))

    def test_native_prepared_download_conversion_and_query_report_dn_are_rejected(self):
        cases = [
            (boundary.PREPARED_METHODS + "download_attachment", {"dn": "PR-ATT"}),
            (boundary.PREPARED_METHODS + "enqueue_json_to_csv_conversion", {"prepared_report_name": "PR-ATT"}),
            ("frappe.desk.query_report.run", {"dn": "PR-ATT", "report_name": "Ordinary"}),
            ("frappe.desk.query_report.run", {"filters": json.dumps({"prepared_report_name": "PR-ATT"})}),
        ]
        for command, args in cases:
            with self.subTest(command=command, args=args), self.assertRaises(Denied):
                self.request("/api/method/" + command, **args)

    def test_rest_payload_private_url_and_zip_cannot_bypass_attendance_classification(self):
        cases = [
            ("/api/resource/Attendance/ATT-B", {}),
            ("/api/v2/document/Employee%20Checkin/CHECK-B", {}),
            ("/api/resource/Prepared%20Report/PR-ATT", {}),
            ("/api/resource/File/F-OTHER", {}),
            ("/private/files/shared.json.gz", {}),
            ("/api/method/frappe.client.save", {"doc": json.dumps({"doctype": "Prepared Report", "report_name": "Attendance Twice"})}),
            ("/api/method/frappe.core.doctype.file.file.zip_files", {"files": json.dumps(["F-OTHER"])}),
        ]
        for path, args in cases:
            with self.subTest(path=path), self.assertRaises(Denied):
                self.request(path, **args)
        with self.assertRaises(Denied):
            self.request("/api/resource/Attendance%20Request")
        self.request("/api/resource/Attendance%20Request%20Extension")  # unknown prefix is left to native DocType permissions

    def test_opted_in_roles_cannot_recover_native_shift_policy_or_widget_access(self):
        self.fake.conf.hbos_iam_roles_enabled=1
        self.fake.db.has_column=lambda *args:True
        for path in (
            '/api/resource/Attendance%20Request',
            '/api/resource/HBOS%20Attendance%20Policy%20Assignment',
            '/api/method/hrms.hr.doctype.shift_assignment.shift_assignment.create_bulk_assignments',
            '/api/method/hrms.hr.doctype.attendance_request.attendance_request.get_attendance_warnings',
            '/api/method/hrms.api.get_attendance_for_calendar',
        ):
            with self.subTest(path=path),self.assertRaises(Denied):self.request(path)
        with self.assertRaises(Denied):
            self.request('/api/method/frappe.desk.doctype.dashboard_chart.dashboard_chart.get',doc=json.dumps({'document_type':'Attendance'}))

    def test_query_conditions_exclude_wrapped_reports_and_url_aliases(self):
        prepared = boundary.prepared_report_query_conditions()
        for name in ("Attendance Base", "Attendance Wrapped", "Attendance Twice"):
            self.assertIn(name, prepared)
        self.assertNotIn("Ordinary", prepared)
        files = boundary.file_query_conditions()
        self.assertIn("iam_file.file_url=`tabFile`.`file_url`", files)
        self.assertIn("`tabPrepared Report`", files)
        self.assertIn("Employee Checkin", files)

    def test_admin_worker_cannot_create_or_reassign_export_owned_by_iam_employee(self):
        self.fake.session.user = "Administrator"
        for doc in [self.doc(name="PR-ATT", report_name="Attendance Base", owner="employee"), self.doc(name="PR-ATT", report_name="Attendance Base", owner="legacy-hr")]:
            with self.subTest(owner=doc.owner), self.assertRaises(Denied):
                boundary.guard_prepared_report(doc, "before_validate")
        boundary.guard_prepared_report(self.doc(name="new-pr", report_name="Attendance Base", owner="legacy-hr"), "before_insert")

    def test_worker_file_requires_private_storage_and_current_prepared_owner(self):
        self.fake.session.user = "Administrator"
        doc = self.doc(name="new-file", file_url="/private/files/new.json.gz", attached_to_doctype="Prepared Report", attached_to_name="PR-ATT", is_private=1)
        with self.assertRaises(Denied):
            boundary.guard_file(doc, "before_insert")
        doc.attached_to_name = "PR-HR"
        doc.is_private = 0
        with self.assertRaises(Denied):
            boundary.guard_file(doc, "before_insert")
        doc.is_private = 1
        boundary.guard_file(doc, "before_insert")

    def test_existing_attendance_attachment_cannot_be_laundered_by_detaching_it(self):
        old = self.doc(name="old-file", file_url="/private/files/old.gz", attached_to_doctype="Attendance", attached_to_name="ATT-B", is_private=1)
        detached = self.doc(name="old-file", file_url="/private/files/renamed.gz", attached_to_doctype="ToDo", is_private=1)
        detached.get_doc_before_save = lambda: old
        with self.assertRaises(Denied):
            boundary.guard_file(detached, "before_validate")

    def test_fixed_background_jobs_recheck_owner_and_enqueuing_user(self):
        self.fake.session.user = "Administrator"
        command = boundary.PREPARED_METHODS + "generate_report"
        with self.assertRaises(Denied):
            boundary.check_background_job(command, {"prepared_report": "PR-ATT"})
        with self.assertRaises(Denied):
            boundary.check_background_job(command, {"prepared_report": "PR-HR"})
        self.fake.local.job.user = "legacy-hr"
        boundary.check_background_job(command, {"prepared_report": "PR-HR"})
        self.fake.local.job.user = "employee"
        with self.assertRaises(Denied):
            boundary.check_background_job("frappe.desk.query_report.run_export_query_job", {"form_params": {"report_name": "Attendance Twice"}})
        boundary.check_background_job("unrelated.job", {"report_name": "Attendance Twice"})

    def test_legacy_hr_and_disabled_rollout_are_left_to_existing_native_permissions(self):
        self.fake.session.user = "legacy-hr"
        self.request("/api/resource/Attendance/ATT-B")
        self.assertTrue(boundary.file_has_permission(self.files[0]))
        self.assertEqual("", boundary.prepared_report_query_conditions())
        self.fake.session.user = "employee"
        self.fake.conf.hbos_iam_enabled = 0
        self.request("/api/resource/Attendance/ATT-B")
        boundary.guard_file(self.doc(attached_to_doctype="Attendance", is_private=0), "before_insert")

    def test_request_guard_rechecks_revoked_authority_after_read_conflict(self):
        from hbos_portal.iam import policy
        conflict = type('ReadConflict', (Exception,), {})
        self.fake.QueryDeadlockError = conflict
        self.fake.db.rollback = Mock()
        # The first attempt cannot finish its authority read. The current
        # transaction after rollback has no native HR authority.
        with patch.object(policy, 'frappe', self.fake), patch('time.sleep'), \
                patch.object(boundary, 'legacy_hr', side_effect=[conflict(), False]) as authority:
            with self.assertRaises(Denied):
                self.request('/api/resource/Attendance/ATT-B')
        self.assertEqual(2, authority.call_count)
        self.fake.db.rollback.assert_called_once_with()

    def test_request_read_conflicts_are_bounded_and_never_allow_dispatch(self):
        from hbos_portal.iam import policy
        for name in ('QueryDeadlockError', 'QueryTimeoutError'):
            conflict = type(name, (Exception,), {})
            setattr(self.fake, name, conflict)
            self.fake.db.rollback = Mock()
            endpoint = Mock()
            with self.subTest(name=name), patch.object(policy, 'frappe', self.fake), \
                    patch('time.sleep') as delay, \
                    patch.object(boundary, 'legacy_hr', side_effect=conflict()) as authority:
                with self.assertRaises(conflict):
                    self.request('/api/method/frappe.client.save')
                    endpoint()
                self.assertEqual(4, authority.call_count)
                self.assertEqual(4, self.fake.db.rollback.call_count)
                self.assertEqual(3, delay.call_count)
                endpoint.assert_not_called()

    def test_recovered_pre_dispatch_read_does_not_repeat_endpoint_command(self):
        from hbos_portal.iam import policy
        conflict = type('ReadConflict', (Exception,), {})
        self.fake.QueryDeadlockError = conflict
        self.fake.db.rollback = Mock()
        endpoint = Mock()
        with patch.object(policy, 'frappe', self.fake), patch('time.sleep'), \
                patch.object(boundary, 'legacy_hr', side_effect=[conflict(), False]):
            self.request('/api/method/frappe.client.save')
            endpoint()
        endpoint.assert_called_once_with()

    def test_request_permission_denial_is_never_retried(self):
        from hbos_portal.iam import policy
        self.fake.db.rollback = Mock()
        with patch.object(policy, 'frappe', self.fake), patch('time.sleep') as delay, \
                patch.object(boundary, 'legacy_hr', side_effect=Denied()) as authority:
            with self.assertRaises(Denied):
                self.request('/api/resource/Attendance/ATT-B')
        authority.assert_called_once()
        delay.assert_not_called()
        self.fake.db.rollback.assert_not_called()

