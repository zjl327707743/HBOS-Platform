# -*- coding: utf-8 -*-
"""M2-R5 全量 DocType 契约测试：13 个 DocType 通用约定 + 入口收敛断言（源码即文档）。"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
HBOS_LIMS = APP_ROOT / "hb_lims_app" / "hbos_lims"
DOCTYPES = HBOS_LIMS / "doctype"

EXPECTED_DOCTYPES = {
    "hbos_sample_type": "HBOS Sample Type",
    "hbos_lab_department": "HBOS Lab Department",
    "hbos_test_item": "HBOS Test Item",
    "hbos_calculation": "HBOS Calculation",
    "hbos_specification": "HBOS Specification",
    "hbos_specification_item": "HBOS Specification Item",
    "hbos_sample": "HBOS Sample",
    "hbos_sample_item": "HBOS Sample Item",
    "hbos_sample_task": "HBOS Sample Task",
    "hbos_test_result": "HBOS Test Result",
    "hbos_result_revision": "HBOS Result Revision",
    "hbos_coa": "HBOS COA",
    "hbos_coa_item": "HBOS COA Item",
}

CHILD_DOCTYPES = {"hbos_specification_item", "hbos_sample_item", "hbos_coa_item"}


class TestAllDoctypeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doctypes = {}
        for dirname, expected in EXPECTED_DOCTYPES.items():
            path = DOCTYPES / dirname / f"{dirname}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["name"] == expected, dirname
            cls.doctypes[dirname] = payload

    def test_all_13_doctypes_present(self):
        self.assertEqual(len(self.doctypes), 13)

    def test_module_and_track_changes(self):
        for dirname, payload in self.doctypes.items():
            self.assertEqual(payload["module"], "HBOS LIMS", dirname)
            self.assertEqual(payload["track_changes"], 1, dirname)
            self.assertEqual(payload["allow_rename"], 0, dirname)

    def test_tri_role_permissions_everywhere(self):
        for dirname, payload in self.doctypes.items():
            roles = {p["role"] for p in payload["permissions"]}
            self.assertIn("System Manager", roles, dirname)
            self.assertIn("LIMS Manager", roles, dirname)
            self.assertIn("LIMS Analyst", roles, dirname)
            self.assertIn("LIMS Reviewer", roles, dirname)

    def test_child_tables_have_istable(self):
        for dirname in CHILD_DOCTYPES:
            self.assertEqual(self.doctypes[dirname]["istable"], 1, dirname)
            self.assertEqual(self.doctypes[dirname]["autoname"], "hash", dirname)

    def test_transactional_naming_series(self):
        expected = {
            "hbos_sample": "HBOS-SMP-.YYYY.-",
            "hbos_sample_task": "HBOS-TSK-.YYYY.-",
            "hbos_test_result": "HBOS-TR-.YYYY.-",
            "hbos_result_revision": "HBOS-REV-.YYYY.-",
            "hbos_coa": "HBOS-COA-.YYYY.-",
        }
        for dirname, series in expected.items():
            fields = {f["fieldname"]: f for f in self.doctypes[dirname]["fields"]}
            self.assertEqual(fields["naming_series"]["options"], series, dirname)

    def test_sample_default_report_view(self):
        """样品登记（HBOS Sample）默认视图必须为 Report（用户需求：新建样品登记默认为报表视图）；
        其他 LIMS DocType 不设 default_view，保持原生默认列表视图。"""
        for dirname, payload in self.doctypes.items():
            if dirname == "hbos_sample":
                self.assertEqual(
                    payload.get("default_view"),
                    "Report",
                    "HBOS Sample 应默认报表视图",
                )
            else:
                self.assertIsNone(
                    payload.get("default_view"),
                    f"{dirname} 不应设置 default_view，保持默认列表视图",
                )

    def test_all_fields_have_chinese_labels(self):
        """所有字段 label 必须为中文（无 label 的 section/列字段除外，含 naming_series）。"""
        no_label_fieldtypes = {"Section Break", "Column Break", "Tab Break"}
        for dirname, payload in self.doctypes.items():
            for f in payload["fields"]:
                if f["fieldtype"] in no_label_fieldtypes:
                    continue
                label = f.get("label") or ""
                self.assertTrue(label, f"{dirname}.{f['fieldname']} 缺少中文 label")
                self.assertRegex(label, r"[一-鿿]", f"{dirname}.{f['fieldname']} label 非中文: {label}")

    def test_translations_cover_doctypes(self):
        """简体中文翻译文件必须覆盖全部 13 个 DocType 名与模块名（控制面板简体中文）。"""
        csv_path = APP_ROOT / "hb_lims_app" / "translations" / "zh.csv"
        self.assertTrue(csv_path.exists())
        lines = [l for l in csv_path.read_text(encoding="utf-8").strip().splitlines() if l]
        self.assertEqual(lines[0], "source,target")
        pairs = dict(l.split(",") for l in lines[1:])
        for doctype in EXPECTED_DOCTYPES.values():
            self.assertIn(doctype, pairs, f"{doctype} 缺少中文翻译")
            self.assertRegex(pairs[doctype], r"[一-鿿]", f"{doctype} 翻译非中文")
        self.assertEqual(pairs["HBOS LIMS"], "海滨LIMS")


class TestReportDirNamingContract(unittest.TestCase):
    """报表目录名必须等于 frappe.scrub(report_name)（ASCII 小写、空格转下划线），否则浏览器路径解析失败。"""

    def test_report_dirs_match_scrub(self):
        report_dir = HBOS_LIMS / "report"
        report_names = ("待检任务看板", "检验结果清单", "样品台账", "审计追踪查询", "COA 发布记录")
        for name in report_names:
            expected_dir = name.lower().replace(" ", "_")
            self.assertTrue((report_dir / expected_dir).exists(), f"{name} -> {expected_dir}")
            self.assertTrue((report_dir / expected_dir / f"{expected_dir}.json").exists(), name)
            self.assertTrue((report_dir / expected_dir / f"{expected_dir}.py").exists(), name)
            self.assertTrue((report_dir / expected_dir / f"{expected_dir}.js").exists(), name)


class TestEntryPointsContract(unittest.TestCase):
    def test_workspace_links_cover_all_routes(self):
        payload = json.loads((HBOS_LIMS / "workspace" / "海滨LIMS工作台" / "海滨LIMS工作台.json").read_text(encoding="utf-8"))
        links = [l for l in payload["links"] if l.get("link_to")]
        targets = {l["link_to"] for l in links}
        # 4 个卡片分区 + 13 个业务链接（3 录入 + 3 查询 + 2 报告 + 5 主数据）
        self.assertEqual(len(links), 13)
        for doctype in ("HBOS Sample", "HBOS Test Result", "HBOS COA",
                        "HBOS Specification", "HBOS Test Item", "HBOS Calculation",
                        "HBOS Sample Type", "HBOS Lab Department"):
            self.assertIn(doctype, targets)
        for report in ("待检任务看板", "样品台账", "检验结果清单", "审计追踪查询", "COA 发布记录"):
            self.assertIn(report, targets)
        # 报表链接必须标记 is_query_report
        for l in payload["links"]:
            if l.get("link_type") == "Report":
                self.assertEqual(l["is_query_report"], 1, l["label"])
            if l.get("label") == "COA 发布记录":
                # 链接指向报表名，报表模块目录为 scrub 形式
                self.assertTrue((HBOS_LIMS / "report" / "coa_发布记录" / "coa_发布记录.json").exists())

    def test_workspace_shortcuts(self):
        payload = json.loads((HBOS_LIMS / "workspace" / "海滨LIMS工作台" / "海滨LIMS工作台.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(payload["shortcuts"]), 5)
        shortcut_labels = {s["label"] for s in payload["shortcuts"]}
        self.assertIn("新建样品登记", shortcut_labels)
        self.assertIn("待检任务看板", shortcut_labels)
        self.assertIn("质量标准", shortcut_labels)

    def test_sidebar_grouped_by_module(self):
        """侧边导航按业务模块分组（Section Break 分组 + collapsible 下拉 + child 子项缩进）。"""
        setup = (HBOS_LIMS / "setup.py").read_text(encoding="utf-8")
        # 5 个模块分组，均为可下拉的 Section Break
        for section in ("样品管理", "检验流程", "报告管理", "质量主数据", "审计追踪"):
            self.assertIn(f'{{"label": "{section}", "type": "Section Break", "collapsible": 1, "keep_closed":', setup)
        # 关键子项均标记 child=1（归入分组下拉）
        for link in (
            '{"label": "新建样品登记", "link_type": "DocType", "link_to": "HBOS Sample", "type": "Link", "icon": "box", "child": 1}',
            '"link_to": "待检任务看板", "type": "Link", "icon": "kanban", "child": 1}',
            '"link_to": "COA 发布记录", "type": "Link", "icon": "paper-plane", "child": 1}',
            '"link_to": "HBOS Specification", "type": "Link", "icon": "book", "child": 1}',
            '"link_to": "审计追踪查询", "type": "Link", "icon": "search", "child": 1}',
        ):
            self.assertIn(link, setup)
        # 分组顺序：每个 Section Break 后跟其模块子项（样例抽查）
        sample_section = setup.index('"label": "样品管理", "type": "Section Break"')
        flow_section = setup.index('"label": "检验流程", "type": "Section Break"')
        report_section = setup.index('"label": "报告管理", "type": "Section Break"')
        self.assertTrue(
            sample_section < setup.index('"link_to": "HBOS Sample", "type": "Link", "icon": "box", "child": 1}')
            < flow_section < setup.index('"link_to": "待检任务看板"')
            < report_section
        )

    def test_desktop_icon_and_logo(self):
        setup = (HBOS_LIMS / "setup.py").read_text(encoding="utf-8")
        self.assertIn('DESKTOP_LABEL = "海滨LIMS"', setup)
        self.assertIn("restrict_removal = 1", setup)
        logo = APP_ROOT / "hb_lims_app" / "public" / "hbos-lims-logo.svg"
        self.assertTrue(logo.exists())

    def test_report_column_resize_assets(self):
        """报表表格列宽拖拽增强：hooks 注入 CSS/JS，CSS 必须含 hover 显示拖拽手柄规则。"""
        hooks = (APP_ROOT / "hb_lims_app" / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('app_include_css = "/assets/hb_lims_app/css/lims_report.css', hooks)
        self.assertIn('"/assets/hb_lims_app/js/lims_report.js', hooks)
        css = (APP_ROOT / "hb_lims_app" / "public" / "css" / "lims_report.css").read_text(encoding="utf-8")
        self.assertIn(".dt-cell__resize-handle", css)
        self.assertIn("opacity: 1 !important", css)
        js = APP_ROOT / "hb_lims_app" / "public" / "js" / "lims_report.js"
        self.assertTrue(js.exists())
        self.assertIn("dt-cell__content", js.read_text(encoding="utf-8"))

    def test_table_text_centered_assets(self):
        """表格字段文字居中增强（用户需求：所有表格字段文字剧中）：
        CSS 对 HBOS LIMS 标记容器（.hbos-lims-list / .hbos-lims-grid / .hbos-lims-report）
        内的表格单元格 text-align:center；JS 注入标记类，非 LIMS 页面不受影响。
        表头居中补充：列表视图表头 flex justify-content:center + 第一列 checkbox 绝对定位
        （消除全选框占位偏右）；datatable 表头 padding-left 补偿（消除左右不对称偏左 5px）。"""
        css = (APP_ROOT / "hb_lims_app" / "public" / "css" / "lims_report.css").read_text(encoding="utf-8")
        self.assertIn("text-align: center", css)
        self.assertIn(".hbos-lims-list .datatable .dt-cell__content", css)
        self.assertIn(".hbos-lims-list .list-row-col", css)
        self.assertIn(".hbos-lims-grid .grid-static-col", css)
        self.assertIn("#page-query-report.hbos-lims-report .datatable .dt-cell__content", css)
        # 表头居中补充：列表视图 flex 表头 + 第一列 checkbox 绝对定位
        self.assertIn(".hbos-lims-list .list-row-head .list-row-col {", css)
        self.assertIn("justify-content: center", css)
        self.assertIn(".list-subject.level .select-like", css)
        self.assertIn("position: absolute", css)
        self.assertIn(".list-subject.level [data-sort-by]", css)
        # datatable 表头 padding 对称补偿
        self.assertIn(".dt-row-header .dt-cell__content", css)
        self.assertIn("padding-left: 16px", css)
        # 列表视图行列高度修复（结果修订记录异常：字段名 result 命中 Frappe 原生
        # .frappe-list .result { min-height:200px } 被撑高，行高异常 + 列错位）
        self.assertIn(".hbos-lims-list .list-row .list-row-col {", css)
        self.assertIn("min-height: auto", css)
        self.assertIn("height: auto", css)
        # JS 注入标记类
        list_js = (APP_ROOT / "hb_lims_app" / "public" / "js" / "lims_list_resize.js").read_text(encoding="utf-8")
        self.assertIn('addClass("hbos-lims-list")', list_js)
        grid_js = (APP_ROOT / "hb_lims_app" / "public" / "js" / "lims_grid_resize.js").read_text(encoding="utf-8")
        self.assertIn('addClass("hbos-lims-grid")', grid_js)
        report_js = (APP_ROOT / "hb_lims_app" / "public" / "js" / "lims_report.js").read_text(encoding="utf-8")
        self.assertIn("hbos-lims-report", report_js)
        self.assertIn("MutationObserver", report_js)

    def test_list_column_resize_assets(self):
        """列表视图列宽拖拽增强（用户反馈：DocType 列表页无法拖宽列）：
        lims_list_resize.js monkey-patch apply_column_widths 恢复持久化宽度并注入
        表头拖拽手柄，限定 HBOS LIMS 模块；CSS 含列表页手柄 hover 显示规则。"""
        hooks = (APP_ROOT / "hb_lims_app" / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"/assets/hb_lims_app/js/lims_list_resize.js', hooks)
        js = APP_ROOT / "hb_lims_app" / "public" / "js" / "lims_list_resize.js"
        code = js.read_text(encoding="utf-8")
        self.assertIn("apply_column_widths", code)
        self.assertIn("list-col-resize-handle", code)
        self.assertIn("hbos_lims_list_column_widths", code)
        self.assertIn("localStorage", code)
        self.assertIn('"HBOS LIMS"', code)
        self.assertIn("dblclick", code)
        css = (APP_ROOT / "hb_lims_app" / "public" / "css" / "lims_report.css").read_text(encoding="utf-8")
        self.assertIn(".list-view .list-row-head .list-row-col .list-col-resize-handle", css)
        self.assertIn("opacity: 1 !important", css)
        # 表头/数据对齐修复：数据行 Subject 列（.list-subject.level）必须与表头同规则
        # （checkbox 绝对定位最左 + 文字居中），否则表头标题居中、数据行靠左造成错位
        self.assertIn(".hbos-lims-list .list-row .list-subject.level .select-like", css)
        self.assertIn("position: absolute", css)

    def test_grid_column_resize_assets(self):
        """表单子表网格列宽拖拽增强（用户反馈：新建样品登记等表单页子表无法拖宽列）：
        lims_grid_resize.js monkey-patch ControlTable.prototype.make + MutationObserver 兜底，
        wrap grid 实例 refresh 恢复持久化列宽并注入表头拖拽手柄，限定 HBOS LIMS 模块；
        CSS 含子表手柄 hover 显示规则。"""
        hooks = (APP_ROOT / "hb_lims_app" / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('"/assets/hb_lims_app/js/lims_grid_resize.js', hooks)
        js = APP_ROOT / "hb_lims_app" / "public" / "js" / "lims_grid_resize.js"
        code = js.read_text(encoding="utf-8")
        self.assertIn("ControlTable.prototype.make", code)
        self.assertIn("grid-col-resize-handle", code)
        self.assertIn("hbos_lims_grid_column_widths", code)
        self.assertIn("localStorage", code)
        self.assertIn('"HBOS LIMS"', code)
        self.assertIn("dblclick", code)
        self.assertIn("MutationObserver", code)
        self.assertIn(".grid-static-col[data-fieldname]", code)
        css = (APP_ROOT / "hb_lims_app" / "public" / "css" / "lims_report.css").read_text(encoding="utf-8")
        self.assertIn(".form-grid .grid-heading-row .grid-static-col .grid-col-resize-handle", css)
        self.assertIn("opacity: 1 !important", css)

    def test_boot_session_sidebar_cache_workaround(self):
        """Frappe v16.26.3 核心 bug workaround：get_can_read_items 缺 return 导致
        非管理员侧边栏 DocType 项全被过滤；hb_lims_app 在 boot_session 预置
        user_perm_can_read 缓存恢复原生权限语义（不改 Frappe 核心源码）。"""
        hooks = (APP_ROOT / "hb_lims_app" / "hooks.py").read_text(encoding="utf-8")
        self.assertIn(
            'boot_session = "hb_lims_app.hbos_lims.setup.sync_user_perm_can_read_cache"', hooks
        )
        setup = (HBOS_LIMS / "setup.py").read_text(encoding="utf-8")
        self.assertIn("def sync_user_perm_can_read_cache(bootinfo=None):", setup)
        self.assertIn('frappe.cache.set_value("user_perm_can_read"', setup)
        self.assertIn("21600", setup)


if __name__ == "__main__":
    unittest.main()
