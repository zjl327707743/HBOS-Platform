frappe.query_reports["月度考勤汇总"] = {
	filters: [
		{fieldname:"month",label:__("月份"),fieldtype:"Select",options:[{value:"1",label:"1月"},{value:"2",label:"2月"},{value:"3",label:"3月"},{value:"4",label:"4月"},{value:"5",label:"5月"},{value:"6",label:"6月"},{value:"7",label:"7月"},{value:"8",label:"8月"},{value:"9",label:"9月"},{value:"10",label:"10月"},{value:"11",label:"11月"},{value:"12",label:"12月"}],default:"7",reqd:1},
		{fieldname:"year",label:__("年份"),fieldtype:"Select",options:[{value:"2024",label:"2024"},{value:"2025",label:"2025"},{value:"2026",label:"2026"},{value:"2027",label:"2027"}],default:"2026",reqd:1},
		{fieldname:"employee",label:__("员工"),fieldtype:"Link",options:"Employee"},
		{fieldname:"department",label:__("部门"),fieldtype:"Link",options:"Department"},
		{fieldname:"from_date",label:__("开始日期"),fieldtype:"Date"},
		{fieldname:"to_date",label:__("结束日期"),fieldtype:"Date"},
	],

	formatter: function (value, row, column, data, default_formatter) {
		var detailFields = ["late_detail","early_detail","absent_detail","leave_detail"];
		if (column && column.fieldname && detailFields.indexOf(column.fieldname) !== -1) {
			if (!value || value.length === 0) return "";
			var parts = value.trim().split(/\s+/);
			var colors = {late_detail:"#e03636", early_detail:"#e86c13", absent_detail:"#999", leave_detail:"#36a64f"};
			var bg = colors[column.fieldname] || "#666";
			var html = '<div style="display:flex;flex-wrap:wrap;gap:2px;max-width:500px">';
			for (var i = 0; i < parts.length; i++) {
				html += '<span style="white-space:nowrap;font-size:11px;background:'+bg+';color:#fff;padding:1px 5px;border-radius:3px;margin:1px">' + parts[i] + '</span>';
			}
			html += '</div>';
			return html;
		}
		return default_formatter(value, row, column, data);
	},

	onload: function (report) {
		report.page.add_inner_button(__("上传原始考勤表"), function () { upload_monthly_excel(report); });
		report.page.add_inner_button(__("导出 Excel"), function () {
			var args = {
				month: report.get_filter_value("month"),
				year: report.get_filter_value("year"),
				employee: report.get_filter_value("employee"),
				department: report.get_filter_value("department"),
				from_date: report.get_filter_value("from_date"),
				to_date: report.get_filter_value("to_date"),
			};
			frappe.call({
				method: "hb_attendance_app.hbos_attendance.report.月度考勤汇总.export.export_xlsx",
				args: args,
				callback: function (r) {
					if (r.message) {
						window.open(r.message, "_blank");
					}
				},
			});
		});
	},
};

function upload_monthly_excel(report) {
	var inp = document.createElement("input");
	inp.type = "file"; inp.accept = ".xlsx";
	inp.onchange = function () {
		var file = this.files[0];
		if (!file) return;
		frappe.show_progress(__("上传中"), 0, __("正在处理..."));
		var fd = new FormData();
		fd.append("file", file);
		fd.append("month", report.get_filter_value("month") || "7");
		fd.append("year", report.get_filter_value("year") || "2026");
		fetch("/api/method/hb_attendance_app.hbos_attendance.page.hbos_monthly_upload.upload.process_excel", {
			method: "POST", body: fd,
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
		}).then(r => r.json()).then(resp => {
			frappe.hide_progress();
			var m = resp.message;
			frappe.msgprint({ title: __("上传成功"), indicator: "green",
				message: __("处理"+m.employees+"人，"+m.checkins+"条打卡，"+m.attendance+"条考勤。迟到"+m.late+"次，缺勤"+m.absent+"天"),
				primary_action: { label: __("刷新报表"), action: function () { report.refresh(); } }
			});
		}).catch(() => { frappe.hide_progress(); frappe.msgprint({ title: __("错误"), message: __("上传失败"), indicator: "red" }); });
	};
	inp.click();
}