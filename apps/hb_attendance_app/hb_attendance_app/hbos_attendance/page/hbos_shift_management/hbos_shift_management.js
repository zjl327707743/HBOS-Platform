frappe.pages["hbos-shift-management"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("班次管理"),
		single_column: true,
	});
	renderPage(wrapper);
};

function renderPage(wrapper) {
	const $main = $(wrapper).find(".layout-main-section").empty();
	$main.append(`
		<div class="shift-mgmt" style="padding: 15px;">
			<ul class="nav nav-pills mb-3">
				<li class="nav-item"><a class="nav-link active" id="tab-setup" href="#">班次设置</a></li>
				<li class="nav-item"><a class="nav-link" id="tab-rules-board" href="#">规则看板</a></li>
			</ul>
			<div id="shift-setup-container">
				<div class="row">
					<div class="col-md-4" id="dept-panel"></div>
					<div class="col-md-8" id="shift-panel"></div>
				</div>
			</div>
			<div id="rules-board-container" style="display:none;"></div>
		</div>
	`);
	$("#tab-setup").on("click", function (e) {
		e.preventDefault();
		switchTab("setup");
	});
	$("#tab-rules-board").on("click", function (e) {
		e.preventDefault();
		switchTab("rules-board");
	});
	loadOverview();
}

function switchTab(tab) {
	if (tab === "setup") {
		$("#tab-setup").addClass("active");
		$("#tab-rules-board").removeClass("active");
		$("#shift-setup-container").show();
		$("#rules-board-container").hide();
	} else {
		$("#tab-rules-board").addClass("active");
		$("#tab-setup").removeClass("active");
		$("#shift-setup-container").hide();
		$("#rules-board-container").show();
		renderRulesBoard();
	}
}

function renderRulesBoard() {
	const $c = $("#rules-board-container");
	$c.html('<div class="text-center p-5"><div class="spinner-border text-primary"></div><p class="mt-2 text-muted">加载规则看板...</p></div>');
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.get_rules_board",
		callback(r) {
			if (!r.message) {
				$c.html('<div class="p-5 text-center text-danger">无法加载规则看板</div>');
				return;
			}
			renderRulesBoardSections($c, r.message);
		},
		error() {
			$c.html('<div class="p-5 text-center text-danger">加载失败，请重试</div>');
		},
	});
}

