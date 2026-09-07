import calendar

import frappe
from collections import defaultdict
from datetime import date, timedelta


SHIFT_NAMES = {
    "早班": "早班",
    "中班": "中班",
    "晚班": "晚班",
    "行政班": "行政班",
    "行政班早班": "行政班",
    "白班": "行政班",
}


def execute(filters=None):
    filters = filters or {}
    enable_ai = bool(filters.get("enable_ai"))
    conditions = []
    values = {}

    # 日期范围过滤：仅当 from_date 与 to_date 都提供且 from<=to 时才生效，
    # 避免「只填开始/结束日期」「起止倒置」等输入产生空结果、界面消失
    from_date = filters.get("from_date") or ""
    to_date = filters.get("to_date") or ""
    if from_date and to_date and str(from_date) <= str(to_date):
        conditions.append("a.attendance_date >= %(from_date)s")
        values["from_date"] = from_date
        conditions.append("a.attendance_date <= %(to_date)s")
        values["to_date"] = to_date
    if filters.get("employee"):
        conditions.append("a.employee = %(employee)s")
        values["employee"] = filters["employee"]
    if filters.get("department"):
        conditions.append("emp.department = %(department)s")
        values["department"] = filters["department"]
    if filters.get("month") and filters.get("year"):
        conditions.append("MONTH(a.attendance_date) = %(month)s")
        values["month"] = int(filters["month"])
        conditions.append("YEAR(a.attendance_date) = %(year)s")
        values["year"] = int(filters["year"])

    # 豁免名单过滤: 经理以上人员不计入异常考勤
    from hb_attendance_app.hbos_attendance.api import EXEMPT_NUMS
    if EXEMPT_NUMS:
        quoted = ",".join("'%s'" % v.replace("'", "") for v in sorted(EXEMPT_NUMS))
        conditions.append("emp.employee_number NOT IN (%s)" % quoted)

    where = " AND ".join(conditions) if conditions else "1=1"

    # Get all attendance records
    attendance = frappe.db.sql(
        f"""
        SELECT
            a.name, a.employee, a.attendance_date, a.status,
            a.late_entry, a.early_exit, a.shift, a.working_hours,
            emp.employee_name, emp.employee_number, emp.department
        FROM tabAttendance a
        LEFT JOIN tabEmployee emp ON emp.name = a.employee
        WHERE {where}
        ORDER BY emp.employee_number, a.attendance_date
        """,
        values,
        as_dict=True,
    )

    # Get leave records for the same period
    leave_conditions = ["lr.approval_status = '已通过'", "lr.docstatus < 2"]
    leave_values = {}
    if filters.get("month") and filters.get("year"):
        leave_conditions.append(
            "MONTH(lr.start_date) <= %(month)s AND MONTH(lr.end_date) >= %(month)s"
        )
        leave_values["month"] = int(filters["month"])
        leave_conditions.append("YEAR(lr.start_date) <= %(year)s AND YEAR(lr.end_date) >= %(year)s")
        leave_values["year"] = int(filters["year"])
    elif filters.get("from_date") and filters.get("to_date"):
        leave_conditions.append(
            "lr.start_date <= %(to_date)s AND lr.end_date >= %(from_date)s"
        )
        leave_values["from_date"] = filters["from_date"]
        leave_values["to_date"] = filters["to_date"]

    leave_where = " AND ".join(leave_conditions) if leave_conditions else "1=1"
    leave_records = frappe.db.sql(
        f"""
        SELECT lr.employee, lr.start_date, lr.end_date, lr.leave_type, lr.leave_days
        FROM `tabHBOS Leave Record` lr
        WHERE {leave_where}
        """,
        leave_values,
        as_dict=True,
    )

    # Build per-employee leave date set
    emp_leave_dates = defaultdict(set)
    emp_leave_detail = defaultdict(list)
    for lr in leave_records:
        d = lr["start_date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        end = lr["end_date"]
        if isinstance(end, str):
            end = date.fromisoformat(end)
        while d <= end:
            emp_leave_dates[lr["employee"]].add(str(d))
            d += timedelta(days=1)
        # Store detail
        emp_leave_detail[lr["employee"]].append({
            "start": str(lr["start_date"]),
            "end": str(lr["end_date"]),
            "type": lr["leave_type"],
            "days": lr["leave_days"],
        })

    # Build per-employee summary
    if attendance:
        emp_summary = {}
        for a in attendance:
            emp = a["employee"]
            if emp not in emp_summary:
                emp_summary[emp] = {
                    "employee": emp,
                    "employee_name": a["employee_name"] or "",
                    "employee_number": a["employee_number"] or "",
                    "department": a["department"] or "",
                    "shifts": defaultdict(int),
                    "late_list": [],
                    "early_list": [],
                    "absent_list": [],
                    "leave_list": [],
                    "normal_list": [],
                }

            s = emp_summary[emp]
            shift_display = SHIFT_NAMES.get(a["shift"], a["shift"] or "未排班")
            s["shifts"][shift_display] += 1

            date_str = str(a["attendance_date"])
            day_label = date_str[8:]

            # Check if this date is a leave day
            is_leave = date_str in emp_leave_dates.get(emp, set())

            if is_leave:
                s["leave_list"].append(day_label)
            elif a["status"] == "Absent":
                s["absent_list"].append(day_label)
            elif a["late_entry"] and a["early_exit"]:
                s["late_list"].append(day_label)
            elif a["late_entry"]:
                s["late_list"].append(day_label)
            elif a["early_exit"]:
                s["early_list"].append(day_label)
            else:
                s["normal_list"].append(day_label)

        # Build report rows
        data = []
        for emp in sorted(emp_summary.keys()):
            s = emp_summary[emp]
            shift_counts = s["shifts"]
            # Build leave detail string
            leave_details = emp_leave_detail.get(emp, [])
            leave_detail_str = "  ".join(
                f"{ld['start'][5:]}-{ld['end'][5:]}" for ld in leave_details
            )
            data.append({
                "employee": s["employee"],
                "employee_name": s["employee_name"],
                "employee_number": s["employee_number"],
                "department": s["department"],
                "shift_行政班": shift_counts.get("行政班", 0),
                "shift_早班": shift_counts.get("早班", 0),
                "shift_中班": shift_counts.get("中班", 0),
                "shift_晚班": shift_counts.get("晚班", 0),
                "shift_未排班": shift_counts.get("未排班", 0),
                "late_count": len(s["late_list"]),
                "early_count": len(s["early_list"]),
                "absent_count": len(s["absent_list"]),
                "leave_count": len(s["leave_list"]),
                "normal_count": len(s["normal_list"]),
                "late_detail": "  ".join(s["late_list"]),
                "early_detail": "  ".join(s["early_list"]),
                "absent_detail": "  ".join(s["absent_list"]),
                "leave_detail": "  ".join(s["leave_list"]),
            })

        if enable_ai:
            _attach_ai_review(data, filters, emp_leave_dates)

        return _columns(enable_ai), data

    return _columns(enable_ai), []


def _range_from_filters(filters):
    """返回 (start, end) 字符串日期，覆盖报表统计范围。

    优先用 from_date/to_date；否则按 month/year 折算整月；都没有则返回空串。
    """
    filters = filters or {}
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    if from_date and to_date:
        return str(from_date), str(to_date)
    month, year = filters.get("month"), filters.get("year")
    if month is None or year is None:
        return "", ""
    y, m = int(year), int(month)
    last_day = calendar.monthrange(y, m)[1]
    return f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last_day:02d}"


