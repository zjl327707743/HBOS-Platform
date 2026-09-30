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

  let disposed = false, checking = false
  const resume = () => { if (document.visibilityState !== 'hidden') void synchronize() }
  async function synchronize() {
    if (disposed || checking) return
    checking = true; sessionError.value = null
    if (/^\/hbos\/(lims|knowledge|twin)(?:\/|$)/.test(route.path)) sessionPending.value = true
    try {
      await portal.bootstrap()
      if (disposed) return
      const app = route.path.match(/^\/hbos\/(lims|knowledge|twin)(?:\/|$)/)?.[1]
      if (app && !portal.apps.some(candidate => candidate.id === app)) {
        await router.replace({ path: '/hbos/403', query: { app } })
        return
      }
    } catch (error) {
      if (disposed) return
      if (isUnauthenticatedError(error)) {
        const redirectTo = safeRedirectTarget(route.fullPath)
        portal.clearSession()
        await router.replace({
          path: '/hbos/login',
          query: { status: 'session_required', redirect_to: redirectTo },
        })
        return
      }
      sessionError.value = error instanceof Error
        ? error.message
        : 'HBOS 初始化失败，请稍后重试。'
    } finally {
      if (!disposed) sessionPending.value = false
      checking = false
    }
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

  return { sessionPending, sessionError }
}
