"""Hash the complete latest isolated Site backup; never export config contents."""
import hashlib,json,os,re
from pathlib import Path
site=os.environ['HBOS_SITE']
if not re.fullmatch(r'uat2-smoke-[a-z0-9-]+\.localhost',site):raise SystemExit('Isolated Site required')
directory=Path('/home/frappe/frappe-bench/sites')/site/'private/backups'
database=max(directory.glob('*-database.sql.gz'),key=lambda p:p.stat().st_mtime)
prefix=database.name.removesuffix('-database.sql.gz')
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob(prefix+'-*') if p.is_file() and not p.is_symlink()}
assert any(n.endswith('-site_config_backup.json') for n in files)
assert any(n.endswith('-files.tar') or n.endswith('-files.tar.gz') for n in files)
assert any(n.endswith('-private-files.tar') or n.endswith('-private-files.tar.gz') for n in files)
raw=(json.dumps({'site':site,'files':files},indent=2)+'\n').encode()
path=directory/'joint-backup-lock.json';path.write_bytes(raw);path.chmod(0o600)
print(json.dumps({'backup_lock_sha256':hashlib.sha256(raw).hexdigest(),'backup_files':files}))
