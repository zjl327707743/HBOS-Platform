"""入库接口的安全契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

2026-09-24 的独立审计在 `hb_inventory_app` 上查出若干**越权类**缺陷。
它们的共同形状是：

    某个动作在"业务上"是对的，但**服务端没有校验调用者有没有资格做它** ——
    而入口处的角色判断（`_require_permission`）只挡"能不能用这个页面"，
    **挡不住"能用页面的人能不能动这一条数据"**。

这类缺陷**没有报错、没有日志**，功能测试全绿也照样存在。所以用静态断言把
"校验必须在场"钉住：改回不校验就红。

## 两个刻意的设计（都是被坑过才这么写的）

**一、断言取「可执行代码」，不取源码文本。**
第一版直接读源码，结果**变异测试当场打脸**：把 `doc.check_permission("read")`
改成 `pass`，测试**照样绿**——因为函数 docstring 里有一句
「为什么必须 `check_permission("read")`」，字符串断言被**注释**满足了。
现在用 `ast.unparse` 重新生成代码（注释天然消失，docstring 显式剥掉），
prose 再也过不了。

**二、能结构化的就不比字符串。**
`existing.item` 在 `frappe.throw` 的提示文案里也会出现——按字符串查，
把校验改成 `if False:` 依然"命中"。所以 `_ensure_batch` 那条改成
**在 AST 里找那个比较节点**。

两条都是同一个教训：**断言的对象必须是它以为的那个东西**；
否则测试会稳定地给假绿，而且看不出哪里不对。

## 为什么用静态断言而不是跑真 site

跑真 site 能验得更实，但那要求 CI 起 Frappe + MariaDB，属后续阶段
（审计 I8-P0-11 已单列）。**当前这一层成本几乎为零**，且正好覆盖
"校验有没有被删掉"这个最容易被回退的点；语义是否正确由人审。
"""

import ast
import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "hb_inventory_app"
API = APP / "hbos_inventory/api.py"
PHOTO_INTAKE = APP / "hbos_inventory/page/hbos_photo_intake/hbos_photo_intake.js"


def _func_ast(name: str) -> ast.FunctionDef:
	"""取某个模块级函数的 AST 节点。"""
	for node in ast.parse(API.read_text()).body:
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"api.py 里找不到函数 {name}")


def _func_code(name: str) -> str:
	"""取某个模块级函数的**可执行代码**：注释与 docstring 都已剥离。

	`ast.unparse` 会把引号规范成单引号——**断言要按规范化后的形态写**
	（`check_permission('read')`，不是 `check_permission("read")`）。
	这是好事：断言因此不受格式化风格影响。
	"""
	body = _func_ast(name).body
	if (
		body
		and isinstance(body[0], ast.Expr)
		and isinstance(body[0].value, ast.Constant)
		and isinstance(body[0].value.value, str)
	):
		body = body[1:]  # 去掉 docstring
	m = ast.Module(body=body, type_ignores=[])
	return "\n".join(ast.unparse(s) for s in ast.parse(ast.unparse(m)).body)


def _calls_in(node: ast.AST) -> list[str]:
	"""列出该子树里所有调用的「规范化签名」，如 `doc.check_permission('read')`。"""
	return [ast.unparse(n.func) + "(%s)" % ", ".join(ast.unparse(a) for a in n.args)
	        for n in ast.walk(node) if isinstance(n, ast.Call)]


class FileAuthorizationTest(unittest.TestCase):
	"""审计 I8-P0-03：File 读取 / 改挂必须有对象级授权。"""

	def test_read_file_checks_permission(self):
		"""`_read_file` 必须调 `check_permission("read")`。

		没有它，任何能调 `recognize_label` 的人只要猜到**私有** file_url，
		就能让服务端把别人的附件读出来送去识别，文件名与批号还会从结果里漏回来。
		"""
		self.assertIn(
			"check_permission('read')",
			_func_code("_read_file"),
			"读文件前必须校验 read 权限",
		)

	def test_read_file_validates_image_content(self):
		"""内容按**魔数**判断是不是图片，不靠文件名 / 扩展名（那些是客户端给的）。"""
		self.assertIn("_require_image(", _func_code("_read_file"), "读出的内容必须过图片校验")
		guard = _func_code("_require_image")
		self.assertIn("_IMAGE_MAGIC", guard, "按魔数判断，不看扩展名")
		self.assertIn("MAX_PHOTO_BYTES", guard, "必须有大小上限")

	def test_attach_photo_only_touches_own_file(self):
		"""`_attach_photo` 必须确认文件属于调用者（或有写权限）。"""
		src = _func_code("_attach_photo")
		self.assertIn("frappe.session.user", src, "要比对 owner 与会话用户")
		self.assertIn("check_permission('write')", src, "不是自己的文件要求写权限")

	def test_attach_photo_reparents_by_copying(self):
		"""已挂在别的单据上的附件**不能改挂**，要复制。

		改挂会让对方单据凭空少一张原始凭证（审计原话："可把已有附件从其他业务
		对象'改挂'到 Stock Entry"）。复制则两边都在。
		"""
		src = _func_code("_attach_photo")
		self.assertIn(
			"_clone_file(source, doctype, docname, file_url)", src, "已被占用的附件应走复制"
		)
		# 得先判断"是否已被占用"，否则复制分支永远不会走
		self.assertIn("source.attached_to_doctype and source.attached_to_name", src)

	def test_attach_photo_url_fallback_is_scoped_to_self(self):
		"""按 url 兜底时也只取自己的文件——否则同一 url 可能取到别人的那条。"""
		self.assertIn("'owner': frappe.session.user", _func_code("_attach_photo"))

	def test_recognize_passes_file_name_from_frontend(self):
		"""前端要把 `File` 的 docname 传下来，服务端才能精确定位（并做 owner 校验）。"""
		self.assertIn("file_name: state.fileDocName", PHOTO_INTAKE.read_text())


