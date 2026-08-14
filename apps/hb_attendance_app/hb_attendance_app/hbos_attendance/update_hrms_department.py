# -*- coding: utf-8 -*-
import frappe, json, datetime
frappe.init(site="frontend")
frappe.connect()

with open("/tmp/hrbos_input.json", encoding="utf-8") as f:
    inp = json.load(f)
roster_map = inp["roster_map"]
deli_by_name = inp["deli_by_name"]
COMPANY = "HAIBIN"

# ---- 0. 删除 17 个 -H 垃圾部门(先确认无人指向) ----
hs = frappe.db.get_all("Department", filters={"name": ("like", "% - H")}, fields=["name"], limit_page_length=99999)
for h in hs:
    n = frappe.db.count("Employee", {"department": h["name"]})
    if n > 0:
        print("!! 有人指向", h["name"], n, "人,不删"); continue
    try:
        frappe.delete_doc("Department", h["name"], ignore_permissions=True)
        frappe.db.commit()
        print("删除:", h["name"])
    except Exception as e:
        print("删除失败:", h["name"], str(e)[:100])

# ---- 1. 用 set_new_name 建纯名部门 ----
roster_depts = sorted(set(roster_map.values()))
created, existed = [], []
for d in roster_depts:
    if frappe.db.exists("Department", d):
        existed.append(d); continue
    try:
        doc = frappe.get_doc({
            "doctype": "Department",
            "department_name": d,
            "company": COMPANY,
        })
        doc.set_new_name(set_name=d)   # 显式 name + 跳过 autoname
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        created.append(d)
    except Exception as e:
        print("部门创建失败:", d, "|", str(e)[:120])
print("部门-已存在:", len(existed), "| 新建:", len(created))
print("新建:", created)

# ---- 2. 补建档 26 人(23 失败 + 3 冲突用 HB- 兜底) ----
all_emp = frappe.db.get_all("Employee", fields=["employee_name","employee_number"], limit_page_length=99999)
emp_by_name = {}
for e in all_emp:
    emp_by_name.setdefault(e["employee_name"].strip(), []).append(e)
missing = sorted(set(roster_map) - set(emp_by_name.keys()))
print("待建档:", len(missing))

created_emps, report_missing = [], []
for name in missing:
    new_dept = roster_map[name]
    emp_num = deli_by_name.get(name, {}).get("employee_num") or ""
    if not emp_num or frappe.db.exists("Employee", {"employee_number": emp_num}):
        emp_num = "HB-" + name   # Deli 无工号或工号冲突 → HB 兜底
    try:
        doc = frappe.get_doc({
            "doctype": "Employee",
            "first_name": name,
            "employee_name": name,
            "employee_number": emp_num,
            "department": new_dept,
            "company": COMPANY,
            "status": "Active",
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "date_of_joining": "2026-08-01",
        })
        doc.insert(ignore_permissions=True)
        created_emps.append(name)
        report_missing.append({"name": name, "status": "建档成功", "emp_num": emp_num, "new_dept": new_dept})
    except Exception as e:
        report_missing.append({"name": name, "status": "建档失败", "emp_num": emp_num, "new_dept": new_dept, "error": str(e)[:100]})
        print("建档失败:", name, "|", str(e)[:100])
frappe.db.commit()
print("新建员工:", len(created_emps), "→", created_emps)
if report_missing:
    fails = [m for m in report_missing if m["status"] != "建档成功"]
    if fails:
        print("仍有失败:", fails)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
with open(f"/tmp/hrbos_report_fix_{stamp}.json", "w", encoding="utf-8") as f:
    json.dump({"created_depts": created, "missing_created": report_missing}, f, ensure_ascii=False, indent=1)
print("报告: /tmp/hrbos_report_fix_%s.json" % stamp)
frappe.destroy()
