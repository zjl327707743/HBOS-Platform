"""入库提交后自动生成货位卡与待检证。

把 M3-R4（打印格式）与 M3-R6（拍照识别入库）接上：入库单提交后，
按单据里的批次自动生成「待检证 + 货位卡」PDF，挂到对应 `Batch` 的附件里。

## 为什么挂在 `on_submit` 而不是生成草稿时

货位卡上的**货位明细 / 入库数量 / 入库日期 / 流水表**都来自真实库存流水
（`Stock Ledger Entry`）。草稿阶段这些**都还不存在**；而且草稿的货位和数量
还能改，改了卡就作废。所以必须等提交。

`frappe/model/document.py` 的 `compose()` 先调控制器方法、再跑 `doc_events` 钩子，
因此 ERPNext 的 `StockEntry.on_submit`（建 SLE）**跑完才轮到本模块**——数据齐了。

## 纸型：为什么要在生成时追加覆盖 CSS

Frappe 打印框架会给每个 Print Format 注入这段：

    .print-format { min-height: 11.69in; padding: 0.75in }
    .print-format td { padding: 6px !important }

`min-height: 11.69in` = 297mm，是**给 A4 屏幕预览**用的。放在 75×110mm 的
待检证纸上，内容块最小就有 297mm → **必然溢出成 2 页**，跟模板写得好不好无关。

实测：不改这段时，待检证无论怎么缩小字号都是 2 页；压掉之后才是 1 页。

所以生成时追加一段覆盖 CSS（`_FRAME_OVERRIDE`），**不改任何 Print Format 模板**。

## 失败不阻断入库

`on_submit` 里抛异常会**回滚整个提交**。生成 PDF 是附加动作，
绝不能因为渲染失败让人入不了库。故整段 try/except 兜底，失败只记日志，
可在 `Batch` 表单上点「重新生成」补。
"""

from __future__ import annotations

import io
import re
import unicodedata

import frappe
from frappe import _
from frappe.utils.pdf import get_pdf

# 待检证 / 自产货位卡 / 外购货位卡（与 print_format 目录下的 `name` 一致）
FMT_QUARANTINE = "HBOS 待检证"
FMT_CARD_SELF = "HBOS 自产货位卡"
FMT_CARD_OUTSOURCED = "HBOS 外购货位卡"

SOURCE_OUTSOURCED = "外购"

# 生成的文件名固定成这个形状，`_purge_previous` 靠它认出「哪些是我们生成的」，
# 从而在重新生成时只删自己那份，**绝不碰人工上传的附件**。
FILENAME_TPL = "HBOS-{batch_id}-待检证+货位卡.pdf"

# 纸型。待检证是 75×110mm 实物标签，货位卡是 A4。
# 注意：wkhtmltopdf **不认 CSS 的 @page size**，纸型只能从这里传。
PDF_OPT_LABEL = {
    "page-width": "75mm",
    "page-height": "110mm",
    "margin-top": "4mm",
    "margin-bottom": "4mm",
    "margin-left": "5mm",
    "margin-right": "5mm",
}
PDF_OPT_A4 = {
    "page-size": "A4",
    "margin-top": "14mm",
    "margin-bottom": "14mm",
    "margin-left": "14mm",
    "margin-right": "14mm",
}

# 压掉 Frappe 打印框架的 A4 假设（详见模块 docstring）。`!important` 是必需的——
# 框架那条 `td { padding: 6px !important }` 不带 important 压不动。
_FRAME_OVERRIDE = """<style>
.print-format { min-height: 0 !important; max-height: none !important;
                max-width: none !important; padding: 0 !important; margin: 0 !important; }
.print-format td, .print-format th { padding: 2px 3px !important; }
</style>"""


def _render(doctype: str, name: str, print_format: str, options: dict) -> bytes:
    """渲染单个 Print Format 为 PDF 字节。

    用 `frappe.get_print(as_pdf=False)` 先取 HTML，是为了能插入覆盖 CSS——
    直接 `as_pdf=True` 拿不到注入前的 HTML。
    """
    html = frappe.get_print(doctype, name, print_format=print_format, as_pdf=False)
    html = html.replace("</head>", _FRAME_OVERRIDE + "</head>", 1)
    return get_pdf(html, options=options)


