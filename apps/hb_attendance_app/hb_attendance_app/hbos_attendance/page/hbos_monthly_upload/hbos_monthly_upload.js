frappe.pages["hbos-monthly-upload"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("上传月度考勤表"),
		single_column: true,
	});
	// HBOS 共享样式层的挂载点：只影响本容器内部，Desk 框架不受影响。
	$(wrapper).addClass("hbos-surface");

	page.set_title(__("上传月度考勤表"));

	// 样式只声明本页结构；色值、圆角一律走 var(--h-*)（由
	// hbos_attendance.bundle.css 在 .hbos-surface 下定义），不写死。
	// 字号只取契约 v2.0 允许的 30 / 20 / 16 / 14 / 12。
	//
	// 强度：本页是**表单 + 回执**，按 V1 处理——实色面板、无动效。
	// 布局用「投入 | 产出」两栏而非居中的窄卡片：居中窄卡是营销页的形状，
	// 而且会把结果挤到屏幕下方；两栏让「选了什么」与「得到了什么」同屏可见，
	// 也与同族的导入页保持同一骨架。
	$("<style id='mu-style'>").text(
		".mu-heading{margin-bottom:16px;}" +
		".mu-heading h1{margin:6px 0 4px;font-size:30px;line-height:38px;font-weight:600;color:var(--h-text);}" +
		".mu-heading p{margin:0;font-size:14px;line-height:22px;color:var(--h-text-2);max-width:64ch;}" +

		".mu-layout{display:grid;grid-template-columns:minmax(0,380px) minmax(0,1fr);gap:16px;align-items:start;}" +
		".mu-panel{background:var(--h-surface-solid);border:1px solid var(--h-border);border-radius:var(--h-radius-card);padding:20px;}" +
		".mu-panel h2{margin:0 0 16px;font-size:16px;line-height:24px;font-weight:600;color:var(--h-text);}" +

		".mu-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;}" +
		".mu-field{display:flex;flex-direction:column;gap:4px;margin-bottom:14px;}" +
		".mu-field label{font-size:12px;line-height:20px;color:var(--h-text-2);margin:0;}" +
		".mu-field .form-control{font-size:14px;}" +
		".mu-actions{display:flex;align-items:center;gap:12px;margin-top:4px;}" +

		".mu-status{display:none;align-items:center;gap:8px;margin-top:14px;font-size:14px;line-height:22px;color:var(--h-text-2);}" +
		".mu-spin{width:16px;height:16px;border:2px solid var(--h-border-strong);border-top-color:var(--h-brand);border-radius:50%;animation:mu-spin .8s linear infinite;}" +
		"@keyframes mu-spin{to{transform:rotate(360deg);}}" +

		".mu-defs{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:0 20px;border-top:1px solid var(--h-border);}" +
		".mu-def{display:flex;flex-direction:column;gap:2px;padding:10px 0;border-bottom:1px solid var(--h-border);}" +
		".mu-def .k{font-size:12px;line-height:20px;color:var(--h-muted);}" +
		".mu-def .v{font-size:30px;line-height:38px;font-weight:600;color:var(--h-text);font-variant-numeric:tabular-nums;}" +
		".mu-hint{padding:24px 0;font-size:14px;line-height:22px;color:var(--h-muted);}" +
		".mu-note{margin:14px 0 0;font-size:12px;line-height:20px;color:var(--h-muted);}" +
		"@media (max-width:900px){.mu-layout{grid-template-columns:1fr;}}"
	).appendTo("head");

	$(frappe.render_template("hbos_monthly_upload", {})).appendTo(page.main);
};

frappe.pages["hbos-monthly-upload"].refresh = function (wrapper) {
	$("#hbos-upload-status").hide();
	// 回执面板不清空为空白：空态本身要说明「这里会出现什么」，
	// 否则用户看到一块什么都没有的牌子，不知道是坏了还是还没跑。
	resetResult();

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

				renderResult(response.message, month, year);
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

function resetResult() {
	$("#hbos-upload-result").html(
		'<h2>本次处理结果</h2>' +
		'<div class="mu-hint">上传并解析后，这里显示本次处理的员工数、打卡记录、考勤记录以及迟到与缺勤统计。</div>'
	);
}

// 五个计数一律走 tabular-nums 的大数字——这是本页唯一的 V2 时刻（结果回执），
// 也是唯一允许出现 30px 的地方。明细留白由「查看月度考勤汇总」承接。
function renderResult(msg, month, year) {
	msg = msg || {};
	var def = function (label, value) {
		return '<div class="mu-def"><span class="k">' + frappe.utils.escape_html(String(label)) +
			'</span><span class="v">' + frappe.utils.escape_html(String(value)) + "</span></div>";
	};
	$("#hbos-upload-result").html(
		"<h2>本次处理结果</h2>" +
		'<div class="mu-defs">' +
			def("处理员工数", msg.employees || 0) +
			def("打卡记录", msg.checkins || 0) +
			def("考勤记录", msg.attendance || 0) +
			def("迟到次数", msg.late || 0) +
			def("缺勤天数", msg.absent || 0) +
		"</div>" +
		'<div class="mu-actions" style="margin-top:16px;">' +
			'<button id="hbos-goto-summary" class="btn btn-default btn-sm">查看月度考勤汇总</button>' +
		"</div>"
	);
	$("#hbos-goto-summary").on("click", function () {
		frappe.set_route("query-report", "月度考勤汇总", { month: month, year: year });
	});
}

// HTML template
frappe.templates["hbos_monthly_upload"] = `
<div class="mu-heading">
	<div class="hbos-breadcrumb">海滨考勤工作台 / 上传月度考勤表</div>
	<h1>上传月度考勤表</h1>
	<p>支持考勤机导出的月度汇总 Excel。系统自动匹配员工、识别班次并判定迟到、早退与缺勤。</p>
</div>

<div class="mu-layout">
	<section class="mu-panel">
		<h2>选择文件</h2>
		<div class="mu-grid">
			<div class="mu-field">
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
			<div class="mu-field">
				<label>{{ __("年份") }}</label>
				<select id="hbos-upload-year" class="form-control">
					<option value="2025">2025</option>
					<option value="2026" selected>2026</option>
					<option value="2027">2027</option>
				</select>
			</div>
		</div>

		<div class="mu-field">
			<label>{{ __("Excel 文件") }}</label>
			<input type="file" id="hbos-file-input" class="form-control" accept=".xlsx">
		</div>

		<div class="mu-actions">
			<button id="hbos-upload-btn" class="btn btn-primary btn-sm">
				{{ __("上传并生成考勤") }}
			</button>
		</div>

		<div id="hbos-upload-status" class="mu-status">
			<span class="mu-spin"></span>
			<span class="status-text"></span>
		</div>

		<p class="mu-note">月度汇总表与逐条打卡流水的处理口径不同：本页写入的是月度暂存，逐条流水请用「导入考勤机导出表」。</p>
	</section>

	<section class="mu-panel" id="hbos-upload-result">
		<h2>本次处理结果</h2>
		<div class="mu-hint">上传并解析后，这里显示本次处理的员工数、打卡记录、考勤记录以及迟到与缺勤统计。</div>
	</section>
</div>
`;
