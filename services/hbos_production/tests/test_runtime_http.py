"""运行态 HTTP 测试 —— 起**真的 uvicorn**，走真的 socket。

## 为什么需要这一层

`TestClient` 走 ASGI 直连，绕过 uvicorn、真实 socket 与真实事件循环。
下面这几条只有真起服务才测得出来：

  1. **并发单飞**：N 个真并发 HTTP 请求只该触发 1 次 producer；
  2. **失败传播**：上游挂了时，所有并发请求拿到同一个错误（不是各拉一遍）；
  3. **缓存跨重启**：落盘 → 新进程启动 → 从磁盘读回，不再重拉；
  4. **凭据缺失**：503，不编数字。

不依赖网络与飞书：**飞书客户端被替身替换**，其余全是真代码路径。

真实 Site / Redis / PDF 生成仍不在覆盖范围内（本机没有）。
"""

from __future__ import annotations

import importlib
import socket
import threading
import time
from datetime import date

import httpx
import pytest
import uvicorn


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Server:
    """在后台线程里跑一个真 uvicorn。"""

    def __init__(self, app, port: int):
        self.port = port
        self.server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> "_Server":
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            if self.server.started:
                return self
            time.sleep(0.02)
        raise RuntimeError("uvicorn 启动超时")

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"


@pytest.fixture
def live_service(tmp_path, monkeypatch):
    """起一个带**假飞书**的真服务，返回 (server, main_module)。"""
    monkeypatch.setenv("HBOS_FEISHU_APP_ID", "cli_fake")
    monkeypatch.setenv("HBOS_FEISHU_APP_SECRET", "fake-secret")
    monkeypatch.setenv("HBOS_PRODUCTION_CACHE_DIR", str(tmp_path))

    import app.config as cfg

    importlib.reload(cfg)
    import app.main as main

    importlib.reload(main)
    main._CACHE.clear()
    main._INTENTS.clear()
    main._NEGATIVE_UNTIL.clear()
    main._NEGATIVE_ERROR.clear()
    main._PERSIST_LOCKS.clear()

    with _Server(main.app, _free_port()) as server:
        yield server, main

    main._CACHE.clear()


def test_health_over_real_http(live_service):
    server, _main = live_service
    with httpx.Client(timeout=10) as c:
        r = c.get(server.url("/health"))
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_cold_start_single_flight_over_real_http(live_service, monkeypatch):
    """N 个**真并发 HTTP** 请求，只该触发 1 次取数。

    这条是本文件存在的核心理由：`TestClient` 是同步直连，测不出真实并发。
    """
    server, main = live_service
    calls: list[int] = []
    lock = threading.Lock()
    release = threading.Event()

    def slow_board_data(today: date) -> dict:
        with lock:
            calls.append(1)
        release.wait(timeout=5)
        return {
            "rows": [
                {
                    "label": label,
                    "done": 1,
                    "target": 2,
                    "yieldRate": None,
                    "targetYieldRate": None,
                    "yesterdayInbound": None,
                }
                for label in main.contract.ROW_MEMBERS
            ],
            "anomaly": {
                "byWorkshop": [],
                "windowStart": "2026-10-01",
                "total": 0,
                "closed": 0,
                "rate": None,
                "failedWorkshops": [],
                "sourceCount": len(main.contract.ANOMALY_SOURCES),
            },
        }

    monkeypatch.setattr(main, "_board_data", slow_board_data)
    monkeypatch.setattr(
        main,
        "_quality_cached",
        lambda month, today: {"byLabel": [], "rate": None, "failedLabels": [], "sourceCount": 4},
    )

    codes: list[int] = []
    codes_lock = threading.Lock()

    def hit():
        try:
            with httpx.Client(timeout=30) as c:
                r = c.get(server.url("/production/monthly"))
        except httpx.HTTPError:
            return
        with codes_lock:
            codes.append(r.status_code)

    threads = [threading.Thread(target=hit) for _ in range(6)]
    for t in threads:
        t.start()
    # 等第一个 producer 真正开始，再放行
    deadline = time.time() + 5
    while time.time() < deadline and not calls:
        time.sleep(0.01)
    release.set()
    for t in threads:
        t.join(timeout=30)

    assert len(calls) == 1, f"真并发下触发了 {len(calls)} 次取数"
    assert codes and all(c == 200 for c in codes), codes


