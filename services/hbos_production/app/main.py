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

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, contract, feishu, sources

logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger("hbos_production")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """启动时把磁盘上的缓存读回来 —— 否则重启后第一次访问要等 100 秒。"""
    _restore("board", "quality", "ai")
    yield


app = FastAPI(
    title="HBOS 生产看板取数服务",
    version="0.1.0",
    description="独立取数服务，飞书凭据只在服务端。见 docs/frontend/P4_生产看板_取数架构方案对比.md",
    lifespan=_lifespan,
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

_CACHE: dict[str, dict[str, Any]] = {}   # key -> {"value":…, "stale_at":…, "built_at":…, "built_on":…}
_REFRESHING: set[str] = set()
_CACHE_LOCK = threading.Lock()
#: 串行化「强制刷新」（前端点刷新按钮时走这条）。见 `_refresh_now`。
_REFRESH_LOCK = threading.Lock()


# --- 缓存落盘 -------------------------------------------------------------
#
# 内存缓存在**服务重启后就没了**。重启是常事（改代码、休眠唤醒、机器重启），
# 而每次重启后的第一次访问都要重拉 18 张飞书表、等 100 秒 —— 这是目前最大
# 的体验问题。
#
# 落盘后：
#   - 服务重启 → 从磁盘读回，**还新鲜就秒开**（连后台刷新都不用）
#   - 跨天 → 读到昨天的缓存，**先给旧值秒开**，同时后台刷新（_cached 的既有逻辑）
#
# 写盘是**异步**的：不能因为磁盘慢拖慢请求。失败只记日志，不影响取数
# （磁盘满 / 权限不对时，退化成纯内存缓存，行为与之前一致）。

def _cache_path(key: str):
    if not config.CACHE_DIR or not str(config.CACHE_DIR):
        return None
    return config.CACHE_DIR / f"{key}.json"


def _persist(key: str) -> None:
    """把某条缓存写到磁盘（调用方不应持有 `_CACHE_LOCK`）。"""
    path = _cache_path(key)
    if path is None:
        return
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
    if hit is None:
        return
    # 形状不对就别落盘 —— 写进去下次启动会读回来，白屏就是这么来的
    if not _plausible(key, hit["value"]):
        log.warning("缓存 %s 结构异常，不落盘", key)
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {
                    "value": hit["value"],
                    "stale_at": hit["stale_at"],
                    "built_at": hit["built_at"],
                    # 日期存成 ISO 串 —— JSON 里没有 date 类型
                    "built_on": hit["built_on"].isoformat() if hit["built_on"] else None,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)      # 原子替换，避免读到写了一半的文件
    except OSError as exc:
        log.warning("缓存落盘失败 %s：%s", key, str(exc)[:100])


def _plausible(key: str, value) -> bool:
    """落盘/恢复前的**结构校验** —— 缓存文件里可能是任何东西。

    踩过（2026-10-26）：测试造的假数据 `{"rows": [], "anomaly": {}}` 被写进了
    `.cache/board.json`。服务启动时 `_restore()` 照单全收，于是：
      - `rows` 空数组 → 看板 0 个产品
      - `anomaly` 是 `{}` → 前端 `anomaly.windowStart.slice(0,7)` 抛异常
        → 整页卡在「正在取生产数据」，**重启也不恢复**（缓存从磁盘读回来）
    排查方向被带偏很久 —— 它看起来完全是服务的问题。

    所以：形状不对就当没有缓存，重新取一次。宁可慢 100 秒，不要白屏。
    """
    # ⚠️ 先判 `ai` 再判 dict —— `ai` 的缓存值是**列表**（飞书记录数组），
    #    如果先写 `if not isinstance(value, dict): return False`，
    #    它永远到不了自己的分支，每轮都判「结构异常」→ 既不恢复也不落盘，
    #    等于这个缓存从来没生效过（实测踩到，日志里反复刷「结构异常」）。
    if key == "ai":
        return isinstance(value, list)
    if not isinstance(value, dict):
        return False
    if key == "board":
        # ⚠️ `anomaly` 不能只判 `isinstance(dict)` —— **`{}` 也是 dict**，
        #    而那次白屏的缓存正是 `{"rows": [], "anomaly": {}}`：
        #    过了 dict 检查，前端 `windowStart.slice()` 却炸了。
        #    必须验到前端真正用到的两个字段。
        anomaly = value.get("anomaly")
        return (
            isinstance(value.get("rows"), list)
            and isinstance(anomaly, dict)
            and isinstance(anomaly.get("byWorkshop"), list)
            and isinstance(anomaly.get("windowStart"), str)
        )
    if key == "quality":
        return isinstance(value.get("byLabel"), list)
    return True


def _restore(*keys: str) -> None:
    """服务启动时把磁盘上的缓存读回内存 —— **跨天的也恢复**。

    这是「跨天第一次打开要等 100 秒」的解法：`_cached` 对「跨天」的判据是
    `built_on != today`，命中时**先返回旧值、后台再刷新**。恢复昨天的缓存就等于
    把这条路径打开，用户秒开，几秒后后台把新数据补上。

    ⚠️ 代价：跨天第一次打开会**先看到昨天的数字**。受影响的是 `yesterdayInbound`
    （「昨日入库」是按昨天算的）—— 其余（产量、收率、目标、异常、质量）与日期
    无关，跨天不变。前端会检测 `dataAsOf` 不是今天并自动重取一次，见
    `ProductionDashboardView.vue` 的 `autoRefreshIfStale`。

    不恢复的话，跨天第一次访问要走「冷启动同步拉」，实测 100 秒 ——
    那正是这套落盘要解决的问题。

    ⚠️ 恢复前走 `_plausible()` 校验结构 —— 形状不对就当没有（见那里的说明）。
    """
    for key in keys:
        path = _cache_path(key)
        if path is None or not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            built_on = date.fromisoformat(raw["built_on"]) if raw.get("built_on") else None
            if not _plausible(key, raw.get("value")):
                log.warning("缓存 %s 结构异常，丢弃并重取", key)
                continue
            with _CACHE_LOCK:
                _CACHE[key] = {
                    "value": raw["value"],
                    "stale_at": raw["stale_at"],
                    "built_at": raw["built_at"],
                    "built_on": built_on,
                }
            log.info("缓存 %s 已从磁盘恢复（%s）", key, built_on)
        except (OSError, ValueError, KeyError) as exc:
            log.warning("读取缓存 %s 失败：%s", key, str(exc)[:100])


def _cached(key: str, producer, *, built_on: date | None = None, ttl: float | None = None):
    """stale-while-revalidate：**先给旧的、后台刷新**。

    `built_on` 是这批数据算出来时的日期。**跨天即视为过期** —— 缓存里的 rows
    是用「今天」算的（当月目标、昨日入库），过了零点再用就不是今天的数据了。
    不判跨天的话，10 号建的缓存 12 号打开会原样返回，页面上「昨日入库」显示的是
    前天的量（实测踩到过）。

    `ttl` 覆盖全局 TTL（秒）。质量数据用一天，见 `config.QUALITY_CACHE_TTL_SECONDS`。
    后台刷新走的是同一个 producer，所以必须把 ttl 一起传下去 —— 否则后台刷新
    会把长 TTL 悄悄改回 5 分钟（那正是要避免的）。
    """
    now = time.time()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        expired = hit is not None and now >= hit["stale_at"]
        rolled_over = (
            hit is not None and built_on is not None and hit.get("built_on") != built_on
        )
        stale = expired or rolled_over
        if stale and key not in _REFRESHING:
            _REFRESHING.add(key)

    if hit is not None:
        if stale:
            _background_refresh(key, producer, built_on, ttl)
        return hit["value"]

    # 冷启动：只能同步拉一次
    value = producer()
    with _CACHE_LOCK:
        _store(key, value, built_on, ttl)
    return value


def _store(
    key: str,
    value,
    built_on: date | None,
    ttl: float | None = None,
    *,
    persist_async: bool = True,
) -> None:
    """写入缓存（调用方需持有 `_CACHE_LOCK`）。

    `ttl` 为 None 时用全局 `CACHE_TTL_SECONDS`。质量数据单独用更长的 TTL，
    见 `config.QUALITY_CACHE_TTL_SECONDS`。

    **落盘在锁外异步做** —— 在锁里写磁盘会卡住所有并发的缓存读取。
    `persist_async=False` 供**跑完就退**的定时任务用（`app/warm.py`）：
    daemon 线程来不及写完进程就没了，那时要自己同步调 `_persist`。
    """
    _CACHE[key] = {
        "value": value,
        "stale_at": time.time() + (config.CACHE_TTL_SECONDS if ttl is None else ttl),
        "built_at": time.time(),
        "built_on": built_on,
    }
    if persist_async:
        threading.Thread(target=_persist, args=(key,), name=f"persist-{key}", daemon=True).start()


def _cached_at(key: str) -> float | None:
    """这批缓存是**什么时候取回来的**（epoch 秒）；没有则 None。

    页面的「数据截至 HH:MM」用它 —— 它是**数据的时刻**，不是请求的时刻。
    """
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
    return hit["built_at"] if hit else None


def _refresh_now(key: str, producer, built_on: date | None, ttl: float | None = None):
    """**同步**重新取数并更新缓存（前端点「刷新」时用）。

    与 `_cached` 的区别：这里真的等它拉完（几十秒）再返回，而不是先给旧值 ——
    点了刷新还拿到同一份旧数据，那个按钮就没有意义。

    并发保护：拿不到锁就说明已经有人在刷，等他刷完直接用结果，不重复拉。
    """
    started = time.time()
    with _REFRESH_LOCK:
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
        # 等锁这段时间别人已经刷过了 → 用他的结果
        if (
            hit is not None
            and hit.get("built_at", 0) >= started
            and (built_on is None or hit.get("built_on") == built_on)
        ):
            return hit["value"]

        value = producer()
        with _CACHE_LOCK:
            _store(key, value, built_on, ttl)
        log.info("强制刷新 %s 完成", key)
    return value


def _background_refresh(
    key: str, producer, built_on: date | None = None, ttl: float | None = None
) -> None:
    """后台刷新 —— 失败保留旧值（旧数据好过没有），只记日志。"""

    def run():
        try:
            value = producer()
            with _CACHE_LOCK:
                _store(key, value, built_on, ttl)
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

def _iso_local(epoch: float | None) -> Optional[str]:
    """epoch 秒 → 带本地时区偏移的 ISO 串（如 `2026-10-12T08:39:20+08:00`）。

    带上偏移是给前端 `new Date(...)` 用的 —— 不带偏移的裸串会被当成本地时间，
    跨时区看就错了。
    """
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch).astimezone().isoformat()


