"""约束校验层单元测试。

只用虚构数据，不依赖任何真实标签、不启动服务、不联网。

运行：
    cd services/hbos_ocr && python3 -m pytest tests/ -v
或（无 pytest 时）：
    cd services/hbos_ocr && python3 tests/test_validate.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.validate import (  # noqa: E402
    normalize_item_code,
    check_batch_no,
    parse_date,
    validate_fields,
)


# --- 物料代码：形近字母纠错（本层最核心的价值） -----------------------------

def test_item_code_clean():
    code, hints = normalize_item_code("13000215")
    assert code == "13000215"
    assert hints == []


def test_item_code_letter_o_to_zero():
    code, hints = normalize_item_code("1300O215")
    assert code == "13000215"
    assert hints and "形近" in hints[0]


def test_item_code_lowercase_l_to_one():
    code, _ = normalize_item_code("130002l5")
    assert code == "13000215"


def test_item_code_multiple_confusables():
    code, _ = normalize_item_code("l3OOO2l5")
    assert code == "13000215"


def test_item_code_with_separators():
    code, _ = normalize_item_code("1300-0215")
    assert code == "13000215"


def test_item_code_wrong_length_kept_but_flagged():
    code, hints = normalize_item_code("1300021")  # 7 位
    assert code == "1300021"
    assert any("长度" in h for h in hints)


def test_item_code_with_letters_that_are_not_confusable():
    code, hints = normalize_item_code("130002K5")
    assert code is None
    assert any("非数字" in h for h in hints)


def test_item_code_empty():
    code, hints = normalize_item_code("")
    assert code is None
    assert hints


# --- 批号 -------------------------------------------------------------------

def test_batch_normal():
    batch, hints = check_batch_no("B2609503")
    assert batch == "B2609503"
    assert hints == []


def test_batch_mixture_prefix():
    batch, hints = check_batch_no("BMT2607701")
    assert batch == "BMT2607701"
    assert hints == []


def test_batch_sub_batch():
    batch, hints = check_batch_no("B2609503-1")
    assert batch == "B2609503-1"
    assert any("亚批" in h for h in hints)


def test_batch_supplier_receipt_10_digits():
    batch, hints = check_batch_no("0010010542", source_type="外购")
    assert batch == "0010010542"
    assert hints == []


def test_batch_no_yearmonth_flagged():
    _, hints = check_batch_no("ABC")
    assert any("年月" in h for h in hints)
    assert any("3 位流水号" in h for h in hints)


def test_batch_spaces_removed():
    batch, hints = check_batch_no(" B2609503 ")
    assert batch == "B2609503"
    assert any("空白" in h for h in hints)


def test_batch_empty():
    batch, hints = check_batch_no(None)
    assert batch is None
    assert hints


# --- 日期 -------------------------------------------------------------------

def test_date_iso():
    d, _ = parse_date("2026-09-14")
    assert d == "2026-09-14"


def test_date_dotted():
    d, _ = parse_date("2026.09.14")
    assert d == "2026-09-14"


def test_date_compact():
    d, _ = parse_date("20260914")
    assert d == "2026-09-14"


def test_date_chinese():
    d, _ = parse_date("2026年09月14日")
    assert d == "2026-09-14"


def test_date_two_digit_year():
    d, _ = parse_date("26.09.14")
    assert d == "2026-09-14"


def test_date_empty_is_silent():
    """生产日期 / 有效期本就可缺，不该产生提示。"""
    d, hints = parse_date("")
    assert d is None
    assert hints == []


def test_date_invalid_flagged():
    d, hints = parse_date("不详")
    assert d is None
    assert hints


# --- 只到月的日期（真实标签约占三分之二） ---------------------------------
#
# 实测 50 张真实标签，多数有效期只印到月（「2028年11月」），日根本没印。
# 这是印刷惯例，不是识别错误；不补日的话 ERPNext 的 Date 字段存不下。


def test_date_chinese_month_only():
    """只到月 → 补成当月最后一天，并明确提示日不是标签印的。"""
    d, hints = parse_date("2028年11月")
    assert d == "2028-11-30"
    assert any("只读到了年月" in h for h in hints)


def test_date_dotted_month_only():
    d, hints = parse_date("2028.11")
    assert d == "2028-11-30"
    assert any("只读到了年月" in h for h in hints)


def test_date_month_only_february_leap():
    """闰年 2 月要补到 29 日。"""
    d, _ = parse_date("2028年2月")
    assert d == "2028-02-29"


def test_date_month_only_non_leap():
    d, _ = parse_date("2027年2月")
    assert d == "2027-02-28"


def test_date_month_only_december():
    """跨年边界：12 月末是 31 日。"""
    d, _ = parse_date("2028年12月")
    assert d == "2028-12-31"


def test_date_full_not_treated_as_month_only():
    """印了日的，不能落到「只到月」分支——这是回归防线。"""
    d, hints = parse_date("2028年11月30日")
    assert d == "2028-11-30"
    assert not any("只读到了年月" in h for h in hints)


def test_date_month_only_bad_month_flagged():
    """月份越界不能被补成合法日期。"""
    d, hints = parse_date("2028年13月")
    assert d is None
    assert hints


# --- 日期溯源校验 -----------------------------------------------------------
#
# 不变量：**识别出的日期，其数字必须真的出现在识别原文里。**
#
# ⚠ 如实记录：这道校验在 50 张真实标签上**一处都没拦到**——这批数据的日期错误
# 是"漏读"（模型只读到年月，本层按月末补日）和"取错"（挑了标签上另一个日期），
# 两种都能在原文里找到数字，拦不住。
#
# 留着它是为 **C1（本地量化 VLM）** 准备的：VLM 的典型失效模式正是
# 凭空生成一个格式合法、原文里却没有的日期。那时这道校验才真正生效。
#
# 下面这些用例验证的是**校验逻辑本身正确**，不代表它在当前数据上有拦截效果。


def test_date_grounded_ok():
    d, hints = parse_date("2025-06-25", raw_text="生产日期：\n2025年06月25日")
    assert d == "2025-06-25"
    assert not any("不可信" in h for h in hints)


def test_date_made_up_day_is_cleared():
    """原文里只有 7 日，却报出 30 日 → 无中生有，必须清空。"""
    d, hints = parse_date("2026-09-30", raw_text="生产日期：\n2026年09月07日")
    assert d is None
    assert any("不可信" in h for h in hints)


def test_date_made_up_month_end_not_excused():
    """回归防线：``2026-09-30`` 恰好是 9 月末。

    早期实现按"是不是月末"去猜月粒度，于是把它误当成"月末推定"放过了。
    现在由调用点明确告知粒度，不再靠猜——否则任何月末的编造日期都会漏过。
    """
    d, _ = parse_date("2026-09-30", raw_text="2026年09月07日")
    assert d is None


def test_date_wrong_year_is_cleared():
    """报出的年月在原文里找不到（原文是 2025 年 6 月）→ 清空。"""
    d, _ = parse_date("2020-11-07", raw_text="生产日期：\n2025年06月25日")
    assert d is None


def test_date_month_only_passes_grounding():
    """模型只读到年月时，日是我们按月末推定的，日本就不在原文里——不能因此判为编造。"""
    d, hints = parse_date("2028年11月", raw_text="复检期/有效期至：\n2028年11月")
    assert d == "2028-11-30"
    assert any("只读到了年月" in h for h in hints)
    assert not any("不可信" in h for h in hints)


def test_date_month_only_dotted_passes_grounding():
    d, hints = parse_date("2028.11", raw_text="复检期/有效期至：\n2028.11")
    assert d == "2028-11-30"
    assert not any("不可信" in h for h in hints)


def test_date_month_only_wrong_month_cleared():
    """只到月但月份对不上原文 → 仍要清空。"""
    d, _ = parse_date("2028年12月", raw_text="有效期至：\n2028年11月")
    assert d is None


def test_date_grounding_skipped_without_raw_text():
    """不传原文时不做溯源校验（保持向后兼容，也让纯文本单测能跑）。"""
    d, _ = parse_date("2026-09-30")
    assert d == "2026-09-30"


def test_date_grounded_one_digit_month_day():
    """原文里月/日写成 1 位也要能对上。"""
    d, _ = parse_date("2026-01-05", raw_text="2026年1月5日")
    assert d == "2026-01-05"


# --- 汇总 -------------------------------------------------------------------

def test_validate_fields_clean():
    report = validate_fields(
        {
            "product_name": "虚构产品A",
            "item_code": "13000215",
            "batch_no": "B2609503",
            "manufacturing_date": "2026-09-01",
            "expiry_date": "2028-09-01",
        }
    )
    assert report.item_code.value == "13000215"
    assert report.batch_no.value == "B2609503"
    assert not report.needs_review(), report.hints()


def test_validate_fields_corrects_confusable_letters():
    """整链路：OCR 把 O 认成 0 的反向错误，应被纠正。"""
    report = validate_fields(
        {
            "product_name": "虚构产品A",
            "item_code": "13OOO215",
            "batch_no": "B2609503",
            "manufacturing_date": "2026-09-01",
            "expiry_date": "2028-09-01",
        }
    )
    assert report.item_code.value == "13000215"
    assert report.item_code.corrected


def test_validate_fields_expiry_before_manufacture():
    # 批号 B2609503 指示 2026 年 09 月，与下面的生产日期同年月；
    # 这样「批号纠正生产日期」那条规则不会插进来，测的就是有效期早于生产日期本身。
    report = validate_fields(
        {
            "product_name": "虚构产品A",
            "item_code": "13000215",
            "batch_no": "B2609503",
            "manufacturing_date": "2026-09-01",
            "expiry_date": "2024-09-01",
        }
    )
    assert any("早于生产日期" in h for h in report.expiry_date.hints)


def test_validate_fields_numeric_batch_warns():
    report = validate_fields(
        {
            "product_name": "虚构产品A",
            "item_code": "13000215",
            "batch_no": "13000215",  # 与代码相同 → 取错字段
            "manufacturing_date": "2026-09-01",
            "expiry_date": "2028-09-01",
        }
    )
    assert any("混淆" in h for h in report.batch_no.hints)


# --- 手写运行（无 pytest 时） ----------------------------------------------

if __name__ == "__main__":
    import traceback

    tests = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
            passed += 1
        except Exception:
            print(f"FAIL  {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {len(tests)} total")
    sys.exit(1 if failed else 0)


# ---------------------------------------------------------------------------
# 批号定年月：纠正生产日期的年与月
# ---------------------------------------------------------------------------


def test_batch_year_month_parses_three_batch_shapes():
    from app.validate import batch_year_month

    assert batch_year_month("B2506402") == (2025, 6)
    assert batch_year_month("BMT2609119") == (2026, 9)
    assert batch_year_month("BMT2603104") == (2026, 3)
    # 月份非法（13 月）判为不可用，不硬纠
    assert batch_year_month("B2613402") is None
    # 不以字母开头 → 不是这条结构，不纠
    assert batch_year_month("2609101") is None
    assert batch_year_month(None) is None


def test_align_manufacturing_date_fixes_wrong_year():
    from app.validate import align_manufacturing_date

    # 实测错误：2026 被读成 2016
    out, hints = align_manufacturing_date("2016-03-02", "BMT2603104")
    assert out == "2026-03-02"
    assert any("批号" in h for h in hints)


def test_align_manufacturing_date_leaves_correct_date_alone():
    from app.validate import align_manufacturing_date

    out, hints = align_manufacturing_date("2026-09-07", "BMT2609119")
    assert out == "2026-09-07"
    assert hints == []


def test_align_manufacturing_date_keeps_day():
    """批号里没有「日」，纠正时必须保住原来读到的日。"""
    from app.validate import align_manufacturing_date

    out, _ = align_manufacturing_date("2020-03-28", "BMT2603104")
    assert out == "2026-03-28"


def test_align_manufacturing_date_clamps_impossible_day():
    """2 月 30 日这种，纠正后不能造出非法日期。"""
    from app.validate import align_manufacturing_date

    out, _ = align_manufacturing_date("2026-01-30", "B2602402")
    assert out == "2026-02-28"


def test_validate_fields_aligns_mfg_by_batch():
    report = validate_fields(
        {
            "product_name": "虚构产品A",
            "item_code": "13000215",
            "batch_no": "BMT2603104",
            "manufacturing_date": "2016-03-02",
            "expiry_date": "2028-03-01",
        }
    )
    assert report.manufacturing_date.value == "2026-03-02"
    assert any("批号" in h for h in report.manufacturing_date.hints)
