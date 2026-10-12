# -*- coding: utf-8 -*-
"""L10-P0-01 审计事务语义实机验证（真实 Frappe 会话 + 非特权用户）。

本轮的缺陷（审核 PR #10 / L10-P0-01）：违规拦截审计原先直接
`frappe.db.commit()`，它提交的是**当前请求的整个事务**，会把拦截发生前的
部分业务写入一并落库，使随后的 `frappe.throw()` 失去回滚意义。
正确语义有两条，必须同时成立：
  1. 业务对象保持原值（违规操作整体不成立）；
  2. 违规审计按设计留存（write-once 合规，不随业务回滚丢失）。

为什么必须实机跑：`frappe.db.commit() / rollback()` 的事务边界只有在真实
数据库连接上才成立；离线契约测试（test_audit_log_contract.py）只能断言源码
接线。且拦截路径对 Administrator / System Manager 短路放行（`_privileged()`），
用 Administrator 跑等于什么都没验证。

覆盖：
- 契约 ×2：默认审计不提交（随业务回滚消失）；`audit_violation` 先回滚未提交
  业务写入、再独立提交留痕；
- 真实链 ×2：留样使用审批 SoD 拦截（`_audit_commit`）、主数据删除拦截
  （`on_trash` 内的 `_audit_delete_block`，风险最高的上下文）；
- 核心回归 ×1：拦截前在同一事务内的挂起业务写入**不得被顺手提交**。

用例只做「尝试拦截」，不改动既有业务数据；审计日志为 append-only 设计，
其留痕不清理（也不允许清理）。

执行方式（需要 Frappe 运行时，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_audit_transaction_runtime.py
"""

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
MGR = "r7c-mgr@test.local"                  # LIMS Manager
QC1 = "r7c-qc1@test.local"                  # LIMS Reviewer（可执行 usage_qc）

# 删除拦截目标：主数据一律禁删（MASTER_DELETABLE_STATUSES = None）
PROTECTED_DOCTYPE = "HBOS Stability Room"

MARKER = "TEST-AUDIT-TX-PENDING-WRITE"

