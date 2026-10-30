"""质量合格率口径（2026-10-19 产品质量数据专题会）。

规则（会议原话，逐字落实）：

    从「同步 QC 数据-产品」取数，按 `生产日期` 列取当月的行。
    已登记的批次**就是合格**（不合格批次根本不录入）。缺值分两种：

        1001~1005、1007~1010 有值，1006 没有 → 1006 **不合格**
        1001~1002 有值，1003~1010 没有       → 后 8 批**还没检测**

    即：最后一个已检批次之后的空 = 未检测（不进分母）；
        两个已检批次之间的空 = 不合格。

本文件的用例**全部取自真实表结构**（字段名、批号格式、日期形态），
改口径时先看这里，别只看函数注释。
"""

import pytest

from app import contract


def _src(**kw):
    base = dict(
        label="测试",
        table_id="t",
        conclusion_field=None,
        test_fields=("性状",),
    )
    base.update(kw)
    return contract.QcSource(**base)


def _row(batch, filled=True, day="2026-10-05", field="性状"):
    r = {"批号": batch, "生产日期": day}
    if filled:
        r[field] = "本品为白色粉末"
    return r


# --- 会议里那两个例子的正例 ------------------------------------------------


def test_tail_gap_is_untested_not_failed():
    # 会议原话：1001~1002 有值，1003~1010 没有 = 后 8 批还没检测
    recs = [_row("B261001"), _row("B261002")] + [
        _row(f"B26{i:04d}", filled=False) for i in range(1003, 1011)
    ]
    st = contract.quality_stats(_src(), recs, "2026-10")
    assert st.tested == 2
    assert st.failed == 0
    assert st.untested == 8
    assert st.rate == 1.0          # 已检的全部合格 —— 但不是「全批全检」


def test_interior_gap_is_failed():
    # 会议原话：1001~1005、1007~1010 有值，1006 没有 = 1006 不合格
    nums = [1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010]
    recs = [_row(f"B26{n:04d}") for n in nums]
    recs.append(_row("B261006", filled=False))
    st = contract.quality_stats(_src(), recs, "2026-10")
    assert st.tested == 9
    assert st.failed == 1
    assert st.untested == 0
    assert st.failed_batches == ["B261006"]
    assert st.rate == pytest.approx(9 / 10)


def test_no_tested_rows_means_rate_is_none_not_100():
    # 整段都没登记 ≠ 100% 合格，而是「本月没数据」
    recs = [_row(f"B26{i:04d}", filled=False) for i in range(1001, 1006)]
    st = contract.quality_stats(_src(), recs, "2026-10")
    assert st.tested == 0
    assert st.failed == 0
    assert st.untested == 5
    assert st.rate is None          # 不是 1.0


# --- 批号分段：不同段各自判档，不能混在一起 --------------------------------


def test_segments_are_evaluated_independently():
    # F12 有 F 线 / G 线，批号前缀不同，各自判档。
    # F 线 1002 夹在 1001 和 1003 之间 → 不合格；
    # G 线的 1004 在 G 线最后一批之后 → 只是未检测，不能算不合格。
    recs = [
        _row("F12-F261001"),
        _row("F12-F261002", filled=False),
        _row("F12-F261003"),
        _row("F12-G261001"), _row("F12-G261002"), _row("F12-G261003"),
        _row("F12-G261004", filled=False),
    ]
    st = contract.quality_stats(_src(), recs, "2026-10")
    assert st.tested == 5
    assert st.failed == 1
    assert st.untested == 1
    assert st.failed_batches == ["F12-F261002"]


def test_prefix_with_hyphen_is_kept_whole():
    # `4B-B261005` 的前缀必须是 `4B-B`；把 `4B-B` 和 `4B-B2...` 拆错会串档
    assert contract._batch_key("4B-B261005") == ("4B-B", 261005)
    assert contract._batch_key("F13-A260985") == ("F13-A", 260985)
    assert contract._batch_key("无批号") is None


# --- 只统计当月的行（按生产日期） ------------------------------------------


def test_only_current_month_rows_count():
    recs = [
        _row("B260901", day="2026-09-30"),     # 上个月，整条跳过
        _row("B261001", day="2026-10-01"),
        _row("B261002", day="2026-10-02", filled=False),
    ]
    st = contract.quality_stats(_src(), recs, "2026-10")
    assert st.tested == 1
    assert st.failed == 0
    assert st.untested == 1


def test_production_date_accepts_timestamp_and_string():
    # 飞书 API 给毫秒时间戳，lark-cli 给 ISO 串 —— 两种都要认（同类坑踩过两次）
    ts = 1791043200000      # 2026-10-04 00:00 +08:00
    recs = [
        {"批号": "B261001", "生产日期": ts, "性状": "x"},
        {"批号": "B261002", "生产日期": "2026-10-05T00:00:00.000+08:00", "性状": "x"},
    ]
    st = contract.quality_stats(_src(), recs, "2026-10")
    assert st.tested == 2


