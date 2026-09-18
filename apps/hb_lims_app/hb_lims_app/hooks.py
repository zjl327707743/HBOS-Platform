app_name = "hb_lims_app"
app_title = "HBOS LIMS"
app_icon = "assets/hb_lims_app/hbos-lims-logo.svg"
app_publisher = "HBOS"
app_description = "HBOS Laboratory Information Management System (M2-LIMS)"
app_email = "admin@example.com"
app_license = "GPL-3.0"
required_apps = ["frappe"]
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
}

# R7C：销毁超期 / 到期提醒派生扫描（cron 每日 00:30 服务器本地；纯派生不改状态，见方案 8.3）
scheduler_events = {
	"cron": {
		"30 0 * * *": [
			"hb_lims_app.hbos_lims.retention_service.scheduler_scan",
		],
	},
}
