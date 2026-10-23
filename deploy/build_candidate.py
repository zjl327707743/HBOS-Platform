"""Build only the registered Owner candidate; no data/provider operation."""
import hashlib,io,json,os,pathlib,shutil,subprocess,tarfile
R=pathlib.Path(__file__).resolve().parent.parent;B=R/'work/build';B.mkdir(exist_ok=True);S=R/'work/knowledge_service';H=R/'work/hbos'
def git(p,*args):return subprocess.check_output(['git','-C',str(p),*args],text=True).strip()
heads={name:git(p,'rev-parse','HEAD') for name,p in [('hbos',H),('service',S)]}
assert not any(git(p,'status','--porcelain') for p in (S,H)),'Build only clean source commits'
frontend_ref=git(H,'rev-parse','refs/heads/codex/knowledge-uat5-frontend')
# The product-base merge brings unrelated Twin UI changes. Preserve the actual
# candidate's other apps while compiling every Knowledge change from its clean
# pre-merge commit. Knowledge-owned source must still equal the final PR tree.
owned=['frontend/hbos-portal-web/src/components/knowledge','frontend/hbos-portal-web/src/views/KnowledgeView.vue',
       'frontend/hbos-portal-web/src/views/KnowledgeMaintenanceView.vue',
       'frontend/hbos-portal-web/src/services/knowledgeMaintenanceApi.ts',
       'frontend/hbos-portal-web/src/composables/useEvidenceResolution.ts',
       'frontend/hbos-portal-web/src/contracts/p1.ts','frontend/hbos-portal-web/src/services/p1Api.ts']
assert not git(H,'diff',frontend_ref,'HEAD','--',*owned),'Update the separate frontend provenance before building changed Knowledge UI'
front_root=B/'frontend-source'
if front_root.exists():shutil.rmtree(front_root)
front_root.mkdir()
archive=subprocess.check_output(['git','-C',str(H),'archive',frontend_ref,'frontend/hbos-portal-web'])
with tarfile.open(fileobj=io.BytesIO(archive)) as source:source.extractall(front_root,filter='data')
front=front_root/'frontend/hbos-portal-web'
(front/'node_modules').symlink_to((H/'frontend/hbos-portal-web/node_modules').resolve(),target_is_directory=True)
with (R/'work/frontend-build-uat5.log').open('w') as log:
 subprocess.run(['npm','run','build'],cwd=front,
    env=dict(os.environ,VITE_PORTAL_DATA_MODE='frappe',VITE_BASE='/assets/hbos_portal/portal/',
             VITE_FRAPPE_BASE_URL='',VITE_FRAPPE_APP_ORIGIN=''),stdout=log,stderr=subprocess.STDOUT,check=True)
assert '/assets/hbos_portal/portal/assets/' in (front/'dist/index.html').read_text()
# Stage the bundle; the live mount is only touched by install_static.py after the
# containers are recreated. Copying into `public/portal` here is what produced a
# new front-end against the old BFF for the length of the swap.
staged=R/'work/build/frontend-staged'
if staged.exists():shutil.rmtree(staged)
shutil.copytree(front/'dist',staged)
shutil.copytree(H/'apps/hb_knowledge_app',B/'domain',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','tests'))
with (R/'work/wheel-build.log').open('w') as log:
 subprocess.run(['uv','build','--wheel','--offline','--out-dir',str(B)],cwd=S,env=dict(os.environ,SOURCE_DATE_EPOCH=git(S,'log','-1','--format=%ct')),stdout=log,stderr=subprocess.STDOUT,check=True)
import tomllib
version=tomllib.loads((S/'pyproject.toml').read_text())['project']['version']
wheel=B/f'hbos_knowledge_service-{version}-py3-none-any.whl';assert wheel.exists()
for kind,user,python in [('frappe','frappe','/home/frappe/frappe-bench/env/bin/python'),('service','synthetic','python')]:
 dockerfile=B/('Dockerfile.'+kind)
 dockerfile.write_text(f'''FROM hbos-knowledge-r2-20261008-{kind}:uat4
LABEL org.hbos.source.hbos={heads['hbos']} org.hbos.source.service={heads['service']} org.hbos.source.dirty=false
USER root
ENV HBOS_MODEL_EGRESS_REQUIRED=0
COPY domain /opt/domain
COPY {wheel.name} /tmp/{wheel.name}
RUN {python} -m pip install --no-deps --no-build-isolation --force-reinstall /opt/domain /tmp/{wheel.name} && {python} -m pip check
ENV HBOS_MODEL_EGRESS_REQUIRED=1
USER {user}
''')
 with (R/f'work/build-{kind}-uat5.log').open('w') as log:
  subprocess.run(['docker','build','-f',str(dockerfile),'-t',f'hbos-knowledge-r2-20261008-{kind}:uat5',str(B)],stdout=log,stderr=subprocess.STDOUT,check=True)
public=H/'apps/hbos_portal/hbos_portal/public/portal'
result={'source_commits':heads,'frontend_source_commit':frontend_ref,'knowledge_frontend_matches_hbos_head':True,'unrelated_candidate_frontend_apps_preserved':True,'source_dirty':{'hbos':False,'service':False},'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'frontend_staged':str(staged),'images':{kind:subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',f'hbos-knowledge-r2-20261008-{kind}:uat5'],text=True).strip() for kind in ('frappe','service')}}
(R/'work/build-info.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
