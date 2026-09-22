# -*- coding: utf-8 -*-
"""个人待办聚合服务的可执行边界测试。"""

import importlib
import sys
import types
from collections import defaultdict
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
