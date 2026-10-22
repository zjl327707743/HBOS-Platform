from __future__ import annotations

import frappe

from hbos_portal.iam import guards, policy, work_commands


def _call(function, *, read_only=False):
    try:
        if frappe.conf.get("hbos_iam_enabled") not in (True, 1, "1"):
            frappe.throw("此站点尚未启用IAM实施候选。", frappe.PermissionError)
        return {"ok": True, "data": policy.current_read(function) if read_only else function()}
    except Exception as exc:
        status = frappe.local.response.get("http_status_code")
        if isinstance(exc, frappe.PermissionError):
            status, code, message = 403, "FORBIDDEN", str(exc)
        elif isinstance(exc, (frappe.QueryDeadlockError, frappe.QueryTimeoutError)):
            status, code, message = (409, "READ_CONFLICT", "读取遇到暂时冲突，请重试查询。") if read_only else (409, "CONFLICT", "并发操作使当前事务失效，改动未保存，请刷新后重新核对。")
        elif isinstance(exc, frappe.TimestampMismatchError) or status == 409:
            status, code, message = 409, "CONFLICT", str(exc)
        elif isinstance(exc, (frappe.ValidationError, ValueError, TypeError)):
            status, code, message = 400, "INVALID_REQUEST", str(exc)
        else:
            status, code, message = 500, "SERVICE_ERROR", "服务暂不可用，已保存内容不变。"
            # Never log request arguments, identity proofs, credentials or SQL.
            frappe.logger("hbos_iam").error("IAM service failure (%s)", type(exc).__name__)
        # A caught exception must never turn a partial write into a successful POST.
        frappe.db.rollback()
        frappe.local.response["http_status_code"] = status
        return {"ok": False, "error": {"code": code, "message": message, "retryable": status in {409, 500}}}


def _only(kwargs, fields=()):
    # Frappe's dispatcher includes its resolved method as cmd in **kwargs.
    # Inspect the wire as well: dispatcher filtering must not silently drop an
    # unsupported client field before this boundary sees it.
    wire = getattr(frappe, "form_dict", None) or {}
    if set(kwargs) - {"cmd"} or set(wire) - set(fields) - {"cmd"}:
        frappe.throw("请求含有未允许的字段。", frappe.ValidationError)


def _current_departments(operation, app_id="iam", *, lock=False):
    """Narrow by delegation first, then use locking reads and current authorization.

    managed_departments is a candidate list, never proof that a stale organization
    row is still in scope. InnoDB repeatable-read snapshots cannot establish that.
    """
    candidates = sorted(set(guards.managed_departments(operation, app_id=app_id)))
    if not candidates:
        return []
    # Locks are for commands that then mutate the target. Reads re-authorize
    # every row anyway, and FOR UPDATE here serialized parallel page reads.
    rows = frappe.db.sql(
        "select name,department_name,parent_department,company,disabled,lft "
        "from `tabDepartment` where name in %(departments)s order by name" + (" for update" if lock else ""),
        {"departments": tuple(candidates)}, as_dict=True,
    )
    result = []
    for row in rows:
        try:
            guards.require_capability(operation, department=row.name, company=row.company, app_id=app_id)
        except frappe.PermissionError:
            continue
        result.append(row)
    return result


def _readable_app(app_id, *, lock=False):
    if not isinstance(app_id, str) or not any(app["id"] == app_id for app in policy.registered_apps()):
        frappe.throw("应用未注册。", frappe.ValidationError)
    rows = _current_departments("iam.access.read", app_id, lock=lock)
    if not rows:
        frappe.throw("没有该应用范围的配置读取权限。", frappe.PermissionError)
    return {row.name: row for row in rows}


EMPLOYEE_SELECT = "name,employee_name,employee_number,department,company,designation,user_id,status,modified"


def _current_employees(departments, *, employee_id=None, user_id=None, search="", lock=True):
    if not departments:
        return []
    where = ["department in %(departments)s"]
    values = {"departments": tuple(sorted(departments))}
    if employee_id is not None:
        where.append("name=%(employee_id)s")
        values["employee_id"] = employee_id
    if user_id is not None:
        where.append("user_id=%(user_id)s")
        values["user_id"] = user_id
    if search:
        where.append("(employee_name like %(search)s or employee_number like %(search)s)")
        values["search"] = "%" + search + "%"
    return frappe.db.sql(
        "select " + EMPLOYEE_SELECT + " from `tabEmployee` where " + " and ".join(where)
        + " order by employee_name,name" + (" for update" if lock else ""), values, as_dict=True,
    )


