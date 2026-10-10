"""用真实打卡数据离线验证「设备动力部 24 小时连班」配对（只读，不写数据库）。

对照两种口径跑同一批真实打卡：
  - long_duty=False（现行 18h 上限）
  - long_duty=True （新增连班形状放宽）
并打印两者的判定差异，以及数据里真实存在的连班形状 / 被守卫挡住的近似形状。

用法:
  PYTHONPATH=apps/hb_attendance_app python3 tools/verify_long_duty_dryrun.py [起日 止日]

注意与 api.py 的差异（本工具是近似，不是重放）：
  - 班次判定用 verify_pairing_dryrun.py 的 shift_fn，未接固定班次绑定与 HBOS Shift Rule；
    本工具只关心 Absent↔Present 的转变，班次名不在核对范围。
  - 未接 emp_leave_dates / emp_rest_dates / schedule_map / GPS 打卡集合；
    这些只会让 api.py 少判缺勤，不会多判，故「新口径把 Absent 变成 Present」的结论方向不受影响。
"""
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "hb_attendance_app"))

from hb_attendance_app.hbos_attendance.pairing import (  # noqa: E402
    pair_employee_checkins, dedup_checkins_with_mapping,
    LONG_DUTY_DEPTS, LONG_DUTY_START_HOURS, LONG_DUTY_END_HOURS,
    LONG_DUTY_MAX_GAP_HOURS, SPLIT_MACHINE_START_DATE,
    IN_TERMINAL_SNS, OUT_TERMINAL_SNS,
)
from hb_attendance_app.hbos_attendance.rule_lists import (  # noqa: E402
    ADMIN_NUMS, SAFETY_NUMS, FOOD_NUMS, EXEMPT_NUMS, LATE_EXEMPT_NUMS,
)

DB_CONTAINER = "hbos-m0-r3a-db-1"
DB_NAME = "_7aecc840db82aaec"
MAX_GAP_HOURS = 18  # api.py regenerate_attendance 的现行上限


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
    env = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DB_ROOT_PASSWORD="):
                return line.split("=", 1)[1]
    sys.exit("未找到 DB_ROOT_PASSWORD")


def query(sql):
    out = subprocess.run(
        ["docker", "exec", DB_CONTAINER, "sh", "-c",
         "mariadb -uroot -p'%s' -D %s -N -e \"%s\" 2>/dev/null"
         % (db_password(), DB_NAME, sql.replace("`", "\\`"))],
        capture_output=True, text=True).stdout
    return [l.split("\t") for l in out.strip().splitlines() if l]


def shape_of(emp_cks):
    """枚举该员工数据里「上班机 07-09 点 → 次日 下班机 07-10 点」的形状。

    必须同时满足设备方向（上班机卡 + 次日下班机卡）——只按时刻窗口统计会把
    「上午上班卡 + 次日上班卡」这种正常早晚班误算成连班（员工 11008011 9/4 的 08:21 上班机
    与 9/5 08:10 上班机即为反例）。
    """
    hits, near = [], []
    by_date = {}
    for c in emp_cks:
        by_date.setdefault(c["time"].date().isoformat(), []).append(c)
    for c in emp_cks:
        if c["time"].date().isoformat() < SPLIT_MACHINE_START_DATE:
            continue
        if c.get("hbos_terminal_sn") not in IN_TERMINAL_SNS:
            continue
        if not (LONG_DUTY_START_HOURS[0] <= c["time"].hour < LONG_DUTY_START_HOURS[1]):
            continue
        nxt = c["time"].date().toordinal() + 1
        for d2, cs in by_date.items():
            if datetime.fromisoformat(d2).toordinal() != nxt:
                continue
            for o in cs:
                if o.get("hbos_terminal_sn") not in OUT_TERMINAL_SNS:
                    continue
                gap = (o["time"] - c["time"]).total_seconds() / 3600
                if gap <= MAX_GAP_HOURS:
                    continue
                in_win = LONG_DUTY_END_HOURS[0] <= o["time"].hour < LONG_DUTY_END_HOURS[1]
                rec = (c["time"].strftime("%m-%d %H:%M"), o["time"].strftime("%m-%d %H:%M"),
                       round(gap, 2))
                if in_win and gap <= LONG_DUTY_MAX_GAP_HOURS:
                    hits.append(rec)
                else:
                    near.append(rec + (("出窗口" if not in_win else "超26h"),))
    return hits, near



