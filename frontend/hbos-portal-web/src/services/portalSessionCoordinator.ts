import { reactive } from 'vue'
import { usePortalStore } from '@/stores/portal'
import { getIamSecurity, type IamSecurity } from './iamAccount'
import { applyIamAccess, clearIamAccess, fetchIamAccess, iamSession } from './iamAccess'
import { blockFrappeWrites, invalidateFrappeRequests, isUnauthenticatedError, FrappeRequestError, logoutFrappeSession } from './frappeClient'
import { getSecurity, type SecurityStatus } from './accountApi'
import { confirmAttendanceSubject, forgetAttendanceState } from './attendancePageState'
import { observeResume } from './attendanceObservation'

export const portalSession = reactive({
  phase: 'initial' as 'initial' | 'ready' | 'password_required' | 'checking' | 'unconfirmed' | 'guest' | 'logging_out',
  security: null as IamSecurity | null, error: '', generation: 0, checkedAt: 0, mounted: false,
  resumeEvents: 0,
})
let flight: Promise<IamSecurity> | null = null, revision = 0
let resumeTimer: ReturnType<typeof setTimeout> | undefined, slowTimer: ReturnType<typeof setTimeout> | undefined
let consumers = 0
const channel = typeof window !== 'undefined' && window.BroadcastChannel ? new BroadcastChannel('hbos-session-boundary') : null
if (channel) channel.onmessage = message => {
  if (!['changed','suspend','signed_out'].includes(message.data)) return
  resetPortalSession(false)
  if (message.data === 'signed_out') portalSession.phase = 'guest'
  else if (message.data === 'suspend') { portalSession.phase = 'unconfirmed'; portalSession.error = '其他窗口正在切换登录状态。请稍后核验或重新登录。' }
  else if (consumers) void ensurePortalSession({force:true}).catch(() => undefined)
}
const FRESH_MS = 5000
let proofFlight: Promise<SecurityStatus> | null = null
export async function refreshAccountProof(): Promise<SecurityStatus> {
  if (consumers) return ensurePortalSession({force:true})
  // Account recovery/change pages outside PortalLayout do not bootstrap any
  // business content. Their mounted proof controls share this protected read.
  if (proofFlight) return proofFlight
  const pending = getSecurity(); proofFlight = pending
  try { const status = await pending; event('hbos:security-confirmed', status.proof); return status }
  finally { if (proofFlight === pending) proofFlight = null }
}
function event(name: string, detail?: unknown) { if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent(name, { detail })) }
function boundary() {
  proofFlight = null
  invalidateFrappeRequests(); blockFrappeWrites(true); clearIamAccess(); usePortalStore().clearSession()
  portalSession.generation++; portalSession.mounted = false; portalSession.security = null; portalSession.checkedAt = 0
  event('hbos:session-boundary')
}
/** Explicit login/logout or a confirmed native session boundary only. */
export function resetPortalSession(notify = true) {
  forgetAttendanceState()
  revision++; flight = null; if (slowTimer) clearTimeout(slowTimer); if (resumeTimer) clearTimeout(resumeTimer)
  boundary(); portalSession.phase = 'initial'; portalSession.error = ''
  if (notify) channel?.postMessage('changed')
}
export function requirePortalRecheck() { portalSession.checkedAt = 0 }
export async function ensurePortalSession(options: { force?: boolean } = {}): Promise<IamSecurity> {
  if (flight) return flight
  if (!options.force && portalSession.security && ['ready', 'password_required'].includes(portalSession.phase) && Date.now() - portalSession.checkedAt < FRESH_MS) return portalSession.security
  const run = revision, previous = portalSession.security, previousRevision = iamSession.revision, previousApps = { ...iamSession.appRevisions }
  const background = !!previous && (portalSession.mounted || previous.first_password_required), uncertain = portalSession.phase === 'unconfirmed'
  portalSession.error = ''; portalSession.phase = background ? (uncertain ? 'unconfirmed' : 'checking') : 'initial'; blockFrappeWrites(true)
  if (slowTimer) clearTimeout(slowTimer)
  // A slow/failed check masks retained data without destroying the draft subtree.
  slowTimer = setTimeout(() => { if (run === revision && portalSession.phase === 'checking') portalSession.phase = 'unconfirmed' }, 800)
  const pending = (async () => {
    try {
      const security = await getIamSecurity()
      if (run !== revision) throw new FrappeRequestError('STALE_RESPONSE', '会话已改变。')
      const newContext = !previous || previous.user !== security.user || previous.session_context !== security.session_context
      if (previous && previous.user !== security.user) forgetAttendanceState()
      if (newContext) boundary()
      portalSession.security = security
      if (security.first_password_required) {
        if (portalSession.mounted) { boundary(); portalSession.security = security }
        clearIamAccess(); portalSession.phase = 'password_required'; blockFrappeWrites(false)
      } else {
        const capabilities = await fetchIamAccess(security.user, security.session_context)
        if (run !== revision) throw new FrappeRequestError('STALE_RESPONSE', '会话已改变。')
        applyIamAccess(capabilities)
        if (newContext) {
          await confirmAttendanceSubject(window.location.host, security.user, security.session_context, portalSession.generation, previous?.user === security.user)
          if (run !== revision) throw new FrappeRequestError('STALE_RESPONSE', '会话已改变。')
        }
        if (!portalSession.mounted) {
          await usePortalStore().bootstrap()
          if (run !== revision) throw new FrappeRequestError('STALE_RESPONSE', '会话已改变。')
          if (usePortalStore().user?.id !== security.user) throw new FrappeRequestError('SESSION_UNCONFIRMED', '当前账号尚未确认，请重新核验。')
          portalSession.mounted = true
        }
        portalSession.phase = 'ready'; blockFrappeWrites(false)
        if (previous && previousRevision !== capabilities.policy_revision) {
          const nextApps = capabilities.app_revisions
          const apps = nextApps && Object.keys(previousApps).length ? [...new Set([...Object.keys(previousApps), ...Object.keys(nextApps)])].filter(app => previousApps[app] !== nextApps[app]) : null
          event('hbos:permissions-changed', { apps })
        }
      }
      portalSession.checkedAt = Date.now(); event('hbos:security-confirmed', security.proof)
      return security
    } catch (error) {
      if (run !== revision) throw error
      blockFrappeWrites(true)
      if (isUnauthenticatedError(error)) { forgetAttendanceState(); boundary(); portalSession.phase = 'guest' }
      else { portalSession.phase = 'unconfirmed'; portalSession.error = error instanceof FrappeRequestError ? error.message : '暂时无法核对当前登录状态。草稿已保留，请重试核验或退出登录。' }
      throw error
    } finally { if (run === revision && slowTimer) clearTimeout(slowTimer) }
  })()
  flight = pending
  try { return await pending } finally { if (flight === pending) flight = null }
}
function resume(event: Event) {
  observeResume(event.type + ':' + document.visibilityState)
  portalSession.resumeEvents++
  if (document.visibilityState === 'hidden') return
  if (resumeTimer) clearTimeout(resumeTimer)
  resumeTimer = setTimeout(() => { void ensurePortalSession().catch(() => undefined) }, 150)
}
function expired() {
  if (portalSession.phase === 'guest') return
  forgetAttendanceState()
  revision++; flight = null; boundary(); portalSession.phase = 'guest'
  channel?.postMessage('signed_out')
}
export function attachPortalSession() {
  if (++consumers === 1) {
    window.addEventListener('focus', resume); window.addEventListener('pageshow', resume)
    document.addEventListener('visibilitychange', resume); window.addEventListener('hbos:session-expired', expired)
  }
  return () => {
    if (--consumers !== 0) return
    if (resumeTimer) clearTimeout(resumeTimer)
    window.removeEventListener('focus', resume); window.removeEventListener('pageshow', resume)
    document.removeEventListener('visibilitychange', resume); window.removeEventListener('hbos:session-expired', expired)
  }
}
export async function signOutPortalSession() {
  resetPortalSession(false); portalSession.phase = 'logging_out'; channel?.postMessage('suspend')
  const run = revision
  try { await logoutFrappeSession(); if (run !== revision) throw new FrappeRequestError('STALE_RESPONSE', '会话已变化，请核对当前身份。'); portalSession.phase = 'guest'; channel?.postMessage('signed_out') }
  catch (error) { if (run === revision) { portalSession.phase = 'unconfirmed'; portalSession.error = '本机内容已隐藏，服务端退出结果尚未确认。请恢复连接后重试退出。' }; throw error }
}
