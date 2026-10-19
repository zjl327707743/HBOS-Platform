# -*- coding: utf-8 -*-
"""Administrator 主体边界的离线行为回归；不代表真实 Site / HTTP 已验证。

执行三个原服务的实际 _check_action，以及实际 approve_result / publish_coa。
仅替代 Frappe 会话、原生 all-role 语义、文档持久化和跨域同步边界。
真实多用户业务链、DB 回滚、PDF 和 HTTP 状态仍由隔离运行门禁验证。
"""

import ast
from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_ROOT))

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.portal.access import build_access_context

DOMAIN = APP_ROOT / "hb_lims_app" / "hbos_lims"
SERVICES = ("lims_service", "retention_service", "stability_service")

# 独立列明已核实只读语义，不把新出现的 get_* 自动认作 Administrator 例外。
READ_ACTIONS = {
    "get_result_ledger", "get_audit_log", "verify_coa_content",
    "verify_audit_integrity", "verify_audit_anchor",
    "get_retention_dashboard", "get_retention_ledger",
    "get_observation_plan", "get_disposal_quarterly",
    "get_stability_dashboard", "get_stability_notices", "get_stability_notice_detail",
    "get_stability_master", "get_stability_products", "get_stability_protocols",
    "get_stability_audit", "get_stability_samples", "get_stability_sample_detail",
    "get_stability_schedule", "get_stability_timepoint_detail", "get_stability_delays",
    "get_stability_validity_advice", "get_stability_results", "get_stability_result_detail",
    "get_stability_trend", "get_stability_reports", "get_stability_report_detail",
    "get_stability_customer_scan", "get_stability_changes", "get_stability_change_detail",
    "get_stability_room_logs", "get_stability_equipments", "get_stability_fault_tickets",
}
WRITE_CAPABILITIES = {
    "lims.results.submit", "lims.results.review", "lims.results.approve",
}
ROLE_CASES = (
    (), (wf.ROLE_SYSTEM,), (wf.ROLE_ANALYST,), (wf.ROLE_REVIEWER,),
    (wf.ROLE_MANAGER,), (wf.ROLE_LIMS_QA,), (wf.ROLE_LIMS_QA_MANAGER,),
    (wf.ROLE_LIMS_QP,), (wf.ROLE_SYSTEM, wf.ROLE_ANALYST),
    (wf.ROLE_SYSTEM, wf.ROLE_REVIEWER), (wf.ROLE_SYSTEM, wf.ROLE_MANAGER),
    (wf.ROLE_SYSTEM, wf.ROLE_LIMS_QA),
)
ALL_ROLES = sorted(set().union(*wf.ACTION_ROLES.values(), *wf.SCOPED_ACTION_ROLES.values()))


class Rejected(Exception):
    pass


class Values(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


def _throw(message, *args, **kwargs):
    raise Rejected(message)


def _load_functions(filename, namespace, names):
    """保留被测函数体，只移除模块级导入和 whitelist 装饰器。"""
    path = DOMAIN / (filename + ".py")
    body = []
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            node.decorator_list = []
            body.append(node)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), namespace)
    return SimpleNamespace(**namespace)


class StoredDocument(SimpleNamespace):
    """只记录存储边界调用，不能作为实际数据库证明。"""

    def get(self, field, default=None):
        return getattr(self, field, default)

    def save(self, **kwargs):
        self.events.append(("save", self.doctype, self.name))
        return self

    def insert(self, **kwargs):
        self.events.append(("insert", self.doctype, self.name))
        return self


class AdministratorBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.roles = {}
        self.frappe = SimpleNamespace(
            session=Values(user="Administrator"),
            get_roles=self._get_roles, throw=_throw,
            utils=SimpleNamespace(
                now_datetime=lambda: datetime(2026, 10, 18, 12, 0, 0),
                pdf=SimpleNamespace(get_pdf=lambda html: b"synthetic-pdf"),
            ),
        )
        self.services = {}
        for service in SERVICES:
            self.services[service] = _load_functions(service, {
                "frappe": self.frappe, "wf": wf,
                "_audit_violation": lambda *args, **kwargs: self.events.append(
                    ("violation", args, kwargs)),
            }, {"_user", "_check_action"})

    def _get_roles(self, user=None):
        user = user or self.frappe.session.user
        # 固定 Frappe v16.26.3 get_roles 的内置主体语义：返回全部 Role。
        return ALL_ROLES if user == "Administrator" else self.roles.get(user, ())

    def _as_user(self, user, roles=()):
        self.frappe.session.user = user
        self.roles[user] = roles

    def _check(self, service, action, scope=None, **kwargs):
        if service == "stability_service":
            return self.services[service]._check_action(
                action, scope or "HBOS Stability Timepoint", "SYNTHETIC", **kwargs)
        return self.services[service]._check_action(action)

    def test_administrator_cannot_use_any_registered_business_action(self):
        writes = set(wf.ACTION_ROLES) - READ_ACTIONS - {"break_glass_update"}
        self.assertIn("eval_trend", writes)  # 实际写入评估人、日期和趋势结论。
        for service in SERVICES:
            for action in sorted(writes):
                with self.subTest(service=service, action=action):
                    with self.assertRaisesRegex(Rejected, "没有执行"):
                        self._check(service, action)
        for scope, action in wf.SCOPED_ACTION_ROLES:
            with self.subTest(scope=scope, action=action):
                with self.assertRaisesRegex(Rejected, "没有执行"):
                    self._check("stability_service", action, scope)

    def test_administrator_retains_declared_read_and_integrity_actions(self):
        self.assertEqual(33, len(READ_ACTIONS))
        self.assertTrue(READ_ACTIONS.issubset(wf.ACTION_ROLES))
        for service in SERVICES:
            for action in sorted(READ_ACTIONS):
                with self.subTest(service=service, action=action):
                    self._check(service, action)

    def test_new_get_named_action_does_not_automatically_authorize_administrator(self):
        with patch.dict(wf.ACTION_ROLES, {"get_and_approve_quality": {wf.ROLE_MANAGER}}):
            for service in SERVICES:
                with self.subTest(service=service):
                    with self.assertRaisesRegex(Rejected, "没有执行"):
                        self._check(service, "get_and_approve_quality")

    def test_named_users_keep_the_existing_role_action_matrix(self):
        cases = [(None, action) for action in wf.ACTION_ROLES]
        cases.extend(wf.SCOPED_ACTION_ROLES)
        for roles in ROLE_CASES:
            # 名称包含 Administrator 不等于 Frappe 的内置用户名。
            self._as_user("Administrator@example.invalid", roles)
            for service in SERVICES:
                for scope, action in cases:
                    if scope and service != "stability_service":
                        continue
                    expected = any(wf.action_allowed(action, role, scope=scope) for role in roles)
                    with self.subTest(service=service, roles=roles, scope=scope, action=action):
                        if expected:
                            self._check(service, action, scope)
                        else:
                            with self.assertRaisesRegex(Rejected, "没有执行"):
                                self._check(service, action, scope)

    def test_explicit_break_glass_keeps_existing_technical_role_boundary(self):
        for user, roles, allowed in (
            ("Administrator", (), True),
            ("ops@example.invalid", (wf.ROLE_SYSTEM,), True),
            ("manager@example.invalid", (wf.ROLE_MANAGER,), False),
        ):
            self._as_user(user, roles)
            with self.subTest(user=user):
                if allowed:
                    self._check("lims_service", "break_glass_update")
                else:
                    with self.assertRaisesRegex(Rejected, "没有执行"):
                        self._check("lims_service", "break_glass_update")

    def test_stability_authorization_rejection_keeps_existing_violation_audit(self):
        with self.assertRaisesRegex(Rejected, "没有执行"):
            self._check("stability_service", "approve_delay")
        self.assertEqual(1, len(self.events))
        self.assertEqual("violation", self.events[0][0])
        self.assertIn("Administrator", str(self.events[0]))
        self.assertIn("approve_delay", str(self.events[0]))

    def test_internal_non_whitelisted_system_transitions_keep_their_existing_path(self):
        for action in ("complete_testing", "reopen_timepoint", "mark_superseded"):
            self._check("stability_service", action, system=True)
        self.assertEqual([], self.events)

    def test_administrator_portal_preserves_reads_without_business_signatures(self):
        for roles in ([], ALL_ROLES):
            with self.subTest(roles=roles):
                access = build_access_context("Administrator", roles)
                self.assertTrue(access["can_enter"])
                self.assertTrue({
                    "lims.read", "lims.results.read", "lims.ledger.read",
                    "lims.retention.read", "lims.audit.read",
                }.issubset(access["capabilities"]))
                self.assertFalse(WRITE_CAPABILITIES.intersection(access["capabilities"]))
                self.assertEqual({}, access["scopes"])

    def test_portal_named_roles_keep_existing_business_capabilities(self):
        for roles in ROLE_CASES:
            with self.subTest(roles=roles):
                access = build_access_context("named@example.invalid", roles)
                expected = {
                    "lims.results." + action.split("_")[0]
                    for action in ("submit_result", "review_result", "approve_result")
                    if any(wf.action_allowed(action, role) for role in roles)
                }
                self.assertEqual(expected, WRITE_CAPABILITIES.intersection(access["capabilities"]))

    def _quality_service(self):
        self.result = StoredDocument(
            doctype="HBOS Test Result", name="SYNTHETIC-RESULT",
            result_status="已复核", is_oos_candidate=0,
            analyst="analyst@example.invalid", reviewer="reviewer@example.invalid",
            approver=None, task="SYNTHETIC-TASK", flags=Values(), events=self.events,
        )
        self.task = StoredDocument(
            doctype="HBOS Sample Task", name="SYNTHETIC-TASK",
            status="已复核", sample="SYNTHETIC-SAMPLE", flags=Values(), events=self.events,
        )
        self.coa = StoredDocument(
            doctype="HBOS COA", name="SYNTHETIC-COA", report_status="已审核",
            qa_reviewer="reviewer@example.invalid", published_by=None,
            pdf_attachment=None, flags=Values(), events=self.events,
        )
        docs = {self.result.doctype: self.result, self.task.doctype: self.task, self.coa.doctype: self.coa}

        def get_doc(doctype, name=None):
            if isinstance(doctype, dict):
                return StoredDocument(
                    **doctype, name="SYNTHETIC-FILE", events=self.events,
                    file_url="/private/files/SYNTHETIC-COA.pdf",
                )
            return docs[doctype]

        self.frappe.get_doc = get_doc
        namespace = {
            "frappe": self.frappe, "wf": wf, "SIGN_APPROVER": "批准人",
            "audit_log": lambda *args, **kwargs: self.events.append(("audit", args)),
            "audit_violation": lambda *args, **kwargs: self.events.append(("violation", args)),
            "_commit": lambda: self.events.append(("commit",)),
            "_rollback": lambda: self.events.append(("rollback",)),
            "_advance_sample_after_task": lambda *args: None,
            "_coa_print_html": lambda doc: "synthetic-html",
            "_coa_content_fingerprint": lambda doc: "synthetic-fingerprint",
        }
        return _load_functions("lims_service", namespace, {
            "_user", "_now", "_signature", "_check_action", "_set_status", "_sod_reject",
            "approve_result", "publish_coa",
        })

    def _with_quality_sync(self):
        return patch.dict(sys.modules, {
            "hb_lims_app.hbos_lims.stability_service": SimpleNamespace(
                validate_standard_test_result_sync=lambda *args, **kwargs: None,
                sync_standard_test_result=lambda *args, **kwargs: None,
            ),
        })

    def test_actual_approve_result_denies_admin_who_is_not_a_previous_signer(self):
        service = self._quality_service()
        self.assertNotIn("Administrator", {self.result.analyst, self.result.reviewer})
        with self._with_quality_sync():
            with self.assertRaisesRegex(Rejected, "没有执行「approve_result」"):
                service.approve_result(self.result.name)
        self.assertEqual("已复核", self.result.result_status)
        self.assertIsNone(self.result.approver)
        self.assertEqual([], self.events)

    def test_actual_publish_coa_denies_admin_who_is_not_the_reviewer(self):
        service = self._quality_service()
        self.assertNotEqual("Administrator", self.coa.qa_reviewer)
        with self.assertRaisesRegex(Rejected, "没有执行「publish_coa」"):
            service.publish_coa(self.coa.name)
        self.assertEqual("已审核", self.coa.report_status)
        self.assertIsNone(self.coa.published_by)
        self.assertIsNone(self.coa.pdf_attachment)
        self.assertEqual([], self.events)

    def test_actual_approve_result_preserves_named_manager_with_explicit_business_role(self):
        service = self._quality_service()
        self._as_user("manager@example.invalid", (wf.ROLE_SYSTEM, wf.ROLE_MANAGER))
        with self._with_quality_sync():
            self.assertEqual(self.result.name, service.approve_result(self.result.name))
        self.assertEqual("已批准", self.result.result_status)
        self.assertEqual("manager@example.invalid", self.result.approver)
        self.assertEqual("已批准", self.task.status)
        self.assertIn(("commit",), self.events)

    def test_actual_publish_coa_preserves_named_qa_with_explicit_business_role(self):
        service = self._quality_service()
        self._as_user("qa@example.invalid", (wf.ROLE_SYSTEM, wf.ROLE_LIMS_QA))
        result = service.publish_coa(self.coa.name)
        self.assertEqual(self.coa.name, result["coa"])
        self.assertEqual("已发布", self.coa.report_status)
        self.assertEqual("qa@example.invalid", self.coa.published_by)
        self.assertIn(("insert", "File", "SYNTHETIC-FILE"), self.events)

    def test_actual_approve_result_keeps_sod_for_named_quality_user(self):
        service = self._quality_service()
        self._as_user(self.result.reviewer, (wf.ROLE_SYSTEM, wf.ROLE_MANAGER))
        with self._with_quality_sync():
            with self.assertRaisesRegex(Rejected, "SoD"):
                service.approve_result(self.result.name)
        self.assertEqual("已复核", self.result.result_status)
        self.assertFalse(any(event[0] in ("save", "insert", "commit") for event in self.events))

    def test_actual_publish_coa_keeps_sod_for_named_quality_user(self):
        service = self._quality_service()
        self._as_user(self.coa.qa_reviewer, (wf.ROLE_SYSTEM, wf.ROLE_LIMS_QA))
        with self.assertRaisesRegex(Rejected, "SoD"):
            service.publish_coa(self.coa.name)
        self.assertEqual("已审核", self.coa.report_status)
        self.assertFalse(any(event[0] in ("save", "insert", "commit") for event in self.events))


if __name__ == "__main__":
    unittest.main()