def _require_feishu() -> None:
    if not config.feishu_configured():
        # 明确 503 而不是编造数据 —— 前端据此显示「未接入」态
        raise HTTPException(status_code=503, detail="飞书凭据未配置，取数服务尚不可用")


def _load_details(fetched: dict | None = None):
    """把 7 张产量明细归一化成 `DetailRecordWithQty` + 标记四车间成员。

    `fetched` 是 `feishu.list_records_many` 的整批结果（见 `_fetch_all`）——
    传进来就不用再逐张拉。为 None 时自己拉（单元测试与单表调用用）。

    关于并发：早先注释写「并发没用、还更容易撞 1254607」，那是**当时没有重试**
    的结论。现在 `_get_with_retry` 会退避重试该码，实测并发 5 路既快又稳
    （57s → 19s，无失败）。详见 `feishu.list_records_many`。
    """
    records: list[contract.DetailRecordWithQty] = []
    four_ws_products: set[str] = set()
    for key, table_id in contract.DETAIL_TABLES.items():
        spec = (contract.BASE_OPERATIONS, table_id)
        raw = fetched.get(spec) if fetched is not None else feishu.list_records(*spec)
        for r in raw or []:
            rec = sources.to_detail_record(r)
            if rec is None:
                continue
            records.append(rec)
            # 会议：四车间当前无在产，暂不录入 —— 按**表来源**判，不按产品名
            if key == "四车间":
                four_ws_products.add(rec.product)
    return records, four_ws_products


