"""写回结果表 —— **幂等**是这里唯一的重点。

既有 openclaw 项目出过一个缺陷：`B6生产台账_AI测试` 里同一格被追加了 **64 次**
同一句话（896 字符，无终止符）。根因是**写入前不清空、也不判重**，每跑一次往后叠。

本模块的规则：

    一个产品 + 一道工序 = **一行**。
    写之前先查：指纹相同 → 跳过；指纹不同 → 更新该行；没有 → 新增。

    此外还要**清掉失效行**：本次没产出的工序（改名/拆分/合并/从工艺描述删除）
    不能继续留在表里 —— 否则看板会一直展示已废止工序的结论。

这样表不会无限膨胀，看板读到的永远是「每条工序的最新结论」。
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

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


def load_existing_rows() -> list[dict]:
    """读现有结果的**全部行**（含重复行）—— 判重与清理都需要逐条 `record_id`。

    不能用 `{(产品, 工序): row}` 的字典形态：那样会压掉重复行，同一工序的
    历史副本永远删不掉。
    """
    rows: list[dict] = []
    for rec in feishu.list_records(BASE_AI, TABLE_AI):
        f = rec.get("fields") or {}
        product = _text(f.get("产品"))
        process = _text(f.get("工序"))
        if not product or not process:
            continue
        rows.append(
            {
                "record_id": rec.get("record_id", ""),
                "product": product,
                "process": process,
                "fingerprint": _text(f.get("数据指纹")),
            }
        )
    return rows


def write_results(
    records: list[dict[str, Any]],
    fingerprint: str,
    *,
    dry_run: bool = False,
    valid_processes: Iterable[str] | None = None,
) -> dict:
    """把一批结果写回。返回统计（新增 / 更新 / 跳过 / 清理）。

    `records` 由 `parse.to_records()` 产出，每条含 `产品` / `工序` / `数据指纹`。

    `valid_processes` 是**本次分析实际产出的工序名**。给了它，本产品在表中
    其余工序的记录就会被删除（工序改名、拆分、合并、从工艺描述删除之后，
    旧行不该继续出现在看板上）。不传则保持旧行为（只增改，不清理）。
    """
    existing_rows = load_existing_rows()

    created = updated = skipped = 0

    # 同一 (产品, 工序) 可能有多条历史副本。**保留最后一条**（飞书返回顺序即
    # 创建顺序），其余标记为待清理 —— 重复行会让看板统计条数失真。
    #
    # ⚠️ `keys`（要更新哪一条）和 `duplicates`（要删哪几条）必须**互斥**，
    # 且都指向同一条 survivor。
    #
    # 踩过（复审 2026-10-28）：早先 `keys` 指向最后一条，而 `duplicates`
    # 却收的是「除第一条以外的所有行」—— 最后一条同时被更新又被删除，
    # 留下的反而是最旧的那条旧结论。而且报告写着 `updated=1, removed=1,
    # cleanupFailed=[]`，退出码 0，完全看不出出了事。
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in existing_rows:
        grouped.setdefault((row["product"], row["process"]), []).append(row)

    keys: dict[tuple[str, str], dict] = {}
    duplicates: list[dict] = []
    for key, rows in grouped.items():
        survivor = rows[-1]
        keys[key] = survivor
        duplicates.extend(rows[:-1])

    for fields in records:
        key = (_text(fields.get("产品")), _text(fields.get("工序")))
        prev = keys.get(key)

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

    stale = _stale_rows(records, existing_rows, duplicates, valid_processes)
    removed = 0
    #: 清理失败的行 —— **必须上报**，否则废行留在表里继续被看板读到，
    #: 而调度系统显示「本轮成功」，没人会去处理。
    cleanup_failed: list[dict] = []
    for row in stale:
        if dry_run:
            log.info(
                "[dry-run] 将删除失效行 %s / %s（%s）",
                row["product"], row["process"], row["reason"],
            )
            continue
        try:
            feishu.delete_record(BASE_AI, TABLE_AI, row["record_id"])
            removed += 1
        except feishu.FeishuError as exc:
            # 结果已经写进去了，所以不让整轮失败；但要把失败**报出去**，
            # 主流程据此返回 partial 并给非零退出码。
            log.warning("删除失效行 %s 失败：%s", row["record_id"], exc)
            cleanup_failed.append(
                {
                    "recordId": row["record_id"],
                    "product": row["product"],
                    "process": row["process"],
                    "reason": str(exc)[:120],
                }
            )

    result = {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "removed": len(stale) if dry_run else removed,
        "cleanupFailed": cleanup_failed,
    }
    log.info("写回完成：%s", result)
    return result


def _stale_rows(
    records: list[dict[str, Any]],
    existing_rows: list[dict],
    duplicates: list[dict],
    valid_processes: Iterable[str] | None,
) -> list[dict]:
    """表里存在、但本次不该再有的行。

    两类：
      1. **重复行** —— 同一 (产品, 工序) 的历史副本；
      2. **失效工序** —— 本次没产出的工序（仅在给出 `valid_processes` 时）。
    """
    products = {_text(r.get("产品")) for r in records if _text(r.get("产品"))}
    valid = {str(p) for p in (valid_processes or [])}
    produced = {(_text(r.get("产品")), _text(r.get("工序"))) for r in records}

    stale: list[dict] = [{**row, "reason": "重复行"} for row in duplicates]
    duplicate_ids = {row["record_id"] for row in duplicates}

    if valid:
        for row in existing_rows:
            if row["record_id"] in duplicate_ids:
                continue
            if row["product"] not in products:
                continue          # 只清理本次分析的产品，别动别的产品
            if (row["product"], row["process"]) in produced:
                continue
            if row["process"] in valid:
                continue          # 本次产出里应该有它（上面已处理）
            stale.append({**row, "reason": "工序已不在工艺描述中"})
    return stale


def configured() -> bool:
    return config.feishu_configured()
