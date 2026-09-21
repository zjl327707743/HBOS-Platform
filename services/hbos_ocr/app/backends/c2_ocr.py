"""C2 后端：本地 OCR + 结构化规则。

为什么 C2 值得做（M3-R6 方案 4.1）：

    - **内存占用小**、**CPU 即可**，在 16 GB 的临时承载机上更稳；
    - **可解释**——出错能看出是"没读对"还是"规则没匹配上"；
    - 印刷体文字识别准确率高（实测 50 张真实标签，正文基本全读对）。

分工（方案 4.3）：**模型负责"读"，规则负责"筛"，人负责"定"。**

    本文件只做前两步。第 1 步交给 PaddleOCR，第 2 步是本文件的启发式规则；
    最后的规范化与纠错在 ``app.validate``。三者解耦。

依赖（**不在 requirements.txt 里**，按需单独装）：

    pip install paddleocr paddlepaddle

未安装时 ``is_available()`` 返回 False，服务仍可启动。

关于 PaddleOCR 版本
-------------------
本后端按 **PaddleOCR 3.x**（实测 3.7.0 / PaddlePaddle 3.3.1）编写。

3.x 与 2.x 的 API 不兼容：没有 ``use_angle_cls`` / ``show_log`` 参数，
也没有 ``.ocr(path, cls=...)``；改用 ``.predict(path)``，返回
``OCRResult``（dict 风格），文本在 ``rec_texts``。

> ⚠ 环境陷阱：若**当前工作目录**里存在名为 ``cv2.py`` 的文件，它会把真正的
> OpenCV 顶掉，PaddleOCR 初始化时报
> ``AttributeError: module 'cv2' has no attribute 'IMREAD_COLOR'``。
> 这跟本服务无关——正常从本目录启动不会有这个问题。
"""

from __future__ import annotations

import datetime
import os
import re
import tempfile

from ..contract import (
    BACKEND_C2,
    BackendResult,
    RecognizeRequest,
    empty_fields,
)
from ..validate import CONFUSABLE_TO_DIGIT
from .base import RecognizeBackend

# ---------------------------------------------------------------------------
# 从 OCR 文本行里抽取字段的规则
# ---------------------------------------------------------------------------
#
# 真实标签的版式（实测 50 张）：
#
#   - **字段名与值是分开的两行**，如「生产批号：」一行、值 B2609503 另一行；
#   - 同一个值常重复出现多次（品名、代码、批号各印 2~3 遍）；
#   - 标签上还有大量与识别无关的印刷内容（公司名、地址、标准号、操作人…），
#     以及被 OCR 切碎的噪声行（如 ``02020.11.07``、``402025.12.23``）。
#
# 所以规则不能"取第一个匹配"，而要用**业务约束**去筛：
#   物料代码 → 8 位纯数字、首位是 1（Owner 确认：1000/1200/1300/1400 开头）
#   批号     → 字母前缀 + 7 位左右数字（B2609503 / BMT2607701）
#   产品名称 → 排除公司名、字段名等固定噪声后，取出现次数最多的中文名
#   日期     → 合法的 年-月(-日)，**最早作生产日期、最晚作有效期**

# 物料代码允许的形近字母（真正的字母→数字映射在 app.validate）
_CODE_CHARS = "".join(sorted(set(CONFUSABLE_TO_DIGIT) | set("0123456789")))
_CODE_TOKEN = re.compile(rf"(?<![0-9A-Za-z])[{_CODE_CHARS}]{{8}}(?![0-9A-Za-z])")

# 批号：字母前缀 + 数字，可带亚批后缀
_BATCH_TOKEN = re.compile(r"(?<![0-9A-Za-z])([A-Za-z]{1,4}\d{5,9}(?:-\d{1,2})?)(?![0-9A-Za-z])")

# 日期：中文年月日（到月为可缺日）
_CN_DATE = re.compile(r"(?<!\d)(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?")
# 日期：数字分隔（2025.06.25 / 2025-06-25 / 2025/06/25），前后不能紧邻数字，
# 借此滤掉 ``402025.12.23`` 这类粘连噪声
_NUM_DATE = re.compile(r"(?<!\d)(\d{4})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})(?!\d)")
# 日期：数字分隔**只到月**（2028.06）。
# 标签上很常见（实测 39/50 张的有效期就是这样），且**不能**与上面的
# 三段式混淆——末尾的负向断言确保 ``2025.06.25`` 不会被截成 ``2025.06``。
#
# 前面的 ``(?<![\d.])`` 同时挡掉两种粘连：
#   ``402025.12.23`` → ``2025.12`` 前是数字
#   ``的2206.07.21`` → 年份 2206 越界，且 ``206.07`` 不足 4 位
_NUM_MONTH = re.compile(r"(?<![\d.])(\d{4})\s*[.\-/]\s*(\d{1,2})(?!\s*[.\-/]\s*\d)(?!\d)")

