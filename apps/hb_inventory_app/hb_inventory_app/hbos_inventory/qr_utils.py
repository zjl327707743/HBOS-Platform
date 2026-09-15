"""货位二维码辅助方法

二维码内容 = **货位查询链接**（不存静态物料信息），扫码后由 Web 页实时查库，
保证信息动态更新（Owner 在 M3-R0 已定）。

本模块经 `hooks.jinja.methods` 注册为 Jinja 全局方法，因此：

- 所有函数以 `hbos_` 前缀命名，避免覆盖 Frappe / ERPNext 的同名 Jinja 全局；
- **不 `from ... import ...`**（包括 pyqrcode），第三方依赖在函数内按需 import。
  注册机制会收集模块内**所有**函数，含 import 进来的函数——把 `qrcreate`
  这类短名注册成 Jinja 全局既无必要也不安全。
"""

import frappe

# 扫码页路由（与 www/hbos_bin.py 对应；路由名不能含连字符，否则模块无法 import）
BIN_PAGE_ROUTE = "hbos_bin"


def hbos_bin_code(warehouse):
	"""货位短码：去掉公司后缀。

	`16-03-221 - HB` → `16-03-221`；非货位库位（如 `3904 六车间中间库 - HB`）
	原样返回去掉后缀的部分。
	"""
	if not warehouse:
		return ""
	return warehouse.split(" - ")[0].strip()


def hbos_bin_url(warehouse):
	"""货位查询链接（二维码内容）。

	货位短码可能含中文与空格（如 `3904 六车间中间库`），需 URL 编码后再入二维码。
	"""
	if not warehouse:
		return ""
	from urllib.parse import quote

	code = hbos_bin_code(warehouse)
	return f"{frappe.utils.get_url()}/{BIN_PAGE_ROUTE}?bin={quote(code)}"


def hbos_bin_qr_svg(warehouse):
	"""货位二维码，返回内联 SVG 字符串（黑底白字反色，适合打印贴标签）。

	无货位或生成失败时返回空串，模板需自行兜底。
	"""
	url = hbos_bin_url(warehouse)
	if not url:
		return ""
	from io import BytesIO

	from pyqrcode import create as qrcreate

	stream = BytesIO()
	try:
		qr = qrcreate(url)
		qr.svg(stream, scale=8, background="white", module_color="black")
		return stream.getvalue().decode()
	finally:
		stream.close()


def hbos_bin_qr_data_uri(warehouse):
	"""货位二维码，返回可直接放进 `img src` 的 data URI。"""
	svg = hbos_bin_qr_svg(warehouse)
	if not svg:
		return ""
	from base64 import b64encode

	return "data:image/svg+xml;base64," + b64encode(svg.encode()).decode()
