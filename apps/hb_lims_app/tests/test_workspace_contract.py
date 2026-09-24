# -*- coding: utf-8 -*-
"""M2-R1 骨架契约测试：断言 hb_lims_app 入口收敛与骨架约定（源码即文档）。"""

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
SETUP = APP_ROOT / "hb_lims_app" / "hbos_lims" / "setup.py"
HOOKS = APP_ROOT / "hb_lims_app" / "hooks.py"
DESKTOP = APP_ROOT / "hb_lims_app" / "config" / "desktop.py"
WORKSPACE = APP_ROOT / "hb_lims_app" / "hbos_lims" / "workspace" / "海滨LIMS工作台" / "海滨LIMS工作台.json"


class TestSkeletonContracts(unittest.TestCase):
    def test_setup_constants(self):
        source = SETUP.read_text(encoding="utf-8")
        self.assertIn('MODULE = "HBOS LIMS"', source)
        self.assertIn('WORKSPACE_TITLE = "海滨LIMS工作台"', source)
        self.assertIn('DESKTOP_LABEL = "海滨LIMS"', source)
        self.assertIn('DESKTOP_LOGO_URL = "/assets/hb_lims_app/hbos-lims-logo.svg"', source)
        for role in ("LIMS Manager", "LIMS Analyst", "LIMS Reviewer"):
            self.assertIn(role, source)

    def test_setup_idempotent_sync_functions_exist(self):
        source = SETUP.read_text(encoding="utf-8")
        for fn in ("after_migrate", "_sync_role", "sync_lims_workspace",
                   "_sync_sidebar", "_sync_desktop_icon", "_hide_stale_workspace_desktop_icon"):
            self.assertIn(f"def {fn}", source, f"缺少函数 {fn}")

    def test_setup_role_creation_idempotent(self):
        source = SETUP.read_text(encoding="utf-8")
        self.assertIn('if frappe.db.exists("Role", role_name):', source)
        self.assertIn("role.desk_access = 1", source)

    def test_hooks_registration(self):
        source = HOOKS.read_text(encoding="utf-8")
        self.assertIn('app_name = "hb_lims_app"', source)
        self.assertIn('app_title = "HBOS LIMS"', source)
        self.assertIn('required_apps = ["frappe", "erpnext"]', source)
        self.assertIn('after_migrate = "hb_lims_app.hbos_lims.setup.after_migrate"', source)
        self.assertIn("hbos-lims-logo.svg", source)
        self.assertIn('app_include_css = "/assets/hb_lims_app/css/lims_report.css', source)

    def test_report_scroll_css_exists(self):
        css = APP_ROOT / "hb_lims_app" / "public" / "css" / "lims_report.css"
        self.assertTrue(css.exists())
        content = css.read_text(encoding="utf-8")
        # 页面容器无 page-query-report 类，必须用 id 选择器（#page-query-report）
        self.assertIn("#page-query-report", content)
        self.assertIn(".dt-scrollable", content)
        self.assertIn("overflow-y: auto !important", content)
        self.assertIn("::-webkit-scrollbar", content)

    def test_desktop_module(self):
        source = DESKTOP.read_text(encoding="utf-8")
        self.assertIn('"module_name": "HBOS LIMS"', source)
        self.assertIn('_("海滨LIMS")', source)

    def test_workspace_fixture_structure(self):
        payload = json.loads(WORKSPACE.read_text(encoding="utf-8"))
        self.assertEqual(payload["doctype"], "Workspace")
        self.assertEqual(payload["name"], "海滨LIMS工作台")
        self.assertEqual(payload["module"], "HBOS LIMS")
        self.assertEqual(payload["app"], "hb_lims_app")
        self.assertEqual(payload["public"], 1)
        # 公开仓库：工作台介绍不得引用私有开发方案或外部开源项目
        self.assertNotIn("开发方案", payload["content"])
        self.assertNotIn("SENAITE", payload["content"])
        # 四个卡片分区：数据录入与任务 / 业务查询 / 报告管理 / 主数据维护
        content = json.loads(payload["content"])
        cards = [b["data"]["card_name"] for b in content if b["type"] == "card"]
        self.assertEqual(cards, ["数据录入与任务", "业务查询", "报告管理", "主数据维护"])
        # 三角色在 workspace 权限中
        roles = {r["role"] for r in payload["roles"]}
        self.assertIn("LIMS Manager", roles)
        self.assertIn("LIMS Analyst", roles)
        self.assertIn("LIMS Reviewer", roles)
        self.assertIn("System Manager", roles)

    def test_pyproject_declares_frappe_and_erpnext_dependencies(self):
        pyproject = (APP_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("[tool.bench.frappe-dependencies]", pyproject)
        self.assertIn('frappe = ">=16.0.0,<17.0.0"', pyproject)
        self.assertIn('erpnext = ">=16.0.0,<17.0.0"', pyproject)
        self.assertNotIn("hrms", pyproject)

    def test_logo_exists(self):
        logo = APP_ROOT / "hb_lims_app" / "public" / "hbos-lims-logo.svg"
        self.assertTrue(logo.exists())
        self.assertIn("<svg", logo.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