# 产品名候选要排除的固定噪声词（公司名、标签名、字段名、包装印刷语）
_NAME_NOISE = (
    "公司", "有限", "标签", "编码", "地址", "标准", "执行", "贮藏", "复核",
    "操作人", "登记号", "来源", "合格证", "原料药", "生产", "日期", "有效期",
    "复检期", "批号", "物料", "代码", "品名", "总件", "净毛", "皮重", "车间",
    "第", "页", "共", "注", "说明", "贮藏", "编号", "版本",
    "省", "市", "区", "街", "路", "号", "坊", "开发区", "工业", "园区",
)

# 「品名：xxx」/「名：xxx」——冒号后即答案
_NAME_LABEL = re.compile(r"(?:品名|名)\s*[:：]\s*(.+)$")

# 生产日期与有效期之间允许的最大间隔（天）。
# 本厂标签效期 2~3 年，给到 5 年留足余量；超过这个跨度还"更早"的日期，
# 基本是 OCR 切出来的噪声而非真生产日期。
_MAX_SHELF_LIFE_DAYS = 365 * 5

# 签核行（操作人/日期、复核人/日期…）。这些行上的日期是**人员签核日期**，
# 不是物料的生产日期或有效期，不能进日期候选——
# 否则「取最早作生产日期」会被签核日期顶掉。
#
# 实测：不排除签核行时，有标签的复核日期被 OCR 误读成 2021.06.27，
# 而真正的生产日期 2025.06.25 因此被挤到"有效期"位置上。
_SIGNATURE_LINE = re.compile(r"操作人|复核人|核发人|签名")


def _iter_lines(lines: list[str]) -> list[str]:
    return [ln.strip() for ln in lines if ln and ln.strip()]


# ---------------------------------------------------------------------------
# 各字段的抽取
# ---------------------------------------------------------------------------


def extract_item_code(lines: list[str]) -> str | None:
    """物料代码：8 位、首位 1。

    先按形近字符映射还原，再要求首位是 ``1``——这一条同时把批号
    （``B2609503`` → 映射后 ``82609503``，首位 8）挡在外面。

    重复出现时取**出现次数最多**的（同一值通常印 2~3 遍）。
    """
    counts: dict[str, int] = {}
    order: list[str] = []
    for line in lines:
        for m in _CODE_TOKEN.finditer(line):
            raw = m.group(0)
            mapped = "".join(CONFUSABLE_TO_DIGIT.get(ch, ch) for ch in raw)
            if not mapped.isdigit() or not mapped.startswith("1"):
                continue
            if mapped not in counts:
                counts[mapped] = 0
                order.append(mapped)
            counts[mapped] += 1
    if not counts:
        return None
    best = max(order, key=lambda v: (counts[v], -order.index(v)))
    return best


def extract_batch_no(lines: list[str]) -> str | None:
    """批号：字母前缀 + 数字。

    批号**可以有字母**（生产线/组份标识），所以这里**不做**形近映射——
    把 ``B`` 映射成 ``8`` 反而会毁掉批号。
    """
    counts: dict[str, int] = {}
    order: list[str] = []
    for line in lines:
        for m in _BATCH_TOKEN.finditer(line):
            tok = m.group(1)
            # 纯字母前缀太短又紧跟长数字的，多半是别的东西；要求前缀 1~4 位即可
            if tok not in counts:
                counts[tok] = 0
                order.append(tok)
            counts[tok] += 1
    if not counts:
        return None
    return max(order, key=lambda v: (counts[v], -order.index(v)))


