"""Guard actual native/legacy paths; IAM administration is not attendance read."""
from __future__ import annotations

import json
from urllib.parse import unquote, urlsplit

import frappe

PERSONAL = "hb_attendance_app.hbos_attendance.portal.personal.get_my_attendance"
BUSINESS_TYPES = {"Attendance", "Employee Checkin"}
ROLE_BUSINESS_TYPES = {"Attendance Request", "Shift Type", "Shift Assignment", "Shift Schedule", "Shift Schedule Assignment", "Employee Attendance Tool",
    "HBOS Attendance Import Log", "HBOS Shift Rule", "HBOS Employee Shift", "HBOS Employee Schedule",
    "HBOS Attendance Policy Assignment", "HBOS Leave Record", "HBOS Overtime Record", "HBOS Rest Leave Record"}


def _business_types():
    # Disabling a positive role source must not expose its persisted files or
    # custom records through native fallback permissions.
    return BUSINESS_TYPES | ROLE_BUSINESS_TYPES

HR_ROLES = {"HR User", "HR Manager", "System Manager"}
REPORT_MODULES = {"HBOS Attendance", "Hbos Attendance"}
ATTENDANCE_PAGES = {'hbos-shift-management','hbos-department-board','hbos-attendance-dashboard','hbos-employee-management','hbos-rules-board','海滨考勤工作台'}
PREPARED_METHODS = "frappe.core.doctype.prepared_report.prepared_report."


def iam_enabled():
    return frappe.conf.get("hbos_iam_enabled") in (True, 1, "1")


def _value(row, key, default=None):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def legacy_hr(user=None, *, for_update=False):
    user = user or frappe.session.user
    if not user or user == "Guest" or not frappe.db.get_value("User", user, "enabled", for_update=for_update):
        return False
    if user == "Administrator":
        return True
    if for_update:
        if not frappe.db.get_value('User',user,'enabled',for_update=True):
            return False
        from hbos_portal.iam.temporary_passwords import status as password_status
        if password_status(user).get('pending'):
            return False
    if frappe.conf.get('hbos_iam_roles_enabled') in (True, 1, '1'):
        from hbos_portal.iam.guards import _managed_user
        if _managed_user(user):
            return False
    # A department policy explicitly brings that department into IAM on this
    # opted-in Site. Neither personal nor department-managed users may recover
    # native access from an obsolete coarse HR role.
    if for_update:
        if frappe.db.exists("DocType", "HBOS IAM Policy"):
            if frappe.db.get_value("HBOS IAM Policy", {"subject_type": "User", "subject_name": user}, "name", for_update=True):
                return False
            if frappe.db.exists("DocType", "Employee"):
                employees = frappe.db.sql("select department from `tabEmployee` where user_id=%s for update", (user,), as_dict=True)
                if any(frappe.db.get_value("HBOS IAM Policy", {"subject_type": "Department", "subject_name": _value(row, "department")}, "name", for_update=True) for row in employees if _value(row, "department")):
                    return False
        roles = frappe.db.sql("select role from `tabHas Role` where parenttype='User' and parent=%s for update", (user,), as_dict=True)
        return bool({_value(row, "role") for row in roles}.intersection(HR_ROLES))
    from hbos_portal.iam.guards import _managed_user
    return not _managed_user(user) and bool(set(frappe.get_roles(user)).intersection(HR_ROLES))


def query_conditions(user=None):
    # Ordinary employees use the bounded personal endpoint. Native lists are
    # deliberately unavailable, even for their own records, in this first cut.
    return "" if not iam_enabled() or legacy_hr(user) else "1=0"


def has_permission(doc, user=None, ptype=None, debug=False):
    return True if not iam_enabled() or legacy_hr(user) else False


