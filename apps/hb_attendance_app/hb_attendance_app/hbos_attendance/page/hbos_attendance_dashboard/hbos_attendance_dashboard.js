frappe.pages["hbos-attendance-dashboard"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("考勤异常仪表盘"),
		single_column: true,
	});

	// Inject CSS
	$("<style>").text(
		".dash-stats{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:18px;}" +
		".dash-stat{flex:1;min-width:130px;background:#fff;border-radius:8px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.07);}" +
		".dash-stat .num{font-size:28px;font-weight:700;}" +
		".dash-stat .lbl{font-size:12px;color:#888;margin-top:2px;}" +
		".dash-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;}" +
		".dash-grid .full{grid-column:1/-1;}" +
		".chart-card{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.05);}" +
		".chart-card h5{font-size:15px;margin:0 0 10px 0;color:#333;}" +
		".cwrap{width:100%;height:380px;}" +
		".cwrap.tall{height:460px;}" +
		".table-card{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.05);margin-top:18px;}" +
		".table-card h5{font-size:15px;margin:0 0 10px 0;color:#333;}" +
		".table-card table{width:100%;font-size:13px;border-collapse:collapse;}" +
		".table-card th{background:#f7f8fa;text-align:left;padding:8px;border-bottom:2px solid #e0e0e0;position:sticky;top:0;}" +
		".table-card td{padding:7px 8px;border-bottom:1px solid #f0f0f0;}" +
		".table-card tr:hover td{background:#fafbfc;}" +
		".table-scroll{max-height:500px;overflow-y:auto;}" +
		".badge-red{display:inline-block;padding:2px 8px;border-radius:10px;background:#fde8e8;color:#c0392b;font-size:12px;}" +
		".badge-orange{display:inline-block;padding:2px 8px;border-radius:10px;background:#fef3e4;color:#e67e22;font-size:12px;}" +
		".dash-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:8px 16px;background:#fff;border-bottom:1px solid #e0e0e0;margin-bottom:16px;}"
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
	toolbarHtml += '<label style="font-size:13px;font-weight:600;">' + __("开始日期") + '</label> ';
	toolbarHtml += '<input type="date" id="dash-start" class="form-control" style="width:150px;display:inline-block;" value="' + startStr + '"> ';
	toolbarHtml += '<label style="font-size:13px;font-weight:600;">' + __("结束日期") + '</label> ';
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

		var h = '<div class="dash-stats">';
		h += '<div class="dash-stat"><div class="num" style="color:#e74c3c;">' + (data.total_late || 0) + '</div><div class="lbl">' + __("迟到") + '</div></div>';
		h += '<div class="dash-stat"><div class="num" style="color:#f39c12;">' + (data.total_early || 0) + '</div><div class="lbl">' + __("早退") + '</div></div>';
		h += '<div class="dash-stat"><div class="num" style="color:#8e44ad;">' + (data.total_absent || 0) + '</div><div class="lbl">' + __("缺勤") + '</div></div>';
		h += '<div class="dash-stat"><div class="num" style="color:#3498db;">' + (data.anomaly_people || 0) + '</div><div class="lbl">' + __("异常人员") + '</div></div>';
		h += '<div class="dash-stat"><div class="num" style="color:#27ae60;">' + (data.attendance_rate || 0) + '%</div><div class="lbl">' + __("出勤率") + '</div></div>';
		h += '<div class="dash-stat"><div class="num" style="color:#2c3e50;">' + (data.total_employees || 0) + '</div><div class="lbl">' + __("总人数") + '</div></div>';
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
			h += '<tr><td>' + (i + 1) + '</td><td>' + (r.num || "-") + '</td><td>' + (r.name || "-") + '</td><td>' + (r.dept || "-") + '</td>';
			h += '<td>' + ((r.late_count || 0) > 0 ? '<span class="badge-red">' + r.late_count + '</span>' : "0") + '</td>';
			h += '<td>' + ((r.early_count || 0) > 0 ? '<span class="badge-orange">' + r.early_count + '</span>' : "0") + '</td>';
			h += '<td>' + ((r.absent_count || 0) > 0 ? '<span class="badge-orange" style="background:#f3e8ff;color:#7c3aed;">' + r.absent_count + '</span>' : "0") + '</td>';
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
					itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: "#e74c3c" }, { offset: 1, color: "#f39c12" }]) } }]
			});
		}
		if (charts["d-c2"]) {
			charts["d-c2"].setOption({
				tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
				grid: { left: 160, right: 50, top: 8, bottom: 20 },
				xAxis: { type: "value", name: __("缺勤天数") },
				yAxis: { type: "category", inverse: true, data: (data.top_absent_names || []).slice(0, 15), axisLabel: { fontSize: 12, width: 140, overflow: "truncate" } },
				series: [{ type: "bar", data: (data.top_absent_counts || []).slice(0, 15), label: { show: true, position: "right", fontSize: 12 },
					itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: "#8e44ad" }, { offset: 1, color: "#d35400" }]) } }]
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
					{ name: __("迟到"), type: "line", data: data.trend_late || [], smooth: true, symbol: "circle", symbolSize: 6, itemStyle: { color: "#e74c3c" }, lineStyle: { width: 2 } },
					{ name: __("早退"), type: "line", data: data.trend_early || [], smooth: true, symbol: "diamond", symbolSize: 6, itemStyle: { color: "#f39c12" }, lineStyle: { width: 2 } },
					{ name: __("缺勤"), type: "line", data: data.trend_absent || [], smooth: true, symbol: "triangle", symbolSize: 7, itemStyle: { color: "#8e44ad" }, lineStyle: { width: 2 } }
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
					{ name: __("迟到"), type: "bar", stack: "total", data: data.dept_late || [], itemStyle: { color: "#e74c3c" }, label: { show: true, fontSize: 10 } },
					{ name: __("早退"), type: "bar", stack: "total", data: data.dept_early || [], itemStyle: { color: "#f39c12" }, label: { show: true, fontSize: 10 } },
					{ name: __("缺勤"), type: "bar", stack: "total", data: data.dept_absent || [], itemStyle: { color: "#8e44ad" }, label: { show: true, fontSize: 10 } }
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
