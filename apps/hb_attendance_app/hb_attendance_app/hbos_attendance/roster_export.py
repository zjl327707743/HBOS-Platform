"""导出「HBOS 班次人员维护表」xlsx（规则看板入口）。

只读：不触发考勤生成，不改数据库。数据来源：在职 Employee + 名单常量 +
班次绑定(HBOS Employee Shift / hbos_fixed_shift) + HBOS Shift Rule + 内置默认班次。
"""
import os
import tempfile
from datetime import datetime

import frappe

from hb_attendance_app.hbos_attendance.pairing import (
    FOUR_SHIFT_NUMS, SPECIAL_SHIFT_NUMS,
)
from hb_attendance_app.hbos_attendance.roster_classify import classify, LIST_SYSTEMS
from hb_attendance_app.hbos_attendance.rule_lists import (
    ADMIN_NUMS, EXEMPT_NUMS, FOOD_NUMS, SAFETY_NUMS,
)
from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS

# 豁免名单中的已注释特殊原因（其余默认"管理层 / 不计异常考勤"）
EXEMPT_REASONS = {
    "11008036": "产假（陈玉姣/王梅林 2026-08-21）",
    "11008053": "产假（陈玉姣/王梅林 2026-08-21）",
    "10008020": "产假（曹凯莉 2026-08-27）",
    "11003033": "长期病假（刘凤岭 2026-08-27）",
    "11003016": "长期病假（马照辉 2026-08-27）",
    "10007006": "豁免人员（刘玉仓 2026-08-27）",
}

# 特殊班次 sheet 的小类定义（顺序固定）
SPECIAL_SECTIONS = (
    ("无菌倒班", SPECIAL_SHIFT_NUMS),
    ("四班次", FOUR_SHIFT_NUMS),
    ("安全倒班", SAFETY_NUMS),
    ("食堂", FOOD_NUMS),
)

# 主表非单一时段体系的描述文本
SYSTEM_DESC = {
    "无菌倒班": "08:30-20:30 / 20:30-08:30（12h 轮）",
    "四班次倒班": "早/中/夜/8:30班 轮（满 8h 算正常）",
    "安全倒班": "早 08:30 / 晚 20:30",
    "食堂": "不判迟到早退",
    "通用倒班": "按打卡时间自动判定",
}

# 单一时段体系迟到起算若规则表缺失时的内置兜底
FALLBACK_LATE = {
    "早班": "08:01", "中班": "16:01", "夜班": "00:01", "晚班": "20:01",
    "行政班": "08:31", "8:30班": "08:31", "无菌早(12h)": "08:31", "无菌晚(12h)": "20:31",
}


def _fmt(t):
    """HH:MM:SS/timedelta/None → 'HH:MM' 或空。"""
    if t is None:
        return ""
    s = str(t)
    parts = s.split(":")
    if len(parts) >= 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
    return s


def _rule_time_for(shift_type, department, rules_by_dept):
    """取某部门+班次类型最匹配的生效规则时间；无则全局；再否则内置默认。

    全局规则与运行时一致：先「全部部门 - HD」，再兜底「全部部门」。
    返回 (时间描述, 迟到起算)。
    """
    today = frappe.utils.today()
    pools = [rules_by_dept.get(department, [])]
    pools.extend(rules_by_dept.get(g, []) for g in ("全部部门 - HD", "全部部门"))
    candidates = []
    for pool in pools:
        candidates = [
            r for r in pool
            if r.shift_type == shift_type and r.status == "生效" and str(r.effective_from) <= today
        ]
        if candidates:
            break
    if candidates:
        r = max(candidates, key=lambda x: str(x.effective_from))
        return (f"{_fmt(r.start_time)}-{_fmt(r.end_time)}", _fmt(r.late_after))
    if shift_type in BUILTIN_SHIFTS:
        b = BUILTIN_SHIFTS[shift_type]
        return (f"{_fmt(b[0])}-{_fmt(b[1])}", _fmt(b[2]))
    return (SYSTEM_DESC.get(shift_type, shift_type), FALLBACK_LATE.get(shift_type, ""))


