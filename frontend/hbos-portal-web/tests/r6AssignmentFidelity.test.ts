import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { flushPromises, mount, DOMWrapper, type VueWrapper } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import Antd, { Modal } from 'ant-design-vue'
import RoleSettings from '@/components/iam/RoleSettings.vue'
import EmployeeDrawer from '@/components/iam/EmployeeDrawer.vue'
import DepartmentsAdminView from '@/views/admin/DepartmentsAdminView.vue'

const api = vi.hoisted(() => ({
  query: vi.fn(), command: vi.fn(), listDepartments: vi.fn(), getPerson: vi.fn(), getEmployeeMetadata: vi.fn(),
  getWorkSummary: vi.fn(), getWorkSubject: vi.fn(), previewLink: vi.fn(), linkUser: vi.fn(), createUser: vi.fn(),
  transferEmployee: vi.fn(), previewTransferEmployee: vi.fn(), disableUser: vi.fn(), resetTemporaryPassword: vi.fn(),
  getDepartmentWork: vi.fn(), previewWork: vi.fn(), workAction: vi.fn(),
}))
const caps = vi.hoisted(() => new Set<string>())
const session = vi.hoisted(() => ({ rolesEnabled: true }))
const proof = vi.hoisted(() => ({ valid: { value: false }, method: { value: 'password' as string | null } }))

vi.mock('@/services/iamRoles', () => ({
  roleQuery: api.query,
  roleCommand: api.command,
  assertRolePreview: (value: unknown) => value,
}))
vi.mock('@/services/iamDepartments', () => ({ listDepartments: api.listDepartments }))
vi.mock('@/services/iamAccess', () => ({
  canIam: (capability: string) => caps.has(capability),
  iamMessage: (error: Error) => error.message,
  iamSession: session,
}))
vi.mock('@/services/iamPeople', () => ({
  getPerson: api.getPerson, getEmployeeMetadata: api.getEmployeeMetadata,
  previewLink: api.previewLink, linkUser: api.linkUser, createUser: api.createUser,
  transferEmployee: api.transferEmployee, previewTransferEmployee: api.previewTransferEmployee,
  disableUser: api.disableUser, resetTemporaryPassword: api.resetTemporaryPassword,
}))
vi.mock('@/services/iamWork', async (importOriginal) => ({
  ...await importOriginal<object>(),
  getWorkSummary: api.getWorkSummary, getWorkSubject: api.getWorkSubject,
  getDepartmentWork: api.getDepartmentWork,
  getEffectiveWork: vi.fn(), previewAppSettings: vi.fn(), saveAppSettings: vi.fn(), previewWork: api.previewWork, workAction: api.workAction,
}))
vi.mock('@/composables/useAccountProof', async () => {
  const { ref } = await import('vue')
  proof.valid = ref(false) as unknown as { value: boolean }
  proof.method = ref('password') as unknown as { value: string | null }
  return {
    useAccountProof: () => ({
      valid: proof.valid, method: proof.method,
      sync: () => { proof.valid.value = true },
      invalidate: () => { proof.valid.value = false },
    }),
  }
})

const Verify = defineComponent({ emits: ['verified', 'invalidated'], template: '<button class="verify-test" type="button" @click="$emit(\'verified\', { valid: true, expires_in: 120, method: \'password\' })">完成测试核验</button>' })
const stubs = { RouterLink: { template: '<a><slot /></a>' }, AppUsageList: true, NativeAppRolePanel: true, WorkSettings: true }
const employeeAssignment = {
  version: 3, mode: 'FOLLOW_DEPARTMENT', role_key: 'staff', department: 'D1', company: 'C1', responsibilities: [],
  selected_role: { source_mode: 'department', source_ref: 'D1', reason: '', role_key: 'staff', published_revision: 2, title: '普通员工', responsibilities: [] },
  effective_access: { allowed: true, reason: '', operations: [{ operation_id: 'attendance.read', label: '查看自己的考勤', scope_type: 'SELF', scope_ref: '', allowed: true }] },
  roles: [{ role_key: 'staff', title: '普通员工', boundary_kind: 'SELF' }, { role_key: 'clerk', title: '部门考勤员', boundary_kind: 'DEPARTMENT' }, { role_key: 'admin', title: '考勤管理员', boundary_kind: 'COMPANY' }],
}
const previewAssignment = {
  context_revision: 'a'.repeat(64), changed: true,
  before: { allowed: true, reason: '', operations: [{ operation_id: 'attendance.read', label: '查看自己的考勤', scope_type: 'SELF', scope_ref: '', allowed: true }] },
  after: { allowed: true, reason: '', operations: [
    { operation_id: 'attendance.read', label: '查看自己的考勤', scope_type: 'SELF', scope_ref: '', allowed: true },
    { operation_id: 'attendance.department.board.read', label: '查看部门考勤面板', scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', allowed: true },
  ] },
}
const person = {
  employee: { id: 'E1', name: '合成员工', employee_number: 'T001', department: 'D1', department_name: '生产一部', company: 'C1', position: '操作员', user_id: null, account_status: 'unopened', attendance_status: 'pending', version: 'v1' },
  account: { user_id: null, username: '', feishu_bound: false, initial_password_pending: false }, association: { employee_id: 'E1', user_id: null }, history: [],
}
const attendanceWorkApp = (suspended = false) => ({
  app_id: 'attendance', title: '考勤管理', integrated: true, status: suspended ? '已临时禁用' : '可以使用',
  summary: '普通员工', source_text: '为此员工单独设置', suspended, permission_mode: 'personal',
  version: 7, context_revision: 'attendance-r1', operations: [],
})
let wrappers: VueWrapper[] = []
async function render(component: object, options: { props?: Record<string, unknown>; path?: string } = {}) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
  await router.push(options.path || '/hbos/admin/people')
  await router.isReady()
  const wrapper = mount(component, {
    attachTo: document.body,
    props: options.props,
    global: { plugins: [Antd, router], stubs: { ...stubs, OwnAccountVerification: Verify } },
  })
  wrappers.push(wrapper)
  return wrapper
}
async function renderWithRouter(component: object, path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(component, {
    attachTo: document.body,
    global: { plugins: [Antd, router], stubs: { ...stubs, OwnAccountVerification: Verify } },
  })
  wrappers.push(wrapper)
  return { wrapper, router }
}

