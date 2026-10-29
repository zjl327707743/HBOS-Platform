"""提示词构造 —— **纯函数**，可离线单测。

输出规格照《4BMA降本增效实验方案分析报告》（Owner 提供）。那份报告确立的几条约定
在本服务里是**硬约束**，不是风格偏好：

    1. 证据分级：文档事实 / 分析判断 / 待验证假设
    2. **缺数据就写「无相关数据」，不臆测** ← 最重要
    3. 每个工序七段式
    4. 评级只用四档：已达标 / 部分达到 / 数据不足 / 未达标

第 2 条之所以是硬约束：Owner 定了**不做人工确认**，AI 结论直接进看板给车间经理看。
输出里任何没有依据的判断，都会以「结论」的形式影响生产决策。
"""

from __future__ import annotations

import json
from typing import Sequence

from .sources import CraftDescription, LedgerBatch

#: 评级枚举 —— 与结果表的单选字段选项**逐字一致**。
GRADES = ("已达标", "部分达到", "数据不足", "未达标")

SYSTEM_PROMPT = """你是新乡海滨药业的生产工艺分析助手。

你的任务：拿「工艺标准」和「近期生产台账」做比对，逐工序给出工艺提升建议。

## 输出要求

只输出一个 JSON 对象，不要任何其他文字、不要 markdown 代码块。结构：

{
  "processes": [
    {
      "name": "<工序名，必须与输入的工序名逐字一致>",
      "grade": "<已达标|部分达到|数据不足|未达标>",
      "summary": "<一句话结论，不超过 60 字>",
      "report": "<七段式完整分析，见下>"
    }
  ]
}

`report` 字段用这七个小标题分段（用「## 标题」的形式）：

## 当前现状
## 目标
## 分析
## 观察到的偏差
## 结果判断
## 是否达到目标
## 数据完整性

## 铁律（违反即视为无效输出）

1. **没有依据的话不说。** 台账里没有的参数，写「台账无相关数据」，**不要推测、
   不要用行业经验补全、不要给出看起来合理的数字**。
2. **每个判断都要能指到来源。** 数据来自哪一批、哪个字段，写清楚（如
   「批 E2603101 转料前预冷水温度 12.2℃」）。
3. **区分三类表述**：
   - 文档事实：原文数据、条件
   - 分析判断：你的比较与审查
   - 待验证假设：只能作为下一轮验证方向，**不得当作结论**
4. **数据不足就如实标 `数据不足`。** 这不是失败，是正确结论。
   标 `已达标` 必须有同口径的实测证据支持。
5. **不下生产指令。** 你只出建议，不批准任何工艺变更。
"""


def _fmt_craft(craft: CraftDescription) -> str:
    """工艺标准（应然）—— 三种维度分开列。"""
    lines: list[str] = []
    for proc in craft.processes:
        lines.append(f"### 工序：{proc}")
        c = craft.craft.get(proc)
        s = craft.standard.get(proc)
        e = craft.equipment.get(proc)
        lines.append(f"- 工艺描述：{c if c else '（台账无相关数据）'}")
        lines.append(f"- 标准参数：{s if s else '（台账无相关数据）'}")
        lines.append(f"- 设备描述：{e if e else '（台账无相关数据）'}")
        lines.append("")
    return "\n".join(lines)


def _fmt_ledger(ledger: Sequence[LedgerBatch]) -> str:
    """近期台账（实然）—— 逐批列，只列非空字段。

    批数由调用方限制（默认最近 30 批）；台账有 1200+ 行，全喂会撑爆上下文。
    """
    if not ledger:
        return "（台账无相关数据）"
    lines: list[str] = []
    for b in ledger:
        head = f"### 批次 {b.batch}" if b.batch else "### 批次（无批号）"
        lines.append(head)
        for k, v in b.values.items():
            lines.append(f"- {k}：{v}")
        lines.append("")
    return "\n".join(lines)


def build_user_prompt(
    product: str, craft: CraftDescription, ledger: Sequence[LedgerBatch]
) -> str:
    """构造用户消息。"""
    return f"""分析产品：**{product}**

以下是该产品的**工序清单**（{len(craft.processes)} 道）：
{json.dumps(craft.processes, ensure_ascii=False)}

要求：**每一道工序都出一条**，不要漏、不要多、`name` 必须与上面逐字一致。

---

## 一、工艺标准（应然）

{_fmt_craft(craft)}

---

## 二、近期生产台账（实然，最近 {len(ledger)} 批）

{_fmt_ledger(ledger)}

---

现在逐工序分析。记住：**没有依据的话不说，数据不足就标数据不足。**
只输出 JSON。
"""
