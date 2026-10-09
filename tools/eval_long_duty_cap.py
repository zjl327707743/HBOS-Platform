"""评估：把设备动力部的配对上限调到 26h 的后果（只读，不写库）。

对比三种口径，对真实打卡数据离线跑配对：
  A 基线      max_gap_hours=18，不开 long_duty（= 当前生产行为）
  B 直接放宽  max_gap_hours=26，仅对设备动力部（= 用户字面问题；无形状守卫）
  C 形状守卫  max_gap_hours=18 + long_duty（= 分支 m1-fix-pairing-long-duty 的实现）

关键：`max_gap_hours` 在 pairing.py 里**被五处使用**，放宽它不只影响主配对：
  :410 day_has_span            —— 「当天已有完整班次结构」→ 孤立卡不判缺勤
  :508 主配对上限
  :559 夜班锁定窗口
  :661 另一条配对路径
  :695 shift_may_be_unfinished —— 「班次可能没结束」→ 不判缺勤
故 B 会通过**三条不同机制**一起减少缺勤判定，而 C 只动主配对那一处。

用法（在仓库根目录）：
  PYTHONPATH=apps/hb_attendance_app python3 tools/eval_long_duty_cap.py
"""
import os
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "hb_attendance_app"))

import importlib.util  # noqa: E402

from hb_attendance_app.hbos_attendance.pairing import (  # noqa: E402
    dedup_checkins_with_mapping, pair_employee_checkins,
)


