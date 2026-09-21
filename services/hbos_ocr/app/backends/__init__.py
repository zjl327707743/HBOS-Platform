"""后端注册表——按名字取后端，并汇报可用性。

设计要点：**缺依赖不该让服务崩掉。** 未安装 mlx-vlm / paddleocr 时，对应后端
``is_available()`` 返回 False，服务照常启动，只是选不了它。
"""

from __future__ import annotations

from ..contract import ALL_BACKENDS, BACKEND_C1, BACKEND_C2, BACKEND_STUB
from .base import RecognizeBackend
from .c1_local_vlm import LocalVLMBackend
from .c2_ocr import DEFAULT_MODEL_TIER, MODEL_TIERS, PaddleOCRBackend, parse_backend_spec
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
    """后端注册表。

    除三个固定后端外，还支持带**模型档位**的写法：``c2_ocr:small``。
    这类后端按需构造并缓存——用于拿同一批样本对照不同档位的耗时与准确率。
    档位切换**不需要装新依赖**，只是换个模型名。
    """

    def __init__(self) -> None:
        self._backends = {name: _build(name) for name in ALL_BACKENDS}
        self._variants: dict[str, RecognizeBackend] = {}

    def get(self, name: str) -> RecognizeBackend:
        backend = self._backends.get(name)
        if backend is None:
            backend = self._get_variant(name)
        if backend is None:
            raise ValueError(f"未知后端：{name}")
        available, reason = backend.is_available()
        if not available:
            raise RuntimeError(f"后端 {name} 不可用：{reason}")
        return backend

    def _get_variant(self, spec: str) -> RecognizeBackend | None:
        """``c2_ocr:medium`` → 构造并缓存一个该档位的后端。

        两个坑，都是实测踩出来的：

        1. **显式写默认档（``c2_ocr:small``）必须能解析。** 早先这里对
           ``tier == DEFAULT_MODEL_TIER`` 直接返回 ``None``，而 ``get()`` 把 ``None``
           当成「未知后端」→ 请求被拒 400。于是「用同一批样本对照档位」这个功能
           在默认档上恰好不可用——最该能跑的那一档跑不了。
        2. **档位名写错必须报错，不能静默回退。** ``PaddleOCRBackend.__init__`` 对
           不认识的档位会回退到默认档，于是 ``c2_ocr:medum``（拼错）会**悄悄跑 small**
           却报告成 medium——对照实验会得出「medium 又快又准」的假结论。
           这种错误极难自查，所以在这里就拦下。
        """
        base, tier = parse_backend_spec(spec)
        if base != BACKEND_C2:
            return None
        if tier == DEFAULT_MODEL_TIER:
            return self._backends[BACKEND_C2]  # 就是默认那个实例，不必另建
        if tier not in MODEL_TIERS:
            raise ValueError(f"未知模型档位：{tier}（可用：{'、'.join(MODEL_TIERS)}）")
        if spec not in self._variants:
            self._variants[spec] = PaddleOCRBackend(tier=tier)
        return self._variants[spec]

    def status(self) -> dict:
        """各后端可用性，供 /health 暴露。"""
        out = {}
        for name, backend in self._backends.items():
            available, reason = backend.is_available()
            out[name] = {"available": available, "reason": reason}
        return out


registry = BackendRegistry()
