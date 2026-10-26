"""参数与收率的统计 —— **纯函数**，先在 Python 里算好，再给模型解读。

## 为什么不在提示词里让模型自己算

模型看到的是「最近 30 批的原始台账」，它**不会**去算相关系数 ——
实测 62 条输出里只有 6 条给了具体动作建议，其余都是「台账缺数据」。
要它做统计，必须把统计结果**算好喂进去**，让它专注于「这些数字对工艺意味着什么」。

## 算什么（每条都能指到数据，不是猜的）

    Spearman 秩相关  参数值与收率的单调关系。用秩相关不用 Pearson ——
                     台账里有离群值（批号当数字、单位混填），Pearson 会被拉偏。
    高低组对比       收率最高 25% 与最低 25% 的批次，某参数的均值差多少。
                     相关只说明「一起变」，分组对比才看得出「往哪调」。
    月度趋势         各月平均收率与参数均值。看的是最近几个月在变好还是变差。
    字段填充率       某个参数有多少批填了。低于阈值的不参与分析 ——
                     3 批数据的「规律」不是规律。

## 什么不能算

**定义性字段必须排除**：`入库干重 / 混前重量 / 重量 / API下料量` 这些是收率的
分子或分母，与收率的相关系数必然是 ±0.9 以上 —— 那不是一个「发现」，
是同义反复。把它们当影响因素喂给模型，它会得出「增加干重能提高收率」
这种废话。见 `DEFINITIONAL_FIELDS`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from .sources import LedgerBatch

_CN_TZ = timezone(timedelta(hours=8))

#: 各产品的**收率字段**（分子/分母关系的源头）。
YIELD_FIELD: dict[str, str] = {
    "4BMA": "入库收率",
    "F9": "入库收率",
    "F12": "收率",
    "F13": "收率",
    "无菌美罗培南": "API收率",
    "无菌亚胺培南": "收率",
}

#: **不能当「影响因素」的字段** —— 它们是收率的分子或分母，或直接由收率派生。
#:
#: 不排除的后果：相关系数 0.94~1.00，模型会把「入库干重 ↑ 收率 ↑」当成发现写进报告，
#: 而那是定义本身，不是工艺结论。实测 4BMA 的 `入库干重` ρ=+0.94、
#: F13 的 `混前重量` ρ=+1.00、F12 的 `重量` ρ=+1.00 —— 全部是这一类。
DEFINITIONAL_FIELDS: dict[str, set[str]] = {
    "4BMA": {"入库干重", "粗品重量", "精品重量", "4AA使用重量", "入库收率"},
    "F9": {
        "F9干重", "F8.5重量", "二次晶体重量", "一次晶体", "入库收率",
        "产量完成值", "批次完成值", "F9批次完成值", "收率完成值",
    },
    "F12": {"重量", "收率"},
    "F13": {
        "混前重量", "投料重量", "收率", "收率完成值", "产量完成值",
        "批次完成值", "F13目标产量/kg", "F13入库目标收率",
    },
    "无菌美罗培南": {
        "API下料量", "下料量量|kg", "投料量（Kg)", "API分装重量（不含取样量）",
        "产量(kg)（包含取样量）", "API收率", "产量|请验重量",
    },
    "无菌亚胺培南": {"上传重量", "分装重量", "产量", "收率"},
}

#: 不是参数的字段：标识、日期、备注。
_NON_PARAM = {
    "SourceID", "record_id", "投料日期", "批号", "批次", "生产批号", "序号", "产品",
}

#: 字段名含这些词的，一律不当工艺参数。
#:
#: - **批号**：`混粉用Na2CO3批号` 是标识符。当数字算会得到 ρ=-0.230 这种
#:   伪关系（实测），而「换了个批号收率就变了」不是工艺结论。
#: - **人员**：F12 的 `浓缩终点判断`、无菌的 `API取样分样人员` / `-2结晶人员`
#:   填的都是人名。按人分组确实能算出「谁当班收率高」，但这条建议既不可执行、
#:   也变成对具体员工的评价 —— 不该出现在工艺改进报告里。
_BLOCKED_KEYWORDS = (
    "批号", "班组", "人员", "责任人", "操作人", "负责", "员工", "签名", "取样", "分样",
)

#: 空值占位 —— 分组时不能当成一个「取值」，否则会出现「`/` 组 88.77%」这种噪音。
_BLANK_VALUES = {"/", "-", "—", "无", "未检出", "N/A", "空"}


def _blocked(name: str) -> bool:
    return any(k in name for k in _BLOCKED_KEYWORDS)


#: 常见中文姓氏（前 60）。用来识别「字段名没写人是人、值全是人名」的情况 ——
#: F12 的 `浓缩终点判断` 就是这样：名字看着像工艺字段，填的却是操作工姓名。
_SURNAMES = set(
    "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘"
    "于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江"
    "尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
)


def _looks_like_person_names(values: set[str]) -> bool:
    """所有取值都像人名 → 这个字段是「谁做的」，不是工艺参数。

    判据：每个值 2~4 个汉字，且**首字都是常见姓氏**。要求「全部满足」而不是
    「大部分」—— `规格` 字段的 `非规/规范/试生产/欧盟` 里只有 `欧盟` 的 `欧`
    像姓氏，不全满足就保留。宁可漏判（保留一个人名字段），不要误杀真参数。
    """
    if not values:
        return False
    for v in values:
        if not (2 <= len(v) <= 4):
            return False
        if not all("一" <= ch <= "龥" for ch in v):
            return False
        if v[0] not in _SURNAMES:
            return False
    return True

#: 填了才可能有统计意义的最小批数。低于它只列「覆盖率」，不参与相关/分组。
MIN_SAMPLES = 30

#: 相关系数绝对值低于它视为「看不出关系」，不写进结论。
#: 0.25 是个务实的门槛 —— 台账噪声大，再低基本是巧合。
MIN_ABS_RHO = 0.25

#: 高低组对比的最小相对差异（20%）。低于它说明「高低收率批次这个参数差不多」。
MIN_GROUP_DELTA = 0.20

#: 唯一值 ≤ 这个数的参数，当**分类**处理（釜号 / 设备位号 / 档位），不当连续变量。
#: 把 `R622 / R632 / R645` 排序算相关是伪关系。
MAX_NUMERIC_CATEGORIES = 6

#: 分类变量分组的最大组数。太多说明是自由文本（备注），分不出有效对比。
MAX_CATEGORY_GROUPS = 12

#: 分类变量的每组最小批数 —— 少于它的组不参与对比（1 批的高收率不算发现）。
MIN_GROUP_SIZE = 5

#: 分类变量「值得报告」的组间极差门槛：相对最好组的比例。
#:
#: 0.3% 看着很低，但收率本身通常只有 1~2pt 的波动空间（F13 全月 49.5~50.6）。
#: 用绝对阈值会漏掉真实差异；用相对阈值才可比。实测 4BMA 的
#: 「釜号 R228 90.01% vs R229 89.98%」只差 0.03% —— 那是噪声，不该报。
MIN_GROUP_SPREAD = 0.003


def _num(value) -> Optional[float]:
    """台账值 → 数字。**转不了返回 None，不返回 0**。

    实测脏值：`'/'`（未检）、`'未检出'`、`'89.33%'`、`'12.4℃'`、空串。
    把 `'/'` 当 0 会让相关分析彻底错乱。
    """
    if value is None:
        return None
    s = str(value).strip().replace("%", "").replace("℃", "").replace("kg", "").strip()
    if not s or s in {"/", "-", "—", "无", "未检出", "N/A"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _month(value) -> Optional[str]:
    """日期值 → `YYYY-MM`；解析不了返回 None。

    ⚠️ 台账里的日期经 `sources._text()` 已经**转成字符串**了：毫秒时间戳会变成
    `'1792425600000'`。早先只判 `isinstance(value, int)`，于是把时间戳的前 7 位
    当成年月 —— 报告里出现 `1791561` 这种月份（实测踩到）。
    """
    if isinstance(value, (int, float)):
        ms = float(value)
    else:
        s = str(value or "").strip()
        if not s:
            return None
        # 纯数字串 = 毫秒时间戳（13 位）
        if s.isdigit() and len(s) >= 10:
            ms = float(s)
        else:
            # `2026-10-01` / `2026.10.01` / `2026/10/01` / `2026年10月01日`
            norm = s[:7].replace("/", "-").replace(".", "-")
            return norm if len(norm) == 7 else None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=_CN_TZ).strftime("%Y-%m")
    except (OSError, ValueError, OverflowError):
        return None


def _rank(values: Sequence[float]) -> list[float]:
    """秩（相同值取平均秩）。"""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Spearman 秩相关系数。

    用秩相关而不是 Pearson：台账里的离群值（批号被当数字、单位混填、千分位）
    会显著拉偏 Pearson。秩相关只看「谁大谁小」，对这些不敏感。
    """
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    rx, ry = _rank(list(xs)), _rank(list(ys))
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return cov / (dx * dy)


