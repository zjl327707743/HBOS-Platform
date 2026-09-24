// Copyright (c) 2026, HBOS and contributors
// For license information, please see license.txt

frappe.query_reports["检验结果清单"] = {
	"filters": [
		{
			"fieldname": "sample",
			"label": __("样品"),
			"fieldtype": "Link",
			"options": "HBOS Sample",
		},
		{
			"fieldname": "verdict",
			"label": __("判定"),
			"fieldtype": "Select",
			"options": "\n合格\n不合格\nOOS候选\n不适用\n无法判定",
		},
		{
			"fieldname": "result_status",
			"label": __("记录状态"),
			"fieldtype": "Select",
			"options": "\n草稿\n已提交\n已复核\n已批准\n已修订",
		},
		{
			"fieldname": "from_date",
			"label": __("提交日期从"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "to_date",
			"label": __("提交日期至"),
			"fieldtype": "Date",
		},
	],
};
