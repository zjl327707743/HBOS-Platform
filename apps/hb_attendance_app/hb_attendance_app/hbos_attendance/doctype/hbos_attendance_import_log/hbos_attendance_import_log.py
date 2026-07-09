import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, now_datetime


NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{2})")


class HBOSAttendanceImportLog(Document):
	def before_insert(self):
		if not self.run_by:
			self.run_by = frappe.session.user


@frappe.whitelist()
def preview_import(log_name=None, source_file=None, local_path=None):
	frappe.only_for(("System Manager", "HR Manager", "HR User"))
	path, file_name = _resolve_source(log_name=log_name, source_file=source_file, local_path=local_path)
	parsed = _parse_monthly_xlsx(path)
	log = _get_or_create_log(log_name, source_file, file_name, path)
	_apply_summary(log, parsed.preview_summary(), status="Previewed")
	log.save(ignore_permissions=True)
	frappe.db.commit()
	return {"log_name": log.name, **parsed.preview_summary()}


@frappe.whitelist()
def run_import(log_name=None, source_file=None, local_path=None, create_missing_employees=1, limit_rows=None):
	frappe.only_for(("System Manager", "HR Manager", "HR User"))
	path, file_name = _resolve_source(log_name=log_name, source_file=source_file, local_path=local_path)
	parsed = _parse_monthly_xlsx(path)
	log = _get_or_create_log(log_name, source_file, file_name, path)
	log.import_status = "Running"
	log.started_at = now_datetime()
	log.run_by = frappe.session.user
	log.save(ignore_permissions=True)
	frappe.db.commit()

	try:
		result = _execute_import(parsed, bool(int(create_missing_employees)), int(limit_rows or 0))
		status = "Success" if result["failed_rows"] == 0 else "Partial Success"
		_apply_summary(log, result, status=status)
	except Exception as exc:
		frappe.db.rollback()
		result = {
			**parsed.preview_summary(),
			"failed_rows": parsed.identity_rows,
			"failure_details": [{"row": 0, "reason": str(exc), "suggestion": "检查导入方法或 Frappe 错误日志"}],
		}
		_apply_summary(log, result, status="Failed")
		log.save(ignore_permissions=True)
		frappe.db.commit()
		raise

	log.finished_at = now_datetime()
	log.save(ignore_permissions=True)
	frappe.db.commit()
	return {"log_name": log.name, **result}


def _resolve_source(log_name=None, source_file=None, local_path=None):
	if local_path:
		path = Path(local_path)
		if not path.exists():
			frappe.throw(f"Local file not found: {local_path}")
		return path, path.name

	file_url = source_file
	if log_name and not file_url:
		file_url = frappe.db.get_value("HBOS Attendance Import Log", log_name, "source_file")

	if not file_url:
		frappe.throw("source_file, local_path, or log_name with source_file is required")

	if file_url.startswith("/private/files/"):
		relative = file_url.replace("/private/", "", 1)
		path = Path(frappe.get_site_path("private", relative.replace("files/", "files/", 1)))
	elif file_url.startswith("/files/"):
		path = Path(frappe.get_site_path("public", file_url.lstrip("/")))
	else:
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		return _resolve_source(source_file=file_doc.file_url)

	if not path.exists():
		frappe.throw(f"Attached file not found on site: {file_url}")
	return path, path.name


def _get_or_create_log(log_name, source_file, file_name, path):
	if log_name:
		log = frappe.get_doc("HBOS Attendance Import Log", log_name)
	else:
		log = frappe.new_doc("HBOS Attendance Import Log")
		log.import_type = "月度汇总表"
		log.import_status = "Draft"
		log.source_file = source_file
	log.source_file_name = file_name
	log.source_file_hash = _sha256(path)
	log.run_by = frappe.session.user
	return log


def _sha256(path):
	h = hashlib.sha256()
	with open(path, "rb") as handle:
		for chunk in iter(lambda: handle.read(1024 * 1024), b""):
			h.update(chunk)
	return h.hexdigest()