def _authorized_employees(rows, operation, app_id="iam"):
    result = []
    for row in rows:
        try:
            guards.require_capability(operation, department=row.department, company=row.company, app_id=app_id)
        except frappe.PermissionError:
            continue
        result.append(row)
    return result


def _lock_work_target(subject_type, subject_name, app_id, *, lock=True):
    # get_effective_access is a read endpoint; holding row locks there made the
    # per-app reads queue (0.8s each, 4.2s for the last of seven).
    departments = _readable_app(app_id, lock=lock)
    if subject_type == "Department":
        row = departments.get(subject_name)
        if not row or row.disabled:
            frappe.throw("没有该目标的配置读取权限，或目标尚未确认。", frappe.PermissionError)
        return
    if subject_type != "User":
        frappe.throw("配置目标类型无效。", frappe.ValidationError)
    rows = _authorized_employees(_current_employees(departments, user_id=subject_name, lock=lock), "iam.access.read", app_id)
    if len(rows) != 1:
        frappe.throw("没有该目标的配置读取权限，或员工关联尚未确认。", frappe.PermissionError)
    # A second association outside the managed department must not be selected
    # away and silently treated as a unique employee. No other employee leaves here.
    associations = frappe.db.sql(
        "select name from `tabEmployee` where user_id=%s order by name limit 2 for update",
        (subject_name,), as_dict=True,
    )
    users = frappe.db.sql("select name,enabled from `tabUser` where name=%s for update", (subject_name,), as_dict=True)
    if len(associations) != 1 or not users:
        frappe.throw("员工账号关联尚未确认，请核验后重试。", frappe.PermissionError)


@frappe.whitelist()
def get_capabilities(**kwargs):
    def load():
        _only(kwargs)
        user = policy.get_current_user()
        capabilities = []
        own, _ = policy._rules("User", user)
        # Management never inherits from department defaults. The absence of
        # a registered personal operation can safely narrow candidates; every
        # candidate still receives the existing fresh target authorization.
        candidates = set(policy.MANAGEMENT) if guards.platform_root() else {row["operation_id"] for row in own if row["operation_id"] in policy.MANAGEMENT and policy.registration(row["app_id"], row["operation_id"])}
        # This read runs on every session resume, so the department set is
        # loaded once and each operation stops at its first authorized target.
        departments = guards.site_departments()
        for operation in policy.MANAGEMENT:
            if operation.startswith('iam.roles.') and not policy.enabled_flag('hbos_iam_roles_enabled'):
                continue
            if operation not in candidates:
                continue
            apps = [app["id"] for app in policy.registered_apps() if app["integrated"]] if operation in {"iam.access.read", "iam.access.manage", "iam.departments.manage"} or operation.startswith('iam.roles.') else ["iam"]
            if any(guards.can_manage_any(operation, app_id=app_id, departments=departments) for app_id in apps):
                capabilities.append(operation)
        if policy.evaluate(user, "attendance", "attendance.read", "SELF", "")["allowed"]:
            capabilities.append("attendance.read")
        from hbos_portal.auth.accounts import browser_session_context
        return {"schema_version": 1, "subject_user": user, "session_context": browser_session_context(), "app_roles_enabled": policy.enabled_flag('hbos_iam_roles_enabled'), **policy.revision_digests(user), "capabilities": capabilities}
    return _call(load, read_only=True)


def _work_person(employee, department=None):
    from hbos_portal.iam.organization import technical_ids
    group = 'technical' if employee.name in technical_ids('Employee', frappe.conf) else 'daily'
    users = frappe.db.sql("select name,enabled from `tabUser` where name=%s for update", (employee.user_id,), as_dict=True) if employee.user_id else []
    enabled = bool(users and users[0].enabled)
    return {"verification_group": group, "id": employee.name, "name": employee.employee_name, "employee_number": employee.employee_number or "", "department": employee.department, "department_name": (department.department_name or department.name) if department else "", "company": employee.company, "position": employee.designation or "", "user_id": employee.user_id, "account_status": "active" if enabled else "disabled" if employee.user_id else "unopened", "attendance_status": "confirmed" if employee.user_id and employee.status == "Active" else "pending", "version": str(employee.modified)}


