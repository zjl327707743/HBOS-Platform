import { beforeEach, describe, expect, it, vi } from 'vitest'
import { callFrappeMethod } from '@/services/frappeClient'
import {
  getManagementContext, getManagedPersonAssignments, listManagedPositions, lookupManagedPeople,
  type ManagementAssignmentQuery, type ManagementListQuery,
} from '@/services/organizationManagementApi'

vi.mock('@/services/frappeClient', async importOriginal => ({
  ...await importOriginal<typeof import('@/services/frappeClient')>(), callFrappeMethod: vi.fn(),
}))
const flags = { read_only: true, runtime_verified: false, authorization_effect: 'none', position_authorization_connected: false }
const position = { record_id: '00000000-0000-0000-0000-000000000001', title: '限定岗位', company_id: '公司甲', department_id: '部门甲', designation_id: null, status: 'active', revision: 2 }
const assignment = { record_id: '00000000-0000-0000-0000-000000000002', position_id: position.record_id, person_source_id: 'EMP-001', status: 'inactive', is_primary: false, valid_from_utc: '2026-10-01T00:00:00+00:00', valid_until_utc: null, revision: 1 }
const person = { source_id: 'EMP-001', display_name: '接口姓名', company_id: '公司甲', department_id: '部门甲', designation_id: null, link_status: 'unlinked', employee_status: 'Left' }
const context = { ...flags, operation_ids: ['hbos.organization.position.read', 'hbos.organization.assignment.read'], scopes: [
  { operation_id: 'hbos.organization.position.read', operation_schema_version: 1, company_id: '公司甲', target_department_ids: ['部门甲'], include_children: false, person_scope: null },
  { operation_id: 'hbos.organization.assignment.read', operation_schema_version: 1, company_id: '公司甲', target_department_ids: ['部门甲'], include_children: false, person_scope: { source_type: 'Employee', company_id: '公司甲', department_ids: ['部门乙'] } },
] }
const page = (item?: unknown, extra: Record<string, unknown> = {}) => ({ ...flags, items: item ? [item] : [], total: item ? 1 : 0, page: 1, page_size: 10, ...extra })
function returns(value: unknown) { vi.mocked(callFrappeMethod).mockResolvedValue({ ok: true, data: value }) }
beforeEach(() => vi.clearAllMocks())