def _apply_summary(log, result, status):
	log.import_type = result.get("import_type", "月度汇总表")
	log.import_status = status
	log.period_start = result.get("period_start")
	log.period_end = result.get("period_end")
	for field in (
		"total_rows",
		"matched_rows",
		"success_rows",
		"failed_rows",
		"created_employees",
		"created_checkins",
		"created_attendance",
		"skipped_duplicates",
	):
		log.set(field, int(result.get(field) or 0))
	log.auto_attendance_used = int(bool(result.get("auto_attendance_used")))
	log.fallback_used = int(bool(result.get("fallback_used")))
	log.mapping_summary = json.dumps(result.get("mapping_summary", {}), ensure_ascii=False, indent=2)
	log.exception_summary = json.dumps(result.get("exception_summary", {}), ensure_ascii=False, indent=2)
	log.failure_details = json.dumps(result.get("failure_details", []), ensure_ascii=False, indent=2)
	if result.get("notes"):
		log.notes = result["notes"]


class MonthlyWorkbook:
	def __init__(self, rows, header_index, headers, records, daily_columns, sheet_names):
		self.rows = rows
		self.header_index = header_index
		self.headers = headers
		self.records = records
		self.daily_columns = daily_columns
		self.sheet_names = sheet_names

	@property
	def identity_rows(self):
		return len(self.records)

	def preview_summary(self):
		dates = [item["date"] for item in self.daily_columns]
		return {
			"import_type": "月度汇总表",
			"total_rows": len(self.rows),
			"matched_rows": 0,
			"success_rows": 0,
			"failed_rows": 0,
			"created_employees": 0,
			"created_checkins": 0,
			"created_attendance": 0,
			"skipped_duplicates": 0,
			"period_start": min(dates).isoformat() if dates else None,
			"period_end": max(dates).isoformat() if dates else None,
			"auto_attendance_used": False,
			"fallback_used": False,
			"mapping_summary": {
				"sheet_names": self.sheet_names,
				"header_row": self.header_index + 1,
				"detected_headers": self.headers,
				"daily_columns": [item["header"] for item in self.daily_columns],
				"identity_rows": self.identity_rows,
				"classification": "月度汇总表 / Demo 转换导入",
				"source_note": "该文件不是一行一条原始打卡流水；导入会按月度汇总表转换生成 Demo Checkin / Attendance。",
			},
			"exception_summary": {},
			"failure_details": [],
			"notes": "Preview only; no Employee, Employee Checkin, or Attendance records were written.",
		}


def _parse_monthly_xlsx(path):
	rows, sheet_names = _read_first_sheet(path)
	header_index = None
	for index, row in enumerate(rows):
		values = {cell.strip() for cell in row if isinstance(cell, str)}
		if {"姓名", "工号", "部门"}.issubset(values):
			header_index = index
			break
	if header_index is None:
		frappe.throw("未识别到包含 姓名 / 工号 / 部门 的表头行")

	headers = [cell.strip().replace("\n", " ") for cell in rows[header_index]]
	header_map = {header: idx for idx, header in enumerate(headers) if header}
	daily_columns = []
	for idx, header in enumerate(headers):
		match = DATE_RE.search(header)
		if match:
			year, month, day = match.groups()
			daily_columns.append({"idx": idx, "header": header, "date": getdate(f"20{year}-{month}-{day}")})

	records = _collect_identity_records(rows[header_index + 1 :], header_map, daily_columns, header_index)
	return MonthlyWorkbook(rows, header_index, headers, records, daily_columns, sheet_names)


def _read_first_sheet(path):
	with zipfile.ZipFile(path) as archive:
		sheet_names = _get_sheet_names(archive)
		shared_strings = _read_shared_strings(archive)
		sheet_xml = archive.read("xl/worksheets/sheet1.xml")

	root = ET.fromstring(sheet_xml)
	rows = []
	for row in root.findall(".//a:sheetData/a:row", NS):
		values = []
		for cell in row.findall("a:c", NS):
			idx = _column_index(cell.attrib.get("r", "A1"))
			while len(values) <= idx:
				values.append("")
			values[idx] = _cell_value(cell, shared_strings)
		rows.append(values)
	return rows, sheet_names


def _get_sheet_names(archive):
	try:
		root = ET.fromstring(archive.read("xl/workbook.xml"))
	except KeyError:
		return []
	return [sheet.attrib.get("name", "") for sheet in root.findall(".//a:sheets/a:sheet", NS)]


def _read_shared_strings(archive):
	try:
		root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
	except KeyError:
		return []
	return ["".join(t.text or "" for t in item.findall(".//a:t", NS)) for item in root.findall("a:si", NS)]


