// 海滨LIMS：表单子表网格列宽拖拽（限定 HBOS LIMS 模块 DocType 表单页）。
// Frappe v16 子表网格（form-grid）列宽由 Bootstrap col-xs-N 栅格类固定，无拖拽交互。
// 本脚本：monkey-patch ControlTable.prototype.make —— 创建 grid 实例后 wrap 其 refresh；
// 同时用 MutationObserver 兜底补扫运行中新构建的子表控件（整页加载与 controls.bundle
// 懒加载存在竞态，make 可能在 patch 前已执行）。每次 grid 重绘后恢复 localStorage
// 持久化列宽、注入表头拖拽手柄（hover 显示，见 lims_report.css）；拖拽调整列宽并
// 持久化（按 父DocType+子表字段），双击手柄复位为该列自动宽度。
(function () {
	"use strict";

	var STORAGE_KEY = "hbos_lims_grid_column_widths";
	var HANDLE_CLASS = "grid-col-resize-handle";
	var MIN_WIDTH = 60;

	function is_lims_doctype(doctype) {
		try {
			return frappe.get_meta(doctype).module === "HBOS LIMS";
		} catch (e) {
			return false;
		}
	}

	function load_widths() {
		try {
			return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
		} catch (e) {
			return {};
		}
	}

	function save_widths(widths) {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(widths));
		} catch (e) {
			// localStorage 不可用时忽略持久化，本次拖拽仍生效
		}
	}

	// 对该列（表头 + 该 grid 全部数据行）应用固定像素宽度，覆盖 col-xs-N 百分比
	function apply_column_width($grid, fieldname, width) {
		$grid
			.find('.grid-static-col[data-fieldname="' + fieldname + '"]')
			.css({ width: width, flex: "0 0 " + width + "px" });
	}

	function bind_resize(grid, $handle, fieldname) {
		$handle.on("mousedown", function (e) {
			e.preventDefault();
			e.stopPropagation();
			var widths = load_widths();
			var parent_key = get_parent_key(grid);
			if (!widths[parent_key]) {
				widths[parent_key] = {};
			}
			var col_widths = widths[parent_key];
			var start_x = e.clientX;
			var start_w = $handle.parent().width();
			var moved = false;

			var on_move = function (ev) {
				var width = Math.max(MIN_WIDTH, start_w + ev.clientX - start_x);
				apply_column_width(grid.$grid, fieldname, width);
				col_widths[fieldname] = width;
				moved = true;
			};
			var on_up = function () {
				$(document).off("mousemove", on_move).off("mouseup", on_up);
				if (moved) {
					save_widths(widths);
				}
			};
			$(document).on("mousemove", on_move).on("mouseup", on_up);
		});

		// 双击手柄：清除该列持久化宽度，重新按 col-xs-N 自动宽度
		$handle.on("dblclick", function (e) {
			e.preventDefault();
			e.stopPropagation();
			var widths = load_widths();
			var parent_key = get_parent_key(grid);
			if (widths[parent_key] && widths[parent_key][fieldname]) {
				delete widths[parent_key][fieldname];
				save_widths(widths);
			}
			reset_column_width(grid.$grid, fieldname);
		});
	}

	function get_parent_key(grid) {
		// 父 DocType + 子表字段名，作为持久化键
		var parent_dt = grid.frm ? grid.frm.doctype : grid.df.parent;
		return parent_dt + ":" + grid.df.fieldname;
	}

	// 复位：清除 inline 宽度，恢复 col-xs-N 百分比栅格
	function reset_column_width($grid, fieldname) {
		$grid
			.find('.grid-static-col[data-fieldname="' + fieldname + '"]')
			.css({ width: "", flex: "" });
	}

	function ensure_resize_handles(grid) {
		if (!grid.$grid || !grid.$grid.length) {
			return;
		}
		grid.$grid.find(".grid-heading-row .grid-static-col[data-fieldname]").each(function () {
			var $col = $(this);
			if ($col.find("." + HANDLE_CLASS).length) {
				return;
			}
			var fieldname = $col.attr("data-fieldname");
			var $handle = $('<div class="' + HANDLE_CLASS + '"></div>').appendTo($col);
			bind_resize(grid, $handle, fieldname);
		});
	}

	function apply_saved_widths(grid) {
		var widths = load_widths()[get_parent_key(grid)];
		if (widths) {
			Object.keys(widths).forEach(function (fieldname) {
				apply_column_width(grid.$grid, fieldname, widths[fieldname]);
			});
		}
	}

	// wrap 单个 grid 实例的 refresh：原生重绘后恢复持久化宽度 + 注入手柄
	function patch_grid_instance(grid) {
		if (!grid || grid.__lims_resize_patched) {
			return;
		}
		grid.__lims_resize_patched = true;

		// 父 DocType 非 HBOS LIMS 模块时不启用
		var parent_dt = grid.frm ? grid.frm.doctype : grid.df.parent;
		if (!is_lims_doctype(parent_dt)) {
			return;
		}

		// grid.parent 为 .frappe-control.form-group，其内部包含 .form-grid-container > .form-grid
		// 也可能自身就是 .form-grid，两处都覆盖
		grid.$grid = $(grid.parent).is(".form-grid")
			? $(grid.parent)
			: $(grid.parent).find(".form-grid").first();

		// 标记 HBOS LIMS 子表网格容器，供 CSS 限定样式（如文字居中）
		grid.$grid.addClass("hbos-lims-grid");

		var orig_refresh = grid.refresh.bind(grid);
		grid.refresh = function () {
			orig_refresh();
			apply_saved_widths(grid);
			ensure_resize_handles(grid);
		};

		// 立即应用一次（grid 已创建并渲染）
		apply_saved_widths(grid);
		ensure_resize_handles(grid);
	}

	// 补扫 DOM 中已存在的子表控件（.frappe-control.form-group 持有 fieldobj 引用）
	function patch_existing_grids() {
		$(document)
			.find(".frappe-control.form-group")
			.each(function () {
				var fieldobj = this.fieldobj;
				if (fieldobj && fieldobj.grid && !fieldobj.grid.__lims_resize_patched) {
					patch_grid_instance(fieldobj.grid);
				}
			});
	}

	var patched = false;
	function init() {
		if (patched) {
			return;
		}
		if (!frappe.ui.form || !frappe.ui.form.ControlTable || !frappe.ui.form.ControlTable.prototype) {
			// controls.bundle.js 懒加载，尚未定义 ControlTable，稍后重试
			setTimeout(init, 300);
			return;
		}
		patched = true;

		var orig_make = frappe.ui.form.ControlTable.prototype.make;
		frappe.ui.form.ControlTable.prototype.make = function () {
			orig_make.call(this);
			// this.grid 已在原生 make 中创建，wrap 其 refresh
			if (this.grid) {
				patch_grid_instance(this.grid);
			}
		};

		// 补扫当前 DOM 中已存在的子表控件
		patch_existing_grids();

		// MutationObserver 兜底：路由切换 / 表单重建时补扫新出现的子表控件
		var observer = new MutationObserver(function () {
			patch_existing_grids();
		});
		observer.observe(document.body, {
			childList: true,
			subtree: true,
		});
	}

	setTimeout(init, 300);
})();