# --- 结论列 vs 检测值列 ----------------------------------------------------


def test_conclusion_field_used_when_present():
    # F13（B）有「检验结论」：登记即合格，为空就是没有
    src = _src(conclusion_field="检验结论", test_fields=())
    recs = [
        {"批号": "F13-A261001", "生产日期": "2026-10-01", "检验结论": "合格"},
        {"批号": "F13-A261002", "生产日期": "2026-10-01", "检验结论": None},
    ]
    st = contract.quality_stats(src, recs, "2026-10")
    assert st.tested == 1
    assert st.untested == 1


def test_test_fields_used_when_no_conclusion_column():
    # 4BMA / F9 / F12 没有结论列 —— 任一检测值非空即视为已登记
    src = _src(conclusion_field=None, test_fields=("性状", "水分"))
    recs = [
        {"批号": "B261001", "生产日期": "2026-10-01", "性状": "白色"},
        {"批号": "B261002", "生产日期": "2026-10-01", "水分": "0.03"},
        {"批号": "B261003", "生产日期": "2026-10-01"},
    ]
    st = contract.quality_stats(src, recs, "2026-10")
    assert st.tested == 2
    assert st.untested == 1


# --- 汇总 ------------------------------------------------------------------


def test_overall_quality_sums_before_dividing():
    # 合计后再算率，不是各产品率的平均（与异常闭环同一条原则）
    a = contract.QualityStats("A", tested=9, failed=1, untested=0, failed_batches=[])
    b = contract.QualityStats("B", tested=1, failed=0, untested=0, failed_batches=[])
    out = contract.overall_quality([a, b], "2026-10")
    assert out["tested"] == 10
    assert out["failed"] == 1
    assert out["rate"] == pytest.approx(10 / 11)   # 不是 (0.9 + 1.0) / 2


def test_overall_quality_with_no_data_is_none():
    out = contract.overall_quality([], "2026-10")
    assert out["rate"] is None
    assert out["coveredLabels"] == []


def test_qc_sources_cover_only_rows_that_have_tables():
    # 无菌两行在 QC Base 里没有对应表，不能凭空造一个源
    labels = {s.label for s in contract.QC_SOURCES}
    assert labels <= set(contract.ROW_MEMBERS)
    assert "无菌美罗培南" not in labels
    assert "无菌亚胺培南" not in labels


# --- 数据源部分失败 ----------------------------------------------------------


def test_quality_reports_failed_label_count(monkeypatch):
    """部分 QC 表取不到时，结果里要能看出「有几张挂了 / 一共几张」。

    前端据此标「部分口径」；只给 failedLabels 而不给总数，前端无法判断
    是「挂了 1 张」还是「全挂了」。
    """
    from app import main as main_mod

    def fake_list(base, table_id, page_size=500):
        if table_id == main_mod.contract.QC_SOURCES[0].table_id:
            return []
        raise main_mod.feishu.FeishuError(1254607, "not ready")

    monkeypatch.setattr(main_mod.feishu, "list_records", fake_list)
    result = main_mod._load_quality("2026-10")

    assert len(result["failedLabels"]) == len(main_mod.contract.QC_SOURCES) - 1
    assert result["sourceCount"] == len(main_mod.contract.QC_SOURCES)


def test_conversion_error_counts_as_source_failure(monkeypatch):
    """单源数据格式异常（ValueError/TypeError）要算该源失败，不能整块 500。

    早先只兜 `FeishuError`；上游字段形状一变，`to_anomaly_record` 抛
    `TypeError` 就把整个 `/production/monthly` 打成 500 —— 其余车间/产品的
    数据一起没了，而且看不出是哪张表的问题。
    """
    from app import main as main_mod

    def fake_list(base, table_id, page_size=500):
        return [{"record_id": "r1", "fields": {"生产日期": "坏数据"}}]

    def boom(src, rows, month):
        raise TypeError("字段形状变了")

    monkeypatch.setattr(main_mod.feishu, "list_records", fake_list)
    monkeypatch.setattr(main_mod.contract, "quality_stats", boom)
    result = main_mod._load_quality("2026-10")

    assert len(result["failedLabels"]) == len(main_mod.contract.QC_SOURCES)
    assert result["rate"] is None


def test_anomaly_conversion_error_counts_as_source_failure(monkeypatch):
    from datetime import date as _date

    from app import main as main_mod

    def fake_list(*spec):
        return [{"record_id": "r1", "fields": {}}]

    def boom(src, rows, start, end):
        raise ValueError("日期解析炸了")

    monkeypatch.setattr(main_mod.feishu, "list_records", fake_list)
    monkeypatch.setattr(main_mod.contract, "anomaly_stats", boom)
    result = main_mod._load_anomalies(_date(2026, 10, 20))

    assert len(result["failedWorkshops"]) == len(main_mod.contract.ANOMALY_SOURCES)
