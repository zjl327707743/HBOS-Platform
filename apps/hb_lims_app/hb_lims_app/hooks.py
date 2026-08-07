app_name = "hb_lims_app"
app_title = "HBOS LIMS"
app_icon = "assets/hb_lims_app/hbos-lims-logo.svg"
app_publisher = "HBOS"
app_description = "HBOS Laboratory Information Management System (M2-LIMS)"
app_email = "admin@example.com"
app_license = "GPL-3.0"
required_apps = ["frappe"]
after_migrate = "hb_lims_app.hbos_lims.setup.after_migrate"
app_include_css = "/assets/hb_lims_app/css/lims_report.css"
app_include_js = "/assets/hb_lims_app/js/lims_report.js"
# Frappe v16.26.3 侧边栏 DocType 项过滤 bug workaround：
# desk/doctype/workspace_sidebar/workspace_sidebar.py 的 get_can_read_items() 缺 return，
# 导致 user_perm_can_read 缓存恒为 None，非 Administrator 用户侧边栏 DocType 项全部不可见。
# 在 boot 阶段按用户预置该缓存，恢复原生权限语义（不修改 Frappe 核心源码）。
boot_session = "hb_lims_app.hbos_lims.setup.sync_user_perm_can_read_cache"
