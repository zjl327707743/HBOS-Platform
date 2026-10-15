import dataclasses
import unittest

from hbos_portal.authorization.errors import ContractError
from hbos_portal.authorization.validation import (
    validate_assignment_projection, validate_assignment_set,
    validate_position_binding, validate_position_projection,
    validate_role_bundle, validate_template_version,
)
from tests.authorization_fixtures import (
    assignment, binding, context, definition, position, registration,
    role_payload, template,
)
from hbos_portal.authorization.registry import build_definition_registry


class AuthorizationRelationTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.templates, self.roles, self.positions = context()

    def validate_binding(self, data, **kwargs):
        return validate_position_binding(data, self.roles[0], self.registry, self.positions, **kwargs)

    def test_off12_two_assignments_keep_whole_role_scope_pairs(self):
        review_a = self.validate_binding(binding())
        submit_b = validate_position_binding(binding("submit", "GROUP-B", "POS-B"), self.roles[1], self.registry, self.positions)
        assignments = validate_assignment_set([assignment(), assignment("ASSIGN-B", "POS-B", False)], self.positions)
        self.assertEqual(review_a.component_scopes[0].reference_ids, ("GROUP-A",))
        self.assertEqual(review_a.role_id, "ROLE-review")
        self.assertEqual(submit_b.component_scopes[0].reference_ids, ("GROUP-B",))
        self.assertEqual(submit_b.role_id, "ROLE-submit")
        self.assertEqual(len(assignments.assignments), 2)
        self.assertFalse(assignments.runtime_verified)
        self.assertEqual(assignments.coverage, "provided_set_only")

    def test_cross_app_components_require_their_own_registered_scope(self):
        registry = build_definition_registry([registration(), registration(app="new_app")])
        second = validate_template_version(template(app="new_app"), registry)
        role_data = role_payload()
        role_data["components"].append({"component_id": "other", "app_id": "new_app", "template_id": "review-role", "template_version": 1})
        role = validate_role_bundle(role_data, [self.templates[0], second])
        data = binding()
        other = binding(app="new_app")["component_scopes"][0]
        other["component_id"] = "other"
        data["component_scopes"].append(other)
        result = validate_position_binding(data, role, registry, self.positions)
        self.assertEqual({s.scope_type for s in result.component_scopes}, {"demo_lab.lab_group", "new_app.lab_group"})
        data["component_scopes"][1]["reference_type"] = "demo_lab.group"
        with self.assertRaises(ContractError):
            validate_position_binding(data, role, registry, self.positions)

    def test_off13_incomplete_extra_empty_wrong_or_executable_scope_rejected(self):
        for mode in ("missing", "extra", "empty", "reference_type", "dimension", "schema", "bool_schema", "sql", "wrong_type"):
            with self.subTest(mode=mode):
                data = binding()
                scope = data["component_scopes"][0]
                if mode == "missing":
                    data["component_scopes"] = []
                elif mode == "extra":
                    data["component_scopes"].append({**scope, "component_id": "other"})
                else:
                    key, value = {"empty": ("reference_ids", []), "reference_type": ("reference_type", "other.group"), "dimension": ("dimension", "other"), "schema": ("schema_version", 42), "bool_schema": ("schema_version", True), "sql": ("sql", "select * from secret"), "wrong_type": ("include_descendants", "false")}[mode]
                    scope[key] = value
                with self.assertRaises(ContractError):
                    self.validate_binding(data)

    def test_off14_equal_labels_never_merge_department_positions_or_business_ids(self):
        self.assertEqual(self.positions[0].label, self.positions[1].label)
        self.assertNotEqual(self.positions[0].position_id, self.positions[1].position_id)
        self.assertNotEqual(self.positions[0].department_ref, self.positions[1].department_ref)
        data = binding(group="DEPT-A")
        result = self.validate_binding(data)
        self.assertEqual(result.component_scopes[0].reference_ids, ("DEPT-A",))
        self.assertFalse(result.runtime_verified)  # Existence or group identity is not inferred.
        data["component_scopes"][0]["include_descendants"] = True
        with self.assertRaises(ContractError) as error:
            self.validate_binding(data)
        self.assertEqual(error.exception.code, "DESCENDANTS_NOT_ALLOWED")

    def test_off15_unlinked_unknown_and_ambiguous_qualifications_are_preserved(self):
        for qualification in ("unknown", "unlinked", "ambiguous"):
            data = assignment()
            data["qualification_status"] = qualification
            data["person_ref"]["source_type"] = "ExternalPerson"
            result = validate_assignment_projection(data, self.positions)
            self.assertIsNone(result.subject_user)
            self.assertEqual(result.qualification_status, qualification)
            self.assertFalse(result.runtime_verified)
        data["qualification_status"] = "verified"
        with self.assertRaises(ContractError):
            validate_assignment_projection(data, self.positions)
        data["subject_user"] = "synthetic-account"
        self.assertFalse(validate_assignment_projection(data, self.positions).runtime_verified)
        data["qualification_status"] = "ambiguous"
        with self.assertRaises(ContractError):
            validate_assignment_projection(data, self.positions)

    def test_off16_intervals_timezone_and_null_end_are_not_permanent_approval(self):
        for start, end in (("2026-01-01T00:00:00", None), ("2026-01-01T00:00:00+08:00", "2026-01-01T00:00:00+08:00"), ("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z"), ("bad", None)):
            data = assignment()
            data.update(valid_from=start, valid_until=end)
            with self.assertRaises(ContractError):
                validate_assignment_projection(data, self.positions)
        result = validate_assignment_projection(assignment(), self.positions)
        self.assertIsNone(result.valid_until)
        self.assertFalse(hasattr(result, "permanent_approved"))

    def test_off17_primary_overlap_and_duplicate_assignment_conflicts(self):
        for second, code in ((assignment("SECOND", "POS-B"), "OVERLAPPING_PRIMARY"), (assignment("SECOND", primary=False), "DUPLICATE_ASSIGNMENT"), (assignment(), "DUPLICATE_ID")):
            with self.assertRaises(ContractError) as error:
                validate_assignment_set([assignment(), second], self.positions)
            self.assertEqual(error.exception.code, code)

    def test_half_open_intervals_and_different_persons_do_not_conflict(self):
        first = assignment()
        first["valid_until"] = "2026-02-01T00:00:00+08:00"
        second = assignment("SECOND")
        second["valid_from"] = first["valid_until"]
        self.assertEqual(len(validate_assignment_set([first, second], self.positions).assignments), 2)
        second = assignment("SECOND")
        second["person_ref"]["source_id"] = "ANOTHER-SYNTHETIC-PERSON"
        self.assertEqual(len(validate_assignment_set([first, second], self.positions).assignments), 2)

    def test_off18_revision_generation_and_source_status_never_autorevive(self):
        for key in ("revision", "authorization_generation"):
            for value in (True, 0, -1, "1"):
                data = assignment()
                data[key] = value
                with self.assertRaises(ContractError):
                    validate_assignment_projection(data, self.positions)
        for status in ("inactive", "revoked"):
            data = assignment("SECOND")
            data["status"] = status
            result = validate_assignment_set([assignment(), data], self.positions)
            self.assertEqual(result.assignments[1].status, status)
            self.assertEqual(result.assignments[1].authorization_generation, 1)

    def test_fixed_role_and_binding_version_conflicts_require_new_version(self):
        original = self.validate_binding(binding())
        changed = binding(group="GROUP-B")
        changed["binding_id"] = original.binding_id
        with self.assertRaises(ContractError) as error:
            self.validate_binding(changed, known_versions=[original])
        self.assertEqual(error.exception.code, "VERSION_CONFLICT")
        changed["version"] = 2
        self.assertEqual(self.validate_binding(changed, known_versions=[original]).version, 2)
        changed_role = role_payload()
        changed_role["components"][0]["component_id"] = "changed"
        with self.assertRaises(ContractError) as error:
            validate_role_bundle(changed_role, self.templates, [self.roles[0]])
        self.assertEqual(error.exception.code, "VERSION_CONFLICT")

    def test_missing_role_template_position_and_duplicate_components_rejected(self):
        for mode in ("template", "component", "version"):
            role = role_payload()
            if mode == "template":
                role["components"][0]["template_id"] = "missing"
            elif mode == "component":
                role["components"].append(dict(role["components"][0]))
            else:
                role["components"][0]["template_version"] = True
            with self.assertRaises(ContractError):
                validate_role_bundle(role, self.templates)
        data = binding()
        data["position_id"] = "unknown"
        with self.assertRaises(ContractError):
            self.validate_binding(data)
        data = assignment()
        data["position_id"] = "unknown"
        with self.assertRaises(ContractError):
            validate_assignment_projection(data, self.positions)

    def test_relation_snapshots_are_deeply_immutable_and_payload_safe(self):
        data = binding()
        fixed = self.validate_binding(data)
        data["component_scopes"][0]["reference_ids"].append("GROUP-B")
        self.assertEqual(fixed.component_scopes[0].reference_ids, ("GROUP-A",))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            fixed.component_scopes[0].reference_ids += ("GROUP-B",)
        data = assignment()
        data["18812345678"] = "secret"
        with self.assertRaises(ContractError) as error:
            validate_assignment_projection(data, self.positions)
        self.assertNotIn("18812345678", str(error.exception))

    def test_inactive_position_projection_preserved_not_used_as_qualification(self):
        data = position()
        data["status"] = "inactive"
        result = validate_position_projection(data)
        self.assertEqual(result.status, "inactive")
        self.assertFalse(result.runtime_verified)
        data["revision"] = True
        with self.assertRaises(ContractError):
            validate_position_projection(data)


if __name__ == "__main__":
    unittest.main()