@frappe.whitelist()
def list_app_people(app_id, search="", department="", page=1, page_size=20, view_group="daily", **kwargs):
    def load():
        _only(kwargs, {"app_id", "search", "department", "page", "page_size", "view_group"})
        departments = _readable_app(app_id)
        if department and department not in departments:
            frappe.throw("没有该部门的应用配置读取权限。", frappe.PermissionError)
        try:
            current, size = int(page), int(page_size)
            if not 1 <= current <= 10000 or not 1 <= size <= 50 or len(str(search)) > 100:
                raise ValueError
        except (ValueError, TypeError):
            frappe.throw("分页或搜索参数无效。", frappe.ValidationError)
        rows = _authorized_employees(_current_employees([department] if department else departments, search=str(search)), "iam.access.read", app_id)
        from hbos_portal.iam.organization import filter_rows, group_filter
        rows = filter_rows(rows, "Employee", view_group, conf=frappe.conf)
        grouped = group_filter("Employee", view_group, frappe.conf)[1]
        # Count and pagination share the same current, re-authorized population;
        # a separate snapshot COUNT could expose moved or revoked employees.
        page_rows = rows[(current - 1) * size:current * size]
        return {"items": [_work_person(row, departments[row.department]) for row in page_rows], "total": len(rows), "page": current, "page_size": size, "groups_available": grouped}
    return _call(load, read_only=True)


@frappe.whitelist()
def get_work_subject(employee_id, app_id, **kwargs):
    def load():
        _only(kwargs, {"employee_id", "app_id"})
        departments = _readable_app(app_id)
        rows = _authorized_employees(_current_employees(departments, employee_id=employee_id), "iam.access.read", app_id)
        if len(rows) != 1:
            frappe.throw("没有该目标的配置读取权限。", frappe.PermissionError)
        row = rows[0]
        person = _work_person(row, departments[row.department])
        return {"employee": person, "account": {"status": person["account_status"], "user_id": row.user_id}, "association": {"status": person["attendance_status"]}, "configuration_only": True}
    return _call(load, read_only=True)


@frappe.whitelist()
def get_registered_apps(**kwargs):
    def load():
        _only(kwargs)
        # One organization read and one pruned authorization probe per app.
        # The previous per-app full department scan with row locks made this
        # list take ~5.6s and every management page waited for it.
        departments = guards.site_departments()
        apps = [app for app in policy.registered_apps() if guards.can_manage_any("iam.access.read", app_id=app["id"], departments=departments)]
        if not apps:
            frappe.throw("没有可读取的应用管理范围。", frappe.PermissionError)
        return {"apps": apps}
    return _call(load, read_only=True)


@frappe.whitelist()
def get_effective_access(subject_type, subject_name, app_id, **kwargs):
    def load():
        _only(kwargs, {"subject_type", "subject_name", "app_id"})
        _lock_work_target(subject_type, subject_name, app_id, lock=False)
        result = work_commands.describe(policy.effective_work(subject_type, subject_name, app_id, lock=False))
        rows = work_commands._rules(policy.get_policy(subject_type, subject_name, for_update=False))
        for operation in result["operations"]:
            operation["editable"] = operation["ordinary"] and operation["available"] and not any(work_commands._complex(row) for row in rows if row["app_id"] == app_id and row["operation_id"] == operation["operation_id"])
        if subject_type == "User":
            employee = policy.resolve_employee(subject_name, required=False)
            department_id = policy.value(employee, "department") if employee else None
            if department_id:
                department = frappe.db.get_value("Department", department_id, ["department_name", "company"], as_dict=True)
                default = policy.effective_work("Department", department_id, app_id)
                can_open = False
                try:
                    guards.require_capability("iam.departments.read", department=department_id, company=policy.value(department, "company"))
                    can_open = True
                except frappe.PermissionError:
                    pass
                # The target was already authorized above. Return only its
                # own source, no department population or business records.
                result["department_default"] = {"id": department_id, "name": policy.value(department, "department_name") or department_id, "enabled": any(row["allowed"] for row in default["operations"] if row["ordinary"] and row["available"]), "suspended": default["suspended"], "can_open": can_open}
        return result
    return _call(load, read_only=True)


