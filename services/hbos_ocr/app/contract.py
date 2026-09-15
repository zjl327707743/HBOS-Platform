"""识别服务的数据契约。

字段命名与 M3 已落地的业务字段对齐（`item_code` / `batch_no` /
`manufacturing_date` / `expiry_date`），避免两侧各叫一套。

本模块**不依赖 FastAPI**，便于在无 Web 依赖的环境下复用与单测。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

# 后端标识
BACKEND_STUB = "stub"
BACKEND_C1 = "c1_local_vlm"
BACKEND_C2 = "c2_ocr"

ALL_BACKENDS = (BACKEND_STUB, BACKEND_C1, BACKEND_C2)

# 与 M3 业务一致的来源类型
SOURCE_SELF = "自产"
SOURCE_OUTSOURCED = "外购"

RECOGNIZE_FIELDS = (
    "product_name",
    "item_code",
    "batch_no",
    "manufacturing_date",
    "expiry_date",
)


@dataclass
class RecognizeRequest:
    """识别请求。

    ``hints`` 是可选线索，不参与识别本身，但会**帮助校验层**判断
    （例如知道是外购，进厂批号的 10 位数字就不会被误报）。
    冒烟测试时也可用 hints 直接指定期望值（见 stub 后端）。
    """

    source_type: Optional[str] = None  # 自产 / 外购
    request_id: Optional[str] = None   # 幂等键
    hints: dict = field(default_factory=dict)


@dataclass
class BackendResult:
    """后端识别的原始产出（**未经校验层处理**）。"""

    fields: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    raw_text: str = ""
    backend: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def empty_fields() -> dict:
    """空字段模板，保证响应结构稳定。"""
    return {name: None for name in RECOGNIZE_FIELDS}


@dataclass
class RecognizeResponse:
    """识别响应（已过校验层）。

    - ``fields``：**校验后**可直接入账的值
    - ``raw_fields``：后端原始产出，便于追溯"AI 读到了什么"
    - ``hints``：按字段的提示，供界面高亮
    - ``backend``：实际使用的后端，便于 C1/C2 对照测量
    """

    ok: bool
    request_id: str
    backend: str
    fields: dict
    raw_fields: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    hints: dict = field(default_factory=dict)
    needs_review: bool = True
    raw_text: str = ""
    error: Optional[str] = None
    elapsed_ms: Optional[int] = None

    def as_dict(self) -> dict:
        return asdict(self)