function renderRulesBoardSections($c, data) {
	if (!$("#rb-style").length) {
		$("<style id='rb-style'>" +
			".rb-chain{display:flex;align-items:stretch;gap:10px;flex-wrap:wrap;margin-bottom:18px;}" +
			".rb-step{flex:1;min-width:150px;background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:10px 12px;}" +
			".rb-step .n{font-weight:700;color:#2c3e50;}" +
			".rb-step .d{font-size:11px;color:#888;margin-top:2px;}" +
			".rb-sec{background:#fff;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.05);margin-bottom:16px;}" +
			".rb-sec h5{font-size:15px;margin:0 0 10px 0;color:#333;}" +
			".rb-sec table{width:100%;font-size:13px;border-collapse:collapse;}" +
			".rb-sec th{background:#f7f8fa;text-align:left;padding:7px 8px;border-bottom:2px solid #e0e0e0;}" +
			".rb-sec td{padding:6px 8px;border-bottom:1px solid #f0f0f0;}" +
			".rb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;}" +
			".rb-card{border:1px solid #e0e0e0;border-radius:8px;padding:12px 14px;cursor:pointer;background:#fff;}" +
			".rb-card:hover{border-color:#5b9bd5;}" +
			".rb-card .t{font-weight:700;font-size:14px;}" +
			".rb-card .c{display:inline-block;background:#eef2f7;border-radius:10px;padding:1px 8px;font-size:12px;color:#2c3e50;margin-left:6px;}" +
			".rb-card .d{font-size:12px;color:#777;margin:6px 0;}" +
			".rb-nums{display:none;margin-top:8px;max-height:220px;overflow-y:auto;font-family:monospace;font-size:12px;line-height:1.7;background:#fafbfc;border-radius:6px;padding:8px;}" +
			"</style>").appendTo("head");
	}

	let h = "";

	// 1. 判定优先级链
	h += '<div class="rb-sec"><h5>考勤判定优先级链</h5><div class="rb-chain">';
	(data.priority_chain || []).forEach(s => {
		h += '<div class="rb-step"><span class="n">' + s.step + '. ' + s.name + '</span><div class="d">' + (s.desc || '') + '</div></div>';
	});
	h += '</div></div>';

	// 2. 班次规则记录
	const rules = data.rules || [];
	const activeRules = rules.filter(r => r.status === "生效" || r.status === "草稿");
	const inactiveRules = rules.filter(r => r.status === "停用");
	const tableHead = '<thead><tr><th>规则名称</th><th>部门</th><th>班次类型</th><th>上班</th><th>下班</th><th>迟到起算</th><th>最小工时</th><th>生效日期</th><th>状态</th><th>绑定人数</th></tr></thead>';
	const ruleRow = r => '<tr><td>' + r.rule_name + '</td><td>' + r.department + '</td><td>' + r.shift_type + '</td>'
		+ '<td>' + fmtTime(r.start_time) + '</td><td>' + fmtTime(r.end_time) + '</td><td>' + fmtTime(r.late_after) + '</td>'
		+ '<td>' + (r.min_hours != null ? r.min_hours : "") + '</td><td>' + r.effective_from + '</td>'
		+ '<td>' + statusBadge(r.status) + '</td><td>' + (r.assigned_count || 0) + '</td></tr>';
	h += '<div class="rb-sec"><h5>班次规则记录（' + rules.length + ' 条）</h5><table>' + tableHead + '<tbody>';
	(activeRules.length ? activeRules : rules).forEach(r => { h += ruleRow(r); });
	h += '</tbody></table>';
	if (inactiveRules.length) {
		h += '<div class="text-muted" style="margin-top:6px;"><a href="#" id="rb-toggle-inactive" style="font-size:12px;">展开已停用历史规则（' + inactiveRules.length + ' 条）</a></div>';
		h += '<div id="rb-inactive" style="display:none;"><table>' + tableHead + '<tbody>';
		inactiveRules.forEach(r => { h += ruleRow(r); });
		h += '</tbody></table></div>';
	}
	h += '</div>';

	// 3. 内置默认班次
	h += '<div class="rb-sec"><h5>内置默认班次（未配置专属规则时按此判定）</h5><table><thead><tr><th>班次</th><th>上班</th><th>下班</th><th>迟到起算</th><th>最小工时(小时)</th></tr></thead><tbody>';
	(data.builtin_shifts || []).forEach(b => {
		h += '<tr><td>' + b.shift_type + '</td><td>' + fmtTime(b.start_time) + '</td><td>' + fmtTime(b.end_time) + '</td>'
			+ '<td>' + fmtTime(b.late_after) + '</td><td>' + b.min_hours + '</td></tr>';
	});
	h += '</tbody></table></div>';

	// 4. 名单规则卡片
	h += '<div class="rb-sec"><h5>名单规则（点击卡片展开工号）</h5><div class="rb-grid">';
	(data.lists || []).forEach(g => {
		h += '<div class="rb-card" data-key="' + g.key + '">'
			+ '<span class="t">' + g.title + '</span><span class="c">' + g.count + ' 个</span>'
			+ '<div class="d">' + (g.desc || '') + '</div>'
			+ '<div class="rb-nums">' + (g.nums || []).join(' ') + '</div>'
			+ '</div>';
	});
	h += '</div></div>';

	// 5. 配对算法参数
	h += '<div class="rb-sec"><h5>配对算法参数</h5><table><thead><tr><th>参数</th><th>值</th><th>说明</th></tr></thead><tbody>';
	(data.pairing_params || []).forEach(p => {
		h += '<tr><td>' + p.name + '</td><td>' + p.value + '</td><td>' + (p.desc || '') + '</td></tr>';
	});
	h += '</tbody></table></div>';

	$c.html(h);

	$c.find(".rb-card").on("click", function () {
		$(this).find(".rb-nums").toggle();
	});
	$c.find("#rb-toggle-inactive").on("click", function (e) {
		e.preventDefault();
		$("#rb-inactive").toggle();
		$(this).text($("#rb-inactive").is(":visible")
			? "收起已停用历史规则"
			: "展开已停用历史规则（" + inactiveRules.length + " 条）");
	});
}

function loadOverview() {
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.get_shift_overview",
		callback(r) {
			const data = r.message;
			renderDeptPanel(data);
			renderActiveShifts(data);
		},
	});
}

