import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePortalStore } from '@/stores/portal'
import { accountRedirect } from '@/services/accountNavigation'
const provider = vi.hoisted(() => ({ getPortalData: vi.fn(), getPortalTasks: vi.fn(), getPortalSummaries: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
vi.mock('@/services/p1Api', () => ({ getTwinStatus: vi.fn(), getTwinManifest: vi.fn() }))
const data = (id: string) => ({ user: { id }, branding: {}, apps: [{id:'knowledge'}], heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] })
beforeEach(() => { setActivePinia(createPinia()); provider.getPortalTasks.mockResolvedValue([]); provider.getPortalSummaries.mockResolvedValue([]) })
it('A07: an old bootstrap cannot restore a user after logout', async () => {
  let resolve!: (value: unknown) => void
  provider.getPortalData.mockReturnValue(new Promise(r => { resolve = r }))
  const portal = usePortalStore(), pending = portal.bootstrap()
  portal.clearSession(); resolve(data('old-user')); await pending
  expect(portal.user).toBeNull(); expect(portal.apps).toEqual([])
})
it('A07: previous user task results cannot refill a cleared session', async () => {
  let resolve!: (value: unknown) => void
  provider.getPortalTasks.mockReturnValue(new Promise(r => { resolve = r }))
  const portal = usePortalStore(); portal.apps = [{id:'knowledge'}] as never
  const pending = portal.refreshTasks(); portal.clearSession()
  resolve([{ id:'previous-user-private-task', appId:'knowledge', status:'open' }]); await pending
  expect(portal.tasks).toEqual([])
})
it.each(['https://other.invalid','//other.invalid','/hbos-evil','/hbos/../outside','/hbos/%2e%2e/outside','/hbos\\outside','/hbos/login?redirect_to=/hbos/login'])('A06: unsafe return target %s is rejected', target => {
  expect(accountRedirect(target)).toBe('/hbos')
})
it('A06: a normal protected deep link retains its query', () => { expect(accountRedirect('/hbos/twin?equipment=M607B')).toBe('/hbos/twin?equipment=M607B') })
