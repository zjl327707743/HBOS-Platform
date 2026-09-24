import type {
  AppManifestDTO,
  PortalBranding,
  PortalUser,
  SearchResultDTO,
  UnifiedTaskDTO,
} from '@/contracts/portal'
import { callFrappeMethod } from '@/services/frappeClient'

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


interface BackendTask {
  task_id: string
  app_id: string
  category: string
  title: string
  description: string
  action: string
  action_label: string
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
  }
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

function mapTask(task: BackendTask, appTitle: string): UnifiedTaskDTO {
  return {
    taskId: task.task_id,
    appId: task.app_id,
    appTitle,
    title: task.title,
    description: task.description,
    priority: normalizeTaskPriority(task.priority),
    ...taskDuePresentation(task.due_at),
    status: 'open',
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


export async function getFrappeTasksForApps(
  apps: AppManifestDTO[],
): Promise<UnifiedTaskDTO[]> {
  const taskApps = apps.filter((app) => app.capabilityTasks)
  const batches = await Promise.allSettled(
    taskApps.map(async (app) => {
      const envelope = await callFrappeMethod<
        PortalEnvelope<BackendDispatch<BackendTaskPayload>>
      >('hbos_portal.api.tasks.get_tasks', {
        app_id: app.id,
        limit: 20,
      })
      const dispatch = unwrap(envelope)
      return (dispatch.data.tasks || []).map((task) =>
        mapTask(task, app.shortTitle),
      )
    }),
  )

  return batches.flatMap((result) =>
    result.status === 'fulfilled' ? result.value : [],
  )
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
): Promise<SearchResultDTO[]> {
  const envelope = await callFrappeMethod<PortalEnvelope<BackendSearchPayload>>(
    'hbos_portal.api.search.search',
    {
      query,
      limit: 20,
    },
  )
  const data = unwrap(envelope)

  return data.results.map((item) => ({
    id: `${item.app_id}:${item.entity_type || 'result'}:${item.entity_id || item.title}`,
    appId: item.app_id,
    appTitle: item.app_id,
    title: item.title,
    subtitle: [item.subtitle, item.status].filter(Boolean).join(' · '),
    typeLabel: item.entity_type || '结果',
    deepLink: item.deep_link,
  }))
}
