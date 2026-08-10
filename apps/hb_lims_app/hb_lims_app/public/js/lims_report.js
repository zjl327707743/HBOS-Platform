// 海滨LIMS：报表表格单元格 hover 显示全文提示 + Query Report 容器标记。
// datatable 为 fixed 布局，列宽不足时内容 ellipsis 截断；未拖动列宽前，
// 悬停单元格即可通过原生 title 查看完整内容（拖动列宽见 lims_report.css）。
$(function () {
	// 标记 HBOS LIMS 的 Query Report 页面容器，供 CSS 限定样式（如文字居中）。
	// 通过页面标题识别：5 个 LIMS 报表名均为 HBOS LIMS 模块自定义。
	// Query Report 为路由懒加载，容器与标题在路由完成后才出现，
	// 故用 MutationObserver 监听 #page-query-report 出现后按标题打标。
	var LIMS_REPORTS = [
		"待检任务看板",
		"检验结果清单",
		"样品台账",
		"审计追踪查询",
		"COA 发布记录",
	];

	function mark_lims_report() {
		var page = $("#page-query-report");
		if (page.length && !page.hasClass("hbos-lims-report")) {
			var title = $(".page-title").first().text().trim();
			if (LIMS_REPORTS.indexOf(title) !== -1) {
				page.addClass("hbos-lims-report");
			}
		}
	}

	mark_lims_report();
	frappe.router && frappe.router.on && frappe.router.on("change", mark_lims_report);

	var observer = new MutationObserver(function () {
		mark_lims_report();
	});
	observer.observe(document.body, { childList: true, subtree: true });

	$(document).on("mouseover", "#page-query-report .datatable .dt-cell__content", function () {
		if (!this.dataset.limsTitle) {
			this.dataset.limsTitle = "1";
			this.title = this.textContent.replace(/\s+/g, " ").trim();
		}
	});
});
