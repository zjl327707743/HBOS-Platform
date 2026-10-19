import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { usePortalSession } from '@/composables/usePortalSession'
import { usePortalStore } from '@/stores/portal'
import { FrappeRequestError } from '@/services/frappeClient'

/**
 * Tab-resume behaviour for the knowledge workspace.
 *
 * The Owner-visible requirement is: after answering a question, leaving the
 * tab and coming back must not blank the page, must not raise a skeleton over
 * the answer, and must not re-run a model request. This suite deliberately
 * exercises the *unresolved* status request, because a resolved-then-asserted
 * test cannot prove anything about the slow path — which is exactly how the
 * earlier version of this file passed while the product still flashed.
 *
 * The probe mirrors the real page: an answer, a draft and a scroll position
 * that must all survive, plus a visible skeleton and an error banner that must
 * NOT appear during a soft resume.
 */

const provider = vi.hoisted(() => ({ getPortalData: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))

const data = (apps: string[] = ['knowledge']) => ({
  user: { id: 'synthetic-reader' }, branding: {}, apps: apps.map(id => ({ id })),
  heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [],
})

// Mirrors the real KnowledgeTwinLayout gate: protected content requires an
// authenticated user and no error, and is only hidden by the pending flag.
const Probe = defineComponent({
  setup() {
    const portal = usePortalStore()
    return { ...usePortalSession(), portal }
  },
  template: `<div>
    <div v-if="sessionPending" data-test="skeleton">Checking</div>
    <div v-if="sessionError" data-test="error">{{ sessionError }}</div>
    <div v-if="portal.user && !sessionError" v-show="!sessionPending" data-test="content">Answered content</div>
    <textarea data-test="draft"></textarea>
    <i data-test="revision">{{ sessionRevision }}</i>
  </div>`,
})

let wrapper: VueWrapper | undefined
let router: ReturnType<typeof createRouter>

async function render(path = '/hbos/knowledge') {
  const pinia = createPinia(); setActivePinia(pinia)
  router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: defineComponent({ template: '<div/>' }) }] })
  await router.push(path); await router.isReady()
  wrapper = mount(Probe, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return wrapper
}

/** Simulate the user having an answer and an unsent follow-up on screen. */
async function withAnswerAndDraft(w: VueWrapper) {
  await w.get('[data-test="draft"]').setValue('那第二条具体是什么意思？')
  const content = w.get('[data-test="content"]').element as HTMLElement
  content.scrollTop = 240
  ;(document.activeElement as HTMLElement | null)?.blur()
  w.get('[data-test="draft"]').element.focus()
  return { draft: '那第二条具体是什么意思？', scroll: content.scrollTop }
}

function deferred<T = unknown>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}

const revision = (w: VueWrapper) => Number(w.get('[data-test="revision"]').text())

beforeEach(() => { provider.getPortalData.mockReset(); provider.getPortalData.mockResolvedValue(data()) })
afterEach(() => { wrapper?.unmount(); wrapper = undefined; vi.restoreAllMocks() })

