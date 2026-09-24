# -*- coding: utf-8 -*-
"""待检任务看板个人作用域的可执行契约测试。"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest


REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / "hb_lims_app"
    / "hbos_lims"
    / "report"
    / "待检任务看板"
    / "待检任务看板.py"
)


class FakeDB:
    def __init__(self):
        self.calls = []

    def sql(self, query, params, as_dict=0):
        self.calls.append((query, params, as_dict))
        return []


@pytest.fixture
def report_module(monkeypatch):
    fake_frappe = types.ModuleType("frappe")
    fake_frappe._ = lambda value: value
    fake_frappe.db = FakeDB()
    fake_frappe.utils = types.SimpleNamespace(today=lambda: "2026-09-22")
    monkeypatch.setitem(sys.modules, "frappe", fake_frappe)
    monkeypatch.setitem(
        sys.modules,
        "hb_lims_app.hbos_lims.todo_service",
        types.SimpleNamespace(get_my_testing_task_names=lambda: ["TASK-MINE-1", "TASK-MINE-2"]),
    )
    spec = importlib.util.spec_from_file_location("todo_report_under_test", REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, fake_frappe


def test_mine_scope_uses_current_session_not_assignee_filter(report_module):
    report, fake_frappe = report_module

    report._fetch({"scope": "mine", "assignee": "bob@example.com"})

    query, params, _ = fake_frappe.db.calls[-1]
    assert "t.name IN %(task_names)s" in query
    assert params["task_names"] == ("TASK-MINE-1", "TASK-MINE-2")
    assert "assignee" not in params


def test_global_scope_keeps_original_report_behavior(report_module):
    report, fake_frappe = report_module

    report._fetch({"assignee": "bob@example.com"})

    query, params, _ = fake_frappe.db.calls[-1]
    assert "t.assignee = %(assignee)s" in query
    assert params["assignee"] == "bob@example.com"
    assert "task_names" not in params


def test_mine_scope_only_returns_current_users_testing_task_names(report_module):
    report, fake_frappe = report_module

    report._fetch({"scope": "mine"})

    _query, params, _ = fake_frappe.db.calls[-1]
    assert set(params["task_names"]) == {"TASK-MINE-1", "TASK-MINE-2"}
