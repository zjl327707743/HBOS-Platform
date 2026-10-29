"""Bounded unit tests for department role defaults and management-role admissions."""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

frappe_stub = sys.modules.setdefault("frappe", types.SimpleNamespace())
if not hasattr(frappe_stub, "whitelist"):
    frappe_stub.whitelist = lambda **kwargs: (lambda function: function)
if "frappe.rate_limiter" not in sys.modules:
    rate_limiter = types.ModuleType("frappe.rate_limiter")
    rate_limiter.rate_limit = lambda **kwargs: (lambda function: function)
    sys.modules["frappe.rate_limiter"] = rate_limiter

from hbos_portal.iam import role_access as roles
from hbos_portal.iam import role_commands, role_models
from hbos_portal.iam.role_models import release_hash


class Attr(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


class Invalid(Exception):
    pass


class PermissionDenied(Exception):
    pass


def employee(**overrides):
    row = Attr(name="EMP-001", user_id="user-a", department="D1", company="C", status="Active", modified="2026-10-01 10:00:00", employee_name="合成员工", employee_number="0001")
    row.update(overrides)
    return row


def role_doc(key="clerk", boundary="DEPARTMENT", release="release-1"):
    return Attr(name=f"role-{key}", app_id="attendance", role_key=key, title=key, boundary_kind=boundary,
                enabled=1, published_release=release)


def release_doc(name="release-1", revision=3):
    return Attr(name=name, role="role-clerk", revision=revision, content_hash="a" * 64, native_mapping_json="[]",
                features=[])


class AdmissionHashTest(unittest.TestCase):
    def test_hash_binds_identity_release_and_scope(self):
        emp, role, release = employee(), role_doc(), release_doc()
        scopes = [dict(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)]
        baseline = roles.admission_hash("D1", "attendance", emp, role, release, scopes)
        self.assertEqual(baseline, roles.admission_hash("D1", "attendance", employee(), role_doc(), release_doc(), [dict(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)]))
        self.assertNotEqual(baseline, roles.admission_hash("D1", "attendance", employee(modified="2026-10-02"), role, release, scopes))
        self.assertNotEqual(baseline, roles.admission_hash("D2", "attendance", emp, role, release, scopes))
        self.assertNotEqual(baseline, roles.admission_hash("D1", "attendance", emp, role, role_doc(release="release-2"), scopes))
        self.assertNotEqual(baseline, roles.admission_hash("D1", "attendance", emp, role, release_doc(revision=4), scopes))
        self.assertNotEqual(baseline, roles.admission_hash("D1", "attendance", emp, role, release, [dict(scope_type="DEPARTMENT", scope_ref="D2", include_descendants=0)]))
        self.assertNotEqual(baseline, roles.admission_hash("D1", "attendance", employee(user_id="user-b"), role, release, scopes))

    def test_admission_key_is_stable_and_unique(self):
        one = roles.admission_key("D1", "attendance", "EMP-001")
        self.assertEqual(one, roles.admission_key("D1", "attendance", "EMP-001"))
        self.assertNotEqual(one, roles.admission_key("D2", "attendance", "EMP-001"))
        self.assertNotEqual(one, roles.admission_key("D1", "attendance", "EMP-002"))
        self.assertNotEqual(one, roles.admission_key("D1", "other", "EMP-001"))


class ResolveAdmissionGateTest(unittest.TestCase):
    def setUp(self):
        department_assignment = Attr(name="dept-assignment", app_id="attendance", mode="DIRECT", role="role-clerk",
                                     enabled=1, version=4, review_required=0,
                                     responsibilities=[Attr(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)])
        self.employee = employee()
        self.department_assignment = department_assignment
        self.feature_rows = [dict(operation_id="attendance.read", scope_binding="SELF"),
                             dict(operation_id="attendance.department.records.read", scope_binding="RESPONSIBLE_DEPARTMENTS")]
        self.fake = types.SimpleNamespace(PermissionError=PermissionDenied, ValidationError=Invalid,
            throw=lambda message, kind=PermissionDenied: (_ for _ in ()).throw(kind(message)))
        self.patches = [
            patch.object(roles, "frappe", self.fake),
            patch.object(roles, "enabled", return_value=True),
            patch.object(roles, "require_available"),
            patch.object(roles, "preserves_legacy_personal", return_value=False),
            patch.object(roles, "assignments", side_effect=self._assignments),
            patch.object(roles, "document", side_effect=self._document),
            patch.object(roles, "management_companies", return_value=["C"]),
            patch.object(roles, "normalize_scopes", side_effect=lambda rows, *args: [dict(row) for row in rows]),
            patch.object(roles, "normalize_features", return_value=self.feature_rows),
            patch.object(role_models, "release_hash", return_value="a" * 64),
        ]
        for row in self.patches:
            row.start()
            self.addCleanup(row.stop)

    def _assignments(self, kind, name, app_id="attendance"):
        if kind == "Employee":
            return []
        return [self.department_assignment] if kind == "Department" and name == "D1" else []

    def _document(self, doctype, name, **kwargs):
        if doctype == roles.ROLE:
            return role_doc()
        if doctype == roles.RELEASE:
            return release_doc()
        raise AssertionError((doctype, name))

    def test_department_clerk_needs_confirmed_matching_admission(self):
        with patch.object(roles, "admission_row", return_value=Attr(status="PENDING", config_hash="x")):
            pending = roles.resolve(self.employee)
        self.assertEqual(pending["role_key"], "clerk")
        self.assertIn("待确认", pending["reason"])
        self.assertEqual(pending["features"], [])
        with patch.object(roles, "admission_row", return_value=None):
            missing = roles.resolve(self.employee)
        self.assertIn("待确认", missing["reason"])
        confirmed_row = Attr(status="CONFIRMED", config_hash=roles.admission_hash("D1", "attendance", self.employee, role_doc(), release_doc(),
                                                                                  [dict(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)]))
        with patch.object(roles, "admission_row", return_value=confirmed_row):
            granted = roles.resolve(self.employee)
        self.assertEqual(granted["reason"], "")
        self.assertEqual(granted["role_key"], "clerk")
        self.assertEqual(granted["admission_status"], "confirmed")
        self.assertTrue(granted["features"])

    def test_stale_confirmation_hash_is_not_a_grant(self):
        stale = Attr(status="CONFIRMED", config_hash="stale")
        with patch.object(roles, "admission_row", return_value=stale):
            resolved = roles.resolve(self.employee)
        self.assertIn("已变化", resolved["reason"])
        self.assertEqual(resolved["features"], [])

    def test_direct_and_staff_sources_do_not_read_admissions(self):
        direct = Attr(name="emp-assignment", app_id="attendance", mode="DIRECT", role="role-staff", enabled=1, version=1,
                      review_required=0, responsibilities=[])
        with patch.object(roles, "assignments", side_effect=lambda kind, name, app_id='attendance': [direct] if kind == "Employee" else []), \
             patch.object(roles, "document", side_effect=lambda doctype, name, **kwargs: Attr(name="role-staff", app_id="attendance", role_key="staff", title="staff", boundary_kind="SELF", enabled=1, published_release="release-1") if doctype == roles.ROLE else Attr(name="release-1", role="role-staff", revision=1, content_hash="a" * 64, native_mapping_json="[]", features=[])), \
             patch.object(roles, "admission_row") as admission:
            resolved = roles.resolve(self.employee)
        admission.assert_not_called()
        self.assertEqual(resolved["role_key"], "staff")

    def test_department_staff_default_does_not_need_admission(self):
        self.department_assignment.role = "role-staff"
        role_staff = role_doc("staff", "SELF")
        with patch.object(roles, "document", side_effect=lambda doctype, name, **kwargs: role_staff if doctype == roles.ROLE else Attr(name="release-1", role="role-staff", revision=1, content_hash="a" * 64, native_mapping_json="[]", features=[])), \
             patch.object(roles, "normalize_features", return_value=[dict(operation_id="attendance.read", scope_binding="SELF")]), \
             patch.object(roles, "normalize_scopes", return_value=[]), \
             patch.object(roles, "admission_row") as admission:
            resolved = roles.resolve(self.employee)
        admission.assert_not_called()
        self.assertEqual(resolved["role_key"], "staff")


class DepartmentCommandHelperTest(unittest.TestCase):
    def setUp(self):
        self.fake = types.SimpleNamespace(
            ValidationError=Invalid, PermissionError=PermissionDenied,
            throw=lambda message, kind=Invalid: (_ for _ in ()).throw(kind(message)))
        self.patch = patch.object(role_commands, "frappe", self.fake)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def test_none_role_rejects_scopes_and_accepts_empty(self):
        self.assertEqual(role_commands._department_scope(None, []), [])
        self.assertEqual(role_commands._department_scope(None, '[]'), [])
        with self.assertRaises(Invalid):
            role_commands._department_scope(None, [dict(scope_type="DEPARTMENT", scope_ref="D1")])

    def test_role_scopes_are_delegated_to_shared_normalizer(self):
        role = role_doc()
        scopes = [dict(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)]
        with patch.object(roles, "management_companies", return_value=["C"]), \
             patch.object(roles, "normalize_scopes", return_value=scopes) as normalizer:
            result = role_commands._department_scope(role, scopes)
        self.assertEqual(result, scopes)
        normalizer.assert_called_once()
        self.assertEqual(normalizer.call_args.args[1], "DEPARTMENT")
        self.assertEqual(normalizer.call_args.args[2], ["C"])

    def test_admission_values_are_server_computed(self):
        scope_rows = [dict(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)]
        values = role_commands._admission_values("D1", "attendance", employee(), role_doc(), release_doc(), scope_rows)
        self.assertEqual(values["admission_key"], roles.admission_key("D1", "attendance", "EMP-001"))
        self.assertEqual(values["config_hash"], roles.admission_hash("D1", "attendance", employee(), role_doc(), release_doc(), scope_rows))
        self.assertEqual(values["role_key"], "clerk")
        self.assertIn("D1", values["responsibilities_json"])


class DepartmentAssignmentValidationTest(unittest.TestCase):
    def setUp(self):
        self.fake = types.SimpleNamespace(
            PermissionError=PermissionDenied, ValidationError=Invalid,
            throw=lambda message, kind=PermissionDenied: (_ for _ in ()).throw(kind(message)),
            db=types.SimpleNamespace(exists=lambda doctype, name: True, sql=lambda *args, **kwargs: []))
        for module in (role_models,):
            patcher = patch.object(module, "frappe", self.fake)
            patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_models.guards, "require_controlled_write")
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_models.roles, "document", side_effect=lambda doctype, name, **kwargs: role_doc() if doctype == role_models.roles.ROLE else release_doc())
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_models.roles, "management_companies", return_value=["C"])
        patcher.start(); self.addCleanup(patcher.stop)

    def doc(self, **overrides):
        row = Attr(app_id="attendance", subject_type="Department", subject_name="D1", mode="DIRECT", role="role-clerk",
                   enabled=1, version=1, review_required=0, responsibilities=[Attr(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)],
                   get_doc_before_save=lambda: None)
        row.update(overrides)
        return row

    def test_department_management_roles_use_the_published_scope_boundary(self):
        with patch.object(role_models.roles, "normalize_scopes", return_value=[dict(scope_type="DEPARTMENT", scope_ref="D1", include_descendants=0)]):
            role_models.validate_assignment(self.doc())
        with patch.object(role_models.roles, "normalize_scopes", side_effect=PermissionDenied("范围不符")):
            with self.assertRaises(PermissionDenied):
                role_models.validate_assignment(self.doc())

    def test_department_follow_or_none_cannot_carry_a_role(self):
        for overrides in (dict(mode="FOLLOW_DEPARTMENT"), dict(mode="NONE")):
            with self.subTest(overrides=overrides), self.assertRaises(PermissionDenied):
                role_models.validate_assignment(self.doc(role="role-clerk", **overrides))


