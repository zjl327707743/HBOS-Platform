from __future__ import annotations

"""拣货单提交 payload 契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

`toWireLocations()` 决定「哪几个字段真的落库」。少传字段**不会报错**，
但会在别处炸掉，且都很难从代码上看出来：

- **少 `stock_qty`**：`Pick List.set_item_locations()` 用 `item.stock_qty`
  （不是 `qty`）算「还剩多少要拣」。为 0 时 ERPNext 的
  `get_items_with_location_and_quantity` 里 `while remaining_stock_qty > 0`
  一次都不进 —— **「定位货位」会把未拣的行全删光、一行也不填**。
  实测：qty=4 的单据点一下就变成 0 行，货位静默丢失。
- **少 `uom`**：界面「单位」列读的就是它，不落库则保存后重开单位变空。

两者都是「服务端不会替你补、Desk 表单却会带上」的字段。这里把它们钉在
payload 里，防止哪天顺手删掉。
"""

import re
import unittest
from pathlib import Path

PICK_TS = (
    Path(__file__).parents[3]
    / "frontend"
    / "hbos-portal-web"
    / "src"
    / "services"
    / "inventoryPick.ts"
)


def _function_body(name: str) -> str:
    text = PICK_TS.read_text(encoding="utf-8")
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", text)
    if not match:
        raise AssertionError(f"inventoryPick.ts 里找不到函数 {name}")
    start = match.end()
    depth = 1
    i = start
    # 从参数表右括号后的第一个 '{' 开始配平
    brace = text.index("{", start)
    depth = 1
    i = brace + 1
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[brace : i]


class PickPayloadContractTest(unittest.TestCase):
    def test_wire_locations_sends_stock_qty(self):
        """必须带 `stock_qty`，否则「定位货位」会把行全删掉。"""
        body = _function_body("toWireLocations")
        self.assertRegex(
            body,
            r"stock_qty\s*:",
            "toWireLocations 必须显式带 stock_qty —— set_item_locations 用它算剩余量，"
            "缺了会让「定位货位」清空未拣行且一行不填",
        )

    def test_wire_locations_sends_uom(self):
        """必须带 `uom`，否则界面「单位」列保存后变空。"""
        body = _function_body("toWireLocations")
        self.assertRegex(
            body,
            r"\buom\s*:",
            "toWireLocations 必须带 uom —— 界面「单位」列读的就是它",
        )


if __name__ == "__main__":
    unittest.main()
