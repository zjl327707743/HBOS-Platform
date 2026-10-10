"""生产看板取数服务（FastAPI）。

集成方式沿用 `services/hbos_ocr` 的规范：**独立服务，通过 HTTP 提供服务**，
不修改 Frappe 核心源码、不直连数据库。

与 hbos_ocr 的两处不同：
    - 本服务**只读飞书**（不写），写飞书的是 AI 分析服务（另一条链路）；
    - 本服务**常驻等请求**（hbos_ocr 也是），而 AI 分析是定时脚本。

**凭据边界**：飞书 `app_secret` 只在本服务的环境变量里，前端拿不到 ——
这是选「独立服务」而非「前端直连」的唯一理由（见取数架构方案 §2）。

运行：
    uvicorn app.main:app --host 127.0.0.1 --port 8101
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import date, timedelta
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, contract, feishu, sources

logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger("hbos_production")

app = FastAPI(
    title="HBOS 生产看板取数服务",
    version="0.1.0",
    description="独立取数服务，飞书凭据只在服务端。见 docs/frontend/P4_生产看板_取数架构方案对比.md",
)

# 允许前端访问。开发默认只放本机 Vite 端口；
# **部署到服务器时用 HBOS_PRODUCTION_CORS_ORIGINS 改成看板的实际域名**，
# 否则浏览器会因 CORS 拦掉请求（见 config.py 的说明）。
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 缓存
# ---------------------------------------------------------------------------
#
# 看板是「看一眼就走」的场景，而飞书**慢到不能每次请求都全量拉**：
# 实测单张 400 行的表就要 5~7 秒，9 张表（含翻页）冷启动 100 秒以上。
#
# 策略：**先给旧的、后台刷新**（stale-while-revalidate）。
#   - 有缓存（哪怕已过期）→ 立刻返回旧值，同时后台异步刷新
#   - 完全没有（服务刚启动）→ 才同步拉一次（这一次慢，不可避免）
#
# 数据按天更新，返回几分钟前的值没有任何问题；而「打开就转圈 100 秒」
# 是致命的。

_CACHE: dict[str, dict[str, Any]] = {}   # key -> {"value":…, "stale_at":…}
_REFRESHING: set[str] = set()
_CACHE_LOCK = threading.Lock()


def _cached(key: str, producer):
    now = time.time()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        stale = hit is not None and now >= hit["stale_at"]
        missing = hit is None
        if stale and key not in _REFRESHING:
            _REFRESHING.add(key)

    if hit is not None and not missing:
        if stale:
            _background_refresh(key, producer)
        return hit["value"]

    # 冷启动：只能同步拉一次
    value = producer()
    with _CACHE_LOCK:
        _CACHE[key] = {"value": value, "stale_at": time.time() + config.CACHE_TTL_SECONDS}
        _REFRESHING.discard(key)
    return value


def _background_refresh(key: str, producer) -> None:
    """后台刷新 —— 失败保留旧值（旧数据好过没有），只记日志。"""

    def run():
        try:
            value = producer()
            with _CACHE_LOCK:
                _CACHE[key] = {
                    "value": value,
                    "stale_at": time.time() + config.CACHE_TTL_SECONDS,
                }
            log.info("后台刷新 %s 完成", key)
        except Exception as exc:  # noqa: BLE001 - 刷新失败不该影响正在看的人
            log.warning("后台刷新 %s 失败，继续用旧值：%s", key, str(exc)[:120])
        finally:
            with _CACHE_LOCK:
                _REFRESHING.discard(key)

    threading.Thread(target=run, name=f"refresh-{key}", daemon=True).start()


# ---------------------------------------------------------------------------
# 取数
# ---------------------------------------------------------------------------

def _require_feishu() -> None:
    if not config.feishu_configured():
        # 明确 503 而不是编造数据 —— 前端据此显示「未接入」态
        raise HTTPException(status_code=503, detail="飞书凭据未配置，取数服务尚不可用")


def _load_details():
    """拉 7 张产量明细，归一化成 `DetailRecordWithQty` + 标记四车间成员。

    **串行**拉。曾试过并发（8 路）—— 实测**没用**：飞书侧本身就是瓶颈
    （单张 400 行的表要 5~7 秒，是服务端在慢慢吐），并发只把总时长从 ~100s
    压到 ~30s，却明显更容易撞上 `1254607 Data not ready`。
    真正解决「打开慢」的是上面的 stale-while-revalidate 缓存，不是并发。
    """
    records: list[contract.DetailRecordWithQty] = []
    four_ws_products: set[str] = set()
    for key, table_id in contract.DETAIL_TABLES.items():
        raw = feishu.list_records(contract.BASE_OPERATIONS, table_id)
        for r in raw:
            rec = sources.to_detail_record(r)
            if rec is None:
                continue
            records.append(rec)
            # 会议：四车间当前无在产，暂不录入 —— 按**表来源**判，不按产品名
            if key == "四车间":
                four_ws_products.add(rec.product)
    return records, four_ws_products


def _load_anomalies(today: date) -> dict:
    """拉各车间的异常表，按滚动窗口算闭环率。

    每个车间一个独立 Base —— 一个失败不该拖垮其余，故逐源 try/except，
    失败的车间在 `byWorkshop` 里标出来（宁可显示「某车间取不到」，也不给一个偏低的合计数）。
    """
    start = contract.anomaly_window_start(today)
    stats: list[contract.AnomalyStats] = []
    failed: list[str] = []
    for src in contract.ANOMALY_SOURCES:
        try:
            raw = feishu.list_records(src.base_token, src.table_id)
        except feishu.FeishuError as exc:
            log.warning("异常表取数失败 %s code=%s", src.name, exc.code)
            failed.append(src.name)
            continue
        # 飞书 API 是 {"record_id":…, "fields":{…}} 嵌套结构 —— 必须拆，
        # 否则字段全取不到、闭环率静默变 0/0（见 sources.to_anomaly_record）
        rows = [sources.to_anomaly_record(r) for r in raw]
        stats.append(contract.anomaly_stats(src, rows, start))

    result = contract.overall_closure(stats, start, contract.ANOMALY_WINDOW_MONTHS)
    result["failedWorkshops"] = failed
    return result


def _board_payload() -> dict:
    _require_feishu()

    today = date.today()
    month = today.strftime("%Y-%m")
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    details, four_ws = _load_details()
    plan_rows = feishu.list_records(contract.BASE_OPERATIONS, contract.PLAN_TABLE)
    target_rows = feishu.list_records(contract.BASE_OPERATIONS, contract.TARGET_TABLE)
    plan_map = sources.to_plan_map(plan_rows)
    target_yield = sources.to_target_yield_map(target_rows)

    rows = contract.build_rows(
        month=month,
        yesterday=yesterday,
        details=details,
        members_excluded=four_ws,
        plan_by_product=plan_map,
        yield_by_product=target_yield,
    )

    return {
        "month": month,
        "daysElapsed": contract.days_elapsed(month, today),
        "updatedAt": today.isoformat(),
        "rows": [contract.asdict_row(r) for r in rows],
        "anomaly": _load_anomalies(today),
    }


# ---------------------------------------------------------------------------
# 接口
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "feishuConfigured": config.feishu_configured(),
        "cacheTtl": config.CACHE_TTL_SECONDS,
    }


@app.get("/production/monthly")
def monthly() -> dict:
    """当月看板行。取不到就 503 —— **不返回 0 或空行**。

    前端 `productionBoard.ts` 收到非 200 即渲染「未接入」态，
    符合「数据接通前不显示任何数字」的纪律（EA-5.4 §16）。
    """
    try:
        return _cached("board", _board_payload)
    except feishu.FeishuError as exc:
        log.error("取数失败 code=%s", exc.code)
        raise HTTPException(status_code=502, detail="飞书取数失败") from exc


@app.get("/production/yesterday")
def yesterday() -> dict:
    """昨日入库量（按收料日期）。已含在 `/monthly` 的 row 里，此处单列便于复用。"""
    data = monthly()
    return {
        "date": data.get("updatedAt"),
        "rows": [
            {"label": r["label"], "inbound": r["yesterdayInbound"]}
            for r in data.get("rows", [])
        ],
    }


@app.get("/production/ai-analysis")
def ai_analysis() -> dict:
    """AI 工艺分析结论（读「AI工艺分析结果」表）。

    表空时返回 `{"rows": []}` —— 前端显示「待分析」，
    而不是伪造一条结论（AI 结论直接影响生产判断）。
    """
    _require_feishu()
    try:
        raw = _cached(
            "ai",
            lambda: feishu.list_records(contract.BASE_AI, contract.AI_TABLE),
        )
    except feishu.FeishuError as exc:
        log.error("AI 结果读取失败 code=%s", exc.code)
        raise HTTPException(status_code=502, detail="AI 结果读取失败") from exc

    rows = []
    for r in raw:
        f = r.get("fields") or {}
        product = sources.text(f.get("产品"))
        process = sources.text(f.get("工序"))
        if not product or not process:
            continue
        rows.append(
            {
                "product": product,
                "process": process,
                "summary": sources.text(f.get("结论摘要")),
                "grade": sources.text(f.get("评级")),
                "analyzedAt": contract.parse_month_day(f.get("分析日期")),
            }
        )
    return {"rows": rows}
