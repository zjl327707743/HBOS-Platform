import frappe
from datetime import datetime, timedelta

READ_ROLES = {"HR User", "HR Manager", "System Manager"}
WRITE_ROLES = {"HR Manager", "System Manager"}


def _require_roles(allowed):
    if not (set(frappe.get_roles()) & set(allowed)):
        frappe.throw("你无权访问考勤班次管理。", frappe.PermissionError)


def _require_hr_read():
    _require_roles(READ_ROLES)


def _require_hr_write():
    _require_roles(WRITE_ROLES)



def _fmt_time(t):
    """timedelta/时间对象 → HH:MM 字符串(前端 Time 输入框需要干净格式)。"""
    if t is None:
        return ""
    if isinstance(t, timedelta):
        total = int(t.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h:02d}:{m:02d}"
    s = str(t)
    parts = s.split(":")
    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}" if len(parts) >= 2 else s


def _fmt_rule(r):
    """规则记录的时间字段转为 HH:MM 字符串。"""
    for f in ("start_time", "end_time", "late_after"):
        if f in r:
            r[f] = _fmt_time(r.get(f))
    return r


def _rule_sort_key(rule):
    return (str(rule.effective_from or ""), str(rule.name or ""))


def _effective_family_version(versions, day):
    """Pick the last version effective on day; a latest 停用 marker disables the family."""
    candidates = [
        r for r in versions
        if r.status != "草稿" and str(r.effective_from or "") <= str(day)
    ]
    if not candidates:
        return None
    chosen = max(candidates, key=_rule_sort_key)
    return None if chosen.status == "停用" else chosen


def _group_rule_versions(rules):
    families = {}
    for rule in rules:
        code = rule.rule_code or rule.rule_name or rule.name
        families.setdefault(code, []).append(rule)
    return families


def _bindable_family_rows(rules, day):
    """One row per stable family for employee binding."""
    rows = []
    for code, versions in _group_rule_versions(rules).items():
        chosen = _effective_family_version(versions, day)
        if chosen is None:
            future_active = [
                r for r in versions
                if r.status == "生效" and str(r.effective_from or "") > str(day)
            ]
            if future_active:
                chosen = min(future_active, key=_rule_sort_key)
        if chosen is None:
            continue
        row = frappe._dict(chosen)
        row["rule_code"] = code
        rows.append(_fmt_rule(row))
    return sorted(rows, key=lambda r: (str(r.department or ""), str(r.rule_name or "")))


@frappe.whitelist()
def get_shift_overview():
    """班次管理总览：版本记录 + 当前有效版本 + 可绑定的稳定规则族。"""
    _require_hr_read()
    from collections import defaultdict

    rules = [_fmt_rule(r) for r in frappe.db.get_all(
        "HBOS Shift Rule",
        fields=["name", "rule_code", "rule_name", "department", "shift_type",
                "start_time", "end_time", "late_after", "min_hours",
                "effective_from", "supersedes", "status"],
        order_by="department, rule_code, effective_from, creation",
    )]

    dept_counts = frappe.db.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["department"],
    )
    dept_emp = defaultdict(int)
    for d in dept_counts:
        dept_emp[d.department] += 1

    now = frappe.utils.nowtime()
    now_secs = _to_secs(now)
    now_display = now.split(".")[0][:5]
    today = frappe.utils.today()

    active_shifts = []
    for _, versions in _group_rule_versions(rules).items():
        r = _effective_family_version(versions, today)
        if not r:
            continue
        st = _to_secs(str(r.start_time))
        et = _to_secs(str(r.end_time))
        if st == 0 and et == 0:
            continue
        running = (st <= now_secs <= et) if et > st else (now_secs >= st or now_secs <= et)
        if running:
            active_shifts.append(_fmt_rule(frappe._dict(r)))

    return {
        "departments": sorted(dept_emp.keys()),
        "dept_employee_count": dict(dept_emp),
        "rules": rules,
        "bindable_rules": _bindable_family_rows(rules, today),
        "active_shifts": active_shifts,
        "now": now_display,
    }


