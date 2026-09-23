/* 全局：把仓库常用单据的「面包屑归属」指到仓库工作台
 *
 * ## 解决什么
 *
 * 从仓库工作台点进「库存单据」（原生 Stock Entry）后，左上角面包屑只有
 * `🏠 / 物料移动`，**看不到「仓库工作台」** —— 看着就像跳进了原生库存模块。
 *
 * ## 为什么只加 `Workspace Shortcut` 不够
 *
 * 我先在工作台上给这几个单据加了 `Workspace Shortcut`（那是
 * `FormMeta.load_workspaces()` 决定 `__workspaces` 的来源）。**数据是对了**
 * （实测 `__workspaces == ['仓库工作台']`），但**主路径上仍然不显示**。
 * 读 `breadcrumbs.js` 才看清：`set_workspace()` 分两条互斥支路，
 *
 *   - 从工作台点进来（`last_route[0] === "Workspaces"`）→ 要求
 *     `breadcrumbs.module` 有值，**且**该模块的工作台列表里含当前工作台；
 *   - 直接开 URL / 从列表点进表单 → 用 `__workspaces[0]`。
 *
 * `Stock Entry` 的 module 是 `Stock`，而「仓库工作台」属于 `HBOS Inventory`，
 * 所以第一条支路**永远匹配不上** —— 而 Owner 走的正是这条。
 *
 * ## 办法：框架自己的扩展点
 *
 * `breadcrumbs.preferred` 就是干这个的（**按单据指定它该挂到哪个模块**），
 * 而且 ERPNext 自己就在用——见 `erpnext/public/js/conf.js`：
 *
 *     $.extend(frappe.breadcrumbs.preferred, {
 *         "Item Group": "Stock", Brand: "Stock", ...
 *     });
 *
 * 所以这里照抄同一个写法。它排在 `erpnext.bundle.js` 之后执行（app 顺序），
 * 两边写的是不同的 doctype 键，互不覆盖。
 *
 * ## 边界（说清楚，别当成万能）
 *
 * - 这**不影响单据本身**，只影响面包屑怎么画；
 * - **没法改的**：单据自己的 `module` 字段是 ERPNext 的数据（`Stock Entry` →
 *   顺带一提，它的中文名「物料移动」也是 ERPNext 的翻译，要改得用 Custom
 *   Translation）；
 * - 从**原生库存模块或搜索框**主动进去，`last_workspace` 不是仓库工作台，
 *   这条支路仍然不显示 —— 那是「主动绕路」，不在本文件职责内。
 */

(function () {
	// app_include_js 按 app 顺序加载，本 app 排在 frappe / erpnext 之后，
	// 此时 desk.bundle.js 已定义好 frappe.breadcrumbs；仍然防一手，
	// 免得将来顺序变化后**静默失效**（这类"不报错但不生效"的坑本分支已踩过多次）。
	const apply = () => {
		if (!window.frappe || !frappe.breadcrumbs || !frappe.breadcrumbs.preferred) return false;
		$.extend(frappe.breadcrumbs.preferred, {
			"Stock Entry": "HBOS Inventory",
			Batch: "HBOS Inventory",
			Item: "HBOS Inventory",
			Warehouse: "HBOS Inventory",
		});
		return true;
	};

	if (!apply()) {
		$(document).ready(apply);
	}
})();
