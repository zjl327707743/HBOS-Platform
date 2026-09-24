# -*- coding: utf-8 -*-
"""M2-R3 状态机契约测试：Sample / Task / Result 全状态转移表 + 角色矩阵。"""

import unittest

from hb_lims_app.hbos_lims import workflow_contract as wf


class TestSampleTransitions(unittest.TestCase):
    def test_valid_path(self):
        path = [wf.SAMPLE_DRAFT, wf.SAMPLE_REGISTERED, wf.SAMPLE_TESTING,
                wf.SAMPLE_TESTED, wf.SAMPLE_RELEASED]
        for cur, nxt in zip(path, path[1:]):
            self.assertTrue(wf.can_transition(wf.FLOW_SAMPLE, cur, nxt), f"{cur}->{nxt}")

    def test_invalid_jumps(self):
        self.assertFalse(wf.can_transition(wf.FLOW_SAMPLE, wf.SAMPLE_DRAFT, wf.SAMPLE_TESTED))
        self.assertFalse(wf.can_transition(wf.FLOW_SAMPLE, wf.SAMPLE_DRAFT, wf.SAMPLE_RELEASED))
        self.assertFalse(wf.can_transition(wf.FLOW_SAMPLE, wf.SAMPLE_REGISTERED, wf.SAMPLE_TESTED))
        self.assertFalse(wf.can_transition(wf.FLOW_SAMPLE, wf.SAMPLE_RELEASED, wf.SAMPLE_REJECTED))

    def test_oos_lock_is_terminal(self):
        self.assertTrue(wf.can_transition(wf.FLOW_SAMPLE, wf.SAMPLE_TESTING, wf.SAMPLE_OOS))
        self.assertFalse(wf.can_transition(wf.FLOW_SAMPLE, wf.SAMPLE_OOS, wf.SAMPLE_RELEASED))
        self.assertTrue(wf.is_final_state(wf.FLOW_SAMPLE, wf.SAMPLE_OOS))


class TestTaskTransitions(unittest.TestCase):
    def test_valid_path(self):
        path = [wf.TASK_PENDING, wf.TASK_ASSIGNED, wf.TASK_TESTING,
                wf.TASK_SUBMITTED, wf.TASK_REVIEWED, wf.TASK_APPROVED]
        for cur, nxt in zip(path, path[1:]):
            self.assertTrue(wf.can_transition(wf.FLOW_TASK, cur, nxt), f"{cur}->{nxt}")

    def test_invalid_jumps(self):
        self.assertFalse(wf.can_transition(wf.FLOW_TASK, wf.TASK_PENDING, wf.TASK_TESTING))
        self.assertFalse(wf.can_transition(wf.FLOW_TASK, wf.TASK_ASSIGNED, wf.TASK_APPROVED))
        self.assertFalse(wf.can_transition(wf.FLOW_TASK, wf.TASK_SUBMITTED, wf.TASK_APPROVED))
        self.assertFalse(wf.can_transition(wf.FLOW_TASK, wf.TASK_APPROVED, wf.TASK_REVIEWED))

    def test_oos_path(self):
        self.assertTrue(wf.can_transition(wf.FLOW_TASK, wf.TASK_TESTING, wf.TASK_OOS_CANDIDATE))
        self.assertTrue(wf.can_transition(wf.FLOW_TASK, wf.TASK_SUBMITTED, wf.TASK_OOS_CANDIDATE))
        self.assertTrue(wf.can_transition(wf.FLOW_TASK, wf.TASK_REVIEWED, wf.TASK_OOS_CANDIDATE))
        self.assertTrue(wf.can_transition(wf.FLOW_TASK, wf.TASK_OOS_CANDIDATE, wf.TASK_OOS_LOCKED))
        self.assertTrue(wf.can_transition(wf.FLOW_TASK, wf.TASK_OOS_CANDIDATE, wf.TASK_TESTING))
        self.assertFalse(wf.can_transition(wf.FLOW_TASK, wf.TASK_OOS_LOCKED, wf.TASK_APPROVED))

    def test_revision_rollback_from_approved(self):
        # 已批准结果修订后任务回退待复核（已提交）
        self.assertTrue(wf.can_transition(wf.FLOW_TASK, wf.TASK_APPROVED, wf.TASK_SUBMITTED))
        # 已批准 -> 已复核 仍非法（只能回退到已提交）
        self.assertFalse(wf.can_transition(wf.FLOW_TASK, wf.TASK_APPROVED, wf.TASK_REVIEWED))


