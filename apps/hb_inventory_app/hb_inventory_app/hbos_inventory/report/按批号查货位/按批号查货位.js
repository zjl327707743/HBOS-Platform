frappe.query_reports["按批号查货位"] = {
	filters: [
		{
			fieldname: "batch_no",
			label: __("批号"),
			fieldtype: "Data",
			description: __("支持模糊匹配；外购物料可输入原厂批号后按结果核对"),
		},
		{
			fieldname: "item_code",
			label: __("物料"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "warehouse",
			label: __("货位"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "release_status",
			label: __("放行状态"),
			fieldtype: "Select",
			options: "\n待检\n已放行\n不放行",
		},
	],
};
