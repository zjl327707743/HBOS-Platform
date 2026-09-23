app_name = "hb_inventory_app"
app_title = "HBOS Inventory"
app_publisher = "HBOS"
app_description = "HBOS warehousing and inventory master data"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext"]

after_migrate = "hb_inventory_app.hbos_inventory.setup.after_migrate"

# 出库放行门禁：出库须有 QA 放行手续与合格证（Owner 确认的业务规则）。
# 挂 before_submit 而非 validate，使草稿仍可自由保存修改。
doc_events = {
    "Delivery Note": {
        "before_submit": "hb_inventory_app.hbos_inventory.release_gate.validate_release",
    },
    "Stock Entry": {
        "before_submit": "hb_inventory_app.hbos_inventory.release_gate.validate_release",
        # 入库提交后自动生成「待检证 + 货位卡」并挂到批次附件。
        # 挂 on_submit 而非生成草稿时——货位卡依赖真实库存流水（SLE），
        # 而 ERPNext 的 on_submit 先建 SLE，我们的钩子在其后跑。详见 doc_gen.py。
        "on_submit": "hb_inventory_app.hbos_inventory.doc_gen.generate_for_stock_entry",
    },
}

# 表单上的自定义行为：
# - Batch：「重新生成货位卡 / 待检证」按钮 + 「返回仓库工作台」出口
# - Stock Entry：提交后给落点 + 「返回仓库工作台」出口
doctype_js = {
    "Batch": "public/js/batch.js",
    "Stock Entry": "public/js/stock_entry.js",
}

# 全局脚本：把仓库常用单据的面包屑指到仓库工作台。
#
# 挂 app_include_js 而不是 doctype_js——它要在 **Desk 启动时**就把表填好，
# 而不是等某个表单打开。本 app 排在 frappe / erpnext 之后，届时
# `frappe.breadcrumbs.preferred` 已存在。详见该文件头部注释。
#
# ⚠ 路径**必须写成 `/assets/<app>/...` 的绝对形式**：非 bundle 文件在
# `bundled_asset()` 里查不到映射，会原样交给 `abs_url()`；给相对路径
# 它只会在前面补一个 `/`（`public/js/x.js` → `/public/js/x.js`），那是 404。
app_include_js = "/assets/hb_inventory_app/js/desk_context.js"

# Print Format 用的 Jinja 全局方法（打印辅助 + 货位二维码）。
# 注册机制会收集所列模块内的所有函数，故这些模块只 `import frappe`，
# 第三方依赖一律在函数内按需 import。
jinja = {
    "methods": [
        "hb_inventory_app.hbos_inventory.print_utils",
        "hb_inventory_app.hbos_inventory.qr_utils",
    ]
}
