import { resolvePortalDataMode } from '@/contracts/dataMode'
import {
  getFrappePortalData, getFrappeSummariesForApps, getFrappeTasksForApps,
  getFrappeTaskPage, resolveFrappeRoute, searchFrappePortal,
} from '@/services/portalApi'
import type { AppManifestDTO, LimsTaskQuery, PortalBranding, TaskPage } from '@/contracts/portal'

export const portalDataSource = resolvePortalDataMode(import.meta.env.VITE_PORTAL_DATA_MODE)
const mockData = () => import('@/data/mockPortal')
const mockBranding: PortalBranding = {
  productName: 'HBOS', companyName: '海滨', logoUrl: null, workspaceName: '海滨智能运营工作台',
}

export async function getPortalData() {
  if (portalDataSource === 'frappe') return getFrappePortalData()
  const data = await mockData()
  return {
    user: data.portalUser, branding: mockBranding, apps: data.appManifests,
    heroMetrics: data.heroMetrics, tasks: data.tasks, businessPulse: data.businessPulse,
    twinStatuses: data.twinStatuses, limsQueue: data.limsQueue,
  }
}

export async function getPortalSummaries(apps: AppManifestDTO[]) {
  if (portalDataSource === 'frappe') return getFrappeSummariesForApps(apps)
  return { items: (await mockData()).heroMetrics, errors: [] }
}

export async function getPortalTasks(apps: AppManifestDTO[], query: LimsTaskQuery = {}) {
  if (portalDataSource === 'frappe') return getFrappeTasksForApps(apps, query)
  return { items: (await mockData()).tasks, errors: [] }
}

export async function getPortalTaskPage(app: AppManifestDTO, query: LimsTaskQuery = {}): Promise<TaskPage> {
  if (portalDataSource === 'frappe') return getFrappeTaskPage(app, query)
  const actions = {
    'my-testing': ['start_task', 'submit_result', 'start_testing', 'record_result', 'complete_sampling'],
    'my-review': ['review_result', 'review_observation', 'eval_trend'],
    'my-approval': ['approve_result', 'publish_coa', 'confirm_stock'],
  }
  const items = (await mockData()).tasks.filter(task => task.appId === app.id)
    .filter(task => !query.view || !task.action || actions[query.view].includes(task.action))
    .filter(task => !query.status || task.domainStatus === query.status)
    .filter(task => !query.priority || task.priority === query.priority)
    .filter(task => !query.keyword || `${task.title} ${task.description}`.includes(query.keyword))
  const offset = Number(query.cursor || 0)
  const limit = query.limit || 20
  return { items: items.slice(offset, offset + limit), total: items.length,
    nextCursor: offset + limit < items.length ? String(offset + limit) : null }
}

export async function resolveBusinessRoute(appId: string, stablePath: string) {
  if (portalDataSource === 'frappe') return resolveFrappeRoute(appId, stablePath)
  return stablePath
}

export async function searchPortal(query: string) {
  const normalizedQuery = query.trim()
  if (portalDataSource === 'frappe') {
    if (!normalizedQuery) return []
    return searchFrappePortal(normalizedQuery)
  }
  const { searchResults } = await mockData()
  const q = normalizedQuery.toLowerCase()
  return q ? searchResults.filter(item =>
    `${item.title} ${item.subtitle} ${item.appTitle} ${item.typeLabel}`.toLowerCase().includes(q)) : searchResults
}
