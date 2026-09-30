import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import AccountSecurity from '@/components/account/AccountSecurity.vue'
import AccountChangeActions from '@/components/account/AccountChangeActions.vue'
import AccountChangeView from '@/views/AccountChangeView.vue'
import LoginView from '@/views/FeishuLoginView.vue'

const api = vi.hoisted(() => ({ getSecurity: vi.fn(), reauthenticate: vi.fn(), requestFeishuCode: vi.fn(), verifyFeishuCode: vi.fn(), setPassword: vi.fn(), unlinkFeishu: vi.fn(), startLink: vi.fn(), adminIssueRecovery: vi.fn() }))
const changes = vi.hoisted(() => ({ changeActions: vi.fn(), recentChanges: vi.fn(), getChange: vi.fn(), getParticipant: vi.fn(), changePost: vi.fn() }))
const session = vi.hoisted(() => ({ bootstrap: vi.fn(), clearSession: vi.fn() }))
const login = vi.hoisted(() => vi.fn())
vi.mock('@/services/accountApi', () => api)
vi.mock('@/services/accountChanges', () => ({ ...changes, kindLabel: (kind: string) => kind, stateLabel: (state: string) => state }))
vi.mock('@/services/p1Api', () => ({ getFeishuLoginStatus: vi.fn(async () => ({ configured: true })) }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => session }))
vi.mock('@/services/frappeClient', async (original) => ({ ...await original<typeof import('@/services/frappeClient')>(), loginWithPassword: login, clearFrappeCsrfToken: vi.fn() }))

const security = { user: 'synthetic@example.test', login_name: 'synthetic', has_password: true, feishu_bound: true, feishu_configured: true, feishu_stepup_available: true, administrator: false, can_admin_recover: false, proof: { valid: false, expires_in: 0, method: null } }
const permitted = { migrated: true, rebind: true, roles: true, role_choices: ['System Manager'], custody: false, identity_restore: false }
let wrappers: VueWrapper[] = []
async function render(component: object, path = '/hbos/profile') {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) },
  ] })
  await router.push(path); await router.isReady()
  const wrapper = mount(component, { attachTo: document.body, global: { plugins: [Antd, router] } })
  wrappers.push(wrapper); await flushPromises()
  return { wrapper, router }
}
async function clickText(wrapper: VueWrapper, text: string) {
  const button = wrapper.findAll('button').find(b => b.text().includes(text))
  expect(button, `visible action: ${text}`).toBeTruthy()
  await button!.trigger('click'); await flushPromises()
}
beforeEach(() => {
  api.getSecurity.mockResolvedValue(structuredClone(security)); api.reauthenticate.mockResolvedValue({ verified: true, expires_in: 1 })
  changes.changeActions.mockResolvedValue(permitted); changes.recentChanges.mockResolvedValue({ changes: [] })
  changes.getChange.mockImplementation(async (operation: string) => ({ operation, kind: 'rebind', expires_in: 600, state: 'Pending' }))
  session.bootstrap.mockResolvedValue(undefined); login.mockResolvedValue({ message: 'Logged In' })
})
afterEach(() => { wrappers.forEach(w => w.unmount()); wrappers = []; document.body.innerHTML = ''; vi.useRealTimers() })