def _report_is_attendance(name, seen=None):
    if not isinstance(name, str) or not name:
        return False
    seen = set() if seen is None else seen
    if name in seen:
        return False
    seen.add(name)
    row = frappe.db.get_value("Report", name, ["ref_doctype", "module", "reference_report"], as_dict=True)
    return bool(row and (_value(row, "ref_doctype") in _business_types() or _value(row, "module") in REPORT_MODULES or _report_is_attendance(_value(row, "reference_report"), seen)))


def _attendance_reports():
    rows = frappe.get_all("Report", fields=["name", "ref_doctype", "module", "reference_report"], limit_page_length=0)
    names = {_value(row, "name") for row in rows if _value(row, "ref_doctype") in _business_types() or _value(row, "module") in REPORT_MODULES}
    # Custom Reports can wrap another Custom Report. Do not hide unrelated
    # reports or trust the wrapper's module to classify the underlying data.
    while True:
        linked = {_value(row, "name") for row in rows if _value(row, "reference_report") in names}
        if linked.issubset(names):
            return names
        names.update(linked)


def _prepared_report(name, *, for_update=False):
    if not isinstance(name, str) or not name:
        return None
    return frappe.db.get_value("Prepared Report", name, ["name", "report_name", "owner"], as_dict=True, for_update=for_update)


def _prepared_is_attendance(name):
    row = _prepared_report(name)
    return bool(row and _report_is_attendance(_value(row, "report_name")))


def _attachment_is_attendance(doc):
    kind, name = _value(doc, "attached_to_doctype"), _value(doc, "attached_to_name")
    return kind in _business_types() or (kind == 'Page' and name in ATTENDANCE_PAGES) or (kind == "Report" and _report_is_attendance(name)) or (kind == "Prepared Report" and _prepared_is_attendance(name))


def _file_references(doc):
    # Core downloads permit any readable File sharing a URL. Inspect every
    # alias, including a later innocuous attachment owned by the requester.
    rows = [doc]
    file_url = _value(doc, "file_url")
    if isinstance(file_url, str) and file_url:
        rows.extend(frappe.get_all("File", filters={"file_url": file_url}, fields=["name", "attached_to_doctype", "attached_to_name"], limit_page_length=0))
    return rows


def _file_is_attendance(doc):
    return any(_attachment_is_attendance(row) for row in _file_references(doc))


def prepared_report_has_permission(doc, user=None, ptype=None, debug=False):
    return not iam_enabled() or not _report_is_attendance(_value(doc, "report_name")) or legacy_hr(user)


def file_has_permission(doc, user=None, ptype=None, debug=False):
    return not iam_enabled() or not _file_is_attendance(doc) or legacy_hr(user)


def prepared_report_query_conditions(user=None):
    if not iam_enabled() or legacy_hr(user):
        return ""
    names = _attendance_reports()
    if not names:
        return ""
    values = ",".join(frappe.db.escape(name) for name in sorted(names))
    return f"coalesce(`tabPrepared Report`.`report_name`,'') not in ({values})"


def _attachment_sql(alias, reports):
    kinds = ",".join(frappe.db.escape(kind) for kind in sorted(_business_types()))
    kind, name = f"coalesce({alias}.`attached_to_doctype`,'')", f"coalesce({alias}.`attached_to_name`,'')"
    conditions = [f"{kind} in ({kinds})"]
    pages=",".join(frappe.db.escape(page) for page in sorted(ATTENDANCE_PAGES))
    conditions.append(f"({kind}='Page' and {name} in ({pages}))")
    if reports:
        values = ",".join(frappe.db.escape(report) for report in sorted(reports))
        conditions.extend([
            f"({kind}='Report' and {name} in ({values}))",
            f"({kind}='Prepared Report' and exists (select 1 from `tabPrepared Report` iam_pr where iam_pr.name={name} and iam_pr.report_name in ({values})))",
        ])
    return "(" + " or ".join(conditions) + ")"


