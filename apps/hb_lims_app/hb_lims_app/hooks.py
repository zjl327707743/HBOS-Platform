app_name = "hb_lims_app"
app_title = "HBOS LIMS"
app_icon = "assets/hb_lims_app/hbos-lims-logo.svg"
app_publisher = "HBOS"
app_description = "HBOS Laboratory Information Management System (M2-LIMS)"
app_email = "admin@example.com"
app_license = "GPL-3.0"
required_apps = ["frappe", "erpnext"]
after_migrate = "hb_lims_app.hbos_lims.setup.after_migrate"
app_include_css = "/assets/hb_lims_app/css/lims_report.css?v=2"
app_include_js = [
	"/assets/hb_lims_app/js/lims_report.js?v=2",
	"/assets/hb_lims_app/js/lims_list_resize.js?v=2",
	"/assets/hb_lims_app/js/lims_grid_resize.js?v=2",
]
# Frappe v16.26.3 侧边栏 DocType 项过滤 bug workaround：
# desk/doctype/workspace_sidebar/workspace_sidebar.py 的 get_can_read_items() 缺 return，
# 导致 user_perm_can_read 缓存恒为 None，非 Administrator 用户侧边栏 DocType 项全部不可见。
# 在 boot 阶段按用户预置该缓存，恢复原生权限语义（不修改 Frappe 核心源码）。
boot_session = "hb_lims_app.hbos_lims.setup.sync_user_perm_can_read_cache"

# HBOS LIMS 独立 Vue 前端的正式同源入口。
# 根路由由 www/hbos-lims.html 提供；history-mode 深链接统一回写到同一壳页，
# 再由 Vue Router 在浏览器端接管。Frappe v16 的 website_route_rules 支持
# <path:...> 捕获多段路径，因此 /hbos-lims/tasks、/hbos-lims/stability/... 均可硬刷新。
website_route_rules = [
	{"from_route": "/hbos-lims/<path:app_path>", "to_route": "hbos-lims"},
]

# 合规审计日志：全量 doc_events 捕获（创建/修改/删除），write-once
doc_events = {
	"HBOS Sample": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Sample Task": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Test Result": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS COA": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Specification": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Sample Type": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Test Item": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# M2-R7 留样板块（write-once 全量捕获）
	"HBOS Retention Product": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Retention Sample": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# R7B 观察记录
	"HBOS Retention Observation": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# R7C 使用/处理申请
	"HBOS Retention Usage Apply": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Retention Disposal Apply": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# M2-R8A 稳定性板块（write-once 全量捕获；子表随父单变更，不单独注册）
	"HBOS Stability Product": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Condition": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Room": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Test Item": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Notice": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Protocol": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# M2-R8B 样品与时间点（子表随父单变更，不单独注册）
	"HBOS Stability Sample": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Timepoint": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# M2-R8C 结果与报告
	"HBOS Stability Result": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Report": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# M2-R8D 变更、稳定性室与设备
	"HBOS Stability Change": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Room Log": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Equipment": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	"HBOS Stability Fault Ticket": {
		"after_insert": "hb_lims_app.hbos_lims.lims_service.audit_on_insert",
		"on_update": "hb_lims_app.hbos_lims.lims_service.audit_on_update",
		"on_trash": "hb_lims_app.hbos_lims.lims_service.audit_on_trash",
	},
	# 稳定性专项报告引用的客户：命名规范强制校验（方案 5.4.2；仅作用于已引用客户）
	"Customer": {
		"validate": "hb_lims_app.hbos_lims.stability_guards.validate_customer_code",
	},
}

# R7C：销毁超期 / 到期提醒派生扫描（cron 每日 00:30 服务器本地；纯派生不改状态，见方案 8.3）
scheduler_events = {
	"cron": {
		"30 0 * * *": [
			"hb_lims_app.hbos_lims.retention_service.scheduler_scan",
			"hb_lims_app.hbos_lims.stability_service.scheduler_scan",
		],
	},
}
