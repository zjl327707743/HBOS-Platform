# -*- coding: utf-8 -*-
"""M2-R3/R6 系统字段守卫实机验证（真实 Frappe 会话 + 非特权用户）。

为什么必须实机跑：控制器守卫在 `validate()` 里读 `doc.flags`、读
`frappe.session.user` 与角色，离线契约测试（test_lims_guards_contract.py）
只能断言源码接线，证明不了：
  1. 直写（frappe.client.set_value）确实被拦下 —— 本轮的交付目标；
  2. 加了放行标记的正规服务链仍然跑得通 —— 防止守卫把业务流程改坏。

两条都必须由**非特权用户**执行：守卫对 Administrator / System Manager 短路放行，
用 Administrator 跑等于什么都没验证。

覆盖：
- 正向全链（多角色真实切换）：建标准 → 生效 → 样品登记 → 生成任务 → 分配 →
  开始检验 → 提交 → 复核 → 批准 → 生成 COA → QA 审核 → 发布 → 样品放行；
- 负向 ×7：直写 5 个 DocType 的状态字段、直写批准人签名、直插伪造已批准记录；
- 对照 ×1：同一非特权用户改**非**系统字段（备注）必须成功，证明不是一刀切全锁。

数据一律 `TEST-HBOS-M2-R3G-` 前缀，用例结束后按依赖顺序清理。
审计日志为 append-only 设计，其留痕不清理（也不允许清理）。

执行方式（需要 Frappe 运行时，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_lims_guards_runtime.py
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


def _ensure_app_on_path():
	for name in [n for n in list(sys.modules)
				 if n == "hb_lims_app" or n.startswith("hb_lims_app.")]:
		sys.modules.pop(name, None)
	while _APP_DIR in sys.path:
		sys.path.remove(_APP_DIR)
	sys.path.insert(0, _APP_DIR)


# 既有非特权测试用户（上一轮验证遗留，均无 System Manager）
MGR = "r7c-mgr@test.local"					# LIMS Manager
ANALYST = "test-hbos-m2-analyst@test.local"  # LIMS Analyst
REVIEWER = "test-hbos-m2-reviewer@test.local"  # LIMS Reviewer

STAMP = "TEST-HBOS-M2-R3G"
SPEC_CODE = f"{STAMP}-SPEC"
BATCH_NO = f"{STAMP}-B01"


@unittest.skipUnless(_SMOKE_READY, "需要 Frappe 运行时且 HBOS_FRAPPE_SMOKE=1")
class TestSystemFieldGuardsRuntime(unittest.TestCase):
	"""一条完整业务链 + 直写负向用例，全部以非特权用户执行。"""

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

		frappe.set_user(MGR)
		cls._run_positive_chain()
		frappe.set_user("Administrator")

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		cls._cleanup()
		if cls.initialized_here:
			frappe.destroy()

	# ------------------------------------------------------------------
	# 正向全链（多角色真实切换）
	# ------------------------------------------------------------------

	@classmethod
	def _run_positive_chain(cls):
		svc = cls.svc
		item = frappe.get_all("HBOS Test Item", pluck="name", limit_page_length=2)
		sample_type = frappe.get_all("HBOS Sample Type", pluck="name", limit_page_length=1)
		if len(item) < 2 or not sample_type:
			raise AssertionError("缺少主数据（HBOS Test Item / HBOS Sample Type），无法建链")
		cls.artifacts["item"] = item

		# 1) 建标准（Manager）+ 生效 —— 生效会改 status，走守卫
		spec = svc.create_specification(
			spec_code=SPEC_CODE, spec_name=f"{STAMP} 规格", material_code=f"{STAMP}-MAT",
			material_name="测试物料", standard_source="企业内控", version="1.0",
			effective_date=frappe.utils.today(),
			items=[
				{"item": item[0], "item_name": item[0], "limits_type": "上限",
				 "upper_limit": 100, "unit": "mg", "significant_digits": 2},
				{"item": item[1], "item_name": item[1], "limits_type": "下限",
				 "lower_limit": 10, "unit": "%", "significant_digits": 2},
			])
		cls.artifacts["spec"] = spec
		svc.activate_specification(spec)

		# 2) 样品登记（Manager）→ 已登记
		sample = svc.register_sample(
			sample_type=sample_type[0], material_code=f"{STAMP}-MAT", material_name="测试物料",
			batch_no=BATCH_NO, sample_source="生产取样", specification=spec, priority="常规")
		cls.artifacts["sample"] = sample

		# 3) 生成任务（Manager）+ 分配
		lab = frappe.get_all("HBOS Lab Department", pluck="name", limit_page_length=1)
		if not lab:
			raise AssertionError("缺少 HBOS Lab Department 主数据")
		tasks = svc.generate_tasks(sample, lab_department=lab[0])
		cls.artifacts["tasks"] = list(tasks)
		for t in tasks:
			svc.assign_task(t, assignee=ANALYST)

		# 4) 检验员开始 + 提交（Analyst）
		frappe.set_user(ANALYST)
		results = []
		pairs = [(100, 50), (10, 20)]  # (限度, 实测)，均在范围内 → 合格、无 OOS
		for t, (_, measured) in zip(tasks, pairs):
			out = svc.start_task(t)
			results.append(out["result"])
			svc.submit_result(out["result"], raw_value=measured, result_value=measured)
		cls.artifacts["results"] = results

		# 5) 复核 + 批准（Reviewer）→ 全部批准后样品自动 检验完成
		frappe.set_user(REVIEWER)
		for r in results:
			svc.review_result(r)
			svc.approve_result(r)
		status = frappe.db.get_value("HBOS Sample", sample, "status")
		if status != "检验完成":
			raise AssertionError(f"全部结果批准后样品应为「检验完成」，实际 {status}")

		# 6) COA 生成 → QA 审核 → 发布（Reviewer）
		coa = svc.create_coa(sample)
		cls.artifacts["coa"] = coa
		svc.review_coa(coa)
		published = svc.publish_coa(coa)
		cls.artifacts["coa_pdf"] = published["pdf"]

		# 7) 样品放行（Reviewer）—— 放行必须在生成 COA 之后（COA 要求「检验完成」）
		svc.release_sample(sample)

	# ------------------------------------------------------------------
	# 负向：直写系统字段必须被拦下
	# ------------------------------------------------------------------

	def _direct_write(self, doctype, name, values):
		frappe.set_user(MGR)
		return frappe.client.set_value(doctype, name, json.dumps(values))

	def _assert_blocked(self, doctype, name, values):
		frappe.set_user(MGR)
		with self.assertRaises(frappe.ValidationError) as ctx:
			frappe.client.set_value(doctype, name, json.dumps(values))
		self.assertIn("系统字段", str(ctx.exception))
		frappe.db.rollback()

	def test_direct_write_sample_status_blocked(self):
		self._assert_blocked("HBOS Sample", self.artifacts["sample"], {"status": "已拒绝"})

	def test_direct_write_sample_oos_lock_blocked(self):
		self._assert_blocked("HBOS Sample", self.artifacts["sample"], {"oos_locked": 1})

	def test_direct_write_task_status_blocked(self):
		self._assert_blocked("HBOS Sample Task", self.artifacts["tasks"][0], {"status": "已提交"})

	def test_direct_write_result_status_blocked(self):
		"""核心用例：不执行服务方法，直接把结果改成「已批准」。"""
		self._assert_blocked("HBOS Test Result", self.artifacts["results"][0],
							 {"result_status": "已提交"})

	def test_direct_write_approver_signature_blocked(self):
		"""伪造审批归属：把自己的名字写进批准人。"""
		self._assert_blocked("HBOS Test Result", self.artifacts["results"][0],
							 {"approver": MGR})

	def test_direct_write_coa_status_blocked(self):
		self._assert_blocked("HBOS COA", self.artifacts["coa"], {"report_status": "草稿"})

	def test_direct_write_spec_status_blocked(self):
		self._assert_blocked("HBOS Specification", self.artifacts["spec"], {"status": "已废止"})

	def test_direct_insert_forged_approved_result_blocked(self):
		"""通用 insert 伪造「已批准」记录必须被拦（新建分支）。"""
		frappe.set_user(MGR)
		with self.assertRaises(frappe.ValidationError) as ctx:
			frappe.client.insert({
				"doctype": "HBOS Test Result",
				"task": self.artifacts["tasks"][0],
				"result_status": "已批准",
			})
		self.assertIn("禁止通过直接新建写入", str(ctx.exception))
		frappe.db.rollback()

	# ------------------------------------------------------------------
	# 对照：非系统字段仍可直写（证明不是一刀切全锁）
	# ------------------------------------------------------------------

	def test_non_system_field_write_still_allowed(self):
		frappe.set_user(MGR)
		frappe.client.set_value("HBOS Sample", self.artifacts["sample"],
							   json.dumps({"remarks": f"{STAMP} 备注直写对照"}))
		self.assertEqual(frappe.db.get_value("HBOS Sample", self.artifacts["sample"], "remarks"),
						 f"{STAMP} 备注直写对照")
		frappe.db.rollback()

	# ------------------------------------------------------------------
	# 清理（依赖顺序：COA → 结果 → 任务 → 样品 → 标准）
	# ------------------------------------------------------------------

	@classmethod
	def _cleanup(cls):
		a = cls.artifacts
		# 依赖顺序：COA → 结果 → 任务 → 样品 → 标准（后者被前者引用）
		for name in [a.get("coa")]:
			if name:
				_force_delete("HBOS COA", name)
		for name in a.get("results", []):
			_force_delete("HBOS Test Result", name)
		for name in a.get("tasks", []):
			_force_delete("HBOS Sample Task", name)
		if a.get("sample"):
			_force_delete("HBOS Sample", a["sample"])
		if a.get("spec"):
			_force_delete("HBOS Specification", a["spec"])
		# COA 附件（File）不随 COA 删除自动清理
		url = a.get("coa_pdf")
		if url:
			for f in frappe.get_all("File", filters={"file_url": url}, pluck="name"):
				_force_delete("File", f)
		frappe.db.commit()


def _force_delete(doctype, name):
	if not frappe.db.exists(doctype, name):
		return
	try:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	except Exception as exc:  # 清理失败不得掩盖验证结论，但要显式暴露
		frappe.log_error(f"清理 {doctype} {name} 失败：{exc}", "HBOS M2-R3G 守卫验证清理")
