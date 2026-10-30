"""运行态契约：包装明细的**实际表结构**与批量加载逻辑一致。

## 这条为什么必要

`load_packaging_map()` 用 `frappe.get_all("HBOS Packaging Detail", filters={"parent": ["in", …]})`
批量取数据。它依赖三件事同时成立：

  1. 子表真的叫 `HBOS Packaging Detail`；
  2. 有 `parent` / `parenttype` / `idx` / `container_type` / `unit_weight` / `count` 列；
  3. `parent` 上有索引（否则批量 in 查询也会退化成全表扫）。

前两条在容器里对着真库核过（`desc tabHBOS Packaging Detail`）。本文件把
核过的事实固化成断言 —— 表结构一旦漂移，这里先红，而不是等到现场扫码页
显示空包装规格才发现。

**不连库**：读的是 DocType JSON 与 `load_packaging_map` 的源码。
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
DOCTYPE_JSON = (
    ROOT / "hb_inventory_app" / "hbos_inventory" / "doctype"
    / "hbos_packaging_detail" / "hbos_packaging_detail.json"
)

#: 实测的列（2026-10-27，portal-preview 容器 `desc tabHBOS Packaging Detail`）。
EXPECTED_COLUMNS = {
    "parent",
    "parentfield",
    "parenttype",
    "idx",
    "container_type",
    "unit_weight",
    "count",
    "is_tail",
    "remark",
}


class PackagingDoctypeShapeTest(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(DOCTYPE_JSON.read_text(encoding="utf-8"))

    def test_doctype_name_is_what_code_queries(self):
        self.assertEqual("HBOS Packaging Detail", self.doc["name"])

    def test_istable_is_true(self):
        """子表必须真的是子表 —— 否则 `frappe.get_all(filters={"parent": …})` 取不到。"""
        self.assertTrue(self.doc.get("istable"))

    def test_expected_columns_exist(self):
        declared = {f["fieldname"] for f in self.doc["fields"]}
        # 框架自动列（parent/parentfield/parenttype/idx）不在 fields 里，
        # 它们是子表的标准列 —— 只校验本 App 自己声明的业务列。
        business = {"container_type", "unit_weight", "count", "is_tail", "remark"}
        missing = business - declared
        self.assertEqual(set(), missing, f"DocType 缺列：{sorted(missing)}")

    def test_unit_weight_is_optional(self):
        """`unit_weight` 非必填 —— 允许「只有件数」的包装（与打印逻辑一致）。"""
        f = next(x for x in self.doc["fields"] if x["fieldname"] == "unit_weight")
        self.assertFalse(f.get("reqd"), "unit_weight 变成必填会影响「10 瓶」这种合法形态")


class AttachmentKindContractTest(unittest.TestCase):
    """附件身份靠 `File.hbos_attachment_kind`，不靠文件名。

    文件名会被 Frappe 重名后缀改写；人工上传的文件也可能撞名。
    早先「只按 file_name + force=True 删除」会误删人工凭证。
    """

    def test_custom_field_registered(self):
        setup = (ROOT / "hb_inventory_app" / "hbos_inventory" / "setup.py").read_text(encoding="utf-8")
        self.assertIn('"File": [', setup)
        self.assertIn("hbos_attachment_kind", setup)

    def test_generated_pdf_carries_kind(self):
        gen = (ROOT / "hb_inventory_app" / "hbos_inventory" / "doc_gen.py").read_text(encoding="utf-8")
        self.assertIn('"hbos_attachment_kind": KIND_CARD', gen)

    def test_photo_carries_kind(self):
        api = (ROOT / "hb_inventory_app" / "hbos_inventory" / "api.py").read_text(encoding="utf-8")
        self.assertIn('"hbos_attachment_kind": "标签照片"', api)

    def test_purge_filters_by_kind_first(self):
        gen = (ROOT / "hb_inventory_app" / "hbos_inventory" / "doc_gen.py").read_text(encoding="utf-8")
        fn = gen[gen.index("def _purge_previous"): gen.index("def _card_format_for")]
        kind_at = fn.index('"hbos_attachment_kind": KIND_CARD')
        name_at = fn.index('"file_name": filename')
        self.assertLess(kind_at, name_at, "先按标记删；文件名只作老数据回退")


class BatchLoaderContractTest(unittest.TestCase):
    """`load_packaging_map` 必须用批量 in 查询，且字段名与表结构对齐。"""

    def setUp(self):
        self.src = (
            ROOT / "hb_inventory_app" / "hbos_inventory" / "print_utils.py"
        ).read_text(encoding="utf-8")

    def test_uses_single_in_query(self):
        self.assertIn('"parent": ["in", names]', self.src)
        self.assertIn('"parenttype": "Batch"', self.src)

    def test_selects_columns_that_exist(self):
        import re

        m = re.search(r"def load_packaging_map[\s\S]*?fields=\[([^\]]+)\]", self.src)
        self.assertIsNotNone(m, "找不到 load_packaging_map 的 fields")
        fields = set(re.findall(r'"([a-z_]+)"', m.group(1)))
        self.assertEqual(set(), fields - EXPECTED_COLUMNS, f"选了不存在的列：{fields - EXPECTED_COLUMNS}")

    def test_orders_by_idx(self):
        self.assertIn('order_by="parent asc, idx asc"', self.src)


if __name__ == "__main__":
    unittest.main()
