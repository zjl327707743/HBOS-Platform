# -*- coding: utf-8 -*-
"""真实 Frappe 会话冒烟：只读调用待办摘要，不使用离线桩。

两个 runner 都必须能把它识别为「跳过」而不是「失败」：

- `python3 -m unittest discover`（项目离线门禁，宿主机无 frappe）——模块必须
  **导入成功**再跳过。因此这里不能在模块级用 `pytest.importorskip`：它会抛
  `Skipped`，被 unittest 的 loader 当成 import 错误，把整轮离线门禁弄红。
- pytest 能正常收集 `unittest.TestCase`，`unittest.skipUnless` 同样生效。

执行方式（需要 Frappe 会话，故只在容器内有效）：

    HBOS_FRAPPE_SMOKE=1 FRAPPE_SITE=frontend \
      /home/frappe/frappe-bench/env/bin/python -m pytest tests/test_todo_runtime_smoke.py
"""

import os
import sys
import unittest

try:  # 宿主机无 frappe：静默降级，不得抛异常
	import frappe
except ImportError:  # pragma: no cover - 离线门禁路径
	frappe = None


_SMOKE_READY = frappe is not None and os.environ.get("HBOS_FRAPPE_SMOKE") == "1"

# `apps/hb_lims_app/__init__.py` 存在时，pytest 会把 `apps/` 插到 sys.path 首位，
# 使 `hb_lims_app` 解析成外层目录（不含 `hbos_lims`）并**缓存进 sys.modules**。
# 只改 sys.path 不够——必须同时清掉这份错误缓存，再把它指回本 app 目录。
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure_app_on_path():
	for name in [n for n in list(sys.modules)
				 if n == "hb_lims_app" or n.startswith("hb_lims_app.")]:
		sys.modules.pop(name, None)
	while _APP_DIR in sys.path:
		sys.path.remove(_APP_DIR)
	sys.path.insert(0, _APP_DIR)


@unittest.skipUnless(_SMOKE_READY, "需要 Frappe 运行时且 HBOS_FRAPPE_SMOKE=1")
class TestTodoRuntimeSmoke(unittest.TestCase):
	def test_get_my_todo_summary_in_real_frappe_session(self):
		site = os.environ.get("FRAPPE_SITE", "frontend")
		sites_path = os.environ.get("FRAPPE_SITES_PATH", "/home/frappe/frappe-bench/sites")
		initialized_here = not getattr(getattr(frappe, "local", None), "site", None)
		if initialized_here:
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
		try:
			_ensure_app_on_path()
			from hb_lims_app.hbos_lims.todo_service import get_my_todo_summary

			response = get_my_todo_summary()

			self.assertGreaterEqual(set(response), {"summary", "user", "generated_at"})
			self.assertEqual(response["user"]["name"], frappe.session.user)
			self.assertGreaterEqual(
				set(response["summary"]),
				{"total", "assigned_to_me", "role_pending", "overdue", "by_module"},
			)
		finally:
			if initialized_here:
				frappe.destroy()
