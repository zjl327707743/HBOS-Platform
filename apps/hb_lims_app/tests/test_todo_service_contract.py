# -*- coding: utf-8 -*-
"""个人待办聚合服务的可执行边界测试。"""

import ast
import importlib
import sys
import types
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest


SERVICE_MODULE = "hb_lims_app.hbos_lims.todo_service"
APP_ROOT = str(Path(__file__).resolve().parents[1])
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

import hb_lims_app.hbos_lims  # noqa: E402


class FakeFrappe(types.ModuleType):
    def __init__(self):
        super().__init__("frappe")
        self.session = types.SimpleNamespace(user="Guest")
        self.roles = {}
        self.full_names = {}
        self.rows = defaultdict(list)
        self.readable_names = {}
        self.query_count = defaultdict(int)
        self.cache_backend = FakeCache()
        self.utils = types.SimpleNamespace(
            get_fullname=lambda user: self.full_names.get(user, user),
            today=lambda: "2026-09-22",
        )

    def cache(self):
        return self.cache_backend

    def log_error(self, *_args, **_kwargs):
        return None

    @staticmethod
    def whitelist(*_args, **_kwargs):
        def decorator(function):
            function.is_whitelisted = True
            return function

        return decorator

    def get_roles(self, user):
        return list(self.roles.get(user, ()))

    def get_fullname(self, user):
        return self.full_names.get(user, user)

    def get_list(self, doctype, filters=None, fields=None, **_kwargs):
        self.query_count[doctype] += 1
        records = list(self.rows.get(doctype, ()))
        allowed = self.readable_names.get(doctype)
        if allowed is not None:
            records = [row for row in records if row.get("name") in allowed]
        if filters:
            records = [row for row in records if self._matches(row, filters)]
        if fields:
            records = [{field: row.get(field) for field in fields} for row in records]
        return records

    def has_permission(self, doctype, ptype="read", doc=None):
        allowed = self.readable_names.get(doctype)
        return allowed is None or doc in allowed

    def get_all(self, doctype, filters=None, fields=None, **_kwargs):
        self.query_count[doctype] += 1
        records = list(self.rows.get(doctype, ()))
        if filters:
            records = [row for row in records if self._matches(row, filters)]
        if fields:
            records = [{field: row.get(field) for field in fields} for row in records]
        return records

    @staticmethod
    def _matches(row, filters):
        for field, expected in filters.items():
            actual = row.get(field)
            if isinstance(expected, (list, tuple)) and len(expected) == 2:
                operator, operand = expected
                if operator == "in" and actual not in operand:
                    return False
                if operator == "not in" and actual in operand:
                    return False
                if operator == "is" and operand == "set" and not actual:
                    return False
                if operator == "is" and operand == "not set" and actual:
                    return False
            elif actual != expected:
                return False
        return True


class FakeCache:
    def __init__(self):
        self.values = {}
        self.get_calls = []
        self.set_calls = []
        self.delete_calls = []

    def get_value(self, key):
        self.get_calls.append(key)
        return self.values.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.set_calls.append((key, value, expires_in_sec))
        self.values[key] = value

    def delete_value(self, key):
        self.delete_calls.append(key)
        self.values.pop(key, None)


@pytest.fixture
def service(monkeypatch):
    fake = FakeFrappe()
    monkeypatch.setitem(sys.modules, "frappe", fake)
    sys.modules.pop(SERVICE_MODULE, None)
    module = importlib.import_module(SERVICE_MODULE)
    return module, fake