class TestResultTransitions(unittest.TestCase):
    def test_valid_path(self):
        path = [wf.RESULT_DRAFT, wf.RESULT_SUBMITTED, wf.RESULT_REVIEWED, wf.RESULT_APPROVED]
        for cur, nxt in zip(path, path[1:]):
            self.assertTrue(wf.can_transition(wf.FLOW_RESULT, cur, nxt), f"{cur}->{nxt}")

    def test_invalid_jumps(self):
        self.assertFalse(wf.can_transition(wf.FLOW_RESULT, wf.RESULT_DRAFT, wf.RESULT_REVIEWED))
        self.assertFalse(wf.can_transition(wf.FLOW_RESULT, wf.RESULT_DRAFT, wf.RESULT_APPROVED))
        self.assertFalse(wf.can_transition(wf.FLOW_RESULT, wf.RESULT_SUBMITTED, wf.RESULT_APPROVED))
        self.assertFalse(wf.can_transition(wf.FLOW_RESULT, wf.RESULT_APPROVED, wf.RESULT_REVIEWED))

    def test_revision_path(self):
        for state in (wf.RESULT_DRAFT, wf.RESULT_SUBMITTED, wf.RESULT_REVIEWED):
            self.assertTrue(wf.can_transition(wf.FLOW_RESULT, state, wf.RESULT_REVISED), state)
        self.assertFalse(wf.can_transition(wf.FLOW_RESULT, wf.RESULT_APPROVED, wf.RESULT_REVISED))
        self.assertTrue(wf.is_final_state(wf.FLOW_RESULT, wf.RESULT_APPROVED))
        self.assertTrue(wf.is_final_state(wf.FLOW_RESULT, wf.RESULT_REVISED))


class TestRoleMatrix(unittest.TestCase):
    def test_submit_roles(self):
        self.assertTrue(wf.action_allowed("submit_result", wf.ROLE_ANALYST))
        self.assertTrue(wf.action_allowed("submit_result", wf.ROLE_MANAGER))
        self.assertFalse(wf.action_allowed("submit_result", wf.ROLE_REVIEWER))

    def test_review_roles(self):
        self.assertTrue(wf.action_allowed("review_result", wf.ROLE_REVIEWER))
        self.assertTrue(wf.action_allowed("review_result", wf.ROLE_MANAGER))
        self.assertFalse(wf.action_allowed("review_result", wf.ROLE_ANALYST))

    def test_approve_roles(self):
        self.assertTrue(wf.action_allowed("approve_result", wf.ROLE_REVIEWER))
        self.assertFalse(wf.action_allowed("approve_result", wf.ROLE_ANALYST))

    def test_revise_manager_only(self):
        self.assertTrue(wf.action_allowed("revise_result", wf.ROLE_MANAGER))
        self.assertFalse(wf.action_allowed("revise_result", wf.ROLE_ANALYST))
        self.assertFalse(wf.action_allowed("revise_result", wf.ROLE_REVIEWER))

    def test_assign_manager_only(self):
        self.assertTrue(wf.action_allowed("assign_task", wf.ROLE_MANAGER))
        self.assertFalse(wf.action_allowed("assign_task", wf.ROLE_ANALYST))

    def test_release_roles(self):
        self.assertTrue(wf.action_allowed("release_sample", wf.ROLE_REVIEWER))
        self.assertTrue(wf.action_allowed("release_sample", wf.ROLE_MANAGER))

    def test_unknown_action_denied(self):
        self.assertFalse(wf.action_allowed("hack", wf.ROLE_MANAGER))


if __name__ == "__main__":
    unittest.main()
