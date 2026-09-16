app_name = "hb_stock_app"
app_title = "海滨库存"
app_publisher = "HBOS"
app_description = "海滨独立库存：复用 ERPNext 原生库存单据与报表，与考勤站点数据隔离"
app_email = "admin@example.com"
app_license = "MIT"
required_apps = ["frappe", "erpnext"]

after_migrate = "hb_stock_app.hbos_stock.setup.after_migrate"
