"""Bulk-export authorization boundary for the self-service population.

Why this module exists
----------------------
``frappe.desk.reportview.export_query`` is authorized by
``frappe.permissions.can_export``, which consults **only** the ``export`` bit of
the caller's effective role permissions::

    def can_export(doctype, raise_exception=False, is_owner=False):
        if "System Manager" in frappe.get_roles():
            return True
        role_permissions = frappe.permissions.get_role_permissions(doctype, is_owner=is_owner)
        has_access = role_permissions.get("export") or role_permissions.get("if_owner").get("export")
        ...

It never consults ``read``, so an ``export`` bit that outlives the ``read`` bit
it was derived from silently becomes a bulk-extraction licence.

``Custom DocPerm.export`` defaults to ``"1"`` (see
``frappe/core/doctype/custom_docperm/custom_docperm.json``), while the HRMS user
type provisioning that mints self-service permissions never writes the flag --
``UserType.add_role_permissions_for_user_doctypes`` passes only ``read``,
``write``, ``create``, ``submit``, ``cancel``, ``amend``, ``delete``, ``print``,
``email`` and ``share``. Rows minted for a Link target carry ``read=0,
select=1`` and silently keep the default ``export=1``.

Measured on the IAM isolation lab, a plain employee-held role set could therefore
bulk-export the whole ``User`` (17/17 rows), ``Role`` (59/59), ``Account``
(96/192), ``Country`` (250), ``Currency`` (149), ``Designation`` (31),
``Department``, ``Warehouse``, ``Salary Component`` ... tables through the
ordinary Desk export endpoint, and could enumerate other users' private
``File`` names because the export path does not re-apply the owner scoping that
the read path enforces.

The boundary enforced here
--------------------------
1. A role may not export what it may not read: ``read=0`` implies ``export=0``.
2. Doctypes whose *read* path is owner/permission scoped, or whose contents are
   organisation-wide payroll/config masters, are not bulk-exportable by the
   self-service population even when ``read`` is granted.

``read``, ``select`` and ``write`` are never touched, so Link pickers, normal
business reads and self-service authoring keep working. Nothing in ``frappe`` or
``hrms`` is patched.

Durability
----------
``after_migrate`` alone is not sufficient. ``UserType.on_update`` regenerates
``Custom DocPerm`` through ``add_role_permissions_for_user_doctypes``,
``add_role_permissions_for_select_doctypes`` and ``add_role_permissions_for_file``
-- none of which writes ``export`` -- so every row those helpers (re)create
inherits ``Custom DocPerm.export``'s JSON default of ``1``. A plain "open the
Employee Self Service user type and press Save" therefore re-opens the bulk-export
door *between* two migrations.

``on_user_type_update`` closes that window by re-asserting the same boundary from
a ``User Type`` ``on_update`` doc event. Frappe composes the controller's own
``on_update`` with the registered ``doc_events`` handlers and runs the controller
method first (``frappe/model/document.py``: ``hook`` -> ``compose`` -> ``runner``
calls ``fn(self)`` before iterating ``hooks``), so the regeneration always lands
before this handler and this handler is the last writer.

Do not import ``frappe`` at module scope: the contract tests exercise
:func:`plan_export_denials` as pure Python.
"""

from __future__ import annotations

#: Roles a self-service employee necessarily holds. HRMS adds ``Employee`` to the
#: linked User (``Employee.validate_employee_role``) and Frappe grants ``All`` to
#: every account, so binding only ``Employee Self Service`` would leave the same
#: ``export`` bit reachable through a sibling role.
BOUND_ROLES = ("Employee Self Service", "Employee", "All")

#: Doctypes that stay bulk-exportable to the self-service population only by
#: accident. Each entry is backed by a measurement in X02-RUNTIME-MATRIX.md.
SENSITIVE_EXPORT_DENIED = (
    # read=1, but read is owner-scoped while export applies no owner filter:
    # the subject exported both private files owned by other users.
    "File",
    # Organisation-wide payroll calendar / withholding configuration.
    "Payroll Period",
    "Salary Withholding",
    # Shift masters: read=0 for Employee Self Service, read=1 for Employee.
    "Shift Type",
)

#: Human-readable reasons, also used by the runtime evidence matrix.
REASON_EXPORT_WITHOUT_READ = "export_without_read"
REASON_SENSITIVE_DOCTYPE = "sensitive_doctype"


