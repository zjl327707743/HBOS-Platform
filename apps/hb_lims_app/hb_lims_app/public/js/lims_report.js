// 海滨LIMS：报表表格单元格 hover 显示全文提示。
// datatable 为 fixed 布局，列宽不足时内容 ellipsis 截断；未拖动列宽前，
// 悬停单元格即可通过原生 title 查看完整内容（拖动列宽见 lims_report.css）。
$(function () {
	$(document).on("mouseover", "#page-query-report .datatable .dt-cell__content", function () {
		if (!this.dataset.limsTitle) {
			this.dataset.limsTitle = "1";
			this.title = this.textContent.replace(/\s+/g, " ").trim();
		}
	});
});
