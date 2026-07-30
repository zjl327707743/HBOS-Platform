import frappe
import json
from datetime import datetime, date, timedelta
from collections import defaultdict


SHIFT_NAMES = {
    "早班": "早班", "中班": "中班", "晚班": "晚班",
    "行政班早班": "白班", "白班": "白班",
}

# 倒班部门关键词
SHIFT_DEPT_KEYWORDS = ["倒班", "班一", "班二", "班三", "班四", "夜"]


def _is_shift_dept(dept_name):
    return any(kw in dept_name for kw in SHIFT_DEPT_KEYWORDS)


@frappe.whitelist()
def process_excel(month=None, year=None):
    from frappe.utils.file_manager import save_file

    file = frappe.request.files.get("file")
    if not file:
        frappe.throw("请选择要上传的文件")

    month = int(month or frappe.form_dict.get("month", 7))
    year = int(year or frappe.form_dict.get("year", 2026))

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name

    try:
        import openpyxl
        wb = openpyxl.load_workbook(tmp_path)
        ws = wb.active

        dates = []
        for col in range(11, 33):
            val = ws.cell(row=2, column=col).value
            if val:
                parts = str(val).split("\n")
                date_str = parts[-1].strip()
                d = datetime.strptime(f"20{date_str}", "%Y-%m-%d").date()
                dates.append(d)

        records = []
        current_emp = None
        emp_rows = []
        for row_num in range(3, ws.max_row + 1):
            name = ws.cell(row=row_num, column=1).value
            emp_id = ws.cell(row=row_num, column=2).value
            dept = ws.cell(row=row_num, column=3).value
            if name and emp_id and dept:
                if current_emp and emp_rows:
                    records.append({"emp": current_emp, "rows": list(emp_rows)})
                current_emp = {"name": str(name).strip(), "id": str(emp_id).strip(), "dept": str(dept).strip()}
                emp_rows = [row_num]
            elif current_emp:
                emp_rows.append(row_num)
        if current_emp and emp_rows:
            records.append({"emp": current_emp, "rows": list(emp_rows)})

        seen_checkins = set()
        seen_attendance = set()
        checkin_count = 0
        att_count = 0
        late_count = 0
        absent_count = 0
        emp_set = set()

        for rec in records:
            emp = rec["emp"]
            emp_obj = frappe.db.get_value("Employee", {"employee_number": emp["id"]}, "name")
            if not emp_obj:
                emp_obj = frappe.db.get_value("Employee", {"employee_name": emp["name"]}, "name")
            if not emp_obj:
                continue
            emp_set.add(emp_obj)

            dept_name = emp["dept"]

            if _is_shift_dept(dept_name):
                # === 倒班模式：跨日配对 ===
                # Step 1: Collect ALL timestamps as (datetime, day_index)
                all_stamps = []
                for day_idx, d in enumerate(dates):
                    for r in rec["rows"]:
                        val = ws.cell(row=r, column=11 + day_idx).value
                        if val and str(val).strip() and str(val).strip() != "-" and str(val).strip() != "00:00":
                            t = str(val).strip()
                            h, m = t.split(":")
                            hour_float = float(h) + float(m) / 60.0
                            dt = datetime.combine(d, datetime.strptime(t, "%H:%M").time())
                            all_stamps.append((dt, hour_float, d))

                if not all_stamps:
                    continue

                all_stamps.sort(key=lambda x: x[0])

                # Step 2: Pair timestamps into shift segments
                #   A shift starts when: time >= 08:00 or time < 00:00 (early morning is end of previous shift)
                #   Actually: pair consecutive stamps. If a stamp at 00:xx-07:xx follows a 15:xx-23:59,
                #   it's the END of the previous shift.
                shifts = []
                pending_start = None

                for i, (dt, hf, d) in enumerate(all_stamps):
                    if pending_start is None:
                        # This is a shift start (or single stamp)
                        shift_type = _assign_shift_type(hf)
                        pending_start = (dt, hf, d, shift_type)
                    elif hf < 8.0:
                        # 00:00-08:00: This is the END of the pending shift
                        prev_dt, prev_hf, prev_d, shift_type = pending_start
                        shifts.append({
                            "date": prev_d,
                            "start": prev_hf,
                            "end": hf,
                            "shift": shift_type,
                        })
                        pending_start = None
                    else:
                        # >= 08:00: Close previous shift (single stamp) and start new one
                        prev_dt, prev_hf, prev_d, shift_type = pending_start
                        shifts.append({
                            "date": prev_d,
                            "start": prev_hf,
                            "end": None,  # single stamp
                            "shift": shift_type,
                        })
                        new_type = _assign_shift_type(hf)
                        pending_start = (dt, hf, d, new_type)

                # Last pending
                if pending_start is not None:
                    prev_dt, prev_hf, prev_d, shift_type = pending_start
                    shifts.append({
                        "date": prev_d,
                        "start": prev_hf,
                        "end": None,
                        "shift": shift_type,
                    })

                # Step 3: Create records
                for s in shifts:
                    att_date = s["date"]
                    shift = s["shift"]
                    start_h = s["start"]
                    end_h = s["end"]

                    # Create checkins
                    for hf in [start_h] + ([end_h] if end_h is not None else []):
                        t_str = f"{int(hf):02d}:{int((hf%1)*60):02d}"
                        dt_str = f"{att_date} {t_str}:00"
                        if (emp_obj, dt_str) not in seen_checkins:
                            seen_checkins.add((emp_obj, dt_str))
                            try:
                                is_in = (hf == start_h)
                                doc = frappe.get_doc({
                                    "doctype": "Employee Checkin",
                                    "employee": emp_obj,
                                    "time": dt_str,
                                    "log_type": "IN" if is_in else "OUT",
                                })
                                doc.insert(ignore_permissions=True)
                                checkin_count += 1
                            except Exception:
                                pass

                    # Create attendance
                    if (emp_obj, str(att_date)) not in seen_attendance:
                        seen_attendance.add((emp_obj, str(att_date)))
                        try:
                            if end_h is None:
                                # Single stamp: not absent, just incomplete
                                status = "Present"
                                late = 0
                                early = 0
                            else:
                                status, late, early = _judge_shift(start_h, end_h, shift)

                            doc = frappe.get_doc({
                                "doctype": "Attendance",
                                "employee": emp_obj,
                                "attendance_date": str(att_date),
                                "status": status,
                                "late_entry": late,
                                "early_exit": early,
                                "shift": shift,
                            })
                            doc.insert(ignore_permissions=True)
                            att_count += 1
                            if late:
                                late_count += 1
                            if status == "Absent":
                                absent_count += 1
                        except Exception:
                            pass

            else:
                # === 非倒班模式：逐日判定（不变） ===
                for day_idx, d in enumerate(dates):
                    times = []
                    for r in rec["rows"]:
                        val = ws.cell(row=r, column=11 + day_idx).value
                        if val and str(val).strip() and str(val).strip() != "-" and str(val).strip() != "00:00":
                            t = str(val).strip()
                            h, m = t.split(":")
                            times.append(float(h) + float(m) / 60.0)

                    if not times:
                        continue

                    shift = _assign_fixed_shift(dept_name, times)
                    status, late_f, early_f = _judge_shift(min(times), max(times), shift) if len(times) >= 2 else ("Present", 0, 0)
                    if len(times) == 1:
                        status = "Absent"

                    # Create checkins
                    sorted_times = sorted(times)
                    for ti, hf in enumerate(sorted_times):
                        t_str = f"{int(hf):02d}:{int((hf%1)*60):02d}"
                        dt_str = f"{d} {t_str}:00"
                        if (emp_obj, dt_str) not in seen_checkins:
                            seen_checkins.add((emp_obj, dt_str))
                            try:
                                doc = frappe.get_doc({
                                    "doctype": "Employee Checkin",
                                    "employee": emp_obj,
                                    "time": dt_str,
                                    "log_type": "IN" if hf == min(times) else "OUT",
                                })
                                doc.insert(ignore_permissions=True)
                                checkin_count += 1
                            except Exception:
                                pass

                    if (emp_obj, str(d)) not in seen_attendance:
                        seen_attendance.add((emp_obj, str(d)))
                        try:
                            doc = frappe.get_doc({
                                "doctype": "Attendance",
                                "employee": emp_obj,
                                "attendance_date": str(d),
                                "status": status,
                                "late_entry": late_f,
                                "early_exit": early_f,
                                "shift": shift,
                            })
                            doc.insert(ignore_permissions=True)
                            att_count += 1
                            if late_f:
                                late_count += 1
                            if status == "Absent":
                                absent_count += 1
                        except Exception:
                            pass

        frappe.db.commit()

        return {
            "employees": len(emp_set),
            "checkins": checkin_count,
            "attendance": att_count,
            "late": late_count,
            "absent": absent_count,
        }

    finally:
        import os
        os.unlink(tmp_path)


