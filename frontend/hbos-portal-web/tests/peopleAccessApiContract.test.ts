import { beforeEach, describe, expect, it, vi } from 'vitest'
import { callFrappeMethod } from '@/services/frappeClient'
import { getPeople, getPeopleOrganizations, getPeopleRoles, type PeopleQuery } from '@/services/peopleAccessApi'

vi.mock('@/services/frappeClient', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/frappeClient')>(), callFrappeMethod: vi.fn(),
}))
const flags = { read_only: true, authorization_domain: 'native_personnel', management_policy_applied: false }
const query: PeopleQuery = { source: 'User', page: 1, page_size: 10, name: '', department: '', position: '' }
const person = { id: 'User:USER-001', record_id: 'USER-001', display_id: 'USER-001', name: '原生账号', phone: '138****0000', department: '', position: '', active: true, account_linked: true, role_profile: '' }
const people = { ...flags, items: [person], total: 1, source: 'User', position_authorization_connected: false }
const role = { id: 'Role-1', name: '原生角色', created_at: '2026-10-01', description: '现有 Frappe 角色' }
const roles = { ...flags, items: [role], total: 1, position_authorization_connected: false }
const organizations = { ...flags, items: [{ id: '部门甲', name: '部门甲', parent_id: null }], truncated: false }
function returns(value: unknown) { vi.mocked(callFrappeMethod).mockResolvedValue({ ok: true, data: value }) }
beforeEach(() => vi.clearAllMocks())

describe('原生人员目录显式来源与筛选契约', () => {
  it('目录只传输六个已知参数，响应明确未应用管理政策', async () => {
    returns(people)
    await expect(getPeople(query)).resolves.toEqual(people)
    expect(callFrappeMethod).toHaveBeenCalledExactlyOnceWith('hbos_portal.api.people_access.get_people', query)
  })
  it('组织树和角色均保留原生权限标识，不被伪装成岗位授权', async () => {
    returns(organizations)
    await expect(getPeopleOrganizations()).resolves.toEqual(organizations)
    expect(callFrappeMethod).toHaveBeenLastCalledWith('hbos_portal.api.people_access.get_organizations', undefined)
    returns(roles)
    await expect(getPeopleRoles(1, 10, ' 原生 ')).resolves.toEqual(roles)
    expect(callFrappeMethod).toHaveBeenLastCalledWith('hbos_portal.api.people_access.get_roles', { page: 1, page_size: 10, name: '原生' })
  })
  it.each(['phone', 'user_id', 'doctype', 'fields', 'order_by', 'filters', 'ignore_permissions'])('运行时注入 %s 在请求之前拒绝，包括空手机号', async key => {
    await expect(getPeople({ ...query, [key]: '' } as PeopleQuery)).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    expect(callFrappeMethod).not.toHaveBeenCalled()
  })
  it('账号资料不能带部门岗位筛选，参数类型和范围必须符合后端', async () => {
    for (const extra of [{ department: '部门甲' }, { position: '岗位甲' }, { page: '1' }, { page_size: 51 }, { name: 'a'.repeat(101) }]) {
      await expect(getPeople({ ...query, ...extra } as PeopleQuery)).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    }
    expect(callFrappeMethod).not.toHaveBeenCalled()
  })
  it('原生权限拒绝传播，客户端不重试管理员、管理或演示入口', async () => {
    vi.mocked(callFrappeMethod).mockResolvedValue({ ok: false, error: { code: 'FORBIDDEN', message: '目录无权' } })
    await expect(getPeople(query)).rejects.toMatchObject({ code: 'FORBIDDEN', message: '目录无权' })
    expect(callFrappeMethod).toHaveBeenCalledTimes(1)
  })
  it('信封成功状态必须为布尔值，错误信封不得含可显示的旧数据', async () => {
    for (const envelope of [{ ok: 1, data: people }, { ok: false, error: { code: 'FORBIDDEN', message: '拒绝' }, data: people }]) {
      vi.mocked(callFrappeMethod).mockResolvedValue(envelope)
      await expect(getPeople(query)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
  })
  it.each([{ authorization_domain: 'management_policy' }, { management_policy_applied: true }, { read_only: false }, { position_authorization_connected: true }])('错误权限领域或生效声明拒绝：%j', async extra => {
    returns({ ...people, ...extra })
    await expect(getPeople(query)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it('字段缺失和旧响应不能默认为原生领域', async () => {
    const { authorization_domain: _domain, ...oldPeople } = people
    void _domain
    for (const call of [() => getPeople(query), () => getPeopleRoles(1, 10, '')]) {
      returns(oldPeople)
      await expect(call()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
    returns({ items: [], truncated: false })
    await expect(getPeopleOrganizations()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it('人员原始手机号、敏感额外字段、来源替换与不合理分页拒绝', async () => {
    for (const value of [
      { ...people, items: [{ ...person, phone: '13800000000' }] },
      { ...people, items: [{ ...person, subject_user: 'private' }] },
      { ...people, source: 'Employee' },
      { ...people, items: [{ ...person, id: 'Employee:USER-001' }] },
      { ...people, total: 0 },
    ]) {
      returns(value)
      await expect(getPeople(query)).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
  })
  it('未关联员工资料保留 Employee 来源，角色映射仍仅为原生显示', async () => {
    const employee = { ...person, id: 'Employee:EMP-001', record_id: 'EMP-001', display_id: '工号001', phone: '', account_linked: false, department: '部门甲', position: '岗位甲', role_profile: '' }
    returns({ ...people, source: 'Employee', items: [employee] })
    await expect(getPeople({ ...query, source: 'Employee', department: '部门甲' })).resolves.toMatchObject({ source: 'Employee', authorization_domain: 'native_personnel', management_policy_applied: false, items: [employee] })
  })
})
