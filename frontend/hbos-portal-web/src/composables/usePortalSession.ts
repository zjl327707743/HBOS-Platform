import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { isUnauthenticatedError } from '@/services/frappeClient'
import { usePortalStore } from '@/stores/portal'
import { accountRedirect } from '@/services/accountNavigation'

function safeRedirectTarget(fullPath: string): string {
  return accountRedirect(fullPath)
}

/**
 * Session bootstrap plus resume handling.
 *
 * Two rules drive this composable:
 *
 * 1. A resume (tab focus, ``pageshow``, ``visibilitychange``) is a *re-check*,
 *    never a page reload. The page keeps the answer, draft, scroll position and
 *    focus it already had, and no skeleton is raised over established content.
 *    Only the first load — or a hard authentication failure — may show the
 *    pending state.
 * 2. A transient failure is not a revocation. Network and service errors keep
 *    the current page and its authorized content. Only an authentication error
 *    clears the session and redirects to the login page; a manifest change
 *    still redirects to 403.
 *
 * The composable never triggers a knowledge or model request. Views decide what
 * to refresh from ``sessionRevision``, which advances only after a *successful*
 * re-verification.
 */
export function usePortalSession() {
  const portal = usePortalStore()
  const route = useRoute()
  const router = useRouter()
  const sessionPending = ref(true)
  const sessionError = ref<string | null>(null)
  // Advances after every successful re-verification. Views watch it to refresh
  // authorization state in place, without being torn down or re-asking a model.
  const sessionRevision = ref(0)

  let disposed = false
  let checking = false
  // True once a bootstrap has succeeded in this page lifetime. It is cleared
  // only by a real authentication failure, so a later transient error cannot
  // promote itself into a "you were logged out" screen.
  let established = false
  // Signature of the last successfully verified identity and app set. It is
  // the ONLY thing that advances ``sessionRevision``: a resume that returns the
  // same user and the same apps has nothing new for the views to read, and
  // bumping it anyway made every focus re-pull the knowledge catalogue.
  let identitySignature = ''

  const resume = () => {
    if (document.visibilityState !== 'hidden') void synchronize(true)
  }

  async function synchronize(soft = false) {
    // Single-flight: repeated focus/pageshow/visibilitychange events must not
    // stack concurrent status requests.
    if (disposed || checking) return
    checking = true
    sessionError.value = null
    const showPending = !soft || !established
    if (showPending && /^\/hbos\/(lims|knowledge|twin)(?:\/|$)/.test(route.path)) sessionPending.value = true
    try {
      await portal.bootstrap({ light: soft })
      if (disposed) return
      const app = route.path.match(/^\/hbos\/(lims|knowledge|twin)(?:\/|$)/)?.[1]
      if (app && !portal.apps.some(candidate => candidate.id === app)) {
        await router.replace({ path: '/hbos/403', query: { app } })
        return
      }
      established = true
      // Only a changed identity or app set needs the views to re-read state.
      // Bumping this unconditionally made every resume look like a refresh to
      // KnowledgeView, which then re-pulled the catalogue and lost scroll.
      // The first successful load records the signature without a bump: the
      // views are mounting for the first time and read their state themselves.
      const nextSignature = `${portal.user?.id ?? ''}|${portal.apps.map(app => app.id).join(',')}`
      if (identitySignature && nextSignature !== identitySignature) sessionRevision.value++
      identitySignature = nextSignature
    } catch (error) {
      if (disposed) return
      if (isUnauthenticatedError(error)) {
        // A real unauthenticated response is the only resume outcome that may
        // discard protected content.
        const redirectTo = safeRedirectTarget(route.fullPath)
        established = false
        portal.clearSession()
        await router.replace({
          path: '/hbos/login',
          query: { status: 'session_required', redirect_to: redirectTo },
        })
        return
      }
      // Transient network/service failure: keep the current page and its
      // already-authorized content. Report the error only when nothing was
      // established yet; otherwise the user keeps working.
      if (!established) {
        sessionError.value = error instanceof Error
          ? error.message
          : 'HBOS 初始化失败，请稍后重试。'
      }
    } finally {
      if (!disposed && showPending) sessionPending.value = false
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

  return { sessionPending, sessionError, sessionRevision }
}
