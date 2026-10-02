#!/usr/bin/env bash
set -euo pipefail
# Execute inside an already configured production bench/container AFTER backup
# restore verification and reviewed mounts are in place. Never new-site/restore.
SITE="${1:?exact existing Site required}"
EXPECTED_DB="${2:?confirmed database fingerprint required}"
ORIGIN="${3:?fixed HTTPS origin required}"
AUDIT_DIR="${4:?protected audit directory required}"
[[ "$ORIGIN" == https://* ]] || { echo '正式入口须为 HTTPS' >&2; exit 1; }
[[ -f "sites/$SITE/site_config.json" ]] || { echo '既有 Site 不存在，未创建替代库' >&2; exit 1; }
mkdir -p "$AUDIT_DIR"
chmod 700 "$AUDIT_DIR"
umask 077
./env/bin/python - "$SITE" "$EXPECTED_DB" "$AUDIT_DIR" <<'PY'
import hashlib,json,sys
from pathlib import Path
c=json.loads(Path('sites',sys.argv[1],'site_config.json').read_text())
if hashlib.sha256(str(c['db_name']).encode()).hexdigest()!=sys.argv[2]:
 raise SystemExit('数据库与已确认目标不一致，未执行迁移')
audit=Path(sys.argv[3]);verified=json.loads((audit/'restore-verified.json').read_text());prepared=json.loads((audit/'backup-prepared.json').read_text())
if verified['database_restore']!='PASS' or verified.get('account_fingerprints_match')!='PASS' or verified['database_fingerprint']!=sys.argv[2] or hashlib.sha256(Path(prepared['database']).read_bytes()).hexdigest()!=verified['database_backup_sha256']:
 raise SystemExit('当前目标备份恢复验证未通过，未执行迁移')
import os,frappe
os.chdir('sites');frappe.init(site=sys.argv[1]);frappe.connect()
from hbos_portal.auth.site_inventory import inspect
current=inspect();before=json.loads((audit/'before.json').read_text())
for k in ['user_fingerprint','credential_fingerprint','role_fingerprint','permission_fingerprint','business_counts','business_association_fingerprint','identity_fingerprint']:
 if current[k]!=before[k]:raise SystemExit('备份后的目标数据发生变化，请重新备份并验证：'+k)
frappe.destroy()
PY
for app in hb_attendance_app hb_inventory_app hb_lims_app hbos_portal hb_knowledge_app hb_twin_app; do
  if ! bench --site "$SITE" list-apps | awk '{print $1}' | grep -qx "$app"; then
    bench --site "$SITE" install-app "$app" >"$AUDIT_DIR/install-$app.log" 2>&1
  fi
done
bench --site "$SITE" set-config hbos_portal_origin "$ORIGIN"
bench --site "$SITE" set-config host_name "$ORIGIN"
bench --site "$SITE" migrate >"$AUDIT_DIR/migrate.log" 2>&1
bench --site "$SITE" execute hbos_portal.auth.site_inventory.inspect >"$AUDIT_DIR/after.json"
./env/bin/python - "$AUDIT_DIR" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);before=json.loads((root/'before.json').read_text());after=json.loads((root/'after.json').read_text())
for key in ['database_fingerprint','user_fingerprint','credential_fingerprint','role_fingerprint','permission_fingerprint','business_counts','business_association_fingerprint','identity_fingerprint']:
 if before[key]!=after[key]: raise SystemExit('保留校验失败：'+key+'；请按受控回滚说明处置，未自动覆盖数据库')
if not after['csrf_enabled'] or after['legacy_feishu_social_keys']:
 raise SystemExit('认证旁路门禁未通过')
print('原用户、密码验证记录、角色、User Permissions 与业务数量保留校验 PASS')
PY
bench --site "$SITE" clear-cache
echo '迁移完成；重启服务并验证 HTTPS、深链、真实本人登录与五应用。此输出不是正式验收证明。'