function bodyText() { return document.body.textContent || '' }
function nativeButton(text: string) {
  const normalized = text.replace(/\s/g, '')
  return Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find(row => (row.textContent || '').replace(/\s/g, '').includes(normalized))
}
async function click(w: VueWrapper, text: string) {
  const normalized = text.replace(/\s/g, '')
  const button = w.findAll('button').find(row => row.text().replace(/\s/g, '').includes(normalized))
  if (button) { await button.trigger('click'); await flushPromises(); await nextTick(); return }
  const native = nativeButton(text)
  expect(native, text).toBeDefined()
  native!.click()
  await flushPromises()
  await nextTick()
}
async function setRadio(w: VueWrapper, value: string) {
  const input = w.find(`input[type="radio"][value="${value}"]`)
  if (input.exists()) { await input.setValue(true); await nextTick(); return }
  const native = document.body.querySelector<HTMLInputElement>(`input[type="radio"][value="${value}"]`)
  expect(native, value).not.toBeNull()
  native!.click()
  await nextTick()
  await flushPromises()
}
function departmentRole() {
  return { version: 4, role_key: '', has_role_default: false, department: 'D1', selected_role: null }
}
function departmentList() {
  return {
    groups_available: false, selected_company: 'C1', companies: [{ id: 'C1', name: '海滨公司' }],
    items: [
      { id: 'D1', name: '生产一部', company: 'C1', confirmed: true, members: [{ id: 'E1', name: '合成员工', employee_number: 'T001', department: 'D1', department_name: '生产一部', company: 'C1', position: '操作员', user_id: null, account_status: 'unopened', attendance_status: 'pending', version: 'v1' }] },
      { id: 'DEPT-2', name: '生产二部', company: 'C1', confirmed: true, members: [] },
    ],
  }
}
beforeEach(() => {
  vi.resetAllMocks()
  caps.clear()
  caps.add('iam.roles.read'); caps.add('iam.roles.assign'); caps.add('iam.access.read'); caps.add('iam.access.manage')
  caps.add('iam.departments.read'); caps.add('iam.departments.manage'); caps.add('iam.people.read')
  caps.add('iam.people.link'); caps.add('iam.people.provision'); caps.add('iam.people.transfer'); caps.add('iam.people.disable'); caps.add('iam.people.reset')
  session.rolesEnabled = true
  proof.valid.value = false
  proof.method.value = 'password'
  api.query.mockImplementation((method: string) => method === 'get_assignment' ? Promise.resolve(structuredClone(employeeAssignment)) : Promise.resolve(structuredClone(departmentRole())))
  api.listDepartments.mockResolvedValue(departmentList())
  api.command.mockResolvedValue(structuredClone(previewAssignment))
  api.getPerson.mockResolvedValue(structuredClone(person))
  api.getWorkSummary.mockResolvedValue({ subject_type: 'User', subject_name: 'user-a', apps: [attendanceWorkApp(), { app_id: 'inventory', title: '仓库管理', integrated: true, status: '可以使用', summary: '仓库普通权限', source_text: '', suspended: false, permission_mode: 'department', version: 1, context_revision: 'inventory-r1', operations: [] }] })
  api.previewWork.mockResolvedValue({ version: 7, context_revision: 'attendance-r1', changed: true, summary: '考勤已临时禁用', after: attendanceWorkApp(true) })
  api.workAction.mockResolvedValue(attendanceWorkApp(true))
  api.getWorkSubject.mockResolvedValue({ employee: structuredClone(person.employee), account: { status: 'unopened', user_id: '' }, association: { status: 'unlinked' }, configuration_only: true })
  api.previewLink.mockResolvedValue({ version: 'preview-v1', summary: '关联后保留原账号' })
  api.linkUser.mockResolvedValue({ employee: structuredClone(person.employee), version: 'v2' })
  api.createUser.mockResolvedValue({ employee: structuredClone(person.employee), version: 'v2', temporary_password: 'Temp-Once-Only' })
  api.getDepartmentWork.mockResolvedValue({ subject_type: 'Department', subject_name: 'D1', apps: [
    { app_id: 'attendance', title: '考勤管理', integrated: true, synthetic: false, status: '可以使用', summary: '部门默认普通员工', source_text: '', suspended: false, permission_mode: 'department', version: 1, context_revision: 'r1', operations: [] },
    { app_id: 'inventory', title: '仓库管理', integrated: true, synthetic: false, status: '可以使用', summary: '仓库普通权限', source_text: '', suspended: false, permission_mode: 'department', version: 1, context_revision: 'r2', operations: [] },
  ] })
})
afterEach(() => {
  vi.restoreAllMocks()
  wrappers.forEach(wrapper => wrapper.unmount())
  wrappers = []
  document.body.innerHTML = ''
})