def _fetch_all() -> dict:
    """**一次并发**把看板要的 13 张表全拉回来 → `{(base, table): rows}`。

    13 张表串行实测 57 秒，并发 5 路 ~19 秒。合并成一次调用而不是分几批，
    是为了让线程池自己调度 —— 分两批反而要多等一轮。
    """
    specs: list[tuple[str, str]] = [
        (contract.BASE_OPERATIONS, tid) for tid in contract.DETAIL_TABLES.values()
    ]
    specs += [
        (contract.BASE_OPERATIONS, contract.PLAN_TABLE),
        (contract.BASE_OPERATIONS, contract.TARGET_TABLE),
    ]
    specs += [(s.base_token, s.table_id) for s in contract.ANOMALY_SOURCES]
    return feishu.list_records_many(specs)


def _load_anomalies(today: date, fetched: dict | None = None) -> dict:
    """各车间的异常表，按**当月**窗口算闭环率（Owner 2026-10-20）。

    每个车间一个独立 Base。**一个失败不该拖垮其余**，所以逐源 try/except ——
    但**整批拉表**（`list_records_many`）时若某张表抛错，`_fetch_all` 会整体失败。
    这里把两种情况都接住：从 `fetched` 取不到就退回单源重拉，
    再失败就把该车间记进 `failedWorkshops`（宁可显示「某车间取不到」，
    也不给一个偏低的合计数）。
    """
    start = contract.anomaly_window_start(today)
    # 上界：当月口径下是下月 1 号。不加的话未来日期的记录（手工填错）会被算进当月
    end = contract.anomaly_window_end(today)
    stats: list[contract.AnomalyStats] = []
    failed: list[str] = []
    for src in contract.ANOMALY_SOURCES:
        spec = (src.base_token, src.table_id)
        try:
            raw = fetched.get(spec) if fetched is not None else None
            if raw is None:
                raw = feishu.list_records(*spec)
        except feishu.FeishuError as exc:
            log.warning("异常表取数失败 %s code=%s", src.name, exc.code)
            failed.append(src.name)
            continue
        # 飞书 API 是 {"record_id":…, "fields":{…}} 嵌套结构 —— 必须拆，
        # 否则字段全取不到、闭环率静默变 0/0（见 sources.to_anomaly_record）
        rows = [sources.to_anomaly_record(r) for r in raw]
        stats.append(contract.anomaly_stats(src, rows, start, end))

    result = contract.overall_closure(
        stats, start, contract.ANOMALY_WINDOW_MONTHS, end
    )
    result["failedWorkshops"] = failed
    return result


