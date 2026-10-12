"""时间类字段**必须现算**，不能冻在缓存里。

背景（实测踩到）：缓存里存的是整个看板 payload，`month` / `daysElapsed` /
`updatedAt` 都是**建缓存那一刻**算的。10 号建的缓存 12 号打开，
页面显示「本月已过 10 天」—— 用户直接看出来了。

修法（A）：只有 rows / anomaly 进缓存，时间类字段每次请求现算；
另加跨天失效（缓存里嵌着「昨日入库」，过零点就不能再用）。

这些用例**不打真实飞书**：把 `_board_data` 换成假的即可。
"""

from __future__ import annotations

import importlib
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient


def _client(monkeypatch):
    monkeypatch.setenv("HBOS_FEISHU_APP_ID", "cli_fake")
    monkeypatch.setenv("HBOS_FEISHU_APP_SECRET", "fake-secret")
    import app.config as cfg

    importlib.reload(cfg)
    import app.main as main

    importlib.reload(main)
    return main, TestClient(main.app)


def _fake_data(today: date) -> dict:
    return {"rows": [], "anomaly": {"total": 0, "closed": 0, "rate": None}}


def _empty_fetch(main) -> dict:
    """`_fetch_all` 的桩：**键要齐全**（`_board_data` 直接按 key 取）。

    空 dict 会 KeyError —— 那正好说明取数边界漏了表，不该在这里被掩盖。
    """
    specs = [(main.contract.BASE_OPERATIONS, t) for t in main.contract.DETAIL_TABLES.values()]
    specs += [
        (main.contract.BASE_OPERATIONS, main.contract.PLAN_TABLE),
        (main.contract.BASE_OPERATIONS, main.contract.TARGET_TABLE),
    ]
    specs += [(s.base_token, s.table_id) for s in main.contract.ANOMALY_SOURCES]
    return {s: [] for s in specs}


def test_board_data_does_not_carry_time_fields(monkeypatch):
    """沉到缓存的 `_board_data` **不得**返回时间类字段。

    它一旦返回，就会随缓存一起过期 —— 这正是「12 号显示 10 天」的成因。
    """
    main, _ = _client(monkeypatch)
    monkeypatch.setattr(main, "_fetch_all", lambda: _empty_fetch(main))

    data = main._board_data(date(2026, 10, 12))
    assert set(data) == {"rows", "anomaly"}


def test_fetch_all_requests_every_table_the_board_needs(monkeypatch):
    """`_fetch_all` 必须把**每张**要用的表都放进去 ——

    少一张，`_board_data` 就会 KeyError（而不是静默少算），但要早发现。
    """
    main, _ = _client(monkeypatch)
    seen: list[tuple[str, str]] = []

    def fake_many(specs):
        seen.extend(specs)
        return {s: [] for s in specs}

    monkeypatch.setattr(main.feishu, "list_records_many", fake_many)
    main._fetch_all()

    want = {(main.contract.BASE_OPERATIONS, t) for t in main.contract.DETAIL_TABLES.values()}
    want |= {
        (main.contract.BASE_OPERATIONS, main.contract.PLAN_TABLE),
        (main.contract.BASE_OPERATIONS, main.contract.TARGET_TABLE),
    }
    want |= {(s.base_token, s.table_id) for s in main.contract.ANOMALY_SOURCES}
    assert set(seen) == want


def test_days_elapsed_is_fresh_even_when_cache_is_old(monkeypatch):
    """缓存是旧的，`daysElapsed` 仍必须是**今天**的。"""
    main, client = _client(monkeypatch)
    monkeypatch.setattr(main, "_board_data", _fake_data)

    # 先建一份「10 号」的缓存
    main._CACHE.clear()
    main._CACHE["board"] = {
        "value": {"rows": [], "anomaly": {}},
        "stale_at": 0.0,  # 已过期
        "built_at": 0.0,
        "built_on": date(2026, 10, 10),
    }

    body = client.get("/production/monthly").json()
    assert body["daysElapsed"] == date.today().day
    assert body["month"] == date.today().strftime("%Y-%m")
    # `dataAsOf` 是**数据**的时刻（旧），不是本次请求的时刻 —— 页面据此标「数据截至」
    assert body["dataAsOf"] is not None


def test_day_rollover_invalidates_cache(monkeypatch):
    """跨天必须视为过期 —— 否则昨日入库量还是前天的。

    只靠 TTL 不够：10 号建、12 号才有人打开，TTL 早就过了但没人触发刷新时序，
    实测就是这里出的问题。所以 `_cached` 显式比对 `built_on`。
    """
    main, _ = _client(monkeypatch)
    calls = []

    def producer():
        calls.append(1)
        return {"rows": [], "anomaly": {}}

    main._CACHE.clear()
    today = date(2026, 10, 12)

    main._cached("board", producer, built_on=today)
    assert len(calls) == 1

    # 同一份缓存，但 `built_on` 是昨天 → 视为过期，会起后台刷新
    main._CACHE["board"]["built_on"] = today - timedelta(days=1)
    main._CACHE["board"]["stale_at"] = 9e18  # TTL 远未到 —— 单靠 TTL 不会刷
    main._cached("board", producer, built_on=today)
    assert "board" in main._REFRESHING or len(calls) > 1, "跨天没有触发刷新"


def test_dataAsOf_reflects_fetch_time_not_request_time(monkeypatch):
    """`dataAsOf` 取自缓存的 `built_at`，不是 `now()`。"""
    main, client = _client(monkeypatch)
    monkeypatch.setattr(main, "_board_data", _fake_data)

    main._CACHE.clear()
    main._CACHE["board"] = {
        "value": {"rows": [], "anomaly": {}},
        "stale_at": 9e18,
        "built_at": 1_760_000_000.0,  # 一个固定的过去时刻
        "built_on": date.today(),
    }
    body = client.get("/production/monthly").json()
    assert body["dataAsOf"] is not None
    assert body["dataAsOf"].startswith("2025-")  # 2026-10 之前的时刻