def _load_branch_pairing():
    """加载 m1-fix-pairing-long-duty 分支上的 pairing.py（含 long_duty 形参）。

    直接跑分支的真实代码，而不是在本脚本里复刻形状守卫——复刻出来的东西
    可能与被测对象不一致，那就不是评估了。
    """
    path = "/tmp/pairing_ld.py"
    if not os.path.exists(path):
        sys.exit("缺少 /tmp/pairing_ld.py（用 git show <分支>:<路径> 导出）")
    spec = importlib.util.spec_from_file_location("pairing_ld", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_branch = _load_branch_pairing()
pair_employee_checkins_ld = _branch.pair_employee_checkins
from hb_attendance_app.hbos_attendance.rule_lists import (  # noqa: E402
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, LATE_EXEMPT_NUMS, SAFETY_NUMS,
)

DB = "hbos-m0-r3a-db-1"
DBNAME = "_7aecc840db82aaec"
DEPT = "设备动力部"


def shift_fn(ck_dt, emp_num, cross_day=False):
    h, m = ck_dt.hour, ck_dt.minute
    ts = ck_dt.strftime("%H:%M:%S")
    if h >= 20 or h < 4:
        return ("晚班", h < 4 and ts > "00:00:00")
    if 4 <= h < 8:
        return ("早班", False)
    if h == 8:
        return ("早班", m > 0)
    if 9 <= h < 12:
        return ("行政班早班", True)
    if 12 <= h < 16:
        return ("中班", False)
    if 16 <= h < 20:
        if cross_day:
            return ("晚班", False) if h >= 19 else ("中班", False)
        return ("中班", ts > "16:00:00")
    return ("晚班", False)


def db_password():
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    with open(env) as fh:
        for line in fh:
            if line.startswith("DB_ROOT_PASSWORD="):
                return line.strip().split("=", 1)[1]
    sys.exit("未找到 DB_ROOT_PASSWORD")


def query(sql):
    out = subprocess.run(
        ["docker", "exec", DB, "sh", "-c",
         "mariadb -uroot -p'%s' -D %s -N -e \"%s\" 2>/dev/null"
         % (db_password(), DBNAME, sql.replace("`", "\\`"))],
        capture_output=True, text=True).stdout
    return [l.split("\t") for l in out.strip().splitlines() if l]


def run(cks, emp_num, eid, max_gap, long_duty):
    deduped, _ = dedup_checkins_with_mapping(cks, terminal_aware=True)
    is_admin = emp_num in ADMIN_NUMS
    fn = pair_employee_checkins_ld if long_duty else pair_employee_checkins
    kwargs = dict(
        is_exempt=emp_num in EXEMPT_NUMS,
    )
    if long_duty:
        kwargs["long_duty"] = True
    atts, _roles = fn(
        deduped, eid, emp_num, shift_fn,
        is_exempt=emp_num in EXEMPT_NUMS,
        is_late_exempt=emp_num in LATE_EXEMPT_NUMS,
        is_admin=is_admin,
        skip_forward=is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS or emp_num in EXEMPT_NUMS,
        skip_night_lock=is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS,
        track_roles=True,
        max_gap_hours=max_gap,
        terminal_aware=True,
        now_dt=datetime(2026, 10, 9, 0, 0),
        **({"long_duty": True} if long_duty else {}),
    )
    _ = kwargs
    # 同日多记录 Present 优先（与 api.py 的 seen 去重同义）
    out = {}
    for a in atts:
        key = a[2]
        if key not in out or (a[3] == "Present" and out[key][3] != "Present"):
            out[key] = a
    return out


def main():
    rows = query(
        "SELECT ec.employee, emp.employee_name, emp.employee_number, emp.department, "
        "ec.time, IFNULL(ec.hbos_terminal_sn,'') "
        "FROM `tabEmployee Checkin` ec JOIN tabEmployee emp ON emp.name=ec.employee "
        "WHERE DATE(ec.time) BETWEEN '2026-08-15' AND '2026-10-08' AND emp.status='Active' "
        "ORDER BY ec.employee, ec.time")
    by_emp = {}
    for eid, name, num, dept, ts, sn in rows:
        by_emp.setdefault(eid, []).append({
            "time": datetime.strptime(ts.split(".")[0], "%Y-%m-%d %H:%M:%S"),
            "employee_name": name, "employee_number": num,
            "department": dept, "hbos_terminal_sn": sn,
        })
    print("载入打卡 %d 行，员工 %d 人（8/15–10/08）\n" % (len(rows), len(by_emp)))

    variants = [
        ("A 基线 18h", 18, False),
        ("B 设备部 26h（无形状守卫）", 26, False),
        ("C 形状守卫 26h（分支实现）", 18, True),
    ]

    # 只对设备动力部施加 B 的放宽；其余部门一律 18h
    results = {}
    for label, cap, ld in variants:
        per_emp = {}
        for eid, cks in by_emp.items():
            emp_num = cks[0].get("employee_number") or ""
            dept = cks[0].get("department") or ""
            is_long = (dept == DEPT)
            eff_cap = cap if is_long else 18
            eff_ld = ld if is_long else False
            per_emp[eid] = run(cks, emp_num, eid, eff_cap, eff_ld)
        results[label] = per_emp

    base = results["A 基线 18h"]
    for label, _, _ in variants[1:]:
        cur = results[label]
        a2p = p2a = other = 0
        changed_emps = []
        new_hours = []
        for eid in cur:
            dept = by_emp[eid][0].get("department") or ""
            diffs = []
            for ds in sorted(set(base[eid]) | set(cur[eid])):
                a = base[eid].get(ds)
                b = cur[eid].get(ds)
                sa = a[3] if a else "—"
                sb = b[3] if b else "—"
                if sa == sb:
                    continue
                diffs.append((ds, sa, sb, b[7] if b else None))
                if sa == "Absent" and sb == "Present":
                    a2p += 1
                    if b and b[7]:
                        new_hours.append((by_emp[eid][0]["employee_name"], ds, b[7]))
                elif sa == "Present" and sb == "Absent":
                    p2a += 1
                else:
                    other += 1
            if diffs:
                changed_emps.append((by_emp[eid][0]["employee_name"], dept, len(diffs)))
        print("═══ %s ═══" % label)
        print("  受影响员工 %d 人（其中非设备部 %d 人）"
              % (len(changed_emps), sum(1 for _, d, _ in changed_emps if d != DEPT)))
        print("  Absent → Present : %d" % a2p)
        print("  Present → Absent : %d" % p2a)
        print("  其他转变          : %d" % other)
        if new_hours:
            hs = sorted(h for _, _, h in new_hours)
            print("  新配对班次的工时分布：最小 %.2fh / 中位 %.2fh / 最大 %.2fh"
                  % (hs[0], hs[len(hs) // 2], hs[-1]))
            over24 = [x for x in new_hours if x[2] > 24.5]
            print("  其中 >24.5h 的 %d 条（最长的几条）：" % len(over24))
            for name, ds, h in sorted(over24, key=lambda x: -x[2])[:5]:
                print("      %s %s  %.2fh" % (name, ds, h))
        # 分类「其他转变」：不是状态翻转，而是记录条目的增减
        cats = {}
        for eid in cur:
            for ds in sorted(set(base[eid]) | set(cur[eid])):
                a, b = base[eid].get(ds), cur[eid].get(ds)
                sa = a[3] if a else "—"
                sb = b[3] if b else "—"
                if sa != sb and not (sa == "Absent" and sb == "Present") \
                        and not (sa == "Present" and sb == "Absent"):
                    cats["%s → %s" % (sa, sb)] = cats.get("%s → %s" % (sa, sb), 0) + 1
        if cats:
            print("  其他转变明细：" + " / ".join("%s %d" % kv for kv in sorted(cats.items())))
        print()

    # ── B 与 C 的直接差异：形状守卫到底挡住了什么 ──
    print("═══ B（无守卫）vs C（形状守卫）：守卫挡住了什么 ═══")
    b, c = results["B 设备部 26h（无形状守卫）"], results["C 形状守卫 26h（分支实现）"]
    shown = 0
    for eid in b:
        for ds in sorted(set(b[eid]) | set(c[eid])):
            rb, rc = b[eid].get(ds), c[eid].get(ds)
            sb = rb[3] if rb else "—"
            sc = rc[3] if rc else "—"
            if sb == sc:
                continue
            name = by_emp[eid][0]["employee_name"]
            hb = ("%.2fh" % rb[7]) if rb and rb[7] else "-"
            hc = ("%.2fh" % rc[7]) if rc and rc[7] else "-"
            print("   %s %s   B=%s(%s)  C=%s(%s)" % (name, ds, sb, hb, sc, hc))
            shown += 1
    if not shown:
        print("   （两者完全一致）")
    print()

if __name__ == "__main__":
    main()
