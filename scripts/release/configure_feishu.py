"""Run with the target bench Python; getpass input never enters argv/logs."""
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

import frappe

from hbos_portal.auth.feishu import discover_enterprise, load_settings, probe_inbox_bot, _site_private_path, _store_protected_text, SECRET_FILENAME, TENANT_FILENAME, _validate_redirect_uri

parser = argparse.ArgumentParser()
parser.add_argument("--site", required=True)
parser.add_argument("--bench", required=True)
parser.add_argument("--app-id", required=True)
parser.add_argument("--origin", required=True)
parser.add_argument("--replace-secret", action="store_true")
parser.add_argument("--enable-inbox-stepup", action="store_true", help="仅在应用机器人及发消息权限批准后启用本人验证码")
parser.add_argument("--enable-disable-sync", action="store_true", help="启用每 5 分钟明确离职/停用状态同步")
args = parser.parse_args()
os.chdir(Path(args.bench) / "sites")
frappe.init(site=args.site); frappe.connect()
try:
    callback = args.origin.rstrip("/") + "/api/method/hbos_portal.auth.feishu.callback"
    if not _validate_redirect_uri(callback):
        raise RuntimeError("服务器入口必须为 HTTPS；本机仅允许 loopback HTTP")
    from frappe.installer import update_site_config
    update_site_config("hbos_feishu_app_id", args.app_id)
    frappe.conf.hbos_feishu_app_id = args.app_id
    settings = load_settings()
    if not settings.app_secret or args.replace_secret:
        value = getpass.getpass("在本机输入现有有效或已轮换的 App Secret：")
        if not 16 <= len(value) <= 512 or any(c.isspace() for c in value):
            raise RuntimeError("Secret 格式无效")
        _store_protected_text(_site_private_path(SECRET_FILENAME), value)
    settings = load_settings()
    company = discover_enterprise(settings)
    print("程序从当前应用核验的企业：", company["name"])
    print("请确认控制台已添加精确回调：", callback)
    print("请确认发布范围仅为本企业内部成员，登录及成员核验权限已批准。")
    already_confirmed = settings.configured and settings.tenant_key == company["tenant_key"] and settings.redirect_uri == callback
    if not already_confirmed and input("输入企业全称确认以上配置：").strip() != company["name"]:
        raise RuntimeError("未确认企业，登录入口仍保持关闭")
    _store_protected_text(_site_private_path(TENANT_FILENAME), company["tenant_key"])
    fields = {"hbos_portal_origin": args.origin.rstrip("/"), "hbos_feishu_redirect_uri": callback, "hbos_feishu_authorize_id_parameter": "client_id", "hbos_feishu_oauth_scopes": "contact:user.base:readonly", "hbos_feishu_app_published": 1, "hbos_feishu_redirect_registered": 1, "hbos_feishu_auto_provision_internal": 1}
    for key, value in fields.items():
        update_site_config(key, value)
    if args.enable_inbox_stepup:
        if not probe_inbox_bot(load_settings()):
            raise RuntimeError("机器人未就绪；未启用收件验证码")
        print("仅启用本人主动请求的安全验证码；不读聊天、不群发。")
        if input("确认 im:message:send_as_bot 已开通并发布，输入 ENABLE SELF INBOX：").strip() != "ENABLE SELF INBOX":
            raise RuntimeError("发送权限未确认；未启用收件验证码")
        update_site_config("hbos_feishu_inbox_recovery_enabled", 1)
    if args.enable_disable_sync:
        update_site_config("hbos_feishu_disable_sync_enabled", 1)
    # Inbox step-up is separately enabled after the bot/send permission works;
    # a new OAuth code alone must never enable password setting.
    print("企业配置已保存；请重启服务，再执行真实网页登录与成员核验。")
finally:
    frappe.destroy()
