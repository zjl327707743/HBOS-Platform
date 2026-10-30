"""LLM 输出的解析与**校验** —— 纯函数，可离线单测。

为什么要有校验层：Owner 定了**不做人工确认**，AI 结论直接进看板。
模型可能给出枚举外的评级、编造的工序名、或夹杂 markdown 围栏。
这些都必须在写飞书**之前**拦下 —— 写进去就进看板了。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .prompt import GRADES

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)

#: 飞书日期字段按北京时间解释（与取数服务 `contract.parse_month_day` 同一条理由）。
_CN_TZ = timezone(timedelta(hours=8))


@dataclass
class Suggestion:
    """一条可执行的工艺改进建议。"""

    action: str       # 做什么（含参数名 + 目标值）
    basis: str        # 依据（哪几批、什么统计）
    expected: str     # 预期效果，或「待验证」
    priority: str     # 高 / 中 / 低


#: 建议优先级枚举。与提示词一致。
PRIORITIES = ("高", "中", "低")


@dataclass
class ProcessAnalysis:
    name: str
    grade: str
    summary: str
    report: str
    suggestions: list[Suggestion] = field(default_factory=list)


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

    # **先校验工序名，再校验内容**。顺序反过来的话，模型多编一道工序时
    # 报出来的会是「那道编造的工序缺 suggestions」—— 把真正的问题
    # （多了个不存在的工序）藏在一句细节报错后面，排查时看不出来。
    names: list[str] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ParseError(f"第 {i} 条不是对象")
        name = str(item.get("name", "")).strip()
        if not name:
            raise ParseError(f"第 {i} 条缺 name")
        names.append(name)

    want = list(expected_processes)
    # 先查重复再查覆盖 —— 反过来写的话重复永远轮不到报（重复必然同时缺一个）。
    if len(set(names)) != len(names):
        dup = sorted({x for x in names if names.count(x) > 1})
        raise ParseError(f"工序有重复：{dup}")
    if sorted(names) != sorted(want):
        missing = [x for x in want if x not in names]
        extra = [x for x in names if x not in want]
        raise ParseError(f"工序对不上。缺：{missing}；多：{extra}")

    out: list[ProcessAnalysis] = []
    for i, item in enumerate(items):
        name = names[i]
        grade = str(item.get("grade", "")).strip()
        summary = str(item.get("summary", "")).strip()
        report = str(item.get("report", "")).strip()
        if grade not in GRADES:
            raise ParseError(f"工序「{name}」的评级非法：{grade!r}（只允许 {'/'.join(GRADES)}）")
        if not summary:
            raise ParseError(f"工序「{name}」缺结论摘要")
        # `完整报告` 是看板「查看详情」的全部内容。空报告能通过校验的话，
        # 看板会显示有效评级 + 摘要，点进去却是空白 —— 车间拿不到依据，
        # 却以为有。宁可本轮不写回。
        if not report:
            raise ParseError(f"工序「{name}」缺完整报告")
        suggestions = _parse_suggestions(name, item.get("suggestions"))
        out.append(
            ProcessAnalysis(
                name=name,
                grade=grade,
                summary=summary,
                report=report,
                suggestions=suggestions,
            )
        )

    return out


def _parse_suggestions(
    process: str, raw: Any
) -> list[Suggestion]:
    """校验 `suggestions` 数组。

    **至少一条**，且每条 `action` 非空、`priority` 在枚举内。
    这条规则不是形式要求 —— Owner 反馈原输出「太单薄」的核心就是
    62 条里只有 6 条给了具体动作。没有 action 的「建议」等于没写，
    让它进结果表就是浪费看板一行。

    但**不校验 action 的「具体度」**（是否含数字）—— 那要靠自然语言判断，
    正则判不准：「先补录烘干温度字段」是合格建议但不含数字。
    """
    if not isinstance(raw, list) or not raw:
        raise ParseError(f"工序「{process}」缺 suggestions（至少要有一条可执行建议）")

    out: list[Suggestion] = []
    for j, s in enumerate(raw):
        if not isinstance(s, dict):
            raise ParseError(f"工序「{process}」的第 {j+1} 条建议不是对象")
        action = str(s.get("action", "")).strip()
        if not action:
            raise ParseError(f"工序「{process}」的第 {j+1} 条建议缺 action")
        priority = str(s.get("priority", "")).strip() or "中"
        if priority not in PRIORITIES:
            # 优先级写错不值得整轮作废，归到「中」并记日志由调用方处理
            priority = "中"
        out.append(
            Suggestion(
                action=action,
                basis=str(s.get("basis", "")).strip(),
                expected=str(s.get("expected", "")).strip(),
                priority=priority,
            )
        )
    return out


def render_suggestions(suggestions: list[Suggestion]) -> str:
    """把结构化建议渲染成报告末尾的「## 改进建议」段。

    为什么由 Python 渲染、不让模型直接写进 report：

      - **格式统一** —— 62 条报告的建议段落长得一样，扫读快
      - **不重复** —— 模型在 report 里写完又在数组里写一遍，两份措辞
        不一样时，车间不知道以哪个为准
      - **优先级可排序** —— 高优先级的排前面，模型不一定按这个顺序写

    结果表没有独立的「建议」字段（不改飞书表结构），所以拼进 `完整报告`。
    """
    if not suggestions:
        return ""
    order = {"高": 0, "中": 1, "低": 2}
    ranked = sorted(suggestions, key=lambda s: order.get(s.priority, 1))
    lines = ["## 改进建议"]
    for i, s in enumerate(ranked, 1):
        lines.append(f"{i}. **[{s.priority}]** {s.action}")
        if s.basis:
            lines.append(f"   - 依据：{s.basis}")
        if s.expected:
            lines.append(f"   - 预期：{s.expected}")
    return "\n".join(lines)


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
    out: list[dict[str, Any]] = []
    for a in analyses:
        # 建议拼在报告末尾 —— 结果表没有独立的「建议」字段（不动飞书表结构）
        report = a.report
        block = render_suggestions(a.suggestions)
        if block:
            report = f"{report}\n\n{block}" if report else block
        out.append(
            {
                "产品": product,          # 单选 → 字符串
                "工序": a.name,
                "分析日期": ms,            # 日期 → 毫秒时间戳
                "结论摘要": a.summary,
                "评级": a.grade,          # 单选 → 字符串
                "完整报告": report,
                "数据指纹": fingerprint,
            }
        )
    return out
