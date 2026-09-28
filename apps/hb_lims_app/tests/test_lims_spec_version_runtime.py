# -*- coding: utf-8 -*-
"""L10-P0-04 质量标准内容冻结与版本链实机验证（真实 Frappe 会话 + 非特权用户）。

缺陷：`HBOS Specification` 控制器只守卫 `status/effective_date`、校验版本唯一与限度
逻辑，未禁止「已生效/已废止」标准的业务内容原地修改；而 LIMS Manager 拥有该 DocType
write 权限，`update_specification` 的文案更明确写着「编辑内容不改版本号」。于是会出现
`SPEC-A V1.0` 已生效后被改掉检验项目/限度/物料，名字仍是 V1.0 —— 同一版本号代表两份
内容，且前端「升版」只是复制一份，不记录任何版本关系。

为什么必须实机跑：内容冻结依赖控制器的 `validate()`（`get_doc_before_save()` 前后值
比较）与真实状态流转；离线契约只能断言接线。且守卫不设特权旁路，用 Administrator 跑
等于什么都没验证。

覆盖：
- 冻结 ×4：已生效标准的头字段直写、检验项目子表直改、备注直改、服务层修订接口；
- 冻结 ×1：已废止标准同样不可原地改；
- 版本链 ×3：并行生效被拒、升版未声明被替代版本被拒、声明后「先废止再生效」成立；
- 快照 ×2：升版后新样品引用新版本，历史样品仍指旧版本且内容为旧版快照。

数据一律 `TEST-HBOS-P004-` 前缀，用例结束后按依赖顺序清理。
审计日志为 append-only 设计，其留痕不清理（也不允许清理）。

执行方式（需要 Frappe 运行时，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_lims_spec_version_runtime.py
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

MGR = "r7c-mgr@test.local"  # LIMS Manager（非 System Manager）

STAMP = "TEST-HBOS-P004"
CODE_FROZEN = f"{STAMP}-F1"   # 内容冻结用例
CODE_UPGRADE = f"{STAMP}-F2"  # 版本链用例


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
class TestSpecificationVersionRuntime(unittest.TestCase):
	"""质量标准：受控状态内容冻结 + 版本链 + 样品快照不漂移。"""

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
		cls.specs = []
		cls.samples = []
		if not frappe.db.exists("User", MGR):
			raise AssertionError("缺少非特权测试用户 {}".format(MGR))
		if "System Manager" in set(frappe.get_roles(MGR)):
			raise AssertionError("{} 含 System Manager，无法验证守卫".format(MGR))
		cls._drop_stale_fixtures()

	@classmethod
	def _drop_stale_fixtures(cls):
		"""清理上次异常中断残留的本轮夹具，使套件可重复运行。

		本轮标准命名固定（spec_code + 版本，autoname 派生），清理又是尽力而为、
		不抛错；一旦残留，下次运行就会在 create_specification 撞重复主键，
		整套用例一并报错。
		"""
		frappe.set_user("Administrator")
		for sample in frappe.get_all("HBOS Sample",
									 filters={"material_code": ["like", f"{STAMP}%"]},
									 pluck="name", limit_page_length=0):
			_force_delete("HBOS Sample", sample)
		for spec in frappe.get_all("HBOS Specification",
								   filters={"spec_code": ["like", f"{STAMP}%"]},
								   pluck="name", limit_page_length=0):
			_force_delete("HBOS Specification", spec)
		frappe.db.commit()

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
	def _create_spec(cls, code, version, supersedes=None):
		frappe.set_user(MGR)
		items = frappe.get_all("HBOS Test Item", pluck="name", limit_page_length=1)
		if not items:
			raise AssertionError("缺少主数据 HBOS Test Item")
		# 仅在确有血缘时传 supersedes：否则夹具会因「参数不存在」而失败，
		# 掩盖真正要断言的守卫行为（反向验证时已踩到）。
		payload = {
			"spec_code": code, "spec_name": f"{STAMP} 规格 {version}",
			"material_code": f"{code}-MAT", "material_name": "P004 测试物料",
			"standard_source": "企业内控", "version": version,
			"effective_date": frappe.utils.today(),
			"items": [{"item": items[0], "item_name": items[0], "limits_type": "上限",
					   "upper_limit": 100, "unit": "mg", "significant_digits": 2}],
			"remarks": "P004 备注",
		}
		if supersedes:
			payload["supersedes"] = supersedes
		name = cls.svc.create_specification(**payload)
		cls.specs.append(name)
		return name

	@classmethod
	def _create_sample(cls, spec_name):
		frappe.set_user(MGR)
		sample_type = frappe.get_all("HBOS Sample Type", pluck="name", limit_page_length=1)
		if not sample_type:
			raise AssertionError("缺少主数据 HBOS Sample Type")
		name = cls.svc.register_sample(
			sample_type=sample_type[0], material_code=f"{STAMP}-MAT",
			material_name="P004 测试物料", batch_no=f"{STAMP}-B01",
			sample_source="生产取样", specification=spec_name, priority="常规")
		cls.samples.append(name)
		return name

	def _assert_blocked(self, message_part, fn):
		"""执行 fn，断言被拦下且抛出信息含 message_part。"""
		with self.assertRaises(frappe.ValidationError) as ctx:
			fn()
		self.assertIn(message_part, str(ctx.exception))
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ------------------------------------------------------------------
	# 内容冻结：已生效 / 已废止
	# ------------------------------------------------------------------

	def test_active_spec_content_is_frozen(self):
		"""已生效标准：头字段直写、检验项目子表、备注、服务层修订一律拒绝。"""
		frappe.set_user(MGR)
		spec = self._create_spec(CODE_FROZEN, "1.0")
		self.svc.activate_specification(spec)
		self.assertEqual("已生效", frappe.db.get_value("HBOS Specification", spec, "status"))

		# 1) 头字段直写（审计原例：改物料 / 标准来源）
		self._assert_blocked("不可修改", lambda: frappe.client.set_value(
			"HBOS Specification", spec, json.dumps({"material_name": "被篡改的物料"})))

		# 2) 检验项目子表直改（审计原例：改检验项目 / 限度）
		def _tamper_child():
			doc = frappe.get_doc("HBOS Specification", spec)
			doc.items[0].upper_limit = 999
			doc.save(ignore_permissions=True)
		self._assert_blocked("不可增删改", _tamper_child)

		# 3) 备注（Owner 决定：一并冻结）
		self._assert_blocked("不可修改", lambda: frappe.client.set_value(
			"HBOS Specification", spec, json.dumps({"remarks": "生效后补写"})))

		# 4) 服务层修订接口（原实现允许原地改内容且版本号不变）
		self._assert_blocked("不可原地修订", lambda: self.svc.update_specification(
			spec, spec_name_label="改名", material_name="被篡改的物料"))

		frappe.set_user("Administrator")
		doc = frappe.get_doc("HBOS Specification", spec)
		self.assertNotIn("篡改", str(doc.material_name or ""), "拦截后物料不得被改写")
		self.assertEqual(100, doc.items[0].upper_limit, "拦截后限度必须保持原值")

	def test_obsolete_spec_content_is_frozen_and_sample_snapshot_kept(self):
		"""已废止标准同样冻结；冻结后样品持有的版本快照不漂移。"""
		frappe.set_user(MGR)
		spec = self._create_spec(CODE_FROZEN + "-OBS", "1.0")
		self.svc.activate_specification(spec)
		sample = self._create_sample(spec)
		frappe.set_user("Administrator")
		self.assertEqual("1.0", frappe.db.get_value("HBOS Sample", sample, "spec_version"))

		frappe.set_user(MGR)
		self.svc.obsolete_specification(spec)
		self.assertEqual("已废止", frappe.db.get_value("HBOS Specification", spec, "status"))
		self._assert_blocked("不可修改", lambda: frappe.client.set_value(
			"HBOS Specification", spec, json.dumps({"material_name": "废止后篡改"})))
		self._assert_blocked("不可原地修订", lambda: self.svc.update_specification(
			spec, remarks="废止后补写"))

		frappe.set_user("Administrator")
		self.assertEqual("1.0", frappe.db.get_value("HBOS Specification", spec, "version"))
		self.assertEqual("1.0", frappe.db.get_value("HBOS Sample", sample, "spec_version"),
						 "历史样品应继续指向旧版本且版本号不变")

	# ------------------------------------------------------------------
	# 版本链：单一生效版本 + 升版必须留血缘
	# ------------------------------------------------------------------

	def test_upgrade_requires_lineage_and_single_active_version(self):
		"""升版：并行生效被拒 → 未声明被替代版本被拒 → 先废止再生效成立。"""
		frappe.set_user(MGR)
		v1 = self._create_spec(CODE_UPGRADE, "1.0")
		self.svc.activate_specification(v1)
		sample_v1 = self._create_sample(v1)
		snapshot_v1 = frappe.db.get_value("HBOS Sample", sample_v1, "spec_version")

		# 并行生效：新版本未声明血缘即激活 → 先撞"已有生效版本"
		v2_bare = self._create_spec(CODE_UPGRADE, "2.0")
		self._assert_blocked("已有生效版本", lambda: self.svc.activate_specification(v2_bare))

		# 废止旧版后，仍缺版本链 → 拒绝
		frappe.set_user(MGR)
		self.svc.obsolete_specification(v1)
		self._assert_blocked("必须声明「被替代的版本」",
							 lambda: self.svc.activate_specification(v2_bare))

		# 删掉无血缘的草稿，改用声明 supersedes 的升版
		frappe.set_user(MGR)
		self.svc.delete_specification(v2_bare)
		self.specs.remove(v2_bare)
		v2 = self._create_spec(CODE_UPGRADE, "2.0", supersedes=v1)
		self.svc.activate_specification(v2)
		frappe.set_user("Administrator")
		self.assertEqual("已生效", frappe.db.get_value("HBOS Specification", v2, "status"))
		self.assertEqual(v1, frappe.db.get_value("HBOS Specification", v2, "supersedes"),
						 "升版必须保留被替代版本关系")
		self.assertEqual("已废止", frappe.db.get_value("HBOS Specification", v1, "status"))

		# 版本链字段受系统字段守卫保护，不得直写
		frappe.set_user(MGR)
		self._assert_blocked("系统字段", lambda: frappe.client.set_value(
			"HBOS Specification", v2, json.dumps({"supersedes": None})))

		# 新样品引用新版本；历史样品仍指旧版本（审计第 4 条）
		sample_v2 = self._create_sample(v2)
		frappe.set_user("Administrator")
		self.assertEqual("2.0", frappe.db.get_value("HBOS Sample", sample_v2, "spec_version"))
		self.assertEqual(v2, frappe.db.get_value("HBOS Sample", sample_v2, "specification"))
		self.assertEqual(v1, frappe.db.get_value("HBOS Sample", sample_v1, "specification"))
		self.assertEqual(snapshot_v1,
						 frappe.db.get_value("HBOS Sample", sample_v1, "spec_version"),
						 "升版后历史样品不得跟随新版本漂移")

	# ------------------------------------------------------------------
	# 清理（依赖顺序：样品 → 标准）
	# ------------------------------------------------------------------

	@classmethod
	def _cleanup(cls):
		frappe.set_user("Administrator")
		for name in cls.samples:
			_force_delete("HBOS Sample", name)
		for name in cls.specs:
			_force_delete("HBOS Specification", name)
		frappe.db.commit()


def _force_delete(doctype, name):
	if not frappe.db.exists(doctype, name):
		return
	try:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
	except Exception as exc:  # 清理失败不得掩盖验证结论，但要显式暴露
		frappe.log_error(f"清理 {doctype} {name} 失败：{exc}", "HBOS P0-04 质量标准验证清理")


if __name__ == "__main__":
	unittest.main()
