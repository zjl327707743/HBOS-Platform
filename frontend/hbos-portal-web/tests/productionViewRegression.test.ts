import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent, nextTick } from 'vue'
import { usePortalStore } from '@/stores/portal'
import ProductionDashboardView from '@/views/ProductionDashboardView.vue'

const api = vi.hoisted(() => ({ fetchProductionBoard: vi.fn(), fetchAiAnalysis: vi.fn() }))
vi.mock('@/services/productionBoard', () => api)

const board = (label = 'SYNTHETIC-ADMIN-DATA') => ({
  month: '2026-10', daysElapsed: 18, updatedAt: '2026-10-18', dataAsOf: '2026-10-18T10:00:00+08:00',
  rows: [{ label, done: 1, target: 10, yieldRate: 0.93, targetYieldRate: 0.9, yesterdayInbound: 37 }],
})
const rejection = (code: string, message: string) => Object.assign(new Error(message), { code })
let wrapper: VueWrapper | undefined

async function render(path = '/hbos/production') {
  const pinia = createPinia(); setActivePinia(pinia)
  const portal = usePortalStore()
  portal.user = { id: 'Administrator' } as never
  portal.apps = [{ id: 'production' }] as never
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) },
  ] })
  await router.push(path); await router.isReady()
  wrapper = mount(ProductionDashboardView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  return { portal, router, wrapper }
}

beforeEach(() => {
  api.fetchProductionBoard.mockReset().mockResolvedValue(board())
  api.fetchAiAnalysis.mockReset().mockResolvedValue([])
})
afterEach(() => { wrapper?.unmount(); wrapper = undefined })

it.each(['FORBIDDEN', 'UNAUTHENTICATED'])('clears old numbers when refresh reports %s', async code => {
  const { wrapper } = await render()
  expect(wrapper.text()).toContain('SYNTHETIC-ADMIN-DATA')
  api.fetchProductionBoard.mockRejectedValue(rejection(code, '权限或会话已失效'))
  await wrapper.get('.pb-refresh').trigger('click'); await flushPromises()
  expect(wrapper.text()).not.toContain('SYNTHETIC-ADMIN-DATA')
  expect(wrapper.text()).toContain('权限或会话已失效')
})

it('keeps the last successful data with an explicit refresh failure', async () => {
  const { wrapper } = await render()
  api.fetchProductionBoard.mockRejectedValue(rejection('PROVIDER_ERROR', '服务暂时不可用'))
  await wrapper.get('.pb-refresh').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('SYNTHETIC-ADMIN-DATA')
  expect(wrapper.get('[role="alert"]').text()).toContain('当前仍显示上次成功读取的数据')
  expect(wrapper.text()).not.toContain('已更新')
})

it('ignores an old in-flight board response after the account changes', async () => {
  let finish!: (value: unknown) => void
  api.fetchProductionBoard.mockReturnValue(new Promise(resolve => { finish = resolve }))
  const { portal, wrapper } = await render()
  portal.user = { id: 'ordinary-employee' } as never
  portal.apps = []
  finish(board('OLD-PRIVATE-RESPONSE')); await flushPromises()
  expect(wrapper.text()).not.toContain('OLD-PRIVATE-RESPONSE')
  expect(wrapper.text()).toContain('会话或生产访问权限已更新')
})

it('keeps displayed evidence during an unchanged authorized bootstrap', async () => {
  const { portal, wrapper } = await render()
  portal.user = { id: 'Administrator' } as never
  portal.apps = [{ id: 'production' }] as never
  await nextTick()
  expect(wrapper.text()).toContain('SYNTHETIC-ADMIN-DATA')
})

it('loads the AI panel when navigating from baseline to center without remounting', async () => {
  const { router, wrapper } = await render()
  expect(api.fetchAiAnalysis).not.toHaveBeenCalled()
  api.fetchAiAnalysis.mockResolvedValue([{ product: 'SYNTHETIC-AI', process: '工序', summary: '合成结果', grade: '数据不足', analyzedAt: null }])
  await router.push('/hbos/production/center'); await flushPromises()
  expect(api.fetchAiAnalysis).toHaveBeenCalledTimes(1)
  expect(wrapper.text()).toContain('SYNTHETIC-AI')
})

it('shows AI service failure separately from a successful empty result', async () => {
  api.fetchAiAnalysis.mockRejectedValue(rejection('PROVIDER_ERROR', '分析结果服务读取失败'))
  const { wrapper } = await render('/hbos/production/center')
  expect(wrapper.text()).toContain('分析结果服务读取失败')
  expect(wrapper.text()).not.toContain('结果表里还没有分析结果')
})

it('drops late AI results after production access disappears', async () => {
  let finish!: (value: unknown) => void
  api.fetchAiAnalysis.mockReturnValue(new Promise(resolve => { finish = resolve }))
  const { portal, wrapper } = await render('/hbos/production/center')
  portal.apps = []
  finish([{ product: 'OLD-PRIVATE-AI', process: '工序', summary: '旧结果', grade: '数据不足', analyzedAt: null }])
  await flushPromises()
  expect(wrapper.text()).not.toContain('OLD-PRIVATE-AI')
  expect(wrapper.text()).not.toContain('SYNTHETIC-ADMIN-DATA')
})
