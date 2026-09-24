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
import calendar
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

# **行首**的生产线字母 + 两位年 + 两位月。比上面那个宽松版多了锚定，
# 用于「批号定年月」这条强约束——必须从开头取，否则流水号里的数字会被误当成年月。
_BATCH_PREFIX_YYMM = re.compile(r"^[A-Za-z]+(\d{2})(\d{2})")


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


def batch_year_month(batch: Optional[str]) -> Optional[tuple[int, int]]:
    """从批号里取「年、月」，取不到返回 None。

    **为什么批号能定年月**：三类批号结构（M3-R0 Owner 确认）都以
    ``生产线字母 + 两位年 + 两位月 + 流水号`` 开头——

        原料药 / 中间体   ``B``   + ``2506`` + ``402``   → B2506402
        混粉               ``BMT`` + ``2609`` + ``119``   → BMT2609119

    实测 **50/50 张真实样本**的批号年月与生产日期的年、月完全一致。
    因此这是一条**不依赖主数据**的强约束。
    """
    if not batch:
        return None
    m = _BATCH_PREFIX_YYMM.match(str(batch).strip())
    if not m:
        return None
    yy, mm = int(m.group(1)), int(m.group(2))
    if not 1 <= mm <= 12:
        return None
    return 2000 + yy, mm


def align_manufacturing_date(
    mfg: Optional[str], batch: Optional[str]
) -> tuple[Optional[str], list[str]]:
    """用批号里的年月**纠正生产日期的年与月**。

    OCR 把年份读错一位是常见错误（实测出现过 ``2026`` 读成 ``2016``——
    2 与 1 只差一横）。批号是车间给的、且 50/50 与生产日期吻合，
    所以拿它来定年、月比让模型自己读更可靠。

    **只改年与月，不动「日」**——批号里没有日。日错了改不了，只能靠人工。
    """
    if not mfg or not batch:
        return mfg, []
    yymm = batch_year_month(batch)
    if not yymm:
        return mfg, []

    y, mo = yymm
    try:
        d = datetime.date.fromisoformat(mfg)
    except (ValueError, TypeError):
        return mfg, []

    if d.year == y and d.month == mo:
        return mfg, []

    fixed = datetime.date(y, mo, min(d.day, calendar.monthrange(y, mo)[1])).isoformat()
    return fixed, [
        f"生产日期的年月与批号不一致（识别为 {d.year}年{d.month}月，批号指示 {y}年{mo}月），"
        f"已按批号纠正为 {fixed}；「日」批号里没有，请照标签核对"
    ]


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

# **只到月**的日期。实测真实标签里有 34/50 张的有效期只印到月
# （如「2028年11月」「2028.11」），日根本没有印。
# 这是标签的印刷惯例，不是识别错误——若不支持，三分之二的有效期会被丢掉。
_CN_MONTH = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?!\s*\d)")
_NUM_MONTH = re.compile(r"^\s*(\d{4})[.\-/](\d{1,2})\s*$")

# 只读到年月时的提示语。
#
# 措辞有讲究：说的是「**识别只读到**年月」，不是「**标签只印**到月」。
# 我们只知道模型读到了什么，不知道标签上印了什么——两者会不一致：
# 实测有标签印的是「2026年9月7日」，而模型只读出了「2026年09月」，
# 此时说"标签只印到月"就是**对着人撒谎**，会让人以为标签上真没有日。
_MONTH_ONLY_HINT = (
    "识别只读到了年月（{shown}），已按**月末**推定日；"
    "若标签上其实印了日，请按标签填写"
)


def _month_end(year: int, month: int) -> str:
    """把「只到月」的日期补成该月**最后一天**。

    「有效期至 2028年11月」的通行读法是"到 11 月底"，取月末比取月初更贴近原意：
    取月初会把效期提前一个月，可能在还能用的时候就被预警拦下。

    本项目的标签上，**有效期有三分之二只印到月**，所以这条不是边角情况。
    """
    return datetime.date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def _date_is_grounded(iso: str, raw_text: str, *, month_only: bool = False) -> bool:
    """该日期能否在识别原文里找到出处。

    不变量：**识别出的日期，其数字必须真的出现在识别原文里。** 找不到出处的，
    就是模型（或本层逻辑）无中生有的，不该进台账。

    实测覆盖情况（50 张真实标签）：**一处都没拦到**。逐张核对后确认，
    这批数据的日期错误是另外两种：

      1. **漏读**——标签印「2026年9月7日」，模型只读出「2026年09月」，
         于是本层的月末推定替它补了个 30。原文里没有 30，但**这不是编造**，
         是我们按规则补的（见 ``_MONTH_ONLY_HINT``，提示语已改成"识别只读到年月"）。
      2. **取错**——标签上有多个日期，模型挑了另一个（如把登记号里的
         ``2020.11.07`` 当成了生产日期）。这个日期**确实在原文里**，本层拦不住。

    所以这道校验在当前数据上是**保险，不是修复**。留着的理由：
    后端可插拔，而 C1（本地量化 VLM）是计划内的——**VLM 的典型失效模式正是
    凭空生成一个格式合法、原文里却没有的日期**。那时这道校验就有用了。

    宁可留空让人补，也不要让编出来的日期进系统。
    """
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except (ValueError, AttributeError):
        return False

    digits = re.sub(r"\D", "", raw_text)  # 原文去掉一切非数字

    def present(*parts: int) -> bool:
        """这几个数字是否按顺序、可跨分隔符地出现在原文里。

        月份与日允许原文写成 1 位（如 `2026年9月7日`）。
        """
        pat = r"\D*".join(str(p) for p in parts)
        alt = r"\D*".join(f"0?{p}" if p < 10 else str(p) for p in parts)
        return bool(re.search(pat, digits) or re.search(alt, digits))

    if month_only:
        # 模型只读到年月，日是本层按月末补的——只要求年月对得上
        return present(y, m)

    return present(y, m, d)


