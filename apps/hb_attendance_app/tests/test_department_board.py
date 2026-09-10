import unittest
from datetime import datetime, date
from pathlib import Path

from hb_attendance_app.hbos_attendance.department_board import (
    resolve_expected, live_state, day_review,
)

DATA_PY = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/department_board_data.py"
WS_JSON = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/workspace/海滨考勤工作台/海滨考勤工作台.json"


def profile(**kw):
    base = {
        "num": "1", "exempt": False, "admin_list": False, "food": False,
        "safety": False, "rotate_label": None,
        "bound": False, "bound_shift_type": None, "bound_start": None, "bound_late": None,
        "schedule": None, "leave_record": False, "leave_record_type": None,
    }
    base.update(kw)
    return base


class ResolveExpectedTest(unittest.TestCase):
    def test_schedule_rest_wins(self):
        p = profile(schedule={"kind": "rest", "shift_type": "休息",
                              "start_time": None, "late_after": None, "leave_type": None})
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "rest")
        self.assertEqual(e["label"], "休息")

    def test_schedule_leave(self):
        p = profile(schedule={"kind": "leave", "shift_type": None,
                              "start_time": None, "late_after": None, "leave_type": "年假"})
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "leave")

    def test_schedule_shift_beats_bound(self):
        p = profile(
            schedule={"kind": "shift", "shift_type": "行政班",
                      "start_time": "08:30", "late_after": "08:31", "leave_type": None},
            bound=True, bound_shift_type="早班", bound_start="08:00", bound_late="08:01",
        )
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "shift")
        self.assertEqual(e["shift_type"], "行政班")
        self.assertEqual(e["start_time"], "08:30")
        self.assertEqual(e["late_after"], "08:31")

    def test_exempt_priority(self):
        p = profile(exempt=True,
                    schedule={"kind": "shift", "shift_type": "早班",
                              "start_time": "08:00", "late_after": "08:01", "leave_type": None})
        e = resolve_expected(p, weekday=0)
        self.assertEqual(e["kind"], "exempt")

    def test_bound_fallback(self):
        e = resolve_expected(profile(bound=True, bound_shift_type="早班",
                                     bound_start="08:00", bound_late="08:01"), weekday=3)
        self.assertEqual(e["kind"], "shift")
        self.assertEqual(e["shift_type"], "早班")
        self.assertEqual(e["start_time"], "08:00")

    def test_admin_weekday_vs_weekend(self):
        e = resolve_expected(profile(admin_list=True), weekday=3)
        self.assertEqual(e["kind"], "shift")
        self.assertEqual(e["start_time"], "08:30")
        self.assertEqual(e["late_after"], "08:31")
        e_we = resolve_expected(profile(admin_list=True), weekday=6)
        self.assertEqual(e_we["kind"], "rest")

    def test_food_fact_only(self):
        e = resolve_expected(profile(food=True), weekday=2)
        self.assertEqual(e["kind"], "shift")
        self.assertIsNone(e["start_time"])
        self.assertEqual(e["label"], "食堂")

    def test_safety_and_rotate_undetermined(self):
        e = resolve_expected(profile(safety=True), weekday=1)
        self.assertIsNone(e["start_time"])
        self.assertEqual(e["label"], "安全倒班")
        e2 = resolve_expected(profile(rotate_label="四班次倒班"), weekday=1)
        self.assertIsNone(e2["start_time"])
        self.assertEqual(e2["label"], "四班次倒班")

    def test_unknown(self):
        e = resolve_expected(profile(), weekday=0)
        self.assertEqual(e["kind"], "unknown")
        self.assertEqual(e["label"], "在册待确认")

    def test_general_rotate_label_fact_only(self):
        """数据层兜底：无排班/绑定/名单命中者 rotate_label=通用倒班 →
        kind=shift、无起算点 → 只报打卡事实、计入应出勤。"""
        e = resolve_expected(profile(rotate_label="通用倒班"), weekday=1)
        self.assertEqual(e["kind"], "shift")
        self.assertIsNone(e["start_time"])
        self.assertIsNone(e["late_after"])
        self.assertEqual(e["label"], "通用倒班")


