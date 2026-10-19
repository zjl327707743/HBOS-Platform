"""Private synchronous export lease. Never set by HTTP parameters or a job flag."""
from contextlib import contextmanager
from contextvars import ContextVar

_current=ContextVar('attendance_role_export',default=None)


def active(kind=None):
    value=_current.get()
    return value if value and (kind is None or value['kind']==kind) else None


def authorizes_new_file(doc,method):
    value=active()
    if not value or method not in {'before_insert','before_validate'} or not doc.is_new():return False
    import frappe
    target=('Page','hbos-shift-management') if value['kind']=='roster' else ('Report','月度考勤汇总')
    return (doc.attached_to_doctype,doc.attached_to_name)==target and doc.is_private in (1,True,'1') and doc.owner==value['actor']==frappe.session.user


@contextmanager
def execution(value):
    if value.get('kind') not in {'monthly','exceptions','roster'}:raise ValueError('Unknown export')
    token=_current.set(value)
    try:yield
    finally:_current.reset(token)


def filters(doctype,original=None):
    value=active('roster')
    original=dict(original or {})
    if value is None:return original
    field={'Employee':'name','HBOS Shift Rule':'department','HBOS Employee Shift':'employee','HBOS Attendance Policy Assignment':'employee'}.get(doctype)
    if field is None:raise ValueError('Unknown roster source')
    original[field]=['in',value['departments'] or ['']] if field=='department' else ['in',value['employee_names'] or ['']]
    return original


def rows(doctype,**kwargs):
    import frappe
    if active('roster'):
        from hb_attendance_app.hbos_attendance.portal.role_scope import current_rows
        return current_rows(doctype,**kwargs)
    return frappe.db.get_all(doctype,**kwargs)


def today(default):
    value=active('roster')
    return value['date_to'] if value else default


def annotate(workbook):
    value=active()
    if not value:return
    sheet=workbook.create_sheet('导出范围')
    sheet.column_dimensions['A'].width=100
    sheet.append([value['scope']])
    sheet.append([value['date_from']+' 至 '+value['date_to']])
    sheet.append(['全部所选归属已核验。' if value['coverage']['complete'] else '部分历史归属缺少依据；本文件仅含可证记录，不代表完整公司结果。'])
    sheet.append(['文件下载时会重新核验当前账号、功能及对应员工范围。'])
    # Existing renderers write only literal values. Keep user-controlled names
    # literal in spreadsheets too; no formula or external-link execution.
    for page in workbook:
        for row in page:
            for cell in row:
                if isinstance(cell.value,str) and cell.value.startswith(('=','+','-','@')):
                    cell.value="'"+cell.value