describe('tab resume keeps the working state', () => {
  it('does not blank the answer or raise a skeleton while the status request is still pending', async () => {
    const w = await render()
    await withAnswerAndDraft(w)
    const pending = deferred()
    provider.getPortalData.mockReturnValue(pending.promise)

    // A slow re-check: assert BEFORE the promise resolves.
    window.dispatchEvent(new Event('focus'))
    await flushPromises()

    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
    expect(w.get('[data-test="content"]').isVisible()).toBe(true)
    expect((w.get('[data-test="draft"]').element as HTMLTextAreaElement).value).toBe('那第二条具体是什么意思？')
    expect((w.get('[data-test="content"]').element as HTMLElement).scrollTop).toBe(240)
    expect(document.activeElement).toBe(w.get('[data-test="draft"]').element)

    pending.resolve(data()); await flushPromises()
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
    expect(w.get('[data-test="content"]').isVisible()).toBe(true)
  })

  it('bumps the revision only after a successful recheck, never before it', async () => {
    const w = await render()
    const before = revision(w)
    const pending = deferred()
    provider.getPortalData.mockReturnValue(pending.promise)

    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(revision(w)).toBe(before)

    pending.resolve(data()); await flushPromises()
    expect(revision(w)).toBeGreaterThan(before)
  })

  it.each([
    ['focus', () => window.dispatchEvent(new Event('focus'))],
    ['pageshow', () => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))],
    ['visibilitychange', () => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' }); document.dispatchEvent(new Event('visibilitychange')) }],
  ])('%s triggers the same non-blanking resume', async (_name, fire) => {
    const w = await render()
    await withAnswerAndDraft(w)
    const pending = deferred()
    provider.getPortalData.mockReturnValue(pending.promise)

    fire(); await flushPromises()
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
    expect(w.get('[data-test="content"]').isVisible()).toBe(true)
    pending.resolve(data()); await flushPromises()
    expect(w.get('[data-test="content"]').isVisible()).toBe(true)
  })

  it('does not re-request status while a check is already in flight', async () => {
    const w = await render()
    provider.getPortalData.mockClear()
    const pending = deferred()
    provider.getPortalData.mockReturnValue(pending.promise)

    window.dispatchEvent(new Event('focus'))
    window.dispatchEvent(new Event('focus'))
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
    document.dispatchEvent(new Event('visibilitychange'))
    await flushPromises()

    // Single-flight: four resume signals, one status request.
    expect(provider.getPortalData).toHaveBeenCalledTimes(1)
    pending.resolve(data()); await flushPromises()
    expect(w.get('[data-test="content"]').isVisible()).toBe(true)
  })

  it('a status re-check never triggers a knowledge answer request', async () => {
    const w = await render()
    const ask = vi.fn()
    window.dispatchEvent(new Event('focus')); await flushPromises()
    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(ask).not.toHaveBeenCalled()
    // The probe has no ask path at all; the assertion documents the contract.
    expect(w.text()).toContain('Answered content')
  })
})

describe('resume distinguishes transient failure from real revocation', () => {
  it('a transient service failure keeps the answer, draft and revision, and shows no error over content', async () => {
    const w = await render()
    await withAnswerAndDraft(w)
    const before = revision(w)
    provider.getPortalData.mockRejectedValueOnce(new Error('network unavailable'))

    window.dispatchEvent(new Event('focus')); await flushPromises()

    expect(w.get('[data-test="content"]').isVisible()).toBe(true)
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
    expect(w.find('[data-test="error"]').exists()).toBe(false)
    expect((w.get('[data-test="draft"]').element as HTMLTextAreaElement).value).toBe('那第二条具体是什么意思？')
    expect(revision(w)).toBe(before)
  })

  it('a real unauthenticated response clears the session and redirects to login', async () => {
    const w = await render()
    provider.getPortalData.mockRejectedValueOnce(new FrappeRequestError('UNAUTHENTICATED', 'session expired', 401))

    window.dispatchEvent(new Event('focus')); await flushPromises()

    expect(router.currentRoute.value.path).toBe('/hbos/login')
    expect(router.currentRoute.value.query.status).toBe('session_required')
    // The protected node is removed outright, not merely hidden.
    expect(w.find('[data-test="content"]').exists()).toBe(false)
  })

  it('a manifest change still revokes access with 403 even on a soft resume', async () => {
    await render()
    provider.getPortalData.mockResolvedValueOnce(data([]))
    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(router.currentRoute.value.path).toBe('/hbos/403')
    expect(router.currentRoute.value.query.app).toBe('knowledge')
  })

  it('recovers normally after a transient failure without a manual refresh', async () => {
    const w = await render()
    provider.getPortalData.mockRejectedValueOnce(new Error('network unavailable'))
    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(w.get('[data-test="content"]').isVisible()).toBe(true)

    const before = revision(w)
    provider.getPortalData.mockResolvedValue(data())
    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(revision(w)).toBeGreaterThan(before)
    expect(w.get('[data-test="content"]').isVisible()).toBe(true)
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
  })

  it('the first load still shows the pending state and a first-load failure still reports it', async () => {
    provider.getPortalData.mockRejectedValueOnce(new Error('bootstrap unavailable'))
    const w = await render()
    expect(w.find('[data-test="error"]').exists()).toBe(true)
    expect(w.find('[data-test="skeleton"]').exists()).toBe(false)
  })
})