function renderDeptPanel(data) {
	const $dept = $("#dept-panel").empty();
	let html = `<div class="card"><div class="card-header">部门列表</div><ul class="list-group list-group-flush">`;
	(data.departments || []).forEach(dept => {
		const cnt = data.dept_employee_count[dept] || 0;
		html += `<li class="list-group-item dept-item" data-dept="${dept}" style="cursor:pointer;">
			${dept} <span class="badge badge-secondary">${cnt}人</span></li>`;
	});
	html += `</ul></div>`;
	$dept.html(html);
	$dept.find(".dept-item").on("click", function () {
		const dept = $(this).attr("data-dept");
		$dept.find(".dept-item").removeClass("active");
		$(this).addClass("active");
		loadDeptShifts(dept);
	});
}

function renderActiveShifts(data) {
	const $shift = $("#shift-panel").empty();
	let html = `<div class="card mb-3">
		<div class="card-header">正在进行的班次（当前 ${data.now}）</div>
		<ul class="list-group list-group-flush">`;
	if ((data.active_shifts || []).length === 0) {
		html += `<li class="list-group-item text-muted">当前没有进行中的班次</li>`;
	}
	data.active_shifts.forEach(s => {
		html += `<li class="list-group-item">
			<b>${s.rule_name}</b>（${s.shift_type}）
			<span class="text-muted">${fmtTime(s.start_time)} - ${fmtTime(s.end_time)}</span>
			<span class="badge badge-success">进行中</span></li>`;
	});
	html += `</ul></div>
		<div class="text-muted mb-3">点击左侧部门查看该部门的班次规则和人员班次设置</div>`;
	$shift.html(html);
}

function loadDeptShifts(dept) {
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.get_department_shifts",
		args: { department: dept },
		callback(r) {
			renderDeptShifts(dept, r.message);
			// 串行: 班次面板渲染完成后再加载人员, 避免异步竞态清空面板
			loadDeptEmployees(dept);
		},
	});
}

function renderDeptShifts(dept, shifts) {
	const $shift = $("#shift-panel").empty();
	let html = `<div class="card mb-3"><div class="card-header">${dept} - 班次规则</div>
		<table class="table table-bordered table-sm">
		<thead><tr><th>规则</th><th>班次</th><th>上班</th><th>下班</th><th>迟到起算</th><th>生效日期</th><th>状态</th><th>操作</th></tr></thead><tbody>`;
	if (!shifts || shifts.length === 0) {
		html += `<tr><td colspan="8" class="text-muted">该部门暂无专属班次规则（使用「全部部门」的全局规则）</td></tr>`;
	}
	(shifts || []).forEach(s => {
		html += `<tr>
			<td>${s.rule_name}</td>
			<td>${s.shift_type}</td>
			<td><input type="time" class="form-control form-control-sm shift-edit" data-name="${s.name}" data-field="start_time" value="${fmtTime(s.start_time)}" ${s.status === "草稿" ? "disabled" : ""}></td>
			<td><input type="time" class="form-control form-control-sm shift-edit" data-name="${s.name}" data-field="end_time" value="${fmtTime(s.end_time)}" ${s.status === "草稿" ? "disabled" : ""}></td>
			<td><input type="time" class="form-control form-control-sm shift-edit" data-name="${s.name}" data-field="late_after" value="${fmtTime(s.late_after)}" ${s.status === "草稿" ? "disabled" : ""}></td>
			<td>${s.effective_from}</td>
			<td>
				<select class="form-control form-control-sm rule-status" data-name="${s.name}">
					<option value="生效" ${s.status === "生效" ? "selected" : ""}>生效</option>
					<option value="停用" ${s.status === "停用" ? "selected" : ""}>停用</option>
					<option value="草稿" ${s.status === "草稿" ? "selected" : ""}>草稿</option>
				</select>
			</td>
			<td>
				${s.status === "生效" ? `<button class="btn btn-xs btn-primary save-shift" data-name="${s.name}">保存</button>` : ""}
				<button class="btn btn-xs btn-danger delete-shift" data-name="${s.name}">删除</button>
			</td>
		</tr>`;
	});
	html += `</tbody></table>
		<div class="card-footer">
			<button class="btn btn-sm btn-secondary" id="btn-new-shift">新建班次</button>
			<button class="btn btn-sm btn-secondary" id="btn-new-rule">新建规则</button>
			<button class="btn btn-sm btn-info" id="btn-import-schedule">导入排班表</button>
			<span class="text-muted ml-2">修改/新建均次日生效（历史考勤不受影响）</span>
		</div></div>
		<div id="dept-employees"><div class="text-muted">加载人员中...</div></div>`;
	$shift.html(html);

	$shift.find(".save-shift").on("click", function () {
		saveShiftRow($(this));
	});
	// 上班时间变化时自动联动迟到起算(+1分钟), 除非用户已手动改过迟到起算
	$shift.find(".shift-edit[data-field='start_time']").on("change", function () {
		const row = $(this).closest("tr");
		const lateInput = row.find(".shift-edit[data-field='late_after']");
		// 只有迟到起算仍等于「旧上班时间+1分钟」时才自动更新(用户手动改过则不动)
		const newLate = addOneMinute($(this).val());
		if (!lateInput.attr("data-user-set") || lateInput.attr("data-user-set") === "0") {
			lateInput.val(newLate);
		}
	});
	$shift.find(".shift-edit[data-field='late_after']").on("change", function () {
		$(this).attr("data-user-set", "1");
	});
	$shift.find(".rule-status").on("change", function () {
		const name = $(this).attr("data-name");
		const status = $(this).val();
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.set_rule_status",
			args: { rule_name: name, status: status },
			callback() {
				frappe.show_alert({ message: __("状态已更新"), indicator: "green" });
				loadDeptShifts(dept);
			},
		});
	});
	$shift.find(".delete-shift").on("click", function () {
		const name = $(this).attr("data-name");
		frappe.confirm(
			__("确定删除这条班次规则吗？已绑定的员工会自动解绑。"),
			() => {
				frappe.call({
					method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.delete_shift_rule",
					args: { rule_name: name },
					callback() {
						frappe.show_alert({ message: __("规则已删除"), indicator: "green" });
						loadDeptShifts(dept);
					},
				});
			}
		);
	});
	$shift.find("#btn-new-shift").on("click", function () {
		showNewShiftDialog(dept);
	});
	$shift.find("#btn-new-rule").on("click", function () {
		showNewRuleDialog(dept);
	});
	$shift.find("#btn-import-schedule").on("click", function () {
		showImportScheduleDialog(dept);
	});
}

