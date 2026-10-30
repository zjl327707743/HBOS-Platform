"""每日预热缓存 —— 让用户打开看板时永远是秒开。

## 它解决什么

服务现在是**懒加载**：缓存过期后的第一个访问者要等 100 秒（拉 18 张飞书表）。
落盘缓存解决了「重启后」的冷启动，但**跨天那一次**仍然是谁先来谁等。

本脚本**按计划主动把缓存建好**，用户永远不是那个「第一个」。

## 两种模式（先走服务，服务不在就自己算）

1. **服务在跑** → 打 `GET /production/monthly?refresh=1`
   好处：走的是完全相同的代码路径，内存缓存和磁盘缓存一起更新。
   注意必须带 `refresh=1` —— 不带的话服务会直接返回旧缓存，起不到预热作用。

2. **服务没跑**（或请求失败）→ 直接调 `_board_data()` 并落盘
   好处：定时任务不依赖「服务恰好活着」。下次服务启动时从磁盘读回。

## 用法

    cd services/hbos_production
    .venv/bin/python -m app.warm

launchd 见 `launchd/com.haibin.hbos.production-warm.plist`。
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from enum import Enum

import httpx

from . import config, main

logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger("hbos_production.warm")


class WarmResult(Enum):
    """预热结果 —— **三态**，不是布尔。

    布尔丢掉了「服务活着但取数失败」这一种：日志里写着 502 时不要直连，
    但 `False` 让调用方无法区分「服务没起（该回退直连）」与「服务起了但
    飞书失败（不该再打一遍）」。实测后果是 502 后立刻又全量拉一遍飞书。
    """

    SUCCESS = "success"
    UNREACHABLE = "unreachable"     # 连接层失败 → 可以回退直连
    FAILED = "failed"               # 服务返回错误（含 502/503/504）→ 不要回退


def _warm_via_service(timeout: float = 300.0) -> WarmResult:
    """打本地服务接口，让它同步重取。"""
    url = f"http://{config.HOST}:{config.PORT}/production/monthly"
    try:
        r = httpx.get(url, params={"refresh": "1"}, timeout=timeout)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        # **只有连接层失败**才说明「服务没起」→ 可以直连兜底
        log.info("服务不可达（%s），改为直接取数", type(exc).__name__)
        return WarmResult.UNREACHABLE
    except httpx.HTTPError as exc:
        # 读超时 / 协议中断：服务**是活的**，很可能正在慢慢拉飞书。
        # 早先把这类也当「不可达」→ 直连又拉一轮，把慢变成双倍请求。
        log.warning("调用服务失败（%s），但服务可能仍在运行，不直连兜底", type(exc).__name__)
        return WarmResult.FAILED
    if r.status_code != 200:
        # 502 = 服务活着但飞书取数失败。这时**不要**再直连重试一次 ——
        # 多半是撞了限流，再打一遍只会更糟。等下一轮。
        log.warning("服务返回 %s：%s", r.status_code, r.text[:120])
        return WarmResult.FAILED
    # 200 也可能是代理错误页 / 截断 JSON —— 这里解析失败要当作 FAILED，
    # 而不是让异常冒到调度器把整个任务打成「脚本出错」。
    try:
        data = r.json()
    except ValueError:
        log.warning("服务返回 200 但响应不是 JSON（前 80 字符：%s）", r.text[:80])
        return WarmResult.FAILED
    if not isinstance(data, dict):
        log.warning("服务返回的 JSON 不是对象：%s", type(data).__name__)
        return WarmResult.FAILED
    log.info(
        "预热完成（经服务）：%s 行，异常 %s/%s，质量 %s",
        len(data.get("rows") or []),
        (data.get("anomaly") or {}).get("closed"),
        (data.get("anomaly") or {}).get("total"),
        (data.get("quality") or {}).get("rate"),
    )
    return WarmResult.SUCCESS


def _warm_direct() -> bool:
    """服务不在时直接算一遍并落盘（下次服务启动会读回）。"""
    today = date.today()
    try:
        data = main._board_data(today)
        # 质量与 board 已解耦（见 `main.monthly`），这里也各存各的 key。
        quality = main._quality_cached(today.strftime("%Y-%m"), today)
    except Exception as exc:  # noqa: BLE001 - 定时任务失败要记为非零退出，但别抛栈
        log.error("直接取数失败：%s", str(exc)[:200])
        return False

    # 两个 key 分开存 —— 与服务里的分缓存策略保持一致：
    # board 走 CACHE_TTL_SECONDS，quality 走 QUALITY_CACHE_TTL_SECONDS。
    #
    # ⚠️ 这里**同步**调 `_persist`，不走 `_store` —— `_store` 的落盘是后台
    # daemon 线程，本脚本存完就退出，线程可能还没写完就被杀，等于没预热。
    with main._CACHE_LOCK:
        main._store(
            "board",
            {"rows": data["rows"], "anomaly": data["anomaly"]},
            today,
            persist_async=False,
        )
        main._store(
            "quality",
            quality,
            today,
            config.QUALITY_CACHE_TTL_SECONDS,
            persist_async=False,
        )
    main._persist("board")
    main._persist("quality")
    log.info("预热完成（直接取数）：%s 行", len(data["rows"]))
    return True


def main_entry() -> int:
    if not config.feishu_configured():
        log.error("飞书凭据未配置，跳过预热")
        return 1
    result = _warm_via_service()
    if result is WarmResult.SUCCESS:
        return 0
    if result is WarmResult.FAILED:
        # 服务在跑但取数失败（多半是限流）。**不回退直连** —— 再打一遍
        # 只会让限流更严重，等下一个调度周期。
        return 1
    return 0 if _warm_direct() else 1


if __name__ == "__main__":
    sys.exit(main_entry())
