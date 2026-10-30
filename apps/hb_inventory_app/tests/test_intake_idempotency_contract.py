"""入库幂等与包装保全 —— 不建 Site，用 frappe 替身跑纯逻辑。

## 这两条为什么必须钉住

1. **幂等键**：同一个 request_id 携**不同内容**时，不能返回上一张单
   （用户改了物料/批次/数量却拿到旧单据，会以为修改生效了）。
   并发两个请求同时 cache miss 时，也只能有一个真去建单。

2. **包装构成**：`None` = 本次不动，`[]` = 清空。前端曾经无条件发数组，
   于是「同批次补录时没填包装」把库里已有的包装清空了 —— 数据静默丢失。

本文件只测**纯函数与判定顺序**，真实的 Redis 原子性与 Frappe 事务不在范围内。
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _install_frappe_stub():
    frappe = sys.modules.get("frappe")
    if frappe is None:
        frappe = types.ModuleType("frappe")
        sys.modules["frappe"] = frappe
    frappe._hbos_stub = True

    frappe.ValidationError = getattr(
        frappe, "ValidationError", type("ValidationError", (Exception,), {})
    )
    frappe.PermissionError = getattr(frappe, "PermissionError", type("PermissionError", (Exception,), {}))

    def _throw(msg, exc=None, title=None):
        raise (exc or frappe.ValidationError)(str(msg))

    frappe.throw = _throw
    frappe._ = lambda s: s
    frappe.whitelist = lambda *a, **kw: (lambda fn: fn)
    frappe.parse_json = __import__("json").loads
    frappe.get_meta = lambda doctype: types.SimpleNamespace(
        get_field=lambda name: types.SimpleNamespace(options="件\n听\n瓶\n桶\n袋\n箱")
    )
    frappe.session = types.SimpleNamespace(user="tester@example.com")

    utils = sys.modules.get("frappe.utils")
    if utils is None:
        utils = types.ModuleType("frappe.utils")
        sys.modules["frappe.utils"] = utils
    utils.cint = lambda v: int(v or 0)
    utils.flt = lambda v: float(v or 0)
    frappe.utils = utils

    frappe.log_error = lambda *a, **kw: None
    frappe.cache = lambda: types.SimpleNamespace(
        get_value=lambda *a, **kw: None,
        set_value=lambda *a, **kw: None,
        delete=lambda *a, **kw: None,
        make_key=lambda k: k,
        set=lambda *a, **kw: True,
    )

    ocr_stub = types.ModuleType("hb_inventory_app.hbos_inventory.ocr_client")
    ocr_stub.OcrUnavailable = type("OcrUnavailable", (Exception,), {})
    sys.modules.setdefault("hb_inventory_app.hbos_inventory.ocr_client", ocr_stub)
    return frappe


def _load_api():
    _install_frappe_stub()
    for mod in list(sys.modules):
        if mod == "hb_inventory_app.hbos_inventory.api":
            del sys.modules[mod]
    from hb_inventory_app.hbos_inventory import api

    return api


class PayloadFingerprintTest(unittest.TestCase):
    def setUp(self):
        self.api = _load_api()

    def _fp(self, **overrides):
        args = dict(
            item_code="ITEM-A",
            batch_no="B001",
            warehouse="3904 - HB",
            qty=10.0,
            file_url="http://x/a.jpg",
            packaging='[{"container_type":"瓶","count":2}]',
            label_text="标签",
        )
        args.update(overrides)
        return self.api._intake_payload_fingerprint(**args)

    def test_same_input_same_fingerprint(self):
        self.assertEqual(self._fp(), self._fp())

    def test_changed_item_changes_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(item_code="ITEM-B"))

    def test_changed_batch_changes_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(batch_no="B002"))

    def test_changed_qty_changes_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(qty=11.0))

    def test_changed_warehouse_changes_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(warehouse="3905 - HB"))

    def test_changed_photo_changes_fingerprint(self):
        """换照片 = 换一张标签，是另一次操作。"""
        self.assertNotEqual(self._fp(), self._fp(file_url="http://x/b.jpg"))

    def test_changed_packaging_changes_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(packaging=None))

    def test_changed_source_type_changes_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(source_type="外购"))

    def test_changed_dates_change_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(manufacturing_date="2026-10-01"))
        self.assertNotEqual(self._fp(), self._fp(expiry_date="2028-10-01"))

    def test_changed_supplier_fields_change_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(supplier_name="甲供应商"))
        self.assertNotEqual(self._fp(), self._fp(manufacturer="甲厂"))
        self.assertNotEqual(self._fp(), self._fp(supplier_batch_no="S-001"))

    def test_changed_master_fields_change_fingerprint(self):
        self.assertNotEqual(self._fp(), self._fp(storage_condition="2-8℃"))
        self.assertNotEqual(self._fp(), self._fp(workshop="六车间"))
        self.assertNotEqual(self._fp(), self._fp(shelf_life_type="复检期"))

    def test_frontend_fingerprint_covers_same_fields(self):
        """前后端指纹字段必须同步 —— 少一边就会出现「前端认为是新操作、
        后端认为是重放」或反过来的错配。"""
        src = (
            ROOT.parents[1] / "frontend" / "hbos-portal-web" / "src" / "services" / "intake.ts"
        ).read_text(encoding="utf-8")
        block = src[src.index("const FINGERPRINT_FIELDS"):src.index("function operationFingerprint")]
        for field in (
            "source_type", "manufacturing_date", "expiry_date", "storage_condition",
            "workshop", "shelf_life_type", "supplier_name", "manufacturer", "supplier_batch_no",
        ):
            self.assertIn(f"'{field}'", block, f"前端指纹漏了 {field}")


class CacheWriteFailureDoesNotFailRequestTest(unittest.TestCase):
    """草稿建好之后，幂等缓存写失败**不能让请求失败**。

    否则用户看到「生成失败」并重试 —— 而缓存里没有记录、锁也已释放，
    重试会再建一张单。这正是幂等机制本来要防的事。
    """

    def test_cache_set_exception_is_swallowed(self):
        src = (
            ROOT / "hb_inventory_app" / "hbos_inventory" / "api.py"
        ).read_text(encoding="utf-8")
        start = src.index("cache.set_value(")
        block = src[start: src.index("return result", start)]
        self.assertIn("except Exception", block, "缓存写入没有异常兜底")
        self.assertIn("finally", block, "锁必须在 finally 里释放")

    def test_lock_release_is_separately_guarded(self):
        src = (
            ROOT / "hb_inventory_app" / "hbos_inventory" / "api.py"
        ).read_text(encoding="utf-8")
        # 取**最后一处** delete（成功路径里的那个）；前面的在失败清理分支
        idx = src.rindex("cache.delete(cache.make_key")
        self.assertIn("except Exception", src[idx: idx + 200], "删锁失败也要兜住")


class ParsePackagingNullSemanticsTest(unittest.TestCase):
    """`None` 表示「本次不动」，必须与 `[]`（清空）区分开。"""

    def setUp(self):
        self.parse = _load_api()._parse_packaging

    def test_none_is_not_empty_list(self):
        self.assertIsNone(self.parse(None))
        self.assertEqual([], self.parse([]))

    def test_count_only_row_survives(self):
        rows = self.parse([{"container_type": "瓶", "count": 10}])
        self.assertEqual(1, len(rows))
        self.assertEqual(0, rows[0]["unit_weight"])


class FrontendPackagingPayloadContractTest(unittest.TestCase):
    """前端必须用 `null` 表示「没填包装」，不能发 `[]`。"""

    def _intake_view(self) -> str:
        return (
            ROOT.parents[1] / "frontend" / "hbos-portal-web" / "src" / "views" / "InventoryIntakeView.vue"
        ).read_text(encoding="utf-8")

    def test_uses_null_when_no_rows(self):
        src = self._intake_view()
        self.assertIn("packagingPayload()", src)
        self.assertIn("if (!filled.length) return null", src)

    def test_does_not_send_empty_array(self):
        src = self._intake_view()
        self.assertNotIn(".filter((r) => r.container_type)", src)

    def test_partial_row_is_reported_not_dropped(self):
        src = self._intake_view()
        self.assertIn("不完整", src)

    def test_service_passes_null_through(self):
        svc = (
            ROOT.parents[1] / "frontend" / "hbos-portal-web" / "src" / "services" / "intake.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("input.packaging === null ? null", svc)


class DeskPhotoIntakeContractTest(unittest.TestCase):
    """Desk 侧拍照页也要有幂等键与 `null` 包装语义 —— 两条路径行为必须一致。"""

    def _js(self) -> str:
        return (
            ROOT.parents[1]
            / "apps" / "hb_inventory_app" / "hb_inventory_app" / "hbos_inventory"
            / "page" / "hbos_photo_intake" / "hbos_photo_intake.js"
        ).read_text(encoding="utf-8")

    def test_desk_passes_request_id(self):
        self.assertIn("args.request_id = requestIdFor(args)", self._js())

    def test_desk_uses_null_for_empty_packaging(self):
        src = self._js()
        self.assertIn("packagingArg = pkgRows && pkgRows.length ? JSON.stringify(pkgRows) : null", src)
        # 不能再出现「无条件 JSON.stringify(… : collectPackaging())」那种写法
        self.assertNotIn("JSON.stringify(\n\t\t\t\t\tstate.packagingRows && state.packagingRows.length", src)

    def test_desk_rotates_nonce_on_new_photo(self):
        self.assertIn("state.opNonce = newId();", self._js())

    def test_desk_fingerprint_covers_same_fields_as_portal_and_backend(self):
        """三处（Desk / Portal / 后端）指纹字段必须完全一致。

        早先 Desk 只取 7 个字段，缺来源类型/日期/供应商等 9 个 —— 用户改了
        这些再重试时，Desk 的 request_id 不变、后端指纹却变了，被判
        「请求内容已变化」直接拒绝，Desk 路径的幂等实际失效。
        """
        fields = {
            "item_code", "batch_no", "warehouse", "file_url", "source_type",
            "manufacturing_date", "expiry_date", "storage_condition", "workshop",
            "shelf_life_type", "supplier_name", "manufacturer", "supplier_batch_no",
            "label_text",
        }

        desk = self._js()
        block = desk[desk.index("const FINGERPRINT_FIELDS"):desk.index("function requestIdFor")]
        for f in fields:
            self.assertIn(f'"{f}"', block, f"Desk 指纹漏了 {f}")

        portal = (
            ROOT.parents[1] / "frontend" / "hbos-portal-web" / "src" / "services" / "intake.ts"
        ).read_text(encoding="utf-8")
        pblock = portal[portal.index("const FINGERPRINT_FIELDS"):portal.index("function operationFingerprint")]
        for f in fields:
            self.assertIn(f"'{f}'", pblock, f"Portal 指纹漏了 {f}")

        api = (ROOT / "hb_inventory_app" / "hbos_inventory" / "api.py").read_text(encoding="utf-8")
        fn = api[api.index("def _intake_payload_fingerprint"):api.index("def _require_item_ready")]
        for f in fields:
            self.assertIn(f"{f}", fn, f"后端指纹漏了 {f}")


if __name__ == "__main__":
    unittest.main()
