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
import math
import os
import tempfile
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

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
#: 每个 key 一把落盘锁 —— 防止旧快照最后落地覆盖新快照（见 `_persist`）。
_PERSIST_LOCKS: dict[str, threading.Lock] = {}
#: 每个 key 的**在途刷新**。谁拿到它谁负责跑 producer，其余请求等同一个结果。
#:
#: 早先是 `_REFRESHING: set[str]` + `threading.Event` 两张表，只能表达「有人在刷」，
#: 表达不了「刷成功了 / 刷失败了」——于是冷启动 leader 失败后，每个等待者都会
#: 依次变成新 leader 再拉一遍（实测 6 并发 → 6 次 producer、6 个异常）。
#: 现在用 `Future` 同时承载值、异常与完成状态。
_INTENTS: dict[str, "_RefreshIntent"] = {}
#: 失败后的**冷却截止时刻**（epoch 秒）。冷却期内不重试，直接抛上次的异常。
_NEGATIVE_UNTIL: dict[str, float] = {}
_NEGATIVE_ERROR: dict[str, BaseException] = {}
#: 失败冷却时长（秒）—— 上游挂了就别让每个请求各捅一次。
_FAIL_COOLDOWN_SECONDS = 10.0
#: 其余请求等一次在途刷新的上限（秒）。超时后自己接手，避免全挂在一个卡住的线程上。
_COLD_WAIT_SECONDS = 300.0
_CACHE_LOCK = threading.Lock()


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
    """把某条缓存写到磁盘（调用方不应持有 `_CACHE_LOCK`）。

    与同 key 的其他落盘**串行化** —— 唯一临时名只解决了「不撞文件」，
    解决不了「旧快照最后落地把新快照盖掉」：线程 A 先读到旧 hit、线程 B 后
    读到新 hit，若 B 先替换、A 后替换，磁盘上留下的就是**旧的那份**。
    服务重启后恢复到过期数据，而且看不出来。
    """
    path = _cache_path(key)
    if path is None:
        return
    tmp_path: str | None = None
    with _persist_lock(key):
        with _CACHE_LOCK:
            hit = _CACHE.get(key)
        if hit is None:
            return
        try:
            # 形状不对就别落盘 —— 写进去下次启动会读回来，白屏就是这么来的。
            # **放在 try 里**：`_plausible` 要遍历缓存里的任意结构，它自己也可能
            # 抛异常（早先只捕获 `OSError`，异常会打穿到落盘的 daemon 线程）。
            if not _plausible(key, hit["value"]):
                log.warning("缓存 %s 结构异常，不落盘", key)
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            # **唯一临时名**：早先固定用 `{key}.tmp`，两个线程同时落盘时
            # 一个先把文件 rename 走，另一个就 `No such file or directory`。
            # 实测并发刷新时出现过 3 次，缓存直接丢掉。
            with tempfile.NamedTemporaryFile(
                "w",
                dir=str(path.parent),
                prefix=f"{key}-",
                suffix=".tmp",
                delete=False,
                encoding="utf-8",
            ) as tmp:
                tmp_path = tmp.name
                tmp.write(
                    json.dumps(
                        {
                            "value": hit["value"],
                            "stale_at": hit["stale_at"],
                            "built_at": hit["built_at"],
                            # 日期存成 ISO 串 —— JSON 里没有 date 类型
                            "built_on": hit["built_on"].isoformat() if hit["built_on"] else None,
                        },
                        ensure_ascii=False,
                    )
                )
            os.replace(tmp_path, path)      # 原子替换，避免读到写了一半的文件
        except Exception as exc:  # noqa: BLE001 - 落盘失败绝不能影响取数/请求路径
            log.warning("缓存落盘失败 %s：%s", key, str(exc)[:100])
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


def _persist_lock(key: str) -> threading.Lock:
    """每个 key 一把落盘锁（惰性创建）。"""
    with _CACHE_LOCK:
        lock = _PERSIST_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PERSIST_LOCKS[key] = lock
        return lock


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
        if not (
            isinstance(anomaly, dict)
            and isinstance(anomaly.get("byWorkshop"), list)
            and isinstance(anomaly.get("windowStart"), str)
        ):
            return False
        # `rows` 空数组**同样是坏缓存**：`build_rows()` 恒返回 ROW_MEMBERS 的
        # 六个固定行，真实数据里不可能为空。早先这里只判 `isinstance(list)`，
        # 于是 `{"rows": [], …}` 一路过关 —— 那正是「看板 0 个产品」的形态。
        return _plausible_rows(value.get("rows"))
    if key == "quality":
        return isinstance(value.get("byLabel"), list)
    return True