// 导入排班表弹窗(支持厂外QC矩阵式 / 四车间纵向式)
function showImportScheduleDialog(dept) {
	const d = new frappe.ui.Dialog({
		title: __("导入排班表"),
		fields: [
			{ label: __("排班表文件"), fieldname: "schedule_file", fieldtype: "Attach" },
			{ label: __("说明"), fieldname: "note", fieldtype: "HTML",
			  options: "<div class='text-muted'>支持两种格式：<br>1. 厂外QC矩阵式（员工×31天，含「班次说明」工作表）<br>2. 四车间纵向式（日期+班次+成员）<br>重复导入同日期范围会覆盖旧记录</div>" },
		],
		primary_action_label: __("导入"),
		primary_action(values) {
			if (!values.schedule_file) {
				frappe.msgprint(__("请先选择排班表文件"));
				return;
			}
			// 传 file_url, 后端从 File 记录读原始字节(Attach 上传的文件无 content 字段)
			frappe.call({
				method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.import_schedule_file",
				args: { file_url: values.schedule_file },
				callback(r) {
					d.hide();
					const m = r.message;
					if (m.date_range && m.date_range.length === 2) {
						frappe.show_alert({
							message: __(`导入完成：${m.created} 条，跳过 ${m.skipped} 条（${m.date_range[0]} ~ ${m.date_range[1]}）`),
							indicator: "green",
						});
					} else {
						frappe.show_alert({
							message: __(`导入完成：${m.created} 条，跳过 ${m.skipped} 条`),
							indicator: "green",
						});
					}
					loadDeptShifts(dept);
				},
			});
		},
	});
	d.show();
}

function loadDeptEmployees(dept) {
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.get_department_employees",
		args: { department: dept },
		callback(r) {
			renderDeptEmployees(dept, r.message);
		},
	});
}