def _cell_value(cell, shared_strings):
	cell_type = cell.attrib.get("t")
	if cell_type == "inlineStr":
		return "".join(t.text or "" for t in cell.findall(".//a:t", NS)).strip()
	value = cell.find("a:v", NS)
	if value is None:
		return ""
	raw = value.text or ""
	if cell_type == "s" and raw.isdigit() and int(raw) < len(shared_strings):
		return shared_strings[int(raw)].strip()
	return raw.strip()


def _column_index(reference):
	letters = "".join(ch for ch in reference if ch.isalpha())
	idx = 0
	for char in letters:
		idx = idx * 26 + ord(char.upper()) - 64
	return idx - 1


def _collect_identity_records(rows, header_map, daily_columns, header_index):
	records = []
	current = None
	for offset, row in enumerate(rows, start=header_index + 2):
		name = _value(row, header_map.get("姓名"))
		employee_number = _value(row, header_map.get("工号"))
		department = _value(row, header_map.get("部门"))
		if name or employee_number or department:
			current = {
				"row": offset,
				"employee_name": name,
				"employee_number": employee_number,
				"department": department,
				"leave_hours": _number(_value(row, header_map.get("请假时长(小时)"))),
				"expected_days": _number(_value(row, header_map.get("应出勤天数"))),
				"actual_days": _number(_value(row, header_map.get("实际出勤天数"))),
				"pay_hours": _number(_value(row, header_map.get("计薪时长 (小时)"))),
				"late_count": _number(_value(row, header_map.get("迟到次数"))),
				"early_count": _number(_value(row, header_map.get("早退次数"))),
				"absent_days": _number(_value(row, header_map.get("旷工天数"))),
				"daily": defaultdict(list),
			}
			records.append(current)
		if current:
			for col in daily_columns:
				text = _value(row, col["idx"])
				if text:
					current["daily"][col["date"]].append(text)
	return records


def _value(row, idx):
	if idx is None or idx >= len(row):
		return ""
	return (row[idx] or "").strip()


def _number(value):
	if not value or value == "-":
		return 0
	try:
		return float(value)
	except ValueError:
		return 0


def _execute_import(parsed, create_missing_employees, limit_rows):
	company = _default_company()
	holiday_list = _default_holiday_list()
	leave_type = _default_leave_type()
	shifts = _ensure_demo_shifts(parsed, holiday_list)
	failures = []
	stats = Counter()
	exceptions = Counter()
	created_checkin_names = []
	attendance_before = set(_attendance_names_for_records(parsed.records, parsed.daily_columns))

	records = parsed.records[:limit_rows] if limit_rows else parsed.records
	for record in records:
		try:
			employee, created = _match_or_create_employee(record, company, holiday_list, create_missing_employees)
			stats["matched_rows"] += 1
			stats["created_employees"] += int(created)
			for day in parsed.daily_columns:
				date_value = day["date"]
				day_tokens = _time_tokens(" ".join(record["daily"].get(date_value, [])))
				status_plan = _status_for_day(record, date_value, bool(day_tokens))
				shift_name = _select_shift(day_tokens, shifts)
				assigned_shift = _ensure_shift_assignment(employee, shift_name, date_value)
				exceptions.update(_day_exception_labels(date_value, day_tokens, assigned_shift, status_plan))
				names, skipped = _create_demo_checkins(employee, date_value, day_tokens, assigned_shift, status_plan)
				stats["created_checkins"] += len(names)
				stats["skipped_duplicates"] += skipped
				created_checkin_names.extend(names)
		except Exception as exc:
			stats["failed_rows"] += 1
			failures.append(
				{
					"row": record["row"],
					"name_field": _mask(record.get("employee_name")),
					"employee_number_field": _mask(record.get("employee_number")),
					"reason": str(exc),
					"suggestion": "检查工号、姓名唯一性、部门或员工主数据后重试",
				}
			)

	_auto_attendance(shifts)
	stats["auto_attendance_used"] = 1

	fallback_created = _fallback_attendance(records, parsed.daily_columns, shifts, leave_type)
	stats["created_attendance"] = len(set(_attendance_names_for_records(records, parsed.daily_columns)) - attendance_before)
	if fallback_created:
		stats["fallback_used"] = 1
		stats["created_attendance"] = max(stats["created_attendance"], fallback_created)

	return {
		**parsed.preview_summary(),
		"matched_rows": stats["matched_rows"],
		"success_rows": max(stats["matched_rows"] - stats["failed_rows"], 0),
		"failed_rows": stats["failed_rows"],
		"created_employees": stats["created_employees"],
		"created_checkins": stats["created_checkins"],
		"created_attendance": stats["created_attendance"],
		"skipped_duplicates": stats["skipped_duplicates"],
		"auto_attendance_used": bool(stats["auto_attendance_used"]),
		"fallback_used": bool(stats["fallback_used"]),
		"exception_summary": dict(exceptions),
		"failure_details": failures[:50],
		"notes": "由月度汇总表转换生成 Demo Checkin；不是原始打卡机流水导入。",
	}


