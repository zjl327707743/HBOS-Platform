"""缓存的并发行为 —— 刷新风暴与落盘撞车。

这两条都是实测出来的，不是理论推演：

    刷新风暴：缓存过期后 5 个并发请求起了 **5 个** producer，一起打飞书。
    落盘撞车：多个线程写同一个 `{key}.tmp`，实测 3 次
              `No such file or directory: probe.tmp -> probe.json`。

关键约束：`_cached()` 对过期缓存**本来就该立刻返回旧值**（stale-while-
revalidate），所以测试要断言的是「起了几次 producer」，不是「等了多久」。
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from app import config, main


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    main._CACHE.clear()
    main._INTENTS.clear()
    main._NEGATIVE_UNTIL.clear()
    main._NEGATIVE_ERROR.clear()
    main._PERSIST_LOCKS.clear()
    yield
    main._CACHE.clear()
    main._INTENTS.clear()
    main._NEGATIVE_UNTIL.clear()
    main._NEGATIVE_ERROR.clear()
    main._PERSIST_LOCKS.clear()


def _wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_concurrent_requests_start_only_one_refresh():
    """缓存已过期时，N 个并发请求只能起 **一个** producer。"""
    calls: list[int] = []
    calls_lock = threading.Lock()
    release = threading.Event()

    def producer():
        with calls_lock:
            calls.append(1)
        # 卡住一会儿，保证其余请求能在刷新进行中穿过 `_cached`
        release.wait(timeout=2)
        return {"rows": [], "anomaly": {}}

    # 先放一份**已过期**的缓存
    main._CACHE["board"] = {
        "value": {"rows": [], "anomaly": {}},
        "stale_at": time.time() - 1,
        "built_at": time.time() - 3600,
        "built_on": None,
    }

    threads = [
        threading.Thread(target=main._cached, args=("board", producer))
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    # 等第一个 producer 真正开始，再确保其余请求都已经穿过单飞判断
    assert _wait_for(lambda: len(calls) == 1)
    for _ in range(20):
        assert main._cached("board", producer) is not None
    release.set()
    for t in threads:
        t.join(timeout=5)

    assert _wait_for(lambda: "board" not in main._INTENTS)
    assert len(calls) == 1, f"起了 {len(calls)} 个 producer，single-flight 失效"


def test_expired_cache_returns_stale_value_immediately():
    """过期缓存仍然**立即返回旧值** —— 不能因为要刷新就变成同步等待。"""
    done = threading.Event()

    def producer():
        done.wait(timeout=2)
        return {"rows": [{"label": "new"}], "anomaly": {}}

    main._CACHE["board"] = {
        "value": {"rows": [{"label": "old"}], "anomaly": {}},
        "stale_at": time.time() - 1,
        "built_at": time.time() - 3600,
        "built_on": None,
    }

    started = time.time()
    value = main._cached("board", producer)
    elapsed = time.time() - started
    done.set()

    assert value["rows"][0]["label"] == "old"
    assert elapsed < 0.5, "过期缓存必须立刻返回，不能等 producer"


def test_concurrent_persist_does_not_lose_cache(tmp_path):
    """多线程同时落盘不能互相踩掉临时文件。

    历史缺陷：固定用 `{key}.tmp`，一个线程 rename 走之后另一个线程就
    `No such file or directory`，那一份缓存直接丢了。
    """
    main._CACHE["probe"] = {
        "value": {"payload": list(range(200))},
        "stale_at": time.time() + 3600,
        "built_at": time.time(),
        "built_on": None,
    }

    errors: list[Exception] = []

    def persist():
        try:
            main._persist("probe")
        except Exception as exc:  # noqa: BLE001 - 测试要看到任何异常
            errors.append(exc)

    threads = [threading.Thread(target=persist) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"并发落盘抛错：{errors}"
    raw = json.loads((tmp_path / "probe.json").read_text(encoding="utf-8"))
    assert raw["value"]["payload"] == list(range(200))

    leftovers = list(tmp_path.glob("probe-*.tmp"))
    assert not leftovers, f"临时文件没清干净：{leftovers}"


def test_persist_leaves_no_temp_file_on_failure(tmp_path, monkeypatch):
    """落盘失败也要清掉临时文件，不能每次失败都在 .cache 里留垃圾。"""

    def boom(*a, **kw):
        raise OSError("磁盘满了")

    monkeypatch.setattr(main.os, "replace", boom)
    main._CACHE["probe"] = {
        "value": {"payload": 1},
        "stale_at": time.time() + 3600,
        "built_at": time.time(),
        "built_on": None,
    }
    main._persist("probe")

    assert not list(tmp_path.glob("probe-*.tmp"))


def test_cold_start_runs_producer_once():
    """服务刚起、没有缓存时，N 个并发请求只能拉 **一次** 13 张表。

    早先这里没有单飞：5 个请求各拉一遍，就是 5×100 秒和 5 份飞书配额。
    """
    calls: list[int] = []
    calls_lock = threading.Lock()

    def producer():
        with calls_lock:
            calls.append(1)
        time.sleep(0.05)
        return {"rows": [{"label": "cold"}], "anomaly": {}}

    results: list[dict] = []
    results_lock = threading.Lock()

    def worker():
        value = main._cached("board", producer, built_on=None)
        with results_lock:
            results.append(value)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert len(calls) == 1, f"冷启动起了 {len(calls)} 个 producer"
    assert len(results) == 6
    assert all(r["rows"][0]["label"] == "cold" for r in results)


def test_cold_start_waiter_gets_same_failure_without_reproducing():
    """领导者拉失败时，等待者收到的应是**同一个异常**，不再各自重拉一遍。

    踩过（复审 2026-10-27）：早先等待者只等 `Event`，事件置位后拿不到「失败了」
    这个信息 —— 每个等待者都会依次变成新 leader 再跑一遍 producer。
    实测 6 并发 + 上游立即失败 = 6 次 producer、6 个异常。
    """
    calls: list[int] = []
    calls_lock = threading.Lock()
    release = threading.Event()

    def producer():
        with calls_lock:
            n = len(calls)
            calls.append(1)
        if n == 0:
            release.wait(timeout=2)
            raise RuntimeError("上游挂了")
        return {"rows": [{"label": "second"}], "anomaly": {}}

    errors: list[Exception] = []

    def worker():
        try:
            main._cached("board", producer)
        except Exception as exc:  # noqa: BLE001 - 失败是本用例的预期
            errors.append(exc)

    leader = threading.Thread(target=worker)
    leader.start()
    assert _wait_for(lambda: len(calls) == 1)

    followers = [threading.Thread(target=worker) for _ in range(5)]
    for t in followers:
        t.start()
    release.set()
    leader.join(timeout=5)
    for t in followers:
        t.join(timeout=5)

    assert len(calls) == 1, f"起了 {len(calls)} 个 producer，等待者没有共享失败结果"
    assert len(errors) == 6, "每个等待者都该收到异常"
    assert all(isinstance(e, RuntimeError) for e in errors)


def test_failure_opens_cooldown_window():
    """失败后短时间内不再重试 —— 上游挂了别让每个请求各捅一次。"""
    calls: list[int] = []

    def producer():
        calls.append(1)
        raise RuntimeError("上游挂了")

    for _ in range(3):
        with pytest.raises(RuntimeError):
            main._cached("board", producer)

    assert len(calls) == 1, f"冷却窗口内又重试了 {len(calls)} 次"


def test_cooldown_does_not_hide_stale_value_on_background_refresh():
    """已有旧值时，后台刷新失败**不影响**正在看的人。"""
    calls: list[int] = []
    release = threading.Event()

    def producer():
        calls.append(1)
        release.wait(timeout=2)
        raise RuntimeError("刷新失败")

    main._CACHE["board"] = {
        "value": {"rows": [{"label": "old"}], "anomaly": {}},
        "stale_at": time.time() - 1,
        "built_at": time.time() - 3600,
        "built_on": None,
    }

    assert main._cached("board", producer)["rows"][0]["label"] == "old"
    release.set()
    assert _wait_for(lambda: "board" not in main._INTENTS)
    # 冷却期内再请求，仍拿到旧值而不是抛错
    assert main._cached("board", producer)["rows"][0]["label"] == "old"
    assert len(calls) == 1


def test_persist_does_not_overwrite_newer_snapshot(tmp_path):
    """旧快照不能最后落地覆盖新快照。

    唯一临时名只解决了「不撞文件」，解决不了顺序：线程 A 先读到旧 hit、
    线程 B 后读到新 hit，若 B 先替换、A 后替换，磁盘上留下的是**旧的**。
    服务重启后恢复到过期数据，而且看不出来。
    """
    from datetime import date

    from app import contract

    def snapshot(built_at: float) -> dict:
        return {
            "value": {
                "rows": [
                    {
                        "label": label,
                        "done": 0,
                        "target": 0,
                        "yieldRate": None,
                        "targetYieldRate": None,
                        "yesterdayInbound": None,
                    }
                    for label in contract.ROW_MEMBERS
                ],
                "anomaly": {"byWorkshop": [], "windowStart": "2026-10-01"},
            },
            "stale_at": 9e18,
            "built_at": built_at,
            "built_on": date.today(),
        }

    for built_at in (1.0, 2.0):
        with main._CACHE_LOCK:
            main._CACHE["board"] = snapshot(built_at)
        main._persist("board")

    saved = json.loads((tmp_path / "board.json").read_text(encoding="utf-8"))
    assert saved["built_at"] == 2.0, "磁盘上应当是最后一份（最新）快照"


def test_waiter_holds_intent_across_leader_completion():
    """等待者必须**拿着 leader 的 future** 去等，不能按 key 再查一次。

    踩过（复审 2026-10-28）：`_claim_intent` 早先返回 `(None, None)`，等待者
    再去 `_INTENTS` 里查 —— leader 恰好在这两次读取之间完成、把自己摘掉，
    等待者就查不到任何 intent，`_await_intent` 返回 `(True, None)`，
    `_load_once` 直接返回 `None`，`monthly()` 随后 `data["rows"]` 抛 500。
    """
    key = "board"
    leader_intent, existing, cooling = main._claim_intent(key, shared=False)
    assert leader_intent is not None and existing is None and cooling is None

    # 第二个请求：应当拿到**同一个** intent 对象
    follower_intent, follower_existing, follower_cooling = main._claim_intent(key, shared=False)
    assert follower_intent is None
    assert follower_existing is leader_intent, "等待者必须拿到 leader 的 intent 引用"
    assert follower_cooling is None

    # 模拟 leader 在等待者开始等之前完成并摘掉自己
    with main._CACHE_LOCK:
        main._INTENTS.pop(key, None)
    leader_intent.future.set_result({"rows": [], "anomaly": {}})

    done, outcome = main._await_intent(follower_existing, timeout=1.0)
    assert done is True
    assert outcome == {"rows": [], "anomaly": {}}, "等待者必须拿到 leader 的结果，不是 None"


def test_waiter_gets_leader_exception_across_completion():
    """同样的窗口下，异常也要传过去。"""
    key = "quality"
    leader_intent, _, _ = main._claim_intent(key, shared=False)
    _, follower_existing, _ = main._claim_intent(key, shared=False)

    with main._CACHE_LOCK:
        main._INTENTS.pop(key, None)
    leader_intent.future.set_exception(RuntimeError("上游挂了"))

    done, outcome = main._await_intent(follower_existing, timeout=1.0)
    assert done is True
    assert isinstance(outcome, RuntimeError)


def test_stale_generation_does_not_overwrite_newer_cache():
    """旧 generation 晚回，不得覆盖新 generation 写的缓存。

    踩过（复审 2026-10-28）：等待超时后接管生成新 intent，旧线程还活着。
    它晚回时若仍无条件 `_store()`，新数据就被旧数据盖掉 ——
    实测 follower 拿到 `{'generation':'new'}`，最终缓存却是 `'old'`。
    """
    key = "board"
    old_intent, _, _ = main._claim_intent(key, shared=False)
    # 模拟超时接管：摘掉旧的，建新的
    with main._CACHE_LOCK:
        main._INTENTS.pop(key, None)
    new_intent, _, _ = main._claim_intent(key, shared=False)

    def old_producer():
        return {"generation": "old"}

    def new_producer():
        return {"generation": "new"}

    # 新 generation 先完成
    main._run_refresh(key, new_intent, new_producer, None, None, None)
    # 旧线程晚回
    main._run_refresh(key, old_intent, old_producer, None, None, None)

    assert main._CACHE[key]["value"] == {"generation": "new"}


def test_stale_generation_failure_does_not_open_cooldown():
    """旧 generation 晚失败，不得开启负缓存冷却 —— 否则刚刷新的新数据被白挡 10 秒。"""
    key = "board"
    old_intent, _, _ = main._claim_intent(key, shared=False)
    with main._CACHE_LOCK:
        main._INTENTS.pop(key, None)
    new_intent, _, _ = main._claim_intent(key, shared=False)

    main._run_refresh(key, new_intent, lambda: {"generation": "new"}, None, None, None)

    def boom():
        raise RuntimeError("旧线程失败")

    main._run_refresh(key, old_intent, boom, None, None, None)

    assert key not in main._NEGATIVE_UNTIL, "旧 generation 不该开冷却"
    assert main._CACHE[key]["value"] == {"generation": "new"}
