# -*- coding: utf-8 -*-
"""受控质量父单删除守卫的离线行为验证；不代替真实 REST/数据库门禁。"""

import unittest

import test_lims_quality_child_write_guards as quality


class TestQualityParentDeleteGuards(unittest.TestCase):
	def setUp(self):
		# Reuse the real controller/metadata loader, without inheriting or rerunning its tests.
		self.context = quality.TestQualityChildWriteGuards()
		self.context.setUp()
		self.events = []

	def _delete_boundary(self, doctype, name, **kwargs):
		doc = self.context.docs[(doctype, name)]
		# Fixed Frappe delete_doc runs controller on_trash before links and SQL deletion.
		self.context._hook(doc, "on_trash")
		self.events.append(("delete", doctype, name))

	def _service(self, referenced=None):
		frappe = self.context.frappe
		frappe.db.exists = lambda *args: referenced
		frappe.delete_doc = self._delete_boundary
		return quality._definitions(quality.DOMAIN / "lims_service.py", {
			"frappe": frappe, "wf": quality.wf,
			"_commit": lambda: self.events.append(("commit",)),
			"_rollback": lambda: self.events.append(("rollback",)),
		}, names={"SPEC_DRAFT", "_spec_doc", "delete_specification", "_check_action", "_user"})

	def test_reviewed_and_published_coa_reject_native_parent_delete(self):
		for status in quality.FROZEN[quality.COA]:
			with self.subTest(status=status):
				doc = self.context._parent(quality.COA, status)
				with self.assertRaisesRegex(quality.ValidationRejected, "COA 禁止删除"):
					self._delete_boundary(doc.doctype, doc.name)
				self.assertEqual(self.events, [])
				self.assertEqual(doc.report_status, status)

	def test_active_and_obsolete_specification_reject_native_parent_delete(self):
		for status in quality.FROZEN[quality.SPEC]:
			with self.subTest(status=status):
				doc = self.context._parent(quality.SPEC, status)
				with self.assertRaisesRegex(quality.ValidationRejected, "质量标准禁止删除"):
					self._delete_boundary(doc.doctype, doc.name)
				self.assertEqual(self.events, [])
				self.assertEqual(doc.status, status)

	def test_technical_identity_and_server_save_flag_do_not_bypass_delete_guard(self):
		for kind in quality.CHILDREN:
			for actor in ("Administrator", "quality-manager@example.invalid"):
				with self.subTest(kind=kind, actor=actor):
					self.context.frappe.session.user = actor
					doc = self.context._parent(kind, quality.FROZEN[kind][-1], service=True)
					doc.flags.ignore_permissions = True
					with self.assertRaisesRegex(quality.ValidationRejected, "禁止删除"):
						self.context._hook(doc, "on_trash")

	def test_draft_parent_delete_is_not_newly_blocked_by_content_guard(self):
		for kind in quality.CHILDREN:
			with self.subTest(kind=kind):
				doc = self.context._parent(kind)
				self._delete_boundary(kind, doc.name)
		self.assertEqual([event[1] for event in self.events], [quality.COA, quality.SPEC])

	def test_actual_delete_specification_service_still_deletes_unreferenced_draft(self):
		doc = self.context._parent(quality.SPEC)
		self.assertEqual(self._service().delete_specification(doc.name), doc.name)
		self.assertEqual(self.events, [("delete", quality.SPEC, doc.name), ("commit",)])

	def test_actual_delete_specification_service_retains_controlled_status_rejection(self):
		for status in quality.FROZEN[quality.SPEC]:
			with self.subTest(status=status):
				self.events.clear()
				doc = self.context._parent(quality.SPEC, status)
				with self.assertRaisesRegex(quality.ValidationRejected, "仅草稿可删除"):
					self._service().delete_specification(doc.name)
				self.assertEqual(self.events, [("rollback",)])

	def test_actual_delete_specification_service_keeps_reference_check(self):
		doc = self.context._parent(quality.SPEC)
		with self.assertRaisesRegex(quality.ValidationRejected, "已被样品 SYNTHETIC-SAMPLE 引用"):
			self._service(referenced="SYNTHETIC-SAMPLE").delete_specification(doc.name)
		self.assertEqual(self.events, [("rollback",)])


if __name__ == "__main__":
	unittest.main()
