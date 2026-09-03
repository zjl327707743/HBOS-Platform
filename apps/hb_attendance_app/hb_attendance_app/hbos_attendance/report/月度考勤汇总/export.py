import frappe
import tempfile
import os
from datetime import datetime


@frappe.whitelist()
def export_xlsx(month=None, year=None, from_date=None, to_date=None, employee=None, department=None,
                enable_ai=None):
    """Export the 月度考勤汇总 report as an XLSX file."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        frappe.throw("请安装 openpyxl: pip install openpyxl")

    # Build filters
    filters = {}
    if month:
        filters["month"] = month
    if year:
        filters["year"] = year
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date
    if employee:
        filters["employee"] = employee
    if department:
        filters["department"] = department
    if enable_ai:
        filters["enable_ai"] = enable_ai

    # Run the report
    from hb_attendance_app.hbos_attendance.report.月度考勤汇总.月度考勤汇总 import execute
    columns, data = execute(filters)

    if not data:
        frappe.throw("没有数据可导出")

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "月度考勤汇总"

    # Styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, size=10, color="FFFFFF")
    normal_font = Font(size=10)
    red_font = Font(size=10, color="E03636")
    orange_font = Font(size=10, color="E86C13")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    wrap_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Headers
    for col_idx, col in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=col["label"])
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = wrap_align
        cell.border = thin_border

    # Data rows
    for row_idx, row_data in enumerate(data, 2):
        for col_idx, col in enumerate(columns, 1):
            fieldname = col["fieldname"]
            value = row_data.get(fieldname, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = normal_font
            cell.alignment = wrap_align
            cell.border = thin_border

            # Color code detail columns
            if fieldname == "late_detail" and value:
                cell.font = red_font
            elif fieldname == "early_detail" and value:
                cell.font = orange_font

    # Column widths
    col_widths = {
        1: 12, 2: 12, 3: 20, 4: 10, 5: 10, 6: 10, 7: 10,
        11: 10,  # normal_count
    }
    # Detail columns get wider
    detail_start = len(columns) - 2
    for i in range(1, len(columns) + 1):
        if i <= 10:
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 10
        else:
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 35

    # Freeze header
    ws.freeze_panes = "A2"

    # Save to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    wb.save(tmp.name)

    # Read and return as file
    with open(tmp.name, "rb") as f:
        file_content = f.read()

    os.unlink(tmp.name)

    # Create Frappe file
    file_name = f"月度考勤汇总_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "content": file_content,
        "is_private": 0,
        "attached_to_doctype": "Report",
        "attached_to_name": "月度考勤汇总",
    })
    file_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return file_doc.file_url


@frappe.whitelist()
def export_exceptions(month=None, year=None, from_date=None, to_date=None, employee=None, department=None,
                      enable_ai=None):
    """导出异常考勤报表（总览 / 缺勤汇总 / 迟到早退），剔除豁免名单人员。

    格式对齐 Owner 提供的「HBOS异常考勤报表」参考文件。
    enable_ai 由前端统一透传；本导出为独立异常口径（非 AI 列导出），仅接收不消费。
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        frappe.throw("请安装 openpyxl: pip install openpyxl")

    import calendar
    from collections import defaultdict
    from datetime import date as _date
    from hb_attendance_app.hbos_attendance.api import EXEMPT_NUMS

    # 计算日期范围: 优先 from_date/to_date, 否则按 month/year 折算整月
    if from_date and to_date:
        start, end = str(from_date), str(to_date)
    elif month and year:
        y, m = int(year), int(month)
        start = f"{y}-{m:02d}-01"
        end = f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"
    else:
        frappe.throw("请指定月份或日期范围")

    conditions = [
        "a.attendance_date BETWEEN %(start)s AND %(end)s",
        "(a.late_entry = 1 OR a.early_exit = 1 OR a.status = 'Absent')",
        "emp.status = 'Active'",
    ]
    values = {"start": start, "end": end}
    if employee:
        conditions.append("a.employee = %(employee)s")
        values["employee"] = employee
    if department:
        conditions.append("emp.department = %(department)s")
        values["department"] = department
    # 豁免名单: 不计入异常考勤
    if EXEMPT_NUMS:
        quoted = ",".join("'%s'" % v.replace("'", "") for v in sorted(EXEMPT_NUMS))
        conditions.append("emp.employee_number NOT IN (%s)" % quoted)

    where = " AND ".join(conditions)
    records = frappe.db.sql(
        f"""
        SELECT emp.employee_name, emp.employee_number, emp.department,
               a.attendance_date, a.status, a.shift, a.late_entry, a.early_exit,
               ROUND(a.working_hours, 2) AS working_hours,
               EXISTS(SELECT 1 FROM `tabEmployee Checkin` ec
                      WHERE ec.employee = a.employee AND DATE(ec.time) = a.attendance_date) AS has_checkin
        FROM tabAttendance a
        JOIN tabEmployee emp ON emp.name = a.employee
        WHERE {where}
        ORDER BY a.attendance_date, emp.department, emp.employee_number
        """,
        values,
        as_dict=True,
    )

    if not records:
        frappe.throw("没有异常考勤记录")

    # ============ 样式常量(对齐参考文件) ============
    FONT = "微软雅黑"
    C_TITLE = "2F5B8F"
    C_HDR = "2F5B8F"
    C_STRIPE = "F2F6FA"
    C_RED = "C00000"
    C_ORANGE = "E36C0A"
    GRAY = "808080"
    THIN = Side(style="thin", color="BFCEDC")
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    def st_title(ws, cellref, text, size=16):
        c = ws[cellref]
        c.value = text
        c.font = Font(name=FONT, size=size, bold=True, color=C_TITLE)
        c.alignment = Alignment(horizontal="left", vertical="center")

    def st_sub(ws, cellref, text):
        c = ws[cellref]
        c.value = text
        c.font = Font(name=FONT, size=10, color=GRAY)
        c.alignment = Alignment(horizontal="left", vertical="center")

    def st_header(ws, row, headers, col0=1):
        for i, h in enumerate(headers):
            c = ws.cell(row=row, column=col0 + i, value=h)
            c.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=C_HDR)
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = BORDER

    def st_cell(ws, row, col, value, *, bold=False, color=None, center=False, fill=None, pct=False):
        c = ws.cell(row=row, column=col, value=value)
        c.font = Font(name=FONT, size=10, bold=bold, color=color or "000000")
        c.alignment = Alignment(horizontal="center" if center else "left", vertical="center")
        c.border = BORDER
        if pct:
            c.number_format = "0.0%"
        if fill:
            c.fill = PatternFill("solid", fgColor=fill)
        return c

    # ============ 数据聚合 ============
    SHORT_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    DATES = sorted({str(r["attendance_date"]) for r in records})
    range_days = (_date.fromisoformat(end) - _date.fromisoformat(start)).days + 1

    def weekday_label(dstr):
        d = _date.fromisoformat(dstr)
        return f"{dstr[5:]}({SHORT_WEEKDAYS[d.weekday()]})"

    def short_date(dstr):
        return dstr[5:]

    # 每人: 缺勤/迟到/早退 日期列表
    absent_by_emp = defaultdict(list)   # emp_key -> [(date, has_checkin)]
    late_by_emp = defaultdict(list)
    early_by_emp = defaultdict(list)
    emp_info = {}
    daily = {d: [0, 0, 0] for d in DATES}  # 迟到/早退/缺勤
    for r in records:
        key = (r["employee_number"], r["employee_name"], r["department"])
        emp_info[key] = True
        dstr = str(r["attendance_date"])
        daily[dstr][2] += int(r["status"] == "Absent")
        if r["late_entry"]:
            daily[dstr][0] += 1
            late_by_emp[key].append(dstr)
        if r["early_exit"]:
            daily[dstr][1] += 1
            early_by_emp[key].append(dstr)
        if r["status"] == "Absent":
            absent_by_emp[key].append((dstr, int(r["has_checkin"])))

    total_absent = sum(len(v) for v in absent_by_emp.values())
    absent_emp_count = len(absent_by_emp)
    total_late = sum(len(v) for v in late_by_emp.values())
    total_early = sum(len(v) for v in early_by_emp.values())
    lateearly_emp_count = len({k for k in set(late_by_emp) | set(early_by_emp)})

    # 部门缺勤分布
    dept_absent = defaultdict(int)
    for key, lst in absent_by_emp.items():
        dept_absent[key[2]] += len(lst)
    dept_absent = sorted(dept_absent.items(), key=lambda x: -x[1])

    # ============ Sheet1 总览 ============
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "总览"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    for col, w in zip("BCDEFG", (20, 12, 12, 12, 12, 12)):
        ws.column_dimensions[col].width = w

    st_title(ws, "B2", "HBOS 异常考勤汇总报表", 18)
    st_sub(ws, "B3", f"统计区间：{start} ～ {end}（共 {range_days} 天）    口径：系统考勤判定，剔除豁免名单人员")
    st_sub(ws, "B4", f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}    数据来源：tabAttendance / tabEmployee / HBOS Employee Schedule")

    kpis = [
        ("缺勤", total_absent, "人次·天", C_RED),
        ("涉及缺勤员工", absent_emp_count, "人", C_RED),
        ("迟到", total_late, "人次", C_ORANGE),
        ("早退", total_early, "人次", C_ORANGE),
        ("迟到/早退员工", lateearly_emp_count, "人", C_ORANGE),
    ]
    r = 6
    for i, (label, val, unit, color) in enumerate(kpis):
        c0 = 2 + i * 2
        kc = ws.cell(row=r, column=c0, value=label)
        kc.font = Font(name=FONT, size=10, bold=True, color=GRAY)
        kc.alignment = Alignment(horizontal="left", vertical="bottom")
        vc = ws.cell(row=r + 1, column=c0, value=val)
        vc.font = Font(name=FONT, size=24, bold=True, color=color)
        vc.alignment = Alignment(horizontal="left", vertical="center")
        uc = ws.cell(row=r + 2, column=c0, value=unit)
        uc.font = Font(name=FONT, size=9, color=GRAY)
        uc.alignment = Alignment(horizontal="left", vertical="top")

    st_title(ws, "B11", "每日异常分布", 13)
    st_header(ws, 12, ["日期", "迟到", "早退", "缺勤", "合计"])
    for i, d in enumerate(DATES):
        rr = 13 + i
        fill = C_STRIPE if i % 2 else None
        st_cell(ws, rr, 2, short_date(d), center=True, fill=fill)
        st_cell(ws, rr, 3, daily[d][0], center=True, fill=fill)
        st_cell(ws, rr, 4, daily[d][1], center=True, fill=fill)
        st_cell(ws, rr, 5, daily[d][2], center=True, fill=fill, color=C_RED if daily[d][2] else None)
        st_cell(ws, rr, 6, sum(daily[d]), center=True, fill=fill, bold=True)
    tr = 13 + len(DATES)
    st_cell(ws, tr, 2, "合计", bold=True, center=True, fill="DDE7F2")
    st_cell(ws, tr, 3, total_late, center=True, bold=True, fill="DDE7F2")
    st_cell(ws, tr, 4, total_early, center=True, bold=True, fill="DDE7F2")
    st_cell(ws, tr, 5, total_absent, center=True, bold=True, fill="DDE7F2")
    st_cell(ws, tr, 6, total_late + total_early + total_absent, center=True, bold=True, fill="DDE7F2")

    st_title(ws, "B" + str(tr + 2), "缺勤按部门分布（人次）", 13)
    hdr_row = tr + 3
    st_header(ws, hdr_row, ["部门", "缺勤人次", "占比"])
    for i, (dept, cnt) in enumerate(dept_absent):
        rr = hdr_row + 1 + i
        fill = C_STRIPE if i % 2 else None
        st_cell(ws, rr, 2, dept, fill=fill)
        st_cell(ws, rr, 3, cnt, center=True, fill=fill)
        st_cell(ws, rr, 4, cnt / total_absent, center=True, fill=fill, pct=True)
    tr2 = hdr_row + 1 + len(dept_absent)
    st_cell(ws, tr2, 2, "合计", bold=True, center=True, fill="DDE7F2")
    st_cell(ws, tr2, 3, total_absent, center=True, bold=True, fill="DDE7F2")
    st_cell(ws, tr2, 4, 1.0, center=True, bold=True, fill="DDE7F2", pct=True)

    # ============ Sheet2 缺勤汇总 ============
    ws2 = wb.create_sheet("缺勤汇总")
    ws2.sheet_view.showGridLines = False
    ws2.freeze_panes = "A5"
    st_title(ws2, "A1", f"缺勤汇总（{start} ～ {end[5:]}，剔除豁免名单）", 14)
    st_sub(ws2, "A2", "缺勤日期格式：MM-DD(星期)；有卡/无卡拆分见「有打卡天数」「无打卡天数」列")
    st_sub(ws2, "A3", f"共 {absent_emp_count} 人 / {total_absent} 人次·天")
    st_header(ws2, 4, ["序号", "工号", "姓名", "部门", "缺勤天数", "有打卡天数", "无打卡天数", "缺勤日期"])
    for i, w in enumerate((6, 14, 10, 16, 10, 12, 12, 44)):
        ws2.column_dimensions[get_column_letter(i + 1)].width = w
    # 按缺勤天数降序
    absent_list = sorted(absent_by_emp.items(), key=lambda kv: (-len(kv[1]), kv[0][2], kv[0][1]))
    r = 5
    for i, ((num, name, dept), lst) in enumerate(absent_list):
        fill = C_STRIPE if i % 2 else None
        days_with_ck = sum(1 for _, hc in lst if hc)
        st_cell(ws2, r, 1, i + 1, center=True, fill=fill)
        st_cell(ws2, r, 2, num, center=True, fill=fill)
        st_cell(ws2, r, 3, name, center=True, fill=fill, bold=True)
        st_cell(ws2, r, 4, dept, center=True, fill=fill)
        st_cell(ws2, r, 5, len(lst), center=True, fill=fill, bold=True, color=C_RED)
        st_cell(ws2, r, 6, days_with_ck, center=True, fill=fill)
        st_cell(ws2, r, 7, len(lst) - days_with_ck, center=True, fill=fill)
        st_cell(ws2, r, 8, "、".join(weekday_label(d) for d, _ in sorted(lst)), fill=fill)
        r += 1
    st_cell(ws2, r, 2, "合计", center=True, bold=True, fill="DDE7F2")
    st_cell(ws2, r, 4, f"{absent_emp_count} 人", center=True, bold=True, fill="DDE7F2")
    st_cell(ws2, r, 5, total_absent, center=True, bold=True, fill="DDE7F2")
    st_cell(ws2, r, 6, sum(1 for _, lst in absent_list for _, hc in lst if hc), center=True, fill="DDE7F2")
    st_cell(ws2, r, 7, sum(1 for _, lst in absent_list for _, hc in lst if not hc), center=True, fill="DDE7F2")

    # ============ Sheet3 迟到早退 ============
    ws3 = wb.create_sheet("迟到早退")
    ws3.sheet_view.showGridLines = False
    ws3.freeze_panes = "A5"
    st_title(ws3, "A1", f"迟到 / 早退汇总（{start} ～ {end[5:]}，剔除豁免名单）", 14)
    st_sub(ws3, "A2", "日期格式：MM-DD(星期)")
    st_sub(ws3, "A3", f"共 {lateearly_emp_count} 人 / 迟到 {total_late} 人次 / 早退 {total_early} 人次")
    st_header(ws3, 4, ["序号", "工号", "姓名", "部门", "迟到次数", "早退次数", "迟到日期", "早退日期"])
    for i, w in enumerate((6, 14, 10, 16, 10, 10, 40, 40)):
        ws3.column_dimensions[get_column_letter(i + 1)].width = w
    lateearly_keys = sorted(set(late_by_emp) | set(early_by_emp), key=lambda k: (k[2], k[1]))
    r = 5
    for i, key in enumerate(lateearly_keys):
        num, name, dept = key
        fill = C_STRIPE if i % 2 else None
        late_dates = late_by_emp.get(key, [])
        early_dates = early_by_emp.get(key, [])
        st_cell(ws3, r, 1, i + 1, center=True, fill=fill)
        st_cell(ws3, r, 2, num, center=True, fill=fill)
        st_cell(ws3, r, 3, name, center=True, fill=fill, bold=True)
        st_cell(ws3, r, 4, dept, center=True, fill=fill)
        st_cell(ws3, r, 5, len(late_dates), center=True, fill=fill, bold=True, color=C_ORANGE)
        st_cell(ws3, r, 6, len(early_dates), center=True, fill=fill, bold=True, color=C_RED)
        st_cell(ws3, r, 7, "、".join(weekday_label(d) for d in sorted(late_dates)) or "—", fill=fill)
        st_cell(ws3, r, 8, "、".join(weekday_label(d) for d in sorted(early_dates)) or "—", fill=fill)
        r += 1
    st_cell(ws3, r, 4, f"{lateearly_emp_count} 人", center=True, bold=True, fill="DDE7F2")
    st_cell(ws3, r, 5, total_late, center=True, bold=True, fill="DDE7F2")
    st_cell(ws3, r, 6, total_early, center=True, bold=True, fill="DDE7F2")

    # ============ 保存 ============
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    wb.save(tmp.name)
    with open(tmp.name, "rb") as f:
        file_content = f.read()
    os.unlink(tmp.name)

    file_name = f"HBOS异常考勤报表_{start.replace('-', '')}-{end.replace('-', '')}.xlsx"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "content": file_content,
        "is_private": 0,
        "attached_to_doctype": "Report",
        "attached_to_name": "月度考勤汇总",
    })
    file_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return file_doc.file_url