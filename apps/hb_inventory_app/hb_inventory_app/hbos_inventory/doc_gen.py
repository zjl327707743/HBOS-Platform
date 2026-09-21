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
