/* 全局：把仓库常用单据的「面包屑归属」和「侧边栏归属」都指到仓库工作台
 *
 * 这两件事机制不同，都由本文件负责（挂在 `app_include_js`，见 hooks.py）。
 *
 * ## 一、面包屑归属（`frappe.breadcrumbs.preferred`）
 *
 * 从仓库工作台点进「库存单据」（原生 Stock Entry）后，左上角面包屑只有
 * `🏠 / 物料移动`，**看不到「仓库工作台」** —— 看着就像跳进了原生库存模块。
 *
 * 只加 `Workspace Shortcut` 不够：那只决定 `__workspaces`，而
 * `breadcrumbs.js` 的 `set_workspace()` 里，**从工作台点进来**那条支路要求
 * doctype 的 module 能映射到该工作台 —— `Stock Entry` 的 module 是 `Stock`、
 * 仓库工作台属于 `HBOS Inventory`，永远匹配不上。
 *
 * `breadcrumbs.preferred` 就是干这个的（**按单据指定它该挂到哪个模块**），
 * 而且 ERPNext 自己就在用——见 `erpnext/public/js/conf.js` 的
 * `$.extend(frappe.breadcrumbs.preferred, { "Item Group": "Stock", ... })`。
 *
 * ## 二、侧边栏归属（`localStorage["sidebar_item_map"]`）
 *
 * `sidebar.js` 的 `resolve_sidebar()` 有四级规则：
 *
 *   1. 当前侧边栏已链接该单据 → 保持不变
 *   2. 这个单据**上次用的侧边栏**（读 localStorage `sidebar_item_map`）
 *   3. （空）
 *   4. 按 `module_app[module]` 过滤候选，再挑
 *
 * SPA 内跳转时规则 1 生效，够用；**但整页刷新时当前侧边栏是空的**，
 * 直接落到规则 4 —— `Stock Entry` 的 module 是 `Stock`，候选只剩 erpnext
 * 那几条，于是掉回原生「库存」。
 *
 * Owner 报的「点『打开草稿』就跳到库存下了」就是这么来的：那个按钮原本是
 * `<a href>`，**href 是整页刷新**。（页面里已改成 `frappe.set_route` 的 SPA 跳转，
 * 但浏览器地址栏直接粘 URL、F5 刷新这类还是会走硬加载。）
 *
 * 所以这里把规则 2 需要的数据先种上。缓存里的键是 `{单据或条目名: [侧边栏]}`，
 * 而 `resolve_sidebar()` 查的是**单据名**（`entity_from_route` 取 route[1]）。
 *
 * ⚠ **注意写入方用的是另一个键空间**：框架自己的
 * `store_last_show_sidebar_for_item()` 写的是 `data-id`，即**侧边栏条目的 label**
 * （见 `sidebar_item.html`）——我们这些 label 都是中文，与单据名不会撞。
 *
 * ## 边界（说清楚，别当成万能）
 *
 * - 只影响面包屑怎么画与侧边栏选哪个，**不影响单据本身**；
 * - 单据自己的 `module` 字段是 ERPNext 的数据（`Stock Entry` → 顺带一提，
 *   它的中文名「物料移动」也是 ERPNext 的翻译，要改得用 Custom Translation）；
 * - 从**原生库存模块或搜索框**主动进去，上下文就是原生的，本文件不接管。
 */

(function () {
	// 仓库日常会用到的原生单据 —— 用于两处。
	// 范围与 `workspace_setup.py` 的 SIDEBAR_ITEMS 保持一致。
	// 报表不在此列：query-report 的面包屑只显示报表标题，不走工作台前缀。
	const DOCTYPES = [
		"Stock Entry",
		"Purchase Receipt",
		"Delivery Note",
		"Material Request",
		"Pick List",
		"Stock Reconciliation",
		"Quality Inspection",
		"Batch",
		"Item",
		"Warehouse",
		"UOM",
	];
	const MODULE = "HBOS Inventory";
	const SIDEBAR = "仓库工作台";

	// app_include_js 按 app 顺序加载，本 app 排在 frappe / erpnext 之后，
	// 此时 desk.bundle.js 已定义好 frappe.breadcrumbs；仍然防一手，
	// 免得将来顺序变化后**静默失效**（这类"不报错但不生效"的坑本分支已踩过多次）。
	const apply = () => {
		if (!window.frappe || !frappe.breadcrumbs || !frappe.breadcrumbs.preferred) return false;

		// ① 面包屑归属
		const preferred = {};
		for (const dt of DOCTYPES) preferred[dt] = MODULE;
		$.extend(frappe.breadcrumbs.preferred, preferred);

		// ② 侧边栏归属（**整页刷新 / 直接粘 URL 时用**）
		//
		// `sidebar.js` 的 `resolve_sidebar()` 规则 1 是「当前侧边栏已链接该单据
		// → 保持不变」——那在 SPA 内跳转时够用，但**整页刷新时当前侧边栏是空的**，
		// 于是走到规则 4：按 `module_app[module]` 过滤候选。
		// `Stock Entry` 的 module 是 `Stock` → 只剩 erpnext 那几条 → 掉回原生「库存」。
		//
		// 规则 2 是「这个单据上次用的是哪个侧边栏」（读 localStorage
		// `sidebar_item_map`，格式 `{单据: [侧边栏, ...]}`）。这里先种上，
		// 刷新后直接命中规则 2、不再走规则 4。
		try {
			const KEY = "sidebar_item_map";
			const map = JSON.parse(localStorage.getItem(KEY) || "{}");
			let changed = false;
			for (const dt of DOCTYPES) {
				if ((map[dt] || [])[0] !== SIDEBAR) {
					map[dt] = [SIDEBAR];
					changed = true;
				}
			}
			if (changed) localStorage.setItem(KEY, JSON.stringify(map));
		} catch (e) {
			// localStorage 不可用（隐私模式等）时不阻断——面包屑那半仍然生效
			console.warn("[hbos] sidebar_item_map 无法写入", e);
		}

		return true;
	};

	if (!apply()) {
		$(document).ready(apply);
	}
})();
