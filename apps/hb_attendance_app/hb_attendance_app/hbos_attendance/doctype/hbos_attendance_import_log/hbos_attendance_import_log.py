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

from hb_attendance_app.hbos_attendance.import_contract import (
	ImportValidationError,
	MAX_IMPORT_FILE_SIZE,
	MONTHLY_SUMMARY,
	RAW_CHECKIN,
	classify_headers,
	classify_raw_day,
	validate_upload_metadata,
)


NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
TIME_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{2})")
LEGACY_DAY_SHIFT = "HBOS-M1-FIX-B-白班-0800-1600"
DEFAULT_DAY_SHIFT = "HBOS-M1-FIX-B-白班-0830-1730"
LEGACY_DEVICE_ID = "HBOS-M1-FIX-B-MONTHLY-DEMO"
DEFAULT_DEVICE_ID = "HBOS-M1-FIX-B-MONTHLY-ADAPTER"


class HBOSAttendanceImportLog(Document):
	def before_insert(self):
		if not self.run_by:
			self.run_by = frappe.session.user


@frappe.whitelist()
def preview_import(log_name=None, source_file=None):
	frappe.only_for(("System Manager", "HR Manager", "HR User"))
	path, file_name = _resolve_source(log_name=log_name, source_file=source_file)
	parsed = _parse_xlsx(path)
	log = _get_or_create_log(log_name, source_file, file_name, path)
	_apply_summary(log, parsed.preview_summary(), status="Previewed")
	log.save(ignore_permissions=True)
	frappe.db.commit()
	return {"log_name": log.name, **parsed.preview_summary()}


@frappe.whitelist()
def run_import(log_name=None, source_file=None, create_missing_employees=1, limit_rows=None):
	frappe.only_for(("System Manager", "HR Manager", "HR User"))
	path, file_name = _resolve_source(log_name=log_name, source_file=source_file)
	parsed = _parse_xlsx(path)
	log = _get_or_create_log(log_name, source_file, file_name, path)
	log.import_status = "Running"
	log.started_at = now_datetime()
	log.run_by = frappe.session.user
	log.save(ignore_permissions=True)
	frappe.db.commit()

	try:
		result = _execute_import(parsed, bool(int(create_missing_employees)), int(limit_rows or 0), log)
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


def _resolve_source(log_name=None, source_file=None):
	file_url = source_file
	if log_name and not file_url:
		file_url = frappe.db.get_value("HBOS Attendance Import Log", log_name, "source_file")

	if not file_url:
		frappe.throw("必须上传私有 .xlsx 附件")
	file_doc = frappe.get_doc("File", {"file_url": file_url})
	if not frappe.has_permission("File", "read", file_doc.name):
		frappe.throw("无权访问该导入附件", frappe.PermissionError)
	try:
		validate_upload_metadata(
			is_private=bool(file_doc.is_private), file_name=file_doc.file_name, size=file_doc.file_size
		)
	except ImportValidationError as exc:
		frappe.throw(str(exc))
	root = Path(frappe.get_site_path("private", "files")).resolve()
	path = Path(file_doc.get_full_path()).resolve()
	if root not in path.parents or not path.is_file():
		frappe.throw("附件路径不在站点私有文件目录内")
	return path, file_doc.file_name


def _get_or_create_log(log_name, source_file, file_name, path):
	if log_name:
		log = frappe.get_doc("HBOS Attendance Import Log", log_name)
	else:
		log = frappe.new_doc("HBOS Attendance Import Log")
		log.import_type = "考勤机月度导出表"
		log.import_status = "Draft"
		log.source_file = source_file
	log.source_file_name = file_name
	log.source_file_hash = _sha256(path)
	previous_count = frappe.db.count(
		"HBOS Attendance Import Log",
		{"source_file_hash": log.source_file_hash, "name": ("!=", log.name or "")},
	)
	log.same_file_import_count = previous_count + 1
	log.is_repeat_import = int(previous_count > 0)
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
		"existing_attendance",
		"skipped_duplicates",
	):
		log.set(field, int(result.get(field) or 0))
	log.auto_attendance_used = int(bool(result.get("auto_attendance_used")))
	log.fallback_used = int(bool(result.get("fallback_used")))
	log.mapping_summary = json.dumps(result.get("mapping_summary", {}), ensure_ascii=False, indent=2)
	log.exception_summary = json.dumps(result.get("exception_summary", {}), ensure_ascii=False, indent=2)
	log.failure_details = json.dumps(result.get("failure_details", []), ensure_ascii=False, indent=2)
	log.readable_summary = _readable_summary(log, result, status)
	if result.get("notes"):
		log.notes = result["notes"]