def parse_date(
    raw: Optional[str],
    *,
    raw_text: Optional[str] = None,
) -> tuple[Optional[str], list[str]]:
    """把识别到的日期规范化为 ``YYYY-MM-DD``。

    标签上的日期写法多样（`2026.09.14` / `2026-09-14` / `2026年09月14日` /
    `20260914` / `26.09.14`），**且粒度不一**——不少标签只印到月。
    逐一尝试，全部失败则返回 None 并提示人工填写。

    只到月的日期会补成**当月最后一天**，并给出提示说明「日是按月末推定的」——
    不能让人误以为标签上真印了那一天。

    ``raw_text`` 给出时，解析结果还要过一道**溯源校验**（见 ``_date_is_grounded``）：
    找不到出处的日期判为不可信、留空。这是防轻量模型编造日期的护栏。
    """
    hints: list[str] = []
    if raw is None or not str(raw).strip():
        return None, []  # 生产日期 / 有效期本就可缺，静默返回

    text = str(raw).strip()

    def finish(iso: Optional[str], extra: list[str] | None = None, *, month_only: bool = False):
        """统一出口：过溯源校验，再决定要不要保留这个日期。"""
        out_hints = hints + (extra or [])
        if iso and raw_text is not None and not _date_is_grounded(iso, raw_text, month_only=month_only):
            out_hints = [h for h in out_hints if "只印到月" not in h]
            out_hints.append(
                f"识别到的日期「{iso}」在标签原文中找不到对应数字，判定为不可信，已清空请人工填写"
            )
            return None, out_hints
        return iso, out_hints

    # 中文年月日
    m = _CN_DATE.search(text)
    if m:
        y, mo, d = (int(m.group(i)) for i in (1, 2, 3))
        try:
            return finish(datetime.date(y, mo, d).isoformat())
        except ValueError:
            hints.append(f"日期数值非法：{text}")
            return None, hints

    # 中文只到月
    m = _CN_MONTH.search(text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            note = [_MONTH_ONLY_HINT.format(shown=f"{y}年{mo}月")]
            return finish(_month_end(y, mo), note, month_only=True)

    # 数字只到月（2028.11 / 2028-11）
    m = _NUM_MONTH.match(text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            note = [_MONTH_ONLY_HINT.format(shown=f"{y}.{mo}")]
            return finish(_month_end(y, mo), note, month_only=True)

    # 去掉常见分隔符后按多种格式尝试
    compact = re.sub(r"[\s]", "", text)
    for fmt in DATE_FORMATS:
        try:
            return finish(datetime.datetime.strptime(compact, fmt).date().isoformat())
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


def validate_fields(
    fields: dict,
    source_type: Optional[str] = None,
    raw_text: Optional[str] = None,
) -> ValidationReport:
    """对识别结果做整体验证。

    ``fields`` 为后端返回的原始字段字典（键名见 ``app.contract``）。

    ``raw_text`` 是识别原文（``BackendResult.raw_text``）。给出时，日期会多过一道
    **溯源校验**——找不到出处的日期判为不可信并清空，防轻量模型编造合法日期。
    """
    name_raw = fields.get("product_name")
    name = (str(name_raw).strip() or None) if name_raw is not None else None
    name_hints = [] if name else ["产品名称未识别到"]

    code, code_hints = normalize_item_code(fields.get("item_code"))
    batch, batch_hints = check_batch_no(fields.get("batch_no"), source_type)
    mfg, mfg_hints = parse_date(fields.get("manufacturing_date"), raw_text=raw_text)
    exp, exp_hints = parse_date(fields.get("expiry_date"), raw_text=raw_text)

    # 批号若为纯数字且已识别到物料代码，提示可能取错字段
    if batch and check_numeric_batch_for_item_code(batch) and code:
        batch_hints.append("批号为纯数字，请确认未与物料代码混淆")

    # 用批号里的年月纠正生产日期（OCR 读错年份是常见错误）
    mfg, align_hints = align_manufacturing_date(mfg, batch)
    mfg_hints.extend(align_hints)

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