@frappe.whitelist()
def update_shift_rule(rule_name, updates=None, field=None, value=None):
    """Create exactly one new version for a stable rule family.

    Legacy one-field calls are rejected deliberately: the old UI emitted three HTTP
    calls and therefore created three versions for one Save action.
    """
    _require_hr_write()
    import json as _json

    if field is not None or value is not None:
        frappe.throw("旧版逐字段保存接口已停用，请刷新页面后一次提交完整班次变更。")

    try:
        changes = _json.loads(updates) if isinstance(updates, str) else dict(updates or {})
    except Exception:
        frappe.throw("班次更新参数格式错误。")

    allowed = {"start_time", "end_time", "late_after", "min_hours"}
    unknown = set(changes) - allowed
    if unknown:
        frappe.throw("不允许修改字段: {}".format(", ".join(sorted(unknown))))
    if not changes:
        frappe.throw("没有需要保存的班次变更。")

    old = frappe.get_doc("HBOS Shift Rule", rule_name)
    if old.status == "草稿":
        frappe.throw("草稿规则请先完成配置后再生效，不通过升版接口修改。")

    latest = frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"rule_code": old.rule_code},
        fields=["name", "effective_from"],
        order_by="effective_from desc, creation desc",
        limit_page_length=1,
    )
    if latest and latest[0].name != old.name:
        frappe.throw("只能从规则族的最新版本创建新版本，请刷新页面。")

    tomorrow = (
        frappe.utils.today_datetime() + timedelta(days=1)
    ).strftime("%Y-%m-%d") if hasattr(frappe.utils, "today_datetime") else (
        datetime.now() + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    new_doc = frappe.copy_doc(old)
    new_doc.rule_code = old.rule_code
    new_doc.supersedes = old.name
    new_doc.status = "生效"
    new_doc.effective_from = tomorrow
    for key, val in changes.items():
        new_doc.set(key, val)
    new_doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "old": old.name,
        "new": new_doc.name,
        "rule_code": new_doc.rule_code,
        "effective_from": tomorrow,
        "updates": changes,
    }


@frappe.whitelist()
def get_department_shifts(department):
    """All versions for one department, with latest-version marker per stable family."""
    _require_hr_read()
    rules = frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"department": department},
        fields=["name", "rule_code", "rule_name", "shift_type", "start_time", "end_time",
                "late_after", "min_hours", "effective_from", "supersedes", "status"],
        order_by="rule_code, effective_from desc, creation desc",
    )
    latest = {}
    for row in rules:
        code = row.rule_code or row.rule_name or row.name
        latest.setdefault(code, row.name)
    for row in rules:
        code = row.rule_code or row.rule_name or row.name
        row["is_latest"] = 1 if latest.get(code) == row.name else 0
    return [_fmt_rule(r) for r in rules]


