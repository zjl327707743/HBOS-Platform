# -*- coding: utf-8 -*-
"""质量子行与 COA 内容绑定的离线行为回归，不代表原生 Site 验收。

执行仓库实际父/子控制器、共享守卫、COA 指纹及相关服务函数；仅替代
Frappe 元数据、会话和持久化边界。父单保存的 db_insert/db_update 边界
依据固定 Frappe 16.26.3 源码建模，真实 REST/权限/事务仍由原生门禁验证。
"""

import ast
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import workflow_contract as wf

DOMAIN = APP_ROOT / "hb_lims_app" / "hbos_lims"
COA = "HBOS COA"
SPEC = "HBOS Specification"
CHILDREN = {COA: "HBOS COA Item", SPEC: "HBOS Specification Item"}
FROZEN = {COA: ("已审核", "已发布"), SPEC: ("已生效", "已废止")}


class ValidationRejected(Exception):
	pass


class PermissionRejected(Exception):
	pass


class Values(SimpleNamespace):
	def get(self, key, default=None):
		return getattr(self, key, default)


def _throw(message, exc=None):
	raise (exc or ValidationRejected)(message)


def _doctype_path(doctype, suffix="py"):
	stem = doctype.lower().replace(" ", "_")
	return DOMAIN / "doctype" / stem / (stem + "." + suffix)


def _meta(doctype):
	data = json.loads(_doctype_path(doctype, "json").read_text(encoding="utf-8"))
	fields = [Values(**dict({"default": None}, **field)) for field in data["fields"]]
	get_field = lambda name: next((field for field in fields if field.fieldname == name), None)
	return Values(fields=fields, get_field=get_field,
		get_label=lambda name: getattr(get_field(name), "label", name))


def _definitions(path, namespace, names=None):
	"""执行实际定义；只略去模块导入与 whitelist 装饰器，不重写函数体。"""
	tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
	body = []
	for node in tree.body:
		if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Assign)):
			continue
		if names is not None:
			assigned = {target.id for target in node.targets if isinstance(target, ast.Name)} \
				if isinstance(node, ast.Assign) else {node.name}
			if not assigned.intersection(names):
				continue
		if isinstance(node, ast.FunctionDef):
			node.decorator_list = []
		body.append(node)
	exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)
	return SimpleNamespace(**namespace)


class DocumentBoundary(Values):
	def get_doc_before_save(self):
		return self.get("_before")

	def db_insert(self):
		self.db_calls.append("insert")

	def db_update(self):
		self.db_calls.append("update")

	def save(self, **kwargs):
		self.validate()
		# Frappe Document.update_child_table uses child.db_update, not child.save.
		for child in self.items:
			child.db_update()
		self.saved = True
		return self

	def insert(self, **kwargs):
		self.validate()
		# Frappe Document.insert uses child.db_insert, not child.insert.
		for child in self.items:
			child.db_insert()
		self.saved = True
		return self


