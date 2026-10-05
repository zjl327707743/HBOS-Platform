# -*- coding: utf-8 -*-
"""R7C 处理/使用申请：原生写路径守卫离线契约测试（IAM Phase-3B / L03）。

背景（运行时确认，IAM Phase-3B 隔离实验台）：

    S-SYSTEM-MANAGER 通过 `PUT /api/resource/HBOS Retention Disposal Apply/<name>`
    与 `frappe.client.set_value` 把 status 由「草稿」直接写成「已批准」，
    HTTP 200 且数据库实际落库；qc_supervisor_sign / qc_manager_sign /
    qa_review_sign / qa_manager_sign / qm_sign 全部为 NULL。
    即：规定的审批/签署链、SoD 校验与电子签名留痕被完全绕过。
    `HBOS Retention Usage Apply` 同型（qm_approval 为 NULL）。

同批被测的 `HBOS Test Result` 在同一请求下返回 417 并提示「字段为系统字段，
只能通过业务操作（服务方法）修改」——说明 R3/R6 补齐的守卫机制有效，
R7C 这两个单据只是漏接线（控制器为 `class X(Document): pass`）。

本测试把该缺口固化为契约，离线运行、不依赖 Frappe：

1. 字段集组成契约（状态为首项）
2. 两个控制器经中性入口接线 `guard_system_fields`，且在 `validate` 内调用
3. **审批单据保存覆盖契约（approval document save coverage）**：
   `retention_service` 中凡是 `doc` 实际指向两类审批 DocType 的业务路径，
   其**每个**保存点都必须经 `_service_save` 放行；
   而 `HBOS Retention Sample` / `HBOS Retention Observation` 等非目标 DocType
   继续使用其原有 `doc.save(ignore_permissions=True)`，本轮刻意不改动。
4. 守卫覆盖完整性：任何**带状态字段**的 LIMS DocType，其控制器必须接线守卫，
   否则必须出现在带理由的豁免表中（防再次遗漏）
5. A04 治理不变量：`action_allowed()` 对 System Manager 只放行只读动作，
   即使 ACTION_ROLES 历史声明里仍保留该角色

第 3 项的判定**按 DocType 精确作用域**，而不是「名为 doc 的局部变量一律禁止」——
后者会把无关业务对象的保存点也算作违规，逼迫为统一风格扩大改动范围。
"""

import ast
import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import workflow_contract as wf

HBOS_LIMS = APP_ROOT / "hb_lims_app" / "hbos_lims"
DOCTYPES = HBOS_LIMS / "doctype"
RETENTION_SERVICE = HBOS_LIMS / "retention_service.py"
STABILITY_GUARDS = HBOS_LIMS / "stability_guards.py"

# 字段集常量名 -> 状态字段
FIELD_SETS = {
	"HBOS_RETENTION_DISPOSAL_SYSTEM_FIELDS": "status",
	"HBOS_RETENTION_USAGE_SYSTEM_FIELDS": "status",
}

# 控制器源文件 -> 必须引用的字段集常量名
CONTROLLERS = {
	"hbos_retention_disposal_apply/hbos_retention_disposal_apply.py":
		"HBOS_RETENTION_DISPOSAL_SYSTEM_FIELDS",
	"hbos_retention_usage_apply/hbos_retention_usage_apply.py":
		"HBOS_RETENTION_USAGE_SYSTEM_FIELDS",
}

# 状态字段名（DocType JSON 中出现的状态类字段）
STATE_FIELDS = ("status", "result_status", "report_status")

# 豁免表：DocType -> 理由。故意保持极短——新增豁免必须写明为什么守卫无效。
GUARD_EXEMPT = {
	"hbos_stability_timepoint_delay":
		"仅有 0 条权限行，不存在非 Administrator 的写入路径；而 guard_system_fields "
		"对 Administrator 始终放行，加守卫不产生任何拒绝效果（见表单 status 字段）。",
}

# 审批单据在 retention_service 内的保存放行入口
SERVICE_SAVE_HELPER = "_service_save"

# 受守卫保护的两类审批 DocType（与 retention_service._APPROVAL_DOCTYPES 同源语义）
APPROVAL_DOCTYPES = (
	"HBOS Retention Disposal Apply",
	"HBOS Retention Usage Apply",
)

# doc 由参数传入的 helper：其 DocType 需从调用点回溯。
PARAM_DOC_HELPERS = ("_enter_pending", "_complete_if_signed", "_write_stock_log")

