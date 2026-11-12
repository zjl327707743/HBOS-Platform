"""LLM 调用（OpenAI 兼容）。

**启动时必须先探活** —— 历史教训：`.env` 里配的模型名被上游下线后，
跑了整批才失败（`docs/milestones/M1_FIX_F_调休模块第一阶段落地记录.md:218`，`HTTP 503 model_not_found`）。
探活失败就直接退出，不进入分析循环。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from . import config

log = logging.getLogger("hbos_production_ai.llm")


class LLMError(RuntimeError):
    def __init__(self, message: str, *, status: int = 0, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def probe() -> dict:
    """探活：一次最小请求，确认「端点通 + key 有效 + 模型名存在」。

    **必须在批量分析前调用。** 三种失败要能分开报，否则排查时看不出是
    key 错还是模型名错（上次就栽在这里）。
    """
    if not config.llm_configured():
        return {"ok": False, "reason": "未配置", "detail": "BASE_URL / API_KEY / MODEL 有缺"}

    try:
        with httpx.Client(timeout=min(config.AI_TIMEOUT, 30)) as c:
            r = c.post(
                f"{config.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.AI_MODEL,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
            )
    except httpx.HTTPError as exc:
        return {"ok": False, "reason": "连不上端点", "detail": str(exc)[:200]}

    body = r.text[:500]
    if r.status_code == 200:
        return {"ok": True, "model": config.AI_MODEL}

    # 分开报：名字错 vs 鉴权错 —— 这两种的处置完全不同
    if r.status_code in (401, 403):
        return {"ok": False, "reason": "鉴权失败（key 无效或过期）", "status": r.status_code, "detail": body}
    if r.status_code == 404 or "model" in body.lower():
        return {
            "ok": False,
            "reason": f"模型名不可用：{config.AI_MODEL}",
            "status": r.status_code,
            "detail": body,
            "hint": "调 GET /models 列出上游可用模型名，改 HBOS_AI_MODEL",
        }
    return {"ok": False, "reason": "请求失败", "status": r.status_code, "detail": body}


def list_models() -> list[str]:
    """列出上游可用模型（探活失败时用来找正确的名字）。"""
    with httpx.Client(timeout=30) as c:
        r = c.get(
            f"{config.AI_BASE_URL}/models",
            headers={"Authorization": f"Bearer {config.AI_API_KEY}"},
        )
    if r.status_code != 200:
        raise LLMError(f"列模型失败 HTTP {r.status_code}", status=r.status_code, body=r.text[:300])
    data = r.json()
    return sorted(m.get("id", "") for m in (data.get("data") or []) if m.get("id"))


def complete(system: str, user: str) -> str:
    """调一次 chat completion，返回正文文本。"""
    payload: dict[str, Any] = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # `temperature` **默认不发**。踩过：gpt-5.6-sol（推理模型）收到它会直接
    # 400（`upstream_error`），而错误信息里看不出是它 —— 二分才定位到。
    # 推理模型本就不接受采样参数，稳不稳定由模型自己决定。
    # 万一换了非推理模型想调，用 HBOS_AI_TEMPERATURE 显式开。
    if config.AI_TEMPERATURE is not None:
        payload["temperature"] = config.AI_TEMPERATURE
    last: LLMError | None = None
    for attempt in range(config.AI_RETRIES + 1):
        try:
            with httpx.Client(timeout=config.AI_TIMEOUT) as c:
                r = c.post(
                    f"{config.AI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.AI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            if r.status_code != 200:
                raise LLMError(
                    f"HTTP {r.status_code}", status=r.status_code, body=r.text[:300]
                )
            data = r.json()
            choices = data.get("choices") or []
            if not choices:
                raise LLMError("响应里没有 choices", body=json.dumps(data, ensure_ascii=False)[:300])
            return choices[0].get("message", {}).get("content", "") or ""
        except (httpx.HTTPError, LLMError) as exc:
            last = exc if isinstance(exc, LLMError) else LLMError(str(exc))
            log.warning("第 %d 次调用失败：%s", attempt + 1, str(last)[:120])
    raise last or LLMError("调用失败")
