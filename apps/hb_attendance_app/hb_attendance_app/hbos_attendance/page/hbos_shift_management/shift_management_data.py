import frappe
from datetime import datetime, timedelta


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


@frappe.whitelist()
def get_shift_overview():
    """班次管理页数据: 部门→班次→人员三层 + 进行中班次。

    返回:
    {
      "departments": [{name, employee_count, shifts: [...]}],
      "active_shifts": [{rule, department, ...}],
      "all_rules": [...]
    }
    """
    from collections import defaultdict

    # 全部生效规则(含未到生效日期的, 前端标记"待生效")
    rules = [_fmt_rule(r) for r in frappe.db.get_all(
        "HBOS Shift Rule",
        fields=["name", "rule_name", "department", "shift_type",
                "start_time", "end_time", "late_after", "min_hours",
                "effective_from", "status"],
        order_by="department, start_time",
    )]

    # 部门员工数
    dept_counts = frappe.db.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["department"],
    )
    dept_emp = defaultdict(int)
    for d in dept_counts:
        dept_emp[d.department] += 1

    # 进行中的班次: 当前时间落在 start_time~end_time 的规则
    now = frappe.utils.nowtime()
    now_secs = _to_secs(now)
    # 显示用: HH:MM 格式(截掉秒和微秒)
    now_display = now.split(".")[0][:5]
    active_shifts = []
    for r in rules:
        if r.status != "生效" or str(r.effective_from) > frappe.utils.today():
            continue
        st = _to_secs(str(r.start_time))
        et = _to_secs(str(r.end_time))
        if st == 0 and et == 0:
            continue
        if et > st:  # 当日班次
            if st <= now_secs <= et:
                active_shifts.append(r)
        else:  # 跨零点班次(如夜班 0-8)
            if now_secs >= st or now_secs <= et:
                active_shifts.append(r)

    return {
        "departments": sorted(dept_emp.keys()),
        "dept_employee_count": dict(dept_emp),
        "rules": rules,
        "active_shifts": active_shifts,
        "now": now_display,
    }


@frappe.whitelist()
def update_shift_rule(rule_name, field, value):
    """在线修改班次规则(次日生效)。

    field: start_time / end_time / late_after / min_hours
    生效方式: 次日生效(Owner 2026-08-20 确认)。修改后:
      - 原规则 status 改为 停用
      - 新规则克隆原规则, 生效日期=明天, status=生效
    返回新规则信息。
    """
    from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS

    ALLOWED = {"start_time", "end_time", "late_after", "min_hours"}
    if field not in ALLOWED:
        frappe.throw(f"不允许修改字段: {field}")

    old = frappe.get_doc("HBOS Shift Rule", rule_name)
    if old.status != "生效":
        frappe.throw("只能修改生效中的规则")

    tomorrow = (frappe.utils.today_datetime() + timedelta(days=1)).strftime("%Y-%m-%d") if hasattr(frappe.utils, "today_datetime") else (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # 克隆新规则(次日生效)
    new_doc = frappe.copy_doc(old)
    new_doc.rule_name = old.rule_name  # 保留同名
    new_doc.status = "生效"
    new_doc.effective_from = tomorrow
    new_doc.set(field, value)
    new_doc.insert(ignore_permissions=True)

    # 原规则停用
    frappe.db.set_value("HBOS Shift Rule", old.name, "status", "停用", update_modified=False)
    frappe.db.commit()

    return {
        "old": old.name,
        "new": new_doc.name,
        "effective_from": tomorrow,
        "field": field,
        "value": str(value),
    }


@frappe.whitelist()
def get_department_shifts(department):
    """某部门的全部班次(生效+停用, 按生效日期倒序)。"""
    rules = frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"department": department},
        fields=["name", "rule_name", "shift_type", "start_time", "end_time",
                "late_after", "min_hours", "effective_from", "status"],
        order_by="effective_from desc",
    )
    return [_fmt_rule(r) for r in rules]