@frappe.whitelist()
def get_department_employees(department):
    """部门人员列表(含固定班次绑定 + 系统名单班次)。"""
    _require_hr_read()
    from hb_attendance_app.hbos_attendance.api import (
        ADMIN_NUMS, EXEMPT_NUMS, WUJUN_NUMS, SAFETY_NUMS, FOOD_NUMS,
    )
    from hb_attendance_app.hbos_attendance.pairing import SPECIAL_SHIFT_NUMS, FOUR_SHIFT_NUMS

    # 系统名单 → 班次体系名称(优先级: 手动绑定 > 系统名单)
    def system_shift(num):
        if num in EXEMPT_NUMS:
            return "豁免(不计异常)"
        if num in SPECIAL_SHIFT_NUMS:
            return "无菌倒班体系"
        if num in FOUR_SHIFT_NUMS:
            return "四班次倒班"
        if num in ADMIN_NUMS:
            return "行政班"
        if num in WUJUN_NUMS:
            return "无菌倒班(旧)"
        if num in SAFETY_NUMS:
            return "安全倒班"
        if num in FOOD_NUMS:
            return "食堂(不判异常)"
        return "通用倒班(按时间判定)"

    rows = frappe.db.sql("""
        SELECT e.name, e.employee_name, e.employee_number,
               e.hbos_fixed_shift, sr.rule_name as fixed_shift_name,
               sr.shift_type as fixed_shift_type
        FROM tabEmployee e
        LEFT JOIN `tabHBOS Shift Rule` sr ON sr.name = e.hbos_fixed_shift
        WHERE e.department = %s AND e.status = 'Active'
        ORDER BY e.employee_number
    """, (department,), as_dict=True)
    for r in rows:
        r["system_shift"] = system_shift(r.employee_number or "")
    return rows


@frappe.whitelist()
def create_shift_rule(rule_name, department, shift_type,
                      start_time, end_time, late_after=None, min_hours=8,
                      effective_from=None):
    """Create the first version of a new stable shift-rule family."""
    _require_hr_write()
    from hb_attendance_app.hbos_attendance.doctype.hbos_shift_rule.hbos_shift_rule import make_rule_code

    if not effective_from:
        effective_from = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    def _norm_time(t):
        if not t:
            return None
        parts = str(t).split(":")
        while len(parts) < 3:
            parts.append("00")
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"

    def _add_one_minute(t):
        parts = str(t).split(":")
        h, m = int(parts[0]), int(parts[1])
        m += 1
        if m >= 60:
            m = 0
            h += 1
        if h >= 24:
            h = 0
        return f"{h:02d}:{m:02d}:00"

    norm_start = _norm_time(start_time)
    code = make_rule_code(department, rule_name, shift_type)
    if frappe.db.exists("HBOS Shift Rule", {"rule_code": code}):
        frappe.throw("同名班次规则族已存在；请使用“保存新版本”，不要重复新建。")

    doc = frappe.get_doc({
        "doctype": "HBOS Shift Rule",
        "rule_code": code,
        "rule_name": rule_name,
        "department": department,
        "shift_type": shift_type,
        "start_time": norm_start,
        "end_time": _norm_time(end_time),
        "late_after": _norm_time(late_after) or _add_one_minute(norm_start),
        "min_hours": float(min_hours or 8),
        "effective_from": effective_from,
        "status": "生效",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {
        "name": doc.name,
        "rule_code": doc.rule_code,
        "rule_name": doc.rule_name,
        "effective_from": effective_from,
    }


@frappe.whitelist()
def bind_employee_shifts(employee, shift_rules):
    """Replace employee bindings using stable rule codes, not version docnames."""
    _require_hr_write()
    import json as _json
    try:
        codes = [str(x).strip() for x in _json.loads(shift_rules or "[]") if str(x).strip()]
    except Exception:
        frappe.throw("班次列表格式错误")

    # Preserve order while removing duplicates.
    codes = list(dict.fromkeys(codes))
    representative = {}
    for code in codes:
        versions = frappe.db.get_all(
            "HBOS Shift Rule",
            filters={"rule_code": code},
            fields=["name", "status", "effective_from"],
            order_by="effective_from desc, creation desc",
        )
        if not versions:
            frappe.throw(f"规则族不存在：{code}")
        usable = [r for r in versions if r.status != "草稿"]
        if not usable:
            frappe.throw(f"规则族 {code} 只有草稿版本，不能绑定员工。")
        representative[code] = usable[0].name

    frappe.db.delete("HBOS Employee Shift", {"employee": employee})
    for index, code in enumerate(codes):
        frappe.get_doc({
            "doctype": "HBOS Employee Shift",
            "employee": employee,
            "rule_code": code,
            "shift_rule": representative[code],
            "is_primary": 1 if index == 0 else 0,
        }).insert(ignore_permissions=True)

    # Maintain legacy single-binding fields only as compatibility mirrors.
    primary = codes[0] if codes else None
    frappe.db.set_value(
        "Employee",
        employee,
        {
            "hbos_fixed_shift_code": primary,
            "hbos_fixed_shift": representative.get(primary) if primary else None,
        },
        update_modified=False,
    )
    frappe.db.commit()
    return {"employee": employee, "shift_rules": codes}


@frappe.whitelist()
def get_employee_bound_shifts(employee):
    """Return stable rule codes bound to the employee."""
    _require_hr_read()
    rows = frappe.db.get_all(
        "HBOS Employee Shift",
        filters={"employee": employee},
        fields=["rule_code", "shift_rule", "is_primary"],
        order_by="is_primary desc, creation asc",
    )
    out = []
    for row in rows:
        code = row.rule_code
        if not code and row.shift_rule:
            code = frappe.db.get_value("HBOS Shift Rule", row.shift_rule, "rule_code")
        if code and code not in out:
            out.append(code)
    return out


@frappe.whitelist()
def set_rule_status(rule_name, status):
    """Versioned status change. Historical versions are never mutated in place."""
    _require_hr_write()
    if status not in {"生效", "停用"}:
        frappe.throw("状态变更只支持「生效 / 停用」；草稿不允许覆盖已生效历史。")

    old = frappe.get_doc("HBOS Shift Rule", rule_name)
    latest = frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"rule_code": old.rule_code},
        fields=["name"],
        order_by="effective_from desc, creation desc",
        limit_page_length=1,
    )
    if latest and latest[0].name != old.name:
        frappe.throw("只能调整规则族最新版本的状态，请刷新页面。")
    if old.status == status:
        return {"rule": old.name, "status": old.status, "versioned": False}

    effective_from = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    new_doc = frappe.copy_doc(old)
    new_doc.rule_code = old.rule_code
    new_doc.supersedes = old.name
    new_doc.status = status
    new_doc.effective_from = effective_from
    new_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {
        "rule": new_doc.name,
        "rule_code": new_doc.rule_code,
        "status": status,
        "effective_from": effective_from,
        "versioned": True,
    }


