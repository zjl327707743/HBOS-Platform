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

# oracle 快照：本 App 内的测试数据，是 hb_attendance_app 的工作台产物的**逐字节副本**。
# 选它的理由：该产物已上线、已被证明能被 Frappe 正常导入，因此可以当作判据，而不是
# 用我们自己对「顶层该有哪些键」的假设。本次事故正是「测试与实现共享同一个盲点」——
# 合成源自造了一份缺少 doctype 的 payload，于是单测全绿而产物不可导入。
#
# 来源路径（上游，只读，不构成运行时依赖）：
#   apps/hb_attendance_app/hb_attendance_app/hbos_attendance/workspace/海滨考勤工作台/海滨考勤工作台.json
# 出处 commit：9ea07c426d8dd19cdb38192d2f91c1ce7b97ba07
#   （feat: 调休/换班记录接入定时同步与工作台入口）
# 上游 git blob：aab0209be3b70b368226fbb960266626a25eb79f
# 快照 sha256：0fd8f12342226eda56180387c424e8f1bf87c26d1a109c491d6eb5c356c63621
# 复制方式：cp -p（字节完全一致；未做任何「修正」「美化」——它的价值就在于原样）。
#
# 为什么快照进本 App 而不是每次直读上游：上游产物一旦重命名 / 移动 / 删除，直读方案
# 会**静默失效**（只剩 skipped，suite 仍 OK），而那正是本防线要防的失效模式。
ORACLE_SNAPSHOT_PATH = (
    Path(__file__).resolve().parent / "oracle" / "海滨考勤工作台.json"
)

# 上游原路径（仅供重建提示与人工追溯引用，测试逻辑不读它）。
ORACLE_SOURCE_PATH = (
    Path(__file__).resolve().parents[2]
    / "hb_attendance_app" / "hb_attendance_app" / "hbos_attendance"
    / "workspace" / "海滨考勤工作台" / "海滨考勤工作台.json"
)

FIXTURE_REBUILD_HINT = (
    "重建方式（在仓库根目录执行）：\n"
    "  docker exec hbos-m0-r3a-backend-1 bash -lc 'cd /home/frappe/frappe-bench && "
    "bench --site frontend execute frappe.client.get "
    "--kwargs \"{\\\"doctype\\\":\\\"Workspace\\\",\\\"name\\\":\\\"Stock\\\"}\" > /tmp/stock_ws.json'\n"
    "  docker cp hbos-m0-r3a-backend-1:/tmp/stock_ws.json /tmp/stock_ws.json\n"
    "  PYTHONPATH=apps/hb_stock_app python3 tools/gen_stock_workspace_fixture.py /tmp/stock_ws.json"
)

ORACLE_REBUILD_HINT = (
    f"重建方式：从上游产物重新快照一份（只读上游，勿修改它）：\n"
    f"  cp -p '{ORACLE_SOURCE_PATH}' apps/hb_stock_app/tests/oracle/海滨考勤工作台.json\n"
    f"  出处 commit：9ea07c426d8dd19cdb38192d2f91c1ce7b97ba07"
)

# Frappe 框架自己写入、不必由 fixture 携带的审计字段。
AUDIT_FIELDS = frozenset({
    "creation", "modified", "modified_by", "owner", "docstatus", "idx",
})

# 生成产物必须覆盖的全部子表。
CHILD_TABLES = ("links", "charts", "number_cards", "roles", "shortcuts",
                "custom_blocks", "quick_lists")


def synthetic_source():
    """最小化的 Stock 工作台 payload，字段名与结构照抄运行态实测结果。

    顶层键集合照抄 `frappe.client.get(Workspace, "Stock")` 的真实回包（33 键），
    包括 doctype 与 custom_blocks / quick_lists 等子表字段；不要凭实现反推，
    否则又会把实现的盲点镜像进合成源。
    """
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
        # Frappe 导入链路（import_file.py:123）直接取 doc["doctype"]，缺则
        # KeyError 并中断 install-app。实测回包里一定有这个键。
        "doctype": "Workspace",
        "for_user": "",
        "hide_custom": 0,
        # 以下 6 个键只出现在 frappe.client.get 的整表回包里，值为空，
        # 已上线的参考产物不含，本生成器刻意不继承。
        "external_link": None,
        "indicator_color": None,
        "link_to": None,
        "link_type": None,
        "parent_page": "",
        "restrict_to_domain": "",
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
        "custom_blocks": [{
            "name": "cb00000001", "owner": "Administrator", "docstatus": 0, "idx": 1,
            "custom_block_name": "custom_block_1", "label": "自定义区块",
            "parent": "Stock", "parentfield": "custom_blocks", "parenttype": "Workspace",
            "doctype": "Workspace Custom Block",
        }],
        "quick_lists": [{
            "name": "ql00000001", "owner": "Administrator", "docstatus": 0, "idx": 1,
            "document_type": "Item", "label": "物料", "quick_list_filter": "[]",
            "column_break_1": None, "section_break_4": None,
            "parent": "Stock", "parentfield": "quick_lists", "parenttype": "Workspace",
            "doctype": "Workspace Quick List",
        }],
    }


IDENTITY_FIELDS = ("name", "owner", "creation", "modified", "modified_by",
                   "docstatus", "idx", "parent", "parentfield", "parenttype", "doctype")


