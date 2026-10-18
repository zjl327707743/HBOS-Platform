import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { usePortalStore } from '@/stores/portal'
import { FrappeHttpError } from '@/services/frappeClient'

const provider = vi.hoisted(() => ({ getPortalData: vi.fn(), getPortalTasks: vi.fn(), getPortalSummaries: vi.fn() }))
const session = vi.hoisted(() => ({ hasFrappeSession: vi.fn(), clearFrappeCsrfToken: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({ ...provider, portalDataSource: 'frappe' }))
vi.mock('@/services/frappeClient', async original => ({ ...await original<typeof import('@/services/frappeClient')>(), ...session }))
vi.mock('@/services/p1Api', () => ({ getTwinStatus: vi.fn(), getTwinManifest: vi.fn() }))
const data = (id: string) => ({ user: { id }, branding: {}, apps: [], heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] })

beforeEach(() => {
  setActivePinia(createPinia())
  provider.getPortalData.mockReset()
  provider.getPortalTasks.mockReset().mockResolvedValue([])
  provider.getPortalSummaries.mockReset().mockResolvedValue([])
  session.hasFrappeSession.mockReset()
  session.clearFrappeCsrfToken.mockReset()
})

it.each(['logout', 'new_account'])('drops a delayed failure probe after %s changes the session generation', async change => {
  let finish!: (active: boolean) => void
  session.hasFrappeSession.mockReturnValue(new Promise(resolve => { finish = resolve }))
  provider.getPortalData.mockRejectedValueOnce(new FrappeHttpError(403, 'Synthetic forbidden'))
  const portal = usePortalStore()
  const pending = portal.bootstrap()
  await flushPromises()
  expect(session.hasFrappeSession).toHaveBeenCalledTimes(1)
  portal.clearSession()
  if (change === 'new_account') {
    provider.getPortalData.mockResolvedValueOnce(data('new-user'))
    await portal.bootstrap()
  }
  finish(false)
  await expect(pending).resolves.toBeUndefined()
  expect(portal.user?.id ?? null).toBe(change === 'new_account' ? 'new-user' : null)
  expect(portal.bootstrapError).toBeNull()
  expect(portal.bootstrapErrorStatus).toBe(0)
  expect(portal.loading).toBe(false)
})

it.each([true, false])('preserves the current session probe result when active=%s', async active => {
  const error = new FrappeHttpError(403, 'Synthetic forbidden')
  session.hasFrappeSession.mockResolvedValue(active)
  provider.getPortalData.mockRejectedValue(error)
  const portal = usePortalStore()
  await expect(portal.bootstrap()).rejects.toBe(error)
  expect(portal.bootstrapErrorStatus).toBe(active ? 403 : 401)
  expect(portal.bootstrapError).toContain(active ? '没有权限' : '会话已失效')
})

it('invalidates the shared CSRF lifecycle when bootstrap discovers a different account', async () => {
  const portal = usePortalStore()
  provider.getPortalData.mockResolvedValueOnce(data('first-user'))
  await portal.bootstrap()
  expect(session.clearFrappeCsrfToken).not.toHaveBeenCalled()
  provider.getPortalData.mockResolvedValueOnce(data('second-user'))
  await portal.bootstrap()
  expect(session.clearFrappeCsrfToken).toHaveBeenCalledTimes(1)
  expect(portal.user?.id).toBe('second-user')
})
