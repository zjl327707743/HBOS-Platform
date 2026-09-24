frappe.query_reports["效期预警"] = {
	filters: [
		{
			fieldname: "within_days",
			label: __("预警天数（剩余不足）"),
			fieldtype: "Int",
			default: 90,
			description: __("列出生效期在 N 天内的批次"),
		},
		{
			fieldname: "include_expired",
			label: __("含已过期"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "warehouse",
			label: __("货位"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "item_code",
			label: __("物料"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "release_status",
			label: __("放行状态"),
			fieldtype: "Select",
			options: "\n待检\n已放行\n不放行",
		},
	],
};
