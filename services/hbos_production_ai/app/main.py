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

from . import config, llm, parse, prompt, runlock, sources, stats, writer

logging.basicConfig(
    level=config.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("hbos_production_ai")


def _engine_signature() -> str:
    """**分析引擎**的标识 —— 模型与调用参数。

    切换模型后指纹必须变，否则探活成功、整轮显示 ok，但所有行因指纹相同被
    `skipped`，看板继续展示旧模型的结果 —— 新模型实际上从没跑过。
    端点和温度同理：它们都会实质改变输出。
    """
    return "|".join(
        [
            config.AI_BASE_URL or "",
            config.AI_MODEL or "",
            "" if config.AI_TEMPERATURE is None else str(config.AI_TEMPERATURE),
        ]
    )


def _fingerprint(
    product: str,
    craft,
    ledger,
    *,
    stats_parts: list[str] | None = None,
) -> str:
    """数据指纹 —— 源数据**或分析规格**变了才重跑。

    取「产品 + 工艺描述全文 + 台账内容 + 统计输入 + 提示词版本 + 分析引擎」的哈希。
    **刻意不含运行时间** —— 否则每次跑指纹都不同，幂等就失效了。

    ⚠️ `prompt.PROMPT_VERSION` 必须参与 —— 踩过：2026-10-26 改了提示词和
    报告结构，但指纹只看源数据；那几个产品当天台账没变，指纹相同 → 全部
    `skipped`，结果表里 55 行仍是旧格式（没有「改进建议」段）。
    改提示词却不改版本号 = 新逻辑只对新数据生效，老行永远停在旧格式。

    ⚠️ `stats_parts` 也必须参与 —— 提示词里的统计来自 `AI_STATS_BATCHES`
    批台账（默认 400），而 `ledger` 只有最近 30 批。早先只看 `ledger`，
    于是第 31~400 批被补录/修正后，**提示词变了但指纹没变**，写回层直接
    跳过 —— 用户改了历史数据却看不到重新分析。

    ⚠️ `_engine_signature()` 也要参与 —— 换模型/换温度/换端点都是「换了
    分析规格」，源数据不变也该重跑（见那里）。
    """
    parts = [
        prompt.PROMPT_VERSION,
        _engine_signature(),
        *sources.fingerprint_parts(product, craft, ledger),
        *(stats_parts or []),
    ]
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

    # 参数↔收率的统计在这里算，**不让模型自己算** —— 模型看几十批原始数字
    # 算不出相关系数，只会给出「可能有关」这类没法用的描述。
    # 算它需要全年数据（近 30 批供不上统计样本），所以单独读一批更长的。
    stat_ledger = sources.fetch_ledger(product, config.AI_STATS_BATCHES)
    ledger_stats = stats.analyze(product, stat_ledger)
    log.info(
        "  工序 %d 道；台账 %d 批（统计用 %d 批，有收率 %d 批，可用参数 %d 个）",
        len(craft.processes),
        len(ledger),
        ledger_stats.total_batches,
        ledger_stats.yield_batches,
        len(ledger_stats.effects),
    )

    fp = _fingerprint(
        product,
        craft,
        ledger,
        stats_parts=sources.stats_fingerprint_parts(stat_ledger, stats.render(ledger_stats)),
    )
    user = prompt.build_user_prompt(product, craft, ledger, ledger_stats)

    raw = llm.complete(prompt.SYSTEM_PROMPT, user)
    try:
        analyses = parse.parse_response(raw, craft.processes)
    except parse.ParseError as exc:
        # 校验不过 → **不写飞书**，保留原文供排查
        log.error("  输出校验失败，本轮不写回：%s", exc)
        return {"product": product, "status": "invalid", "reason": str(exc), "raw": raw[:500]}

    records = parse.to_records(product, analyses, date.today().isoformat(), fp)
    # 本次有效工序清单 —— writer 用它清理「表里还有、但这次没产出」的旧行
    result = writer.write_results(
        records,
        fp,
        dry_run=config.DRY_RUN,
        valid_processes=[a.name for a in analyses],
    )
    grades = [a.grade for a in analyses]
    n_sug = sum(len(a.suggestions) for a in analyses)
    log.info("  评级分布：%s；建议 %d 条", {g: grades.count(g) for g in set(grades)}, n_sug)

    # 清理失效行失败 → 状态是 **partial**，不是 ok。
    # 废行还在表里、看板还会读到它；报 ok 会让调度系统以为一切正常。
    status = "partial" if result.get("cleanupFailed") else "ok"
    return {
        "product": product,
        "status": status,
        "processes": len(analyses),
        "suggestions": n_sug,
        **result,
    }


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

    # 3) 逐产品 —— **单个产品失败不能中断整轮**。
    #
    # 踩过：早先是 `[analyze_product(p) for p in ...]`，4BMA 一次超时抛异常就把
    # 后面 5 个产品全带走，等于整轮白跑（一次调用要 300+ 秒，代价很高）。
    # 现在逐个 try/except，失败的记进结果表继续下一个。
    #
    # 整轮套一把**跨进程锁**：定时任务与手动任务同时跑时，两边都会读到
    # 「这条工序不存在」而各建一行 —— 重复行就是这么来的（见 runlock）。
    try:
        with runlock.run_lock():
            results = _analyze_all()
    except runlock.LockBusy as exc:
        log.warning("%s —— 本轮跳过", exc)
        return 0

    log.info("=== 汇总 ===")
    for r in results:
        log.info("  %-12s %s", r["product"], r["status"])
    failed = [r for r in results if r["status"] not in ("ok", "skipped")]
    return 1 if failed else 0


def _analyze_all() -> list[dict]:
    results: list[dict] = []
    for p in config.AI_PRODUCTS:
        try:
            results.append(analyze_product(p))
        except Exception as exc:  # noqa: BLE001 - 一个产品失败不该拖垮其余
            log.error("%s 分析失败：%s", p, str(exc)[:200])
            results.append({"product": p, "status": "error", "reason": str(exc)[:200]})
    return results


if __name__ == "__main__":
    sys.exit(main())
