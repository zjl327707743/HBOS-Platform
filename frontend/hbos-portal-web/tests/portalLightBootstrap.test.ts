import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const provider = vi.hoisted(() => ({ getPortalData: vi.fn(), getPortalSummaries: vi.fn(), getPortalTasks: vi.fn() }))
vi.mock('@/services/portalProvider', () => ({
  ...provider,
  portalDataSource: 'frappe',
}))
vi.mock('@/services/p1Api', () => ({ getTwinStatus: vi.fn(), getTwinManifest: vi.fn() }))

const { usePortalStore } = await import('@/stores/portal')

const payload = (overrides: Record<string, unknown> = {}) => ({
  user: { id: 'synthetic-reader' },
  branding: { productName: 'HBOS' },
  apps: [{ id: 'knowledge' }],
  heroMetrics: [],
  tasks: [],
  businessPulse: [],
  twinStatuses: [],
  limsQueue: [],
  ...overrides,
})

beforeEach(() => { setActivePinia(createPinia()); provider.getPortalData.mockReset() })

describe('light bootstrap never clears the home data it is not fetching', () => {
  it('keeps metrics, tasks, pulse, twin statuses and the LIMS queue across a light resume', async () => {
    const portal = usePortalStore()
    portal.heroMetrics = [{ id: 'h1', label: '已发布资料', value: 918 } as never]
    portal.tasks = [{ id: 't1', status: 'open' } as never]
    portal.businessPulse = [{ id: 'p1', label: '质量', value: '1', trend: '', tone: 'neutral' } as never]
    portal.twinStatuses = [{ id: 'model', label: '私有模型', value: '已配置', tone: 'success', meta: '' } as never]
    portal.limsQueue = [{ id: 'q1' } as never]

    provider.getPortalData.mockResolvedValue(payload())
    await portal.bootstrap({ light: true })

    expect(portal.heroMetrics).toHaveLength(1)
    expect(portal.tasks).toHaveLength(1)
    expect(portal.businessPulse).toHaveLength(1)
    expect(portal.twinStatuses).toHaveLength(1)
    expect(portal.limsQueue).toHaveLength(1)
    expect(portal.user?.id).toBe('synthetic-reader')
  })

  it('clears the previous user home data when the identity changes', async () => {
    const portal = usePortalStore()
    portal.heroMetrics = [{ id: 'h1', label: '上一位用户的指标', value: 1 } as never]
    portal.tasks = [{ id: 't1', status: 'open' } as never]
    portal.user = { id: 'synthetic-previous' } as never

    provider.getPortalData.mockResolvedValue(payload({ user: { id: 'synthetic-successor' } }))
    await portal.bootstrap({ light: true })

    expect(portal.heroMetrics).toEqual([])
    expect(portal.tasks).toEqual([])
    expect(portal.user?.id).toBe('synthetic-successor')
  })

  it('still applies a real payload from a non-light bootstrap', async () => {
    const portal = usePortalStore()
    provider.getPortalData.mockResolvedValue(payload())
    await portal.bootstrap()
    expect(portal.user?.id).toBe('synthetic-reader')
    // The full path also re-reads tasks and summaries for the home feed.
    expect(provider.getPortalTasks).toHaveBeenCalled()
    expect(provider.getPortalSummaries).toHaveBeenCalled()
  })

  it('does not re-read home tasks on a light resume', async () => {
    const portal = usePortalStore()
    provider.getPortalData.mockResolvedValue(payload())
    await portal.bootstrap({ light: true })
    expect(provider.getPortalTasks).not.toHaveBeenCalled()
    expect(provider.getPortalSummaries).not.toHaveBeenCalled()
  })

  it('keeps the current page on a transient failure instead of clearing it', async () => {
    const portal = usePortalStore()
    portal.user = { id: 'synthetic-reader' } as never
    portal.heroMetrics = [{ id: 'h1', label: '保留的指标', value: 1 } as never]
    provider.getPortalData.mockRejectedValue(new Error('network unavailable'))

    await expect(portal.bootstrap({ light: true })).rejects.toThrow('network unavailable')

    expect(portal.heroMetrics).toHaveLength(1)
    expect(portal.user?.id).toBe('synthetic-reader')
  })
})
