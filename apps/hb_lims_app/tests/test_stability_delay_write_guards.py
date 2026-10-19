# -*- coding: utf-8 -*-
"""延期历史写入守卫的离线行为回归，不代表原生 HTTP / Site 已验收。

执行实际父/子控制器、共享守卫及延期服务函数，仅替代 Frappe 元数据、
文档存储、审计和会话边界。特别覆盖父 validate 之外的独立子文档钩子。
原生 REST 路由、父子持久化顺序与角色授权仍须在固定 Frappe Site 验证。
"""

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import stability_contract as stb
from hb_lims_app.hbos_lims import workflow_contract as wf

DOMAIN = APP_ROOT / "hb_lims_app" / "hbos_lims"
TIMEPOINT = "HBOS Stability Timepoint"
DELAY = "HBOS Stability Timepoint Delay"
PARENT_PATH = DOMAIN / "doctype/hbos_stability_timepoint/hbos_stability_timepoint.py"
CHILD_PATH = DOMAIN / "doctype/hbos_stability_timepoint_delay/hbos_stability_timepoint_delay.py"


class Rejected(Exception):
	pass


class Values(dict):
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__


def _throw(message, exc=None):
	raise Rejected(message)


def _meta(doctype):
	stem = doctype.lower().replace(" ", "_")
	data = json.loads((DOMAIN / "doctype" / stem / (stem + ".json")).read_text())
	fields = [Values(default=None, **f) if "default" not in f else Values(f)
			  for f in data["fields"]]
	return SimpleNamespace(fields=fields, get_field=lambda name: next(
		(f for f in fields if f.fieldname == name), None))


def _definitions(path, namespace, names=None):
	"""载入实际定义，移除模块导入/whitelist 装饰器；不重写被测函数。"""
	tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	body = []
	for node in tree.body:
		if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Assign)):
			continue
		if names is not None and getattr(node, "name", None) not in names:
			continue
		if isinstance(node, ast.FunctionDef):
			node.decorator_list = []
		body.append(node)
	exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)
	return SimpleNamespace(**namespace)


class DocumentBoundary(Values):
	def get_doc_before_save(self):
		return self.get("_before")

	def append(self, field, values):
		self[field].append(Values(values))

	def save(self, **kwargs):
		# Only the controller boundary is exercised here, not database I/O.
		self.validate()
		self.saved = True
		return self


def _delay(**changes):
	values = dict(
		doctype=DELAY, name="SYNTHETIC-DELAY-1", idx=1, delay_type="取样延期",
		planned_due_date="2026-11-01", policy_latest_due_date="2026-11-10",
		requested_due_date="2026-11-03", reason="合成延期申请",
		apply_by="delay-applicant@example.invalid", apply_date="2026-10-18",
		status="待批准", approver_by=None, approve_at=None,
		approved_due_date=None, reject_reason=None,
	)
	values.update(changes)
	return Values(values)


