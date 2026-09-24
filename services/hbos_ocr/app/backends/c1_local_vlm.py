"""C1 后端：本地量化视觉语言模型（走 MLX / Metal）。

为什么是 MLX：
    这台临时承载机是 Apple M4。MLX 是 Apple 官方推理框架，**能吃满 Metal 与
    神经网络引擎**；而 Docker 里的 Linux arm64 容器拿不到 Metal，只能跑 CPU。
    所以本服务**原生跑在 Mac 上**，不塞进 Frappe 容器（M3-R6 方案 3.1）。

依赖（**不在 requirements.txt 里**，按需单独装——它们体积大且平台相关）：

    pip install mlx-vlm

未安装时 ``is_available()`` 返回 False，服务仍可启动（只是选不了本后端）。

选型提示（M3-R6 方案 4.1）：
    16 GB 统一内存下只能跑**小模型**（3B 级、4-bit 量化）。小模型在**密集小字**
    标签上会漏读或串行，这正是需要与 C2 对照实测的原因。
"""

from __future__ import annotations

import json
import re

from ..contract import (
    BACKEND_C1,
    BackendResult,
    RecognizeRequest,
    empty_fields,
)
from .base import RecognizeBackend

#: 默认模型。可在环境变量 HBOS_OCR_C1_MODEL 中覆盖。
DEFAULT_MODEL = "mlx-community/Qwen2.5-VL-3B-Instruct-4bit"

#: 提示词：要求模型**只输出 JSON**，字段名与业务字段对齐。
PROMPT = """请读取这张药品/物料标签图片，提取以下字段并以 JSON 返回，不要输出任何解释文字。

字段：
- product_name: 产品名称
- item_code: 物料代码（8 位数字）
- batch_no: 批号
- manufacturing_date: 生产日期（YYYY-MM-DD）
- expiry_date: 有效期至（YYYY-MM-DD）

无法识别的字段填 null。只输出一个 JSON 对象。"""

_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


class LocalVLMBackend(RecognizeBackend):
    name = BACKEND_C1

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or DEFAULT_MODEL
        self._model = None
        self._processor = None

    def is_available(self) -> tuple[bool, str]:
        try:
            import mlx_vlm  # noqa: F401
        except Exception:
            return False, "未安装 mlx-vlm；请执行 `pip install mlx-vlm`"
        return True, ""

    # --- 模型按需加载。首次调用较慢，之后复用。 ---

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from mlx_vlm import load

        self._model, self._processor = load(self.model_path)

    def recognize(self, image_bytes: bytes, request: RecognizeRequest) -> BackendResult:
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(reason)

        self._ensure_loaded()

        # 图片仅传入内存，不落盘（M3-R6 方案第六节）
        import tempfile

        from mlx_vlm import generate
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config

        # NOTE: mlx-vlm 的 generate 目前只接受**文件路径**，不接受字节流。
        # 因此这里落一个临时文件，**用完立即删除**——仍是"不长期留存"，
        # 但属于对上游限制的让步，已在 M3-R6 主文档中记录。
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fh:
            fh.write(image_bytes)
            tmp_path = fh.name

        try:
            config = load_config(self.model_path)
            formatted = apply_chat_template(self._processor, config, PROMPT, num_images=1)
            text = generate(self._model, self._processor, formatted, [tmp_path], verbose=False)
        finally:
            import os

            os.unlink(tmp_path)

        fields = self._parse(text)
        return BackendResult(
            fields=fields,
            confidence={},  # 小模型不返回可靠置信度，交由校验层与人工判断
            raw_text=text if isinstance(text, str) else str(text),
            backend=self.name,
        )

    @staticmethod
    def _parse(text: str) -> dict:
        """从模型输出里抠出 JSON。

        小模型常带前后缀文字，故用正则截取第一个 ``{...}`` 块。
        """
        fields = empty_fields()
        if not text:
            return fields
        m = _JSON_BLOCK.search(text if isinstance(text, str) else str(text))
        if not m:
            return fields
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            return fields
        for key in fields:
            value = parsed.get(key)
            fields[key] = None if value in (None, "", "null", "None") else str(value)
        return fields
