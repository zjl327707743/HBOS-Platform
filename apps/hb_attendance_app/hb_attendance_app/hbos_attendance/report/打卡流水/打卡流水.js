frappe.query_reports["打卡流水"] = {
	filters: [
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
			fieldname: "employee",
			label: __("员工"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "department",
			label: __("部门"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "import_log",
			label: __("HBOS 导入批次"),
			fieldtype: "Link",
			options: "HBOS Attendance Import Log",
		},
		{
			fieldname: "source_device",
			label: __("来源设备"),
			fieldtype: "Data",
		},
		{
			fieldname: "hbos_only",
			label: __("只看 HBOS 导入/适配数据"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