def _seed_testing_rows(fake):
    fake.rows["HBOS Sample"] = [
        {
            "name": "SAMPLE-1",
            "material_name": "阿莫西林",
            "batch_no": "A01",
            "sample_source": "生产取样",
            "stability_timepoint": None,
        },
        {
            "name": "SAMPLE-STB",
            "material_name": "稳定性样品",
            "batch_no": "B01",
            "sample_source": "稳定性",
            "stability_timepoint": "TP-001",
        },
        {
            "name": "SAMPLE-HIDDEN",
            "material_name": "不可读样品",
            "batch_no": "H01",
            "sample_source": "生产取样",
            "stability_timepoint": None,
        },
    ]
    fake.rows["HBOS Sample Task"] = [
        {
            "name": "TASK-ME",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-WATER",
            "item_name": "水分",
            "assignee": "alice@example.com",
            "due_date": "2026-09-20",
            "priority": "特急",
            "status": "已分配",
            "result": None,
            "modified": "2026-09-20T08:00:00+08:00",
        },
        {
            "name": "TASK-ROLE",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-ASH",
            "item_name": "灰分",
            "assignee": None,
            "due_date": "2026-09-24",
            "priority": "常规",
            "status": "已分配",
            "result": None,
            "modified": "2026-09-20T09:00:00+08:00",
        },
        {
            "name": "TASK-OTHER",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-OTHER",
            "item_name": "有关物质",
            "assignee": "bob@example.com",
            "due_date": "2026-09-25",
            "priority": "加急",
            "status": "已分配",
            "result": None,
            "modified": "2026-09-20T10:00:00+08:00",
        },
        {
            "name": "TASK-STB-MAPPED",
            "sample": "SAMPLE-STB",
            "test_item": "ITEM-ASSAY",
            "item_name": "含量",
            "assignee": None,
            "due_date": "2026-09-26",
            "priority": "加急",
            "status": "已分配",
            "result": None,
            "modified": "2026-09-20T11:00:00+08:00",
        },
        {
            "name": "TASK-STB-UNMAPPED",
            "sample": "SAMPLE-STB",
            "test_item": "ITEM-WATER",
            "item_name": "水分",
            "assignee": None,
            "due_date": "2026-09-27",
            "priority": "常规",
            "status": "已分配",
            "result": None,
            "modified": "2026-09-20T12:00:00+08:00",
        },
        {
            "name": "TASK-HIDDEN",
            "sample": "SAMPLE-HIDDEN",
            "test_item": "ITEM-HIDDEN",
            "item_name": "不可读项目",
            "assignee": None,
            "due_date": "2026-09-19",
            "priority": "特急",
            "status": "已分配",
            "result": None,
            "modified": "2026-09-20T13:00:00+08:00",
        },
        {
            "name": "TASK-RESULT-DRAFT",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-CONTENT",
            "item_name": "鉴别",
            "assignee": "alice@example.com",
            "due_date": "2026-09-28",
            "priority": "加急",
            "status": "检验中",
            "result": "RESULT-DRAFT",
            "modified": "2026-09-20T14:00:00+08:00",
        },
        {
            "name": "TASK-RESULT-REVIEW",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-ID",
            "item_name": "鉴别",
            "assignee": "bob@example.com",
            "due_date": "2026-09-29",
            "priority": "常规",
            "status": "已提交",
            "result": "RESULT-REVIEW",
            "modified": "2026-09-20T15:00:00+08:00",
        },
    ]
    fake.rows["HBOS Test Result"] = [
        {
            "name": "RESULT-DRAFT",
            "task": "TASK-RESULT-DRAFT",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-CONTENT",
            "item_name": "含量",
            "result_status": "草稿",
            "analyst": "alice@example.com",
            "reviewer": None,
            "approver": None,
            "modified": "2026-09-20T14:10:00+08:00",
        },
        {
            "name": "RESULT-REVIEW",
            "task": "TASK-RESULT-REVIEW",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-ID",
            "item_name": "鉴别",
            "result_status": "已提交",
            "analyst": "bob@example.com",
            "reviewer": None,
            "approver": None,
            "modified": "2026-09-20T15:10:00+08:00",
        },
    ]
    fake.rows["HBOS Stability Timepoint Item"] = [
        {"name": "TPI-1", "parent": "TP-001", "stability_test_item": "STB-ASSAY"},
    ]
    fake.rows["HBOS Stability Test Item"] = [
        {"name": "STB-ASSAY", "base_test_item": "ITEM-ASSAY"},
        {"name": "STB-WATER", "base_test_item": "ITEM-WATER"},
    ]
    fake.readable_names["HBOS Sample Task"] = {
        row["name"] for row in fake.rows["HBOS Sample Task"]
        if row["name"] != "TASK-HIDDEN"
    }
    fake.readable_names["HBOS Sample"] = {"SAMPLE-1", "SAMPLE-STB"}