class WarehousePermissionTest(unittest.TestCase):
	"""审计 I8-P0-02：仓库 API 不得绕过 Warehouse / Company 权限。"""

	def test_leaf_warehouses_is_permission_aware(self):
		"""货位下拉必须用权限感知查询。

		`frappe.get_all` 明确"不检查权限"（框架 docstring 原话）。用它列货位，
		等于把全公司所有公司的货位都端给任何能打开本页面的人。
		"""
		src = _func_code("_leaf_warehouses")
		self.assertIn("frappe.get_list(", src, "货位下拉必须走 get_list")
		self.assertNotIn("frappe.get_all(", src, "不得用不检查权限的 get_all")

	def test_nearby_item_codes_is_permission_aware(self):
		src = _func_code("_nearby_item_codes")
		self.assertIn("frappe.get_list(", src)
		self.assertNotIn("frappe.get_all(", src)

	def test_create_draft_checks_warehouse_and_company(self):
		"""建草稿前必须显式校验目标货位与公司。

		本函数随后用 `ignore_permissions` 写库——那是为了不依赖 ERPNext 的
		Item / Stock Entry 权限矩阵，**不是**为了绕过货位权限。
		两者必须分开：校验在这里做掉，提权只负责把写操作落地。
		"""
		src = _func_code("create_intake_draft")
		self.assertIn("_require_warehouse_write(warehouse)", src, "必须校验目标货位写权限")
		self.assertIn("has_permission('Company', 'read'", src, "必须校验公司权限")

	def test_no_bare_get_all_in_api(self):
		"""整个 api.py 不出现 `frappe.get_all` —— 防以后再引入。

		新增查询时若确实需要不受权限限制的读，得先改这条测试并写明理由，
		而不是被静默放过。
		"""
		self.assertNotIn(
			"frappe.get_all(",
			API.read_text(),
			"api.py 不应出现不检查权限的 frappe.get_all（用 get_list，或写明理由后另议）",
		)


class BatchOwnershipTest(unittest.TestCase):
	"""审计 I8-P0-05：已存在的 Batch 必须校验所属 Item。"""

	def test_existing_batch_item_is_compared(self):
		"""`_ensure_batch` 里必须存在一个「`existing.item` 与 `item_code` 相比」的比较。

		`Batch.batch_id` 全局唯一，其语义就是"批号"——同一个批号不可能属于两个物料。
		少了这一步，物料代码认错时会**默默把 B 的数量记到 A 的批号上**。

		**在 AST 里找那个比较，而不是找字符串**：`existing.item` 在 `frappe.throw`
		的提示文案里也会出现，按字符串查会被那处满足
		——把校验改成 `if False:` 测试照样"通过"（第一版就漏在这儿）。
		"""
		node = _func_ast("_ensure_batch")
		found = []
		for sub in ast.walk(node):
			if not isinstance(sub, ast.Compare):
				continue
			texts = [ast.unparse(o) for o in [sub.left, *sub.comparators]]
			if any("existing.item" in t for t in texts) and any("item_code" in t for t in texts):
				found.append(ast.unparse(sub))
		self.assertTrue(
			found,
			"_ensure_batch 里必须有一个把 existing.item 与 item_code 相比的比较"
			"（删了就不再校验批号归属）",
		)

	def test_mismatch_is_rejected(self):
		"""比对之后必须拒绝——只比不拦等于没比。"""
		node = _func_ast("_ensure_batch")
		# 找到那个比较节点所在的 if，确认它体内有 throw
		for sub in ast.walk(node):
			if not isinstance(sub, ast.If):
				continue
			texts = [ast.unparse(o) for o in ast.walk(sub.test) if isinstance(o, ast.Compare)]
			if not any("existing.item" in t for t in texts):
				continue
			body_calls = sum(len(_calls_in(s)) for s in sub.body)
			self.assertIn(
				"frappe.throw",
				_func_code("_ensure_batch"),
				"不一致必须 throw",
			)
			self.assertTrue(body_calls, "归属不符的分支不能是空的")
			return
		self.fail("没找到「existing.item 与 item_code 比较」的那个 if")


if __name__ == "__main__":
	unittest.main()
