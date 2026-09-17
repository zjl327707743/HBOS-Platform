"""stock 站点初始化：创建公司主体与默认仓库。

幂等：已存在则跳过。通过
    bench --site stock execute hb_stock_app.hbos_stock.init_site.run
调用。

前置说明（本轮回测确认）：`stock` 站点由 `bench new-site` + `install-app erpnext`
建成，**从未跑过 ERPNext 的 setup wizard**，因此 ERPNext 建站主数据（`Warehouse
Type` / `UOM` / `Item Group` / `Party Type` …）一条都没有。而 ERPNext 的
`Company.on_update -> create_default_warehouses()` 会为「Goods In Transit」仓写死
`warehouse_type="Transit"`（`erpnext/setup/doctype/company/company.py`），该条只由
`erpnext.setup.setup_wizard.operations.install_fixtures.install()`（setup wizard 第 2
阶段）创建，**不在 `install-app erpnext` 里**。故本脚本在建公司前，先用 ERPNext
原生装配器补齐建站主数据。

该装配器落库走 `make_records()` ->
`frappe/desk/page/setup_wizard/setup_wizard.py`，实现为
`doc.insert(ignore_permissions=True, ignore_if_duplicate=True)` 包在 savepoint 里、
失败回滚，**设计上幂等**。本脚本仍把它整体门控在「`Warehouse Type` 为空」之下：
避免重复执行时无条件触碰 `update_selling_defaults()` / `update_buying_defaults()`
里的 `.save()`，也让「幂等」在脚本层面显式成立。

本脚本只调用 ERPNext 原生 DocType / 原生函数，不新建 DocType、不重写库存逻辑。
"""

import frappe

COMPANY = "HAIBIN"
ABBR = "H"
COUNTRY = "China"
CURRENCY = "CNY"

# 建站主数据存在性探针。选 `Warehouse Type` 是因为它只由 setup wizard 装配器创建，
# 且恰是 `Company.on_update` 建默认仓库路径的硬依赖（`Transit`）。
MASTER_DATA_PROBE = "Warehouse Type"


def _ensure_setup_master_data():
	"""仅当建站主数据缺失时，用 ERPNext 原生装配器补齐。返回是否本次补齐。"""
	if frappe.db.count(MASTER_DATA_PROBE):
		return False

	from erpnext.setup.setup_wizard.operations import install_fixtures

	savepoint = "hbos_stock_setup_fixtures"
	frappe.db.savepoint(savepoint)
	try:
		install_fixtures.install(COUNTRY)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise

	frappe.db.commit()
	return True


def run():
	"""创建 HAIBIN 公司；ERPNext 会随之自动建默认仓库与会计科目。"""
	master_data_created = _ensure_setup_master_data()

	created = False
	if not frappe.db.exists("Company", COMPANY):
		savepoint = "hbos_stock_company"
		frappe.db.savepoint(savepoint)
		try:
			company = frappe.new_doc("Company")
			company.company_name = COMPANY
			company.abbr = ABBR
			company.country = COUNTRY
			company.default_currency = CURRENCY
			company.insert(ignore_permissions=True)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			raise
		created = True

	frappe.db.commit()

	warehouses = [w.name for w in frappe.get_all(
		"Warehouse", filters={"company": COMPANY}, fields=["name"], order_by="name")]
	accounts = frappe.db.count("Account", {"company": COMPANY})
	price_lists = frappe.db.count("Price List")
	print(
		f"company={COMPANY} created={created} master_data_created={master_data_created} "
		f"warehouses={len(warehouses)} accounts={accounts} price_lists={price_lists}"
	)
	print(f"warehouses={warehouses}")
	return {"company": COMPANY, "warehouses": warehouses}
