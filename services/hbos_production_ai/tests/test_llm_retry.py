"""LLM 重试策略 —— 只重试**值得重试**的错误。

踩过（复审 2026-10-27）：所有非 200 都进重试，包括 400/401/403/404。
超时配到 600 秒时，一次「模型名写错」会浪费好几轮等待才失败，
日志也被同一句刷满。

真实网络不在测试范围内 —— 这里只钉判定函数本身。
"""

from __future__ import annotations

import pytest

from app import llm


@pytest.mark.parametrize("status", [400, 401, 403, 404, 405, 422])
def test_client_errors_are_not_retried(status):
    assert not llm._retryable(llm.LLMError(f"HTTP {status}", status=status))


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
def test_transient_errors_are_retried(status):
    assert llm._retryable(llm.LLMError(f"HTTP {status}", status=status))


def test_network_error_without_status_is_retried():
    """超时 / 连接中断没有状态码，属于可重试。"""
    assert llm._retryable(llm.LLMError("timed out"))


def test_complete_raises_immediately_on_401(monkeypatch):
    """401 必须**立刻**失败，不能按 AI_RETRIES 空转。"""
    from app import config

    calls: list[int] = []

    class Resp:
        status_code = 401
        text = "unauthorized"

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **kw):
            calls.append(1)
            return Resp()

    monkeypatch.setattr(llm.httpx, "Client", lambda **kw: Client())
    monkeypatch.setattr(config, "AI_RETRIES", 3)

    with pytest.raises(llm.LLMError):
        llm.complete("sys", "user")
    assert len(calls) == 1, f"401 被重试了 {len(calls)} 次"


def test_complete_retries_on_503(monkeypatch):
    from app import config

    calls: list[int] = []

    class Resp:
        status_code = 503
        text = "busy"

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **kw):
            calls.append(1)
            return Resp()

    monkeypatch.setattr(llm.httpx, "Client", lambda **kw: Client())
    monkeypatch.setattr(config, "AI_RETRIES", 2)

    with pytest.raises(llm.LLMError):
        llm.complete("sys", "user")
    assert len(calls) == 3, "503 应当按 AI_RETRIES 重试"
