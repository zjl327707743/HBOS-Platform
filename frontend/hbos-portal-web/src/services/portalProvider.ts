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

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export async function getPortalPrototypeData() {
  await sleep(180)
  return {
    user: portalUser,
    apps: appManifests,
    heroMetrics,
    tasks,
    businessPulse,
    twinStatuses,
    limsQueue,
  }
}

export async function searchPortal(query: string) {
  await sleep(90)
  const q = query.trim().toLowerCase()
  if (!q) return searchResults
  return searchResults.filter((item) =>
    `${item.title} ${item.subtitle} ${item.appTitle} ${item.typeLabel}`.toLowerCase().includes(q),
  )
}
