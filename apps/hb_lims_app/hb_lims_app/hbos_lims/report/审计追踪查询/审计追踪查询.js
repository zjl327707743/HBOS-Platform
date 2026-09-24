// Copyright (c) 2026, HBOS and contributors
// For license information, please see license.txt

frappe.query_reports["审计追踪查询"] = {
	"filters": [
		{
			"fieldname": "result",
			"label": __("结果记录"),
			"fieldtype": "Link",
			"options": "HBOS Test Result",
		},
		{
			"fieldname": "changed_by",
			"label": __("修改人"),
			"fieldtype": "Link",
			"options": "User",
		},
		{
			"fieldname": "from_date",
			"label": __("修改时间从"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "to_date",
			"label": __("修改时间至"),
			"fieldtype": "Date",
		},
	],
};
