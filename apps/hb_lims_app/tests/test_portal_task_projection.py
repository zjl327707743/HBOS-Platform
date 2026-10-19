from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from hb_lims_app.hbos_lims.portal.tasks import (
    get_task_projection,
    normalize_cursor,
    normalize_priority,
    normalize_view,
    project_todo,
)


class PortalTaskProjectionTest(unittest.TestCase):
    def test_projects_existing_todo_without_copying_business_state(self):
        task = project_todo(
            {
                "todo_key": "HBOS Test Result:RESULT-001:review_result",
                "module": "testing",
                "title": "阿莫西林 · 含量",
                "description": "复核结果：含量",
                "action": "review_result",
                "action_label": "复核结果",
                "status": "已提交",
                "priority": "高",
                "due_at": "2026-09-25",
                "is_overdue": True,
                "owner_type": "role",
                "route": "/tasks",
                "route_params": {"scope": "mine", "task": "TASK-001"},
                "modified_at": "2026-09-24T17:30:00+08:00",
            }
        )

        self.assertEqual(
            "lims:HBOS Test Result:RESULT-001:review_result",
            task["task_id"],
        )
        self.assertEqual("lims", task["app_id"])
        self.assertEqual("testing", task["category"])
        self.assertEqual("high", task["priority"])
        self.assertTrue(task["overdue"])
        self.assertEqual("role_pool", task["assignment_type"])
        self.assertEqual("已提交", task["status"])
        self.assertEqual(
            "/hbos/lims/tasks?scope=mine&task=TASK-001",
            task["deep_link"],
        )
        self.assertNotIn("candidate_roles", task)
        self.assertNotIn("source_doctype", task)

    def test_priority_vocabulary_is_platform_semantic(self):
        self.assertEqual("critical", normalize_priority("加急"))
        self.assertEqual("high", normalize_priority("高"))
        self.assertEqual("normal", normalize_priority("常规"))
        self.assertEqual("low", normalize_priority("低"))
        self.assertEqual("normal", normalize_priority("未知"))
        self.assertEqual("high", normalize_priority("high"))

    def test_projection_translates_frontend_priority_filter_to_domain_value(self):
        high_item = {
            "todo_key": "HBOS Test Result:RESULT-001:review_result",
            "module": "testing",
            "title": "阿莫西林 · 含量",
            "description": "复核结果：含量",
            "action": "review_result",
            "action_label": "复核结果",
            "status": "已提交",
            "priority": "高",
            "owner_type": "role",
            "route": "/tasks",
            "route_params": {"scope": "mine", "task": "TASK-001"},
        }
        low_item = {**high_item, "todo_key": "low", "priority": "低"}
        fake_frappe = types.SimpleNamespace(whitelist=lambda *args, **kwargs: (lambda fn: fn))
        with patch.dict(sys.modules, {"frappe": fake_frappe}), patch(
            "hb_lims_app.hbos_lims.todo_service.get_my_todos",
            return_value={"items": [high_item, low_item]},
        ) as get_todos, patch(
            "hb_lims_app.hbos_lims.portal.tasks.get_pending_coa_todos",
            return_value=[],
        ):
            payload = get_task_projection(limit=20, priority="high")

        get_todos.assert_called_once_with(
            limit=200,
            offset=0,
            status=None,
            priority="高",
            keyword=None,
        )
        self.assertEqual(["high"], [item["priority"] for item in payload["tasks"]])

    def test_cursor_is_offset_but_remains_provider_opaque(self):
        self.assertEqual(0, normalize_cursor(None))
        self.assertEqual(20, normalize_cursor("20"))
        for invalid in ("-1", "bad"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    normalize_cursor(invalid)

    def test_task_views_are_stable_and_reject_unknown_values(self):
        self.assertIsNone(normalize_view(None))
        self.assertEqual("my-testing", normalize_view("my-testing"))
        self.assertEqual("my-review", normalize_view("my-review"))
        self.assertEqual("my-approval", normalize_view("my-approval"))
        with self.assertRaises(ValueError):
            normalize_view("all-roles")

    def test_task_projection_maps_approval_view_and_preserves_domain_status(self):
        result_item = {
            "todo_key": "HBOS Test Result:RESULT-001:approve_result",
            "module": "testing",
            "title": "阿莫西林 · 含量",
            "description": "批准结果：含量",
            "action": "approve_result",
            "action_label": "批准结果",
            "status": "已复核",
            "priority": "常规",
            "owner_type": "role",
            "route": "/tasks",
            "route_params": {"scope": "mine", "task": "TASK-001"},
        }
        coa_item = {
            "todo_key": "HBOS COA:COA-001:publish_coa",
            "module": "quality",
            "title": "阿莫西林 · COA",
            "description": "发布 COA：SAMPLE-001",
            "action": "publish_coa",
            "action_label": "发布 COA",
            "status": "已审核",
            "priority": "常规",
            "owner_type": "role",
            "route": "/tasks",
            "route_params": {"scope": "mine", "view": "my-approval", "coa": "COA-001"},
        }
        fake_frappe = types.SimpleNamespace(whitelist=lambda *args, **kwargs: (lambda fn: fn))
        with patch.dict(sys.modules, {"frappe": fake_frappe}), patch(
            "hb_lims_app.hbos_lims.todo_service.get_my_todos",
            return_value={"items": [result_item]},
        ), patch(
            "hb_lims_app.hbos_lims.portal.tasks.get_pending_coa_todos",
            return_value=[coa_item],
        ):
            payload = get_task_projection(limit=20, view="my-approval")

        self.assertEqual(2, payload["total"])
        self.assertEqual("my-approval", payload["view"])
        self.assertEqual({"已复核", "已审核"}, {item["status"] for item in payload["tasks"]})
        self.assertTrue(all(item["action"] in {"approve_result", "publish_coa"} for item in payload["tasks"]))


if __name__ == "__main__":
    unittest.main()
