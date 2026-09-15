"""约束校验层——识别准确率的放大器。

设计理念（M3-R6 方案 4.3）：

    模型负责"读"，规则负责"筛"，人负责"定"。

本模块独立于任何识别后端，接收「原始识别结果」，输出「规范化 + 校验结论」。
无论走 C1（本地大模型）还是 C2（OCR + 规则），都要过这一层。

核心事实（Owner 确认）：
    **物料代码是 8 位、全数字，不存在含字母的情况。**

这一条让代码可以**不依赖任何主数据**就完成纠错——OCR 最常见的错误是把数字认成
形近字母（`0`/`O`、`1`/`l`、`5`/`S`、`8`/`B` …），既然代码只可能是数字，把字母
无条件映射回形近数字即可，不需要知道"合法代码有哪些"。

业务边界（M3-R0 确认）：
    仓库不负责批号管理，批号由车间给出。因此批号校验**只提示、不阻断**，
    绝不能因为格式不符就拒绝录入。
"""

from __future__ import annotations

import re
import datetime
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# 物料代码
# ---------------------------------------------------------------------------

ITEM_CODE_LENGTH = 8

# 形近字符映射：OCR 把数字认成字母时，按此表还原。
# 依据：数字与字母在常见字体下的形近关系。
CONFUSABLE_TO_DIGIT = {
    "O": "0",
    "o": "0",
    "D": "0",
    "Q": "0",
    "I": "1",
    "l": "1",
    "i": "1",
    "|": "1",
    "Z": "2",
    "z": "2",
    "A": "4",
    "S": "5",
    "s": "5",
    "G": "6",
    "b": "8",
    "B": "8",
    "g": "9",
    "q": "9",
    "T": "7",
    "?": "7",
}


def normalize_item_code(raw: Optional[str]) -> tuple[Optional[str], list[str]]:
    """把识别到的物料代码规范化为 8 位数字。

    返回 ``(规范化后的代码 或 None, 警告列表)``。

    规则：
      1. 去掉空白与常见分隔符（空格、`-`、`.`）；
      2. 形近字母 → 数字；
      3. 校验长度为 8、且全为数字。

    第 2 步是关键：**不需要合法代码清单**，纯字符映射即可纠正绝大多数 OCR 错字。
    """
    warnings: list[str] = []
    if raw is None:
        return None, ["物料代码为空"]

    cleaned = re.sub(r"[\s\-_.]", "", str(raw).strip())
    if not cleaned:
        return None, ["物料代码为空"]

    # 形近字母还原
    mapped = "".join(CONFUSABLE_TO_DIGIT.get(ch, ch) for ch in cleaned)
    if mapped != cleaned:
        warnings.append(f"已按形近字符纠正：{cleaned} → {mapped}")

    if not mapped.isdigit():
        leftover = sorted({ch for ch in mapped if not ch.isdigit()})
        warnings.append(f"纠错后仍含非数字字符 {leftover}，代码可能识别有误或取错字段")
        return None, warnings

    if len(mapped) != ITEM_CODE_LENGTH:
        warnings.append(
            f"代码长度为 {len(mapped)} 位，应为 {ITEM_CODE_LENGTH} 位（疑似漏字或多字）"
        )
        # 长度不符仍返回，交由人工判断——不因长度问题丢弃已有信息
        return mapped, warnings

    return mapped, warnings


# ---------------------------------------------------------------------------
# 批号
# ---------------------------------------------------------------------------

# 批号的三类结构（M3-R0 3.9，Owner 提供）：
#   1. 原料药 / 中间体：<生产线>-<年>-<月>-<流水号 3 位>
#   2. 混粉：          <生产线>-<两组份拼音首字母>-<年>-<月>-<流水号 3 位>
#   3. 亚批：          <主批号>-<序号>
#
# 注意：**不做硬性拦截**。仓库不负责批号管理，批号由车间给出，
# 格式只用于提示与低置信度标记（见模块 docstring）。

# 进厂批号（外购收货批）在实测数据中为 10 位纯数字
SUPPLIER_RECEIPT_BATCH_LEN = 10

_BATCH_YEAR_MONTH = re.compile(r"(\d{2})(\d{2})")  # 形如 2609 = 26 年 09 月


def check_batch_no(raw: Optional[str], source_type: Optional[str] = None) -> tuple[Optional[str], list[str]]:
    """校验批号结构，返回 ``(规范化批号, 提示列表)``。

    只在**明确可疑**时给出提示，不因格式不符阻断流程。
    """
    hints: list[str] = []
    if raw is None or not str(raw).strip():
        return None, ["批号为空"]

    original = str(raw)
    batch = original.strip().replace(" ", "")
    if batch != original:
        hints.append("批号含空白字符，已去除")

    # 进厂批号：外购场景下的 10 位纯数字，属正常，直接通过
    if source_type == "外购" and batch.isdigit() and len(batch) == SUPPLIER_RECEIPT_BATCH_LEN:
        return batch, hints

    # 亚批：形如主批号-1 / -2 / -3
    if re.fullmatch(r".+-\d{1,2}", batch):
        hints.append("识别为亚批次（主批号 + 序号），请核对与主批号一致")
        return batch, hints

    # 其余结构：要求"含年月 + 以 3 位流水号结尾"
    if not _BATCH_YEAR_MONTH.search(batch):
        hints.append("批号中未见形如「年月」的两位年份+两位月份，请人工核对")

    if not re.search(r"\d{3}$", batch):
        hints.append("批号末尾不是 3 位流水号，请人工核对")

    if not re.match(r"[A-Za-z]", batch):
        hints.append("批号未以生产线字母开头（原料药/中间体与混粉通常以字母开头）")

    return batch, hints


