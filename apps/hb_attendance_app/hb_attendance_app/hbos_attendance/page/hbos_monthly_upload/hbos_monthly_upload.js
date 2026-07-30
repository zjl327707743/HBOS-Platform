frappe.pages["hbos-monthly-upload"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("上传月度考勤表"),
		single_column: true,
	});

	page.set_title(__("上传月度考勤表"));

	$(frappe.render_template("hbos_monthly_upload", {})).appendTo(page.main);
};

frappe.pages["hbos-monthly-upload"].refresh = function (wrapper) {
	$("#hbos-upload-status").hide();
	$("#hbos-upload-result").hide();

	$("#hbos-upload-btn").off("click").on("click", function () {
		var file = $("#hbos-file-input")[0].files[0];
		if (!file) {
			frappe.msgprint(__("请先选择文件"));
			return;
		}

		var month = $("#hbos-upload-month").val();
		var year = $("#hbos-upload-year").val();

		$("#hbos-upload-status").show().find(".status-text").text(__("正在上传并解析..."));
		$("#hbos-upload-btn").prop("disabled", true);

		var formData = new FormData();
		formData.append("file", file);
		formData.append("month", month);
		formData.append("year", year || "2026");

		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_monthly_upload.upload.process_excel",
			args: {
				month: month,
				year: year || "2026",
			},
			type: "POST",
			always: function () {
				$("#hbos-upload-btn").prop("disabled", false);
			},
		});
	});

	// Actually use XMLHttpRequest for file upload
	$("#hbos-upload-btn").off("click").on("click", function () {
		var file = $("#hbos-file-input")[0].files[0];
		if (!file) {
			frappe.msgprint(__("请先选择文件"));
			return;
		}

		var month = $("#hbos-upload-month").val();
		var year = $("#hbos-upload-year").val();

		$("#hbos-upload-status").show().find(".status-text").text(__("正在上传并解析..."));
		$("#hbos-upload-btn").prop("disabled", true);

		var formData = new FormData();
		formData.append("file", file);
		formData.append("month", month);
		formData.append("year", year || "2026");
		formData.append("cmd", "hb_attendance_app.hbos_attendance.page.hbos_monthly_upload.upload.process_excel");

		// Add CSRF token
		formData.append("csrf_token", frappe.csrf_token);

		$.ajax({
			url: "/api/method/hb_attendance_app.hbos_attendance.page.hbos_monthly_upload.upload.process_excel",
			type: "POST",
			data: formData,
			processData: false,
			contentType: false,
			headers: {
				"X-Frappe-CSRF-Token": frappe.csrf_token,
			},
			success: function (response) {
				$("#hbos-upload-status").hide();
				$("#hbos-upload-btn").prop("disabled", false);

				var msg = response.message;
				$("#hbos-result-employees").text(msg.employees || 0);
				$("#hbos-result-checkins").text(msg.checkins || 0);
				$("#hbos-result-attendance").text(msg.attendance || 0);
				$("#hbos-result-late").text(msg.late || 0);
				$("#hbos-result-absent").text(msg.absent || 0);
				$("#hbos-upload-result").show();

				// Add link to summary report
				$("#hbos-goto-summary").off("click").on("click", function () {
					frappe.set_route("query-report", "月度考勤汇总", {
						month: month,
						year: year,
					});
				});
			},
			error: function (xhr) {
				$("#hbos-upload-status").hide();
				$("#hbos-upload-btn").prop("disabled", false);
				var err = "上传失败";
				try {
					var resp = JSON.parse(xhr.responseText);
					if (resp._server_messages) {
						err = JSON.parse(resp._server_messages)[0];
					} else if (resp.exc || resp.exception) {
						err = resp.exc || resp.exception;
					}
				} catch (e) {}
				frappe.msgprint(__(err));
			},
		});
	});
};

// HTML template
frappe.templates["hbos_monthly_upload"] = `
<div style="max-width: 600px; margin: 40px auto;">
	<div class="card">
		<div class="card-body">
			<h5>{{ __("上传原始考勤表") }}</h5>
			<p class="text-muted">{{ __("支持考勤机导出的月度汇总 Excel 文件。系统将自动匹配员工、识别班次、判定迟到/早退/缺勤。") }}</p>

			<div class="form-group">
				<label>{{ __("月份") }}</label>
				<select id="hbos-upload-month" class="form-control">
					<option value="1">1月</option>
					<option value="2">2月</option>
					<option value="3">3月</option>
					<option value="4">4月</option>
					<option value="5">5月</option>
					<option value="6">6月</option>
					<option value="7" selected>7月</option>
					<option value="8">8月</option>
					<option value="9">9月</option>
					<option value="10">10月</option>
					<option value="11">11月</option>
					<option value="12">12月</option>
				</select>
			</div>

			<div class="form-group">
				<label>{{ __("年份") }}</label>
				<select id="hbos-upload-year" class="form-control">
					<option value="2025">2025</option>
					<option value="2026" selected>2026</option>
					<option value="2027">2027</option>
				</select>
			</div>

			<div class="form-group">
				<label>{{ __("选择文件 (.xlsx)") }}</label>
				<input type="file" id="hbos-file-input" class="form-control" accept=".xlsx">
			</div>

			<button id="hbos-upload-btn" class="btn btn-primary">
				{{ __("上传并生成考勤") }}
			</button>

			<div id="hbos-upload-status" style="display:none; margin-top:15px;">
				<div class="flex align-items-center">
					<div class="spinner" style="width:18px;height:18px;border:2px solid #ccc;border-top-color:#2490ef;border-radius:50%;animation:spin 0.8s linear infinite;"></div>
					<span class="status-text ml-2"></span>
				</div>
			</div>
		</div>
	</div>

	<div id="hbos-upload-result" class="card mt-4" style="display:none;">
		<div class="card-body">
			<h5>{{ __("处理完成") }}</h5>
			<table class="table table-bordered mt-3">
				<tr><td>{{ __("处理员工数") }}</td><td><strong id="hbos-result-employees">-</strong></td></tr>
				<tr><td>{{ __("打卡记录") }}</td><td><strong id="hbos-result-checkins">-</strong></td></tr>
				<tr><td>{{ __("考勤记录") }}</td><td><strong id="hbos-result-attendance">-</strong></td></tr>
				<tr><td>{{ __("迟到次数") }}</td><td><strong id="hbos-result-late">-</strong></td></tr>
				<tr><td>{{ __("缺勤天数") }}</td><td><strong id="hbos-result-absent">-</strong></td></tr>
			</table>
			<button id="hbos-goto-summary" class="btn btn-primary mt-2">
				{{ __("查看月度考勤汇总") }}
			</button>
		</div>
	</div>
</div>
`;
