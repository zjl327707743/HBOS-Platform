import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { isUnauthenticatedError } from '@/services/frappeClient'
import { usePortalStore } from '@/stores/portal'
import { accountRedirect } from '@/services/accountNavigation'
import { portalDataSource } from '@/services/portalProvider'
import { attachPortalSession, ensurePortalSession, portalSession, resetPortalSession } from '@/services/portalSessionCoordinator'
import { attendanceCapabilityAllowed, attendancePathCapability } from '@/services/attendanceNav'

/** App shells share the same subject lifecycle as PortalLayout. */
export function usePortalSession() {
  const portal = usePortalStore(), route = useRoute(), router = useRouter()
  const mockPending = ref(true), mockError = ref<string | null>(null)
  let disposed = false, initialized = false, detach: (() => void) | undefined, domainFlight: Promise<boolean> | null = null
  const accessChecking = ref(false), accessError = ref<string | null>(null)
  const accessApproved = ref(false)
  // Advances only after a *successful* re-verification that changed the signed-in
  // subject or the authorized app set. The knowledge workspace watches it to
  // refresh authorization in place; a resume with nothing new must not look like
  // a refresh to the views, or every tab switch re-pulls the catalogue and the
  // reader loses its position.
  const sessionRevision = ref(0)
  let identitySignature = ''
  watch(() => portalSession.generation, () => {
    accessApproved.value = false
    // A confirmed session boundary (login, logout, subject change) after this
    // page had already verified an identity is always worth a re-read. The
    // boundary raised while the first identity is being established is not a
    // change: the views are mounting and read their own state.
    if (identitySignature) sessionRevision.value++
    identitySignature = ''
  }, { flush: 'sync' })
  const real = portalDataSource === 'frappe'
  const sessionPending = computed(() => real ? !portalSession.mounted && portalSession.phase === 'initial' : mockPending.value)
  const sessionError = computed(() => real ? portalSession.error || accessError.value || null : mockError.value)
  const sessionReady = computed(() => accessApproved.value && (real ? portalSession.mounted : !mockPending.value && !!portal.user))
  const sessionGeneration = computed(() => real ? portalSession.generation : 0)
  const sessionBlocked = computed(() => real && (!accessApproved.value || accessChecking.value || !!accessError.value || !portalSession.mounted || ['unconfirmed','guest','logging_out','password_required'].includes(portalSession.phase)))
  function recordVerifiedIdentity() {
    const next = `${portal.user?.id ?? ''}|${portal.apps.map(app => app.id).join(',')}`
    if (identitySignature && next !== identitySignature) sessionRevision.value++
    identitySignature = next
  }
  function checkAccess(refresh = false): Promise<boolean> {
    if (domainFlight) return domainFlight
    const pending = (async () => {
      accessError.value = null
      accessChecking.value = refresh
      try {
        if (refresh) {
          const generation = portalSession.generation
          // The resume re-check needs the identity and the manifest, not the
          // home feed: a light bootstrap keeps metrics, tasks, pulse and the
          // LIMS queue that this payload does not carry.
          await portal.bootstrap({ light: true })
          if (disposed || generation !== portalSession.generation) return false
          if (portal.user?.id !== portalSession.security?.user) {
            resetPortalSession(false)
            await ensurePortalSession({ force: true })
          }
        }
        if (disposed) return false
        const app = route.path.match(/^\/hbos\/(attendance|lims|knowledge|twin|inventory|production)(?:\/|$)/)?.[1]
        if (app && !portal.apps.some(candidate => candidate.id === app)) {
          accessApproved.value = false
          await router.replace({ path: '/hbos/403', query: { app } })
          return false
        }
        if (app === 'attendance') {
          const manifest=portal.apps.find(candidate=>candidate.id===app)
          const capabilities=manifest?.accessCapabilities || []
          const required=attendancePathCapability(route.path)
          const allowed=attendanceCapabilityAllowed(required,capabilities)
          if (capabilities.includes('attendance.role.managed') && !allowed) {
            accessApproved.value=false
            await router.replace({path:'/hbos/403',query:{app}})
            return false
          }
        }
        accessApproved.value = true
        recordVerifiedIdentity()
        return true
      } catch (error) {
        if (!disposed) accessError.value = error instanceof Error ? error.message : '暂时无法核对应用权限，请重试。'
        return false
      } finally { accessChecking.value = false }
    })()
    domainFlight = pending
    void pending.finally(() => { if (domainFlight === pending) domainFlight = null })
    return pending
  }
  const confirmed = () => { if (initialized && !disposed && /\/hbos\/(attendance|lims|knowledge|twin|inventory|production)(?:\/|$)/.test(route.path)) void checkAccess(true) }
  async function synchronize(): Promise<boolean> {
    if (disposed) return false
    try {
      if (real) {
        const security = await ensurePortalSession({ force: true })
        if (disposed) return false
        if (security.first_password_required) { await router.replace('/hbos/profile'); return false }
      } else {
        mockError.value = null
        await portal.bootstrap()
      }
      return await checkAccess(false)
    } catch (error) {
      if (disposed) return false
      if (isUnauthenticatedError(error)) {
        await router.replace({ path: '/hbos/login', query: { status: 'session_required', redirect_to: accountRedirect(route.fullPath) } })
      } else if (!real) mockError.value = error instanceof Error ? error.message : 'HBOS 初始化失败，请稍后重试。'
      return false
    } finally { mockPending.value = false; initialized = true }
  }
  onMounted(() => { if (real) { detach = attachPortalSession(); window.addEventListener('hbos:security-confirmed', confirmed) }; void synchronize() })
  onBeforeUnmount(() => { disposed = true; detach?.(); window.removeEventListener('hbos:security-confirmed', confirmed) })
  return { sessionPending, sessionError, sessionReady, sessionBlocked, sessionGeneration, sessionRevision, synchronize }
}
