from __future__ import annotations

"""「自定义字段归属」契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

本项目已经**四次**栽在同一类缺陷上：**假设了不存在的结构**。

    1. `Bin.batch_no`               （v16 起批次库存在 Serial and Batch Entry）
    2. 对账的账面数                  （必须带 row 参数，否则 500）
    3. `Pick List.posting_date`      （该 doctype 根本没有日期字段）
    4. `Batch.hbos_storage_condition`（实为 `Item` 上的字段）

前三次是**查询字段**（服务端会 417/500，能在运行态撞出来）。第 4 次更隐蔽：
`frappe.client.get` **不做字段校验**，从 `Batch` 上读一个 `Item` 的字段只会
默默返回 `undefined` —— 页面「本批信息」永远空白，而打印件（`print_utils`
也是从 `Item` 取）却有值。**同一份事实，两处不一致，且不报错。**

这类缺陷静态测试抓不到「运行态到底有没有」，但**归属**是能从源码里锁死的：
自定义字段由 `setup.py` 声明，前端读哪个 doctype 也写在源码里。两边一比即可。

## 它守什么

- `inventoryDocs.ts` 的 `RawBatch` 里出现的每个 `hbos_*` 字段，
  必须在 `setup.py` 的 `Batch` 自定义字段里**确实声明过**；
- 三个物料主数据字段（储存条件 / 生产车间 / 效期类型）必须声明在 `Item` 上，
  且 `getBatch` 的映射要取自 `master.`（回查 Item），不是批次文档。

同 `test_report_contract.py` 的套路：**把重复变成有测试兜底的重复。**
"""

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SETUP_PY = ROOT / "hb_inventory_app" / "hbos_inventory" / "setup.py"
INVENTORY_DOCS = (
    Path(__file__).parents[3]
    / "frontend"
    / "hbos-portal-web"
    / "src"
    / "services"
    / "inventoryDocs.ts"
)

#: 这三个是**物料主数据**字段，`setup.py` 把它们建在 `Item` 上，`Batch` 上没有。
MASTER_FIELDS_ON_ITEM = (
    "hbos_storage_condition",
    "hbos_workshop",
    "hbos_shelf_life_type",
)


def _custom_fields_by_doctype() -> dict[str, set[str]]:
    """从 setup.py 里**静态**取出「doctype → 自定义字段名集合」。

    用 `ast` 解析而不 import —— setup.py 顶层 `import frappe`，测试环境没有
    site 也要能跑。找不到 `create_custom_fields` 调用就抛错，不静默返回空
    （否则测试会「因为什么都没测」而假绿）。
    """
    tree = ast.parse(SETUP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name != "create_custom_fields" or not node.args:
            continue
        mapping = node.args[0]
        if not isinstance(mapping, ast.Dict):
            continue
        result: dict[str, set[str]] = {}
        for key, value in zip(mapping.keys, mapping.values):
            if not isinstance(key, ast.Constant) or not isinstance(value, ast.List):
                continue
            names = set()
            for entry in value.elts:
                if not isinstance(entry, ast.Dict):
                    continue
                for k, v in zip(entry.keys, entry.values):
                    if (
                        isinstance(k, ast.Constant)
                        and k.value == "fieldname"
                        and isinstance(v, ast.Constant)
                    ):
                        names.add(str(v.value))
            result[str(key.value)] = names
        if result:
            return result
    raise AssertionError("setup.py 里找不到 create_custom_fields(...) 的定义")


def _raw_interface_body(name: str) -> str:
    """取出 `interface <name> { ... }` 的正文（花括号配平）。"""
    text = INVENTORY_DOCS.read_text(encoding="utf-8")
    match = re.search(rf"interface\s+{re.escape(name)}\s*\{{", text)
    if not match:
        raise AssertionError(f"inventoryDocs.ts 里找不到 interface {name}")
    start = match.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start : i - 1]


class BatchMasterFieldContractTest(unittest.TestCase):
    def setUp(self):
        self.fields = _custom_fields_by_doctype()

    def test_setup_declares_the_three_master_fields_on_item(self):
        item = self.fields.get("Item", set())
        for field in MASTER_FIELDS_ON_ITEM:
            self.assertIn(
                field,
                item,
                f"{field} 必须声明在 Item 上（它是物料主数据，不是批次字段）",
            )

    def test_setup_does_not_declare_master_fields_on_batch(self):
        batch = self.fields.get("Batch", set())
        for field in MASTER_FIELDS_ON_ITEM:
            self.assertNotIn(
                field,
                batch,
                f"{field} 不该声明在 Batch 上——它与 Item 上同名会造成两个真相来源",
            )

    def test_raw_batch_only_reads_fields_that_exist_on_batch(self):
        """RawBatch 里出现的每个 hbos_* 字段，都必须是 Batch 的自定义字段。

        读 `Batch` 上一个「其实是 Item 的字段」不会报错，只会静默返回 undefined，
        所以这条只能靠静态归属来挡。
        """
        declared = self.fields.get("Batch", set())
        body = _raw_interface_body("RawBatch")
        read = set(re.findall(r"\b(hbos_[a-z_]+)\??:", body))
        self.assertTrue(read, "RawBatch 里没解析出任何 hbos_* 字段——正则失效了")

        missing = sorted(f for f in read if f not in declared)
        self.assertEqual(
            [],
            missing,
            f"RawBatch 读了 Batch 上不存在的字段（Batch 声明的是 {sorted(declared)}）",
        )

    def test_get_batch_takes_master_fields_from_item_not_batch_doc(self):
        """`getBatch` 的三个主数据字段必须来自 `master.`（Item 回查），不是 `doc.`。"""
        text = INVENTORY_DOCS.read_text(encoding="utf-8")
        match = re.search(r"export async function getBatch\b.*?\n\}", text, re.S)
        self.assertIsNotNone(match, "找不到 getBatch 函数体")
        body = match.group(0)

        for prop in ("storageCondition", "workshop", "shelfLifeType"):
            self.assertRegex(
                body,
                rf"{prop}:\s*master\.",
                f"getBatch 的 {prop} 应从 master（Item）取，不该从批次文档读",
            )
            self.assertNotRegex(
                body,
                rf"{prop}:\s*doc\.",
                f"getBatch 的 {prop} 不能从批次文档（doc）读——Batch 上没有该字段",
            )


if __name__ == "__main__":
    unittest.main()
