"""识别后端的抽象契约。

M3-R6 方案 4.3 的核心设计：**后端可插拔**。

    C1（本地大模型）/ C2（本地 OCR + 规则）/ stub（冒烟测试用）
    实现同一契约 → 换后端不需要重写服务。

这也是"先量后决"的工程前提：同一批样本跑不同后端，产出一张准确率对照表。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..contract import BackendResult, RecognizeRequest


class RecognizeBackend(ABC):
    """识别后端基类。"""

    #: 后端标识，与 ``app.contract`` 中的常量对应
    name: str = ""

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """后端是否可用。

        返回 ``(可用, 原因)``。不可用时服务仍能启动，只是该后端无法被选中——
        这样缺依赖不会导致整个服务挂掉。
        """

    @abstractmethod
    def recognize(self, image_bytes: bytes, request: RecognizeRequest) -> BackendResult:
        """识别一张标签图片。

        ``image_bytes`` 为图片原始字节；实现方**不得落盘**（M3-R6 方案第六节：
        识别后即释放，照片不出内网、不长期留存）。
        """
