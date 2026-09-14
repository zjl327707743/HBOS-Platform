frappe.query_reports["库级盘点三对账"] = {
	filters: [
		{
			fieldname: "warehouse",
			label: __("库位"),
			fieldtype: "Link",
			options: "Warehouse",
			description: __("选库位（如 3904）或货位；配合下方勾选展开下级"),
		},
		{
			fieldname: "include_children",
			label: __("含下级"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "item_code",
			label: __("物料"),
			fieldtype: "Link",
			options: "Item",
		},
	],
};
