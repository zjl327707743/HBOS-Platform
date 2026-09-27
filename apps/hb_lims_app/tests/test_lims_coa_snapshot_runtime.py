# -*- coding: utf-8 -*-
"""L10-P0-05 COA 快照冻结与内容指纹实机验证（真实 Frappe 会话 + 非特权用户）。

缺陷：`HBOSCOA._validate_locked_after_review()` 只判断
`len(self.items) != len(before.items)`，**没有比较同长度子表的每一行内容**；
`HBOS COA Item` 控制器是空的 `pass`。于是已审核/已发布状态下，只要不改变行数，
仍可改掉检验项目 / 方法 SOP / 标准限度 / 结果 / 判定 / 备注，甚至仅仅调换行序。
另有一处脆弱点：该方法的早退判据是**当前**状态（`self.report_status == 草稿`），
一旦状态被合法回退到草稿，冻结即失效。

为什么必须实机跑：冻结依赖控制器 `validate()` 的前后值比较与真实状态流转；离线
契约只能断言接线。且守卫不设特权旁路，用 Administrator 跑等于什么都没验证。

覆盖（用例带序号，顺序即生命周期，故意如此）：
- 已审核 ×4：报告头字段、子表行内容、子表行序、备注，四者皆不可改；
- 已发布 ×1：发布后同样整份冻结（含 pdf_attachment 不可换）；
- 指纹 ×2：发布时固化内容指纹、`verify_coa_content()` 通过；绕过 validate 的
  低层直写会被该接口检出（体现"可主动校验"而非仅靠结构保证）。

数据一律 `TEST-HBOS-P005-` 前缀，用例结束后按依赖顺序清理。
审计日志为 append-only 设计，其留痕不清理（也不允许清理）。

执行方式（需要 Frappe 运行时，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_lims_coa_snapshot_runtime.py
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
REVIEWER = "test-hbos-m2-reviewer@test.local"  # LIMS Reviewer（结果复核）
REVIEWER2 = "r7c-qc2@test.local"               # LIMS Reviewer（换人批准，P0-03 SoD）

STAMP = "TEST-HBOS-P005"
SPEC_CODE = f"{STAMP}-SPEC"
BATCH_NO = f"{STAMP}-B01"


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
class TestCoaSnapshotRuntime(unittest.TestCase):
	"""COA 审核/发布后整份快照冻结 + 内容指纹可主动校验。"""

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
		for user in (MGR, REVIEWER, REVIEWER2):
			if not frappe.db.exists("User", user):
				raise AssertionError("缺少非特权测试用户 {}".format(user))
			if "System Manager" in set(frappe.get_roles(user)):
				raise AssertionError("{} 含 System Manager，无法验证守卫".format(user))

		frappe.set_user("Administrator")
		cls._drop_stale_fixtures()
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
	def _drop_stale_fixtures(cls):
		"""清理上次异常中断残留的本轮夹具，使套件可重复运行。

		必须连**整条依赖链**一起删。HBOS Sample 的命名序列在删除后会被复用（实测旧
		样品 HBOS-SMP-2026-00037 被删后，新样品拿到同一名字），若只删样品与标准，
		上一轮的结果 / 任务会以同名留在库里，被本轮 `create_coa` 的按样品查询命中
		—— 本轮实测因此造出 4 行 COA（2 行本轮 + 2 行上轮孤儿）。
		"""
		for sample in frappe.get_all("HBOS Sample",
									 filters={"material_code": ["like", f"{STAMP}%"]},
									 pluck="name", limit_page_length=0):
			for coa in frappe.get_all("HBOS COA", filters={"sample": sample},
									  pluck="name", limit_page_length=0):
				for name in frappe.get_all("File",
										   filters={"attached_to_doctype": "HBOS COA",
													"attached_to_name": coa},
										   pluck="name", limit_page_length=0):
					_force_delete("File", name)
				_force_delete("HBOS COA", coa)
			for doctype in ("HBOS Test Result", "HBOS Sample Task"):
				for name in frappe.get_all(doctype, filters={"sample": sample},
										   pluck="name", limit_page_length=0):
					_force_delete(doctype, name)
			_force_delete("HBOS Sample", sample)
		for spec in frappe.get_all("HBOS Specification",
								   filters={"spec_code": ["like", f"{STAMP}%"]},
								   pluck="name", limit_page_length=0):
			_force_delete("HBOS Specification", spec)
		frappe.db.commit()

	@classmethod
	def _build_chain(cls):
		"""最小全链：标准 → 样品 → 2 个任务 → 提交/复核/批准 → COA 已审核。"""
		svc = cls.svc
		items = frappe.get_all("HBOS Test Item", pluck="name", limit_page_length=2)
		sample_type = frappe.get_all("HBOS Sample Type", pluck="name", limit_page_length=1)
		lab = frappe.get_all("HBOS Lab Department", pluck="name", limit_page_length=1)
		if len(items) < 2 or not sample_type or not lab:
			raise AssertionError("缺少主数据（HBOS Test Item ×2 / Sample Type / Lab Department）")

		frappe.set_user(MGR)
		spec = svc.create_specification(
			spec_code=SPEC_CODE, spec_name=f"{STAMP} 规格", material_code=f"{STAMP}-MAT",
			material_name="P005 测试物料", standard_source="企业内控", version="1.0",
			effective_date=frappe.utils.today(),
			items=[
				{"item": items[0], "item_name": items[0], "limits_type": "上限",
				 "upper_limit": 100, "unit": "mg", "significant_digits": 2},
				{"item": items[1], "item_name": items[1], "limits_type": "下限",
				 "lower_limit": 10, "unit": "%", "significant_digits": 2},
			])
		svc.activate_specification(spec)
		cls.artifacts["spec"] = spec

		sample = svc.register_sample(
			sample_type=sample_type[0], material_code=f"{STAMP}-MAT", material_name="P005 测试物料",
			batch_no=BATCH_NO, sample_source="生产取样", specification=spec, priority="常规")
		cls.artifacts["sample"] = sample

		tasks = svc.generate_tasks(sample, lab_department=lab[0])
		cls.artifacts["tasks"] = list(tasks)
		for task in tasks:
			svc.assign_task(task, assignee=MGR)

		results = []
		for task, measured in zip(tasks, (50, 20)):  # 均在限度内 → 合格、无 OOS
			out = svc.start_task(task)
			results.append(out["result"])
			svc.submit_result(out["result"], raw_value=measured, result_value=measured)
		cls.artifacts["results"] = results

		frappe.set_user(REVIEWER)
		for name in results:
			svc.review_result(name)
		frappe.set_user(REVIEWER2)
		for name in results:
			svc.approve_result(name)

		frappe.set_user(MGR)
		coa = svc.create_coa(sample)
		svc.review_coa(coa)
		cls.artifacts["coa"] = coa
		if frappe.db.get_value("HBOS COA", coa, "report_status") != "已审核":
			raise AssertionError("夹具异常：COA 未进入已审核")
		item_rows = frappe.get_all("HBOS COA Item", filters={"parent": coa},
								   pluck="name", limit_page_length=0)
		if len(item_rows) != len(results):
			raise AssertionError(
				"夹具异常：COA 项目行为 {}，与本轮已批准结果数 {} 不符 —— 疑似同名孤儿数据"
				"（样品已被删、但其结果 / 任务仍在库中，被样品名复用后命中的查询捡到）".format(
					len(item_rows), len(results)))

	# ------------------------------------------------------------------
	# 断言助手
	# ------------------------------------------------------------------

	def _assert_blocked(self, message_part, fn, as_user=None):
		"""以非特权身份执行 fn，断言被拦下；随后回到 Administrator 读库。

		守卫对 Administrator / System Manager 短路放行，因此**必须**在 fn 之前显式
		切换身份 —— 本助手把这件事收进自己内部，不留给调用方按顺序记（本轮实测：
		若沿用上一条检查残留的 Administrator 身份，`pdf_attachment` 直改会静默通过，
		表现为「守卫失效」，实际是测试身份错了）。
		"""
		frappe.set_user(as_user or MGR)
		try:
			with self.assertRaises(frappe.ValidationError) as ctx:
				fn()
		finally:
			frappe.set_user("Administrator")
		self.assertIn(message_part, str(ctx.exception))
		frappe.db.rollback()

	def _coa(self):
		return self.artifacts["coa"]

	def _first_item_name(self, coa):
		names = frappe.get_all("HBOS COA Item", filters={"parent": coa},
							   order_by="idx asc", pluck="name", limit_page_length=1)
		return names[0] if names else None

	# ------------------------------------------------------------------
	# 用例 01：已审核状态整份快照冻结
	# ------------------------------------------------------------------

	def test_01_reviewed_snapshot_frozen(self):
		"""已审核：关联字段、备注、子表行内容与行序皆不可改；派生字段不可被改写。"""
		coa = self._coa()
		frappe.set_user(MGR)
		self.assertEqual("已审核", frappe.db.get_value("HBOS COA", coa, "report_status"))

		# 1) 子表行内容（审计头号缺陷：原实现只比 len(self.items)，同长度改内容完全放行）
		def _tamper_row():
			doc = frappe.get_doc("HBOS COA", coa)
			doc.items[0].result = "被篡改的结果"
			doc.save(ignore_permissions=True)
		self._assert_blocked("不可增删改", _tamper_row)

		# 2) 子表行序（内容集合不变，仅调换顺序）
		def _swap_rows():
			doc = frappe.get_doc("HBOS COA", coa)
			first, second = doc.items[0], doc.items[1]
			doc.items = [second, first]
			doc.save(ignore_permissions=True)
		self._assert_blocked("含顺序", _swap_rows)

		# 3) 备注（原实现未列入锁定字段）
		self._assert_blocked("不可修改", lambda: frappe.client.set_value(
			"HBOS COA", coa, json.dumps({"remarks": "审核后补写"})))

		# 4) 报告头关联字段 sample（非派生，可直接改）
		current_sample = frappe.db.get_value("HBOS COA", coa, "sample")
		other = frappe.get_all("HBOS Sample", filters={"name": ["!=", current_sample]},
							   pluck="name", limit_page_length=1)
		if other:
			self._assert_blocked("不可修改", lambda: frappe.client.set_value(
				"HBOS COA", coa, json.dumps({"sample": other[0]})))

		# 5) 派生字段（batch_no / material_name / spec_version 由 sample 带出）不可被改写：
		#    或由守卫拦下，或保存时被 fetch_from 重新派生覆盖 —— 结果都必须是原值。
		frappe.set_user(MGR)
		original = frappe.db.get_value("HBOS COA", coa, "material_name")
		try:
			frappe.client.set_value("HBOS COA", coa,
									json.dumps({"material_name": "被篡改的物料"}))
		except frappe.ValidationError:
			pass
		frappe.set_user("Administrator")
		frappe.db.rollback()
		self.assertEqual(original, frappe.db.get_value("HBOS COA", coa, "material_name"),
						 "派生字段不得被改写")

		frappe.set_user("Administrator")
		doc = frappe.get_doc("HBOS COA", coa)
		self.assertEqual(2, len(doc.items))
		self.assertNotIn("篡改", str(doc.items[0].result or ""))

	# ------------------------------------------------------------------
	# 用例 02：发布后同样冻结 + 内容指纹可主动校验
	# ------------------------------------------------------------------

	def test_02_publish_freezes_snapshot_and_records_fingerprint(self):
		"""发布：整份快照仍冻结、PDF 附件不可换、内容指纹可校验且能检出低层直写。"""
		coa = self._coa()
		frappe.set_user(MGR)
		published = self.svc.publish_coa(coa)
		self.artifacts["pdf"] = published["pdf"]
		frappe.set_user("Administrator")
		self.assertEqual("已发布", frappe.db.get_value("HBOS COA", coa, "report_status"))
		self.assertTrue(frappe.db.get_value("HBOS COA", coa, "content_fingerprint"),
						"发布必须固化内容指纹")

		# 发布后内容与附件依旧不可改（附件属系统字段：只能由服务在发布时写入）
		frappe.set_user(MGR)
		self._assert_blocked("不可修改", lambda: frappe.client.set_value(
			"HBOS COA", coa, json.dumps({"remarks": "发布后补写"})))

		def _swap_pdf():
			doc = frappe.get_doc("HBOS COA", coa)
			doc.pdf_attachment = "/files/forged.pdf"
			doc.save(ignore_permissions=True)
		self._assert_blocked("系统字段", _swap_pdf)

		# 指纹校验通过：归档 PDF 与当前结构化内容同属一个版本
		self.assertEqual(True, self.svc.verify_coa_content(coa)["ok"])

		# 绕过 validate 的低层直写（frappe.db.set_value）会被指纹校验检出
		row = self._first_item_name(coa)
		self.assertIsNotNone(row)
		frappe.set_user("Administrator")
		frappe.db.set_value("HBOS COA Item", row, "verdict", "不合格", update_modified=False)
		verdict = self.svc.verify_coa_content(coa)
		self.assertEqual(False, verdict["ok"], "低层直写必须被内容指纹检出")
		self.assertNotEqual(verdict["stored"], verdict["actual"])
		# 回滚该次直写后恢复一致（用例不留副作用）
		frappe.db.rollback()
		self.assertEqual(True, self.svc.verify_coa_content(coa)["ok"])

	# ------------------------------------------------------------------
	# 清理（依赖顺序：COA 附件 → COA → 结果 → 任务 → 样品 → 标准）
	# ------------------------------------------------------------------

	@classmethod
	def _cleanup(cls):
		a = cls.artifacts
		if not a:
			return
		frappe.set_user("Administrator")
		url = a.get("pdf")
		if url:
			for name in frappe.get_all("File", filters={"file_url": url}, pluck="name"):
				_force_delete("File", name)
		if a.get("coa"):
			_force_delete("HBOS COA", a["coa"])
		for name in a.get("results", []):
			_force_delete("HBOS Test Result", name)
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
		frappe.log_error(f"清理 {doctype} {name} 失败：{exc}", "HBOS P0-05 COA 验证清理")


if __name__ == "__main__":
	unittest.main()
