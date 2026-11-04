"""Reviewable isolated deploy/migrate/verify/backup/rollback commands."""
import argparse,hashlib,ipaddress,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('action',choices=['validate','build','deploy','initialize','migrate','verify','backup','rollback','rollback-plan','stop'])
p.add_argument('--release',type=Path,required=True);p.add_argument('--env',type=Path,required=True)
p.add_argument('--manifest-sha256',required=True)
p.add_argument('--backup-lock-sha256');p.add_argument('--rollback-marker');a=p.parse_args()
root=a.release.resolve();raw=(root/'joint-manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=a.manifest_sha256:raise SystemExit('Manifest differs from the separately reviewed release lock')
manifest=json.loads(raw)
for name,digest in manifest['files'].items():
    path=root/name
    if Path(name).is_absolute() or '..' in Path(name).parts:raise SystemExit('Invalid artifact path')
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise SystemExit('Joint artifact hash mismatch: '+name)
env={}
for line in a.env.read_text().splitlines():
    if line and not line.startswith('#'):
        key,value=line.split('=',1);env[key]=value
project=env.get('COMPOSE_PROJECT_NAME','');site=env.get('HBOS_SITE','')
if not re.fullmatch(r'hbos-uat2-smoke-[a-z0-9-]+',project) or not re.fullmatch(r'uat2-smoke-[a-z0-9-]+\.localhost',site):raise SystemExit('This executable is restricted to the isolated rehearsal target')
subnet=ipaddress.ip_network(env.get('HBOS_NETWORK_SUBNET',''))
if subnet.version!=4 or not 24<=subnet.prefixlen<=28 or not any(subnet.subnet_of(ipaddress.ip_network(block)) for block in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):raise SystemExit('A reviewed unused RFC1918 /24–/28 subnet is required')
if any('/Users/' in v or 'Codex/' in v for k,v in env.items() if k not in {'HBOS_RELEASE_ROOT','HBOS_PRIVATE_ROOT','HBOS_UPLOAD_ROOT','HBOS_AUDIT_ROOT'}):raise SystemExit('Runtime configuration depends on a Mac development path')
for name in ('FRAPPE_IMAGE','PYTHON_IMAGE','MARIADB_IMAGE','REDIS_IMAGE','NGINX_IMAGE'):
    if not re.search(r'@sha256:[0-9a-f]{64}$',env.get(name,'')):raise SystemExit('Immutable base image required: '+name)
environment=dict(os.environ,**env)
compose=['docker','compose','--env-file',str(a.env.resolve()),'-p',project,'-f',str(root/'deployment/compose.yml')]
def run(command):subprocess.run(command,env=environment,check=True)
if a.action=='validate':print('JOINT_CODE_HASHES_PASS; runtime/server/UAT remain separate gates')
elif a.action=='build':
    for kind,arg in [('frappe','FRAPPE_IMAGE'),('service','PYTHON_IMAGE')]:
        run(['docker','build','--build-arg',arg+'='+env[arg],'-f',str(root/f'deployment/Dockerfile.{kind}'),'-t',env['HBOS_'+kind.upper()+'_IMAGE'],str(root)])
elif a.action=='deploy':run(compose+['up','-d','db','redis','bff','frontend'])
elif a.action=='initialize':run(compose+['--profile','initialize','run','--rm','initialize'])
elif a.action=='migrate':run(compose+['exec','-T','-w','/home/frappe/frappe-bench','bff','bench','--site',site,'migrate'])
elif a.action=='verify':
    code="import os;os.chdir('sites');import frappe;frappe.init(site=os.environ['HBOS_SITE']);frappe.connect();assert 'hb_knowledge_app' in frappe.get_installed_apps();assert frappe.db.has_column('HBOS Knowledge Connection','verification_json');assert frappe.db.count('HBOS Knowledge Document')==0;print('CLEAN_METADATA_PASS; provider calls=0; no company corpus loaded');frappe.destroy()"
    run(compose+['exec','-T','-w','/home/frappe/frappe-bench','-e','HBOS_SITE='+site,'bff','/home/frappe/frappe-bench/env/bin/python','-c',code])
elif a.action=='backup':
    run(compose+['exec','-T','-w','/home/frappe/frappe-bench','bff','bench','--site',site,'backup','--with-files'])
    run(compose+['exec','-T','-e','HBOS_SITE='+site,'bff','/home/frappe/frappe-bench/env/bin/python','/opt/hbos-joint/backup_receipt.py'])
elif a.action=='rollback':
    if not re.fullmatch(r'[0-9a-f]{64}',a.backup_lock_sha256 or ''):raise SystemExit('Separately reviewed backup lock hash is required')
    environment['HBOS_BACKUP_LOCK_SHA256']=a.backup_lock_sha256
    if a.rollback_marker:environment['HBOS_ROLLBACK_MARKER']=a.rollback_marker
    run(compose+['stop','bff','frontend'])
    run(compose+['--profile','rollback','run','--rm','rollback'])
    run(compose+['up','-d','bff','frontend'])
elif a.action=='rollback-plan':
    print('Stop rehearsal writers. Verify the previous immutable image and protected backup hashes. Restore ONLY this isolated rehearsal DB/sites snapshot with bench restore, then use the prior environment lock and verify. Existing company/RAGFlow volumes are never overwritten by this tool.')
else:run(compose+['stop'])
