frappe.pages["hbos-attendance-import"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "导入考勤机导出表",
		single_column: true,
	});
	// HBOS 共享样式层的挂载点：只影响本容器内部，Desk 框架不受影响。
	$(wrapper).addClass("hbos-surface");

	// 样式只声明本页结构；色值、圆角、阴影一律走 var(--h-*)（由
	// hbos_attendance.bundle.css 在 .hbos-surface 下定义），不写死。
	// 字号只取契约 v2.0 允许的 30 / 20 / 16 / 14 / 12。
	//
	// 强度：本页是**两栏工作台**（左识别、右结果），工作区按 V1 处理——
	// 实色面板、密集定义列表、无动效；玻璃只留在顶部工具条上。
	//
	// 结构上唯一的「装饰」是步骤条，但它是信息而非装饰：本页确实是一条
	// 三步流程（选表 → 识别 → 导入），步骤条回答的是「我卡在哪一步」。
	// 若只是三个并列按钮，失败时用户无法判断该退回哪一步。
	$("<style id='imp-style'>").text(
		".imp-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:16px;}" +
		".imp-heading h1{margin:6px 0 4px;font-size:30px;line-height:38px;font-weight:600;color:var(--h-text);}" +
		".imp-heading p{margin:0;font-size:14px;line-height:22px;color:var(--h-text-2);max-width:64ch;}" +

		".imp-steps{display:flex;align-items:center;gap:0;margin-bottom:16px;background:var(--h-surface);border:1px solid var(--h-border);border-radius:var(--h-radius-control);padding:10px 16px;}" +
		".imp-step{display:flex;align-items:center;gap:8px;font-size:12px;line-height:20px;color:var(--h-muted);}" +
		".imp-step .n{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;border-radius:50%;font-size:12px;background:rgba(114,130,157,.14);color:var(--h-muted);}" +
		".imp-step.on{color:var(--h-text);font-weight:500;}" +
		".imp-step.on .n{background:var(--h-accent);color:#fff;}" +
		".imp-step.done{color:var(--h-success);}" +
		".imp-step.done .n{background:rgba(27,188,134,.14);color:var(--h-success);}" +
		".imp-sep{flex:0 0 28px;height:1px;background:var(--h-border-strong);margin:0 10px;}" +
		".imp-actions{margin-left:auto;display:flex;gap:8px;}" +

		".imp-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;}" +
		".imp-panel{background:var(--h-surface-solid);border:1px solid var(--h-border);border-radius:var(--h-radius-card);padding:20px;min-height:260px;}" +
		".imp-panel h2{margin:0 0 4px;font-size:16px;line-height:24px;font-weight:600;color:var(--h-text);}" +
		".imp-panel .hint{margin:0 0 14px;font-size:12px;line-height:20px;color:var(--h-muted);}" +

		// 定义列表取代「指标卡墙」：这些是只读事实，不是 KPI。
		// 每项一个色块卡会让人以为它们各自独立、可点击、可比较大小。
		".imp-defs{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:0 20px;border-top:1px solid var(--h-border);}" +
		".imp-def{display:flex;flex-direction:column;gap:2px;padding:10px 0;border-bottom:1px solid var(--h-border);}" +
		".imp-def .k{font-size:12px;line-height:20px;color:var(--h-muted);}" +
		".imp-def .v{font-size:14px;line-height:22px;color:var(--h-text);font-weight:500;word-break:break-word;font-variant-numeric:tabular-nums;}" +

		".imp-note{margin:14px 0 0;font-size:12px;line-height:20px;color:var(--h-muted);}" +
		".imp-empty{padding:24px 0;font-size:14px;line-height:22px;color:var(--h-muted);}" +
		".imp-file{font-size:14px;line-height:22px;color:var(--h-text-2);}" +
		".imp-links{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;padding-top:16px;border-top:1px solid var(--h-border);}" +
		".imp-links .lbl{width:100%;font-size:12px;line-height:20px;color:var(--h-muted);margin-bottom:2px;}" +
		"@media (max-width:900px){.imp-heading{flex-direction:column;}.imp-layout{grid-template-columns:1fr;}}"
	).appendTo("head");

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
		<div class="imp-heading">
			<div>
				<div class="hbos-breadcrumb">海滨考勤工作台 / 导入考勤机导出表</div>
				<h1>导入考勤机导出表</h1>
				<p>海滨考勤复用 HRMS 的员工、打卡和考勤结果数据；本页面负责考勤机 Excel 导入并汇入 HBOS 中文报表主线。</p>
			</div>
			<button class="btn btn-default btn-xs" data-route="Workspaces/海滨考勤工作台">返回海滨考勤工作台</button>
		</div>

		<div class="imp-steps" id="imp-steps">
			<span class="imp-step on" data-step="1"><span class="n">1</span>选择表格</span>
			<span class="imp-sep"></span>
			<span class="imp-step" data-step="2"><span class="n">2</span>识别并预览</span>
			<span class="imp-sep"></span>
			<span class="imp-step" data-step="3"><span class="n">3</span>确认导入</span>
			<span class="imp-actions">
				<input class="hbos-file-input hidden" type="file" accept=".xlsx" />
				<button class="btn btn-primary btn-xs" data-action="choose-file">上传原始表格</button>
				<button class="btn btn-default btn-xs" data-action="preview" disabled>识别并预览</button>
				<button class="btn btn-success btn-xs" data-action="run" disabled>确认导入</button>
			</span>
		</div>

		<div class="imp-layout">
			<section class="imp-panel">
				<h2>文件与识别</h2>
				<p class="hint">上传考勤机月度导出表后先做识别，识别不会写入任何数据。</p>
				<div class="hbos-file-state imp-file">尚未选择 Excel 文件。</div>
				<div class="hbos-preview-state"></div>
			</section>
			<section class="imp-panel">
				<h2>导入结果</h2>
				<p class="hint">确认导入后才会写入打卡流水与考勤结果。</p>
				<div class="hbos-result-state imp-empty">完成预览后可确认导入。</div>
			</section>
		</div>

		<div class="imp-links">
			<button class="btn btn-default btn-xs" data-route="List/HBOS Attendance Import Log">查看考勤导入日志</button>
			<button class="btn btn-default btn-xs" data-report="打卡流水">查看 HBOS 打卡流水</button>
			<button class="btn btn-default btn-xs" data-report="考勤结果">查看 HBOS 考勤结果</button>
			<button class="btn btn-default btn-xs" data-report="HBOS 月度汇总暂存（对账）">查看月度汇总暂存</button>
		</div>
	`);

	const $body = $(page.body);
	const $fileInput = $body.find(".hbos-file-input");

	// 步骤条状态：1 选表 → 2 已选待识别 → 3 已识别待导入 → 3 全绿(已导入)
	function setStep(step, allDone) {
		$body.find(".imp-step").each(function () {
			const n = Number($(this).attr("data-step"));
			$(this).toggleClass("done", allDone ? true : n < step);
			$(this).toggleClass("on", !allDone && n === step);
		});
	}

	$body.find("[data-action='choose-file']").on("click", () => $fileInput.trigger("click"));
	$body.find("[data-action='preview']").on("click", () => previewImport());
	$body.find("[data-action='run']").on("click", () => runImport());
	$body.find("[data-route]").on("click", function () {
		frappe.set_route($(this).attr("data-route").split("/"));
	});
	$body.find("[data-report]").on("click", function () {
		if (state.result && state.result.log_name) {
			frappe.route_options = { import_log: state.result.log_name };
		}
		frappe.set_route("query-report", $(this).attr("data-report"));
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
			setStep(2);
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
			setStep(3);
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
				setStep(3, true);
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
			<div class="imp-defs">
				${def("识别类型", data.import_type)}
				${def("日期范围", `${data.period_start || "-"} 至 ${data.period_end || "-"}`)}
				${def("员工行数", mapping.identity_rows || 0)}
				${def("日期列数", (mapping.daily_columns || []).length)}
				${def("表头行", mapping.header_row || "-")}
				${def("默认班次", "白班/行政班 08:30-17:30")}
			</div>
			<p class="imp-note">月度汇总表只进入「月度汇总 / 对账暂存」；逐条原始打卡流水才写入 Employee Checkin 并触发 HRMS Auto Attendance。</p>
		`);
	}

	function renderResult(data) {
		const $target = $body.find(".hbos-result-state");
		if (!data) {
			$target.attr("class", "hbos-result-state imp-empty")
				.html("完成预览后可确认导入。");
			return;
		}
		const isMonthlyStaging = (data.notes || "").includes("月度汇总仅已暂存");
		$target.attr("class", "hbos-result-state").html(`
			<div class="imp-defs">
				${def("批次号", data.log_name)}
				${def("导入类型", data.import_type || "-")}
				${def(isMonthlyStaging ? "暂存员工数" : "匹配员工数", data.matched_rows || 0)}
				${def(isMonthlyStaging ? "月度行数" : "成功行数", data.success_rows || 0)}
				${def("写入打卡流水", isMonthlyStaging ? "不写入" : data.created_checkins || 0)}
				${def("跳过重复记录", data.skipped_duplicates || 0)}
				${def("生成 Attendance", isMonthlyStaging ? "不生成" : data.created_attendance || 0)}
				${def("已存在考勤结果", data.existing_attendance || 0)}
				${def("失败记录", data.failed_rows || 0)}
				${def("自动考勤", isMonthlyStaging ? "不触发" : data.auto_attendance_used ? "已触发" : "未触发")}
				${def("兜底生成", data.fallback_used ? "本批次使用" : "未使用")}
			</div>
			<p class="imp-note" style="color:var(--h-text-2);">${escapeHtml(data.notes || "本次导入未重复创建已有打卡记录，系统自动跳过已存在记录。")}</p>
			<p class="imp-note">查看结果：原始流水看 HBOS 打卡流水；考勤结果看 HBOS 考勤结果；月度汇总表看「月度汇总 / 对账暂存」。</p>
		`);
	}

	function def(label, value) {
		return `
			<div class="imp-def">
				<span class="k">${escapeHtml(String(label))}</span>
				<span class="v">${escapeHtml(String(value ?? "-"))}</span>
			</div>
		`;
	}
};