def _readable_summary(log, result, status):
	repeat_text = "是" if getattr(log, "is_repeat_import", 0) else "否"
	same_count = int(getattr(log, "same_file_import_count", 1) or 1)
	reason_parts = []
	exceptions = result.get("exception_summary") or {}
	if exceptions:
		reason_parts.append("异常口径：" + "，".join(f"{key} {value}" for key, value in exceptions.items()))
	failures = result.get("failure_details") or []
	if failures:
		reason_parts.append(f"失败 {len(failures)} 条，详见失败摘要")
	if not reason_parts:
		reason_parts.append("未发现阻断性失败")
	auto_text = "已触发 HRMS 自动考勤" if result.get("auto_attendance_used") else "未触发 HRMS 自动考勤"
	fallback_text = "本批次使用本地兜底生成补齐考勤结果；该兜底仅用于 M1 本地演示补偿，不代表正式生产口径。" if result.get("fallback_used") else "本批次未使用本地兜底生成。"
	return "\n".join(
		[
			f"批次号：{log.name or '预览批次'}",
			f"文件名：{getattr(log, 'source_file_name', '') or '未记录'}",
			f"文件 Hash：{getattr(log, 'source_file_hash', '') or '未记录'}",
			f"是否重复导入：{repeat_text}",
			f"同一文件第几次识别/导入：第 {same_count} 次",
			f"新增打卡流水：{int(result.get('created_checkins') or 0)}",
			f"跳过重复打卡流水：{int(result.get('skipped_duplicates') or 0)}",
			f"新增考勤结果：{int(result.get('created_attendance') or 0)}",
			f"已存在考勤结果：{int(result.get('existing_attendance') or 0)}",
			f"失败记录：{int(result.get('failed_rows') or 0)}",
			f"原因摘要：{'；'.join(reason_parts)}",
			auto_text,
			fallback_text,
			"本次导入未重复创建已有打卡记录，系统自动跳过已存在记录。",
			f"当前状态：{status}",
		]
	)


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
			"import_type": "考勤机月度导出表",
			"total_rows": len(self.rows),
			"matched_rows": 0,
			"success_rows": 0,
			"failed_rows": 0,
			"created_employees": 0,
			"created_checkins": 0,
			"created_attendance": 0,
			"existing_attendance": 0,
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
				"classification": "考勤机月度导出表 / 适配导入",
				"source_note": "该文件不是一行一条原始打卡流水；导入会按月度汇总表适配生成打卡流水与考勤结果。",
				"supported_routes": ["考勤机月度导出表", "逐条原始打卡流水表（后续适配）"],
				"default_shift": "白班/行政班 08:30-17:30；中班 16:00-00:00；夜班 00:00-08:00；跨夜班 20:00-04:00",
			},
			"exception_summary": {},
			"failure_details": [],
			"notes": "仅预览校验；未写入员工、打卡流水或考勤结果。",
		}


