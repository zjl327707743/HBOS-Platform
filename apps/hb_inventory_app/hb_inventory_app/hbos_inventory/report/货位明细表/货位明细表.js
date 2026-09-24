frappe.query_reports["货位明细表"] = {
	filters: [
		{
			fieldname: "warehouse",
			label: __("货位 / 库位"),
			fieldtype: "Link",
			options: "Warehouse",
			description: __("可填具体货位，也可填库位或层，配合下方勾选展开"),
		},
		{
			fieldname: "include_children",
			label: __("含下级货位"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "item_code",
			label: __("物料"),
			fieldtype: "Link",
			options: "Item",
		},
		{
			fieldname: "batch_no",
			label: __("批号"),
			fieldtype: "Data",
		},
	],
};
