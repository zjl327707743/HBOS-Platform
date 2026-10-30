"""预热脚本的离线单测 —— 不起服务、不打飞书。

真正要钉住的是两条分支：

    服务在跑  → 走 HTTP，带 refresh=1（不带就只是读缓存，预热等于没做）
    服务没跑  → 自己算一遍，**同步落盘**（后台 daemon 线程会在进程退出时丢）

第二条尤其重要：`_store` 的落盘是异步的，脚本跑完就退，异步线程来不及写完 ——
这里是踩过的坑，用 `persist_async=False` + 手动 `_persist` 解决。
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from app import config, main, warm


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    main._CACHE.clear()
    yield tmp_path
    main._CACHE.clear()


def test_via_service_sends_refresh_flag(monkeypatch):
    """必须带 refresh=1 —— 不带的话服务直接返回旧缓存，预热没意义。"""
    seen = {}

    def fake_get(url, params=None, timeout=None):
        seen["url"] = url
        seen["params"] = params
        req = httpx.Request("GET", url)
        return httpx.Response(
            200,
            request=req,
            json={"rows": [{"label": "4BMA"}], "anomaly": {"closed": 1, "total": 2},
                  "quality": {"rate": 1.0}},
        )

    monkeypatch.setattr(warm.httpx, "get", fake_get)
    assert warm._warm_via_service() is warm.WarmResult.SUCCESS
    assert seen["params"] == {"refresh": "1"}
    assert "/production/monthly" in seen["url"]


def test_read_timeout_does_not_fall_back_to_direct(monkeypatch):
    """读超时 ≠ 服务不可达 —— 服务很可能正在慢慢拉飞书。

    早先把所有 `httpx.HTTPError` 都归为不可达，超时后立刻直连再拉一轮，
    把「慢」放大成「双倍请求」。
    """
    def fake_get(url, params=None, timeout=None):
        req = httpx.Request("GET", url)
        raise httpx.ReadTimeout("server slow", request=req)

    monkeypatch.setattr(warm.httpx, "get", fake_get)
    assert warm._warm_via_service() is warm.WarmResult.FAILED


def test_connect_error_falls_back_to_direct(monkeypatch):
    def fake_get(*a, **kw):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(warm.httpx, "get", fake_get)
    assert warm._warm_via_service() is warm.WarmResult.UNREACHABLE


def test_service_502_does_not_trigger_second_fetch(monkeypatch):
    """服务返回 502 = 飞书取数失败（多半撞了限流）。

    这时**不能**再直连重试一次 —— 再打一遍只会让限流更糟。
    光返回 `False` 不够：调用方分不清「服务没起」和「服务起了但取数失败」。
    """

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(502, request=httpx.Request("GET", url), text="飞书取数失败")

    monkeypatch.setattr(warm.httpx, "get", fake_get)
    assert warm._warm_via_service() is warm.WarmResult.FAILED


def test_main_entry_does_not_fall_back_after_502(monkeypatch):
    """502 时**不得**调用 `_warm_direct()` —— 这是那条注释真正的约束。"""
    monkeypatch.setattr(warm, "_warm_via_service", lambda *a, **kw: warm.WarmResult.FAILED)
    called = []
    monkeypatch.setattr(warm, "_warm_direct", lambda: called.append(1) or True)

    assert warm.main_entry() == 1
    assert not called, "502 之后不能再直连拉一遍飞书"


def test_main_entry_falls_back_when_service_is_down(monkeypatch):
    monkeypatch.setattr(warm, "_warm_via_service", lambda *a, **kw: warm.WarmResult.UNREACHABLE)
    monkeypatch.setattr(warm, "_warm_direct", lambda: True)
    assert warm.main_entry() == 0


def test_direct_mode_persists_synchronously(monkeypatch, cache_dir):
    """直连模式必须**同步**落盘 —— 脚本跑完就退，异步线程会丢。"""
    from app import contract

    rows = [
        {
            "label": label,
            "done": 36 if label == "4BMA" else 0,
            "target": 0,
            "yieldRate": None,
            "targetYieldRate": None,
            "yesterdayInbound": None,
        }
        for label in contract.ROW_MEMBERS
    ]
    monkeypatch.setattr(
        main,
        "_board_data",
        lambda today: {
            "rows": rows,
            # 形状要真实 —— `_persist` 会过 `_plausible` 校验，缺 byWorkshop / byLabel
            # 会被判成结构异常而不落盘（那正是这道校验要挡的东西）
            "anomaly": {"byWorkshop": [], "windowStart": "2026-10-01", "closed": 1, "total": 2},
        },
    )
    # 质量现在与 board 解耦，预热要单独取一次（见 `_warm_direct`）
    monkeypatch.setattr(
        main,
        "_quality_cached",
        lambda month, today: {"byLabel": [], "rate": 1.0, "tested": 10},
    )
    assert warm._warm_direct() is True

    board = json.loads((cache_dir / "board.json").read_text(encoding="utf-8"))
    quality = json.loads((cache_dir / "quality.json").read_text(encoding="utf-8"))
    assert board["built_on"] == date.today().isoformat()
    row = next(r for r in board["value"]["rows"] if r["label"] == "4BMA")
    assert row["done"] == 36
    assert "quality" not in board["value"], "质量不该再冻进 board 快照"
    assert quality["value"]["rate"] == 1.0


def test_direct_mode_failure_is_reported_not_raised(monkeypatch, cache_dir):
    def boom(today):
        raise RuntimeError("飞书挂了")

    monkeypatch.setattr(main, "_board_data", boom)
    assert warm._warm_direct() is False      # 返回 False，不抛栈


def test_main_entry_requires_credentials(monkeypatch):
    monkeypatch.setattr(config, "FEISHU_APP_ID", "")
    monkeypatch.setattr(config, "FEISHU_APP_SECRET", "")
    assert warm.main_entry() == 1


def test_200_with_non_json_body_is_failed(monkeypatch):
    """200 + HTML（代理错误页）不该冒成异常。"""
    def fake_get(url, params=None, timeout=None):
        return httpx.Response(200, request=httpx.Request("GET", url), text="<html>oops</html>")

    monkeypatch.setattr(warm.httpx, "get", fake_get)
    assert warm._warm_via_service() is warm.WarmResult.FAILED


def test_200_with_non_object_json_is_failed(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return httpx.Response(200, request=httpx.Request("GET", url), text='["not","an","object"]')

    monkeypatch.setattr(warm.httpx, "get", fake_get)
    assert warm._warm_via_service() is warm.WarmResult.FAILED
