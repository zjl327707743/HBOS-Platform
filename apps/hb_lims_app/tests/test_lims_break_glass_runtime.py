# -*- coding: utf-8 -*-
"""L10-P0-06 系统字段守卫取消角色旁路 + 受审计应急处置实机验证。

缺陷：通用 `guard_system_fields()` 依赖 `stability_guards._privileged()` 对
**Administrator 与 System Manager 短路放行**，于是技术管理员可绕过「系统字段只能由
业务服务写入」直接改状态 / 签署 / 版本链。留样样品自带的 `_guard_system_fields()`
是同一缺陷的第三处。技术管理员与质量批准人不是同一概念。

为什么必须实机跑：本项要证明的正是「身份不再换权限」，必须在真实会话与真实角色下
验证 —— 用 Administrator 跑等于验证「旁路还在不在」，而它已经不该在。

覆盖（用例带序号，顺序即流程，故意如此）：
- 旁路已取消 ×3：System Manager 经 `frappe.client.set_value` / 直接 save 均被拦；
  Administrator 同样被拦；
- 应急处置闸门 ×4：非技术角色拒绝、缺理由拒绝、未登记 DocType 拒绝、未登记字段
  （业务内容）拒绝并按「越权拦截」留痕；
- 应急处置正路 ×1：技术管理员带理由修改成功，且逐字段留下「应急处置」审计
  （前后值 + 理由 + 操作人）。

数据一律 `TEST-HBOS-P006-` 前缀，用例结束后清理。

执行方式（需要 Frappe 运行时，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_lims_break_glass_runtime.py
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

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MGR = "r7c-mgr@test.local"      # LIMS Manager（质量角色，非技术管理员）
SYSADMIN = "r7audit@test.local"  # System Manager（技术管理员，非质量批准人）

STAMP = "TEST-HBOS-P006"
SPEC_CODE = f"{STAMP}-SPEC"
REASON = f"{STAMP} 应急处置：修正误置状态"


def _ensure_app_on_path():
	"""幂等把 `hb_lims_app` 解析到真正的 App 包（见其余 runtime 用例的同一说明）。"""
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
class TestBreakGlassRuntime(unittest.TestCase):
	"""技术管理员不再自动拥有质量绕过权；应急改动走受审计的 break-glass。"""

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
		for user in (MGR, SYSADMIN):
			if not frappe.db.exists("User", user):
				raise AssertionError("缺少测试用户 {}".format(user))
		if "System Manager" not in set(frappe.get_roles(SYSADMIN)):
			raise AssertionError("{} 不是 System Manager，无法验证旁路已取消".format(SYSADMIN))
		if "System Manager" in set(frappe.get_roles(MGR)):
			raise AssertionError("{} 不应含 System Manager".format(MGR))

		frappe.set_user("Administrator")
		cls._drop_stale_fixtures()
		cls._build_fixture()
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
		for spec in frappe.get_all("HBOS Specification",
								   filters={"spec_code": ["like", f"{STAMP}%"]},
								   pluck="name", limit_page_length=0):
			_force_delete("HBOS Specification", spec)
		frappe.db.commit()

	@classmethod
	def _build_fixture(cls):
		"""建一份草稿质量标准：其 `status` 属系统字段，正好用于验证旁路与应急处置。"""
		items = frappe.get_all("HBOS Test Item", pluck="name", limit_page_length=1)
		if not items:
			raise AssertionError("缺少主数据 HBOS Test Item")
		frappe.set_user(MGR)
		spec = cls.svc.create_specification(
			spec_code=SPEC_CODE, spec_name=f"{STAMP} 规格", material_code=f"{STAMP}-MAT",
			material_name="P006 测试物料", standard_source="企业内控", version="1.0",
			effective_date=frappe.utils.today(),
			items=[{"item": items[0], "item_name": items[0], "limits_type": "上限",
					"upper_limit": 100, "unit": "mg", "significant_digits": 2}])
		cls.artifacts["spec"] = spec
		frappe.set_user("Administrator")
		if frappe.db.get_value("HBOS Specification", spec, "status") != "草稿":
			raise AssertionError("夹具异常：草稿标准未处于草稿状态")

	# ------------------------------------------------------------------
	# 断言助手（执行前显式切换身份，避免残留身份让守卫短路）
	# ------------------------------------------------------------------

	def _assert_blocked(self, message_part, fn, as_user):
		frappe.set_user(as_user)
		try:
			with self.assertRaises(frappe.ValidationError) as ctx:
				fn()
		finally:
			frappe.set_user("Administrator")
		self.assertIn(message_part, str(ctx.exception))
		frappe.db.rollback()

	# ------------------------------------------------------------------
	# 用例 01：角色旁路已取消
	# ------------------------------------------------------------------

	def test_01_system_manager_and_admin_cannot_bypass(self):
		"""System Manager 与 Administrator 直接改系统字段均被拦下。"""
		spec = self.artifacts["spec"]

		# 1) System Manager 经 frappe.client.set_value 直写状态
		self._assert_blocked("系统字段", lambda: frappe.client.set_value(
			"HBOS Specification", spec, json.dumps({"status": "已生效"})), as_user=SYSADMIN)

		# 2) System Manager 直接 save
		def _sm_save():
			doc = frappe.get_doc("HBOS Specification", spec)
			doc.status = "已生效"
			doc.save(ignore_permissions=True)
		self._assert_blocked("系统字段", _sm_save, as_user=SYSADMIN)

		# 3) Administrator 同样不得直改（技术管理员 ≠ 质量批准人）
		self._assert_blocked("系统字段", lambda: frappe.client.set_value(
			"HBOS Specification", spec, json.dumps({"status": "已生效"})),
			as_user="Administrator")

		frappe.set_user("Administrator")
		self.assertEqual("草稿", frappe.db.get_value("HBOS Specification", spec, "status"),
						 "拦截后状态必须保持原值")

	# ------------------------------------------------------------------
	# 用例 02：应急处置的四道闸门
	# ------------------------------------------------------------------

	def test_02_break_glass_guards(self):
		"""非技术角色 / 缺理由 / 未登记 DocType / 未登记字段，四者皆拒绝。"""
		spec = self.artifacts["spec"]

		# 1) 质量角色（LIMS Manager）不得调用
		self._assert_blocked("没有执行「break_glass_update」的权限",
							 lambda: self.svc.break_glass_update(
								 "HBOS Specification", spec,
								 json.dumps({"status": "已生效"}), REASON),
							 as_user=MGR)

		# 2) 技术管理员缺理由
		self._assert_blocked("必须填写理由", lambda: self.svc.break_glass_update(
			"HBOS Specification", spec, json.dumps({"status": "已生效"}), "   "),
			as_user=SYSADMIN)

		# 3) 未登记 DocType（留样样品另有受审计业务路径）
		self._assert_blocked("未登记系统字段", lambda: self.svc.break_glass_update(
			"HBOS Retention Sample", spec, json.dumps({"status": "在库"}), REASON),
			as_user=SYSADMIN)

		# 4) 未登记字段：`remarks` 是业务内容，不在系统字段白名单内 —— 逃生口不得成为
		#    绕过内容冻结（P0-04 / P0-05）的后门
		before_audits = frappe.db.count(
			"HBOS Audit Log", {"log_type": "越权拦截", "doc_name": spec})
		self._assert_blocked("未登记为系统字段", lambda: self.svc.break_glass_update(
			"HBOS Specification", spec, json.dumps({"remarks": "借道改内容"}), REASON),
			as_user=SYSADMIN)
		frappe.set_user("Administrator")
		after_audits = frappe.db.count(
			"HBOS Audit Log", {"log_type": "越权拦截", "doc_name": spec})
		self.assertEqual(before_audits + 1, after_audits,
						 "越界尝试必须按「越权拦截」留痕")
		self.assertEqual("草稿", frappe.db.get_value("HBOS Specification", spec, "status"))
		self.assertNotEqual("借道改内容",
							frappe.db.get_value("HBOS Specification", spec, "remarks"))

	# ------------------------------------------------------------------
	# 用例 03：应急处置正路 —— 成功且逐字段留痕
	# ------------------------------------------------------------------

	def test_03_break_glass_updates_and_audits(self):
		"""技术管理员带理由修改系统字段：生效，并留下含前后值与理由的「应急处置」审计。"""
		spec = self.artifacts["spec"]
		before = frappe.db.count("HBOS Audit Log",
								 {"log_type": "应急处置", "doc_name": spec})

		frappe.set_user(SYSADMIN)
		out = self.svc.break_glass_update(
			"HBOS Specification", spec, json.dumps({"status": "已生效"}), REASON)
		frappe.set_user("Administrator")

		self.assertEqual(["status"], out["changed"])
		self.assertEqual("已生效", frappe.db.get_value("HBOS Specification", spec, "status"))
		rows = frappe.get_all(
			"HBOS Audit Log",
			filters={"log_type": "应急处置", "doc_name": spec, "reason": REASON},
			fields=["field_changed", "old_value", "new_value", "user"])
		self.assertEqual(before + 1, len(rows), "应急处置必须逐字段留痕")
		self.assertEqual("status", rows[0]["field_changed"])
		self.assertEqual("草稿", rows[0]["old_value"])
		self.assertEqual("已生效", rows[0]["new_value"])
		self.assertEqual(SYSADMIN, rows[0]["user"], "审计须记录真实操作人")

	# ------------------------------------------------------------------
	# 清理
	# ------------------------------------------------------------------

	@classmethod
	def _cleanup(cls):
		if not cls.artifacts:
			return
		frappe.set_user("Administrator")
		if cls.artifacts.get("spec"):
			_force_delete("HBOS Specification", cls.artifacts["spec"])
		frappe.db.commit()


def _force_delete(doctype, name):
	if not frappe.db.exists(doctype, name):
		return
	try:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	except Exception as exc:  # 清理失败不得掩盖验证结论，但要显式暴露
		frappe.log_error(f"清理 {doctype} {name} 失败：{exc}", "HBOS P0-06 break-glass 验证清理")


if __name__ == "__main__":
	unittest.main()
