# -*- coding: utf-8 -*-
"""L10-P0-02 审计指纹语义与外部锚定实机验证。

缺陷：`_checksum()` 用未加密的 sha1，且只覆盖 7 个字段 —— `action_text` /
`field_changed` / `reason` **不在覆盖内**，改这三个字段检不出来；指纹与内容同库同行，
有 DB 直写权限者可同时改写两者；而代码/文案却称之为「防篡改」。

本轮口径（Owner 选定：完整性校验 + 轻量外部锚定）：
- 指纹升为 sha256 且覆盖全部载荷字段；历史行按其原 v1 算法仍可校验；
- 逐行记录 `checksum_version`，校验接口同时统计 legacy 行数；
- 全量历史摘要 + 行数每日锚定到**数据库之外**的 append-only 文件，使「仅 DB 写权限」
  的删除 / 改写暴露；并明确不宣称强防篡改。

覆盖：
- v2 ×2：新行按 v2 落库并校验通过；篡改 `action_text`（v1 漏掉的字段）被检出；
- 历史 ×1：v1 旧行仍可按原算法校验，且被计为 legacy；
- 锚定 ×2：锚定后对账通过；删行后对账失败（能指出是删除），回滚后恢复通过。

执行方式（需要 Frappe 运行时，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_lims_audit_integrity_runtime.py
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

try:  # 宿主机无 frappe：静默降级，不得抛异常
	import frappe
except ImportError:  # pragma: no cover - 离线门禁路径
	frappe = None


_SMOKE_READY = frappe is not None and os.environ.get("HBOS_FRAPPE_SMOKE") == "1"

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MGR = "r7c-mgr@test.local"  # LIMS Manager（校验接口允许的质量角色）
STAMP = "TEST-HBOS-P002"
DOC_NAME = f"{STAMP}-AUDIT-SENTINEL"


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
class TestAuditIntegrityRuntime(unittest.TestCase):
	"""指纹版本语义 + 篡改检出 + 外部锚定对账。

	审计日志为 append-only，本用例产生的「创建」审计行不清理（也不允许清理）。
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

		from hb_lims_app.hbos_lims import audit_anchor_service as anchor
		from hb_lims_app.hbos_lims import lims_service as svc

		cls.svc = svc
		cls.anchor = anchor
		cls.tmpdir = tempfile.mkdtemp(prefix="hbos-anchor-test-")
		cls.anchor_path = os.path.join(cls.tmpdir, "anchor.log")
		if not frappe.db.exists("User", MGR):
			raise AssertionError("缺少测试用户 {}".format(MGR))

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		shutil.rmtree(cls.tmpdir, ignore_errors=True)
		if cls.initialized_here:
			frappe.destroy()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _row(self, name):
		return frappe.db.get_value(
			"HBOS Audit Log", name,
			["name", "action_text", "checksum", "checksum_version"], as_dict=True)

	# ------------------------------------------------------------------
	# 用例 01：新行走 v2 且可校验
	# ------------------------------------------------------------------

	def test_01_new_rows_use_v2_and_verify(self):
		"""新写入的审计行按 v2（sha256 全字段）落库，校验通过。"""
		frappe.set_user("Administrator")
		# commit=True：该行是后续用例（篡改检出、锚定对账）的观测对象，必须落库留存
		name = self.svc.audit_log("修改", "HBOS Sample", DOC_NAME,
								  action_text="P002 完整性校验用例",
								  field_changed="remarks", old_value="", new_value="x",
								  reason="P002 用例", commit=True)
		row = self._row(name)
		self.assertEqual("2", str(row.checksum_version or ""), "新行须记录 v2")
		self.assertEqual(64, len(row.checksum or ""), "sha256 十六进制应为 64 位")

		frappe.set_user(MGR)
		result = self.svc.verify_audit_integrity(name=name)
		frappe.set_user("Administrator")
		self.assertEqual(1, result["checked"])
		self.assertEqual([], result["mismatched"])
		self.assertEqual(0, result["legacy"])

	# ------------------------------------------------------------------
	# 用例 02：v1 历史行仍可校验
	# ------------------------------------------------------------------

	def test_02_legacy_rows_still_verify(self):
		"""历史行按原 v1 算法校验（覆盖字段较少），并被计为 legacy。"""
		legacy = frappe.db.sql(
			"select name from `tabHBOS Audit Log`"
			" where ifnull(checksum_version, '') = '' order by created_at asc limit 1",
			as_list=True)
		if not legacy:
			self.skipTest("站点已无 v1 历史行")
		frappe.set_user(MGR)
		result = self.svc.verify_audit_integrity(name=legacy[0][0])
		frappe.set_user("Administrator")
		self.assertEqual(1, result["checked"])
		self.assertEqual(1, result["legacy"])
		self.assertEqual([], result["mismatched"], "历史行须仍可按 v1 校验")

	# ------------------------------------------------------------------
	# 用例 03：v1 漏掉的字段被篡改 —— v2 能检出
	# ------------------------------------------------------------------

	def test_03_tampering_previously_uncovered_field_is_detected(self):
		"""低层直写 `action_text`（v1 完全覆盖不到的字段）必须被 v2 指纹检出。"""
		frappe.set_user("Administrator")
		rows = frappe.get_all("HBOS Audit Log", filters={"doc_name": DOC_NAME},
							  pluck="name", limit_page_length=1, order_by="creation desc")
		self.assertTrue(rows, "用例 01 应已写入审计行")
		name = rows[0]
		self.assertEqual([], self._verify_as_mgr(name)["mismatched"])

		# 绕过 validate 的直写（模拟 DB 级改写）：改的正是 v1 未覆盖的 action_text
		frappe.db.set_value("HBOS Audit Log", name, "action_text", "被改写的摘要",
							update_modified=False)
		self.assertEqual([name], self._verify_as_mgr(name)["mismatched"],
						 "action_text 被改写必须检出")
		frappe.db.rollback()
		self.assertEqual([], self._verify_as_mgr(name)["mismatched"], "回滚后应恢复一致")

	def _verify_as_mgr(self, name):
		frappe.set_user(MGR)
		try:
			return self.svc.verify_audit_integrity(name=name)
		finally:
			frappe.set_user("Administrator")

	# ------------------------------------------------------------------
	# 用例 04：外部锚定检出历史变化
	# ------------------------------------------------------------------

	def test_04_anchor_detects_history_change(self):
		"""锚定后对账通过；删行（DB 级）后对账失败并指出删除；回滚后恢复。"""
		frappe.set_user("Administrator")
		written = self.anchor.write_anchor_at(path=self.anchor_path, source="test")
		self.assertEqual(frappe.db.count("HBOS Audit Log"), written["rows"])

		verdict = self.anchor.verify_anchor_at(path=self.anchor_path)
		self.assertTrue(verdict["ok"], verdict.get("reason"))

		# 删掉一条审计行（DB 级，绕过 on_trash 保护），对账必须失败
		rows = frappe.get_all("HBOS Audit Log", filters={"doc_name": DOC_NAME},
							  pluck="name", limit_page_length=1)
		frappe.db.sql("delete from `tabHBOS Audit Log` where name=%s", rows[0])
		self.assertEqual(frappe.db.count("HBOS Audit Log"), written["rows"] - 1)
		verdict = self.anchor.verify_anchor_at(path=self.anchor_path)
		self.assertFalse(verdict["ok"], "删行后对账必须失败")
		self.assertIn("更少", verdict["reason"])

		frappe.db.rollback()
		self.assertTrue(self.anchor.verify_anchor_at(path=self.anchor_path)["ok"],
						"回滚后对账应恢复通过")

	def test_05_anchor_chain_detects_edited_anchor_line(self):
		"""锚定行自身串链：改动历史锚定行会使链校验失败。"""
		frappe.set_user("Administrator")
		self.anchor.write_anchor_at(path=self.anchor_path, source="test")
		self.assertTrue(self.anchor.verify_anchor_at(path=self.anchor_path)["ok"])

		with open(self.anchor_path, encoding="utf-8") as handle:
			lines = [line for line in handle if line.strip()]
		first = json.loads(lines[0])
		first["rows"] = 99999  # 改行数即改内容，锚定哈希随之不符
		with open(self.anchor_path, "w", encoding="utf-8") as handle:
			handle.write(json.dumps(first, ensure_ascii=False, sort_keys=True) + "\n")
			handle.writelines(lines[1:])
		verdict = self.anchor.verify_anchor_at(path=self.anchor_path)
		self.assertFalse(verdict["ok"], "锚定行被改动必须检出")
		self.assertIn("锚定", verdict["reason"])


if __name__ == "__main__":
	unittest.main()
