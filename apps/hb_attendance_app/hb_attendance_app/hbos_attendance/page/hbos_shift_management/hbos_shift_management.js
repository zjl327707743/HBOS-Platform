// 全部函数收在本页闭包里。此前它们是顶层 function，而 hbos_employee_management.js
// 同样定义了顶层 renderPage —— 两个页面脚本都在 Desk 里常驻求值，后求值的那个
// 会覆盖前者，导致其中一页渲染出另一页的内容。收进 IIFE 后同名不再冲突。
(function () {
frappe.pages["hbos-shift-management"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("班次管理"),
		single_column: true,
	});
	// HBOS 共享样式层的挂载点：只影响本容器内部，Desk 框架不受影响。
	$(wrapper).addClass("hbos-surface");

	renderPage(wrapper);
};

// 规则名、部门名、班次类型都来自用户可写字段 → 一律转义后再拼进 HTML
const esc =
	(frappe.utils && frappe.utils.escape_html) ||
	function (value) {
		return String(value)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#039;");
	};

// 样式只声明本页结构；色值、圆角、阴影一律走 var(--h-*)（由
// hbos_attendance.bundle.css 在 .hbos-surface 下定义），不写死。
// 字号只取契约 v2.0 允许的 30 / 20 / 16 / 14 / 12。
//
// 强度：本页是**编辑器**（改时间、绑人员），整页按 V1 处理——面板实色不模糊、
// 表格密集、无动效。这是四处改造里唯一「一屏没有任何玻璃」的页面：编辑动作
// 里最不该出现的就是会动的装饰。标签页沿用共享样式给的 nav-pills 重着色。
function injectStyle() {
	if ($("#sm-style").length) return;
	$("<style id='sm-style'>").text(
		".sm-heading{margin-bottom:16px;}" +
		".sm-heading h1{margin:6px 0 4px;font-size:30px;line-height:38px;font-weight:600;color:var(--h-text);}" +
		".sm-heading p{margin:0;font-size:14px;line-height:22px;color:var(--h-text-2);max-width:64ch;}" +
		".sm-tabs{margin-bottom:16px;}" +

		".sm-panel{background:var(--h-surface-solid);border:1px solid var(--h-border);border-radius:var(--h-radius-card);margin-bottom:16px;overflow:hidden;}" +
		".sm-panel-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid var(--h-border);font-size:16px;line-height:24px;font-weight:600;color:var(--h-text);}" +
		".sm-panel-head .hint{font-size:12px;line-height:20px;font-weight:400;color:var(--h-muted);}" +
		".sm-panel-body{padding:16px;}" +
		".sm-panel-foot{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:12px 16px;border-top:1px solid var(--h-border);background:var(--h-subtle);}" +

		"ul.sm-depts{list-style:none;margin:0;padding:0;max-height:520px;overflow:auto;}" +
		".sm-dept{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:9px 16px;font-size:14px;line-height:22px;color:var(--h-text);border-bottom:1px solid var(--h-border);cursor:pointer;}" +
		".sm-dept:hover{background:var(--h-subtle);}" +
		".sm-dept.active{background:rgba(103,95,255,.08);box-shadow:inset 3px 0 0 var(--h-brand);font-weight:500;}" +
		".sm-dept .cnt{font-size:12px;color:var(--h-muted);font-variant-numeric:tabular-nums;}" +

		"table.sm-tbl{width:100%;border-collapse:collapse;font-size:14px;line-height:22px;}" +
		".sm-tbl th{background:var(--h-subtle);color:var(--h-text-2);font-weight:500;font-size:12px;line-height:20px;text-align:left;padding:10px 12px;border-bottom:1px solid var(--h-border-strong);white-space:nowrap;}" +
		".sm-tbl td{padding:8px 12px;border-bottom:1px solid var(--h-border);color:var(--h-text);vertical-align:middle;}" +
		".sm-tbl tbody tr:hover td{background:var(--h-subtle);}" +
		".sm-tbl .num{font-variant-numeric:tabular-nums;}" +
		".sm-tbl .form-control{border-radius:var(--h-radius-control);}" +
		".sm-none{padding:20px 16px;font-size:14px;line-height:22px;color:var(--h-muted);}" +
		".sm-foot-note{margin:12px 0 0;font-size:12px;line-height:20px;color:var(--h-muted);}" +
		".sys-shift{color:var(--h-info);}" +
		".sm-load{padding:32px 16px;text-align:center;font-size:14px;line-height:22px;color:var(--h-text-2);}" +
		".sm-load.error{color:var(--h-critical);}"
	).appendTo("head");
}

