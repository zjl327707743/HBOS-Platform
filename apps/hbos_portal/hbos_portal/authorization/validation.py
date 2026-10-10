"""Strict, side-effect-free structural validation. No policy decisions here."""
import re
from collections.abc import Mapping
from datetime import datetime

from .contracts import (
    ActionDefinition, AppDefinition, AssignmentProjection, AssignmentSet,
    EntryBinding, PositionBinding, PositionProjection, ResourceDefinition,
    RoleBundleVersion, RoleComponent, ScopeDefinition, ScopeSelection,
    SourceRef, TemplateVersion,
)
from .errors import ContractError

_SEGMENT = r"[a-z][a-z0-9_]*"


def _fail(code, path):
    raise ContractError(code, path)


def _fields(value, required, path, optional=()):
    if not isinstance(value, Mapping):
        _fail("INVALID_TYPE", path)
    if set(value) - set(required) - set(optional):
        # Do not echo unknown keys; a key itself can contain sensitive payload.
        _fail("UNKNOWN_FIELD", path)
    for key in required:
        if key not in value:
            _fail("MISSING_FIELD", f"{path}.{key}")
    return value


def _text(value, path):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        _fail("INVALID_TEXT", path)
    return value


def _integer(value, path, supported=None):
    if type(value) is not int or value < 1:
        _fail("INVALID_VERSION", path)
    if supported is not None and value not in supported:
        _fail("UNSUPPORTED_VERSION", path)
    return value


def _boolean(value, path):
    if type(value) is not bool:
        _fail("INVALID_TYPE", path)
    return value


def _array(value, path, nonempty=True):
    if not isinstance(value, (list, tuple)) or (nonempty and not value):
        _fail("INVALID_COLLECTION", path)
    return value


def _texts(value, path):
    result = tuple(_text(item, f"{path}[{i}]") for i, item in enumerate(_array(value, path)))
    if len(set(result)) != len(result):
        _fail("DUPLICATE_ID", path)
    return tuple(sorted(result))


def _app_id(value, path):
    value = _text(value, path)
    if not re.fullmatch(_SEGMENT, value):
        _fail("INVALID_NAMESPACE", path)
    return value


def _namespaced(value, app_id, path):
    value = _text(value, path)
    if not re.fullmatch(re.escape(app_id) + rf"\.{_SEGMENT}(?:\.{_SEGMENT})*", value):
        _fail("INVALID_NAMESPACE", path)
    return value


def _unique(items, key, path):
    if len({getattr(item, key) for item in items}) != len(items):
        _fail("DUPLICATE_ID", path)
    return tuple(sorted(items, key=lambda item: getattr(item, key)))


