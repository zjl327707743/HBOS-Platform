"""根据每位员工每天的首次打卡时间匹配班次（DB 时间 = 中国时间）"""
import frappe


def match_shifts():
    employees = frappe.db.sql("""
        SELECT DISTINCT employee, DATE(time) as dt
        FROM `tabEmployee Checkin`
        WHERE name LIKE 'DELICLOUD-%%' AND employee IS NOT NULL
    """, as_dict=1)
    print(f"Unique employee-date groups: {len(employees)}")

    update_count = 0
    shift_stats = {"晚班": 0, "早班": 0, "行政班早班": 0, "中班": 0}

    for row in employees:
        e = row["employee"]
        d = row["dt"]

        # 首次打卡时间（DB 已是中国时间，直接使用）
        first = frappe.db.sql("""
            SELECT MIN(time) as ft FROM `tabEmployee Checkin`
            WHERE employee = %s AND DATE(time) = %s AND name LIKE 'DELICLOUD-%%'
        """, (e, d), as_dict=1)[0]["ft"]

        if not first:
            continue

        h = first.hour
        m = first.minute

        # 班次判断逻辑（中国时间）
        if h < 8:
            # 0:00 - 7:59 → 晚班
            shift = "晚班"
        elif h == 8 and m < 30:
            # 8:00 - 8:29 → 早班（8:00-16:00）
            shift = "早班"
        elif h >= 8 and h < 16:
            # 8:30 - 15:59 → 行政班早班（8:30-17:30）
            shift = "行政班早班"
        elif h >= 16:
            # 16:00 - 23:59 → 中班（16:00-00:00）
            shift = "中班"
        else:
            shift = "行政班早班"

        # 更新该员工该日所有打卡记录
        frappe.db.sql("""
            UPDATE `tabEmployee Checkin`
            SET shift = %s
            WHERE employee = %s AND DATE(time) = %s AND name LIKE 'DELICLOUD-%%'
        """, (shift, e, d))
        update_count += 1
        shift_stats[shift] += 1

        if update_count % 200 == 0:
            frappe.db.commit()
            print(f"  Progress: {update_count}")

    frappe.db.commit()

    # 统计
    print(f"\n=== 班次匹配完成 ===")
    total = 0
    for s, c in shift_stats.items():
        print(f"  {s}: {c} 人天")
        total += c
    print(f"  合计: {total} 人天")

    verify = frappe.db.sql("""
        SELECT shift, COUNT(*) as cnt FROM `tabEmployee Checkin`
        WHERE name LIKE 'DELICLOUD-%%' AND employee IS NOT NULL
        GROUP BY shift
    """, as_dict=1)
    print(f"\n=== 打卡记录分布 ===")
    for v in verify:
        print(f"  {v['shift']}: {v['cnt']} 条")

    null_shift = frappe.db.sql("""
        SELECT COUNT(*) as c FROM `tabEmployee Checkin`
        WHERE name LIKE 'DELICLOUD-%%' AND (shift IS NULL OR shift = '')
    """)[0][0]
    print(f"  未匹配: {null_shift} 条")

    return {"status": "OK", "shifts": shift_stats, "null_check": null_shift}


if __name__ == "__main__":
    match_shifts()