describe('confirmed account UI regressions', () => {
  it('A02: the password form preserves spaces and special characters', async () => {
    const {wrapper} = await render(LoginView,'/hbos/login')
    await wrapper.find('input[autocomplete="username"]').setValue('synthetic')
    await wrapper.find('input[autocomplete="current-password"]').setValue('  合法 password $ & <>  ')
    await wrapper.find('form').trigger('submit'); await flushPromises()
    expect(login).toHaveBeenCalledWith('synthetic','  合法 password $ & <>  ','','')
  })
  it('FLOW-02: a lost begin response offers a usable query action before an operation is known', async () => {
    changes.changePost.mockRejectedValue(new Error('response lost'))
    const {wrapper} = await render(AccountChangeView, '/hbos/account-change?kind=rebind')
    await wrapper.find('textarea').setValue('已明确核验本人账号归属及本次变更的影响')
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic password')
    await clickText(wrapper,'验证本人身份')
    await wrapper.find('form').trigger('submit'); await flushPromises()
    await clickText(wrapper,'查询上次提交结果')
    expect(changes.getChange).toHaveBeenCalledWith('',expect.stringMatching(/^[0-9a-f-]{36}$/))
    expect(changes.changePost).toHaveBeenCalledTimes(1)
  })
  it('D02/A03: Enter verifies only this step, and IME confirmation does not submit', async () => {
    const outer = vi.fn()
    const Parent = defineComponent({ components: { OwnAccountVerification }, setup: () => ({outer}), template: '<form @submit.prevent="outer"><OwnAccountVerification /></form>' })
    const { wrapper } = await render(Parent)
    const input = wrapper.find('input[autocomplete="current-password"]')
    await input.setValue('synthetic password')
    await input.trigger('keydown', {key:'Enter', isComposing:true})
    expect(api.reauthenticate).not.toHaveBeenCalled()
    await input.trigger('keydown', {key:'Enter'})
    await flushPromises()
    expect(api.reauthenticate).toHaveBeenCalledTimes(1); expect(outer).not.toHaveBeenCalled()
  })
  it('C01: focus rechecks a proof consumed in another window', async () => {
    api.reauthenticate.mockResolvedValue({verified:true, expires_in:300})
    const { wrapper } = await render(OwnAccountVerification)
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic password')
    await clickText(wrapper,'验证本人身份')
    // A user may start re-verifying while the existing proof is still valid.
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic password being re-entered')
    api.getSecurity.mockResolvedValue(structuredClone(security))
    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(wrapper.text()).toMatch(/已过期、已使用或会话已变化/)
    expect(wrapper.find('input[autocomplete="current-password"]').element).toHaveProperty('value', '')
  })
  it('FLOW-01: an earlier operation response cannot replace a new target', async () => {
    let resolve!: (value: unknown) => void
    changes.getChange.mockImplementationOnce(() => new Promise(r => { resolve = r }))
    const {wrapper,router} = await render(AccountChangeView, '/hbos/account-change?operation=old-target')
    await router.push('/hbos/account-change?operation=new-target'); await flushPromises()
    resolve({operation:'old-target',kind:'custody',state:'Invited',expires_in:600}); await flushPromises()
    expect(wrapper.text()).not.toContain('custody'); expect(wrapper.text()).not.toContain('old-target')
  })
  it('C01/A08: proof invalidation clears password drafts in the containing security form', async () => {
    api.reauthenticate.mockResolvedValue({verified:true, expires_in:300})
    const { wrapper } = await render(AccountSecurity)
    await clickText(wrapper,'修改密码')
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic current password')
    await clickText(wrapper,'验证本人身份')
    for (const field of wrapper.findAll('input[autocomplete="new-password"]')) {
      await field.setValue('synthetic unsubmitted password draft')
    }
    api.getSecurity.mockResolvedValue(structuredClone(security))
    window.dispatchEvent(new Event('focus')); await flushPromises()
    expect(wrapper.findAll('input[type="password"]').every(field => (field.element as HTMLInputElement).value === '')).toBe(true)
    expect(api.setPassword).not.toHaveBeenCalled()
  })
  it('C10: an uncertain write prevents duplicates and can query its receipt', async () => {
    api.setPassword.mockRejectedValue(new Error('response lost'))
    const { wrapper } = await render(AccountSecurity)
    await clickText(wrapper,'修改密码')
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic password')
    await clickText(wrapper,'验证本人身份')
    const fields = wrapper.findAll('input[autocomplete="new-password"]')
    await fields[0]!.setValue('synthetic replacement password'); await fields[1]!.setValue('synthetic replacement password')
    const form = wrapper.find('form')
    await form.trigger('submit'); await form.trigger('submit'); await flushPromises()
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toMatch(/查询上次提交结果/)
    api.getSecurity.mockResolvedValue({...security,write_result:{completed:true,action:'password'}})
    await clickText(wrapper,'查询上次提交结果')
    expect(wrapper.text()).toMatch(/服务器已确认上次提交/)
    expect(api.getSecurity).toHaveBeenLastCalledWith(expect.stringMatching(/^[0-9a-f-]{36}$/))
  })
  it('FORM-01: verification has its own submit boundary without nesting forms', async () => {
    const Parent = defineComponent({ components: { OwnAccountVerification }, template: '<form @submit.prevent><OwnAccountVerification /></form>' })
    const { wrapper } = await render(Parent)
    expect(wrapper.find('form form').exists()).toBe(false)
  })
  it('ERROR-01: a failed security read ends its skeleton and offers retry', async () => {
    api.getSecurity.mockRejectedValue(new Error('network unavailable'))
    const { wrapper } = await render(AccountSecurity)
    expect(wrapper.find('.ant-skeleton').exists()).toBe(false)
    expect(wrapper.text()).toMatch(/重试/)
  })
  it('ERROR-02: actions read failure stays visible instead of disappearing', async () => {
    changes.changeActions.mockRejectedValue(new Error('network unavailable'))
    const { wrapper } = await render(AccountChangeActions)
    expect(wrapper.text()).toMatch(/无法|失败/)
    expect(wrapper.text()).toMatch(/重试/)
  })
  it('STATE-01: proof expires and enables reauthentication', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    const { wrapper } = await render(OwnAccountVerification)
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic current password')
    const submit = wrapper.findAll('button').find(b => b.text().includes('验证本人身份'))!
    await submit.trigger('click'); await flushPromises()
    if (wrapper.find('form').exists()) { await wrapper.find('form').trigger('submit'); await flushPromises() }
    expect(wrapper.text()).toMatch(/已验证|验证完成/)
    await vi.advanceTimersByTimeAsync(1500); await flushPromises()
    expect(wrapper.text()).toMatch(/过期|失效|重新验证/)
    expect(wrapper.emitted('invalidated')).toBeTruthy()
  })
  it('FLOW-01: query change reloads the operation and clears the previous target', async () => {
    const { wrapper, router } = await render(AccountChangeView, '/hbos/account-change?operation=operation-first')
    await router.push('/hbos/account-change?operation=operation-second'); await flushPromises()
    expect(changes.getChange).toHaveBeenLastCalledWith('operation-second')
    expect(wrapper.text()).not.toContain('operation-first')
  })
  it('FLOW-02: successful password write survives a failed status refresh', async () => {
    api.setPassword.mockResolvedValue({ changed: true, login_name: 'synthetic' })
    const { wrapper } = await render(AccountSecurity)
    const open = wrapper.findAll('button').find(b => /修改密码|设置密码/.test(b.text()))
    if (open) { await open.trigger('click'); await flushPromises() }
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic current password')
    await clickText(wrapper, '验证本人身份')
    expect(api.reauthenticate).toHaveBeenCalledTimes(1)
    await wrapper.find('input[autocomplete="new-password"]').setValue('synthetic replacement password')
    await wrapper.findAll('input[autocomplete="new-password"]')[1]!.setValue('synthetic replacement password')
    api.getSecurity.mockRejectedValue(new Error('refresh failed'))
    const form = wrapper.findAll('form').find(f => f.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit'); await flushPromises()
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toMatch(/密码已保存/)
    expect(wrapper.text()).not.toContain('本人已验证 ·')
    expect(wrapper.text()).not.toContain('操作未完成：')
  })
  it('A04: changing the login user clears the old MFA challenge', async () => {
    login.mockResolvedValue({ tmp_id: 'synthetic-mfa-challenge', verification: {} })
    const { wrapper } = await render(LoginView, '/hbos/login')
    await wrapper.find('input[autocomplete="username"]').setValue('first-synthetic')
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic password')
    await wrapper.find('form').trigger('submit'); await flushPromises()
    expect(wrapper.find('input[autocomplete="one-time-code"]').exists()).toBe(true)
    await wrapper.find('input[autocomplete="username"]').setValue('second-synthetic'); await flushPromises()
    expect(wrapper.find('input[autocomplete="one-time-code"]').exists()).toBe(false)
  })
  it('A05: bootstrap failure after login can retry without resubmitting credentials', async () => {
    session.bootstrap.mockRejectedValueOnce(new Error('bootstrap read failed'))
    const { wrapper } = await render(LoginView, '/hbos/login')
    await wrapper.find('input[autocomplete="username"]').setValue('synthetic')
    await wrapper.find('input[autocomplete="current-password"]').setValue('synthetic password')
    await wrapper.find('form').trigger('submit'); await flushPromises()
    expect(wrapper.text()).toMatch(/已登录|登录已完成/)
    expect(wrapper.text()).toMatch(/重试/)
    expect(login).toHaveBeenCalledTimes(1)
  })
})
