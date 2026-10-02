import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { isUnauthenticatedError } from '@/services/frappeClient'
import { usePortalStore } from '@/stores/portal'
import { accountRedirect } from '@/services/accountNavigation'

function safeRedirectTarget(fullPath: string): string {
  return accountRedirect(fullPath)
}

export function usePortalSession() {
  const portal = usePortalStore()
  const route = useRoute()
  const router = useRouter()
  const sessionPending = ref(true)
  const sessionError = ref<string | null>(null)

  let disposed = false
  let inflight: Promise<boolean> | null = null
  const resume = () => { if (document.visibilityState !== 'hidden') void synchronize() }
  async function runCheck(): Promise<boolean> {
    sessionError.value = null
    if (/^\/hbos\/(lims|knowledge|twin)(?:\/|$)/.test(route.path)) sessionPending.value = true
    try {
      await portal.bootstrap()
      if (disposed) return false
      const app = route.path.match(/^\/hbos\/(lims|knowledge|twin)(?:\/|$)/)?.[1]
      if (app && !portal.apps.some(candidate => candidate.id === app)) {
        await router.replace({ path: '/hbos/403', query: { app } })
        return false
      }
      return true
    } catch (error) {
      if (disposed) return false
      if (isUnauthenticatedError(error)) {
        const redirectTo = safeRedirectTarget(route.fullPath)
        portal.clearSession()
        await router.replace({
          path: '/hbos/login',
          query: { status: 'session_required', redirect_to: redirectTo },
        })
        return false
      }
      sessionError.value = error instanceof Error
        ? error.message
        : 'HBOS 初始化失败，请稍后重试。'
      return false
    } finally {
      if (!disposed) sessionPending.value = false
    }
  }
  async function synchronize(): Promise<boolean> {
    if (disposed) return false
    // 复用进行中的检查：重试与后台探测共享同一结果，重试不再被静默丢弃。
    inflight ||= runCheck().finally(() => { inflight = null })
    return inflight
  }
  onMounted(() => {
    void synchronize()
    window.addEventListener('focus', resume)
    window.addEventListener('pageshow', resume)
    document.addEventListener('visibilitychange', resume)
  })
  onBeforeUnmount(() => {
    disposed = true
    window.removeEventListener('focus', resume)
    window.removeEventListener('pageshow', resume)
    document.removeEventListener('visibilitychange', resume)
  })

  return { sessionPending, sessionError, synchronize }
}
