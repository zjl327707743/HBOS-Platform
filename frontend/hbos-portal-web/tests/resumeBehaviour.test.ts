import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { resetPortalSession, ensurePortalSession, portalSession } from '@/services/portalSessionCoordinator'
import { usePortalSession } from '@/composables/usePortalSession'
import { usePortalStore } from '@/stores/portal'
import { FrappeRequestError } from '@/services/frappeClient'

/**
 * Tab-resume behaviour of the knowledge workspace.
 *
 * Two requirements meet here and neither may be dropped:
 *
 *  - Platform session policy: while the account is being re-checked, protected
 *    content shown before the check must not stay readable, and a confirmed
 *    authentication failure clears the page.
 *  - Knowledge: a resume is not a page reload. The answer, draft, filters and
 *    scroll position are kept — masked, not destroyed — no skeleton is raised
 *    over established content, and views are not told to re-read when the
 *    identity and the authorized app set are unchanged.
 *
 * The suite leaves the re-check unresolved where that matters, because a
 * resolved-then-asserted test cannot prove anything about the slow path.
 */

vi.mock('@/services/iamAccount', () => ({ getIamSecurity: vi.fn(async () => ({ user: 'synthetic-reader', session_context: 'a'.repeat(64), first_password_required: false, proof: {} })) }))
vi.mock('@/services/iamAccess', () => ({ iamSession: { revision: 'r1', appRevisions: {} }, fetchIamAccess: vi.fn(async () => ({ subject_user: 'synthetic-reader', session_context: 'a'.repeat(64), policy_revision: 'r1', capabilities: [] })), applyIamAccess: vi.fn(), clearIamAccess: vi.fn() }))

const provider = vi.hoisted(() => ({ getPortalData: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))

const data = (apps: string[] = ['knowledge'], user = 'synthetic-reader') => ({
  user: { id: user }, branding: {}, apps: apps.map(id => ({ id })),
  heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [],
})

// Mirrors KnowledgeTwinLayout: a skeleton only for the first load, the content
// node masked while the account is re-checked and never removed for that
// reason, and the shell's alert for a confirmed error.
const Probe = defineComponent({
  setup() {
    const portal = usePortalStore()
    return { ...usePortalSession(), portal }
  },
  template: `<div>
    <div v-if="sessionPending" data-test="skeleton">Checking</div>
    <div v-if="sessionError" data-test="error">{{ sessionError }}</div>
    <div
      v-if="portal.user && !sessionError"
      v-show="!sessionPending"
      :class="{ 'kb-session-masked': sessionBlocked }"
      :inert="sessionBlocked || undefined"
      data-test="content"
    >Answered content</div>
    <textarea data-test="draft"></textarea>
    <i data-test="revision">{{ sessionRevision }}</i>
  </div>`,
})

let wrapper: VueWrapper | undefined
let router: ReturnType<typeof createRouter>

async function render(path = '/hbos/knowledge') {
  const pinia = createPinia(); setActivePinia(pinia); resetPortalSession(false)
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: defineComponent({ template: '<div/>' }) }] })
  await router.push(path); await router.isReady()
  wrapper = mount(Probe, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await ensurePortalSession().catch(() => undefined); await flushPromises()
  return wrapper
}

/** Simulate the user having an answer and an unsent follow-up on screen. */
async function withAnswerAndDraft(w: VueWrapper) {
  await w.get('[data-test="draft"]').setValue('那第二条具体是什么意思？')
  const content = w.get('[data-test="content"]').element as HTMLElement
  content.scrollTop = 240
  ;(document.activeElement as HTMLElement | null)?.blur()
  w.get('[data-test="draft"]').element.focus()
}

/**
 * A resume: the coordinator debounces 150 ms, and it re-verifies a session it
 * already confirmed only once its 5 s freshness window has passed (a revoked
 * account cannot hide behind a local timer, but a burst of focus events must
 * not multiply status reads). Both waits are part of the platform behaviour.
 */
async function resume({ fresh = true } = {}) {
  if (fresh) await vi.advanceTimersByTimeAsync(5100)
  window.dispatchEvent(new Event('focus'))
  await vi.advanceTimersByTimeAsync(151)
  await flushPromises()
}

function deferred<T = unknown>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

const revision = (w: VueWrapper) => Number(w.get('[data-test="revision"]').text())
const masked = (w: VueWrapper) => w.get('[data-test="content"]').classes().includes('kb-session-masked')

beforeEach(() => {
  vi.useFakeTimers()
  window.sessionStorage.clear()
  provider.getPortalData.mockReset()
  provider.getPortalData.mockResolvedValue(data())
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.useRealTimers() })

