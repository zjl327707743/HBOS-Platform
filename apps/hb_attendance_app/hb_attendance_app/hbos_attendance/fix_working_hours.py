"""一次性修复脚本：为 HBOS 配对算法生成的 Attendance 记录回填 working_hours。

用法（在后端容器内）:
    bench --site frontend execute hb_attendance_app.hbos_attendance.fix_working_hours.run
"""
import frappe
from datetime import timedelta
from collections import defaultdict


def run():
    from hb_attendance_app.hbos_attendance import api

    # 读取所有 HBOS 生成的 Present 记录
    hbos_atts = frappe.db.sql("""
        SELECT a.name, a.employee, a.attendance_date, a.status, a.shift,
               a.late_entry, emp.employee_number
        FROM tabAttendance a
        JOIN tabEmployee emp ON emp.name = a.employee
        WHERE a.name LIKE 'HBOS-ATT-%%' AND a.status = 'Present'
    """, as_dict=True)

    if not hbos_atts:
        frappe.msgprint("没有 HBOS 生成的 Present 记录")
        return {"updated": 0, "skipped": 0}

    # 读取打卡记录（覆盖 HBOS 记录日期范围，前后各留 1 天用于跨天配对）
    dates = [a["attendance_date"] for a in hbos_atts]
    min_date = min(dates)
    max_date = max(dates)
    range_start = (min_date - timedelta(days=1)).strftime("%Y-%m-%d")
    range_end = (max_date + timedelta(days=1)).strftime("%Y-%m-%d")

    all_ck = frappe.db.sql("""
        SELECT ec.employee, ec.time, emp.employee_number
        FROM `tabEmployee Checkin` ec
        JOIN tabEmployee emp ON emp.name = ec.employee
        WHERE DATE(ec.time) BETWEEN %s AND %s
        ORDER BY ec.employee, ec.time
    """, (range_start, range_end), as_dict=True)

    by_emp = defaultdict(list)
    for ck in all_ck:
        by_emp[ck["employee"]].append(ck)

    # 与 api.py 配对算法一致：对每个员工做贪心配对并计算工作时长
    updated = 0
    skipped = 0

    for att in hbos_atts:
        emp = att["employee"]
        date_str = str(att["attendance_date"])
        cks = by_emp.get(emp, [])
        if not cks:
            skipped += 1
            continue

        # 去重: 相邻打卡间隔<10min视为重复, 保留最早的
        dedup_ck = []
        skip_until = None
        for c in cks:
            if skip_until and c["time"] <= skip_until:
                continue
            dedup_ck.append(c)
            skip_until = c["time"] + timedelta(minutes=10)
        cks = dedup_ck

        # 找出当天该员工的配对（与 api.py 相同的贪心规则）
        hours = _pair_for_date(cks, date_str)

        if hours is not None and hours > 0:
            frappe.db.set_value("Attendance", att["name"], "working_hours", hours)
            updated += 1
        else:
            skipped += 1

    frappe.db.commit()
    frappe.msgprint(
        "工作时长回填完成：更新 {} 条，跳过 {} 条（无法配对）".format(updated, skipped)
    )
    return {"updated": updated, "skipped": skipped}


def _pair_for_date(cks, date_str):
    """按 api.py 的贪心配对规则计算某日期的工作时长（小时），无法配对返回 None。"""
    from datetime import timedelta

    used = [False] * len(cks)
    for i in range(len(cks)):
        if used[i]:
            continue
        ck1 = cks[i]
        if str(ck1["time"].date()) != date_str:
            continue
        h = ck1["time"].hour

        # 凌晨打卡(H<4)优先向前配对(跨天班次下班卡)
        if h < 4 and i > 0:
            for p in range(i - 1, -1, -1):
                if used[p]:
                    continue
                gap = (ck1["time"] - cks[p]["time"]).total_seconds() / 3600
                if 0.5 <= gap <= 18:
                    used[p] = True
                    used[i] = True
                    return round(gap, 2)
            used[i] = True
            return None

        # 正常向后配对
        best_j = -1
        for j in range(i + 1, len(cks)):
            if used[j]:
                continue
            gap = (cks[j]["time"] - ck1["time"]).total_seconds() / 3600
            if 0.5 <= gap <= 18:
                cross_day = cks[j]["time"].date() != ck1["time"].date()
                if cross_day:
                    # 早班/行政班(6-14)不允许跨天
                    if 6 <= ck1["time"].hour < 14:
                        continue
                best_j = j
                break

        if best_j == -1:
            used[i] = True
            return None
        ck2 = cks[best_j]
        used[i] = True
        used[best_j] = True
        return round((ck2["time"] - ck1["time"]).total_seconds() / 3600, 2)

    return None