class TestQualityChildWriteGuards(unittest.TestCase):
	def setUp(self):
		self.frappe = Values(throw=_throw, PermissionError=PermissionRejected,
			get_meta=_meta, session=Values(user="quality-manager@example.invalid"),
			get_roles=lambda user: ["LIMS Manager"], db=Values(get_value=lambda *args: None))
		self.guards = _definitions(DOMAIN / "stability_guards.py",
			{"frappe": self.frappe, "json": json})
		namespace = {"frappe": self.frappe, "Document": DocumentBoundary, "wf": wf,
			"guard_system_fields": self.guards.guard_system_fields,
			"guard_content_frozen": self.guards.guard_content_frozen}
		self.parents = {
			COA: _definitions(_doctype_path(COA), namespace.copy()).HBOSCOA,
			SPEC: _definitions(_doctype_path(SPEC), namespace.copy()).HBOSSpecification,
		}
		self.children = {
			COA: _definitions(_doctype_path(CHILDREN[COA]), namespace.copy()).HBOSCOAItem,
			SPEC: _definitions(_doctype_path(CHILDREN[SPEC]), namespace.copy()).HBOSSpecificationItem,
		}
		self.docs = {}
		self.frappe.get_doc = lambda doctype, name: self.docs[(doctype, name)]
		self.service = _definitions(DOMAIN / "lims_service.py", {
			"frappe": self.frappe, "wf": wf, "hashlib": hashlib, "json": json,
			"_now": lambda: "2026-10-18 12:00:00",
			"_commit": lambda: None, "_rollback": lambda: None,
		}, names={"COA_FINGERPRINT_FIELDS", "COA_FINGERPRINT_ITEM_FIELDS",
			"_coa_content_fingerprint", "verify_coa_content", "review_coa", "_check_action", "_user"})

	def _row(self, kind, number=1):
		values = {field.fieldname: field.default for field in _meta(CHILDREN[kind]).fields}
		values.update(doctype=CHILDREN[kind], name=f"SYNTHETIC-ROW-{number}", idx=number,
			parent="SYNTHETIC-PARENT", parenttype=kind, parentfield="items",
			flags=Values(), db_calls=[])
		if kind == COA:
			values.update(test_item=f"SYNTHETIC-ITEM-{number}", item_name=f"检验项目{number}",
				method_sop="SYNTHETIC-SOP", standard="limit|qualifier", result="50", verdict="合格")
		else:
			values.update(item=f"SYNTHETIC-ITEM-{number}", item_name="含量|SOP", method_sop="HBOS",
				limits_type="区间", lower_limit=0, upper_limit=100, unit="%", significant_digits=2)
		return self.children[kind](**values)

	def _parent(self, kind, status="草稿", new=False, service=False):
		values = {field.fieldname: field.default for field in _meta(kind).fields}
		values.update(doctype=kind, name="SYNTHETIC-PARENT", meta=_meta(kind),
			flags=Values(), items=[self._row(kind), self._row(kind, 2)], saved=False)
		if kind == COA:
			values.update(report_status=status, sample="SYNTHETIC-SAMPLE", batch_no="SYNTHETIC-BATCH",
				material_code="SYNTHETIC-MATERIAL", material_name="合成物料", spec_version="1.0")
		else:
			values.update(status=status, spec_code="SYNTHETIC-SPEC", spec_name="合成标准", version="1.0")
		doc = self.parents[kind](**values)
		doc._before = None if new else Values(**copy.deepcopy(values))
		doc.flags.allow_system_fields = service
		self.docs[(kind, doc.name)] = doc
		return doc

	def _hook(self, doc, hook):
		# An old pass controller has no hook: absence must fail the rejection assertion.
		method = getattr(type(doc), hook, None)
		if method:
			method(doc)

	def test_independent_child_insert_is_permission_rejected_for_both_actor_types(self):
		for kind in CHILDREN:
			for actor in ("Administrator", "quality-manager@example.invalid"):
				with self.subTest(kind=kind, actor=actor):
					self.frappe.session.user = actor
					row = self._row(kind)
					row.name = None
					with self.assertRaises(PermissionRejected):
						self._hook(row, "validate")
					self.assertEqual(row.db_calls, [])

	def test_independent_child_update_rejected_in_draft_and_every_frozen_state(self):
		for kind in CHILDREN:
			for status in ("草稿", *FROZEN[kind]):
				with self.subTest(kind=kind, status=status):
					doc = self._parent(kind, status)
					doc.items[0].remark = "独立篡改"
					with self.assertRaises(PermissionRejected):
						self._hook(doc.items[0], "validate")
					self.assertEqual(doc.items[0].db_calls, [])

	def test_independent_child_delete_is_permission_rejected(self):
		for kind in CHILDREN:
			with self.subTest(kind=kind), self.assertRaises(PermissionRejected):
				self._hook(self._row(kind), "on_trash")

	def test_reparenting_and_child_flags_cannot_bypass_the_parent_boundary(self):
		for kind in CHILDREN:
			for hook in ("validate", "on_trash"):
				with self.subTest(kind=kind, hook=hook):
					row = self._parent(kind, FROZEN[kind][-1]).items[0]
					row._before = copy.deepcopy(row)
					row.parent = "DIFFERENT-DRAFT-PARENT"
					row.flags.allow_system_fields = True
					row.flags.ignore_permissions = True
					with self.assertRaises(PermissionRejected):
						self._hook(row, hook)

	def test_draft_parent_can_edit_add_and_remove_children(self):
		for kind in CHILDREN:
			with self.subTest(kind=kind):
				doc = self._parent(kind)
				doc.items[0].remark = "父单草稿合法编辑"
				doc.items.pop()
				doc.items.append(self._row(kind, 3))
				doc.save()
				self.assertTrue(doc.saved)
				self.assertEqual([row.name for row in doc.items], ["SYNTHETIC-ROW-1", "SYNTHETIC-ROW-3"])
				self.assertEqual([row.db_calls for row in doc.items], [["update"], ["update"]])

	def test_new_draft_parent_keeps_child_db_insert_path(self):
		for kind in CHILDREN:
			with self.subTest(kind=kind):
				doc = self._parent(kind, new=True)
				doc.insert()
				self.assertTrue(doc.saved)
				self.assertEqual([row.db_calls for row in doc.items], [["insert"], ["insert"]])

	def test_actual_review_service_keeps_marked_parent_save_path(self):
		doc = self._parent(COA)
		self.assertEqual(self.service.review_coa(doc.name), doc.name)
		self.assertTrue(doc.flags.allow_system_fields)
		self.assertTrue(doc.saved)
		self.assertEqual(doc.report_status, "已审核")
		self.assertEqual(doc.qa_reviewer, "quality-manager@example.invalid")
		self.assertEqual([row.db_calls for row in doc.items], [["update"], ["update"]])

	def test_ordinary_parent_content_and_signatures_remain_frozen(self):
		for kind in CHILDREN:
			for status in FROZEN[kind]:
				for field in ("remark", "status"):
					with self.subTest(kind=kind, status=status, field=field):
						doc = self._parent(kind, status)
						if field == "remark":
							doc.items[0].remark = "冻结后篡改"
						else:
							setattr(doc, "report_status" if kind == COA else "status", "草稿")
						with self.assertRaises(ValidationRejected):
							doc.save()
						self.assertFalse(doc.saved)
						self.assertEqual(doc.items[0].db_calls, [])

	def test_frozen_parent_rejects_same_content_under_a_replacement_row_name(self):
		for kind in CHILDREN:
			for status in FROZEN[kind]:
				with self.subTest(kind=kind, status=status):
					doc = self._parent(kind, status)
					doc.items[0].name = "REPLACEMENT-ROW"
					with self.assertRaises(ValidationRejected):
						doc.validate()

	def test_frozen_coa_rejects_idx_only_changes_without_array_reordering(self):
		for status in FROZEN[COA]:
			with self.subTest(status=status):
				doc = self._parent(COA, status)
				doc.items[0].idx, doc.items[1].idx = 2, 1
				self.assertEqual([row.name for row in doc.items], [row.name for row in doc._before.items])
				with self.assertRaises(ValidationRejected):
					doc.validate()

	def test_frozen_coa_rejects_delimiter_boundary_shift_between_standard_and_result(self):
		for status in FROZEN[COA]:
			with self.subTest(status=status):
				doc = self._parent(COA, status)
				doc.items[0].standard, doc.items[0].result = "limit", "qualifier|50"
				with self.assertRaises(ValidationRejected):
					doc.validate()

	def test_frozen_specification_rejects_delimiter_boundary_shift(self):
		for status in FROZEN[SPEC]:
			with self.subTest(status=status):
				doc = self._parent(SPEC, status)
				doc.items[0].item_name, doc.items[0].method_sop = "含量", "SOP|HBOS"
				with self.assertRaises(ValidationRejected):
					doc.validate()

	def test_frozen_parent_does_not_collapse_zero_or_false_into_blank(self):
		for kind in CHILDREN:
			for value in (0, False):
				with self.subTest(kind=kind, value=value):
					doc = self._parent(kind, FROZEN[kind][-1])
					doc.items[0].remark = value
					with self.assertRaises(ValidationRejected):
						doc.validate()

	def test_only_specification_row_order_remains_semantically_unordered(self):
		doc = self._parent(SPEC, "已生效")
		doc.items.reverse()
		for idx, row in enumerate(doc.items, 1):
			row.idx = idx
		doc.validate()
		coa = self._parent(COA, "已发布")
		coa.items.reverse()
		with self.assertRaises(ValidationRejected):
			coa.validate()

	def test_unchanged_escaped_content_and_null_to_blank_remain_stable(self):
		for kind in CHILDREN:
			with self.subTest(kind=kind):
				doc = self._parent(kind, FROZEN[kind][-1])
				for snapshot in (doc, doc._before):
					snapshot.items[0].remark = '含量|上下限\n"原文"\\尾部'
				doc.items[1].remark = ""
				doc.validate()
		coa = self._parent(COA)
		self.assertEqual(self.service._coa_content_fingerprint(coa),
			self.service._coa_content_fingerprint(copy.deepcopy(coa)))

	def test_fingerprint_distinguishes_delimiter_shifts_in_rows_and_header(self):
		for location in ("row", "header"):
			with self.subTest(location=location):
				coa = self._parent(COA)
				if location == "header":
					coa.sample, coa.batch_no = "sample|batch", "one"
				before = self.service._coa_content_fingerprint(coa)
				if location == "row":
					coa.items[0].standard, coa.items[0].result = "limit", "qualifier|50"
				else:
					coa.sample, coa.batch_no = "sample", "batch|one"
				self.assertNotEqual(before, self.service._coa_content_fingerprint(coa))

	def test_fingerprint_binds_row_identity_idx_array_order_and_falsy_content(self):
		for change in ("name", "idx", "order", "zero", "false"):
			with self.subTest(change=change):
				coa = self._parent(COA)
				before = self.service._coa_content_fingerprint(coa)
				if change == "name":
					coa.items[0].name = "REPLACEMENT-ROW"
				elif change == "idx":
					coa.items[0].idx, coa.items[1].idx = 2, 1
				elif change == "order":
					coa.items.reverse()
				else:
					coa.items[0].remark = 0 if change == "zero" else False
				self.assertNotEqual(before, self.service._coa_content_fingerprint(coa))

	def test_actual_verify_reports_stable_changed_missing_and_old_v1_honestly(self):
		coa = self._parent(COA, "已发布")
		coa.content_fingerprint = self.service._coa_content_fingerprint(coa)
		self.assertTrue(self.service.verify_coa_content(coa.name)["ok"])
		coa.items[0].standard, coa.items[0].result = "limit", "qualifier|50"
		self.assertFalse(self.service.verify_coa_content(coa.name)["ok"])
		coa.content_fingerprint = ""
		missing = self.service.verify_coa_content(coa.name)
		self.assertFalse(missing["ok"])
		self.assertIn("无法校验", missing["reason"])
		# #43 has not shipped v1 to the product. Do not pretend a v1 hash is v2 evidence.
		parts = ["hbos-coa-v1"]
		parts.extend(str(coa.get(field) or "") for field in self.service.COA_FINGERPRINT_FIELDS)
		for row in coa.items:
			parts.extend(str(row.get(field) or "") for field in self.service.COA_FINGERPRINT_ITEM_FIELDS)
		coa.content_fingerprint = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
		self.assertFalse(self.service.verify_coa_content(coa.name)["ok"])


if __name__ == "__main__":
	unittest.main()