def _range_ym(filters):
    """从 filters 推导报表所属 (year, month)；无时间范围则返回 None。"""
    filters = filters or {}
    if filters.get("month") is not None and filters.get("year") is not None:
        return int(filters["year"]), int(filters["month"])
    start, _ = _range_from_filters(filters)
    if start:
        return int(start[:4]), int(start[5:7])
    return None


def _split_tokens(text):
    return [t for t in (text or "").split() if t]


def _row_anomaly(r):
    """行是否有异常：迟到/早退/缺勤任一 >0。"""
    return ((r.get("late_count") or 0) + (r.get("early_count") or 0)
            + (r.get("absent_count") or 0)) > 0


def _detail_has(detail, d):
    """detail（空格分隔日标签）是否含日期 d（YYYY-MM-DD）。标签为两位日号或 MM-DD。"""
    yyyy, mm, dd = d.split("-")
    for t in _split_tokens(detail):
        if t == dd or t == f"{mm}-{dd}":
            return True
    return False


def _anomaly_dates(r, filters):
    """把行内 late/early/absent_detail 的日标签还原为 YYYY-MM-DD 全集（去重保序）。

    日报表 detail 只存两位日号（如 "15"），这里用 filters 的 year/month 补全成完整日期，
    供 build_prompt / parse_review 使用。
    """
    ym = _range_ym(filters)
    if ym is None:
        return []
    year, month = ym
    dates = []
    for t in (_split_tokens(r.get("late_detail")) + _split_tokens(r.get("early_detail"))
              + _split_tokens(r.get("absent_detail"))):
        try:
            if "-" in t:
                mm, dd = t.split("-", 1)
                full = f"{year:04d}-{int(mm):02d}-{int(dd):02d}"
            else:
                full = f"{year:04d}-{month:02d}-{int(t):02d}"
        except ValueError:
            continue
        if full not in dates:
            dates.append(full)
    return dates


