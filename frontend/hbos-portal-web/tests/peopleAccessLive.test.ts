import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PeopleAccessView from '@/views/PeopleAccessView.vue'
import { getPeople, getPeopleOrganizations, getPeopleRoles } from '@/services/peopleAccessApi'
import { getManagementContext } from '@/services/organizationManagementApi'

vi.mock('@/services/organizationManagementApi', () => ({ getManagementContext: vi.fn(), listManagedPositions: vi.fn(), getManagedPersonAssignments: vi.fn() }))
vi.mock('@/services/peopleAccessApi', () => ({ getPeople: vi.fn(), getPeopleOrganizations: vi.fn(), getPeopleRoles: vi.fn() }))
const wrappers: ReturnType<typeof mount>[] = []
const person = { id: 'User:actual-fixture', record_id: 'actual-fixture', display_id: 'actual-fixture', name: '接口返回人员', phone: '138****1234', department: '', position: '', active: true, account_linked: true, role_profile: '' }
async function open(path = '/hbos/admin/people') {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/hbos/admin/people', name: 'admin-people', component: PeopleAccessView },
    { path: '/hbos/admin/roles', name: 'admin-roles', component: PeopleAccessView },
  ] })
  await router.push(path)
  const wrapper = mount(PeopleAccessView, { global: { plugins: [router], stubs: { 'a-modal': { template: '<div><slot /></div>' }, 'a-pagination': true } } }); wrappers.push(wrapper)
  await flushPromises()
  return { wrapper, router }
}
beforeEach(() => {
  vi.mocked(getManagementContext).mockRejectedValue({ code: 'NOT_SUPPORTED' })
  vi.mocked(getPeople).mockResolvedValue({ items: [person], total: 1, source: 'User', read_only: true, position_authorization_connected: false, authorization_domain: 'native_personnel', management_policy_applied: false })
  vi.mocked(getPeopleOrganizations).mockResolvedValue({ items: [], truncated: false, read_only: true, authorization_domain: 'native_personnel', management_policy_applied: false })
  vi.mocked(getPeopleRoles).mockResolvedValue({ items: [{ id: 'native', name: 'Native Role', created_at: '2026-10-01', description: '原生角色' }], total: 1, read_only: true, position_authorization_connected: false, authorization_domain: 'native_personnel', management_policy_applied: false })
})
afterEach(() => { wrappers.splice(0).forEach(w => w.unmount()); vi.clearAllMocks() })
describe('5178 人员权限真实只读页面', () => {
  it('只显示接口资料和指定七列，所有尚未接入的写操作禁用', async () => {
    const { wrapper } = await open()
    expect(wrapper.findAll('th').map(th => th.text())).toEqual(['ID', '人员名称', '部门', '岗位', '手机号', '角色', '操作'])
    expect(wrapper.text()).toContain('接口返回人员')
    expect(wrapper.text()).toContain('138****1234')
    expect(wrapper.text()).not.toContain('张明')
    expect(wrapper.text()).not.toContain('演示模式')
    expect(wrapper.find('input[aria-label="手机号筛选"]').exists()).toBe(false)
    for (const text of ['新增人员', '编辑']) expect(wrapper.findAll('button').find(b => b.text().includes(text))?.attributes('disabled')).toBeDefined()
  })
  it('搜索发送后端分页和过滤参数，不在浏览器加载全员再筛选', async () => {
    const { wrapper } = await open()
    await wrapper.get('input[aria-label="人员名称筛选"]').setValue('指定姓名')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(getPeople).toHaveBeenLastCalledWith({ source: 'User', page: 1, page_size: 10, name: '指定姓名', department: '', position: '' })
  })
  it('原生权限拒绝清空旧结果，显示错误，保持真实空状态', async () => {
    const { wrapper } = await open()
    vi.mocked(getPeople).mockRejectedValue(new Error('没有资料查看权限'))
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.text()).not.toContain('接口返回人员')
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('人员资料暂不可用')
  })
  it('切换员工来源后显式查询 Employee，不把账号资料伪装成员工', async () => {
    const { wrapper } = await open()
    await wrapper.get('select[aria-label="资料来源"]').setValue('Employee'); await flushPromises()
    expect(getPeople).toHaveBeenLastCalledWith(expect.objectContaining({ source: 'Employee', department: '', position: '' }))
  })
  it('角色页只显示原生查询结果，不开放角色或岗位写入', async () => {
    const { wrapper } = await open('/hbos/admin/roles')
    expect(wrapper.text()).toContain('Native Role')
    expect(getPeople).not.toHaveBeenCalled()
    for (const text of ['添加角色', '编辑', '关联岗位', '删除']) expect(wrapper.findAll('button').find(b => b.text().includes(text))?.attributes('disabled')).toBeDefined()
  })
  it('账号详情不推断员工身份，员工详情通过稳定Employee标识查询任职', async () => {
    const { wrapper } = await open()
    await wrapper.findAll('button').find(b => b.text() === '详情')!.trigger('click'); await flushPromises()
    expect(getManagementContext).not.toHaveBeenCalled()
    vi.mocked(getPeople).mockResolvedValue({ items: [{ ...person, id: 'Employee:EMP-A', record_id: 'EMP-A', display_id: 'EMP-A' }], total: 1, source: 'Employee', read_only: true, position_authorization_connected: false, authorization_domain: 'native_personnel', management_policy_applied: false })
    await wrapper.get('select[aria-label="资料来源"]').setValue('Employee'); await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === '详情')!.trigger('click'); await flushPromises()
    expect(getManagementContext).toHaveBeenCalledOnce()
  })
  it('过期的请求结果不能覆盖切换页面后的资料', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof getPeople>>) => void
    vi.mocked(getPeople).mockReturnValue(new Promise(done => { resolve = done }))
    const { wrapper, router } = await open()
    await router.push('/hbos/admin/roles'); await flushPromises()
    resolve({ items: [person], total: 1, source: 'User', read_only: true, position_authorization_connected: false, authorization_domain: 'native_personnel', management_policy_applied: false }); await flushPromises()
    expect(wrapper.text()).toContain('Native Role')
    expect(wrapper.text()).not.toContain('接口返回人员')
  })
})