# 审计日志 append-only：同名留痕会永久累积，故契约用例一律使用「增量」断言，
# 保证用例可重复执行（不依赖站点当前是否已有同名的历史留痕）。
SENTINEL_DEFAULT = "TEST-AUDIT-TX-DEFAULT"
SENTINEL_PENDING = "TEST-AUDIT-TX-SENTINEL"
SENTINEL_VIOLATION = "TEST-AUDIT-TX-VIOLATION"


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
class TestAuditTransactionRuntime(unittest.TestCase):
	"""拦截路径的事务语义：业务全弃 + 审计留存。"""

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
		from hb_lims_app.hbos_lims import workflow_contract as wf

		cls.svc = svc
		cls.wf = wf
		for user in (MGR, QC1):
			cls._assert_non_privileged(user)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		if cls.initialized_here:
			frappe.destroy()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ------------------------------------------------------------------
	# 夹具定位（只读；站点缺少可用记录时显式跳过）
	# ------------------------------------------------------------------

	@classmethod
	def _assert_non_privileged(cls, user):
		if not frappe.db.exists("User", user):
			raise AssertionError("缺少非特权测试用户 {}".format(user))
		roles = set(frappe.get_roles(user))
		if "System Manager" in roles:
			raise AssertionError("{} 含 System Manager，无法验证拦截路径".format(user))

	def _find_sod_fixture(self):
		"""找一条「待QC批准」的留样使用申请，且其库存确认人本身有 usage_qc 权限。

		这样运行该用户会先过 `_check_action`，再撞上 SoD（同一单据连续两级签署）。
		"""
		rows = frappe.get_all(
			"HBOS Retention Usage Apply",
			filters={"status": "待QC批准"},
			fields=["name", "stock_confirm_by", "applicant"],
			order_by="modified desc", limit_page_length=50)
		for row in rows:
			runner = row.stock_confirm_by or row.applicant
			if not runner or runner in ("Administrator", "Guest") \
					or not frappe.db.exists("User", runner):
				continue
			roles = set(frappe.get_roles(runner))
			if "System Manager" in roles:
				continue
			if not any(self.wf.action_allowed("usage_qc", role) for role in roles):
				continue
			return row.name, runner
		return None, None

	def _pending_write_target(self):
		"""挑一个可安全做「挂起写入」观测的业务对象（读多写少，观测后回滚）。"""
		names = frappe.get_all("HBOS Sample", pluck="name", limit_page_length=1)
		if not names:
			return None, None
		return "HBOS Sample", names[0]

	def _find_protected_record(self):
		names = frappe.get_all(PROTECTED_DOCTYPE, pluck="name", limit_page_length=1)
		return names[0] if names else None

	@staticmethod
	def _audit_count(log_type, doc_name=None):
		filters = {"log_type": log_type}
		if doc_name:
			filters["doc_name"] = doc_name
		return frappe.db.count("HBOS Audit Log", filters)

	# ------------------------------------------------------------------
	# 契约：默认审计随业务事务回滚；audit_violation 独立留存并丢弃挂起写入
	# ------------------------------------------------------------------

	def test_default_audit_does_not_commit(self):
		"""默认 commit=False：未提交的审计随 rollback 一起消失（与业务同成败）。"""
		frappe.set_user("Administrator")
		before = self._audit_count("修改", SENTINEL_DEFAULT)
		self.svc.audit_log("修改", "HBOS Sample", SENTINEL_DEFAULT,
						   action_text="默认不提交契约")
		self.assertEqual(before + 1, self._audit_count("修改", SENTINEL_DEFAULT),
						 "默认审计应可在同事务内读到")
		frappe.db.rollback()
		self.assertEqual(before, self._audit_count("修改", SENTINEL_DEFAULT),
						 "默认审计不应被独立提交（应随 rollback 消失）")

	def test_violation_audit_survives_rollback_and_discards_pending_write(self):
		"""audit_violation：先回滚挂起业务写入，再独立提交审计留痕。"""
		doctype, name = self._pending_write_target()
		if not doctype:
			self.skipTest("站点缺少 HBOS Sample，无法观测挂起写入")
		frappe.set_user("Administrator")
		original = frappe.db.get_value(doctype, name, "remarks")
		if original == MARKER:
			self.skipTest("样例 remarks 已被占用于其它用例")
		# 增量计数：审计日志 append-only，同名历史留痕不得让用例不可重复执行
		before_pending = self._audit_count("修改", SENTINEL_PENDING)
		before_violation = self._audit_count("SoD 拦截", SENTINEL_VIOLATION)

		self.svc.audit_log("修改", doctype, SENTINEL_PENDING,
						   action_text="将被丢弃的挂起写入")
		frappe.db.set_value(doctype, name, "remarks", MARKER, update_modified=False)
		self.svc.audit_violation("SoD 拦截", doctype, SENTINEL_VIOLATION,
								 action_text="事务语义契约", reason="实机验证")
		try:
			self.assertEqual(
				before_pending, self._audit_count("修改", SENTINEL_PENDING),
				"audit_violation 应先回滚同一事务内未提交的业务写入")
			self.assertEqual(
				before_violation + 1, self._audit_count("SoD 拦截", SENTINEL_VIOLATION),
				"违规审计必须独立提交留存")
			self.assertEqual(
				original, frappe.db.get_value(doctype, name, "remarks"),
				"挂起业务写入必须被回滚")
		finally:
			frappe.db.rollback()

	# ------------------------------------------------------------------
	# 真实链：SoD 拦截（_audit_commit）与删除拦截（on_trash）
	# ------------------------------------------------------------------

	def test_sod_interception_keeps_business_unchanged_and_audits(self):
		"""留样使用审批 SoD 拦截：单据零变化，且新增「SoD 拦截」审计。"""
		usage, runner = self._find_sod_fixture()
		if not usage:
			self.skipTest("站点缺少可触发 SoD 的「待QC批准」留样使用申请")
		from hb_lims_app.hbos_lims import retention_service as rsvc

		before = frappe.db.get_value(
			"HBOS Retention Usage Apply", usage,
			["status", "qc_approval", "qa_approval", "qm_approval"], as_dict=True)
		before_audits = self._audit_count("SoD 拦截", usage)

		frappe.set_user(runner)
		with self.assertRaises(frappe.ValidationError):
			rsvc.approve_usage(usage)
		frappe.set_user("Administrator")

		after = frappe.db.get_value(
			"HBOS Retention Usage Apply", usage,
			["status", "qc_approval", "qa_approval", "qm_approval"], as_dict=True)
		self.assertEqual(before, after, "SoD 拦截后单据字段必须保持原值")
		self.assertEqual(before_audits + 1, self._audit_count("SoD 拦截", usage),
						 "SoD 拦截必须留下审计（理由：同一单据连续两级签署）")

	def test_interception_discards_pending_business_write(self):
		"""核心回归：拦截发生前在同一事务内的业务写入不得被顺手提交。"""
		usage, runner = self._find_sod_fixture()
		doctype, name = self._pending_write_target()
		if not usage or not doctype:
			self.skipTest("缺少 SoD 夹具或挂起写入目标")
		from hb_lims_app.hbos_lims import retention_service as rsvc

		original = frappe.db.get_value(doctype, name, "remarks")

		frappe.set_user(runner)
		try:
			frappe.db.set_value(doctype, name, "remarks", MARKER, update_modified=False)
			with self.assertRaises(frappe.ValidationError):
				rsvc.approve_usage(usage)
		finally:
			frappe.set_user("Administrator")

		leaked = frappe.db.get_value(doctype, name, "remarks")
		if leaked == MARKER:  # 旧实现会把挂起写入一并提交
			frappe.db.set_value(doctype, name, "remarks", original, update_modified=False)
			frappe.db.commit()
		self.assertEqual(original, leaked,
						 "拦截前的挂起业务写入被提交了 —— 事务原子性被破坏（L10-P0-01）")

	def test_delete_interception_keeps_record_and_audits(self):
		"""主数据删除拦截（on_trash 内）：记录仍在，挂起写入不泄漏，且新增「删除拦截」审计。

		`on_trash` 是挂起状态最多的上下文（外层删除流程本身就在同一事务里），
		因此这里同时观测「拦截前的挂起业务写入不得被顺手提交」。
		"""
		record = self._find_protected_record()
		doctype, name = self._pending_write_target()
		if not record or not doctype:
			self.skipTest("缺少 {} 记录或挂起写入目标".format(PROTECTED_DOCTYPE))
		before_audits = self._audit_count("删除拦截", record)
		original = frappe.db.get_value(doctype, name, "remarks")

		frappe.set_user(MGR)
		try:
			frappe.db.set_value(doctype, name, "remarks", MARKER, update_modified=False)
			with self.assertRaises(frappe.ValidationError) as ctx:
				frappe.delete_doc(PROTECTED_DOCTYPE, record, ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

		self.assertIn("不允许删除", str(ctx.exception))
		self.assertTrue(frappe.db.exists(PROTECTED_DOCTYPE, record),
						"删除被拦截后记录必须仍然存在")
		self.assertEqual(before_audits + 1, self._audit_count("删除拦截", record),
						 "删除拦截必须留下审计（on_trash 上下文）")
		leaked = frappe.db.get_value(doctype, name, "remarks")
		if leaked == MARKER:  # 旧实现会把挂起写入一并提交
			frappe.db.set_value(doctype, name, "remarks", original, update_modified=False)
			frappe.db.commit()
		self.assertEqual(original, leaked,
						 "on_trash 内的挂起业务写入被提交了 —— 事务原子性被破坏（L10-P0-01）")


if __name__ == "__main__":
	unittest.main()
