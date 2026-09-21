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


def hbos_bin_qr_svg(warehouse, size_mm=20):
	"""货位二维码，返回内联 SVG 字符串（适合打印贴标签）。

	**尺寸由 `size_mm` 定，直接写进 SVG 的 width/height 属性。**

	为什么不能只在模板里用 CSS 定尺寸（实测教训）：pyqrcode 生成的 SVG 自带
	`height="520" width="520"`（约 138mm），而 **wkhtmltopdf 不认 CSS 对 svg 的
	`width`/`height` 覆盖**。于是那个 138mm 的块会把 60×40mm 的标签撑爆。
	改成把尺寸写进 SVG 属性后，wkhtmltopdf 就认了。

	⚠ **默认值 20mm 是与「HBOS 货位二维码」模板配套实测出来的**：
	该标签纸型 60×40mm，减去 3mm 四周页边距后可用高约 34mm。
	实测在这个尺寸下，「二维码 + 货位号(13pt) + 提示行(7pt)」刚好一页；
	调到 22mm 就会溢出成两页。**改这个默认值前请先跑一遍打印验证。**

	无货位或生成失败时返回空串，模板需自行兜底。
	"""
	url = hbos_bin_url(warehouse)
	if not url:
		return ""
	import re
	from io import BytesIO

	from pyqrcode import create as qrcreate

	stream = BytesIO()
	try:
		qr = qrcreate(url)
		qr.svg(stream, scale=8, background="white", module_color="black")
		svg = stream.getvalue().decode()
	finally:
		stream.close()

	# 去掉 XML 声明——内联进 HTML 时才合法
	svg = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", svg)

	# 把自带的像素尺寸换掉。注意 pyqrcode 的 520 是随 QR 版本变的，不能写死，
	# 故按属性名替换而不是按数值匹配。
	def _resize(m):
		attrs = re.sub(r'\s(?:width|height)="[^"]*"', "", m.group(1))
		return f'<svg{attrs} width="{size_mm}mm" height="{size_mm}mm"'

	return re.sub(r"<svg([^>]*)", _resize, svg, count=1)


def hbos_bin_qr_data_uri(warehouse, size_mm=26):
	"""货位二维码，返回可直接放进 `img src` 的 data URI。"""
	svg = hbos_bin_qr_svg(warehouse, size_mm=size_mm)
	if not svg:
		return ""
	from base64 import b64encode

	return "data:image/svg+xml;base64," + b64encode(svg.encode()).decode()
