import frappe
from frappe.utils import now_datetime


def create_missing_employees():
    """为得力云中无工号的 21 人创建 HBOS Employee，然后匹配打卡记录"""

    # 21 个缺失员工及所属部门
    missing = [
        ("丰银帅", "仓库行政班"),
        ("郑丹丹", "市场部"),
        ("钱玥", "市场部"),
        ("张志兴", "无菌倒班"),
        ("李笛", "无菌倒班"),
        ("杜加凯", "无菌倒班"),
        ("程大梁", "无菌倒班"),
        ("范青锋", "无菌倒班"),
        ("陈龙禧", "无菌倒班"),
        ("栗春兵", "无菌办公室"),
        ("耿献磊", "无菌办公室"),
        ("孙海涛", "设备动力部办公室"),
        ("孙辉燕", "质量保证部"),
        ("李瑞晨", "质量控制部"),
        ("吕明恒", "食堂"),
        ("岳福芹", "食堂"),
        ("王勇", "食堂"),
        ("王增送", "食堂"),
        ("王慧明", "食堂"),
        ("王新中", "食堂"),
        ("路天广", "食堂"),
    ]

    # 获取最大工号
    max_num = frappe.db.sql("""
        SELECT MAX(CAST(employee_number AS UNSIGNED))
        FROM tabEmployee
        WHERE employee_number REGEXP '^[0-9]+$'
    """)[0][0] or 11009031

    created = 0
    matched = 0

    for i, (name, dept) in enumerate(missing):
        emp_num = str(max_num + i + 1)

        # 查找部门
        dept_name = frappe.db.get_value("Department", dept, "name")
        if not dept_name:
            print(f"  WARNING: 部门 {dept} 不存在，跳过 {name}")
            continue

        # 检查是否已有同名员工
        existing = frappe.db.get_value("Employee", {"employee_name": name}, "name")
        if existing:
            print(f"  员工 {name} 已存在: {existing}")
            emp_record = existing
        else:
            # 创建员工
            emp = frappe.get_doc({
                "doctype": "Employee",
                "first_name": name,
                "employee_name": name,
                "employee_number": emp_num,
                "department": dept_name,
                "company": "HAIBIN",
                "status": "Active",
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2026-07-01",
            })
            emp.insert(ignore_permissions=True)
            frappe.db.commit()
            emp_record = emp.name
            created += 1
            print(f"  ✅ 创建员工: {name} | 工号: {emp_num} | 部门: {dept} | ID: {emp_record}")

        # 匹配得力云打卡记录（按姓名）+ 更新工号
        updated = frappe.db.sql("""
            UPDATE `tabEmployee Checkin`
            SET employee = %s, hbos_employee_num = %s
            WHERE employee_name = %s AND employee IS NULL
        """, (emp_record, emp_num, name))
        if updated:
            matched += updated
            print(f"    更新打卡记录: {updated} 条")

    frappe.db.commit()

    # 处理 employee_number = '10008015' 那条
    still_null = frappe.db.sql("""
        SELECT name, employee_name, hbos_employee_num FROM `tabEmployee Checkin`
        WHERE employee IS NULL AND name LIKE 'DELICLOUD-%%'
    """, as_dict=1)
    if still_null:
        print(f"\n⚠ 仍无法匹配的记录: {len(still_null)}")
        for r in still_null:
            print(f"  {r['name']} | {r['employee_name']} | 工号={r['hbos_employee_num']}")

    print(f"\n=== DONE ===")
    print(f"创建员工: {created}")
    print(f"匹配打卡记录: {matched}")
    print(f"剩余未匹配: {len(still_null) if still_null else 0}")

    return {"created": created, "matched": matched}