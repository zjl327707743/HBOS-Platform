import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'
import AccountSecurity from '@/components/account/AccountSecurity.vue'
import Profile from '@/views/ProfileSettingsView.vue'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { readPendingAccountWrite, rememberPendingAccountWrite } from '@/services/accountWriteRecovery'
import { clearFrappeCsrfToken, FrappeRequestError } from '@/services/frappeClient'

const api = vi.hoisted(() => ({
  getSecurity: vi.fn(), reauthenticate: vi.fn(), requestFeishuCode: vi.fn(), verifyFeishuCode: vi.fn(),
  setPassword: vi.fn(), unlinkFeishu: vi.fn(), startLink: vi.fn(), adminIssueRecovery: vi.fn(),
}))
const changes = vi.hoisted(() => ({ changeActions: vi.fn(), recentChanges: vi.fn() }))
const employees = vi.hoisted(() => ({ getMyEmployeeStatus: vi.fn() }))
const actor = vi.hoisted(() => ({ user: { id: 'synthetic@example.test', displayName: '合成员工', avatarText: '合', avatarUrl: null as string | null, roleLabel: '员工账号', department: '合成部门' }, apps: [] }))

vi.mock('@/services/accountApi', () => api)
vi.mock('@/services/accountChanges', () => ({
  ...changes,
  kindLabel: (kind: string) => kind,
  stateLabel: (state: string) => state,
}))
vi.mock('@/services/iamAccount', () => employees)
vi.mock('@/services/iamAccess', () => ({
  iamMessage: (error: Error) => error.message,
  hasManagementAccess: () => false,
}))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => actor }))
vi.mock('@/services/frappeClient', async (original) => ({
  ...await original<typeof import('@/services/frappeClient')>(),
  clearFrappeCsrfToken: vi.fn(),
}))

function security(overrides: Record<string, unknown> = {}) {
  return {
    user: actor.user.id,
    login_name: 'synthetic',
    has_password: true,
    password_login_available: true,
    feishu_bound: false,
    feishu_configured: true,
    feishu_stepup_available: false,
    desk_access: false,
    administrator: false,
    administrator_link_enabled: false,
    mail_recovery_available: false,
    can_admin_recover: false,
    proof: { valid: false, expires_in: 0, method: null },
    ...overrides,
  }
}