def _attach_pdf(batch_name: str, filename: str, content: bytes) -> str:
    """把 PDF 挂到 `Batch` 上，返回 `File` 的 docname。

    与 `api.py::_attach_photo` 同一套做法（`File` 存内网，随单据走）。
    内容直接以字节传入，不落中间文件。
    """
    f = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": filename,
            "is_private": 1,
            "attached_to_doctype": "Batch",
            "attached_to_name": batch_name,
            "content": content,
        }
    )
    f.flags.ignore_permissions = True
    f.insert()
    return f.name


def _purge_previous(batch_name: str, filename: str) -> int:
    """删掉本 App 之前给这个批次生成的那一份（按文件名精确匹配）。

    只删同名文件——**人工上传的附件名字不会长这样，动不到**。
    重提（amend）时不这么做，附件会越堆越多。
    """
    stale = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Batch",
            "attached_to_name": batch_name,
            "file_name": filename,
        },
        pluck="name",
    )
    for name in stale:
        frappe.delete_doc("File", name, force=True, ignore_permissions=True)
    return len(stale)


def _card_format_for(batch_name: str) -> str:
    """按批次的来源类型选自产货位卡还是外购货位卡。"""
    source = frappe.db.get_value("Batch", batch_name, "hbos_source_type")
    return FMT_CARD_OUTSOURCED if source == SOURCE_OUTSOURCED else FMT_CARD_SELF


# ---------------------------------------------------------------------------
# ToUnicode 修补：wkhtmltopdf 会把一批汉字的码位写成「康熙部首」
# ---------------------------------------------------------------------------
#
# Qt（wkhtmltopdf 的渲染内核）生成 PDF 的 ToUnicode CMap 时，对这些字形
# **挑了康熙部首块的码位**（U+2E80–U+2FDF）而不是正常汉字（U+4E00–U+9FFF）——
# 因为这些字形在字体里同时挂在这两个码位上。
#
# 后果分两种，都真实存在：
#
# - **页面上看着是对的**（渲染按字形走，字形本身没错），所以肉眼容易放过；
# - **复制/搜索拿到的是部首字符**，而且**按 Unicode 回查字体的阅读器**
#   （部分手机端、部分网页预览、PDF 无障碍朗读）会去取「部首字形」——
#   那是为部首区单独设计的小号/错位字形，**看起来就是乱字**。
#
# 实测受影响的是这几个常用字：人 入 手 日 月 生 自 行
# （正好是「操作人/日期」「入库」「经手人」「生产单位」「自产」「放行」用到的）。
#
# 修法：把 CMap 里落在部首区的**目标**码位换回对应汉字。康熙部首在 Unicode
# 里有兼容分解，NFKC 一下正好得到那个字，不用自己维护映射表。

_KANGXI_LO, _KANGXI_HI = 0x2E80, 0x2FDF
_BFCHAR_RE = re.compile(r"beginbfchar(.*?)endbfchar", re.S)
_BFRANGE_RE = re.compile(r"beginbfrange(.*?)endbfrange", re.S)
_HEX4 = r"<[0-9A-Fa-f]{4}>"

# 「CJK 部首补充」里那批**简体部首**（U+2E80–U+2EF3）没有 Unicode 兼容分解，
# NFKC 救不了，只能列出来。它们本身就是独立的字，只是长得和简体字一样，
# Qt 又挑了部首那个码位。实测我们的模板会碰到 `⻋`（生产车间）和 `⻚`（第（ ）页）。
_RADICAL_SUPPLEMENT = {
    0x2EB0: "纟",  # ⺰ → 纟
    0x2EC5: "见",  # ⻅ → 见
    0x2EC8: "言",  # ⻈ → 言
    0x2ECB: "车",  # ⻋ → 车
    0x2ED0: "金",  # ⻐ → 金
    0x2ED3: "长",  # ⻓ → 长
    0x2ED4: "门",  # ⻔ → 门
    0x2EDA: "页",  # ⻚ → 页
    0x2EDB: "风",  # ⻛ → 风
    0x2EDC: "飞",  # ⻜ → 飞
    0x2EE0: "食",  # ⻠ → 食
    0x2EE2: "马",  # ⻢ → 马
    0x2EE5: "鱼",  # ⻥ → 鱼
    0x2EE6: "鸟",  # ⻦ → 鸟
    0x2EF0: "龙",  # ⻰ → 龙
    0x2EF3: "龟",  # ⻳ → 龟
}


