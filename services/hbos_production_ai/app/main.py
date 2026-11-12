"""AI 分析服务 —— 定时跑，按产品分析工艺，结果写回飞书。

运行（手动）：
    cd services/hbos_production_ai
    uv run --env-file .env python -m app.main

定时：`launchd/com.haibin.hbos.production-ai.plist`（每天 16:30），见 README。

**顺序很重要**：

    1. 检查配置齐不齐
    2. **探活模型** —— 失败就直接退出，不进入分析循环
       （历史教训：模型名被下线后跑了整批才失败）
    3. 逐产品：取数据 → 组提示词 → 调模型 → 校验 → 写回（幂等）

**校验失败不写飞书** —— 宁可这一轮没有结果，也不让没通过校验的内容进看板
（Owner 定了不做人工确认）。
"""

from __future__ import annotations

import hashlib
import logging
import sys
from datetime import date

from . import config, llm, parse, prompt, sources, writer

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("hbos_production_ai")


def _fingerprint(product: str, craft, ledger) -> str:
    """数据指纹 —— 源数据变了才重跑。

    取「产品 + 工艺描述全文 + 台账内容」的哈希（用**已加载**的数据，不重复拉表）。
    **刻意不含运行时间** —— 否则每次跑指纹都不同，幂等就失效了。
    """
    parts = sources.fingerprint_parts(product, craft, ledger)
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:32]


def analyze_product(product: str) -> dict:
    """分析一个产品并写回。返回该产品的统计。"""
    log.info("=== %s ===", product)

    craft, ledger = sources.load_product(product, config.AI_MAX_BATCHES)
    if not craft.processes:
        log.warning("%s 没有读到工序清单，跳过", product)
        return {"product": product, "status": "skipped", "reason": "无工序清单"}
    log.info("  工序 %d 道；台账 %d 批", len(craft.processes), len(ledger))

    fp = _fingerprint(product, craft, ledger)
    user = prompt.build_user_prompt(product, craft, ledger)

    raw = llm.complete(prompt.SYSTEM_PROMPT, user)
    try:
        analyses = parse.parse_response(raw, craft.processes)
    except parse.ParseError as exc:
        # 校验不过 → **不写飞书**，保留原文供排查
        log.error("  输出校验失败，本轮不写回：%s", exc)
        return {"product": product, "status": "invalid", "reason": str(exc), "raw": raw[:500]}

    records = parse.to_records(product, analyses, date.today().isoformat(), fp)
    stats = writer.write_results(records, fp, dry_run=config.DRY_RUN)
    grades = [a.grade for a in analyses]
    log.info("  评级分布：%s", {g: grades.count(g) for g in set(grades)})

    return {"product": product, "status": "ok", "processes": len(analyses), **stats}


def main() -> int:
    log.info("AI 分析服务启动")

    # 1) 配置
    # 分开报缺了哪个 —— 一句「模型未配置」在排查时看不出是 URL、key 还是模型名。
    missing = [
        name
        for name, value in (
            ("HBOS_AI_BASE_URL", config.AI_BASE_URL),
            ("HBOS_AI_API_KEY", config.AI_API_KEY),
            ("HBOS_AI_MODEL", config.AI_MODEL),
        )
        if not value
    ]
    if missing:
        log.error("模型未配置，缺：%s", ", ".join(missing))
        log.error("  请填 %s/.env", __file__.rsplit("/app/", 1)[0])
        return 2
    if not writer.configured():
        log.error("飞书凭据未配置（HBOS_FEISHU_APP_ID / SECRET），退出")
        return 2
    if not config.AI_ENABLED:
        log.warning("HBOS_AI_ENABLED=0，未启用分析。要跑请设为 1。")
        return 0

    # 2) 探活 —— 失败不进入循环
    probe = llm.probe()
    if not probe.get("ok"):
        log.error("模型探活失败：%s", probe.get("reason"))
        if probe.get("detail"):
            log.error("  详情：%s", probe["detail"])
        if probe.get("hint"):
            log.error("  %s", probe["hint"])
            try:
                log.error("  上游可用模型：%s", ", ".join(llm.list_models()[:40]))
            except Exception as exc:  # noqa: BLE001 - 探活阶段尽力而为
                log.error("  列模型也失败：%s", exc)
        return 3
    log.info("模型探活通过：%s", probe.get("model"))

    # 3) 逐产品
    results = [analyze_product(p) for p in config.AI_PRODUCTS]

    log.info("=== 汇总 ===")
    for r in results:
        log.info("  %-12s %s", r["product"], r["status"])
    failed = [r for r in results if r["status"] not in ("ok", "skipped")]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