def check_numeric_batch_for_item_code(batch: str) -> bool:
    """辅助判断：批号是否为纯数字。

    用于**区分批号与物料代码**——物料代码全为数字，而批号通常含生产线字母。
    若两者都是纯数字，则提示人工确认是否取错了字段。
    """
    return bool(batch) and batch.isdigit()


# ---------------------------------------------------------------------------
# 日期
# ---------------------------------------------------------------------------

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y%m%d",
    "%y.%m.%d",
    "%y-%m-%d",
    "%y%m%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
)

_CN_DATE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?")


def parse_date(raw: Optional[str]) -> tuple[Optional[str], list[str]]:
    """把识别到的日期规范化为 ``YYYY-MM-DD``。

    标签上的日期写法多样（`2026.09.14` / `2026-09-14` / `2026年09月14日` /
    `20260914` / `26.09.14`）。本函数逐一尝试，全部失败则返回 None 并提示人工填写。
    """
    hints: list[str] = []
    if raw is None or not str(raw).strip():
        return None, []  # 生产日期 / 有效期本就可缺，静默返回

    text = str(raw).strip()

    # 中文年月日
    m = _CN_DATE.search(text)
    if m:
        y, mo, d = (int(m.group(i)) for i in (1, 2, 3))
        try:
            return datetime.date(y, mo, d).isoformat(), hints
        except ValueError:
            hints.append(f"日期数值非法：{text}")
            return None, hints

    # 去掉常见分隔符后按多种格式尝试
    compact = re.sub(r"[\s]", "", text)
    for fmt in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(compact, fmt).date().isoformat(), hints
        except ValueError:
            continue

    hints.append(f"无法解析日期「{text}」，请人工填写")
    return None, hints


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------


@dataclass
class FieldReport:
    """单个字段的校验结论。"""

    raw: Optional[str] = None
    value: Optional[str] = None
    hints: list[str] = field(default_factory=list)

    @property
    def corrected(self) -> bool:
        """是否发生了规范化（说明原始识别结果与最终值不同）。"""
        return self.raw is not None and self.value is not None and str(self.raw).strip() != self.value

    @property
    def ok(self) -> bool:
        """是否可直接采用（有值且无提示）。"""
        return bool(self.value) and not self.hints


@dataclass
class ValidationReport:
    """一张标签的整体验证结论。"""

    product_name: FieldReport
    item_code: FieldReport
    batch_no: FieldReport
    manufacturing_date: FieldReport
    expiry_date: FieldReport

    def as_dict(self) -> dict:
        return {
            "product_name": self.product_name.value,
            "item_code": self.item_code.value,
            "batch_no": self.batch_no.value,
            "manufacturing_date": self.manufacturing_date.value,
            "expiry_date": self.expiry_date.value,
        }

    def hints(self) -> dict:
        """按字段返回提示，供界面高亮。"""
        out = {}
        for name in ("product_name", "item_code", "batch_no", "manufacturing_date", "expiry_date"):
            rep: FieldReport = getattr(self, name)
            if rep.hints:
                out[name] = rep.hints
        return out

    def needs_review(self) -> bool:
        """是否必须人工复核（任一字段有提示即需要）。"""
        return bool(self.hints())


def validate_fields(fields: dict, source_type: Optional[str] = None) -> ValidationReport:
    """对识别结果做整体验证。

    ``fields`` 为后端返回的原始字段字典（键名见 ``app.contract``）。
    """
    name_raw = fields.get("product_name")
    name = (str(name_raw).strip() or None) if name_raw is not None else None
    name_hints = [] if name else ["产品名称未识别到"]

    code, code_hints = normalize_item_code(fields.get("item_code"))
    batch, batch_hints = check_batch_no(fields.get("batch_no"), source_type)
    mfg, mfg_hints = parse_date(fields.get("manufacturing_date"))
    exp, exp_hints = parse_date(fields.get("expiry_date"))

    # 批号若为纯数字且已识别到物料代码，提示可能取错字段
    if batch and check_numeric_batch_for_item_code(batch) and code:
        batch_hints.append("批号为纯数字，请确认未与物料代码混淆")

    # 有效期早于生产日期属明显异常
    if mfg and exp and exp < mfg:
        exp_hints.append(f"有效期（{exp}）早于生产日期（{mfg}），请人工核对")

    return ValidationReport(
        product_name=FieldReport(raw=name_raw, value=name, hints=name_hints),
        item_code=FieldReport(raw=fields.get("item_code"), value=code, hints=code_hints),
        batch_no=FieldReport(raw=fields.get("batch_no"), value=batch, hints=batch_hints),
        manufacturing_date=FieldReport(raw=fields.get("manufacturing_date"), value=mfg, hints=mfg_hints),
        expiry_date=FieldReport(raw=fields.get("expiry_date"), value=exp, hints=exp_hints),
    )
