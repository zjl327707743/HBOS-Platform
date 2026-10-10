"""One-time local upgrade after protected backup; ordinary startup never migrates."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import frappe

p = argparse.ArgumentParser()
p.add_argument("--site", required=True)
p.add_argument("--origin", required=True)
p.add_argument("--expected-database", required=True)
p.add_argument("--before", required=True, help="protected preservation manifest from target backup")
p.add_argument("--audit", required=True)
args = p.parse_args()
origin = urlsplit(args.origin)
if origin.scheme != "http" or not (origin.hostname == "localhost" or str(origin.hostname).endswith(".localhost")) or origin.path or origin.query or origin.fragment or origin.username:
    raise SystemExit("仅允许明确的本机 loopback HTTP 配置；服务器使用原 HTTPS 发布工具")
os.umask(0o077)
audit = Path(args.audit)
audit.mkdir(mode=0o700, parents=True, exist_ok=True)
keys = ["database_fingerprint", "user_fingerprint", "credential_fingerprint", "role_fingerprint", "permission_fingerprint", "business_counts", "business_association_fingerprint", "identity_fingerprint"]
before = json.loads(Path(args.before).read_text())
os.chdir("/home/frappe/frappe-bench/sites")
frappe.init(site=args.site); frappe.connect()
try:
    from hbos_portal.auth.site_inventory import inspect
    actual = inspect()
    if actual["database_fingerprint"] != args.expected_database or any(actual[k] != before[k] for k in keys):
        raise RuntimeError("目标或备份后数据改变；没有执行迁移")
    if not actual["csrf_enabled"] or actual["legacy_feishu_social_keys"]:
        raise RuntimeError("认证旁路门禁未通过")
    from frappe.installer import update_site_config
    for key, value in {"host_name": args.origin, "hbos_portal_origin": args.origin,
                       "hbos_knowledge_gateway_url": "http://local-gateway:8080",
                       "hbos_account_test_site": False,
                       "hbos_portal_development_origins": []}.items():
        update_site_config(key, value)
finally:
    frappe.destroy()
with (audit / "migrate.log").open("w") as log:
    subprocess.run(["bench", "--site", args.site, "migrate"], cwd="/home/frappe/frappe-bench", stdout=log, stderr=log, check=True)
frappe.init(site=args.site); frappe.connect()
try:
    from hbos_portal.auth.site_inventory import inspect
    after = inspect()
    (audit / "after.json").write_text(json.dumps(after))
    changed = [k for k in keys if after[k] != before[k]]
    if changed:
        raise RuntimeError("保留核对未通过：" + ", ".join(changed) + "；未自动恢复或清库")
    print("PASS: 目标数据库、用户、密码记录、角色、数据权限、业务关联和身份映射均保留；CSRF 未关闭。")
finally:
    frappe.destroy()
