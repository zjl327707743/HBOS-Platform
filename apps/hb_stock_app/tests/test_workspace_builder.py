import copy
import json
import unittest
from pathlib import Path

from hb_stock_app.hbos_stock.workspace_builder import (
    TARGET_APP,
    TARGET_MODULE,
    TARGET_WORKSPACE,
    build_workspace_payload,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "hb_stock_app" / "hbos_stock" / "workspace" / TARGET_WORKSPACE
    / f"{TARGET_WORKSPACE}.json"
)


def synthetic_source():
    """最小化的 Stock 工作台 payload，字段名与结构照抄运行态实测结果。"""
    return {
        "name": "Stock",
        "label": "Stock",
        "title": "Stock",
        "module": "Stock",
        "app": "erpnext",
        "icon": "stock",
        "is_hidden": 0,
        "public": 1,
        "sequence_id": 7.0,
        "type": "Workspace",
        "content": json.dumps([
            {"id": "abc123", "type": "header", "data": {"text": "<b>Masters</b>", "col": 12}},
            {"id": "def456", "type": "card", "data": {"card_name": "Items Catalogue", "col": 4}},
        ]),
        "links": [
            {
                "name": "si4ekhi8tq", "owner": "Administrator",
                "creation": "2020-03-02 15:43:10.096528",
                "modified": "2026-07-21 12:26:58.048794", "modified_by": "Administrator",
                "docstatus": 0, "idx": 1, "type": "Link", "label": "Item", "icon": None,
                "description": None, "hidden": 0, "link_type": "DocType", "link_to": "Item",
                "report_ref_doctype": None, "dependencies": "", "only_for": None,
                "onboard": 1, "is_query_report": 0, "link_count": 0,
                "parent": "Stock", "parentfield": "links", "parenttype": "Workspace",
                "doctype": "Workspace Link",
            },
            {
                "name": "si4po43tnv", "owner": "Administrator",
                "creation": "2020-03-02 15:43:10.096528",
                "modified": "2026-07-21 12:26:58.048794", "modified_by": "Administrator",
                "docstatus": 0, "idx": 11, "type": "Card Break",
                "label": "Stock Transactions", "icon": None, "description": None,
                "hidden": 0, "link_type": None, "link_to": None, "report_ref_doctype": None,
                "dependencies": None, "only_for": None, "onboard": 0,
                "is_query_report": 0, "link_count": 0,
                "parent": "Stock", "parentfield": "links", "parenttype": "Workspace",
                "doctype": "Workspace Link",
            },
        ],
        "charts": [{
            "name": "si43jqfj07", "owner": "Administrator", "docstatus": 0, "idx": 1,
            "chart_name": "Stock Value by Item Group", "label": "Stock Value by Item Group",
            "parent": "Stock", "parentfield": "charts", "parenttype": "Workspace",
            "doctype": "Workspace Chart",
        }],
        "number_cards": [{
            "name": "si48oamd8m", "owner": "Administrator", "docstatus": 0, "idx": 1,
            "number_card_name": "Total Warehouses", "label": "Total Warehouses",
            "parent": "Stock", "parentfield": "number_cards", "parenttype": "Workspace",
            "doctype": "Workspace Number Card",
        }],
        "roles": [],
        "shortcuts": [],
        "custom_blocks": [],
        "quick_lists": [],
    }


IDENTITY_FIELDS = ("name", "owner", "creation", "modified", "modified_by",
                   "docstatus", "idx", "parent", "parentfield", "parenttype", "doctype")


class BuildPayloadTest(unittest.TestCase):
    def test_target_identity(self):
        p = build_workspace_payload(synthetic_source())
        self.assertEqual(p["name"], "海滨库存")
        self.assertEqual(p["label"], "海滨库存")
        self.assertEqual(p["title"], "海滨库存")
        self.assertEqual(p["module"], "HBOS Stock")
        self.assertEqual(p["app"], "hb_stock_app")

    def test_top_level_fields_carried_over(self):
        p = build_workspace_payload(synthetic_source())
        self.assertEqual(p["icon"], "stock")
        self.assertEqual(p["type"], "Workspace")
        self.assertEqual(p["public"], 1)
        self.assertEqual(p["sequence_id"], 7.0)

    def test_link_rows_drop_child_identity(self):
        p = build_workspace_payload(synthetic_source())
        self.assertEqual(len(p["links"]), 2)
        for row in p["links"]:
            for field in IDENTITY_FIELDS:
                self.assertNotIn(field, row,
                                 f"子表行不应带 {field}，否则会复用原生 Stock 的子文档名")

    def test_charts_and_number_cards_drop_child_identity(self):
        p = build_workspace_payload(synthetic_source())
        self.assertEqual(p["charts"], [{"chart_name": "Stock Value by Item Group",
                                        "label": "Stock Value by Item Group"}])
        self.assertEqual(p["number_cards"], [{"number_card_name": "Total Warehouses",
                                              "label": "Total Warehouses"}])

    def test_link_semantics_preserved(self):
        p = build_workspace_payload(synthetic_source())
        link, card_break = p["links"]
        self.assertEqual(link["type"], "Link")
        self.assertEqual(link["label"], "Item")
        self.assertEqual(link["link_type"], "DocType")
        self.assertEqual(link["link_to"], "Item")
        self.assertEqual(link["onboard"], 1)
        self.assertEqual(card_break["type"], "Card Break")
        self.assertEqual(card_break["label"], "Stock Transactions")

    def test_source_not_mutated(self):
        source = synthetic_source()
        before = copy.deepcopy(source)
        build_workspace_payload(source)
        self.assertEqual(source, before, "build_workspace_payload 不得修改入参")

    def test_content_prepends_title_header_once(self):
        p = build_workspace_payload(synthetic_source())
        blocks = json.loads(p["content"])
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0]["id"], "hbos-stock-title")
        self.assertEqual(blocks[0]["type"], "header")
        self.assertIn("海滨库存", blocks[0]["data"]["text"])
        # 原有块逐字保留
        self.assertEqual(blocks[1]["id"], "abc123")
        self.assertEqual(blocks[2]["id"], "def456")

    def test_empty_source_tolerated(self):
        p = build_workspace_payload({})
        self.assertEqual(p["links"], [])
        self.assertEqual(p["charts"], [])
        self.assertEqual(p["number_cards"], [])
        self.assertEqual(p["roles"], [])
        self.assertEqual(p["shortcuts"], [])


@unittest.skipUnless(FIXTURE_PATH.exists(), "fixture 尚未生成")
class GeneratedFixtureTest(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(FIXTURE_PATH.read_text())

    def test_real_stock_scale(self):
        self.assertEqual(len(self.payload["links"]), 72)
        self.assertEqual(len(self.payload["charts"]), 1)
        self.assertEqual(len(self.payload["number_cards"]), 3)

    def test_real_card_break_count(self):
        breaks = [r for r in self.payload["links"] if r["type"] == "Card Break"]
        self.assertEqual(len(breaks), 8)

    def test_no_child_row_carries_identity(self):
        for table in ("links", "charts", "number_cards"):
            for row in self.payload[table]:
                for field in IDENTITY_FIELDS:
                    self.assertNotIn(field, row)


if __name__ == "__main__":
    unittest.main()