def _plausible_number(v) -> bool:
    """数值字段：int/float 且有限。bool 是 int 的子类，要单独排掉。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    return math.isfinite(v)


def _plausible_optional_number(v) -> bool:
    return v is None or _plausible_number(v)


def _plausible_rows(rows) -> bool:
    """看板行必须**恰好**覆盖 ROW_MEMBERS 的六行，且字段类型对。

    只验「是 list」不够：任意对象列表都能过，前端算术拿到 `undefined`
    会算出 `NaN`，指标显示空白 —— 比白屏更难查。

    ⚠️ 顺序很重要：先逐行确认 `label` 是**字符串**，再取集合比较。
    早先是 `sorted(labels)` 直接排序 —— 混入 `None` 时抛 `TypeError`
    （`'<' not supported between 'str' and 'NoneType'`），而调用方在
    `_persist()` 里只捕获 `OSError`，异常会打穿到落盘线程。
    """
    if not isinstance(rows, list) or not rows:
        return False
    labels: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            return False
        label = row.get("label")
        if not isinstance(label, str):
            return False
        labels.append(label)
    if sorted(labels) != sorted(contract.ROW_MEMBERS):
        return False
    for row in rows:
        if not _plausible_number(row.get("done")) or not _plausible_number(row.get("target")):
            return False
        if not _plausible_optional_number(row.get("yieldRate")):
            return False
        if not _plausible_optional_number(row.get("targetYieldRate")):
            return False
        if not _plausible_optional_number(row.get("yesterdayInbound")):
            return False
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
    时间字段也要验类型：`stale_at` 若是字符串，`now >= hit["stale_at"]` 会抛
    `TypeError`，而且是在请求路径上抛 —— 缓存损坏能把服务变成持续 500。
    """
    for key in keys:
        path = _cache_path(key)
        if path is None or not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            built_on = date.fromisoformat(raw["built_on"]) if raw.get("built_on") else None
            stale_at = raw["stale_at"]
            built_at = raw["built_at"]
            if not (_plausible_number(stale_at) and _plausible_number(built_at)):
                log.warning("缓存 %s 时间字段异常，丢弃并重取", key)
                continue
            if not _plausible(key, raw.get("value")):
                log.warning("缓存 %s 结构异常，丢弃并重取", key)
                continue
            with _CACHE_LOCK:
                _CACHE[key] = {
                    "value": raw["value"],
                    "stale_at": float(stale_at),
                    "built_at": float(built_at),
                    "built_on": built_on,
                }
            log.info("缓存 %s 已从磁盘恢复（%s）", key, built_on)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            log.warning("读取缓存 %s 失败：%s", key, str(exc)[:100])


class _RefreshIntent:
    """一次在途刷新。持有 `Future`，成功值/异常都放在里面。"""

    __slots__ = ("future", "started", "shared")

    def __init__(self, *, shared: bool):
        self.future: Future = Future()
        self.started = time.time()
        #: `shared=True` 表示这是**后台刷新**——别人可以等它，也可以继续拿旧值。
        self.shared = shared


def _fail_cooling(key: str) -> BaseException | None:
    """冷却期内返回上次的异常，否则 None（调用方需持有 `_CACHE_LOCK`）。"""
    until = _NEGATIVE_UNTIL.get(key)
    if until is None:
        return None
    if time.time() >= until:
        _NEGATIVE_UNTIL.pop(key, None)
        _NEGATIVE_ERROR.pop(key, None)
        return None
    return _NEGATIVE_ERROR.get(key) or RuntimeError("上次取数失败，冷却中")


def _record_failure(key: str, exc: BaseException) -> None:
    """记下失败并开启冷却（调用方需持有 `_CACHE_LOCK`）。"""
    _NEGATIVE_UNTIL[key] = time.time() + _FAIL_COOLDOWN_SECONDS
    _NEGATIVE_ERROR[key] = exc


def _is_current(key: str, intent: _RefreshIntent) -> bool:
    """这个 intent 是否仍是该 key 的**当前 generation**（调用方需持 `_CACHE_LOCK`）。"""
    return _INTENTS.get(key) is intent


