frappe.pages["hbos-employee-management"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("人员管理"),
		single_column: true,
	});
	renderPage(wrapper);
};

function renderPage(wrapper) {
	const $main = $(wrapper).find(".layout-main-section").empty();
	$main.append(`
		<div style="padding: 15px;">
			<div class="row mb-3">
				<div class="col-md-3">
					<select id="dept-filter" class="form-control"><option value="">全部部门</option></select>
				</div>
				<div class="col-md-3">
					<input type="text" id="emp-search" class="form-control" placeholder="搜索姓名/工号">
				</div>
				<div class="col-md-2">
					<button class="btn btn-primary" id="btn-search">查询</button>
				</div>
			</div>
			<div id="emp-table"></div>
		</div>
	`);
	loadFilters();
	loadEmps();
	$("#btn-search").on("click", () => loadEmps());
	$("#emp-search").on("keypress", e => { if (e.which === 13) loadEmps(); });
}

function loadFilters() {
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.get_departments",
		callback(r) {
			const $sel = $("#dept-filter");
			(r.message || []).forEach(d => {
				$sel.append(`<option value="${d.department}">${d.department}（${d.cnt}人）</option>`);
			});
			$sel.on("change", () => loadEmps());
		},
	});
}

function loadEmps() {
	const dept = $("#dept-filter").val();
	const search = $("#emp-search").val();
	frappe.call({
		method: "hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.get_employees",
		args: { department: dept, search: search },
		callback(r) {
			renderEmpTable(r.message);
		},
	});
}

function renderEmpTable(emps) {
	const $t = $("#emp-table").empty();
	let html = `<table class="table table-bordered table-sm">
		<thead><tr>
			<th>照片</th><th>工号</th><th>姓名</th><th>部门</th><th>联系方式</th><th>入职日期</th>
		</tr></thead><tbody>`;
	(emps || []).forEach(e => {
		const img = e.image ? `<img src="${e.image}" style="width:36px;height:36px;border-radius:50%;">` : `<span class="text-muted">无</span>`;
		html += `<tr>
			<td>${img}</td>
			<td>${e.employee_number || ""}</td>
			<td>${e.employee_name || ""}</td>
			<td>${e.department || ""}</td>
			<td>${e.cell_number || ""}</td>
			<td>${e.date_of_joining ? e.date_of_joining : ""}</td>
		</tr>`;
	});
	html += `</tbody></table>`;
	if (!emps || emps.length === 0) {
		html = `<div class="alert alert-info">暂无员工数据</div>`;
	}
	$t.html(html);
}
