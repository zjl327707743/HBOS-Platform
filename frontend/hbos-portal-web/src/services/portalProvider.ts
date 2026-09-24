import {
  appManifests,
  businessPulse,
  heroMetrics,
  limsQueue,
  portalUser,
  searchResults,
  tasks,
  twinStatuses,
} from '@/data/mockPortal'
import {
  getFrappePortalData,
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
    return getFrappePortalData()
  }
  return getMockPortalData()
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
  if (portalDataSource === 'frappe') {
    return searchFrappePortal(query)
  }

  await sleep(90)
  const q = query.trim().toLowerCase()
  if (!q) return searchResults
  return searchResults.filter((item) =>
    `${item.title} ${item.subtitle} ${item.appTitle} ${item.typeLabel}`.toLowerCase().includes(q),
  )
}