def validate_definition(payload, source_id, expected_app_id):
    path = "definition"
    _text(source_id, "source_id")
    expected_app_id = _app_id(expected_app_id, "expected_app_id")
    data = _fields(payload, ("contract_version", "app_id", "definition_revision", "resources", "scopes", "actions", "bindings"), path)
    app_id = _app_id(data["app_id"], f"{path}.app_id")
    if app_id != expected_app_id:
        _fail("SOURCE_MISMATCH", f"{path}.app_id")
    version = _integer(data["contract_version"], f"{path}.contract_version", {1})
    revision = _text(data["definition_revision"], f"{path}.definition_revision")
    resources = []
    for i, item in enumerate(_array(data["resources"], "definition.resources")):
        p = f"definition.resources[{i}]"
        item = _fields(item, ("resource_id", "label"), p)
        resources.append(ResourceDefinition(_namespaced(item["resource_id"], app_id, p + ".resource_id"), _text(item["label"], p + ".label")))
    resources = _unique(resources, "resource_id", "definition.resources")
    scopes = []
    for i, item in enumerate(_array(data["scopes"], "definition.scopes")):
        p = f"definition.scopes[{i}]"
        item = _fields(item, ("scope_type", "schema_version", "dimension", "reference_type", "allow_descendants"), p)
        scopes.append(ScopeDefinition(
            _namespaced(item["scope_type"], app_id, p + ".scope_type"),
            _integer(item["schema_version"], p + ".schema_version", {1}),
            _text(item["dimension"], p + ".dimension"),
            _namespaced(item["reference_type"], app_id, p + ".reference_type"),
            _boolean(item["allow_descendants"], p + ".allow_descendants"),
        ))
    scopes = _unique(scopes, "scope_type", "definition.scopes")
    resource_ids = {item.resource_id for item in resources}
    scope_ids = {item.scope_type for item in scopes}
    actions = []
    for i, item in enumerate(_array(data["actions"], "definition.actions")):
        p = f"definition.actions[{i}]"
        item = _fields(item, ("action_id", "label", "resource_id", "scope_types", "enabled", "implemented", "status"), p)
        action = ActionDefinition(
            _namespaced(item["action_id"], app_id, p + ".action_id"),
            _text(item["label"], p + ".label"), _text(item["resource_id"], p + ".resource_id"),
            _texts(item["scope_types"], p + ".scope_types"),
            _boolean(item["enabled"], p + ".enabled"), _boolean(item["implemented"], p + ".implemented"),
            _text(item["status"], p + ".status"),
        )
        if action.status not in {"active", "retired"}:
            _fail("INVALID_STATUS", p + ".status")
        if action.resource_id not in resource_ids or not set(action.scope_types) <= scope_ids:
            _fail("UNKNOWN_REFERENCE", p)
        actions.append(action)
    actions = _unique(actions, "action_id", "definition.actions")
    action_map = {item.action_id: item for item in actions}
    bindings = []
    for i, item in enumerate(_array(data["bindings"], "definition.bindings")):
        p = f"definition.bindings[{i}]"
        item = _fields(item, ("binding_key", "action_id", "resource_id", "scope_types"), p)
        key = _text(item["binding_key"], p + ".binding_key")
        # Opaque identifiers only: no executable paths, expressions or SQL.
        if not re.fullmatch(r"[a-z][a-z0-9_]*:[a-z][a-z0-9_.:-]*", key):
            _fail("INVALID_BINDING_KEY", p + ".binding_key")
        binding = EntryBinding(key, _text(item["action_id"], p + ".action_id"), _text(item["resource_id"], p + ".resource_id"), _texts(item["scope_types"], p + ".scope_types"))
        action = action_map.get(binding.action_id)
        if action is None:
            _fail("UNKNOWN_REFERENCE", p + ".action_id")
        if (binding.resource_id, binding.scope_types) != (action.resource_id, action.scope_types):
            _fail("INCOMPATIBLE_BINDING", p)
        bindings.append(binding)
    bindings = _unique(bindings, "binding_key", "definition.bindings")
    if {item.action_id for item in bindings} != set(action_map):
        _fail("MISSING_BINDING", "definition.bindings")
    return AppDefinition(source_id, version, app_id, revision, resources, scopes, actions, bindings)


def _fixed_version(result, known_versions, identity, path):
    for previous in known_versions:
        if identity(previous) == identity(result) and previous != result:
            _fail("VERSION_CONFLICT", path)
    return result


def validate_template_version(payload, registry, known_versions=(), *, historical=False):
    p = "template"
    data = _fields(payload, ("app_id", "template_id", "version", "action_ids"), p)
    app_id = _app_id(data["app_id"], p + ".app_id")
    app = registry.apps.get(app_id)
    if app is None:
        _fail("UNKNOWN_REFERENCE", p + ".app_id")
    template_id = _text(data["template_id"], p + ".template_id")
    version = _integer(data["version"], p + ".version")
    action_ids = _texts(data["action_ids"], p + ".action_ids")
    actions = {item.action_id: item for item in app.actions}
    unavailable = []
    for action_id in action_ids:
        _namespaced(action_id, app_id, p + ".action_ids")
        if action_id not in actions:
            _fail("UNKNOWN_REFERENCE", p + ".action_ids")
        if not actions[action_id].declared_available:
            unavailable.append(action_id)
    if unavailable and not historical:
        _fail("UNAVAILABLE_ACTION", p + ".action_ids")
    result = TemplateVersion(app_id, template_id, version, action_ids, tuple(unavailable))
    # Availability is an observation of the current directory, not template content.
    identity = lambda t: (t.app_id, t.template_id, t.version)
    for previous in known_versions:
        if identity(previous) == identity(result) and previous.action_ids != result.action_ids:
            _fail("VERSION_CONFLICT", p)
    return result


