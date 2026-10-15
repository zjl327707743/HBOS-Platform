# -*- coding: utf-8 -*-
"""L10-P0-03 普通检验结果链职责分离（SoD）实机验证（真实 Frappe 会话 + 非特权用户）。

缺陷：`HBOS Test Result` 的 `review_result()` / `approve_result()` 只校验角色与状态，
未拒绝「复核人 = 检验人」「批准人 = 复核人」；而 `LIMS Manager` 同时持有
submit / review / approve 三个动作 —— 同一账号可独立跑完检验→复核→批准全链。

为什么必须实机跑：SoD 依赖真实会话身份、真实角色表与真实状态机；离线契约测试
（test_lims_service_contract.py）只能断言源码接线。且守卫对 Administrator /
System Manager 短路放行，用 Administrator 跑等于什么都没验证。

覆盖：
- 阻断 ×4：非检验人提交（非 Manager）、Manager 代提交缺理由、复核人 = 检验人、
  批准人 = 复核人；
- 放行 ×2：Manager 代提交（带理由，审计含理由与真实操作人）、换人批准；
- 守卫 ×1：`analyst` 直写被系统字段守卫拦下（否则改检验人即可绕过 SoD）；
- 留痕 ×1：每次阻断都新增一条 `HBOS Audit Log`（log_type = SoD 拦截）。

数据一律 `TEST-HBOS-P003-` 前缀，用例结束后按依赖顺序清理。
审计日志为 append-only 设计，其留痕不清理（也不允许清理）。

执行方式（需要 Frappe 运行时，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_lims_result_sod_runtime.py
"""

import json
import os
import sys
import unittest

try:  # 宿主机无 frappe：静默降级，不得抛异常
	import frappe
except ImportError:  # pragma: no cover - 离线门禁路径
	frappe = None


_SMOKE_READY = frappe is not None and os.environ.get("HBOS_FRAPPE_SMOKE") == "1"

# `apps/hb_lims_app/__init__.py` 存在时，pytest 会把 `apps/` 插到 sys.path 首位，
# 使 `hb_lims_app` 解析成外层目录（不含 `hbos_lims`）并缓存进 sys.modules。
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 既有非特权测试用户（均无 System Manager）
MGR = "r7c-mgr@test.local"                     # LIMS Manager
ANALYST = "test-hbos-m2-analyst@test.local"    # LIMS Analyst（结果 A 的检验人）
ANALYST2 = "r7c-an@test.local"                 # LIMS Analyst（非 Manager，用于越权提交）
REVIEWER = "test-hbos-m2-reviewer@test.local"  # LIMS Reviewer
REVIEWER2 = "r7c-qc2@test.local"               # LIMS Reviewer（换人批准）

STAMP = "TEST-HBOS-P003"
SPEC_CODE = f"{STAMP}-SPEC"
BATCH_NO = f"{STAMP}-B01"
PROXY_REASON = f"{STAMP} 检验员休假，经理代提交"


def _ensure_app_on_path():
	"""把 `hb_lims_app` 解析到真正的 App 包（`apps/hb_lims_app/hb_lims_app`）。

	幂等：同一进程内多个测试文件都会调用本函数，而反复清除并重导入
	`hb_lims_app.*` 会让 DocType 控制器类出现「同一路径、不同对象」的两个副本，
	后续 `frappe.get_cached_doc` 写 Redis 文档缓存时 pickle 直接失败
	（PicklingError: not the same object）。故只要已按正确根路径导入过就不再动。
	"""
	loaded = sys.modules.get("hb_lims_app.hbos_lims.lims_service")
	if loaded and getattr(loaded, "__file__", "").startswith(_APP_DIR):
		return
	for name in [n for n in list(sys.modules)
				 if n == "hb_lims_app" or n.startswith("hb_lims_app.")]:
		sys.modules.pop(name, None)
	while _APP_DIR in sys.path:
		sys.path.remove(_APP_DIR)
	sys.path.insert(0, _APP_DIR)


