import { isSafeInternalPath } from '@/services/internalPath'
import type { Router } from 'vue-router'
import { portalDataSource, resolveBusinessRoute } from '@/services/portalProvider'
import { message } from 'ant-design-vue'
import { callFrappeMethod, FrappeRequestError } from '@/services/frappeClient'

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

export async function openBusinessRoute(
  router: Router,
  appId: string,
  stablePath: string,
) {
  let target: string
  try {
    target = await resolveBusinessRoute(appId, stablePath)
  } catch (error) {
    if (error instanceof FrappeRequestError && ['UNAUTHENTICATED', 'FORBIDDEN'].includes(error.code)) {
      const session = await callFrappeMethod<{ csrf_token?: string }>('hbos_portal.auth.accounts.get_request_security').catch(() => null)
      if (session && !session.csrf_token) {
        message.info('登录状态已失效，请重新登录。')
        await router.push({ path: '/hbos/login', query: { redirect_to: stablePath } })
        return
      }
    }
    message.warning(error instanceof Error ? error.message : '应用暂时无法打开，请稍后重试。')
    return
  }

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
