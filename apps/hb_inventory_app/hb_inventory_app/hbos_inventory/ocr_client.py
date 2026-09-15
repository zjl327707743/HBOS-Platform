"""入库拍照识别服务——Frappe 侧调用客户端。

集成方式遵循项目规范 `docs/team/05_开源代码二次开发与升级规范.md` 的
**优先级 5：外部服务**：Frappe 侧只通过 HTTP 调用，**不直连对方数据库**，
**不修改任何核心源码**。

服务地址（按优先级）：
    1. site config：`bench set-config hbos_ocr_url http://…`
    2. 环境变量：`HBOS_OCR_URL`
    3. 默认：`http://host.docker.internal:8100`

为什么默认是 ``host.docker.internal``：按 M3-R6 方案 3.1，识别服务**原生跑在
宿主机上**（容器是 Linux arm64，拿不到 Metal 加速，模型只能跑 CPU）。
Docker 容器经该域名访问宿主机，M3-R6 已实测其可解析。

**降级设计**：本客户端在服务不可用、超时、返回异常时**一律抛
``OcrUnavailable``**，由调用方决定如何提示。**绝不返回伪造的识别结果**——
识别不可用时，仓库应走既有的**人工录入**通道（M3-R2 已具备）。
"""

from __future__ import annotations

import os

import frappe
import requests

DEFAULT_BASE_URL = "http://host.docker.internal:8100"

#: 单个接口调用的超时（秒）。识别本身可能数秒，健康检查要快。
DEFAULT_TIMEOUT = 60
HEALTH_TIMEOUT = 5


class OcrUnavailable(Exception):
    """识别服务不可用（未启动 / 超时 / 返回异常）。

    刻意区别于"识别失败"——前者是**服务层**问题，后者是**单张图片**问题。
    对操作员的提示语不同：前者建议走人工录入，后者建议重拍。
    """


def get_base_url() -> str:
    return (
        frappe.conf.get("hbos_ocr_url")
        or os.environ.get("HBOS_OCR_URL")
        or DEFAULT_BASE_URL
    ).rstrip("/")


def _request(method: str, path: str, timeout: int, **kwargs) -> dict:
    url = f"{get_base_url()}{path}"
    try:
        resp = requests.request(method, url, timeout=timeout, **kwargs)
    except requests.exceptions.RequestException as exc:
        # 只记录异常类型与地址，不记录请求体（照片内容）
        frappe.log_error(
            title="HBOS OCR 服务不可达",
            message=f"{method} {url} -> {type(exc).__name__}: {exc}",
        )
        raise OcrUnavailable(f"识别服务不可达（{type(exc).__name__}）") from exc

    if resp.status_code >= 400:
        detail = ""
        try:
            detail = resp.json().get("detail") or ""
        except Exception:  # noqa: BLE001
            detail = resp.text[:200]
        raise OcrUnavailable(f"识别服务返回 {resp.status_code}：{detail}")

    try:
        return resp.json()
    except ValueError as exc:
        raise OcrUnavailable("识别服务返回的不是合法 JSON") from exc


def health() -> dict:
    """探测服务与各后端可用性。供界面提示"服务在不在"。"""
    return _request("GET", "/health", HEALTH_TIMEOUT)


def recognize(
    *,
    file_name: str,
    content: bytes,
    source_type: str | None = None,
    backend: str | None = None,
    request_id: str | None = None,
    hints: dict | None = None,
) -> dict:
    """调用识别服务，返回其原始响应字典。

    图片以 multipart 传出；**服务端不长期留存**（见 M3-R6 方案第六节）。

    ``request_id`` 用作幂等键——同一次入库的重复调用会命中服务端缓存，
    避免产生两份识别结果。
    """
    import json as _json

    files = {"image": (file_name or "label.jpg", content, "application/octet-stream")}
    data: dict[str, str] = {}
    if source_type:
        data["source_type"] = source_type
    if backend:
        data["backend"] = backend
    if request_id:
        data["request_id"] = request_id
    if hints:
        data["hints"] = _json.dumps(hints, ensure_ascii=False)

    return _request(
        "POST",
        "/api/v1/recognize",
        DEFAULT_TIMEOUT,
        files=files,
        data=data,
    )