def file_query_conditions(user=None):
    if not iam_enabled() or legacy_hr(user):
        return ""
    reports = _attendance_reports()
    direct = _attachment_sql("`tabFile`", reports)
    alias = _attachment_sql("iam_file", reports)
    return f"not ({direct} or (coalesce(`tabFile`.`file_url`,'')<>'' and exists (select 1 from `tabFile` iam_file where iam_file.file_url=`tabFile`.`file_url` and {alias})))"


def _before(doc):
    getter = getattr(doc, "get_doc_before_save", None)
    return getter() if callable(getter) else None


def _require_prepared_owner(row):
    # A worker may run as Administrator. Its execution identity never turns a
    # revoked or IAM-managed Prepared Report owner into an authorised exporter.
    if not _value(row, "owner") or not legacy_hr(_value(row, "owner"), for_update=True):
        _deny()


def guard_prepared_report(doc, method=None):
    if not iam_enabled():
        return
    subjects = [row for row in (_before(doc), doc) if row]
    if not any(_report_is_attendance(_value(row, "report_name")) for row in subjects):
        return
    if not legacy_hr(for_update=True):
        _deny()
    if method == "on_trash":
        return
    # Check the stored original owner as well as an attempted reassignment.
    # A privileged worker cannot launder an existing export by changing owner.
    stored = _prepared_report(_value(doc, "name"), for_update=True)
    for row in [*subjects, *([stored] if stored else [])]:
        _require_prepared_owner(row)


def guard_file(doc, method=None):
    if not iam_enabled():
        return
    from hb_attendance_app.hbos_attendance.portal.export_scope import authorizes_new_file
    if authorizes_new_file(doc,method):
        return
    from hb_attendance_app.hbos_attendance.portal.import_scope import authorizes_new_file as import_file
    if import_file(doc,method):
        return
    subjects = [row for row in (_before(doc), doc) if row]
    references = [ref for row in subjects for ref in _file_references(row)]
    if not any(_attachment_is_attendance(row) for row in references):
        return
    if not legacy_hr(for_update=True):
        _deny()
    if method == "on_trash":
        return
    if _value(doc, "is_private") not in (1, True, "1"):
        frappe.throw("考勤附件须保存在私有文件区域。", frappe.PermissionError)
    for row in references:
        if _value(row, "attached_to_doctype") == "Prepared Report":
            prepared = _prepared_report(_value(row, "attached_to_name"), for_update=True)
            if prepared and _report_is_attendance(_value(prepared, "report_name")):
                _require_prepared_owner(prepared)


def check_background_job(method=None, kwargs=None, transaction_type=None):
    """Recheck the fixed native report jobs before data is read or computed."""
    if not iam_enabled():
        return
    kwargs = kwargs or {}
    if callable(method):method=method.__module__+'.'+method.__qualname__
    native_attendance=bool(isinstance(method,str) and method.startswith((
        'hb_attendance_app.hbos_attendance.', 'hrms.hr.doctype.attendance.',
        'hrms.hr.doctype.employee_checkin.', 'hrms.hr.doctype.shift_type.',
        'hrms.hr.doctype.shift_assignment.', 'hrms.hr.doctype.employee_attendance_tool.',
        'hrms.hr.doctype.attendance_request.', 'hrms.api.roster.',
    ))) or method=='frappe.utils.background_jobs.execute_doc_method' and kwargs.get('doctype') in _business_types()
    if native_attendance:
        pass  # No synchronous scoped lease is transferable into an old job.
    elif method in (PREPARED_METHODS + "generate_report", PREPARED_METHODS + "convert_json_to_csv"):
        name = kwargs.get("prepared_report") or kwargs.get("prepared_report_name")
        row = _prepared_report(name, for_update=True)
        if not row or not _report_is_attendance(_value(row, "report_name")):
            return
        _require_prepared_owner(row)
    elif method == "frappe.desk.query_report.run_export_query_job":
        params = _json(kwargs.get("form_params"))
        if not isinstance(params, dict) or not _report_is_attendance(params.get("report_name")):
            return
    else:
        return
    # Frappe's queue stores the enqueuing user separately from the current
    # execution session. An Administrator worker cannot lend its authority.
    job_user = _value(getattr(frappe.local, "job", None), "user")
    if not job_user or not legacy_hr(job_user, for_update=True):
        _deny()