function renderPage(wrapper) {
	injectStyle();
	const $main = $(wrapper).find(".layout-main-section").empty();
	$main.append(`
		<div class="sm-heading">
			<div class="hbos-breadcrumb">海滨考勤工作台 / 班次管理</div>
			<h1>班次管理</h1>
			<p>按部门维护班次规则与人员绑定。改动次日生效，历史考勤不受影响。</p>
		</div>
		<ul class="nav nav-pills sm-tabs">
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
	$c.html('<div class="rb-toolbar">'
		+ '<button class="btn btn-primary btn-xs" id="rb-export-roster">导出班次人员维护表</button></div>'
		+ '<div class="rb-loading sm-load">加载规则看板…</div>');
	$c.find("#rb-export-roster").on("click", function () {
		const $btn = $(this).prop("disabled", true);
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.roster_export.export_shift_roster",
			callback(r) {
				$btn.prop("disabled", false);
				if (r.message) {
					frappe.show_alert({ message: __("已生成导出文件，开始下载"), indicator: "green" });
					window.open(r.message, "_blank");
				} else {
					frappe.show_alert({ message: __("导出失败，请重试"), indicator: "red" });
				}
			},
			error() {
				$btn.prop("disabled", false);
				frappe.show_alert({ message: __("导出失败，请查看服务端错误"), indicator: "red" });
			},
		});
	});
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_shift_management.shift_management_data.get_rules_board",
		callback(r) {
			if (!r.message) {
				$c.find(".rb-loading").addClass("error").text("无法加载规则看板");
				return;
			}
			renderRulesBoardSections($c, r.message);
		},
		error() {
			$c.find(".rb-loading").addClass("error").text("加载失败，请重试");
		},
	});
}

function renderRulesBoardSections($c, data) {
	if (!$("#rb-style").length) {
		// 规则看板自己的类，与 .sm-* 分开：看板是「读」的面（分节卡片更像文档），
		// 设置页是「改」的面（面板+密集表）。两者共用同一套 token，故观感一致。
		$("<style id='rb-style'>" +
			".rb-chain{display:flex;align-items:stretch;gap:10px;flex-wrap:wrap;margin-bottom:18px;}" +
			".rb-step{flex:1;min-width:150px;background:var(--h-surface-solid);border:1px solid var(--h-border);border-radius:var(--h-radius-card);padding:10px 12px;}" +
			".rb-step .n{font-weight:600;font-size:14px;line-height:22px;color:var(--h-text);}" +
			".rb-step .d{font-size:12px;line-height:20px;color:var(--h-muted);margin-top:2px;}" +
			".rb-sec{background:var(--h-surface-solid);border:1px solid var(--h-border);border-radius:var(--h-radius-card);padding:16px;margin-bottom:16px;}" +
			".rb-sec h5{font-size:16px;line-height:24px;font-weight:600;margin:0 0 12px 0;color:var(--h-text);}" +
			".rb-sec h5 .hint{font-size:12px;line-height:20px;font-weight:400;color:var(--h-muted);}" +
			".rb-sec table{width:100%;font-size:14px;line-height:22px;border-collapse:collapse;}" +
			".rb-sec th{background:var(--h-subtle);color:var(--h-text-2);font-weight:500;font-size:12px;line-height:20px;text-align:left;padding:10px 12px;border-bottom:1px solid var(--h-border-strong);white-space:nowrap;}" +
			".rb-sec td{padding:9px 12px;border-bottom:1px solid var(--h-border);color:var(--h-text);font-variant-numeric:tabular-nums;}" +
			".rb-sec tbody tr:hover td{background:var(--h-subtle);}" +
			".rb-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;}" +
			".rb-card{border:1px solid var(--h-border);border-radius:var(--h-radius-card);padding:12px 14px;cursor:pointer;background:var(--h-surface-solid);transition:border-color var(--h-motion) var(--h-ease);}" +
			".rb-card:hover{border-color:var(--h-brand);}" +
			".rb-card .t{font-weight:600;font-size:14px;line-height:22px;color:var(--h-text);}" +
			".rb-card .c{display:inline-block;background:rgba(103,95,255,.10);border-radius:var(--h-radius-pill);padding:1px 8px;font-size:12px;line-height:18px;color:var(--h-processing);margin-left:6px;}" +
			".rb-card .d{font-size:12px;line-height:20px;color:var(--h-muted);margin:6px 0;}" +
			".rb-nums{display:none;margin-top:8px;max-height:220px;overflow-y:auto;font-family:var(--h-font);font-size:12px;line-height:20px;background:var(--h-subtle);border:1px solid var(--h-border);border-radius:var(--h-radius-control);padding:8px;color:var(--h-text-2);font-variant-numeric:tabular-nums;}" +
			// 部门分区容器：此前是内联 border/#e0e0e0，收进类里便于统一改值
			".rb-dept-card{border:1px solid var(--h-border);border-radius:var(--h-radius-control);padding:12px 14px;margin-bottom:12px;background:var(--h-surface-solid);}" +
			".rb-dept-card .rb-dept-title{font-weight:500;font-size:14px;line-height:22px;color:var(--h-text);margin-bottom:8px;}" +
			".rb-dept-card .rb-dept-title .hint{font-weight:400;font-size:12px;color:var(--h-muted);}" +
			".rb-toggle-dept{font-size:12px;line-height:20px;}" +
			".rb-toolbar{display:flex;justify-content:flex-end;gap:8px;margin-bottom:12px;}" +
			"</style>").appendTo("head");
	}

	let h = "";

	// 1. 判定优先级链
	h += '<div class="rb-sec"><h5>考勤判定优先级链 <span class="hint">从上到下依次命中，命中即停</span></h5><div class="rb-chain">';
	(data.priority_chain || []).forEach(s => {
		h += '<div class="rb-step"><span class="n">' + s.step + '. ' + s.name + '</span><div class="d">' + (s.desc || '') + '</div></div>';
	});
	h += '</div></div>';

	// 2. 班次规则记录（按部门分区：全局规则排前，各部门独立表格，停用历史可展开）
	const rules = data.rules || [];
	const tableHead = '<thead><tr><th>规则名称</th><th>班次类型</th><th>上班</th><th>下班</th><th>迟到起算</th><th>最小工时</th><th>生效日期</th><th>状态</th><th>绑定人数</th></tr></thead>';
	const ruleRow = r => '<tr><td>' + r.rule_name + '</td><td>' + r.shift_type + '</td>'
		+ '<td>' + fmtTime(r.start_time) + '</td><td>' + fmtTime(r.end_time) + '</td><td>' + fmtTime(r.late_after) + '</td>'
		+ '<td>' + (r.min_hours != null ? r.min_hours : "") + '</td><td>' + r.effective_from + '</td>'
		+ '<td>' + statusBadge(r.status) + '</td><td>' + (r.assigned_count || 0) + '</td></tr>';
	// 按部门分组；部门名含「全部部门」判定为全局规则
	const byDept = {};
	(rules || []).forEach(r => { (byDept[r.department] = byDept[r.department] || []).push(r); });
	const isGlobalDept = d => (d || "").indexOf("全部部门") === 0;
	const deptNames = Object.keys(byDept).sort((a, b) => {
		const ag = isGlobalDept(a) ? 0 : 1;
		const bg = isGlobalDept(b) ? 0 : 1;
		if (ag !== bg) return ag - bg;
		return a.localeCompare(b, "zh");
	});
	h += '<div class="rb-sec"><h5>班次规则记录 <span class="hint">' + rules.length + ' 条，按部门分组；停用规则折叠在各部门内</span></h5>';
	deptNames.forEach((dept, di) => {
		const dRules = byDept[dept];
		const dActive = dRules.filter(r => r.status !== "停用");
		const dInactive = dRules.filter(r => r.status === "停用");
		const shown = dActive.length ? dActive : dRules;
		const cardTitle = isGlobalDept(dept) ? '全局规则（' + dept + '）' : dept;
		h += '<div class="rb-dept-card">';
		h += '<div class="rb-dept-title">' + cardTitle
			+ ' <span class="hint">' + dRules.length + ' 条规则</span></div>';
		h += '<table><thead>' + tableHead + '</thead><tbody>';
		shown.forEach(r => { h += ruleRow(r); });
		h += '</tbody></table>';
		if (dInactive.length) {
			h += '<div style="margin-top:8px;"><a href="#" class="rb-toggle-dept" data-di="' + di + '" data-count="' + dInactive.length + '">展开已停用历史规则（' + dInactive.length + ' 条）</a></div>';
			h += '<div class="rb-dept-inactive" data-di="' + di + '" style="display:none;"><table><thead>' + tableHead + '</thead><tbody>';
			dInactive.forEach(r => { h += ruleRow(r); });
			h += '</tbody></table></div>';
		}
		h += '</div>';
	});
	h += '</div>';


	// 3. 内置默认班次
	h += '<div class="rb-sec"><h5>内置默认班次 <span class="hint">未配置专属规则时按此判定</span></h5><table><thead><tr><th>班次</th><th>上班</th><th>下班</th><th>迟到起算</th><th>最小工时(小时)</th></tr></thead><tbody>';
	(data.builtin_shifts || []).forEach(b => {
		h += '<tr><td>' + b.shift_type + '</td><td>' + fmtTime(b.start_time) + '</td><td>' + fmtTime(b.end_time) + '</td>'
			+ '<td>' + fmtTime(b.late_after) + '</td><td>' + b.min_hours + '</td></tr>';
	});
	h += '</tbody></table></div>';

	// 4. 名单规则卡片（点击展开姓名，未建档/离职工号兜底显示工号）
	h += '<div class="rb-sec"><h5>名单规则 <span class="hint">点击卡片展开名单，未建档或已离职工号回退显示工号</span></h5><div class="rb-grid">';
	(data.lists || []).forEach(g => {
		const items = (g.names || g.nums || []);
		h += '<div class="rb-card" data-key="' + g.key + '">'
			+ '<span class="t">' + g.title + '</span><span class="c">' + g.count + ' 个</span>'
			+ '<div class="d">' + (g.desc || '') + '</div>'
			+ '<div class="rb-nums">' + items.join(' ') + '</div>'
			+ '</div>';
	});
	h += '</div></div>';

	// 5. 配对算法参数
	h += '<div class="rb-sec"><h5>配对算法参数 <span class="hint">配对上限与判定窗口的当前取值</span></h5><table><thead><tr><th>参数</th><th>值</th><th>说明</th></tr></thead><tbody>';
	(data.pairing_params || []).forEach(p => {
		h += '<tr><td>' + p.name + '</td><td>' + p.value + '</td><td>' + (p.desc || '') + '</td></tr>';
	});
	h += '</tbody></table></div>';

	$c.find(".rb-loading").replaceWith(h);

	$c.find(".rb-card").on("click", function () {
		$(this).find(".rb-nums").toggle();
	});
	// 部门分区内「展开/收起已停用历史规则」
	$c.find(".rb-toggle-dept").on("click", function (e) {
		e.preventDefault();
		const $panel = $c.find(".rb-dept-inactive[data-di='" + $(this).attr("data-di") + "']");
		const count = $(this).attr("data-count") || "";
		$panel.toggle();
		$(this).text($panel.is(":visible")
			? "收起已停用历史规则"
			: "展开已停用历史规则（" + count + " 条）");
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
	const depts = data.departments || [];
	let items = "";
	if (!depts.length) {
		items = '<li class="sm-none">没有可维护的部门。</li>';
	} else {
		depts.forEach(dept => {
			const cnt = data.dept_employee_count[dept] || 0;
			items += '<li class="sm-dept" data-dept="' + esc(dept) + '">'
				+ '<span>' + esc(dept) + '</span><span class="cnt">' + cnt + ' 人</span></li>';
		});
	}
	$dept.html('<div class="sm-panel">'
		+ '<div class="sm-panel-head">部门 <span class="hint">选中后右侧显示规则与人员</span></div>'
		+ '<ul class="sm-depts">' + items + '</ul></div>');
	$dept.find(".sm-dept").on("click", function () {
		const dept = $(this).attr("data-dept");
		$dept.find(".sm-dept").removeClass("active");
		$(this).addClass("active");
		loadDeptShifts(dept);
	});
}

function renderActiveShifts(data) {
	const $shift = $("#shift-panel").empty();
	const active = data.active_shifts || [];
	let body;
	if (!active.length) {
		body = '<div class="sm-none">当前没有进行中的班次。</div>';
	} else {
		body = '<table class="sm-tbl"><thead><tr><th>规则</th><th>班次类型</th><th>时间</th><th>状态</th></tr></thead><tbody>';
		active.forEach(s => {
			body += '<tr><td>' + esc(s.rule_name) + '</td><td>' + esc(s.shift_type) + '</td>'
				+ '<td class="num">' + fmtTime(s.start_time) + ' - ' + fmtTime(s.end_time) + '</td>'
				+ '<td><span class="h-badge h-badge--success">进行中</span></td></tr>';
		});
		body += '</tbody></table>';
	}
	$shift.html('<div class="sm-panel">'
		+ '<div class="sm-panel-head">正在进行的班次 <span class="hint">当前 ' + esc(data.now || "") + '</span></div>'
		+ body
		+ '<div class="sm-panel-foot">点击左侧部门查看该部门的班次规则和人员班次设置</div>'
		+ '</div>');
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
	let rows = "";
	if (!shifts || shifts.length === 0) {
		rows = `<tr><td colspan="8" class="sm-none">该部门暂无专属班次规则（使用「全部部门」的全局规则）</td></tr>`;
	}
	(shifts || []).forEach(s => {
		rows += `<tr>
			<td>${esc(s.rule_name)}</td>
			<td>${esc(s.shift_type)}</td>
			<td><input type="time" class="form-control form-control-sm shift-edit" data-name="${esc(s.name)}" data-field="start_time" value="${fmtTime(s.start_time)}" ${s.status === "草稿" ? "disabled" : ""}></td>
			<td><input type="time" class="form-control form-control-sm shift-edit" data-name="${esc(s.name)}" data-field="end_time" value="${fmtTime(s.end_time)}" ${s.status === "草稿" ? "disabled" : ""}></td>
			<td><input type="time" class="form-control form-control-sm shift-edit" data-name="${esc(s.name)}" data-field="late_after" value="${fmtTime(s.late_after)}" ${s.status === "草稿" ? "disabled" : ""}></td>
			<td class="num">${esc(s.effective_from)}</td>
			<td>
				<select class="form-control form-control-sm rule-status" data-name="${esc(s.name)}">
					<option value="生效" ${s.status === "生效" ? "selected" : ""}>生效</option>
					<option value="停用" ${s.status === "停用" ? "selected" : ""}>停用</option>
					<option value="草稿" ${s.status === "草稿" ? "selected" : ""}>草稿</option>
				</select>
			</td>
			<td>
				${s.status === "生效" ? `<button class="btn btn-xs btn-primary save-shift" data-name="${esc(s.name)}">保存</button>` : ""}
				<button class="btn btn-xs btn-danger delete-shift" data-name="${esc(s.name)}">删除</button>
			</td>
		</tr>`;
	});
	$shift.html(`<div class="sm-panel">
			<div class="sm-panel-head">${esc(dept)} · 班次规则 <span class="hint">改动次日生效，历史考勤不受影响</span></div>
			<table class="sm-tbl">
				<thead><tr><th>规则</th><th>班次</th><th>上班</th><th>下班</th><th>迟到起算</th><th>生效日期</th><th>状态</th><th>操作</th></tr></thead>
				<tbody>${rows}</tbody>
			</table>
			<div class="sm-panel-foot">
				<button class="btn btn-xs btn-default" id="btn-new-shift">新建班次</button>
				<button class="btn btn-xs btn-default" id="btn-new-rule">新建规则</button>
				<button class="btn btn-xs btn-default" id="btn-import-schedule">导入排班表</button>
			</div>
		</div>
		<div class="sm-panel"><div class="sm-panel-head">人员班次绑定</div><div class="sm-panel-body" id="dept-employees"><span class="sm-none">加载人员中…</span></div></div>`);


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
	// 外层 .sm-panel / .sm-panel-head 由 renderDeptShifts 提供，这里只出内容，
	// 避免面板套面板。
	const $emp = $("#dept-employees").empty();
	let rows = "";
	if (!(employees || []).length) {
		rows = `<tr><td colspan="4" class="sm-none">该部门没有在职员工。</td></tr>`;
	}
	(employees || []).forEach(e => {
		// 手动绑定优先, 否则显示系统名单班次
		const current = e.fixed_shift_name
			? esc(`${e.fixed_shift_name}（${e.fixed_shift_type}）`)
			: `<span class="sys-shift">${esc(e.system_shift || "通用倒班(按时间判定)")}</span>`;
		rows += `<tr>
			<td class="num">${esc(e.employee_number || "")}</td>
			<td>${esc(e.employee_name || "")}</td>
			<td class="bound-display" data-emp="${esc(e.name)}">${current}</td>
			<td class="shift-checkbox-cell" data-emp="${esc(e.name)}"></td>
		</tr>`;
	});
	$emp.html(`<table class="sm-tbl">
			<thead><tr><th style="width:110px;">工号</th><th style="width:110px;">姓名</th><th style="width:220px;">已绑定班次</th><th>设置班次（勾选绑定）</th></tr></thead>
			<tbody>${rows}</tbody>
		</table>
		<p class="sm-foot-note">蓝字 = 系统名单班次；勾选即绑定、取消勾选即解绑；绑定多个班次时判定按打卡时间自动匹配。</p>`);

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
		$cell.html('<span class="sm-foot-note" style="margin:0;">未绑定</span>');
		return;
	}
	let html = "";
	boundRules.forEach(r => {
		const rule = allRules.find(x => x.name === r);
		const label = rule ? `${rule.rule_name}` : r;
		html += `<span class="h-badge h-badge--info" style="margin-right:4px;">${esc(label)}</span>`;
	});
	// 字号只取契约允许的 30/20/16/14/12，此处原为 11px
	html += `<span class="sm-foot-note" style="margin:0;">（${boundRules.length} 个）</span>`;
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
	// 统一走共享徽章类：色 + 文字，不靠颜色单独承载语义（EA-4 §530）
	if (s === "生效") return `<span class="h-badge h-badge--success">生效</span>`;
	if (s === "停用") return `<span class="h-badge h-badge--neutral">停用</span>`;
	return `<span class="h-badge h-badge--warning">${esc(s)}</span>`;
}

})();
