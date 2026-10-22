"""Bounded cross-application native role API. Authentication is the Frappe session."""
from __future__ import annotations

import frappe

from hbos_portal.iam import app_roles


def _only(kwargs, fields=()):
    wire = getattr(frappe, "form_dict", None) or {}
    if set(kwargs) - {"cmd"} or set(wire) - set(fields) - {"cmd"}:
        frappe.throw("请求含有未允许的字段。", frappe.ValidationError)


def _call(function, *, read_only=False):
    try:
        if frappe.conf.get("hbos_iam_enabled") not in (True, 1, "1"):
            frappe.throw("此站点尚未启用IAM管理。", frappe.PermissionError)
        from hbos_portal.iam import policy

        return {"ok": True, "data": policy.current_read(function) if read_only else function()}
    except Exception as exc:
        status = frappe.local.response.get("http_status_code")
        if isinstance(exc, frappe.AuthenticationError):
            status, code, message = 403, "PROOF_REQUIRED", "请重新验证本人密码及已有二次认证。"
        elif isinstance(exc, frappe.PermissionError):
            status, code, message = 403, "FORBIDDEN", str(exc)
        elif isinstance(exc, (frappe.QueryDeadlockError, frappe.QueryTimeoutError, frappe.TimestampMismatchError)) or status == 409:
            status, code, message = 409, "CONFLICT", "资料或权限已变化，本次未保存，请重新读取。"
        elif isinstance(exc, (frappe.ValidationError, ValueError, TypeError)):
            status, code, message = 400, "INVALID_REQUEST", str(exc)
        else:
            status, code, message = 500, "SERVICE_ERROR", "操作暂时无法完成，未保留部分更新，请稍后重试。"
            frappe.logger("hbos_iam").error("App role service failure (%s)", type(exc).__name__)
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = status
        return {"ok": False, "error": {"code": code, "message": message, "retryable": status in {409, 500}}}


@frappe.whitelist(methods=["GET"])
def describe(employee_id, **kwargs):
    def run():
        _only(kwargs, ("employee_id",))
        return app_roles.describe(employee_id)

    return _call(run, read_only=True)


@frappe.whitelist(methods=["POST"])
def preview(employee_id, app_id, roles, expected_version, acknowledged_global_scope=False, **kwargs):
    def run():
        _only(kwargs, ("employee_id", "app_id", "roles", "expected_version", "acknowledged_global_scope"))
        return app_roles.preview(employee_id, app_id, roles, expected_version, acknowledged_global_scope is True)

    return _call(run, read_only=True)


@frappe.whitelist(methods=["POST"])
def save(employee_id, app_id, roles, expected_version, context_revision, request_id, acknowledged_global_scope=False, **kwargs):
    def run():
        _only(kwargs, ("employee_id", "app_id", "roles", "expected_version", "context_revision", "request_id", "acknowledged_global_scope"))
        return app_roles.save(employee_id, app_id, roles, expected_version, context_revision, request_id, acknowledged_global_scope is True)

    return _call(run)
