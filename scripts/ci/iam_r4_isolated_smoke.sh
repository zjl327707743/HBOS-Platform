#!/usr/bin/env bash
# Read-only business smoke against the explicitly owned, synthetic IAM Site.
# Credentials remain in this clone's ignored private directory, never argv/logs.
set -euo pipefail
task_root="$(git rev-parse --show-toplevel)"
if [[ "$task_root" != "/Users/hb/Projects/HBOS-IAM-R4-B" ]]; then
  echo 'Refusing: this entry point only targets the approved isolated clone.' >&2
  exit 2
fi
task_project='hbos-iam-r4-b-20261015'
task_container="${task_project}-backend-1"
task_label="$(docker inspect "$task_container" --format '{{index .Config.Labels "com.docker.compose.project"}}')"
[[ "$task_label" == "$task_project" ]] || { echo 'Refusing: container ownership mismatch.' >&2; exit 2; }
python3 - "$task_root" <<'PY'
import json,sys,urllib.request,urllib.error,urllib.parse,http.cookiejar
from pathlib import Path
root=Path(sys.argv[1]);private=root/'.local/iam-v1'
if private.stat().st_mode & 0o077:
    raise SystemExit('Refusing: private directory permissions must be 0700.')
fixture=json.loads((private/'fixture.json').read_text())
credentials=json.loads((private/'fixture-credentials.json').read_text())
evidence=[]
def check(name,ok,**safe):
    evidence.append(dict(name=name,status='PASS' if ok else 'FAIL',**safe))
    if not ok: raise AssertionError(name)
class Session:
    def __init__(self,key):
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf=None
        code,_=self.request('login',dict(usr=fixture['users'][key],pwd=credentials[key]),True)
        check(key+' native session',code==200,http=code)
        code,body=self.request('hbos_portal.api.csrf.get_token')
        self.csrf=body.get('csrf_token')
        check(key+' session CSRF',code==200 and bool(self.csrf),http=code)
    def request(self,method,data=None,post=False):
        path='/api/method/'+method
        headers={'Host':'iam-r4-b.localhost:5198','Origin':'http://iam-r4-b.localhost:5198','Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'}
        if self.csrf:headers['X-Frappe-CSRF-Token']=self.csrf
        if data and not post:path+='?'+urllib.parse.urlencode(data)
        body=json.dumps(data or {}).encode() if post else None
        req=urllib.request.Request('http://127.0.0.1:8198'+path,data=body,headers=headers,method='POST' if post else 'GET')
        try:response=self.opener.open(req,timeout=45)
        except urllib.error.HTTPError as error:response=error
        parsed=json.loads(response.read());value=parsed.get('message',parsed)
        value=value.get('data',value) if isinstance(value,dict) else {}
        return response.status,value
try:
    employee=Session('a');manager=Session('manager1')
    personal='hb_attendance_app.hbos_attendance.portal.personal.get_my_attendance'
    code,own=employee.request(personal,dict(date_from='2026-10-14',date_to='2026-10-14'))
    check('self rows/count/summary',code==200 and own.get('total')==3 and own.get('summary')==dict(records=3,days=1),http=code,total=own.get('total'))
    code,_=employee.request(personal,dict(employee=fixture['employees']['b']))
    check('foreign subject parameter denied',code==403,http=code)
    code,_=manager.request(personal)
    check('management does not grant attendance',code==403,http=code)
    target=dict(subject_type='User',subject_name=fixture['users']['a'],app_id='attendance')
    code,current=manager.request('hbos_portal.api.iam_access.get_effective_access',target)
    check('current configuration',code==200 and current.get('subject_name')==fixture['users']['a'],http=code,version=current.get('version'))
    code,preview=manager.request('hbos_portal.api.iam_access.preview_work',dict(target,changes=[],expected_version=current['version'],context_revision=current['context_revision']),True)
    encoded=json.dumps(preview)
    check('configuration has no attendance payload',code==200 and not preview.get('changed') and all(text not in encoded for text in ['08:11:00','17:21:00','09:37:00','"rows"','"records"']),http=code)
    code,apps=manager.request('hbos_portal.api.iam_access.get_registered_apps')
    integrations={item['id']:item['integrated'] for item in apps.get('apps',[])}
    check('only approved real business integrated',code==200 and integrations.get('attendance') is True and all(integrations.get(key) is False for key in ['inventory','lims','knowledge','twin']),http=code,integrations=integrations)
finally:
    path=private/'repeatable-smoke-evidence.json'
    path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    print(json.dumps({'checks':len(evidence),'failed':sum(item['status']!='PASS' for item in evidence),'evidence':str(path)},ensure_ascii=False))
PY
