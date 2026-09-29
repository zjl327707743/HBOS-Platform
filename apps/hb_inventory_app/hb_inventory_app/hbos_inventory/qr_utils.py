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

	## 改 width/height 的同时**必须补 `viewBox`**（2026-09-29 修）

	pyqrcode 出的 SVG **不带 `viewBox`**，内容按自己的坐标画（边长 =
	`(模块数+8) × scale`，实测量到 520 或 328）。SVG 的规则是：**没有 `viewBox`
	就只换视口、不缩放内容** —— 于是 520 单位的内容被裁进 20mm（≈75px）的框里，
	**只看得见左上角一小块**，二维码是残的、扫不出来。

	Owner 2026-09-29 报了这条（导出的货位二维码只有一小块）。
	补上 `viewBox="0 0 N N"` 后内容会等比缩放到 20mm。

	注意：上一版只测了「一页装得下」，没有核对二维码**是否完整**——
	`trHeight` 那类「样式写错但不报错」的坑，这里又踩了一次。

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
	sv = re.sub(r"^\s*<\?xml[^>]*\?>\s*", "", svg)

	# 从原始 width 里取出内容边长（= 模块数 × scale），用作 viewBox。
	# 按属性读而不是自己算 `(len(qr.code)+8)*scale`——静区是 pyqrcode 的实现细节，
	# 写死会随它的版本漂移。
	m = re.search(r"<svg[^>]*\swidth=\"(\d+)\"", sv)
	side = m.group(1) if m else ""

	# 换掉自带的像素尺寸，并补 viewBox。注意 pyqrcode 的 520 随 QR 版本变，不能写死，
	# 故按属性名替换而不是按数值匹配。
	def _resize(match):
		attrs = re.sub(r'\s(?:width|height)="[^"]*"', "", match.group(1))
		view_box = f' viewBox="0 0 {side} {side}"' if side else ""
		return f'<svg{attrs}{view_box} width="{size_mm}mm" height="{size_mm}mm"'

	return re.sub(r"<svg([^>]*)", _resize, sv, count=1)


def hbos_bin_qr_data_uri(warehouse, size_mm=26):
	"""货位二维码，返回可直接放进 `img src` 的 data URI。"""
	svg = hbos_bin_qr_svg(warehouse, size_mm=size_mm)
	if not svg:
		return ""
	from base64 import b64encode

	return "data:image/svg+xml;base64," + b64encode(svg.encode()).decode()
