"""LLM 输出的解析与**校验** —— 纯函数，可离线单测。

为什么要有校验层：Owner 定了**不做人工确认**，AI 结论直接进看板。
模型可能给出枚举外的评级、编造的工序名、或夹杂 markdown 围栏。
这些都必须在写飞书**之前**拦下 —— 写进去就进看板了。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .prompt import GRADES

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)

#: 飞书日期字段按北京时间解释（与取数服务 `contract.parse_month_day` 同一条理由）。
_CN_TZ = timezone(timedelta(hours=8))


@dataclass
class ProcessAnalysis:
    name: str
    grade: str
    summary: str
    report: str


class ParseError(ValueError):
    pass


def strip_fence(text: str) -> str:
    """去掉可能出现的 markdown 代码围栏。

    提示词里明确要求「不要 markdown 代码块」，但模型仍可能加 —— 这是
    最常见的格式偏差，先兜住，不必因此判失败。
    """
    return _FENCE.sub("", (text or "").strip()).strip()


def parse_response(raw: str, expected_processes: list[str]) -> list[ProcessAnalysis]:
    """解析模型输出并校验。

    校验项（任一不过即抛 `ParseError`，**不写飞书**）：
      - 必须是合法 JSON、含 `processes` 数组
      - 每条含 name / grade / summary / report
      - `grade` 必须是四档之一（模型可能自造「基本达标」这类值）
      - `name` 必须**恰好覆盖**期望的工序清单（不多不少）
    """
    text = strip_fence(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ParseError(f"不是合法 JSON：{exc}") from exc

    items = data.get("processes") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise ParseError("缺少 processes 数组或为空")

    out: list[ProcessAnalysis] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ParseError(f"第 {i} 条不是对象")
        name = str(item.get("name", "")).strip()
        grade = str(item.get("grade", "")).strip()
        summary = str(item.get("summary", "")).strip()
        report = str(item.get("report", "")).strip()
        if not name:
            raise ParseError(f"第 {i} 条缺 name")
        if grade not in GRADES:
            raise ParseError(f"工序「{name}」的评级非法：{grade!r}（只允许 {'/'.join(GRADES)}）")
        if not summary:
            raise ParseError(f"工序「{name}」缺结论摘要")
        out.append(ProcessAnalysis(name=name, grade=grade, summary=summary, report=report))

    got = [p.name for p in out]
    want = list(expected_processes)
    # 先查重复再查覆盖 —— 反过来写的话重复永远轮不到报（重复必然同时缺一个），
    # 报出来的会是含糊的「工序对不上」。
    if len(set(got)) != len(got):
        dup = sorted({x for x in got if got.count(x) > 1})
        raise ParseError(f"工序有重复：{dup}")
    if sorted(got) != sorted(want):
        missing = [x for x in want if x not in got]
        extra = [x for x in got if x not in want]
        raise ParseError(f"工序对不上。缺：{missing}；多：{extra}")

    return out


def analyzed_on_ms(day: str) -> int:
    """`YYYY-MM-DD` → 飞书日期字段要的**毫秒时间戳**（北京当地午夜）。

    踩过：写 `"2026-10-08"` 或 `"2026-10-08T00:00:00+08:00"` 都被拒
    （`DatetimeFieldConvFail`）。飞书只要毫秒整数。

    **按北京时间取午夜** —— 与 `contract.parse_month_day` 同一条理由：
    用 UTC 会得到前一天，跨月批次会落错月。
    """
    y, m, d = (int(x) for x in day.split("-"))
    return int(datetime(y, m, d, tzinfo=_CN_TZ).timestamp() * 1000)


def to_records(
    product: str, analyses: list[ProcessAnalysis], analyzed_on: str, fingerprint: str
) -> list[dict[str, Any]]:
    """转成结果表的字段 dict 列表。

    字段名与飞书表 `AI工艺分析结果` **逐字一致**（见 AI 规格 §4.2）。

    **值的格式**（实测出来的，别照直觉改）：
      - 单选（`产品` / `评级`）→ **字符串**，不是数组。传数组会
        `SingleSelectFieldConvFail`（读的时候是数组，写的时候不是 —— 不对称）
      - 日期（`分析日期`）→ **毫秒时间戳**，字符串会被 `DatetimeFieldConvFail` 拒
    """
    ms = analyzed_on_ms(analyzed_on)
    return [
        {
            "产品": product,          # 单选 → 字符串
            "工序": a.name,
            "分析日期": ms,            # 日期 → 毫秒时间戳
            "结论摘要": a.summary,
            "评级": a.grade,          # 单选 → 字符串
            "完整报告": a.report,
            "数据指纹": fingerprint,
        }
        for a in analyses
    ]
