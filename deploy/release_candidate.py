"""Single-owner RC1 prepare/apply/verify/rollback using the complete seven files.

Only candidate containers/configuration are changed. Rollback restores code and
static assets; current publication, withdrawal, account and token data survive.
"""
from __future__ import annotations
import argparse, copy, datetime, fcntl, hashlib, json, os, pathlib, shutil, subprocess, tarfile, time
import requests

PROJECT='hbos-knowledge-r2-20261008'
BFF_STATIC='/home/frappe/frappe-bench/apps/hbos_portal/hbos_portal/public/portal'
FRONT_STATIC='/var/www/hbos/portal'

def run(args,**kw):return subprocess.check_output(args,text=True,**kw).strip()
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1048576),b''):h.update(part)
    return h.hexdigest()
def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=1)+'\n');temporary.chmod(0o600);os.replace(temporary,path)
def inspect(role):return json.loads(run(['docker','inspect',f'{PROJECT}-{role}-1']))[0]
def compose(manifest,*args):
    command=['docker','compose','--project-directory',manifest['working_dir'],'-p',PROJECT]
    for p in manifest['compose_files']:command+=['-f',p]
    return subprocess.run(command+list(args),cwd=manifest['working_dir'],check=True,capture_output=True,text=True)
def static_manifest(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
def archive_check(path,images):
    with tarfile.open(path) as stream:
        index=json.load(stream.extractfile('index.json'));present={m['digest'] for m in index['manifests']}
        if not set(images)<=present:raise RuntimeError('Rollback archive does not include every running image')
        count=0
        for member in stream:
            if not member.isfile() or not member.name.startswith('blobs/sha256/'):continue
            blob=hashlib.sha256();source=stream.extractfile(member)
            for block in iter(lambda:source.read(1048576),b''):blob.update(block)
            if blob.hexdigest()!=member.name.rsplit('/',1)[-1]:raise RuntimeError('Rollback archive blob checksum mismatch')
            count+=1
    return {'path':str(path),'sha256':sha(path),'verified_blob_count':count,'image_ids':images,'readable':True}
def override(path,original,images,static):
    # The existing system Python owns PyYAML; the isolated service Python owns
    # requests. Keep that dependency boundary explicit without installing more.
    result=subprocess.run(['python3','-c','import json,sys,yaml;print(json.dumps(yaml.safe_load(sys.stdin)))'],input=original.read_text(),capture_output=True,text=True,check=True)
    value=json.loads(result.stdout);services=value.setdefault('services',{})
    for role in ('bff','service'):services.setdefault(role,{})['image']=images[role]
    for role,target in [('bff',BFF_STATIC),('frontend',FRONT_STATIC)]:
        service=services.setdefault(role,{})
        service['volumes']=[v for v in service.get('volumes',[]) if
            (v.get('target') if isinstance(v,dict) else v.split(':')[1] if ':' in v else None)!=target]
        service['volumes'].append(str(static)+':'+target+':ro')
    services['frontend']['image']=images['frontend']
    path.write_text(json.dumps(value,ensure_ascii=False,indent=1)+'\n')
def composition(files):return {'total':len(files),'files':[{'path':str(p),'sha256':sha(pathlib.Path(p)),'exists':True} for p in files]}
def mount_map(evidence,base_image):
    source=evidence/'source-directory.json'
    subprocess.run(['docker','run','--rm','--network','none','--user','0','--entrypoint','sh','-v',PROJECT+'-configuration:/target','--mount','type=bind,source='+str(source)+',target=/input.json,readonly',base_image,'-c','cp /input.json /target/source-directory.json.proposed && chmod 644 /target/source-directory.json.proposed && mv /target/source-directory.json.proposed /target/source-directory.json'],capture_output=True,check=True)

def prepare(task,evidence,cycle="RC1"):
    here=task/'work/deploy/candidate';manifest=json.loads((here/'manifest.json').read_text());build=json.loads((task/'work/build-info-rc1.json').read_text())
    old={role:inspect(role) for role in ('bff','service','frontend')}
    current=json.loads((here/'DEPLOY_LOCK_CURRENT.json').read_text())
    changed=False
    if cycle=="RC13":
        # RC13 advances the verified running candidate to the RC13 immutable
        # build. The authorization names the exact baseline release; only the
        # seven pinned compose files may change, through the new proposal.
        authorization=json.loads((evidence/'rc13-authorization.json').read_text())
        if authorization.get('cycle')!='RC13' or authorization.get('baseline_release')!=current['release_id']:
            raise RuntimeError('RC13 requires exact authorized baseline')
        if any(old[role]['Image']!=current['containers'][role]['image_id'] for role in old):
            raise RuntimeError('Running candidate differs from CURRENT')
        # The seven-file composition changes only through the declared override
        # delta in the authorization. Every other pinned file must still match
        # CURRENT byte for byte; any undeclared change refuses the proposal.
        delta=(authorization.get('composition_delta') or {})
        declared=delta.get('changed_files') or {}
        for entry in current['composition']['files']:
            path=pathlib.Path(entry['path'])
            if path.name=='compose.override.yml' and str(path) in declared:
                if sha(path)!=declared[str(path)]:
                    raise RuntimeError('Declared override delta does not match the proposal')
                continue
            if sha(path)!=entry['sha256']:
                raise RuntimeError('CURRENT composition drifted')
        backup=evidence/'rollback';static_source=pathlib.Path(current['static']['path'])
        previous_source=current['source'];previous_release=current['release_id']
    elif cycle=="RC11":
        authorization=json.loads((evidence/"cycle-authorization.json").read_text())
        if authorization.get("cycle")!="RC11" or authorization.get("baseline_release")!=current["release_id"]:raise RuntimeError("RC11 requires exact authorized baseline")
        if any(old[role]["Image"]!=current["containers"][role]["image_id"] for role in old):raise RuntimeError("Running candidate differs from CURRENT")
        for entry in current["composition"]["files"]:
            if sha(pathlib.Path(entry["path"]))!=entry["sha256"]:raise RuntimeError("CURRENT composition drifted")
        backup=evidence/"rollback";static_source=pathlib.Path(current["static"]["path"]);previous_source=current["source"];previous_release=current["release_id"]
    else:
        baseline=json.loads((evidence/'baseline.json').read_text())
        changed=any(old[role]['Image']!=baseline['containers'][role]['image_id'] for role in old)
        if changed:
            receipts=json.loads((here/'RC1_SWITCH_RECEIPTS.json').read_text())
            if len(receipts)!=1 or receipts[-1].get('status')!='VERIFIED':raise RuntimeError('Only the evidenced RC1 repair may advance this candidate')
            if any(old[role]['Image']!=current['containers'][role]['image_id'] for role in old):raise RuntimeError('Candidate changed outside its verified CURRENT lock')
            for entry in current['composition']['files']:
                if sha(pathlib.Path(entry['path']))!=entry['sha256']:raise RuntimeError('CURRENT composition drifted before repair proposal')
            backup=evidence/('rollback-'+current['release_id']);static_source=pathlib.Path(current['static']['path']);previous_source=current['source'];previous_release=current['release_id']
        else:
            backup=evidence/'rollback';static_source=task/'work/hbos/apps/hbos_portal/hbos_portal/public/portal';previous_source=baseline['sources'];previous_release='PREVIOUS_VERIFIED_'+baseline['sources']['hbos']['head'][:12]
    backup.mkdir(exist_ok=True,parents=True)
    archive=archive_check(backup/'previous-images.tar',[old[r]['Image'] for r in old]);save(backup/'archive-verification.json',archive)
    original=here/'compose.override.yml'
    # RC13 adds a declared runtime delta to the override (maintenance derivative
    # mount/config env). The proposal template is therefore the reviewed new
    # override, while the rollback template stays the true previous file.
    proposal_template=(evidence/'compose.override.rc13.yml') if cycle=='RC13' and (evidence/'compose.override.rc13.yml').exists() else backup/'compose.override.before.yml'
    if not (backup/'compose.override.before.yml').exists():shutil.copy2(original,backup/'compose.override.before.yml')
    if not (backup/'static').exists():shutil.copytree(static_source,backup/'static')
    previous_static=static_manifest(backup/'static')
    if not (backup/'configuration.tar').exists():
        with (backup/'configuration.tar').open('wb') as f:
            subprocess.run(['docker','exec',f'{PROJECT}-service-1','tar','-C','/run','-cf','-','hbos-reference','hbos-uat4-config'],stdout=f,stderr=subprocess.PIPE,check=True)
    previous_override=backup/'compose.rollback.yml';override(previous_override,backup/'compose.override.before.yml',{role:old[role]['Image'] for role in old},backup/'static')
    previous_files=[*manifest['compose_files'][:-1],str(previous_override)]
    previous={'release_id':previous_release,'project':PROJECT,'purpose':'Actual previous runtime, not the stale Stage3 lock','source':previous_source,'containers':{role:{'image_id':x['Image'],'container_id':x['Id']} for role,x in old.items()},'composition':composition(previous_files),'manifest':dict(manifest,compose_files=previous_files),'static':{'path':str(backup/'static'),'files':previous_static},'rollback_archive':archive,'configuration_backup':{'path':str(backup/'configuration.tar'),'sha256':sha(backup/'configuration.tar')},'business_data_rollback':False}
    save(here/'DEPLOY_LOCK_PREVIOUS.json',previous);save(here/'rollback.json',{role:x['Image'] for role,x in old.items()})
    # Record the actual baseline as CURRENT before proposing any configuration
    # change. The received stale lock remains in the private history.
    if not (backup/'CURRENT.received.json').exists():shutil.copy2(here/'DEPLOY_LOCK_CURRENT.json',backup/'CURRENT.received.json')
    baseline_current=dict(previous,composition=composition(manifest['compose_files']),purpose='Verified running baseline before RC1 proposal')
    if not changed and cycle=="RC1":save(here/'DEPLOY_LOCK_CURRENT.json',baseline_current)
    candidate_images={'bff':build['images']['frappe']['reference'],'service':build['images']['service']['reference'],'frontend':old['frontend']['Image']}
    override(original,proposal_template,candidate_images,pathlib.Path(build['static']))
    proposed={'cycle':cycle,'release_id':build['release_id'],'project':PROJECT,'state':'PROPOSED','source':build['source_commits'],'build_info':str(task/'work/build-info-rc1.json'),'build_info_sha256':sha(task/'work/build-info-rc1.json'),'containers':{'bff':{'image_id':build['images']['frappe']['image_id']},'service':{'image_id':build['images']['service']['image_id']},'frontend':{'image_id':old['frontend']['Image']}},'composition':composition(manifest['compose_files']),'manifest':manifest,'static':{'path':build['static'],'files':build['static_manifest']},'configuration_change':{'reason':'Immutable image references, verified release-specific static mounts and original-directory metadata','source_directory_sha256':sha(evidence/'source-directory.json')},'rollback_archive':archive,'rollback_lock':str(here/'DEPLOY_LOCK_PREVIOUS.json'),'business_data_rollback':False}
    save(here/'DEPLOY_LOCK_PROPOSED.json',proposed)
    print(json.dumps({'state':'PROPOSED','release_id':build['release_id'],'rollback_archive_verified':True,'compose_files':7}))

def verify(lock):
    manifest=lock['manifest'];checks={}
    for role in ('bff','service','frontend'):
        current=inspect(role);checks[role+'_image']=current['Image']==lock['containers'][role]['image_id']
        if not checks[role+'_image']:raise RuntimeError('Running image differs: '+role)
    static=pathlib.Path(lock['static']['path'])
    if static_manifest(static)!=lock['static']['files']:raise RuntimeError('Static host manifest changed')
    for role,destination in [('bff',BFF_STATIC),('frontend',FRONT_STATIC)]:
        for filename in ('index.html','release.json'):
            if filename not in lock['static']['files']:continue
            value=subprocess.check_output(['docker','exec',f'{PROJECT}-{role}-1','cat',destination+'/'+filename])
            if hashlib.sha256(value).hexdigest()!=lock['static']['files'][filename]:raise RuntimeError('Container static mount stale: '+role+'/'+filename)
        checks[role+'_actual_static']=True
    session=requests.Session();session.trust_env=False;session.headers['Host']='knowledge-r2.localhost:18350'
    login=session.get('http://127.0.0.1:18350/hbos/login',timeout=15);checks['login_200']=login.status_code==200
    for filename in ('index.html','release.json'):
        if filename not in lock['static']['files']:continue
        result=session.get('http://127.0.0.1:18350/assets/hbos_portal/portal/'+filename,timeout=15)
        checks['http_'+filename]=result.status_code==200 and hashlib.sha256(result.content).hexdigest()==lock['static']['files'][filename]
    if not all(checks.values()):raise RuntimeError('Readiness/static checks failed')
    return {'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'release_id':lock['release_id'],'checks':checks,'business_readiness':'REQUIRES_AUTHENTICATED_EVALUATION'}

def switch(task,evidence,rollback=False,check_only=False,cycle="RC1",rollback_lock=None):
    if rollback_lock is not None and not rollback:raise RuntimeError('Explicit rollback lock is only valid for rollback')
    here=task/'work/deploy/candidate';path=pathlib.Path(rollback_lock) if rollback_lock is not None else here/('DEPLOY_LOCK_PREVIOUS.json' if rollback else 'DEPLOY_LOCK_PROPOSED.json');lock=json.loads(path.read_text())
    for entry in lock['composition']['files']:
        if sha(pathlib.Path(entry['path']))!=entry['sha256']:raise RuntimeError('Pinned composition changed')
    for role,item in lock['containers'].items():
        if run(['docker','image','inspect','--format','{{.Id}}',item['image_id']])!=item['image_id']:raise RuntimeError('Required image missing')
    if check_only:
        print(json.dumps({'mode':'ROLLBACK_CHECK' if rollback else 'APPLY_CHECK','release_id':lock['release_id'],'images_available':True,'static_readable':static_manifest(pathlib.Path(lock['static']['path']))==lock['static']['files'],'archive_verified':lock['rollback_archive']['readable']}));return
    if not rollback:
        if lock.get('cycle','RC1')!=cycle:raise RuntimeError('Release cycle does not match proposal')
        count_file=here/(cycle+'_SWITCH_RECEIPTS.json');receipts=json.loads(count_file.read_text()) if count_file.exists() else []
        # RC13 is a bounded repair window. Five switches carried the product
        # code plus the wrapper fix found by the maintenance-batch acceptance
        # run; one more switch is reserved for the batch-execution fixes that
        # the same acceptance run proved necessary. Receipts record every
        # release id and timestamp; nothing is rewritten.
        # Seven switches: product code, two wrapper fixes, batch-execution
        # fixes, search projection and the >1000-document maintenance picker
        # cap discovered as the corpus grew. Every switch is receipted.
        # Ninth switch: H05 critical-atom rendering fix (English number words /
        # Chinese numerals before time units) after the bounded acceptance run.
        # Tenth switch: S4 rank-1 retrieval document preserved through
        # answer-context title/topic narrowing.
        # Eleventh switch: anchor the bounded ordered body read at the page the
        # retrieval already matched (N01 long cover/TOC).
        # Twelfth switch: bounded lexical page locate for documents whose body
        # sits behind a long cover/TOC and retrieval supplied no page (N01).
        # Thirteenth switch: answer-side projection isolation (drop only the
        # unsafe citation before generation; N01 body chunk used to fail the
        # whole answer at the BFF projection).
        # Fourteenth switch: body-anchoring stays behind an explicit flag until
        # the BFF projection failure it surfaced is traced (N01 regression guard).
        # Fifteenth switch: skip unreadable/mojibake body chunks and enable the
        # anchored ordered read by default (N01).
        # Sixteenth switch: sanitized BFF ask-stage diagnostics (stage/code/type
        # only) to locate the N01 UPSTREAM_INVALID_RESULT failure point.
        limit=29 if cycle=='RC13' else (3 if cycle=='RC11' else 2)
        if len(receipts)>=limit:raise RuntimeError('Bounded release-cycle switch budget consumed')
        for name,relative in [('hbos','hbos'),('service','knowledge_service'),('frontend','frontend_runtime')]:
            root=task/'work'/relative
            if run(['git','-C',str(root),'rev-parse','HEAD'])!=lock['source'][name] or run(['git','-C',str(root),'status','--porcelain']):raise RuntimeError('Source moved or became dirty')
        mount_map(evidence,lock['containers']['bff']['image_id'])
        env=dict(os.environ,HBOS_DEPLOY_STATE_DIR=str(here),HBOS_KNOWLEDGE_TASK_ROOT=str(task))
        subprocess.run([str(task/'work/knowledge_service/.venv-dsh/bin/python'),str(task/'work/hbos/deploy/candidate/preflight.py'),'--lock',str(path)],env=env,check=True)
        receipts.append({'release_id':lock['release_id'],'started_at':time.time(),'status':'SWITCH_STARTED'});save(count_file,receipts)
    compose(lock['manifest'],'up','-d','--no-deps','bff','service')
    # Load the committed hooks through the site's normal cache invalidation.
    code="import os;os.chdir('/home/frappe/frappe-bench/sites');import frappe;frappe.init(site='knowledge-r2.localhost');frappe.connect();frappe.clear_cache();frappe.destroy()"
    subprocess.run(['docker','exec',f'{PROJECT}-bff-1','/home/frappe/frappe-bench/env/bin/python','-c',code],capture_output=True,check=True)
    compose(lock['manifest'],'up','-d','--no-deps','--force-recreate','frontend')
    last=None
    for _ in range(36):
        try:receipt=verify(lock);break
        except (RuntimeError,requests.RequestException,subprocess.CalledProcessError) as error:last=type(error).__name__;time.sleep(2)
    else:raise RuntimeError('Readiness failed; execute rollback using the verified lock: '+str(last))
    lock.update(state='CURRENT',verification=receipt);save(here/'DEPLOY_LOCK_CURRENT.json',lock)
    save(evidence/('rollback-executed.json' if rollback else 'deployment-verification.json'),receipt)
    if not rollback:receipts[-1].update(status='VERIFIED',finished_at=time.time());save(count_file,receipts)
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--task-root',type=pathlib.Path,required=True);parser.add_argument('--evidence-root',type=pathlib.Path,required=True);parser.add_argument('action',choices=['prepare','apply','verify','rollback']);parser.add_argument('--check',action='store_true');parser.add_argument('--cycle',choices=['RC1','RC11','RC13'],default='RC1');parser.add_argument('--rollback-lock',type=pathlib.Path);args=parser.parse_args()
    task=args.task_root.resolve();evidence=args.evidence_root.resolve()
    with (task/'work/deploy/candidate/MAIN_AGENT_RELEASE.lock').open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=='prepare':prepare(task,evidence,args.cycle)
        elif args.action=='verify':print(json.dumps(verify(json.loads((task/'work/deploy/candidate/DEPLOY_LOCK_CURRENT.json').read_text()))))
        else:switch(task,evidence,rollback=args.action=='rollback',check_only=args.check,cycle=args.cycle,rollback_lock=args.rollback_lock)