def _load_quality(month: str) -> dict:
    """各产品的 QC 表，按会议规则（2026-10-19）算当月质量合格率。

    **4 张表并发拉**（2026-10-20）：这 4 张是 1000~1200 行的大表，串行实测
    **94.8 秒**，并发 5~8 路后 ~52 秒。它们是冷缓存总时长的主要来源。

    为什么不并进 `_fetch_all`：QC Base 的权限与营运 Base 不同源，历史上
    应用身份读它一直 403。把它并进 `list_records_many` 的话，**一张表失败
    会让整批抛错** → 整个看板 502，连产量都看不到。所以这里单独一批，
    并且**逐源 try/except**：取不到的产品记进 `failedLabels`，前端显示
    「暂不可用」，其余产品照常出数。
    """
    stats: list[contract.QualityStats] = []
    failed: list[str] = []

    def fetch(src: contract.QcSource) -> Optional[list[dict]]:
        try:
            return feishu.list_records(contract.QC_BASE, src.table_id)
        except feishu.FeishuError as exc:
            log.warning("QC 表取数失败 %s code=%s", src.label, exc.code)
            return None

    workers = min(config.FETCH_WORKERS, len(contract.QC_SOURCES)) or 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        raw_by_src = list(pool.map(fetch, contract.QC_SOURCES))

    for src, raw in zip(contract.QC_SOURCES, raw_by_src):
        if raw is None:
            failed.append(src.label)
            continue
        rows = [sources.to_anomaly_record(r) for r in raw]
        stats.append(contract.quality_stats(src, rows, month))

    result = contract.overall_quality(stats, month)
    result["failedLabels"] = failed
    return result


def _board_data(today: date) -> dict:
    """**进入缓存的部分** —— 只有「要查飞书才拿得到」的行与异常。

    `月 / 已过天数 / 数据时刻` 刻意**不在这里**：它们不查飞书、每次请求都能算准，
    冻进缓存只会让页面显示过期的时间（实测：12 号打开显示「本月已过 10 天」）。
    见 `monthly()`。
    """
    _require_feishu()

    month = today.strftime("%Y-%m")
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # 13 张表**一次并发**拉完（串行 57s → 并发 ~19s，见 `_fetch_all`）
    fetched = _fetch_all()

    details, four_ws = _load_details(fetched)
    plan_rows = fetched[(contract.BASE_OPERATIONS, contract.PLAN_TABLE)]
    target_rows = fetched[(contract.BASE_OPERATIONS, contract.TARGET_TABLE)]
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
        "rows": [contract.asdict_row(r) for r in rows],
        "anomaly": _load_anomalies(today, fetched),
        "quality": _quality_cached(month, today),
    }


