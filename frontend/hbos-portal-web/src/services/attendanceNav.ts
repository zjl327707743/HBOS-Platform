// 考勤应用内导航的**唯一来源**。侧栏、移动端抽屉、面包屑都从这里取，
// 避免同一份菜单在多处各写一遍后漂移（本项目为「一个业务含义只留一份名单」
// 专门收敛过行政班名单，同一道理适用）。
//
// 两类入口：
//   native —— 门户 SPA 自己的页面，`to` 即稳定路径，点开由 Vue 渲染。
//   embed  —— 报表 / 列表 / 配置页。按 frontend 规范 §1.2 不重写成原生前端，
//             而是把稳定路径交给后端解析成 Desk 路径，由同域 iframe 承载。
//
// 稳定路径（stablePath）必须与后端 `portal/routes.py` 的
// NATIVE_PATHS / EMBEDDED_ROUTES 逐条对应——后端是权威，这里是它的镜像；
// 任一侧新增都必须同时改另一侧，否则解析会被后端拒绝（前端落 403）。

export type AttendanceNavKind = 'native' | 'report' | 'list' | 'import' | 'monthly-upload' | 'embed'

export interface AttendanceNavItem {
  /** 嵌入路由的地址片段：/hbos/attendance/embed/<slug>；报表为 /hbos/attendance/report/<slug> */
  slug: string
  label: string
  /** 交给后端 resolve_route 解析的稳定路径 */
  stablePath: string
  kind: AttendanceNavKind
  icon: string
}

export interface AttendanceNavGroup {
  label: string
  items: AttendanceNavItem[]
}

export const attendanceNavGroups: AttendanceNavGroup[] = [
  {
    label: '概览',
    items: [
      { slug: 'dashboard', label: '考勤仪表盘', stablePath: '/hbos/attendance', kind: 'native', icon: 'dashboard' },
      { slug: 'employees', label: '人员管理', stablePath: '/hbos/attendance/employees', kind: 'native', icon: 'team' },
      { slug: 'board', label: '部门看板', stablePath: '/hbos/attendance/board', kind: 'native', icon: 'apartment' },
    ],
  },
  {
    label: '报表',
    items: [
      { slug: 'monthly', label: '月度考勤汇总', stablePath: '/hbos/attendance/report/monthly', kind: 'report', icon: 'chart' },
      { slug: 'checkins', label: '打卡流水', stablePath: '/hbos/attendance/report/checkins', kind: 'report', icon: 'profile' },
      { slug: 'results', label: '考勤结果', stablePath: '/hbos/attendance/report/results', kind: 'report', icon: 'table' },
      { slug: 'staging', label: '月度汇总 / 对账暂存', stablePath: '/hbos/attendance/report/staging', kind: 'report', icon: 'reconciliation' },
    ],
  },
  {
    label: '数据与导入',
    items: [
      { slug: 'import', label: '导入考勤机导出表', stablePath: '/hbos/attendance/import', kind: 'import', icon: 'upload' },
      { slug: 'monthly-upload', label: '上传月度考勤表', stablePath: '/hbos/attendance/monthly-upload', kind: 'monthly-upload', icon: 'cloudUpload' },
      { slug: 'import-log', label: '考勤导入日志', stablePath: '/hbos/attendance/import-log', kind: 'list', icon: 'fileSearch' },
      { slug: 'feishu-leave', label: '飞书请假记录', stablePath: '/hbos/attendance/feishu/leave', kind: 'list', icon: 'calendar' },
      { slug: 'feishu-overtime', label: '飞书加班记录', stablePath: '/hbos/attendance/feishu/overtime', kind: 'list', icon: 'fieldTime' },
      { slug: 'feishu-rest-leave', label: '飞书调休记录', stablePath: '/hbos/attendance/feishu/rest-leave', kind: 'list', icon: 'swap' },
    ],
  },
  {
    label: '配置',
    items: [
      { slug: 'shifts', label: '班次管理', stablePath: '/hbos/attendance/shifts', kind: 'embed', icon: 'setting' },
    ],
  },
]

const flatItems: AttendanceNavItem[] = attendanceNavGroups.flatMap((group) => group.items)

/** 门户内可直接访问的地址：原生项即稳定路径，报表走 report 子路由，其余走 embed。 */
export function navTarget(item: AttendanceNavItem): string {
  if (item.kind === 'native') return item.stablePath
  if (item.kind === 'report') return `/hbos/attendance/report/${item.slug}`
  if (item.kind === 'list') return `/hbos/attendance/list/${item.slug}`
  if (item.kind === 'import') return '/hbos/attendance/import'
  if (item.kind === 'monthly-upload') return '/hbos/attendance/monthly-upload'
  return `/hbos/attendance/embed/${item.slug}`
}

export function findNavBySlug(slug: string): AttendanceNavItem | undefined {
  return flatItems.find((item) => item.slug === slug)
}

/** 侧栏高亮判据：当前路由路径命中了哪一项（无命中返回 undefined）。 */
export function activeNavForPath(path: string): AttendanceNavItem | undefined {
  const normalized = path.replace(/\/+$/, '') || '/'
  return flatItems.find((item) => {
    const target = navTarget(item).replace(/\/+$/, '') || '/'
    return normalized === target
  })
}