function renderDeptEmployees(dept, employees) {
	const $emp = $("#dept-employees").empty();
	let html = `<div class="card"><div class="card-header">${dept} - 人员班次设置（${(employees || []).length}人）</div>
		<table class="table table-bordered table-sm">
		<thead><tr><th>工号</th><th>姓名</th><th>已绑定班次</th><th>设置班次（勾选绑定）</th></tr></thead><tbody>`;
	(employees || []).forEach(e => {
		// 手动绑定优先, 否则显示系统名单班次
		const current = e.fixed_shift_name
			? `${e.fixed_shift_name}（${e.fixed_shift_type}）`
			: `<span class="text-primary">${e.system_shift || "通用倒班(按时间判定)"}</span>`;
		html += `<tr>
			<td>${e.employee_number || ""}</td>
			<td>${e.employee_name || ""}</td>
			<td class="bound-display" data-emp="${e.name}">${current}</td>
			<td class="shift-checkbox-cell" data-emp="${e.name}"></td>
		</tr>`;
	});
	html += `</tbody></table>
		<div class="text-muted mb-1">蓝色 = 系统名单班次；勾选即绑定、取消勾选即解绑；绑定多个班次时判定按打卡时间自动匹配</div></div>`;
	$emp.html(html);

	// 填充复选框(全部生效规则)
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.get_shift_overview",
		callback(r) {
			const rules = (r.message.rules || []).filter(x => x.status === "生效");
			$emp.find(".shift-checkbox-cell").each(function () {
				const $cell = $(this);
				const emp = $cell.attr("data-emp");
				// 渲染复选框列表
				let cbHtml = "";
				rules.forEach(s => {
					cbHtml += `<label class="mr-2 mb-1" style="display:inline-block; white-space:nowrap;">
						<input type="checkbox" class="emp-shift-cb" value="${s.name}">
						${s.rule_name}
					</label>`;
				});
				$cell.html(cbHtml);
				// 查询已绑定并勾选
				frappe.call({
					method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.get_employee_bound_shifts",
					args: { employee: emp },
					callback(res) {
						const bound = res.message || [];
						$cell.find(".emp-shift-cb").each(function () {
							$(this).prop("checked", bound.includes($(this).val()));
						});
						updateBoundDisplay(emp, bound, rules);
					},
				});
				// 勾选/取消即保存
				$cell.on("change", ".emp-shift-cb", function () {
					const checked = [];
					$cell.find(".emp-shift-cb:checked").each(function () {
						checked.push($(this).val());
					});
					bindShifts(emp, checked);
					updateBoundDisplay(emp, checked, rules);
				});
			});
		},
	});
}

// 更新「已绑定班次」列的徽章显示
function updateBoundDisplay(emp, boundRules, allRules) {
	const $cell = $(`.bound-display[data-emp="${emp}"]`);
	if (!boundRules || boundRules.length === 0) {
		$cell.html('<span class="text-muted">未绑定</span>');
		return;
	}
	let html = "";
	boundRules.forEach(r => {
		const rule = allRules.find(x => x.name === r);
		const label = rule ? `${rule.rule_name}` : r;
		html += `<span class="badge badge-primary mr-1">${label}</span>`;
	});
	html += `<span class="text-muted" style="font-size:11px;">（${boundRules.length} 个）</span>`;
	$cell.html(html);
}

function bindShifts(emp, shiftList) {
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.bind_employee_shifts",
		args: {
			employee: emp,
			shift_rules: JSON.stringify((shiftList || []).filter(x => x !== "")),
		},
		callback() {
			frappe.show_alert({ message: __("班次绑定已更新"), indicator: "green" });
		},
	});
}

function bindShift(emp, shift) {
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.bind_shift",
		args: { employee: emp, shift_rule: shift },
		callback() {
			frappe.show_alert({ message: __("绑定已更新"), indicator: "green" });
		},
	});
}

function saveShiftRow($btn) {
	const row = $btn.closest("tr");
	const name = $btn.attr("data-name");
	const updates = {};
	row.find(".shift-edit").each(function () {
		updates[$(this).attr("data-field")] = $(this).val();
	});
	let chain = Promise.resolve();
	Object.keys(updates).forEach(field => {
		chain = chain.then(() =>
			frappe.call({
				method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.update_shift_rule",
				args: { rule_name: name, field: field, value: normTime(updates[field]) },
			})
		);
	});
	chain.then(() => {
		frappe.show_alert({ message: __("已保存，次日生效"), indicator: "green" });
		loadOverview();
	});
}

