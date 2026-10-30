"""服务的冒烟测试 —— 只测**行为边界**，不打真实飞书。

重点验证一条纪律：**凭据没配时不返回任何数字**（EA-5.4 §16）。
这条比接口通不通更重要 —— 看板给车间经理看，编造的数据会被当成真实产量。
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


def _client(monkeypatch, app_id: str = "", app_secret: str = ""):
    monkeypatch.setenv("HBOS_FEISHU_APP_ID", app_id)
    monkeypatch.setenv("HBOS_FEISHU_APP_SECRET", app_secret)
    # 重新加载 config 与 main，让环境变量生效（模块级读了 env）
    import app.config as cfg

    importlib.reload(cfg)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_health_reports_credential_state(monkeypatch):
    c = _client(monkeypatch, "", "")
    r = c.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["feishuConfigured"] is False


def test_monthly_returns_503_without_credentials(monkeypatch):
    """凭据没配 → 503，且**响应体里没有任何数字**。

    前端据此渲染「未接入」态。若这里改成返回 0，看板就会显示一片 0%，
    被读成「本月没产量」。
    """
    c = _client(monkeypatch, "", "")
    r = c.get("/production/monthly")
    assert r.status_code == 503
    assert "rows" not in r.text and "0" not in r.text


def test_yesterday_returns_503_without_credentials(monkeypatch):
    c = _client(monkeypatch, "", "")
    assert c.get("/production/yesterday").status_code == 503


def test_ai_analysis_returns_503_without_credentials(monkeypatch):
    c = _client(monkeypatch, "", "")
    assert c.get("/production/ai-analysis").status_code == 503


def test_secret_never_appears_in_health(monkeypatch):
    """健康检查不得回显凭据（哪怕是配好的情况下）。"""
    c = _client(monkeypatch, "cli_fake", "super-secret-value")
    r = c.get("/health")
    assert "super-secret-value" not in r.text


# ---------------------------------------------------------------------------
# token 失效补救：清缓存 + 只重试一次
# ---------------------------------------------------------------------------

def test_auth_error_clears_token_and_retries_once(monkeypatch):
    """飞书判定 token 无效时，必须清掉本地缓存并重试 —— 否则一路 502 到重启。"""
    from app import feishu

    calls = {"get": 0, "token": 0}

    monkeypatch.setattr(feishu, "_token", lambda: calls.__setitem__("token", calls["token"] + 1) or "tok")
    monkeypatch.setattr(feishu, "_clear_token", lambda: None)

    class Resp:
        status_code = 200

        def __init__(self, code):
            self._code = code

        def json(self):
            return {"code": self._code, "msg": "invalid token"}

    class Client:
        def get(self, url, params=None, headers=None):
            calls["get"] += 1
            # 第一次返回 token 失效，之后正常
            return Resp(99991663 if calls["get"] == 1 else 0)

    body = feishu._get_with_retry(Client(), "http://x", {})
    assert body["code"] == 0
    assert calls["get"] == 2, "应当只重试一次就成功"


def test_auth_error_does_not_retry_forever(monkeypatch):
    """真正的权限问题不该无限重试 —— 每次调用最多补救一次。"""
    from app import feishu

    calls = {"get": 0}
    cleared = {"n": 0}

    monkeypatch.setattr(feishu, "_token", lambda: "tok")
    monkeypatch.setattr(feishu, "_clear_token", lambda: cleared.__setitem__("n", cleared["n"] + 1))
    monkeypatch.setattr(feishu.time, "sleep", lambda s: None)

    class Resp:
        status_code = 200

        def json(self):
            return {"code": 99991663, "msg": "invalid token"}

    class Client:
        def get(self, url, params=None, headers=None):
            calls["get"] += 1
            return Resp()

    with pytest.raises(feishu.FeishuError):
        feishu._get_with_retry(Client(), "http://x", {})

    assert cleared["n"] == 1, "清 token 只该发生一次"
    assert calls["get"] == 2, "换过 token 仍然失效 → 立刻失败，不再空转"
