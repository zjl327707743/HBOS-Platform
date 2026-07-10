import unittest
from datetime import date, time

from hb_attendance_app.hbos_attendance.import_contract import (
	ImportValidationError,
	MAX_IMPORT_FILE_SIZE,
	MONTHLY_SUMMARY,
	RAW_CHECKIN,
	classify_headers,
	classify_no_checkin_day,
	classify_raw_day,
	select_shift_key,
	shift_window,
	validate_upload_metadata,
)


class ImportContractTest(unittest.TestCase):
	def test_raw_checkin_headers_are_not_monthly_summary(self):
		self.assertEqual(classify_headers(["工号", "打卡时间", "打卡类型"]), RAW_CHECKIN)

	def test_monthly_summary_headers_are_not_raw_checkins(self):
		self.assertEqual(
			classify_headers(["姓名", "工号", "部门", "应出勤天数", "周三 26-07-01"]),
			MONTHLY_SUMMARY,
		)

	def test_public_non_xlsx_and_oversized_uploads_are_rejected(self):
		for is_private, file_name, size in (
			(False, "打卡.xlsx", 1),
			(True, "打卡.csv", 1),
			(True, "打卡.xlsx", MAX_IMPORT_FILE_SIZE + 1),
		):
			with self.assertRaises(ImportValidationError):
				validate_upload_metadata(is_private=is_private, file_name=file_name, size=size)

	def test_night_shift_boundaries_are_not_misclassified_as_cross_day(self):
		self.assertEqual(select_shift_key(time(0, 0)), "night")
		self.assertEqual(select_shift_key(time(3, 59)), "night")
		self.assertEqual(select_shift_key(time(4, 0)), "night")
		self.assertEqual(select_shift_key(time(8, 0)), "day")
		self.assertEqual(select_shift_key(time(16, 0)), "middle")
		self.assertEqual(select_shift_key(time(23, 59)), "middle")

	def test_explicit_assignment_wins_over_time_guess(self):
		self.assertEqual(select_shift_key(time(9, 0), assigned_shift="行政班"), "行政班")

	def test_middle_shift_window_crosses_midnight_but_night_does_not(self):
		middle_start, middle_end = shift_window(date(2026, 7, 1), time(16), time(0))
		night_start, night_end = shift_window(date(2026, 7, 1), time(0), time(8))
		self.assertEqual((middle_end - middle_start).total_seconds(), 8 * 3600)
		self.assertEqual((night_end - night_start).total_seconds(), 8 * 3600)
		self.assertEqual(night_end.date(), date(2026, 7, 1))

	def test_single_raw_checkin_is_missing_card_not_synthesized_pair(self):
		self.assertEqual(classify_raw_day(["IN"]), "上班缺卡")
		self.assertEqual(classify_raw_day(["OUT"]), "下班缺卡")

	def test_no_checkin_precedence_is_leave_then_holiday_then_assignment_then_absent(self):
		self.assertEqual(classify_no_checkin_day(has_leave=True, is_holiday=True, has_shift=True), "请假")
		self.assertEqual(classify_no_checkin_day(has_leave=False, is_holiday=True, has_shift=True), "休息日/节假日")
		self.assertEqual(classify_no_checkin_day(has_leave=False, is_holiday=False, has_shift=False), "未排班")
		self.assertEqual(classify_no_checkin_day(has_leave=False, is_holiday=False, has_shift=True), "缺勤")


if __name__ == "__main__":
	unittest.main()