# 审批单据的写路径（14 个函数 / 15 个保存点；approve_disposal 有两个保存点）。
# 这些路径的每个保存点都必须经 _service_save 打标，否则守卫会中断业务流程。
APPROVAL_SAVE_FUNCTIONS = frozenset({
	"submit_usage_apply", "confirm_stock", "approve_usage",
	"execute_usage", "reject_usage", "cancel_usage_apply",
	"submit_disposal_apply", "approve_disposal", "_enter_pending",
	"_dsp_sign", "_complete_if_signed", "continue_retention",
	"reject_disposal", "cancel_disposal_apply",
})

# 非目标 DocType 的写路径：`doc` 实际是 HBOS Retention Sample / Observation。
# 本轮刻意保留其原有 doc.save(ignore_permissions=True)，不得为统一风格改写。
NON_TARGET_SAVE_FUNCTIONS = frozenset({
	"adjust_stock", "select_obs_batch", "cancel_obs_batch",
	"review_observation", "_write_stock_log", "transfer_out",
})


def _source(path):
	return path.read_text(encoding="utf-8")


def _status_bearing_doctypes():
	"""扫描 LIMS DocType JSON，返回带状态字段的目录名列表。"""
	found = []
	for folder in sorted(DOCTYPES.iterdir()):
		spec_file = folder / (folder.name + ".json")
		if not folder.is_dir() or not spec_file.exists():
			continue
		spec = json.loads(_source(spec_file))
		fieldnames = {f.get("fieldname") for f in spec.get("fields", [])}
		if fieldnames & set(STATE_FIELDS):
			found.append(folder.name)
	return found


def _service_functions(tree):
	"""函数名 -> FunctionDef 节点。"""
	return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def _local_var_doctypes(func):
	"""函数内 `x = frappe.get_doc("DocType", ...)` 的局部变量 -> DocType 集合。"""
	mapping = {}
	for node in ast.walk(func):
		if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
			continue
		callee = node.value.func
		name = (callee.attr if isinstance(callee, ast.Attribute)
				else getattr(callee, "id", None))
		if name != "get_doc" or not node.value.args:
			continue
		first = node.value.args[0]
		if not isinstance(first, ast.Constant):
			continue
		for target in node.targets:
			if isinstance(target, ast.Name):
				mapping.setdefault(target.id, set()).add(first.value)
	return mapping


def _resolve_doc_doctypes(tree):
	"""函数名 -> 该函数内 `doc` 实际指向的 DocType 集合。

	参数形式（helper）通过回溯全部调用点的实参变量求解。
	"""
	funcs = _service_functions(tree)
	locals_by_func = {name: _local_var_doctypes(node) for name, node in funcs.items()}

	helper_doctypes = {h: set() for h in PARAM_DOC_HELPERS}
	for fname, node in funcs.items():
		for call in ast.walk(node):
			if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)):
				continue
			if call.func.id not in PARAM_DOC_HELPERS or not call.args:
				continue
			arg = call.args[0]
			if isinstance(arg, ast.Name):
				helper_doctypes[call.func.id] |= locals_by_func.get(fname, {}).get(arg.id, set())

	resolved = {}
	for fname in funcs:
		if fname in PARAM_DOC_HELPERS:
			resolved[fname] = set(helper_doctypes[fname])
		else:
			resolved[fname] = set(locals_by_func.get(fname, {}).get("doc", set()))
	return resolved, funcs


def _marked_save_sites(func):
	"""函数内经 `_service_save(<x>)` 放行的保存点行号。"""
	sites = []
	for node in ast.walk(func):
		if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
				and node.func.id == SERVICE_SAVE_HELPER):
			sites.append(node.lineno)
	return sites


def _bare_doc_saves(func):
	"""函数内裸 `doc.save(...)` 的行号。"""
	sites = []
	for node in ast.walk(func):
		if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
				and node.func.attr == "save"
				and isinstance(node.func.value, ast.Name)
				and node.func.value.id == "doc"):
			sites.append(node.lineno)
	return sites