def validate_role_bundle(payload, templates, known_versions=(), *, historical=False):
    templates = tuple(templates)
    p = "role"
    data = _fields(payload, ("role_id", "version", "components"), p)
    components = []
    for i, item in enumerate(_array(data["components"], p + ".components")):
        q = f"role.components[{i}]"
        item = _fields(item, ("component_id", "app_id", "template_id", "template_version"), q)
        key = (_app_id(item["app_id"], q + ".app_id"), _text(item["template_id"], q + ".template_id"), _integer(item["template_version"], q + ".template_version"))
        matches = [t for t in templates if (t.app_id, t.template_id, t.version) == key]
        if not matches:
            _fail("UNKNOWN_REFERENCE", q)
        if any(t != matches[0] for t in matches):
            _fail("VERSION_CONFLICT", q)
        if matches[0].unavailable_action_ids and not historical:
            _fail("UNAVAILABLE_ACTION", q)
        components.append(RoleComponent(_text(item["component_id"], q + ".component_id"), matches[0]))
    result = RoleBundleVersion(_text(data["role_id"], p + ".role_id"), _integer(data["version"], p + ".version"), _unique(components, "component_id", p + ".components"))
    return _fixed_version(result, known_versions, lambda r: (r.role_id, r.version), p)


def validate_position_binding(payload, role, registry, positions, known_versions=(), *, historical=False):
    p = "binding"
    data = _fields(payload, ("binding_id", "version", "position_id", "role_id", "role_version", "component_scopes"), p)
    role_id = _text(data["role_id"], p + ".role_id")
    role_version = _integer(data["role_version"], p + ".role_version")
    if (role_id, role_version) != (role.role_id, role.version):
        _fail("UNKNOWN_REFERENCE", p + ".role_id")
    position_id = _text(data["position_id"], p + ".position_id")
    if position_id not in {position.position_id for position in positions}:
        _fail("UNKNOWN_REFERENCE", p + ".position_id")
    expected = {}
    for component in role.components:
        app = registry.apps.get(component.template.app_id)
        if app is None:
            _fail("UNKNOWN_REFERENCE", p + ".component_scopes")
        actions = {a.action_id: a for a in app.actions}
        for action_id in component.template.action_ids:
            action = actions.get(action_id)
            if action is None:
                _fail("UNKNOWN_REFERENCE", p + ".component_scopes")
            if not action.declared_available and not historical:
                _fail("UNAVAILABLE_ACTION", p + ".component_scopes")
            for scope_type in action.scope_types:
                expected[(component.component_id, scope_type)] = next(s for s in app.scopes if s.scope_type == scope_type)
    scopes = []
    seen = set()
    for i, item in enumerate(_array(data["component_scopes"], p + ".component_scopes")):
        q = f"binding.component_scopes[{i}]"
        item = _fields(item, ("component_id", "scope_type", "schema_version", "dimension", "reference_type", "reference_ids", "include_descendants"), q)
        component_id = _text(item["component_id"], q + ".component_id")
        scope_type = _text(item["scope_type"], q + ".scope_type")
        key = (component_id, scope_type)
        schema = expected.get(key)
        if schema is None:
            _fail("UNKNOWN_REFERENCE", q)
        if key in seen:
            _fail("DUPLICATE_ID", q)
        seen.add(key)
        version = _integer(item["schema_version"], q + ".schema_version", {schema.schema_version})
        dimension = _text(item["dimension"], q + ".dimension")
        ref_type = _text(item["reference_type"], q + ".reference_type")
        if (dimension, ref_type) != (schema.dimension, schema.reference_type):
            _fail("INCOMPATIBLE_SCOPE", q)
        descendants = _boolean(item["include_descendants"], q + ".include_descendants")
        if descendants and not schema.allow_descendants:
            _fail("DESCENDANTS_NOT_ALLOWED", q + ".include_descendants")
        scopes.append(ScopeSelection(component_id, scope_type, version, dimension, ref_type, _texts(item["reference_ids"], q + ".reference_ids"), descendants))
    if seen != set(expected):
        _fail("MISSING_SCOPE", p + ".component_scopes")
    result = PositionBinding(_text(data["binding_id"], p + ".binding_id"), _integer(data["version"], p + ".version"), position_id, role_id, role_version, tuple(sorted(scopes, key=lambda s: (s.component_id, s.scope_type))))
    return _fixed_version(result, known_versions, lambda b: (b.binding_id, b.version), p)