@unittest.skipUnless(_SMOKE_READY, "需要 Frappe 运行时且 HBOS_FRAPPE_SMOKE=1")
class TestResultChainSodRuntime(unittest.TestCase):
	"""一条最小业务链 + SoD 正负向用例，全部以非特权用户执行。

	结果分配（各自独立，避免用例间状态耦合）：
	  resultA 检验人=ANALYST → 提交归属与代提交理由
	  resultB 检验人=MGR     → 复核人 = 检验人 阻断
	  resultC 检验人=MGR     → 批准人 = 复核人 阻断 / 换人批准放行
	"""

	@classmethod
	def setUpClass(cls):
		site = os.environ.get("FRAPPE_SITE", "frontend")
		sites_path = os.environ.get("FRAPPE_SITES_PATH", "/home/frappe/frappe-bench/sites")
		cls.initialized_here = not getattr(getattr(frappe, "local", None), "site", None)
		if cls.initialized_here:
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
		_ensure_app_on_path()

		from hb_lims_app.hbos_lims import lims_service as svc

		cls.svc = svc
		cls.artifacts = {}
		for user in (MGR, ANALYST, ANALYST2, REVIEWER, REVIEWER2):
			cls._assert_non_privileged(user)

		frappe.set_user("Administrator")
		cls._build_chain()
		frappe.set_user("Administrator")

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		cls._cleanup()
		if cls.initialized_here:
			frappe.destroy()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ------------------------------------------------------------------
	# 夹具
	# ------------------------------------------------------------------

	@classmethod
	def _assert_non_privileged(cls, user):
		if not frappe.db.exists("User", user):
			raise AssertionError("缺少非特权测试用户 {}".format(user))
		if "System Manager" in set(frappe.get_roles(user)):
			raise AssertionError("{} 含 System Manager，无法验证拦截路径".format(user))

	@classmethod
	def _build_chain(cls):
		svc = cls.svc
		items = frappe.get_all("HBOS Test Item", pluck="name", limit_page_length=3)
		sample_type = frappe.get_all("HBOS Sample Type", pluck="name", limit_page_length=1)
		lab = frappe.get_all("HBOS Lab Department", pluck="name", limit_page_length=1)
		if len(items) < 3 or not sample_type or not lab:
			raise AssertionError("缺少主数据（HBOS Test Item ×3 / Sample Type / Lab Department）")

		frappe.set_user(MGR)
		spec = svc.create_specification(
			spec_code=SPEC_CODE, spec_name=f"{STAMP} 规格", material_code=f"{STAMP}-MAT",
			material_name="SoD 测试物料", standard_source="企业内控", version="1.0",
			effective_date=frappe.utils.today(),
			items=[
				{"item": items[0], "item_name": items[0], "limits_type": "上限",
				 "upper_limit": 100, "unit": "mg", "significant_digits": 2},
				{"item": items[1], "item_name": items[1], "limits_type": "下限",
				 "lower_limit": 10, "unit": "%", "significant_digits": 2},
				{"item": items[2], "item_name": items[2], "limits_type": "区间",
				 "lower_limit": 10, "upper_limit": 20, "unit": "mL", "significant_digits": 2},
			])
		svc.activate_specification(spec)
		cls.artifacts["spec"] = spec

		sample = svc.register_sample(
			sample_type=sample_type[0], material_code=f"{STAMP}-MAT", material_name="SoD 测试物料",
			batch_no=BATCH_NO, sample_source="生产取样", specification=spec, priority="常规")
		cls.artifacts["sample"] = sample

		tasks = svc.generate_tasks(sample, lab_department=lab[0])
		cls.artifacts["tasks"] = list(tasks)
		# 结果 A 的检验人 = ANALYST，其余两个任务留给 MGR
		svc.assign_task(tasks[0], assignee=ANALYST)
		for task in tasks[1:]:
			svc.assign_task(task, assignee=MGR)

		frappe.set_user(ANALYST)
		cls.artifacts["resultA"] = svc.start_task(tasks[0])["result"]

		frappe.set_user(MGR)
		cls.artifacts["resultB"] = svc.start_task(tasks[1])["result"]
		cls.artifacts["resultC"] = svc.start_task(tasks[2])["result"]

		if frappe.db.get_value("HBOS Test Result", cls.artifacts["resultA"], "analyst") != ANALYST:
			raise AssertionError("夹具异常：结果 A 的检验人不是 ANALYST")
		for key in ("resultB", "resultC"):
			if frappe.db.get_value("HBOS Test Result", cls.artifacts[key], "analyst") != MGR:
				raise AssertionError("夹具异常：{} 的检验人不是 MGR".format(key))
		frappe.set_user("Administrator")

	@staticmethod
	def _audit_count(result_name, log_type="SoD 拦截"):
		return frappe.db.count("HBOS Audit Log", {"log_type": log_type, "doc_name": result_name})

	def _assert_blocked_with_audit(self, result_name, message_part, fn):
		"""执行 fn，断言被拦截且新增一条 SoD 审计（业务全弃 + 审计留存）。"""
		before = self._audit_count(result_name)
		status_before = frappe.db.get_value("HBOS Test Result", result_name, "result_status")
		with self.assertRaises(frappe.ValidationError) as ctx:
			fn()
		self.assertIn(message_part, str(ctx.exception))
		frappe.set_user("Administrator")
		self.assertEqual(
			status_before,
			frappe.db.get_value("HBOS Test Result", result_name, "result_status"),
			"拦截后结果状态必须保持原值")
		self.assertEqual(before + 1, self._audit_count(result_name),
						 "SoD 拦截必须新增一条 HBOS Audit Log（log_type=SoD 拦截）")

	# ------------------------------------------------------------------
	# 提交归属：非检验人 / Manager 代提交（同一夹具按序执行，避免 run-order 耦合）
	# ------------------------------------------------------------------

	def test_submit_ownership_then_manager_proxy(self):
		"""结果 A（检验人=ANALYST）依次验证：越权提交 → 代提交缺理由 → 代提交带理由。"""
		result = self.artifacts["resultA"]

		# 1) 非检验人且非 Manager：SoD 拦截留痕
		frappe.set_user(ANALYST2)
		self._assert_blocked_with_audit(
			result, "只能提交本人的检验记录",
			lambda: self.svc.submit_result(result, raw_value=50, result_value=50))

		# 2) Manager 代提交但未填理由：拒绝（受控理由必填，不产生状态变化）
		frappe.set_user(MGR)
		with self.assertRaises(frappe.ValidationError) as ctx:
			self.svc.submit_result(result, raw_value=50, result_value=50)
		frappe.set_user("Administrator")
		self.assertIn("必须填写代提交理由", str(ctx.exception))
		self.assertEqual("草稿", frappe.db.get_value("HBOS Test Result", result, "result_status"),
						 "缺理由的代提交不得生效")

		# 3) Manager 代提交带理由：放行，且审计记录理由与真实操作人
		frappe.set_user(MGR)
		self.svc.submit_result(result, raw_value=50, result_value=50, proxy_reason=PROXY_REASON)
		frappe.set_user("Administrator")
		self.assertEqual("已提交", frappe.db.get_value("HBOS Test Result", result, "result_status"))
		self.assertEqual(ANALYST, frappe.db.get_value("HBOS Test Result", result, "analyst"),
						 "代提交不得改写检验人归属")
		rows = frappe.get_all(
			"HBOS Audit Log",
			filters={"log_type": "提交", "doc_name": result, "reason": PROXY_REASON},
			fields=["user", "action_text"])
		self.assertEqual(1, len(rows), "代提交必须留下含理由的审计（log_type=提交）")
		self.assertEqual(MGR, rows[0]["user"], "审计必须记录真实操作人（代提交者）")
		self.assertIn("代提交", rows[0]["action_text"])

	# ------------------------------------------------------------------
	# 复核 SoD：复核人 ≠ 检验人
	# ------------------------------------------------------------------

	def test_reviewer_equals_analyst_blocked(self):
		"""检验人本人复核自己的结果（Manager 双角色）→ SoD 拦截留痕。"""
		result = self.artifacts["resultB"]
		frappe.set_user(MGR)
		self.svc.submit_result(result, raw_value=15, result_value=15)  # 本人草稿，无需代提交理由
		self.assertEqual("已提交", frappe.db.get_value("HBOS Test Result", result, "result_status"))
		self._assert_blocked_with_audit(result, "复核人不得为检验人",
									   lambda: self.svc.review_result(result))

	# ------------------------------------------------------------------
	# 批准 SoD：批准人 ≠ 复核人
	# ------------------------------------------------------------------

	def test_approver_equals_reviewer_blocked_then_other_approver_allowed(self):
		"""同一账号先复核再批准 → SoD 拦截留痕；换人批准 → 放行。"""
		result = self.artifacts["resultC"]
		frappe.set_user(MGR)
		self.svc.submit_result(result, raw_value=15, result_value=15)

		frappe.set_user(REVIEWER)
		self.svc.review_result(result)
		self.assertEqual(REVIEWER, frappe.db.get_value("HBOS Test Result", result, "reviewer"))
		self._assert_blocked_with_audit(result, "批准人必须同时区别于检验人和复核人",
									   lambda: self.svc.approve_result(result))

		frappe.set_user(REVIEWER2)
		self.svc.approve_result(result)
		frappe.set_user("Administrator")
		self.assertEqual("已批准", frappe.db.get_value("HBOS Test Result", result, "result_status"))
		self.assertEqual(REVIEWER2, frappe.db.get_value("HBOS Test Result", result, "approver"),
						 "换人批准应记录真实批准人")

	# ------------------------------------------------------------------
	# 守卫：检验人字段不可直写（否则改检验人即可绕过 SoD）
	# ------------------------------------------------------------------

	def test_direct_write_analyst_blocked(self):
		"""直写 `analyst` 必须被系统字段守卫拦下（L10-P0-03 对齐稳定性字段集）。

		否则草稿态改掉检验人即可绕过「复核人 ≠ 检验人」。用例不依赖执行顺序：
		守卫比较保存前后的字段值，令其发生变化即触发（与当前状态无关）。
		"""
		result = self.artifacts["resultA"]
		self.assertEqual(ANALYST, frappe.db.get_value("HBOS Test Result", result, "analyst"),
						 "夹具前提：结果 A 的检验人为 ANALYST")
		frappe.set_user(MGR)
		with self.assertRaises(frappe.ValidationError) as ctx:
			frappe.client.set_value("HBOS Test Result", result, json.dumps({"analyst": MGR}))
		self.assertIn("系统字段", str(ctx.exception))
		frappe.db.rollback()
		frappe.set_user("Administrator")
		self.assertEqual(ANALYST, frappe.db.get_value("HBOS Test Result", result, "analyst"),
						 "直写被拦后检验人必须保持原值")

	# ------------------------------------------------------------------
	# 清理（依赖顺序：结果 → 任务 → 样品 → 标准）
	# ------------------------------------------------------------------

	@classmethod
	def _cleanup(cls):
		a = cls.artifacts
		if not a:
			return
		frappe.set_user("Administrator")
		for key in ("resultA", "resultB", "resultC"):
			if a.get(key):
				_force_delete("HBOS Test Result", a[key])
		for name in a.get("tasks", []):
			_force_delete("HBOS Sample Task", name)
		if a.get("sample"):
			_force_delete("HBOS Sample", a["sample"])
		if a.get("spec"):
			_force_delete("HBOS Specification", a["spec"])
		frappe.db.commit()


def _force_delete(doctype, name):
	if not frappe.db.exists(doctype, name):
		return
	try:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	except Exception as exc:  # 清理失败不得掩盖验证结论，但要显式暴露
		frappe.log_error(f"清理 {doctype} {name} 失败：{exc}", "HBOS P0-03 SoD 验证清理")


if __name__ == "__main__":
	unittest.main()
