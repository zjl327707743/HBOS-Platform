import { getMethod } from './client'

export type TodoOwnerType = 'user' | 'role'
export type TodoExecuteMode = 'direct' | 'route'
export type TodoModule = 'testing' | 'stability' | 'retention' | 'quality' | 'compliance'

export interface TodoItem {
  todo_key: string
  module: TodoModule
  module_label: string
  source_doctype: string
  source_name: string
  title: string
  action: string
  action_label: string
  status: string
  status_label: string
  execute_mode: TodoExecuteMode
  owner_type: TodoOwnerType
  owner_label: string
  assignee: string | null
  candidate_roles: string[]
  priority: string | null
  due_at: string | null
  is_overdue: boolean
  route: string
  route_params: Record<string, string>
  modified_at: string | null
}

export interface TodoModuleSummary {
  testing: number
  stability: number
  retention: number
  quality: number
  compliance: number
}

export interface TodoSummary {
  total: number
  assigned_to_me: number
  role_pending: number
  overdue: number
  by_module: TodoModuleSummary
}

export interface TodoSummaryResponse {
  user: { name: string; full_name: string }
  summary: TodoSummary
  generated_at: string
}

export interface TodoFilters {
  module?: TodoModule
  owner_type?: TodoOwnerType
  status?: string
  priority?: string
  overdue?: boolean
  keyword?: string
  limit?: number
  offset?: number
}

export interface TodoListResponse {
  items: TodoItem[]
  total: number
  limit: number
  offset: number
  filtered_summary: TodoSummary
  user: { name: string; full_name: string }
  generated_at: string
}

export function getMyTodoSummary(): Promise<TodoSummaryResponse> {
  return getMethod<TodoSummaryResponse>(
    'hb_lims_app.hbos_lims.todo_service.get_my_todo_summary',
  )
}

export function getMyTodos(filters: TodoFilters = {}): Promise<TodoListResponse> {
  const {
    module,
    owner_type,
    status,
    priority,
    overdue = false,
    keyword,
    limit = 20,
    offset = 0,
  } = filters
  const params: Record<string, unknown> = {
    overdue,
    limit,
    offset,
  }
  if (module) params.module = module
  if (owner_type) params.owner_type = owner_type
  if (status) params.status = status
  if (priority) params.priority = priority
  if (keyword) params.keyword = keyword
  return getMethod<TodoListResponse>(
    'hb_lims_app.hbos_lims.todo_service.get_my_todos',
    params,
  )
}
