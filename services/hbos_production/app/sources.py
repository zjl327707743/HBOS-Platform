"""把飞书记录转成 `contract` 的输入结构。

飞书的记录形如 `{"record_id": "...", "fields": {...}}`，字段值是**中文键 + 原值**
（日期可能是毫秒时间戳或字符串，收率可能是 `"0.9014"` 或数字）。这里统一归一化。

**本模块不做业务判断**，只做「解析 + 类型转换 + 空的如实保留为 None」。
"""

from __future__ import annotations

from typing import Any, Optional

from .contract import DetailRecordWithQty, parse_month_day


def _field(record: dict, name: str) -> Any:
    return (record.get("fields") or {}).get(name)


def text(value: Any) -> str:
    """飞书文本/多选字段可能是 list，统一成字符串。"""
    if value is None:
        return ""
    if isinstance(value, list):
        return "".join(str(x) for x in value).strip()
    return str(value).strip()


def _number(value: Any) -> Optional[float]:
    """转数字。**转不了返回 None，绝不返回 0** ——
    「没有值」与「值是 0」在业务上完全不同（见视觉方案 §3.2 对 A7 的讨论）。"""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def to_detail_record(record: dict) -> Optional[DetailRecordWithQty]:
    """一条产量明细 → `DetailRecordWithQty`。

    产品名为空的行直接丢弃（飞书表里有几条这样的空行，实测 5~10 行）。
    """
    product = text(_field(record, "产品名称"))
    if not product:
        return None
    return DetailRecordWithQty(
        product=product,
        batch=text(_field(record, "批号")),
        received_on=parse_month_day(_field(record, "收料日期")),
        yield_rate=_number(_field(record, "收率")),
        qty=_number(_field(record, "产量")),
    )


def to_plan_map(records: list[dict]) -> dict[str, int]:
    """`月度生产计划明细` → `{产品: 1–31 日求和}`。"""
    from .contract import plan_batches

    out: dict[str, int] = {}
    for r in records:
        product = text(_field(r, "产品名称"))
        if not product:
            continue
        out[product] = plan_batches(r.get("fields") or {})
    return out


def to_target_yield_map(records: list[dict]) -> dict[str, float]:
    """`月度目标产能` → `{产品: 目标收率}`。

    目标收率是小数（0.91 表示 91%）。无值的不进 map —— 调用方按「缺」处理。
    """
    out: dict[str, float] = {}
    for r in records:
        product = text(_field(r, "产品名称"))
        if not product:
            continue
        y = _number(_field(r, "目标收率"))
        if y is not None:
            out[product] = y
    return out


def table_department(table_key: str) -> str:
    """明细表 key → 车间名。用于四车间排除。

    表 key 见 `contract.DETAIL_TABLES`（二车间 / 三车间 / 四车间 / 五车间 / 六车间 / 粗品 / 无菌）。
    粗品表与无菌表不属四车间。
    """
    return table_key


def to_anomaly_record(record: dict) -> dict:
    """飞书 API 的 item 是 `{"record_id":…, "fields": {…}}` —— **嵌套**的。

    而 lark-cli 的 `--format ndjson` 是**平铺**的。两者在排查时都见过，
    所以这里统一拆一次：调用方拿到的一律是平铺的字段 dict。

    不拆的话，`record.get("事件原因")` 永远取不到 —— 不报错、不抛异常，
    只是所有字段都空 → 闭环率静默变成 0/0。**最难发现的那种错**。
    """
    return record.get("fields") or record