def _default_company():
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		return company
	return frappe.db.get_value("Company", {"name": ("like", "%Demo%")}, "name") or frappe.get_all("Company", pluck="name")[0]


def _default_holiday_list():
	return (
		frappe.db.get_value("Holiday List", {"holiday_list_name": ("like", "%M1R3C%")}, "name")
		or frappe.db.get_value("Holiday List", {}, "name")
	)


def _default_leave_type():
	return frappe.db.get_value("Leave Type", {"name": ("like", "%事假%")}, "name") or frappe.db.get_value(
		"Leave Type", {}, "name"
	)


def _ensure_demo_shifts(parsed, holiday_list):
	dates = [item["date"] for item in parsed.daily_columns]
	start = min(dates) if dates else getdate()
	end = max(dates) if dates else getdate()
	last_sync = get_datetime(datetime.combine(end, time(23, 59, 59)) + timedelta(days=1))
	specs = {
		"day": ("HBOS-M1-FIX-B-白班-0800-1600", "08:00:00", "16:00:00"),
		"middle": ("HBOS-M1-FIX-B-中班-1600-0000", "16:00:00", "00:00:00"),
		"night": ("HBOS-M1-FIX-B-夜班-0000-0800", "00:00:00", "08:00:00"),
		"cross": ("HBOS-M1-FIX-B-跨夜班-2000-0400", "20:00:00", "04:00:00"),
	}
	result = {}
	for key, (name, start_time, end_time) in specs.items():
		if frappe.db.exists("Shift Type", name):
			doc = frappe.get_doc("Shift Type", name)
		else:
			doc = frappe.new_doc("Shift Type")
			doc.name = name
		doc.update(
			{
				"start_time": start_time,
				"end_time": end_time,
				"holiday_list": holiday_list,
				"enable_auto_attendance": 1,
				"determine_check_in_and_check_out": "Strictly based on Log Type in Employee Checkin",
				"working_hours_calculation_based_on": "First Check-in and Last Check-out",
				"begin_check_in_before_shift_start_time": 240,
				"allow_check_out_after_shift_end_time": 240,
				"process_attendance_after": start,
				"last_sync_of_checkin": last_sync,
				"enable_late_entry_marking": 1,
				"late_entry_grace_period": 0,
				"enable_early_exit_marking": 1,
				"early_exit_grace_period": 0,
				"working_hours_threshold_for_half_day": 4,
				"working_hours_threshold_for_absent": 1,
			}
		)
		doc.save(ignore_permissions=True)
		result[key] = name
	return result


def _match_or_create_employee(record, company, holiday_list, create_missing):
	employee_number = record.get("employee_number")
	name = record.get("employee_name")
	if employee_number:
		employee = frappe.db.get_value("Employee", {"employee_number": employee_number}, "name")
		if not employee:
			employee = frappe.db.get_value("Employee", {"attendance_device_id": employee_number}, "name")
		if employee:
			return employee, False

	if name:
		matches = frappe.get_all("Employee", filters={"employee_name": name}, pluck="name")
		if len(matches) == 1:
			return matches[0], False
		if len(matches) > 1:
			frappe.throw("姓名匹配到多名员工，不能静默导入")

	if not create_missing:
		frappe.throw("未匹配员工，且本次不允许自动创建")
	if not name:
		frappe.throw("缺少员工姓名，不能创建 Employee")

	department = _ensure_department(record.get("department"), company)
	employee = frappe.new_doc("Employee")
	employee.first_name = name
	employee.employee_name = name
	employee.employee_number = employee_number
	employee.attendance_device_id = employee_number
	employee.company = company
	employee.department = department
	employee.gender = "Prefer not to say"
	employee.date_of_birth = getdate("1990-01-01")
	employee.date_of_joining = getdate("2026-07-01")
	employee.holiday_list = holiday_list
	employee.insert(ignore_permissions=True)
	return employee.name, True


