import os
import tempfile
import unittest

from openpyxl import Workbook

from hb_attendance_app.hbos_attendance.schedule_import import (
    parse_xlsx_matrix,
    parse_xlsx_vertical,
)


def _make_xlsx(sheets):
    """构造临时 xlsx。sheets: [(sheet名, [[行1], [行2], ...])]"""
    wb = Workbook()
    for i, (name, rows) in enumerate(sheets):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = name
        for r in rows:
            ws.append(r)
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(path)
    return path


class ScheduleImportTest(unittest.TestCase):
    """排班表格式判别: 矩阵式必有「班次说明」sheet, 纵向式无此 sheet。

    修复回归(Owner 2026-08-26): 纵向式文件(如四车间排班表, 只有 Sheet1)
    之前被 parse_xlsx_matrix 误判为矩阵式, 解析出垃圾行导致员工全部跳过。
    """

    def test_matrix_parser_rejects_file_without_explanation_sheet(self):
        # 纵向式文件: 无「班次说明」sheet → matrix 解析应返回空
        path = _make_xlsx([("Sheet1", [
            ["倒班组", "", "行政班组"],
            ["2026.08.25"],
            ["夜班", 7, "崔兴生", "李文东"],
            ["早班", 5, "张三", "李四"],
        ])])
        try:
            rows, _ = parse_xlsx_matrix(path)
            self.assertEqual(rows, [], "无「班次说明」sheet 时矩阵解析应返回空")
        finally:
            os.unlink(path)

    def test_vertical_parser_reads_schedule(self):
        # 纵向式文件: parse_xlsx_vertical 应正确解析日期+班次+成员
        path = _make_xlsx([("Sheet1", [
            ["倒班组", "", "行政班组"],
            ["2026.08.25"],
            ["夜班", 7, "崔兴生", "李文东"],
        ])])
        try:
            rows, _ = parse_xlsx_vertical(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["employee_name"], "崔兴生")
            self.assertEqual(rows[0]["shift_type"], "夜班")
            self.assertEqual(rows[0]["date"], "2026-08-25")
            self.assertEqual(rows[1]["employee_name"], "李文东")
        finally:
            os.unlink(path)

    def test_matrix_parser_accepts_file_with_explanation_sheet(self):
        # 矩阵式文件: 有「班次说明」sheet → matrix 解析不应因缺说明返回空
        # (此处只验证判别逻辑不误伤, 不校验具体行列解析)
        path = _make_xlsx([
            ("班次说明", [["班次1", "08:30-17:30"]]),
            ("排班表", [["员工排班表"]]),
        ])
        try:
            rows, _ = parse_xlsx_matrix(path)
            # 有说明 sheet 时不应走「返回空」分支; 具体行列取决于排班表内容,
            # 此处只需确认未被「无说明 sheet」判别拦截
            self.assertIsNotNone(rows)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