@frappe.whitelist()
def delete_shift_rule(rule_name):
    """Only an unreferenced draft version may be physically deleted."""
    _require_hr_write()
    if not frappe.db.exists("HBOS Shift Rule", rule_name):
        frappe.throw("规则不存在")
    doc = frappe.get_doc("HBOS Shift Rule", rule_name)
    if doc.status != "草稿":
        frappe.throw("已进入历史链的规则版本不可物理删除；请创建「停用」版本。")
    if frappe.db.exists("HBOS Shift Rule", {"supersedes": doc.name}):
        frappe.throw("该规则版本已有后继版本，不可删除。")
    if frappe.db.exists("HBOS Employee Shift", {"rule_code": doc.rule_code}):
        frappe.throw("该规则族已有员工绑定，不可删除。")
    frappe.delete_doc("HBOS Shift Rule", doc.name, ignore_permissions=True)
    frappe.db.commit()
    return {"deleted": doc.name}


@frappe.whitelist()
def import_schedule_file(file_path=None, file_content=None, file_url=None):
    """Import schedules while respecting source ownership.

    IMPORT may replace earlier IMPORT/ROTATION rows in the requested window.
    LEGACY/MANUAL/SWAP rows are protected and never deleted by this import.
    """
    _require_hr_write()
    import base64
    import tempfile
    import os

    if file_path:
        frappe.throw("不允许通过 API 读取服务器任意文件路径；请使用已上传的 File。", frappe.PermissionError)

    from hb_attendance_app.hbos_attendance.schedule_import import (
        parse_xlsx_matrix, parse_xlsx_vertical,
    )

    tmp_path = None
    source_ref = "inline-upload"
    if file_url:
        fdoc = frappe.get_doc("File", {"file_url": file_url})
        if hasattr(fdoc, "check_permission"):
            fdoc.check_permission("read")
        raw = fdoc.get_content(encodings=())
        source_ref = fdoc.name
        if isinstance(raw, str):
            raw = raw.encode("latin-1")
        fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        file_path = tmp_path
    elif file_content:
        try:
            raw = base64.b64decode(file_content, validate=True)
        except Exception:
            frappe.throw("排班表 base64 内容无效。")
        fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        file_path = tmp_path

    if not file_path or not os.path.exists(file_path):
        frappe.throw("排班表文件不存在")

    try:
        rows = []
        try:
            rows, _ = parse_xlsx_matrix(file_path)
        except Exception:
            rows = []
        if not rows:
            try:
                rows, _ = parse_xlsx_vertical(file_path)
            except Exception:
                rows = []
        if not rows:
            frappe.throw("未能解析排班表（支持的格式：厂外QC矩阵式 / 四车间纵向式）")

        emp_by_num = {
            e.employee_number: e.name
            for e in frappe.db.get_all(
                "Employee",
                fields=["name", "employee_number"],
                filters={"employee_number": ["is", "set"]},
            )
        }
        emp_by_name = {
            e.employee_name: e.name
            for e in frappe.db.get_all("Employee", fields=["name", "employee_name"])
        }

        resolved = []
        skipped = 0
        input_keys = set()
        for row in rows:
            emp = None
            if row["employee_number"] and row["employee_number"] in emp_by_num:
                emp = emp_by_num[row["employee_number"]]
            elif row["employee_name"] and row["employee_name"] in emp_by_name:
                emp = emp_by_name[row["employee_name"]]
            if not emp:
                skipped += 1
                continue
            key = (emp, str(row["date"]))
            if key in input_keys:
                frappe.throw(
                    "导入文件中员工 {} 在 {} 出现重复排班，请先消除歧义。".format(*key)
                )
            input_keys.add(key)
            resolved.append((emp, row))

        dates = sorted({str(row["date"]) for _, row in resolved})
        matched_emps = sorted({emp for emp, _ in resolved})

        if dates and matched_emps:
            for emp in matched_emps:
                frappe.db.delete(
                    "HBOS Employee Schedule",
                    {
                        "employee": emp,
                        "schedule_date": ["between", [dates[0], dates[-1]]],
                        "source_type": ["in", ["IMPORT", "ROTATION"]],
                    },
                )

        created = 0
        protected = 0
        for emp, row in resolved:
            ds = str(row["date"])
            existing = frappe.db.get_value(
                "HBOS Employee Schedule",
                {"employee": emp, "schedule_date": ds},
                ["name", "source_type"],
                as_dict=True,
            )
            if existing:
                protected += 1
                continue
            frappe.get_doc({
                "doctype": "HBOS Employee Schedule",
                "employee": emp,
                "schedule_date": ds,
                "shift_type": row["shift_type"] or "",
                "leave_type": row["leave_type"] or "",
                "source_type": "IMPORT",
                "source_ref": source_ref,
            }).insert(ignore_permissions=True)
            created += 1

        frappe.db.commit()
        return {
            "created": created,
            "skipped": skipped,
            "protected": protected,
            "total": len(rows),
            "date_range": [dates[0], dates[-1]] if dates else [],
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@frappe.whitelist()
def get_conflicts():
    """Return identity/version collisions and bindings that cannot resolve a rule family."""
    _require_hr_read()

    overlaps = frappe.db.sql(
        """SELECT rule_code, effective_from, COUNT(*) AS c
           FROM `tabHBOS Shift Rule`
           WHERE IFNULL(rule_code, '') != ''
           GROUP BY rule_code, effective_from
           HAVING COUNT(*) > 1""",
        as_dict=True,
    )

    stale_bindings = []
    for binding in frappe.db.get_all(
        "HBOS Employee Shift",
        fields=["name", "employee", "employee_name", "rule_code", "shift_rule"],
    ):
        code = binding.rule_code
        if not code and binding.shift_rule:
            code = frappe.db.get_value("HBOS Shift Rule", binding.shift_rule, "rule_code")
        if not code or not frappe.db.exists("HBOS Shift Rule", {"rule_code": code}):
            stale_bindings.append({
                "binding": binding.name,
                "employee": binding.employee,
                "employee_name": binding.employee_name,
                "rule_code": code or "",
                "shift_rule": binding.shift_rule or "",
            })

    return {"overlaps": overlaps, "stale_bindings": stale_bindings}


def _to_secs(t_str):
    """时间字符串 → 秒。兼容 HH:MM 和 HH:MM:SS 两种格式。"""
    try:
        parts = str(t_str).split(":")
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        return hh * 3600 + mm * 60
    except Exception:
        return 0


@frappe.whitelist()
def get_rules_board():
    """规则看板数据：规则记录（含绑定人数）+ 内置班次 + 名单 + 配对参数 + 判定优先级。

    只读端点，不触发考勤生成、不改数据库。各数据源独立 try/except，
    任一失败只空该分组并记录到 errors，不整体抛错。
    """
    _require_hr_read()
    from hb_attendance_app.hbos_attendance import rules_board as rb

    out = {
        "rules": [],
        "builtin_shifts": [],
        "lists": [],
        "pairing_params": [],
        "priority_chain": [],
    }
    errors = {}

    # 1. 规则记录（含实时绑定人数：HBOS Employee Shift 多绑定 + Employee.hbos_fixed_shift 单绑定）
    try:
        rules = [_fmt_rule(r) for r in frappe.db.get_all(
            "HBOS Shift Rule",
            fields=["name", "rule_name", "department", "shift_type",
                    "start_time", "end_time", "late_after", "min_hours",
                    "effective_from", "status"],
            order_by="department, start_time",
        )]
        count_map = {}
        for r in frappe.db.sql(
            "SELECT shift_rule, COUNT(*) c FROM `tabHBOS Employee Shift` GROUP BY shift_rule",
            as_dict=True,
        ):
            count_map[r.shift_rule] = r.c
        for e in frappe.db.get_all(
            "Employee", fields=["hbos_fixed_shift"],
            filters={"hbos_fixed_shift": ["is", "set"]},
        ):
            count_map[e.hbos_fixed_shift] = count_map.get(e.hbos_fixed_shift, 0) + 1
        for r in rules:
            r["assigned_count"] = count_map.get(r["name"], 0)
        out["rules"] = rules
    except Exception as e:
        errors["rules"] = str(e)

    # 2. 名单规则: 补充员工姓名映射(工号→姓名, 未建档/离职工号用工号兜底)
    try:
        lists = rb.list_groups()
        all_nums = set()
        for g in lists:
            all_nums.update(g["nums"])
        num_to_name = {}
        if all_nums:
            for e in frappe.db.get_all(
                "Employee", fields=["employee_number", "employee_name"],
                filters={"employee_number": ["in", list(all_nums)]},
            ):
                num_to_name[e.employee_number] = e.employee_name or ""
        for g in lists:
            g["names"] = [num_to_name.get(n, n) for n in g["nums"]]
        out["lists"] = lists
    except Exception as e:
        errors["lists"] = str(e)

    # 3-5. 其余静态数据（纯函数，见 rules_board.py）
    for key, builder in (
        ("builtin_shifts", rb.builtin_shifts),
        ("pairing_params", rb.pairing_params),
        ("priority_chain", rb.priority_chain),
    ):
        try:
            out[key] = builder()
        except Exception as e:
            errors[key] = str(e)

    if errors:
        out["errors"] = errors
    return out
