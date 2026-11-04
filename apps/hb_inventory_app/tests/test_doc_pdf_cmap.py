"""Offline regression for the inventory PDF's ToUnicode transformation.

Load the actual pure transformation without importing Frappe or a PDF engine.
These checks preserve complete CMap syntax and target-only Unicode changes;
the isolated native CI separately verifies text in genuinely generated PDFs.
"""

import ast
from pathlib import Path
import re
import unicodedata
import unittest


def _load_transform():
    source = Path(__file__).resolve().parents[1] / "hb_inventory_app/hbos_inventory/doc_gen.py"
    constants = {
        "_KANGXI_LO", "_KANGXI_HI", "_BFCHAR_RE", "_BFRANGE_RE", "_HEX4", "_RADICAL_SUPPLEMENT",
    }
    functions = {"_kangxi_to_han", "_fix_tounicode_cmap"}
    nodes = []
    for node in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(part, ast.Name) and part.id in constants
            for target in node.targets for part in ast.walk(target)
        ):
            nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
    namespace = {"re": re, "unicodedata": unicodedata}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_fix_tounicode_cmap"]


_TRANSFORM = _load_transform()
_HEADER = """/CIDInit /ProcSet findresource begin
12 dict begin
begincmap
/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def
/CMapName /HBOSRegression def
/CMapType 2 def
1 begincodespacerange
<0000> <FFFF>
endcodespacerange
"""
_FOOTER = """endcmap
CMapName currentdict /CMap defineresource pop
end
end
"""


def _cmap(body):
    return _HEADER + body + _FOOTER


class InventoryPdfCMapTest(unittest.TestCase):
    def test_ascii_array_after_zero_range_is_byte_preserved(self):
        # Qt commonly emits a zero range before the actual character array.
        # Joining these two lines loses the latter range in pypdf's parser.
        marker = "R3QR-A R3QR-B-HIDDEN"
        targets = " ".join(f"<{ord(char):04X}>" for char in marker)
        original = _cmap(
            "2 beginbfrange\n<0000> <0000> <0000>\n"
            f"<0001> <{len(marker):04X}> [{targets}]\nendbfrange\n"
        )
        self.assertEqual(original, _TRANSFORM(original))

    def test_bfchar_preserves_source_cid_whitespace_and_crlf(self):
        original = _cmap(
            "2 beginbfchar\n\t<2F47>  <2F08>\n  <0002> <0041>\nendbfchar\n"
        ).replace("\n", "\r\n")
        expected = original.replace("<2F08>", "<4EBA>")
        self.assertEqual(expected, _TRANSFORM(original))

    def test_numeric_ranges_keep_separate_lines_and_only_change_targets(self):
        original = _cmap(
            "3 beginbfrange\n"
            "<2F08> <2F08> <0041>\n"
            "  <0001>\t<0001>  <2F47>\n"
            "<0002> <0002> <2EDB>\n"
            "endbfrange\n"
        )
        expected = original.replace("<2F47>", "<65E5>").replace("<2EDB>", "<98CE>")
        self.assertEqual(expected, _TRANSFORM(original))

    def test_array_between_numeric_ranges_retains_order_and_boundaries(self):
        original = _cmap(
            "3 beginbfrange\n"
            "<0000> <0000> <0000>\n"
            "<0001> <0003> [<0052> <2F08> <0041>]\n"
            "<2F47> <2F47> <2ECB>\n"
            "endbfrange\n"
        )
        expected = original.replace("<2F08>", "<4EBA>").replace("<2ECB>", "<8F66>")
        self.assertEqual(expected, _TRANSFORM(original))

    def test_independent_mapping_blocks_and_nonmapping_text_are_preserved(self):
        original = _cmap(
            "% Keep source-like text <2F08> outside mappings intact.\n"
            "1 beginbfchar\n<0001> <2F08>\nendbfchar\n"
            "1 beginbfrange\n<0002> <0003> [<0041> <0042>]\nendbfrange\n"
            "1 beginbfrange\n<0004> <0004> <2ECB>\nendbfrange\n"
        )
        expected = original.replace("<0001> <2F08>", "<0001> <4EBA>")
        expected = expected.replace("<0004> <0004> <2ECB>", "<0004> <0004> <8F66>")
        self.assertEqual(expected, _TRANSFORM(original))

    def test_normalization_is_idempotent(self):
        original = _cmap(
            "2 beginbfrange\n<0000> <0000> <0000>\n"
            "<0001> <0003> [<0052> <2F08> <2ECB>]\nendbfrange\n"
        )
        expected = original.replace("<2F08>", "<4EBA>").replace("<2ECB>", "<8F66>")
        self.assertEqual(expected, _TRANSFORM(_TRANSFORM(original)))


if __name__ == "__main__":
    unittest.main()
