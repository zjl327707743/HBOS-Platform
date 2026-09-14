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
    },
}

# 打印辅助方法：整个模块的函数注册为 Jinja 全局方法，供 Print Format 直接调用。
jinja = {
    "methods": ["hb_inventory_app.hbos_inventory.print_utils"],
}
