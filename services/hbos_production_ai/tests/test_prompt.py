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


# ---------------------------------------------------------------------------
# 2026-10-20 改版：要求给出可执行的改进建议
# ---------------------------------------------------------------------------


def test_system_prompt_demands_specific_actions():
    """「建议优化工艺参数」这类废话必须被明令禁止。

    Owner 反馈原输出太单薄 —— 62 条里只有 6 条给了具体动作。
    """
    s = prompt.SYSTEM_PROMPT
    assert "suggestions" in s
    assert "action" in s and "basis" in s
    # 正例与反例都要给 —— 只说「要具体」模型不知道什么叫具体
    assert "合格的建议" in s
    assert "不合格的建议" in s
    assert "建议优化工艺参数" in s       # 反例原文
    # 数据不足时也要给动作（补录），不是甩一句「数据不足」了事
    assert "补录" in s


def test_prompt_includes_stats_block():
    """统计必须在提示词里，且明确告诉模型「不要自己重算」。"""
    st = _stats()
    p = prompt.build_user_prompt("4BMA", _craft(), _ledger(), st)
    assert "参数与收率" in p
    assert "不要自己重算" in p
    assert "水分" in p          # 统计里的字段名要能看到


def test_prompt_without_stats_says_so():
    # 没传统计时要说清楚，不能让模型以为「没有参数影响」= 没有关系
    p = prompt.build_user_prompt("4BMA", _craft(), _ledger())
    assert "本轮未提供统计" in p


def _stats():
    from app import sources as src_mod
    from app import stats as s

    rows = [{"入库收率": str(88 + i * 0.1), "水分": str(0.03 + i * 0.002)} for i in range(50)]
    batches = [src_mod.LedgerBatch(batch=f"B{i}", values=v) for i, v in enumerate(rows)]
    return s.analyze("4BMA", batches)
