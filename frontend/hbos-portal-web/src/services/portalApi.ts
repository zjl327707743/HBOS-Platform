import type {
  AppManifestDTO,
  PortalBranding,
  PortalUser,
  SearchResultDTO,
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
