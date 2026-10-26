"""缓存落盘 —— 服务重启后不该再等 100 秒。

背景：拉 18 张飞书表冷启动要 100 秒。内存缓存在**服务重启后就没了**，而重启
是常事（改代码、机器休眠唤醒）。落盘后重启能直接读回来，跨天则靠 `built_on`
拒绝恢复（昨天的数据是按昨天算的，恢复了会给错值）。

本文件只测**恢复的判据**，不测写入（写入走 `_store` 的后台线程，难以稳定断言）。
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta

import pytest

from app import config, main


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """把缓存目录指到临时目录，别污染仓库里的 .cache/。"""
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    main._CACHE.clear()
    yield tmp_path
    main._CACHE.clear()


def _write(cache_dir, key, *, built_on: date, stale_in: float, value: dict):
    (cache_dir / f"{key}.json").write_text(
        json.dumps(
            {
                "value": value,
                "stale_at": time.time() + stale_in,
                "built_at": time.time(),
                "built_on": built_on.isoformat(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _board_value(rows: list[dict]) -> dict:
    """一份**形状真实**的 board 缓存 —— `rows` 是列表、`anomaly` 是 dict。

    形状不对的会被 `_restore` 的 `_plausible` 校验挡掉（那正是要测的），
    所以这里不能用 `{"rows": [...]}` 这种简化结构。
    """
    return {"rows": rows, "anomaly": {"byWorkshop": [], "windowStart": "2026-10-01"}}


def test_fresh_cache_from_today_is_restored(cache_dir):
    _write(cache_dir, "board", built_on=date.today(), stale_in=3600,
           value=_board_value([{"label": "4BMA", "done": 36}]))
    main._restore("board")
    assert "board" in main._CACHE
    assert main._CACHE["board"]["value"]["rows"][0]["done"] == 36


def test_expired_but_same_day_cache_is_still_restored(cache_dir):
    """当天但过了 TTL 的**要恢复** —— 这是「先给旧值、后台刷新」的前提。

    丢掉它就等于冷启动，用户要等 100 秒；而那份数据只是旧了几小时。
    """
    _write(cache_dir, "board", built_on=date.today(), stale_in=-3600,
           value=_board_value([{"label": "old"}]))
    main._restore("board")
    assert "board" in main._CACHE, "当天过期缓存应当恢复，靠 _cached 后台刷新"


def test_yesterdays_cache_is_restored_so_cross_day_is_fast(cache_dir):
    """跨天的缓存**也要恢复** —— 这是「跨天第一次打开等 100 秒」的解法。

    `_cached` 对跨天的判据是 `built_on != today`，命中时先返回旧值、后台刷新。
    恢复昨天的缓存就等于把这条路径打开：用户秒开，几秒后后台补上新数据。

    代价是第一次打开会先看到昨天的 `yesterdayInbound` —— 前端检测到
    `dataAsOf` 不是今天就自动重取一次。
    """
    _write(cache_dir, "board", built_on=date.today() - timedelta(days=1),
           stale_in=-99999, value=_board_value([{"label": "yesterday"}]))
    main._restore("board")
    assert "board" in main._CACHE
    # built_on 必须原样保留 —— `_cached` 靠它判断「跨天了，该刷新」
    assert main._CACHE["board"]["built_on"] == date.today() - timedelta(days=1)


def test_missing_file_is_ignored(cache_dir):
    main._restore("board", "quality", "ai")
    assert main._CACHE == {}


def test_corrupt_file_is_ignored_not_raised(cache_dir):
    """磁盘上写了一半 / 手改坏了的文件不能让服务起不来。"""
    (cache_dir / "board.json").write_text("{ not json", encoding="utf-8")
    main._restore("board")
    assert "board" not in main._CACHE


def test_persist_writes_atomically(cache_dir):
    """落盘走临时文件 + 原子替换，避免读到写了一半的内容。"""
    main._CACHE["board"] = {
        "value": _board_value([]),
        "stale_at": time.time() + 60,
        "built_at": time.time(),
        "built_on": date.today(),
    }
    main._persist("board")
    written = json.loads((cache_dir / "board.json").read_text(encoding="utf-8"))
    assert written["built_on"] == date.today().isoformat()
    assert not (cache_dir / "board.tmp").exists(), "临时文件应当被替换掉"