class RawCheckinWorkbook:
	def __init__(self, rows, header_index, headers, records, sheet_names):
		self.rows, self.header_index, self.headers, self.records, self.sheet_names = rows, header_index, headers, records, sheet_names
		self.daily_columns = []

	@property
	def identity_rows(self):
		return len(self.records)

	def preview_summary(self):
		dates = [record["checkin_time"].date() for record in self.records]
		return {
			"import_type": RAW_CHECKIN, "total_rows": len(self.rows), "matched_rows": 0,
			"success_rows": 0, "failed_rows": 0, "created_employees": 0,
			"created_checkins": 0, "created_attendance": 0, "existing_attendance": 0,
			"skipped_duplicates": 0, "period_start": min(dates).isoformat() if dates else None,
			"period_end": max(dates).isoformat() if dates else None,
			"auto_attendance_used": False, "fallback_used": False,
			"mapping_summary": {"sheet_names": self.sheet_names, "header_row": self.header_index + 1,
				"detected_headers": self.headers, "identity_rows": self.identity_rows,
				"classification": RAW_CHECKIN, "source_note": "逐条原始打卡事件；仅此类型可写入 Employee Checkin。"},
			"exception_summary": {}, "failure_details": [], "notes": "仅预览校验；未写入数据。",
		}


def _parse_xlsx(path):
	rows, sheet_names = _read_first_sheet(path)
	header_index = None
	import_type = None
	for index, row in enumerate(rows):
		try:
			import_type = classify_headers([cell.strip().replace("\n", " ") for cell in row])
			header_index = index
			break
		except ImportValidationError:
			continue
	if header_index is None:
		frappe.throw("未识别到受支持的 Excel 表头")

	headers = [cell.strip().replace("\n", " ") for cell in rows[header_index]]
	header_map = {header: idx for idx, header in enumerate(headers) if header}
	if import_type == RAW_CHECKIN:
		return _parse_raw_workbook(rows, header_index, headers, sheet_names)
	daily_columns = []
	for idx, header in enumerate(headers):
		match = DATE_RE.search(header)
		if match:
			year, month, day = match.groups()
			daily_columns.append({"idx": idx, "header": header, "date": getdate(f"20{year}-{month}-{day}")})

	records = _collect_identity_records(rows[header_index + 1 :], header_map, daily_columns, header_index)
	return MonthlyWorkbook(rows, header_index, headers, records, daily_columns, sheet_names)


def _parse_raw_workbook(rows, header_index, headers, sheet_names):
	lookup = {header: index for index, header in enumerate(headers) if header}
	def first_index(options):
		return next((lookup[item] for item in options if item in lookup), None)
	identifier_index = first_index(("工号", "员工工号", "employee_number", "employee_identifier"))
	time_index = first_index(("打卡时间", "checkin_time", "签到时间"))
	type_index = first_index(("打卡类型", "checkin_type", "log_type"))
	name_index, device_index, shift_index = lookup.get("姓名"), lookup.get("设备ID"), lookup.get("班次")
	records = []
	for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
		if not any(row):
			continue
		try:
			log_type = _value(row, type_index).upper()
			if log_type not in {"IN", "OUT"}:
				raise ValueError("打卡类型必须为 IN 或 OUT")
			records.append({"row": row_number, "employee_number": _value(row, identifier_index),
				"employee_name": _value(row, name_index), "checkin_time": get_datetime(_value(row, time_index)),
				"log_type": log_type, "device_id": _value(row, device_index), "shift": _value(row, shift_index)})
		except Exception as exc:
			frappe.throw(f"第 {row_number} 行原始打卡流水无效：{exc}")
	return RawCheckinWorkbook(rows, header_index, headers, records, sheet_names)


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


def _execute_import(parsed, create_missing_employees, limit_rows, log=None):
	if isinstance(parsed, MonthlyWorkbook):
		return _stage_monthly_summary(parsed, log)
	return _execute_raw_checkins(parsed, create_missing_employees, limit_rows, log)


def _stage_monthly_summary(parsed, log):
	"""月度汇总只能暂存/对账，绝不伪造逐条打卡或 Attendance。"""
	rows = [{key: value for key, value in record.items() if key != "daily"} for record in parsed.records]
	if hasattr(log, "monthly_summary_staging"):
		log.monthly_summary_staging = json.dumps({"schema_version": "M1-FIX-B2", "records": rows}, ensure_ascii=False)
	return {**parsed.preview_summary(), "matched_rows": len(rows), "success_rows": len(rows),
		"notes": "月度汇总仅已暂存用于对账/演示；未写入 Employee Checkin，未触发 Auto Attendance。"}


