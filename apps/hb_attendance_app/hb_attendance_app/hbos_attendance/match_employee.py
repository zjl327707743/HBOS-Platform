"""匹配得力云工号到 HBOS Employee 并更新打卡记录"""
import frappe


def match_and_update_employee():
    # 1. 先建立工号 -> HBOS Employee name 的映射
    emp_map = {}
    for emp in frappe.db.sql("SELECT employee_number, name, employee_name FROM tabEmployee WHERE employee_number IS NOT NULL AND employee_number != ''", as_dict=1):
        emp_map[emp["employee_number"]] = emp

    print(f"HBOS Employee 总数: {len(emp_map)}")

    # 2. 获取全部得力云打卡记录
    records = frappe.db.sql("""
        SELECT name, hbos_employee_num, employee_name
        FROM `tabEmployee Checkin`
        WHERE name LIKE 'DELICLOUD-%%'
    """, as_dict=1)
    print(f"得力云打卡记录总数: {len(records)}")

    # 3. 按工号匹配并更新
    matched = 0
    unmatched = 0

    for rec in records:
        emp_num = rec.get("hbos_employee_num", "")
        emp_info = emp_map.get(emp_num)
        if emp_info:
            # 更新 employee 字段，指向 HBOS Employee; employee_name 从 Employee 自动 fetch
            frappe.db.sql("""
                UPDATE `tabEmployee Checkin`
                SET employee = %s
                WHERE name = %s
            """, (emp_info["name"], rec["name"]))
            matched += 1
        else:
            unmatched += 1

    frappe.db.commit()
    print(f"\n匹配成功: {matched}")
    print(f"未匹配 (无对应HBOS员工或空工号): {unmatched}")

    # 4. 验证
    total = frappe.db.sql("SELECT COUNT(*) as c FROM `tabEmployee Checkin` WHERE name LIKE 'DELICLOUD-%%'")[0][0]
    with_emp = frappe.db.sql("SELECT COUNT(*) as c FROM `tabEmployee Checkin` WHERE name LIKE 'DELICLOUD-%%' AND employee IS NOT NULL")[0][0]
    print(f"\n总记录: {total}, 已关联Employee: {with_emp}, 未关联: {total - with_emp}")

    return {"total": total, "matched": matched, "unmatched": unmatched}