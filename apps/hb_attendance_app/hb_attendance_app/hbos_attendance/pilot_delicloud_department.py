import os, re, hashlib, time, json, requests

env = {}
with open('.env', encoding='utf-8') as f:
    for line in f:
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line.strip())
        if m: env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
APP_KEY, APP_SECRET = env['DELICLOUD_APP_KEY'], env['DELICLOUD_APP_SECRET']
BASE = "https://v2-api.delicloud.com"

def call(path, body, pause=0.3):
    ts = str(int(time.time() * 1000))
    sig = hashlib.md5((path + ts + APP_KEY + APP_SECRET).encode()).hexdigest().lower()
    h = {"Content-Type": "application/json; charset=UTF-8",
         "App-Key": APP_KEY, "App-Timestamp": ts, "App-Sig": sig}
    r = requests.post(BASE + path, json=body, headers=h, timeout=30)
    if pause: time.sleep(pause)
    return r.json()

depts = {d['id']: d for d in json.load(open('/tmp/delicloud_depts.json'))}
emps  = {e['id']: e for e in json.load(open('/tmp/delicloud_emps.json'))}

# 试点:姓名 -> (员工id, 目标部门名)
pilot = [
    ("孟金秋", "7",  "人事行政部"),
    ("卞德志", "28", "4车间"),
    ("蒋义勇", "290", "6车间"),
    ("赵磊",   "785", "欧盟"),
    ("李瑞华", "631", "非规"),
]

# 1) 部门设 ext_id(用自身 id 作为 ext_id)
target_ids = set()
for _, _, dname in pilot:
    d = next((x for x in depts.values() if x['name'] == dname), None)
    if not d: print("!! 找不到部门:", dname); continue
    target_ids.add(d['id'])
    if not d.get('department_ext_id'):
        r = call("/v2.0/department/ext", {"id": d['id'], "ext_id": d['id']})
        print(f"部门设ext: {dname} ({d['id']}) -> code={r.get('code')} msg={r.get('msg')}")
        if r.get("code") != 0:
            print("   失败详情:", r); raise SystemExit(1)
    else:
        print(f"部门ext已有: {dname} = {d.get('department_ext_id')}")

# 2) 员工设 ext_id
for name, eid, dname in pilot:
    e = emps.get(eid)
    if not e: print("!! 找不到员工id:", eid); continue
    if not e.get('ext_id'):
        r = call("/v2.0/employee/ext", {"id": eid, "ext_id": eid})
        print(f"员工设ext: {name} ({eid}) -> code={r.get('code')} msg={r.get('msg')}")
        if r.get("code") != 0:
            print("   失败详情:", r); raise SystemExit(1)

# 3) upsert 改部门(传原 name/mobile/employee_num,只改 department_infos)
for name, eid, dname in pilot:
    e = emps[eid]
    body = {
        "employee_ext_id": eid,
        "name": e.get("name"),
        "mobile": e.get("mobile", ""),
        "employee_num": e.get("employee_num", ""),
        "department_infos": [{"ext_id": next(x['id'] for x in depts.values() if x['name']==dname)}],
    }
    r = call("/v2.0/employee", body)
    print(f"改部门: {name} -> {dname} code={r.get('code')} msg={r.get('msg')} resp={r.get('data')}")
    if r.get("code") != 0:
        print("   失败详情:", r); raise SystemExit(1)

print("\n== 试点写入完成 ==")
