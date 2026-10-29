"""服务的冒烟测试 —— 只测**行为边界**，不打真实飞书。

重点验证一条纪律：**凭据没配时不返回任何数字**（EA-5.4 §16）。
这条比接口通不通更重要 —— 看板给车间经理看，编造的数据会被当成真实产量。
"""

from __future__ import annotations

import importlib

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
