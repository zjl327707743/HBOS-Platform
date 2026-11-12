"""工艺描述解析的单测 —— 纯函数，不联网、不调模型。

为什么值得单测：各产品的工艺描述表**结构并不一致**（这是实测踩出来的）——
4BMA 用「项目」列标维度、F9 用「序号」的裸数字 1/2/3、F12/F13 用「序号」的
中文标签、无菌两张表还用「规格/投料量」把同一工序分成多个规格组。

解析错的后果不是报错，而是**静默出错**：要么把「序号」「基本信息」当成工序
喂给模型，要么多规格互相覆盖只剩最后一组。所以每条形态各钉一个用例。
"""

from __future__ import annotations

from app.sources import parse_craft_records


def _rec(**fields):
    return {"fields": fields}


# ---------------------------------------------------------------------------
# 4BMA 形态：`项目` = 工艺 / 标准工艺参数 / 设备描述
# ---------------------------------------------------------------------------

def test_4bma_style_item_column():
    recs = [
        _rec(项目="工艺", SourceID="x", **{"锌粉活化": "加150kg锌粉", "7eβ合成": "15~18℃滴加"}),
        _rec(项目="标准工艺参数", **{"锌粉活化": "64~68℃", "7eβ合成": "M3≤3.0%"}),
        _rec(项目="设备描述", **{"锌粉活化": "R228 3000L"}),
    ]
    cd = parse_craft_records("4BMA", recs)
    assert cd.processes == ["锌粉活化", "7eβ合成"]      # 不含 项目 / SourceID
    assert cd.standard["锌粉活化"] == "64~68℃"
    assert cd.equipment["锌粉活化"] == "R228 3000L"
    assert "7eβ合成" not in cd.equipment                 # 该行没这个字段


# ---------------------------------------------------------------------------
# F9 形态：`序号` = 裸数字 1/2/3，语义靠位置（1=工艺, 2=标准, 3=设备）
# ---------------------------------------------------------------------------

def test_f9_style_positional_numbers():
    recs = [
        _rec(序号="1", **{"F7.5后处理": "1.5M盐酸洗"}),
        _rec(序号="2", **{"F7.5后处理": "F7.5≤0.3%"}),
        _rec(序号="3", **{"F7.5后处理": "R332 5000L"}),
    ]
    cd = parse_craft_records("F9", recs)
    assert cd.processes == ["F7.5后处理"]                # 序号未被当成工序
    assert cd.craft["F7.5后处理"] == "1.5M盐酸洗"
    assert cd.standard["F7.5后处理"] == "F7.5≤0.3%"
    assert cd.equipment["F7.5后处理"] == "R332 5000L"


# ---------------------------------------------------------------------------
# F12/F13 形态：`序号` = 中文标签（顺序与 4BMA 不同，靠标签不靠位置）
# ---------------------------------------------------------------------------

def test_f12_style_labelled_index_column():
    # F12 实测顺序是 工艺描述 / 设备描述 / 标准工艺参数 —— 顺序与 4BMA 不同
    recs = [
        _rec(序号="工艺描述", 产品基本信息="五车间", **{"离心": "分两次转离心机"}),
        _rec(序号="设备描述", **{"离心": "1250L 1000R/min"}),
        _rec(序号="标准工艺参数", **{"离心": "釜温0-5℃"}),
    ]
    cd = parse_craft_records("F12", recs)
    assert cd.processes == ["离心"]                      # 产品基本信息被排除
    assert cd.craft["离心"] == "分两次转离心机"
    assert cd.equipment["离心"] == "1250L 1000R/min"
    assert cd.standard["离心"] == "釜温0-5℃"


def test_f13_style_index_labels():
    # F13 用「工艺描述 / 工艺参数 / 设备参数」
    recs = [
        _rec(序号="工艺描述", 产品基本信息="六车间", **{"氢化工序": "转入氢化釜"}),
        _rec(序号="工艺参数", **{"氢化工序": "40~43℃"}),
        _rec(序号="设备参数", **{"氢化工序": "3000L 浆式"}),
    ]
    cd = parse_craft_records("F13", recs)
    assert cd.processes == ["氢化工序"]
    assert cd.standard["氢化工序"] == "40~43℃"
    assert cd.equipment["氢化工序"] == "3000L 浆式"


# ---------------------------------------------------------------------------
# 无菌形态：`项目` = 工艺描述 / 工艺参数 / 设备参数，且一表多规格
# ---------------------------------------------------------------------------

def test_sterile_single_spec_has_no_suffix():
    # 真实表列名是「规格/投料量」（带斜杠），用 dict 字面量构造
    recs = [
        {"fields": {"项目": "工艺描述", "产品名称": "美罗培南", "规格/投料量": "规范/50kg",
                    "干燥": "30-35℃干燥"}},
        {"fields": {"项目": "工艺参数", "规格/投料量": "规范/50kg", "干燥": "干燥5-6h"}},
        {"fields": {"项目": "设备参数", "规格/投料量": "规范/50kg", "干燥": "桨式"}},
    ]
    cd = parse_craft_records("无菌美罗培南", recs)
    assert cd.processes == ["干燥"]                      # 单规格不加后缀
    assert "产品名称" not in cd.processes
    assert "规格/投料量" not in cd.processes


def test_sterile_multi_spec_suffixes_processes():
    # 两个规格组，工序名必须带规格后缀，否则后一组会覆盖前一组
    recs = [
        {"fields": {"项目": "工艺描述", "规格/投料量": "规范/50kg", "结晶": "A法"}},
        {"fields": {"项目": "工艺参数", "规格/投料量": "规范/50kg", "结晶": "15±2℃"}},
        {"fields": {"项目": "工艺描述", "规格/投料量": "欧盟/160kg", "结晶": "B法"}},
        {"fields": {"项目": "工艺参数", "规格/投料量": "欧盟/160kg", "结晶": "10±5℃"}},
    ]
    cd = parse_craft_records("无菌亚胺培南", recs)
    assert cd.processes == ["结晶（规范/50kg）", "结晶（欧盟/160kg）"]
    # 两组的值各归各位 —— 这正是「不加后缀就丢数据」要防的
    assert cd.craft["结晶（规范/50kg）"] == "A法"
    assert cd.craft["结晶（欧盟/160kg）"] == "B法"
    assert cd.standard["结晶（欧盟/160kg）"] == "10±5℃"


# ---------------------------------------------------------------------------
# 边界
# ---------------------------------------------------------------------------

def test_rows_without_dimension_marker_are_skipped():
    recs = [_rec(SourceID="x", 锌粉活化="..."), _rec(项目="工艺", 锌粉活化="ok")]
    cd = parse_craft_records("4BMA", recs)
    assert cd.craft == {"锌粉活化": "ok"}


def test_process_list_is_union_across_rows():
    # 只取一行会漏字段：F12 实测有的行多出字段、有的行少
    recs = [
        _rec(项目="工艺", A="1"),
        _rec(项目="标准工艺参数", A="2", B="只有这行有"),
    ]
    cd = parse_craft_records("X", recs)
    assert cd.processes == ["A", "B"]
    assert cd.standard["B"] == "只有这行有"
