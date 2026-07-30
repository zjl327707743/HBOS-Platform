import frappe
import tempfile
import os
from datetime import datetime


@frappe.whitelist()
def export_xlsx(month=None, year=None, from_date=None, to_date=None, employee=None, department=None):
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