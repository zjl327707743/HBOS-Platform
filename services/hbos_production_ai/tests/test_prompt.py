"""提示词构造的单测 —— 纯函数，不联网。

重点验证一条：**缺数据的工序必须被明确标注**，不能留给模型去补。
提示词里那句「台账无相关数据」是给模型的显式信号 —— 缺了它，
模型会用行业经验编一个看起来合理的值出来。
"""

from __future__ import annotations

from app import prompt
from app.sources import CraftDescription, LedgerBatch


def _craft():
    return CraftDescription(
        product="4BMA",
        processes=["锌粉活化", "7eβ合成"],
        craft={"锌粉活化": "加入150kg 800目锌粉活化1小时"},
        standard={"锌粉活化": "64~68℃", "7eβ合成": "M3含量≤3.0%"},
        equipment={},   # 刻意留空 → 应出现「无相关数据」
    )


def _ledger():
    return [
        LedgerBatch(batch="E2603101", values={"实际反应控温℃": "54.0-55.8"}),
        LedgerBatch(batch="E2603102", values={"反应时长min": "83"}),
    ]


def test_prompt_lists_all_processes_and_demands_one_each():
    p = prompt.build_user_prompt("4BMA", _craft(), _ledger())
    assert "锌粉活化" in p and "7eβ合成" in p
    assert "每一道工序都出一条" in p


def test_prompt_marks_missing_data_explicitly():
    # 设备描述为空 → 必须出现「台账无相关数据」，否则模型会编
    p = prompt.build_user_prompt("4BMA", _craft(), _ledger())
    assert "（台账无相关数据）" in p


def test_prompt_includes_ledger_values_verbatim():
    p = prompt.build_user_prompt("4BMA", _craft(), _ledger())
    assert "54.0-55.8" in p          # 原始区间文本原样给模型，不预解析
    assert "E2603101" in p


def test_prompt_handles_empty_ledger_without_crashing():
    p = prompt.build_user_prompt("4BMA", _craft(), [])
    assert "（台账无相关数据）" in p


def test_system_prompt_states_the_hard_rules():
    s = prompt.SYSTEM_PROMPT
    # 三条铁律必须在提示词里（不做人工确认，全靠这段约束模型）
    assert "没有依据的话不说" in s
    assert "不要推测" in s
    assert "数据不足就如实标" in s
    # 评级枚举要在
    for g in prompt.GRADES:
        assert g in s