class TestStabilityDelayWriteGuards(unittest.TestCase):
	def setUp(self):
		self.frappe = SimpleNamespace(throw=_throw, PermissionError=Rejected, get_meta=_meta,
			get_doc=lambda *args: Values(), session=Values(user="Administrator"))
		self.guards = _definitions(DOMAIN / "stability_guards.py", {"frappe": self.frappe, "json": json})
		namespace = {"frappe": self.frappe, "Document": DocumentBoundary, "guards": self.guards}
		self.Parent = _definitions(PARENT_PATH, namespace.copy()).HBOSStabilityTimepoint
		self.Child = _definitions(CHILD_PATH, namespace.copy()).HBOSStabilityTimepointDelay

	def _parent(self, rows=(), before=True, service=False):
		values = {f.fieldname: f.default for f in _meta(TIMEPOINT).fields}
		values.update(doctype=TIMEPOINT, name="SYNTHETIC-TIMEPOINT", flags=Values(),
			delays=copy.deepcopy(list(rows)), test_items=[], is_zero_month=0,
			time_point_value=3, time_point_unit="月", plan_sample_date="2026-11-01")
		if not before:
			# New generic documents may only supply declared system-field defaults.
			values["plan_sample_date"] = None
		doc = self.Parent(values)
		doc._before = Values(copy.deepcopy(values)) if before else None
		doc.flags.allow_system_fields = service
		return doc

	def _child(self, before=True, service=False):
		doc = self.Child(_delay())
		doc.flags = Values(allow_system_fields=service)
		doc._before = Values(copy.deepcopy(doc)) if before else None
		return doc

	def _hook(self, doc, name):
		# Empty old controllers have no hook; absence means no guard rejected.
		method = getattr(type(doc), name, None)
		if method:
			method(doc)

	def test_parent_insert_rejects_injected_pending_or_approved_history(self):
		for status in ("待批准", "已批准", "已驳回"):
			with self.subTest(status=status), self.assertRaises(Rejected):
				self._parent([_delay(status=status)], before=False).validate()

	def test_parent_insert_without_delays_remains_permitted(self):
		self._parent(before=False).validate()

	def test_parent_rejects_added_delay(self):
		doc = self._parent()
		doc.delays.append(_delay(status="已批准", approved_due_date="2026-11-30"))
		with self.assertRaises(Rejected):
			doc.validate()

	def test_parent_rejects_removed_delay(self):
		doc = self._parent([_delay()])
		doc.delays = []
		with self.assertRaises(Rejected):
			doc.validate()

	def test_parent_rejects_replacing_a_row_with_identical_content(self):
		doc = self._parent([_delay()])
		doc.delays[0].name = "SYNTHETIC-REPLACEMENT-ROW"
		with self.assertRaises(Rejected):
			doc.validate()

	def test_parent_rejects_reordering_the_history(self):
		doc = self._parent([_delay(), _delay(name="SYNTHETIC-DELAY-2", idx=2, status="已驳回")])
		doc.delays.reverse()
		with self.assertRaises(Rejected):
			doc.validate()

	def test_parent_rejects_changing_idx_without_reordering_the_payload(self):
		doc = self._parent([_delay(), _delay(name="SYNTHETIC-DELAY-2", idx=2, status="已驳回")])
		doc.delays[0].idx, doc.delays[1].idx = 2, 1
		self.assertEqual([row.name for row in doc.delays], [row.name for row in doc._before.delays])
		with self.assertRaises(Rejected):
			doc.validate()

	def test_parent_rejects_moving_signatures_between_existing_rows(self):
		doc = self._parent([
			_delay(status="已批准", approver_by="qa-one@example.invalid",
				approve_at="2026-10-18 10:00:00", approved_due_date="2026-11-05"),
			_delay(name="SYNTHETIC-DELAY-2", idx=2, delay_type="检测延期",
				status="已驳回", approver_by="qa-two@example.invalid",
				approve_at="2026-10-18 11:00:00", reject_reason="合成驳回"),
		])
		left, right = copy.deepcopy(doc.delays)
		for field in _meta(DELAY).fields:
			if field.fieldtype in ("Section Break", "Column Break", "Tab Break"):
				continue
			doc.delays[0][field.fieldname] = right.get(field.fieldname)
			doc.delays[1][field.fieldname] = left.get(field.fieldname)
		self.assertEqual([(row.name, row.idx) for row in doc.delays],
			[(row.name, row.idx) for row in doc._before.delays])
		with self.assertRaises(Rejected):
			doc.validate()

	def test_parent_rejects_each_application_and_approval_field_change(self):
		changes = dict(delay_type="检测延期", planned_due_date="2026-11-02",
			policy_latest_due_date="2026-12-30", requested_due_date="2026-11-06",
			reason="篡改原因", apply_by="other@example.invalid", apply_date="2026-10-19",
			status="已批准", approver_by="forged@example.invalid",
			approve_at="2026-10-18 12:00:00", approved_due_date="2026-11-30",
			reject_reason="伪造驳回")
		for field, value in changes.items():
			with self.subTest(field=field):
				doc = self._parent([_delay()])
				doc.delays[0][field] = value
				with self.assertRaises(Rejected):
					doc.validate()

	def test_parent_rejects_falsy_values_in_blank_history_fields(self):
		# Data fields persist 0/False as content; neither is an unchanged blank.
		for value in (0, False):
			with self.subTest(value=value):
				doc = self._parent([_delay()])
				doc.delays[0].reject_reason = value
				with self.assertRaises(Rejected):
					doc.validate()

	def test_unchanged_history_allows_unrelated_parent_edit(self):
		doc = self._parent([_delay(status="已批准", approved_due_date="2026-11-05")])
		doc.extra_reason = "普通父单字段仍可修改"
		doc.validate()
		self.assertEqual(doc.delays, doc._before.delays)

	def test_server_marked_parent_insert_remains_permitted(self):
		self._parent([_delay()], before=False, service=True).validate()

	def test_independent_child_insert_is_rejected(self):
		with self.assertRaises(Rejected):
			self._hook(self._child(before=False), "validate")

	def test_independent_child_update_is_rejected(self):
		doc = self._child()
		doc.approved_due_date = "2026-12-30"
		with self.assertRaises(Rejected):
			self._hook(doc, "validate")

	def test_independent_child_delete_is_rejected(self):
		with self.assertRaises(Rejected):
			self._hook(self._child(), "on_trash")

	def test_child_flags_cannot_replace_the_parent_service_path(self):
		for hook in ("validate", "on_trash"):
			with self.subTest(hook=hook), self.assertRaises(Rejected):
				self._hook(self._child(service=True), hook)

	def _service(self, doc, user="delay-approver@example.invalid"):
		namespace = {"frappe": self.frappe, "stb": stb, "wf": wf,
			"TIMEPOINT_DOCTYPE": TIMEPOINT, "SAMPLE_DOCTYPE": "HBOS Stability Sample",
			"_check_action": lambda *args: None, "_lock_row": lambda *args: doc,
			"_product_of_sample": lambda sample: None, "_add_days": stb._add_days,
			"_user": lambda: user, "_today": lambda: "2026-10-18",
			"_now": lambda: "2026-10-18 12:00:00",
			"_audit_on": lambda *args, **kwargs: None,
			"_audit_commit": lambda *args, **kwargs: None,
			"_commit": lambda: None, "_rollback": lambda: None}
		return _definitions(DOMAIN / "stability_service.py", namespace, names={
			"_delay_rows", "_planned_due_of", "_policy_latest_of", "_policy_latest_sample",
			"apply_delay", "approve_delay", "reject_delay"})

	def test_existing_apply_approve_reject_services_pass_the_actual_parent_guard(self):
		for action, rows, expected in (("apply_delay", [], "待批准"),
			("approve_delay", [_delay()], "已批准"), ("reject_delay", [_delay()], "已驳回")):
			with self.subTest(action=action):
				doc = self._parent(rows)
				service = self._service(doc)
				if action == "apply_delay":
					service.apply_delay(doc.name, "取样延期", "2026-11-03", "合成申请")
				elif action == "approve_delay":
					service.approve_delay(doc.name, "取样延期", "2026-11-05")
				else:
					service.reject_delay(doc.name, "取样延期", "合成驳回")
				self.assertTrue(doc.saved)
				self.assertEqual(doc.delays[0].status, expected)
				self.assertTrue(doc.flags.allow_system_fields)

	def test_service_still_rejects_applicant_self_approval(self):
		doc = self._parent([_delay()])
		with self.assertRaisesRegex(Rejected, "SoD"):
			self._service(doc, user=doc.delays[0].apply_by).approve_delay(
				doc.name, "取样延期", "2026-11-05")
		self.assertFalse(doc.saved)
		self.assertEqual(doc.delays, doc._before.delays)

	def test_delay_history_is_not_a_break_glass_field(self):
		self.assertNotIn("delays", self.guards.TIMEPOINT_SYSTEM_FIELDS)


if __name__ == "__main__":
	unittest.main()
