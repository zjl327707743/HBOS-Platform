export type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'critical'
export type AppMigrationMode = 'legacy' | 'hybrid' | 'native'
export type PortalDataSource = 'mock' | 'frappe'

export interface PortalBranding {
  productName: string
  companyName: string
  logoUrl?: string | null
  workspaceName: string
}

export interface PortalUser {
  id: string
  displayName: string
  avatarText: string
  avatarUrl?: string | null
  identityProvider?: 'frappe' | 'feishu' | 'other'
  roleLabel: string
  department: string
}

export interface AppManifestDTO {
  id: string
  title: string
  shortTitle: string
  description: string
  icon: string
  accent: string
  route: string
  migrationMode: AppMigrationMode
  capabilitySummary: boolean
  capabilityTasks: boolean
  capabilitySearch: boolean
  /** Raw Provider capability keys; the LIMS shell projects these separately. */
  capabilities?: string[]
  /** Semantic capabilities returned by the owning app access context. */
  accessCapabilities?: string[]
  pendingCount?: number
  meta?: string
  featured?: boolean
}

export interface SummaryMetricDTO {
  id: string
  label: string
  value: string | number
  appId: string
  tone: Tone
  meta?: string
  deepLink?: string
  scopeLabel?: string
  generatedAt?: string
  summaryStatus?: string
}

export interface UnifiedTaskDTO {
  taskId: string
  appId: string
  appTitle: string
  title: string
  description: string
  priority: 'low' | 'normal' | 'high' | 'critical'
  dueLabel: string
  dueGroup: 'today' | 'week' | 'later'
  status: 'open' | 'waiting' | 'done'
  /** Domain status projected by the owning business Provider. */
  domainStatus?: string
  action?: string
  actionLabel?: string
  assignmentType?: string
  category?: string
  overdue?: boolean
  deepLink: string
}

export type LimsTaskView = 'my-testing' | 'my-review' | 'my-approval'

export interface LimsTaskQuery {
  view?: LimsTaskView
  status?: string
  priority?: UnifiedTaskDTO['priority']
  keyword?: string
  cursor?: string
  limit?: number
}

export interface ProviderBatch<T> {
  items: T[]
  errors: Array<{ appId: string; appTitle: string; message: string }>
}

export interface TaskPage {
  items: UnifiedTaskDTO[]
  nextCursor: string | null
  total: number
}

export interface BusinessPulseDTO {
  id: string
  label: string
  value: string
  trend?: string
  tone?: Tone
  sparkline?: number[]
}

export interface TwinStatusDTO {
  id: string
  label: string
  value: string
  progress?: number
  tone?: Tone
}

export interface SearchResultDTO {
  id: string
  appId: string
  appTitle: string
  title: string
  subtitle: string
  typeLabel: string
  deepLink: string
}

export interface LimsQueueItemDTO {
  id: string
  sample: string
  material: string
  action: string
  owner: string
  due: string
  status: string
  tone: Tone
}