def _json(value):
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


def _check_named_document(kind, name):
    if kind in _business_types() or (kind == "Report" and _report_is_attendance(name)) or (kind == "Prepared Report" and _prepared_is_attendance(name)):
        _deny()
    if kind == "File" and isinstance(name, str):
        row = frappe.db.get_value("File", name, ["name", "file_url", "attached_to_doctype", "attached_to_name"], as_dict=True)
        if row and _file_is_attendance(row):
            _deny()


def _check_document_payload(doc):
    if isinstance(doc, list):
        for row in doc:
            _check_document_payload(row)
    elif isinstance(doc, dict):
        _check_named_document(doc.get("doctype"), doc.get("name"))
        if doc.get("doctype") == "Prepared Report" and _report_is_attendance(doc.get("report_name")):
            _deny()
        if doc.get("doctype") == "File" and _file_is_attendance(doc):
            _deny()


def _deny():
    frappe.throw("此原生入口未向当前账号开放，请从当前角色获准的考勤页面办理。", frappe.PermissionError)


def _check_widget_source(kind, name=None, raw=None):
    if kind not in {'Dashboard Chart','Number Card','Dashboard Chart Source'}:return
    fields=[field for field in ('document_type','report_name','source','method') if frappe.db.has_column(kind,field)]
    row=raw if isinstance(raw,dict) else frappe.db.get_value(kind,name,fields,as_dict=True) if name and fields else None
    if not row:return
    if _value(row,'document_type') in _business_types() or _report_is_attendance(_value(row,'report_name')) or str(_value(row,'method') or '').startswith('hb_attendance_app.'):
        _deny()
    if kind=='Dashboard Chart' and _value(row,'source'):
        _check_widget_source('Dashboard Chart Source',_value(row,'source'))


def check_request():
    # Non-opted-in attendance Sites keep the original native path without
    # requiring the optional Portal package just to serve a request.
    if not iam_enabled():
        return
    # This pre-dispatch guard only reads authorization. A retry starts a fresh
    # transaction and re-runs every guard before any endpoint command can run.
    from hbos_portal.iam import policy
    return policy.current_read(_check_request)


