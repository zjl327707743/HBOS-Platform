"""Synthetic protocol data only; no Site, environment or personal records."""
from copy import deepcopy

from hbos_portal.authorization.contracts import RegistrationInput
from hbos_portal.authorization.registry import build_definition_registry
from hbos_portal.authorization.validation import (
    validate_position_projection, validate_role_bundle, validate_template_version,
)


def definition(app="demo_lab"):
    return {
        "contract_version": 1, "app_id": app, "definition_revision": "opaque-r1",
        "resources": [{"resource_id": f"{app}.result", "label": "合成结果"}],
        "scopes": [{"scope_type": f"{app}.lab_group", "schema_version": 1, "dimension": "lab_group", "reference_type": f"{app}.group", "allow_descendants": False}],
        "actions": [{"action_id": f"{app}.results.{verb}", "label": verb, "resource_id": f"{app}.result", "scope_types": [f"{app}.lab_group"], "enabled": True, "implemented": True, "status": "active"} for verb in ("read", "review", "submit")],
        "bindings": [{"binding_key": f"provider:{verb}", "action_id": f"{app}.results.{verb}", "resource_id": f"{app}.result", "scope_types": [f"{app}.lab_group"]} for verb in ("read", "review", "submit")],
    }


def registration(payload=None, app="demo_lab", source="synthetic"):
    return RegistrationInput(source, app, deepcopy(payload if payload is not None else definition(app)))


def template(action="review", app="demo_lab"):
    return {"app_id": app, "template_id": f"{action}-role", "version": 1, "action_ids": [f"{app}.results.{action}"]}


def position(identifier="POS-A", department="DEPT-A"):
    return {"position_id": identifier, "department_ref": {"source_type": "Department", "source_id": department}, "label": "检验岗位", "status": "active", "revision": 1}


def role_payload(action="review", app="demo_lab"):
    return {"role_id": f"ROLE-{action}", "version": 1, "components": [{"component_id": action, "app_id": app, "template_id": f"{action}-role", "template_version": 1}]}


def binding(action="review", group="GROUP-A", position_id="POS-A", app="demo_lab"):
    return {"binding_id": f"BIND-{group}", "version": 1, "position_id": position_id, "role_id": f"ROLE-{action}", "role_version": 1, "component_scopes": [{"component_id": action, "scope_type": f"{app}.lab_group", "schema_version": 1, "dimension": "lab_group", "reference_type": f"{app}.group", "reference_ids": [group], "include_descendants": False}]}


def assignment(identifier="ASSIGN-A", position_id="POS-A", primary=True):
    return {"assignment_id": identifier, "person_ref": {"source_type": "Employee", "source_id": "PERSON-SYNTHETIC"}, "subject_user": None, "position_id": position_id, "is_primary": primary, "valid_from": "2026-01-01T00:00:00+08:00", "valid_until": None, "status": "active", "revision": 1, "authorization_generation": 1, "qualification_status": "unlinked"}


def context():
    registry = build_definition_registry([registration()])
    templates = [validate_template_version(template(action), registry) for action in ("review", "submit")]
    roles = [validate_role_bundle(role_payload(action), templates) for action in ("review", "submit")]
    positions = [validate_position_projection(position()), validate_position_projection(position("POS-B", "DEPT-B"))]
    return registry, templates, roles, positions
