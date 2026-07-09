import frappe


WORKSPACE_CONTENT = (
	'[{"id":"hbos-import-header","type":"header","data":{"text":"<span style=\\"font-size: 18px;\\"><b>导入与结果</b></span>","col":12}},'
	'{"id":"hbos-import-card","type":"card","data":{"card_name":"导入与结果","col":4}},'
	'{"id":"hbos-attendance-card","type":"card","data":{"card_name":"中文考勤视图","col":4}},'
	'{"id":"hbos-hrms-card","type":"card","data":{"card_name":"HRMS 原始对象","col":4}}]'
)


def after_migrate():
	sync_attendance_workspace()


def sync_attendance_workspace():
	if frappe.db.exists("Workspace", "海滨考勤工作台"):
		workspace = frappe.get_doc("Workspace", "海滨考勤工作台")
	else:
		workspace = frappe.new_doc("Workspace")
		workspace.name = "海滨考勤工作台"
		workspace.label = "海滨考勤工作台"
	workspace.update(
		{
			"app": "hb_attendance_app",
			"title": "海滨考勤工作台",
			"module": "HBOS Attendance",
			"icon": "calendar",
			"type": "Workspace",
			"public": 1,
			"is_hidden": 0,
			"content": WORKSPACE_CONTENT,
		}
	)
	workspace.set(
		"roles",
		[
			{"role": "System Manager"},
			{"role": "HR Manager"},
			{"role": "HR User"},
		],
	)
	workspace.set(
		"links",
		[
			{"type": "Card Break", "label": "导入与结果", "link_count": 2},
			{
				"type": "Link",
				"label": "导入考勤机导出表",
				"link_type": "Page",
				"link_to": "hbos-attendance-import",
				"onboard": 1,
			},
			{
				"type": "Link",
				"label": "导入日志",
				"link_type": "DocType",
				"link_to": "HBOS Attendance Import Log",
				"onboard": 1,
			},
			{"type": "Card Break", "label": "中文考勤视图", "link_count": 2},
			{
				"type": "Link",
				"label": "打卡流水",
				"link_type": "Report",
				"link_to": "打卡流水",
				"is_query_report": 1,
			},
			{
				"type": "Link",
				"label": "考勤结果",
				"link_type": "Report",
				"link_to": "考勤结果",
				"is_query_report": 1,
			},
			{"type": "Card Break", "label": "HRMS 原始对象", "link_count": 2},
			{"type": "Link", "label": "原始打卡记录", "link_type": "DocType", "link_to": "Employee Checkin"},
			{"type": "Link", "label": "出勤记录", "link_type": "DocType", "link_to": "Attendance"},
		],
	)
	workspace.set(
		"shortcuts",
		[
			{"type": "Page", "label": "导入考勤机导出表", "link_to": "hbos-attendance-import", "color": "Blue"},
			{
				"type": "DocType",
				"label": "导入日志",
				"link_to": "HBOS Attendance Import Log",
				"doc_view": "List",
				"color": "Blue",
			},
			{"type": "Report", "label": "打卡流水", "link_to": "打卡流水", "color": "Green"},
			{"type": "Report", "label": "考勤结果", "link_to": "考勤结果", "color": "Orange"},
		],
	)
	workspace.save(ignore_permissions=True)
