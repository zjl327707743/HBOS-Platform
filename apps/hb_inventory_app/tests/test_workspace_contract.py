"""仓库工作台入口契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

`hb_attendance_app` 早已用 `tests/test_workspace_contract.py` 锁住了
「入口必须可达」这条契约；`hb_inventory_app` 当时没建，于是缺陷一路带到
Owner 验收才被发现——**桌面上一个入口都没有**。

真正的原因不是「图标没生效」，而是 Frappe 的 `get_desktop_icons()` 里有
**两条失败时完全不报错**的过滤规则：

    规则 A：图标 label 必须能在 bootinfo 的侧边栏映射里查到
            sidebar = bootinfo.workspace_sidebar_item.get(s.label.lower())
            permitted = bool(sidebar and sidebar["items"])

    规则 B：父图标不在放行集合里，挂在它下面的图标也一起出不来
            user_icons = [s for s in permitted_icons
                          if not s.parent_icon or s.parent_icon in permitted_parent_labels]

当时踩的链子：图标 label 叫「仓储库存」而侧边栏叫「仓储库存工作台」→
规则 A 丢弃；想补的工作台条目又挂在那个已被丢弃的父图标下 → 规则 B 连它
一起过滤。

这里把这条链子的每一环都固定住，改回去就红。
"""

import ast
import json
import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "hb_inventory_app"
INV = APP / "hbos_inventory"
WORKSPACE_SETUP = INV / "workspace_setup.py"
PHOTO_INTAKE = INV / "page/hbos_photo_intake/hbos_photo_intake.js"
STOCK_ENTRY_JS = Path(__file__).parents[1] / "hb_inventory_app/public/js/stock_entry.js"
BATCH_JS = Path(__file__).parents[1] / "hb_inventory_app/public/js/batch.js"

# ERPNext 原生 Stock 模块用的图标。顶层入口**绝不能**用这一个，
# 否则两个图标在桌面上无法区分，点错即进入原生模块且回不来。
ERPNEXT_STOCK_ICON = "stock"


def _eval(node, consts):
	"""递归求值，把嵌套的 Name 也解出来。

	`SIDEBAR_ITEMS` 里混着常量引用（`{"label": WORKSPACE_TITLE, ...}`），
	`ast.literal_eval` 直接吃会报错，所以自己走一遍。
	"""
	if isinstance(node, ast.Constant):
		return node.value
	if isinstance(node, ast.Name):
		return consts[node.id]  # 未定义的会 KeyError，正是我们要的
	if isinstance(node, ast.List):
		return [_eval(e, consts) for e in node.elts]
	if isinstance(node, ast.Tuple):
		return tuple(_eval(e, consts) for e in node.elts)
	if isinstance(node, ast.Dict):
		return {_eval(k, consts): _eval(v, consts) for k, v in zip(node.keys, node.values)}
	raise ValueError(f"不支持的表达式：{ast.dump(node)[:60]}")


def _module_consts():
	"""把模块级赋值解析成 `{名: 值}`（运行时值，不是源码文本）。

	按**源码顺序**单遍求值——常量都在使用它们之前定义，前向引用天然可用。
	"""
	tree = ast.parse(WORKSPACE_SETUP.read_text())
	resolved: dict = {}
	for node in tree.body:
		if not isinstance(node, ast.Assign):
			continue
		target = getattr(node.targets[0], "id", None)
		if not target:
			continue
		try:
			resolved[target] = _eval(node.value, resolved)
		except (ValueError, KeyError):
			continue  # 非字面量 / 函数调用等，跳过
	return resolved


def _assign(name):
	"""取模块级常量的**运行时值**（不是源码文本）。"""
	value = _module_consts().get(name)
	# `WORKSPACE_CONTENT` 是三元引号字符串，_eval 能直接拿到
	if value is None:
		raise KeyError(f"未能在 {WORKSPACE_SETUP.name} 中解析出 {name}")
	return value


def _set_call_list(prop):
	"""取 `workspace.set("<prop>", [...])` 里那个列表的运行时值。

	**必须走 AST**：那块是函数体里的字面量，不是模块级常量；按文本抠会
	连带把注释里的说明一起算进去。
	"""
	consts = _module_consts()
	for node in ast.walk(ast.parse(WORKSPACE_SETUP.read_text())):
		if not isinstance(node, ast.Call):
			continue
		func = node.func
		if not (isinstance(func, ast.Attribute) and func.attr == "set"):
			continue
		if not node.args or not isinstance(node.args[0], ast.Constant):
			continue
		if node.args[0].value == prop:
			return _eval(node.args[1], consts)
	raise KeyError(f"未找到 workspace.set(\"{prop}\", ...)")