class LiveStateTest(unittest.TestCase):
    def _day(self):
        return datetime(2026, 9, 8)  # 周二

    def test_leave_record_no_card(self):
        p = profile(leave_record=True, leave_record_type="事假",
                    schedule={"kind": "shift", "shift_type": "行政班",
                              "start_time": "08:30", "late_after": "08:31", "leave_type": None})
        e = resolve_expected(p, weekday=1)
        st = live_state(e, p, [], datetime(2026, 9, 8, 10, 0))
        self.assertEqual(st["state"], "leave")
        self.assertIn("事假", st["label"])

    def test_leave_record_but_clocked_is_present(self):
        p = profile(leave_record=True, leave_record_type="病假",
                    schedule={"kind": "shift", "shift_type": "行政班",
                              "start_time": "08:30", "late_after": "08:31", "leave_type": None})
        e = resolve_expected(p, weekday=1)
        # 8:25 在入窗点(04:30)之后、迟到点(08:31)之前 → 出勤非迟到
        ev = [datetime(2026, 9, 8, 8, 25)]
        st = live_state(e, p, ev, datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "present")
        self.assertEqual(st["first_hm"], "08:25")

    def test_before_start(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [], datetime(2026, 9, 8, 7, 0))
        self.assertEqual(st["state"], "before_start")

    def test_pending_between_start_and_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        # 08:30:30 在上班点(08:30)之后、迟到点(08:31)之前 → 未打卡待判定
        st = live_state(e, profile(), [], datetime(2026, 9, 8, 8, 30, 30))
        self.assertEqual(st["state"], "pending")

    def test_absent_expected_after_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "absent_expected")
        self.assertTrue(st["note"])

    def test_present_not_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [datetime(2026, 9, 8, 8, 20)], datetime(2026, 9, 8, 9, 0))
        self.assertEqual(st["state"], "present")
        self.assertEqual(st["tags"], [])

    def test_late(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        st = live_state(e, profile(), [datetime(2026, 9, 8, 8, 45)], datetime(2026, 9, 8, 9, 0))
        self.assertEqual(st["state"], "late")
        self.assertIn("迟到", st["tags"])

    def test_offwindow_card_not_absent(self):
        e = {"kind": "shift", "shift_type": "行政班", "start_time": "08:30",
             "late_after": "08:31", "label": "行政班"}
        # 只有 00:30 一张卡（入窗点 04:30 之前），不应判「未打卡」
        st = live_state(e, profile(), [datetime(2026, 9, 8, 0, 30)], datetime(2026, 9, 8, 9, 0))
        self.assertIn(st["state"], ("present_offwindow",))
        self.assertFalse(st["tags"])

    def test_fact_only(self):
        e = {"kind": "shift", "shift_type": None, "start_time": None, "late_after": None,
             "label": "食堂"}
        st = live_state(e, profile(food=True), [datetime(2026, 9, 8, 10, 0)],
                        datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "fact_present")
        st2 = live_state(e, profile(food=True), [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st2["state"], "fact_none")

    def test_rest_leave_exempt_unknown(self):
        self.assertEqual(live_state({"kind": "rest", "label": "休息"}, profile(),
                                    [], datetime(2026, 9, 8, 12, 0))["state"], "rest")
        self.assertEqual(live_state({"kind": "exempt", "label": "豁免"}, profile(),
                                    [], datetime(2026, 9, 8, 12, 0))["state"], "exempt")
        self.assertEqual(live_state({"kind": "unknown", "label": "在册待确认"}, profile(),
                                    [], datetime(2026, 9, 8, 12, 0))["state"], "unknown")

    def test_unknown_with_leave_record_is_leave(self):
        """无排班/绑定/名单命中（kind=unknown）但有已通过请假记录 →
        不得被 unknown 短路，显示请假并带请假类型。"""
        p = profile(leave_record=True, leave_record_type="病假")
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "unknown")
        st = live_state(e, p, [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "leave")
        self.assertIn("病假", st["label"])

    def test_rest_still_beats_leave_record(self):
        """豁免/休息优先级保留：排班休息 + 有请假记录 → 仍显示休息。"""
        p = profile(leave_record=True, leave_record_type="事假",
                    schedule={"kind": "rest", "shift_type": "休息",
                              "start_time": None, "late_after": None, "leave_type": None})
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "rest")
        st = live_state(e, p, [], datetime(2026, 9, 8, 12, 0))
        self.assertEqual(st["state"], "rest")
        self.assertNotEqual(st["state"], "leave")


class DayReviewTest(unittest.TestCase):
    def test_no_attendance_shift_without_events_no_pair(self):
        p = profile(schedule={"kind": "shift", "shift_type": "行政班",
                              "start_time": "08:30", "late_after": "08:31", "leave_type": None})
        e = resolve_expected(p, weekday=1)
        st = day_review(e, p, [], datetime(2026, 9, 8, 23, 59))
        self.assertEqual(st["state"], "no_pair")
        self.assertFalse(st["tags"])  # 不判缺勤

    def test_unknown_with_leave_record_is_leave(self):
        """回顾模式同构：kind=unknown + 已通过请假记录 → 显示请假（含类型）。"""
        p = profile(leave_record=True, leave_record_type="病假")
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "unknown")
        st = day_review(e, p, [], datetime(2026, 9, 8, 23, 59))
        self.assertEqual(st["state"], "leave")
        self.assertIn("病假", st["label"])

    def test_rest_still_beats_leave_record(self):
        """回顾模式：排班休息 + 有请假记录 → 仍显示休息。"""
        p = profile(leave_record=True, leave_record_type="事假",
                    schedule={"kind": "rest", "shift_type": "休息",
                              "start_time": None, "late_after": None, "leave_type": None})
        e = resolve_expected(p, weekday=1)
        self.assertEqual(e["kind"], "rest")
        st = day_review(e, p, [], datetime(2026, 9, 8, 23, 59))
        self.assertEqual(st["state"], "rest")


