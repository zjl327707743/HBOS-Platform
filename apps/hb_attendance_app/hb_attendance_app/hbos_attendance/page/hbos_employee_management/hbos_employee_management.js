// 全部函数收在本页闭包里。此前它们是顶层 function，而 hbos_shift_management.js
// 同样定义了顶层 renderPage —— 两个页面脚本都在 Desk 里常驻求值，后求值的那个
// 会覆盖前者，导致其中一页渲染出另一页的内容。收进 IIFE 后同名不再冲突。
//
// 注意 on_page_load 的赋值必须在闭包**内部**：它在闭包里调 renderPage，
// 放到闭包外会 ReferenceError（2026-10-02 实测踩到，页面整个空白）。
(function () {
frappe.pages["hbos-employee-management"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("人员管理"),
		single_column: true,
	});
	// HBOS 共享样式层的挂载点：只影响本容器内部，Desk 框架不受影响。
	$(wrapper).addClass("hbos-surface");

	renderPage(wrapper);
};

	const escapeHtml = (frappe.utils && frappe.utils.escape_html) || String;

	// 样式只声明本页结构；色值、圆角、阴影一律走 var(--h-*)（由
	// hbos_attendance.bundle.css 在 .hbos-surface 下定义），不写死——写死就会
	// 与门户和其它页面漂移。字号只取契约 v2.0 允许的 30 / 20 / 16 / 14 / 12。
	//
	// 强度：本页是**名录型操作面**，按 V1 处理——工作面板实色不模糊、行密集、
	// 表头吸顶、无动效。玻璃只出现在工具条外壳上（与门户顶部一致）；表格是给人
	// 读数字的，工作区不铺玻璃。
	function injectStyle() {
		if ($("#emp-style").length) return;
		$("<style id='emp-style'>").text(
			".emp-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 16px;margin-bottom:16px;background:var(--h-surface);border:1px solid var(--h-border);border-radius:var(--h-radius-control);}" +
			".emp-toolbar label{font-size:12px;line-height:20px;color:var(--h-text-2);margin:0;}" +
			".emp-ctl{display:inline-flex;align-items:center;gap:6px;}" +
			".emp-count{margin-left:auto;font-size:12px;line-height:20px;color:var(--h-muted);font-variant-numeric:tabular-nums;}" +
			".emp-panel{background:var(--h-surface-solid);border:1px solid var(--h-border);border-radius:var(--h-radius-card);overflow:hidden;}" +
			".emp-scroll{max-height:640px;overflow:auto;}" +
			"table.emp-tbl{width:100%;border-collapse:collapse;font-size:14px;line-height:22px;}" +
			".emp-tbl th{position:sticky;top:0;z-index:1;background:var(--h-subtle);color:var(--h-text-2);font-weight:500;font-size:12px;line-height:20px;text-align:left;padding:10px 12px;border-bottom:1px solid var(--h-border-strong);white-space:nowrap;}" +
			".emp-tbl td{padding:9px 12px;border-bottom:1px solid var(--h-border);color:var(--h-text);vertical-align:middle;}" +
			".emp-tbl tbody tr:hover td{background:var(--h-subtle);}" +
			".emp-tbl .num{font-variant-numeric:tabular-nums;color:var(--h-text-2);}" +
			".emp-tbl .nm{font-weight:500;}" +
			".emp-photo{width:32px;height:32px;border-radius:50%;object-fit:cover;display:block;}" +
			".emp-nophoto{display:inline-block;width:32px;height:32px;border-radius:50%;background:var(--h-subtle);border:1px solid var(--h-border);}" +
			".emp-state{padding:32px 16px;text-align:center;font-size:14px;line-height:22px;color:var(--h-muted);}" +
			".emp-state.error{color:var(--h-critical);}"
		).appendTo("head");
	}

	function renderPage(wrapper) {
		injectStyle();

		const $main = $(wrapper).find(".layout-main-section").empty();
		$main.append(`
			<div class="emp-toolbar">
				<span class="emp-ctl">
					<label>${__("部门")}</label>
					<select id="dept-filter" class="form-control input-xs" style="width:200px;">
						<option value="">${__("全部部门")}</option>
					</select>
				</span>
				<span class="emp-ctl">
					<label>${__("搜索")}</label>
					<input type="text" id="emp-search" class="form-control input-xs" style="width:200px;" placeholder="${__("姓名或工号")}">
				</span>
				<button class="btn btn-primary btn-xs" id="btn-search">${__("查询")}</button>
				<span class="emp-count" id="emp-count"></span>
			</div>
			<div class="emp-panel"><div class="emp-scroll" id="emp-table"></div></div>
		`);

		loadFilters();
		loadEmps();
		$("#btn-search").on("click", loadEmps);
		$("#emp-search").on("keypress", (e) => { if (e.which === 13) loadEmps(); });
	}

	function setCount(text) {
		$("#emp-count").text(text || "");
	}

	function loadFilters() {
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.get_departments",
			callback(r) {
				const $sel = $("#dept-filter");
				(r.message || []).forEach((d) => {
					// 部门名取自 tabEmployee.department，是用户可写数据 → 转义
					const nm = escapeHtml(d.department || "");
					if (!nm) return;
					$sel.append(`<option value="${nm}">${nm}（${d.cnt}人）</option>`);
				});
				$sel.on("change", loadEmps);
			},
		});
	}

	function loadEmps() {
		const dept = $("#dept-filter").val();
		const search = $("#emp-search").val();
		$("#emp-table").html(`<div class="emp-state">${__("加载中…")}</div>`);
		setCount("");
		frappe.call({
			method: "hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.get_employees",
			args: { department: dept, search: search },
			callback(r) { renderEmpTable(r.message); },
			error() {
				$("#emp-table").html(`<div class="emp-state error">${__("加载失败，请重试。")}</div>`);
			},
		});
	}

	function renderEmpTable(emps) {
		const list = emps || [];
		setCount(list.length ? __("共 {0} 人", [list.length]) : "");
		if (!list.length) {
			$("#emp-table").html(`<div class="emp-state">${__("没有符合条件的员工。换个部门或清空搜索词再试。")}</div>`);
			return;
		}
		let html = `<table class="emp-tbl"><thead><tr>
			<th style="width:56px;">${__("照片")}</th>
			<th style="width:120px;">${__("工号")}</th>
			<th style="width:110px;">${__("姓名")}</th>
			<th>${__("部门")}</th>
			<th style="width:150px;">${__("联系方式")}</th>
			<th style="width:130px;">${__("入职日期")}</th>
		</tr></thead><tbody>`;
		list.forEach((e) => {
			const photo = e.image
				? `<img class="emp-photo" src="${escapeHtml(e.image)}" alt="">`
				: `<span class="emp-nophoto"></span>`;
			html += `<tr>
				<td>${photo}</td>
				<td class="num">${escapeHtml(e.employee_number || "—")}</td>
				<td class="nm">${escapeHtml(e.employee_name || "")}</td>
				<td>${escapeHtml(e.department || "—")}</td>
				<td class="num">${escapeHtml(e.cell_number || "—")}</td>
				<td class="num">${escapeHtml(e.date_of_joining || "—")}</td>
			</tr>`;
		});
		html += `</tbody></table>`;
		$("#emp-table").html(html);
	}
})();
