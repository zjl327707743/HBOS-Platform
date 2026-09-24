# -*- coding: utf-8 -*-
"""M2-R3/R6 系统字段守卫离线契约测试（补充轮）。

背景：检验流程 5 个 DocType（Sample / Sample Task / Test Result / COA / Specification）
按方案 8.6 保留 DocType 层 create/write，但当时没有 R8 那样的系统字段守卫，
状态与签署字段可被 `frappe.client.set_value` 直接改写，绕过 lims_service 的状态机、
SoD 与电子签名写入（即「伪造审批」）。本轮按 R8 既有机制补齐控制器层守卫。

覆盖：
- 5 个字段集的组成契约（状态 + 签署 + 版本链）
- 5 个控制器已接线 guard_system_fields
- lims_service 中受守卫 DocType 的每个保存点都有服务放行标记
  （防未来新增保存点遗漏——遗漏会被守卫拦下并中断业务流程）
- guards 中性入口与 stability_guards 实现的一致性

本测试不依赖 Frappe，可在宿主机直接运行。
"""

import ast
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import workflow_contract as wf

LIMS_SERVICE = APP_ROOT / "hb_lims_app" / "hbos_lims" / "lims_service.py"
GUARDS = APP_ROOT / "hb_lims_app" / "hbos_lims" / "guards.py"
STABILITY_GUARDS = APP_ROOT / "hb_lims_app" / "hbos_lims" / "stability_guards.py"
DOCTYPES = APP_ROOT / "hb_lims_app" / "hbos_lims" / "doctype"

# 字段集常量名 -> 该 DocType 的状态字段（必须有）
FIELD_SETS = {
	"HBOS_SAMPLE_SYSTEM_FIELDS": "status",
	"HBOS_SAMPLE_TASK_SYSTEM_FIELDS": "status",
	"HBOS_TEST_RESULT_SYSTEM_FIELDS": "result_status",
	"HBOS_COA_SYSTEM_FIELDS": "report_status",
	"HBOS_SPECIFICATION_SYSTEM_FIELDS": "status",
}

# 控制器源文件 -> 该文件必须引用的字段集常量名
CONTROLLERS = {
	"hbos_sample/hbos_sample.py": "HBOS_SAMPLE_SYSTEM_FIELDS",
	"hbos_sample_task/hbos_sample_task.py": "HBOS_SAMPLE_TASK_SYSTEM_FIELDS",
	"hbos_test_result/hbos_test_result.py": "HBOS_TEST_RESULT_SYSTEM_FIELDS",
	"hbos_coa/hbos_coa.py": "HBOS_COA_SYSTEM_FIELDS",
	"hbos_specification/hbos_specification.py": "HBOS_SPECIFICATION_SYSTEM_FIELDS",
}

# lims_service 内指向受守卫 DocType 的局部变量名
GUARDED_VARS = ("sample", "task", "result", "coa", "spec", "new_doc", "old")

# 允许不带放行标记的保存点：该处不修改任何系统字段
NO_FLAG_NEEDED = {
	# 仅回填子表 task 指针，样品状态不变（状态推进由 register_sample / start_task 负责）
	("generate_tasks", "sample"),
}

SAVE_METHODS = ("save", "insert")


def _source(path):
	return path.read_text(encoding="utf-8")


class TestFieldSetContract(unittest.TestCase):
	def test_every_set_declares_its_state_field(self):
		for name, state_field in FIELD_SETS.items():
			fields = getattr(wf, name)
			self.assertIn(state_field, fields, f"{name} 缺状态字段 {state_field}")
			self.assertTrue(fields[0] == state_field,
							f"{name} 状态字段应为首项（便于审阅）")

	def test_composition_is_state_plus_signature_plus_version_chain(self):
		"""字段集组成固定：状态 + 签署 + 版本链；业务判定数据（verdict/result_value 等）
		不在其中——那类字段由 RESULT_LOCKED_FIELDS 在提交后锁定，属另一机制。"""
		self.assertEqual(wf.HBOS_SAMPLE_SYSTEM_FIELDS, ("status", "oos_locked"))
		self.assertEqual(wf.HBOS_SAMPLE_TASK_SYSTEM_FIELDS,
						 ("status", "assignee", "assigned_by", "assigned_date", "result"))
		self.assertEqual(wf.HBOS_TEST_RESULT_SYSTEM_FIELDS, (
			"result_status", "is_oos_candidate", "superseded_by",
			"submitted_signature", "submitted_at",
			"reviewer", "reviewed_signature", "reviewed_at",
			"approver", "approved_signature", "approved_at",
		))
		self.assertEqual(wf.HBOS_COA_SYSTEM_FIELDS, (
			"report_status", "qa_reviewer", "qa_reviewed_at",
			"published_by", "published_at", "pdf_attachment",
		))
		self.assertEqual(wf.HBOS_SPECIFICATION_SYSTEM_FIELDS, ("status", "effective_date"))

	def test_no_collision_with_stability_field_sets(self):
		"""稳定性板块 stability_guards 持有自己的同名业务对象字段集，
		两者语义不同，命名必须可区分（禁止同名漂移）。"""
		src = _source(STABILITY_GUARDS)
		for name in FIELD_SETS:
			self.assertNotIn(f"\n{name} = (", src,
							 f"stability_guards 出现同名常量 {name}，与检验流程字段集混淆")