def _seed_stability_rows(fake):
    fake.rows["HBOS Stability Timepoint"] = [
        {
            "name": "TP-SAMPLE",
            "status": "待取样",
            "sample_by": None,
            "test_by": None,
            "evaluator": None,
            "trend_conclusion": None,
            "modified": "2026-09-20T08:00:00+08:00",
        },
        {
            "name": "TP-TEST",
            "status": "待检测",
            "sample_by": "bob@example.com",
            "test_by": None,
            "evaluator": None,
            "trend_conclusion": None,
            "modified": "2026-09-20T09:00:00+08:00",
        },
        {
            "name": "TP-RESULT",
            "status": "检测中",
            "sample_by": "bob@example.com",
            "test_by": "bob@example.com",
            "evaluator": None,
            "trend_conclusion": None,
            "modified": "2026-09-20T10:00:00+08:00",
        },
    ]
    fake.rows["HBOS Stability Timepoint Item"] = [
        {"name": "TPI-RESULT", "parent": "TP-RESULT", "stability_test_item": "STB-ASSAY", "is_required": 1},
    ]
    fake.rows["HBOS Stability Result"] = [
        {
            "name": "STB-SYNCED",
            "timepoint": "TP-RESULT",
            "stability_test_item": "STB-ASSAY",
            "status": "草稿",
            "analyst": "alice@example.com",
            "reviewed_by": None,
            "approved_by": None,
            "source_test_result": "HBOS-TR-0001",
            "modified": "2026-09-20T11:00:00+08:00",
        },
        {
            "name": "STB-MANUAL-DRAFT",
            "timepoint": "TP-RESULT",
            "stability_test_item": "STB-WATER",
            "status": "草稿",
            "analyst": "alice@example.com",
            "reviewed_by": None,
            "approved_by": None,
            "source_test_result": None,
            "modified": "2026-09-20T11:10:00+08:00",
        },
        {
            "name": "STB-REVIEW-OWN",
            "timepoint": "TP-RESULT",
            "stability_test_item": "STB-WATER",
            "status": "已提交",
            "analyst": "alice@example.com",
            "reviewed_by": None,
            "approved_by": None,
            "source_test_result": None,
            "modified": "2026-09-20T11:20:00+08:00",
        },
        {
            "name": "STB-REVIEW-OTHER",
            "timepoint": "TP-RESULT",
            "stability_test_item": "STB-WATER",
            "status": "已提交",
            "analyst": "bob@example.com",
            "reviewed_by": None,
            "approved_by": None,
            "source_test_result": None,
            "modified": "2026-09-20T11:30:00+08:00",
        },
        {
            "name": "STB-APPROVE-OWN",
            "timepoint": "TP-RESULT",
            "stability_test_item": "STB-WATER",
            "status": "已复核",
            "analyst": "bob@example.com",
            "reviewed_by": "alice@example.com",
            "approved_by": None,
            "source_test_result": None,
            "modified": "2026-09-20T11:40:00+08:00",
        },
        {
            "name": "STB-APPROVE-OTHER",
            "timepoint": "TP-RESULT",
            "stability_test_item": "STB-WATER",
            "status": "已复核",
            "analyst": "bob@example.com",
            "reviewed_by": "bob@example.com",
            "approved_by": None,
            "source_test_result": None,
            "modified": "2026-09-20T11:50:00+08:00",
        },
    ]


