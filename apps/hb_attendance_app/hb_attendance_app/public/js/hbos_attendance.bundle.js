/* HBOS 共享视觉层的 Desk 侧挂载点：让**本 App 的报表与列表页**也用同一套语言。
 *
 * ## 为什么需要
 *
 * hbos_attendance.bundle.css 的规则全部限定在 `.hbos-surface` 下。
 * 6 个自定义 Desk 页自己挂这个 class，但**报表页与 DocType 列表页不挂**——
 * 它们由 Frappe 的视图工厂生成，不是我们的代码。结果：同一个「海滨考勤工作台」
 * 里，仪表盘是门户观感、财务报表还是 Frappe 原样，观感割裂。
 *
 * ## 为什么不用别的手段
 *
 * - 改 report/*.json 的 page_class：Report 没有这个字段；且 `frappe.report`
 *   是框架依赖的标识类名，不便替换。
 * - 在 bundle.css 里不加作用域直接命中 `.dt-cell`：会波及 Desk 里**所有** app
 *   的报表（ERPNext 的、HRMS 的），爆炸半径远超需求。
 * - **本文件**：按路由判断「当前是不是本 App 的报表 / 列表」，是则给容器挂上
 *   `.hbos-surface`，于是 bundle 里已有的规则自然生效——加挂载点，不复制样式。
 *
 * ## 边界
 *
 * 只认本 App 自己的报表名与 DocType 名（见下方两张表）。其余一切页面原样不动。
 * 离开这些路由时会把 class 摘掉，不残留。任何一步失败都静默跳过——最坏就是
 * 报表保持 Frappe 原样，功能不受影响。
 */
(function () {
  'use strict';

  var SURFACE_CLASS = 'hbos-surface';
  var DATA_CLASS = 'hbos-surface--data'; // 数据密集页：不铺极光

  // 本 App 的报表（与 report/<目录>/<名>.json 的 report_name 一致）
  var ATTENDANCE_REPORTS = [
    '月度考勤汇总',
    '打卡流水',
    '考勤结果',
    'HBOS 月度汇总暂存（对账）'
  ];

  // 本 App 的 DocType 列表
  var ATTENDANCE_DOCTYPES = [
    'HBOS Attendance Import Log',
    'HBOS Leave Record',
    'HBOS Overtime Record',
    'HBOS Rest Leave Record'
  ];

  // 承载内容的容器。按优先级试，命中即用。
  var CONTAINER_SELECTORS = [
    '.main-section .content.page-container',
    '.content.page-container',
    '.page-container'
  ];

  function currentRoute() {
    try {
      return frappe.get_route() || [];
    } catch (e) {
      return [];
    }
  }

  /** 当前路由是否属于本 App 的报表 / 列表。 */
  function isAttendanceDataView() {
    var route = currentRoute();
    if (!route.length) return false;
    var head = String(route[0] || '').toLowerCase();

    if (head === 'query-report') {
      return ATTENDANCE_REPORTS.indexOf(String(route[1] || '')) !== -1;
    }
    // List 视图：Frappe 的 route 形如 ['List', '<DocType>', ...]
    if (head === 'list') {
      return ATTENDANCE_DOCTYPES.indexOf(String(route[1] || '')) !== -1;
    }
    return false;
  }

  function container() {
    for (var i = 0; i < CONTAINER_SELECTORS.length; i++) {
      var el = document.querySelector(CONTAINER_SELECTORS[i]);
      if (el) return el;
    }
    return null;
  }

  function apply() {
    var el = container();
    if (!el) return;

    if (isAttendanceDataView()) {
      el.classList.add(SURFACE_CLASS);
      el.classList.add(DATA_CLASS);
    } else {
      // 离开时摘掉，避免样式残留到别的页面
      el.classList.remove(SURFACE_CLASS);
      el.classList.remove(DATA_CLASS);
    }
  }

  function schedule() {
    // 等视图渲染完再挂；Frappe 是异步渲染，立即执行往往抓不到容器
    window.requestAnimationFrame(apply);
    window.setTimeout(apply, 150);
    window.setTimeout(apply, 500);
  }

  function boot() {
    if (typeof frappe === 'undefined' || !frappe.router) return;
    frappe.router.on('change', schedule);
    // 首屏：router 的 change 在初次加载时不一定触发
    if (frappe.ready) frappe.ready(schedule);
    else schedule();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