class WorkspaceContractTest(unittest.TestCase):
	def test_title_label_and_sidebar_are_the_same_name(self):
		"""工作台 / 侧边栏 / 桌面图标**必须同名**。

		三者的 `name` 都等于标题，而规则 A 要求图标 label 能在侧边栏映射里
		查到——名字一旦不一致，图标就被静默丢弃。这是历史上出问题的根因。
		"""
		self.assertEqual(
			_assign("WORKSPACE_TITLE"),
			_assign("DESKTOP_LABEL"),
			"`DESKTOP_LABEL` 必须等于 `WORKSPACE_TITLE`，否则图标会被 Frappe 静默丢弃",
		)
		content = WORKSPACE_SETUP.read_text()
		self.assertIn("DESKTOP_LABEL = WORKSPACE_TITLE", content)
		# 侧边栏 / 图标都拿同一个常量当名字
		self.assertIn("sidebar.title = WORKSPACE_TITLE", content)
		self.assertIn("icon.label = DESKTOP_LABEL", content)
		self.assertIn("icon.link_to = WORKSPACE_TITLE", content)
		self.assertIn("icon.sidebar = WORKSPACE_TITLE", content)

	def test_top_level_icon_does_not_collide_with_erpnext_stock(self):
		icon = _assign("DESKTOP_ICON")
		self.assertNotEqual(
			icon,
			ERPNEXT_STOCK_ICON,
			"顶层入口图标不能与 ERPNext 原生 Stock 模块同名——"
			"桌面上会分不清，点错即进入原生库存模块且无法返回",
		)
		self.assertTrue(icon, "顶层入口必须显式指定图标")

	def test_parent_icon_is_explicitly_cleared(self):
		"""`parent_icon` 必须被显式清空，不能靠「没赋值」蒙混过关。

		规则 B 会把「父图标不可见」的图标一起过滤掉。已存在的文档会带着
		旧值，不覆盖就残留——这正是上一版改完仍不见效的原因。
		"""
		content = WORKSPACE_SETUP.read_text()
		self.assertIn('icon.parent_icon = ""', content)

	def test_legacy_titles_are_cleaned_up(self):
		"""换标题等于换主键，旧对象不会自动消失，必须显式删。

		残留的旧 Desktop Icon 会被规则 A 丢弃（不显示但记录还在），
		而挂在它下面的图标会被规则 B 连累一起消失。
		"""
		legacy = _assign("LEGACY_TITLES")
		self.assertIn("仓储库存工作台", legacy, "改名前的标题必须登记")
		self.assertIn("仓储库存", legacy, "更早的僵尸父图标名必须登记")
		self.assertNotIn(
			_assign("WORKSPACE_TITLE"), legacy, "当前标题不能出现在待删列表里"
		)
		content = WORKSPACE_SETUP.read_text()
		self.assertIn("def _cleanup_legacy_objects", content)
		# 必须最先执行，否则旧图标会在本次同步期间继续干扰
		self.assertLess(
			content.index("_cleanup_legacy_objects()\n\n\tworkspace ="),
			content.index("_sync_sidebar()"),
			"清理历史对象必须排在同步之前",
		)

	def test_legacy_cleanup_unparents_children_before_deleting(self):
		"""删旧图标前要先解除子图标的指向，避免留下悬空 `parent_icon`。"""
		content = WORKSPACE_SETUP.read_text()
		self.assertIn('"parent_icon": legacy', content)

	def test_sidebar_only_lists_what_is_unique_to_this_app(self):
		"""侧边栏**只放本 App 独有的**：1 个页面 + 4 个报表。

		Owner 在 2026-09-23 提出「为什么要单独做仓库工作台、不能集成在原生库存里」，
		结论是**保留工作台但瘦身**——把与 ERPNext 原生库存重复的条目撤掉，
		让这个工作台只回答「海滨特有的东西在哪」。

		撤掉的理由（别再有人加回去）：那些目标本来就是原生库存模块的内容；
		而且三个 Stock Entry 条目**指向同一个地方**（原生 Stock Entry 列表），
		只是标签不同，等于在许诺一件没做的事。

		**按解析出的常量断言，不按源码文本**——注释里会提到这些名字
		（说明「为什么撤掉」），按文本查会误报。
		"""
		labels = {i["label"] for i in _assign("SIDEBAR_ITEMS")}
		for label in (
			"入库拍照识别",
			"按批号查货位",
			"货位明细表",
			"效期预警",
			"库级盘点三对账",
		):
			self.assertIn(label, labels, f"侧边栏缺入口：{label}")

		for label in ("入库登记（原生）", "出库核销", "货位变更", "货位二维码（在货位上打印）"):
			self.assertNotIn(label, labels, f"「{label}」与原生库存重复，不应再列")

	def test_sidebar_has_no_doctype_links_at_all(self):
		"""侧边栏不再指向任何原生 DocType——那些入口归原生库存模块管。

		这条比逐条列举更耐用：以后想加「规格」「BOM」之类，会先撞到这里，
		逼着人重新想一遍「这到底是不是海滨特有的」。
		"""
		items = _assign("SIDEBAR_ITEMS")
		bad = [i["label"] for i in items if i.get("link_type") == "DocType"]
		self.assertEqual(bad, [], f"侧边栏不应再列原生 DocType 入口，却发现了：{bad}")

	def test_shortcuts_are_not_repeated_in_sidebar_links(self):
		"""快捷方式与「链接卡片」是两套，不该列同一批东西。"""
		shortcuts = _set_call_list("shortcuts")
		labels = {s["label"] for s in shortcuts}
		self.assertEqual(labels, {"入库拍照识别"}, f"快捷方式应只留拍照识别，实际：{labels}")

	def test_workspace_links_expose_the_four_reports(self):
		content = WORKSPACE_SETUP.read_text()
		for report in ("按批号查货位", "货位明细表", "效期预警", "库级盘点三对账"):
			self.assertIn(f'"link_to": "{report}"', content)

	def test_native_forms_have_a_way_back(self):
		"""会用到的两个原生表单都要有「返回仓库工作台」的出口。

		原生库存模块里没有本 App 的侧边栏，从拍照识别过来的操作员落在那里
		会找不到回去的路（Owner 报的「跳出了仓库工作台」）。
		库存单据**继续用原生表单**（重写等于改核心源码），只是补一条回路：

		- `Stock Entry`：草稿复核 / 提交都在这里；
		- `Batch`：提交后被引导到这里取货位卡与待检证。
		"""
		title = _assign("WORKSPACE_TITLE")
		for path in (STOCK_ENTRY_JS, BATCH_JS):
			content = path.read_text()
			self.assertIn("返回仓库工作台", content, f"{path.name} 缺少返回出口")
			self.assertIn(f'frappe.set_route("Workspaces", "{title}")', content)

	def test_photo_intake_page_has_a_way_back_to_the_workspace(self):
		"""拍照识别页要给「返回工作台」的出口，且指向**当前**工作台名。

		原生库存模块没有本 App 的侧边栏，用户进去就回不来；
		本 App 自己的页面必须至少有一条回路。改名后这条路由要跟着改，
		否则按钮会 404。
		"""
		title = _assign("WORKSPACE_TITLE")
		content = PHOTO_INTAKE.read_text()
		self.assertIn("返回仓库工作台", content)
		self.assertIn(f'data-route="Workspaces/{title}"', content)

	def test_workspace_content_is_valid_json(self):
		"""`WORKSPACE_CONTENT` 是塞进 JSON 字段的字符串，拼错会静默坏版式。

		必须按**运行时的值**校验：源码里那些 `\\\\"` 要经过 Python 字符串
		解析才变成 JSON 里的 `\\"`。直接对源码文本 `json.loads` 会误报，
		用 `ast.literal_eval` 取到真正的字符串，与 `_parse_content` 同口径。
		"""
		parsed = json.loads(_assign("WORKSPACE_CONTENT"))
		self.assertIsInstance(parsed, list)
		self.assertTrue(parsed, "工作台内容不能为空")
		for block in parsed:
			self.assertIn("id", block)
			self.assertIn("type", block)


if __name__ == "__main__":
	unittest.main()