def _kangxi_to_han(hex4: str) -> str:
    """`<XXXX>` 形式的码位：是部首就换成对应汉字，否则原样返回（含尖括号）。"""
    cp = int(hex4.strip("<>"), 16)
    if _KANGXI_LO <= cp <= _KANGXI_HI:
        han = _RADICAL_SUPPLEMENT.get(cp) or unicodedata.normalize("NFKC", chr(cp))
        if han != chr(cp):
            return "<" + han.encode("utf-16-be").hex().upper() + ">"
    return hex4


def _fix_tounicode_cmap(text: str) -> str:
    """改一份 ToUnicode CMap 文本。

    **只动目标码位**，不碰源码位——源是 CID，也可能正好长得像 `2Fxx`，
    一起改就全错位了。

    目标有两种写法（Qt 两种都用）：

        beginbfchar
        <0003> <2F08>                       ← 单值：改第 2 个
        endbfchar

        beginbfrange
        <0000> <0000> <0000>                ← 单值：改第 3 个
        <0001> <0020> [<5F85> <2F47> ...]   ← 数组：改方括号里的**每一个**
        endbfrange

    数组那种最容易漏——它是「一个 CID 区间对应一串目标字」，位置即语义，
    所以只能在原位置逐个换值，不能增删。
    """

    def fix_hex(m):
        return _kangxi_to_han(m.group(0))

    def fix_char(m):
        def one_line(line):
            # 多单元目标 <AABB CCDD>、及罕见的数组写法，统一在行内替换
            return re.sub(_HEX4, fix_hex, line) if line.count("<") > 2 else _fix_pair(line)

        def _fix_pair(line):
            parts = re.findall(_HEX4, line)
            if len(parts) != 2:
                return line
            return f"{parts[0]} {_kangxi_to_han(parts[1])}"

        body = "".join(one_line(l) for l in m.group(1).splitlines(keepends=True))
        return "beginbfchar" + body + "endbfchar"

    def fix_range(m):
        def one_line(line):
            if "[" in line:
                return re.sub(
                    r"\[(.*?)\]",
                    lambda mm: "[" + re.sub(_HEX4, fix_hex, mm.group(1), flags=re.S) + "]",
                    line,
                    flags=re.S,
                )
            parts = re.findall(_HEX4, line)
            if len(parts) != 3:
                return line
            return f"{parts[0]} {parts[1]} {_kangxi_to_han(parts[2])}"

        body = "".join(one_line(l) for l in m.group(1).splitlines(keepends=True))
        return "beginbfrange" + body + "endbfrange"

    return _BFRANGE_RE.sub(fix_range, _BFCHAR_RE.sub(fix_char, text))


def _fix_pdf_tounicode(writer) -> int:
    """就地修 `PdfWriter` 里所有字体的 ToUnicode，返回改动的流数。

    在 `writer.write()` **之前**调用。详见上方长注释。
    """
    changed = 0
    for page in writer.pages:
        fonts = (page.get("/Resources") or {}).get("/Font") or {}
        for ref in fonts.values():
            font = ref.get_object()
            stream = font.get("/ToUnicode")
            if stream is None:
                continue
            raw = stream.get_data().decode("latin-1")
            fixed = _fix_tounicode_cmap(raw)
            if fixed != raw:
                stream.set_data(fixed.encode("latin-1"))
                changed += 1
    return changed


