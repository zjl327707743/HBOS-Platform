frappe.query_reports["HBOS 月度汇总暂存（对账）"] = {
	filters: [
		{
			fieldname: "import_log",
			label: __("HBOS 导入批次"),
			fieldtype: "Link",
			options: "HBOS Attendance Import Log",
		},
		{
			fieldname: "from_date",
			label: __("开始日期"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("结束日期"),
			fieldtype: "Date",
		},
		{
			fieldname: "department",
			label: __("部门"),
			fieldtype: "Data",
		},
		{
			fieldname: "employee_number",
			label: __("工号"),
			fieldtype: "Data",
		},
	],
};
