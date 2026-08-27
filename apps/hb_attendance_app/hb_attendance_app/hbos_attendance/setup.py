import frappe
import json
from pathlib import Path

MODULE = "HBOS Attendance"
WORKSPACE_TITLE = "海滨考勤工作台"
DESKTOP_LABEL = "海滨考勤"
DESKTOP_LOGO_URL = "/assets/hb_attendance_app/hbos-attendance-logo.svg"
# HRMS 界面汉化：覆盖官方翻译与补漏（源文本 → 中文译文）。
HRMS_ZH_TRANSLATIONS = {
    "Frappe HR": "海滨HR",
    "Tenure": "任职",
    "Expenses": "费用报销",
    "HR Setup": "HR 设置",
}
PRIMARY_SIDEBAR_ITEMS = [
	{"label": "导入考勤机导出表", "link_type": "Page", "link_to": "hbos-attendance-import", "type": "Link", "icon": "upload"},
	{"label": "考勤异常仪表盘", "link_type": "Page", "link_to": "hbos-attendance-dashboard", "type": "Link", "icon": "dashboard"},
	{"label": "考勤导入日志", "link_type": "DocType", "link_to": "HBOS Attendance Import Log", "type": "Link", "icon": "list"},
	{"label": "飞书请假记录", "link_type": "DocType", "link_to": "HBOS Leave Record", "type": "Link", "icon": "leave"},
	{"label": "飞书加班记录", "link_type": "DocType", "link_to": "HBOS Overtime Record", "type": "Link", "icon": "clock"},
	{"label": "HBOS 打卡流水", "link_type": "Report", "link_to": "打卡流水", "type": "Link", "icon": "clock"},
	{"label": "HBOS 考勤结果", "link_type": "Report", "link_to": "考勤结果", "type": "Link", "icon": "calendar-check"},
	{"label": "月度考勤汇总", "link_type": "Report", "link_to": "月度考勤汇总", "type": "Link", "icon": "milestone"},
	{"label": "月度汇总 / 对账暂存", "link_type": "Report", "link_to": "HBOS 月度汇总暂存（对账）", "type": "Link", "icon": "clipboard-list"},
]


def after_migrate():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({
        "Employee Checkin": [
            {"fieldname": "hbos_source_type", "label": "HBOS 来源类型", "fieldtype": "Select",
             "options": "HBOS raw checkin import\nHBOS monthly adapter\nHRMS native / existing", "read_only": 1},
            {"fieldname": "hbos_import_log", "label": "HBOS 导入批次", "fieldtype": "Link",
             "options": "HBOS Attendance Import Log", "read_only": 1},
            {"fieldname": "hbos_calc_version", "label": "HBOS 计算版本", "fieldtype": "Data", "read_only": 1},
        ],
        "Attendance": [
            {"fieldname": "hbos_source_type", "label": "HBOS 来源类型", "fieldtype": "Select",
             "options": "HRMS Auto Attendance\nHBOS fallback\nMonthly Summary staging\nManual correction", "read_only": 1},
            {"fieldname": "hbos_import_log", "label": "HBOS 导入批次", "fieldtype": "Link",
             "options": "HBOS Attendance Import Log", "read_only": 1},
            {"fieldname": "hbos_fallback_generated", "label": "HBOS 兜底生成", "fieldtype": "Check", "read_only": 1},
            {"fieldname": "hbos_calc_version", "label": "HBOS 计算版本", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "hbos_raw_reference", "label": "HBOS 原始引用", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "hbos_missing_out", "label": "HBOS 缺下班卡", "fieldtype": "Check", "read_only": 1},
        ]
    })
    sync_attendance_workspace()
    apply_hr_localization()
    fix_hr_setup_groups()
    reorder_hr_icon()


def fix_hr_setup_groups():
    """修复「HR 设置」里 Setup / Settings 两个分组都被译成「设置」的问题。

    HRMS 原版 HR Setup 的 Card Break「Setup」「Settings」在中文翻译里都是「设置」，
    造成两个同名分组。这里直接把分组名改为中文「组织架构」「系统设置」（幂等）。
    """
    if not frappe.db.exists("Workspace", "HR Setup"):
        return
    rename = {"Setup": "组织架构", "Settings": "系统设置"}
    doc = frappe.get_doc("Workspace", "HR Setup")

    for link in doc.get("links"):
        if link.get("type") == "Card Break" and link.get("label") in rename:
            link.set("label", rename[link.get("label")])

    try:
        content = json.loads(doc.content) if isinstance(doc.content, str) else doc.content
    except (TypeError, ValueError):
        content = []
    for card in content:
        card_name = card.get("data", {}).get("card_name") if isinstance(card.get("data"), dict) else None
        if card.get("type") == "card" and card_name in rename:
            card["data"]["card_name"] = rename[card_name]
    doc.content = json.dumps(content)

    doc.save(ignore_permissions=True)