@frappe.whitelist()
def get_department_employees(department):
    """部门人员列表(含固定班次绑定 + 系统名单班次)。"""
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
    """新建班次规则(状态=生效)。effective_from 缺省时为次日。"""
    if not effective_from:
        effective_from = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    def _norm_time(t):
        """规范化时间格式为 HH:MM:SS(前端可能传 HH:MM 或错误拼接成 HH:MM:SS:SS)。"""
        if not t:
            return None
        parts = str(t).split(":")
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"

    def _add_one_minute(t):
        """时间 +1 分钟(迟到起算默认=上班时间+1分钟)。"""
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
    doc = frappe.get_doc({
        "doctype": "HBOS Shift Rule",
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
    return {"name": doc.name, "rule_name": doc.rule_name, "effective_from": effective_from}


@frappe.whitelist()
def bind_employee_shifts(employee, shift_rules):
    """多班次绑定: 替换员工的全部班次绑定。

    shift_rules: JSON 数组字符串, 如 '["HBOS-SHIFT-0001","HBOS-SHIFT-0002"]'
    """
    import json as _json
    try:
        rules = _json.loads(shift_rules or "[]")
    except Exception:
        frappe.throw("班次列表格式错误")
    # 清空旧绑定
    frappe.db.delete("HBOS Employee Shift", {"employee": employee})
    for r in rules:
        frappe.get_doc({
            "doctype": "HBOS Employee Shift",
            "employee": employee,
            "shift_rule": r,
        }).insert(ignore_permissions=True)
    frappe.db.commit()
    return {"employee": employee, "shift_rules": rules}


@frappe.whitelist()
def get_employee_bound_shifts(employee):
    """员工的全部班次绑定(规则名列表)。"""
    return [r.shift_rule for r in frappe.db.get_all(
        "HBOS Employee Shift",
        filters={"employee": employee},
        fields=["shift_rule"],
        order_by="shift_rule")]


@frappe.whitelist()
def set_rule_status(rule_name, status):
    """调整规则状态: 生效/停用/草稿。"""
    allowed = {"生效", "停用", "草稿"}
    if status not in allowed:
        frappe.throw(f"不允许的状态: {status}")
    if not frappe.db.exists("HBOS Shift Rule", rule_name):
        frappe.throw("规则不存在")
    frappe.db.set_value("HBOS Shift Rule", rule_name, "status", status, update_modified=False)
    frappe.db.commit()
    return {"rule": rule_name, "status": status}


@frappe.whitelist()
def delete_shift_rule(rule_name):
    """删除班次规则。已绑定员工的规则先解绑。"""
    if not frappe.db.exists("HBOS Shift Rule", rule_name):
        frappe.throw("规则不存在")
    # 解绑所有绑定此规则的员工
    bound = frappe.db.count("HBOS Employee Shift", {"shift_rule": rule_name})
    frappe.db.delete("HBOS Employee Shift", {"shift_rule": rule_name})
    # 清除单字段绑定
    for e in frappe.db.get_all("Employee", filters={"hbos_fixed_shift": rule_name}, pluck="name"):
        frappe.db.set_value("Employee", e, "hbos_fixed_shift", None, update_modified=False)
    frappe.db.delete("HBOS Shift Rule", rule_name)
    frappe.db.commit()
    return {"deleted": rule_name, "unbound": bound}


@frappe.whitelist()
def import_schedule_file(file_path=None, file_content=None, file_url=None):
    """导入排班表(支持厂外QC矩阵式与四车间纵向式)。覆盖式重导。

    参数三选一:
      file_url: 前端 Attach 字段上传的文件 URL（推荐, 从 File 记录读原始字节）
      file_content: 前端上传的 base64 内容
      file_path: 服务器上的文件路径
    返回导入统计。
    """
    import base64
    import tempfile
    import os
    from hb_attendance_app.hbos_attendance.schedule_import import (
        parse_xlsx_matrix, parse_xlsx_vertical,
    )

    # 临时诊断日志: 定位前端传参问题, 定位后移除
    frappe.log_error(
        f"import_schedule_file 收到参数: file_url={file_url!r}, file_content={bool(file_content)}, file_path={file_path!r}",
        "排班表导入诊断",
    )

    tmp_path = None
    if file_url:
        # Attach 上传的文件: 从 File 记录读原始字节(不走 base64, 避免二进制被编码破坏)
        fdoc = frappe.get_doc("File", {"file_url": file_url})
        raw = fdoc.get_content(encodings=())
        if isinstance(raw, str):
            raw = raw.encode("latin-1")
        fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
        file_path = tmp_path
    elif file_content:
        raw = base64.b64decode(file_content)
        fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
        file_path = tmp_path
    if not file_path or not os.path.exists(file_path):
        frappe.throw("排班表文件不存在")

    # 尝试两种格式
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

    # 员工匹配
    emp_by_num = {e.employee_number: e.name for e in frappe.db.get_all(
        "Employee", fields=["name", "employee_number"],
        filters={"employee_number": ["is", "set"]})}
    emp_by_name = {e.employee_name: e.name for e in frappe.db.get_all(
        "Employee", fields=["name", "employee_name"])}

    created = 0
    skipped = 0
    # 覆盖式重导: 按「排班表涉及的部门」清理旧记录(不同部门的排班互不影响)
    depts_in_file = sorted({r['department'] for r in rows if r['department']})
    matched_emps = set()
    for r in rows:
        emp = None
        if r['employee_number'] and r['employee_number'] in emp_by_num:
            emp = emp_by_num[r['employee_number']]
        elif r['employee_name'] and r['employee_name'] in emp_by_name:
            emp = emp_by_name[r['employee_name']]
        if emp:
            matched_emps.add(emp)
    dates = sorted({r['date'] for r in rows})
    if dates and matched_emps:
        # 按员工+日期范围清理(只清本次文件覆盖到的员工)
        emp_list = "','".join(matched_emps)
        frappe.db.sql(
            f"DELETE FROM `tabHBOS Employee Schedule` WHERE employee IN ('{emp_list}') AND schedule_date BETWEEN %s AND %s",
            (dates[0], dates[-1]))
    for r in rows:
        emp = None
        if r['employee_number'] and r['employee_number'] in emp_by_num:
            emp = emp_by_num[r['employee_number']]
        elif r['employee_name'] and r['employee_name'] in emp_by_name:
            emp = emp_by_name[r['employee_name']]
        if not emp:
            skipped += 1
            continue
        doc = frappe.get_doc({
            "doctype": "HBOS Employee Schedule",
            "employee": emp,
            "schedule_date": r['date'],
            "shift_type": r['shift_type'] or '',
            "leave_type": r['leave_type'] or '',
        })
        doc.insert(ignore_permissions=True)
        created += 1
    frappe.db.commit()
    if tmp_path:
        os.unlink(tmp_path)
    return {"created": created, "skipped": skipped, "total": len(rows),
            "date_range": [dates[0], dates[-1]] if dates else []}


@frappe.whitelist()
def get_conflicts():
    """班次冲突检测:
    1. 同部门同班次类型存在多条生效规则(版本重叠)
    2. 员工绑定的固定班次指向已停用规则
    返回 {overlaps: [...], stale_bindings: [...]}
    """
    overlaps = []
    rules = frappe.db.get_all(
        "HBOS Shift Rule",
        filters={"status": "生效"},
        fields=["name", "rule_name", "department", "shift_type", "start_time", "effective_from"],
        order_by="department, shift_type, effective_from",
    )
    seen = {}
    for r in rules:
        key = (r.department, r.shift_type)
        if key in seen:
            overlaps.append({
                "department": r.department,
                "shift_type": r.shift_type,
                "rules": [seen[key], r],
            })
        else:
            seen[key] = r

    stale_bindings = frappe.db.sql("""
        SELECT e.employee_name, e.employee_number, e.name employee,
               e.hbos_fixed_shift, sr.status, sr.rule_name
        FROM tabEmployee e
        LEFT JOIN `tabHBOS Shift Rule` sr ON sr.name = e.hbos_fixed_shift
        WHERE e.hbos_fixed_shift IS NOT NULL AND e.hbos_fixed_shift != ''
          AND (sr.name IS NULL OR sr.status != '生效')
    """, as_dict=True)

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