// 新建规则: 上下班时间 → 生效方式 → 命名班次。名称有自动生成默认值, 可修改
function showNewRuleDialog(dept) {
	const d = new frappe.ui.Dialog({
		title: __("新建规则"),
		fields: [
			{ label: __("上班时间"), fieldname: "start_time", fieldtype: "Time", reqd: 1 },
			{ label: __("下班时间"), fieldname: "end_time", fieldtype: "Time", reqd: 1 },
			{ label: __("生效方式"), fieldname: "effective_mode", fieldtype: "Select",
			  options: "次日生效\n立即生效\n指定日期", default: "次日生效", reqd: 1,
			  description: "指定日期: 可选过去的日期, 让历史考勤按此规则重新判定" },
			{ label: __("生效日期"), fieldname: "effective_date", fieldtype: "Date",
			  default: defaultTomorrow(),
			  description: "仅「指定日期」方式使用" },
			{ label: __("班次名称"), fieldname: "rule_name", fieldtype: "Data", reqd: 1,
			  description: "默认可自动生成, 也可自行修改" },
		],
		primary_action_label: __("创建"),
		primary_action(values) {
			const [stype, late] = guessShiftType(values.start_time);
			// 自动命名(可被用户覆盖): 部门-类型-时间
			const auto_name = `${dept}-${stype}-${values.start_time.substring(0, 5)}`;
			const rule_name = values.rule_name || auto_name;
			let effective_from;
			if (values.effective_mode === "立即生效") {
				effective_from = frappe.datetime.get_today();
			} else if (values.effective_mode === "指定日期") {
				effective_from = values.effective_date;
			} else {
				effective_from = defaultTomorrow();
			}
			d.hide();
			frappe.call({
				method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.create_shift_rule",
				args: {
					rule_name: rule_name,
					department: dept,
					shift_type: stype,
					start_time: normTime(values.start_time),
					end_time: normTime(values.end_time),
					late_after: late,
					effective_from: effective_from,
				},
				callback(r) {
					frappe.show_alert({
						message: __(`规则「${r.message.rule_name}」已创建，${r.message.effective_from} 生效`),
						indicator: "green",
					});
					loadDeptShifts(dept);
				},
			});
		},
	});
	// 班次名称实时联动: 改时间后自动更新默认名称
	d.fields_dict.start_time.$input.on("change", () => {
		const st = d.get_value("start_time");
		if (!st) return;
		const [stype] = guessShiftType(st);
		const cur = d.get_value("rule_name") || "";
		// 仅当名称还是自动格式时更新, 用户手动改过的名称不动
		if (!cur || /^.+-(早班|中班|夜班|行政班|8:30班|无菌早\(12h\)|无菌晚\(12h\))-\d{2}:\d{2}$/.test(cur)) {
			d.set_value("rule_name", `${dept}-${stype}-${st.substring(0, 5)}`);
		}
	});
	d.show();
}

