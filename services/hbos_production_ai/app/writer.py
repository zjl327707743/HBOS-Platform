"""写回结果表 —— **幂等**是这里唯一的重点。

既有 openclaw 项目出过一个缺陷：`B6生产台账_AI测试` 里同一格被追加了 **64 次**
同一句话（896 字符，无终止符）。根因是**写入前不清空、也不判重**，每跑一次往后叠。

本模块的规则：

    一个产品 + 一道工序 = **一行**。
    写之前先查：指纹相同 → 跳过；指纹不同 → 更新该行；没有 → 新增。

这样表不会无限膨胀，看板读到的永远是「每条工序的最新结论」。
"""

from __future__ import annotations

import logging
from typing import Any

from . import config, feishu

log = logging.getLogger("hbos_production_ai.writer")

#: 结果表（Owner 2026-10-02 建）。
BASE_AI = "Dl45bIEEya78fWsL4DXcwuJtn8c"
TABLE_AI = "tblXD7oAwbU8U040"


def _text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "".join(str(x) for x in v).strip()
    return str(v).strip()


def load_existing() -> dict[tuple[str, str], dict]:
    """读现有结果 → `{(产品, 工序): {"record_id":…, "数据指纹":…}}`。"""
    out: dict[tuple[str, str], dict] = {}
    for rec in feishu.list_records(BASE_AI, TABLE_AI):
        f = rec.get("fields") or {}
        key = (_text(f.get("产品")), _text(f.get("工序")))
        if not key[0] or not key[1]:
            continue
        out[key] = {"record_id": rec.get("record_id", ""), "fingerprint": _text(f.get("数据指纹"))}
    return out


def write_results(records: list[dict[str, Any]], fingerprint: str, *, dry_run: bool = False) -> dict:
    """把一批结果写回。返回统计（新增 / 更新 / 跳过）。

    `records` 由 `parse.to_records()` 产出，每条含 `产品` / `工序` / `数据指纹`。
    """
    existing = load_existing()

    created = updated = skipped = 0
    for fields in records:
        key = (_text(fields.get("产品")), _text(fields.get("工序")))
        prev = existing.get(key)

        if prev and prev["fingerprint"] == fingerprint:
            # 同一条工序、源数据没变 → 不重复写（这正是 openclaw 缺的那一步）
            skipped += 1
            continue

        if dry_run:
            log.info("[dry-run] %s / %s → 将%s", key[0], key[1], "更新" if prev else "新增")
            (updated := updated + 1) if prev else (created := created + 1)
            continue

        if prev and prev["record_id"]:
            feishu.update_record(BASE_AI, TABLE_AI, prev["record_id"], fields)
            updated += 1
        else:
            feishu.create_record(BASE_AI, TABLE_AI, fields)
            created += 1

    result = {"created": created, "updated": updated, "skipped": skipped}
    log.info("写回完成：%s", result)
    return result


def configured() -> bool:
    return config.feishu_configured()