def extract_product_name(lines: list[str]) -> str | None:
    """产品名称。

    两条路，按可靠性排序：

    1. **贴着字段名取**——标签上有「品名：某原料药甲」「名：某原料药乙」这类行，
       冒号后面的就是答案。实测这比任何统计都准。
    2. 退化到**频次法**：排除公司名/地址/包装语等固定噪声后，取出现次数最多的中文串。

    不能简单取"最长的中文行"——那通常是公司名或生产地址。
    """
    # 1) 贴着「品名：」/「名：」取
    anchored: list[str] = []
    for line in lines:
        m = _NAME_LABEL.search(line)
        if not m:
            continue
        val = m.group(1).strip()
        if not val or re.search(r"[\x00-\x7F]", val):
            continue
        if re.search(r"[一-鿿]{2,}", val):
            anchored.append(val)
    if anchored:
        return max(anchored, key=len)

    # 2) 频次法
    counts: dict[str, int] = {}
    order: list[str] = []
    for line in lines:
        s = line.strip()
        if any(ch in s for ch in "：:（）()"):
            continue  # 带冒号/括号的多半是字段名或包装说明
        if re.search(r"[\x00-\x7F]", s):
            continue  # 含 ASCII 的一律不算品名
        if not re.search(r"[一-鿿]{2,}", s):
            continue
        if any(w in s for w in _NAME_NOISE):
            continue
        if s not in counts:
            counts[s] = 0
            order.append(s)
        counts[s] += 1
    if not counts:
        return None
    # 先比出现次数，再比长度
    return max(order, key=lambda v: (counts[v], len(v), -order.index(v)))


def extract_dates(lines: list[str]) -> list[tuple[str, tuple[int, int, int | None]]]:
    """抽出所有**合法**日期，返回 ``[(原始串, (年, 月, 日或None)), ...]``，按出现顺序。

    只取**物料日期**——签核行（操作人/复核人/日期）上的日期被排除，
    理由见 ``_SIGNATURE_LINE``。

    过滤掉月份/日越界的噪声（如 ``02020.11.07`` 被前后数字约束挡掉，
    ``27112.2`` 不构成 年-月-日 也挡掉）。
    """
    found: list[tuple[str, tuple[int, int, int | None]]] = []

    def push(raw: str, y: str, mo: str, d: str | None) -> None:
        yi, mi = int(y), int(mo)
        di = int(d) if d else None
        if not (2000 <= yi <= 2099):
            return
        if not (1 <= mi <= 12):
            return
        if di is not None and not (1 <= di <= 31):
            return
        found.append((raw, (yi, mi, di)))

    for line in lines:
        if _SIGNATURE_LINE.search(line):
            continue
        for m in _CN_DATE.finditer(line):
            push(m.group(0), m.group(1), m.group(2), m.group(3))
        for m in _NUM_DATE.finditer(line):
            push(m.group(0), m.group(1), m.group(2), m.group(3))
        for m in _NUM_MONTH.finditer(line):
            push(m.group(0), m.group(1), m.group(2), None)

    return found


def _date_key(v: tuple[int, int, int | None]) -> tuple[int, int, int]:
    """把 (年,月,日或None) 变成可比较的键；日缺省当 1 号，仅用于排序。"""
    y, m, d = v
    return (y, m, d if d is not None else 1)


# ---------------------------------------------------------------------------
# 后端
# ---------------------------------------------------------------------------

# 模型档位 → (检测模型, 识别模型)
#
# PaddleOCR 自带多档模型，**无需装任何新依赖**，换个名字即可。
# 实测这台 M4 上「原图 4096×3072、单张」的代价与准确率（50 张真实标签）：
#
#   档位     单张耗时   全字段正确   有效期   说明
#   medium    35 s       84%        96%     最准，但慢
#   small      7 s       80%        90%     **默认**
#   tiny       3 s       72%        80%     最快，但掉太多
#
# 选 small：唯一同时满足耗时标准（≤10 s）与准确率的档位。
# 准确率那点损失由 validate 层的提示 + 强制人工校对兜住。
#
# 注：small 的日期错误主要是**漏读日**（只读到年月）与**取错日期**，
# 不是编造——详见 ``app.validate._date_is_grounded`` 的说明。
MODEL_TIERS = {
    "medium": ("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"),
    "small": ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"),
    "tiny": ("PP-OCRv6_tiny_det", "PP-OCRv6_tiny_rec"),
}

DEFAULT_MODEL_TIER = "small"


def parse_backend_spec(spec: str) -> tuple[str, str]:
    """把 ``c2_ocr`` / ``c2_ocr:small`` 拆成 ``(后端名, 模型档位)``。

    档位缺省用 ``DEFAULT_MODEL_TIER``。不认识的后端名原样返回，交给注册表报错。
    """
    if ":" not in spec:
        return spec, DEFAULT_MODEL_TIER
    name, tier = spec.split(":", 1)
    return name, (tier or DEFAULT_MODEL_TIER)


