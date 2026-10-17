from __future__ import annotations

import unittest

from hb_lims_app.hbos_lims.portal.tasks import (
    normalize_cursor,
    normalize_priority,
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

    def test_cursor_is_offset_but_remains_provider_opaque(self):
        self.assertEqual(0, normalize_cursor(None))
        self.assertEqual(20, normalize_cursor("20"))
        for invalid in ("-1", "bad"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    normalize_cursor(invalid)


if __name__ == "__main__":
    unittest.main()