class TestRetentionFieldSets(unittest.TestCase):
	def test_every_set_declares_its_state_field_first(self):
		for name, state_field in FIELD_SETS.items():
			fields = getattr(wf, name)
			with self.subTest(field_set=name):
				self.assertIn(state_field, fields, f"{name} 缺状态字段 {state_field}")
				self.assertEqual(fields[0], state_field,
								 "状态字段应为首项（便于审阅）")

	def test_composition_is_state_plus_signature_chain(self):
		"""处理申请：QC 主管 / QC 负责人 / QA 复核 / QA 负责人 / QM 签署位。
		使用申请：库存确认 + QC / QA / QM 批准位。"""
		self.assertEqual(wf.HBOS_RETENTION_DISPOSAL_SYSTEM_FIELDS, (
			"status",
			"qc_supervisor_sign", "qc_manager_sign",
			"qa_review_sign", "qa_manager_sign",
			"qm_sign", "qm_approved_at",
			"disposal_by", "disposal_date", "monitor_by", "monitor_date",
		))
		self.assertEqual(wf.HBOS_RETENTION_USAGE_SYSTEM_FIELDS, (
			"status",
			"stock_confirm_by", "stock_confirm_date",
			"qc_approval", "qa_approval", "qm_approval",
			"executed_by", "executed_date",
		))

	def test_approval_actor_fields_are_covered(self):
		"""签署人/执行人字段必须受守卫，否则可伪造「谁批准的」「谁执行的」。"""
		required = {
			"HBOS_RETENTION_DISPOSAL_SYSTEM_FIELDS": (
				"qc_supervisor_sign", "qc_manager_sign", "qa_review_sign",
				"qa_manager_sign", "qm_sign", "qm_approved_at",
				"disposal_by", "monitor_by",
			),
			"HBOS_RETENTION_USAGE_SYSTEM_FIELDS": (
				"stock_confirm_by", "qc_approval", "qa_approval", "qm_approval",
				"executed_by",
			),
		}
		for name, expected in required.items():
			fields = getattr(wf, name)
			for field in expected:
				with self.subTest(field_set=name, field=field):
					self.assertIn(field, fields,
								  f"{name} 未覆盖签署/执行留痕字段 {field}")


