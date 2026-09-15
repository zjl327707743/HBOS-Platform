"""C2 后端：本地 OCR + 结构化规则 + 主数据约束匹配。

为什么 C2 值得做（M3-R6 方案 4.1）：

    - **内存占用小**（1–2 GB）、**CPU 即可**，在这台 16 GB 的临时承载机上更稳；
    - **可解释**——出错能看出是"没读对"还是"规则没匹配上"；
    - 印刷体文字识别准确率高。

关键洞察（方案 7.8 八）：

    **物料代码是 8 位、全数字。** 这一条让代码纠错**不需要任何主数据清单**——
    OCR 最常见的错误是把数字认成形近字母（`0`/`O`、`1`/`l`、`5`/`S`…），
    既然代码只可能是数字，把字母无条件映射回形近数字即可。纠错逻辑在
    ``app.validate``，与后端解耦。

依赖（**不在 requirements.txt 里**，按需单独装）：

    pip install paddleocr paddlepaddle

未安装时 ``is_available()`` 返回 False，服务仍可启动。
"""

from __future__ import annotations

import re

from ..contract import (
    BACKEND_C2,
    BackendResult,
    RecognizeRequest,
    empty_fields,
)
from .base import RecognizeBackend

# 从 OCR 文本行里抽取字段的辅助模式。
# 注意这些是**启发式**，不是硬规则——抽不到就留 None，交给人工补。
_CODE_LINE = re.compile(r"(\d[\dOoIlSBGZbqAT]{6,9}\d)")
_BATCH_LINE = re.compile(r"([A-Z]{1,4}\d{5,}[A-Z]?(?:-\d{1,2})?)")
_DATE_LIKE = re.compile(
    r"((?:19|20)\d{2}[\s.\-/年]\d{1,2}[\s.\-/月]\d{1,2}\s*日?|\d{8}|\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2})"
)


class PaddleOCRBackend(RecognizeBackend):
    name = BACKEND_C2

    def __init__(self) -> None:
        self._ocr = None

    def is_available(self) -> tuple[bool, str]:
        try:
            import paddleocr  # noqa: F401
        except Exception:
            return False, "未安装 paddleocr / paddlepaddle；请执行 `pip install paddleocr paddlepaddle`"
        return True, ""

    def _ensure_loaded(self) -> None:
        if self._ocr is None:
            from paddleocr import PaddleOCR

            # 只用中英识别；关闭方向分类器以省内存
            self._ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)

    def recognize(self, image_bytes: bytes, request: RecognizeRequest) -> BackendResult:
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(reason)

        self._ensure_loaded()

        import tempfile

        # PaddleOCR 同样只接受文件路径；临时文件用完即删
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fh:
            fh.write(image_bytes)
            tmp_path = fh.name

        try:
            raw = self._ocr.ocr(tmp_path, cls=False)
        finally:
            import os

            os.unlink(tmp_path)

        lines = self._flatten(raw)
        fields = self._extract(lines)
        return BackendResult(
            fields=fields,
            confidence={},  # 由 OCR 逐行置信度聚合，此处先不暴露
            raw_text="\n".join(lines),
            backend=self.name,
        )

    @staticmethod
    def _flatten(raw) -> list[str]:
        """把 PaddleOCR 的嵌套返回压平成文本行列表。"""
        lines: list[str] = []
        if not raw:
            return lines
        for page in raw:
            for item in page or []:
                try:
                    lines.append(str(item[1][0]))
                except (IndexError, TypeError):
                    continue
        return lines

    @staticmethod
    def _extract(lines: list[str]) -> dict:
        """按启发式规则从文本行里抽取字段。

        每条规则都可能抽不到——**抽不到留 None**，交由人工或在 Frappe 侧由
        物料代码回填（产品名称可由代码反查主数据）。
        """
        fields = empty_fields()
        joined = "\n".join(lines)

        # 物料代码：8 位、允许形近字母（真正的纠错在 validate 层）
        m = _CODE_LINE.search(joined)
        if m:
            fields["item_code"] = m.group(1)

        # 批号：字母前缀 + 数字
        prefixes = [ln for ln in lines if _BATCH_LINE.fullmatch(ln.strip())]
        if prefixes:
            fields["batch_no"] = prefixes[0].strip()

        # 日期：取前两个可解析的，先出现的作生产日期、后出现的作有效期
        dates = _DATE_LIKE.findall(joined)
        if dates:
            fields["manufacturing_date"] = dates[0]
            if len(dates) > 1:
                fields["expiry_date"] = dates[1]

        # 产品名称：取最长的一行中文（启发式，通常品名那行最长且含中文）
        cn_lines = [ln.strip() for ln in lines if re.search(r"[一-鿿]{2,}", ln)]
        if cn_lines:
            fields["product_name"] = max(cn_lines, key=len)

        return fields
