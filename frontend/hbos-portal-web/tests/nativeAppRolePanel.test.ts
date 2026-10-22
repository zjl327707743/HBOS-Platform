import { beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { ref } from 'vue'

const api = vi.hoisted(() => ({ describe: vi.fn(), preview: vi.fn(), save: vi.fn() }))
vi.mock('@/services/iamAppRoles', () => ({ describeAppRoles: api.describe, previewAppRoles: api.preview, saveAppRoles: api.save }))
vi.mock('@/composables/useAccountProof', async () => {
  const vue = await import('vue')
  const proof = { valid: vue.ref(true), method: vue.ref<string | null>('password'), remaining: vue.ref(300), sync: vi.fn(), invalidate: vi.fn(), recheck: vi.fn(), grant: vi.fn() }
  ;(globalThis as unknown as { __hbosProof: typeof proof }).__hbosProof = proof
  return { useAccountProof: () => proof }
})

import NativeAppRolePanel from '@/components/iam/NativeAppRolePanel.vue'
import { clearIamAccess, iamSession } from '@/services/iamAccess'

const proof = (globalThis as unknown as { __hbosProof: { valid: ReturnType<typeof ref<boolean>>; method: ReturnType<typeof ref<string | null>>; remaining: ReturnType<typeof ref<number>>; sync: () => void; invalidate: () => void; recheck: () => void; grant: () => void } }).__hbosProof

const state = () => ({
  employee: 'E1',
  user: 'u1',
  company: 'C1',
  department: 'D1',
  version: 'v1',
  native_roles: ['Employee'],
  apps: [{
    app_id: 'inventory',
    title: '仓储库存',
    scope_note: '原生角色不区分仓库',
    roles: [{ role: 'Stock User', title: '仓储经办', native_scope: 'GLOBAL', risk: 'medium', summary: '读取库存主数据', permissions_note: '含单据读写' }],
    blocked: [],
    current: [],
  }],
  is_grantor: true,
  can_grant: true,
  grant_requirement: '只有站点级授权人可授予',
  scope_envelope: { company: 'C1', source: 'User Permission', name: 'UP1' },
})

const preview = () => ({
  employee: 'E1', user: 'u1', app_id: 'inventory', current: [], target: ['Stock User'], add: ['Stock User'], remove: [],
  unchanged: [], other_roles_preserved: ['Employee'], changed: true, version: 'v1', context_revision: 'ctx',
  scope_note: 'GLOBAL', scope_envelope: { company: 'C1', source: 'User Permission', name: 'UP1' },
})

function mountPanel () {
  return mount(NativeAppRolePanel, {
    props: { employeeId: 'E1' },
    global: { plugins: [Antd], stubs: { OwnAccountVerification: { template: '<div class="proof-stub" />' }, 'a-skeleton': true } },
  })
}
const click = async (wrapper: ReturnType<typeof mountPanel>, text: string) => {
  const button = wrapper.findAll('button').find(row => row.text() === text)
  expect(button, text).toBeDefined()
  await button!.trigger('click')
  await flushPromises()
  return button!
}
const checkbox = (wrapper: ReturnType<typeof mountPanel>, index: number) => wrapper.findAll('input[type="checkbox"]')[index]!

beforeEach(() => {
  clearIamAccess()
  Object.assign(iamSession, { ready: true, user: 'grantor', capabilities: ['iam.access.manage'] })
  proof.valid.value = true
  proof.method.value = 'password'
  vi.resetAllMocks()
  api.describe.mockResolvedValue(state())
  api.preview.mockResolvedValue(preview())
})

it('never submits without an acknowledged, freshly previewed change', async () => {
  const wrapper = mountPanel()
  await flushPromises()
  await click(wrapper, '调整原生角色')
  // Selecting a GLOBAL role is a grant: it must not be previewable until the
  // operator has acknowledged the unscoped native authority.
  await checkbox(wrapper, 0).setValue(true)
  const prepare = await click(wrapper, '预览变更')
  expect(api.preview).not.toHaveBeenCalled()
  expect(prepare.attributes('disabled')).toBeDefined()

  await checkbox(wrapper, 1).setValue(true)
  await click(wrapper, '预览变更')
  expect(api.preview).toHaveBeenCalledWith('E1', 'inventory', ['Stock User'], 'v1', true)
  expect(wrapper.text()).toContain('保存后的差异')

  // Changing the selected role after a preview must invalidate it, otherwise
  // the commit would carry an unpreviewed role set with a stale revision.
  await checkbox(wrapper, 0).setValue(false)
  expect(wrapper.text()).not.toContain('保存后的差异')
  expect(api.save).not.toHaveBeenCalled()
  wrapper.unmount()
})

it('keeps the editor after a 409 conflict and never reports success', async () => {
  api.save.mockRejectedValue(Object.assign(new Error('conflict'), { status: 409 }))
  const wrapper = mountPanel()
  await flushPromises()
  await click(wrapper, '调整原生角色')
  await checkbox(wrapper, 0).setValue(true)
  await checkbox(wrapper, 1).setValue(true)
  await click(wrapper, '预览变更')
  await click(wrapper, '确认保存')
  expect(api.save).toHaveBeenCalledTimes(1)
  expect(wrapper.text()).toContain('草稿已保留')
  expect(wrapper.text()).toContain('仓储库存')
  expect(wrapper.find('.session-recovery').exists()).toBe(false)
  expect(wrapper.findAll('button').some(row => row.text() === '确认保存')).toBe(false)
  expect(wrapper.emitted('saved')).toBeUndefined()
  wrapper.unmount()
})

it('accepts only a password proof for the GLOBAL grant', async () => {
  proof.method.value = 'feishu_inbox'
  const wrapper = mountPanel()
  await flushPromises()
  await click(wrapper, '调整原生角色')
  await checkbox(wrapper, 0).setValue(true)
  await checkbox(wrapper, 1).setValue(true)
  await click(wrapper, '预览变更')
  const save = wrapper.findAll('button').find(row => row.text() === '确认保存')!
  expect(save.attributes('disabled')).toBeDefined()
  await save.trigger('click')
  await flushPromises()
  expect(api.save).not.toHaveBeenCalled()
  wrapper.unmount()
})

it('reuses one request id across retries of the same edit intent', async () => {
  api.save.mockRejectedValueOnce(Object.assign(new Error('timeout'), { status: 500 })).mockResolvedValueOnce(preview())
  const wrapper = mountPanel()
  await flushPromises()
  await click(wrapper, '调整原生角色')
  await checkbox(wrapper, 0).setValue(true)
  await checkbox(wrapper, 1).setValue(true)
  await click(wrapper, '预览变更')
  await click(wrapper, '确认保存')
  await click(wrapper, '预览变更')
  await click(wrapper, '确认保存')
  expect(api.save).toHaveBeenCalledTimes(2)
  expect(api.save.mock.calls[0]![5]).toBe(api.save.mock.calls[1]![5])
  wrapper.unmount()
})

it('keeps an existing GLOBAL role revocable without grantor rights or envelope', async () => {
  api.describe.mockResolvedValue({
    ...state(),
    can_grant: false,
    is_grantor: false,
    scope_envelope: null,
    apps: [{ ...state().apps[0], current: ['Stock User'] }],
  })
  api.preview.mockResolvedValue({ ...preview(), add: [], remove: ['Stock User'], target: [], changed: true })
  const wrapper = mountPanel()
  await flushPromises()
  // Removing a role must stay reachable exactly when the envelope is gone —
  // otherwise a privilege could no longer be taken away through the portal.
  const edit = wrapper.findAll('button').find(row => row.text() === '调整原生角色')
  expect(edit).toBeDefined()
  await edit!.trigger('click'); await flushPromises()
  await click(wrapper, '预览变更')
  expect(api.preview).toHaveBeenCalledWith('E1', 'inventory', ['Stock User'], 'v1', false)
  wrapper.unmount()
})

it('does not require a GLOBAL acknowledgement when no GLOBAL role is being granted', async () => {
  api.describe.mockResolvedValue({
    ...state(),
    apps: [{ ...state().apps[0], current: ['Stock User'], roles: [{ ...state().apps[0].roles[0], native_scope: 'SCOPED' }] }],
  })
  api.preview.mockResolvedValue({ ...preview(), add: [], remove: ['Stock User'], target: [], changed: true })
  const wrapper = mountPanel()
  await flushPromises()
  await click(wrapper, '调整原生角色')
  await checkbox(wrapper, 0).setValue(false)
  await click(wrapper, '预览变更')
  expect(api.preview).toHaveBeenCalledWith('E1', 'inventory', [], 'v1', false)
  expect(wrapper.text()).not.toContain('我确认 Stock User 为 GLOBAL')
  wrapper.unmount()
})

it('does not offer editing on the operator own employee record', async () => {
  api.describe.mockResolvedValue({ ...state(), user: 'grantor' })
  const wrapper = mountPanel()
  await flushPromises()
  Object.assign((await import('@/services/iamAccess')).iamSession, { ready: true, user: 'grantor', capabilities: ['iam.access.manage'] })
  await flushPromises()
  expect(wrapper.text()).toContain('不能为自己的账号调整原生角色')
  expect(wrapper.findAll('button').some(row => row.text() === '调整原生角色')).toBe(false)
  wrapper.unmount()
})