def _run_refresh(key: str, intent: _RefreshIntent, producer, built_on, ttl, stale_at_fn) -> None:
    """真正执行 producer 并写缓存；成功/失败都通过 `intent.future` 传播。

    ⚠️ **写缓存与写负缓存前必须确认自己还是当前 generation。**
    等待超时后接管会生成新的 intent 并把旧的从 `_INTENTS` 摘掉，但旧线程
    还活着。它晚回时若仍无条件 `_store()`，就会把**旧数据盖在新数据上**
    （实测：follower 拿到 `{'generation':'new'}`，最终缓存却是 `'old'`）。
    同理，旧 generation 晚失败时不能开启全局冷却，否则刚刷新的新数据
    会被无谓地挡住 10 秒。
    """
    try:
        value = producer()
        with _CACHE_LOCK:
            if _is_current(key, intent):
                _store(
                    key,
                    value,
                    built_on,
                    ttl,
                    stale_at=stale_at_fn() if stale_at_fn else None,
                )
                _NEGATIVE_UNTIL.pop(key, None)
                _NEGATIVE_ERROR.pop(key, None)
            else:
                log.info("缓存 %s 的刷新已被新 generation 接管，本轮结果不写入", key)
        intent.future.set_result(value)
    except BaseException as exc:  # noqa: BLE001 - 失败必须让等待者看到同一个异常
        with _CACHE_LOCK:
            if _is_current(key, intent):
                _record_failure(key, exc)
            else:
                log.info("缓存 %s 的旧 generation 失败，不开启冷却：%s", key, type(exc).__name__)
        intent.future.set_exception(exc)
        # 标记「已取回」——后台刷新没人 await 时，不标记会打一条
        # "Future exception was never retrieved" 噪声日志。
        # 这只是抑制噪声：后续 `result()` 仍会抛出同一个异常。
        intent.future.exception()
    finally:
        with _CACHE_LOCK:
            if _INTENTS.get(key) is intent:
                _INTENTS.pop(key, None)


def _claim_intent(
    key: str, *, shared: bool
) -> tuple[_RefreshIntent | None, _RefreshIntent | None, BaseException | None]:
    """在锁内尝试取得该 key 的刷新权。

    返回三样：
      - `(intent, None, None)`  → **你**负责跑 producer；
      - `(None, existing, None)` → 别人在刷，**拿着这个 intent 去等它的 future**；
      - `(None, None, exc)`     → 冷却中，直接抛。

    ⚠️ 第二个返回值必须把 existing intent **原样交出去**。早先这里是
    `(None, None)`，等待者再去 `_INTENTS` 里查一次 —— leader 恰好在这两次
    读取之间完成并从 `_INTENTS` 摘掉自己，等待者就什么都查不到，
    `_await_intent` 返回 `(True, None)`，`_load_once` 直接返回 `None`，
    `monthly()` 随后 `data["rows"]` 抛 500。已用最小竞态复现。
    """
    with _CACHE_LOCK:
        cooling = _fail_cooling(key)
        if cooling is not None:
            return None, None, cooling
        existing = _INTENTS.get(key)
        if existing is not None:
            return None, existing, None
        intent = _RefreshIntent(shared=shared)
        _INTENTS[key] = intent
        return intent, None, None


def _await_intent(intent: _RefreshIntent, timeout: float) -> tuple[bool, Any]:
    """等**指定的那个** intent。返回 `(完成?, 值或异常)`。

    显式传入 intent 而不是按 key 再查一次 —— 见 `_claim_intent` 的说明。

    `future.result()` 会把 leader 的异常**重新抛出**（不是返回），所以这里要
    自己接住再以返回值的形式交给调用方 —— 调用方据此 `raise outcome`，
    保持「等待者收到同一个异常」的语义。
    """
    try:
        return True, intent.future.result(timeout=timeout)
    except TimeoutError:
        return False, None
    except BaseException as exc:  # noqa: BLE001 - leader 的异常原样转交
        return True, exc


