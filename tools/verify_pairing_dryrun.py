"""用真实打卡数据离线验证新配对算法（不写数据库，只打印结果）。

用法:
  PYTHONPATH=apps/hb_attendance_app python3 tools/verify_pairing_dryrun.py
"""
import json
import subprocess
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "hb_attendance_app"))

from hb_attendance_app.hbos_attendance.pairing import pair_employee_checkins

# 班次判定: 与 api._get_shift_and_late 一致（测试员工均不在特殊名单）
def shift_fn(ck_dt, emp_num, cross_day=False):
    h = ck_dt.hour
    m = ck_dt.minute
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


def main():
    dbpass = ""
    env = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DB_ROOT_PASSWORD="):
                dbpass = line.split("=", 1)[1]
    if not dbpass:
        print("未找到 DB_ROOT_PASSWORD")
        sys.exit(1)

    q = ("SELECT ec.employee, emp.employee_name, emp.employee_number, emp.department, "
         "DATE_FORMAT(ec.time,'%Y-%m-%d %H:%i:%s') FROM `tabEmployee Checkin` ec "
         "JOIN tabEmployee emp ON emp.name=ec.employee "
         "WHERE DATE(ec.time) BETWEEN '2026-08-01' AND '2026-08-05' "
         "ORDER BY ec.employee, ec.time")
    out = subprocess.run(
        ["docker", "exec", "hbos-m0-r3a-db-1", "sh", "-c",
         f"mariadb -uroot -p'{dbpass}' -D _7aecc840db82aaec -N -e \"{q.replace(chr(96), chr(92) + chr(96))}\" 2>/dev/null"],
        capture_output=True, text=True).stdout

    by_emp = {}
    for line in out.strip().splitlines():
        eid, name, num, dept, ts = line.split("\t", 4)
        by_emp.setdefault(eid, []).append({
            "time": datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"),
            "employee_name": name, "department": dept,
        })

    total_absent = 0
    total_present = 0
    for eid, cks in by_emp.items():
        atts = pair_employee_checkins(cks, eid, "", shift_fn)
        for a in atts:
            if a[3] == "Absent":
                total_absent += 1
            elif a[3] == "Present":
                total_present += 1
        # 只打印有缺勤记录的员工
        absents = [a for a in atts if a[3] == "Absent"]
        if absents:
            name = cks[0]["employee_name"]
            for a in absents:
                print(f"缺勤 {name} {a[2]}")
            for a in atts:
                print(f"  {a[2]} {a[3]} {a[4]} late={a[5]} hours={a[7]}")

    print(f"\n总计: Present={total_present} Absent={total_absent}")


if __name__ == "__main__":
    main()
