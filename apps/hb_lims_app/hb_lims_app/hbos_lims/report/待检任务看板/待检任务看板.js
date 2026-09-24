// Copyright (c) 2026, HBOS and contributors
// For license information, please see license.txt

frappe.query_reports["待检任务看板"] = {
	"filters": [
		{
			"fieldname": "lab_department",
			"label": __("检验组"),
			"fieldtype": "Link",
			"options": "HBOS Lab Department",
		},
		{
			"fieldname": "status",
			"label": __("状态"),
			"fieldtype": "Select",
			"options": "\n待分配\n已分配\n检验中\n已提交\n已复核\n已批准\nOOS候选\nOOS锁定",
		},
		{
			"fieldname": "assignee",
			"label": __("检验员"),
			"fieldtype": "Link",
			"options": "User",
		},
		{
			"fieldname": "priority",
			"label": __("优先级"),
			"fieldtype": "Select",
			"options": "\n常规\n加急\n特急",
		},
	],
};
