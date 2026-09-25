import type { Router } from 'vue-router'
import { portalDataSource, resolveBusinessRoute } from '@/services/portalProvider'

function normalizeOrigin(value: string): string {
  return value.trim().replace(/\/+$/, '')
}

export function businessNavigationTarget(target: string): string {
  if (portalDataSource !== 'frappe') return target

  const frappeOrigin = normalizeOrigin(
    import.meta.env.VITE_FRAPPE_APP_ORIGIN || '',
  )

  if (!frappeOrigin || !target.startsWith('/')) return target

  return `${frappeOrigin}${target}`
}

export async function openBusinessRoute(
  router: Router,
  appId: string,
  stablePath: string,
) {
  const target = await resolveBusinessRoute(appId, stablePath)
  const navigationTarget = businessNavigationTarget(target)

  // Mock mode and same-origin native Portal routes remain SPA navigation.
  // In Frappe dev/preview mode, VITE_FRAPPE_APP_ORIGIN makes resolved
  // implementation routes absolute so /app/... and /hbos-lims/... do not
  // accidentally stay on the Vite origin.
  if (
    navigationTarget === target &&
    target.startsWith('/hbos/')
  ) {
    await router.push(target)
    return
  }

  window.location.assign(navigationTarget)
}