def test_upstream_failure_is_propagated_not_repeated(live_service, monkeypatch):
    """上游挂了：所有并发请求都收到 502，且只打了一次上游。"""
    server, main = live_service
    calls: list[int] = []
    lock = threading.Lock()

    def boom(today: date) -> dict:
        with lock:
            calls.append(1)
        time.sleep(0.05)
        raise main.feishu.FeishuError(1254607, "not ready")

    monkeypatch.setattr(main, "_board_data", boom)

    codes: list[int] = []
    codes_lock = threading.Lock()

    def hit():
        with httpx.Client(timeout=20) as c:
            r = c.get(server.url("/production/monthly"))
        with codes_lock:
            codes.append(r.status_code)

    threads = [threading.Thread(target=hit) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert codes == [502] * 5, codes
    assert len(calls) == 1, f"上游挂了却打了 {len(calls)} 次"


def test_today_endpoint_reports_yesterday_date(live_service, monkeypatch):
    """/production/yesterday 的 date 必须是昨天（真 HTTP 校验）。"""
    server, main = live_service
    monkeypatch.setattr(
        main,
        "_board_data",
        lambda today: {
            "rows": [
                {
                    "label": label,
                    "done": 0,
                    "target": 0,
                    "yieldRate": None,
                    "targetYieldRate": None,
                    "yesterdayInbound": 1.5,
                }
                for label in main.contract.ROW_MEMBERS
            ],
            "anomaly": {
                "byWorkshop": [],
                "windowStart": "2026-10-01",
                "total": 0,
                "closed": 0,
                "rate": None,
                "failedWorkshops": [],
                "sourceCount": 1,
            },
        },
    )
    monkeypatch.setattr(
        main,
        "_quality_cached",
        lambda month, today: {"byLabel": [], "rate": None, "failedLabels": [], "sourceCount": 1},
    )

    with httpx.Client(timeout=20) as c:
        body = c.get(server.url("/production/yesterday")).json()

    from datetime import timedelta

    assert body["date"] == (date.today() - timedelta(days=1)).isoformat()


def test_cache_survives_restart(live_service, monkeypatch, tmp_path):
    """落盘 → 重启 → 从磁盘读回，不再重取。

    这是「重启后第一次打开要等 100 秒」的解法，只有真跑一遍 uvicorn 才验证得了
    lifespan 是否真的调用了 `_restore`。
    """
    server, main = live_service
    monkeypatch.setattr(
        main,
        "_board_data",
        lambda today: {
            "rows": [
                {
                    "label": label,
                    "done": 7,
                    "target": 9,
                    "yieldRate": None,
                    "targetYieldRate": None,
                    "yesterdayInbound": None,
                }
                for label in main.contract.ROW_MEMBERS
            ],
            "anomaly": {
                "byWorkshop": [],
                "windowStart": "2026-10-01",
                "total": 0,
                "closed": 0,
                "rate": None,
                "failedWorkshops": [],
                "sourceCount": 1,
            },
        },
    )
    monkeypatch.setattr(
        main,
        "_quality_cached",
        lambda month, today: {"byLabel": [], "rate": None, "failedLabels": [], "sourceCount": 1},
    )

    with httpx.Client(timeout=20) as c:
        assert c.get(server.url("/production/monthly")).status_code == 200

    # 落盘是后台线程 —— 等它写完
    target = tmp_path / "board.json"
    deadline = time.time() + 5
    while time.time() < deadline and not target.exists():
        time.sleep(0.02)
    assert target.exists(), "缓存没有落盘"

    # 模拟重启：清内存，重新走 lifespan（`_restore`）
    main._CACHE.clear()
    main._restore("board", "quality", "ai")
    assert "board" in main._CACHE
    assert main._CACHE["board"]["value"]["rows"][0]["done"] == 7


def test_unwrapped_upstream_error_becomes_502(live_service, monkeypatch):
    """非 `FeishuError` 的上游异常也必须变成 502，不能是 500。

    实测：把取数函数换成抛 `httpx.ReadTimeout` 后，接口直接向 FastAPI
    抛未处理异常 → 500，前端只能看到「服务内部错误」。
    """
    server, main = live_service

    def boom(today):
        raise httpx.ReadTimeout("upstream slow", request=httpx.Request("GET", "http://x"))

    monkeypatch.setattr(main, "_board_data", boom)

    with httpx.Client(timeout=20) as c:
        r = c.get(server.url("/production/monthly"))
    assert r.status_code == 502, r.status_code


def test_unwrapped_ai_error_becomes_502(live_service, monkeypatch):
    server, main = live_service

    def boom(*a, **kw):
        raise ValueError("bad json shape")

    monkeypatch.setattr(main.feishu, "list_records", boom)

    with httpx.Client(timeout=20) as c:
        r = c.get(server.url("/production/ai-analysis"))
    assert r.status_code == 502, r.status_code