def reorder_hr_icon():
    """把「海滨考勤」「海滨HR」排到最前两个，其余图标恢复各 App 原始顺序。

    海滨考勤 idx=-2、海滨HR（Frappe HR）idx=-1（负数确保排最前、且不与
    其他 App 图标的 idx 冲突）；其余图标从各 App 的 desktop_icon fixture 读回
    原始 idx，恢复安装时的默认顺序。
    """
    import os
    import glob

    if frappe.db.exists("Desktop Icon", "海滨考勤"):
        frappe.db.set_value("Desktop Icon", "海滨考勤", "idx", -2)
    if frappe.db.exists("Desktop Icon", "Frappe HR"):
        frappe.db.set_value("Desktop Icon", "Frappe HR", "idx", -1)

    for app in frappe.get_installed_apps():
        icon_dir = os.path.join(frappe.get_app_path(app), "desktop_icon")
        if not os.path.isdir(icon_dir):
            continue
        for f in glob.glob(os.path.join(icon_dir, "*.json")):
            try:
                with open(f) as fp:
                    d = json.load(fp)
            except (OSError, ValueError):
                continue
            label = d.get("label")
            if not label or label in ("海滨考勤", "Frappe HR"):
                continue
            if frappe.db.exists("Desktop Icon", label):
                frappe.db.set_value("Desktop Icon", label, "idx", d.get("idx", 0))


def localize_app_data(bootinfo):
    """把 boot 数据里 hrms 的 app_title 改为「海滨HR」。

    Frappe 侧边栏副标题（header_subtitle）直接读 boot.app_data 的 app_title，
    不走翻译，因此需在 boot_session 阶段覆盖。其余显示点（桌面图标 label 等）走翻译，
    已由 apply_hr_localization 处理。
    """
    for app in getattr(bootinfo, "app_data", None) or []:
        if app.get("app_name") == "hrms":
            app["app_title"] = "海滨HR"


def apply_hr_localization():
    """HRMS 汉化与「Frappe HR」→「海滨HR」改名。

    通过 Frappe Custom Translation 机制写入，不修改 HRMS 第三方源码；
    clone 后执行 migrate 即自动生效（幂等，可重复执行）。
    """
    from frappe.translate import clear_cache, update_translations_for_source

    for source, translated in HRMS_ZH_TRANSLATIONS.items():
        update_translations_for_source(source, json.dumps({"zh": translated}))

    # 编译 HRMS 自带中文翻译（.po → .mo），使「班次与考勤」「假期列表」等原生翻译生效。
    # hrms 未安装（get-app 未执行）时 .po 不存在，函数内部静默跳过。
    try:
        from frappe.gettext.translate import _compile_translation

        _compile_translation("hrms", "zh")
    except Exception:
        frappe.log_error("HRMS 中文翻译编译失败", "hrms_localization")

    clear_cache()


def sync_attendance_workspace():
	"""以版本化 fixture 和运行态派生对象收敛海滨考勤入口。"""
	fixture = Path(__file__).parent / "workspace" / WORKSPACE_TITLE / f"{WORKSPACE_TITLE}.json"
	payload = json.loads(fixture.read_text())
	workspace = frappe.get_doc("Workspace", payload["name"]) if frappe.db.exists("Workspace", payload["name"]) else frappe.new_doc("Workspace")
	for field in ("app", "content", "icon", "is_hidden", "label", "module", "public", "sequence_id", "title", "type"):
		workspace.set(field, payload[field])
	for field in ("links", "roles", "shortcuts"):
		workspace.set(field, payload[field])
	workspace.save(ignore_permissions=True)
	_sync_sidebar(DESKTOP_LABEL)
	_sync_sidebar(WORKSPACE_TITLE)
	_sync_desktop_icon()
	_hide_stale_workspace_desktop_icon()


def _sync_sidebar(title):
	sidebar = frappe.get_doc("Workspace Sidebar", title) if frappe.db.exists("Workspace Sidebar", title) else frappe.new_doc("Workspace Sidebar")
	sidebar.title = title
	sidebar.header_icon = "calendar-check"
	sidebar.module = MODULE
	sidebar.standard = 0
	sidebar.app = ""
	sidebar.set("items", [_sidebar_home_item(), *PRIMARY_SIDEBAR_ITEMS])
	sidebar.save(ignore_permissions=True)


def _sidebar_home_item():
	return {"label": "海滨考勤工作台", "link_type": "Workspace", "link_to": WORKSPACE_TITLE, "type": "Link", "icon": "home"}


def _sync_desktop_icon():
	icon = frappe.get_doc("Desktop Icon", DESKTOP_LABEL) if frappe.db.exists("Desktop Icon", DESKTOP_LABEL) else frappe.new_doc("Desktop Icon")
	icon.label = DESKTOP_LABEL
	icon.icon_type = "Link"
	icon.link_type = "Workspace Sidebar"
	icon.link_to = DESKTOP_LABEL
	icon.sidebar = DESKTOP_LABEL
	icon.icon = "calendar-check"
	icon.logo_url = DESKTOP_LOGO_URL
	icon.icon_image = DESKTOP_LOGO_URL
	icon.bg_color = "blue"
	icon.hidden = 0
	icon.idx = 0
	icon.restrict_removal = 1
	icon.save(ignore_permissions=True)


def _hide_stale_workspace_desktop_icon():
	if frappe.db.exists("Desktop Icon", WORKSPACE_TITLE):
		stale_icon = frappe.get_doc("Desktop Icon", WORKSPACE_TITLE)
		stale_icon.hidden = 0
		stale_icon.parent_icon = DESKTOP_LABEL
		stale_icon.icon = "calendar-check"
		stale_icon.logo_url = DESKTOP_LOGO_URL
		stale_icon.icon_image = DESKTOP_LOGO_URL
		stale_icon.bg_color = "blue"
		stale_icon.save(ignore_permissions=True)
