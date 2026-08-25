# -*- coding: utf-8 -*-
"""飞书 OAuth 登录。

飞书 OAuth 2.0（OIDC 授权码模式）与标准 OAuth2 有两处不同：
1. 授权页参数名是 ``app_id``（不是 ``client_id``）
2. 换 token 前要先调 ``app_access_token`` 接口，再用 ``Bearer`` 头换用户 token

Frappe 自带的 ``login_via_oauth2`` 走标准 client_secret 换 token，不适用于飞书，
因此本模块单独实现飞书的授权跳转 + token 交换。

身份匹配策略（对齐 M1-R0/M1-R7 设计）：
- 以飞书稳定 ID（``union_id`` 优先，``open_id`` 兜底）作为用户唯一键，
  存入 Frappe User 的 ``social_logins`` 子表（provider=feishu）。
- ``contact:user.base:readonly`` 即返回 union_id/open_id/name/avatar，因此
  **不强制要求** ``contact:user.email:readonly``；若飞书返回了邮箱则优先用邮箱
  作为 User 标识（便于与既有 User 匹配）。

密钥读取：环境变量 ``FEISHU_APP_ID`` / ``FEISHU_APP_SECRET``（docker-compose 已注入）。
"""
import base64
import json
import os
from urllib.parse import quote

import frappe
import requests
from frappe.utils import get_url

FEISHU_BASE = "https://open.feishu.cn"
PROVIDER = "feishu"
# 临时默认角色：用于让飞书用户能进入 Desk（无 Employee 匹配时）。
# 注意：ERPNext 会在 User validate 时自动移除无 Employee 映射的 "Employee" /
# "Employee Self Service" 角色，因此未做「飞书→员工」匹配前不能授予这两个角色。
# 待实现飞书身份→Employee 匹配后，应改回 "Employee Self Service"。
DEFAULT_ROLE = "Desk User"


def _credentials():
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        frappe.throw("未配置飞书登录密钥：请设置 FEISHU_APP_ID / FEISHU_APP_SECRET")
    return app_id, app_secret


def _callback_url():
    return get_url("/api/method/hb_attendance_app.feishu_login.callback")


@frappe.whitelist(allow_guest=True)
def redirect(redirect_to=None):
    """跳转飞书授权页（登录按钮指向这里）。"""
    app_id, _ = _credentials()
    state = {
        "site": get_url(),
        "token": frappe.generate_hash(),
        "redirect_to": redirect_to,
    }
    state_b64 = base64.b64encode(json.dumps(state).encode("utf-8")).decode("utf-8")
    authorize_url = (
        f"{FEISHU_BASE}/open-apis/authen/v1/authorize"
        f"?app_id={quote(app_id)}"
        f"&redirect_uri={quote(_callback_url())}"
        f"&state={quote(state_b64)}"
    )
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = authorize_url