describe('固定管理 GET 最小只读契约', () => {
  it('管理上下文仅通过精确方法与必需 CSRF 选项读取，完整保留逐条范围', async () => {
    returns(context)
    await expect(getManagementContext()).resolves.toEqual(context)
    expect(callFrappeMethod).toHaveBeenCalledExactlyOnceWith('hbos_portal.api.organization_relations.get_management_context', undefined, { requireCsrf: true })
  })
  it('岗位查询发送明确分页和字面筛选字段，响应保留最小事实投影', async () => {
    returns(page(position))
    await expect(listManagedPositions({ q: ' %_ ', company_id: ' 公司甲 ', department_id: '部门甲' })).resolves.toEqual(page(position))
    expect(callFrappeMethod).toHaveBeenCalledExactlyOnceWith('hbos_portal.api.organization_relations.list_positions', { page: 1, page_size: 10, company_id: '公司甲', department_id: '部门甲', q: '%_' }, { requireCsrf: true })
  })
  it('任职只使用 Employee ID 和分页，不将用户、手机号或角色当作身份', async () => {
    returns(page(assignment))
    await expect(getManagedPersonAssignments({ employee_id: ' EMP-001 ' })).resolves.toEqual(page(assignment))
    expect(callFrappeMethod).toHaveBeenCalledExactlyOnceWith('hbos_portal.api.organization_relations.get_person_assignments', { employee_id: 'EMP-001', page: 1, page_size: 10 }, { requireCsrf: true })
  })
  it('姓名查找包含来源关联状态，离职事实可读仍明确没有授权效果', async () => {
    returns(page(person))
    await expect(lookupManagedPeople()).resolves.toEqual(page(person))
    expect(callFrappeMethod).toHaveBeenCalledExactlyOnceWith('hbos_portal.api.organization_relations.lookup_people', { page: 1, page_size: 10, company_id: '', department_id: '', q: '' }, { requireCsrf: true })
  })
  it.each(['phone', 'user_id', 'doctype', 'fields', 'order_by', 'include_children', 'filters'])('列表参数拒绝运行时注入 %s，发送前失败', async key => {
    await expect(listManagedPositions({ [key]: '' } as ManagementListQuery)).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    await expect(lookupManagedPeople({ [key]: '' } as ManagementListQuery)).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    expect(callFrappeMethod).not.toHaveBeenCalled()
  })
  it.each([{ page: 0 }, { page: 10001 }, { page: '1' }, { page_size: 51 }, { page_size: true }, { page: null }, { q: null }, { q: 'a'.repeat(81) }, { department_id: 'a\n' }])('无效范围参数在请求前拒绝：%j', async query => {
    await expect(listManagedPositions(query as ManagementListQuery)).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    expect(callFrappeMethod).not.toHaveBeenCalled()
  })
  it('任职额外字段、空身份和数组参数全部拒绝', async () => {
    for (const query of [{ employee_id: '' }, { employee_id: 'EMP-001', user_id: 'User-1' }, []]) {
      await expect(getManagedPersonAssignments(query as ManagementAssignmentQuery)).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    }
    expect(callFrappeMethod).not.toHaveBeenCalled()
  })
  it.each(['NOT_SUPPORTED', 'MANAGEMENT_DENIED', 'CONFLICT', 'SOURCE_UNAVAILABLE'])('保留 %s，失败后没有原生查询或演示回退', async code => {
    vi.mocked(callFrappeMethod).mockResolvedValue({ ok: false, error: { code, message: '明确拒绝' } })
    await expect(listManagedPositions()).rejects.toMatchObject({ code, message: '明确拒绝' })
    expect(callFrappeMethod).toHaveBeenCalledTimes(1)
  })
  it('拒绝不明确的成功标志、混入错误数据和不完整错误信封', async () => {
    for (const envelope of [{ ok: 'true', data: page(position) }, { ok: true, data: page(position), error: { code: 'FORBIDDEN' } }, { ok: false, error: { message: '缺少错误代码' } }]) {
      vi.mocked(callFrappeMethod).mockResolvedValue(envelope)
      await expect(listManagedPositions()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
  })
  it.each([{ read_only: false }, { runtime_verified: true }, { authorization_effect: 'grant' }, { position_authorization_connected: true }])('拒绝声称可写或授权已生效的响应：%j', async extra => {
    returns(page(position, extra))
    await expect(listManagedPositions()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it.each([{ page: 2 }, { page_size: 20 }, { total: -1 }, { total: '1' }, { total: 2 }, { items: [] }])('页码、总数或结果数量不一致时拒绝：%j', async extra => {
    returns(page(position, extra))
    await expect(listManagedPositions()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it('正常空页与边界分页可读，返回字段不含授权推断', async () => {
    returns(page(undefined, { page: 10000, page_size: 50 }))
    await expect(listManagedPositions({ page: 10000, page_size: 50 })).resolves.toMatchObject({ items: [], total: 0, page: 10000, page_size: 50, authorization_effect: 'none' })
  })
  it('岗位、任职、人员和上下文额外敏感字段全部拒绝', async () => {
    for (const [call, value] of [
      [() => listManagedPositions(), page({ ...position, policy_ref: 'private' })],
      [() => getManagedPersonAssignments({ employee_id: 'EMP-001' }), page({ ...assignment, subject_user: 'private' })],
      [() => lookupManagedPeople(), page({ ...person, phone: '13800000000' })],
      [() => getManagementContext(), { ...context, approval_ref: 'private' }],
    ] as const) {
      returns(value)
      await expect(call()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
  })
  it('缺失字段、坏修订、未知事实状态和重复记录不能进入 UI', async () => {
    const { designation_id: _designation, ...incomplete } = position
    void _designation
    for (const value of [page(incomplete), page({ ...position, revision: 0 }), page({ ...position, status: 'ended' }), page(position, { items: [position, position], total: 2 })]) {
      returns(value)
      await expect(listManagedPositions()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
  })
  it('任职查询不接受另一人员、非 UTC 或倒置期限', async () => {
    for (const value of [
      { ...assignment, person_source_id: 'EMP-OTHER' },
      { ...assignment, valid_from_utc: '2026-10-01T00:00:00+08:00' },
      { ...assignment, valid_from_utc: '2026-02-30T00:00:00+00:00' },
      { ...assignment, valid_until_utc: assignment.valid_from_utc },
    ]) {
      returns(page(value))
      await expect(getManagedPersonAssignments({ employee_id: 'EMP-001' })).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
  })
  it('保留后端 UTC 微秒期限，不将有效的一微秒任职错误当作空区间', async () => {
    const value = { ...assignment, valid_from_utc: '2026-10-01T00:00:00.000001+00:00', valid_until_utc: '2026-10-01T00:00:00.000002+00:00' }
    returns(page(value))
    await expect(getManagedPersonAssignments({ employee_id: 'EMP-001' })).resolves.toMatchObject({ items: [value] })
  })
  it('上下文拒绝未知操作、跨公司人员范围、自动包含下级和操作范围不完整', async () => {
    for (const value of [
      { ...context, operation_ids: ['hbos.organization.position.write'] },
      { ...context, scopes: [{ ...context.scopes[0], include_children: true }] },
      { ...context, scopes: [{ ...context.scopes[1], person_scope: { source_type: 'Employee', company_id: '其他公司', department_ids: ['部门乙'] } }] },
      { ...context, scopes: [] },
    ]) {
      returns(value)
      await expect(getManagementContext()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    }
  })
})