// 三步向导: 选日期 → 定时间 → 命名。每步新建 Dialog, 避免 clear/make 复用问题
function showNewShiftDialog(dept) {
	const wizardData = {
		department: dept,
		effective_from: null,
		start_time: null,
		end_time: null,
		rule_name: null,
		shift_type: null,
		late_after: null,
	};

	showStep1();

	function showStep1() {
		const d = new frappe.ui.Dialog({
			title: __("新建班次（第 1 步 / 共 3 步）— 选择生效日期"),
			fields: [
				{ label: __("生效日期"), fieldname: "effective_from", fieldtype: "Date",
				  default: defaultTomorrow(), reqd: 1,
				  description: "默认次日生效；可选更晚日期" },
			],
			primary_action_label: __("下一步"),
			primary_action(values) {
				wizardData.effective_from = values.effective_from;
				d.hide();
				showStep2();
			},
		});
		d.show();
	}

	function showStep2() {
		const d = new frappe.ui.Dialog({
			title: __("新建班次（第 2 步 / 共 3 步）— 设定时间"),
			fields: [
				{ label: __("上班时间"), fieldname: "start_time", fieldtype: "Time", reqd: 1 },
				{ label: __("下班时间"), fieldname: "end_time", fieldtype: "Time", reqd: 1 },
			],
			primary_action_label: __("下一步"),
			primary_action(values) {
				wizardData.start_time = values.start_time;
				wizardData.end_time = values.end_time;
				const [stype, late] = guessShiftType(values.start_time);
				wizardData.shift_type = stype;
				wizardData.late_after = late;
				d.hide();
				showStep3();
			},
			secondary_action_label: __("上一步"),
			secondary_action() {
				d.hide();
				showStep1();
			},
		});
		d.show();
	}

	function showStep3() {
		const d = new frappe.ui.Dialog({
			title: __("新建班次（第 3 步 / 共 3 步）— 命名班次"),
			fields: [
				{ label: __("班次名称"), fieldname: "rule_name", fieldtype: "Data", reqd: 1,
				  description: "例如：一车间-早班A" },
				{ label: __("班次类型"), fieldname: "shift_type", fieldtype: "Select",
				  options: "早班\n中班\n夜班\n晚班\n行政班\n8:30班\n无菌早(12h)\n无菌晚(12h)",
				  default: wizardData.shift_type, reqd: 1 },
				{ label: __("生效方式"), fieldname: "effective_mode", fieldtype: "Select",
				  options: "次日生效\n立即生效", default: "次日生效", reqd: 1,
				  description: "立即生效会影响今天的考勤判定；次日生效更安全" },
				{ label: __("时间确认"), fieldname: "time_display", fieldtype: "Data",
				  default: `${wizardData.start_time} - ${wizardData.end_time}（迟到起算 ${wizardData.late_after}）`, read_only: 1 },
			],
			primary_action_label: __("创建"),
			primary_action(values) {
				wizardData.rule_name = values.rule_name;
				wizardData.shift_type = values.shift_type;
				if (values.effective_mode === "立即生效") {
					wizardData.effective_from = frappe.datetime.get_today();
				}
				d.hide();
				frappe.call({
					method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.create_shift_rule",
					args: {
						rule_name: wizardData.rule_name,
						department: wizardData.department,
						shift_type: wizardData.shift_type,
						start_time: normTime(wizardData.start_time),
						end_time: normTime(wizardData.end_time),
						late_after: wizardData.late_after,
						effective_from: wizardData.effective_from,
					},
					callback(r) {
						frappe.show_alert({
							message: __(`班次「${r.message.rule_name}」已创建，${r.message.effective_from} 生效`),
							indicator: "green",
						});
						loadDeptShifts(wizardData.department);
					},
				});
			},
			secondary_action_label: __("上一步"),
			secondary_action() {
				d.hide();
				showStep2();
			},
		});
		d.show();
	}
}

// 按上班时间自动识别班次类型, 返回 [类型, 迟到起算]
// 20点后=晚班(通用倒班晚班), 不再自动归为无菌晚
function guessShiftType(timeStr) {
	const t = timeStr ? String(timeStr).substring(0, 5) : "";
	const h = parseInt(t.split(":")[0] || "0", 10);
	if (h < 4) return ["夜班", "00:01:00"];
	if (h < 9) return [t >= "08:30" ? "8:30班" : "早班", t >= "08:30" ? "08:31:00" : "08:01:00"];
	if (h < 16) return ["行政班", "08:31:00"];
	if (h < 20) return ["中班", "16:01:00"];
	return ["晚班", "20:01:00"];
}

function defaultTomorrow() {
	const t = new Date();
	t.setDate(t.getDate() + 1);
	return frappe.datetime.obj_to_str(t).substring(0, 10);
}

// 时间规范化: 确保 HH:MM:SS 格式(Frappe Time 字段可能返回 HH:MM 或 HH:MM:SS)
function normTime(t) {
	if (!t) return "";
	const parts = String(t).split(":");
	const hh = (parts[0] || "00").padStart(2, "0");
	const mm = (parts[1] || "00").padStart(2, "0");
	const ss = (parts[2] || "00").padStart(2, "0");
	return `${hh}:${mm}:${ss}`;
}

// 时间 +1 分钟(HH:MM 格式)
function addOneMinute(t) {
	const parts = String(t || "00:00").split(":");
	let h = parseInt(parts[0] || "0", 10);
	let m = parseInt(parts[1] || "0", 10);
	m += 1;
	if (m >= 60) { m = 0; h += 1; }
	if (h >= 24) h = 0;
	return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function fmtTime(t) {
	return t ? String(t).substring(0, 5) : "";
}

function statusBadge(s) {
	if (s === "生效") return `<span class="badge badge-success">生效</span>`;
	if (s === "停用") return `<span class="badge badge-secondary">停用</span>`;
	return `<span class="badge badge-warning">${s}</span>`;
}
