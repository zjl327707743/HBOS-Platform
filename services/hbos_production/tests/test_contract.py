"""口径的纯函数单测。

这些测试**不联网、不碰飞书** —— `contract.py` 是纯函数，正是为了能被这样测。
口径是 Owner 逐条确认过的（2026-10-02），改动必须同步改测试。
"""

from __future__ import annotations

from datetime import date

from app import contract
from app.contract import DetailRecordWithQty


# ---------------------------------------------------------------------------
# 日期解析：飞书各表混用多种写法，实测都要能兜住
# ---------------------------------------------------------------------------

def test_parse_millisecond_timestamp_is_beijing_time():
    # 飞书 datetime 返回**当地午夜**的毫秒时间戳。
    # 1759248000000 = 2025-10-01 00:00 +08:00。
    # 用 UTC 解释会得到 2025-09-30 16:00 → 格式化成**前一天**（每天少一天，
    # 跨月批次会落错月）。这里锁住按北京时间解释。
    assert contract.parse_month_day(1759248000000) == "2025-10-01"


def test_parse_string_variants():
    # 实测这几种写法都出现过（无菌台账里尤其多）
    assert contract.parse_month_day("2026-10-01") == "2026-10-01"
    assert contract.parse_month_day("2026.10.01") == "2026-10-01"
    assert contract.parse_month_day("2026/10/01") == "2026-10-01"


def test_parse_garbage_returns_none_not_guess():
    # 「解析不出来」必须返回 None —— 不猜（既有项目栽在这里过）
    assert contract.parse_month_day("205.10.") is None
    assert contract.parse_month_day("投料日期") is None
    assert contract.parse_month_day(None) is None
    assert contract.parse_month_day("") is None


# ---------------------------------------------------------------------------
# 目标：月度生产计划明细 1–31 日求和（宽表）
# ---------------------------------------------------------------------------

def test_plan_batches_sums_wide_table():
    row = {"1日": 2, "2日": "1", "3日": None, "31日": 3}
    assert contract.plan_batches(row) == 6


def test_plan_batches_tolerates_slash_and_junk():
    row = {"1日": "/", "2日": "", "3日": "abc", "4日": 5}
    assert contract.plan_batches(row) == 5


# ---------------------------------------------------------------------------
# 合并行目标收率：按计划批数加权（Owner 2026-10-02）
# ---------------------------------------------------------------------------

def test_weighted_target_yield_is_weighted_not_simple_average():
    # 美罗培南族实况：B 权重 59 收率 0.90；美罗培南 权重 18 收率 0.88
    # 简单平均 = 0.89；加权 = (59*.90 + 18*.88)/77 = 0.89532...
    got = contract.weighted_target_yield({"B": 59, "M": 18}, {"B": 0.90, "M": 0.88})
    assert got is not None
    assert abs(got - (59 * 0.90 + 18 * 0.88) / 77) < 1e-9
    assert got != 0.89


def test_weighted_target_yield_none_when_no_yield_data():
    # 全无收率数据 → None（不补默认值，交页面显示「—」）
    assert contract.weighted_target_yield({"A": 10}, {}) is None
    # 有权重但收率为 0 → 视为无数据（den 为 0）
    assert contract.weighted_target_yield({"A": 0}, {"A": 0.9}) is None


# ---------------------------------------------------------------------------
# 落月口径：按收料日期（会议 2026-10-02；既有 openclaw 用投料日期，已改）
# ---------------------------------------------------------------------------

def _rec(product, received, rate=None, qty=None):
    return DetailRecordWithQty(
        product=product, batch="X", received_on=received, yield_rate=rate, qty=qty
    )


def test_aggregate_month_uses_receipt_date_not_investment_date():
    recs = [
        _rec("4BMA", "2026-09-30", 0.90),   # 8 月底投料、9 月底收料 → 归 9 月
        _rec("4BMA", "2026-10-01", 0.91),   # 10 月
        _rec("4BMA", None, 0.99),           # 无收料日期 → 不计
    ]
    got = contract.aggregate_month(recs, "2026-09")
    assert got["4BMA"][0] == 1
    assert got["4BMA"][1] == [0.90]
    assert contract.aggregate_month(recs, "2026-10")["4BMA"][0] == 1


def test_aggregate_month_keeps_none_yield_out_of_average():
    # 有批数但收率为空 → 批数要算，平均值不含它（不能当 0）
    recs = [_rec("F9", "2026-10-01", None), _rec("F9", "2026-10-01", 1.10)]
    cnt, rates = contract.aggregate_month(recs, "2026-10")["F9"]
    assert cnt == 2
    assert rates == [1.10]


# ---------------------------------------------------------------------------
# 昨日入库：按收料日期取当天产量求和
# ---------------------------------------------------------------------------

