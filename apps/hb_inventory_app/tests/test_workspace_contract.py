"""仓储库存入口契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

`hb_attendance_app` 早已用 `tests/test_workspace_contract.py` 锁住了
「入口必须可达」这条契约；`hb_inventory_app` 当时没建，于是三个入口缺陷
一路带到 Owner 验收才被发现：

1. 顶层图标用了 `stock`——**与 ERPNext 原生 Stock 模块同名同图**，
   桌面上两个一模一样的方块并排，点错就进了原生库存模块；
   而原生模块没有本 App 的侧边栏，用户**回不来**；
2. **工作台本身没有桌面条目**——桌面按「仓储库存工作台」搜不到任何东西；
3. 顶层条目叫「仓储库存」而非工作台名，靠名字找不到。

这里把这三条固定住，改回去就红。
"""

import json
import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "hb_inventory_app"
INV = APP / "hbos_inventory"
WORKSPACE_SETUP = INV / "workspace_setup.py"
PHOTO_INTAKE = INV / "page/hbos_photo_intake/hbos_photo_intake.js"

# ERPNext 原生 Stock 模块用的图标。顶层入口**绝不能**用这一个，
# 否则两个图标在桌面上无法区分（见模块 docstring 第 1 条）。
ERPNEXT_STOCK_ICON = "stock"


class WorkspaceContractTest(unittest.TestCase):
	def test_top_level_icon_does_not_collide_with_erpnext_stock(self):
		content = WORKSPACE_SETUP.read_text()
		icon_line = next(
			line for line in content.splitlines() if line.startswith("DESKTOP_ICON = ")
		)
		icon = icon_line.split("=", 1)[1].strip().strip('"').strip("'")
		self.assertNotEqual(
			icon,
			ERPNEXT_STOCK_ICON,
			"顶层入口图标不能与 ERPNext 原生 Stock 模块同名——"
			"桌面上会分不清，点错即进入原生库存模块且无法返回",
		)
		self.assertTrue(icon, "顶层入口必须显式指定图标")

	def test_workspace_has_its_own_desktop_entry_nested_under_entry_tile(self):
		"""桌面图标的 label 必须等于侧边栏名，且不得留 `parent_icon`。

		Frappe 的 `get_desktop_icons()` 拿 `label.lower()` 去
		`bootinfo.workspace_sidebar_item` 里查，**查不到就静默丢弃这个图标**
		（不报错、不提示）。而且父图标若不在放行集合里，**挂在它下面的图标
		会跟着一起消失**。

		历史上就栽在这两条上：label 用了 `仓储库存`（侧边栏叫
		`仓储库存工作台`）→ 查不到；parent_icon 又残留指向那个不可见的父图标
		→ 连工作台条目也一起被过滤，桌面上**一个入口都没有**。
		"""
		content = WORKSPACE_SETUP.read_text()
		self.assertIn("DESKTOP_LABEL = WORKSPACE_TITLE", content)
		self.assertNotIn('DESKTOP_LABEL = "仓储库存"', content)
		# parent_icon 必须被显式清空，不能靠「没赋值」蒙混过去——
		# 已存在的文档会带着旧值，不覆盖就残留。
		self.assertIn('icon.parent_icon = ""', content)

	def test_desktop_icon_label_matches_the_sidebar_it_points_at(self):
		"""图标 label、`link_to`、`sidebar` 三者同源，指向同一个侧边栏。

		`_sync_sidebar()` 用 `WORKSPACE_TITLE` 建侧边栏，
		`_sync_desktop_icon()` 也必须用同一个常量，否则又会出现
		「label 查不到侧边栏 → 图标被丢弃」。
		"""
		content = WORKSPACE_SETUP.read_text()
		self.assertIn("sidebar.title = WORKSPACE_TITLE", content)
		self.assertIn("icon.label = DESKTOP_LABEL", content)
		self.assertIn("icon.link_to = WORKSPACE_TITLE", content)
		self.assertIn("icon.sidebar = WORKSPACE_TITLE", content)

	def test_stale_desktop_icons_are_cleaned_up(self):
		"""早期留下的、不指向任何侧边栏的图标必须被清掉。

		这类图标不会被渲染，但记录还在；而挂在它下面的图标会跟着一起消失。
		留着只会让后来的人以为「已经配过了」。
		"""
		content = WORKSPACE_SETUP.read_text()
		self.assertIn("STALE_DESKTOP_LABELS", content)
		self.assertIn("def _cleanup_stale_desktop_icons", content)
		self.assertIn("_cleanup_stale_desktop_icons()", content)
		self.assertIn('"仓储库存"', content)

	def test_desktop_and_sidebar_point_at_the_workspace_sidebar(self):
		content = WORKSPACE_SETUP.read_text()
		self.assertIn('WORKSPACE_TITLE = "仓储库存工作台"', content)
		self.assertIn('icon.link_type = "Workspace Sidebar"', content)
		self.assertIn("icon.link_to = WORKSPACE_TITLE", content)
		self.assertIn("sidebar.title = WORKSPACE_TITLE", content)

	def test_sidebar_covers_entry_page_reports_and_master_data(self):
		content = WORKSPACE_SETUP.read_text()
		for label in (
			"仓储库存工作台",
			"入库拍照识别",
			"入库登记（原生）",
			"出库核销",
			"货位变更",
			"批次",
			"物料",
			"货位",
			"按批号查货位",
			"货位明细表",
			"效期预警",
			"库级盘点三对账",
			"货位二维码（在货位上打印）",
		):
			self.assertIn(label, content, f"侧边栏缺入口：{label}")

	def test_workspace_links_expose_the_four_reports(self):
		content = WORKSPACE_SETUP.read_text()
		for report in ("按批号查货位", "货位明细表", "效期预警", "库级盘点三对账"):
			self.assertIn(f'"link_to": "{report}"', content)

	def test_photo_intake_page_has_a_way_back_to_the_workspace(self):
		"""拍照识别页要给「返回工作台」的出口。

		原生库存模块没有本 App 的侧边栏，用户进去就回不来；
		本 App 自己的页面必须至少有一条回路。
		"""
		content = PHOTO_INTAKE.read_text()
		self.assertIn("返回仓储库存工作台", content)
		self.assertIn('data-route="Workspaces/仓储库存工作台"', content)

	def test_workspace_content_is_valid_json(self):
		"""`WORKSPACE_CONTENT` 是塞进 JSON 字段的字符串，拼错会静默坏版式。

		必须按**运行时的值**校验：源文件里那些 `\\\\"` 要经过 Python 字符串
		解析才变成 JSON 里的 `\\"`。直接对源码文本 `json.loads` 会误报，
		用 `ast.literal_eval` 取到真正的字符串，与 `_parse_content` 同口径。
		"""
		import ast

		tree = ast.parse(WORKSPACE_SETUP.read_text())
		node = next(
			n
			for n in tree.body
			if isinstance(n, ast.Assign)
			and getattr(n.targets[0], "id", None) == "WORKSPACE_CONTENT"
		)
		payload = ast.literal_eval(node.value)
		parsed = json.loads(payload)
		self.assertIsInstance(parsed, list)
		self.assertTrue(parsed, "工作台内容不能为空")
		# 每个块都要有 id / type，否则 Desk 渲染时会静默丢块
		for block in parsed:
			self.assertIn("id", block)
			self.assertIn("type", block)


if __name__ == "__main__":
	unittest.main()
