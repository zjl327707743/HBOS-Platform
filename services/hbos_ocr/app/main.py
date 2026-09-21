"""入库拍照识别服务（FastAPI）。

集成方式遵循项目既有规范 `docs/team/05_开源代码二次开发与升级规范.md`
的**优先级 5：外部服务**——独立服务，通过 HTTP 与 Frappe 交互，
**不修改 Frappe 核心源码、不直连数据库**。

数据边界（M3-R6 方案第六节，Owner 已定）：
    - 照片**不出内网**——本服务不开任何外网访问；
    - 照片**不落盘**——识别后即释放（对上游库只接受文件路径的限制，
      使用临时文件并**用完立即删除**，已在主文档记录该让步）；
    - 日志**不记录照片内容、批号或产品名**——只记 request_id / 耗时 / 成败 / 错误类型。

运行：
    uvicorn app.main:app --host 127.0.0.1 --port 8100
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import OrderedDict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from . import config
from .backends import registry
from .backends.c2_ocr import parse_backend_spec
from .contract import (
    ALL_BACKENDS,
    RecognizeRequest,
    RecognizeResponse,
)
from .validate import validate_fields

logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger("hbos_ocr")

app = FastAPI(
    title="HBOS 入库拍照识别服务",
    version="0.1.0",
    description="本地部署，照片不出内网。见 docs/milestones/M3_R6_入库拍照识别服务方案.md",
)


# ---------------------------------------------------------------------------
# 幂等：进程内短期缓存
# ---------------------------------------------------------------------------
#
# 目的：同一次入库里重复点击/超时重试，不应产生两份识别结果。
# 局限：**进程内、非持久**——重启即失效。这符合需求（防重复点击，非严格去重），
#       已在 M3-R6 主文档中如实说明。

_IDEMPOTENCY: "OrderedDict[str, dict]" = OrderedDict()


def _parse_hints(raw: str | None) -> dict:
    """把 JSON 字符串形式的 hints 解析为字典。

    解析失败不报错——hints 是**可选**线索，格式不对不该让识别失败。
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        log.warning("hints 解析失败，已忽略")
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _idem_get(request_id: str | None) -> dict | None:
    if not request_id:
        return None
    hit = _IDEMPOTENCY.get(request_id)
    if hit is None:
        return None
    created, payload = hit
    if time.time() - created > config.IDEMPOTENCY_TTL_SECONDS:
        _IDEMPOTENCY.pop(request_id, None)
        return None
    return payload


def _idem_put(request_id: str | None, payload: dict) -> None:
    if not request_id:
        return
    _IDEMPOTENCY[request_id] = (time.time(), payload)
    while len(_IDEMPOTENCY) > config.IDEMPOTENCY_MAX_ITEMS:
        _IDEMPOTENCY.popitem(last=False)


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    """健康检查，并汇报各后端可用性。

    暴露后端可用性是为了让 Frappe 侧能判断"该服务能不能用、能用哪个后端"。
    """
    return {
        "ok": True,
        "default_backend": config.DEFAULT_BACKEND,
        "backends": registry.status(),
    }


@app.post("/api/v1/recognize", response_model=None)
async def recognize(
    image: UploadFile = File(..., description="标签照片"),
    backend: str | None = Form(default=None, description="指定后端，缺省用配置的默认后端"),
    source_type: str | None = Form(default=None, description="自产 / 外购（帮助校验）"),
    request_id: str | None = Form(default=None, description="幂等键"),
    hints: str | None = Form(
        default=None,
        description='可选线索，JSON 字符串，如 {"batch_no": "B2609503"}。'
        "既可用于传入已知信息，也可用于测试时注入期望值。",
    ),
) -> dict:
    """识别一张标签照片，返回**经校验层处理**的结构化字段。

    响应中的 ``hints`` 是按字段的提示，供 Frappe 侧高亮需要人工复核的字段。
    **本接口不写入任何业务数据**——落库由 Frappe 侧在人工确认后执行。
    """
    rid = request_id or uuid.uuid4().hex

    cached = _idem_get(request_id)
    if cached is not None:
        log.info("recognize idempotent-hit request_id=%s", rid)
        return cached

    backend_name = backend or config.DEFAULT_BACKEND
    # 支持带模型档位的写法（如 ``c2_ocr:small``）——先剥掉档位再校验后端名
    if parse_backend_spec(backend_name)[0] not in ALL_BACKENDS:
        raise HTTPException(status_code=400, detail=f"未知后端：{backend_name}")

    started = time.time()
    try:
        image_bytes = await image.read()
    except Exception as exc:  # noqa: BLE001
        log.warning("recognize read-failed request_id=%s error=%s", rid, type(exc).__name__)
        raise HTTPException(status_code=400, detail="读取上传图片失败") from exc

    if not image_bytes:
        raise HTTPException(status_code=400, detail="上传图片为空")
    if len(image_bytes) > config.MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"图片超过大小上限（{config.MAX_IMAGE_BYTES} 字节）",
        )

    try:
        impl = registry.get(backend_name)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request = RecognizeRequest(
        source_type=source_type,
        request_id=rid,
        hints=_parse_hints(hints),
    )

    try:
        # 图片仅以字节流传入后端；后端负责用完即弃（不落长期文件）
        result = impl.recognize(image_bytes, request)
    except Exception as exc:  # noqa: BLE001
        # 失败要落日志，但**不记照片内容**
        log.warning(
            "recognize failed request_id=%s backend=%s error=%s",
            rid,
            backend_name,
            type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail=f"识别失败：{type(exc).__name__}") from exc
    finally:
        del image_bytes

    report = validate_fields(result.fields, source_type=source_type, raw_text=result.raw_text)

    elapsed_ms = int((time.time() - started) * 1000)
    payload = RecognizeResponse(
        ok=True,
        request_id=rid,
        backend=result.backend or backend_name,
        fields=report.as_dict(),
        raw_fields=dict(result.fields),
        confidence=dict(result.confidence),
        hints=report.hints(),
        needs_review=report.needs_review(),
        raw_text=result.raw_text,
        elapsed_ms=elapsed_ms,
    ).as_dict()

    # 日志只记非敏感信息
    log.info(
        "recognize ok request_id=%s backend=%s elapsed_ms=%s needs_review=%s",
        rid,
        payload["backend"],
        elapsed_ms,
        payload["needs_review"],
    )

    _idem_put(request_id, payload)
    return payload