class EmployeeAssignmentCatalogueTest(unittest.TestCase):
    """The employee page must read the same published catalogue as the department.

    A read-only projection only: no grant is implied, and a role that cannot be
    read stays not-grantable with its reason instead of becoming an offer.
    """

    def setUp(self):
        self.fake = types.SimpleNamespace(
            PermissionError=PermissionDenied, ValidationError=Invalid,
            throw=lambda message, kind=PermissionDenied: (_ for _ in ()).throw(kind(message)),
            db=types.SimpleNamespace(exists=lambda doctype, name: True, sql=lambda *args, **kwargs: []))
        patcher = patch.object(role_commands, "frappe", self.fake)
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_commands.roles, "require_available")
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_commands, "_employee", return_value=employee())
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_commands.roles, "assignments", return_value=[])
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_commands.roles, "resolve", return_value=None)
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_commands.roles, "preserves_legacy_personal", return_value=False)
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(role_commands, "_effective", return_value={"allowed": False, "reason": "", "operations": []})
        patcher.start(); self.addCleanup(patcher.stop)

    def test_get_assignment_projects_the_shared_published_catalogue(self):
        catalog = [
            {"role_key": "staff", "title": "普通员工", "boundary_kind": "SELF", "grantable": True, "reason": "", "published_revision": 2},
            {"role_key": "clerk", "title": "部门考勤员", "boundary_kind": "DEPARTMENT", "grantable": False, "reason": "角色尚未发布，暂不能授予。", "published_revision": 0},
        ]
        with patch.object(role_commands, "_department_role_catalog", return_value=catalog) as projection:
            result = role_commands.get_assignment("EMP-001", "attendance")
        projection.assert_called_once_with("D1", "C")
        self.assertEqual(result["roles"], catalog)
        # Reading the catalogue never grants anything.
        self.assertEqual(result["mode"], "FOLLOW_DEPARTMENT")
        self.assertNotIn("changed", result)


