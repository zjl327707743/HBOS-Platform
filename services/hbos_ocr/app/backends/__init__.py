"""后端注册表——按名字取后端，并汇报可用性。

设计要点：**缺依赖不该让服务崩掉。** 未安装 mlx-vlm / paddleocr 时，对应后端
``is_available()`` 返回 False，服务照常启动，只是选不了它。
"""

from __future__ import annotations

from ..contract import ALL_BACKENDS, BACKEND_C1, BACKEND_C2, BACKEND_STUB
from .base import RecognizeBackend
from .c1_local_vlm import LocalVLMBackend
from .c2_ocr import PaddleOCRBackend
from .stub import StubBackend


def _build(name: str) -> RecognizeBackend:
    if name == BACKEND_STUB:
        return StubBackend()
    if name == BACKEND_C1:
        return LocalVLMBackend()
    if name == BACKEND_C2:
        return PaddleOCRBackend()
    raise ValueError(f"未知后端：{name}")


class BackendRegistry:
    def __init__(self) -> None:
        self._backends = {name: _build(name) for name in ALL_BACKENDS}

    def get(self, name: str) -> RecognizeBackend:
        backend = self._backends.get(name)
        if backend is None:
            raise ValueError(f"未知后端：{name}")
        available, reason = backend.is_available()
        if not available:
            raise RuntimeError(f"后端 {name} 不可用：{reason}")
        return backend

    def status(self) -> dict:
        """各后端可用性，供 /health 暴露。"""
        out = {}
        for name, backend in self._backends.items():
            available, reason = backend.is_available()
            out[name] = {"available": available, "reason": reason}
        return out


registry = BackendRegistry()
