frappe.pages["hbos-department-board"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper, title: __("部门看板"), single_column: true,
	});

	$("<style>").text(
		".db-stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;}" +
		".db-stat{flex:1;min-width:110px;background:#fff;border-radius:8px;padding:14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.07);}" +
		".db-stat .num{font-size:24px;font-weight:700;}" +
		".db-stat .lbl{font-size:12px;color:#888;margin-top:2px;}" +
		".db-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:8px 16px;background:#fff;border-bottom:1px solid #e0e0e0;margin-bottom:16px;}" +
		".db-dept-card{background:#fff;border-radius:8px;padding:14px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,0.05);}" +
		".db-dept-card h5{margin:0 0 8px 0;font-size:15px;color:#333;}" +
		".db-table{width:100%;font-size:13px;border-collapse:collapse;}" +
		".db-table th{background:#f7f8fa;text-align:left;padding:7px;border-bottom:2px solid #e0e0e0;}" +
		".db-table td{padding:6px 7px;border-bottom:1px solid #f0f0f0;}" +
		".badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;margin-right:4px;}" +
		".b-green{background:#e6f7e6;color:#1e8e3e;}" +
		".b-red{background:#fde8e8;color:#c0392b;}" +
		".b-amber{background:#fef3e4;color:#e67e22;}" +
		".b-grey{background:#eef1f4;color:#5f6b7a;}" +
		".b-blue{background:#e8f1fb;color:#2c7be5;}" +
		".b-purple{background:#f3e8ff;color:#7c3aed;}" +
		".b-orange{background:#fff1e0;color:#e67e22;}"
	).appendTo("head");

	var today = new Date();
	var fmt = function (d) {
		return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
	};

	var state = { dept: "全部部门", date: fmt(today), poll: true, timer: null, loading: false };

	var toolbar = '<div class="db-toolbar">'
		+ '<label style="font-size:13px;font-weight:600;">' + __("部门") + '</label> '
		+ '<select id="db-dept" class="form-control" style="width:180px;display:inline-block;"><option value="全部部门">' + __("全部部门") + '</option></select> '
		+ '<label style="font-size:13px;font-weight:600;">' + __("日期") + '</label> '
		+ '<input type="date" id="db-date" class="form-control" style="width:150px;display:inline-block;" value="' + state.date + '" max="' + state.date + '"> '
		+ '<button class="btn btn-primary btn-sm" id="db-go">' + __("查询") + '</button> '
		+ '<label class="checkbox" style="font-size:13px;margin:0 0 0 8px;"><input type="checkbox" id="db-autorefresh" checked> ' + __("自动刷新(60s)") + '</label> '
		+ '<button class="btn btn-secondary btn-sm" id="db-sync" style="display:none;">' + __("立即同步打卡") + '</button>'
		+ '<span id="db-sync-msg" style="font-size:12px;color:#888;"></span>'
		+ '</div>';
	toolbar += '<div id="db-content" style="padding:0 16px 16px;"></div>';
	$(wrapper).html(toolbar);

	// 加载部门下拉
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data.get_data",
		args: { date_str: state.date },
		callback: function (r) { if (r.message && r.message.departments) populateDepts(r.message.departments); }
	});

	function populateDepts(depts) {
		var sel = $("#db-dept");
		(depts || []).forEach(function (d) {
			if (d.name) {
				sel.append('<option value="' + d.name + '">' + d.name + " (" + d.count + ")</option>");
			}
		});
	}

	var colorFor = function (s) {
		if (s === "late" || s === "absent_day" || s === "absent_expected") return "b-red";
		if (s === "present") return "b-green";
		if (s === "leave") return "b-purple";
		if (s === "rest") return "b-blue";
		if (s === "exempt") return "b-grey";
		return "b-amber";
	};

	function render(data) {
		var d = data.meta || {};
		var s = data.stats || {};
		var rows = data.rows || [];
		var container = $("#db-content");
		page.set_title(__("部门看板") + " — " + d.scope + " · " + d.date +
			(d.mode === "live" ? " · 实时 " + (d.now_hm || "") : " · 回顾"));

		var h = '<div class="db-stats">';
		[["total", __("在册"), "#2c3e50"], ["expected", __("应出勤"), "#2c3e50"],
		 ["present", __("已到岗"), "#27ae60"], ["late", __("迟到"), "#e74c3c"],
		 ["no_card", __("未打卡/无考勤"), "#e67e22"], ["leave", __("请假"), "#8e44ad"],
		 ["rest", __("休息"), "#3498db"], ["exempt", __("豁免"), "#7f8c8d"],
		 ["unknown", __("待确认"), "#95a5a6"]].forEach(function (c) {
			h += '<div class="db-stat"><div class="num" style="color:' + c[2] + ';">' + (s[c[0]] || 0) +
				'</div><div class="lbl">' + __(c[1]) + "</div></div>";
		});
		if (s.attendance_rate != null) {
			h += '<div class="db-stat"><div class="num" style="color:#16a085;">' + s.attendance_rate + "%</div><div class=\"lbl\">" + __("出勤率") + "</div></div>";
		}
		h += "</div>";

		var byDept = {};
		rows.forEach(function (r) { (byDept[r.dept || "未分组"] = byDept[r.dept || "未分组"] || []).push(r); });
		Object.keys(byDept).sort().forEach(function (dept) {
			h += '<div class="db-dept-card"><h5>' + __(dept) + " <span style=\"font-weight:400;font-size:12px;color:#888;\">" + byDept[dept].length + " 人</span></h5>";
			h += '<div class="db-table-scroll" style="max-height:420px;overflow-y:auto;"><table class="db-table"><thead><tr>';
			h += "<th>" + __("工号") + "</th><th>" + __("姓名") + "</th><th>" + __("期望班次") + "</th><th>" + __("状态") + "</th><th>" + __("首卡") + "</th><th>" + __("卡数") + "</th><th>" + __("说明") + "</th>";
			h += "</tr></thead><tbody>";
			byDept[dept].forEach(function (r) {
				var tags = (r.tags || []).map(function (t) {
					return '<span class="badge b-red">' + __(t) + "</span>";
				}).join("");
				h += "<tr><td>" + (r.num || "-") + "</td><td>" + (r.name || "-") + "</td><td>" + __(r.expected_label || "-") + "</td>";
				h += "<td><span class=\"badge " + colorFor(r.state) + "\">" + __(r.label || r.state) + "</span>" + tags + "</td>";
				h += "<td>" + (r.first_hm || "-") + "</td><td>" + (r.card_count || 0) + "</td><td style=\"font-size:12px;color:#888;\">" + __(r.note || "") + "</td>";
				h += "</tr>";
			});
			h += "</tbody></table></div></div>";
		});
		if (!rows.length) h = '<div class="p-5 text-center text-muted">' + __("当前范围无在册员工") + "</div>";
		container.html(h);
	}

	function isLive() {
		return state.date === fmt(new Date());
	}

	function load() {
		if (state.loading) return;
		state.loading = true;
		$("#db-sync").toggle(isLive());
		$("#db-content").html('<div class="text-center p-5"><div class="spinner-border text-primary"></div><p class="mt-2 text-muted">' + __("加载考勤数据...") + "</p></div>");
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_department_board.department_board_data.get_data",
			args: { department: state.dept, date_str: state.date },
			callback: function (r) {
				state.loading = false;
				if (r.message && r.message.meta) render(r.message);
				else $("#db-content").html('<div class="p-5 text-center text-danger">' + __("无法加载数据") + "</div>");
			},
			error: function (r) {
				state.loading = false;
				var msg = (r && r.message) ? __(r.message) : __("加载失败，请重试");
				$("#db-content").html('<div class="p-5 text-center text-danger">' + msg + "</div>");
			}
		});
	}

	function go() {
		state.dept = $("#db-dept").val() || "全部部门";
		state.date = $("#db-date").val() || fmt(new Date());
		stopPoll(); load(); startPoll();
	}

	$("#db-go").on("click", go);
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
				setTimeout(function () { $("#db-sync").prop("disabled", false); load(); }, 1500);
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
			if (document.visibilityState === "visible") load();
		}, 60000);
	}
	function stopPoll() { if (state.timer) { clearInterval(state.timer); state.timer = null; } }
	$(document).on("visibilitychange", function () {
		if (document.visibilityState === "visible") { load(); startPoll(); }
		else stopPoll();
	});

	load(); startPoll();
};