def test_aggregate_day_qty_sums_by_receipt_date():
    recs = [
        _rec("F12", "2026-10-01", qty=800.2),
        _rec("4BMA", "2026-10-01", qty=676.06),
        _rec("F12", "2026-10-01", qty=0.0),      # 0 也是有效值（当批产量 0）
        _rec("F12", "2026-09-30", qty=999.9),    # 不在当天 → 不计
    ]
    got = contract.aggregate_day_qty(recs, "2026-10-01")
    assert got["F12"] == 800.2
    assert got["4BMA"] == 676.06


# ---------------------------------------------------------------------------
# 排除规则（会议 2026-10-02）
# ---------------------------------------------------------------------------

def test_exclusion_by_keyword_and_exact():
    for name in ("F12-欧盟", "美罗培南混粉", "美罗培南混粉USP", "美罗培南晶种"):
        assert contract.is_excluded(name), name
    for name in ("碳酸氢钠", "碳酸钠（EP）", "比阿培南"):
        assert contract.is_excluded(name), name
    for name in ("4BMA", "F9", "美罗培南B", "国内规范粗品"):
        assert not contract.is_excluded(name), name


# ---------------------------------------------------------------------------
# 组装
# ---------------------------------------------------------------------------

def test_build_rows_merges_f13_from_three_members():
    # F13 = 国内规范粗品 + 粗品B + 粗品C（Owner 2026-10-02 口径）
    details = [
        _rec("国内规范粗品", "2026-10-01", 0.50, 100.0),
        _rec("美罗培南粗品B", "2026-10-01", 0.51, 200.0),
    ]
    rows = contract.build_rows(
        month="2026-10",
        yesterday="2026-10-01",
        details=details,
        members_excluded=set(),
        plan_by_product={"国内规范粗品": 29, "美罗培南粗品B": 105, "美罗培南粗品C": 0},
        yield_by_product={"美罗培南粗品B": 0.50},
    )
    f13 = next(r for r in rows if r.label == "F13")
    assert f13.done == 2
    assert f13.target == 134
    assert f13.yesterdayInbound == 300.0


def test_build_rows_excludes_four_workshop_members():
    # 会议：四车间暂不录入。B5/A7/B6/CDCA 都是四车间 ——
    # 它们不在 ROW_MEMBERS 里，天然不进任何行；这里验证「传了排除集也不会串行」
    details = [_rec("4BMA", "2026-10-01", 0.90, 10.0)]
    rows = contract.build_rows(
        month="2026-10", yesterday="2026-10-01", details=details,
        members_excluded={"B5", "A7", "B6", "CDCA"},
        plan_by_product={"4BMA": 87}, yield_by_product={"4BMA": 0.91},
    )
    labels = [r.label for r in rows]
    assert "B5" not in labels and "B6" not in labels
    assert labels == list(contract.ROW_MEMBERS.keys())


def test_build_rows_label_matches_frontend_contract():
    # 前端按 label 对齐行 —— label 必须与 src/data/productionNav.ts 的
    # PRODUCTION_ROWS 逐字一致。这里锁住顺序与字面量。
    assert list(contract.ROW_MEMBERS.keys()) == [
        "4BMA", "F9", "F12", "F13", "无菌美罗培南", "无菌亚胺培南",
    ]


# ---------------------------------------------------------------------------
# 月初基准
# ---------------------------------------------------------------------------

def test_days_elapsed_only_for_current_month():
    assert contract.days_elapsed("2026-10", date(2026, 10, 1)) == 1
    assert contract.days_elapsed("2026-10", date(2026, 11, 3)) == 0


# ---------------------------------------------------------------------------
# 数据指纹（幂等用）
# ---------------------------------------------------------------------------

def test_fingerprint_stable_and_sensitive():
    a = contract.fingerprint("4BMA", "工艺描述v1", "2026-10-01")
    b = contract.fingerprint("4BMA", "工艺描述v1", "2026-10-01")
    c = contract.fingerprint("4BMA", "工艺描述v1", "2026-10-02")
    assert a == b
    assert a != c


# ---------------------------------------------------------------------------
# 异常闭环（会议 2026-10-02 + Owner 2026-10-08 口径）
# ---------------------------------------------------------------------------

def _src(name="二车间", closure="事件原因", content="事件内容"):
    return contract.AnomalySource(
        name=name, base_token="b", table_id="t",
        content_field=content, date_field="发生时间",
        closure_field=closure, closure_label=closure,
    )


def _anom(date="2026-03-01", content="设备异响", closure="轴套磨损", field="事件原因"):
    """造一条**平铺**的异常记录（与飞书 API 的 item 同形）。"""
    r = {"事件内容": content, "发生时间": f"{date}T00:00:00.000+08:00"}
    r[field] = closure
    return r