def _cached(
    key: str,
    producer,
    *,
    built_on: date | None = None,
    ttl: float | None = None,
    stale_at_fn: Callable[[], float] | None = None,
):
    """stale-while-revalidate：**先给旧的、后台刷新**。

    `built_on` 是这批数据算出来时的日期。**跨天即视为过期** —— 缓存里的 rows
    是用「今天」算的（当月目标、昨日入库），过了零点再用就不是今天的数据了。
    不判跨天的话，10 号建的缓存 12 号打开会原样返回，页面上「昨日入库」显示的是
    前天的量（实测踩到过）。

    `ttl` 覆盖全局 TTL（秒）。质量数据用一天，见 `config.QUALITY_CACHE_TTL_SECONDS`。
    `stale_at_fn` 是**过期时刻函数**，每次写缓存时求值一次 —— AI 结果用
    （下一个 16:35 才失效，见 `config.seconds_until_ai_refresh`）。
    用函数而不是固定值：缓存可能在任何时刻被重建，过期点要跟着重建时刻走。

    ttl / stale_at_fn 都要传给后台刷新 —— 否则后台刷新会把长 TTL 悄悄改回默认值。
    """
    now = time.time()
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        expired = hit is not None and now >= hit["stale_at"]
        rolled_over = (
            hit is not None and built_on is not None and hit.get("built_on") != built_on
        )
        stale = expired or rolled_over

    if hit is not None:
        if stale:
            # **single-flight**：只有抢到刷新权的请求起线程，其余直接拿旧值。
            intent, _existing, cooling = _claim_intent(key, shared=True)
            if cooling is not None:
                log.warning("缓存 %s 上次取数失败、冷却中，继续用旧值", key)
            elif intent is not None:
                threading.Thread(
                    target=_run_refresh,
                    args=(key, intent, producer, built_on, ttl, stale_at_fn),
                    name=f"refresh-{key}",
                    daemon=True,
                ).start()
        return hit["value"]

    # 冷启动：没有旧值可给，只能同步拉。**同样单飞** —— 服务刚起时若 5 个请求
    # 同时进来，早先会各拉一遍 13 张表（5×100 秒、5 份飞书配额）。
    # 而且 leader 失败时，等待者必须收到**同一个异常**，不能各自再拉一遍。
    return _load_once(key, producer, built_on, ttl, stale_at_fn)


def _load_once(
    key: str,
    producer,
    built_on: date | None,
    ttl: float | None,
    stale_at_fn: Callable[[], float] | None,
):
    """冷启动的 single-flight：领导者在**当前线程**跑，其余等同一个 Future。"""
    intent, existing, cooling = _claim_intent(key, shared=False)
    if cooling is not None:
        raise cooling
    if intent is None:
        # 别人在刷：等**它那一个** future（`existing` 由 claim 一并交出）。
        # 超时说明它卡住了 —— 重新抢一次刷新权（新 generation），
        # 而不是递归回来再等同一个 future（那会永远等下去）。
        assert existing is not None
        done, outcome = _await_intent(existing, _COLD_WAIT_SECONDS)
        if not done:
            log.warning("等待 %s 的在途刷新超时，尝试接管", key)
            with _CACHE_LOCK:
                stale_intent = _INTENTS.get(key)
                # 只接管**确实是老的那一个**：期间它已完成的话，直接走下面的重新读取
                if stale_intent is not None and time.time() - stale_intent.started >= _COLD_WAIT_SECONDS:
                    _INTENTS.pop(key, None)
            return _load_once(key, producer, built_on, ttl, stale_at_fn)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    _run_refresh(key, intent, producer, built_on, ttl, stale_at_fn)
    # `_run_refresh` 已把结果写进 future；这里同步取出（要么值、要么原异常）
    return intent.future.result()


