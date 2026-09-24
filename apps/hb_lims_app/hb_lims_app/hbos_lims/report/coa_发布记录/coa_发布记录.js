// Copyright (c) 2026, HBOS and contributors
// For license information, please see license.txt

frappe.query_reports["COA 发布记录"] = {
	"filters": [
		{
			"fieldname": "report_status",
			"label": __("报告状态"),
			"fieldtype": "Select",
			"options": "\n草稿\n已审核\n已发布",
		},
		{
			"fieldname": "sample",
			"label": __("样品"),
			"fieldtype": "Link",
			"options": "HBOS Sample",
		},
		{
			"fieldname": "published_by",
			"label": __("发布人"),
			"fieldtype": "Link",
			"options": "User",
		},
	],
};