def _seed_retention_rows(fake):
    fake.rows["HBOS Retention Sample"] = [
        {
            "name": "RET-OBS",
            "sample_name": "留样-观察",
            "batch_no": "R01",
            "observed_flag": 1,
            "next_obs_month": 12,
            "next_obs_due_date": "2026-09-20",
            "status": "在库",
            "modified": "2026-09-20T08:00:00+08:00",
        },
        {
            "name": "RET-PENDING",
            "sample_name": "留样-待审",
            "batch_no": "R02",
            "observed_flag": 1,
            "next_obs_month": 12,
            "next_obs_due_date": "2026-09-25",
            "status": "在库",
            "modified": "2026-09-20T08:10:00+08:00",
        },
        {
            "name": "RET-DONE",
            "sample_name": "留样-已完成",
            "batch_no": "R03",
            "observed_flag": 1,
            "next_obs_month": 12,
            "next_obs_due_date": "2026-09-25",
            "status": "在库",
            "modified": "2026-09-20T08:20:00+08:00",
        },
    ]
    fake.rows["HBOS Retention Observation"] = [
        {
            "name": "OBS-PENDING",
            "retention_sample": "RET-PENDING",
            "obs_month": 12,
            "observer": "bob@example.com",
            "reviewed_by": None,
            "modified": "2026-09-20T09:00:00+08:00",
        },
        {
            "name": "OBS-DONE",
            "retention_sample": "RET-DONE",
            "obs_month": 12,
            "observer": "bob@example.com",
            "reviewed_by": "carol@example.com",
            "modified": "2026-09-20T09:10:00+08:00",
        },
    ]
    fake.rows["HBOS Retention Usage Apply"] = [
        {"name": "USE-DRAFT", "status": "草稿", "applicant": "alice@example.com", "modified": "2026-09-20T10:00:00+08:00"},
        {"name": "USE-STOCK", "status": "待库存确认", "applicant": "bob@example.com", "modified": "2026-09-20T10:10:00+08:00"},
        {"name": "USE-QC", "status": "待QC批准", "applicant": "bob@example.com", "modified": "2026-09-20T10:20:00+08:00"},
        {"name": "USE-QA", "status": "待QA批准", "applicant": "bob@example.com", "modified": "2026-09-20T10:30:00+08:00"},
        {"name": "USE-QM", "status": "待QM批准", "applicant": "bob@example.com", "modified": "2026-09-20T10:40:00+08:00"},
        {"name": "USE-EXEC", "status": "已批准", "applicant": "bob@example.com", "modified": "2026-09-20T10:50:00+08:00"},
    ]
    fake.rows["HBOS Retention Disposal Apply"] = [
        {"name": "DSP-DRAFT", "status": "草稿", "disposal_type": "留样期满销毁", "applicant": "alice@example.com", "deadline": None, "disposal_by": None, "monitor_by": None, "modified": "2026-09-20T11:00:00+08:00"},
        {"name": "DSP-QC", "status": "待QC主管审核", "disposal_type": "留样期满销毁", "applicant": "bob@example.com", "deadline": None, "disposal_by": None, "monitor_by": None, "modified": "2026-09-20T11:10:00+08:00"},
        {"name": "DSP-QA", "status": "待QA审核", "disposal_type": "留样期满销毁", "applicant": "bob@example.com", "deadline": None, "disposal_by": None, "monitor_by": None, "modified": "2026-09-20T11:20:00+08:00"},
        {"name": "DSP-CONTINUE", "status": "已批准", "disposal_type": "留样期满继续留样", "applicant": "bob@example.com", "deadline": None, "disposal_by": None, "monitor_by": None, "modified": "2026-09-20T11:30:00+08:00"},
        {"name": "DSP-EXEC", "status": "待执行", "disposal_type": "留样期满销毁", "applicant": "bob@example.com", "deadline": "2026-09-21", "disposal_by": None, "monitor_by": None, "modified": "2026-09-20T11:40:00+08:00"},
        {"name": "DSP-MONITOR", "status": "待执行", "disposal_type": "留样期满销毁", "applicant": "bob@example.com", "deadline": "2026-09-24", "disposal_by": "bob@example.com", "monitor_by": None, "modified": "2026-09-20T11:50:00+08:00"},
        {"name": "DSP-DONE-SIGNS", "status": "待执行", "disposal_type": "留样期满销毁", "applicant": "bob@example.com", "deadline": "2026-09-24", "disposal_by": "bob@example.com", "monitor_by": "carol@example.com", "modified": "2026-09-20T12:00:00+08:00"},
    ]


def test_public_apis_reject_identity_override_and_use_session_identity(service):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer"]
    fake.full_names["alice@example.com"] = "Alice"

    identity = todo_service._current_identity()

    assert identity.user == "alice@example.com"
    assert identity.business_roles == ("LIMS Analyst", "LIMS Reviewer")
    assert identity.full_name == "Alice"
    with pytest.raises(TypeError):
        todo_service.get_my_todos(user="bob@example.com")
    with pytest.raises(TypeError):
        todo_service.get_my_todo_summary(roles=["LIMS Manager"])


def test_identity_and_today_use_supported_frappe_utils(service):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst"]
    fake.get_fullname = None
    fake.utils = types.SimpleNamespace(
        get_fullname=lambda user: "Alice Utils",
        today=lambda: "2026-09-22",
    )

    identity = todo_service._current_identity()

    assert identity.full_name == "Alice Utils"
    assert todo_service._today() == "2026-09-22"


def test_inaccessible_source_doctype_is_skipped_instead_of_crashing(service):
    todo_service, fake = service
    original_get_list = fake.get_list

    def deny_sample_tasks(doctype, *args, **kwargs):
        if doctype == "HBOS Sample Task":
            raise PermissionError("Not permitted")
        return original_get_list(doctype, *args, **kwargs)

    fake.get_list = deny_sample_tasks

    assert todo_service._get_list("HBOS Sample Task", {}, ["name"]) == []