def _ensure_department(department_name, company):
	if not department_name:
		return None
	existing = frappe.db.get_value("Department", {"department_name": department_name, "company": company}, "name")
	if existing:
		return existing
	doc = frappe.new_doc("Department")
	doc.department_name = department_name
	doc.company = company
	doc.parent_department = frappe.db.get_value("Department", {"parent_department": "", "company": ("is", "not set")}, "name")
	doc.insert(ignore_permissions=True)
	return doc.name


def _time_tokens(text):
	tokens = []
	for hour, minute in TIME_RE.findall(text or ""):
		tokens.append(time(int(hour), int(minute)))
	return tokens


def _status_for_day(record, date_value, has_tokens):
	exceptions = []
	status = "Present" if has_tokens else "Absent"
	if record.get("leave_hours", 0) >= 8 and not has_tokens:
		status = "On Leave"
		exceptions.append("全天请假")
	elif 0 < record.get("leave_hours", 0) < 8:
		status = "Half Day"
		exceptions.append("半天请假")
	if not has_tokens and record.get("absent_days", 0) > 0:
		status = "Absent"
		exceptions.append("全天缺勤")
	return {"status": status, "exceptions": exceptions}


def _select_shift(tokens, shifts):
	if not tokens:
		return shifts["day"]
	first = tokens[0]
	if first >= time(20, 0) or first < time(4, 0):
		return shifts["cross"]
	if time(15, 0) <= first < time(20, 0):
		return shifts["middle"]
	if time(0, 0) <= first < time(8, 0):
		return shifts["night"]
	return shifts["day"]


def _ensure_shift_assignment(employee, shift, date_value):
	if frappe.db.exists(
		"Shift Assignment",
		{
			"employee": employee,
			"shift_type": shift,
			"start_date": ("<=", date_value),
			"end_date": (">=", date_value),
			"docstatus": 1,
		},
	):
		return shift
	existing_shift = frappe.db.get_value(
		"Shift Assignment",
		{
			"employee": employee,
			"start_date": ("<=", date_value),
			"end_date": (">=", date_value),
			"docstatus": 1,
			"status": "Active",
		},
		"shift_type",
	)
	if existing_shift:
		return existing_shift
	doc = frappe.new_doc("Shift Assignment")
	doc.employee = employee
	doc.shift_type = shift
	doc.start_date = date_value
	doc.end_date = date_value
	doc.status = "Active"
	doc.insert(ignore_permissions=True)
	doc.submit()
	return shift


def _day_exception_labels(date_value, tokens, shift, status_plan):
	labels = list(status_plan["exceptions"])
	if status_plan["status"] == "Absent" and not tokens and "全天缺勤" not in labels:
		labels.append("全天缺勤")
	if status_plan["status"] in {"Absent", "On Leave"}:
		return labels
	if not tokens:
		return labels

	checkins = _checkin_plan(date_value, tokens, shift)
	shift_doc = frappe.get_doc("Shift Type", shift)
	start_dt = datetime.combine(getdate(date_value), _to_time(shift_doc.start_time))
	end_dt = datetime.combine(getdate(date_value), _to_time(shift_doc.end_time))
	if end_dt <= start_dt:
		end_dt += timedelta(days=1)
		labels.append("跨夜班")
	if len(tokens) == 1:
		labels.append("单时间点转换")
	if checkins[0][0] > start_dt:
		labels.append("迟到")
	if checkins[-1][0] < end_dt:
		labels.append("早退")
	if not labels:
		labels.append("正常出勤")
	return labels


def _create_demo_checkins(employee, date_value, tokens, shift, status_plan):
	if not tokens or status_plan["status"] in {"Absent", "On Leave"}:
		return [], 0
	checkins = _checkin_plan(date_value, tokens, shift)
	created = []
	skipped = 0
	for checkin_time, log_type in checkins:
		if frappe.db.exists("Employee Checkin", {"employee": employee, "time": checkin_time, "log_type": log_type}):
			skipped += 1
			continue
		doc = frappe.new_doc("Employee Checkin")
		doc.employee = employee
		doc.time = checkin_time
		doc.log_type = log_type
		doc.device_id = "HBOS-M1-FIX-B-MONTHLY-DEMO"
		doc.skip_auto_attendance = 0
		doc.insert(ignore_permissions=True)
		created.append(doc.name)
	return created, skipped


