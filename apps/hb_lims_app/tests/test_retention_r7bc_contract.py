# -*- coding: utf-8 -*-
"""M2-R7 R7B/R7C 契约纯函数单测（零 Frappe 依赖）。"""

import pytest

from hb_lims_app.hbos_lims import retention_contract as rtc
from hb_lims_app.hbos_lims import workflow_contract as wf


class TestR7CTransitions:
	def test_usage_flow_forward_and_terminal(self):
		trans = wf.USAGE_APPLY_TRANSITIONS
		assert trans[wf.USE_DRAFT] == {wf.USE_WAIT_STOCK, wf.USE_CANCELLED}
		assert wf.USE_WAIT_QC in trans[wf.USE_WAIT_STOCK]
		assert wf.USE_APPROVED in trans[wf.USE_WAIT_QM]
		# rev6 逃生口：已批准可取消
		assert wf.USE_CANCELLED in trans[wf.USE_APPROVED]
		assert trans[wf.USE_EXECUTED] == set()
		assert trans[wf.USE_REJECTED] == set()
		assert trans[wf.USE_CANCELLED] == set()

	def test_disposal_flow_4_5_dual_path(self):
		trans = wf.DISPOSAL_APPLY_TRANSITIONS
		# 5 级/4 级双路径：待QA审核 → 待QA负责人审核 或 待QM批准
		assert {wf.DSP_WAIT_QA_LEAD, wf.DSP_WAIT_QM, wf.DSP_REJECTED} <= trans[wf.DSP_WAIT_QA_REVIEW]
		assert wf.DSP_WAIT_EXECUTE in trans[wf.DSP_APPROVED]
		# rev6 逃生口：待执行可取消
		assert wf.DSP_CANCELLED in trans[wf.DSP_WAIT_EXECUTE]
		assert trans[wf.DSP_DONE] == set()

	def test_transitions_registered(self):
		assert wf.FLOW_USAGE_APPLY in wf.FLOW_TRANSITIONS
		assert wf.FLOW_DISPOSAL_APPLY in wf.FLOW_TRANSITIONS

	def test_r7b_r7c_actions_registered(self):
		for action in ("select_obs_batch", "record_observation", "review_observation",
					   "create_usage_apply", "usage_confirm", "usage_qa", "usage_qm",
					   "usage_execute", "usage_cancel", "create_disposal_apply",
					   "disposal_qc", "disposal_qa", "disposal_handler",
					   "disposal_monitor", "disposal_cancel", "transfer_out"):
			assert action in wf.ACTION_ROLES, action
		# 角色分离：QM/逃生口仅 Manager+System
		assert wf.ACTION_ROLES["usage_qm"] == {wf.ROLE_MANAGER, wf.ROLE_SYSTEM}
		assert wf.ACTION_ROLES["usage_cancel"] == {wf.ROLE_MANAGER, wf.ROLE_SYSTEM}
		assert wf.ROLE_LIMS_QA in wf.ACTION_ROLES["review_observation"]


class TestRetentionContractR7BC:
	def test_sod_sign(self):
		ok, _ = rtc.check_sod_sign("an@x", None, "qc@x")
		assert ok
		ok, err = rtc.check_sod_sign("an@x", None, "an@x")
		assert not ok and "申请人" in err
		ok, err = rtc.check_sod_sign("an@x", "qc@x", "qc@x")
		assert not ok and "连续两级" in err
		ok, _ = rtc.check_sod_sign("an@x", "qc1@x", "qc2@x")
		assert ok

	def test_release_requires(self):
		assert rtc.release_requires("草稿") is False
		assert rtc.release_requires("待库存确认") is False
		assert rtc.release_requires("待QC批准") is True
		assert rtc.release_requires("已批准") is True

	def test_sample_source_whitelist_raw_material(self):
		# 主数据原料类样品类型为「原材料」，必须放行（P1 修复）
		ok, err = rtc.check_sample_source_mapping("原材料", "检验完成", "供应商A",
												  "CODE", True)
		assert ok, err
		ok, _ = rtc.check_sample_source_mapping("成品", "已放行", "留样", "CODE", True)
		assert ok is False  # 防递归
		ok, _ = rtc.check_sample_source_mapping("稳定性样品", "检验完成", "供应商A", "C", True)
		assert ok is False  # 稳定性硬隔离
		assert rtc.map_sample_type_to_category("原材料") == "关键物料"

	def test_obs_constants(self):
		assert rtc.OBS_ANNUAL_CAP == 3
		assert rtc.OBS_REASON_ANNUAL == "年度观察批（每年 3 批）"