def test_child_table_reads_check_parent_permission_before_get_all(service):
    todo_service, fake = service
    permission_checks = []
    fake.has_permission = lambda doctype, ptype="read", doc=None: permission_checks.append(
        (doctype, ptype, doc)
    ) or doc == "TP-001"
    fake.get_all = lambda doctype, filters=None, fields=None, **_kwargs: [
        {field: row.get(field) for field in fields}
        for row in fake.rows[doctype]
        if row.get("parent") in (filters or {}).get("parent", ["in", []])[1]
    ]
    original_get_list = fake.get_list

    def deny_child_list(doctype, *args, **kwargs):
        if doctype == "HBOS Stability Timepoint Item":
            raise PermissionError("Child table has no permission rows")
        return original_get_list(doctype, *args, **kwargs)

    fake.get_list = deny_child_list
    fake.rows["HBOS Stability Timepoint Item"] = [
        {"parent": "TP-001", "stability_test_item": "STB-ASSAY", "is_required": 1},
    ]

    assert todo_service._stability_timepoint_items(["TP-001"]) == {
        "TP-001": [{"parent": "TP-001", "stability_test_item": "STB-ASSAY", "is_required": 1}]
    }
    assert permission_checks == [("HBOS Stability Timepoint", "read", "TP-001")]


