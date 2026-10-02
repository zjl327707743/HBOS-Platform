import type {
  AppManifestDTO,
  PortalBranding,
  PortalUser,
  SearchResultDTO,
  SummaryMetricDTO,
  LimsTaskQuery,
  UnifiedTaskDTO,
  ProviderBatch,
  TaskPage,
} from '@/contracts/portal'
import { callFrappeMethod, isAuthError } from '@/services/frappeClient'
import { portalErrorMessage } from '@/services/portalErrors'

interface PortalErrorPayload {
  code: string
  message: string
  retryable: boolean
  trace_id?: string | null
}

interface PortalEnvelope<T> {
  ok: boolean
  data?: T
  error?: PortalErrorPayload
}

interface BackendUser {
  id: string
  display_name: string
  avatar_url?: string | null
  identity_provider?: string | null
}

interface BackendBranding {
  product_name: string
  company_name: string
  logo_url?: string | null
  workspace_name: string
}

interface BackendManifest {
  contract_version: number
  id: string
  title: string
  short_title: string
  description: string
  icon: string
  accent: string
  order: number
  migration_mode: 'legacy' | 'hybrid' | 'native'
  route: string
  capabilities: string[]
}

interface BackendApp {
  manifest: BackendManifest
  access: {
    can_enter: boolean
    capabilities?: string[]
    scopes?: Record<string, string[]>
  }
}

interface BackendBootstrap {
  contract_version: number
  generated_at: string
  user: BackendUser
  branding: BackendBranding
  apps: BackendApp[]
  preferences: {
    reduce_motion?: boolean | null
    density?: string
  }
}



interface BackendSummaryMetric {
  id: string
  label: string
  value: string | number
  tone: string
  deep_link?: string | null
}

interface BackendSummaryPayload {
  app_id: string
  generated_at: string
  scope_label?: string
  status?: string
  metrics: BackendSummaryMetric[]
}

interface BackendTask {
  task_id: string
  app_id: string
  category: string
  title: string
  description: string
  action: string
  action_label: string
  status?: string
  priority: string
  due_at?: string | null
  overdue?: boolean
  assignment_type: string
  deep_link: string
  modified_at?: string | null
}

interface BackendTaskPayload {
  tasks: BackendTask[]
  next_cursor?: string | null
  total?: number
}

interface BackendDispatch<T> {
  trace_id: string
  generated_at: string
  data: T
}

interface BackendRoutePayload {
  app_id: string
  stable_path: string
  resolved_path: string
  migration_mode: 'legacy' | 'hybrid' | 'native'
}

interface BackendSearchResult {
  app_id: string
  entity_type?: string
  entity_id?: string
  title: string
  subtitle?: string
  status?: string
  deep_link: string
}

interface BackendSearchPayload {
  query: string
  results: BackendSearchResult[]
  provider_errors: Array<{
    app_id: string
    code: string
    trace_id?: string | null
  }>
}

export class PortalApiError extends Error {
  code: string
  retryable: boolean
  traceId?: string | null

  constructor(error: PortalErrorPayload) {
    super(error.message)
    this.name = 'PortalApiError'
    this.code = error.code
    this.retryable = error.retryable
    this.traceId = error.trace_id
  }
}

function unwrap<T>(envelope: PortalEnvelope<T>): T {
  if (!envelope.ok || envelope.data === undefined) {
    throw new PortalApiError(
      envelope.error || {
        code: 'PROVIDER_ERROR',
        message: 'HBOS 服务返回了无效响应。',
        retryable: true,
      },
    )
  }
  return envelope.data
}

