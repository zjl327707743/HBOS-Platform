# -*- coding: utf-8 -*-
"""个人待办纯契约测试：身份、当前动作、去重与排序。"""

from datetime import date

from hb_lims_app.hbos_lims import workflow_contract as wf
from hb_lims_app.hbos_lims.todo_contract import (
    TODO_RULES,
    business_roles_for_user,
    current_action,
    deduplicate_todos,
    find_rule,
    make_todo_key,
    resolve_owner_type,
    sort_todos,
    testing_task_is_covered as _testing_task_is_covered,
)


def test_administrator_has_no_role_pending_roles():
    roles = ["Administrator", "System Manager", "LIMS Analyst", "LIMS Reviewer"]

    assert business_roles_for_user("Administrator", roles) == ()


def test_system_manager_role_does_not_expand_business_pending():
    assert business_roles_for_user("manager@example.com", ["System Manager"]) == ()


def test_only_supported_lims_roles_are_kept_once_in_contract_order():
    roles = [
        "LIMS Reviewer",
        "Employee",
        "LIMS Analyst",
        "LIMS Reviewer",
        "LIMS QA",
    ]

    assert business_roles_for_user("multi@example.com", roles) == (
        "LIMS Analyst",
        "LIMS Reviewer",
        "LIMS QA",
    )


def test_direct_assignment_wins_over_role_match():
    assert resolve_owner_type(
        current_user="analyst@example.com",
        assigned_user="analyst@example.com",
        role_match=True,
    ) == "user"


def test_other_users_assignment_blocks_role_pending():
    assert resolve_owner_type(
        current_user="reviewer@example.com",
        assigned_user="other@example.com",
        role_match=True,
    ) is None


def test_unassigned_action_uses_role_pending_only_when_role_matches():
    assert resolve_owner_type("reviewer@example.com", None, True) == "role"
    assert resolve_owner_type("reviewer@example.com", None, False) is None


def test_only_mapped_timepoint_item_is_suppressed():
    mapping = {
        "含量测定": "STB-ASSAY",
        "水分": "STB-WATER",
    }
    timepoint_items = {"STB-ASSAY"}

    assert _testing_task_is_covered("含量测定", mapping, timepoint_items) is True
    assert _testing_task_is_covered("水分", mapping, timepoint_items) is False
    assert _testing_task_is_covered("干燥失重", mapping, timepoint_items) is False


def test_synced_stability_result_has_no_manual_action():
    assert current_action(
        module="stability_result",
        status="已提交",
        source_test_result="HBOS-TR-0001",
    ) is None


def test_each_simple_state_resolves_to_one_current_action():
    expected = {
        ("testing_task", "已分配"): "start_task",
        ("testing_result", "草稿"): "submit_result",
        ("testing_result", "已提交"): "review_result",
        ("testing_result", "已复核"): "approve_result",
        ("stability_timepoint", "待取样"): "complete_sampling",
        ("stability_timepoint", "待检测"): "start_testing",
        ("stability_result", "草稿"): "submit_result",
        ("stability_result", "已提交"): "review_result",
        ("stability_result", "已复核"): "approve_result",
        ("retention_usage", "草稿"): "submit_usage_apply",
        ("retention_usage", "待库存确认"): "confirm_stock",
        ("retention_usage", "待QC批准"): "approve_usage",
        ("retention_usage", "待QA批准"): "approve_usage",
        ("retention_usage", "待QM批准"): "approve_usage",
        ("retention_usage", "已批准"): "execute_usage",
        ("retention_disposal", "草稿"): "submit_disposal_apply",
        ("retention_disposal", "待QC主管审核"): "approve_disposal",
        ("retention_disposal", "待QC负责人审核"): "approve_disposal",
        ("retention_disposal", "待QA审核"): "approve_disposal",
        ("retention_disposal", "待QA负责人审核"): "approve_disposal",
        ("retention_disposal", "待QM批准"): "approve_disposal",
    }

    assert {
        key: current_action(module=key[0], status=key[1])
        for key in expected
    } == expected
    assert current_action(module="testing_task", status="已批准") is None


def test_rules_derive_allowed_roles_from_workflow_contract():
    testing = find_rule("testing_task", "已分配")
    stability = find_rule("stability_result", "已提交")

    assert set(testing.allowed_roles) == wf.ACTION_ROLES["start_task"] - {wf.ROLE_SYSTEM}
    assert set(stability.allowed_roles) == (
        wf.SCOPED_ACTION_ROLES[("HBOS Stability Result", "review_result")]
        - {wf.ROLE_SYSTEM}
    )


def test_rules_keep_result_due_dates_empty_and_routes_real():
    rules = [
        find_rule("stability_result", "草稿"),
        find_rule("stability_result", "已提交"),
        find_rule("stability_result", "已复核"),
    ]

    assert all(rule.due_extractor is None for rule in rules)
    assert all(rule.route == "/stability/results" for rule in rules)
    assert all(rule.route_param_fields == ("timepoint", "result") for rule in rules)


def test_todo_key_is_stable_and_unambiguous():
    assert make_todo_key("HBOS Sample Task", "TASK-0001", "start_task") == (
        "HBOS Sample Task:TASK-0001:start_task"
    )


def test_deduplicate_prefers_direct_assignment_for_same_work():
    role_item = {
        "todo_key": "HBOS Sample Task:TASK-0001:start_task",
        "owner_type": "role",
        "title": "角色任务",
    }
    direct_item = {
        "todo_key": "HBOS Sample Task:TASK-0001:start_task",
        "owner_type": "user",
        "title": "指派任务",
    }

    assert deduplicate_todos([role_item, direct_item]) == [direct_item]
    assert deduplicate_todos([direct_item, role_item]) == [direct_item]


def test_sorting_is_overdue_then_due_then_priority_then_modified():
    items = [
        {
            "todo_key": "normal-no-due",
            "is_overdue": False,
            "due_at": None,
            "priority": "普通",
            "modified_at": "2026-09-22T11:00:00+08:00",
        },
        {
            "todo_key": "overdue-later",
            "is_overdue": True,
            "due_at": date(2026, 9, 20),
            "priority": "普通",
            "modified_at": "2026-09-22T08:00:00+08:00",
        },
        {
            "todo_key": "overdue-earlier",
            "is_overdue": True,
            "due_at": "2026-09-19",
            "priority": "低",
            "modified_at": "2026-09-22T07:00:00+08:00",
        },
        {
            "todo_key": "normal-urgent",
            "is_overdue": False,
            "due_at": "2026-09-23",
            "priority": "加急",
            "modified_at": "2026-09-22T06:00:00+08:00",
        },
    ]

    assert [item["todo_key"] for item in sort_todos(items)] == [
        "overdue-earlier",
        "overdue-later",
        "normal-urgent",
        "normal-no-due",
    ]


def test_rule_keys_are_unique():
    keys = [(rule.module, rule.status, rule.condition) for rule in TODO_RULES]

    assert len(keys) == len(set(keys))
