import type { Router } from 'vue-router'
import { portalDataSource, resolveBusinessRoute } from '@/services/portalProvider'

function normalizeOrigin(value: string): string {
  return value.trim().replace(/\/+$/, '')
}

export function businessNavigationTarget(target: string): string | null {
  if (!isSafeInternalPath(target)) return null
  if (portalDataSource !== 'frappe') return target

  // Stable/native Portal routes belong to the Portal SPA itself.
  if (target.startsWith('/hbos/')) return target

  const frappeOrigin = normalizeOrigin(
    import.meta.env.VITE_FRAPPE_APP_ORIGIN || '',
  )

  if (!frappeOrigin) return target

  return `${frappeOrigin}${target}`
}

function isSafeInternalPath(target: string): boolean {
  if (!target.startsWith('/')
    || target.startsWith('//')
    || target.startsWith('/\\')
    || target.includes('\\')
    || /%(?:2f|2e|5c)/i.test(target)) return false
  try {
    const decoded = decodeURIComponent(target)
    const segments = decoded.split('/')
    return !segments.includes('.') && !segments.includes('..')
  } catch {
    return false
  }
}

export async function openBusinessRoute(
  router: Router,
  appId: string,
  stablePath: string,
) {
  const target = await resolveBusinessRoute(appId, stablePath)

  // Keep LIMS on the Portal frontend while the user-facing pages are designed.
  // The resolver still validates the current user's access in Frappe mode.
  if (appId === 'lims') {
    if (!isSafeInternalPath(stablePath)
      || !(stablePath === '/hbos/lims' || stablePath.startsWith('/hbos/lims/'))) {
      await router.replace({ name: 'forbidden' })
      return
    }
    await router.push(stablePath)
    return
  }

  const navigationTarget = businessNavigationTarget(target)

  if (!navigationTarget) {
    await router.replace({ name: 'forbidden' })
    return
  }

  if (navigationTarget === target && target.startsWith('/hbos/')) {
    await router.push(target)
    return
  }

  window.location.assign(navigationTarget)
}