def _check_request():
    request = getattr(frappe.local, "request", None)
    user = getattr(frappe.session, "user", None)
    if not iam_enabled() or not request or not user or user == "Guest" or legacy_hr(user):
        return
    path = unquote(request.path)
    args = frappe.local.form_dict or {}
    command = str(args.get("cmd") or "")
    if "/method/" in path:
        command = path.split("/method/", 1)[1]
    integrated = {
        *{'hb_attendance_app.hbos_attendance.portal.imports.'+name for name in ('preview_import','execute_import')},
        *{'hb_attendance_app.hbos_attendance.portal.scoped_exports.'+name for name in ('create_export','download_export')},
        *{'hb_attendance_app.hbos_attendance.list_data.'+name for name in ('get_list','get_filter_options')},
        *{'hb_attendance_app.hbos_attendance.portal.calculations.'+name for name in ('calculation_employees','preview_calculation','execute_calculation','get_employee_policies','save_employee_policy')},
        *{'hb_attendance_app.hbos_attendance.portal.corrections.' + name for name in ('list_correction_employees','list_corrections','get_correction_context','create_correction','update_correction','transition_correction')},
        *{'hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.' + name for name in ('get_employees','get_departments','get_department_attendance')},
        *{'hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.' + name for name in ('get_shift_overview', 'get_department_shifts', 'get_department_employees', 'get_employee_bound_shifts', 'update_shift_rule', 'create_shift_rule', 'set_rule_status', 'delete_shift_rule', 'bind_employee_shifts')},
        'hb_attendance_app.hbos_attendance.page.hbos_attendance_dashboard.dashboard_data.get_data',
        'hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data.get_data',
        *{'hb_attendance_app.hbos_attendance.report_data.' + key for key in ('get_monthly_summary','get_checkin_flow','get_attendance_results','get_monthly_staging')},
    }
    role_path = frappe.conf.get('hbos_iam_roles_enabled') in (True,1,'1') and command in integrated
    if command.startswith("hb_attendance_app.") and command != PERSONAL and not role_path:
        _deny()
    for prefix in ("/api/resource/", "/api/v2/document/", "/api/v2/doctype/"):
        if path.startswith(prefix):
            parts = path[len(prefix):].split("/")
            _check_named_document(parts[0], parts[1] if len(parts) > 1 else None)
    doctype = args.get("doctype") or args.get("dt")
    _check_named_document(doctype, args.get("name") or args.get("docname") or args.get("dn"))
    names = _json(args.get("names"))
    if isinstance(names, list):
        for name in names:
            _check_named_document(doctype, name)
    for field in ("docs", "doc", "document", "data"):
        _check_document_payload(_json(args.get(field)))
    if command.startswith(("hrms.hr.doctype.employee_checkin.", "hrms.hr.doctype.attendance.", "hrms.hr.doctype.attendance_tool.", "hrms.hr.doctype.employee_attendance_tool.", "hrms.api.roster.")) or command in {
        'hrms.overrides.employee_master.get_timeline_data',
        'hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet.get_attendance_years',
    }:
        _deny()
    if frappe.conf.get('hbos_iam_roles_enabled') in (True,1,'1'):
        if command.startswith(('hrms.hr.doctype.shift_','hrms.hr.doctype.attendance_request.')) or command in {
            'hrms.api.'+name for name in ('get_attendance_calendar_events','get_attendance_for_calendar','get_shift_requests','get_attendance_requests','get_shift_request_approvers','get_shifts')
        }:
            _deny()
        widgets={'frappe.desk.doctype.dashboard_chart.dashboard_chart.':'Dashboard Chart','frappe.desk.doctype.number_card.number_card.':'Number Card'}
        for prefix,kind in widgets.items():
            if command.startswith(prefix):
                _check_widget_source(kind,args.get('chart_name') or args.get('card_name') or args.get('name'),_json(args.get('doc')))
    report = args.get("report_name") or args.get("report")
    if _report_is_attendance(report):
        _deny()
    # Native conversion does not check its Prepared Report at all. Query Report
    # rendering also accepts an explicit `dn`, independent of report_name.
    prepared = args.get("prepared_report_name")
    if command.startswith(PREPARED_METHODS):
        prepared = prepared or args.get("dn")
        if command.endswith(".stop_prepared_report"):
            prepared = prepared or args.get("report_name")
    if command.startswith("frappe.desk.query_report."):
        prepared = prepared or args.get("dn")
        filters = _json(args.get("filters"))
        if isinstance(filters, dict):
            prepared = prepared or filters.get("prepared_report_name")
    if _prepared_is_attendance(prepared):
        _deny()
    if command.startswith(("frappe.core.api.file.", "frappe.core.doctype.file.file.")):
        _check_named_document("File", args.get("name"))
        files = _json(args.get("files"))
        if isinstance(files, list):
            for item in files:
                _check_named_document("File", item if isinstance(item, str) else _value(item, "name"))
    file_url = args.get("file_url") or args.get("file_path") or (path if path.startswith(("/private/files/", "/files/")) else None)
    if file_url:
        # A private attachment to an attendance document/report must not escape
        # through a generic file endpoint or a previous background export.
        file_url = unquote(urlsplit(str(file_url)).path)
        files = frappe.get_all("File", filters={"file_url": file_url}, fields=["attached_to_doctype", "attached_to_name"], limit_page_length=0)
        for row in files:
            if _attachment_is_attendance(row):
                _deny()
