"""Keep protected organization records out of ordinary native entry points.

Controlled repositories use fixed, root-locked SQL and their own current policy
checks. Native roles, shares, Administrator and client flags do not substitute
for that capability. This guard does not take over the ERP/HR personnel domain
or inspect arbitrary trusted application SQL.
"""
import json
from urllib.parse import unquote

from .storage_schema import (
    ASSIGNMENT, ASSIGNMENT_REVISION, POSITION, POSITION_REVISION, RECEIPT, WRITE_LOCK,
)
from .management_storage import POLICY, POLICY_REVISION
from .write_guard import is_controlled_write

PROTECTED_DOCTYPES = frozenset((
    POSITION, POSITION_REVISION, ASSIGNMENT, ASSIGNMENT_REVISION, RECEIPT, WRITE_LOCK,
    POLICY, POLICY_REVISION,
))
_SLUGS = frozenset(kind.lower().replace(" ", "-") for kind in PROTECTED_DOCTYPES)
DENIAL_MESSAGE = "请使用受控人员与权限接口查看或维护这些记录。"


def protected_doctypes():
    return PROTECTED_DOCTYPES


def _deny(native=None):
    if native is None:
        import frappe as native
    raise native.PermissionError(DENIAL_MESSAGE)


def deny_native_permission(doc=None, ptype=None, user=None, doctype=None, **kwargs):
    # Return False rather than None: native hooks cannot infer an allowance.
    return False


def deny_native_query(user=None, doctype=None):
    # A false SQL predicate is insufficient: native shared rows can be OR'ed
    # outside permission_query_conditions, and the no-role share path skips it.
    _deny()


class NativeReadProtectedDocument:
    """Check before Document's Administrator / ignore_permissions shortcuts."""
    def has_permission(self, permtype="read", *, debug=False, user=None):
        # Existing trusted repositories save/insert inside a private capability.
        # Insert checks create before autoname; only its exact record_key may
        # supply the future name. Any populated name must match that key.
        name, key = self.name, self.get("record_key")
        return bool(permtype in ("create", "write") and key
                    and (not name or name == key)
                    and is_controlled_write(self.doctype, name or key))

    def check_permission(self, permtype="read", permlevel=None):
        if not self.has_permission(permtype):
            _deny()


def _contains_protected(value):
    """Bounded JSON/document classification, without evaluating client input."""
    remaining = 1024

    def visit(item, depth):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > 12:
            raise ValueError("classification limit")
        if isinstance(item, dict):
            return any(visit(key, depth + 1) or visit(val, depth + 1) for key, val in item.items())
        if isinstance(item, (list, tuple)):
            return any(visit(val, depth + 1) for val in item)
        if isinstance(item, str):
            if len(item) > 65536:
                raise ValueError("classification limit")
            text = item.strip()
            if text in PROTECTED_DOCTYPES or any("tab" + kind in text for kind in PROTECTED_DOCTYPES):
                return True
            if text.startswith(("{", "[")):
                return visit(json.loads(text), depth + 1)
        return False

    return visit(value, 0)


def _protected_report(name, resolver):
    if not isinstance(name, str) or not name or resolver is None:
        return True
    visited = set()
    for _ in range(8):
        if name in visited:
            return True
        visited.add(name)
        report = resolver(name)
        if not isinstance(report, dict):
            return True
        if (not isinstance(report.get("ref_doctype"), str) or not report["ref_doctype"]
                or report.get("report_type") not in ("Custom Report", "Query Report", "Script Report", "Report Builder")):
            return True
        if report["ref_doctype"] in PROTECTED_DOCTYPES:
            return True
        if report.get("report_type") != "Custom Report":
            return False
        name = report.get("reference_report")
        if not isinstance(name, str) or not name:
            return True
    return True


def is_protected_request(path, params, report_resolver=None):
    """Classify native REST/RPC/Desk inputs before native dispatch.

Only the eight protected DocTypes are closed. Fixed custom services continue
to enforce their separate capabilities. Malformed known-native inputs and
unresolvable report references fail closed; no raw query is executed here.
"""
    if not isinstance(path, str) or not isinstance(params, dict):
        return True
    segments = unquote(path).strip("/").split("/")
    if len(segments) >= 2 and segments[0] in ("desk", "app") and segments[1] in _SLUGS:
        return True
    target = None
    if segments[:2] == ["api", "resource"] and len(segments) >= 3:
        target = segments[2]
    elif segments[:3] == ["api", "v1", "resource"] and len(segments) >= 4:
        target = segments[3]
    elif segments[:3] in (["api", "v2", "document"], ["api", "v2", "doctype"]) and len(segments) >= 4:
        target = segments[3]
    if target in PROTECTED_DOCTYPES:
        return True

    # Native cmd takes precedence over the route, including a cmd on '/'.
    command = params.get("cmd")
    if command is None:
        if segments[:2] == ["api", "method"] and len(segments) >= 3:
            command = segments[2]
        elif segments[:3] in (["api", "v1", "method"], ["api", "v2", "method"]) and len(segments) >= 4:
            if len(segments) >= 5 and segments[3] in PROTECTED_DOCTYPES:
                return True
            command = segments[3]
    if command is not None and not isinstance(command, str):
        return True
    # REST of a different DocType may still submit a protected nested document
    # or explicitly refer to a protected table through fields/filters.
    native_entry = target is not None or bool(command and (
        command.startswith("frappe.") or command in ("run_doc_method", "runserverobj")))
    if not native_entry:
        return False
    try:
        if _contains_protected(params):
            return True
        if command and command.startswith("frappe.desk.query_report."):
            return _protected_report(params.get("report_name"), report_resolver)
    except Exception:
        return True
    return False


def before_request(native=None):
    if native is None:
        import frappe as native
    request = native.local.request

    def resolve_report(name):
        # Fixed metadata fields only. Do not execute a report or read its SQL.
        rows = native.db.sql(
            "SELECT ref_doctype,report_type,reference_report FROM `tabReport` WHERE name=%s",
            (name,), as_dict=True,
        )
        return dict(rows[0]) if len(rows) == 1 else None

    try:
        denied = is_protected_request(request.path, dict(native.form_dict), resolve_report)
    except Exception:
        # Report metadata/source failure must never turn into permission.
        denied = True
    if denied:
        _deny(native)
