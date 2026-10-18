frappe.pages["hbos-department-board"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper, title: __("部门看板"), single_column: true,
	});
	// HBOS 共享样式层的挂载点：只影响本容器内部，Desk 框架不受影响。
	$(wrapper).addClass("hbos-surface");


	// 设计: 概览优先。KPI 一行 → 部门汇总表（可展开）→ 人员明细内联展开。
	// 用发丝分隔线替代卡片阴影; 数字 tabular-nums 右对齐; 唯一的大数字是出勤率。
	// 部门看板自己的样式。
	//
	// 色值与字号一律走 var(--h-*)（由 hbos_attendance.bundle.css 在 .hbos-surface
	// 下定义），不再写死——写死就会与门户和其它页面漂移。
	// 字号只取契约 v2.0 允许的 30 / 20 / 16 / 14 / 12（EA-5.4 §44）。
	//
	// 强度：本页与考勤仪表盘同级，按 V2 dashboard 处理——KPI 用卡片，
	// 明细表保留密集行（V1 操作面），两者共存。
	$("<style>").text(
		// ---- 工具条：玻璃面板，与门户顶部一致 ----
		".db-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:14px 20px;background:var(--h-surface);border:1px solid var(--h-glass-border);border-radius:var(--h-radius-panel);box-shadow:var(--h-shadow);backdrop-filter:var(--h-glass-blur);-webkit-backdrop-filter:var(--h-glass-blur);margin-bottom:16px;}" +
		".db-toolbar label{font-size:12px;line-height:20px;color:var(--h-text-2);margin:0;font-weight:500;}" +
		".db-toolbar .db-ctl{display:inline-flex;align-items:center;gap:6px;}" +
		// 内容区也是一块玻璃面板，表格浮在画布之上
		".db-wrap{padding:20px 20px 28px;background:var(--h-surface);border:1px solid var(--h-glass-border);border-radius:var(--h-radius-panel);box-shadow:var(--h-shadow);backdrop-filter:var(--h-glass-blur);-webkit-backdrop-filter:var(--h-glass-blur);}" +
		".db-num{font-variant-numeric:tabular-nums;font-feature-settings:'tnum';}" +

		// ---- KPI：V2 玻璃卡（与门户 .glass-surface 同一做法）----
		".db-kpi{display:flex;gap:16px;flex-wrap:wrap;margin:0 0 16px;}" +
		".db-hero,.db-kpi-i{flex:1;min-width:140px;background:var(--h-surface);border:1px solid var(--h-glass-border);border-radius:var(--h-radius-card);box-shadow:var(--h-shadow);backdrop-filter:var(--h-glass-blur);-webkit-backdrop-filter:var(--h-glass-blur);padding:20px 16px;text-align:center;transition:transform var(--h-motion) var(--h-ease),box-shadow var(--h-motion) var(--h-ease),background var(--h-motion) var(--h-ease);}" +
		".db-hero:hover,.db-kpi-i:hover{transform:translateY(-5px);background:rgba(255,255,255,.91);box-shadow:var(--h-shadow-hover);}" +
		// 出勤率是这组里唯一的主数字，用域色条强调；其余用同一条但更短更淡
		".db-hero::before,.db-kpi-i::before{content:'';display:block;height:3px;width:32px;margin:0 auto 12px;border-radius:var(--h-radius-pill);background:var(--h-accent);}" +
		".db-kpi-i::before{opacity:.45;}" +
		".db-hero .v{font-size:30px;line-height:38px;font-weight:600;color:var(--h-text);letter-spacing:-0.01em;}" +
		".db-hero .k{font-size:12px;line-height:20px;color:var(--h-muted);margin-top:4px;}" +
		".db-kpis{display:contents;}" +
		".db-kpi-i .v{font-size:30px;line-height:38px;font-weight:600;color:var(--h-text);}" +
		".db-kpi-i .k{font-size:12px;line-height:20px;color:var(--h-muted);margin-top:4px;}" +
		".db-kpi-i.warn .v{color:var(--h-warning);}" +
		".db-kpi-i.bad .v{color:var(--h-critical);}" +

		// ---- 分节标题 ----
		".db-sec{display:flex;align-items:baseline;justify-content:space-between;margin:24px 0 12px;}" +
		".db-sec h5{margin:0;font-size:16px;line-height:24px;font-weight:600;color:var(--h-text);}" +
		".db-sec .hint{font-size:12px;line-height:20px;color:var(--h-muted);}" +

		// ---- 明细表（V1 操作面：密集行、表头吸顶）----
		".db-tbl{width:100%;border-collapse:collapse;font-size:14px;line-height:22px;}" +
		".db-tbl th{text-align:left;font-weight:500;font-size:12px;line-height:20px;color:var(--h-text-2);padding:10px 12px;border-bottom:1px solid var(--h-border-strong);white-space:nowrap;background:var(--h-subtle);position:sticky;top:0;z-index:1;}" +
		".db-tbl td{padding:9px 12px;border-bottom:1px solid var(--h-border);color:var(--h-text);vertical-align:middle;}" +
		".db-tbl th.r,.db-tbl td.r{text-align:right;}" +
		".db-tbl tbody tr:hover td{background:var(--h-subtle);}" +
		".db-dept-row{cursor:pointer;}" +
		".db-dept-row .nm{font-weight:500;}" +
		".db-dept-row .caret{display:inline-block;width:12px;color:var(--h-muted);font-size:12px;transition:transform var(--h-motion) var(--h-ease);}" +
		".db-dept-row.open .caret{transform:rotate(90deg);}" +
		".db-zero{color:var(--h-muted);opacity:.5;}" +
		".db-strong{font-weight:600;}" +
		".db-detail td{background:var(--h-subtle);padding:0;border-bottom:1px solid var(--h-border);}" +
		".db-detail .inner{padding:2px 10px 8px 26px;}" +
		".db-tbl.mini th{font-size:12px;color:var(--h-muted);padding:6px 10px;border-bottom:1px solid var(--h-border);}" +
		".db-tbl.mini td{padding:6px 10px;font-size:12px;line-height:20px;border-bottom:1px solid var(--h-border);}" +
		".db-tbl.mini tbody tr:last-child td{border-bottom:none;}" +

		// ---- 状态色块：统一走 status token，一律「色 + 文字」----
		".db-s{display:inline-block;padding:2px 8px;border-radius:var(--h-radius-pill);font-size:12px;line-height:18px;white-space:nowrap;font-weight:500;}" +
		".s-green{background:rgba(27,188,134,.12);color:var(--h-success);}" +
		".s-red{background:rgba(237,90,114,.12);color:var(--h-critical);}" +
		".s-amber{background:rgba(244,165,35,.14);color:var(--h-warning);}" +
		".s-blue{background:rgba(75,156,255,.12);color:var(--h-info);}" +
		".s-purple{background:rgba(103,95,255,.12);color:var(--h-processing);}" +
		".s-grey{background:rgba(114,130,157,.12);color:var(--h-neutral);}" +
		".db-chip{font-size:12px;color:var(--h-muted);margin-left:6px;}" +
		".db-note{font-size:12px;line-height:20px;color:var(--h-text-2);padding:4px 2px 10px;}" +
		".db-empty{padding:32px 16px;text-align:center;color:var(--h-muted);font-size:14px;}" +
		".db-updating{font-size:12px;color:var(--h-muted);margin-left:auto;opacity:0;transition:opacity var(--h-motion) var(--h-ease);}" +
		".db-updating.on{opacity:1;}"
	).appendTo("head");

	var fmt = function (d) {
		return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
	};

	var state = {
		dept: "全部部门",
		date: fmt(new Date()),
		onlyAttention: false,
		openDepts: {},      // 展开的部门（轮询刷新后保持）
		timer: null,
		inFlight: false,
	};

	var toolbar = '<div class="db-toolbar">'
		+ '<span class="db-ctl"><label>' + __("部门") + '</label>'
		+ '<select id="db-dept" class="form-control input-xs" style="width:170px;"><option value="全部部门">' + __("全部部门") + '</option></select></span>'
		+ '<span class="db-ctl"><label>' + __("日期") + '</label>'
		+ '<input type="date" id="db-date" class="form-control input-xs" style="width:140px;" value="' + state.date + '" max="' + state.date + '"></span>'
		+ '<button class="btn btn-primary btn-xs" id="db-go">' + __("查询") + '</button>'
		+ '<span class="db-ctl"><label class="db-chk" style="margin:0;font-weight:400;">'
		+ '<input type="checkbox" id="db-only-attention"> ' + __("只看异常") + '</label></span>'
		+ '<span class="db-ctl"><label style="margin:0;font-weight:400;">'
		+ '<input type="checkbox" id="db-autorefresh" checked> ' + __("自动刷新(60s)") + '</label></span>'
		+ '<button class="btn btn-default btn-xs" id="db-sync" style="display:none;">' + __("立即同步打卡") + '</button>'
		+ '<span id="db-sync-msg" class="db-chip" style="margin-left:0;"></span>'
		+ '<span class="db-updating db-num" id="db-updating">' + __("更新中…") + '</span>'
		+ '</div>';
	toolbar += '<div class="db-wrap" id="db-content"></div>';
	$(wrapper).html(toolbar);

	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data.get_data",
		args: { date_str: state.date },
		callback: function (r) { if (r.message && r.message.departments) populateDepts(r.message.departments); }
	});

	function populateDepts(depts) {
		var sel = $("#db-dept");
		(depts || []).forEach(function (d) {
			// 部门名来自 tabEmployee.department，是用户可写数据；与下方各渲染处一致做转义
			var nm = frappe.utils.escape_html(d.name || "");
			if (nm) sel.append('<option value="' + nm + '">' + nm + " (" + d.count + ")");
		});
	}

	// ---- 状态语义（与后端 state 串一一对应）----
	var ATTENTION_STATES = { late: 1, absent_day: 1, absent_expected: 1, no_pair: 1, fact_none: 1, out_offwindow: 1, out_only: 1 };

	function cls(state, r) {
		if (r && r.anomaly_hidden) return "s-grey";                          // 不显示异常 → 中性
		if (state === "late" || state === "absent_day") return "s-red";      // 仅确凿定性用红
		if (state === "present" || state === "out_day" || state === "fact_present") return "s-green";
		if (state === "leave") return "s-purple";
		if (state === "rest") return "s-blue";
		if (state === "exempt") return "s-grey";
		return "s-amber";                                                    // 未打卡/待确认等一律中性琥珀
	}

	// 删掉逐行重复的长说明，只保留有信息量的短标记
	var NOTE_MAP = {
		"以 HRMS 考勤结果为准": "",
		"班次起算点待排班/规则确认，仅记录打卡事实": "班次待定",
		"仅记录打卡事实，不判到点/迟到（班次起算点待排班/规则确认）": "班次待定",
		"当日有排班/固定班次但无配对考勤记录，未判缺勤": "未判缺勤",
		"当日有卡但无 HRMS 配对考勤结果": "无配对考勤",
		"班次时段内无卡，未定性为缺勤，请以月度考勤汇总为准": "未定性缺勤",
		"当天仅有下班卡，无到岗卡，未判迟到/缺勤": "仅下班卡",
		"排班标注请假但当天有打卡，请人工核实": "有卡请核实",
	};
	function shortNote(note) {
		if (!note) return "";
		return NOTE_MAP.hasOwnProperty(note) ? NOTE_MAP[note] : note;
	}

	// 状态文案：「已下班 HH:MM」只在有可信下班卡时追加
	// （后端按设备 SN 判定 + 最短班次 2h，避免误刷/上班卡伪造已下班）
	function statusText(r) {
		var t = __(r.label || r.state);
		if (r.out_hm) t += " · " + __("已下班") + " " + r.out_hm;
		return t;
	}

	function hasTag(r, t) { return (r.tags || []).indexOf(t) >= 0; }
	// 看板不显示异常的人（anomaly_hidden，如设备动力部）：只展示打卡事实，
	// 不标迟到/缺勤，也不算「异常」（只看异常不列出、排序不置顶）
	function isLate(r) { return !r.anomaly_hidden && (r.state === "late" || hasTag(r, "迟到")); }
	function needsAttention(r) { return !r.anomaly_hidden && (isLate(r) || !!ATTENTION_STATES[r.state]); }
	function rowTags(r) { return r.anomaly_hidden ? [] : (r.tags || []); }

	function groupByDept(rows) {
		var out = {};
		rows.forEach(function (r) {
			var d = r.dept || "未分组";
			(out[d] = out[d] || []).push(r);
		});
		return out;
	}

	function detailSort(a, b) {
		var pa = needsAttention(a) ? 0 : 1, pb = needsAttention(b) ? 0 : 1;
		if (pa !== pb) return pa - pb;
		return String(a.num || "").localeCompare(String(b.num || ""));
	}

	function kpiHtml(s) {
		var rate = s.attendance_rate;
		var h = '<div class="db-kpi">';
		h += '<div class="db-hero"><div class="v db-num">' + (rate == null ? "—" : rate + "%") + '</div>'
			+ '<div class="k">' + __("出勤率") + '</div></div>';
		h += '<div class="db-kpis db-num">';
		[["应出勤", s.expected, ""], ["已到岗", s.present, ""],
		 ["迟到", s.late, "bad"], ["未打卡", s.noCard, "warn"],
		 ["缺勤", s.absent, "bad"], ["请假", s.leave, ""],
		 ["休息", s.rest, ""]].forEach(function (c) {
			h += '<div class="db-kpi-i ' + c[2] + '"><div class="v">' + c[1] + '</div><div class="k">' + __(c[0]) + '</div></div>';
		});
		h += '</div></div>';
		// 非预警桶单列一行，避免与「未打卡」混淆（9 点时这两类人最多）
		var others = [["仅下班卡", s.outOnly], ["班次未定", s.unknownTime], ["未开始", s.notStarted]]
			.filter(function (x) { return x[1]; });
		if (others.length) {
			h += '<div class="db-note db-num">' + __("其他") + "：" +
				others.map(function (x) { return __(x[0]) + " " + x[1]; }).join(" · ") +
				'<span class="db-chip">' + __("（不计入未打卡）") + "</span></div>";
		}
		return h;
	}

	function deptTableHtml(deptStats, byDept) {
		var h = '<div class="db-sec"><h5>' + __("部门概览") + '</h5>'
			+ '<span class="hint">' + __("点击部门行展开人员明细") + '</span></div>';
		h += '<table class="db-tbl"><thead><tr>'
			+ '<th>' + __("部门") + '</th>'
			+ '<th class="r">' + __("在册") + '</th><th class="r">' + __("应出勤") + '</th>'
			+ '<th class="r">' + __("已到岗") + '</th><th class="r">' + __("迟到") + '</th>'
			+ '<th class="r">' + __("无打卡") + '</th><th class="r">' + __("缺勤") + '</th>'
			+ '<th class="r">' + __("请假") + '</th>'
			+ '</tr></thead><tbody>';
		deptStats.forEach(function (d) {
			var open = !!state.openDepts[d.dept];
			h += '<tr class="db-dept-row' + (open ? " open" : "") + '" data-dept="' + frappe.utils.escape_html(d.dept) + '">';
			h += '<td class="nm"><span class="caret">▶</span> ' + frappe.utils.escape_html(d.dept) + '</td>';
			h += '<td class="r db-num">' + d.total + '</td>';
			h += '<td class="r db-num">' + d.expected + '</td>';
			h += '<td class="r db-num">' + d.present + '</td>';
			h += '<td class="r db-num">' + (d.late ? '<span class="db-strong" style="color:var(--h-critical);">' + d.late + '</span>' : '<span class="db-zero">0</span>') + '</td>';
			h += '<td class="r db-num">' + (d.noCard ? '<span class="db-strong" style="color:var(--h-warning);">' + d.noCard + '</span>' : '<span class="db-zero">0</span>') + '</td>';
			h += '<td class="r db-num">' + (d.absent ? '<span class="db-strong" style="color:var(--h-critical);">' + d.absent + '</span>' : '<span class="db-zero">0</span>') + '</td>';
			h += '<td class="r db-num">' + (d.leave ? d.leave : '<span class="db-zero">0</span>') + '</td>';
			h += '</tr>';
			if (open) h += detailRowHtml(byDept[d.dept] || [], 8);
		});
		h += '</tbody></table>';
		return h;
	}

	function detailRowHtml(rows, span) {
		var list = rows.slice().sort(detailSort);
		if (state.onlyAttention) list = list.filter(needsAttention);
		var inner;
		if (!list.length) {
			inner = '<div class="db-empty">' + (state.onlyAttention ? __("该部门无异常") : __("无人员")) + '</div>';
		} else {
			inner = '<table class="db-tbl mini"><thead><tr>'
				+ '<th>' + __("工号") + '</th><th>' + __("姓名") + '</th><th>' + __("班次") + '</th>'
				+ '<th>' + __("状态") + '</th><th class="r">' + __("首卡") + '</th><th class="r">' + __("卡数") + '</th>'
				+ '</tr></thead><tbody>';
			list.forEach(function (r) {
				var tags = rowTags(r).map(function (t) {
					return '<span class="db-s s-red">' + frappe.utils.escape_html(t) + '</span>';
				}).join("");
				var note = shortNote(r.note);
				inner += '<tr>'
					+ '<td class="db-num">' + frappe.utils.escape_html(r.num || "-") + '</td>'
					+ '<td>' + frappe.utils.escape_html(r.name || "-") + '</td>'
					+ '<td>' + __(frappe.utils.escape_html(r.expected_label || "-")) + '</td>'
					+ '<td><span class="db-s ' + cls(r.state, r) + '">' + frappe.utils.escape_html(statusText(r)) + '</span>'
					+ (tags ? " " + tags : "") + (note ? '<span class="db-chip">' + __(note) + '</span>' : "") + '</td>'
					+ '<td class="r db-num">' + (r.first_hm || "-") + '</td>'
					+ '<td class="r db-num">' + (r.card_count || 0) + '</td>'
					+ '</tr>';
			});
			inner += '</tbody></table>';
		}
		return '<tr class="db-detail"><td colspan="' + span + '"><div class="inner">' + inner + '</div></td></tr>';
	}

	function flatTableHtml(rows) {
		var list = rows.slice().sort(detailSort);
		if (state.onlyAttention) list = list.filter(needsAttention);
		var h = '<div class="db-sec"><h5>' + __("人员明细") + '</h5>'
			+ '<span class="hint db-num">' + list.length + ' / ' + rows.length + ' ' + __("人") + '</span></div>';
		if (!list.length) return h + '<div class="db-empty">' + (state.onlyAttention ? __("当前范围无异常") : __("当前范围无在册员工")) + '</div>';
		h += '<table class="db-tbl"><thead><tr>'
			+ '<th>' + __("工号") + '</th><th>' + __("姓名") + '</th><th>' + __("部门") + '</th><th>' + __("班次") + '</th>'
			+ '<th>' + __("状态") + '</th><th class="r">' + __("首卡") + '</th><th class="r">' + __("卡数") + '</th>'
			+ '</tr></thead><tbody>';
		list.forEach(function (r) {
			var tags = rowTags(r).map(function (t) {
				return '<span class="db-s s-red">' + frappe.utils.escape_html(t) + '</span>';
			}).join("");
			var note = shortNote(r.note);
			h += '<tr>'
				+ '<td class="db-num">' + frappe.utils.escape_html(r.num || "-") + '</td>'
				+ '<td>' + frappe.utils.escape_html(r.name || "-") + '</td>'
				+ '<td>' + frappe.utils.escape_html(r.dept || "-") + '</td>'
				+ '<td>' + __(frappe.utils.escape_html(r.expected_label || "-")) + '</td>'
				+ '<td><span class="db-s ' + cls(r.state, r) + '">' + frappe.utils.escape_html(statusText(r)) + '</span>'
				+ (tags ? " " + tags : "") + (note ? '<span class="db-chip">' + __(note) + '</span>' : "") + '</td>'
				+ '<td class="r db-num">' + (r.first_hm || "-") + '</td>'
				+ '<td class="r db-num">' + (r.card_count || 0) + '</td>'
				+ '</tr>';
		});
		h += '</tbody></table>';
		return h;
	}

	function render(data) {
		var d = data.meta || {};
		var rows = data.rows || [];
		var container = $("#db-content");
		page.set_title(__("部门看板") + " — " + d.scope + " · " + d.date +
			(d.mode === "live" ? " · " + __("实时") + " " + (d.now_hm || "") : " · " + __("回顾")));

		var scrollTop = (document.scrollingElement || document.documentElement).scrollTop;

		var h = kpiHtml(data.stats || {});
		if (!rows.length) {
			h += '<div class="db-empty">' + __("当前范围无在册员工") + '</div>';
		} else if (d.scope && d.scope !== "全部部门") {
			h += flatTableHtml(rows);          // 单部门：直接明细，不要多余的汇总层
		} else {
			h += deptTableHtml(data.dept_stats || [], groupByDept(rows));
		}
		container.html(h);
		(document.scrollingElement || document.documentElement).scrollTop = scrollTop;

		container.find(".db-dept-row").on("click", function () {
			var name = $(this).attr("data-dept");
			if (state.openDepts[name]) delete state.openDepts[name];
			else state.openDepts[name] = true;
			$(this).toggleClass("open");
			var deptRows = groupByDept(rows)[name] || [];
			if (state.openDepts[name]) {
				// 部门表共 8 列（部门 + 在册/应出勤/已到岗/迟到/未打卡/缺勤/请假），
				// colspan 必须与之一致，否则展开的明细行错位
				$(detailRowHtml(deptRows, 8)).insertAfter($(this));
			} else {
				$(this).next(".db-detail").remove();
			}
		});
	}

	function isLive() { return state.date === fmt(new Date()); }

	function load(opts) {
		opts = opts || {};
		if (state.inFlight) return;
		state.inFlight = true;
		$("#db-sync").toggle(isLive());
		var silent = !!opts.silent;            // 轮询静默刷新：不闪屏、不打断阅读
		if (silent) $("#db-updating").addClass("on");
		else $("#db-content").html('<div class="db-empty">' + __("加载考勤数据…") + "</div>");
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data.get_data",
			args: { department: state.dept, date_str: state.date },
			callback: function (r) {
				state.inFlight = false;
				$("#db-updating").removeClass("on");
				if (r.message && r.message.meta) render(r.message);
				else $("#db-content").html('<div class="db-empty" style="color:var(--h-critical);">' + __("无法加载数据") + "</div>");
			},
			error: function (r) {
				state.inFlight = false;
				$("#db-updating").removeClass("on");
				// r.message 是服务端回传的错误文本（可能含 frappe.throw 里带的用户输入），
				// 拼进 HTML 前先转义，避免把异常信息变成注入面
				var msg = (r && r.message)
					? frappe.utils.escape_html(String(r.message))
					: __("加载失败，请重试");
				if (!silent) $("#db-content").html('<div class="db-empty" style="color:var(--h-critical);">' + msg + "</div>");
			}
		});
	}

	function go() {
		state.dept = $("#db-dept").val() || "全部部门";
		state.date = $("#db-date").val() || fmt(new Date());
		state.openDepts = {};
		stopPoll(); load(); startPoll();
	}

	$("#db-go").on("click", go);
	$("#db-dept").on("change", go);
	$("#db-only-attention").on("change", function () {
		state.onlyAttention = $(this).is(":checked");
		load();
	});
	$("#db-autorefresh").on("change", function () { if ($(this).is(":checked")) startPoll(); else stopPoll(); });

	$("#db-sync").on("click", function () {
		if ($(this).prop("disabled")) return;
		$(this).prop("disabled", true);
		$("#db-sync-msg").text(__("同步中…"));
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data.live_sync",
			callback: function (r) {
				var m = r.message || {};
				$("#db-sync-msg").text(m.throttled ? __("请稍后再试(" + m.seconds_left + "s)") : (m.error ? __(m.error) : __("同步完成")));
				setTimeout(function () { $("#db-sync").prop("disabled", false); load({ silent: true }); }, 1500);
			},
			error: function () {
				$("#db-sync-msg").text(__("同步失败"));
				$("#db-sync").prop("disabled", false);
			}
		});
	});

	function startPoll() {
		stopPoll();
		if (!$("#db-autorefresh").is(":checked") || !isLive()) return;
		state.timer = setInterval(function () {
			if (document.visibilityState === "visible") load({ silent: true });
		}, 60000);
	}
	function stopPoll() { if (state.timer) { clearInterval(state.timer); state.timer = null; } }
	$(document).on("visibilitychange", function () {
		if (document.visibilityState === "visible") { load({ silent: true }); startPoll(); }
		else stopPoll();
	});

	load(); startPoll();
};
