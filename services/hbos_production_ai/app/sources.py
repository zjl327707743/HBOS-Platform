"""数据源：工艺描述 + 生产台账。

**只读**。写入在 `writer.py`。

产品 → 表 ID 的映射在这里；工艺描述的「工序清单」从**字段名**动态取
（不硬编码）—— 这样新增工序或新增产品时不用改代码。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from . import feishu

#: 生产台账 Base（工艺描述 + 台账都在这）。
BASE_MAIN = "IiYMb9NO2a6TGOsDS7YcxO8In4c"

#: 工艺描述表里**不当作工序**的字段。
#:
#: 各表的元数据列名不统一（实测）：4BMA 用 `项目`，F9/F12/F13 用 `序号`；
#: 无菌两张表还多出 `产品名称` / `基本信息` / `物料代码` / `规格/投料量`。
#: 少列一个，它就会被当成「一道工序」喂给模型 —— 所以这里要列全。
_NON_PROCESS_FIELDS = {
    "SourceID",
    "record_id",
    "项目",
    "序号",
    "产品基本信息",
    "产品基本信息 1",
    "产品名称",
    "产品名称/物料代码",
    "基本信息",
    "物料代码",
    "规格/投料量",
}

#: 标记「这一行是哪种维度」的列名，按顺序探测。
_DIMENSION_FIELDS = ("项目", "序号")

#: 维度标记值 → 维度。各表用词不同，但都归到这三类。
_CRAFT_MARKS = {"工艺", "工艺描述"}
_STANDARD_MARKS = {"标准工艺参数", "工艺参数"}
_EQUIPMENT_MARKS = {"设备描述", "设备参数"}

#: F9 那种用位置序号标记的表：`序号` 是裸数字 1/2/3。
#: 实测 F9 的三行依次是 工艺 / 标准参数 / 设备 —— 与其它表的语义一致。
_POSITIONAL_MARKS = {"1": "craft", "2": "standard", "3": "equipment"}

#: `规格/投料量` 列 —— 无菌两张表用它区分多个规格（如 `规范/50kg` / `欧盟/160kg`）。
_SPEC_FIELD = "规格/投料量"

#: 维度名 → `CraftDescription` 上的字段名。
_DIM_ATTR = {"craft": "craft", "standard": "standard", "equipment": "equipment"}


@dataclass
class ProductSource:
    """一个产品的数据源定义。"""

    name: str
    craft_table: str          # 工艺描述表
    ledger_table: str         # 生产台账
    ledger_date_field: str    # 台账里用于排序/取月的日期字段（各表不同）


#: 产品 → 源表。**表 ID 是稳定的**；日期字段各表不同（实测各表命名不统一）。
PRODUCTS: dict[str, ProductSource] = {
    "4BMA": ProductSource("4BMA", "tblJsLbPXWSwwYAh", "tblfQOYswTOloLrm", "投料日期"),
    "F9": ProductSource("F9", "tblxGSiTDrJzYjij", "tblPeLAOWUNSWEeo", "投料日期"),
    "F12": ProductSource("F12", "tblASeWbg8RDsNaR", "tblv966qw8jqcopk", "投料日期"),
    "F13": ProductSource("F13", "tblb3Q6vp3IHPIGO", "tbl2bTjioeEMvdHC", "投料日期"),
    "无菌美罗培南": ProductSource(
        "无菌美罗培南", "tblQJilNsoE0GNFb", "tblHQugTwjq5m4u1", "投料日期"
    ),
    "无菌亚胺培南": ProductSource(
        "无菌亚胺培南", "tblGhO7ONxJS4732", "tbl2HIeSG0OyGMw8", "投料日期"
    ),
}

#: 源表行的维度标记 —— 工艺描述表每种维度一行。
#: （保留旧常量名供老代码/文档引用；实际解析已改为按 `_DIMENSION_FIELDS` 探测。）
ITEM_CRAFT = "工艺"
ITEM_STANDARD = "标准工艺参数"
ITEM_EQUIPMENT = "设备描述"


@dataclass
class CraftDescription:
    """一个产品的工艺描述（三种维度）。

    `processes` 是**工序名清单**（从字段名取，排除 SourceID/项目/产品基本信息），
    与 `craft` / `standard` / `equipment` 三个 dict 的键一致。
    """

    product: str
    processes: list[str] = field(default_factory=list)
    craft: dict[str, str] = field(default_factory=dict)        # 工序 → 工艺描述
    standard: dict[str, str] = field(default_factory=dict)     # 工序 → 标准参数
    equipment: dict[str, str] = field(default_factory=dict)    # 工序 → 设备描述


@dataclass
class LedgerBatch:
    """台账的一批（只保留非空字段）。"""

    batch: str
    values: dict[str, str] = field(default_factory=dict)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "".join(str(x) for x in value).strip()
    return str(value).strip()


def _dimension_of(fields: dict) -> Optional[str]:
    """判断一行的维度（craft / standard / equipment）；认不出返回 None。

    各表用词不一：4BMA 的 `项目` 写「工艺 / 标准工艺参数 / 设备描述」，
    F12/F13 的 `序号` 写「工艺描述 / 标准工艺参数 / 设备描述」，无菌表写
    「工艺描述 / 工艺参数 / 设备参数」，F9 的 `序号` 只给裸数字 1/2/3。
    这些都必须归到同一套维度上，否则整行会被丢掉。
    """
    for key in _DIMENSION_FIELDS:
        mark = _text(fields.get(key))
        if not mark:
            continue
        if mark in _CRAFT_MARKS:
            return "craft"
        if mark in _STANDARD_MARKS:
            return "standard"
        if mark in _EQUIPMENT_MARKS:
            return "equipment"
        if mark in _POSITIONAL_MARKS:
            return _POSITIONAL_MARKS[mark]
    return None


def parse_craft_records(product: str, records: list[dict]) -> CraftDescription:
    """把工艺描述表的原始记录解析成 `CraftDescription`（**纯函数**，可离线单测）。

    工序清单 = 所有行出现的字段名去掉 `_NON_PROCESS_FIELDS`（保序、跨行取并集）——
    只看一行会漏字段：实测 F12 有的行多出 `产品基本信息 1`、有的行少字段。

    多规格表（无菌两张，用 `规格/投料量` 分 `规范/50kg` / `欧盟/160kg` 等）：
    规格数 > 1 时给工序名加规格后缀，如 `结晶（欧盟/160kg）`。
    不加后缀的话三组会互相覆盖，只剩最后一组 —— 静默丢数据。
    """
    rows: list[tuple[str, str, dict]] = []
    for rec in records:
        f = rec.get("fields") or {}
        dim = _dimension_of(f)
        if dim is None:
            continue
        rows.append((dim, _text(f.get(_SPEC_FIELD)), f))

    # 工序名：跨行取并集（保序）
    procs: list[str] = []
    for _, _, f in rows:
        for k in f:
            if k not in _NON_PROCESS_FIELDS and k not in procs:
                procs.append(k)

    specs = sorted({spec for _, spec, _ in rows if spec})
    multi = len(specs) > 1

    out = CraftDescription(product=product)
    for dim, spec, f in rows:
        suffix = f"（{spec}）" if multi and spec else ""
        target = getattr(out, _DIM_ATTR[dim])
        for proc in procs:
            v = _text(f.get(proc))
            if not v:
                continue
            name = f"{proc}{suffix}"
            if name not in out.processes:
                out.processes.append(name)
            target[name] = v
    return out


def fetch_craft(product: str) -> CraftDescription:
    """读某产品的工艺描述（各维度一行；无菌表可能多规格多组）。"""
    src = PRODUCTS[product]
    records = feishu.list_records(BASE_MAIN, src.craft_table)
    return parse_craft_records(product, records)


def _sort_key(record: dict, date_field: str) -> int:
    """取日期字段的可排序值（**整数比较**，不是字符串）。

    踩过：早先写成 `str(v)` 做字符串排序 —— 同一张表里日期既有毫秒时间戳
    也有字符串（`2026-10-01` / `2026.10.01` / `2026/10/01`，实测各表混用），
    13 位字符串比大小碰巧对，但混进别的格式就静默排错。
    「取最近 N 批」排错 = **分析的是错的批次**，而且看不出来。

    缺失返回 0（排最后），不是 None —— 避免比较时报错。
    """
    f = record.get("fields") or {}
    v = f.get(date_field)
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v or "").strip()
    if not s:
        return 0
    # 日期字符串 → 归一成 `YYYYMMDD` 整数
    import re as _re

    m = _re.match(r"(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})", s)
    if m:
        return int(f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}")
    return 0


def fetch_ledger(product: str, limit: int) -> list[LedgerBatch]:
    """读某产品台账**最近 `limit` 批**（按日期倒序）。

    只取最近 N 批 —— 台账有 1200+ 行，全喂会撑爆上下文且没必要：
    分析看的是近期工艺稳定性。
    """
    src = PRODUCTS[product]
    records = feishu.list_records(BASE_MAIN, src.ledger_table)
    records.sort(key=lambda r: _sort_key(r, src.ledger_date_field), reverse=True)

    out: list[LedgerBatch] = []
    for rec in records[:limit]:
        f = rec.get("fields") or {}
        # 批号字段各表命名不同，逐个兜
        batch = ""
        for k in ("批号", "精制批号", "生产批号", "批次"):
            if _text(f.get(k)):
                batch = _text(f.get(k))
                break
        values = {
            k: _text(v)
            for k, v in f.items()
            if _text(v) and k not in ("SourceID", "record_id")
        }
        out.append(LedgerBatch(batch=batch, values=values))
    return out


def load_product(product: str, max_batches: int) -> tuple[CraftDescription, list[LedgerBatch]]:
    """一次取齐某产品的工艺描述与台账。"""
    return fetch_craft(product), fetch_ledger(product, max_batches)


def process_names(product: str) -> list[str]:
    """某产品的工序清单（供上层展示用，不触发额外请求时用缓存）。"""
    return fetch_craft(product).processes


def fingerprint_parts(
    product: str, craft: CraftDescription, ledger: list[LedgerBatch]
) -> list[str]:
    """参与数据指纹的「源数据版本」部分（**纯函数**，用已加载的数据）。

    取「工艺描述全文 + 台账批号与值」—— 任一变化都应触发重分析。
    刻意**不含运行时间**：「跑过一次」不该改变指纹，否则幂等就失效了。

    覆盖范围 = **实际喂给模型的那批数据**（即 `ledger`，已按上限截断）。
    这样「输入没变就不重跑」是精确的 —— 窗口外的批次被改不影响判断。
    """
    parts = [product]
    for proc in sorted(craft.processes):
        parts.append(proc)
        parts.append(craft.craft.get(proc, ""))
        parts.append(craft.standard.get(proc, ""))
    for b in ledger:
        parts.append(b.batch)
        parts.append("|".join(f"{k}={v}" for k, v in sorted(b.values.items())))
    return parts
