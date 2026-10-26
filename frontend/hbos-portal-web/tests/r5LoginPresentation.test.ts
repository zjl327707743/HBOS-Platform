import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent } from 'vue'
import Antd from 'ant-design-vue'
import Login from '@/views/FeishuLoginView.vue'
import AccountLayout from '@/components/account/AccountLayout.vue'
import { FrappeRequestError } from '@/services/frappeClient'
const mocks = vi.hoisted(() => ({ status: vi.fn(), login: vi.fn(), ensure: vi.fn(), reset: vi.fn(), logout: vi.fn(), clear: vi.fn() }))
vi.mock('@/services/p1Api', () => ({ getFeishuLoginStatus: mocks.status }))
vi.mock('@/services/frappeClient', async original => ({ ...await original<typeof import('@/services/frappeClient')>(), loginWithPassword: mocks.login }))
vi.mock('@/services/portalSessionCoordinator', () => ({ ensurePortalSession: mocks.ensure, resetPortalSession: mocks.reset, signOutPortalSession: mocks.logout }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => ({ clearSession: mocks.clear }) }))
let wrappers: VueWrapper[] = []
async function render(component: object = Login) {
 const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
 await router.push('/hbos/login'); await router.isReady()
 const wrapper = mount(component, { attachTo: document.body, props: component === AccountLayout ? { title: '账号恢复' } : {}, global: { plugins: [Antd, router] } })
 wrappers.push(wrapper); await flushPromises(); return { wrapper, router }
}
async function click(w: VueWrapper, text: string) { await w.findAll('button').find(b => b.text().includes(text))!.trigger('click'); await flushPromises() }
async function submit(w: VueWrapper) { await w.find('#hbos-username').setValue('synthetic'); await w.find('#hbos-password').setValue('synthetic-password'); await w.find('form').trigger('submit'); await flushPromises() }
beforeEach(() => { vi.resetAllMocks(); mocks.status.mockResolvedValue({ configured: false }); mocks.login.mockResolvedValue({ message: 'Logged In' }); mocks.ensure.mockResolvedValue({}); mocks.logout.mockResolvedValue(undefined) })
afterEach(() => { wrappers.forEach(w => w.unmount()); wrappers = []; document.body.innerHTML = '' })
it('configured login has one primary method group; fallback opens and focuses the real form', async () => {
 mocks.status.mockResolvedValue({ configured: true }); const { wrapper } = await render()
 expect(wrapper.find('form').exists()).toBe(false)
 expect(wrapper.findAll('.ant-btn-primary')).toHaveLength(1)
 await click(wrapper, '使用账号密码登录')
 expect(document.activeElement?.id).toBe('hbos-username')
 expect(wrapper.find('form').exists()).toBe(true)
 expect(mocks.login).not.toHaveBeenCalled(); expect(mocks.status).toHaveBeenCalledTimes(1)
})
it('unconfigured Feishu directly exposes password login without a simulated OAuth action', async () => {
 const { wrapper } = await render(); expect(wrapper.text()).toContain('飞书登录暂时不可用')
 expect(wrapper.find('#hbos-password').exists()).toBe(true)
 expect(wrapper.findAll('button').some(b => b.text().includes('使用飞书登录'))).toBe(false)
})
it('failed status read remains explicit, allows password and retries the existing status API', async () => {
 mocks.status.mockRejectedValueOnce(new Error('network')); const { wrapper } = await render()
 expect(wrapper.find('[role="alert"]').text()).toContain('无法读取飞书登录状态')
 expect(wrapper.find('form').exists()).toBe(true); await click(wrapper, '重试读取登录方式')
 expect(mocks.status).toHaveBeenCalledTimes(2); expect(wrapper.text()).toContain('飞书登录暂时不可用')
})
it.each([['UNAUTHENTICATED', '账号或密码不正确。'], ['RATE_LIMITED', '验证尝试较多，当前暂不可用。请稍后重试。']])('existing %s rejection stays visible and clears secrets', async (code, message) => {
 mocks.login.mockRejectedValue(new FrappeRequestError(code, message)); const { wrapper } = await render(); await submit(wrapper)
 expect(wrapper.find('[role="alert"]').text()).toContain(message)
 expect((wrapper.find('#hbos-password').element as HTMLInputElement).value).toBe('')
 expect(mocks.ensure).not.toHaveBeenCalled()
})
it('MFA uses the backend challenge and cancelling clears its password and code', async () => {
 mocks.login.mockResolvedValue({ tmp_id: 'synthetic-challenge', verification: {} }); const { wrapper } = await render(); await submit(wrapper)
 expect(wrapper.find('#login-otp').exists()).toBe(true); await click(wrapper, '取消二次认证')
 expect(wrapper.find('#login-otp').exists()).toBe(false); expect(mocks.ensure).not.toHaveBeenCalled()
})
it('workspace retry after authentication never resubmits credentials', async () => {
 mocks.ensure.mockRejectedValueOnce(new Error('read failed')); const { wrapper } = await render(); await submit(wrapper)
 expect(wrapper.text()).toContain('登录已完成'); expect(wrapper.find('form').exists()).toBe(false)
 await click(wrapper, '重试加载工作台'); expect(mocks.login).toHaveBeenCalledTimes(1); expect(mocks.ensure).toHaveBeenCalledTimes(2)
})
it('switching account waits for confirmed logout and preserves retry on rejection', async () => {
 mocks.ensure.mockRejectedValue(new Error('read failed')); mocks.logout.mockRejectedValueOnce(new Error('退出尚未确认'))
 const { wrapper, router } = await render(); await submit(wrapper); await click(wrapper, '退出并换一个账号')
 expect(wrapper.text()).toContain('退出尚未确认'); expect(wrapper.text()).toContain('登录已完成'); expect(router.currentRoute.value.query.status).toBeUndefined()
 await click(wrapper, '退出并换一个账号'); expect(mocks.logout).toHaveBeenCalledTimes(2)
 expect(router.currentRoute.value.query.status).toBe('signed_out'); expect(wrapper.find('#hbos-username').exists()).toBe(true)
 expect((wrapper.find('#hbos-username').element as HTMLInputElement).value).toBe('')
})
it('the default shared account layout keeps its single-card structure', async () => {
 const { wrapper } = await render(AccountLayout); expect(wrapper.find('.account-login-main').exists()).toBe(false)
 expect(wrapper.find('.account-r5').exists()).toBe(false); expect(wrapper.findAll('h1')).toHaveLength(1)
})
it('retrying status preserves the visible password draft even when Feishu becomes configured', async () => {
 mocks.status.mockRejectedValueOnce(new Error('network'))
 const { wrapper } = await render(); await wrapper.find('#hbos-username').setValue('synthetic-draft')
 let resolve!: (value: unknown) => void; mocks.status.mockImplementationOnce(() => new Promise(r => { resolve = r }))
 await click(wrapper, '重试读取登录方式'); expect(wrapper.find('form').exists()).toBe(true)
 expect((wrapper.find('#hbos-username').element as HTMLInputElement).value).toBe('synthetic-draft')
 resolve({ configured: true }); await flushPromises()
 expect(wrapper.find('form').exists()).toBe(true); expect(mocks.status).toHaveBeenCalledTimes(2)
})
it('logout progress describes logout and keeps only a sanitized return target after confirmation', async () => {
 mocks.ensure.mockRejectedValue(new Error('read failed')); const { wrapper, router } = await render()
 await router.push('/hbos/login?redirect_to=%2Fhbos%2Fwork'); await submit(wrapper)
 let finish!: () => void; mocks.logout.mockImplementationOnce(() => new Promise<void>(r => { finish = r }))
 await click(wrapper, '退出并换一个账号')
 expect(wrapper.text()).toContain('正在退出当前账号'); expect(wrapper.text()).not.toContain('正在加载工作台')
 finish(); await flushPromises(); expect(router.currentRoute.value.query.redirect_to).toBe('/hbos/work')
})