class PreconditionTest(unittest.TestCase):
    """无条件前置条件检查：必需测试数据缺失时**响亮失败**，不带任何 skip。

    背景：本套件里依赖文件的用例全都带 skip / skipTest。文件被重命名、搬走或删除时，
    suite 依旧输出 `OK`，只是 skipped 数变多；CI 若只看退出码，防线就等于不存在。
    这与本轮事故（「测试全绿、产物不可用」）是同一个失效模式，所以必须有一条
    **不带 skip 的**用例兜底：缺失即为 FAIL，并打印期望路径与如何重建。

    覆盖的路径（两条都是本 App 内的、已入库的必需测试数据，不是可选场景）：
    1. `FIXTURE_PATH`——待验证的落盘产物本身；
    2. `ORACLE_SNAPSHOT_PATH`——oracle 快照；它一旦消失，整条超集防线会静默失效。
    真正的可选场景（例如某字段不存在时的分支）仍保留 skip，不在此列。
    """

    def test_required_artifacts_exist_and_parse(self):
        required = (
            ("落盘 fixture", FIXTURE_PATH, FIXTURE_REBUILD_HINT),
            ("oracle 快照", ORACLE_SNAPSHOT_PATH, ORACLE_REBUILD_HINT),
        )
        missing = [
            f"  - {label} 缺失：{path}\n      {hint}"
            for label, path, hint in required if not path.is_file()
        ]
        self.assertEqual(
            missing, [],
            "以下必需测试数据缺失（这是 FAIL，不是 skip）：\n" + "\n".join(missing),
        )
        for label, path, _hint in required:
            with self.subTest(artifact=label):
                try:
                    data = json.loads(path.read_text())
                except Exception as exc:
                    self.fail(
                        f"{label} 存在但无法解析为 JSON：{path}\n"
                        f"      {type(exc).__name__}: {exc}"
                    )
                self.assertIsInstance(
                    data, dict, f"{label} 顶层不是 JSON 对象：{path}")


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

    def test_doctype_carried_over(self):
        """顶层 doctype 是 Frappe 导入链路的硬要求，缺则 install-app 直接崩。"""
        p = build_workspace_payload(synthetic_source())
        self.assertEqual(p["doctype"], "Workspace")

    def test_custom_blocks_and_quick_lists_drop_child_identity(self):
        p = build_workspace_payload(synthetic_source())
        self.assertEqual(p["custom_blocks"],
                         [{"custom_block_name": "custom_block_1", "label": "自定义区块"}])
        self.assertEqual(p["quick_lists"],
                         [{"document_type": "Item", "label": "物料",
                           "quick_list_filter": "[]"}])
        for table in ("custom_blocks", "quick_lists"):
            for row in p[table]:
                for field in IDENTITY_FIELDS:
                    self.assertNotIn(field, row)

    def test_empty_source_tolerated(self):
        p = build_workspace_payload({})
        for table in CHILD_TABLES:
            self.assertEqual(p[table], [])


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

    def test_fixture_covers_all_child_tables(self):
        for table in CHILD_TABLES:
            self.assertIn(table, self.payload)

    def test_no_child_row_carries_identity(self):
        for table in CHILD_TABLES:
            for row in self.payload[table]:
                for field in IDENTITY_FIELDS:
                    self.assertNotIn(field, row)


class OracleSupersetTest(unittest.TestCase):
    """用已上线的参考产物当 oracle，校验生成产物的顶层键集合。

    这道防线是本轮事故的直接产物：上一版 `_assert_no_drop_fields()` 只校验子表，
    顶层漏了 `doctype` 却全绿，直到 `bench install-app` 才 `KeyError: 'doctype'`。
    判据刻意取自外部证据——`hb_attendance_app` 的「海滨考勤工作台」产物同样位于
    `<module>/workspace/<name>/<name>.json`，已经走通 Frappe 同一条导入链路并上线，
    因此「它有的键我们也要有」比「我们自己觉得该有什么」可靠。

    只断言超集而非相等：我们允许比 oracle 多键（多出来的键由本生成器的白名单显式
    控制，另由其他用例覆盖），但绝不允许少键。

    读的是本 App 内的快照 `tests/oracle/海滨考勤工作台.json`（来源与出处 commit 见
    文件头注释）。这里**没有 skip**：oracle 快照是本 App 已入库的测试数据，缺失不是
    可选场景；若给它加 skip，整个防线会随文件消失而静默熄灭——正是要防的失效模式。
    缺失时由 `PreconditionTest` 给出带重建提示的 FAIL，本类则直接报错。
    """

    @classmethod
    def setUpClass(cls):
        cls.oracle = json.loads(ORACLE_SNAPSHOT_PATH.read_text())

    def _assert_superset(self, payload, label):
        expected = set(self.oracle) - AUDIT_FIELDS
        missing = sorted(expected - set(payload))
        self.assertEqual(
            missing, [],
            f"{label} 缺少已上线参考产物所需的顶层键 {missing}；"
            f"oracle 快照={ORACLE_SNAPSHOT_PATH}",
        )

    def test_builder_output_covers_oracle(self):
        self._assert_superset(build_workspace_payload(synthetic_source()), "生成器输出")

    def test_generated_fixture_covers_oracle(self):
        if not FIXTURE_PATH.exists():
            self.skipTest("fixture 尚未生成")
        self._assert_superset(json.loads(FIXTURE_PATH.read_text()), "落盘 fixture")

    def test_generated_fixture_is_importable_workspace_doc(self):
        if not FIXTURE_PATH.exists():
            self.skipTest("fixture 尚未生成")
        payload = json.loads(FIXTURE_PATH.read_text())
        # import_file.py:123 第一步就 doc["doctype"]，这是 install-app 的硬门槛。
        self.assertEqual(payload["doctype"], "Workspace")
        self.assertEqual(payload["name"], TARGET_WORKSPACE)


if __name__ == "__main__":
    unittest.main()
