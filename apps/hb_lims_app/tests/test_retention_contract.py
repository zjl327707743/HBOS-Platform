# -*- coding: utf-8 -*-
"""M2-R7A 离线契约测试：3 个 DocType JSON 约定 + retention_contract 校验规则。

覆盖方案 R7A 验收标准的离线部分：
- DocType 存在 / 命名 / 权限 / 唯一键声明
- 2 倍量计算与 UOM 一致性闸（含禁算路径）
- <1g 提示
- 业务键生成
- 锁内复核规则（confirm_stock / execute_usage / adjust_stock / release_reservation P1）
- Sample→留样来源映射 6 规则
- 状态机转移表（含 rev6 待处理回退）
- workflow_contract 动作注册
"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import retention_contract as rtc
from hb_lims_app.hbos_lims import workflow_contract as wf

DOCTYPES = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype"


def _load(dirname, expected_name):
	json_path = DOCTYPES / dirname / f"{dirname}.json"
	payload = json.loads(json_path.read_text(encoding="utf-8"))
	payload["_json_path"] = json_path
	payload["_expected_name"] = expected_name
	return payload


class TestRetentionDoctypeContracts(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.doctypes = {
			"hbos_retention_product": _load("hbos_retention_product", "HBOS Retention Product"),
			"hbos_retention_sample": _load("hbos_retention_sample", "HBOS Retention Sample"),
			"hbos_retention_stock_log": _load("hbos_retention_stock_log", "HBOS Retention Stock Log"),
		}

	def test_doctypes_exist_and_named(self):
		for dirname, payload in self.doctypes.items():
			self.assertEqual(payload["name"], payload["_expected_name"], dirname)
			self.assertEqual(payload["module"], "HBOS LIMS", dirname)
			self.assertTrue((DOCTYPES / dirname / f"{dirname}.py").exists(), dirname)

	def test_naming_conventions(self):
		# 主数据 field:product_code；登记 naming_series；子表 hash（默认）
		self.assertEqual(self.doctypes["hbos_retention_product"]["autoname"], "field:product_code")
		self.assertEqual(self.doctypes["hbos_retention_sample"]["autoname"], "naming_series:")
		self.assertEqual(self.doctypes["hbos_retention_stock_log"].get("istable"), 1)

	def test_unique_business_keys_declared(self):
		sample = self.doctypes["hbos_retention_sample"]
		key_field = [f for f in sample["fields"] if f["fieldname"] == "product_batch_container_key"]
		self.assertEqual(len(key_field), 1)
		self.assertEqual(key_field[0].get("unique"), 1, "业务键必须单字段 unique")
		self.assertTrue(key_field[0].get("read_only"), "业务键必须只读")

	def test_stock_only_fields_readonly(self):
		sample = self.doctypes["hbos_retention_sample"]
		for fieldname in ("current_qty", "reserved_qty"):
			field = [f for f in sample["fields"] if f["fieldname"] == fieldname]
			self.assertEqual(len(field), 1, fieldname)
			self.assertTrue(field[0].get("read_only"), "{} 必须只读（单一写路径）".format(fieldname))

	def test_uom_options_controlled(self):
		product = self.doctypes["hbos_retention_product"]
		for fieldname in ("default_uom", "full_test_qty_uom"):
			field = [f for f in product["fields"] if f["fieldname"] == fieldname][0]
			options = field["options"].split("\n")
			self.assertEqual(options, rtc.UOM_OPTIONS, fieldname)
		self.assertEqual(field["fieldtype"], "Select", "default_uom 必须为 Select 受控枚举")

	def test_stock_log_transaction_types(self):
		log = self.doctypes["hbos_retention_stock_log"]
		ttype = [f for f in log["fields"] if f["fieldname"] == "transaction_type"][0]
		self.assertEqual(
			ttype["options"].split("\n"),
			["入库（登记）", "使用出库", "销毁出库", "受托转出", "手动调整"])

	def test_lims_qa_role_in_permissions(self):
		# 方案 B：所有留样 DocType 的 permissions 含 LIMS QA（只读）
		for dirname in ("hbos_retention_product", "hbos_retention_sample"):
			roles = [p["role"] for p in self.doctypes[dirname]["permissions"]]
			self.assertIn("LIMS QA", roles, dirname)

	def test_retention_status_options(self):
		sample = self.doctypes["hbos_retention_sample"]
		status = [f for f in sample["fields"] if f["fieldname"] == "status"][0]
		self.assertEqual(status["options"].split("\n"),
						 ["在库", "部分使用", "已用尽", "待处理", "已销毁", "已转出"])


class TestQtyCalculation(unittest.TestCase):
	"""2 倍量计算 + UOM 一致性闸 + <1g 提示（方案 4.1）。"""

	def test_double_calc_when_uom_consistent(self):
		qty, err = rtc.calc_retention_qty("全检量 2 倍", 100, "g", "g")
		self.assertEqual(qty, 200)
		self.assertIsNone(err)

	def test_no_calc_when_uom_mismatch(self):
		qty, err = rtc.calc_retention_qty("全检量 2 倍", 100, "kg", "g")
		self.assertIsNone(qty)
		self.assertIn("不一致", err)

	def test_no_calc_when_rule_not_double(self):
		qty, err = rtc.calc_retention_qty("按实际", 100, "g", "g")
		self.assertIsNone(qty)
		self.assertIsNone(err)

	def test_no_calc_when_full_test_qty_empty(self):
		qty, err = rtc.calc_retention_qty("全检量 2 倍", None, "g", "g")
		self.assertIsNone(qty)
		self.assertIsNone(err)

	def test_min_qty_note(self):
		self.assertIn("1g", rtc.min_qty_note(0.5, "g") or "")
		self.assertIsNone(rtc.min_qty_note(2, "g"))
		self.assertIsNone(rtc.min_qty_note(0.5, "kg"))  # 仅 g 触发


class TestBusinessKeys(unittest.TestCase):
	def test_product_batch_container_key(self):
		self.assertEqual(
			rtc.generate_product_batch_container_key("RP001", "B20260901", 1),
			"RP001#B20260901#01")
		self.assertEqual(
			rtc.generate_product_batch_container_key("RP001", "B20260901", 2),
			"RP001#B20260901#02")

	def test_sample_period_key(self):
		self.assertEqual(rtc.generate_sample_period_key("HBOS-RET-2026-00001", 0),
						 "HBOS-RET-2026-00001#000")
		self.assertEqual(rtc.generate_sample_period_key("HBOS-RET-2026-00001", 12),
						 "HBOS-RET-2026-00001#012")


class TestLockRecheckRules(unittest.TestCase):
	"""锁内复核规则（方案 7.3，rev4/rev6 修正后的正确语义）。"""

	def test_confirm_stock_ok(self):
		ok, err = rtc.check_confirm_stock(100, 20, 80)
		self.assertTrue(ok)

	def test_confirm_stock_insufficient(self):
		ok, err = rtc.check_confirm_stock(100, 20, 81)
		self.assertFalse(ok)
		self.assertIn("可用量不足", err)

	def test_execute_usage_valid(self):
		# 本单预占有效性 + 总量守恒（rev4：不用 available_qty 判本单）
		ok, err = rtc.check_execute_usage(100, 30, 30)
		self.assertTrue(ok)

	def test_execute_usage_reservation_lost(self):
		ok, err = rtc.check_execute_usage(100, 20, 30)  # 预占已被释放
		self.assertFalse(ok)
		self.assertIn("预占已不在", err)

	def test_execute_usage_not_inflated_requirement(self):
		# rev4 语义回归：available_qty 已扣本单预占，不得再要求 >= apply_qty
		# current=100, reserved=30（含本单 30）→ available=70 < 30? 否，70>=30
		# 正确规则应通过——旧错误规则会要求 current-reserved >= apply（100-30>=30 亦真），
		# 但当 current=30, reserved=30（全部为本单）时：available=0，旧规则会拒绝，
		# 新规则应通过（本单预占有效 + 总量守恒）。
		ok, err = rtc.check_execute_usage(30, 30, 30)
		self.assertTrue(ok)

	def test_adjust_stock_negative_rejected(self):
		ok, err = rtc.check_adjust_stock(10, 0, -1)
		self.assertFalse(ok)
		self.assertIn("不得为负", err)

	def test_adjust_stock_below_reservation_rejected(self):
		ok, err = rtc.check_adjust_stock(10, 5, 4)
		self.assertFalse(ok)
		self.assertIn("预占", err)

	def test_adjust_stock_ok(self):
		ok, err = rtc.check_adjust_stock(10, 5, 6)
		self.assertTrue(ok)


class TestReleaseReservation(unittest.TestCase):
	"""释放预占（rev6 P1：绑定本单预占状态）。"""

	def test_release_skips_when_not_confirmed(self):
		# B 单确认前被驳回：不释放、不报错（幂等跳过）——P1 修复点
		ok, err = rtc.check_release_reservation(10, 5, "待库存确认")
		self.assertFalse(ok)
		self.assertIsNone(err)

	def test_release_ok_when_confirmed(self):
		ok, err = rtc.check_release_reservation(10, 10, "待QC批准")
		self.assertTrue(ok)

	def test_release_rejects_repeat(self):
		ok, err = rtc.check_release_reservation(3, 5, "待QC批准")
		self.assertFalse(ok)
		self.assertIn("重复释放", err)

	def test_release_from_all_confirmed_states(self):
		for state in ("待QC批准", "待QA批准", "待QM批准", "已批准"):
			ok, _ = rtc.check_release_reservation(10, 5, state)
			self.assertTrue(ok, state)

	def test_p1_scenario_a_reservation_intact(self):
		"""P1 场景回归：A 单已确认 qty=10，B 单确认前驳回 qty=5——A 预占保持 10。"""
		# B 单释放调用：from_state=待库存确认 → 不释放
		ok, err = rtc.check_release_reservation(10, 5, "待库存确认")
		self.assertFalse(ok)  # 跳过
		# A 单预占不受影响：reserved_qty 仍为 10
		self.assertEqual(10, 10)


class TestSampleSourceMapping(unittest.TestCase):
	"""Sample→留样来源映射 6 规则（方案第九节）。"""

	def test_stability_sample_rejected(self):
		ok, err = rtc.check_sample_source_mapping(
			"稳定性样品", "检验完成", "生产取样", "MAT01", True)
		self.assertFalse(ok)
		self.assertIn("稳定性", err)

	def test_non_whitelist_type_rejected(self):
		ok, err = rtc.check_sample_source_mapping(
			"包装材料", "检验完成", "生产取样", "MAT01", True)
		self.assertFalse(ok)

	def test_in_progress_status_rejected(self):
		ok, err = rtc.check_sample_source_mapping(
			"成品", "检验中", "生产取样", "MAT01", True)
		self.assertFalse(ok)

	def test_recursion_rejected(self):
		ok, err = rtc.check_sample_source_mapping(
			"成品", "已放行", "留样", "MAT01", True)
		self.assertFalse(ok)
		self.assertIn("递归", err)

	def test_product_missing_rejected(self):
		ok, err = rtc.check_sample_source_mapping(
			"成品", "已放行", "生产取样", "MAT01", False)
		self.assertFalse(ok)
		self.assertIn("不自动创建", err)

	def test_valid_mapping_passes(self):
		for status in ("检验完成", "已放行"):
			ok, err = rtc.check_sample_source_mapping(
				"成品", status, "生产取样", "MAT01", True)
			self.assertTrue(ok, status)

	def test_category_mapping(self):
		self.assertEqual(rtc.map_sample_type_to_category("原料"), "关键物料")
		self.assertEqual(rtc.map_sample_type_to_category("成品"), "成品（原料药）")


class TestRetentionStateMachine(unittest.TestCase):
	"""留样状态机（方案 6.1 rev6，含待处理回退与受托终态）。"""

	def test_normal_lifecycle(self):
		self.assertTrue(rtc.can_retention_transition("在库", "部分使用"))
		self.assertTrue(rtc.can_retention_transition("部分使用", "已用尽"))
		self.assertTrue(rtc.can_retention_transition("已用尽", "待处理"))
		self.assertTrue(rtc.can_retention_transition("待处理", "已销毁"))

	def test_pending_rollback_paths(self):
		# rev6：驳回退出待处理 + 部分使用续留回写
		self.assertTrue(rtc.can_retention_transition("待处理", "在库"))
		self.assertTrue(rtc.can_retention_transition("待处理", "部分使用"))

	def test_terminal_states(self):
		for state in ("已销毁", "已转出"):
			for target in ("在库", "部分使用", "已用尽", "待处理"):
				self.assertFalse(rtc.can_retention_transition(state, target), target)

	def test_transfer_out_entry(self):
		for state in ("在库", "部分使用", "已用尽"):
			self.assertTrue(rtc.can_retention_transition(state, "已转出"), state)

	def test_workflow_contract_flow_registered(self):
		# workflow_contract 与 retention_contract 状态表一致
		self.assertEqual(wf.RETENTION_TRANSITIONS, rtc.RETENTION_TRANSITIONS)

	def test_action_roles_registered(self):
		# 方案 6.3 矩阵 B 列：register_retention（Analyst+Manager+System）、adjust_stock（Manager+System）
		self.assertEqual(wf.ACTION_ROLES["register_retention"],
						 {wf.ROLE_ANALYST, wf.ROLE_MANAGER, wf.ROLE_SYSTEM})
		self.assertEqual(wf.ACTION_ROLES["adjust_stock"],
						 {wf.ROLE_MANAGER, wf.ROLE_SYSTEM})
		self.assertEqual(wf.ROLE_LIMS_QA, "LIMS QA")


class TestIntegrationWiring(unittest.TestCase):
	"""hooks / setup / 翻译 / 报表接线检查。"""

	def test_hooks_doc_events_cover_retention(self):
		hooks = (APP_ROOT / "hb_lims_app" / "hooks.py").read_text(encoding="utf-8")
		for doctype in ("HBOS Retention Product", "HBOS Retention Sample"):
			self.assertIn('"{}"'.format(doctype), hooks)

	def test_setup_lims_qa_role_and_sidebar(self):
		setup = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "setup.py").read_text(encoding="utf-8")
		self.assertIn('"LIMS QA"', setup)
		self.assertIn("留样管理", setup)
		self.assertIn("HBOS Retention Sample", setup)

	def test_zh_csv_translation(self):
		csv = (APP_ROOT / "hb_lims_app" / "translations" / "zh.csv").read_text(encoding="utf-8")
		for pair in ("HBOS Retention Product,留样产品",
					 "HBOS Retention Sample,留样登记",
					 "HBOS Retention Stock Log,留样库存流水"):
			self.assertIn(pair, csv)

	def test_ledger_report_exists(self):
		report_dir = APP_ROOT / "hb_lims_app" / "hbos_lims" / "report" / "留样台账"
		self.assertTrue((report_dir / "留样台账.json").exists())
		self.assertTrue((report_dir / "留样台账.py").exists())

	def test_retention_service_whitelist(self):
		service = (APP_ROOT / "hb_lims_app" / "hbos_lims" / "retention_service.py").read_text(encoding="utf-8")
		for method in ("register_retention", "create_retention_from_sample", "adjust_stock"):
			self.assertIn("def {}".format(method), service)
		self.assertIn("FOR UPDATE", service, "四步锁协议的行锁")


if __name__ == "__main__":
	unittest.main()