class DataLayerContractTest(unittest.TestCase):
    """数据层 get_data 依赖 frappe 运行态，测试按仓库惯例用文件内容校验契约。"""

    def test_data_module_whitelists_get_data(self):
        content = DATA_PY.read_text()
        self.assertIn("@frappe.whitelist()", content)
        self.assertIn("def get_data(department=None, date_str=None)", content)
        self.assertIn('frappe.throw("不能查看未来日期")', content)
        # 复用名单/班次常量，不内联复制
        self.assertIn("from hb_attendance_app.hbos_attendance.rule_lists import", content)
        self.assertIn("from hb_attendance_app.hbos_attendance.shift_rules import BUILTIN_SHIFTS", content)
        self.assertIn("live_state", content)
        self.assertIn("day_review", content)
        self.assertIn("resolve_expected", content)

    def test_aggregate_rate_and_contract(self):
        content = DATA_PY.read_text()
        self.assertIn('"kind": exp["kind"]', content)
        self.assertIn("_PRESENT_STATES", content)
        self.assertIn("attendance=attendance.get", content)
        self.assertIn("ORDER BY employee, time", content)
        self.assertIn("FOUR_SHIFT_NUMS, SPECIAL_SHIFT_NUMS", content)

    def test_role_gate_tz_plus8_and_general_rotate_fallback(self):
        """整分支审查拍板：API 角色门禁、时区 +8、通用倒班兜底入应出勤。"""
        content = DATA_PY.read_text()
        # get_data 与 live_sync 两处均需门禁
        self.assertGreaterEqual(content.count("frappe.only_for"), 2)
        self.assertIn("TZ_PLUS8", content)
        self.assertIn('timezone(timedelta(hours=8))', content)
        # 通用倒班兜底：非名单命中的无排班员工计入应出勤分母
        self.assertIn("通用倒班", content)
        self.assertIn('_rotating_label(ROTATE_SYSTEM, num) or "通用倒班"', content)