def _store(
    key: str,
    value,
    built_on: date | None,
    ttl: float | None = None,
    *,
    persist_async: bool = True,
    stale_at: float | None = None,
) -> None:
    """写入缓存（调用方需持有 `_CACHE_LOCK`）。

    `ttl` 为 None 时用全局 `CACHE_TTL_SECONDS`。质量数据单独用更长的 TTL，
    见 `config.QUALITY_CACHE_TTL_SECONDS`。

    `stale_at` 直接给**绝对过期时刻**（epoch 秒），优先于 `ttl`。
    AI 结果用它 —— 那种「每天固定时刻更新一次」的数据，按间隔算 TTL 是错的
    （见 `config.seconds_until_ai_refresh` 的说明）。

    **落盘在锁外异步做** —— 在锁里写磁盘会卡住所有并发的缓存读取。
    `persist_async=False` 供**跑完就退**的定时任务用（`app/warm.py`）：
    daemon 线程来不及写完进程就没了，那时要自己同步调 `_persist`。
    """
    _CACHE[key] = {
        "value": value,
        "stale_at": stale_at if stale_at is not None else time.time() + (
            config.CACHE_TTL_SECONDS if ttl is None else ttl
        ),
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


def _refresh_now(
    key: str,
    producer,
    built_on: date | None,
    ttl: float | None = None,
    stale_at_fn: Callable[[], float] | None = None,
):
    """**同步**重新取数并更新缓存（前端点「刷新」时用）。

    与 `_cached` 的区别：这里真的等它拉完（几十秒）再返回，而不是先给旧值 ——
    点了刷新还拿到同一份旧数据，那个按钮就没有意义。

    并发保护：**与后台刷新共用同一个 per-key 在途标记**。早先这里是独立的
    `_REFRESH_LOCK`，后台刷新在跑时手动刷新会再起一个 producer ——
    实测两个一起打飞书（`['bg', 'manual']`）。

    `stale_at_fn` 是**每次重新求值**的过期时刻函数（AI 用）—— 不能传固定值：
    刷新发生在 16:30 前后时，算出来的下一个失效点是不同的。
    """
    started = time.time()
    intent, existing, cooling = _claim_intent(key, shared=False)
    if cooling is not None:
        raise cooling
    if intent is None:
        # 已经有人在刷（后台或另一个手动）—— 等它的结果，不重复拉。
        assert existing is not None
        done, outcome = _await_intent(existing, _COLD_WAIT_SECONDS)
        if done and isinstance(outcome, BaseException):
            raise outcome
        if done:
            return outcome
        # 等超时：接管一次
        with _CACHE_LOCK:
            stale_intent = _INTENTS.get(key)
            if stale_intent is not None and time.time() - stale_intent.started >= _COLD_WAIT_SECONDS:
                _INTENTS.pop(key, None)
        return _refresh_now(key, producer, built_on, ttl, stale_at_fn)

    # 抢到刷新权后，再确认一次「等锁期间别人是否已经刷过了」
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
    if (
        hit is not None
        and hit.get("built_at", 0) >= started
        and (built_on is None or hit.get("built_on") == built_on)
    ):
        with _CACHE_LOCK:
            if _INTENTS.get(key) is intent:
                _INTENTS.pop(key, None)
        intent.future.set_result(hit["value"])
        return hit["value"]

    _run_refresh(key, intent, producer, built_on, ttl, stale_at_fn)
    log.info("强制刷新 %s 完成", key)
    return intent.future.result()


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
        # 否则字段全取不到、闭环率静默变 0/0（见 sources.to_anomaly_record）。
        #
        # 转换/统计阶段的 `ValueError` / `TypeError`（上游字段形状变了）
        # **也要算进这一源的失败** —— 早先只兜 `FeishuError`，一个格式异常
        # 就能把整个 /production/monthly 打成 500，其余车间的数据一起没了。
        try:
            rows = [sources.to_anomaly_record(r) for r in raw]
            stats.append(contract.anomaly_stats(src, rows, start, end))
        except Exception as exc:  # noqa: BLE001 - 单源格式异常不该拖垮整块
            log.warning(
                "异常表数据异常 %s（%s）：%s", src.name, type(exc).__name__, str(exc)[:120]
            )
            failed.append(src.name)

    result = contract.overall_closure(
        stats, start, contract.ANOMALY_WINDOW_MONTHS, end
    )
    # 前端要能区分「部分车间失败」和「全部车间失败」：
    #   - 部分失败 → 合计数偏低，必须标「部分口径」
    #   - 全部失败 → total=0 且 rate=None，**不能**显示成「当月无异常记录」
    # 只给 failedWorkshops 不够 —— 前端不知道一共有几个车间。
    result["failedWorkshops"] = failed
    result["sourceCount"] = len(contract.ANOMALY_SOURCES)
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
        # 同 `_load_anomalies`：转换阶段的格式异常也要算该源失败，
        # 否则一张表字段漂移就让整个质量面板（含已成功的表）一起 500。
        try:
            rows = [sources.to_anomaly_record(r) for r in raw]
            stats.append(contract.quality_stats(src, rows, month))
        except Exception as exc:  # noqa: BLE001 - 单源格式异常不该拖垮整块
            log.warning(
                "QC 表数据异常 %s（%s）：%s", src.label, type(exc).__name__, str(exc)[:120]
            )
            failed.append(src.label)

    result = contract.overall_quality(stats, month)
    result["failedLabels"] = failed
    # 与异常同理：前端要能判「部分 QC 失败 → 合格率是部分口径」
    result["sourceCount"] = len(contract.QC_SOURCES)
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
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 兜底：任何未包装的上游异常都算 502
        # 客户端边界已经尽量把网络/解析错误包成 `FeishuError`，但线程池、
        # 缓存层或未来新增的调用仍可能抛出别的东西 —— 让它变成 500 会把
        # 上游故障说成「服务自身 bug」，前端的重试提示也会跑偏。
        log.exception("取数出现未包装异常：%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="上游取数异常") from exc

    built_at = _cached_at("board")
    # 质量**不在 board 快照里**，而是响应时独立读它自己的缓存。
    #
    # 早先 quality 是在 `_board_data()` 里取的，于是它被冻进了 board 的快照：
    # 质量过期时 board 拿到的是**旧质量值**，后台刷新只更新 `quality` 这个 key，
    # board 快照里的那份再也不会变 —— 页面却用 board 的 `built_at` 标「数据截至」，
    # 把上一天的质量数据标成刚取回来的。实测复现：
    #     board.quality.rate = 0.9，quality 缓存刷新成 0.8，board 仍是 0.9
    # 现在两者各有各的时间戳，前端可以如实展示。
    quality, quality_at = _quality_snapshot(month, today)
    return {
        "month": month,
        "daysElapsed": contract.days_elapsed(month, today),
        "updatedAt": today.isoformat(),
        # 这批**行数据**是什么时候取回来的（不是本次请求的时刻）。
        # 页面据此标「数据截至」—— 缓存命中时它会早于现在，这是有意的。
        "dataAsOf": _iso_local(built_at),
        # 质量数据**自己的**取回时刻。它可能比 board 旧，前端要分开标。
        "qualityDataAsOf": _iso_local(quality_at),
        "rows": data["rows"],
        "anomaly": data["anomaly"],
        "quality": quality,
    }


def _quality_snapshot(month: str, today: date) -> tuple[dict | None, float | None]:
    """质量合格率 + 它的取回时刻。

    **失败不拖垮看板**：质量只是四个 KPI 之一，QC 表取不到时该显示
    「暂不可用」，而不是让整个 `/monthly` 变成 502（连产量都看不到）。
    `_load_quality` 已逐源 try/except，这里再兜一层是防缓存层/线程池的意外异常。
    """
    try:
        value = _quality_cached(month, today)
    except Exception as exc:  # noqa: BLE001 - 质量失败不该影响产量
        log.warning("质量取数失败，本轮不返回质量：%s", str(exc)[:120])
        return None, None
    return value, _cached_at("quality")


@app.get("/production/yesterday")
def yesterday() -> dict:
    """昨日入库量（按收料日期）。已含在 `/monthly` 的 row 里，此处单列便于复用。

    ⚠️ `date` 必须是**昨日**的日期。早先取的是 `monthly().updatedAt`，
    而那个字段是「今天」—— 接口名叫 yesterday 却报今天的日期，
    调用方按它去核对入库量会错位一天。
    """
    today = date.today()
    data = monthly()
    return {
        "date": (today - timedelta(days=1)).isoformat(),
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
        # AI 结果表**只在每天 16:30 那轮定时任务里变**，除此之外一动不动。
        #
        # 所以不能用「固定间隔 TTL」：间隔短了（如 30 分钟）一天白拉 47 次；
        # 间隔长了（如 12 小时）16:30 写进去的新结论当天看不到。
        #
        # 用**过期时刻函数**：缓存活到「下一个 16:35」为止。见
        # `config.seconds_until_ai_refresh()` 的说明。
        raw = _cached(
            "ai",
            lambda: feishu.list_records(contract.BASE_AI, contract.AI_TABLE),
            stale_at_fn=lambda: time.time() + config.seconds_until_ai_refresh(time.time()),
        )
    except feishu.FeishuError as exc:
        log.error("AI 结果读取失败 code=%s", exc.code)
        raise HTTPException(status_code=502, detail="AI 结果读取失败") from exc
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 与 monthly 同理：未包装异常也算上游失败
        log.exception("AI 结果读取出现未包装异常：%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="AI 结果读取异常") from exc

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