def run_pairing(emp_cks, emp_num, eid, long_duty):
    """按 api.py regenerate_attendance 的口径跑一遍配对。

    long_duty 由调用方按部门决定（与 api.py 一致）；此处不再自行判断，
    否则会把只应作用于个别部门的放宽错误地施加到全员。
    """
    deduped, _ = dedup_checkins_with_mapping(emp_cks, terminal_aware=True)
    is_admin = emp_num in ADMIN_NUMS
    skip_forward = is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS or emp_num in EXEMPT_NUMS
    skip_night_lock = is_admin or emp_num in SAFETY_NUMS or emp_num in FOOD_NUMS
    atts, _roles = pair_employee_checkins(
        deduped, eid, emp_num, shift_fn,
        is_exempt=emp_num in EXEMPT_NUMS,
        is_late_exempt=emp_num in LATE_EXEMPT_NUMS,
        is_admin=is_admin,
        skip_forward=skip_forward,
        skip_night_lock=skip_night_lock,
        track_roles=True,
        max_gap_hours=MAX_GAP_HOURS,
        terminal_aware=True,
        long_duty=long_duty,
        now_dt=datetime(2026, 10, 2, 0, 0),
    )
    # 同日多记录时 Present 优先（api.py 的 seen 去重同义），此处按日期收敛成一条
    out = {}
    for a in atts:
        key = a[2]
        if key not in out or (a[3] == "Present" and out[key][3] != "Present"):
            out[key] = a
    return out



def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "2026-08-15"
    end = sys.argv[2] if len(sys.argv) > 2 else "2026-10-01"

    rows = query(
        "SELECT ec.employee, emp.employee_name, emp.employee_number, emp.department, "
        "DATE_FORMAT(ec.time,'%%Y-%%m-%%d %%H:%%i:%%s'), IFNULL(ec.hbos_terminal_sn,'') "
        "FROM `tabEmployee Checkin` ec JOIN tabEmployee emp ON emp.name=ec.employee "
        "WHERE DATE(ec.time) BETWEEN '%s' AND '%s' AND emp.status='Active' "
        "ORDER BY ec.employee, ec.time" % (start, end))
    print("载入打卡 %d 行（%s ~ %s）" % (len(rows), start, end))

    by_emp = {}
    for eid, name, num, dept, ts, sn in rows:
        by_emp.setdefault(eid, []).append({
            "time": datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"),
            "employee_name": name, "employee_number": num,
            "department": dept, "hbos_terminal_sn": sn,
        })

    print("\n===== 1) 真实数据里的连班形状（部门 = %s）=====" % "/".join(sorted(LONG_DUTY_DEPTS)))
    total_hits = 0
    for eid, cks in sorted(by_emp.items(), key=lambda kv: kv[1][0]["employee_name"]):
        dept = cks[0].get("department") or ""
        if dept not in LONG_DUTY_DEPTS:
            continue
        hits, near = shape_of(cks)
        if not hits and not near:
            continue
        name = cks[0]["employee_name"]
        num = cks[0]["employee_number"]
        for rec in hits:
            total_hits += 1
            print("  连班 %s(%s) %s → %s  %.2fh" % (name, num, rec[0], rec[1], rec[2]))
        for rec in near:
            print("  [守卫挡住] %s(%s) %s → %s  %.2fh %s" % (name, num, rec[0], rec[1], rec[2], rec[3]))
    print("  连班形状合计: %d" % total_hits)

    print("\n===== 2) 两种口径的判定差异（按人按日净变化）=====")
    n_dept = n_other = 0
    a2p = p2a = add = drop = 0
    for eid, cks in sorted(by_emp.items(), key=lambda kv: kv[1][0]["employee_name"]):
        emp_num = cks[0].get("employee_number") or ""
        dept = cks[0].get("department") or ""
        # 与 api.py 一致：只有连班部门的员工才开 long_duty
        flagged = dept in LONG_DUTY_DEPTS
        off = run_pairing(cks, emp_num, eid, long_duty=False)
        on = run_pairing(cks, emp_num, eid, long_duty=True) if flagged else off
        diffs = []
        for ds in sorted(set(off) | set(on)):
            sa = off[ds][3] if ds in off else "—"
            sb = on[ds][3] if ds in on else "—"
            if sa != sb:
                diffs.append((ds, sa, sb, on[ds][7] if ds in on else None))
        if not diffs:
            continue
        if flagged:
            n_dept += 1
        else:
            n_other += 1
        print("  %s%s(%s) %s" % ("[连班部门] " if flagged else "[!! 非连班部门变动] ",
                                 cks[0]["employee_name"], emp_num, dept))
        for ds, sa, sb, wh in diffs:
            print("    %s  %s → %s%s" % (ds, sa, sb, ("  工时=%.2fh" % wh) if wh else ""))
            if sa == "Absent" and sb == "Present":
                a2p += 1
            elif sa == "Present" and sb == "Absent":
                p2a += 1
            elif sa == "—":
                add += 1
            elif sb == "—":
                drop += 1

    print("\n===== 汇总 =====")
    print("  变动员工：连班部门 %d 人，非连班部门 %d 人（后者应为 0）" % (n_dept, n_other))
    print("  Absent → Present : %d 条（本次修复的目标）" % a2p)
    print("  新增记录(—→有)   : %d 条" % add)
    print("  移除记录(有→—)   : %d 条" % drop)
    print("  Present → Absent : %d 条（回退信号，非 0 需解释）" % p2a)



if __name__ == "__main__":
    main()