@dataclass
class CategoryEffect:
    """低基数参数（釜号、设备位号、厂家…）按取值分组的收率对比。

    这类字段**不该算相关** —— 把 `R622 / R632 / R645` 当成 622 < 632 < 645 排序
    没有物理意义。但按取值分组比收率很有价值：「R622 平均 89.8%，
    R645 平均 90.4%」是车间能立刻采取行动的信息（查那台釜）。
    """

    name: str
    groups: list[tuple[str, int, float]]   # (取值, 批数, 收率均值)，按收率降序

    @property
    def spread(self) -> Optional[float]:
        """组间收率极差（最高组 - 最低组）。"""
        if len(self.groups) < 2:
            return None
        return self.groups[0][2] - self.groups[-1][2]

    @property
    def worth_reporting(self) -> bool:
        s = self.spread
        best = max((g[2] for g in self.groups), default=0)
        if s is None or not best:
            return False
        return s / abs(best) >= MIN_GROUP_SPREAD


def _category_effect(
    name: str, pairs: Sequence[tuple[dict[str, str], float]]
) -> Optional[CategoryEffect]:
    """把一个字段按**取值**分组，比各组的收率均值。

    只对「低基数」字段有意义：釜号、设备位号、厂家、是否超温、液位状态…
    这类字段当连续变量算相关是伪关系（`R622 < R632 < R645` 没有物理含义），
    但「R645 那台釜平均收率高 0.6pt」是车间能立刻查的事。

    返回 None 表示这个字段分不出有效的组（自由文本、每组都太小）。
    """
    groups: dict[str, list[float]] = {}
    for values, y in pairs:
        raw = values.get(name)
        if raw is None:
            continue
        key = str(raw).strip()
        if not key or key in _BLANK_VALUES:
            # 空占位不能当成一个「取值」—— 否则报告里会出现
            # 「`/` 组 88.77%（170 批）」这种噪音，那组只是「没填」。
            continue
        groups.setdefault(key, []).append(y)

    if not 2 <= len(groups) <= MAX_CATEGORY_GROUPS:
        return None

    # 值是清一色的人名 → 「谁当班收率高」，不是工艺参数。这条建议既不可执行，
    # 又变成对具体员工的评价，不该进报告。
    if _looks_like_person_names(set(groups)):
        return None

    sized = [
        (k, len(v), sum(v) / len(v))
        for k, v in groups.items()
        if len(v) >= MIN_GROUP_SIZE
    ]
    if len(sized) < 2:
        return None
    sized.sort(key=lambda t: -t[2])
    return CategoryEffect(name=name, groups=sized)