@frappe.whitelist()
def export_shift_roster():
    """导出班次人员维护表（5-sheet xlsx），返回文件 URL。"""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    except ImportError:
        frappe.throw("请安装 openpyxl: pip install openpyxl")

    today = frappe.utils.today()

    # ---- 数据收集 ----
    emps = frappe.db.get_all(
        "Employee", filters={"status": "Active"},
        fields=["name", "employee_number", "employee_name", "department", "hbos_fixed_shift"],
    )
    if not emps:
        frappe.throw("没有在职员工可导出")

    # 绑定规则 → shift_type（HBOS Employee Shift，is_primary 优先，否则 hbos_fixed_shift）
    bound_map = {}  # employee -> shift_type
    binds = frappe.db.get_all(
        "HBOS Employee Shift", fields=["employee", "shift_rule", "is_primary"])
    rule_type = {r.name: r.shift_type for r in frappe.db.get_all(
        "HBOS Shift Rule", fields=["name", "shift_type"])}
    for b in sorted(binds, key=lambda x: not x.is_primary):  # primary 优先
        bound_map.setdefault(b.employee, rule_type.get(b.shift_rule, ""))
    # 无 HBOS Employee Shift 绑定但有单绑字段 → 回退 hbos_fixed_shift（Rule name → shift_type）
    for e in emps:
        if e.name not in bound_map and e.hbos_fixed_shift:
            bound_map[e.name] = rule_type.get(e.hbos_fixed_shift, "")

    # 生效规则表（部门/班次类型/状态/时间）
    rules_by_dept = {}
    for r in frappe.db.get_all(
        "HBOS Shift Rule",
        fields=["department", "shift_type", "status", "start_time", "end_time", "late_after", "effective_from"],
    ):
        rules_by_dept.setdefault(r.department, []).append(r)

    # ---- 主表行聚合 ----
    rows = {}  # (department, label) -> {"people": [(num, name, origin)], }
    emp_num_to_name_dept = {}

    def fmt_person(num, name):
        return f"{name}({num})" if name else num

    for e in emps:
        num = e.employee_number or ""
        name = e.employee_name or ""
        dept = e.department or ""
        emp_num_to_name_dept[num] = (name, dept)
        bound = bound_map.get(e.name, "")
        label = classify(num, bound)
        if label == "":
            # 豁免名单（EXEMPT 命中 → classify 返回空）：不进主表
            continue
        origin = "绑定" if bound else ("名单" if any(num in s for s, _ in LIST_SYSTEMS) else "通用")
        rows.setdefault((dept, label), []).append((num, name, origin))

    # 名单 sheet 行：仅列在职建档成员（emp_num_to_name_dept 只收 Active 员工；
    # 已离职/未建档工号 get 到空姓名部门，整行不列出，避免空白行）
    exempt_rows = []
    for num in EXEMPT_NUMS:
        name, dept = emp_num_to_name_dept.get(num, ("", ""))
        if not name:
            continue
        exempt_rows.append((num, name, dept, EXEMPT_REASONS.get(num, "管理层 / 不计异常考勤")))
    exempt_rows.sort(key=lambda x: (x[2], x[1]))
    admin_rows = []
    for num in sorted(ADMIN_NUMS):
        name, dept = emp_num_to_name_dept.get(num, ("", ""))
        if not name:
            continue
        admin_rows.append((num, name, dept))

    # ---- Workbook ----
    wb = openpyxl.Workbook()
    FONT = "微软雅黑"
    C_HDR = "2F5B8F"
    C_STRIPE = "F2F6FA"
    THIN = Side(style="thin", color="BFCEDC")
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    def style_header(ws, row, headers, start_col=1):
        for i, h in enumerate(headers):
            c = ws.cell(row=row, column=start_col + i, value=h)
            c.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=C_HDR)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = BORDER

    def style_cell(ws, row, col, value, *, bold=False, center=False, fill=None, wrap=False):
        c = ws.cell(row=row, column=col, value=value)
        c.font = Font(name=FONT, size=10, bold=bold, color="000000")
        c.alignment = Alignment(horizontal="center" if center else "left", vertical="center", wrap_text=wrap)
        c.border = BORDER
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
        return c

    # Sheet1 主表
    ws = wb.active
    ws.title = "部门-班次-人员"
    ws.freeze_panes = "A3"
    ws.column_dimensions["A"].width = 5
    for col, w in zip("BCDEFGH", (16, 13, 22, 11, 6, 60, 8)):
        ws.column_dimensions[col].width = w
    c = ws.cell(row=1, column=1, value=f"HBOS 班次人员维护表（数据日期 {today}，共 {len(emps)} 在职员工）")
    c.font = Font(name=FONT, size=13, bold=True, color=C_HDR)
    style_header(ws, 2, ["序号", "部门", "班次", "上下班时间", "迟到起算", "人数", "人员姓名", "备注"])

    def main_sort_key(item):
        dept, label = item[0]
        return (dept, label)

    r = 3
    for idx, ((dept, label), people) in enumerate(sorted(rows.items(), key=main_sort_key), 1):
        people.sort(key=lambda x: x[0])
        origins = sorted({o for _, _, o in people})
        time_txt, late_txt = _rule_time_for(label, dept, rules_by_dept)
        fill = C_STRIPE if idx % 2 == 0 else None
        style_cell(ws, r, 1, idx, center=True, fill=fill)
        style_cell(ws, r, 2, dept, fill=fill)
        style_cell(ws, r, 3, label, center=True, fill=fill, bold=True)
        style_cell(ws, r, 4, time_txt, center=True, fill=fill)
        style_cell(ws, r, 5, late_txt, center=True, fill=fill)
        style_cell(ws, r, 6, len(people), center=True, fill=fill, bold=True)
        style_cell(ws, r, 7, "、".join(fmt_person(n, nm) for n, nm, _ in people), wrap=True, fill=fill)
        style_cell(ws, r, 8, "/".join(origins), center=True, fill=fill)
        r += 1

    # Sheet2 豁免人员
    ws2 = wb.create_sheet("豁免人员")
    ws2.freeze_panes = "A2"
    for col, w in zip("ABCD", (12, 12, 18, 30)):
        ws2.column_dimensions[col].width = w
    style_header(ws2, 1, ["工号", "姓名", "部门", "原因"])
    for i, (num, name, dept, reason) in enumerate(exempt_rows):
        fill = C_STRIPE if i % 2 else None
        style_cell(ws2, i + 2, 1, num, center=True, fill=fill)
        style_cell(ws2, i + 2, 2, name, center=True, fill=fill)
        style_cell(ws2, i + 2, 3, dept, fill=fill)
        style_cell(ws2, i + 2, 4, reason, fill=fill)

    # Sheet3 特殊班次
    ws3 = wb.create_sheet("特殊班次")
    ws3.freeze_panes = "A2"
    for col, w in zip("ABCD", (13, 12, 12, 18)):
        ws3.column_dimensions[col].width = w
    style_header(ws3, 1, ["小类", "工号", "姓名", "部门"])
    rr = 2
    for label, nums in SPECIAL_SECTIONS:
        for i, num in enumerate(sorted(nums)):
            name, dept = emp_num_to_name_dept.get(num, ("", ""))
            if not name:
                continue  # 仅列在职建档成员
            fill = C_STRIPE if i % 2 else None
            style_cell(ws3, rr, 1, label, center=True, fill=fill)
            style_cell(ws3, rr, 2, num, center=True, fill=fill)
            style_cell(ws3, rr, 3, name, center=True, fill=fill)
            style_cell(ws3, rr, 4, dept, fill=fill)
            rr += 1

    # Sheet4 行政班名单
    ws4 = wb.create_sheet("行政班名单")
    ws4.freeze_panes = "A2"
    for col, w in zip("ABC", (12, 12, 18)):
        ws4.column_dimensions[col].width = w
    style_header(ws4, 1, ["工号", "姓名", "部门"])
    for i, (num, name, dept) in enumerate(admin_rows):
        fill = C_STRIPE if i % 2 else None
        style_cell(ws4, i + 2, 1, num, center=True, fill=fill)
        style_cell(ws4, i + 2, 2, name, center=True, fill=fill)
        style_cell(ws4, i + 2, 3, dept, fill=fill)

    # Sheet5 说明
    ws5 = wb.create_sheet("说明")
    ws5.column_dimensions["A"].width = 100
    lines = [
        f"HBOS 班次人员维护表 —— 生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}，数据日期 {today}",
        "",
        "【主表 部门-班次-人员】行 = 仅实际有人的「部门 × 班次体系」组合（部门取员工 HRMS 真实部门）。",
        "人员归行优先级：豁免名单不进主表；已绑定班次规则的人按规则班次归行（多绑定取主班次，无则第一条，再否则 hbos_fixed_shift）；",
        "  其余按名单归入 无菌倒班/四班次倒班/行政班/安全倒班/食堂；都不命中者归入 通用倒班。",
        "备注列来源：绑定 = 绑定规则；名单 = 系统名单；通用 = 未绑定且不在名单。",
        "",
        "【豁免人员】EXEMPT_NUMS 名单成员（管理层、产假/病假等），不参与迟到/早退/缺勤异常判定，不进主表。",
        "【特殊班次】无菌倒班 / 四班次 / 安全倒班 / 食堂 名单全部成员（在职建档者主表中另有对应体系行）。",
        "【行政班名单】ADMIN_NUMS 名单全部成员（固定 8:30-17:30，08:31 起算迟到，周末双休）。",
        "",
        "名单之间允许交叉（如某员工同时在特殊班次名单与豁免名单，会分列对应 sheet）。",
        "豁免/特殊班次/行政班名单 sheet 均只列出在职建档成员；已离职或未建档（HB- 前缀无档）工号不列出。",
    ]
    for i, line in enumerate(lines, 1):
        c = ws5.cell(row=i, column=1, value=line)
        c.font = Font(name=FONT, size=10, color="000000")
        c.alignment = Alignment(vertical="top")

    # ---- 存 File ----
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    try:
        wb.save(tmp.name)
        with open(tmp.name, "rb") as f:
            file_content = f.read()
    finally:
        os.unlink(tmp.name)

    file_name = f"HBOS班次人员维护表_{today.replace('-', '')}.xlsx"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "content": file_content,
        "is_private": 0,
        "attached_to_doctype": "Page",
        "attached_to_name": "hbos-shift-management",
    })
    file_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return file_doc.file_url