def _source_ref(payload, path):
    data = _fields(payload, ("source_type", "source_id"), path)
    return SourceRef(_text(data["source_type"], path + ".source_type"), _text(data["source_id"], path + ".source_id"))


def _status(value, path):
    value = _text(value, path)
    if value not in {"active", "inactive", "revoked"}:
        _fail("INVALID_STATUS", path)
    return value


def validate_position_projection(payload):
    p = "position"
    data = _fields(payload, ("position_id", "department_ref", "label", "status", "revision"), p)
    return PositionProjection(_text(data["position_id"], p + ".position_id"), _source_ref(data["department_ref"], p + ".department_ref"), _text(data["label"], p + ".label"), _status(data["status"], p + ".status"), _integer(data["revision"], p + ".revision"))


def _time(value, path):
    if not isinstance(value, str):
        _fail("INVALID_TIME", path)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        _fail("INVALID_TIME", path)
    if result.tzinfo is None or result.utcoffset() is None:
        _fail("TIMEZONE_REQUIRED", path)
    return result


def validate_assignment_projection(payload, positions):
    p = "assignment"
    data = _fields(payload, ("assignment_id", "person_ref", "subject_user", "position_id", "is_primary", "valid_from", "valid_until", "status", "revision", "authorization_generation", "qualification_status"), p)
    position_id = _text(data["position_id"], p + ".position_id")
    if position_id not in {position.position_id for position in positions}:
        _fail("UNKNOWN_REFERENCE", p + ".position_id")
    qualification = _text(data["qualification_status"], p + ".qualification_status")
    if qualification not in {"unknown", "unlinked", "ambiguous", "verified"}:
        _fail("INVALID_QUALIFICATION", p + ".qualification_status")
    subject = data["subject_user"]
    if subject is not None:
        subject = _text(subject, p + ".subject_user")
    if (qualification == "verified" and subject is None) or (qualification in {"unlinked", "ambiguous"} and subject is not None):
        _fail("INCONSISTENT_QUALIFICATION", p + ".subject_user")
    start = _time(data["valid_from"], p + ".valid_from")
    end = None if data["valid_until"] is None else _time(data["valid_until"], p + ".valid_until")
    if end is not None and start >= end:
        _fail("INVALID_INTERVAL", p + ".valid_until")
    return AssignmentProjection(
        _text(data["assignment_id"], p + ".assignment_id"), _source_ref(data["person_ref"], p + ".person_ref"), subject,
        position_id, _boolean(data["is_primary"], p + ".is_primary"), start, end,
        _status(data["status"], p + ".status"), _integer(data["revision"], p + ".revision"),
        _integer(data["authorization_generation"], p + ".authorization_generation"), qualification,
    )


def validate_assignment_set(payloads, positions):
    positions = tuple(positions)
    assignments = tuple(validate_assignment_projection(item, positions) for item in _array(payloads, "assignments", nonempty=False))
    _unique(assignments, "assignment_id", "assignments")
    for i, current in enumerate(assignments):
        for other in assignments[:i]:
            if current.person_ref != other.person_ref or current.status != "active" or other.status != "active":
                continue
            overlap = (other.valid_until is None or current.valid_from < other.valid_until) and (current.valid_until is None or other.valid_from < current.valid_until)
            if overlap and current.position_id == other.position_id:
                _fail("DUPLICATE_ASSIGNMENT", f"assignments[{i}]")
            if overlap and current.is_primary and other.is_primary:
                _fail("OVERLAPPING_PRIMARY", f"assignments[{i}]")
    return AssignmentSet(tuple(sorted(assignments, key=lambda a: a.assignment_id)))