@dataclass
class ParamEffect:
    """一个参数与收率的关系。"""

    name: str
    samples: int
    rho: Optional[float]          # 秩相关
    low_mean: Optional[float]     # 低收率组的均值
    high_mean: Optional[float]    # 高收率组的均值
    coverage: float               # 填充率 0~1

    @property
    def delta_ratio(self) -> Optional[float]:
        """高组相对低组的变化比例。"""
        if self.low_mean is None or self.high_mean is None or not self.low_mean:
            return None
        return (self.high_mean - self.low_mean) / abs(self.low_mean)

    @property
    def worth_reporting(self) -> bool:
        """值不值得写进报告：相关够强，或两组差得够多。"""
        if self.rho is not None and abs(self.rho) >= MIN_ABS_RHO:
            return True
        d = self.delta_ratio
        return d is not None and abs(d) >= MIN_GROUP_DELTA


@dataclass
class MonthPoint:
    month: str
    batches: int
    yield_mean: Optional[float]
    param_means: dict[str, float]

@dataclass
class LedgerStats:
    """一个产品的台账统计结果。"""

    product: str
    yield_field: str
    total_batches: int
    yield_batches: int
    yield_min: Optional[float]
    yield_max: Optional[float]
    yield_mean: Optional[float]
    effects: list[ParamEffect]
    months: list[MonthPoint]
    #: 有字段但样本太少，只能报覆盖率，不能分析
    sparse_fields: list[tuple[str, int]]
    #: 低基数参数（釜号等）的分组对比
    categories: list[CategoryEffect] = field(default_factory=list)

    @property
    def analyzable(self) -> bool:
        """有收率数据且有至少一个可用线索，才值得让模型解读。"""
        return (
            self.yield_batches >= MIN_SAMPLES
            and (bool(self.effects) or bool(self.categories))
        )


