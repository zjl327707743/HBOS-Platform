import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ManagedOrganizationReadOnly from '@/components/peopleAccess/ManagedOrganizationReadOnly.vue'
import { getManagementContext, getManagedPersonAssignments, listManagedPositions } from '@/services/organizationManagementApi'
vi.mock('@/services/organizationManagementApi', () => ({ getManagementContext: vi.fn(), listManagedPositions: vi.fn(), getManagedPersonAssignments: vi.fn() }))
const flags = { read_only: true, runtime_verified: false, authorization_effect: 'none', position_authorization_connected: false } as const
const position = { record_id: 'position-A', title: '获准岗位甲', company_id: 'CO-A', department_id: 'DEP-A', designation_id: 'TYPE-A', status: 'active', revision: 1 } as const
const assignment = { record_id: 'assignment-A', position_id: 'position-A', person_source_id: 'EMP-A', status: 'active', is_primary: true, valid_from_utc: '2026-10-01T00:00:00Z', valid_until_utc: '2026-10-30T00:00:00Z', revision: 1 } as const
const wrappers: ReturnType<typeof mount>[] = []
async function open(kind: 'positions' | 'assignments' = 'positions', employeeId?: string) {
  const wrapper = mount(ManagedOrganizationReadOnly, { props: { kind, employeeId }, global: { stubs: { 'a-pagination': { template: '<div data-testid="pagination">共 {{ total }} 条<button @click="$emit(\'update:current\', 2)">下一页</button></div>', props: ['total'] } } } })
  wrappers.push(wrapper); await flushPromises(); return wrapper
}
beforeEach(() => {
  vi.mocked(getManagementContext).mockResolvedValue({ operation_ids: ['hbos.organization.position.read', 'hbos.organization.assignment.read'], scopes: [], ...flags })
  vi.mocked(listManagedPositions).mockResolvedValue({ items: [position], total: 1, page: 1, page_size: 10, ...flags })
  vi.mocked(getManagedPersonAssignments).mockResolvedValue({ items: [assignment], total: 1, page: 1, page_size: 10, ...flags })
})
afterEach(() => { wrappers.splice(0).forEach(w => w.unmount()); vi.clearAllMocks() })
describe('真实岗位与任职只读接入', () => {
  it('queries context before positions and displays only authorized server results', async () => {
    const wrapper = await open()
    expect(vi.mocked(getManagementContext).mock.invocationCallOrder[0]).toBeLessThan(vi.mocked(listManagedPositions).mock.invocationCallOrder[0]!)
    expect(listManagedPositions).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    expect(wrapper.text()).toContain('获准岗位甲'); expect(wrapper.text()).toContain('共 1 条')
    expect(wrapper.findAll('button').some(b => /保存|新增|编辑|删除/.test(b.text()))).toBe(false)
  })
  it.each(['NOT_SUPPORTED', 'FORBIDDEN', 'SOURCE_UNAVAILABLE'])('handles %s without claiming an empty count or reading another domain', async code => {
    vi.mocked(getManagementContext).mockRejectedValue({ code })
    const wrapper = await open()
    expect(wrapper.find('[data-testid="pagination"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('共 0 条'); expect(wrapper.text()).not.toContain('暂无可查看')
    expect(wrapper.text()).toContain(code === 'NOT_SUPPORTED' ? '尚未启用' : code === 'FORBIDDEN' ? '没有查看' : '暂时无法读取')
    expect(listManagedPositions).not.toHaveBeenCalled(); expect(getManagedPersonAssignments).not.toHaveBeenCalled()
  })
  it('assignment read cannot substitute for position read', async () => {
    vi.mocked(getManagementContext).mockResolvedValue({ operation_ids: ['hbos.organization.assignment.read'], scopes: [], ...flags })
    const wrapper = await open(); expect(wrapper.text()).toContain('没有查看'); expect(listManagedPositions).not.toHaveBeenCalled()
  })
  it('queries exact Employee ID without deriving an identity or granting access', async () => {
    const wrapper = await open('assignments', 'EMP-A')
    expect(getManagedPersonAssignments).toHaveBeenCalledWith({ employee_id: 'EMP-A', page: 1, page_size: 10 })
    expect(listManagedPositions).not.toHaveBeenCalled(); expect(wrapper.text()).toContain('position-A')
  })
  it('missing Employee identity performs no query', async () => {
    const wrapper = await open('assignments'); expect(wrapper.text()).toContain('尚未关联员工资料'); expect(getManagementContext).not.toHaveBeenCalled()
  })
  it('refresh clears previous rows and counts on revoked read permission', async () => {
    const wrapper = await open(); vi.mocked(getManagementContext).mockRejectedValue({ code: 'FORBIDDEN' })
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.text()).not.toContain('获准岗位甲'); expect(wrapper.find('[data-testid="pagination"]').exists()).toBe(false)
  })
  it('search and paging stay server-side and do not load all records', async () => {
    const wrapper = await open(); await wrapper.get('input').setValue('指定岗位'); await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(listManagedPositions).toHaveBeenLastCalledWith({ page: 1, page_size: 10, q: '指定岗位' })
    await wrapper.get('[data-testid="pagination"] button').trigger('click'); await flushPromises()
    expect(listManagedPositions).toHaveBeenLastCalledWith({ page: 2, page_size: 10, q: '指定岗位' })
  })
  it('changing the target withholds a previous pending request', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof listManagedPositions>>) => void
    vi.mocked(listManagedPositions).mockReturnValueOnce(new Promise(done => { resolve = done }))
    const wrapper = await open(); await wrapper.setProps({ kind: 'assignments', employeeId: 'EMP-A' }); await flushPromises()
    resolve({ items: [position], total: 1, page: 1, page_size: 10, ...flags }); await flushPromises()
    expect(wrapper.text()).not.toContain('获准岗位甲'); expect(wrapper.text()).toContain('position-A')
  })
  it('unmount cancels a pending context before it can issue a data query', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof getManagementContext>>) => void
    vi.mocked(getManagementContext).mockReturnValueOnce(new Promise(done => { resolve = done }))
    const wrapper = await open(); wrapper.unmount()
    resolve({ operation_ids: ['hbos.organization.position.read'], scopes: [], ...flags }); await flushPromises()
    expect(listManagedPositions).not.toHaveBeenCalled()
  })
})
