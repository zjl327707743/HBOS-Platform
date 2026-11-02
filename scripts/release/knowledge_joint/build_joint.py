"""Allowlisted, hashed joint code bundle. No company data or runtime credentials."""
import argparse,gzip,hashlib,json,os,shutil,subprocess,tarfile
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--service-source',type=Path,required=True)
parser.add_argument('--ragflow-source',type=Path,required=True)
parser.add_argument('--portal-dist',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--test-snapshot',action='store_true')
args=parser.parse_args();hbos=Path(__file__).resolve().parents[3]
service=args.service_source.resolve();rag=args.ragflow_source.resolve();out=args.output.resolve()
if out.exists():raise SystemExit('Output already exists; preserve prior artifact and select a new directory')
def git(root,*cmd):return subprocess.check_output(['git','-C',str(root),*cmd],text=True).strip()
heads={key:git(root,'rev-parse','HEAD') for key,root in [('hbos',hbos),('knowledge_service',service),('ragflow',rag)]}
dirty={key:bool(git(root,'status','--porcelain')) for key,root in [('hbos',hbos),('knowledge_service',service),('ragflow',rag)]}
if dirty['ragflow'] or heads['ragflow']!='ec9c08d809f63ba2815090182fa225899d2437d5':raise SystemExit('Fixed original RAGFlow source changed')
if any(dirty.values()) and not args.test_snapshot:raise SystemExit('A release bundle requires clean reviewed commits')
out.mkdir(parents=True);(out/'artifacts').mkdir();(out/'requirements').mkdir()
roots=['apps/hbos_portal','apps/hb_knowledge_app','apps/hb_attendance_app','apps/hb_inventory_app','apps/hb_lims_app','apps/hb_twin_app']
names=git(hbos,'ls-files','-co','--exclude-standard').splitlines()
for name in names:
    if not any(name.startswith(root+'/') for root in roots):continue
    relative=Path(name)
    if any(part in {'__pycache__','node_modules','dist','.pytest_cache'} or part.startswith('.env') for part in relative.parts):continue
    source=hbos/name
    if source.is_symlink():raise SystemExit('Symlink in app source')
    if source.is_file():
        target=out/'hbos'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
public=out/'hbos/apps/hbos_portal/hbos_portal/public/portal'
if public.exists():shutil.rmtree(public)
shutil.copytree(args.portal_dist,public)
shutil.copytree(Path(__file__).parent,out/'deployment',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for extra,name in [('server,mcp,ingestion,build','runtime'),('ingestion','ingestion'),('build','build')]:
    command=['uv','export','--quiet','--frozen','--no-emit-project','--no-header','--format','requirements-txt']
    for value in extra.split(','):command+=['--extra',value]
    with (out/'requirements'/f'{name}.lock').open('w') as target:subprocess.run(command,cwd=service,stdout=target,check=True)
subprocess.run(['uv','build','--wheel','--out-dir',str(out/'artifacts')],cwd=service,
               env=dict(os.environ,SOURCE_DATE_EPOCH=git(service,'log','-1','--format=%ct')),check=True)
shutil.copy2(service/'uv.lock',out/'requirements/service-uv.lock')
for name in git(service,'ls-files','-co','--exclude-standard').splitlines():
    if name in {'pyproject.toml','uv.lock','README.md'} or name.startswith('knowledge_service/'):
        relative=Path(name)
        if '__pycache__' in relative.parts or name.endswith('.pyc'):continue
        source=service/name
        if source.is_symlink():raise SystemExit('Symlink in service source')
        if source.is_file():
            target=out/'service-source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
shutil.copy2(hbos/'frontend/hbos-portal-web/package-lock.json',out/'requirements/portal-package-lock.json')
with (out/'artifacts/ragflow-fixed-source.tar.gz').open('wb') as target:
    subprocess.run(['git','-C',str(rag),'archive','--format=tar.gz','HEAD'],stdout=target,check=True)
files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
manifest={'schema':1,'source_commits':heads,'source_dirty':dirty,'test_snapshot':args.test_snapshot,
          'status':'CODE_BUNDLE_ONLY_OWNER_UAT_AND_SERVER_NOT_RUN','python':{'frappe':'3.14','service':'3.12','ragflow':'3.13'},
          'node':'22','accounting_mode':'AUDIT_ONLY','ragflow_data_included':False,'secrets_included':False,'files':files}
(out/'joint-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'source_commits':heads,'test_snapshot':args.test_snapshot,'file_count':len(files)}))