describe('a resume keeps the working state and hides it only while it is re-checked', () => {
  it('masks the answer instead of blanking it, and never raises a skeleton over it', async () => {
    const w = await render()
    await withAnswerAndDraft(w)
    const pending = deferred()
    provider.getPortalData.mockReturnValue(pending.promise)

    await vi.advanceTimersByTimeAsync(5100)
    window.dispatchEvent(new Event('focus'))
    await vi.advanceTimersByTimeAsync(151)
    await flushPromises()

    // Platform policy: not readable while the account is being re-checked.
    expect(masked(w)).toBe(true)
    expect(w.get('[data-test="content"]').attributes('inert')).toBeDefined()
    // Knowledge requirement: the node is still there, with its state.
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
    expect((w.get('[data-test="draft"]').element as HTMLTextAreaElement).value).toBe('那第二条具体是什么意思？')
    expect((w.get('[data-test="content"]').element as HTMLElement).scrollTop).toBe(240)
    expect(document.activeElement).toBe(w.get('[data-test="draft"]').element)

    pending.resolve(data()); await flushPromises()
    expect(masked(w)).toBe(false)
    expect(w.get('[data-test="content"]').text()).toContain('Answered content')
    expect((w.get('[data-test="draft"]').element as HTMLTextAreaElement).value).toBe('那第二条具体是什么意思？')
    expect((w.get('[data-test="content"]').element as HTMLElement).scrollTop).toBe(240)
  })

  it('does not advance the revision when the identity and app set are unchanged', async () => {
    const w = await render()
    const before = revision(w)
    await resume()
    await resume()
    expect(revision(w)).toBe(before)
    expect(masked(w)).toBe(false)
  })

  it('advances the revision when the signed-in identity changes', async () => {
    const w = await render()
    const before = revision(w)
    provider.getPortalData.mockResolvedValue(data(['knowledge'], 'synthetic-successor'))
    await resume()
    expect(revision(w)).toBeGreaterThan(before)
  })

  it('advances the revision when the authorized app set changes', async () => {
    const w = await render()
    const before = revision(w)
    provider.getPortalData.mockResolvedValue(data(['knowledge', 'lims']))
    await resume()
    expect(revision(w)).toBeGreaterThan(before)
  })

  it('does not advance the revision on the first successful load, so the view is not re-read twice', async () => {
    const w = await render()
    expect(revision(w)).toBe(0)
  })

  it('re-verifies on every resume instead of skipping inside a freshness window', async () => {
    const w = await render()
    provider.getPortalData.mockClear()
    await resume()
    provider.getPortalData.mockClear()
    await resume()
    // Two resumes seconds apart must each reach the server: a revoked account
    // cannot be hidden behind a local timer.
    expect(provider.getPortalData).toHaveBeenCalled()
    expect(masked(w)).toBe(false)
  })

  it('a resume never triggers a knowledge answer request', async () => {
    const w = await render()
    const ask = vi.fn()
    await resume()
    await resume()
    expect(ask).not.toHaveBeenCalled()
    expect(w.text()).toContain('Answered content')
  })
})

describe('a re-check distinguishes transient failure from real revocation', () => {
  it('a transient service failure keeps the answer, draft and revision, and does not redirect to login', async () => {
    const w = await render()
    await withAnswerAndDraft(w)
    const before = revision(w)
    provider.getPortalData.mockRejectedValueOnce(new Error('network unavailable'))

    await resume()

    expect(router.currentRoute.value.path).toBe('/hbos/knowledge')
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
    expect((w.get('[data-test="draft"]').element as HTMLTextAreaElement).value).toBe('那第二条具体是什么意思？')
    expect(revision(w)).toBe(before)
  })

  it('a real unauthenticated response ends the session instead of keeping old content', async () => {
    const w = await render()
    const iam = await import('@/services/iamAccount')
    vi.mocked(iam.getIamSecurity).mockRejectedValueOnce(new FrappeRequestError('UNAUTHENTICATED', 'session expired', 401))

    await resume()

    // The coordinator confirms 'guest' and clears the store; the protected node
    // is removed outright, not merely hidden. The shell's redirect to the login
    // page for this phase is asserted at the layout level.
    expect(portalSession.phase).toBe('guest')
    expect(usePortalStore().user).toBeNull()
    expect(w.find('[data-test="content"]').exists()).toBe(false)
  })

  it('a manifest change still revokes access with 403 even on a soft resume', async () => {
    await render()
    provider.getPortalData.mockResolvedValueOnce(data([]))
    await resume()
    expect(router.currentRoute.value.path).toBe('/hbos/403')
    expect(router.currentRoute.value.query.app).toBe('knowledge')
  })

  it('recovers normally after a transient failure without a manual refresh', async () => {
    const w = await render()
    provider.getPortalData.mockRejectedValueOnce(new Error('network unavailable'))
    await resume()

    const before = revision(w)
    provider.getPortalData.mockResolvedValue(data())
    await resume()
    expect(revision(w)).toBe(before)
    expect(w.get('[data-test="content"]').text()).toContain('Answered content')
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
  })
})