class PaddleOCRBackend(RecognizeBackend):
    name = BACKEND_C2

    def __init__(self, tier: str | None = None) -> None:
        # 档位可在构造时指定（对照实验用），也可从环境变量取，最后落到默认档
        self.tier = tier or os.environ.get("HBOS_OCR_C2_MODEL") or DEFAULT_MODEL_TIER
        if self.tier not in MODEL_TIERS:
            self.tier = DEFAULT_MODEL_TIER
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

            det, rec = MODEL_TIERS[self.tier]

            # 关掉三个与本任务无关的预处理模型：方向分类、文档矫正、文本行朝向。
            # 标签照片是正着拍的，开了只是白白多花时间和内存。
            self._ocr = PaddleOCR(
                lang="ch",
                text_detection_model_name=det,
                text_recognition_model_name=rec,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

    def recognize(self, image_bytes: bytes, request: RecognizeRequest) -> BackendResult:
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(reason)

        self._ensure_loaded()

        # PaddleOCR 只接受文件路径；临时文件用完即删（M3-R6 方案第六节）
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fh:
            fh.write(image_bytes)
            tmp_path = fh.name

        try:
            raw = self._ocr.predict(tmp_path)
        finally:
            os.unlink(tmp_path)

        lines = self._flatten(raw)
        fields = self._extract(lines)
        return BackendResult(
            fields=fields,
            confidence={},  # 逐行置信度暂不暴露；人工复核由 validate 层的 hints 驱动
            raw_text="\n".join(lines),
            backend=self.name,
        )

    # -- OCR 原始返回 → 文本行 ------------------------------------------------

    @staticmethod
    def _flatten(raw) -> list[str]:
        """把 OCR 返回压平成文本行列表。

        兼容 3.x（``rec_texts``）与 2.x（``[[box, (text, score)], ...]``）两种结构——
        两个版本的返回形状完全不同，且都不会报错，只是静默读不到东西。
        """
        lines: list[str] = []
        if not raw:
            return lines

        for page in raw:
            texts = None

            # 3.x：OCRResult 是 dict 风格
            try:
                texts = page.get("rec_texts")
            except AttributeError:
                texts = None

            if texts:
                lines.extend(str(t) for t in texts)
                continue

            # 2.x：嵌套列表
            for item in page or []:
                try:
                    lines.append(str(item[1][0]))
                except (IndexError, TypeError):
                    continue
        return lines

    @staticmethod
    def _extract(lines: list[str]) -> dict:
        """按业务约束从文本行里抽字段。抽不到留 None，交给人工或主数据回填。"""
        lines = _iter_lines(lines)
        fields = empty_fields()

        fields["item_code"] = extract_item_code(lines)
        fields["batch_no"] = extract_batch_no(lines)
        fields["product_name"] = extract_product_name(lines)

        # 日期：有效期取**最晚**的；生产日期取**最有可能的那一个**。
        #
        # 生产日期不能只是"取最早"（实测教训）：有标签上出现三个日期——
        #     2020.11.07  ← OCR 把某段印刷内容切出来的噪声
        #     2025.06.25  ← **真正的生产日期，模型读对了**
        #     2028.06.24  ← 有效期
        # 「取最早」把噪声当成了生产日期，**读对的正确值反被扔掉**，
        # 且格式合法、原文里确实有这串数字，任何格式校验都拦不住。
        #
        # 但也不能改成"早于有效期的最晚一个"——实测那样反而更差（会选到
        # 靠近生产日期的另一个噪声日期）。改用**保质期常识**来筛：
        # 本厂标签效期 2~3 年，那么"离效期 5 年以上"的日期当生产日期就不合常理，
        # 判为噪声剔除；剩下的候选里再取最早。
        uniq: dict[tuple[int, int, int | None], str] = {}
        for raw, val in extract_dates(lines):
            uniq.setdefault(val, raw)

        if uniq:
            ordered = sorted(uniq.items(), key=lambda kv: _date_key(kv[0]))

            # 有效期：最晚的一个
            if len(ordered) > 1:
                fields["expiry_date"] = ordered[-1][1]

            # 生产日期：剔除"离效期远得不像话"的噪声，取剩下里最早的
            earlier = ordered[:-1]  # 严格早于有效期的候选（有效期自己不算）
            if earlier:
                e_y, e_m, e_d = ordered[-1][0]
                expiry = datetime.date(e_y, e_m, e_d or 1)

                def gap_days(kv):
                    y, m, d = kv[0]
                    return (expiry - datetime.date(y, m, d or 1)).days

                plausible = [kv for kv in earlier if gap_days(kv) <= _MAX_SHELF_LIFE_DAYS]
                # 全被剔光就退回不筛，宁可给个日期也不要弄丢
                fields["manufacturing_date"] = (plausible or earlier)[0][1]
            else:
                fields["manufacturing_date"] = ordered[0][1]

        return fields
