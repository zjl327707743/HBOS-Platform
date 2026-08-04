// Copyright (c) 2026, HBOS and contributors
// For license information, please see license.txt

frappe.query_reports["样品台账"] = {
	"filters": [
		{
			"fieldname": "sample_type",
			"label": __("样品类型"),
			"fieldtype": "Link",
			"options": "HBOS Sample Type",
		},
		{
			"fieldname": "status",
			"label": __("状态"),
			"fieldtype": "Select",
			"options": "\n草稿\n已登记\n检验中\n检验完成\n已放行\n已拒绝\nOOS锁定",
		},
		{
			"fieldname": "material_code",
			"label": __("物料编码"),
			"fieldtype": "Data",
		},
		{
			"fieldname": "from_date",
			"label": __("登记日期从"),
			"fieldtype": "Date",
		},
		{
			"fieldname": "to_date",
			"label": __("登记日期至"),
			"fieldtype": "Date",
		},
	],
};
