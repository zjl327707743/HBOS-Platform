import type { TodoFilters, TodoItem, TodoSummary } from '@/api/todo'

const MODULE_LABELS: Record<string, string> = {
  testing: '检验业务',
  stability: '稳定性',
  retention: '留样',
  quality: '质量',
  compliance: '合规',
}

export function emptyModuleSummary() {
  return {
    testing: 0,
    stability: 0,
    retention: 0,
    quality: 0,
    compliance: 0,
  }
}

export function emptySummary(): TodoSummary {
  return {
    total: 0,
    assigned_to_me: 0,
    role_pending: 0,
    overdue: 0,
    by_module: emptyModuleSummary(),
  }
}

export function normalizeTodoItem(item: TodoItem): TodoItem {
  return {
    ...item,
    module_label: item.module_label || MODULE_LABELS[item.module] || item.module,
    status_label: item.status_label || item.status,
    owner_label: item.owner_label || (item.owner_type === 'user' ? '指派给我' : '角色待处理'),
    candidate_roles: item.candidate_roles || [],
    route_params: item.route_params || {},
  }
}

export function buildTodoQuery(filters: TodoFilters = {}): Record<string, unknown> {
  const params: Record<string, unknown> = {
    overdue: filters.overdue ?? false,
    limit: filters.limit ?? 20,
    offset: filters.offset ?? 0,
  }
  const allowedKeys: (keyof TodoFilters)[] = [
    'module', 'owner_type', 'status', 'priority', 'keyword',
  ]
  for (const key of allowedKeys) {
    const value = filters[key]
    if (value !== undefined && value !== '') params[key] = value
  }
  return params
}

export function readScalarQuery(value: unknown): string | undefined {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return undefined
}

/**
 * Builds a stable route location for a todo source page. Keeping this as a
 * plain object makes deep-link behavior testable without mounting Vue Router.
 */
export function buildTodoRoute(path: string, params: Record<string, string | undefined> = {}) {
  const query = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  )
  return { path, query }
}

const PRIORITY_RANK: Record<string, number> = {
  特急: 4,
  紧急: 4,
  加急: 3,
  高: 3,
  常规: 2,
  普通: 2,
  中: 1,
  低: 0,
}

export function sortTodoItems(items: TodoItem[]): TodoItem[] {
  return [...items].sort((left, right) => {
    if (left.is_overdue !== right.is_overdue) return left.is_overdue ? -1 : 1
    const priorityDelta = (PRIORITY_RANK[right.priority || ''] ?? 1) - (PRIORITY_RANK[left.priority || ''] ?? 1)
    if (priorityDelta) return priorityDelta
    const leftDue = left.due_at || '9999-12-31'
    const rightDue = right.due_at || '9999-12-31'
    if (leftDue !== rightDue) return leftDue.localeCompare(rightDue)
    return (right.modified_at || '').localeCompare(left.modified_at || '')
  })
}

export function retainPreviousOnError<T>(previous: T, next: T, failed: boolean): T {
  return failed ? previous : next
}
