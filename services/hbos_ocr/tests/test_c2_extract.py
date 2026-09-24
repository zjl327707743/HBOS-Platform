"""C2 抽取规则的单测。

**全部用虚构数据。** 规则本身是从真实标签的*版式*里总结的，但版式不是业务数据——
测试里出现的代码/批号/品名都是编的，只有"形状"和真实标签一样：

    物料代码  8 位纯数字、首位 1
    批号      字母前缀 + 7 位左右数字
    品名      跟在「品名：」/「名：」后面，或者是重复出现的中文串
    日期      年-月(-日)，可能只到月

真实样本在仓库外（``~/Documents/M3R6样本``），不进版本库。

无 pytest 时可直接运行：``python tests/test_c2_extract.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backends.c2_ocr import (  # noqa: E402
    PaddleOCRBackend,
    extract_batch_no,
    extract_dates,
    extract_item_code,
    extract_product_name,
)


# --- 物料代码 ---------------------------------------------------------------


def test_item_code_basic():
    assert extract_item_code(["物料代码：", "13000215"]) == "13000215"


def test_item_code_confusable_letters_mapped():
    """OCR 把数字认成形近字母，规则层要先还原才可能匹配。"""
    assert extract_item_code(["13OOO215"]) == "13000215"
    assert extract_item_code(["l3OOO2l5"]) == "13000215"


def test_item_code_majority_wins():
    """同一个值通常印 2~3 遍，取出现最多的。"""
    lines = ["13000215", "13000215", "99999999"]
    assert extract_item_code(lines) == "13000215"


def test_item_code_ignores_batch():
    """批号 B2609503 映射后会变成 82609503，首位不是 1，不能被当成代码。"""
    assert extract_item_code(["B2609503"]) is None


def test_item_code_requires_first_digit_one():
    """Owner 确认：物料代码 1000/1200/1300/1400 开头，首位恒为 1。"""
    assert extract_item_code(["83000215"]) is None


def test_item_code_wrong_length_rejected():
    assert extract_item_code(["1300021"]) is None    # 7 位
    assert extract_item_code(["130002155"]) is None  # 9 位


def test_item_code_not_inside_longer_token():
    """嵌在更长串里的 8 位数字不算——避免从别的编号里抠出一段。"""
    assert extract_item_code(["X13000215Y"]) is None


# --- 批号 -------------------------------------------------------------------


def test_batch_basic():
    assert extract_batch_no(["生产批号：", "B2609503"]) == "B2609503"


def test_batch_with_letters_prefix():
    assert extract_batch_no(["BMT2607701"]) == "BMT2607701"


def test_batch_sub_batch_suffix():
    assert extract_batch_no(["B2609503-1"]) == "B2609503-1"


def test_batch_keeps_letters_unchanged():
    """批号**不能**做形近映射：把 B 映成 8 会毁掉批号。"""
    assert extract_batch_no(["B2609503"]) == "B2609503"


def test_batch_majority_wins():
    lines = ["B2609503", "B2609503", "B2609504"]
    assert extract_batch_no(lines) == "B2609503"


def test_batch_none_when_absent():
    assert extract_batch_no(["纯中文没有批号"]) is None


# --- 产品名称 ---------------------------------------------------------------


def test_name_anchored_after_label():
    """贴着「品名：」取——实测这是最可靠的一条。"""
    assert extract_product_name(["品名：测试原料甲"]) == "测试原料甲"
    assert extract_product_name(["名：测试原料甲"]) == "测试原料甲"


def test_name_anchored_beats_company_name():
    """公司名比品名长，但锚定规则不受长度影响。"""
    lines = ["某某某制药有限公司", "品名：测试原料甲"]
    assert extract_product_name(lines) == "测试原料甲"


def test_name_fallback_majority():
    """没有「品名：」锚点时，退回频次法。"""
    lines = ["某某某制药有限公司", "测试原料甲", "测试原料甲"]
    assert extract_product_name(lines) == "测试原料甲"


def test_name_skips_ascii_and_labels():
    lines = ["Shenzhen Something Co., Ltd", "编码：APP-SOP-QA-1", "测试原料甲", "测试原料甲"]
    assert extract_product_name(lines) == "测试原料甲"


def test_name_excludes_address_words():
    """地址里的「市/区/街/坊」是噪声，不能选成品名。"""
    lines = ["测试原料甲", "某市某技术开发区某街坊"]
    assert extract_product_name(lines) == "测试原料甲"


def test_name_none_when_nothing_usable():
    assert extract_product_name(["1234567890", "ABC-DEF"]) is None


def test_name_label_split_across_lines():
    """标签与值被 OCR 切成两行时，往后回看取值。

    实测标签上「品」「名：」「美罗培南」是三个独立的框。旧规则要求
    冒号后至少一个字符（`.+`），这种标签**根本不被识别成标签**，
    于是值永远取不到，只能退化到频次法抓噪声。
    """
    assert extract_product_name(["品", "名：", "测试原料甲"]) == "测试原料甲"


def test_name_lookahead_does_not_take_field_label():
    """回看撞上带冒号的行就停，不能把「生产批号：」当成品名。"""
    assert extract_product_name(["品名：", "生产批号："]) is None


def test_name_allows_ascii_in_parentheses():
    """品名里的少量 ASCII（如「（B）」）不能把整条判掉。

    实测真实品名「美罗培南（B）」含字母 B；按「含 ASCII 就丢弃」的
    旧判据会被整条扔掉，再退化到频次法抓回一串噪声。
    """
    assert extract_product_name(["名：测试原料甲（B）"]) == "测试原料甲（B）"


def test_name_fallback_rejects_short_fragments():
    """频次法有长度下限：宁可不给，也不能从残渣里抓碎片交差。

    实测只要标签上没读到品名，旧的频次法就会交出「存新件」「合证」
    「避免硫碰。」这类 2~5 字残渣，把「没读到」谎报成「读到了」。
    """
    assert extract_product_name(["存新件"]) is None
    assert extract_product_name(["合证", "紧明"]) is None
    # 够长的仍要认出来，不能因为加了下限就把真品名一起挡掉
    assert extract_product_name(["存新件", "测试原料甲混粉"]) == "测试原料甲混粉"


# --- 日期 -------------------------------------------------------------------


def test_dates_chinese_full():
    got = dict(extract_dates(["2026年09月14日"]))
    assert got == {"2026年09月14日": (2026, 9, 14)}


def test_dates_chinese_month_only():
    """只到月要能抽出来，日留 None。"""
    got = dict(extract_dates(["2028年11月"]))
    assert got == {"2028年11月": (2028, 11, None)}


def test_dates_dotted():
    got = dict(extract_dates(["2026.09.14"]))
    assert got == {"2026.09.14": (2026, 9, 14)}


def test_dates_rejects_digit_glued_noise():
    """标签上常被 OCR 切出 ``402025.12.23`` 这类粘连噪声，必须挡掉。"""
    assert extract_dates(["402025.12.23"]) == []


def test_dates_rejects_bad_month():
    assert extract_dates(["2026年13月"]) == []


def test_dates_rejects_bad_day():
    assert extract_dates(["2026.09.32"]) == []


def test_dates_rejects_out_of_range_year():
    assert extract_dates(["1899年09月14日"]) == []


def test_dates_numeric_month_only():
    """数字分隔只到月（``2028.06``）——实测 39/50 张的有效期就是这样印的。

    漏了这一种，三分之二的有效期会整条丢掉。
    """
    got = dict(extract_dates(["2028.06"]))
    assert got == {"2028.06": (2028, 6, None)}


def test_dates_month_only_after_colon():
    """标签上常见的 ``复检期/有效期至：2027.06`` 被 OCR 切成 ``:2027.06``。"""
    got = dict(extract_dates([":2027.06"]))
    assert got == {"2027.06": (2027, 6, None)}


def test_dates_full_not_truncated_to_month():
    """``2026.07.27`` 不能被月粒度规则再截出一个 ``2026.07``——这是回归防线。"""
    got = extract_dates(["2026.07.27"])
    assert got == [("2026.07.27", (2026, 7, 27))]


def test_dates_mixed_granularity():
    got = dict(extract_dates(["2026.07.27", "2028.06"]))
    assert got == {"2026.07.27": (2026, 7, 27), "2028.06": (2028, 6, None)}


def test_dates_skips_signature_lines():
    """签核行（操作人/复核人/日期）上的日期是**人员签核日期**，不是物料日期。

    实测有一张标签：复核日期被误读成 2021.06.27，而真正的生产日期
    2025.06.25 因此被挤到"有效期"位置上——「取最早作生产日期」被顶掉了。
    """
    lines = [
        "生产日期：",
        "2025年06月25日",
        "复核人/日期：2021.06.27",
    ]
    got = dict(extract_dates(lines))
    assert got == {"2025年06月25日": (2025, 6, 25)}


def test_dates_skips_operator_line():
    assert extract_dates(["操作人/日期：2026.03.02"]) == []


def test_dates_keeps_real_expiry_next_to_signature_word():
    """真值行不该因为同页有签核字样就被牵连——只有该行自身含签核词才跳过。"""
    lines = ["复核人/日期：2021.06.27", "复检期/有效期至：", "2028年06月"]
    got = dict(extract_dates(lines))
    assert got == {"2028年06月": (2028, 6, None)}


# --- 组装：最早作生产日期、最晚作有效期 -------------------------------------


def _extract(lines):
    return PaddleOCRBackend._extract(lines)


def test_extract_earliest_is_production_latest_is_expiry():
    fields = _extract(["2026年09月14日", "2028年11月"])
    assert fields["manufacturing_date"] == "2026年09月14日"
    assert fields["expiry_date"] == "2028年11月"


def test_extract_single_date_no_expiry():
    fields = _extract(["2026年09月14日"])
    assert fields["manufacturing_date"] == "2026年09月14日"
    assert fields["expiry_date"] is None


def test_extract_ignores_blank_lines():
    fields = _extract(["", "   ", "13000215"])
    assert fields["item_code"] == "13000215"


def test_extract_full_label_shape():
    """整张标签的形状：字段名与值分行、重复出现、混着噪声。"""
    lines = [
        "某某某制药有限公司",
        "Shenzhen Something Pharmaceutical Co., Ltd",
        "原料药标签（API）",
        "品名：",
        "测试原料甲",
        "生产批号：",
        "B2609503",
        "生产日期：",
        "2026年09月14日",
        "物料代码：",
        "13000215",
        "复检期/有效期至：",
        "2028年11月",
        "402025.12.23",  # 粘连噪声
    ]
    fields = _extract(lines)
    assert fields["product_name"] == "测试原料甲"
    assert fields["batch_no"] == "B2609503"
    assert fields["item_code"] == "13000215"
    assert fields["manufacturing_date"] == "2026年09月14日"
    assert fields["expiry_date"] == "2028年11月"


# --- 生产日期：按保质期常识剔除噪声 -----------------------------------------
#
# 实测教训：有标签上出现三个日期，其中一个是 OCR 把某段印刷内容切出来的噪声，
# 而另一个才是**真正的生产日期**（模型读对了）。
# 「取最早」把噪声当成了生产日期，**读对的正确值反被扔掉**，
# 且格式合法、原文里确实有这串数字，任何格式校验都拦不住。


def test_extract_production_skips_far_future_noise():
    """噪声远在效期之前（超 5 年）→ 不当生产日期。"""
    lines = [
        "生产日期：",
        "2025年06月25日",
        "复检期/有效期至：",
        "2028年06月24日",
        "210h2020.11.07",  # 噪声：比真实生产日期还早 4 年
    ]
    fields = _extract(lines)
    assert fields["manufacturing_date"] == "2025年06月25日"
    assert fields["expiry_date"] == "2028年06月24日"


def test_extract_production_keeps_plausible_earliest():
    """2~3 年保质期内的候选照常取最早，不能误伤。"""
    fields = _extract(["2026年8月26日", "2026年8月28日", "2028年7月31日"])
    assert fields["manufacturing_date"] == "2026年8月26日"


def test_extract_production_not_dropped_when_all_implausible():
    """若全部候选都离效期很远，不能把生产日期弄丢——退回不筛。"""
    fields = _extract(["2010年01月01日", "2011年01月01日", "2028年07月31日"])
    assert fields["manufacturing_date"] == "2010年01月01日"


def test_extract_production_two_year_shelf_life():
    """2 年保质期（如混粉）也要落在阈值内。"""
    fields = _extract(["2026年9月1日", "2028年8月31日"])
    assert fields["manufacturing_date"] == "2026年9月1日"


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
