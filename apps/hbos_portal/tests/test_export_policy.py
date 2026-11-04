from __future__ import annotations

import importlib.util
import inspect
import pathlib
import unittest

from hbos_portal.auth import export_policy
from hbos_portal.auth.export_policy import (
    BOUND_ROLES,
    REASON_EXPORT_WITHOUT_READ,
    REASON_SENSITIVE_DOCTYPE,
    SENSITIVE_EXPORT_DENIED,
    denied_doctypes,
    plan_export_denials,
)

APP_ROOT = pathlib.Path(export_policy.__file__).resolve().parents[1]
HOOKS_PATH = APP_ROOT / "hooks.py"
ENFORCER = "hbos_portal.auth.export_policy.enforce_sensitive_export_boundary"
HANDLER = "hbos_portal.auth.export_policy.on_user_type_update"


def load_hooks_namespace():
    """Load ``hooks.py`` by path.

    ``hooks.py`` is plain data and imports nothing, so it can be read without a
    Frappe runtime. Loading by path keeps the test independent of the package
    ``__init__`` chain.
    """
    spec = importlib.util.spec_from_file_location("hbos_portal_hooks_under_test", HOOKS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return vars(module)


def row(name, parent, read, export, role="Employee Self Service", select=0):
    return {
        "name": name,
        "role": role,
        "parent": parent,
        "read": read,
        "export": export,
        "select": select,
        "if_owner": 0,
    }


class ExportDenialPlanTest(unittest.TestCase):
    """`export` may not outlive `read`."""

    def test_select_only_link_target_loses_export(self):
        # Exactly the shape HRMS mints for a Link target: select=1, read=0 and
        # an `export` bit nobody asked for.
        plan = plan_export_denials([row("cp-1", "User", read=0, export=1, select=1)])
        self.assertEqual([item["parent"] for item in plan], ["User"])
        self.assertEqual(plan[0]["reason"], REASON_EXPORT_WITHOUT_READ)

    def test_privileged_doctypes_from_the_incident_are_all_covered(self):
        doctypes = (
            "User",
            "Role",
            "DocType",
            "Department",
            "Warehouse",
            "Attendance",
            "Shift Type",
        )
        rows = [
            row("cp-%d" % index, doctype, read=0, export=1, select=1)
            for index, doctype in enumerate(doctypes)
        ]
        # Shift Type is additionally on the sensitivity list, so exercise the
        # read=0 path for it explicitly and assert coverage regardless of reason.
        self.assertEqual(
            denied_doctypes(plan_export_denials(rows)),
            sorted(doctypes),
        )

    def test_readable_self_service_doctypes_keep_export(self):
        # The self-service surface must not be narrowed: these are read=1 rows on
        # doctypes that are neither owner-scoped nor organisation-wide masters.
        rows = [
            row("cp-1", "Employee", read=1, export=1),
            row("cp-2", "Leave Application", read=1, export=1),
            row("cp-3", "Expense Claim", read=1, export=1),
            row("cp-4", "Salary Slip", read=1, export=1),
            row("cp-5", "Attendance Request", read=1, export=1, role="Employee"),
        ]
        self.assertEqual(plan_export_denials(rows), [])

    def test_owner_scoped_and_master_doctypes_lose_export(self):
        for doctype in SENSITIVE_EXPORT_DENIED:
            with self.subTest(doctype=doctype):
                plan = plan_export_denials([row("cp-1", doctype, read=1, export=1)])
                self.assertEqual([item["parent"] for item in plan], [doctype])
                self.assertEqual(plan[0]["reason"], REASON_SENSITIVE_DOCTYPE)

    def test_file_is_denied_even_though_it_is_readable(self):
        self.assertIn("File", SENSITIVE_EXPORT_DENIED)
        plan = plan_export_denials([row("cp-1", "File", read=1, export=1)])
        self.assertEqual([item["parent"] for item in plan], ["File"])

    def test_rows_without_export_are_left_alone(self):
        rows = [
            row("cp-1", "User", read=0, export=0, select=1),
            row("cp-2", "Role", read=0, export=0, select=1),
            row("cp-3", "Employee", read=1, export=0),
        ]
        self.assertEqual(plan_export_denials(rows), [])

    def test_sibling_roles_held_by_the_same_subject_are_bound(self):
        # HRMS also grants `Employee`, and Frappe grants `All`; an export bit
        # reachable through either would defeat the boundary.
        self.assertEqual(BOUND_ROLES, ("Employee Self Service", "Employee", "All"))
        for role in BOUND_ROLES:
            with self.subTest(role=role):
                plan = plan_export_denials([row("cp-1", "User", read=0, export=1, role=role)])
                self.assertEqual([item["parent"] for item in plan], ["User"])

    def test_unbound_roles_are_never_touched(self):
        # HR/privileged roles keep their export rights: this is not a global
        # "strip every export" change.
        for role in ("HR Manager", "HR User", "System Manager", "Accounts Manager"):
            with self.subTest(role=role):
                rows = [
                    row("cp-1", "User", read=0, export=1, role=role),
                    row("cp-2", "File", read=1, export=1, role=role),
                    row("cp-3", "Shift Type", read=1, export=1, role=role),
                ]
                self.assertEqual(plan_export_denials(rows), [])

    def test_empty_and_none_input(self):
        self.assertEqual(plan_export_denials([]), [])
        self.assertEqual(plan_export_denials(None), [])

    def test_plan_reports_state_for_evidence(self):
        plan = plan_export_denials(
            [row("cp-1", "Warehouse", read=0, export=1, select=1, role="Employee")]
        )
        self.assertEqual(
            plan,
            [
                {
                    "name": "cp-1",
                    "role": "Employee",
                    "parent": "Warehouse",
                    "read": 0,
                    "select": 1,
                    "reason": REASON_EXPORT_WITHOUT_READ,
                }
            ],
        )

    def test_role_constants_are_the_provisioned_self_service_roles(self):
        # Keep the names pinned so a rename cannot silently disable enforcement.
        self.assertIn("Employee Self Service", BOUND_ROLES)
        self.assertIn("Employee", BOUND_ROLES)
        self.assertIn("All", BOUND_ROLES)


class UserTypeDurabilityTest(unittest.TestCase):
    """The boundary must survive an ordinary User Type save, not only a migrate.

    ``UserType.on_update`` re-mints ``Custom DocPerm`` rows through helpers that
    never write ``export``, so those rows inherit the field default of ``1``.
    ``after_migrate`` cannot cover the window between two migrations; the
    ``doc_events`` handler can.
    """

    def test_hooks_registers_user_type_on_update(self):
        hooks = load_hooks_namespace()
        self.assertEqual(hooks["doc_events"]["User Type"]["on_update"], HANDLER)

    def test_existing_doc_events_are_preserved(self):
        # Registering the durability hook must not displace the existing ones.
        doc_events = load_hooks_namespace()["doc_events"]
        self.assertIn("User", doc_events)
        self.assertIn("Social Login Key", doc_events)
        self.assertIn("on_update", doc_events["User"])

    def test_migrate_and_install_hooks_still_enforce(self):
        hooks = load_hooks_namespace()
        self.assertIn(ENFORCER, hooks["after_migrate"])
        self.assertIn(ENFORCER, hooks["after_install"])

    def test_handler_delegates_to_the_single_enforcer(self):
        calls = []
        sentinel = {"examined": 0, "denied": 0}
        original = export_policy.enforce_sensitive_export_boundary

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return sentinel

        export_policy.enforce_sensitive_export_boundary = spy
        try:
            result = export_policy.on_user_type_update(object(), "on_update")
        finally:
            export_policy.enforce_sensitive_export_boundary = original

        # Called exactly once, with no arguments: the handler re-states nothing.
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], ((), {}))
        self.assertEqual(result, {"export_policy": sentinel})

    def test_handler_accepts_doc_and_method(self):
        # Mirrors frappe.model.document._accepts_method_argument: a handler with
        # two positional parameters is invoked as handler(doc, method).
        params = [
            parameter
            for parameter in inspect.signature(export_policy.on_user_type_update).parameters.values()
            if parameter.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        self.assertGreaterEqual(len(params), 2)

    def test_handler_does_not_restate_the_policy(self):
        source = inspect.getsource(export_policy.on_user_type_update)
        for token in ("BOUND_ROLES", "SENSITIVE_EXPORT_DENIED", "read=0", "export=1"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_there_is_exactly_one_policy_definition(self):
        # A second copy of the constants anywhere in the app would be a second
        # policy that could silently drift from the enforced one.
        definitions = []
        for path in sorted(APP_ROOT.rglob("*.py")):
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                for constant in ("BOUND_ROLES =", "SENSITIVE_EXPORT_DENIED ="):
                    if stripped.startswith(constant):
                        definitions.append((path.name, constant))

        self.assertEqual(
            sorted(definitions),
            [
                ("export_policy.py", "BOUND_ROLES ="),
                ("export_policy.py", "SENSITIVE_EXPORT_DENIED ="),
            ],
        )

    def test_enforcement_writes_through_db_set_value_only(self):
        # Recursion safety: the enforcer must not save a User Type. It may only
        # touch Custom DocPerm rows through frappe.db.set_value.
        source = inspect.getsource(export_policy.enforce_sensitive_export_boundary)
        self.assertIn('frappe.db.set_value("Custom DocPerm"', source)
        for token in ("User Type", ".save(", ".insert(", "on_update"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