def _execute_raw_checkins(parsed, create_missing_employees, limit_rows, log):
	company, holiday_list = _default_company(), _default_holiday_list()
	records = parsed.records[:limit_rows] if limit_rows else parsed.records
	stats, failures, impacted, daily_types = Counter(), [], set(), defaultdict(list)
	for record in records:
		try:
			employee, created = _match_or_create_employee(record, company, holiday_list, create_missing_employees)
			stats["matched_rows"] += 1; stats["created_employees"] += int(created)
			if frappe.db.exists("Employee Checkin", {"employee": employee, "time": record["checkin_time"], "log_type": record["log_type"]}):
				stats["skipped_duplicates"] += 1
			else:
				doc = frappe.new_doc("Employee Checkin")
				doc.update({"employee": employee, "time": record["checkin_time"], "log_type": record["log_type"],
					"device_id": record["device_id"] or "HBOS-RAW-IMPORT", "skip_auto_attendance": 0})
				doc.insert(ignore_permissions=True); stats["created_checkins"] += 1
			impacted.add((employee, getdate(record["checkin_time"])))
			daily_types[(employee, getdate(record["checkin_time"]))].append(record["log_type"])
		except Exception as exc:
			stats["failed_rows"] += 1; failures.append({"row": record["row"], "reason": str(exc), "suggestion": "检查工号、员工和排班后重试"})
	for employee, date_value in impacted:
		assignment = frappe.db.get_value("Shift Assignment", {"employee": employee, "start_date": ("<=", date_value), "end_date": (">=", date_value), "docstatus": 1}, "shift_type")
		if assignment:
			frappe.get_doc("Shift Type", assignment).process_auto_attendance(is_manually_triggered=False)
			stats["auto_attendance_used"] = 1
			for attendance in frappe.get_all("Attendance", filters={"employee": employee, "attendance_date": date_value, "docstatus": ("<", 2)}, pluck="name"):
				_mark_attendance_source(attendance, log.name, "HRMS Auto Attendance")
	exceptions = Counter(classify_raw_day(types) for types in daily_types.values())
	return {**parsed.preview_summary(), "matched_rows": stats["matched_rows"],
		"success_rows": stats["matched_rows"] - stats["failed_rows"], "failed_rows": stats["failed_rows"],
		"created_employees": stats["created_employees"], "created_checkins": stats["created_checkins"],
		"skipped_duplicates": stats["skipped_duplicates"], "auto_attendance_used": bool(stats["auto_attendance_used"]),
		"fallback_used": False, "exception_summary": dict(exceptions), "failure_details": failures[:50],
		"notes": "原始流水已写入 Employee Checkin；单边打卡只标记缺卡，不合成虚假 IN/OUT；未使用本地兜底。"}


def _mark_attendance_source(attendance_name, log_name, source_type):
	if frappe.db.has_column("Attendance", "hbos_source_type"):
		frappe.db.set_value("Attendance", attendance_name, {"hbos_source_type": source_type, "hbos_import_log": log_name,
			"hbos_fallback_generated": 0, "hbos_calc_version": "M1-FIX-B2"}, update_modified=False)


def _legacy_execute_import(parsed, create_missing_employees, limit_rows, log=None):
	company = _default_company()
	holiday_list = _default_holiday_list()
	leave_type = _default_leave_type()
	shifts = _ensure_hbos_shifts(parsed, holiday_list)
	failures = []
	stats = Counter()
	exceptions = Counter()
	created_checkin_names = []
	records = parsed.records[:limit_rows] if limit_rows else parsed.records
	attendance_before = set(_attendance_names_for_records(records, parsed.daily_columns))
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
				names, skipped = _create_adapted_checkins(employee, date_value, day_tokens, assigned_shift, status_plan)
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
	attendance_after = set(_attendance_names_for_records(records, parsed.daily_columns))
	stats["created_attendance"] = len(attendance_after - attendance_before)
	stats["existing_attendance"] = len(attendance_after & attendance_before)
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
		"existing_attendance": stats["existing_attendance"],
		"skipped_duplicates": stats["skipped_duplicates"],
		"auto_attendance_used": bool(stats["auto_attendance_used"]),
		"fallback_used": bool(stats["fallback_used"]),
		"exception_summary": dict(exceptions),
		"failure_details": failures[:50],
		"notes": "由考勤机月度导出表适配生成打卡流水与考勤结果；不是逐条原始打卡流水导入。默认白班/行政班为 08:30-17:30。",
	}


