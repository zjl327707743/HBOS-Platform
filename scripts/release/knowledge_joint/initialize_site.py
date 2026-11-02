"""Initialize only a NEW rehearsal Site; no restore/force/employee seed/provider probe."""
import json,os,re
from pathlib import Path
import frappe
from frappe.installer import _new_site

site=os.environ['HBOS_SITE'];project=os.environ['HBOS_SMOKE_PROJECT']
if not re.fullmatch(r'hbos-uat2-smoke-[a-z0-9-]+',project) or not re.fullmatch(r'uat2-smoke-[a-z0-9-]+\.localhost',site):
    raise SystemExit('Fresh-site initializer is restricted to the explicit isolated rehearsal target')
os.chdir('/home/frappe/frappe-bench/sites')
if Path(site).exists():raise SystemExit('Site already exists; initializer will not overwrite it')
Path('common_site_config.json').write_text(json.dumps({'db_host':'db','redis_cache':'redis://redis:6379/0',
    'redis_queue':'redis://redis:6379/1','redis_socketio':'redis://redis:6379/2','socketio_port':9000}))
apps=Path('apps.txt').read_text().splitlines() if Path('apps.txt').exists() else ['frappe','erpnext']
for app in ('hbos_portal','hb_knowledge_app'):
    if app not in apps:apps.append(app)
Path('apps.txt').write_text('\n'.join(apps)+'\n')
frappe.init(site=site,new_site=True)
_new_site(db_name=None,site=site,db_host='db',db_type='mariadb',db_root_username='root',
    db_root_password=Path('/run/secrets/db-root-password').read_text().strip(),
    admin_password=Path('/run/secrets/site-admin-password').read_text().strip(),
    install_apps=['hbos_portal','hb_knowledge_app'],mariadb_user_host_login_scope='%',force=False)
frappe.init(site=site);frappe.connect()
cfg=Path(site)/'site_config.json';values=json.loads(cfg.read_text());values.update(
    hbos_portal_origin=os.environ['HBOS_PORTAL_ORIGIN'],host_name=os.environ['HBOS_PORTAL_ORIGIN'],
    hbos_portal_auth_mode='unified',pause_scheduler=True)
cfg.write_text(json.dumps(values,indent=2)+'\n')
frappe.db.commit();frappe.destroy()
print('FRESH_ISOLATED_SITE_INITIALIZED; no company accounts or provider calls')
