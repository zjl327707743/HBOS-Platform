import type { Router } from 'vue-router'
import { portalDataSource, resolveBusinessRoute } from '@/services/portalProvider'
import { alignLoopbackHost } from '@/services/frappeClient'

function normalizeOrigin(value: string): string {
  return value.trim().replace(/\/+$/, '')
}

export function businessNavigationTarget(target: string): string {
  if (portalDataSource !== 'frappe') return target

  // Stable/native Portal routes belong to the Portal SPA itself.
  if (target.startsWith('/hbos/')) return target

  // 主机名对齐的理由见 `frappeClient.alignLoopbackHost` 的注释
  // （Frappe 的 sid 是 host-only cookie，localhost 与 127.0.0.1 互不相通）
  const frappeOrigin = alignLoopbackHost(
    normalizeOrigin(import.meta.env.VITE_FRAPPE_APP_ORIGIN || ''),
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

  if (navigationTarget === target && target.startsWith('/hbos/')) {
    await router.push(target)
    return
  }

  window.location.assign(navigationTarget)
}