describe('R6-A2.2 employee apps and assignment fidelity', () => {
  it('matches the department prototype with selectable directory rows and tucked-away scope filters', async () => {
    const w = await render(DepartmentsAdminView)
    await flushPromises()

    expect(w.find('.r6-department-tree .ant-tree').exists()).toBe(false)
    expect(w.findAll('button.r6-department-row')).toHaveLength(2)
    expect(w.find('button.r6-department-row[aria-current="page"]').text()).toContain('生产一部')
    expect(w.find('.r6-dept-info').exists()).toBe(true)
    expect(w.find('[aria-label="搜索组织部门"]').exists()).toBe(false)

    await click(w, '筛选部门')
    expect(w.find('[aria-label="搜索组织部门"]').exists()).toBe(true)
    await w.get<HTMLInputElement>('[aria-label="搜索组织部门"]').setValue('二部')
    await flushPromises()
    expect(w.findAll('button.r6-department-row')).toHaveLength(1)
    expect(w.find('button.r6-department-row').text()).toContain('生产二部')
  })

  it('keeps department read errors inside the full-height detail card', async () => {
    api.getDepartmentWork.mockRejectedValueOnce(new Error('部门安排暂时无法读取'))
    const w = await render(DepartmentsAdminView)
    await flushPromises()

    const error = w.find('.r6-resource-error-inline')
    expect(error.exists()).toBe(true)
    expect(error.element.closest('.r6-panel-frame')?.querySelector('[data-scroll-region="department-detail"]')?.getAttribute('aria-label')).toBe('部门默认安排与成员')
    expect(w.findAll('.r6-panel-frame')).toHaveLength(2)
  })

  it('shows role cards only for a direct assignment and keeps real effective functions separate', async () => {
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true, subjectLabel: '合成员工' } })
    await flushPromises()
    expect(w.text()).toContain('跟随部门安排')
    expect(w.findAll('.r6-role-card')).toHaveLength(0)
    await setRadio(w, 'DIRECT')
    expect(w.findAll('.r6-role-card')).toHaveLength(3)
    expect(w.text()).toContain('典型能力')
    expect(w.text()).toContain('当前实际可用功能')
    expect(w.text()).toContain('查看自己的考勤')
  })

  it('ignores a pending preview response after the subject changes', async () => {
    let resolvePreview!: (value: unknown) => void
    const pending = new Promise(resolve => { resolvePreview = resolve })
    api.query.mockImplementation((method: string, params: Record<string, unknown>) => method === 'get_assignment'
      ? Promise.resolve({ ...structuredClone(employeeAssignment), role_key: params.employee_id === 'E2' ? 'clerk' : 'staff' })
      : Promise.resolve(structuredClone(departmentRole())))
    api.command.mockReturnValueOnce(pending)
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await click(w, '核对实际结果')
    expect(api.command).toHaveBeenCalledTimes(1)
    await w.setProps({ subjectId: 'E2' })
    await flushPromises()
    resolvePreview({ ...structuredClone(previewAssignment), context_revision: 'c'.repeat(64), after: { allowed: true, reason: '', operations: [{ operation_id: 'attendance.read', label: '旧预览功能', scope_type: 'SELF', scope_ref: '', allowed: true }] } })
    await flushPromises()
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(false)
    expect(w.text()).not.toContain('旧预览功能')
  })

  it('renders the employee role editor directly in embedded mode with all three roles and no hidden setup step', async () => {
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true, subjectLabel: '合成员工' } })
    await flushPromises()
    expect(w.text()).toContain('角色来源')
    expect(w.text()).toContain('普通员工')
    expect(w.text()).not.toContain('设置角色与范围')
    expect(w.findAll('.r6-role-card')).toHaveLength(0)
    await setRadio(w, 'DIRECT')
    expect(w.text()).toContain('部门考勤员')
    expect(w.text()).toContain('考勤管理员')
    expect(w.findAll('input[type="radio"]').map(row => (row.element as HTMLInputElement).value)).toEqual(expect.arrayContaining(['FOLLOW_DEPARTMENT', 'DIRECT', 'NONE', 'staff', 'clerk', 'admin']))
    expect(api.query).toHaveBeenCalledWith('get_assignment', expect.objectContaining({ employee_id: 'E1' }))
  })

  it('blocks a clerk preview without a department, then sends the explicitly selected DEPT-2 with include_descendants=0', async () => {
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await setRadio(w, 'clerk')
    await click(w, '核对实际结果')
    expect(api.command).not.toHaveBeenCalled()
    expect(w.text()).toContain('负责部门')

    const selector = w.findComponent({ name: 'ASelect' })
    expect(selector.exists()).toBe(true)
    selector.vm.$emit('update:value', ['DEPT-2'])
    await nextTick()
    await click(w, '核对实际结果')
    expect(api.command).toHaveBeenCalledTimes(1)
    expect(api.command).toHaveBeenCalledWith('preview_assignment', expect.objectContaining({
      employee_id: 'E1', mode: 'DIRECT', role_key: 'clerk',
      responsibilities: [{ scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', include_descendants: 0 }],
      expected_version: 3,
    }))
  })

  it('keeps known personal restrictions visible and never implies that NONE or follow-department clears them', async () => {
    api.query.mockResolvedValue({ ...structuredClone(employeeAssignment), mode: 'DIRECT', role_key: 'staff', selected_role: { ...structuredClone(employeeAssignment.selected_role), source_mode: 'direct', source_ref: 'E1' }, effective_access: { allowed: false, reason: '已有禁止或临时禁用仍然生效。', operations: [{ operation_id: 'attendance.read', label: '查看自己的考勤', scope_type: 'SELF', scope_ref: '', allowed: false, reason: '已有禁止或临时禁用仍然生效。' }] } })
    api.command.mockResolvedValue({ ...structuredClone(previewAssignment), after: { allowed: false, reason: '已有禁止或临时禁用仍然生效。', operations: [] } })
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    expect(w.text()).toContain('已有禁止或临时禁用仍然生效。')
    expect(w.text()).toContain('不会解除')
    await setRadio(w, 'NONE')
    expect(w.findAll('.r6-role-card')).toHaveLength(0)
    expect(w.text()).toContain('不安排此角色')
    await click(w, '核对实际结果')
    expect(api.command).toHaveBeenCalledWith('preview_assignment', expect.objectContaining({ mode: 'NONE', responsibilities: [] }))
    const modal = w.findComponent({ name: 'ChangeReview' })
    expect(modal.props('open')).toBe(true)
    expect(bodyText()).toContain('原有个人限制仍保留')
    expect(bodyText()).toContain('本页保存不会解除')
    await click(w, '返回修改')
    await setRadio(w, 'FOLLOW_DEPARTMENT')
    await click(w, '核对实际结果')
    expect(api.command).toHaveBeenLastCalledWith('preview_assignment', expect.objectContaining({ mode: 'FOLLOW_DEPARTMENT', role_key: '', responsibilities: [] }))
    expect(bodyText()).toContain('原有个人限制仍保留')
  })

  it('keeps an unset department default as a separate read-only legacy state instead of silently selecting no-default', async () => {
    const baseline = { context_revision: 'd'.repeat(64), changed: false, reference_count: 2, effective_changed_count: 0, personal_preserved: 3, members: [{ employee: 'E1', name: '合成员工', changed: false, before_allowed: true, after_allowed: false, reason: '账号未开通。' }] }
    api.command.mockImplementation((method: string, params: Record<string, unknown>) => {
      if (method === 'preview_department_role' && params.role_key === 'staff') return Promise.resolve({ context_revision: 'b'.repeat(64), changed: true, reference_count: 2, effective_changed_count: 1, personal_preserved: 3, members: [] })
      return Promise.resolve(baseline)
    })
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(w.text()).toContain('沿用已有安排')
    expect(w.text()).toContain('只读')
    expect((w.find('input[type="radio"][value="LEGACY"]').element as HTMLInputElement).checked).toBe(true)
    expect((w.find('input[type="radio"][value="LEGACY"]').element as HTMLInputElement).disabled).toBe(true)
    expect((w.find('input[type="radio"][value=""]').element as HTMLInputElement).checked).toBe(false)
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).checked).toBe(false)
    expect(w.findAll('button').find(row => row.text().includes('核对部门变化'))!.attributes('disabled')).toBeDefined()
    expect(api.command).toHaveBeenCalledWith('preview_department_role', expect.objectContaining({ department: 'D1', role_key: '', expected_version: 4 }))
    expect(api.command.mock.calls.some(call => call[0] === 'save_department_role')).toBe(false)
    expect(w.text()).not.toContain('实际权限将变化')
    expect(w.text()).toContain('当前有可用考勤')

    await setRadio(w, 'staff')
    await click(w, '核对部门变化')
    expect(api.command).toHaveBeenCalledWith('preview_department_role', expect.objectContaining({ department: 'D1', role_key: 'staff', expected_version: 4 }))
  })

  it('shows real baseline follower counts, preserved arrangements and a fixed check action in the department page', async () => {
    const baseline = { context_revision: 'd'.repeat(64), changed: false, reference_count: 2, effective_changed_count: 0, personal_preserved: 3, members: [{ employee: 'E1', name: '合成员工', changed: false, before_allowed: true, after_allowed: false, reason: '账号未开通。' }] }
    const candidate = { context_revision: 'b'.repeat(64), changed: true, reference_count: 2, effective_changed_count: 1, personal_preserved: 3, members: [{ employee: 'E1', name: '合成员工', changed: true, before_allowed: true, after_allowed: true, reason: '权限范围变化' }] }
    api.command.mockImplementation((method: string, params: Record<string, unknown>) => {
      if (method === 'save_department_role') return Promise.resolve({})
      if (method === 'preview_department_role' && params.role_key === 'staff') return Promise.resolve(candidate)
      return Promise.resolve(baseline)
    })
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(api.getDepartmentWork).toHaveBeenCalledWith('D1')
    expect(w.text()).toContain('仅影响选择跟随部门安排的员工；个人安排和已有限制保留。')
    expect(w.text()).toContain('跟随人数')
    expect(w.text()).toContain('2')
    expect(w.text()).toContain('单独安排保留')
    expect(w.text()).toContain('3')
    expect(w.text()).toContain('合成员工')
    expect(w.text()).toContain('当前有可用考勤')
    expect(w.text()).toContain('仓库管理')
    expect(api.command).toHaveBeenCalledWith('preview_department_role', expect.objectContaining({ department: 'D1', role_key: '', expected_version: 4 }))
    expect(api.command.mock.calls.some(call => call[0] === 'save_department_role')).toBe(false)

    await setRadio(w, 'staff')
    await setRadio(w, 'members')
    await flushPromises()
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).checked).toBe(true)
    await setRadio(w, 'apps')
    await flushPromises()
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).checked).toBe(true)
    expect(w.text()).toContain('有未保存的修改')
    await click(w, '核对部门变化')
    expect(api.command).toHaveBeenCalledWith('preview_department_role', expect.objectContaining({ department: 'D1', role_key: 'staff' }))
    expect(bodyText()).toContain('跟随默认 2 人')
    expect(bodyText()).toContain('个人安排保留 3 人')
    await click(w, '完成测试核验')
    await click(w, '确认保存')
    expect(api.command).toHaveBeenCalledWith('save_department_role', expect.objectContaining({ department: 'D1', role_key: 'staff', context_revision: 'b'.repeat(64), request_id: expect.any(String) }))
  })

  it('asks before discarding an embedded draft and keeps it when the user continues editing', async () => {
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await setRadio(w, 'staff')
    let asked: { title?: string; content?: string; onOk?: () => void; onCancel?: () => void } | null = null
    const confirm = vi.spyOn(Modal, 'confirm').mockImplementation((config: Record<string, unknown>) => { asked = config as typeof asked; return {} as never })
    const exposed = w.vm as unknown as { requestLeave: () => Promise<boolean> }
    const first = exposed.requestLeave()
    expect(asked?.title).toContain('放弃尚未保存的角色安排？')
    asked!.onCancel!()
    expect(await first).toBe(false)
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).checked).toBe(true)
    const second = exposed.requestLeave()
    asked!.onOk!()
    expect(await second).toBe(true)
    expect(w.findAll('.r6-role-card')).toHaveLength(0)
    expect(w.text()).toContain('与当前安排一致')
    confirm.mockRestore()
  })

  it('does not render submittable choices for a read-only role viewer', async () => {
    for (const capability of ['iam.roles.assign', 'iam.access.manage', 'iam.departments.manage']) caps.delete(capability)
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    expect(w.text()).toContain('普通员工')
    expect(w.text()).toContain('只读')
    expect(w.find('input[type="radio"]').exists()).toBe(false)
    expect(w.findAll('button').some(row => row.text().includes('核对实际结果'))).toBe(false)
    expect(api.command).not.toHaveBeenCalled()
  })

  it('keeps the clerk draft after a conflict and refuses another preview until the latest assignment is read', async () => {
    api.command.mockRejectedValueOnce(Object.assign(new Error('设置已被更新或预览已过期。草稿已保留。'), { status: 409 }))
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await setRadio(w, 'clerk')
    const selector = w.findComponent({ name: 'ASelect' })
    selector.vm.$emit('update:value', ['DEPT-2'])
    await nextTick()
    await click(w, '核对实际结果')
    expect(api.command).toHaveBeenCalledTimes(1)
    expect((w.find('input[type="radio"][value="clerk"]').element as HTMLInputElement).checked).toBe(true)
    expect(w.text()).toContain('草稿已保留')
    await click(w, '核对实际结果')
    expect(api.command).toHaveBeenCalledTimes(1)
    await click(w, '读取最新安排，保留草稿')
    expect(api.query).toHaveBeenCalledTimes(2)
    expect((w.find('input[type="radio"][value="clerk"]').element as HTMLInputElement).checked).toBe(true)
    await click(w, '核对实际结果')
    expect(api.command).toHaveBeenCalledTimes(2)
  })

  it('clears an open preview and the old scope content when the subject changes', async () => {
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await click(w, '核对实际结果')
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(true)
    await w.setProps({ subjectId: 'E2' })
    await flushPromises()
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(false)
    expect(api.query).toHaveBeenLastCalledWith('get_assignment', expect.objectContaining({ employee_id: 'E2' }))
  })

  it('opens the application-role tab from an apps/initialApp deep link and preserves its draft across tab changes', async () => {
    const w = await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'apps', initialApp: 'attendance' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('应用角色')
    expect(bodyText()).toContain('角色来源')
    expect(bodyText()).not.toContain('返回应用清单')
    await setRadio(w, 'DIRECT')
    expect(bodyText()).toContain('部门考勤员')
    await setRadio(w, 'clerk')
    const selector = w.findComponent({ name: 'ASelect' })
    selector.vm.$emit('update:value', ['DEPT-2'])
    await nextTick()
    const tabs = Array.from(document.body.querySelectorAll<HTMLElement>('.ant-tabs-tab'))
    const profileTab = tabs.find(row => (row.textContent || '').includes('员工资料'))
    expect(profileTab).toBeDefined()
    profileTab!.click()
    await flushPromises()
    const appsTab = Array.from(document.body.querySelectorAll<HTMLElement>('.ant-tabs-tab')).find(row => (row.textContent || '').includes('应用角色'))
    appsTab!.click()
    await flushPromises()
    expect((document.body.querySelector('input[type="radio"][value="clerk"]') as HTMLInputElement).checked).toBe(true)
  })

  it('offers an independent low-frequency attendance pause entry for a real User app and calls preview_work then suspend_app', async () => {
    api.getPerson.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'confirmed' },
      account: { user_id: 'user-a' }, association: { employee_id: 'E1', user_id: 'user-a' }, history: [],
    })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'apps' }, path: '/hbos/admin/people' })
    await flushPromises()
    const section = new DOMWrapper(document.body.querySelector<HTMLElement>('.r6-attendance-more')!)
    expect(section.text()).toContain('更多考勤操作')
    expect(section.text()).toContain('临时暂停或恢复')
    expect(section.text()).toContain('不改变角色')
    await section.get('button[aria-label="考勤管理的更多操作"]').trigger('click')
    await flushPromises()
    const suspend = Array.from(document.body.querySelectorAll<HTMLElement>('.ant-dropdown-menu-item')).find(row => row.textContent?.includes('临时禁用考勤'))
    expect(suspend).toBeDefined()
    suspend!.click()
    await flushPromises()
    expect(api.previewWork).toHaveBeenCalledWith(expect.objectContaining({
      target: expect.objectContaining({ subject_type: 'User', subject_name: 'user-a', app_id: 'attendance' }),
      expected_version: 7, context_revision: 'attendance-r1',
    }), 'suspend')
    const confirm = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find(row => row.textContent?.trim() === '确认临时禁用')
    expect(confirm).toBeDefined()
    confirm!.click()
    await flushPromises()
    expect(api.workAction).toHaveBeenCalledWith('suspend_app', expect.objectContaining({
      subject_type: 'User', subject_name: 'user-a', app_id: 'attendance',
    }), 7, 'attendance-r1', expect.any(String))
  })

  it('uses reenable_app for a suspended attendance app instead of a separate new command', async () => {
    api.getPerson.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'confirmed' },
      account: { user_id: 'user-a' }, association: { employee_id: 'E1', user_id: 'user-a' }, history: [],
    })
    api.getWorkSummary.mockResolvedValue({ subject_type: 'User', subject_name: 'user-a', apps: [attendanceWorkApp(true)] })
    api.previewWork.mockResolvedValue({ version: 7, context_revision: 'attendance-r1', changed: true, summary: '考勤已恢复', after: attendanceWorkApp(false) })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'apps' }, path: '/hbos/admin/people' })
    await flushPromises()
    const section = new DOMWrapper(document.body.querySelector<HTMLElement>('.r6-attendance-more')!)
    expect(section.text()).toContain('已临时禁用')
    await section.get('button[aria-label="考勤管理的更多操作"]').trigger('click')
    await flushPromises()
    const reenable = Array.from(document.body.querySelectorAll<HTMLElement>('.ant-dropdown-menu-item')).find(row => row.textContent?.includes('解除临时禁用'))
    expect(reenable).toBeDefined()
    reenable!.click()
    await flushPromises()
    expect(api.previewWork).toHaveBeenCalledWith(expect.objectContaining({ target: expect.objectContaining({ app_id: 'attendance' }) }), 'reenable')
    const confirm = Array.from(document.body.querySelectorAll<HTMLButtonElement>('button')).find(row => row.textContent?.trim() === '确认解除临时禁用')
    expect(confirm).toBeDefined()
    confirm!.click()
    await flushPromises()
    expect(api.workAction).toHaveBeenCalledWith('reenable_app', expect.objectContaining({ app_id: 'attendance' }), 7, 'attendance-r1', expect.any(String))
  })

  it('keeps the legacy app view and hides the attendance pause entry when roles are disabled or the manage capability is absent', async () => {
    api.getPerson.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'confirmed' },
      account: { user_id: 'user-a' }, association: { employee_id: 'E1', user_id: 'user-a' }, history: [],
    })
    session.rolesEnabled = false
    const legacy = await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'apps' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('应用角色功能尚未启用')
    expect(document.body.querySelector('.r6-attendance-more')).toBeNull()
    legacy.unmount()
    wrappers = wrappers.filter(wrapper => wrapper !== legacy)
    document.body.innerHTML = ''

    session.rolesEnabled = true
    caps.delete('iam.access.manage')
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'apps' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('应用角色')
    expect(document.body.querySelector('.r6-attendance-more')).toBeNull()
  })

  it('hides the attendance pause entry when the work summary has no real attendance app', async () => {
    api.getPerson.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'confirmed' },
      account: { user_id: 'user-a' }, association: { employee_id: 'E1', user_id: 'user-a' }, history: [],
    })
    api.getWorkSummary.mockResolvedValue({ subject_type: 'User', subject_name: 'user-a', apps: [] })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'apps' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(document.body.querySelector('.r6-attendance-more')).toBeNull()
  })

  it('shows the real Employee and User keys as read-only manual review for a linked but unresolved association', async () => {
    api.getPerson.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'pending' },
      account: { user_id: 'user-a' }, association: { employee_id: 'E1', user_id: 'user-a' }, history: [],
    })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'basic' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('关联异常，需人工核查')
    expect(bodyText()).toContain('Employee 主键')
    expect(bodyText()).toContain('E1')
    expect(bodyText()).toContain('User 主键')
    expect(bodyText()).toContain('user-a')
    expect(bodyText()).toContain('本页没有安全确认命令')
    expect(bodyText()).toContain('人工核查')
    expect(api.linkUser).not.toHaveBeenCalled()
    expect(Array.from(document.body.querySelectorAll('button')).some(row => row.textContent?.includes('确认关联'))).toBe(false)
  })

  it('does not label a configuration-only record as an association error when the status is unavailable', async () => {
    caps.delete('iam.people.read')
    api.getWorkSubject.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'pending' },
      account: { status: 'active', user_id: 'user-a' }, association: { employee_id: 'E1', user_id: 'user-a' }, configuration_only: true,
    })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'basic' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('关联状态不可核对')
    expect(bodyText()).not.toContain('关联异常，人工核查')
    expect(document.body.querySelector('.r6-association-review')).toBeNull()
  })

  it('treats an unopened employee only as an account-opening task, not as an association-review todo', async () => {
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'basic' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('待开通登录账号')
    expect(bodyText()).not.toContain('关联异常')
    expect(bodyText()).not.toContain('本页没有安全确认命令')
  })

  it('collects explicit existing-account identity, evidence and confirmation before the real link preview and link call', async () => {
    const w = await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('已有员工档案，无需重复新增')
    expect(bodyText()).toContain('开通新的登录账号')
    expect(bodyText()).toContain('关联已有的登录账号')
    expect(bodyText()).toContain('核对与选择')
    await setRadio(w, 'link')
    const accountInput = Array.from(document.body.querySelectorAll<HTMLInputElement>('input')).find(row => (row.placeholder || '').includes('账号'))
    expect(accountInput).toBeDefined()
    await new DOMWrapper(accountInput!).setValue('user-existing')
    const textarea = document.body.querySelector<HTMLTextAreaElement>('textarea')
    expect(textarea).not.toBeNull()
    await new DOMWrapper(textarea!).setValue('已核对工号 T001、公司与账号 user-existing 的归属')
    const checkbox = document.body.querySelector<HTMLInputElement>('.employee-drawer input[type="checkbox"]')
    expect(checkbox).not.toBeNull()
    checkbox!.click()
    await nextTick()
    await click(w, '核对并关联')
    expect(bodyText()).toContain('确认关联已有登录账号')
    expect(api.linkUser).not.toHaveBeenCalled()
    await click(w, '完成测试核验')
    await click(w, '确认关联')
    expect(api.previewLink).toHaveBeenCalledWith('E1', 'user-existing', expect.objectContaining({ employee_number: 'T001', company: 'C1', account_user_id: 'user-existing', reference: expect.stringContaining('T001') }))
    expect(api.linkUser).toHaveBeenCalledWith('E1', 'user-existing', expect.objectContaining({ employee_number: 'T001', company: 'C1', account_user_id: 'user-existing' }), 'preview-v1', expect.any(String))
  })

  it('does not emit a pending save result after the subject changes', async () => {
    let resolveSave!: (value: unknown) => void
    const pendingSave = new Promise(resolve => { resolveSave = resolve })
    api.command.mockResolvedValueOnce(structuredClone(previewAssignment)).mockReturnValueOnce(pendingSave)
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await click(w, '核对实际结果')
    proof.valid.value = true
    await nextTick()
    await click(w, '确认保存')
    await w.setProps({ subjectId: 'E2' })
    await flushPromises()
    resolveSave({})
    await flushPromises()
    expect(w.emitted('saved')).toBeUndefined()
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(false)
  })

  it('keeps an unknown-write lock through focus and preview close', async () => {
    api.command.mockResolvedValueOnce(structuredClone(previewAssignment)).mockRejectedValueOnce(Object.assign(new Error('未知写入结果'), { status: 500 }))
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await click(w, '核对实际结果')
    proof.valid.value = true
    await nextTick()
    await click(w, '确认保存')
    expect(w.text()).toContain('未知写入结果')
    expect(w.text()).toContain('读取最新安排，保留草稿')
    const fieldset = w.find('fieldset')
    expect(fieldset.attributes('disabled')).toBeDefined()
    window.dispatchEvent(new Event('focus'))
    w.findComponent({ name: 'ChangeReview' }).vm.$emit('cancel')
    await flushPromises()
    expect(w.text()).toContain('读取最新安排，保留草稿')
    expect(fieldset.attributes('disabled')).toBeDefined()
  })

  it('asks before canceling a dirty role draft', async () => {
    let asked: { title?: string; onOk?: () => void; onCancel?: () => void } | null = null
    const confirm = vi.spyOn(Modal, 'confirm').mockImplementation((config: Record<string, unknown>) => { asked = config as typeof asked; return {} as never })
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await setRadio(w, 'staff')
    await click(w, '取消修改')
    expect(asked?.title).toContain('放弃尚未保存的角色安排？')
    asked!.onCancel!()
    await flushPromises()
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).checked).toBe(true)
    await click(w, '取消修改')
    asked!.onOk!()
    await flushPromises()
    expect(w.findAll('.r6-role-card')).toHaveLength(0)
    confirm.mockRestore()
  })

  it('does not send the restricted department impact preview for a read-only account', async () => {
    for (const capability of ['iam.departments.manage', 'iam.roles.assign']) caps.delete(capability)
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(api.query).toHaveBeenCalledWith('get_department_role', expect.objectContaining({ department: 'D1' }))
    expect(api.command.mock.calls.some(call => call[0] === 'preview_department_role')).toBe(false)
    expect(w.text()).toContain('当前账号不能核对跟随人数')
    expect(w.text()).toContain('待核对')
    expect(w.find('input[type="radio"][value="staff"]').exists()).toBe(false)
  })

  it('shows the department impact error and member entry instead of inventing zero followers', async () => {
    api.command.mockRejectedValueOnce(new Error('部门影响读取被拒绝'))
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(w.text()).toContain('部门影响读取被拒绝')
    expect(w.text()).toContain('待核对')
    expect(w.text()).toContain('查看部门成员')
    expect(w.text()).not.toContain('0跟随人数')
  })

  it('ignores a delayed old department link response', async () => {
    let resolveOld!: (value: unknown) => void
    const oldResponse = new Promise(resolve => { resolveOld = resolve })
    api.listDepartments.mockImplementation((_group: string, target?: string) => {
      if (target === 'D3') return oldResponse
      if (target === 'D4') return Promise.resolve({ ...departmentList(), items: [{ id: 'D4', name: '生产四部', company: 'C1', confirmed: true, members: [] }] })
      return Promise.resolve(departmentList())
    })
    const { wrapper, router } = await renderWithRouter(DepartmentsAdminView, '/hbos/admin/departments')
    await flushPromises()
    await router.push({ path: '/hbos/admin/departments', query: { department: 'D3', tab: 'apps', app: 'attendance' } })
    await flushPromises()
    await router.push({ path: '/hbos/admin/departments', query: { department: 'D4', tab: 'apps', app: 'attendance' } })
    await flushPromises()
    resolveOld({ ...departmentList(), items: [{ id: 'D3', name: '生产三部', company: 'C1', confirmed: true, members: [] }] })
    await flushPromises()
    expect(wrapper.text()).toContain('生产四部')
    expect(wrapper.text()).not.toContain('生产三部')
  })

  it('hides and blocks account details for configuration-only access', async () => {
    caps.delete('iam.people.read')
    api.getWorkSubject.mockResolvedValue({ employee: { ...structuredClone(person.employee), user_id: '' }, account: { status: 'unopened', user_id: '' }, association: { employee_id: 'E1', user_id: '' }, configuration_only: true })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(api.getPerson).not.toHaveBeenCalled()
    expect(api.getWorkSubject).toHaveBeenCalled()
    expect(bodyText()).toContain('基本资料')
    expect(bodyText()).not.toContain('查看账号')
    expect(bodyText()).not.toContain('已有员工档案，无需重复新增')
    expect(document.body.querySelector('.employee-drawer textarea')).toBeNull()
    expect(document.body.querySelector('.account-choice')).toBeNull()
    expect(bodyText()).not.toContain('未设置')
    expect(bodyText()).not.toContain('未绑定')
  })

  it('renders only the account actions allowed by capability', async () => {
    caps.delete('iam.people.provision')
    const linkOnly = await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('关联已有的登录账号')
    expect(bodyText()).not.toContain('开通新的登录账号')
    expect(document.body.querySelector('input[type="radio"][value="create"]')).toBeNull()
    expect(document.body.querySelector('input[type="radio"][value="link"]')).not.toBeNull()
    linkOnly.unmount()
    wrappers = wrappers.filter(wrapper => wrapper !== linkOnly)
    document.body.innerHTML = ''
    caps.delete('iam.people.link')
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('没有开户或关联权限')
    expect(document.body.querySelector('.account-choice')).toBeNull()
    expect(document.body.querySelector('.employee-drawer textarea')).toBeNull()
    expect(bodyText()).not.toContain('核对并开通')
    expect(bodyText()).not.toContain('核对并关联')
  })

  it('does not present missing username or Feishu fields as unset facts', async () => {
    api.getPerson.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active' },
      account: { user_id: 'user-a' },
      association: { employee_id: 'E1', user_id: 'user-a' },
      history: [],
    })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
    expect(bodyText()).toContain('登录名')
    expect(bodyText()).toContain('待核对')
    expect(bodyText()).not.toContain('未设置')
    expect(bodyText()).not.toContain('未绑定')
    expect(bodyText()).not.toContain('无待设置标记')
  })


  it('clears the previous employee department options when the next subject fails to load', async () => {
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    await setRadio(w, 'DIRECT')
    await setRadio(w, 'clerk')
    expect(w.findComponent({ name: 'ASelect' }).props('options')).toHaveLength(2)
    api.query.mockImplementation((method: string, params: Record<string, unknown>) => {
      if (method === 'get_assignment' && params.employee_id === 'E2') return Promise.reject(new Error('新对象读取失败'))
      return Promise.resolve(structuredClone(employeeAssignment))
    })
    await w.setProps({ subjectId: 'E2' })
    await flushPromises()
    expect(w.text()).toContain('新对象读取失败')
    expect(w.findComponent({ name: 'ASelect' }).exists()).toBe(false)
    expect(w.text()).not.toContain('生产二部')
  })

  it('keeps a department draft after a failed department save and clears the lock only after a real read', async () => {
    const baseline = { context_revision: 'd'.repeat(64), changed: false, reference_count: 2, effective_changed_count: 0, personal_preserved: 3, members: [{ employee: 'E1', name: '合成员工', changed: false, before_allowed: true, after_allowed: false, reason: '账号未开通。' }] }
    const candidate = { context_revision: 'b'.repeat(64), changed: true, reference_count: 2, effective_changed_count: 1, personal_preserved: 3, members: [] }
    api.command.mockImplementation((method: string, params: Record<string, unknown>) => {
      if (method === 'save_department_role') return Promise.reject(Object.assign(new Error('部门保存冲突'), { status: 500 }))
      if (method === 'preview_department_role' && params.role_key === 'staff') return Promise.resolve(candidate)
      return Promise.resolve(baseline)
    })
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    await setRadio(w, 'staff')
    await click(w, '核对部门变化')
    proof.valid.value = true
    await nextTick()
    await click(w, '确认保存')
    expect(w.text()).toContain('部门保存冲突')
    expect(w.text()).toContain('读取最新部门安排，保留草稿')
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).checked).toBe(true)
    window.dispatchEvent(new Event('focus'))
    w.findComponent({ name: 'ChangeReview' }).vm.$emit('cancel')
    await flushPromises()
    expect(w.text()).toContain('读取最新部门安排，保留草稿')
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).disabled).toBe(true)
    await click(w, '读取最新部门安排，保留草稿')
    expect((w.find('input[type="radio"][value="staff"]').element as HTMLInputElement).checked).toBe(true)
    expect(w.text()).not.toContain('部门保存冲突')
  })

})
