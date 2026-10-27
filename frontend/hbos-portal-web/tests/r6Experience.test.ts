import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, DOMWrapper, type VueWrapper } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import Antd from 'ant-design-vue'
import Roles from '@/views/admin/RolesAdminView.vue'
import Profile from '@/views/ProfileSettingsView.vue'
import People from '@/views/admin/PeopleAdminView.vue'
import { roleFeatureKey, roleScopeLabel, sameRoleFeatures } from '@/services/rolePresentation'
import type { AppRole } from '@/services/iamRoles'
const api = vi.hoisted(() => ({ loadRoles: vi.fn(), roleCommand: vi.fn(), getMyEmployeeStatus: vi.fn(), listPeople: vi.fn(), getEmployeeMetadata: vi.fn(), createEmployee: vi.fn() }))
const actor = vi.hoisted(() => ({ id: 'hr@example.test', displayName: '合成人事管理员', avatarText: '合', roleLabel: '人事管理员' }))
const permissions = vi.hoisted(() => new Set<string>())
vi.mock('@/services/iamRoles', () => ({ loadRoles: api.loadRoles, roleCommand: api.roleCommand, assertRolePreview: (value: unknown) => value }))
vi.mock('@/services/iamAccount', () => ({ getMyEmployeeStatus: api.getMyEmployeeStatus }))
vi.mock('@/services/iamPeople', () => ({ listPeople: api.listPeople, getEmployeeMetadata: api.getEmployeeMetadata, createEmployee: api.createEmployee }))
vi.mock('@/stores/portal', () => ({ usePortalStore: () => ({ user: actor, apps: [] }) }))
vi.mock('@/services/iamAccess', () => ({ canIam: (cap: string) => permissions.has(cap), hasManagementAccess: () => true, iamMessage: (error: Error) => error.message }))
const Verify = defineComponent({ emits: ['verified', 'invalidated'], template: '<button class="verify-test" @click="$emit(\'verified\', {valid:true,expires_in:120,method:\'password\'})">完成测试核验</button>' })
const self = { operation_id: 'attendance.read', scope_binding: 'SELF' }
const board = { operation_id: 'attendance.department.board.read', scope_binding: 'RESPONSIBLE_DEPARTMENTS' }
const baseRole: AppRole = { id: 'role-clerk', app_id: 'attendance', role_key: 'clerk', title: '部门考勤员', boundary_kind: 'DEPARTMENT', draft_version: 4, draft_features: [self, board], published_release: 'release-3', published_revision: 3, published_features: [self], releases: [], registry: [{ ...self, title: '查看自己的考勤', group: 'self', allowed: true, integrated: true, reason: '' }, { ...board, title: '查看部门考勤面板', group: 'board', allowed: true, integrated: true, reason: '' }] }
let wrappers: VueWrapper[] = []
async function render(component: object, path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
  await router.push(path); await router.isReady()
  const wrapper = mount(component, { attachTo: document.body, global: { plugins: [Antd, router], stubs: { OwnAccountVerification: Verify, AccountSecurity: true, AppDiagnostics: true, EmployeeDrawer: true } } })
  wrappers.push(wrapper); await flushPromises(); return wrapper
}
function action(w: VueWrapper, text: string) {
  const modal = [...document.querySelectorAll<HTMLElement>('.ant-modal-wrap')].reverse().find(item => item.style.display !== 'none')
  const native = modal ? [...modal.querySelectorAll('button')].find(item => item.textContent?.includes(text)) : undefined
  return native ? new DOMWrapper(native) : w.findAll('button').find(item => item.text().includes(text))
}
async function click(w: VueWrapper, text: string) {
  await vi.waitFor(() => expect(action(w, text), text).toBeDefined())
  await action(w, text)!.trigger('click'); await flushPromises()
}
beforeEach(() => {
  vi.resetAllMocks(); permissions.clear(); permissions.add('iam.roles.read'); permissions.add('iam.roles.edit'); permissions.add('iam.roles.publish')
  actor.id = 'hr@example.test'; api.loadRoles.mockResolvedValue([structuredClone(baseRole)])
  api.getMyEmployeeStatus.mockResolvedValue({ status: 'linked', employee_id: 'EMP-1', employee_number: 'T001', department: '合成人事部', position: '合成人事主管' })
  api.listPeople.mockResolvedValue({ items: [{ id: 'EMP-1', name: '合成测试员工', employee_number: 'T001', department: 'D1', department_name: '合成部门', position: '测试岗位', account_status: 'unopened', attendance_status: 'pending', user_id: null }], total: 57, page: 1, page_size: 20 })
  api.getEmployeeMetadata.mockResolvedValue({ version: 'meta-1', required_fields: [], companies: [], departments: [{ value: 'D1', label: '合成部门', company: 'C1' }], genders: [] })
})
afterEach(() => { wrappers.forEach(w => w.unmount()); wrappers = []; document.body.innerHTML = '' })
describe('R6 formal data and role contracts', () => {
  it('uses complete operation/scope pairs, including real server responsibility bindings', () => {
    expect(roleFeatureKey(board)).not.toBe(roleFeatureKey({ ...board, scope_binding: 'RESPONSIBLE_COMPANIES' }))
    expect(sameRoleFeatures([self, board], [board, self])).toBe(true)
    expect(sameRoleFeatures([board], [{ ...board, scope_binding: 'SELF' }])).toBe(false)
    expect(roleScopeLabel(board.scope_binding)).toContain('不包含下级')
  })
  it('reads the published release by default and shows draft features only in draft view', async () => {
    const w = await render(Roles, '/hbos/admin/roles')
    expect(w.findAll('.r6-feature-read').map(row => row.text())).toEqual(expect.arrayContaining(['查看自己的考勤已启用', '查看部门考勤面板未启用']))
    expect(w.find('input[type=checkbox]').exists()).toBe(false)
    await click(w, '待发布修改')
    expect(w.findAll('.r6-feature-read').find(row => row.text().includes('部门'))!.text()).toContain('已启用')
    expect(api.roleCommand).not.toHaveBeenCalled()
  })
  it('retains an unsaved role draft across cached route changes and requires fresh proof on return', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path: '/roles', component: Roles },
      { path: '/other', component: defineComponent({ template: '<p>其他工作</p>' }) },
    ] })
    await router.push('/roles'); await router.isReady()
    const Root = defineComponent({ template: '<RouterView v-slot="{ Component }"><KeepAlive><component :is="Component" /></KeepAlive></RouterView>' })
    const w = mount(Root, { attachTo: document.body, global: { plugins: [Antd, router], stubs: { OwnAccountVerification: Verify } } })
    wrappers.push(w); await flushPromises()
    await click(w, '编辑功能'); await w.findAll('input[type=checkbox]')[0]!.setValue(false)
    await w.get('input[aria-label="搜索角色功能"]').setValue('查看')
    await click(w, '保存草稿'); await click(w, '完成测试核验')
    expect(action(w, '确认保存草稿')!.attributes('disabled')).toBeUndefined()
    await router.push('/other'); await flushPromises(); expect(w.text()).toContain('其他工作')
    await router.push('/roles'); await flushPromises()
    expect((w.findAll('input[type=checkbox]')[0]!.element as HTMLInputElement).checked).toBe(false)
    expect((w.get('input[aria-label="搜索角色功能"]').element as HTMLInputElement).value).toBe('查看')
    await click(w, '保存草稿')
    expect(action(w, '确认保存草稿')!.attributes('disabled')).toBeDefined()
    expect(api.loadRoles).toHaveBeenCalledTimes(1)
    expect(api.roleCommand).not.toHaveBeenCalled()
  })
  it('saves only registered selected pairs with the current draft version, without publishing', async () => {
    const w = await render(Roles, '/hbos/admin/roles'); await click(w, '编辑功能')
    await w.findAll('input[type=checkbox]')[0]!.setValue(false); await click(w, '保存草稿'); await click(w, '完成测试核验'); await click(w, '确认保存草稿')
    expect(api.roleCommand).toHaveBeenCalledExactlyOnceWith('save_role_draft', { role_key: 'clerk', expected_draft_version: 4, features: [board], request_id: expect.any(String) })
  })
  it.each([409, 500])('preserves draft and requires a read plus new proof after a %i write failure', async status => {
    api.roleCommand.mockRejectedValueOnce(Object.assign(new Error('需核对服务端结果'), { status }))
    const w = await render(Roles, '/hbos/admin/roles'); await click(w, '编辑功能'); await w.findAll('input[type=checkbox]')[0]!.setValue(false); await click(w, '保存草稿'); await click(w, '完成测试核验'); await click(w, '确认保存草稿')
    expect((w.findAll('input[type=checkbox]')[0]!.element as HTMLInputElement).checked).toBe(false)
    expect(w.findAll('button').find(item => item.text() === '保存草稿')!.attributes('disabled')).toBeDefined()
    await click(w, '核对最新结果'); expect((w.findAll('input[type=checkbox]')[0]!.element as HTMLInputElement).checked).toBe(false)
    await click(w, '保存草稿')
    expect(action(w, '确认保存草稿')!.attributes('disabled')).toBeDefined()
    expect(api.roleCommand).toHaveBeenCalledTimes(1)
  })
  it('publishes only after server preview, using the exact release, context and draft version', async () => {
    const context = 'a'.repeat(64); api.roleCommand.mockResolvedValueOnce({ changed: true, context_revision: context, reference_count: 2, effective_changed_count: 1, members: [] }).mockResolvedValueOnce({})
    const w = await render(Roles, '/hbos/admin/roles'); await click(w, '核对发布影响'); expect(w.findComponent({name:'ChangeReview'}).props('open')).toBe(true); await new Promise(resolve => setTimeout(resolve, 80)); await flushPromises(); const button = Array.from(document.body.querySelectorAll('button')).find(item => item.textContent?.trim() === '确认发布')!; expect(button).toBeDefined(); expect(button.disabled).toBe(true); await click(w, '完成测试核验'); await click(w, '确认发布')
    expect(api.roleCommand).toHaveBeenNthCalledWith(2, 'publish_role', { role_key: 'clerk', expected_draft_version: 4, expected_release: 'release-3', context_revision: context, request_id: expect.any(String) })
  })
  it('hides editing and publishing actions for a read-only role viewer', async () => {
    permissions.delete('iam.roles.edit'); permissions.delete('iam.roles.publish'); const w = await render(Roles, '/hbos/admin/roles'); expect(w.text()).not.toContain('编辑功能'); expect(w.findAll('button').some(button => button.text().includes('核对发布影响'))).toBe(false); expect(w.find('input[type=checkbox]').exists()).toBe(false)
  })
  it('treats only the built-in Administrator as Employee not applicable', async () => {
    const hr = await render(Profile, '/hbos/profile'); expect(hr.text()).toContain('合成人事部'); expect(hr.text()).toContain('T001'); expect(hr.text()).toContain('合成人事主管'); expect(hr.text()).not.toContain('员工档案不适用')
    actor.id = 'Administrator'; const admin = await render(Profile, '/hbos/profile'); expect(admin.text()).toContain('员工档案不适用'); expect(api.getMyEmployeeStatus).toHaveBeenCalledTimes(1)
  })
  it('does not present a missing/conflicted Employee as linked or fabricate a position', async () => {
    api.getMyEmployeeStatus.mockResolvedValue({ status: 'conflict' }); const w = await render(Profile, '/hbos/profile'); expect(w.text()).toContain('员工归属存在冲突'); expect(w.text()).not.toContain('员工档案已关联'); expect(w.text()).toContain('待核对')
  })
  it('shows server total independently from current-page todo counts', async () => {
    const w = await render(People, '/hbos/admin/people'); const cards = w.findAll('.r6-overview'); expect(cards[0]!.text()).toContain('57'); expect(cards[1]!.text()).toContain('本页待开通账号1'); expect(cards[2]!.text()).toContain('本页待核对关联1'); expect(api.listPeople).toHaveBeenCalledWith(expect.objectContaining({ page: 1, page_size: 20, category: 'employees', view_group: 'daily' }))
  })
  it('keeps pagination bounded while loading or empty and accepts a real second page', async () => {
    let resolve!: (value: unknown) => void
    api.listPeople.mockReturnValueOnce(new Promise(done => { resolve = done }))
    const w = await render(People, '/hbos/admin/people')
    const pager = w.findComponent({ name: 'APagination' })
    expect(pager.props('disabled')).toBe(true)
    pager.vm.$emit('change', 0); await flushPromises()
    expect(api.listPeople).toHaveBeenCalledTimes(1)
    resolve({ items: [], total: 27, page: 1, page_size: 20 }); await flushPromises()
    expect(pager.props('disabled')).toBe(false)
    for (const invalid of [0, -1, 1.5, 3]) pager.vm.$emit('change', invalid)
    await flushPromises(); expect(api.listPeople).toHaveBeenCalledTimes(1)
    pager.vm.$emit('change', 2); await flushPromises()
    expect(api.listPeople).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }))
    api.listPeople.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 20 })
    await w.get('input[aria-label="搜索人员"]').setValue('不存在的合成员工')
    await new Promise(done => setTimeout(done, 320)); await flushPromises()
    expect(pager.props('current')).toBe(1); expect(pager.props('disabled')).toBe(true)
    const count = api.listPeople.mock.calls.length
    pager.vm.$emit('change', 0); await flushPromises()
    expect(api.listPeople).toHaveBeenCalledTimes(count)
  })
  it('does not replace the current employee group metadata with a late response for the previous group', async () => {
    let finishDaily!: (value: unknown) => void, finishTechnical!: (value: unknown) => void
    api.getEmployeeMetadata.mockReturnValueOnce(new Promise(resolve => { finishDaily = resolve }))
      .mockReturnValueOnce(new Promise(resolve => { finishTechnical = resolve }))
    api.listPeople.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, groups_available: true })
    const w = await render(People, '/hbos/admin/people')
    const group = w.findAllComponents({ name: 'ASelect' }).find(item => item.attributes('aria-label') === '员工分组')!
    expect(group.exists()).toBe(true)
    group.vm.$emit('update:value', 'technical'); await flushPromises()
    finishTechnical({ version: 'technical', companies: [], genders: [], required_fields: [], departments: [{ value: 'TECH', label: '当前分组部门', company: 'C1' }] })
    await flushPromises()
    finishDaily({ version: 'daily', companies: [], genders: [], required_fields: [], departments: [{ value: 'OLD', label: '旧分组部门', company: 'C1' }] })
    await flushPromises()
    const department = w.findAllComponents({ name: 'ASelect' }).find(item => item.attributes('aria-label') === '筛选部门')!
    expect(department.props('options')).toEqual([{ value: 'TECH', label: '当前分组部门 · C1' }])
  })
  it('uses a new submission identity when a rechecked employee draft changes, while preserving its original uncertain request', async () => {
    permissions.add('iam.people.create')
    api.getEmployeeMetadata.mockResolvedValue({ version: 'meta-1', required_fields: [],
      companies: [{ value: 'C1', label: '公司甲' }], departments: [{ value: 'D1', label: '部门甲', company: 'C1' }], genders: [{ value: 'Female', label: '女' }] })
    api.createEmployee.mockRejectedValue(Object.assign(new Error('提交结果待核对'), { status: 500 }))
    const w = await render(People, '/hbos/admin/people'); await click(w, '新增员工档案')
    const item = (label: string) => w.findAllComponents({ name: 'AFormItem' }).find(row => row.props('label') === label)!
    for (const [label, value] of [['公司', 'C1'], ['主部门', 'D1'], ['性别', 'Female']]) {
      item(label!).findComponent({ name: 'ASelect' }).vm.$emit('update:value', value); await flushPromises()
    }
    for (const [label, value] of [['姓名', '合成建档一'], ['工号', 'CREATE-01'], ['出生日期', '1990-01-01'], ['入职日期', '2026-10-01']]) await item(label!).get('input').setValue(value)
    await click(w, '完成测试核验')
    await new DOMWrapper(document.querySelector('.ant-modal form')!).trigger('submit'); await flushPromises()
    expect(api.createEmployee).toHaveBeenCalledTimes(1)
    const firstId = api.createEmployee.mock.calls[0]![2]
    await click(w, '核对最新结果'); await click(w, '完成测试核验')
    await new DOMWrapper(document.querySelector('.ant-modal form')!).trigger('submit'); await flushPromises()
    expect(api.createEmployee).toHaveBeenCalledTimes(2)
    expect(api.createEmployee.mock.calls[1]![2]).toBe(firstId)
    await click(w, '核对最新结果')
    await item('工号').get('input').setValue('CREATE-02')
    await click(w, '完成测试核验')
    await new DOMWrapper(document.querySelector('.ant-modal form')!).trigger('submit'); await flushPromises()
    expect(api.createEmployee).toHaveBeenCalledTimes(3)
    expect(api.createEmployee.mock.calls[2]![0]).toMatchObject({ employee_number: 'CREATE-02' })
    expect(api.createEmployee.mock.calls[2]![2]).not.toBe(firstId)
  })
  it('collects business employee fields with local labels while native creation owns its numbering series', async () => {
    permissions.add('iam.people.create')
    api.getEmployeeMetadata.mockResolvedValue({ version: 'meta-1', required_fields: [
      { fieldname: 'naming_series', label: 'Series', fieldtype: 'Select', options: 'HR-EMP-' },
      { fieldname: 'first_name', label: 'First Name', fieldtype: 'Data' },
      { fieldname: 'gender', label: 'Gender', fieldtype: 'Link' },
    ], companies: [], departments: [], genders: [] })
    const w = await render(People, '/hbos/admin/people'); await click(w, '新增员工档案')
    const labels = Array.from(document.querySelectorAll('.ant-modal label')).map(item => item.textContent)
    expect(labels).toContain('姓名'); expect(labels).toContain('工号'); expect(labels).toContain('性别')
    expect(labels).not.toContain('Series'); expect(labels).not.toContain('First Name')
    expect(api.roleCommand).not.toHaveBeenCalled()
  })
})
