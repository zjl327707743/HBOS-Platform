"""门户原生页需要的文件上传支持。

## 为什么需要单独一个模块

Frappe 对**非安全方法**（POST/PUT/…）做 CSRF 校验（`frappe/auth.py`
`validate_csrf_token`）。放行条件只有三种：配置 `ignore_csrf`、请求头带的 token
与会话里的一致、或 Referer 命中 `allowed_referrers` 配置——本环境三者都不成立。

Desk 页面之所以能上传，是因为 `frappe.csrf_token` 由 `desk.html` 直接内联下发；
门户是独立的 Vue SPA，拿不到它。故这里补一个**只读**端点把 token 交给已认证的
同源前端——这正是 CSRF token 的本来用途（它对每个 Desk 用户本来就是可见的）。

## 边界

`get_csrf_token` 只读、只回当前会话的 token，不泄漏任何业务数据。
上传本身仍走 Frappe 内置的 `upload_file`，权限与文件类型校验由框架负责，
本模块不重复实现一套。
"""
from __future__ import annotations

import frappe


@frappe.whitelist()
def get_csrf_token():
    """返回当前会话的 CSRF token，供门户发起 POST（如文件上传）。

    必须已登录：未登录会话没有 token 可言，也不该拿到。

    **为什么不做角色限制**：这个 token 是**调用者自己会话**的，Desk 侧对每个
    登录用户本来就通过 `desk.html` 下发同一个值——限制它不构成任何边界。
    真正的权限边界在上传端点自己（`upload_file` / `process_excel` 各自校验），
    在那里拦才有意义。
    """
    if frappe.session.user in (None, "", "Guest"):
        frappe.throw("请先登录", frappe.AuthenticationError)

    from frappe.sessions import get_csrf_token as _generate

    return _generate()
