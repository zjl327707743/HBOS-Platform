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
    report = validate_fields(
        {
            "product_name": "虚构产品A",
            "item_code": "13000215",
            "batch_no": "B2609503",
            "manufacturing_date": "2028-09-01",
            "expiry_date": "2026-09-01",
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
