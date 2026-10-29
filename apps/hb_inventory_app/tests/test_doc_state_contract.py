from __future__ import annotations

"""单据状态三态契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

三个写入页（库存单据 / 拣货单 / 库存对账）都按 `docstatus` 决定状态标签与是否可编辑。
早先都写成二元判断：

    :class="docstatus === 1 ? 'submitted' : 'draft'"
    const readonly = computed(() => docstatus.value === 1)

**`docstatus` 是三态：0 草稿 / 1 已提交 / 2 已取消。** 二元判断把**已取消**的单据
读成「草稿」——标签显示成琥珀色的「草稿 · 未入账」，而且 `readonly` 为 false，
界面白让用户去编辑一张已经冲销掉的单据（点了保存服务端才拒）。

## 它守什么

1. `inventoryDocs.ts` 必须导出 `docState`，且 2 映射到 `cancelled`；
2. 三个视图里**不得**再出现二元的状态标签类绑定，且 `readonly` 必须走 `docState`。
"""

import re
import unittest
from pathlib import Path

SRC = Path(__file__).parents[3] / "frontend" / "hbos-portal-web" / "src"
DOCS_TS = SRC / "services" / "inventoryDocs.ts"
VIEWS = (
    SRC / "views" / "InventoryEntryView.vue",
    SRC / "views" / "InventoryPickView.vue",
    SRC / "views" / "InventoryReconcileView.vue",
)

#: 二元状态绑定的醒目写法（改回它就意味着「已取消」会被读成「草稿」）
NAIVE_TAG = re.compile(r"docstatus\s*===\s*1\s*\?\s*'submitted'\s*:\s*'draft'")


class DocStateContractTest(unittest.TestCase):
    def test_inventory_docs_exports_three_state_helper(self):
        text = DOCS_TS.read_text(encoding="utf-8")
        self.assertIn("export function docState(", text, "必须导出 docState 三态助手")
        body = re.search(r"export function docState\(.*?\n\}", text, re.S)
        self.assertIsNotNone(body)
        body = body.group(0)
        self.assertIn("return 'cancelled'", body, "docState 必须把 2 归为 cancelled")
        self.assertIn("=== 1", body, "docState 必须把 1 归为 submitted")

    def test_views_do_not_use_two_state_status_binding(self):
        for view in VIEWS:
            text = view.read_text(encoding="utf-8")
            self.assertIsNone(
                NAIVE_TAG.search(text),
                f"{view.name} 仍有二元状态绑定 —— docstatus=2（已取消）会被读成「草稿」",
            )

    def test_views_base_readonly_on_doc_state(self):
        for view in VIEWS:
            text = view.read_text(encoding="utf-8")
            readonly = re.search(r"const readonly = computed\(\(\) =>.*?\)", text)
            self.assertIsNotNone(readonly, f"{view.name} 找不到 readonly 定义")
            expr = readonly.group(0)
            # 允许 `docStateOf(docstatus.value) !== 'draft'` 或 `docState.value !== 'draft'`
            self.assertTrue(
                "docStateOf" in expr or "docState.value" in expr,
                f"{view.name} 的 readonly 必须基于三态（已取消的单据不可编辑），实际：{expr}",
            )
            self.assertNotIn(
                "docstatus.value === 1",
                expr,
                f"{view.name} 的 readonly 又退回二元判断了（已取消会被当成可编辑）",
            )


if __name__ == "__main__":
    unittest.main()
