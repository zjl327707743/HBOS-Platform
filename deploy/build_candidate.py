"""Build immutable, reconstructible Knowledge RC1 artifacts in isolated staging.

Usage: python deploy/build_candidate.py --task-root /absolute/isolated/task
The runtime work/build_candidate_uat5.py is only a compatibility entry point.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, pathlib, shutil, subprocess, tarfile, tomllib

def output(args, **kw):return subprocess.check_output(args,text=True,**kw).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(root,*args):return output(['git','-C',str(root),*args])
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=1)+'\n')
def build(task):
    hbos=task/'work/hbos';service=task/'work/knowledge_service';frontend=task/'work/frontend_runtime'
    for root in (hbos,service,frontend):
        if git(root,'status','--porcelain'):raise RuntimeError('Build requires clean committed source: '+root.name)
    heads={k:git(p,'rev-parse','HEAD') for k,p in [('hbos',hbos),('service',service),('frontend',frontend)]}
    owned=['frontend/hbos-portal-web/src/components/knowledge','frontend/hbos-portal-web/src/views/KnowledgeView.vue',
           'frontend/hbos-portal-web/src/views/KnowledgeMaintenanceView.vue','frontend/hbos-portal-web/src/views/KnowledgeDocumentView.vue',
           'frontend/hbos-portal-web/src/services/knowledgeMaintenanceApi.ts','frontend/hbos-portal-web/src/services/documentReaderApi.ts',
           'frontend/hbos-portal-web/src/composables/useEvidenceResolution.ts','frontend/hbos-portal-web/src/composables/useDocumentReader.ts',
           'frontend/hbos-portal-web/src/contracts/p1.ts','frontend/hbos-portal-web/src/contracts/documentReader.ts',
           'frontend/hbos-portal-web/src/services/p1Api.ts','frontend/hbos-portal-web/src/stores/knowledgeReturn.ts',
           'frontend/hbos-portal-web/src/router/index.ts']
    if git(hbos,'diff',heads['frontend'],heads['hbos'],'--',*owned):raise RuntimeError('Knowledge frontend differs from the PR source')
    bases={kind:output(['docker','image','inspect','--format','{{.Id}}',f'hbos-knowledge-r2-20261008-{kind}:uat4']) for kind in ('frappe','service')}
    inputs={'source_commits':heads,'base_images':bases,'builder_sha256':sha(pathlib.Path(__file__)),
            'dependency_locks':{'service':sha(service/'uv.lock'),'frontend':sha(frontend/'frontend/hbos-portal-web/package-lock.json')}}
    release='rc1-'+hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
    stage=task/'work/build/releases'/release
    if stage.exists():raise RuntimeError('Immutable release staging already exists; inspect its receipt instead of overwriting')
    stage.mkdir(parents=True)
    source=stage/'frontend-source';source.mkdir()
    archive=subprocess.check_output(['git','-C',str(frontend),'archive',heads['frontend'],'frontend/hbos-portal-web'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:stream.extractall(source,filter='data')
    front=source/'frontend/hbos-portal-web';(front/'node_modules').symlink_to(hbos/'frontend/hbos-portal-web/node_modules',target_is_directory=True)
    with (stage/'frontend-build.log').open('w') as log:
        subprocess.run(['npm','run','build'],cwd=front,env=dict(os.environ,VITE_PORTAL_DATA_MODE='frappe',VITE_BASE='/assets/hbos_portal/portal/',VITE_FRAPPE_BASE_URL='',VITE_FRAPPE_APP_ORIGIN=''),stdout=log,stderr=subprocess.STDOUT,check=True)
    static=stage/'static';shutil.copytree(front/'dist',static)
    save(static/'release.json',{'release_id':release,'source_commits':heads})
    index=static/'index.html';index.write_text(index.read_text().replace('<head>','<head><meta name="hbos-build-id" content="'+release+'">',1))
    domain=stage/'domain';domain.mkdir()
    archive=subprocess.check_output(['git','-C',str(hbos),'archive',heads['hbos'],'apps/hb_knowledge_app'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:stream.extractall(domain,filter='data')
    with (stage/'wheel-build.log').open('w') as log:
        subprocess.run(['uv','build','--wheel','--offline','--out-dir',str(stage)],cwd=service,env=dict(os.environ,SOURCE_DATE_EPOCH=git(service,'log','-1','--format=%ct')),stdout=log,stderr=subprocess.STDOUT,check=True)
    version=tomllib.loads((service/'pyproject.toml').read_text())['project']['version']
    wheel=stage/f'hbos_knowledge_service-{version}-py3-none-any.whl'
    (stage/'.dockerignore').write_text('frontend-source/\nstatic/\n*.log\n')
    images={}
    for kind,user,python in [('frappe','frappe','/home/frappe/frappe-bench/env/bin/python'),('service','synthetic','python')]:
        base_ref=f'hbos-knowledge-rc1-base-{kind}:'+bases[kind].split(':')[1]
        subprocess.run(['docker','tag',bases[kind],base_ref],check=True)
        dockerfile=stage/('Dockerfile.'+kind)
        dockerfile.write_text(f'''FROM {base_ref}
LABEL org.hbos.release={release} org.hbos.source.hbos={heads['hbos']} org.hbos.source.service={heads['service']} org.hbos.source.frontend={heads['frontend']} org.hbos.source.dirty=false
USER root
ENV HBOS_MODEL_EGRESS_REQUIRED=0
COPY domain/apps/hb_knowledge_app /opt/domain
COPY {wheel.name} /tmp/{wheel.name}
RUN {python} -m pip install --no-deps --no-build-isolation --force-reinstall /opt/domain /tmp/{wheel.name} && {python} -m pip check
ENV HBOS_MODEL_EGRESS_REQUIRED=1
USER {user}
''')
        reference=f'hbos-knowledge-rc1-{kind}:{release}'
        with (stage/f'image-{kind}.log').open('w') as log:
            subprocess.run(['docker','build','-f',str(dockerfile),'-t',reference,str(stage)],stdout=log,stderr=subprocess.STDOUT,check=True)
        images[kind]={'reference':reference,'image_id':output(['docker','image','inspect','--format','{{.Id}}',reference])}
    manifest={'release_id':release,'build_inputs':inputs,'source_commits':heads,'frontend_source_commit':heads['frontend'],'source_dirty':{'hbos':False,'service':False,'frontend':False},'wheel':str(wheel),'wheel_sha256':sha(wheel),'static':str(static),'static_manifest':{str(p.relative_to(static)):sha(p) for p in sorted(static.rglob('*')) if p.is_file()},'images':images}
    save(stage/'build-info.json',manifest);save(task/'work/build-info-rc1.json',manifest)
    print(json.dumps({'release_id':release,'wheel_sha256':manifest['wheel_sha256'],'images':images},indent=1))
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--task-root',type=pathlib.Path,required=True);args=parser.parse_args();build(args.task_root.resolve())
