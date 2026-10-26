"""参数↔收率统计的单测 —— **纯函数**，不联网。

这套统计是「让 AI 给出可执行建议」的地基：模型不会自己算相关系数，
所以数字必须先算对。这里钉住四件事：

    1. 定义性字段（收率的分子/分母）必须排除 —— 否则 ρ=+1.00 的废话会进报告
    2. 脏值 `/`、`未检出` 不能被当成 0
    3. 样本不足的参数只能报覆盖率，不能参与分析
    4. 收率单位混用要归一（0.50 是 50%，不是 0.5%）
"""

from __future__ import annotations

import pytest

from app import stats
from app.sources import LedgerBatch


def _batches(product_fields: list[dict]) -> list[LedgerBatch]:
    return [LedgerBatch(batch=f"B{i}", values=v) for i, v in enumerate(product_fields)]


# ---------------------------------------------------------------------------
# 相关系数
# ---------------------------------------------------------------------------


def test_spearman_perfect_monotonic():
    assert stats.spearman([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) == pytest.approx(1.0)
    assert stats.spearman([1, 2, 3, 4, 5], [50, 40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_ignores_outliers():
    # 秩相关对离群值不敏感 —— 这正是用它而不用 Pearson 的理由：
    # 台账里批号被当数字、单位混填的情况很常见。
    xs = [1, 2, 3, 4, 5, 999999]
    ys = [1, 2, 3, 4, 5, 6]
    assert stats.spearman(xs, ys) == pytest.approx(1.0)


def test_spearman_returns_none_when_constant():
    # 整列常数的「相关」没有意义
    assert stats.spearman([5, 5, 5, 5], [1, 2, 3, 4]) is None


# ---------------------------------------------------------------------------
# 脏值与定义性字段
# ---------------------------------------------------------------------------


def test_dirty_values_are_not_zero():
    # `/` 是「未检」，不是 0。当成 0 会让相关分析彻底错乱。
    assert stats._num("/") is None
    assert stats._num("未检出") is None
    assert stats._num("") is None
    assert stats._num(None) is None
    assert stats._num("89.33%") == pytest.approx(89.33)
    assert stats._num("12.4℃") == pytest.approx(12.4)


def test_definitional_fields_are_excluded():
    """入库干重是收率的分子 —— 它与收率 ρ≈0.94，但那不是工艺发现。

    不排除的话模型会写「增加干重能提高收率」，这是同义反复。
    """
    rows = []
    for i in range(60):
        dry = 200 + i
        rows.append(
            {
                "入库干重": str(dry),
                "入库收率": str(85 + i * 0.1),      # 与干重同向
                "THF水分": str(0.03 + (i % 3) * 0.01),
            }
        )
    st = stats.analyze("4BMA", _batches(rows))
    names = [e.name for e in st.effects]
    assert "入库干重" not in names, "定义性字段必须被排除"
    assert "入库收率" not in names


def test_non_parameter_fields_excluded():
    rows = [{"批号": f"B{i}", "投料日期": "2026-10-01", "入库收率": "90", "水分": str(i)}
            for i in range(40)]
    st = stats.analyze("4BMA", _batches(rows))
    names = [e.name for e in st.effects]
    assert "批号" not in names
    assert "投料日期" not in names


# ---------------------------------------------------------------------------
# 样本阈值
# ---------------------------------------------------------------------------


def test_sparse_fields_reported_not_analyzed():
    """只有 10 批记录的参数，不能拿去算规律 —— 但要说出来（台账填写不全）。"""
    rows = []
    for i in range(60):
        v = {"入库收率": str(88 + i * 0.05)}
        if i < 10:
            v["偶发参数"] = str(i * 2)
        rows.append(v)
    st = stats.analyze("4BMA", _batches(rows))
    assert "偶发参数" not in [e.name for e in st.effects]
    assert any(name == "偶发参数" for name, _ in st.sparse_fields)
    out = stats.render(st)
    assert "记录太少" in out


def test_no_yield_data_returns_empty_message():
    rows = [{"水分": "0.03"} for _ in range(50)]
    st = stats.analyze("4BMA", _batches(rows))
    assert st.yield_batches == 0
    assert "无收率数据" in stats.render(st)


# ---------------------------------------------------------------------------
# 收率单位归一
# ---------------------------------------------------------------------------


def test_yield_ratio_is_scaled_to_percent():
    """F12/F13 台账里收率存的是比值（1.48 / 0.50），不是百分数。

    不换算的话报告里会出现「收率均值 0.50」—— 会被车间当场指出是错的。
    """
    rows = [{"收率": "0.50", "水分": str(i % 5)} for i in range(40)]
    st = stats.analyze("F13", _batches(rows))
    out = stats.render(st)
    assert "50.00%" in out, out
    assert "已换算为百分数" in out


def test_yield_percent_is_kept_as_is():
    rows = [{"入库收率": "90.0", "水分": str(i % 5)} for i in range(40)]
    st = stats.analyze("4BMA", _batches(rows))
    out = stats.render(st)
    assert "90.00%" in out
    assert "已换算" not in out


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------


def test_render_includes_monthly_trend():
    rows = [
        {"入库收率": "90", "水分": "0.03", "投料日期": "2026-08-15"},
        {"入库收率": "91", "水分": "0.03", "投料日期": "2026-09-15"},
    ] + [
        {"入库收率": "90", "水分": "0.03", "投料日期": f"2026-09-{i:02d}"} for i in range(1, 30)
    ]
    st = stats.analyze("4BMA", _batches(rows))
    out = stats.render(st)
    assert "月度趋势" in out
    assert "2026-09" in out


def test_render_never_invents_conclusions():
    """统计块只给数字和字段名，不给「该提高XX」这类结论 —— 那是模型的活。"""
    rows = [{"入库收率": str(88 + i * 0.1), "水分": str(0.03 + i * 0.001)} for i in range(60)]
    out = stats.render(stats.analyze("4BMA", _batches(rows)))
    for word in ("应该提高", "建议调整", "必须控制"):
        assert word not in out


# ---------------------------------------------------------------------------
# 分类字段（釜号 / 位号 / 厂家）
# ---------------------------------------------------------------------------


def test_low_cardinality_goes_to_category_not_correlation():
    """釜号只有 3 个取值，当连续变量算相关是伪关系（R228 < R262 < R516 无物理意义）。

    改成按取值分组比收率 —— 「R516 那台釜平均低 0.8pt」才是车间能查的事。
    """
    rows = []
    for i in range(90):
        kettle = ["R228", "R262", "R516"][i % 3]
        # R516 的收率明显低
        y = 90.0 if kettle != "R516" else 89.2
        rows.append({"入库收率": str(y), "釜号": kettle, "水分": str(i % 7)})
    st = stats.analyze("4BMA", _batches(rows))
    assert "釜号" not in [e.name for e in st.effects]
    names = [c.name for c in st.categories]
    assert "釜号" in names
    cat = next(c for c in st.categories if c.name == "釜号")
    assert cat.groups[0][2] > cat.groups[-1][2], "高收率的组应排在前面"


def test_person_name_field_is_excluded():
    """按人分组算收率既不可执行，又变成对员工的评价 —— 必须排除。

    实测 F12 的 `浓缩终点判断` 填的就是操作工姓名。
    """
    rows = []
    for i in range(60):
        rows.append(
            {
                "入库收率": str(89 + (i % 3)),
                "浓缩终点判断": ["张伟", "李娜", "王强"][i % 3],
                "水分": str(i % 5),
            }
        )
    st = stats.analyze("4BMA", _batches(rows))
    assert "浓缩终点判断" not in [c.name for c in st.categories]


def test_batch_number_field_is_excluded():
    """批号是标识符，不是参数。「换了批号收率就变」不是工艺结论。"""
    rows = [
        {"入库收率": str(88 + i * 0.1), "混粉用Na2CO3批号": f"3250{8416 + i}"}
        for i in range(60)
    ]
    st = stats.analyze("4BMA", _batches(rows))
    assert "混粉用Na2CO3批号" not in [e.name for e in st.effects]
    assert "混粉用Na2CO3批号" not in [c.name for c in st.categories]


def test_blank_placeholder_not_a_category():
    """`/` 是「没填」，不能当成一个取值 —— 否则报告里出现「`/` 组 88.8%」这种噪音。"""
    rows = []
    for i in range(80):
        rows.append(
            {
                "入库收率": str(88 + (i % 5) * 0.2),
                "规格": "非规" if i % 2 else "/",
                "水分": str(i % 3),
            }
        )
    st = stats.analyze("4BMA", _batches(rows))
    cat = next((c for c in st.categories if c.name == "规格"), None)
    if cat:      # 组数够才会出现
        assert "/" not in [g[0] for g in cat.groups]
