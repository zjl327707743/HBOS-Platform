frappe.query_reports["考勤结果"] = {
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
			fieldname: "source_type",
			label: __("来源类型"),
			fieldtype: "Select",
			options: "\nHRMS Auto Attendance\nHBOS fallback\nMonthly Summary staging\nManual correction",
		},
		{
			fieldname: "hbos_only",
			label: __("只看 HBOS 标记数据"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
