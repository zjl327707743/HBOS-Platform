from __future__ import annotations

"""「取消已提交单据」契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

仓管本轮才拿到「取消」入口。这条链上有几处**抄错就会静默坏掉**的地方：

1. **`cancel` 与 `submit` 的传参语义相反**。`submit` 走 `frappe.get_doc(dict)`，
   必须先把全文读回来再提交；`cancel` 走 `frappe.get_doc(doctype, name)`，只传
   单号即可。照抄 `submitDocument` 的写法不会报错，但会多一次无谓的全文读取
   （也就罢了）；**反过来**照抄 `cancelDocument` 去写 submit 会让提交必然失败。
   所以这里钉住两者的形状。

2. **拍照识别那页的三态**。该页早先只判 `docstatus === 1`，`docstatus === 2`
   会掉进**可编辑的复核表单**——一张已经冲销掉的入库单被当成草稿给人改。
   与上一轮修掉的三态缺陷同源，所以单独钉一条。

3. **文案**。提交确认框若还写着「提交后如需撤销，要走红字冲销」，就等于对用户
   撒谎（本页已经能取消了）。
"""

import re
import unittest
from pathlib import Path

SRC = Path(__file__).parents[3] / "frontend" / "hbos-portal-web" / "src"
CLIENT_TS = SRC / "services" / "frappeClient.ts"
DOCS_TS = SRC / "services" / "inventoryDocs.ts"
ENTRY_TS = SRC / "services" / "inventoryEntry.ts"
PICK_TS = SRC / "services" / "inventoryPick.ts"
DRAFT_VIEW = SRC / "views" / "InventoryDraftReviewView.vue"
ENTRY_VIEW = SRC / "views" / "InventoryEntryView.vue"
PICK_VIEW = SRC / "views" / "InventoryPickView.vue"

#: (视图, 该视图要 import 的 service 函数)
VIEW_SERVICE_WIRING = (
    (ENTRY_VIEW, "cancelStockEntry"),
    (PICK_VIEW, "cancelPickList"),
    (DRAFT_VIEW, "cancelIntakeDraft"),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class CancelTransportContractTest(unittest.TestCase):
    def test_client_exports_cancel_document(self):
        text = _read(CLIENT_TS)
        self.assertIn("export async function cancelDocument(", text)

    def test_cancel_calls_the_whitelisted_method_with_doctype_and_name(self):
        """`frappe.client.cancel` 只需 {doctype, name}，**不要像 submit 那样传全文**。"""
        text = _read(CLIENT_TS)
        body = re.search(r"export async function cancelDocument\(.*?\n\}", text, re.S)
        self.assertIsNotNone(body, "找不到 cancelDocument 函数体")
        body = body.group(0)
        self.assertIn("frappe.client.cancel", body)
        self.assertNotIn("getDocument", body, "cancel 不该先读全文——它的语义是按名字加载")
        self.assertNotIn("JSON.stringify", body, "cancel 不需要传 doc 字典")

    def test_submit_still_reads_the_full_doc(self):
        """反向钉住：submit 必须仍然先读全文（这是实测会失败的那个坑）。"""
        text = _read(CLIENT_TS)
        body = re.search(r"export async function submitDocument\(.*?\n\}", text, re.S)
        self.assertIsNotNone(body)
        self.assertIn("getDocument", body.group(0))


class CancelServiceContractTest(unittest.TestCase):
    def test_each_service_wraps_cancel_document(self):
        cases = (
            (DOCS_TS, "cancelIntakeDraft", "Stock Entry"),
            (ENTRY_TS, "cancelStockEntry", "Stock Entry"),
            (PICK_TS, "cancelPickList", "Pick List"),
        )
        for path, fn, doctype in cases:
            text = _read(path)
            self.assertIn(f"export async function {fn}(", text, f"{path.name} 缺 {fn}")
            body = re.search(rf"export async function {fn}\(.*?\n\}}", text, re.S)
            self.assertIsNotNone(body, f"{path.name} 里 {fn} 的函数体没解析出来")
            body = body.group(0)
            self.assertIn("cancelDocument", body, f"{fn} 必须走共享的 cancelDocument")
            self.assertIn(doctype, body, f"{fn} 的 doctype 应为 {doctype}")


class CancelViewContractTest(unittest.TestCase):
    def test_views_import_and_call_their_cancel_service(self):
        for view, fn in VIEW_SERVICE_WIRING:
            text = _read(view)
            self.assertIn(fn, text, f"{view.name} 没接上 {fn}")
            self.assertRegex(
                text,
                rf"await\s+{fn}\(",
                f"{view.name} 必须真的 await {fn}()",
            )

    def test_cancel_failures_surface_the_server_message(self):
        """取消失败（权限 / 依赖 / 状态不对）要把服务端的中文提示呈现出来，
        不能吞掉——否则用户只看到「什么都没发生」。"""
        for view, _fn in VIEW_SERVICE_WIRING:
            text = _read(view)
            self.assertRegex(
                text,
                r"取消失败",
                f"{view.name} 的取消失败要有可读的错误呈现",
            )
            self.assertIn("FrappeHttpError", text)

    def test_cancel_button_is_a_guarded_danger_action(self):
        """取消要二次确认（`Modal.confirm`）且是危险色，不能一点就走。"""
        for view, _fn in VIEW_SERVICE_WIRING:
            text = _read(view)
            self.assertRegex(
                text,
                r"danger[^>]*@click=\"confirmCancel\"",
                f"{view.name} 的取消按钮应是 danger 且绑到 confirmCancel",
            )
            self.assertRegex(text, r"function confirmCancel\(", f"{view.name} 缺 confirmCancel")
            self.assertRegex(
                text,
                r"function confirmCancel\([\s\S]{0,400}?Modal\.confirm\(",
                f"{view.name} 的 confirmCancel 必须走 Modal.confirm 二次确认",
            )


class DraftReviewThreeStateTest(unittest.TestCase):
    """拍照识别复核页：`docstatus=2` 必须落在「已取消」，**不能掉进可编辑表单**。"""

    def test_view_state_includes_cancelled(self):
        text = _read(DRAFT_VIEW)
        decl = re.search(r"type ViewState =.*", text)
        self.assertIsNotNone(decl, "找不到 ViewState 声明")
        self.assertIn("'cancelled'", decl.group(0))

    def test_mounted_handles_docstatus_two(self):
        text = _read(DRAFT_VIEW)
        self.assertRegex(
            text,
            r"docstatus\s*===\s*2[\s\S]{0,200}?state\.value\s*=\s*'cancelled'",
            "onMounted 必须把 docstatus===2 落到 cancelled，否则会显示可编辑的复核表单",
        )


class NoStaleReversalCopyTest(unittest.TestCase):
    def test_red_letter_reversal_copy_is_gone(self):
        """本页已能取消，再说「要走红字冲销」就是骗用户。"""
        for view in (ENTRY_VIEW, DRAFT_VIEW):
            self.assertNotIn(
                "红字冲销",
                _read(view),
                f"{view.name} 还留着「要走红字冲销」——现在可以直接取消",
            )


if __name__ == "__main__":
    unittest.main()
