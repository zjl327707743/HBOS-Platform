import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { isUnauthenticatedError } from '@/services/frappeClient'
import { usePortalStore } from '@/stores/portal'

function safeRedirectTarget(fullPath: string): string {
  return fullPath.startsWith('/hbos') && !fullPath.startsWith('/hbos/login')
    ? fullPath
    : '/hbos'
}

export function usePortalSession() {
  const portal = usePortalStore()
  const route = useRoute()
  const router = useRouter()
  const sessionPending = ref(true)
  const sessionError = ref<string | null>(null)

  onMounted(async () => {
    try {
      await portal.bootstrap()
    } catch (error) {
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
      sessionPending.value = false
    }
  })

  return { sessionPending, sessionError }
}
