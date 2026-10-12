import {
  appManifests,
  businessPulse,
  frontendModules,
  heroMetrics,
  limsQueue,
  portalUser,
  searchResults,
  tasks,
  twinStatuses,
} from '@/data/mockPortal'
import {
  getFrappePortalData,
  getFrappeSummariesForApps,
  getFrappeTasksForApps,
  resolveFrappeRoute,
  searchFrappePortal,
} from '@/services/portalApi'
import type { AppManifestDTO, PortalBranding, PortalDataSource } from '@/contracts/portal'

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const mode = (import.meta.env.VITE_PORTAL_DATA_MODE || 'mock').toLowerCase()

export const portalDataSource: PortalDataSource =
  mode === 'frappe' ? 'frappe' : 'mock'

const mockBranding: PortalBranding = {
  productName: 'HBOS',
  companyName: '海滨',
  logoUrl: null,
  workspaceName: '海滨智能运营工作台',
}

/**
 * 把**前端自有模块**并入后端/ mock 返回的 apps。
 *
 * 生产看板与 Frappe 无关，后端 provider 里没有它，所以在这一层补上 ——
 * `getPortalData` 是两条数据源（mock / frappe）的唯一汇合点，
 * 放这里比分别改两边少一处遗漏（此前 Portal 出过「页面在、入口被挡」的漏改）。
 *
 * 判重按 `id`：将来若真有了后端 provider，也不会出现两个 production。
 */
function withFrontendModules<T extends { apps: AppManifestDTO[] }>(data: T): T {
  const known = new Set(data.apps.map((app) => app.id))
  const missing = frontendModules.filter((app) => !known.has(app.id))
  if (!missing.length) return data
  return { ...data, apps: [...data.apps, ...missing] }
}

async function getMockPortalData() {
  await sleep(180)
  return {
    user: portalUser,
    branding: mockBranding,
    apps: appManifests,
    heroMetrics,
    tasks,
    businessPulse,
    twinStatuses,
    limsQueue,
  }
}

export async function getPortalData() {
  if (portalDataSource === 'frappe') {
    return withFrontendModules(await getFrappePortalData())
  }
  return withFrontendModules(await getMockPortalData())
}


export async function getPortalSummaries(apps: AppManifestDTO[]) {
  if (portalDataSource === 'frappe') {
    return getFrappeSummariesForApps(apps)
  }
  return heroMetrics
}

export async function getPortalTasks(apps: AppManifestDTO[]) {
  if (portalDataSource === 'frappe') {
    return getFrappeTasksForApps(apps)
  }
  return tasks
}

export async function resolveBusinessRoute(appId: string, stablePath: string) {
  if (portalDataSource === 'frappe') {
    return resolveFrappeRoute(appId, stablePath)
  }
  return stablePath
}

export async function searchPortal(query: string) {
  const normalizedQuery = query.trim()

  if (portalDataSource === 'frappe') {
    if (!normalizedQuery) return []
    return searchFrappePortal(normalizedQuery)
  }

  await sleep(90)
  const q = normalizedQuery.toLowerCase()
  if (!q) return searchResults
  return searchResults.filter((item) =>
    `${item.title} ${item.subtitle} ${item.appTitle} ${item.typeLabel}`.toLowerCase().includes(q),
  )
}