def _quality_cached(month: str, today: date) -> dict:
    """质量合格率**单独缓存一天**（Owner 2026-10-20 定）。

    为什么要单独一层缓存：QC 那 4 张表 1000~1200 行，并发拉也要 ~50 秒，
    是冷缓存总时长的大头；而**质量结论一天最多变一次**（QC 按天录入）。

    为什么**不看刷新按钮**：用户点「刷新」要的是产量/收率/异常的最新值，
    为了一次刷新多等 50 秒去拉 4000 行几个月都不变的 QC 数据不划算。
    当天新录入的 QC 结果会在缓存过期后出现 —— `built_on` 保证**跨天必重拉**，
    所以最长滞后 24 小时，不会连着两天用同一份。
    """
    return _cached(
        "quality",
        lambda: _load_quality(month),
        built_on=today,
        ttl=config.QUALITY_CACHE_TTL_SECONDS,
    )


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
def monthly(refresh: bool = False) -> dict:
    """当月看板行。取不到就 503 —— **不返回 0 或空行**。

    前端 `productionBoard.ts` 收到非 200 即渲染「未接入」态，
    符合「数据接通前不显示任何数字」的纪律（EA-5.4 §16）。

    `?refresh=1` = **同步**重新取数（前端「刷新」按钮）。不带就是缓存优先，
    先给旧值、后台更新 —— 打开页面因此不会转圈。

    **`月 / 已过天数 / 数据时刻` 每次都现算**（见 `_board_data` 的说明）：
    只有 rows 与 anomaly 走缓存。这样即使行数据是几分钟前的，
    「本月已过 N 天」「数据截至 HH:MM」也永远是对的。
    """
    today = date.today()
    month = today.strftime("%Y-%m")
    try:
        data = (
            _refresh_now("board", lambda: _board_data(today), today)
            if refresh
            else _cached("board", lambda: _board_data(today), built_on=today)
        )
    except feishu.FeishuError as exc:
        log.error("取数失败 code=%s", exc.code)
        raise HTTPException(status_code=502, detail="飞书取数失败") from exc

    built_at = _cached_at("board")
    return {
        "month": month,
        "daysElapsed": contract.days_elapsed(month, today),
        "updatedAt": today.isoformat(),
        # 这批**行数据**是什么时候取回来的（不是本次请求的时刻）。
        # 页面据此标「数据截至」—— 缓存命中时它会早于现在，这是有意的。
        "dataAsOf": _iso_local(built_at),
        "rows": data["rows"],
        "anomaly": data["anomaly"],
        "quality": data.get("quality"),
    }


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
def ai_analysis(full: bool = False) -> dict:
    """AI 工艺分析结论（读「AI工艺分析结果」表）。

    表空时返回 `{"rows": []}` —— 前端显示「待分析」，
    而不是伪造一条结论（AI 结论直接影响生产判断）。

    **`完整报告` 默认不返回**（`full=false`）：
      62 道工序 × 每份 800~2000 字 = 十几万字符，而看板一屏只用得上摘要。
      要读全文的调用方（看板的「查看详情」弹窗）显式传 `?full=1`。
      这条不是性能优化，是**避免把整张表的内容一次性塞进页面** ——
      实测 62 条全文 ~110KB，移动端打开会明显卡。
    """
    _require_feishu()
    try:
        # AI 结果由定时任务每天 16:30 写一次，不随取随变 —— 缓存按
        # `AI_CACHE_TTL_SECONDS`（3 天）走，不跟看板的 12 小时节奏。
        # 见 config 里那段说明：为什么不永久（任务可能连续失败）。
        raw = _cached(
            "ai",
            lambda: feishu.list_records(contract.BASE_AI, contract.AI_TABLE),
            ttl=config.AI_CACHE_TTL_SECONDS,
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
        item = {
            "product": product,
            "process": process,
            "summary": sources.text(f.get("结论摘要")),
            "grade": sources.text(f.get("评级")),
            "analyzedAt": contract.parse_month_day(f.get("分析日期")),
        }
        if full:
            item["report"] = sources.text(f.get("完整报告"))
        rows.append(item)
    return {"rows": rows}