def test_window_start_is_12_natural_months_inclusive():
    # 近 12 个自然月含当月：2026-10 → 2025-11-01
    from datetime import date as _d
    assert contract.anomaly_window_start(_d(2026, 10, 8)) == "2025-11-01"
    assert contract.anomaly_window_start(_d(2026, 1, 15)) == "2025-02-01"


def test_empty_placeholder_row_is_not_counted():
    # 飞书表里有全空占位行（实测六车间 10 行全空）—— 不进分母
    st = contract.anomaly_stats(_src(), [{}, {"事件内容": ""}], "2025-11-01")
    assert st.total == 0
    assert st.rate is None           # 「没有异常」≠「0% 闭环」


def test_closed_means_closure_field_non_empty():
    recs = [_anom(closure="轴套磨损"), _anom(closure=""), _anom(closure="   ")]
    st = contract.anomaly_stats(_src(), recs, "2025-11-01")
    assert st.total == 3
    # 只有空格的也算「没填」（有人敲了个空格就保存）
    assert st.closed == 1


def test_window_excludes_older_records():
    recs = [_anom(date="2025-10-31"), _anom(date="2025-11-01"), _anom(date="2026-03-01")]
    st = contract.anomaly_stats(_src(), recs, "2025-11-01")
    assert st.total == 2             # 2025-10-31 那条在窗口外


def test_datetime_may_be_millisecond_timestamp():
    # 飞书 API 直接返回时 datetime 是**毫秒时间戳**；lark-cli 看到的是 ISO 字符串。
    # 只按字符串处理会把 1759248000000 截成 "1759248000"，跟 "2025-11-01"
    # 一比就判成窗口外 —— 整个车间静默变 0 条（踩过）。
    r = {"事件内容": "x", "发生时间": 1759248000000}   # 2025-10-01 00:00 +08:00
    assert contract.resolve_anomaly_date(r, _src()) == "2025-10-01"


def test_date_falls_back_to_text_then_survey_date():
    # 无菌车间 32 条里只有 10 条填了「发生时间」，另 22 条的日期写在内容开头
    # 注：无菌那张表的内容列叫「异常事件内容」，不是「事件内容」——
    #     源配置的 content_field 必须对，否则连内容都读不到（这一条踩过）
    sterile = _src(name="无菌车间", closure="CAPA完成时间", content="异常事件内容")
    r = {"异常事件内容": "2026.03.13 12:23 电子秤校秤失败", "事件原因": "信号线接触不良"}
    assert contract.resolve_anomaly_date(r, sterile) == "2026-03-13"

    r2 = {"异常事件内容": "设备异响", "调查完成时间": "2026-04-01T00:00:00.000+08:00"}
    assert contract.resolve_anomaly_date(r2, _src()) == "2026-04-01"

    r3 = {"异常事件内容": "设备异响"}
    assert contract.resolve_anomaly_date(r3, _src()) is None


def test_undated_records_are_reported_not_silently_dropped():
    # 解析不出日期的记 `undated`，如实报出 —— 静默丢弃会让比率失真且看不出
    recs = [_anom(), {"事件内容": "无日期的异常", "事件原因": "x"}]
    st = contract.anomaly_stats(_src(), recs, "2025-11-01")
    assert st.total == 1
    assert st.undated == 1


def test_closure_field_is_uniform_across_workshops():
    # Owner 2026-10-08：**全车间统一用「事件原因」**。
    # 无菌那张表虽有 CAPA 字段，但各车间判据不同会让合计数失去意义。
    labels = {s.closure_field for s in contract.ANOMALY_SOURCES}
    assert labels == {"事件原因"}, labels


def test_overall_closure_is_aggregate_not_average_of_rates():
    # 二车间 9/31（29%）+ 三车间 8/9（89%）：
    # 平均 = 59%，合计 = 17/40 = 42.5% —— 看板用**合计**
    a = contract.AnomalyStats("二车间", "事件原因", 31, 9)
    b = contract.AnomalyStats("三车间", "事件原因", 9, 8)
    got = contract.overall_closure([a, b], "2025-11-01", 12)
    assert got["total"] == 40 and got["closed"] == 17
    assert abs(got["rate"] - 17 / 40) < 1e-9
    assert len(got["byWorkshop"]) == 2


def test_overall_closure_rate_none_when_no_records_anywhere():
    got = contract.overall_closure(
        [contract.AnomalyStats("六车间", "事件原因", 0, 0)], "2025-11-01", 12
    )
    assert got["total"] == 0
    assert got["rate"] is None
    assert got["activeWorkshops"] == []      # 表在但窗口内无异常
