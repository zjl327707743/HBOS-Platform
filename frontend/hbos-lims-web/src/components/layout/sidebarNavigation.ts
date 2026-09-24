export type SidebarGroupKey = 'testing' | 'quality' | 'retention' | 'stability' | 'compliance'

export interface SidebarNavItem {
  key: string
  label: string
  path: string
  badge?: 'pending' | 'schedule' | 'results' | 'todo-total'
}

export interface SidebarNavGroup {
  key: SidebarGroupKey
  label: string
  children: SidebarNavItem[]
  badge?: number
}

export const myTodoNavItem = {
  key: 'my-todos',
  label: '我的待办',
  path: '/my-todos',
  badge: 'todo-total' as const,
}

export const sidebarGroups: SidebarNavGroup[] = [
  {
    key: 'testing',
    label: '检验业务',
    children: [
      { key: 'samples', label: '样品登记与台账', path: '/samples' },
      { key: 'tasks', label: '待检任务看板', path: '/tasks', badge: 'pending' },
      { key: 'results', label: '检验结果录入', path: '/results' },
      { key: 'result-ledger', label: '检验结果台账', path: '/results/ledger' },
    ],
  },
  {
    key: 'quality',
    label: '质量与报告',
    children: [
      { key: 'coas', label: 'COA 报告管理', path: '/coas' },
      { key: 'specs', label: '质量标准库', path: '/specs' },
    ],
  },
  {
    key: 'retention',
    label: '留样管理',
    children: [
      { key: 'retention-dashboard', label: '留样工作台', path: '/retention' },
      { key: 'retention-samples', label: '留样登记与台账', path: '/retention/samples' },
      { key: 'retention-products', label: '留样产品', path: '/retention/products' },
      { key: 'retention-observations', label: '观察任务', path: '/retention/observations' },
      { key: 'retention-usage', label: '使用申请', path: '/retention/usage' },
      { key: 'retention-disposal', label: '处理申请', path: '/retention/disposal' },
    ],
  },
  {
    key: 'stability',
    label: '稳定性管理',
    children: [
      { key: 'stability-dashboard', label: '稳定性工作台', path: '/stability' },
      { key: 'stability-study', label: '考察申请与方案', path: '/stability/study' },
      { key: 'stability-samples', label: '样品入箱与台账', path: '/stability/samples' },
      { key: 'stability-schedule', label: '取样与检测计划', path: '/stability/schedule', badge: 'schedule' },
      { key: 'stability-results', label: '结果录入与趋势', path: '/stability/results', badge: 'results' },
      { key: 'stability-reports', label: '报告与有效期', path: '/stability/reports' },
      { key: 'stability-ops', label: '变更 / 稳定性室 / 设备', path: '/stability/ops' },
    ],
  },
  {
    key: 'compliance',
    label: '合规审计',
    children: [
      { key: 'audit', label: '审计追踪查询', path: '/audit' },
      { key: 'audit-log', label: '合规审计日志', path: '/audit-log' },
    ],
  },
]

function pathMatches(path: string, target: string): boolean {
  if (target === '/results') {
    return path === '/results' || /^\/results\/[^/]+$/.test(path)
  }
  if (target === '/retention' || target === '/stability') {
    return path === target
  }
  return path === target || path.startsWith(`${target}/`)
}

export function getGroupForPath(path: string): SidebarGroupKey | null {
  return sidebarGroups.find((group) => group.children.some((item) => pathMatches(path, item.path)))?.key ?? null
}

export function getInitialExpandedGroup(path: string): SidebarGroupKey | null {
  return getGroupForPath(path)
}

export function isSidebarItemActive(path: string, target: string): boolean {
  return pathMatches(path, target)
}
