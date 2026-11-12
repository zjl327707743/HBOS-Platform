"""Bounded orchestration of native HRMS shift calculations and Attendance docs.

Never call ShiftType._process: it enumerates all assignees and commits batches.
Only input employee/dates are eligible; existing human attendance is preserved.
"""
from collections import Counter
from datetime import timedelta
from itertools import groupby

import frappe
from frappe.utils import flt, getdate, get_datetime


def process_checkins(impacted, log_name):
    from hrms.hr.doctype.employee_checkin.employee_checkin import (
        add_comment_in_checkins, get_overtime_data, skip_attendance_in_checkins,
        update_attendance_in_checkins,
    )
    from hb_attendance_app.hbos_attendance.doctype.hbos_attendance_import_log.hbos_attendance_import_log import _mark_attendance_source

    stats = Counter()
    for employee in sorted({item[0] for item in impacted}):
        days = {day for person, day in impacted if person == employee}
        # Pairing may consume adjacent-day checkins, never another employee.
        logs = frappe.db.sql("""select name,employee,time,log_type,shift,shift_start,
            shift_end,shift_actual_start,shift_actual_end,overtime_type from `tabEmployee Checkin`
            where employee=%s and time>=%s and time<%s and skip_auto_attendance=0
            and coalesce(attendance,'')='' and offshift=0 order by shift,shift_start,time,name for update""",
            (employee, min(days)-timedelta(days=2), max(days)+timedelta(days=3)), as_dict=True)
        for (shift_name, shift_start), group in groupby(logs, lambda row: (row.shift, row.shift_start)):
            items = list(group)
            if not shift_name or not shift_start or getdate(shift_start) not in days:
                continue
            shift = frappe.get_doc('Shift Type', shift_name, for_update=True)
            if shift.has_incorrect_shift_config():
                continue
            items = [row for row in items if row.time >= get_datetime(shift.process_attendance_after)
                     and row.shift_actual_end and row.shift_actual_end < get_datetime(shift.last_sync_of_checkin)]
            if not items:
                continue
            day = getdate(shift_start)
            if not shift.should_mark_attendance(employee, day):
                continue
            existing = frappe.db.sql('select name,company from `tabAttendance` where employee=%s and attendance_date=%s and docstatus<2 for update', (employee, day), as_dict=True)
            if existing:
                # Native importer also skips an existing result. Keep its
                # source and half-day/correction state completely unchanged.
                skip_attendance_in_checkins([row.name for row in items])
                add_comment_in_checkins([row.name for row in items], '已有考勤或更正结果，本次导入保留原结果。')
                stats['existing_attendance'] += len(existing)
                continue
            half, absent = flt(shift.working_hours_threshold_for_half_day), flt(shift.working_hours_threshold_for_absent)
            if shift.is_half_holiday(employee, day):
                half, absent = half / 2, absent / 2
            status, hours, late, early, in_time, out_time = shift.get_attendance(items, absent, half)
            if status == 'Skip':
                skip_attendance_in_checkins([row.name for row in items])
                continue
            if status not in {'Present', 'Absent', 'Half Day'}:
                frappe.throw('原生班次计算返回未知考勤状态。', frappe.ValidationError)
            doc = frappe.get_doc(dict(doctype='Attendance', employee=employee,
                company=frappe.db.get_value('Employee',employee,'company',for_update=True),
                attendance_date=day, status=status, shift=shift.name, working_hours=hours,
                late_entry=late, early_exit=early, in_time=in_time, out_time=out_time))
            overtime_type = items[0].get('overtime_type')
            if overtime_type and status == 'Present':
                overtime = get_overtime_data(shift.name, hours)
                if overtime:
                    doc.update(dict(overtime_type=overtime_type, **overtime))
            doc.flags.ignore_permissions = True  # Exact preflighted employee/date only.
            doc.insert(ignore_permissions=True)
            doc.submit()  # Native validation, overlaps, leave, workflow and hooks.
            if status == 'Absent':
                doc.add_comment(text=frappe._('Employee was marked Absent for not meeting the working hours threshold.'))
            update_attendance_in_checkins([row.name for row in items], doc.name)
            _mark_attendance_source(doc.name, log_name, 'HRMS Auto Attendance')
            stats['created_attendance'] += 1
            stats['auto_attendance_used'] = 1
    return stats
