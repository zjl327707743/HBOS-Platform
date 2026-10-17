"""Apply Owner-approved private domain config without writing User roles."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

import frappe

parser = argparse.ArgumentParser()
parser.add_argument("--site", required=True)
parser.add_argument("--bench", required=True)
parser.add_argument("--expected-database", required=True)
parser.add_argument("--private-config", required=True)
args = parser.parse_args()
path = Path(args.private_config)
info = path.lstat()
if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid() or info.st_size > 128 * 1024:
    raise SystemExit("私下批准配置须为当前用户所有的普通 0600 文件")
config = json.loads(path.read_text())
os.chdir(Path(args.bench) / "sites")
frappe.init(site=args.site); frappe.connect()
try:
    if hashlib.sha256(str(frappe.conf.db_name).encode()).hexdigest() != args.expected_database:
        raise RuntimeError("目标与已确认数据库不一致")
    allowed = {"hbos_knowledge_policy", "hbos_twin_policy", "hbos_twin_asset_root", "hbos_knowledge_gateway_url", "hbos_knowledge_gateway_client_id"}
    if not set(config) <= allowed | {"gateway_token_file"}:
        raise RuntimeError("配置含未经支持的字段")
    from hbos_portal.auth.feishu import _store_protected_text
    token_path = Path(config["gateway_token_file"])
    metadata = token_path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077 or metadata.st_uid != os.geteuid():
        raise RuntimeError("Gateway token 文件权限无效")
    token = token_path.read_text().strip()
    if not 32 <= len(token) <= 512 or any(c.isspace() for c in token):
        raise RuntimeError("Gateway token 格式无效")
    _store_protected_text(Path(frappe.get_site_path("private", "hbos_knowledge_gateway_token")), token)
    from frappe.installer import update_site_config
    for key in allowed & set(config):
        update_site_config(key, config[key])
    print("私下批准的知识/设备配置已保存，未修改 User 或角色；重启后验证真实检索及模型。")
finally:
    frappe.destroy()