def test_synced_business_coverage_suppresses_only_mapped_stability_record_todo(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst"]
    _seed_stability_rows(fake)
    fake.rows["HBOS Sample"] = [{
        "name": "STABILITY-SAMPLE-1",
        "sample_source": "稳定性",
        "stability_timepoint": "TP-RESULT",
    }]
    fake.rows["HBOS Sample Task"] = [{
        "name": "BUSINESS-TASK-ASSAY",
        "sample": "STABILITY-SAMPLE-1",
        "test_item": "ITEM-ASSAY",
    }]
    fake.rows["HBOS Stability Test Item"] = [{
        "name": "STB-ASSAY",
        "base_test_item": "ITEM-ASSAY",
    }]
    monkeypatch.setattr(todo_service, "_enrich_stability_schedule", _enrich_stability_rows)
    monkeypatch.setattr(todo_service, "_business_stability_items_for_timepoint", lambda _name: {"STB-ASSAY"})

    items = todo_service._collect_stability_todos(todo_service._current_identity())

    assert not any(item["action"] == "record_result" for item in items)


def test_testing_approve_sod_reads_reviewer_field(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Reviewer"]
    _seed_testing_rows(fake)
    fake.rows["HBOS Sample Task"].append({
        "name": "TASK-APPROVE-OWN",
        "sample": "SAMPLE-1",
        "test_item": "ITEM-APPROVE",
        "item_name": "含量",
        "assignee": "bob@example.com",
        "status": "已复核",
        "priority": "常规",
        "due_date": "2026-09-25",
        "modified": "2026-09-20T16:00:00+08:00",
    })
    fake.rows["HBOS Test Result"].append({
        "name": "RESULT-APPROVE-OWN",
        "task": "TASK-APPROVE-OWN",
        "sample": "SAMPLE-1",
        "test_item": "ITEM-APPROVE",
        "item_name": "含量",
        "result_status": "已复核",
        "analyst": "bob@example.com",
        "reviewer": "alice@example.com",
        "modified": "2026-09-20T16:10:00+08:00",
    })
    fake.readable_names["HBOS Sample Task"].add("TASK-APPROVE-OWN")
    fake.readable_names.setdefault("HBOS Test Result", set()).update({
        "RESULT-DRAFT", "RESULT-REVIEW", "RESULT-APPROVE-OWN",
    })
    monkeypatch.setattr(todo_service, "_business_stability_items_for_timepoint", lambda _name: {"STB-ASSAY"})

    items = todo_service.get_my_todos(module="testing", limit=100)["items"]

    assert "RESULT-APPROVE-OWN" not in {item["source_name"] for item in items}


def test_due_at_is_serialized_as_iso_string(service):
    todo_service, _fake = service
    rule = todo_service.find_rule("testing_task", "已分配")
    identity = todo_service.Identity("alice@example.com", "Alice", (), ())

    item = todo_service._make_item(
        rule,
        {"name": "TASK-1"},
        identity,
        "user",
        (),
        title="任务",
        status="已分配",
        due_at=date(2026, 9, 22),
    )

    assert item["due_at"] == "2026-09-22"


def test_testing_provider_combines_direct_and_role_work_without_leaking(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer"]
    _seed_testing_rows(fake)
    monkeypatch.setattr(
        todo_service,
        "_business_stability_items_for_timepoint",
        lambda timepoint: {"STB-ASSAY"} if timepoint == "TP-001" else set(),
    )

    response = todo_service.get_my_todos(limit=50)
    items = {item["source_name"]: item for item in response["items"]}

    assert set(items) == {
        "TASK-ME",
        "TASK-ROLE",
        "TASK-STB-UNMAPPED",
        "RESULT-DRAFT",
        "RESULT-REVIEW",
    }
    assert items["TASK-ME"]["owner_type"] == "user"
    assert items["TASK-ROLE"]["owner_type"] == "role"
    assert items["TASK-STB-UNMAPPED"]["owner_type"] == "role"
    assert items["RESULT-DRAFT"]["owner_type"] == "user"
    assert items["RESULT-REVIEW"]["owner_type"] == "role"
    assert items["TASK-ME"]["route_params"] == {"scope": "mine", "task": "TASK-ME"}
    assert response["filtered_summary"]["assigned_to_me"] == 2
    assert response["filtered_summary"]["role_pending"] == 3
    assert response["filtered_summary"]["by_module"]["testing"] == 5


def test_administrator_only_sees_explicit_assignments(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "Administrator"
    fake.roles["Administrator"] = [
        "System Manager",
        "LIMS Analyst",
        "LIMS Reviewer",
        "LIMS Manager",
    ]
    _seed_testing_rows(fake)
    fake.rows["HBOS Sample Task"].append(
        {
            "name": "TASK-ADMIN",
            "sample": "SAMPLE-1",
            "test_item": "ITEM-ADMIN",
            "item_name": "管理员指派",
            "assignee": "Administrator",
            "due_date": None,
            "priority": "常规",
            "status": "已分配",
            "result": None,
            "modified": "2026-09-20T16:00:00+08:00",
        }
    )
    fake.readable_names["HBOS Sample Task"].add("TASK-ADMIN")
    monkeypatch.setattr(
        todo_service,
        "_business_stability_items_for_timepoint",
        lambda _timepoint: {"STB-ASSAY"},
    )

    response = todo_service.get_my_todos(limit=50)

    assert [item["source_name"] for item in response["items"]] == ["TASK-ADMIN"]
    assert response["items"][0]["owner_type"] == "user"
    assert response["filtered_summary"]["role_pending"] == 0


def test_filters_sort_and_page_are_applied_after_identity_policy(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer"]
    _seed_testing_rows(fake)
    monkeypatch.setattr(todo_service, "_today", lambda: "2026-09-22")
    monkeypatch.setattr(
        todo_service,
        "_business_stability_items_for_timepoint",
        lambda _timepoint: {"STB-ASSAY"},
    )

    response = todo_service.get_my_todos(
        module="testing",
        owner_type="user",
        overdue=True,
        keyword="水分",
        limit=1,
        offset=0,
    )

    assert response["total"] == 1
    assert [item["source_name"] for item in response["items"]] == ["TASK-ME"]
    assert response["filtered_summary"]["total"] == 1


def test_summary_uses_unfiltered_session_scope(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer"]
    fake.full_names["alice@example.com"] = "Alice"
    _seed_testing_rows(fake)
    monkeypatch.setattr(
        todo_service,
        "_business_stability_items_for_timepoint",
        lambda _timepoint: {"STB-ASSAY"},
    )

    response = todo_service.get_my_todo_summary()

    assert response["user"] == {"name": "alice@example.com", "full_name": "Alice"}
    assert response["summary"]["total"] == 5
    assert response["summary"]["assigned_to_me"] == 2
    assert response["summary"]["role_pending"] == 3
    assert response["summary"]["by_module"] == {
        "testing": 5,
        "stability": 0,
        "retention": 0,
        "quality": 0,
        "compliance": 0,
    }
    assert response["generated_at"]


def test_response_contract_has_labels_paging_and_no_unified_write_api(service):
    todo_service, _fake = service

    assert callable(todo_service._action_allowed)
    assert callable(todo_service._serialize_todo)
    assert not hasattr(todo_service, "execute_todo")

    response = todo_service.get_my_todos(limit=7, offset=3)

    assert response["limit"] == 7
    assert response["offset"] == 3
    assert response["items"] == []


def _enrich_stability_rows(rows):
    enriched = []
    for row in rows:
        copy = dict(row)
        if row["name"] == "TP-SAMPLE":
            copy.update(effective_sample_due="2026-09-20", sample_overdue=1)
        if row["name"] == "TP-TEST":
            copy.update(effective_test_due="2026-09-21", test_overdue=1)
        if row["name"] == "TP-RESULT":
            copy.update(effective_test_due="2026-09-25", test_overdue=0)
        enriched.append(copy)
    return enriched


def test_synced_result_is_excluded_from_all_manual_actions(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer"]
    _seed_stability_rows(fake)
    monkeypatch.setattr(todo_service, "_enrich_stability_schedule", _enrich_stability_rows)

    items = todo_service.get_my_todos(module="stability", limit=100)["items"]

    assert "STB-SYNCED" not in {item["source_name"] for item in items}


def test_manual_result_actions_respect_analyst_reviewer_separation(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer", "LIMS QA"]
    _seed_stability_rows(fake)
    monkeypatch.setattr(todo_service, "_enrich_stability_schedule", _enrich_stability_rows)

    items = todo_service.get_my_todos(module="stability", limit=100)["items"]
    names = {item["source_name"] for item in items}

    assert "STB-MANUAL-DRAFT" in names
    assert "STB-REVIEW-OWN" not in names
    assert "STB-REVIEW-OTHER" in names
    assert "STB-APPROVE-OWN" not in names
    assert "STB-APPROVE-OTHER" in names


def test_result_todo_has_no_due_date_or_overdue_flag(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer"]
    _seed_stability_rows(fake)
    monkeypatch.setattr(todo_service, "_enrich_stability_schedule", _enrich_stability_rows)

    result_items = [
        item for item in todo_service.get_my_todos(module="stability", limit=100)["items"]
        if item["source_doctype"] == "HBOS Stability Result"
    ]

    assert result_items
    assert all(item["due_at"] is None and item["is_overdue"] is False for item in result_items)


def test_sampling_and_testing_use_effective_due_values(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst"]
    _seed_stability_rows(fake)
    monkeypatch.setattr(todo_service, "_enrich_stability_schedule", _enrich_stability_rows)

    items = todo_service.get_my_todos(module="stability", limit=100)["items"]
    by_name = {item["source_name"]: item for item in items}

    assert by_name["TP-SAMPLE"]["due_at"] == "2026-09-20"
    assert by_name["TP-SAMPLE"]["is_overdue"] is True
    assert by_name["TP-TEST"]["due_at"] == "2026-09-21"
    assert by_name["TP-TEST"]["is_overdue"] is True


def test_service_never_queries_effective_due_as_database_column():
    service_path = Path(__file__).resolve().parents[1] / "hb_lims_app" / "hbos_lims" / "todo_service.py"
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    for call in [node for node in ast.walk(tree) if isinstance(node, ast.Call)]:
        if not (isinstance(call.func, ast.Name) and call.func.id == "_get_list"):
            continue
        fields_keyword = next((kw for kw in call.keywords if kw.arg == "fields"), None)
        if fields_keyword is None:
            continue
        field_names = [
            node.value for node in ast.walk(fields_keyword.value)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        assert "effective_sample_due" not in field_names
        assert "effective_test_due" not in field_names


def test_retention_provider_emits_one_current_action_per_source(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = [
        "LIMS Analyst", "LIMS Reviewer", "LIMS QA", "LIMS Manager",
    ]
    _seed_retention_rows(fake)
    monkeypatch.setattr(todo_service, "_today", lambda: "2026-09-22")

    items = todo_service.get_my_todos(module="retention", limit=100)["items"]
    by_name = {}
    for item in items:
        by_name.setdefault(item["source_name"], []).append(item)

    assert by_name["RET-OBS"][0]["action"] == "record_observation"
    assert "RET-PENDING" not in by_name
    assert "RET-DONE" not in by_name
    assert by_name["OBS-PENDING"][0]["action"] == "review_observation"
    assert by_name["USE-DRAFT"][0]["owner_type"] == "user"
    assert by_name["USE-DRAFT"][0]["action"] == "submit_usage_apply"
    assert by_name["USE-STOCK"][0]["action"] == "confirm_stock"
    assert by_name["USE-QC"][0]["action"] == "approve_usage"
    assert by_name["USE-QA"][0]["action"] == "approve_usage"
    assert by_name["USE-QM"][0]["action"] == "approve_usage"
    assert by_name["USE-EXEC"][0]["action"] == "execute_usage"
    assert by_name["DSP-DRAFT"][0]["owner_type"] == "user"
    assert by_name["DSP-DRAFT"][0]["action"] == "submit_disposal_apply"
    assert by_name["DSP-QC"][0]["action"] == "approve_disposal"
    assert by_name["DSP-QA"][0]["action"] == "approve_disposal"
    assert by_name["DSP-CONTINUE"][0]["action"] == "continue_retention"
    assert by_name["DSP-EXEC"][0]["action"] == "dispose_handle"
    assert by_name["DSP-MONITOR"][0]["action"] == "dispose_monitor"
    assert "DSP-DONE-SIGNS" not in by_name
    assert by_name["DSP-EXEC"][0]["is_overdue"] is True


def test_retention_due_fields_map_only_to_actions_that_have_deadlines(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer", "LIMS QA", "LIMS Manager"]
    _seed_retention_rows(fake)
    monkeypatch.setattr(todo_service, "_today", lambda: "2026-09-22")

    items = todo_service.get_my_todos(module="retention", limit=100)["items"]
    by_name = {item["source_name"]: item for item in items}

    assert by_name["RET-OBS"]["due_at"] == "2026-09-20"
    assert by_name["DSP-EXEC"]["due_at"] == "2026-09-21"
    assert by_name["USE-QC"]["due_at"] is None
    assert by_name["DSP-QC"]["due_at"] is None


def test_summary_cache_key_contains_user_and_roles_hash(service):
    todo_service, fake = service

    key = todo_service._summary_cache_key("alice@example.com", ("LIMS Analyst", "LIMS Reviewer"))

    assert "alice@example.com" in key
    assert todo_service._roles_hash(("LIMS Analyst", "LIMS Reviewer")) in key
    assert key != todo_service._summary_cache_key("bob@example.com", ("LIMS Analyst", "LIMS Reviewer"))


def test_summary_cache_ttl_is_30_seconds(service):
    todo_service, _fake = service

    assert todo_service.SUMMARY_CACHE_TTL_SECONDS == 30


def test_list_query_does_not_use_summary_cache(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst"]
    monkeypatch.setattr(todo_service, "_summary_cache_get", lambda _key: (_ for _ in ()).throw(AssertionError("list read cache")))

    todo_service.get_my_todos(limit=1)


def test_my_testing_task_names_include_result_linked_tasks(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst", "LIMS Reviewer"]
    _seed_testing_rows(fake)
    monkeypatch.setattr(todo_service, "_business_stability_items_for_timepoint", lambda _name: {"STB-ASSAY"})

    assert set(todo_service.get_my_testing_task_names()) == {
        "TASK-ME", "TASK-ROLE", "TASK-STB-UNMAPPED",
        "TASK-RESULT-DRAFT", "TASK-RESULT-REVIEW",
    }


def test_failed_summary_refresh_does_not_return_another_users_value(service, monkeypatch):
    todo_service, fake = service
    fake.session.user = "alice@example.com"
    fake.roles["alice@example.com"] = ["LIMS Analyst"]
    key = todo_service._summary_cache_key("bob@example.com", ("LIMS Analyst",))
    fake.cache_backend.values[key] = {"summary": {"total": 999}}
    monkeypatch.setattr(todo_service, "_collect_all", lambda _identity: (_ for _ in ()).throw(RuntimeError("db down")))

    with pytest.raises(RuntimeError):
        todo_service.get_my_todo_summary()


def test_commit_hooks_invalidate_current_users_summary():
    app_root = Path(__file__).resolve().parents[1] / "hb_lims_app" / "hbos_lims"
    service_paths = [
        app_root / "lims_service.py",
        app_root / "stability_service.py",
        app_root / "retention_service.py",
    ]
    for path in service_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        commit = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_commit"
        )
        source = ast.get_source_segment(path.read_text(encoding="utf-8"), commit) or ""
        assert "frappe.db.commit()" in source
        assert "invalidate_my_todo_summary_cache" in source
