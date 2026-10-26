"""数据指纹的单测 —— 幂等的边界。

指纹决定「这一轮要不要重新调模型」。它必须满足两条**相反**的要求：

    源数据没变       → 指纹相同 → 跳过（省钱、省时间，一次调用 300+ 秒）
    分析规格变了     → 指纹**必须**不同 → 否则结果表里永远留着旧格式的报告

第二条是踩出来的：2026-10-26 改了提示词和报告结构，但指纹只看源数据，
那几个产品当天台账没变，全部 skipped，62 行里 55 行仍是旧格式。
"""

from __future__ import annotations

from app import main, prompt
from app.sources import CraftDescription, LedgerBatch


def _craft() -> CraftDescription:
    return CraftDescription(
        product="4BMA",
        processes=["锌粉活化"],
        craft={"锌粉活化": "加入 150kg 锌粉"},
        standard={"锌粉活化": "64~68℃"},
        equipment={},
    )


def _ledger() -> list[LedgerBatch]:
    return [LedgerBatch(batch="E2603101", values={"实际反应控温℃": "54.0"})]


def test_same_input_same_fingerprint():
    a = main._fingerprint("4BMA", _craft(), _ledger())
    b = main._fingerprint("4BMA", _craft(), _ledger())
    assert a == b


def test_different_product_different_fingerprint():
    a = main._fingerprint("4BMA", _craft(), _ledger())
    b = main._fingerprint("F9", _craft(), _ledger())
    assert a != b


def test_changed_ledger_changes_fingerprint():
    a = main._fingerprint("4BMA", _craft(), _ledger())
    ledger = _ledger()
    ledger[0].values["实际反应控温℃"] = "55.0"
    b = main._fingerprint("4BMA", _craft(), ledger)
    assert a != b


def test_changed_craft_changes_fingerprint():
    a = main._fingerprint("4BMA", _craft(), _ledger())
    craft = _craft()
    craft.standard["锌粉活化"] = "65~70℃"
    b = main._fingerprint("4BMA", craft, _ledger())
    assert a != b


def test_prompt_version_is_part_of_fingerprint(monkeypatch):
    """改提示词/报告结构必须重跑 —— 否则结果表永远留着旧格式。

    这条是整个幂等逻辑里最容易漏的一环：源数据没变看着「没必要重跑」，
    但产出的内容格式变了，不重跑就永远看不到新格式。
    """
    base = main._fingerprint("4BMA", _craft(), _ledger())
    monkeypatch.setattr(prompt, "PROMPT_VERSION", "999-test")
    bumped = main._fingerprint("4BMA", _craft(), _ledger())
    assert base != bumped
