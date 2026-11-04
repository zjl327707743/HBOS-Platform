"""解析与校验层的单测 —— **不联网、不调模型**。

校验层是这轮的关键防线：Owner 定了不做人工确认，AI 结论直接进看板。
模型给出的枚举外的评级、编造的工序名，都必须在写飞书之前拦下。
"""

from __future__ import annotations

import json

import pytest

from app import parse
from app.prompt import GRADES


def _resp(processes):
    return json.dumps({"processes": processes}, ensure_ascii=False)


GOOD = [
    {"name": "锌粉活化", "grade": "数据不足", "summary": "台账缺锌粉粒度记录", "report": "## 当前现状\n..."},
    {"name": "7eβ合成", "grade": "部分达到", "summary": "温度达标，时长偏短", "report": "## 当前现状\n..."},
]


# ---------------------------------------------------------------------------
# 正常路径
# ---------------------------------------------------------------------------

def test_parse_valid_response():
    got = parse.parse_response(_resp(GOOD), ["锌粉活化", "7eβ合成"])
    assert [p.name for p in got] == ["锌粉活化", "7eβ合成"]
    assert got[0].grade == "数据不足"


def test_strip_markdown_fence():
    # 提示词要求不要代码块，但模型常加 —— 兜住，不必因此判失败
    raw = "```json\n" + _resp(GOOD) + "\n```"
    assert len(parse.parse_response(raw, ["锌粉活化", "7eβ合成"])) == 2


# ---------------------------------------------------------------------------
# 校验：这些必须拦下（拦不住就会进看板）
# ---------------------------------------------------------------------------

def test_reject_illegal_grade():
    # 模型可能自造评级（如「基本达标」）—— 结果表是单选，写进去会多出一个选项
    bad = [dict(GOOD[0], grade="基本达标"), GOOD[1]]
    with pytest.raises(parse.ParseError, match="评级非法"):
        parse.parse_response(_resp(bad), ["锌粉活化", "7eβ合成"])


def test_reject_missing_process():
    with pytest.raises(parse.ParseError, match="工序对不上"):
        parse.parse_response(_resp(GOOD[:1]), ["锌粉活化", "7eβ合成"])


def test_reject_invented_process():
    # 模型凭空加一道工序 —— 会污染结果表，且看板会多出一行
    bad = GOOD + [{"name": "不存在的工序", "grade": "数据不足", "summary": "x", "report": "y"}]
    with pytest.raises(parse.ParseError, match="工序对不上"):
        parse.parse_response(_resp(bad), ["锌粉活化", "7eβ合成"])


def test_reject_duplicate_process():
    bad = [GOOD[0], dict(GOOD[0])]
    with pytest.raises(parse.ParseError, match="重复"):
        parse.parse_response(_resp(bad), ["锌粉活化"])


def test_reject_non_json():
    with pytest.raises(parse.ParseError, match="不是合法 JSON"):
        parse.parse_response("我分析了一下，情况如下：……", ["锌粉活化"])


def test_reject_empty_processes():
    with pytest.raises(parse.ParseError):
        parse.parse_response('{"processes": []}', ["锌粉活化"])


def test_reject_missing_summary():
    bad = [dict(GOOD[0], summary=""), GOOD[1]]
    with pytest.raises(parse.ParseError, match="结论摘要"):
        parse.parse_response(_resp(bad), ["锌粉活化", "7eβ合成"])


# ---------------------------------------------------------------------------
# 转记录：字段名必须与飞书表逐字一致
# ---------------------------------------------------------------------------

def test_to_records_field_names_match_feishu_table():
    got = parse.parse_response(_resp(GOOD), ["锌粉活化", "7eβ合成"])
    recs = parse.to_records("4BMA", got, "2026-10-02", "abc123")
    assert len(recs) == 2
    assert set(recs[0].keys()) == {
        "产品", "工序", "分析日期", "结论摘要", "评级", "完整报告", "数据指纹",
    }
    assert all(r["数据指纹"] == "abc123" for r in recs)


def test_select_fields_are_strings_not_arrays():
    # 实测：单选用**字符串**。传数组会 SingleSelectFieldConvFail ——
    # 读的时候飞书返回数组，写的时候要字符串，这个不对称很容易写错。
    got = parse.parse_response(_resp(GOOD), ["锌粉活化", "7eβ合成"])
    rec = parse.to_records("4BMA", got, "2026-10-02", "x")[0]
    assert rec["产品"] == "4BMA"
    assert rec["评级"] == "数据不足"


def test_date_field_is_millisecond_timestamp_beijing():
    # 实测：日期要**毫秒时间戳**。字符串（含 ISO 带时区）都会被
    # DatetimeFieldConvFail 拒。且按北京时间取午夜，不是 UTC
    # （否则会落到前一天，与落月口径同一条坑）。
    ms = parse.analyzed_on_ms("2026-10-08")
    assert ms == 1791388800000
    # 北京时间 2026-10-08 00:00 == UTC 2026-10-07 16:00
    from datetime import datetime, timezone
    assert datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") == "2026-10-07 16:00"


def test_grades_constant_matches_feishu_options():
    # 结果表的单选选项就是这个四档 —— 改了这里必须同步改飞书表的选项
    assert GRADES == ("已达标", "部分达到", "数据不足", "未达标")
