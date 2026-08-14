# -*- coding: utf-8 -*-
"""断点续跑:只做员工部门 upsert,跳过已正确的。分批写快照,超时安全。"""
import os, re, hashlib, time, json, requests, sys

env = {}
with open('.env', encoding='utf-8') as f:
    for line in f:
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line.strip())
        if m: env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
APP_KEY, APP_SECRET = env['DELICLOUD_APP_KEY'], env['DELICLOUD_APP_SECRET']
BASE = "https://v2-api.delicloud.com"

def call(path, body, pause=0.25):
    ts = str(int(time.time() * 1000))
    sig = hashlib.md5((path + ts + APP_KEY + APP_SECRET).encode()).hexdigest().lower()
    h = {"Content-Type": "application/json; charset=UTF-8",
         "App-Key": APP_KEY, "App-Timestamp": ts, "App-Sig": sig}
    r = requests.post(BASE + path, json=body, headers=h, timeout=30)
    if pause: time.sleep(pause)
    return r.json()

depts = json.load(open('/tmp/delicloud_depts.json'))
emps = json.load(open('/tmp/delicloud_emps.json'))
dept_by_name = {}
for d in depts:
    dept_by_name.setdefault(d['name'], []).append(d)
dept_by_id = {d['id']: d for d in depts}

inp = json.load(open('/tmp/hrbos_input.json'))
roster_map = inp['roster_map']
DEPT_MAP = {
    '一车间': '1车间', '二车间': '2车间', '三车间': '3车间', '四车间': '4车间', '五车间': '5车间',
    '六车间': '6车间', '六车间（规范）': '欧盟', '六车间（非规）': '非规', '六车间（精馏）': '精馏塔',
}
target_dl = {n: DEPT_MAP.get(rd, rd) for n, rd in roster_map.items()}

dln = {e['name'].strip(): e for e in emps}
to_update = [(n, dln[n], t) for n, t in target_dl.items() if n in dln]
print("花名册∩Deli:", len(to_update), "人")

# 当前部门与目标对比,只改错的
def current_dept_name(e):
    ids = [str(di['id']) for di in e.get('department_infos', [])]
    return [dept_by_id.get(i, {}).get('name', i) for i in ids]

todo, already_ok = [], []
for n, e, tname in to_update:
    if current_dept_name(e) == [tname]:
        already_ok.append(n)
    else:
        todo.append((n, e, tname))
print("已正确(跳过):", len(already_ok), "| 待改:", len(todo))

# 断点:读上次进度(失败或中断时手工标记)
resume = 0
if os.path.exists('/tmp/deli_progress.json'):
    resume = json.load(open('/tmp/deli_progress.json')).get('done', 0)
    print("断点续跑 from:", resume)

ok, fail = 0, []
for i, (name, e, tname) in enumerate(todo):
    if i < resume:
        continue
    dep_id = dept_by_name[tname][0]['id']
    body = {
        'employee_ext_id': e['id'],
        'name': e.get('name'),
        'mobile': e.get('mobile', ''),
        'employee_num': e.get('employee_num', ''),
        'department_infos': [{'ext_id': dep_id}],
    }
    r = call('/v2.0/employee', body)
    if r.get('code') == 0:
        ok += 1
    else:
        fail.append({'name': name, 'id': e['id'], 'resp': r})
        print(f"!! 失败: {name}: code={r.get('code')} msg={r.get('msg')}")
    # 每 50 条写进度
    if (i + 1) % 50 == 0:
        json.dump({'done': resume + i + 1, 'ok': ok, 'fail': fail}, open('/tmp/deli_progress.json','w'), ensure_ascii=False)
        print(f"  进度 {resume+i+1}/{len(todo)} 成功 {ok} 失败 {len(fail)} (已存档)")
json.dump({'done': len(todo), 'ok': ok, 'fail': fail}, open('/tmp/deli_progress.json','w'), ensure_ascii=False)
missing_in_deli = sorted(n for n in roster_map if n not in dln)
print(f"\n完成: 成功 {ok} / 失败 {len(fail)} / 花名册无Deli记录 {len(missing_in_deli)} 人")
if fail:
    print("失败名单:", [(f['name'], f['resp'].get('msg')) for f in fail])
print("花名册无Deli记录:", missing_in_deli)