class TestControllerWiring(unittest.TestCase):
	def test_controllers_import_neutral_guard_entry(self):
		for rel, const in CONTROLLERS.items():
			src = _source(DOCTYPES / rel)
			with self.subTest(controller=rel):
				self.assertIn(
					"from hb_lims_app.hbos_lims.guards import guard_system_fields",
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

	def test_shared_implementation_is_reused(self):
		"""禁止在 R7C 控制器内另造守卫实现（两套逻辑会分叉）。"""
		for rel in CONTROLLERS:
			src = _source(DOCTYPES / rel)
			with self.subTest(controller=rel):
				self.assertNotIn("def _guard_system_fields", src)
				self.assertIn("def guard_system_fields", _source(STABILITY_GUARDS))

	def test_controller_docstrings_do_not_claim_a_fixed_chain_length(self):
		"""注释准确度：Usage Apply 并非「五级」签署链，不得写死级数而误导审阅。"""
		for rel in CONTROLLERS:
			src = _source(DOCTYPES / rel)
			with self.subTest(controller=rel):
				self.assertNotIn("五级签署链", src,
								 "注释应描述为「规定的审批/签署链和业务服务校验」")


class TestRetentionServiceSaveAuthorization(unittest.TestCase):
	"""审批单据保存覆盖契约（approval document save coverage）。

	判定按 DocType 精确作用域：只有 `doc` 实际指向两类审批 DocType 的业务路径
	才受「必须经 _service_save 打标」约束；非目标 DocType 保留原有保存逻辑。
	"""

	@classmethod
	def setUpClass(cls):
		cls.src = _source(RETENTION_SERVICE)
		cls.tree = ast.parse(cls.src, filename=str(RETENTION_SERVICE))
		cls.doc_doctypes, cls.funcs = _resolve_doc_doctypes(cls.tree)

	# 只读聚合投影：会 get_doc 审批单据但从不保存，不属于写路径。
	READ_ONLY_APPROVAL_LOADERS = frozenset({
		"list_disposal_applies", "list_usage_applies",
	})

	@property
	def approval_functions(self):
		"""`doc` 指向审批 DocType **且确实执行保存**的函数（真正的写路径）。

		只读投影（见 READ_ONLY_APPROVAL_LOADERS）虽然持有审批单据对象，
		但不产生写入，因此不在保存覆盖契约的作用域内。
		"""
		out = set()
		for name, dts in self.doc_doctypes.items():
			if not (dts & set(APPROVAL_DOCTYPES)):
				continue
			func = self.funcs[name]
			if _marked_save_sites(func) or _bare_doc_saves(func):
				out.add(name)
		return out

	def test_service_save_helper_sets_the_documented_flag(self):
		func = self.funcs[SERVICE_SAVE_HELPER]
		self.assertTrue(
			any(isinstance(n, ast.Attribute) and n.attr == "allow_system_fields"
				for n in ast.walk(func)),
			f"{SERVICE_SAVE_HELPER} 必须设置 doc.flags.allow_system_fields")
		self.assertIn("_APPROVAL_DOCTYPES", self.src)

	def test_service_save_helper_is_scoped_to_the_two_approval_doctypes(self):
		"""助手自身必须是「仅对两类审批单据」打标，不得无条件放行。"""
		func = self.funcs[SERVICE_SAVE_HELPER]
		guards = [n for n in ast.walk(func) if isinstance(n, ast.If)]
		self.assertTrue(guards, f"{SERVICE_SAVE_HELPER} 必须带 DocType 作用域判断")
		self.assertIn("_APPROVAL_DOCTYPES", self.src)
		for doctype in APPROVAL_DOCTYPES:
			self.assertIn(doctype, self._approval_doctypes_literal(),
						  f"{doctype} 应在 _APPROVAL_DOCTYPES 中")

	def test_read_only_approval_loaders_are_not_write_paths(self):
		"""只读聚合投影持有审批单据对象但不保存，不得被误判为写路径
		（否则会逼迫为其凭空添加 _service_save 而扩大 diff）。"""
		for name in sorted(self.READ_ONLY_APPROVAL_LOADERS):
			with self.subTest(function=name):
				func = self.funcs[name]
				self.assertEqual(_bare_doc_saves(func), [], f"{name} 不应保存")
				self.assertEqual(_marked_save_sites(func), [], f"{name} 不应打标")
				self.assertNotIn(name, self.approval_functions,
								 f"{name} 是只读投影，不属于审批写路径")

	def _approval_doctypes_literal(self):
		"""读取 retention_service._APPROVAL_DOCTYPES 的实际取值。"""
		for node in ast.walk(self.tree):
			if isinstance(node, ast.Assign) and any(
					getattr(t, "id", None) == "_APPROVAL_DOCTYPES" for t in node.targets):
				return [e.value for e in node.value.elts]
		self.fail("retention_service 未定义 _APPROVAL_DOCTYPES")

	def test_no_bare_save_on_approval_documents(self):
		"""审批单据写路径不得再出现裸 `doc.save(...)`。

		作用域限定为 `doc` 实际是两类审批 DocType 的函数 ——
		非目标 DocType（Retention Sample / Observation）不在此约束内。
		"""
		violations = {}
		for name in sorted(self.approval_functions):
			if name == SERVICE_SAVE_HELPER:
				continue
			bare = _bare_doc_saves(self.funcs[name])
			if bare:
				violations[name] = bare
		self.assertEqual(
			violations, {},
			"以下审批单据写路径仍直接 doc.save(...)，其状态/签署系统字段会被守卫拦下："
			+ ", ".join(f"{k}@{v}" for k, v in violations.items()))

	def test_approval_save_coverage_matches_the_reviewed_set(self):
		"""固化已审阅的审批写路径集合：新增路径必须显式更新本表，
		避免悄悄出现未经 _service_save 打标的新的状态写入点。"""
		self.assertEqual(
			sorted(self.approval_functions), sorted(APPROVAL_SAVE_FUNCTIONS),
			"审批单据写路径集合发生变化，请复核新路径是否经 _service_save 打标后更新本表")

	def test_every_approval_save_site_goes_through_the_helper(self):
		"""15 个保存点（14 个函数；approve_disposal 含两个）全部经助手放行。"""
		marked = {}
		for name in self.approval_functions:
			sites = _marked_save_sites(self.funcs[name])
			if sites:
				marked[name] = sites
		total = sum(len(v) for v in marked.values())
		self.assertEqual(total, 15,
						 f"审批单据保存点应有 15 个经 {SERVICE_SAVE_HELPER} 放行，实际 {total}")
		self.assertEqual(sorted(marked), sorted(APPROVAL_SAVE_FUNCTIONS),
						 "存在未使用 _service_save 的审批写路径")

	def test_non_target_doctypes_keep_their_original_save_logic(self):
		"""非目标 DocType（Retention Sample / Observation）保持原有保存逻辑。

		本轮刻意*不*为统一风格把它们改写成 _service_save ——
		那会扩大 diff 却不改变任何安全语义。
		"""
		for name in sorted(NON_TARGET_SAVE_FUNCTIONS):
			with self.subTest(function=name):
				func = self.funcs[name]
				self.assertEqual(
					_marked_save_sites(func), [],
					f"{name} 不是审批单据写路径，不应使用 {SERVICE_SAVE_HELPER}")
				self.assertTrue(
					_bare_doc_saves(func),
					f"{name} 应保留其原有 doc.save(ignore_permissions=True)")

	def test_non_target_functions_are_not_approval_documents(self):
		"""反证：上述非目标函数内的 doc 确实不是两类审批 DocType。"""
		for name in sorted(NON_TARGET_SAVE_FUNCTIONS):
			with self.subTest(function=name):
				dts = self.doc_doctypes.get(name, set())
				self.assertFalse(
					dts & set(APPROVAL_DOCTYPES),
					f"{name} 的 doc 实际是 {sorted(dts)}，不应列入非目标集合")

	def test_authorization_uses_the_documented_flag_name(self):
		self.assertIn("allow_system_fields", self.src)
		for invented in ("hbos_skip_guard", "skip_system_field_guard", "force_save"):
			self.assertNotIn(invented, self.src,
							 f"禁止另造放行机制：{invented}")


class TestGuardCoverageCompleteness(unittest.TestCase):
	"""L03 的直接回归护栏：带状态字段的 DocType 不得再次漏接线守卫。"""

	def test_every_status_bearing_doctype_is_guarded_or_explicitly_exempt(self):
		uncovered = []
		for folder in _status_bearing_doctypes():
			if folder in GUARD_EXEMPT:
				continue
			controller = DOCTYPES / folder / (folder + ".py")
			if not controller.exists():
				uncovered.append(f"{folder}（无控制器文件）")
				continue
			src = _source(controller)
			if "guard_system_fields" not in src:
				uncovered.append(folder)
		self.assertEqual(
			uncovered, [],
			"以下带状态字段的 LIMS DocType 控制器未接线系统字段守卫，"
			"可被原生 REST / frappe.client.set_value 直改状态或签署字段："
			+ ", ".join(uncovered)
			+ "。若确认守卫无效，请加入 GUARD_EXEMPT 并写明理由。")

	def test_exemption_table_entries_are_real_doctypes(self):
		for folder in GUARD_EXEMPT:
			self.assertTrue((DOCTYPES / folder).is_dir(),
							f"豁免表条目 {folder} 不是真实 DocType 目录")

	def test_the_two_reported_doctypes_are_not_exempt(self):
		"""L03 运行时确认的两个漏洞单据必须真正被守卫，不得用豁免掩盖。"""
		for folder in ("hbos_retention_disposal_apply", "hbos_retention_usage_apply"):
			with self.subTest(doctype=folder):
				self.assertNotIn(folder, GUARD_EXEMPT)
				src = _source(DOCTYPES / folder / (folder + ".py"))
				self.assertIn("guard_system_fields", src)


class TestSystemManagerGovernance(unittest.TestCase):
	"""A04 运行时结论固化：System Manager 是技术运维角色，不是质量批准角色。"""

	def test_system_manager_is_denied_every_write_action(self):
		from hb_lims_app.hbos_lims.workflow_contract import ACTION_ROLES, action_allowed

		allowed_writes = [a for a in ACTION_ROLES
						  if not a.startswith("get_") and action_allowed(a, "System Manager")]
		self.assertEqual(allowed_writes, [],
						 "System Manager 不得执行任何状态/签署/主数据写动作")

	def test_system_manager_keeps_read_actions(self):
		from hb_lims_app.hbos_lims.workflow_contract import ACTION_ROLES, action_allowed

		read_actions = [a for a in ACTION_ROLES if a.startswith("get_")]
		self.assertTrue(read_actions, "应有只读动作")
		self.assertTrue(any(action_allowed(a, "System Manager") for a in read_actions),
						"System Manager 应保留只读动作")

	def test_historical_grants_do_not_imply_runtime_allowance(self):
		"""ACTION_ROLES 里保留的 System Manager 记录只是历史兼容，
		必须以 action_allowed() 的运行时结论为准（防止静态计数误判为越权放行）。"""
		from hb_lims_app.hbos_lims.workflow_contract import ACTION_ROLES

		declared = [a for a, roles in ACTION_ROLES.items() if "System Manager" in roles]
		self.assertTrue(declared, "ACTION_ROLES 仍保留历史声明（本测试固化该事实）")
		for action in declared:
			if action.startswith("get_"):
				continue
			self.assertFalse(wf.action_allowed(action, "System Manager"),
							 f"{action} 声明含 System Manager，但运行时必须拒绝")


if __name__ == "__main__":
	unittest.main()