@frappe.whitelist()
def preview_work(subject_type, subject_name, app_id, changes=None, kind="save", expected_version=None, context_revision=None, **kwargs):
    def load():
        _only(kwargs, {"subject_type", "subject_name", "app_id", "changes", "kind", "expected_version", "context_revision"})
        result = work_commands.preview_work(subject_type, subject_name, app_id, changes, kind)
        if expected_version is not None and int(expected_version) != result["before"]["version"]:
            work_commands._conflict("安排已变化，请刷新结果并保留草稿。")
        if context_revision is not None and context_revision != result["context_revision"]:
            work_commands._conflict("权限来源或员工状态已变化，请重新核对预览。")
        return result
    return _call(load)


def _commit(kind, subject_type, subject_name, app_id, changes=None, expected_version=None, context_revision=None, request_id=None, **kwargs):
    def save():
        _only(kwargs, {"subject_type", "subject_name", "app_id", "changes", "expected_version", "context_revision", "request_id"})
        return work_commands.commit_work(subject_type, subject_name, app_id, changes, expected_version, context_revision, request_id, kind)
    return _call(save)


@frappe.whitelist(methods=["POST"])
def save_work(subject_type, subject_name, app_id, changes=None, expected_version=None, context_revision=None, request_id=None, **kwargs):
    return _commit("save", subject_type, subject_name, app_id, changes, expected_version, context_revision, request_id, **kwargs)


@frappe.whitelist(methods=["POST"])
def preview_app_settings(subject_type, subject_name, app_id, settings, expected_version, context_revision, **kwargs):
    def load():
        guards.require_post()
        _only(kwargs, {"subject_type", "subject_name", "app_id", "settings", "expected_version", "context_revision"})
        result = work_commands.preview_work(subject_type, subject_name, app_id, kind="configure", settings=settings)
        if int(expected_version) != result["before"]["version"] or context_revision != result["context_revision"]:
            work_commands._conflict("权限或来源已变化，请重新核对。")
        return result
    return _call(load)


@frappe.whitelist(methods=["POST"])
def save_app_settings(subject_type, subject_name, app_id, settings, expected_version, context_revision, request_id, **kwargs):
    def save():
        _only(kwargs, {"subject_type", "subject_name", "app_id", "settings", "expected_version", "context_revision", "request_id"})
        return work_commands.commit_work(subject_type, subject_name, app_id, expected_version=expected_version, context_revision=context_revision, request_id=request_id, kind="configure", settings=settings)
    return _call(save)


@frappe.whitelist(methods=["POST"])
def restore_department_work(subject_type, subject_name, app_id, expected_version=None, context_revision=None, request_id=None, **kwargs):
    return _commit("restore", subject_type, subject_name, app_id, None, expected_version, context_revision, request_id, **kwargs)


@frappe.whitelist(methods=["POST"])
def suspend_app(subject_type, subject_name, app_id, expected_version=None, context_revision=None, request_id=None, **kwargs):
    return _commit("suspend", subject_type, subject_name, app_id, None, expected_version, context_revision, request_id, **kwargs)


@frappe.whitelist(methods=["POST"])
def reenable_app(subject_type, subject_name, app_id, expected_version=None, context_revision=None, request_id=None, **kwargs):
    return _commit("reenable", subject_type, subject_name, app_id, None, expected_version, context_revision, request_id, **kwargs)


@frappe.whitelist(methods=["POST"])
def update_personal_exception(subject_name, app_id, changes=None, expected_version=None, context_revision=None, request_id=None, **kwargs):
    return _commit("save", "User", subject_name, app_id, changes, expected_version, context_revision, request_id, **kwargs)


@frappe.whitelist()
def preview_department_default(subject_name, app_id, changes=None, expected_version=None, context_revision=None, **kwargs):
    return preview_work("Department", subject_name, app_id, changes, "save", expected_version, context_revision, **kwargs)


@frappe.whitelist(methods=["POST"])
def update_department_default(subject_name, app_id, changes=None, expected_version=None, context_revision=None, request_id=None, **kwargs):
    return _commit("save", "Department", subject_name, app_id, changes, expected_version, context_revision, request_id, **kwargs)