function makeAvatarText(displayName: string): string {
  const name = displayName.trim()
  if (!name) return 'HB'

  const parts = name.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0]?.[0] || ''}${parts[1]?.[0] || ''}`.toUpperCase()
  }

  return name.slice(0, 2).toUpperCase()
}

function normalizeIdentityProvider(
  value?: string | null,
): PortalUser['identityProvider'] {
  if (value === 'frappe' || value === 'feishu') return value
  return value ? 'other' : 'frappe'
}

function mapUser(user: BackendUser): PortalUser {
  return {
    id: user.id,
    displayName: user.display_name,
    avatarText: makeAvatarText(user.display_name),
    avatarUrl: user.avatar_url || null,
    identityProvider: normalizeIdentityProvider(user.identity_provider),
    roleLabel: 'HBOS User',
    department: '',
  }
}

function mapBranding(value: BackendBranding): PortalBranding {
  return {
    productName: value.product_name,
    companyName: value.company_name,
    logoUrl: value.logo_url || null,
    workspaceName: value.workspace_name,
  }
}

function mapApp(value: BackendApp): AppManifestDTO {
  const manifest = value.manifest
  const capabilities = new Set(manifest.capabilities || [])

  return {
    id: manifest.id,
    title: manifest.title,
    shortTitle: manifest.short_title,
    description: manifest.description,
    icon: manifest.icon,
    accent: manifest.accent,
    route: manifest.route,
    migrationMode: manifest.migration_mode,
    capabilitySummary: capabilities.has('summary'),
    capabilityTasks: capabilities.has('tasks'),
    capabilitySearch: capabilities.has('search'),
    capabilities: [...capabilities],
    accessCapabilities: [...(value.access.capabilities || [])],
    featured: ['knowledge', 'twin', 'lims', 'inventory', 'attendance'].includes(manifest.id),
  }
}



function normalizeTone(value: string): SummaryMetricDTO['tone'] {
  if (
    value === 'info' ||
    value === 'success' ||
    value === 'warning' ||
    value === 'critical'
  ) {
    return value
  }
  return 'neutral'
}

function normalizeTaskPriority(value: string): UnifiedTaskDTO['priority'] {
  if (value === 'critical' || value === 'high' || value === 'low') return value
  return 'normal'
}

function taskDuePresentation(dueAt?: string | null): Pick<UnifiedTaskDTO, 'dueLabel' | 'dueGroup'> {
  if (!dueAt) return { dueLabel: '无截止时间', dueGroup: 'later' }

  const raw = String(dueAt)
  const datePart = raw.slice(0, 10)
  const due = new Date(`${datePart}T00:00:00`)
  if (Number.isNaN(due.getTime())) {
    return { dueLabel: raw, dueGroup: 'later' }
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const diffDays = Math.round((due.getTime() - today.getTime()) / 86400000)
  const timeMatch = raw.match(/T(\d{2}:\d{2})/)
  const time = timeMatch?.[1] ? ` ${timeMatch[1]}` : ''

  if (diffDays === 0) return { dueLabel: `今天${time}`, dueGroup: 'today' }
  if (diffDays === 1) return { dueLabel: `明天${time}`, dueGroup: 'week' }
  if (diffDays < 0) return { dueLabel: `${Math.abs(diffDays)} 天前`, dueGroup: 'later' }

  return {
    dueLabel: `${due.getMonth() + 1}月${due.getDate()}日${time}`,
    dueGroup: diffDays <= 7 ? 'week' : 'later',
  }
}

export function normalizeTaskStatus(status?: string, action?: string): UnifiedTaskDTO['status'] {
  if (status === 'open' || status === 'waiting' || status === 'done') return status
  // 领域单据状态不等于待办状态：已完成时间点仍可等待趋势评价，已批准申请仍可等待执行。
  if (action) return 'open'
  if (['已完成', '已取消', '已关闭'].includes(status || '')) return 'done'
  if (['等待别人', '等待中', '挂起'].includes(status || '')) return 'waiting'
  return 'open'
}

function mapTask(task: BackendTask, appTitle: string): UnifiedTaskDTO {
  return {
    taskId: task.task_id,
    appId: task.app_id,
    appTitle,
    title: task.title,
    description: task.description,
    priority: normalizeTaskPriority(task.priority),
    ...taskDuePresentation(task.due_at),
    status: normalizeTaskStatus(task.status, task.action),
    domainStatus: task.status || undefined,
    action: task.action || undefined,
    actionLabel: task.action_label || undefined,
    assignmentType: task.assignment_type || undefined,
    category: task.category || undefined,
    overdue: Boolean(task.overdue),
    deepLink: task.deep_link,
  }
}

export async function getFrappePortalData() {
  const envelope = await callFrappeMethod<PortalEnvelope<BackendBootstrap>>(
    'hbos_portal.api.bootstrap.get_bootstrap',
  )
  const data = unwrap(envelope)

  return {
    user: mapUser(data.user),
    branding: mapBranding(data.branding),
    apps: data.apps
      .filter((app) => app.access?.can_enter)
      .map(mapApp),
    heroMetrics: [],
    tasks: [],
    businessPulse: [],
    twinStatuses: [],
    limsQueue: [],
  }
}


export async function getFrappeSummariesForApps(
  apps: AppManifestDTO[],
): Promise<ProviderBatch<SummaryMetricDTO>> {
  const summaryApps = apps.filter((app) => app.capabilitySummary)
  const batches = await Promise.allSettled(
    summaryApps.map(async (app) => {
      const envelope = await callFrappeMethod<
        PortalEnvelope<BackendDispatch<BackendSummaryPayload>>
      >('hbos_portal.api.summary.get_summary', {
        app_id: app.id,
      })
      const dispatch = unwrap(envelope)
      return (dispatch.data.metrics || []).map((metric) => ({
        id: `${app.id}:${metric.id}`,
        label: metric.label,
        value: metric.value,
        appId: app.id,
        tone: normalizeTone(metric.tone),
        meta: app.shortTitle,
        deepLink: metric.deep_link || undefined,
        scopeLabel: dispatch.data.scope_label || undefined,
        generatedAt: dispatch.data.generated_at || undefined,
        summaryStatus: dispatch.data.status || undefined,
      }))
    }),
  )

  return collectBatches(summaryApps, batches, '业务概览暂时不可用，请重试。')
}

function collectBatches<T>(apps: AppManifestDTO[], batches: PromiseSettledResult<T[]>[], fallback: string): ProviderBatch<T> {
  const items: T[] = []
  const errors: ProviderBatch<T>['errors'] = []
  batches.forEach((result, index) => {
    if (result.status === 'fulfilled') items.push(...result.value)
    else {
      if (isAuthError(result.reason)) throw result.reason
      const app = apps[index]!
      errors.push({ appId: app.id, appTitle: app.shortTitle,
        message: portalErrorMessage(result.reason, fallback) })
    }
  })
  return { items, errors }
}

export async function getFrappeTaskPage(app: AppManifestDTO, query: LimsTaskQuery = {}): Promise<TaskPage> {
  const envelope = await callFrappeMethod<PortalEnvelope<BackendDispatch<BackendTaskPayload>>>(
    'hbos_portal.api.tasks.get_tasks', {
      app_id: app.id, limit: query.limit || 20, cursor: query.cursor,
      ...(app.id === 'lims' ? { view: query.view, status: query.status,
        priority: query.priority, keyword: query.keyword } : {}),
    })
  const dispatch = unwrap(envelope)
  const items = (dispatch.data.tasks || []).map(task => mapTask(task, app.shortTitle))
  return { items, nextCursor: dispatch.data.next_cursor || null, total: dispatch.data.total ?? items.length }
}

/** Portal 汇总加载全部游标页，避免工作计数被第一页截断。单页界面使用 getFrappeTaskPage。 */
export async function getFrappeTasksForApps(apps: AppManifestDTO[], query: LimsTaskQuery = {}): Promise<ProviderBatch<UnifiedTaskDTO>> {
  const taskApps = apps.filter(app => app.capabilityTasks)
  const batches = await Promise.all(taskApps.map(async app => {
    const items = new Map<string, UnifiedTaskDTO>()
    const cursors = new Set<string>()
    try {
      let cursor: string | undefined
      do {
        const page = await getFrappeTaskPage(app, { ...query, cursor })
        page.items.forEach(task => items.set(task.taskId, task))
        cursor = page.nextCursor || undefined
        if (cursor && (cursors.has(cursor) || cursors.size >= 200)) {
          throw new Error('任务分页游标无效')
        }
        if (cursor) cursors.add(cursor)
      } while (cursor)
      return { items: [...items.values()], errors: [] }
    } catch (error) {
      if (isAuthError(error)) throw error
      return { items: [...items.values()], errors: [{ appId: app.id, appTitle: app.shortTitle,
        message: portalErrorMessage(error, '工作事项加载不完整，请重试。') }] }
    }
  }))
  return { items: batches.flatMap(batch => batch.items), errors: batches.flatMap(batch => batch.errors) }
}

export async function resolveFrappeRoute(
  appId: string,
  stablePath: string,
): Promise<string> {
  const envelope = await callFrappeMethod<PortalEnvelope<BackendRoutePayload>>(
    'hbos_portal.api.routes.resolve_route',
    {
      app_id: appId,
      stable_path: stablePath,
    },
  )
  return unwrap(envelope).resolved_path
}

export async function searchFrappePortal(
  query: string,
): Promise<ProviderBatch<SearchResultDTO>> {
  const envelope = await callFrappeMethod<PortalEnvelope<BackendSearchPayload>>(
    'hbos_portal.api.search.search',
    {
      query,
      limit: 20,
    },
  )
  const data = unwrap(envelope)

  const items = data.results.map((item) => ({
    id: `${item.app_id}:${item.entity_type || 'result'}:${item.entity_id || item.title}`,
    appId: item.app_id,
    appTitle: item.app_id.toUpperCase(),
    title: item.title,
    subtitle: [item.subtitle, item.status].filter(Boolean).join(' · '),
    typeLabel: item.entity_type || '结果',
    deepLink: item.deep_link,
  }))
  return { items, errors: (data.provider_errors || []).map(error => ({
    appId: error.app_id, appTitle: error.app_id,
    message: portalErrorMessage({ traceId: error.trace_id }, '此应用搜索暂时不可用，结果不完整。'),
  })) }
}