def _get_app_access_token():
    app_id, app_secret = _credentials()
    resp = requests.post(
        f"{FEISHU_BASE}/open-apis/auth/v3/app_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        frappe.throw(f"获取飞书 app_access_token 失败：{data.get('msg')}")
    return data["app_access_token"]


def _get_user_info(code):
    app_token = _get_app_access_token()
    resp = requests.post(
        f"{FEISHU_BASE}/open-apis/authen/v1/oidc/access_token",
        headers={"Authorization": f"Bearer {app_token}"},
        json={"grant_type": "authorization_code", "code": code},
        timeout=10,
    )
    token_data = resp.json()
    if token_data.get("code") != 0:
        frappe.throw(f"飞书换取用户 token 失败：{token_data.get('msg')}")
    data = token_data.get("data", {})

    # 若已申请用户信息权限，oidc 返回里可能已带 name/avatar/email/mobile
    if data.get("name") and (data.get("avatar_url") or data.get("avatar_big")):
        return data

    user_token = data.get("access_token")
    resp2 = requests.get(
        f"{FEISHU_BASE}/open-apis/authen/v1/user_info",
        headers={"Authorization": f"Bearer {user_token}"},
        timeout=10,
    )
    user_data = resp2.json()
    if user_data.get("code") != 0:
        frappe.throw(f"获取飞书用户信息失败：{user_data.get('msg')}")
    return user_data.get("data", {})


def _find_or_create_user(feishu_id, name, avatar, email):
    """按飞书 ID 找/建 Frappe User，返回 User 文档。

    优先级：飞书 ID 已绑定 → 邮箱已存在 → 新建（邮箱缺省时用合成邮箱）。
    """
    user_email = None

    # 1. 已绑定过飞书 ID
    linked = frappe.db.get_value(
        "User Social Login", {"provider": PROVIDER, "userid": feishu_id}, "parent"
    )
    if linked and frappe.db.exists("User", linked):
        user_email = linked
    # 2. 飞书返回了真实邮箱，且系统中已存在该邮箱 User
    elif email and frappe.db.exists("User", email):
        user_email = email

    if not user_email:
        user_email = email or f"feishu-{feishu_id}@hbos.local"

    if frappe.db.exists("User", user_email):
        user = frappe.get_doc("User", user_email)
    else:
        user = frappe.new_doc("User")
        user.update(
            {
                "email": user_email,
                "first_name": name or "飞书用户",
                "enabled": 1,
                "user_image": avatar,
                "new_password": frappe.generate_hash(),
            }
        )
        user.flags.ignore_permissions = True
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)

    # 补绑定飞书 ID（幂等）
    if not user.get_social_login_userid(PROVIDER):
        user.append("social_logins", {"provider": PROVIDER, "userid": feishu_id})

    # 确保默认最低权限角色存在（幂等，新老用户都生效，对齐 M1-R0）。
    # user_type 由 has_desk_access() 自动推导：有 desk_access 角色即 System User。
    existing_roles = {d.role for d in user.get("roles")}
    if DEFAULT_ROLE not in existing_roles:
        user.append("roles", {"role": DEFAULT_ROLE})

    user.flags.ignore_permissions = True
    user.save(ignore_permissions=True)

    return user


def _post_login_redirect(state):
    redirect_to = None
    if state:
        try:
            redirect_to = json.loads(base64.b64decode(state).decode("utf-8")).get(
                "redirect_to"
            )
        except Exception:
            redirect_to = None
    return redirect_to or "/app"


@frappe.whitelist(allow_guest=True)
def callback(code=None, state=None):
    """飞书 OAuth 回调：飞书跳回后带 code/state，这里完成登录。"""
    if not code:
        frappe.respond_as_web_page("授权失败", "缺少授权码", http_status_code=400)
        return

    info = _get_user_info(code)

    # 诊断日志：只记录各身份字段「有无」，不记录内容（避免泄露隐私）。
    frappe.log_error(
        "feishu_login fields: "
        f"email={bool(info.get('email') or info.get('enterprise_email'))}, "
        f"union_id={bool(info.get('union_id'))}, "
        f"open_id={bool(info.get('open_id'))}, "
        f"name={bool(info.get('name'))}",
        "feishu_login",
    )

    feishu_id = info.get("union_id") or info.get("open_id")
    if not feishu_id:
        frappe.respond_as_web_page(
            "登录失败", "飞书未返回用户身份标识（open_id/union_id）", http_status_code=400
        )
        return

    email = info.get("email") or info.get("enterprise_email")
    name = info.get("name")
    avatar = info.get("avatar_url") or info.get("avatar_big")

    user = _find_or_create_user(feishu_id, name, avatar, email)

    if not user.enabled:
        frappe.respond_as_web_page("登录失败", "该账号已被禁用", http_status_code=403)
        return

    frappe.local.login_manager.login_as(user.name)
    frappe.db.commit()

    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = _post_login_redirect(state)
