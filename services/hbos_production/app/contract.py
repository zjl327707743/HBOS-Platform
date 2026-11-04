"""生产看板的数据契约与**口径实现**。

本模块**不依赖 FastAPI、不依赖飞书**，是纯函数 —— 便于离线单测。
取数服务（`main.py`）只负责「把飞书数据取回来交给这里算」。

口径来源（**全部经 Owner 确认，2026-10-02**）：

    数据源      7 张 产量明细数据-*（二/三/四/五/六车间、粗品、无菌）
    目标        月度生产计划明细 1–31 日求和
    完成/收率    按「收料日期」落月
    目标收率     月度目标产能.目标收率（合并行按计划批数加权）
    排除        欧盟线 / 混粉 / 晶种 / USP / 碳酸氢钠 / 比阿培南
    不录        四车间（B5·A7·B6·CDCA）
    合并        F13 = 国内规范粗品 + 粗品B + 粗品C
                无菌美罗培南 = 美罗培南B + 美罗培南 + （FDA）+ 精粗品D + 精粗品EP
                无菌亚胺培南 = 亚胺培南-乙醇 + -甲醇 + （CEP）
    暂不列      六车间 亚胺培南粗品-甲醇 / -乙醇
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# 行定义（与前端 `src/data/productionNav.ts` 的 PRODUCTION_ROWS 保持一致）
# ---------------------------------------------------------------------------
#
# ⚠️ 两处必须逐字一致，否则前端按 label 对不上行。
#    前端那份是渲染用，这份是聚合用 —— 改一处必须改另一处。

ROW_MEMBERS: dict[str, list[str]] = {
    "4BMA": ["4BMA"],
    "F9": ["F9"],
    "F12": ["F12"],
    "F13": ["国内规范粗品", "美罗培南粗品B", "美罗培南粗品C"],
    "无菌美罗培南": ["美罗培南B", "美罗培南", "美罗培南（FDA）", "美罗培南精粗品D", "美罗培南精粗品EP"],
    "无菌亚胺培南": ["亚胺培南-乙醇", "亚胺培南-甲醇", "亚胺培南（CEP）"],
}

#: 表名 → 表 ID。7 张产量明细，按车间分。
DETAIL_TABLES: dict[str, str] = {
    "二车间": "tblPvD1GfXmQbXh8",
    "三车间": "tbloTGF3VpwELBYt",
    "四车间": "tblUx6saofgbUESV",
    "五车间": "tblt03Eqt6YVe6Y3",
    "六车间": "tblK3pT2dhEFatRb",
    "粗品": "tbltTtWAYMfCAm0f",
    "无菌": "tblMd9p9atCqnpHg",
}

#: 目标与目标收率两张表。
PLAN_TABLE = "tbl5gFQjK33y24en"      # 月度生产计划明细（1–31 日宽表）
TARGET_TABLE = "tblzNpwsuc9ZD2Bk"    # 月度目标产能（含 目标收率）

#: Base token。
BASE_OPERATIONS = "NGSdbumUGa8oWQsT5E9cwviWn0c"   # 营运数据（明细 + 计划 + 目标）
BASE_AI = "Dl45bIEEya78fWsL4DXcwuJtn8c"           # AI 分析结果
AI_TABLE = "tblXD7oAwbU8U040"

#: 排除规则（会议 2026-10-02）。
EXCLUDE_KEYWORDS = ("欧盟", "混粉", "晶种", "USP")
EXCLUDE_EXACT = ("碳酸氢钠", "碳酸钠（EP）", "比阿培南")


# ---------------------------------------------------------------------------
# 异常闭环率
# ---------------------------------------------------------------------------
#
# 会议（2026-10-02）：「以各车间日报中的异常事件信息为唯一数据源，
# 仅统计已填报的事件原因相关内容。」
#
# 但各车间的表是**各自独立的 Base**（车间自己维护），字段并不完全一致 ——
# 见下面每个源的 `closure_field` 与 `date_field`。
#
# 取数窗口（Owner 2026-10-08 定）：**滚动 12 个自然月**。
# 不按当月 —— 异常是稀疏事件，二车间月均 3 条、三车间月均 1 条，
# 按当月取分母经常是 0 或 1，比率会在 0%/100%/无值之间跳，没有信息量。
# 也不按全部历史 —— 各车间表的起始时间不齐（二车间 2025-11 起、
# 三车间 2026-01 起），且一年前的异常不该影响今天的判断。

ANOMALY_WINDOW_MONTHS = 12


@dataclass
class AnomalySource:
    """一个车间的异常表。

    各车间的字段名不一样，所以逐源配置 —— 加新车间只需在 `ANOMALY_SOURCES` 里加一项。
    """

    name: str              # 车间名（展示用）
    base_token: str
    table_id: str
    content_field: str     # 「这条是不是有效记录」的判据（非空才算一条）
    date_field: str        # 日期字段（可能为空 —— 见 `resolve_anomaly_date`）
    closure_field: str     # 该字段非空 = 已闭环
    closure_label: str     # 闭环口径名（展示用）


#: 已收集到的车间异常表。
#:
#: 闭环判据**全车间统一 = `事件原因` 非空**（Owner 2026-10-08）。
#: 无菌那张表虽有整套 CAPA 字段（`CAPA完成时间` 等），但为保持跨车间可比，
#: 不用它 —— 各车间判据不同会让合计数失去意义。
#:
#: `closure_label` 保留在配置里：换判据时不用改算法，也便于页面上标注口径。
ANOMALY_SOURCES: list[AnomalySource] = [
    AnomalySource(
        name="二车间",
        base_token="EYI1b7bvKaQPo2sR2jMcbOxKnmd",
        table_id="tbltnGNSmFkPmMqy",
        content_field="事件内容",
        date_field="发生时间",
        closure_field="事件原因",
        closure_label="事件原因",
    ),
    AnomalySource(
        name="三车间",
        base_token="D3GCbGh7mawzPnslT71chJfInAc",
        table_id="tblXqmQkrZ53ct1C",
        content_field="事件内容",
        date_field="发生时间",
        closure_field="事件原因",
        closure_label="事件原因",
    ),
    AnomalySource(
        name="六车间",
        base_token="QHifbyzqtaJ74Xs9lVMcpDv7nce",
        table_id="tblM5t0mwRJswGdc",
        content_field="事件内容",
        date_field="发生时间",
        closure_field="事件原因",
        closure_label="事件原因",
    ),
    AnomalySource(
        name="无菌车间",
        base_token="D98VbrCWXaHSo9sKrICc54iwnLh",
        table_id="tblBlBaex5F6ksWE",
        content_field="异常事件内容",
        date_field="发生时间",
        closure_field="事件原因",
        closure_label="事件原因",
    ),
]

#: 六车间那张表**存在但是空的**（10 行全 null），其日报写「未发生」。
#: 按 Owner 2026-10-08：空表 + 日报「未发生」= **该车间没有异常事件**，
#: 贡献 0 条，不参与比率（不是 0% 闭环）。


def anomaly_window_start(today: date, months: int = ANOMALY_WINDOW_MONTHS) -> str:
    """近 N 个自然月的起点（含当月），返回 `YYYY-MM-01`。

    `2026-10` + 12 个月 → `2025-11-01`。
    """
    y, m = today.year, today.month
    m -= months - 1
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}-01"


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "".join(str(x) for x in value).strip()
    return str(value).strip()


_DATE_IN_TEXT = re.compile(r"\s*(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})")


def resolve_anomaly_date(record: dict, src: "AnomalySource") -> Optional[str]:
    """解析一条异常的发生日期，返回 `YYYY-MM-DD`；三处都取不到返回 None。

    三级兜底 —— 实测无菌车间那张表 **32 条里只有 10 条填了 `发生时间`**，
    另外 22 条的日期写在 `异常事件内容` 开头（`2026.03.13 12:23 …`）：

        ① `发生时间` 字段
        ② 从 `异常事件内容` 文本开头解析 `YYYY.MM.DD`
        ③ `调查完成时间` 字段（近似 —— 调查通常在发生后几天，可接受）

    不兜的话那 22 条会因「没有日期」被 12 个月窗口排除，
    无菌的闭环率就只按 10 条算 —— 那是错的。
    """
    # ⚠️ 飞书 API 直接返回时，datetime 字段是**毫秒时间戳（int）**；
    #    经 lark-cli 看到的却是 ISO 字符串 —— 同一字段两种形态。
    #    早先只按字符串处理，`str(1759248000000)[:10]` = "1759248000"，
    #    跟 "2025-11-01" 一比（'1' < '2'）**全都判成窗口外**，整个车间静默变 0 条。
    raw = record.get(src.date_field)
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(raw / 1000, tz=_CN_TZ).strftime("%Y-%m-%d")
        except (OSError, ValueError, OverflowError):
            pass
    v = _as_text(raw)
    if v:
        return v[:10]

    m = _DATE_IN_TEXT.match(_as_text(record.get(src.content_field)))
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    v = _as_text(record.get("调查完成时间"))
    if v:
        return v[:10]
    return None


@dataclass
class AnomalyStats:
    """一个车间的异常闭环统计（**窗口内**）。"""

    name: str
    closure_label: str
    total: int
    closed: int
    undated: int = 0     # 无法解析日期、未纳入窗口的条数（如实报出，不藏）

    @property
    def rate(self) -> Optional[float]:
        """**无有效记录返回 None**（不是 0）—— 「没有异常」和「0% 闭环」是两回事。"""
        return self.closed / self.total if self.total else None


def anomaly_stats(
    src: "AnomalySource", records: Iterable[dict], start: str
) -> AnomalyStats:
    """按窗口统计一个车间。

    `records` 是**平铺**的字段 dict（不是 `{"fields": …}`）。
    窗口 = `resolve_anomaly_date(r) >= start`（`YYYY-MM-DD` 字符串比较即可）。
    """
    total = closed = undated = 0
    for r in records:
        if not _as_text(r.get(src.content_field)):
            continue  # 全空占位行（实测六车间 10 行全空、三车间有 1 行空）
        d = resolve_anomaly_date(r, src)
        if not d:
            undated += 1
            continue
        if d < start:
            continue
        total += 1
        if _as_text(r.get(src.closure_field)):
            closed += 1
    return AnomalyStats(
        name=src.name,
        closure_label=src.closure_label,
        total=total,
        closed=closed,
        undated=undated,
    )


def overall_closure(stats: list[AnomalyStats], start: str, months: int) -> dict:
    """全厂汇总 —— **合计后再算率**，不是各车间率的平均。

    两者差别很大：二车间 9/31（29%）、三车间 8/9（89%），
    平均 = 59%，合计 = 17/40 = 42.5%。看板用合计（那是「全厂还剩多少没闭环」）。
    """
    total = sum(s.total for s in stats)
    closed = sum(s.closed for s in stats)
    active = [s for s in stats if s.total]
    return {
        "windowMonths": months,
        "windowStart": start,
        "total": total,
        "closed": closed,
        "rate": (closed / total) if total else None,
        "workshops": [s.name for s in stats],
        # 有记录、真正参与计算的车间；其余是「表在但窗口内无异常」
        "activeWorkshops": [s.name for s in active],
        "byWorkshop": [
            {
                "name": s.name,
                "closureLabel": s.closure_label,
                "total": s.total,
                "closed": s.closed,
                "rate": s.rate,
                "undated": s.undated,
            }
            for s in stats
        ],
    }


@dataclass
class ProductionRow:
    label: str
    done: int
    target: int
    yieldRate: Optional[float]      # 本月实际收率（按收料日期）
    targetYieldRate: Optional[float]  # 目标收率（合并行加权）
    yesterdayInbound: Optional[float]  # 昨日入库量 kg


# ---------------------------------------------------------------------------
# 日期解析
# ---------------------------------------------------------------------------

#: 飞书日期按**北京时间**解释。
#:
#: ⚠️ 这里踩过一个坑：飞书的 datetime 字段返回的是**当地午夜**的毫秒时间戳。
#:    例如「2025-10-01」→ 1759248000000，用 `utcfromtimestamp` 会得到
#:    2025-09-30 16:00 UTC，**格式化成前一天** —— 每一天都少一天，
#:    跨月批次会被算进上一个月（本看板正是按日期落月的，后果直接）。
#:    故固定用 UTC+8 解释（部署目标是国内，不引 tzdata 依赖）。
_CN_TZ = timezone(timedelta(hours=8))


def parse_month_day(value) -> Optional[str]:
    """把飞书日期字段解析成 `YYYY-MM-DD`。

    飞书日期可能是 **毫秒时间戳（int）** 或 **字符串**，字符串还有多种写法
    （`2026-10-01`、`2026.10.01`、`2026/10/01`）。实测各表混用，
    故这里统一兜住；解析不出来就返回 None（**不猜**）。
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, tz=_CN_TZ).strftime("%Y-%m-%d")
        except (OSError, ValueError, OverflowError):
            return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(s[: len(fmt) + 4], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def month_of(day: str) -> str:
    """`2026-10-01` → `2026-10`。"""
    return day[:7]


# ---------------------------------------------------------------------------
# 计划 / 目标
# ---------------------------------------------------------------------------

def plan_batches(plan_row: dict) -> int:
    """`月度生产计划明细` 的一行 → 1–31 日求和。

    该表是**宽表**：`1日`…`31日` 各一列。缺列按 0 计（不报错）。
    """
    total = 0
    for d in range(1, 32):
        v = plan_row.get(f"{d}日")
        if v in (None, "", "/"):
            continue
        try:
            total += int(float(str(v).strip()))
        except (TypeError, ValueError):
            continue
    return total


def weighted_target_yield(
    member_targets: dict[str, int], member_yields: dict[str, float]
) -> Optional[float]:
    """合并行的目标收率 —— 按**计划批数加权**（Owner 2026-10-02 定）。

    map 里没有的成员跳过；全无收率数据返回 None（**不补默认值**）。
    """
    num = 0.0
    den = 0
    for name, y in member_yields.items():
        w = member_targets.get(name, 0)
        num += w * y
        den += w
    if den == 0:
        return None
    return num / den


# ---------------------------------------------------------------------------
# 明细聚合
# ---------------------------------------------------------------------------

@dataclass
class DetailRecord:
    """`产量明细数据-*` 的一行（只取用得到的字段）。"""
    product: str
    batch: str
    received_on: Optional[str]   # 收料日期 YYYY-MM-DD
    yield_rate: Optional[float]


@dataclass
class DetailRecordWithQty(DetailRecord):
    """带产量的明细行（昨日入库量需要）。"""
    qty: Optional[float] = None


def aggregate_month(
    records: Iterable[DetailRecord], month: str
) -> dict[str, tuple[int, list[float]]]:
    """按**收料日期**落月聚合：`{产品: (批数, [收率…])}`。

    会议 2026-10-02：完成与收率都按收料日期落月（既有 openclaw 用投料日期，本次改）。
    """
    out: dict[str, list] = {}
    for r in records:
        if not r.received_on or month_of(r.received_on) != month:
            continue
        slot = out.setdefault(r.product, [0, []])
        slot[0] += 1
        if r.yield_rate is not None:
            slot[1].append(r.yield_rate)
    return {k: (v[0], v[1]) for k, v in out.items()}


def aggregate_day_qty(
    records: Iterable[DetailRecordWithQty], day: str
) -> dict[str, float]:
    """按收料日期求某天的产量合计：`{产品: kg}`（昨日入库量用）。

    会议 2026-10-02：管理人员看板的「昨日入库量」= 前一日收料日期对应的产量求和。
    """
    out: dict[str, float] = {}
    for r in records:
        if not r.received_on or r.received_on != day:
            continue
        if r.qty is None:
            continue
        out[r.product] = out.get(r.product, 0.0) + r.qty
    return out


def is_excluded(product: str) -> bool:
    """会议排除规则。四车间的不靠产品名排（那是车间维度），此处只排产品名。"""
    if product in EXCLUDE_EXACT:
        return True
    return any(k in product.upper() for k in EXCLUDE_KEYWORDS)


# ---------------------------------------------------------------------------
# 组装
# ---------------------------------------------------------------------------

def build_rows(
    *,
    month: str,
    yesterday: str,
    details: list[DetailRecordWithQty],
    members_excluded: set[str],
    plan_by_product: dict[str, int],
    yield_by_product: dict[str, float],
) -> list[ProductionRow]:
    """把上游数据组装成看板行。

    `members_excluded` 是「车间维度排除」的结果（四车间那批）——
    由调用方按明细所在表判断，因为「哪个产品属四车间」是车间口径，不是产品名属性。
    """
    month_agg = aggregate_month(details, month)
    day_agg = aggregate_day_qty(details, yesterday)

    rows: list[ProductionRow] = []
    for label, members in ROW_MEMBERS.items():
        # 暂不列的成员（六车间 亚胺培南粗品-甲醇/乙醇）不在任何一行的 members 里，
        # 天然不会被计入 —— 这里不需要额外过滤。
        effective = [m for m in members if m not in members_excluded]

        done = sum(month_agg.get(m, (0, []))[0] for m in effective)
        target = sum(plan_by_product.get(m, 0) for m in effective)

        yields: list[float] = []
        for m in effective:
            yields.extend(month_agg.get(m, (0, []))[1])
        rate = sum(yields) / len(yields) if yields else None

        tgt_yield = weighted_target_yield(
            {m: plan_by_product.get(m, 0) for m in effective},
            {m: yield_by_product[m] for m in effective if m in yield_by_product},
        )

        inbound = sum(day_agg.get(m, 0.0) for m in effective)

        rows.append(
            ProductionRow(
                label=label,
                done=done,
                target=target,
                yieldRate=rate,
                targetYieldRate=tgt_yield,
                yesterdayInbound=inbound if day_agg else None,
            )
        )
    return rows


def asdict_row(row: ProductionRow) -> dict:
    """`ProductionRow` → 可直接 JSON 序列化的 dict（键名与前端 TS 接口一致）。"""
    return asdict(row)


def days_elapsed(month: str, today: date) -> int:
    """本月已过天数（月初基准提示用）。非当月返回该月总天数或 0。

    `today` 由调用方传入 —— 本模块不做「现在几点」的判断，便于测试。
    """
    if month != today.strftime("%Y-%m"):
        return 0
    return today.day


def fingerprint(*parts: str) -> str:
    """数据指纹（幂等用）。见 AI 规格 §3.2 —— 既有项目缺这一步，导致同一格被追加 64 次。"""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:32]
