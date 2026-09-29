from __future__ import annotations

"""货位二维码契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

货位二维码属于「生成成功但**印出来扫不出来**」的一类缺陷——PDF 能开、页码对、
文字也在，唯独二维码被裁掉了。它在服务端不报任何错，只有拿到实物才发现。

2026-09-29 Owner 报的就是这条：导出的二维码只剩左上角一小块。

**根因**：`pyqrcode` 生成的 SVG **不带 `viewBox`**，内容按自己的坐标画
（边长 = 模块数 × scale，实测量到 520 / 328）。SVG 的规则是
**没有 `viewBox` 就只换视口、不缩放内容**——于是 520 单位的内容被裁进
20mm（≈75px）的框里，只看得见一个角。

上一版把 `<svg width="520" height="520">` 改成 `width="20mm" height="20mm"`
就以为完事了，**实测只验了「一页装得下」，没验「二维码是不是完整」**。
两个数都变了，但方向不同：一个管**溢出**，一个管**裁切**。

## 这份测试守什么

`hbos_bin_qr_svg` 的尺寸改写必须三件事一起做：

1. **补 `viewBox`**，边长取自**原始 svg 的 width 属性**（不能自己按
   `(模块数+8)*scale` 算——静区是 pyqrcode 的实现细节，会随上游漂）；
2. `width` / `height` 改成 `{size_mm}mm`；
3. 把自带的像素 `width`/`height` **删掉**，别两套尺寸并存。

它是**静态**的：读源码断言形状。要证明「肉眼看到的是完整二维码」，
得渲染 PDF 再解码——那属于另一种测试，本文件不做。
"""

import re
import unittest
from pathlib import Path

QR_UTILS = (
    Path(__file__).parents[1] / "hb_inventory_app" / "hbos_inventory" / "qr_utils.py"
)
QR_TEMPLATE = (
    Path(__file__).parents[1]
    / "hb_inventory_app"
    / "hbos_inventory"
    / "print_format"
    / "HBOS货位二维码"
    / "HBOS货位二维码.json"
)


def _fn_body(src: str, name: str) -> str:
    """取 `def <name>(...)` 的**代码正文**（到下一个顶层 def 为止）。

    **剥掉 docstring**：函数文档里大量讨论 viewBox / 尺寸，若把 docstring 算进去，
    断言 `"viewBox" in body` 光靠注释就能通过——那是假绿。
    （实测：把 viewBox 那行删掉后，带 docstring 的版本仍判「通过」。）
    """
    m = re.search(rf"\ndef {name}\(.*?(?=\ndef |\Z)", src, re.S)
    assert m, f"找不到 {name}"
    body = m.group(0)
    # 去掉紧跟 def 行的三引号文档字符串
    return re.sub(r'^\t""".*?"""\n', "", body, count=1, flags=re.S | re.M)


class WarehouseQrSvgContractTest(unittest.TestCase):
    def setUp(self):
        src = QR_UTILS.read_text(encoding="utf-8")
        self.body = _fn_body(src, "hbos_bin_qr_svg")
        self.assertNotIn('"""', self.body, "docstring 没剥干净，后面的断言会假绿")

    def test_viewbox_is_added(self):
        """没有 viewBox 就只换视口、不缩放内容——内容会被裁成一个角。

        这一半（拼装）与下一半（边长取自原始 width）**必须同时成立**；
        放开任何一条都等于退回 2026-09-29 那个 bug。

        **断言盯的是真正拼进 SVG 的那一句**，不是「文中出现过这个词」——
        docstring 与注释里都写着 viewBox，只查关键词的话删掉实现也照样绿
        （实测踩过：注释里那半句就让这条假通过了）。
        """
        ret = re.search(r"return f'<svg\{attrs\}[^\n]*", self.body)
        self.assertIsNotNone(ret, "找不到拼 SVG 标签的那一句 return")
        self.assertIn(
            "{view_box}",
            ret.group(0),
            "拼出的 <svg> 标签要插进 view_box——只有它能让内容缩放进尺寸框",
        )
        assign = re.search(r'view_box\s*=\s*f\'[^\']*viewBox="0 0 \{side\} \{side\}"', self.body)
        self.assertIsNotNone(
            assign,
            "view_box 变量本身要拼出 `viewBox=\"0 0 {side} {side}\"`",
        )

    def test_viewbox_side_comes_from_the_original_width_attribute(self):
        """viewBox 边长必须**从原始 svg 读**，不能自己算。

        自己算就得写死静区（`+8`），那是 pyqrcode 的实现细节，会随它的版本漂。
        """
        # 先按属性名把原始 width 抓出来
        self.assertRegex(
            self.body,
            r"re\.search\(\s*r\"<svg\[\^>\]\*\\swidth=",
            "应从 svg 标签的 width 属性读原始边长",
        )
        self.assertRegex(
            self.body,
            r"side\s*=\s*m\.group\(1\)",
            "把捕获到的原始边长存进 side",
        )
        self.assertRegex(
            self.body,
            r"viewBox=\"0 0 \{side\} \{side\}\"",
            "viewBox 用 side 拼出 0 0 N N",
        )

    def test_size_becomes_mm_and_pixel_size_is_stripped(self):
        self.assertIn('width="{size_mm}mm"', self.body)
        self.assertIn('height="{size_mm}mm"', self.body)
        self.assertRegex(
            self.body,
            r're\.sub\(\s*r\'\\s\(\?:width\|height\)=',
            "先把自带的像素 width/height 去掉，避免两套尺寸并存",
        )

    def test_xml_declaration_is_still_stripped(self):
        """内联进 HTML 的 SVG 不能带 XML 声明。"""
        self.assertRegex(
            self.body,
            r're\.sub\(\s*r"\^\\s\*<\\\?xml',
            "仍要剥掉 <?xml ... ?> 声明",
        )


class WarehouseQrTemplateContractTest(unittest.TestCase):
    def setUp(self):
        import json

        self.html = json.loads(QR_TEMPLATE.read_text(encoding="utf-8"))["html"]

    def test_template_passes_a_size(self):
        """尺寸全在 SVG 属性里，模板必须显式传——CSS 覆盖不了。"""
        m = re.search(r"hbos_bin_qr_svg\(doc\.name,\s*(\d+)\)", self.html)
        self.assertIsNotNone(m, "模板没调用 hbos_bin_qr_svg(doc.name, N)")
        size = int(m.group(1))
        # 与 qr_utils 里那条实测结论对齐：60×40mm 标签上 22mm 会溢出成两页
        self.assertLessEqual(size, 20, "超过 20mm 会把这枚 60×40mm 标签撑成两页")
        self.assertGreater(size, 0)

    def test_template_does_not_size_the_svg_with_css(self):
        """CSS 对 svg 的 width/height 在 wkhtmltopdf 里不生效——模板不能再走那条路。"""
        css = self.html[self.html.find("<style") : self.html.find("</style>")]
        self.assertNotRegex(
            css,
            r"\.hbos-qr\s+\.img\s+svg\s*\{[^}]*\bwidth\s*:",
            "别用 CSS 给 svg 定宽——wkhtmltopdf 不认",
        )


if __name__ == "__main__":
    unittest.main()
