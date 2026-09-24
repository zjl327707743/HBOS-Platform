# -*- coding: utf-8 -*-
"""我的待办页面与侧栏轮询生命周期契约。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "frontend" / "hbos-lims-web"


def _read(relative):
    return (WEB / relative).read_text(encoding="utf-8")


def test_my_todo_route_and_page_show_identity_dimensions():
    router = _read("src/router/index.ts")
    page = _read("src/views/MyTodosView.vue")

    assert "path: 'my-todos'" in router
    assert "owner_type" in page
    assert "module_label" in page
    assert "指派给我" in page
    assert "角色待处理" in page


def test_my_todo_page_has_visible_only_polling_and_cleanup():
    page = _read("src/views/MyTodosView.vue")

    assert "POLL_INTERVAL_MS = 60_000" in page
    assert "document.visibilityState === 'visible'" in page
    assert "setInterval(refreshWhenVisible, POLL_INTERVAL_MS)" in page
    assert "clearInterval(timer)" in page
    assert "addEventListener('visibilitychange'" in page
    assert "removeEventListener('visibilitychange'" in page
    assert "addEventListener('focus'" in page
    assert "removeEventListener('focus'" in page


def test_sidebar_uses_personal_summary_and_keeps_only_stability_child_badges():
    sidebar = _read("src/components/layout/SidebarNav.vue")

    assert "todoStore.summary.total" in sidebar
    assert "totalAttentionCount" not in sidebar
    assert "stabilityCounts.value.schedule + stabilityCounts.value.results" not in sidebar
    assert "itemBadge(item)" in sidebar


def test_store_has_logout_cleanup_and_sidebar_has_no_global_timer():
    store = _read("src/stores/todo.ts")
    sidebar = _read("src/components/layout/SidebarNav.vue")

    assert "clearForLogout" in store
    assert "setInterval" not in sidebar
    assert "clearInterval" not in sidebar


def test_todo_deep_links_are_consumed_by_each_source_view():
    task_board = _read("src/views/TaskBoardView.vue")
    schedule = _read("src/views/StabilityScheduleView.vue")
    result = _read("src/views/StabilityResultView.vue")
    observations = _read("src/views/RetentionObservationsView.vue")
    usage = _read("src/views/RetentionUsageView.vue")
    disposal = _read("src/views/RetentionDisposalView.vue")

    assert "scope" in task_board and "task" in task_board
    assert "timepoint" in schedule
    assert "timepoint" in result and "result" in result
    assert "sample" in observations and "observation" in observations
    assert "usage" in usage
    assert "disposal" in disposal and "focus" in disposal


def test_todo_actions_delegate_to_original_apis_and_refresh_after_failure():
    actions = _read("src/features/todos/todoActions.ts")
    retention_api = _read("src/api/retention.ts")
    page = _read("src/views/MyTodosView.vue")

    for action in (
        "start_task", "review_result", "approve_result", "complete_sampling",
        "start_testing", "review_observation", "submit_usage_apply", "confirm_stock",
        "approve_usage", "execute_usage", "submit_disposal_apply", "approve_disposal",
        "continue_retention", "dispose_handle", "dispose_monitor",
    ):
        assert action in actions
    assert "reviewObservationByName" in retention_api
    assert "await context.refresh()" in actions
    assert "context.notifyError(errorMessage(error))" not in actions
    assert "removeResolved" not in actions
    assert "runTodoAction" in page
    assert "actionLoadingKey" in page


def test_todo_page_refreshes_select_filters_and_exposes_supported_modules_only():
    page = _read("src/views/MyTodosView.vue")

    assert "function onModuleChange" in page
    assert "function onOwnerChange" in page
    assert "void todoStore.fetchList()" in page
    assert "value: 'quality'" not in page
    assert "value: 'compliance'" not in page
    assert "statusOptions" in page
    assert "priorityOptions" in page


def test_todo_page_distinguishes_initial_error_from_successful_empty_state():
    page = _read("src/views/MyTodosView.vue")
    store = _read("src/stores/todo.ts")

    assert "listLoaded" in store
    assert "todoStore.error && !todoStore.listLoaded" in page
    assert "待办加载失败，请刷新重试" in page


def test_task_board_does_not_ship_test_user_or_test_department_defaults():
    page = _read("src/views/TaskBoardView.vue")

    assert "test-hbos-m2-analyst@test.local" not in page
    assert "Administrator'" not in page
    assert "TEST-HBOS-M2-DEP-PH" not in page
    assert "listDoctype" in page


def test_recent_shortcuts_do_not_claim_fake_visit_times():
    navigation = _read("src/components/layout/sidebarNavigation.ts")

    assert "2 小时前" not in navigation
    assert "昨天" not in navigation