def analyze(
    product: str,
    ledger: Sequence[LedgerBatch],
    *,
    month_limit: int = 6,
) -> LedgerStats:
    """算某产品台账里「参数 ↔ 收率」的关系。

    `ledger` 是**最近 N 批**（调用方截断过的）。这里不再排序 ——
    上游 `fetch_ledger` 已按日期倒序。
    """
    yf = YIELD_FIELD.get(product, "收率")
    excluded = DEFINITIONAL_FIELDS.get(product, set()) | _NON_PARAM | {yf}

    pairs: list[tuple[dict[str, str], float]] = []
    months_raw: dict[str, list[tuple[dict[str, str], float]]] = {}
    for b in ledger:
        y = _num(b.values.get(yf))
        if y is None:
            continue
        pairs.append((b.values, y))
        m = _month(b.values.get("投料日期"))
        if m:
            months_raw.setdefault(m, []).append((b.values, y))

    yields = [y for _, y in pairs]

    # 收集所有可当参数的字段
    all_fields: set[str] = set()
    for values, _ in pairs:
        all_fields.update(values)

    effects: list[ParamEffect] = []
    sparse: list[tuple[str, int]] = []
    categories: list[CategoryEffect] = []
    for name in sorted(all_fields):
        if name in excluded or _blocked(name):
            continue
        series = [(_num(values.get(name)), y) for values, y in pairs]
        pts = [(x, y) for x, y in series if x is not None]
        if not pts:
            # 不是数字：可能是「釜号 R622」「液位正常」这类分类值 ——
            # 按取值分组看收率差异（这比把它们当数字排序有意义得多）
            cat = _category_effect(name, pairs)
            if cat is not None:
                categories.append(cat)
            continue
        coverage = len(pts) / len(pairs) if pairs else 0.0
        if len(pts) < MIN_SAMPLES:
            sparse.append((name, len(pts)))
            continue

        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]

        # **低基数**（唯一值 ≤ 6）：多半是位号/釜号/档位，当连续变量算相关没意义。
        # 改用分组对比。实测 4BMA 的「釜号」当数字算得 ρ=-0.254，看着像发现，
        # 实际是「R228 比 R516 编号小」这种巧合。
        if len(set(xs)) <= MAX_NUMERIC_CATEGORIES:
            cat = _category_effect(name, pairs)
            if cat is not None:
                categories.append(cat)
            continue

        rho = spearman(xs, ys)

        # 高低收率组：按收率排序取两端 25%
        ordered = sorted(pts, key=lambda t: t[1])
        q = max(3, len(ordered) // 4)
        low = ordered[:q]
        high = ordered[-q:]
        low_mean = sum(x for x, _ in low) / len(low)
        high_mean = sum(x for x, _ in high) / len(high)

        effects.append(
            ParamEffect(
                name=name,
                samples=len(pts),
                rho=rho,
                low_mean=low_mean,
                high_mean=high_mean,
                coverage=coverage,
            )
        )

    # 只留值得说的，按相关强度排序
    effects = [e for e in effects if e.worth_reporting]
    effects.sort(key=lambda e: -abs(e.rho or 0))
    categories = [c for c in categories if c.worth_reporting]
    categories.sort(key=lambda c: -(c.spread or 0))

    # 月度趋势
    months: list[MonthPoint] = []
    for m in sorted(months_raw)[-month_limit:]:
        rows = months_raw[m]
        ys = [y for _, y in rows]
        # 只统计参数集合里出现的（且非定义性的）
        pmeans: dict[str, float] = {}
        for e in effects:
            vals = [_num(v.get(e.name)) for v, _ in rows]
            vals = [x for x in vals if x is not None]
            if len(vals) >= 3:
                pmeans[e.name] = sum(vals) / len(vals)
        months.append(
            MonthPoint(
                month=m,
                batches=len(rows),
                yield_mean=sum(ys) / len(ys) if ys else None,
                param_means=pmeans,
            )
        )

    return LedgerStats(
        product=product,
        yield_field=yf,
        total_batches=len(ledger),
        yield_batches=len(pairs),
        yield_min=min(yields) if yields else None,
        yield_max=max(yields) if yields else None,
        yield_mean=sum(yields) / len(yields) if yields else None,
        effects=effects,
        months=months,
        sparse_fields=sorted(sparse, key=lambda t: -t[1])[:10],
        categories=categories,
    )


def _fmt(v: Optional[float], digits: int = 2) -> str:
    return "—" if v is None else f"{v:.{digits}f}"


def _norm_yield(values: list[float]) -> tuple[list[float], str]:
    """收率统一成百分数。

    实测各单位混用：4BMA/F9 存 `90.06`（已是百分数），F12 存 `1.48`（=148%），
    F13 存 `0.50`（=50%）。不归一的话「收率均值 0.50」在报告里会被读成 0.5%，
    而实际是 50% —— 这是个会被车间当场指出的错。

    判据：均值 < 3 视为比值，×100；否则视为已是百分数。
    """
    if not values:
        return values, ""
    mean = sum(values) / len(values)
    if mean < 3:
        return [v * 100 for v in values], "（台账存比值，已换算为百分数）"
    return values, ""


def _scaled_triplet(stats: LedgerStats) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """把 最低/最高/均值 三个收率一起归一（用同一套判据，不能各算各的）。"""
    raw = [stats.yield_min, stats.yield_max, stats.yield_mean]
    present = [v for v in raw if v is not None]
    if not present:
        return None, None, None
    scaled, _ = _norm_yield(present)
    it = iter(scaled)
    return tuple(next(it) if v is not None else None for v in raw)  # type: ignore[return-value]


def _scale_groups(c: CategoryEffect) -> list[tuple[str, int, float]]:
    """分组均值也归一成百分数（与整体收率同一套判据）。"""
    means = [g[2] for g in c.groups]
    scaled, _ = _norm_yield(means)
    return [(g[0], g[1], scaled[i]) for i, g in enumerate(c.groups)]


def render(stats: LedgerStats) -> str:
    """把统计结果渲染成给模型看的紧凑文本块。

    **只给数字和字段名，不给结论** —— 结论由模型结合工艺标准去下。
    这里要是把「该提高XX」写死了，模型就只是在复读。
    """
    if not stats.yield_batches:
        return "（台账无收率数据，无法做参数影响分析）"

    lines: list[str] = []
    lines.append(
        f"样本：{stats.yield_batches} 批有「{stats.yield_field}」"
        f"（台账共 {stats.total_batches} 批）。"
    )
    yield_lines: list[str] = []
    _, note = _norm_yield([stats.yield_min or 0]) if stats.yield_min else ([], "")
    scaled_min, scaled_max, scaled_mean = _scaled_triplet(stats)
    yield_lines.append(
        f"收率分布：最低 {_fmt(scaled_min)}%，最高 {_fmt(scaled_max)}%，"
        f"均值 {_fmt(scaled_mean)}%{note}。"
    )
    lines.extend(yield_lines)

    if not stats.effects and not stats.categories:
        # 「数据有、但没有信号」和「没数据」是两件事，说法要分开 ——
        # 前者其实是好消息（工艺稳定），后者是台账没填。
        rng = None
        if stats.yield_min is not None and stats.yield_max is not None:
            # 极差也要走同一套归一 —— 直接相减会得到 0.011（比值口径），
            # 打印成「0.01 pt」看着像没有波动（实测踩到）。
            scaled, _ = _norm_yield([stats.yield_min, stats.yield_max])
            rng = scaled[1] - scaled[0]
        lines.append(
            f"已逐字段比对，**没有任何参数的分组差异或相关达到报告门槛**"
            f"（|ρ|≥{MIN_ABS_RHO}，或分组极差≥最好组的 {MIN_GROUP_SPREAD*100:.1f}%，"
            f"或高低收率组差异≥{int(MIN_GROUP_DELTA*100)}%）。"
        )
        if rng is not None and stats.yield_mean:
            scaled_mean, _ = _norm_yield([stats.yield_mean])
            m = scaled_mean[0]
            rel = rng / abs(m) * 100
            lines.append(
                f"这本身是个结论：收率在 {_fmt(rng, 2)} pt 的窄幅内波动"
                f"（相对均值 {rel:.1f}%），**波动不是这些台账参数引起的** ——"
                f"继续从现有字段里找原因是无用的，要么补录过程参数，要么维持现状。"
            )
    else:
        if stats.effects:
            lines.append("")
            lines.append(
                "参数与收率的关系（秩相关 ρ；低/高 = 收率最低/最高各 25% 批次的该参数均值）："
            )
            for e in stats.effects:
                d = e.delta_ratio
                trend = "同向" if (e.rho or 0) > 0 else "反向"
                lines.append(
                    f"  · {e.name}：ρ={_fmt(e.rho, 3)}（{trend}），"
                    f"低收率组 {_fmt(e.low_mean)} → 高收率组 {_fmt(e.high_mean)}"
                    + (f"（{d*100:+.0f}%）" if d is not None else "")
                    + f"，样本 {e.samples} 批"
                )
        if stats.categories:
            lines.append("")
            lines.append("按取值分组的收率对比（用于位号/设备/状态的横向比较）：")
            for c in stats.categories:
                _, n = _norm_yield([g[2] for g in c.groups])
                groups = "、".join(
                    f"{k} {_fmt(v)}%（{cnt} 批）" for k, cnt, v in _scale_groups(c)
                )
                lines.append(f"  · {c.name}：{groups}")

    if len(stats.months) >= 2:
        lines.append("")
        lines.append("月度趋势（近 %d 个月）：" % len(stats.months))
        month_means = [m.yield_mean for m in stats.months if m.yield_mean is not None]
        scaled, _ = _norm_yield(list(month_means)) if month_means else ([], "")
        for i, m in enumerate(stats.months):
            yv = (
                f"{scaled[i]:.2f}%"
                if m.yield_mean is not None and i < len(scaled)
                else "—"
            )
            extra = "、".join(f"{k} {_fmt(v)}" for k, v in list(m.param_means.items())[:4])
            lines.append(
                f"  · {m.month}：{m.batches} 批，收率均值 {yv}"
                + (f"；{extra}" if extra else "")
            )

    if stats.sparse_fields:
        lines.append("")
        lines.append(
            "以下参数记录太少（不足 %d 批），**无法判断影响**，只能说明台账填写不完整："
            % MIN_SAMPLES
        )
        lines.append("  " + "、".join(f"{k}({n}批)" for k, n in stats.sparse_fields))

    return "\n".join(lines)
