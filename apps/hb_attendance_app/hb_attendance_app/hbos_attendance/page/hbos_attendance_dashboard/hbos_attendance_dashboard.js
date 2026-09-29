frappe.pages["hbos-attendance-dashboard"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("考勤异常仪表盘"),
		single_column: true,
	});
	// HBOS 共享样式层的挂载点：只影响本容器内部，Desk 框架不受影响。
	$(wrapper).addClass("hbos-surface");


	// Inject CSS —— 对齐 HBOS 设计系统的 V2 仪表盘 / V1 操作面。
	//
	// 依据：docs/experience/EA-4_DESIGN_SYSTEM_V1.md（token）、
	// EA-5.4_COMPONENT_INTERACTION_SPEC.md（字号契约 v2.0）、
	// P4_THREE_APP_FRONTEND_STRENGTHENING_PLAN.md（考勤定位 = V2 dashboard + V1 操作）。
	//
	// 字面量而非 var(...)：本页跑在 Frappe Desk 里，portal 的 tokens.css 不在
	// 这个文档中，引用它的自定义属性会静默落空。故把值抄在这里，值本身与
	// frontend/hbos-portal-web/src/theme/tokens.css 保持一致；两处若漂移，
	// 以 tokens.css 为准。
	//
	// 范围：只做「自定义 Desk 页面内部」的对齐（P4 计划对 Inventory 的同一做法）。
	// 不碰 Frappe Desk 外壳（EA-4 §38 要求 Desk 保留自身身份）。
	// 强度分档：KPI/图表 = V2（中等玻璃、域色、轻动效）；筛选/表格 = V1
	//（实色、无模糊无动效、密集行、表头吸顶，效率优先）。
	//
	// 字号只取契约允许的 30 / 20 / 16 / 14 / 12。原稿的 28 / 15 / 13 均被
	// v2.0 明文禁止（EA-5.4 §44）。
	var H = {
		canvas: "#f4f8fd", surface: "#ffffff", subtle: "#f7f9fc",
		border: "rgba(65,91,138,.10)", borderStrong: "rgba(65,91,138,.16)",
		textPrimary: "#17253c", textSecondary: "#425675", textMuted: "#72829d",
		warning: "#f4a523", critical: "#ed5a72", success: "#1bbc86",
		accentFrom: "#6b60ff", accentTo: "#8c61ff",
		radiusControl: "12px", radiusCard: "18px", radiusPill: "999px",
		shadowCard: "0 18px 56px rgba(47,72,117,.09)",
		shadowHover: "0 24px 72px rgba(47,72,117,.14)",
		font: 'Inter, "SF Pro Display", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif',
		ease: "cubic-bezier(.2,0,0,1)",
		motionFast: "160ms",
	};
	// badge 只为「有值」的行生成；0 值直接渲染成灰色正文，不再用彩色徽章。
	// 状态一律「色 + 文字/数字」，不靠颜色单独承载语义（EA-4 §530）。
	$("<style>").text(
		".hbos-dash{font-family:" + H.font + ";color:" + H.textPrimary + ";}" +

		// ---- 顶部筛选：V1 操作面，实色、无动效 ----
		".dash-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 16px;background:" + H.surface + ";border:1px solid " + H.border + ";border-radius:" + H.radiusControl + ";margin-bottom:16px;}" +
		".dash-toolbar label{font-size:12px;color:" + H.textSecondary + ";margin:0;}" +

		// ---- KPI：V2 仪表盘面，域色、轻动效 ----
		".dash-stats{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;}" +
		".dash-stat{flex:1;min-width:140px;background:" + H.surface + ";border:1px solid " + H.border + ";border-radius:" + H.radiusCard + ";padding:20px 16px;text-align:center;box-shadow:" + H.shadowCard + ";transition:transform " + H.motionFast + " " + H.ease + ",box-shadow " + H.motionFast + " " + H.ease + ";}" +
		".dash-stat:hover{transform:translateY(-2px);box-shadow:" + H.shadowHover + ";}" +
		".dash-stat .num{font-size:30px;line-height:38px;font-weight:600;font-variant-numeric:tabular-nums;}" +
		".dash-stat .lbl{font-size:12px;line-height:20px;color:" + H.textMuted + ";margin-top:4px;}" +
		// 顶部一道 3px 域色条，是这组卡片唯一的「V2 装饰」，不动数据本身
		".dash-stat .rule{height:3px;border-radius:" + H.radiusPill + ";margin:0 auto 12px;width:32px;background:linear-gradient(135deg," + H.accentFrom + "," + H.accentTo + ");}" +

		// ---- 图表卡：V2 ----
		".dash-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}" +
		".dash-grid .full{grid-column:1/-1;}" +
		".chart-card{background:" + H.surface + ";border:1px solid " + H.border + ";border-radius:" + H.radiusCard + ";padding:20px;box-shadow:" + H.shadowCard + ";}" +
		".chart-card h5{font-size:16px;line-height:24px;font-weight:600;margin:0 0 12px 0;color:" + H.textPrimary + ";}" +
		".cwrap{width:100%;height:380px;}" +
		".cwrap.tall{height:460px;}" +

		// ---- 明细表：V1 操作面，密集行、表头吸顶 ----
		".table-card{background:" + H.surface + ";border:1px solid " + H.border + ";border-radius:" + H.radiusCard + ";padding:20px;box-shadow:" + H.shadowCard + ";margin-top:16px;}" +
		".table-card h5{font-size:16px;line-height:24px;font-weight:600;margin:0 0 12px 0;color:" + H.textPrimary + ";}" +
		".table-card table{width:100%;font-size:14px;line-height:22px;border-collapse:collapse;}" +
		".table-card th{background:" + H.subtle + ";color:" + H.textSecondary + ";font-weight:500;text-align:left;padding:10px 12px;border-bottom:1px solid " + H.borderStrong + ";position:sticky;top:0;}" +
		".table-card td{padding:9px 12px;border-bottom:1px solid " + H.border + ";color:" + H.textPrimary + ";font-variant-numeric:tabular-nums;}" +
		".table-card tr:hover td{background:" + H.subtle + ";}" +
		".table-card .muted{color:" + H.textMuted + ";}" +
		".table-scroll{max-height:500px;overflow-y:auto;}" +

		// ---- 状态徽章：只用 token 里的 status 色，且带数字（色 + 文字） ----
		".hbos-badge{display:inline-block;min-width:24px;padding:2px 8px;border-radius:" + H.radiusPill + ";font-size:12px;line-height:18px;font-weight:500;text-align:center;}" +
		".badge-critical{background:rgba(237,90,114,.12);color:" + H.critical + ";}" +
		".badge-warning{background:rgba(244,165,35,.14);color:#b8770a;}" +
		".badge-success{background:rgba(27,188,134,.12);color:" + H.success + ";}"
	).appendTo("head");
	// 旧名保留为别名，避免遗漏调用点造成样式丢失
	$("<style>").text(
		".badge-red{display:inline-block;min-width:24px;padding:2px 8px;border-radius:" + H.radiusPill + ";font-size:12px;line-height:18px;font-weight:500;text-align:center;background:rgba(237,90,114,.12);color:" + H.critical + ";}" +
		".badge-orange{display:inline-block;min-width:24px;padding:2px 8px;border-radius:" + H.radiusPill + ";font-size:12px;line-height:18px;font-weight:500;text-align:center;background:rgba(244,165,35,.14);color:#b8770a;}"
	).appendTo("head");


	// ---- Date helpers ----
	var today = new Date();
	var day = today.getDay();
	var monday = new Date(today);
	monday.setDate(today.getDate() - (day === 0 ? 6 : day - 1));
	var sunday = new Date(monday);
	sunday.setDate(monday.getDate() + 6);
	var fmt = function (d) {
		return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
	};

	var startStr = fmt(monday);
	var endStr = fmt(sunday);

	// ---- Build toolbar ----
	var toolbarHtml = '<div class="dash-toolbar">';
	toolbarHtml += '<label>' + __("开始日期") + '</label> ';
	toolbarHtml += '<input type="date" id="dash-start" class="form-control" style="width:150px;display:inline-block;" value="' + startStr + '"> ';
	toolbarHtml += '<label>' + __("结束日期") + '</label> ';
	toolbarHtml += '<input type="date" id="dash-end" class="form-control" style="width:150px;display:inline-block;" value="' + endStr + '"> ';
	toolbarHtml += '<button class="btn btn-primary btn-sm" id="dash-go">' + __("查询") + '</button>';
	toolbarHtml += '</div>';
	toolbarHtml += '<div id="dash-content" style="padding:0 16px 16px;"></div>';

	$(wrapper).html(toolbarHtml);
	page.set_title(__("考勤异常仪表盘") + " — " + startStr + " ~ " + endStr);

	// ---- Load ECharts + data ----
	function loadECharts(cb) {
		if (window.echartsLoaded) { cb(); return; }
		$.getScript("https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js", function () {
			window.echartsLoaded = true;
			cb();
		});
	}

	function renderPage(data) {
		var charts = {};
		var container = $("#dash-content");
		if (!container.length) return;

		var h = '<div class="hbos-dash">';
		h += '<div class="dash-stats">';
		// 每个 KPI 顶一道域色短条（V2 的唯一装饰）；数字用 status/中性色，
		// 不逐卡换色——EA-4 §39 明文反对「每个指标一个随机颜色」。
		h += '<div class="dash-stat"><div class="rule"></div><div class="num" style="color:' + H.warning + ';">' + (data.total_late || 0) + '</div><div class="lbl">' + __("迟到") + '</div></div>';
		h += '<div class="dash-stat"><div class="rule"></div><div class="num" style="color:' + H.textPrimary + ';">' + (data.total_early || 0) + '</div><div class="lbl">' + __("早退") + '</div></div>';
		h += '<div class="dash-stat"><div class="rule"></div><div class="num" style="color:' + H.critical + ';">' + (data.total_absent || 0) + '</div><div class="lbl">' + __("缺勤") + '</div></div>';
		h += '<div class="dash-stat"><div class="rule"></div><div class="num" style="color:' + H.textPrimary + ';">' + (data.anomaly_people || 0) + '</div><div class="lbl">' + __("异常人员") + '</div></div>';
		h += '<div class="dash-stat"><div class="rule"></div><div class="num" style="color:' + H.success + ';">' + (data.attendance_rate || 0) + '%</div><div class="lbl">' + __("出勤率") + '</div></div>';
		h += '<div class="dash-stat"><div class="rule"></div><div class="num" style="color:' + H.textPrimary + ';">' + (data.total_employees || 0) + '</div><div class="lbl">' + __("总人数") + '</div></div>';
		h += '</div>';
		h += '<div class="dash-grid">';
		h += '<div class="chart-card"><h5>' + __("迟到 Top 15") + '</h5><div class="cwrap" id="d-c1"></div></div>';
		h += '<div class="chart-card"><h5>' + __("缺勤 Top 15") + '</h5><div class="cwrap" id="d-c2"></div></div>';
		h += '<div class="chart-card full"><h5>' + __("每日异常趋势") + '</h5><div class="cwrap tall" id="d-c3"></div></div>';
		h += '<div class="chart-card full"><h5>' + __("部门异常分布") + '</h5><div class="cwrap tall" id="d-c4"></div></div>';
		h += '</div>';
		h += '<div class="table-card"><h5>' + __("异常明细排行") + '</h5><div class="table-scroll"><table><thead><tr>';
		h += '<th>' + __("排名") + '</th><th>' + __("工号") + '</th><th>' + __("姓名") + '</th><th>' + __("部门") + '</th>';
		h += '<th>' + __("迟到") + '</th><th>' + __("早退") + '</th><th>' + __("缺勤") + '</th><th>' + __("异常合计") + '</th>';
		h += '</tr></thead><tbody>';

		var rows = data.table_rows || [];
		for (var i = 0; i < rows.length; i++) {
			var r = rows[i];
			var total = (r.late_count || 0) + (r.early_count || 0) + (r.absent_count || 0);
			// 0 值渲染成灰色正文而非彩色徽章：徽章表达「有异常」，0 不是异常。
			var cell = function (n, cls) {
				return (n || 0) > 0 ? '<span class="hbos-badge ' + cls + '">' + n + '</span>' : '<span class="muted">0</span>';
			};
			h += '<tr><td>' + (i + 1) + '</td><td>' + (r.num || "-") + '</td><td>' + (r.name || "-") + '</td><td>' + (r.dept || "-") + '</td>';
			h += '<td>' + cell(r.late_count, 'badge-warning') + '</td>';
			h += '<td>' + cell(r.early_count, 'badge-warning') + '</td>';
			h += '<td>' + cell(r.absent_count, 'badge-critical') + '</td>';
			h += '<td><b>' + total + '</b></td></tr>';
		}
		h += '</tbody></table></div></div>';
		container.html(h);

		// Init charts
		["d-c1","d-c2","d-c3","d-c4"].forEach(function(id) {
			var el = document.getElementById(id);
			if (el) charts[id] = echarts.init(el);
		});

		if (charts["d-c1"]) {
			charts["d-c1"].setOption({
				tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
				grid: { left: 160, right: 50, top: 8, bottom: 20 },
				xAxis: { type: "value", name: __("迟到次数") },
				yAxis: { type: "category", inverse: true, data: (data.top_late_names || []).slice(0, 15), axisLabel: { fontSize: 12, width: 140, overflow: "truncate" } },
				series: [{ type: "bar", data: (data.top_late_counts || []).slice(0, 15), label: { show: true, position: "right", fontSize: 12 },
					itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: H.warning }, { offset: 1, color: H.critical }]) } }]
			});
		}
		if (charts["d-c2"]) {
			charts["d-c2"].setOption({
				tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
				grid: { left: 160, right: 50, top: 8, bottom: 20 },
				xAxis: { type: "value", name: __("缺勤天数") },
				yAxis: { type: "category", inverse: true, data: (data.top_absent_names || []).slice(0, 15), axisLabel: { fontSize: 12, width: 140, overflow: "truncate" } },
				series: [{ type: "bar", data: (data.top_absent_counts || []).slice(0, 15), label: { show: true, position: "right", fontSize: 12 },
					itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: H.critical }, { offset: 1, color: H.accentTo }]) } }]
			});
		}
		if (charts["d-c3"]) {
			charts["d-c3"].setOption({
				tooltip: { trigger: "axis" },
				legend: { data: [__("迟到"), __("早退"), __("缺勤")], top: 4 },
				grid: { left: 50, right: 40, top: 40, bottom: 30 },
				xAxis: { type: "category", data: data.trend_labels || [], axisLabel: { fontSize: 11 } },
				yAxis: { type: "value", name: __("人次") },
				series: [
					{ name: __("迟到"), type: "line", data: data.trend_late || [], smooth: true, symbol: "circle", symbolSize: 6, itemStyle: { color: H.warning }, lineStyle: { width: 2 } },
					{ name: __("早退"), type: "line", data: data.trend_early || [], smooth: true, symbol: "diamond", symbolSize: 6, itemStyle: { color: H.accentTo }, lineStyle: { width: 2 } },
					{ name: __("缺勤"), type: "line", data: data.trend_absent || [], smooth: true, symbol: "triangle", symbolSize: 7, itemStyle: { color: H.critical }, lineStyle: { width: 2 } }
				]
			});
		}
		if (charts["d-c4"]) {
			charts["d-c4"].setOption({
				tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
				legend: { data: [__("迟到"), __("早退"), __("缺勤")], top: 4 },
				grid: { left: 120, right: 40, top: 40, bottom: 40 },
				xAxis: { type: "category", data: data.dept_names || [], axisLabel: { fontSize: 11, rotate: 30 } },
				yAxis: { type: "value", name: __("人次") },
				series: [
					{ name: __("迟到"), type: "bar", stack: "total", data: data.dept_late || [], itemStyle: { color: H.warning }, label: { show: true, fontSize: 10 } },
					{ name: __("早退"), type: "bar", stack: "total", data: data.dept_early || [], itemStyle: { color: H.accentTo }, label: { show: true, fontSize: 10 } },
					{ name: __("缺勤"), type: "bar", stack: "total", data: data.dept_absent || [], itemStyle: { color: H.critical }, label: { show: true, fontSize: 10 } }
				]
			});
		}

		$(window).off("resize.dashboard").on("resize.dashboard", function () {
			Object.values(charts).forEach(function (c) { c && c.resize(); });
		});
	}

	function loadData() {
		$("#dash-content").html('<div class="text-center p-5"><div class="spinner-border text-primary"></div><p class="mt-2 text-muted">' + __("加载考勤数据...") + '</p></div>');
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_attendance_dashboard.dashboard_data.get_data",
			args: { start_str: startStr, end_str: endStr },
			callback: function (r) {
				if (r.message && r.message.total_employees != null) {
					renderPage(r.message);
				} else {
					$("#dash-content").html('<div class="p-5 text-center text-danger">' + __("无法加载数据") + '</div>');
				}
			},
			error: function () {
				$("#dash-content").html('<div class="p-5 text-center text-danger">' + __("加载失败，请重试") + '</div>');
			}
		});
	}

	$("#dash-go").on("click", function () {
		startStr = $("#dash-start").val();
		endStr = $("#dash-end").val();
		if (!startStr || !endStr) return;
		page.set_title(__("考勤异常仪表盘") + " — " + startStr + " ~ " + endStr);
		loadData();
	});

	loadECharts(function () { loadData(); });
};