class LiveSyncContractTest(unittest.TestCase):
    """live_sync 手动同步端点契约：frappe 运行态函数，测试用文件内容校验。"""

    def test_live_sync_throttle_present(self):
        content = DATA_PY.read_text()
        self.assertIn("def live_sync()", content)
        self.assertIn("sync_delicloud_checkin", content)
        self.assertIn("120", content)  # 节流秒数


class FrontendContractTest(unittest.TestCase):
    """前端 Page JS/JSON 与工作台 workspace 契约：仅文件文本断言，不 import 运行态模块。"""

    def test_page_js_has_controls_and_endpoints(self):
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertIn('frappe.pages["hbos-department-board"]', js)
        self.assertIn("db-dept", js)
        self.assertIn("db-date", js)
        self.assertIn("db-autorefresh", js)
        self.assertIn("db-only-attention", js)
        self.assertIn("db-sync", js)
        self.assertIn("get_data", js)
        self.assertIn("live_sync", js)
        self.assertIn("visibilityState", js)

    def test_page_js_overview_first_layout(self):
        """整洁化改版：概览优先 + 展开式明细，取代「每部门一张卡片堆叠」。"""
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertIn("db-dept-row", js)          # 部门汇总行（可点击展开）
        self.assertIn("db-detail", js)            # 内联展开的人员明细
        self.assertIn("tabular-nums", js)         # 数字列对齐可读
        self.assertNotIn("db-dept-card", js)      # 旧的多卡片堆叠已移除
        # 轮询静默刷新：自动刷新不再整屏 spinner，且保留展开状态
        self.assertIn("openDepts", js)
        self.assertIn("silent", js)

    def test_kpi_splits_absent_from_no_record(self):
        """缺勤（已定性）与无打卡记录（未知）必须是两张分开的卡片，不得混在一张里。"""
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        self.assertNotIn("未打卡/无考勤", js)
        self.assertIn('"无打卡记录"', js)
        self.assertIn('"缺勤"', js)
        self.assertIn("s.absent", js)             # 缺勤独立计数
        self.assertIn('r.state === "absent_day"', js)   # 仅已定性的缺勤计入缺勤

    def test_page_json_and_folder_named(self):
        folder = Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board"
        self.assertTrue((folder / "hbos_department_board.json").exists())
        self.assertTrue((folder / "department_board_data.py").exists())
        content = (folder / "hbos_department_board.json").read_text()
        self.assertIn('"name": "hbos-department-board"', content)

    def test_workspace_json_link_and_shortcut(self):
        content = WS_JSON.read_text()
        self.assertIn('"label": "部门看板"', content)
        self.assertIn('"link_to": "hbos-department-board"', content)

    def test_color_for_review_fix(self):
        """配色：红=late/absent_day（确凿）；绿=present/out_day/fact_present；
        absent_expected（未打卡不定性）落琥珀默认，不得进红分支。"""
        js = (Path(__file__).parents[1] / "hb_attendance_app/hbos_attendance/page/hbos_department_board/hbos_department_board.js").read_text()
        red_line = next(l for l in js.splitlines() if 'return "s-red"' in l)
        self.assertIn('"late"', red_line)
        self.assertIn('"absent_day"', red_line)
        self.assertNotIn("absent_expected", red_line)
        green_line = next(l for l in js.splitlines() if 'return "s-green"' in l)
        self.assertIn('"present"', green_line)
        self.assertIn('"out_day"', green_line)