class TestControllerWiring(unittest.TestCase):
	def test_controllers_import_neutral_guard_entry(self):
		for rel, const in CONTROLLERS.items():
			src = _source(DOCTYPES / rel)
			with self.subTest(controller=rel):
				self.assertIn("from hb_lims_app.hbos_lims.guards import guard_system_fields",
							  src, "应经中性入口 guards 引入守卫，避免误以为依赖稳定性板块")
				self.assertIn(f"guard_system_fields(self, wf.{const})", src,
							  f"validate 未接线 {const}")

	def test_guard_is_called_inside_validate(self):
		for rel in CONTROLLERS:
			tree = ast.parse(_source(DOCTYPES / rel), filename=rel)
			cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
			validate = next((n for n in cls.body
							 if isinstance(n, ast.FunctionDef) and n.name == "validate"), None)
			with self.subTest(controller=rel):
				self.assertIsNotNone(validate, "控制器缺 validate")
				called = [d for d in ast.walk(validate)
						  if isinstance(d, ast.Call)
						  and getattr(d.func, "id", None) == "guard_system_fields"]
				self.assertTrue(called, "validate 内未调用 guard_system_fields")

	def test_guards_module_reexports_single_implementation(self):
		"""中性入口只做再导出，实现唯一（避免两套守卫逻辑分叉）。"""
		src = _source(GUARDS)
		self.assertIn("from hb_lims_app.hbos_lims.stability_guards import guard_system_fields", src)
		self.assertNotIn("def guard_system_fields", src)
		self.assertIn("def guard_system_fields", _source(STABILITY_GUARDS))


class TestServiceAuthorizationFlags(unittest.TestCase):
	"""受守卫 DocType 的每个保存点必须显式声明服务放行，否则保存会被守卫拦下。"""

	@classmethod
	def setUpClass(cls):
		cls.src = _source(LIMS_SERVICE)
		cls.tree = ast.parse(cls.src, filename=str(LIMS_SERVICE))

	def _functions(self):
		for node in ast.walk(self.tree):
			if isinstance(node, ast.FunctionDef):
				yield node

	@staticmethod
	def _authorized_vars(func):
		"""收集函数体内 `X.flags.allow_system_fields = True` 的 X。"""
		names = set()
		for node in ast.walk(func):
			if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
				continue
			if node.value.value is not True:
				continue
			for tgt in node.targets:
				inner = getattr(tgt, "value", None)  # X.flags
				if (isinstance(tgt, ast.Attribute) and tgt.attr == "allow_system_fields"
						and isinstance(inner, ast.Attribute) and inner.attr == "flags"
						and isinstance(inner.value, ast.Name)):
					names.add(inner.value.id)
		return names

	@staticmethod
	def _save_sites(func):
		"""收集函数体内 `X.save(...)` / `X.insert(...)`（含 ignore_permissions 与否）。"""
		sites = set()
		for node in ast.walk(func):
			if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
					and node.func.attr in SAVE_METHODS
					and isinstance(node.func.value, ast.Name)
					and node.func.value.id in GUARDED_VARS):
				sites.add(node.func.value.id)
		return sites

	def test_every_guarded_save_site_is_authorized(self):
		missing = []
		for func in self._functions():
			authorized = self._authorized_vars(func)
			for var in self._save_sites(func):
				if var in authorized:
					continue
				if (func.name, var) in NO_FLAG_NEEDED:
					continue
				missing.append(f"{func.name}(): {var}")
		self.assertEqual(
			missing, [],
			"以下保存点缺少 doc.flags.allow_system_fields = True，会被系统字段守卫拦下："
			+ ", ".join(missing))

	def test_authorization_uses_the_documented_flag_name(self):
		"""放行标记名与 R8 stability_service 保持一致，禁止另造机制。"""
		self.assertIn("allow_system_fields", self.src)
		self.assertNotIn("hbos_skip_guard", self.src)

	def test_no_flag_on_unguarded_framework_writes(self):
		"""非受守卫对象（File / Result Revision / Audit Log）不需要也不应加放行标记。"""
		for func in self._functions():
			if func.name == "publish_coa":
				self.assertNotIn("file_doc", self._authorized_vars(func))


if __name__ == "__main__":
	unittest.main()
