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


def test_stats_batches_are_part_of_fingerprint():
    """提示词里的统计来自 400 批，指纹必须覆盖它 —— 否则改了历史数据不重跑。

    踩过（2026-10-27）：`_fingerprint` 只看 `ledger`（最近 30 批）。
    第 31~400 批被补录/修正后，提示词里的统计变了，但指纹不变 →
    写回层直接 skipped，用户以为自己的修改没被采纳。
    """
    from app.sources import stats_fingerprint_parts

    ledger = _ledger()
    base = main._fingerprint("4BMA", _craft(), ledger)

    stat_ledger = [LedgerBatch(batch="E250101", values={"实际反应控温℃": "50.0"})]
    parts_a = stats_fingerprint_parts(stat_ledger, "统计块 A")
    a = main._fingerprint("4BMA", _craft(), ledger, stats_parts=parts_a)

    stat_ledger_b = [LedgerBatch(batch="E250101", values={"实际反应控温℃": "52.0"})]
    parts_b = stats_fingerprint_parts(stat_ledger_b, "统计块 A")
    b = main._fingerprint("4BMA", _craft(), ledger, stats_parts=parts_b)

    assert a != base, "统计输入参与指纹后，指纹必须与只看 30 批时不同"
    assert a != b, "第 31~400 批的历史值变化必须触发重跑"


def test_stats_render_change_changes_fingerprint():
    """渲染口径变了（指标/舍入/新增维度）也要重跑 —— 提示词逐字用了它。"""
    from app.sources import stats_fingerprint_parts

    stat_ledger = _ledger()
    a = main._fingerprint(
        "4BMA", _craft(), _ledger(),
        stats_parts=stats_fingerprint_parts(stat_ledger, "样本：10 批"),
    )
    b = main._fingerprint(
        "4BMA", _craft(), _ledger(),
        stats_parts=stats_fingerprint_parts(stat_ledger, "样本：12 批"),
    )
    assert a != b


def test_model_change_forces_reanalysis(monkeypatch):
    """换模型必须重跑 —— 否则新模型实际上从没跑过，看板还是旧结论。

    踩过（复审 2026-10-27）：指纹只看源数据 + 提示词版本。切模型后探活成功、
    整轮显示 ok，但每行指纹相同被 skipped，结果表一动不动。
    """
    from app import config

    base = main._fingerprint("4BMA", _craft(), _ledger())
    monkeypatch.setattr(config, "AI_MODEL", "another-model")
    assert main._fingerprint("4BMA", _craft(), _ledger()) != base


def test_temperature_change_forces_reanalysis(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "AI_TEMPERATURE", None)
    base = main._fingerprint("4BMA", _craft(), _ledger())
    monkeypatch.setattr(config, "AI_TEMPERATURE", 0.7)
    assert main._fingerprint("4BMA", _craft(), _ledger()) != base


def test_endpoint_change_forces_reanalysis(monkeypatch):
    from app import config

    base = main._fingerprint("4BMA", _craft(), _ledger())
    monkeypatch.setattr(config, "AI_BASE_URL", "https://other.example/v1")
    assert main._fingerprint("4BMA", _craft(), _ledger()) != base