class AdmissionTransitionTest(unittest.TestCase):
    """Every status pair the command layer can produce must be accepted.

    Regression: a member whose admission context changed (for example after a
    transfer back into the department) keeps an existing CONFIRMED row. The save
    rewrites that row as CONFIRMED with a new hash, and the missing
    CONFIRMED -> CONFIRMED pair made the legitimate re-confirmation fail with
    "准入状态转换无效" (403).
    """

    def test_reconfirming_an_existing_confirmation_is_allowed(self):
        from hbos_portal.iam.role_models import ADMISSION_TRANSITIONS
        self.assertIn(('CONFIRMED', 'CONFIRMED'), ADMISSION_TRANSITIONS)
        self.assertIn(('PENDING', 'CONFIRMED'), ADMISSION_TRANSITIONS)
        self.assertIn(('REVOKED', 'CONFIRMED'), ADMISSION_TRANSITIONS)
        self.assertIn(('CONFIRMED', 'REVOKED'), ADMISSION_TRANSITIONS)
        self.assertIn(('REVOKED', 'PENDING'), ADMISSION_TRANSITIONS)

    def test_no_transition_can_jump_out_of_an_unknown_state(self):
        from hbos_portal.iam.role_models import ADMISSION_TRANSITIONS
        self.assertFalse([pair for pair in ADMISSION_TRANSITIONS if pair[0] not in {'PENDING', 'CONFIRMED', 'REVOKED'}])

    def test_a_revoked_row_is_the_cleanup_path_for_a_changed_context(self):
        """Revoking must work when the stored hash no longer matches.

        The hash binds identity/release/scope. After a transfer or a new release
        an existing CONFIRMED row is stale; the department save has to be able to
        revoke it, otherwise every later save fails and the row can never be
        cleaned up. A CONFIRMED/PENDING row must still match its hash exactly.
        """
        fake = types.SimpleNamespace(
            PermissionError=PermissionDenied, ValidationError=Invalid,
            throw=lambda message, kind=PermissionDenied: (_ for _ in ()).throw(kind(message)),
            db=types.SimpleNamespace(
                exists=lambda doctype, name: True,
                get_value=lambda *args, **kwargs: employee(),
            ))
        doc = Attr(app_id='attendance', department='D1', employee='EMP-001', role='role-clerk', role_key='clerk',
                   responsibilities_json='[{"scope_type": "DEPARTMENT", "scope_ref": "D1", "include_descendants": 0}]',
                   config_hash='stale', status='REVOKED', version=2, confirmed_by='hr', confirmed_at='2026-10-01',
                   revoked_by='hr', revoked_at='2026-10-02',
                   get_doc_before_save=lambda: Attr(status='CONFIRMED', version=1, department='D1', app_id='attendance',
                                                    employee='EMP-001', role='role-clerk', role_key='clerk'))
        doc.admission_key = roles.admission_key('D1', 'attendance', 'EMP-001')
        with patch.object(role_models, 'frappe', fake), \
             patch.object(role_models.guards, 'require_controlled_write'), \
             patch.object(role_models.roles, 'document', side_effect=lambda doctype, name, **kwargs: role_doc() if doctype == role_models.roles.ROLE else release_doc()), \
             patch.object(role_models.roles, 'management_companies', return_value=['C']), \
             patch.object(role_models.roles, 'normalize_scopes', return_value=[dict(scope_type='DEPARTMENT', scope_ref='D1', include_descendants=0)]), \
             patch.object(role_models.roles, 'admission_hash', return_value='fresh'):
            role_models.validate_department_admission(doc)  # stale hash on a REVOKED row is accepted
            doc.status = 'CONFIRMED'
            with self.assertRaises(PermissionDenied):
                role_models.validate_department_admission(doc)


if __name__ == "__main__":
    unittest.main()