def _checkin_plan(date_value, tokens, shift):
	shift_doc = frappe.get_doc("Shift Type", shift)
	start_dt = datetime.combine(getdate(date_value), _to_time(shift_doc.start_time))
	end_dt = datetime.combine(getdate(date_value), _to_time(shift_doc.end_time))
	if end_dt <= start_dt:
		end_dt += timedelta(days=1)
	token_dts = [datetime.combine(getdate(date_value), token) for token in tokens]
	token_dts = [dt + timedelta(days=1) if dt < start_dt - timedelta(hours=4) else dt for dt in token_dts]
	token_dts = sorted(token_dts)
	if len(token_dts) >= 2:
		return [(token_dts[0], "IN"), (token_dts[-1], "OUT")]
	token_dt = token_dts[0]
	start_delta = abs((token_dt - start_dt).total_seconds())
	end_delta = abs((token_dt - end_dt).total_seconds())
	if start_delta <= end_delta:
		return [(token_dt, "IN"), (end_dt, "OUT")]
	return [(start_dt, "IN"), (token_dt, "OUT")]


def _to_time(value):
	if isinstance(value, timedelta):
		seconds = int(value.total_seconds()) % 86400
		return (datetime.min + timedelta(seconds=seconds)).time()
	if isinstance(value, time):
		return value
	return get_datetime(f"2000-01-01 {value}").time()


def _auto_attendance(shifts):
	for shift in set(shifts.values()):
		doc = frappe.get_doc("Shift Type", shift)
		doc.process_auto_attendance(is_manually_triggered=False)


def _fallback_attendance(records, daily_columns, shifts, leave_type):
	created = 0
	for record in records:
		employee = _find_employee(record)
		if not employee:
			continue
		for day in daily_columns:
			date_value = day["date"]
			if frappe.db.exists("Attendance", {"employee": employee, "attendance_date": date_value, "docstatus": ("<", 2)}):
				continue
			tokens = _time_tokens(" ".join(record["daily"].get(date_value, [])))
			plan = _status_for_day(record, date_value, bool(tokens))
			shift = _select_shift(tokens, shifts)
			attendance = frappe.new_doc("Attendance")
			attendance.employee = employee
			attendance.attendance_date = date_value
			attendance.status = plan["status"]
			attendance.shift = shift
			if plan["status"] == "On Leave" and leave_type:
				attendance.leave_type = leave_type
			if tokens:
				checkins = _checkin_plan(date_value, tokens, shift)
				attendance.in_time = checkins[0][0]
				attendance.out_time = checkins[-1][0]
				attendance.working_hours = max((attendance.out_time - attendance.in_time).total_seconds() / 3600, 0)
				shift_doc = frappe.get_doc("Shift Type", shift)
				start_dt = datetime.combine(getdate(date_value), _to_time(shift_doc.start_time))
				end_dt = datetime.combine(getdate(date_value), _to_time(shift_doc.end_time))
				if end_dt <= start_dt:
					end_dt += timedelta(days=1)
				attendance.late_entry = int(attendance.in_time > start_dt)
				attendance.early_exit = int(attendance.out_time < end_dt)
			attendance.insert(ignore_permissions=True)
			attendance.submit()
			created += 1
	return created


def _find_employee(record):
	employee_number = record.get("employee_number")
	if employee_number:
		return frappe.db.get_value("Employee", {"employee_number": employee_number}, "name") or frappe.db.get_value(
			"Employee", {"attendance_device_id": employee_number}, "name"
		)
	name = record.get("employee_name")
	matches = frappe.get_all("Employee", filters={"employee_name": name}, pluck="name") if name else []
	return matches[0] if len(matches) == 1 else None


def _attendance_names_for_records(records, daily_columns):
	names = []
	for record in records:
		employee = _find_employee(record)
		if not employee:
			continue
		for day in daily_columns:
			name = frappe.db.get_value(
				"Attendance",
				{"employee": employee, "attendance_date": day["date"], "docstatus": ("<", 2)},
				"name",
			)
			if name:
				names.append(name)
	return names


def _mask(value):
	if not value:
		return ""
	text = str(value)
	if len(text) <= 2:
		return "*"
	return text[:1] + "***" + text[-1:]
