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

# 批次表单上的「重新生成货位卡 / 待检证」按钮（自动生成失败或数据变更后补生成）
doctype_js = {"Batch": "public/js/batch.js"}

# Print Format 用的 Jinja 全局方法（打印辅助 + 货位二维码）。
# 注册机制会收集所列模块内的所有函数，故这些模块只 `import frappe`，
# 第三方依赖一律在函数内按需 import。
jinja = {
    "methods": [
        "hb_inventory_app.hbos_inventory.print_utils",
        "hb_inventory_app.hbos_inventory.qr_utils",
    ]
}