def _type_for_date(r, d):
    """返回日期 d（YYYY-MM-DD）在行 r 中属哪类异常：迟到/早退/缺勤。"""
    if _detail_has(r.get("late_detail"), d):
        return "迟到"
    if _detail_has(r.get("early_detail"), d):
        return "早退"
    if _detail_has(r.get("absent_detail"), d):
        return "缺勤"
    return "异常"


def _rule_line_for(r):
    """返回该员工班次判定文本。本期为通用文本，并标注豁免/行政班名单命中。"""
    parts = ["按系统规则（部门-班次-人员 + 内置班次）判定"]
    num = str(r.get("employee_number") or "").strip()
    if num:
        try:
            from hb_attendance_app.hbos_attendance.api import ADMIN_NUMS, EXEMPT_NUMS
        except Exception:
            ADMIN_NUMS = set()
            EXEMPT_NUMS = set()
        if num in EXEMPT_NUMS:
            parts.append("该员工在免异常考勤白名单")
        if num in ADMIN_NUMS:
            parts.append("该员工为行政班（周末双休、不判缺勤）")
    return "；".join(parts) + "。"


def _attach_ai_review(data, filters, emp_leave_dates):
    """enable_ai 时：为当月有异常的员工逐人调 AI，写 ai_review 文本。

    仅复核迟到/早退/缺勤任一 >0 的员工；逐人失败回落提示，不整体中断。
    """
    from hb_attendance_app.hbos_attendance.ai_review import (
        AI_BATCH, AI_BATCH_SECONDS, build_prompt, call_llm, env_config, parse_review,
    )
    cfg = env_config()
    if not (cfg["base_url"] and cfg["api_key"] and cfg["model"]):
        for r in data:
            if _row_anomaly(r):
                r["ai_review"] = "AI复核失败：未配置 AI（HBOS_AI_BASE_URL / HBOS_AI_API_KEY / HBOS_AI_MODEL）"
        return

    if _range_ym(filters) is None:
        for r in data:
            if _row_anomaly(r):
                r["ai_review"] = "AI复核失败：缺少时间范围（请选择 month/year 或 from_date/to_date）"
        return

    # 收集有异常员工的异常日期 + 考勤明细
    all_target = [(r, _anomaly_dates(r, filters)) for r in data if _row_anomaly(r)]
    if not all_target:
        return
    # 单批上限：同步逐人调 LLM 受报表请求超时限制（PROXY_READ_TIMEOUT=120s），
    # 只复核前 AI_BATCH 人，其余异常员工标记未复核（不发起调用、不产生费用）
    target = all_target[:AI_BATCH]
    for r, _ in all_target[AI_BATCH:]:
        r["ai_review"] = f"未复核：本批上限 {AI_BATCH} 人，当前异常员工较多，请用部门/员工过滤缩小范围或分批逐次复核"
    emp_ids = [r["employee"] for r, _ in target]
    if not emp_ids:
        return

    # 打卡流水（供 AI 判断；按员工拉全部当月卡，facts 内筛对应异常日）
    from_date, to_date = _range_from_filters(filters)
    checkin_map = {}
    if emp_ids:
        q = ",".join("'%s'" % e.replace("'", "") for e in emp_ids)
        rows = frappe.db.sql(
            f"SELECT employee, time, log_type, device_id FROM `tabEmployee Checkin` "
            f"WHERE employee IN ({q}) AND DATE(time) BETWEEN %(s)s AND %(e)s "
            f"ORDER BY employee, time",
            {"s": from_date, "e": to_date}, as_dict=True)
        for c in rows:
            checkin_map.setdefault(c.employee, []).append(c)

    import time as _time
    batch_deadline = _time.monotonic() + AI_BATCH_SECONDS
    for r, dates in target:
        # 累计时间预算：超预算停止新调用（请求须在代理超时内返回），剩余标记未复核
        if _time.monotonic() > batch_deadline:
            idx = target.index((r, dates))
            for rr, _ in target[idx:]:
                if rr.get("ai_review") is None:
                    rr["ai_review"] = f"未复核：单批时间预算 {AI_BATCH_SECONDS}s 已到，请缩小范围或分批复核"
            break
        emp_id = r["employee"]
        rule_line = _rule_line_for(r)
        cks = checkin_map.get(emp_id, [])
        ck_lines = "\n".join(
            f"{c.time.strftime('%m/%d %H:%M')} {c.log_type or ''} {c.device_id or ''}"
            for c in cks if str(c.time.date()) in dates
        ) or "无打卡记录"
        items = [(d, _type_for_date(r, d)) for d in dates]
        prompt = build_prompt(
            {"name": r["employee_name"], "num": r["employee_number"], "dept": r["department"]},
            items, ck_lines, rule_line,
        )
        try:
            text = call_llm(cfg, prompt)
            parsed = parse_review(text, dates)
            r["ai_review"] = "\n".join(f"{d}｜{parsed[d]}" for d in dates if d in parsed) or "AI复核失败：无有效返回"
        except Exception as e:
            r["ai_review"] = f"AI复核失败：{e}"


