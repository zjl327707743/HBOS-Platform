"""Restore only the hash-reviewed clean rehearsal Site with official Frappe code."""
import hashlib,json,os,re
from pathlib import Path
import frappe
from frappe.commands.site import _restore
site=os.environ['HBOS_SITE'];project=os.environ['HBOS_SMOKE_PROJECT']
if not re.fullmatch(r'hbos-uat2-smoke-[a-z0-9-]+',project) or not re.fullmatch(r'uat2-smoke-[a-z0-9-]+\.localhost',site):
    raise SystemExit('Rollback is restricted to the explicitly isolated rehearsal target')
os.chdir('/home/frappe/frappe-bench/sites');directory=Path(site)/'private/backups'
raw=(directory/'joint-backup-lock.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=os.environ['HBOS_BACKUP_LOCK_SHA256']:raise SystemExit('Backup lock hash mismatch')
lock=json.loads(raw)
if lock['site']!=site:raise SystemExit('Backup belongs to another Site')
for name,digest in lock['files'].items():
    if Path(name).name!=name:raise SystemExit('Unsafe backup name')
    p=directory/name
    if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit('Backup file hash mismatch')
def selected(suffix):
    items=[directory/n for n in lock['files'] if n.endswith(suffix)]
    if len(items)!=1:raise SystemExit('Exactly one reviewed backup is required: '+suffix)
    return items[0]
db=selected('-database.sql.gz');config=selected('-site_config_backup.json')
current=Path(site)/'site_config.json';old=json.loads(config.read_text());now=json.loads(current.read_text())
if any(old.get(k)!=now.get(k) for k in ('db_name','db_user','db_host','db_type','encryption_key')):
    raise SystemExit('Site identity/config changed; isolated rollback requires review')
public=[directory/n for n in lock['files'] if n.endswith(('-files.tar','-files.tar.gz')) and '-private-files.' not in n]
private=[directory/n for n in lock['files'] if n.endswith(('-private-files.tar','-private-files.tar.gz'))]
if len(public)!=1 or len(private)!=1:raise SystemExit('Complete file backup required')
frappe.init(site=site)
_restore(site=site,sql_file_path=str(db.resolve()),db_root_username='root',
    db_root_password=Path('/run/secrets/db-root-password').read_text().strip(),
    force=False,with_public_files=str(public[0].resolve()),with_private_files=str(private[0].resolve()))
current.write_text(json.dumps(old,indent=2)+'\n');current.chmod(0o600)
frappe.destroy();frappe.init(site=site);frappe.connect()
assert 'hb_knowledge_app' in frappe.get_installed_apps()
assert frappe.db.count('HBOS Knowledge Document')==0
marker=os.environ.get('HBOS_ROLLBACK_MARKER')
if marker:
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,140}',marker):raise SystemExit('Invalid rehearsal marker')
    assert not frappe.db.exists('Comment',marker),'Rehearsal marker survived DB restore'
frappe.destroy()
print('ISOLATED_DATABASE_CONFIG_FILES_ROLLBACK_PASS; company and RAGFlow data untouched')
