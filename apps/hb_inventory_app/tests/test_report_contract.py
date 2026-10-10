from __future__ import annotations

"""报表筛选定义契约测试（纯静态断言，不需要 site 即可跑）。

## 为什么有这份测试

四张报表的**筛选定义**住在两处，必然重复：

- 报表的 `<报表>.js`（`frappe.query_reports["<报表名>"] = { filters: [...] }`）
  —— Desk 侧用，是**业务 Authority**；
- `frontend/hbos-portal-web/src/data/inventoryReports.ts`
  —— Portal 侧用；服务端**不提供读取接口**（`query_report.run` 的 `js_filters`
  参数是「客户端传上来做权限校验」，方向相反），所以前端只能自己声明一份。

重复本身躲不掉，但**漂移可以挡住**。这里断言两边的 `fieldname` 集合完全一致：
报表加/改一个筛选项而忘了同步前端，CI 直接红——而不是等 Owner 在页面上发现
「怎么少了一个筛选」。

这与 `test_workspace_contract.py` 守「入口必须可达」是同一个套路：
**把重复变成有测试兜底的重复。**

## 为什么用正则而不是 `js_filters` 接口去问服务端

问服务端要不到（理由见上）。这里读的是**仓库里的源文件**，与前端读的是同一份
真相来源，且测试在 CI 里跑得到——比运行时探测更早发现问题。
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
REPORT_DIR = ROOT / "hb_inventory_app" / "hbos_inventory" / "report"
PORTAL_DATA = (
    Path(__file__).parents[3]
    / "frontend"
    / "hbos-portal-web"
    / "src"
    / "data"
    / "inventoryReports.ts"
)

#: 报表名 → Portal 侧的 id。两边命名不同（Portal 用 kebab-case 走 URL，报表用中文名做主键）。
REPORTS = {
    "货位明细表": "location-detail",
    "效期预警": "expiry-warning",
    "按批号查货位": "batch-location",
    "库级盘点三对账": "stocktake",
}


#: ERPNext 自带报表的 .js 位置（在容器内的 bench 里；CI 里有挂载）
ERPNEXT_REPORT_JS = {
    "stock-balance": "stock/report/stock_balance/stock_balance.js",
}


def _external_report_js_fieldnames(portal_id: str) -> set[str]:
    """读 ERPNext 标准报表的 `.js` 里的筛选字段。

    找不到文件就返回空集 —— 由调用方断言「测试失效」，而不是静默放过。
    """
    rel = ERPNEXT_REPORT_JS.get(portal_id)
    if not rel:
        return set()
    for base in (
        Path("/home/frappe/frappe-bench/apps/erpnext/erpnext"),
        Path(__file__).parents[3] / "runtime" / "apps" / "erpnext" / "erpnext",
    ):
        path = base / rel
        if path.exists():
            source = path.read_text(encoding="utf-8")
            return set(re.findall(r"fieldname:\s*['\"]([^'\"]+)['\"]", source))
    return set()


def _js_fieldnames(report_name: str) -> set[str]:
    """从报表的 `<报表>.js` 里取 `fieldname:` 的值。"""
    path = REPORT_DIR / report_name / f"{report_name}.js"
    source = path.read_text(encoding="utf-8")
    return set(re.findall(r"fieldname:\s*['\"]([^'\"]+)['\"]", source))


def _ts_blocks() -> dict[str, str]:
    """把 `inventoryReports.ts` 按 `id: '<kebab-case>'` 切成块。

    **通用切块**，不认识具体的 id —— 旧写法只认 `REPORTS` 里那几个 id，
    于是数组字面量之外后来追加的报表（`stock-balance`）会被算进前一块的尾巴，
    报出「库级盘点三对账多出 from_date / to_date」这种假差异。

    只认形如 `id: 'kebab-case'` 的行；`reportName` 等其它键不会误命中。
    """
    source = PORTAL_DATA.read_text(encoding="utf-8")
    marks = [
        (m.start(), m.group(1))
        for m in re.finditer(r"^\s*id:\s*'([a-z0-9]+(?:-[a-z0-9]+)*)'", source, re.M)
    ]
    blocks: dict[str, str] = {}
    for i, (pos, report_id) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(source)
        blocks[report_id] = source[pos:end]
    return blocks


def _ts_fieldnames(report_id: str) -> set[str]:
    """从 `inventoryReports.ts` 里取该报表的 `fieldname:` 值。"""
    block = _ts_blocks().get(report_id)
    if block is None:
        return set()
    return set(re.findall(r"fieldname:\s*'([^']+)'", block))


class InventoryReportFilterContractTest(unittest.TestCase):
    def test_every_report_has_a_js_definition(self):
        for report_name in REPORTS:
            with self.subTest(report=report_name):
                path = REPORT_DIR / report_name / f"{report_name}.js"
                self.assertTrue(path.exists(), f"缺少 {path}")
                self.assertTrue(_js_fieldnames(report_name), "报表 .js 里没有筛选项？")

    def test_portal_declares_exactly_the_same_filter_fields(self):
        """两边的筛选字段集合必须**完全一致**——多一个少一个都算漂移。

        多：前端声明了报表不认的字段（传过去会被忽略，用户以为筛选生效了却没生效）。
        少：报表有但前端没给入口（用户没法用）。
        两种都是真问题，所以用相等而不是包含。
        """
        for report_name, report_id in REPORTS.items():
            with self.subTest(report=report_name):
                js_fields = _js_fieldnames(report_name)
                ts_fields = _ts_fieldnames(report_id)
                self.assertEqual(
                    js_fields,
                    ts_fields,
                    f"「{report_name}」的筛选项与 Portal 侧不一致："
                    f"报表多出 {sorted(js_fields - ts_fields)}，"
                    f"Portal 多出 {sorted(ts_fields - js_fields)}",
                )

    #: Portal 为「库存余额」声明的筛选项，**冻结于此**。
    #:
    #: 来源：2026-09-25 从 ERPNext `stock/report/stock_balance/stock_balance.js`
    #: （v16）**人工转录**，只取了仓管真会用的子集。
    #:
    #: 为什么不直接去读上游那份 `.js`：**ERPNext 源码在镜像里，本机与 CI 的
    #: 宿主机上都读不到**（`runtime/apps` 只挂了 hrms）。读不到就没法在 CI 里
    #: 守护这条路 —— 所以改成冻结一份期望值。
    #:
    #: **升级 ERPNext 时必须回来核对这份清单**（文件名、字段名都可能变）。
    #: 这条测试挡不住「上游改了而这份没跟上」，但它挡得住「Portal 侧被人改坏」，
    #: 并把「该人工核对」这件事记在了代码里而不是某个人的脑子里。
    STOCK_BALANCE_FILTERS = frozenset({
        "from_date",
        "to_date",
        "warehouse",
        "item_code",
        "item_group",
        "include_zero_stock_items",
    })

    def test_stock_balance_keeps_the_frozen_filter_subset(self):
        """「库存余额」的筛选项必须正好是冻结的那 6 个。

        **为什么是「正好相等」而不是「只要够用」**：
        多一个 = 有人加了个上游不认（或仓管用不上）的字段，会静默失效；
        少一个 = 有人删了必填的 `from_date` / `to_date`，报表会因缺参报错。
        两个方向都是真问题。

        上游若有变，先跑一次：

        ```bash
        docker compose exec backend cat \\
          /home/frappe/frappe-bench/apps/erpnext/erpnext/stock/report/stock_balance/stock_balance.js
        ```

        核对后再改这里的冻结清单。
        """
        ts_fields = _ts_fieldnames("stock-balance")
        self.assertEqual(
            set(self.STOCK_BALANCE_FILTERS),
            ts_fields,
            "库存余额的 Portal 筛选项与冻结清单不一致。"
            "若是有意改动，请先核对 ERPNext 上游并同步更新 "
            "STOCK_BALANCE_FILTERS 的注释（含核对日期）。",
        )

    def test_upstream_report_js_is_checked_when_reachable(self):
        """宿主机能读到 ERPNext 源码时（例如挂了 runtime 挂载），顺带核一次上游。

        读不到就 **skip**，并说明原因——**不假装验过**。
        """
        js_fields = _external_report_js_fieldnames("stock-balance")
        if not js_fields:
            self.skipTest(
                "ERPNext 源码不在宿主机上（在容器镜像里），无法核对上游；"
                "改由 test_stock_balance_keeps_the_frozen_filter_subset 守 Portal 侧"
            )

        invented = _ts_fieldnames("stock-balance") - js_fields
        self.assertEqual(
            set(),
            invented,
            f"Portal 声明了 Stock Balance 不认的筛选字段：{sorted(invented)}",
        )

    def test_portal_report_ids_are_url_safe(self):
        """id 会进 URL 路径段，必须是 kebab-case 且不含特殊字符。"""
        for report_id in REPORTS.values():
            with self.subTest(report_id=report_id):
                self.assertRegex(report_id, r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_default_values_match_between_sides(self):
        """默认值也要一致——否则同一个报表在 Desk 和 Portal 打开是不同的结果集。

        **比的是语义，不是字面量**：报表 `.js` 里 Check 型的默认值是 `default: 1`，
        Portal 侧写的是 `defaultChecked: true`——同一个意思的两种表达。
        拿字面量硬比会误报（第一版就是这么错的）。

        规范化后统一成：
          - Check：「勾选」/「不勾选」
          - 其它：数值字面量
        """
        for report_name, report_id in REPORTS.items():
            with self.subTest(report=report_name):
                js_path = REPORT_DIR / report_name / f"{report_name}.js"
                js_source = js_path.read_text(encoding="utf-8")
                ts_source = PORTAL_DATA.read_text(encoding="utf-8")

                for block in _js_filter_blocks(js_source):
                    field = block["fieldname"]
                    js_default = _canonical_js_default(block)
                    if js_default is None:
                        continue  # 报表没写默认值 —— 容器侧也不该编一个

                    field_pos = ts_source.find(f"fieldname: '{field}'")
                    self.assertGreater(field_pos, -1, f"Portal 侧缺少字段 {field}")
                    # 窗口必须**止于下一个 fieldname**：否则会读成下一个字段的默认值
                    # （第一版固定取 400 字符，把 include_expired 的 defaultChecked 读给了
                    #  within_days，报出「90 != 勾选」这种假差异）。
                    nxt = ts_source.find("fieldname:", field_pos + 1)
                    window = ts_source[field_pos : nxt if nxt > 0 else len(ts_source)]

                    ts_default = _canonical_ts_default(window, block.get("fieldtype", ""))
                    self.assertEqual(
                        js_default,
                        ts_default,
                        f"「{report_name}.{field}」默认值两边不一致："
                        f"报表 = {js_default}，Portal = {ts_default}",
                    )


def _js_filter_blocks(source: str) -> list[dict[str, str]]:
    """把报表 `.js` 里每个 filter 对象的键值抠出来。

    这些对象是**单层**的（没有嵌套），所以按花括号切块足够；不需要引 JS 解析器。
    """
    blocks = []
    for raw in re.findall(r"\{([^{}]*fieldname:[^{}]*)\}", source, re.S):
        entry: dict[str, str] = {}
        for key, value in re.findall(r"(\w+):\s*['\"]?([^,'\"\n}]+)", raw):
            entry[key] = value.strip()
        if entry.get("fieldname"):
            blocks.append(entry)
    return blocks


def _canonical_js_default(block: dict[str, str]) -> str | None:
    """把报表 `.js` 的默认值规范化成语义串。没写默认值就返回 None。"""
    if "default" not in block:
        return None
    value = block["default"]
    if block.get("fieldtype") == "Check":
        return "勾选" if value not in {"0", "false"} else "不勾选"
    return value


def _canonical_ts_default(window: str, js_fieldtype: str) -> str | None:
    """把 Portal 侧该字段窗口里的默认值规范化成语义串。

    **按 fieldtype 只找对应的那个属性**：Check 找 `defaultChecked`，其余找 `defaultValue`。
    两个都试会让 Check 字段误读成相邻字段的数值。
    """
    if js_fieldtype == "Check":
        checked = re.search(r"defaultChecked:\s*(true|false)", window)
        if not checked:
            return None
        return "勾选" if checked.group(1) == "true" else "不勾选"

    value = re.search(r"defaultValue:\s*([0-9.]+)", window)
    return value.group(1) if value else None


if __name__ == "__main__":
    unittest.main()


class ReportEmptyScopeTest(unittest.TestCase):
    """空货位范围**必须**返回空结果，不能拼出 `in ()`。

    ## 缺陷与修法

    两张报表（货位明细表、库级盘点三对账）都用同一套 `_warehouse_scope`：

        scope = _warehouse_scope(filters)
        if scope is not None:
            placeholders = ", ".join(f"%(wh_{i})s" for i in range(len(scope)))
            conditions.append(f"sbe.warehouse in ({placeholders})")

    `include_children` 勾上、而货位名又拼错（或该库位下没有子货位）时，`scope` 是
    **空列表**——`placeholders` 拼出来是空串，SQL 变成 `sbe.warehouse in ()`，
    MariaDB 报语法错误，报表以 500 收场。

    用户看到的因此是「报表没跑起来」，而事实是「这个货位没有库存」。
    **把空结果误报成故障，与把故障误报成空结果是同一类错误**，都让人做出错判断。

    ## 这些断言为什么是静态的

    `execute()` 要连库（`frappe.db.sql`），在无 site 的 CI 里跑不起来。
    所以这里断言**源码结构**：空 scope 的早退分支必须存在，且位置在拼 SQL 之前。
    """

    #: 共享同一套 `_warehouse_scope` 的两张报表
    SCOPE_REPORTS = ("货位明细表", "库级盘点三对账")

    def _source(self, report_name: str) -> str:
        return (REPORT_DIR / report_name / f"{report_name}.py").read_text(encoding="utf-8")

    def test_empty_scope_returns_early(self):
        for report_name in self.SCOPE_REPORTS:
            with self.subTest(report=report_name):
                source = self._source(report_name)
                self.assertIn(
                    "if scope is not None and not scope:",
                    source,
                    f"「{report_name}」缺少「空范围 → 空结果」的早退分支；"
                    f"货位名拼错时报表会 500 而不是返回空",
                )

    def test_early_return_precedes_placeholder_building(self):
        """早退必须在**拼占位符之前**——放在后面等于没放。"""
        for report_name in self.SCOPE_REPORTS:
            with self.subTest(report=report_name):
                source = self._source(report_name)
                guard = source.index("if scope is not None and not scope:")
                build = source.index("placeholders = ")
                self.assertLess(
                    guard,
                    build,
                    f"「{report_name}」的空范围判断在拼接 SQL 之后，起不到保护作用",
                )

    def test_early_return_yields_columns_and_no_rows(self):
        """空结果仍要给出列定义——否则前端拿不到表头，连空表都画不出来。"""
        for report_name in self.SCOPE_REPORTS:
            with self.subTest(report=report_name):
                source = self._source(report_name)
                self.assertIn("return _columns(), []", source)

    def test_single_value_warehouse_reports_are_not_affected(self):
        """另两张用单值相等（`sbe.warehouse = %(warehouse)s`），不拼 IN，天然没有这个坑。

        记录这条是为了说清「为什么只改两张」——免得后来者以为漏改了两张。
        """
        for report_name in ("效期预警", "按批号查货位"):
            with self.subTest(report=report_name):
                source = self._source(report_name)
                self.assertNotIn("_warehouse_scope", source)
