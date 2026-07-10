frappe.pages["hbos-attendance-import"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "导入考勤机导出表",
		single_column: true,
	});

	const state = {
		sourceFile: null,
		logName: null,
		preview: null,
		result: null,
	};
	const escapeHtml =
		(frappe.utils && frappe.utils.escape_html) ||
		function (value) {
			return String(value)
				.replace(/&/g, "&amp;")
				.replace(/</g, "&lt;")
				.replace(/>/g, "&gt;")
				.replace(/"/g, "&quot;")
				.replace(/'/g, "&#039;");
		};

	$(page.body).html(`
		<div class="hbos-import-page">
			<div class="hbos-import-heading">
				<div>
					<div class="hbos-breadcrumb">海滨考勤工作台 / 导入考勤机导出表</div>
					<p class="text-muted">海滨考勤复用 HRMS 的员工、打卡和考勤结果数据；本页面负责考勤机 Excel 导入并汇入 HBOS 中文报表主线。</p>
				</div>
				<button class="btn btn-default" data-route="Workspaces/海滨考勤工作台">返回海滨考勤工作台</button>
			</div>
			<div class="hbos-import-toolbar">
				<input class="hbos-file-input hidden" type="file" accept=".xlsx" />
				<button class="btn btn-primary" data-action="choose-file">上传原始表格</button>
				<button class="btn btn-default" data-action="preview" disabled>识别并预览</button>
				<button class="btn btn-success" data-action="run" disabled>确认导入</button>
			</div>
			<div class="hbos-import-layout">
				<section class="hbos-panel">
					<h4>文件与识别</h4>
					<div class="hbos-file-state text-muted">尚未选择 Excel 文件。</div>
					<div class="hbos-preview-state"></div>
				</section>
				<section class="hbos-panel">
					<h4>导入结果</h4>
					<div class="hbos-result-state text-muted">完成预览后可确认导入。</div>
				</section>
			</div>
			<div class="hbos-links">
					<button class="btn btn-default" data-route="List/HBOS Attendance Import Log">查看考勤导入日志</button>
					<button class="btn btn-default" data-route="query-report/打卡流水">查看 HBOS 打卡流水</button>
					<button class="btn btn-default" data-route="query-report/考勤结果">查看 HBOS 考勤结果</button>
			</div>
		</div>
		<style>
			.hbos-import-page { padding: 16px 0 32px; }
			.hbos-import-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
			.hbos-breadcrumb { font-weight: 600; margin-bottom: 4px; }
			.hbos-import-toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
			.hbos-import-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
			.hbos-panel { border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; background: var(--fg-color); min-height: 220px; }
			.hbos-panel h4 { margin: 0 0 12px; font-size: 16px; }
			.hbos-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }
			.hbos-metric { border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 10px; }
			.hbos-metric .label { color: var(--text-muted); font-size: 12px; }
			.hbos-metric .value { font-weight: 600; margin-top: 2px; word-break: break-word; }
			.hbos-links { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
			@media (max-width: 900px) { .hbos-import-heading { flex-direction: column; } .hbos-import-layout { grid-template-columns: 1fr; } }
		</style>
	`);

	const $body = $(page.body);
	const $fileInput = $body.find(".hbos-file-input");

	$body.find("[data-action='choose-file']").on("click", () => $fileInput.trigger("click"));
	$body.find("[data-action='preview']").on("click", () => previewImport());
	$body.find("[data-action='run']").on("click", () => runImport());
	$body.find("[data-route]").on("click", function () {
		frappe.set_route($(this).attr("data-route").split("/"));
	});
	$fileInput.on("change", async function () {
		if (!this.files || !this.files.length) return;
		await uploadFile(this.files[0]);
	});

	async function uploadFile(file) {
		if (!file.name.toLowerCase().endsWith(".xlsx")) {
			frappe.msgprint("请上传 .xlsx 格式的考勤机月度导出表。");
			return;
		}
		const formData = new FormData();
		formData.append("file", file);
		formData.append("is_private", "1");
		formData.append("folder", "Home/Attachments");
		formData.append("doctype", "HBOS Attendance Import Log");
		frappe.dom.freeze("正在上传原始表格...");
		try {
			const response = await fetch("/api/method/upload_file", {
				method: "POST",
				headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
				body: formData,
			});
			const payload = await response.json();
			if (!response.ok || payload.exc) {
				throw new Error(payload._server_messages || payload.exc || "上传失败");
			}
			state.sourceFile = payload.message.file_url;
			state.logName = null;
			state.preview = null;
			state.result = null;
			$body.find(".hbos-file-state").html(`<b>已上传：</b>${escapeHtml(file.name)}`);
			$body.find("[data-action='preview']").prop("disabled", false);
			$body.find("[data-action='run']").prop("disabled", true);
			renderPreview(null);
			renderResult(null);
		} catch (error) {
			frappe.msgprint(`上传失败：${escapeHtml(error.message)}`);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	async function previewImport() {
		if (!state.sourceFile) return;
		frappe.dom.freeze("正在识别表格...");
		try {
			const response = await frappe.call({
				method: "hb_attendance_app.hbos_attendance.doctype.hbos_attendance_import_log.hbos_attendance_import_log.preview_import",
				args: { source_file: state.sourceFile },
			});
			state.preview = response.message;
			state.logName = response.message.log_name;
			renderPreview(state.preview);
			$body.find("[data-action='run']").prop("disabled", false);
		} finally {
			frappe.dom.unfreeze();
		}
	}

	async function runImport() {
		if (!state.sourceFile) return;
		frappe.confirm("确认导入当前考勤机月度导出表？系统会自动跳过已存在的打卡流水。", async () => {
			frappe.dom.freeze("正在导入...");
			try {
				const response = await frappe.call({
					method: "hb_attendance_app.hbos_attendance.doctype.hbos_attendance_import_log.hbos_attendance_import_log.run_import",
					args: { source_file: state.sourceFile, log_name: state.logName, create_missing_employees: 1 },
				});
				state.result = response.message;
				state.logName = response.message.log_name;
				renderResult(state.result);
				frappe.show_alert({ message: "导入完成，可查看导入日志、打卡流水和考勤结果。", indicator: "green" });
			} finally {
				frappe.dom.unfreeze();
			}
		});
	}

	function renderPreview(data) {
		const $target = $body.find(".hbos-preview-state");
		if (!data) {
			$target.html("");
			return;
		}
		const mapping = data.mapping_summary || {};
		$target.html(`
			<div class="hbos-metrics">
				${metric("识别类型", data.import_type)}
				${metric("日期范围", `${data.period_start || "-"} 至 ${data.period_end || "-"}`)}
				${metric("员工行数", mapping.identity_rows || 0)}
				${metric("日期列数", (mapping.daily_columns || []).length)}
				${metric("表头行", mapping.header_row || "-")}
				${metric("默认班次", "白班/行政班 08:30-17:30")}
			</div>
			<p class="text-muted" style="margin-top: 12px;">当前支持：考勤机月度导出表。后续适配：逐条原始打卡流水表。</p>
		`);
	}

	function renderResult(data) {
		const $target = $body.find(".hbos-result-state");
		if (!data) {
			$target.html('<span class="text-muted">完成预览后可确认导入。</span>');
			return;
		}
		$target.html(`
			<div class="hbos-metrics">
				${metric("批次号", data.log_name)}
				${metric("新增打卡流水", data.created_checkins || 0)}
				${metric("跳过重复记录", data.skipped_duplicates || 0)}
				${metric("新增考勤结果", data.created_attendance || 0)}
				${metric("已存在考勤结果", data.existing_attendance || 0)}
				${metric("失败记录", data.failed_rows || 0)}
				${metric("自动考勤", data.auto_attendance_used ? "已触发" : "未触发")}
				${metric("兜底生成", data.fallback_used ? "本批次使用" : "未使用")}
			</div>
			<p style="margin-top: 12px;">本次导入未重复创建已有打卡记录，系统自动跳过已存在记录。</p>
		`);
	}

	function metric(label, value) {
		return `
			<div class="hbos-metric">
				<div class="label">${escapeHtml(String(label))}</div>
				<div class="value">${escapeHtml(String(value ?? "-"))}</div>
			</div>
		`;
	}
};