def generate_for_batch(batch_name: str) -> dict:
    """为一个批次生成「待检证 + 货位卡」合并 PDF 并挂到该批次上。

    **不做异常兜底**——由调用方决定失败怎么处理（入库流程要吞掉，手动按钮要抛）。
    """
    batch_id = frappe.db.get_value("Batch", batch_name, "batch_id") or batch_name
    filename = FILENAME_TPL.format(batch_id=batch_id)
    card_fmt = _card_format_for(batch_name)

    # 两段纸型不同，所以分两次渲染、再塞进同一个 writer。
    # 这是 Frappe 自己的做法，见 `frappe/utils/print_format.py` 的多格式下载。
    from pypdf import PdfWriter

    writer = PdfWriter()
    label = _render("Batch", batch_name, FMT_QUARANTINE, PDF_OPT_LABEL)
    writer.append(io.BytesIO(label))
    card = _render("Batch", batch_name, card_fmt, PDF_OPT_A4)
    writer.append(io.BytesIO(card))

    # 必须在 write() 之前：见 _fix_pdf_tounicode 上方长注释
    _fix_pdf_tounicode(writer)

    buf = io.BytesIO()
    writer.write(buf)
    content = buf.getvalue()

    _purge_previous(batch_name, filename)
    file_name = _attach_pdf(batch_name, filename, content)

    return {
        "batch": batch_name,
        "batch_id": batch_id,
        "card_format": card_fmt,
        "file": file_name,
        "bytes": len(content),
    }


def generate_for_stock_entry(doc, method: str | None = None) -> None:
    """`Stock Entry` 的 `on_submit` 钩子：给单里每个批次生成一套卡。

    只处理 **Material Receipt**（入库）。Material Transfer / Issue 等不动。

    **失败必须吞掉**：`on_submit` 抛异常会回滚整个提交，
    绝不能因为生成 PDF 出错就让人入不了库。出错记 `Error Log`，可手动补生成。
    """
    try:
        if doc.get("purpose") != "Material Receipt":
            return

        batches = _distinct_batches(doc)
        if not batches:
            return

        done, failed = [], []
        for batch_name in batches:
            try:
                done.append(generate_for_batch(batch_name))
            except Exception as exc:  # noqa: BLE001
                failed.append(batch_name)
                frappe.log_error(
                    title="生成货位卡/待检证失败",
                    message=f"批次 {batch_name}（入库单 {doc.name}）\n{type(exc).__name__}: {exc}",
                )

        if done:
            frappe.msgprint(
                _("已自动生成货位卡与待检证：{0} 个批次。可在批次的附件中查看。").format(len(done)),
                indicator="green",
                alert=True,
            )
        if failed:
            # 如实告知，并给出补救路径——不静默
            frappe.msgprint(
                _("有 {0} 个批次的货位卡/待检证**生成失败**：{1}。"
                  "入库本身已完成，可在批次页面点「重新生成货位卡 / 待检证」重试。").format(
                    len(failed), "、".join(failed)
                ),
                indicator="orange",
                alert=True,
            )
    except Exception as exc:  # noqa: BLE001
        frappe.log_error(
            title="自动生成货位卡/待检证失败（整体）",
            message=f"入库单 {doc.name}\n{type(exc).__name__}: {exc}",
        )


def _distinct_batches(doc) -> list[str]:
    """单据里出现过的批次（去重、保序、跳过空值）。

    同一批次可能拆成多行（不同货位），但**一个批号只对应一张货位卡**（M3-R0 确认），
    所以这里必须去重，否则会生成重复的卡。
    """
    seen: list[str] = []
    for item in doc.get("items") or []:
        batch = (item.get("batch_no") or "").strip()
        if batch and batch not in seen and frappe.db.exists("Batch", batch):
            seen.append(batch)
    return seen


@frappe.whitelist()
def regenerate_for_batch(batch_name: str) -> dict:
    """供「重新生成」按钮调用：白名单方法，带权限检查，失败要抛给界面看。

    与入库钩子相反——这里**不吞异常**，操作员点了按钮就该知道成没成。
    """
    if not (set(frappe.get_roles()) & {"System Manager", "Stock Manager", "Stock User"}):
        frappe.throw(_("你无权重新生成货位卡 / 待检证。"), frappe.PermissionError)

    if not frappe.db.exists("Batch", batch_name):
        frappe.throw(_("找不到批次：{0}").format(batch_name))

    out = generate_for_batch(batch_name)
    frappe.msgprint(
        _("已生成：{0}（{1} KB）").format(out["file"], round(out["bytes"] / 1024, 1)),
        indicator="green",
        alert=True,
    )
    return out