def _assign_shift_type(hour_float):
    """Assign shift type based on clock-in time."""
    if 6.0 <= hour_float <= 10.0:
        return "早班"
    elif 14.0 <= hour_float <= 18.0:
        return "中班"
    elif hour_float >= 20.0 or hour_float <= 4.0:
        return "晚班"
    return "早班"


def _assign_fixed_shift(dept_name, times):
    in_time = min(times)
    if "白班" in dept_name:
        return "早班"
    elif "办公室" in dept_name or "行政" in dept_name or "人事" in dept_name or "财务" in dept_name or "市场" in dept_name or "技术" in dept_name or "注册" in dept_name or "采购" in dept_name or "质量" in dept_name or "安全" in dept_name or "生产部" in dept_name or "设备动力部" in dept_name or "总经办" in dept_name or "AI" in dept_name:
        return "行政班早班"
    elif "常白班" in dept_name or "工艺白班组" in dept_name:
        return "行政班早班"
    elif 6.0 <= in_time <= 10.0:
        return "早班"
    elif 14.0 <= in_time <= 18.0:
        return "中班"
    return "早班"


def _judge_shift(start_h, end_h, shift_name):
    """Judge late/early status for a given shift. end_h can be None for single stamp."""
    shift_map = {
        "行政班早班": (8.5, 17.5),
        "早班": (8.0, 16.0),
        "中班": (16.0, 24.0),
        "晚班": (0.0, 8.0),
    }
    expected_start, expected_end = shift_map.get(shift_name, (8.0, 16.0))

    if end_h is None:
        return "Present", 0, 0

    late = start_h > expected_start
    early = end_h < expected_end

    if late:
        return "Present", 1, 0
    if early:
        return "Present", 0, 1
    return "Present", 0, 0