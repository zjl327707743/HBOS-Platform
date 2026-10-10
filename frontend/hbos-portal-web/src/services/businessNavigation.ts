import type { Router } from 'vue-router'
import { portalDataSource, resolveBusinessRoute } from '@/services/portalProvider'
import { alignLoopbackHost } from '@/services/frappeClient'
import { frontendModules } from '@/data/mockPortal'
import { isNativePortalPath } from '@/router/nativeRoutes'

function normalizeOrigin(value: string): string {
  return value.trim().replace(/\/+$/, '')
}

/** 前端自有模块的 id 集合（如生产看板）。 */
const FRONTEND_MODULE_IDS = new Set(frontendModules.map((app) => app.id))

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
  // 前端自有模块（如生产看板）**不问后端**。
  //
  // 它在 hbos_portal 的注册表里没有 provider（与 Frappe 无关），
  // 调 resolve_route 会直接被拒 —— 而这里的 await 一抛异常，
  // 后面的导航就整段不执行，表现为**点了没反应**。
  // 它的路由本来就在 SPA 内，直接 push 即可。
  if (FRONTEND_MODULE_IDS.has(appId) && isNativePortalPath(stablePath)) {
    await router.push(stablePath)
    return
  }

  const target = await resolveBusinessRoute(appId, stablePath)
  const navigationTarget = businessNavigationTarget(target)

  if (navigationTarget === target && target.startsWith('/hbos/')) {
    await router.push(target)
    return
  }

  window.location.assign(navigationTarget)
}