def _default_company():
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		return company
	return frappe.db.get_value("Company", {"name": ("like", "%Demo%")}, "name") or frappe.get_all("Company", pluck="name")[0]


def _default_holiday_list():
	try:
		rows = frappe.db.sql("SELECT name FROM \`tabHoliday List\` WHERE name LIKE '%M1R3C%' LIMIT 1", as_dict=True)
		if rows: return rows[0].name
	except: pass
	try:
		rows = frappe.db.sql("SELECT name FROM \`tabHoliday List\` LIMIT 1", as_dict=True)
		if rows: return rows[0].name
	except: pass
	return None


def _default_leave_type():
	try:
		rows = frappe.db.sql("SELECT name FROM \`tabLeave Type\` WHERE name LIKE '%事假%' LIMIT 1", as_dict=True)
		if rows: return rows[0].name
	except: pass
	try:
		rows = frappe.db.sql("SELECT name FROM \`tabLeave Type\` LIMIT 1", as_dict=True)
		if rows: return rows[0].name
	except: pass
	return None


def _ensure_hbos_shifts(parsed, holiday_list):
	dates = [item["date"] for item in parsed.daily_columns]
	start = min(dates) if dates else getdate()
	end = max(dates) if dates else getdate()
	last_sync = get_datetime(datetime.combine(end, time(23, 59, 59)) + timedelta(days=1))
	specs = {
		"day": (DEFAULT_DAY_SHIFT, "08:30:00", "17:30:00"),
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
	_replace_legacy_day_shift(result["day"])
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
	existing_assignment = frappe.db.get_value(
		"Shift Assignment",
		{
			"employee": employee,
			"start_date": ("<=", date_value),
			"end_date": (">=", date_value),
			"docstatus": 1,
			"status": "Active",
		},
		["name", "shift_type"],
		as_dict=True,
	)
	if existing_assignment:
		if existing_assignment.shift_type == LEGACY_DAY_SHIFT and shift == DEFAULT_DAY_SHIFT:
			frappe.db.set_value("Shift Assignment", existing_assignment.name, "shift_type", DEFAULT_DAY_SHIFT)
			return DEFAULT_DAY_SHIFT
		return existing_assignment.shift_type
	doc = frappe.new_doc("Shift Assignment")
	doc.employee = employee
	doc.shift_type = shift
	doc.start_date = date_value
	doc.end_date = date_value
	doc.status = "Active"
	doc.insert(ignore_permissions=True)
	doc.submit()
	return shift


def _replace_legacy_day_shift(new_shift):
	if not frappe.db.exists("Shift Type", LEGACY_DAY_SHIFT):
		return
	for doctype, fieldname in (
		("Shift Assignment", "shift_type"),
		("Attendance", "shift"),
		("Employee Checkin", "shift"),
	):
		if not frappe.db.has_column(doctype, fieldname):
			continue
		for row in frappe.get_all(doctype, filters={fieldname: LEGACY_DAY_SHIFT}, pluck="name"):
			frappe.db.set_value(doctype, row, fieldname, new_shift, update_modified=False)
	for row in frappe.get_all("Employee Checkin", filters={"device_id": LEGACY_DEVICE_ID}, pluck="name"):
		frappe.db.set_value("Employee Checkin", row, "device_id", DEFAULT_DEVICE_ID, update_modified=False)


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


def _create_adapted_checkins(employee, date_value, tokens, shift, status_plan):
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
		doc.device_id = DEFAULT_DEVICE_ID
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
