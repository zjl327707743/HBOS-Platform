// 海滨LIMS：列表视图列宽拖拽（限定 HBOS LIMS 模块 DocType 列表页）。
// Frappe v16 列表视图原生仅按内容自动计算列宽（apply_column_widths），无拖拽交互。
// 本脚本：monkey-patch ListView.prototype.apply_column_widths —— 原生自动算宽后
// 恢复 localStorage 持久化列宽、注入表头列拖拽手柄（hover 表头显示，见 lims_report.css）；
// 拖拽调整列宽并持久化（按 DocType+字段），双击手柄复位为该列自动宽度。
// list.bundle.js 为路由懒加载，故轮询等待 frappe.views.ListView 定义后 patch 一次。
(function () {
	"use strict";

	var STORAGE_KEY = "hbos_lims_list_column_widths";
	var HANDLE_CLASS = "list-col-resize-handle";
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

	// 与原生 apply_column_widths 相同的选择器：表头列（.list-header-subject 内）
	// 与全部行列（.level-left 内）均命中，字段名即列 CSS 类
	function apply_width($list_view, fieldname, width) {
		$list_view
			.find(".result .level-left .list-row-col." + fieldname)
			.css({ width: width, flex: "1 0 " + width + "px" });
	}

	function bind_resize(list_view, $handle, fieldname) {
		var $list_view = list_view.$frappe_list;

		$handle.on("mousedown", function (e) {
			e.preventDefault();
			e.stopPropagation();
			var widths = load_widths();
			if (!widths[list_view.doctype]) {
				widths[list_view.doctype] = {};
			}
			var doctype_widths = widths[list_view.doctype];
			var start_x = e.clientX;
			var start_w = $handle.parent().width();
			var moved = false;

			var on_move = function (ev) {
				var width = Math.max(MIN_WIDTH, start_w + ev.clientX - start_x);
				apply_width($list_view, fieldname, width);
				doctype_widths[fieldname] = width;
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

		// 双击手柄：清除该列持久化宽度，重新按内容自动计算（复用 patch 后的 apply_column_widths）
		$handle.on("dblclick", function (e) {
			e.preventDefault();
			e.stopPropagation();
			var widths = load_widths();
			if (widths[list_view.doctype] && widths[list_view.doctype][fieldname]) {
				delete widths[list_view.doctype][fieldname];
				save_widths(widths);
			}
			list_view.apply_column_widths();
		});
	}

	function ensure_resize_handles(list_view) {
		var columns = list_view.columns || [];
		list_view.$frappe_list
			.find(".list-row-head .list-row-col")
			.each(function (i) {
				var col = columns[i];
				// 无字段列（全选/按钮/下拉等附加列）不注入手柄
				if (!col || !col.df || !col.df.fieldname) {
					return;
				}
				var $col = $(this);
				if ($col.find("." + HANDLE_CLASS).length) {
					return;
				}
				var $handle = $('<div class="' + HANDLE_CLASS + '"></div>').appendTo($col);
				bind_resize(list_view, $handle, col.df.fieldname);
			});
	}

	var patched = false;
	function init() {
		if (patched) {
			return;
		}
		if (!frappe.views || !frappe.views.ListView || !frappe.views.ListView.prototype) {
			// list.bundle.js 懒加载，尚未定义 ListView，稍后重试
			setTimeout(init, 300);
			return;
		}
		patched = true;

		var orig_apply_column_widths = frappe.views.ListView.prototype.apply_column_widths;
		frappe.views.ListView.prototype.apply_column_widths = function () {
			orig_apply_column_widths.call(this);
			// 仅 HBOS LIMS 模块 DocType 列表页启用（不影响考勤等其他列表页）
			if (!is_lims_doctype(this.doctype)) {
				return;
			}
			// 标记 HBOS LIMS 列表容器，供 CSS 限定样式（如文字居中）
			this.$frappe_list.addClass("hbos-lims-list");
			var widths = load_widths()[this.doctype];
			if (widths) {
				Object.keys(widths).forEach(function (fieldname) {
					apply_width(this.$frappe_list, fieldname, widths[fieldname]);
				}, this);
			}
			ensure_resize_handles(this);
		};

		// list.bundle.js 路由懒加载，patch 时机可能晚于首个 LIMS 列表页实例的
		// 首次渲染（渲染已调用 patch 前的原生 apply_column_widths，手柄未注入）。
		// 对已存在且已渲染的 LIMS 列表实例补调一次，注入手柄并恢复持久化列宽。
		Object.keys(frappe.views.list_view).forEach(function (route) {
			var lv = frappe.views.list_view[route];
			if (
				lv &&
				lv.doctype &&
				is_lims_doctype(lv.doctype) &&
				lv.$frappe_list &&
				lv.$frappe_list.length
			) {
				lv.apply_column_widths();
			}
		});
	}

	setTimeout(init, 300);
})();
