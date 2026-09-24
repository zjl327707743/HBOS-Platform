import type { Router } from 'vue-router'
import { resolveBusinessRoute } from '@/services/portalProvider'

export async function openBusinessRoute(
  router: Router,
  appId: string,
  stablePath: string,
) {
  const target = await resolveBusinessRoute(appId, stablePath)

  if (target.startsWith('/hbos/')) {
    await router.push(target)
    return
  }

  window.location.assign(target)
}