def plan_export_denials(rows, roles=BOUND_ROLES, sensitive=None):
    """Return the permission rows whose ``export`` bit must be withdrawn.

    ``rows`` are permission mappings carrying at least ``name``, ``role``,
    ``parent``, ``read`` and ``export``. Pure function: no database access.
    """
    bound = set(roles)
    sensitive = set(SENSITIVE_EXPORT_DENIED if sensitive is None else sensitive)

    plan = []
    for row in rows or ():
        if not row.get("export"):
            continue
        if row.get("role") not in bound:
            continue
        parent = row.get("parent")
        if not row.get("read"):
            reason = REASON_EXPORT_WITHOUT_READ
        elif parent in sensitive:
            reason = REASON_SENSITIVE_DOCTYPE
        else:
            continue
        plan.append(
            {
                "name": row.get("name"),
                "role": row.get("role"),
                "parent": parent,
                "read": int(row.get("read") or 0),
                "select": int(row.get("select") or 0),
                "reason": reason,
            }
        )
    return plan


def denied_doctypes(plan):
    """Sorted doctype names covered by a denial plan."""
    return sorted({item["parent"] for item in plan})


def enforce_sensitive_export_boundary():
    """Re-assert the boundary and report what changed.

    Idempotent: safe to run on every migrate. Fails loudly rather than silently
    leaving an escalated ``export`` bit in place.
    """
    import frappe

    rows = frappe.get_all(
        "Custom DocPerm",
        filters={"role": ("in", list(BOUND_ROLES)), "export": 1},
        # Every field the planner reads must be selected as well as filtered:
        # a missing key would silently plan nothing.
        fields=["name", "role", "parent", "read", "select", "export", "if_owner"],
        limit_page_length=0,
    )
    plan = plan_export_denials(rows)

    for item in plan:
        frappe.db.set_value("Custom DocPerm", item["name"], "export", 0, update_modified=False)

    if plan:
        # Role permissions are cached; running workers must observe the change.
        frappe.clear_cache()

    residual = _residual_rows(frappe)
    if residual:
        frappe.throw(
            "自助角色仍持有不合理的高权限导出位，已中止："
            + ", ".join(sorted(residual))
        )

    return {
        "roles": list(BOUND_ROLES),
        "examined": len(rows),
        "denied": len(plan),
        "doctypes": denied_doctypes(plan),
        "by_role": _count_by_role(plan),
        "reasons": sorted({item["reason"] for item in plan}),
    }


def on_user_type_update(doc, method=None):
    """Re-assert the export boundary whenever a ``User Type`` is saved.

    Registered as ``doc_events["User Type"]["on_update"]``. ``UserType.on_update``
    regenerates ``Custom DocPerm`` rows whose ``export`` flag is never written by
    the HRMS provisioning helpers, so those rows fall back to the
    ``Custom DocPerm.export`` default of ``1``. That makes the boundary
    re-openable by an ordinary User Type save, which ``after_migrate`` cannot
    prevent because it only runs at migrate time.

    Frappe runs the controller's own ``on_update`` *before* the ``doc_events``
    handlers (``frappe/model/document.py``: ``hook`` -> ``compose`` -> ``runner``),
    so this handler executes after the regeneration and is the last writer.

    There is deliberately **one** policy implementation: this delegates to
    :func:`enforce_sensitive_export_boundary` rather than restating the rules.
    That function writes only through ``frappe.db.set_value("Custom DocPerm", ...)``
    and never saves a ``User Type``, so no ``on_update`` recursion is possible.
    Failing loudly is intentional: an unsatisfiable post-condition must abort the
    save rather than leave an escalated ``export`` bit in place.
    """
    result = enforce_sensitive_export_boundary()
    return {"export_policy": result}


def _count_by_role(plan):
    counts = {}
    for item in plan:
        counts[item["role"]] = counts.get(item["role"], 0) + 1
    return counts

def _residual_rows(frappe_module):
    """Post-condition: within the bound roles no export bit may outlive read, and
    none may remain on a sensitive doctype."""
    residual = frappe_module.get_all(
        "Custom DocPerm",
        filters={"role": ("in", list(BOUND_ROLES)), "export": 1, "read": 0},
        pluck="parent",
        limit_page_length=0,
    )
    residual += frappe_module.get_all(
        "Custom DocPerm",
        filters={
            "role": ("in", list(BOUND_ROLES)),
            "export": 1,
            "parent": ("in", list(SENSITIVE_EXPORT_DENIED)),
        },
        pluck="parent",
        limit_page_length=0,
    )
    return sorted(set(residual))