@frappe.whitelist()
def ai_review_preview(month=None, year=None, employee=None, department=None,
                      from_date=None, to_date=None):
    """AI复核确认弹窗：统计当前范围有异常员工数与异常条数（已剔豁免名单）。"""
    filters = {"enable_ai": 0}
    if month is not None:
        filters["month"] = month
    if year is not None:
        filters["year"] = year
    if employee:
        filters["employee"] = employee
    if department:
        filters["department"] = department
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date
    _, data = execute(filters)
    employees = set()
    anomaly_count = 0
    for r in data:
        n = ((r.get("late_count") or 0) + (r.get("early_count") or 0)
             + (r.get("absent_count") or 0))
        if n > 0:
            employees.add(r["employee"])
            anomaly_count += n
    from hb_attendance_app.hbos_attendance.ai_review import AI_BATCH
    return {"employee_count": len(employees), "anomaly_count": anomaly_count,
            "batch": AI_BATCH}


def _columns(enable_ai=False):
    cols = [
        {"label": "员工姓名", "fieldname": "employee_name", "fieldtype": "Data", "width": 100},
        {"label": "工号", "fieldname": "employee_number", "fieldtype": "Data", "width": 100},
        {"label": "部门", "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": "行政班(天)", "fieldname": "shift_行政班", "fieldtype": "Int", "width": 85},
        {"label": "早班(天)", "fieldname": "shift_早班", "fieldtype": "Int", "width": 85},
        {"label": "中班(天)", "fieldname": "shift_中班", "fieldtype": "Int", "width": 85},
        {"label": "晚班(天)", "fieldname": "shift_晚班", "fieldtype": "Int", "width": 85},
        {"label": "迟到(次)", "fieldname": "late_count", "fieldtype": "Int", "width": 80},
        {"label": "早退(次)", "fieldname": "early_count", "fieldtype": "Int", "width": 80},
        {"label": "缺勤(天)", "fieldname": "absent_count", "fieldtype": "Int", "width": 80},
        {"label": "请假(天)", "fieldname": "leave_count", "fieldtype": "Int", "width": 80},
        {"label": "正常(天)", "fieldname": "normal_count", "fieldtype": "Int", "width": 80},
        {"label": "迟到详情", "fieldname": "late_detail", "fieldtype": "Small Text", "width": 500},
        {"label": "早退详情", "fieldname": "early_detail", "fieldtype": "Small Text", "width": 500},
        {"label": "缺勤详情", "fieldname": "absent_detail", "fieldtype": "Small Text", "width": 500},
        {"label": "请假详情", "fieldname": "leave_detail", "fieldtype": "Small Text", "width": 500},
    ]
    if enable_ai:
        cols.append({"label": "AI复核", "fieldname": "ai_review",
                     "fieldtype": "Small Text", "width": 450})
    return cols