let wrappers: VueWrapper[] = []
async function render(component: object, path = '/hbos/profile', props: Record<string, unknown> = {}): Promise<{ wrapper: VueWrapper; router: Router }> {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(component, { attachTo: document.body, props, global: { plugins: [Antd, router] } })
  wrappers.push(wrapper)
  await flushPromises()
  return { wrapper, router }
}
function modal(wrapper: VueWrapper) {
  return wrapper.findComponent({ name: 'AModal' })
}
function button(wrapper: VueWrapper, text: string) {
  const normalized = text.replace(/\s+/g, '')
  const found = wrapper.findAll('button').find(item => item.text().replace(/\s+/g, '').includes(normalized))
  expect(found, `visible action: ${text}`).toBeTruthy()
  return found!
}
async function click(wrapper: VueWrapper, text: string) {
  await button(wrapper, text).trigger('click')
  await flushPromises()
}
function proofInput(wrapper: VueWrapper) {
  return wrapper.find('input[autocomplete="current-password"]')
}
function newPasswordFields(wrapper: VueWrapper) {
  return wrapper.findAll('input[autocomplete="new-password"]')
}
async function verifyPassword(wrapper: VueWrapper) {
  await proofInput(wrapper).setValue('synthetic current password')
  await click(wrapper, '验证本人身份')
}
async function advanceToPasswordForm(wrapper: VueWrapper) {
  await click(wrapper, '修改密码')
  await verifyPassword(wrapper)
  expect(newPasswordFields(wrapper)).toHaveLength(2)
}
async function fillNewPassword(wrapper: VueWrapper, value = 'synthetic replacement password') {
  await newPasswordFields(wrapper)[0]!.setValue(value)
  await newPasswordFields(wrapper)[1]!.setValue(value)
}
async function submitPasswordForm(wrapper: VueWrapper) {
  const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
  await form.trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  actor.user.id = 'synthetic@example.test'
  actor.user.displayName = '合成员工'
  actor.user.avatarUrl = null
  api.getSecurity.mockImplementation(async () => security())
  api.reauthenticate.mockResolvedValue({ verified: true, expires_in: 120 })
  api.setPassword.mockResolvedValue({ changed: true, login_name: 'synthetic' })
  api.unlinkFeishu.mockResolvedValue({ unlinked: true })
  api.startLink.mockResolvedValue({ authorize_url: 'https://owned.example.test/authorize' })
  api.adminIssueRecovery.mockResolvedValue({ recovery_url: 'https://owned.example.test/reset', target: { display_name: '合成员工', login_name: 'synthetic' }, expires_in: 600 })
  changes.changeActions.mockResolvedValue({ migrated: false })
  changes.recentChanges.mockResolvedValue({ changes: [] })
  employees.getMyEmployeeStatus.mockResolvedValue({ status: 'linked', employee_id: 'EMP-1', employee_number: 'T001', department: '合成部门', position: '合成岗位' })
})
afterEach(() => {
  wrappers.forEach(wrapper => wrapper.unmount())
  wrappers = []
  document.body.innerHTML = ''
  sessionStorage.clear()
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('R6-A2.2 个人中心完整弹窗', () => {
  it('账号安全标题保留原型的保护说明和分隔层级', async () => {
    const { wrapper } = await render(AccountSecurity)
    const heading = wrapper.find('.account-security-heading')
    expect(heading.find('h3').text()).toBe('登录与安全')
    expect(heading.find('span').text()).toBe('账号保护')
    expect(heading.find('p').text()).toContain('选择适合你的登录方式')
  })

  it('三行安全操作都在 600px 模态中打开，不直接跳转', async () => {
    const { wrapper, router } = await render(AccountSecurity)
    const dialog = modal(wrapper)
    expect(dialog.props('open')).toBe(false)

    await click(wrapper, '修改密码')
    expect(dialog.props('open')).toBe(true)
    expect(dialog.props('width')).toBe(600)
    expect(dialog.props('title')).toBe('修改登录密码')
    expect(router.currentRoute.value.path).toBe('/hbos/profile')
    await click(wrapper, '取消')
    expect(document.activeElement).toBe(button(wrapper, '修改密码').element)

    await click(wrapper, '查看登录方式')
    expect(dialog.props('title')).toBe('飞书登录')
    expect(router.currentRoute.value.path).toBe('/hbos/profile')
    await click(wrapper, '关闭')

    await click(wrapper, '查看恢复方式')
    expect(dialog.props('title')).toBe('账号恢复方式')
    expect(router.currentRoute.value.path).toBe('/hbos/profile')
  })

  it('密码第一步没有新口令输入，真实 proof 后才进入设置步骤', async () => {
    const { wrapper } = await render(AccountSecurity)
    await click(wrapper, '修改密码')
    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(proofInput(wrapper).exists()).toBe(true)

    await verifyPassword(wrapper)
    expect(api.reauthenticate).toHaveBeenCalledWith('synthetic current password', '', '')
    expect(wrapper.text()).toContain('本人已验证')
    expect(wrapper.find('.ant-steps').text()).toContain('验证本人')
    expect(newPasswordFields(wrapper)).toHaveLength(2)
    expect(wrapper.text()).toContain('最多 512 字符')
    expect(wrapper.text()).toContain('账号安全要求')
    expect(wrapper.text()).not.toContain('本页只')
    expect(wrapper.text()).not.toMatch(/强度(优秀|良好|很强|百分)/)
  })

  it('个人中心弹窗不采用 getSecurity 中仍有效的旧 proof', async () => {
    api.getSecurity.mockImplementation(async () => security({ proof: { valid: true, expires_in: 250, method: 'password' } }))
    const { wrapper } = await render(AccountSecurity)
    await click(wrapper, '修改密码')
    const verification = wrapper.findComponent(OwnAccountVerification)
    expect(verification.props('adoptExisting')).toBe(false)
    expect(verification.emitted('verified')).toBeUndefined()
    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(wrapper.text()).not.toContain('本人已验证')
    await verifyPassword(wrapper)
    expect(newPasswordFields(wrapper)).toHaveLength(2)
  })

  it('proof 到期会清除新口令并回到验证步骤', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    api.reauthenticate.mockResolvedValue({ verified: true, expires_in: 1 })
    const { wrapper } = await render(AccountSecurity)
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)

    await vi.advanceTimersByTimeAsync(1300)
    await flushPromises()

    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(proofInput(wrapper).exists()).toBe(true)
    expect(wrapper.text()).toMatch(/过期|失效|重新验证/)
  })

  it('取消后重开需要重新验证，旧 proof 不能复用', async () => {
    const { wrapper } = await render(AccountSecurity)
    await advanceToPasswordForm(wrapper)
    await click(wrapper, '取消')

    await click(wrapper, '修改密码')
    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(proofInput(wrapper).exists()).toBe(true)
    expect(button(wrapper, '继续设置').attributes('disabled')).toBeDefined()
    expect(api.reauthenticate).toHaveBeenCalledTimes(1)
  })

  it('恢复弹窗显示真实邮箱状态，打开时不自动跳转，仅可用时提供现有流程链接', async () => {
    api.getSecurity.mockImplementation(async () => security({ mail_recovery_available: false }))
    const unavailable = await render(AccountSecurity)
    await click(unavailable.wrapper, '查看恢复方式')
    expect(unavailable.wrapper.text()).toContain('暂无恢复邮箱')
    expect(unavailable.wrapper.find('a[href="/hbos/reset-password"]').exists()).toBe(false)
    expect(unavailable.router.currentRoute.value.path).toBe('/hbos/profile')
    unavailable.wrapper.unmount()
    wrappers = wrappers.filter(item => item !== unavailable.wrapper)

    api.getSecurity.mockImplementation(async () => security({ mail_recovery_available: true }))
    const available = await render(AccountSecurity)
    await click(available.wrapper, '查看恢复方式')
    expect(available.wrapper.text()).toContain('恢复邮箱可用')
    const link = available.wrapper.find('a[href="/hbos/reset-password"]')
    expect(link.exists()).toBe(true)
    expect(available.router.currentRoute.value.path).toBe('/hbos/profile')
    await link.trigger('click')
    await flushPromises()
    expect(available.router.currentRoute.value.path).toBe('/hbos/reset-password')
  })

  it.each([
    [{ feishu_configured: false }, '飞书登录服务当前不可用'],
    [{ administrator: true, administrator_link_enabled: false }, '管理员飞书绑定需要专门授权'],
  ])('受控范围未开放时不放无法操作的 proof 或绑定按钮 %j', async (overrides, message) => {
    api.getSecurity.mockImplementation(async () => security(overrides))
    const { wrapper } = await render(AccountSecurity)
    await click(wrapper, '查看登录方式')
    expect(wrapper.text()).toContain(message)
    expect(wrapper.find('.proof-form').exists()).toBe(false)
    expect(wrapper.findAll('button').some(item => item.text().includes('授权绑定本人飞书'))).toBe(false)
    expect(wrapper.text()).toContain('继续使用密码登录')
  })

  it('只有 setPassword 真实 resolved 后才显示完成', async () => {
    let resolveWrite!: (value: unknown) => void
    api.setPassword.mockReturnValue(new Promise(resolve => { resolveWrite = resolve }))
    const { wrapper } = await render(AccountSecurity)
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()

    expect(api.setPassword).toHaveBeenCalledWith('synthetic replacement password', expect.stringMatching(/^[0-9a-f-]{36}$/))
    expect(wrapper.text()).not.toContain('密码设置完成')
    expect(wrapper.text()).not.toContain('密码已保存')

    resolveWrite({ changed: true, login_name: 'synthetic' })
    await flushPromises()
    await flushPromises()
    expect(wrapper.text()).toContain('密码设置完成')
    expect(wrapper.text()).toContain('密码已保存')
    expect(wrapper.text()).toContain('synthetic')
    expect(vi.mocked(clearFrappeCsrfToken)).toHaveBeenCalled()
    expect(readPendingAccountWrite(actor.user.id)).toBeNull()
  })

  it('已有不同 pending 时拒绝覆盖并禁止新的安全写', async () => {
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const existing = crypto.randomUUID()
    expect(rememberPendingAccountWrite(actor.user.id, 'password', existing)).toBe(true)
    await submitPasswordForm(wrapper)
    expect(api.setPassword).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('上次操作待核对')
    expect(readPendingAccountWrite(actor.user.id)?.requestId).toBe(existing)
  })

  it('无法写入 pending marker 时拒绝发送安全写', async () => {
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('unavailable') })
    await submitPasswordForm(wrapper)
    expect(api.setPassword).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('无法保留本次核对记录')
    expect(readPendingAccountWrite(actor.user.id)).toBeNull()
    setItem.mockRestore()
  })

  it('浏览器不能生成请求编号时显示错误且不发送安全写', async () => {
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    vi.spyOn(crypto, 'randomUUID').mockImplementation(() => { throw new TypeError('secure random unavailable') })

    await submitPasswordForm(wrapper)

    expect(api.setPassword).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('当前浏览器无法建立安全提交记录')
  })

  it('明确 4xx 拒绝后清除 pending marker，不进入查询', async () => {
    api.setPassword.mockRejectedValueOnce(new FrappeRequestError('VALIDATION_ERROR', '密码不符合要求。', 400))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    await submitPasswordForm(wrapper)
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    expect(readPendingAccountWrite(actor.user.id)).toBeNull()
    expect(wrapper.text()).toContain('密码不符合要求')
    expect(wrapper.text()).not.toContain('查询上次提交结果')
  })

  it('502 写入跨组件卸载保留同 User 请求编号，重进后只查询不重发', async () => {
    api.setPassword.mockRejectedValueOnce(new FrappeRequestError('SERVICE_ERROR', '服务暂时不可用。', 502))
    const first = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(first.wrapper)
    await fillNewPassword(first.wrapper)
    await submitPasswordForm(first.wrapper)
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    const marker = readPendingAccountWrite(actor.user.id)
    expect(marker?.kind).toBe('password')
    const requestId = marker!.requestId

    first.wrapper.unmount()
    wrappers = wrappers.filter(item => item !== first.wrapper)
    api.getSecurity.mockImplementation(async () => security())
    const second = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await flushPromises()
    await flushPromises()
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    expect(api.getSecurity).toHaveBeenCalledWith(requestId)
    expect(second.wrapper.text()).toContain('上次操作待核对')
    expect(readPendingAccountWrite(actor.user.id)?.requestId).toBe(requestId)

    api.getSecurity.mockImplementation(async (id?: string) => id
      ? security({ write_result: { completed: true, action: 'password' } })
      : security())
    await click(second.wrapper, '查询上次提交结果')
    expect(second.wrapper.text()).toContain('密码已保存')
    expect(readPendingAccountWrite(actor.user.id)).toBeNull()
    expect(api.setPassword).toHaveBeenCalledTimes(1)
  })

  it('session-boundary 清除未核对 pending marker', async () => {
    api.setPassword.mockRejectedValueOnce(new FrappeRequestError('SERVICE_ERROR', '服务暂时不可用。', 502))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    await submitPasswordForm(wrapper)
    expect(readPendingAccountWrite(actor.user.id)).not.toBeNull()
    window.dispatchEvent(new Event('hbos:session-boundary'))
    await flushPromises()
    expect(readPendingAccountWrite(actor.user.id)).not.toBeNull()
    expect(modal(wrapper).props('open')).toBe(false)
  })

  it('identity 暂时变为未知时保留同一账号的 pending marker', async () => {
    api.setPassword.mockRejectedValueOnce(new FrappeRequestError('SERVICE_ERROR', '服务暂时不可用。', 502))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    await submitPasswordForm(wrapper)
    const requestId = readPendingAccountWrite(actor.user.id)?.requestId
    expect(requestId).toBeTruthy()

    await wrapper.setProps({ identity: undefined })
    await flushPromises()
    expect(readPendingAccountWrite(actor.user.id)?.requestId).toBe(requestId)
  })

  it('实际 identity 换人清除旧 User 的 pending marker', async () => {
    api.setPassword.mockRejectedValueOnce(new FrappeRequestError('SERVICE_ERROR', '服务暂时不可用。', 502))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    await submitPasswordForm(wrapper)
    expect(readPendingAccountWrite(actor.user.id)).not.toBeNull()
    api.getSecurity.mockImplementation(async () => security({ user: 'another@example.test', login_name: 'another' }))
    await wrapper.setProps({ identity: 'another@example.test' })
    await flushPromises()
    expect(sessionStorage.getItem('hbos:pending-account-write:v1')).toBeNull()
  })

  it('不同 User 不恢复旧 pending marker', async () => {
    api.setPassword.mockRejectedValueOnce(new FrappeRequestError('SERVICE_ERROR', '服务暂时不可用。', 502))
    const first = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(first.wrapper)
    await fillNewPassword(first.wrapper)
    await submitPasswordForm(first.wrapper)
    expect(readPendingAccountWrite(actor.user.id)).not.toBeNull()
    first.wrapper.unmount()
    wrappers = wrappers.filter(item => item !== first.wrapper)

    actor.user.id = 'another@example.test'
    actor.user.displayName = '另一账号'
    api.getSecurity.mockImplementation(async () => security())
    const second = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await flushPromises()
    expect(second.wrapper.text()).not.toContain('上次操作待核对')
    expect(sessionStorage.getItem('hbos:pending-account-write:v1')).toBeNull()
    expect(api.setPassword).toHaveBeenCalledTimes(1)
  })

  it('receipt 的 completed action 不匹配时仍保持待核对', async () => {
    api.setPassword.mockRejectedValueOnce(new Error('response lost'))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    await submitPasswordForm(wrapper)
    const marker = readPendingAccountWrite(actor.user.id)
    const requestId = marker!.requestId
    api.getSecurity.mockImplementation(async (id?: string) => id
      ? security({ write_result: { completed: true, action: 'unlink' } })
      : security())
    await click(wrapper, '查询上次提交结果')
    expect(wrapper.text()).not.toContain('密码设置完成')
    expect(wrapper.text()).toContain('上次操作尚未确认')
    expect(readPendingAccountWrite(actor.user.id)?.requestId).toBe(requestId)
    expect(api.setPassword).toHaveBeenCalledTimes(1)
  })

  it('恢复签发 receipt 只确认已签发，不自动重签或伪造原链接', async () => {
    api.getSecurity.mockImplementation(async () => security({ can_admin_recover: true }))
    api.adminIssueRecovery.mockRejectedValueOnce(new FrappeRequestError('SERVICE_ERROR', '服务暂时不可用。', 502))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await wrapper.find('.ant-collapse-header').trigger('click')
    await flushPromises()
    await click(wrapper, '协助员工恢复账号')
    await verifyPassword(wrapper)
    await wrapper.find('#recovery-user').setValue('synthetic')
    await wrapper.find('#recovery-reason').setValue('已核对员工本人与账号归属以及影响')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const marker = readPendingAccountWrite(actor.user.id)
    expect(marker?.kind).toBe('recovery')
    expect(api.adminIssueRecovery).toHaveBeenCalledTimes(1)

    api.getSecurity.mockImplementation(async (id?: string) => id
      ? security({ can_admin_recover: true, write_result: { completed: true, action: 'recovery_issue' } })
      : security({ can_admin_recover: true }))
    await click(wrapper, '查询上次提交结果')
    expect(wrapper.text()).toContain('服务器已确认上次重置链接已签发')
    expect(wrapper.text()).toContain('原链接无法再次读取')
    expect(wrapper.text()).not.toContain('复制一次性链接')
    expect(readPendingAccountWrite(actor.user.id)).toBeNull()
    expect(api.adminIssueRecovery).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).not.toContain('重新验证后签发新链接')
    await click(wrapper, '协助员工恢复账号')
    expect(wrapper.find('.proof-form').exists()).toBe(true)
    expect(api.adminIssueRecovery).toHaveBeenCalledTimes(1)
  })

  it('未知写入结果在关闭重开后仍保留，阻止重发并允许查询收据', async () => {
    vi.mocked(clearFrappeCsrfToken).mockClear()
    api.setPassword.mockRejectedValue(new Error('response lost'))
    const { wrapper } = await render(AccountSecurity)
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('查询上次提交结果')
    expect(api.setPassword).toHaveBeenCalledTimes(1)

    await click(wrapper, '关闭')
    await click(wrapper, '修改密码')
    expect(wrapper.text()).toContain('上次操作待核对')
    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(api.setPassword).toHaveBeenCalledTimes(1)

    api.getSecurity.mockImplementation(async (requestId?: string) => requestId
      ? security({ write_result: { completed: true, action: 'password' } })
      : security())
    await click(wrapper, '查询上次提交结果')
    expect(api.getSecurity).toHaveBeenLastCalledWith(expect.stringMatching(/^[0-9a-f-]{36}$/))
    expect(wrapper.text()).toContain('密码设置完成')
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    expect(vi.mocked(clearFrappeCsrfToken)).toHaveBeenCalledOnce()
  })

  it('已绑定的普通账号解绑须原密码、MFA proof 和明确 checkbox', async () => {
    api.getSecurity.mockImplementation(async () => security({ feishu_bound: true, feishu_stepup_available: true }))
    const { wrapper } = await render(AccountSecurity)
    await click(wrapper, '管理绑定')
    expect(wrapper.find('.proof-form').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('本人飞书验证码')
    const unlink = button(wrapper, '确认解绑飞书')
    expect(unlink.attributes('disabled')).toBeDefined()

    await verifyPassword(wrapper)
    expect(api.reauthenticate).toHaveBeenCalledTimes(1)
    expect(unlink.attributes('disabled')).toBeDefined()
    await wrapper.find('input[type="checkbox"]').setValue(true)
    expect(unlink.attributes('disabled')).toBeUndefined()
    await unlink.trigger('click')
    await flushPromises()
    expect(api.unlinkFeishu).toHaveBeenCalledWith(expect.stringMatching(/^[0-9a-f-]{36}$/))
    expect(wrapper.text()).toContain('飞书已解绑')
  })

  it('内置 Administrator 的飞书绑定不能由本流程删除', async () => {
    api.getSecurity.mockImplementation(async () => security({ administrator: true, administrator_link_enabled: true, feishu_bound: true }))
    const { wrapper } = await render(AccountSecurity)
    await click(wrapper, '管理绑定')
    expect(wrapper.text()).toMatch(/专项|保管人交接/)
    expect(wrapper.findAll('button').some(item => item.text().includes('确认解绑飞书'))).toBe(false)
    expect(wrapper.find('.proof-form').exists()).toBe(false)
  })

  it('切换本人身份会关闭弹窗并清空未提交口令', async () => {
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    api.getSecurity.mockImplementation(async () => security({ user: 'another@example.test', login_name: 'another' }))
    await wrapper.setProps({ identity: 'another@example.test' })
    await flushPromises()
    expect(modal(wrapper).props('open')).toBe(false)
    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(wrapper.emitted('statusChange')?.at(-1)?.[0]).toMatchObject({ user: 'another@example.test' })
  })

  it('写入遇到 401 会关闭弹窗、清空口令并清除账号状态', async () => {
    api.setPassword.mockRejectedValue(new FrappeRequestError('UNAUTHENTICATED', '会话已失效，请重新登录。', 401))
    const { wrapper } = await render(AccountSecurity)
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    expect(modal(wrapper).props('open')).toBe(false)
    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(wrapper.text()).toContain('会话已失效')
    expect(wrapper.text()).toMatch(/重试读取账号状态/)
    expect(readPendingAccountWrite(actor.user.id)).toBeNull()
  })

  it('Profile 身份摘要保留 Admin 不适用、unlinked/conflict 待核对语义', async () => {
    employees.getMyEmployeeStatus.mockResolvedValue({ status: 'unlinked' })
    api.getSecurity.mockImplementation(async () => security({
      identity: { display_name: '未关联不应显示', employee_number: 'T001', department: '未关联部门', login_name: 'synthetic' },
    }))
    const unlinked = await render(Profile)
    expect(unlinked.wrapper.text()).toContain('员工档案待关联')
    expect(unlinked.wrapper.text()).toContain('待核对')
    expect(unlinked.wrapper.text()).not.toContain('员工档案已关联')
    expect(unlinked.wrapper.text()).not.toContain('未关联不应显示')
    expect(unlinked.wrapper.text()).not.toContain('未关联部门')
    await click(unlinked.wrapper, '核对关联')
    expect(unlinked.wrapper.text()).toContain('员工档案尚未关联')
    unlinked.wrapper.unmount()
    wrappers = wrappers.filter(item => item !== unlinked.wrapper)

    actor.user.id = 'Administrator'
    actor.user.displayName = '内置管理员'
    api.getSecurity.mockImplementation(async () => security({
      identity: { display_name: '不应显示档案姓名', employee_number: 'T001', department: '不应显示部门', login_name: 'Administrator' },
    }))
    employees.getMyEmployeeStatus.mockClear()
    const admin = await render(Profile)
    expect(admin.wrapper.text()).toContain('系统账号')
    expect(admin.wrapper.text()).toContain('员工档案不适用')
    expect(admin.wrapper.text()).toContain('不适用')
    expect(admin.wrapper.text()).not.toContain('不应显示档案姓名')
    expect(admin.wrapper.text()).not.toContain('不应显示部门')
    expect(employees.getMyEmployeeStatus).not.toHaveBeenCalled()
    admin.wrapper.unmount()
    wrappers = wrappers.filter(item => item !== admin.wrapper)

    actor.user.id = 'conflict@example.test'
    employees.getMyEmployeeStatus.mockResolvedValue({ status: 'conflict' })
    const conflict = await render(Profile)
    expect(conflict.wrapper.text()).toContain('员工归属存在冲突')
    expect(conflict.wrapper.text()).toContain('待核对')
    await click(conflict.wrapper, '核对关联')
    expect(conflict.wrapper.text()).toContain('员工档案归属存在冲突')
  })

  it('linked 且 User、工号一致时使用 security.identity 的档案姓名和部门', async () => {
    actor.user.displayName = '账号显示名'
    api.getSecurity.mockImplementation(async () => security({
      identity: { display_name: '档案姓名', employee_number: 'T001', department: '人事部', login_name: 'synthetic' },
    }))
    const { wrapper } = await render(Profile)
    expect(wrapper.find('.profile-card h2').text()).toBe('档案姓名')
    expect(wrapper.text()).toContain('人事部 · 合成岗位')
    expect(wrapper.text()).not.toContain('账号显示名 · 档案姓名待核对')
    await click(wrapper, '查看员工资料')
    expect(wrapper.text()).toContain('档案姓名')
    expect(wrapper.text()).toContain('人事部')
    expect(wrapper.text()).not.toContain('employee_name')
  })

  it('identity 工号与本人档案不一致时不信任档案姓名和部门', async () => {
    actor.user.displayName = '账号显示名'
    api.getSecurity.mockImplementation(async () => security({
      identity: { display_name: '不可信档案姓名', employee_number: 'T999', department: '错误部门', login_name: 'synthetic' },
    }))
    const { wrapper } = await render(Profile)
    expect(wrapper.find('.profile-card h2').text()).toBe('账号显示名')
    expect(wrapper.text()).toContain('账号显示名 · 档案姓名待核对')
    await click(wrapper, '查看员工资料')
    expect(wrapper.text()).toContain('账号显示名（档案姓名待核对）')
    expect(wrapper.text()).not.toContain('不可信档案姓名')
    expect(wrapper.text()).not.toContain('错误部门')
    expect(wrapper.text()).toContain('合成部门')
  })

  it('旧 User 的 identity 不能覆盖当前账号或显示档案姓名', async () => {
    actor.user.displayName = '账号显示名'
    api.getSecurity.mockImplementation(async () => security({
      user: 'old-user@example.test',
      identity: { display_name: '旧档案姓名', employee_number: 'T001', department: '旧部门', login_name: 'old' },
    }))
    const { wrapper } = await render(Profile)
    expect(wrapper.find('.profile-card h2').text()).toBe('账号显示名')
    expect(wrapper.text()).toContain('账号显示名 · 档案姓名待核对')
    expect(wrapper.text()).not.toContain('旧档案姓名')
    expect(wrapper.text()).not.toContain('旧部门')
    expect(wrapper.text()).not.toContain('当前使用明亮主题')
  })

  it('proof 失效会清除解绑确认', async () => {
    api.getSecurity.mockImplementation(async () => security({ feishu_bound: true }))
    const { wrapper } = await render(AccountSecurity)
    await click(wrapper, '管理绑定')
    await verifyPassword(wrapper)
    const checkbox = wrapper.find('input[type="checkbox"]')
    await checkbox.setValue(true)
    expect((checkbox.element as HTMLInputElement).checked).toBe(true)

    api.getSecurity.mockImplementation(async () => security({ feishu_bound: true, proof: { valid: false, expires_in: 0, method: null } }))
    window.dispatchEvent(new Event('focus'))
    await flushPromises()
    expect((wrapper.find('input[type="checkbox"]').element as HTMLInputElement).checked).toBe(false)
  })

  it('session-boundary 清除临时恢复链接和未提交内容', async () => {
    api.getSecurity.mockImplementation(async () => security({ can_admin_recover: true }))
    const { wrapper } = await render(AccountSecurity)
    await wrapper.find('.ant-collapse-header').trigger('click')
    await flushPromises()
    await click(wrapper, '协助员工恢复账号')
    await verifyPassword(wrapper)
    await wrapper.find('#recovery-user').setValue('synthetic')
    await wrapper.find('#recovery-reason').setValue('已核对员工本人与账号归属以及影响')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('复制一次性链接')

    window.dispatchEvent(new Event('hbos:session-boundary'))
    await flushPromises()
    expect(wrapper.text()).not.toContain('复制一次性链接')
    expect(wrapper.text()).not.toContain('已签发给')
    expect(wrapper.text()).toContain('登录状态已变化')
  })

  it.each([
    { label: '缺少 changed', response: {} },
    { label: 'changed=false', response: { changed: false } },
  ])('setPassword $label 的成功响应进入 unknown，关闭重开只查询同 request_id 不重发', async ({ response }) => {
    api.setPassword.mockResolvedValue(response)
    const { wrapper } = await render(AccountSecurity)
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()
    expect(api.setPassword).toHaveBeenCalledTimes(1)
    const requestId = api.setPassword.mock.calls[0]![1]
    expect(wrapper.text()).toContain('查询上次提交结果')
    expect(newPasswordFields(wrapper)).toHaveLength(0)

    await click(wrapper, '关闭')
    await click(wrapper, '修改密码')
    expect(wrapper.text()).toContain('上次操作待核对')
    expect(newPasswordFields(wrapper)).toHaveLength(0)
    expect(api.setPassword).toHaveBeenCalledTimes(1)

    api.getSecurity.mockImplementation(async (id?: string) => id
      ? security({ write_result: { completed: true, action: 'password' } })
      : security())
    await click(wrapper, '查询上次提交结果')
    expect(api.getSecurity).toHaveBeenLastCalledWith(requestId)
    expect(wrapper.text()).toContain('密码设置完成')
    expect(api.setPassword).toHaveBeenCalledTimes(1)
  })

  it.each([
    { label: '缺少 unlinked', response: {} },
    { label: 'unlinked=false', response: { unlinked: false } },
  ])('unlink $label 的成功响应进入 unknown，查询确认前不重复解绑', async ({ response }) => {
    api.getSecurity.mockImplementation(async () => security({ feishu_bound: true }))
    api.unlinkFeishu.mockResolvedValue(response)
    const { wrapper } = await render(AccountSecurity)
    await click(wrapper, '管理绑定')
    await verifyPassword(wrapper)
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await click(wrapper, '确认解绑飞书')
    expect(api.unlinkFeishu).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('查询上次提交结果')
    expect(wrapper.text()).not.toContain('飞书已解绑')

    api.getSecurity.mockImplementation(async (id?: string) => id
      ? security({ feishu_bound: false, write_result: { completed: true, action: 'unlink' } })
      : security({ feishu_bound: true }))
    await click(wrapper, '查询上次提交结果')
    expect(api.unlinkFeishu).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('飞书已解绑')
  })

  it('旧账号写入完成不会解除新账号正在提交的锁定', async () => {
    let finishOld!: (value: unknown) => void, finishNew!: (value: unknown) => void
    api.setPassword.mockReturnValueOnce(new Promise(resolve => { finishOld = resolve }))
      .mockReturnValueOnce(new Promise(resolve => { finishNew = resolve }))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper); await fillNewPassword(wrapper); await submitPasswordForm(wrapper)
    api.getSecurity.mockImplementation(async () => security({ user: 'another@example.test', login_name: 'another' }))
    await wrapper.setProps({ identity: 'another@example.test' }); await flushPromises()
    await advanceToPasswordForm(wrapper); await fillNewPassword(wrapper); await submitPasswordForm(wrapper)
    expect(api.setPassword).toHaveBeenCalledTimes(2)
    finishOld({ changed: true, login_name: 'old-user-login' }); await flushPromises()
    expect(button(wrapper, '确认设置').attributes('disabled')).toBeDefined()
    finishNew({ changed: true, login_name: 'another' }); await flushPromises()
    expect(wrapper.text()).not.toContain('old-user-login')
  })
  it('身份切换后旧密码写入成功响应不得显示完成或旧 User', async () => {
    let resolveWrite!: (value: unknown) => void
    api.setPassword.mockReturnValue(new Promise(resolve => { resolveWrite = resolve }))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()

    api.getSecurity.mockImplementation(async () => security({ user: 'another@example.test', login_name: 'another' }))
    await wrapper.setProps({ identity: 'another@example.test' })
    await flushPromises()
    resolveWrite({ changed: true, login_name: 'old-user-login' })
    await flushPromises()
    expect(modal(wrapper).props('open')).toBe(false)
    expect(wrapper.text()).not.toContain('密码设置完成')
    expect(wrapper.text()).not.toContain('old-user-login')
    expect(wrapper.emitted('statusChange')?.at(-1)?.[0]).toMatchObject({ user: 'another@example.test' })
  })

  it('身份切换后旧 refresh 响应不得恢复旧 User 成功状态', async () => {
    let resolveRefresh!: (value: unknown) => void
    api.setPassword.mockResolvedValue({ changed: true, login_name: 'old-user-login' })
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    api.getSecurity.mockImplementation(async () => new Promise(resolve => { resolveRefresh = resolve }))
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('密码设置完成')

    await wrapper.setProps({ identity: 'another@example.test' })
    await flushPromises()
    resolveRefresh(security({ user: actor.user.id, login_name: 'old-user-login' }))
    await flushPromises()
    expect(wrapper.text()).not.toContain('密码设置完成')
    expect(wrapper.emitted('statusChange')?.at(-1)?.[0]?.user).not.toBe(actor.user.id)
  })

  it('身份切换后旧 checkOutcome 成功响应不得显示完成', async () => {
    let resolveCheck!: (value: unknown) => void
    api.setPassword.mockRejectedValue(new Error('response lost'))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('查询上次提交结果')

    api.getSecurity.mockImplementation(async (id?: string) => id
      ? new Promise(resolve => { resolveCheck = resolve })
      : security({ user: 'another@example.test', login_name: 'another' }))
    await click(wrapper, '查询上次提交结果')
    await wrapper.setProps({ identity: 'another@example.test' })
    await flushPromises()
    resolveCheck(security({ write_result: { completed: true, action: 'password' }, login_name: 'old-user-login' }))
    await flushPromises()
    expect(wrapper.text()).not.toContain('密码设置完成')
    expect(wrapper.text()).not.toContain('old-user-login')
    expect(wrapper.emitted('statusChange')?.at(-1)?.[0]).toMatchObject({ user: 'another@example.test' })
  })

  it('session-boundary 后旧密码写入成功响应不得显示完成', async () => {
    let resolveWrite!: (value: unknown) => void
    api.setPassword.mockReturnValue(new Promise(resolve => { resolveWrite = resolve }))
    const { wrapper } = await render(AccountSecurity, '/hbos/profile', { identity: actor.user.id })
    await advanceToPasswordForm(wrapper)
    await fillNewPassword(wrapper)
    const form = wrapper.findAll('form').find(item => item.find('input[autocomplete="new-password"]').exists())!
    await form.trigger('submit')
    await flushPromises()

    window.dispatchEvent(new Event('hbos:session-boundary'))
    await flushPromises()
    resolveWrite({ changed: true, login_name: 'old-user-login' })
    await flushPromises()
    expect(modal(wrapper).props('open')).toBe(false)
    expect(wrapper.text()).not.toContain('密码设置完成')
    expect(wrapper.text()).not.toContain('old-user-login')
    expect(wrapper.text()).toContain('登录状态已变化')
  })
})
