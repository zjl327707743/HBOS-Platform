"""stub 后端——无任何 ML 依赖，用于**链路冒烟测试**。

存在意义（M3-R6 方案第九节的时序结论）：

    「用合成 / 公开标签做链路冒烟测试」**不需要真实样本**。

本后端让服务骨架、契约、校验层、幂等、失败日志、以及 Frappe 侧的上传与校对
界面**现在就能端到端跑通**，不必等 C1/C2 的模型依赖装好、也不必等仓库样本。

它不识别图像，而是从**文件名**或 **hints** 里取预置值，返回结构化结果。
因此可以配合任意图片（哪怕是纯色图）驱动整条链路。

**本后端不得用于生产**——它不读图片内容。
"""

from __future__ import annotations

import re

from ..contract import (
    BACKEND_STUB,
    BackendResult,
    RecognizeRequest,
    empty_fields,
)
from .base import RecognizeBackend

# 文件名约定的简单解析：`自产-13000215-B2609503-20260901-20280901.jpg`
# 缺省的段用 `_` 占位。
_FILENAME_HINT = re.compile(r"^(?P<source>[^_]+)?_(?P<code>[^_]*)_(?P<batch>[^_]*)")


class StubBackend(RecognizeBackend):
    name = BACKEND_STUB

    def is_available(self) -> tuple[bool, str]:
        return True, ""

    def recognize(self, image_bytes: bytes, request: RecognizeRequest) -> BackendResult:
        fields = empty_fields()

        # hints 优先（便于测试脚本直接指定期望值）
        for key in fields:
            if request.hints.get(key):
                fields[key] = request.hints[key]

        # 未给的字段填一组**明显是虚构**的默认值，避免误当真实数据
        fields.setdefault("product_name", None)
        if not fields.get("product_name"):
            fields["product_name"] = "STUB-虚构产品"
        if not fields.get("item_code"):
            fields["item_code"] = "13000215"
        if not fields.get("batch_no"):
            fields["batch_no"] = "B2609503"
        if not fields.get("manufacturing_date"):
            fields["manufacturing_date"] = "2026-09-01"
        if not fields.get("expiry_date"):
            fields["expiry_date"] = "2028-09-01"

        # 置信度：stub 恒为高置信度，便于观察"高置信度错误"指标的计算路径
        confidence = {key: 0.99 for key in fields}

        return BackendResult(
            fields=fields,
            confidence=confidence,
            raw_text="[stub backend] 未读取图像内容，返回值由 hints / 默认值构造",
            backend=self.name,
        )
