"""不依赖 Frappe 的导入安全与考勤判定契约。"""

from datetime import datetime, time, timedelta


RAW_CHECKIN = "逐条原始打卡流水表"
MONTHLY_SUMMARY = "考勤机月度导出表"
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024

RAW_TIME_HEADERS = {"打卡时间", "checkin_time", "签到时间"}
RAW_TYPE_HEADERS = {"打卡类型", "checkin_type", "log_type"}
IDENTIFIER_HEADERS = {"工号", "员工工号", "employee_number", "employee_identifier"}
MONTHLY_HEADERS = {"应出勤天数", "实际出勤天数", "请假时长(小时)", "旷工天数"}


class ImportValidationError(ValueError):
	"""导入文件或格式不满足安全/业务契约。"""


def validate_upload_metadata(*, is_private, file_name, size):
	if not is_private:
		raise ImportValidationError("只允许导入私有附件")
	if not file_name or not file_name.lower().endswith(".xlsx"):
		raise ImportValidationError("只允许导入 .xlsx 文件")
	if size is None or int(size) < 1 or int(size) > MAX_IMPORT_FILE_SIZE:
		raise ImportValidationError(f"导入文件必须大于 0 且不超过 {MAX_IMPORT_FILE_SIZE // 1024 // 1024}MB")


def classify_headers(headers):
	normalized = {str(header).strip() for header in headers if str(header).strip()}
	if normalized & RAW_TIME_HEADERS and normalized & RAW_TYPE_HEADERS and normalized & IDENTIFIER_HEADERS:
		return RAW_CHECKIN
	if {"姓名", "工号", "部门"}.issubset(normalized) and (
		normalized & MONTHLY_HEADERS or any("-" in header for header in normalized)
	):
		return MONTHLY_SUMMARY
	raise ImportValidationError("未识别到受支持的原始打卡流水表或月度汇总表表头")


def select_shift_key(checkin_time, assigned_shift=None):
	"""优先使用明确排班；无排班时仅作保守的自然日时间推断。"""
	if assigned_shift:
		return assigned_shift
	if time(0, 0) <= checkin_time < time(8, 0):
		return "night"
	if time(16, 0) <= checkin_time <= time(23, 59, 59):
		return "middle"
	return "day"


def shift_window(attendance_date, start_time, end_time):
	start = datetime.combine(attendance_date, start_time)
	end = datetime.combine(attendance_date, end_time)
	if end <= start:
		end += timedelta(days=1)
	return start, end


def classify_raw_day(log_types):
	types = {str(item).upper() for item in log_types if item}
	if "IN" in types and "OUT" in types:
		return "完整打卡"
	if "IN" in types:
		return "上班缺卡"
	if "OUT" in types:
		return "下班缺卡"
	return "无打卡"


def classify_no_checkin_day(*, has_leave, is_holiday, has_shift):
	if has_leave:
		return "请假"
	if is_holiday:
		return "休息日/节假日"
	if not has_shift:
		return "未排班"
	return "缺勤"
