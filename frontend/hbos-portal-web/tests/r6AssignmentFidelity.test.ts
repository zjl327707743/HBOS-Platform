import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
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
  roles: [
    { role_key: 'staff', title: '普通员工', boundary_kind: 'SELF', grantable: true, published_revision: 2 },
    { role_key: 'clerk', title: '部门考勤员', boundary_kind: 'DEPARTMENT', grantable: true, published_revision: 2 },
    { role_key: 'admin', title: '考勤管理员', boundary_kind: 'COMPANY', grantable: true, published_revision: 2 },
  ],
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
  it('refreshes the department directory after returning to its cached view', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
    await router.push('/hbos/admin/departments')
    await router.isReady()
    const active = ref(true)
    const Empty = defineComponent({ template: '<div />' })
    const Host = defineComponent({
      setup: () => ({ active, DepartmentsAdminView, Empty }),
      template: '<KeepAlive><component :is="active ? DepartmentsAdminView : Empty" /></KeepAlive>',
    })
    const w = mount(Host, { attachTo: document.body, global: { plugins: [Antd, router], stubs: { OwnAccountVerification: Verify } } })
    wrappers.push(w)
    await flushPromises()
    expect(api.listDepartments).toHaveBeenCalledTimes(1)
    active.value = false
    await flushPromises()
    active.value = true
    await flushPromises()
    expect(api.listDepartments).toHaveBeenCalledTimes(2)
  })

  it('waits for department app access reads before loading the department role baseline', async () => {
    let finishApps!: (value: unknown) => void
    api.getDepartmentWork.mockReturnValue(new Promise(resolve => { finishApps = resolve }))
    const w = await render(DepartmentsAdminView)
    await flushPromises()

    expect(api.query.mock.calls.some(call => call[0] === 'get_department_role')).toBe(false)
    expect(api.command.mock.calls.some(call => call[0] === 'preview_department_role')).toBe(false)
    finishApps({ subject_type: 'Department', subject_name: 'D1', apps: [] })
    await flushPromises()
    expect(api.query).toHaveBeenCalledWith('get_department_role', expect.objectContaining({ department: 'D1' }))
    expect(api.command).toHaveBeenCalledWith('preview_department_role', expect.objectContaining({ department: 'D1' }))
    w.unmount()
  })

  it('shows role cards only for a direct assignment and keeps real effective functions separate', async () => {
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true, subjectLabel: '合成员工' } })
    await flushPromises()
    expect(w.text()).toContain('跟随部门安排')
    expect(w.findAll('.r6-choice-card')).toHaveLength(0)
    await setRadio(w, 'DIRECT')
    expect(w.findAll('.r6-choice-card')).toHaveLength(3)
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
    expect(w.findAll('.r6-choice-card')).toHaveLength(0)
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
    expect(w.findAll('.r6-choice-card')).toHaveLength(0)
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
    expect(w.findAll('.r6-choice-card')).toHaveLength(0)
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

  it('preserves the selected account-link mode and re-previews the current employee version after a conflict', async () => {
    const latestPerson = (version: string) => ({
      ...structuredClone(person),
      employee: { ...structuredClone(person.employee), version },
    })
    api.getPerson.mockResolvedValueOnce(latestPerson('v1')).mockResolvedValueOnce(latestPerson('v2')).mockResolvedValue(latestPerson('v2'))
    api.previewLink.mockResolvedValueOnce({ version: 'preview-v1', summary: '首次核对' }).mockResolvedValueOnce({ version: 'preview-v2', summary: '最新核对' })
    api.linkUser.mockRejectedValueOnce(Object.assign(new Error('员工档案已变化'), { status: 409 })).mockResolvedValueOnce({ employee: { ...person.employee, user_id: 'user-existing', account_status: 'active' } })
    const w = await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
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
    await click(w, '完成测试核验')
    await click(w, '确认关联')
    expect(bodyText()).toContain('读取最新资料，保留选择')
    await click(w, '读取最新资料，保留选择')
    await flushPromises()

    const linkRadio = Array.from(document.body.querySelectorAll<HTMLInputElement>('input[type="radio"]')).find(row => row.value === 'link')
    expect(linkRadio?.checked).toBe(true)
    const latestAccountInput = Array.from(document.body.querySelectorAll<HTMLInputElement>('input')).find(row => (row.placeholder || '').includes('账号'))
    expect(latestAccountInput?.value).toBe('user-existing')
    await click(w, '核对并关联')
    await click(w, '完成测试核验')
    await click(w, '确认关联')

    expect(api.previewLink).toHaveBeenCalledTimes(2)
    expect(api.linkUser.mock.calls[0]?.[3]).toBe('preview-v1')
    expect(api.linkUser.mock.calls[1]?.[3]).toBe('preview-v2')
    expect(api.linkUser.mock.calls[1]?.[4]).toBe(api.linkUser.mock.calls[0]?.[4])
    expect(api.createUser).not.toHaveBeenCalled()
  })

  it('does not ask link-only operators to discard a form they never changed', async () => {
    caps.delete('iam.people.provision')
    const confirm = vi.spyOn(Modal, 'confirm')
    const w = await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
    await click(w, '关闭详情')
    expect(confirm).not.toHaveBeenCalled()
  })

  it('reuses the same assist request id after an unknown result and a fresh state read', async () => {
    const activePerson = {
      ...structuredClone(person),
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'confirmed' },
      account: { user_id: 'user-a', username: 'user-a', feishu_bound: false, initial_password_pending: false },
      association: { employee_id: 'E1', user_id: 'user-a' },
    }
    api.getPerson.mockResolvedValue(activePerson)
    api.resetTemporaryPassword.mockRejectedValueOnce(new Error('网络响应丢失')).mockResolvedValueOnce({ temporary_password: 'new-temporary-password' })
    const w = await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'account' }, path: '/hbos/admin/people' })
    await flushPromises()
    const assistDetails = Array.from(document.body.querySelectorAll<HTMLDetailsElement>('details')).find(row => row.querySelector('summary')?.textContent?.includes('更多账号协助'))
    expect(assistDetails).toBeDefined()
    assistDetails!.open = true
    await nextTick()
    await click(w, '受控重置临时密码')
    await click(w, '完成测试核验')
    await click(w, '确认重置')
    expect(api.resetTemporaryPassword).toHaveBeenCalledTimes(1)
    expect(bodyText()).toContain('读取最新资料，保留选择')

    await click(w, '读取最新资料，保留选择')
    await flushPromises()
    const reopenedAssistDetails = Array.from(document.body.querySelectorAll<HTMLDetailsElement>('details')).find(row => row.querySelector('summary')?.textContent?.includes('更多账号协助'))
    expect(reopenedAssistDetails).toBeDefined()
    reopenedAssistDetails!.open = true
    await nextTick()
    await click(w, '受控重置临时密码')
    await click(w, '完成测试核验')
    await click(w, '确认重置')

    expect(api.resetTemporaryPassword).toHaveBeenCalledTimes(2)
    expect(api.resetTemporaryPassword.mock.calls[1]?.[2]).toBe(api.resetTemporaryPassword.mock.calls[0]?.[2])
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
    expect(w.findAll('.r6-choice-card')).toHaveLength(0)
    confirm.mockRestore()
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

  it('shows the two independent clerk scopes from published capability instead of inferring them from the role name', async () => {
    api.query.mockResolvedValue({
      ...structuredClone(employeeAssignment), mode: 'DIRECT', role_key: 'clerk', responsibilities: [{ scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', include_descendants: 0 }],
      selected_role: { ...structuredClone(employeeAssignment.selected_role), source_mode: 'direct', role_key: 'clerk', title: '部门考勤员', responsibilities: [{ scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2' }] },
      effective_access: { allowed: true, reason: '', operations: [
        { operation_id: 'attendance.read', label: '查看自己的考勤', scope_type: 'SELF', scope_ref: '', allowed: true },
        { operation_id: 'attendance.department.board.read', label: '查看部门考勤面板', scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', allowed: true },
      ] },
    })
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true, subjectLabel: '质量员工' } })
    await flushPromises()
    const split = w.find('.role-scope-split')
    expect(split.exists()).toBe(true)
    expect(split.text()).toContain('本人考勤')
    expect(split.text()).toContain('已包含：可查看本人考勤')
    expect(split.text()).toContain('明确负责')
    expect(split.text()).toContain('不含下级')
    expect(w.text()).toContain('单独设置只替换此人的考勤默认，不影响其他应用')
    expect(w.find('.role-state-distinction').text()).toContain('不安排该角色')
    expect(w.find('.role-state-distinction').text()).toContain('暂停考勤应用')
    expect(w.find('.role-state-distinction').text()).toContain('停用账号')
  })

  it('warns when a published clerk role does not actually include the employee own attendance read', async () => {
    api.query.mockResolvedValue({
      ...structuredClone(employeeAssignment), mode: 'DIRECT', role_key: 'clerk', responsibilities: [{ scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', include_descendants: 0 }],
      selected_role: { ...structuredClone(employeeAssignment.selected_role), source_mode: 'direct', role_key: 'clerk', title: '部门考勤员' },
      effective_access: { allowed: true, reason: '', operations: [
        { operation_id: 'attendance.department.board.read', label: '查看部门考勤面板', scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', allowed: true },
      ] },
    })
    const w = await render(RoleSettings, { props: { subjectKind: 'employee', subjectId: 'E1', embedded: true } })
    await flushPromises()
    expect(w.find('.role-scope-split').text()).toContain('已发布角色未包含本人考勤读取')
    expect(w.find('.role-scope-split').text()).toContain('不能只凭角色名称推断')
  })

  it('summarizes every application independently in the employee drawer without enabling unsupported ones', async () => {
    api.getPerson.mockResolvedValue({
      employee: { ...structuredClone(person.employee), user_id: 'user-a', account_status: 'active', attendance_status: 'confirmed' },
      account: { user_id: 'user-a' }, association: { employee_id: 'E1', user_id: 'user-a' }, history: [],
    })
    api.getWorkSummary.mockResolvedValue({ subject_type: 'User', subject_name: 'user-a', apps: [
      attendanceWorkApp(),
      { app_id: 'inventory', title: '仓库管理', integrated: false, synthetic: false, status: '暂不可用', summary: '', source_text: '', suspended: false, version: 0, context_revision: 'inventory-r1', operations: [] },
    ] })
    await render(EmployeeDrawer, { props: { open: true, employeeId: 'E1', initialTab: 'apps' }, path: '/hbos/admin/people' })
    await flushPromises()

    const overview = new DOMWrapper(document.body.querySelector<HTMLElement>('.r6-app-access-overview')!)
    expect(overview.text()).toContain('按应用查看权限')
    const cards = overview.findAll('.r6-app-access-card')
    expect(cards.length).toBe(2)
    expect(cards[0].text()).toContain('考勤管理')
    expect(cards[0].text()).toContain('来源')
    expect(cards[0].text()).toContain('角色 / 实际能力')
    expect(cards[0].text()).toContain('数据范围')
    expect(cards[0].text()).toContain('有效状态与受限原因')
    expect(cards[1].text()).toContain('仓库管理')
    expect(cards[1].text()).toContain('尚未接入')
    expect(cards[1].text()).toContain('不套用考勤角色接口')
    const buttons = cards[1].findAll('button')
    expect(buttons.filter(row => /启用|开通|保存|开关/.test(row.text())).length).toBe(0)
  })

})

describe('R6 v1.4 department defaults: reading first, explicit editing', () => {
  function clerkCatalog(grantable = true) {
    return [
      { role_key: 'staff', title: '普通员工', boundary_kind: 'SELF', grantable, published_revision: 2 },
      { role_key: 'clerk', title: '部门考勤员', boundary_kind: 'DEPARTMENT', grantable, published_revision: 2 },
      { role_key: 'admin', title: '考勤管理员', boundary_kind: 'COMPANY', grantable, published_revision: 2 },
    ]
  }
  const baseline = { context_revision: 'd'.repeat(64), changed: false, reference_count: 2, effective_changed_count: 0, personal_preserved: 1, pending_count: 1, confirmed_count: 0, members: [
    { employee: 'E1', name: '合成员工', employee_number: 'T001', changed: false, before_allowed: false, after_allowed: false, reason: '部门管理角色准入待确认。', admission_state: 'PENDING' },
  ], personal: [{ employee: 'E2', name: '单独设置员工', employee_number: 'T002', mode: 'DIRECT', reason: '个人单独设置或既有安排保持不变' }] }

  it('opens in reading mode with the two fixed tabs and never pre-selects a role for a legacy department', async () => {
    api.query.mockResolvedValue({ version: 4, role_key: '', has_role_default: false, department: 'D1' })
    api.command.mockResolvedValue(baseline)
    const w = await render(DepartmentsAdminView)
    await flushPromises()

    const tabs = w.findAll('[role="tab"]')
    expect(tabs.map(row => row.text().split(' ')[0])).toEqual(['默认设置', '成员权限'])
    expect(w.find('.r6-dept-reading').exists()).toBe(true)
    expect(w.find('.r6-dept-editing').exists()).toBe(false)
    expect(w.text()).toContain('尚未设置部门默认')
    expect(w.text()).toContain('当前成员继续沿用原有安排')
    expect(w.find('.r6-dept-reading').text()).toContain('沿用原有安排')
    expect(w.findAll('input[type="radio"]').length).toBe(0)
    expect(w.findAll('button').find(row => row.text().includes('设置部门默认'))).toBeDefined()
  })

  it('enters editing only on an explicit action and keeps assignment mode separate from the three role cards', async () => {
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: clerkCatalog(), responsibilities: [] })
    api.command.mockResolvedValue(baseline)
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(w.text()).not.toContain('分配方式')
    await click(w, '修改默认设置')
    expect(w.find('.r6-dept-editing').exists()).toBe(true)
    expect(w.text()).toContain('正在修改 · 未保存')
    expect(w.text()).toContain('分配方式')
    const cards = w.findAll('.r6-role-picker .r6-choice-card')
    expect(cards.length).toBe(3)
    expect(cards.map(row => row.text())).not.toContain('不通过部门分配')
    expect(w.findAll('input[type="radio"]').map(row => (row.element as HTMLInputElement).value)).toEqual(
      expect.arrayContaining(['department', 'none', 'staff', 'clerk', 'admin']),
    )
    expect(w.find('input[type="radio"][value="LEGACY"]').exists()).toBe(false)
    expect(w.find('.r6-dept-footer-bar').text()).toContain('与当前部门默认一致')
    await setRadio(w, 'clerk')
    expect(w.find('.r6-dept-footer-bar').text()).toContain('有未保存的修改')
    expect(w.findAll('button').some(row => row.text().includes('取消修改'))).toBe(true)
  })

  it('cancels without writing and without leaving a cancel action on a clean draft', async () => {
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: clerkCatalog() })
    api.command.mockResolvedValue(baseline)
    const confirm = vi.spyOn(Modal, 'confirm')
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    await click(w, '修改默认设置')
    await click(w, '取消修改')
    expect(api.command.mock.calls.some(call => call[0] === 'save_department_role')).toBe(false)
    expect(confirm).not.toHaveBeenCalled()
    expect(w.find('.r6-dept-editing').exists()).toBe(false)
    expect(w.find('.r6-dept-footer-bar').text()).toContain('当前默认')
    confirm.mockRestore()
  })

  it('blocks the preview locally for a clerk without a named department and never sends the request', async () => {
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: clerkCatalog() })
    api.command.mockResolvedValue(baseline)
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    await click(w, '修改默认设置')
    await setRadio(w, 'clerk')
    const previews = api.command.mock.calls.filter(call => call[0] === 'preview_department_role').length
    expect(w.find('.r6-field-error').text()).toContain('部门考勤员必须明确选择至少一个负责部门')
    expect(w.findAll('button').find(row => row.text().includes('预览变更'))!.attributes('disabled')).toBeDefined()
    expect(api.command.mock.calls.filter(call => call[0] === 'preview_department_role').length).toBe(previews)
  })

  it('does not treat a missing catalogue entry as a grantable role', async () => {
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: [
      { role_key: 'staff', title: '普通员工', boundary_kind: 'SELF', grantable: true, published_revision: 2 },
      { role_key: 'clerk', title: '部门考勤员', boundary_kind: 'DEPARTMENT', grantable: false, reason: '该角色尚未发布，暂不能授予。' },
    ] })
    api.command.mockResolvedValue(baseline)
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    await click(w, '修改默认设置')
    const cards = w.findAll('.r6-role-picker .r6-choice-card')
    expect(cards.length).toBe(3)
    const admin = cards.find(row => row.attributes('data-role') === 'admin')!
    expect(admin.find('input').attributes('disabled')).toBeDefined()
    expect(admin.text()).toContain('角色目录暂无法读取，不能授予')
    const clerk = cards.find(row => row.attributes('data-role') === 'clerk')!
    expect(clerk.find('input').attributes('disabled')).toBeDefined()
    expect(clerk.text()).toContain('该角色尚未发布，暂不能授予')
    expect(cards.find(row => row.attributes('data-role') === 'staff')!.find('input').attributes('disabled')).toBeUndefined()
  })

  it('maps every member state explicitly, including revoked and unknown, and never claims automatic inheritance', async () => {
    api.query.mockResolvedValue({ version: 5, role_key: 'clerk', has_role_default: true, department: 'D1', roles: clerkCatalog(), responsibilities: [{ scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', include_descendants: 0 }] })
    api.command.mockResolvedValue({ ...baseline, context_revision: 'c'.repeat(64), members: [
      { employee: 'E1', name: '待确认员工', employee_number: 'T001', changed: false, before_allowed: false, after_allowed: false, reason: '部门管理角色准入待确认。', admission_state: 'PENDING' },
      { employee: 'E2', name: '已确认员工', employee_number: 'T002', changed: false, before_allowed: true, after_allowed: true, reason: '', admission_state: 'CONFIRMED' },
      { employee: 'E3', name: '未识别员工', employee_number: 'T003', changed: false, before_allowed: false, after_allowed: false, reason: '', admission_state: 'SOMETHING_NEW' },
    ], personal: [{ employee: 'E4', name: '撤销员工', employee_number: 'T004', mode: 'NONE', reason: '已撤销确认' }] })
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    await click(w, '成员权限')
    const text = w.text()
    expect(text).toContain('待确认角色')
    expect(text).toContain('可使用')
    expect(text).toContain('暂无法确认')
    expect(text).toContain('未通过此来源分配')
    expect(text).not.toContain('自动继承')
    expect(w.findAll('.r6-members__card').length).toBeGreaterThan(0)
  })

  it('shows the pending count on the members tab and the preview separates saved from usable', async () => {
    api.query.mockResolvedValue({ version: 5, role_key: 'clerk', has_role_default: true, department: 'D1', roles: clerkCatalog(), responsibilities: [{ scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', include_descendants: 0 }] })
    api.command.mockResolvedValue(baseline)
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(w.find('.r6-dept-tabs__count').text()).toContain('待确认 1')
    expect(w.find('.r6-dept-pending').text()).toContain('需要确认后才能使用此角色')
  })

  it('keeps the current, the draft, the confirmation and the effective status in four separate places', async () => {
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: clerkCatalog() })
    api.command.mockResolvedValue(baseline)
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    const summary = w.find('.r6-assignment-summary')
    expect(summary.findAll('[data-fact]').map(row => row.attributes('data-fact'))).toEqual(['source', 'role', 'scope', 'status'])
    expect(summary.text()).toContain('跟随部门默认')
    expect(summary.text()).toContain('普通员工')
    expect(summary.text()).toContain('仅本人')
    await click(w, '修改默认设置')
    await setRadio(w, 'clerk')
    const select = w.findComponent({ name: 'ScopeSelector' })
    expect(select.exists()).toBe(true)
    select.vm.$emit('update:modelValue', ['DEPT-2'])
    await nextTick()
    await click(w, '预览变更')
    expect(api.command).toHaveBeenCalledWith('preview_department_role', expect.objectContaining({
      department: 'D1', role_key: 'clerk',
      responsibilities: [{ scope_type: 'DEPARTMENT', scope_ref: 'DEPT-2', include_descendants: 0 }],
    }))
    expect(bodyText()).toContain('确认部门默认权限')
    expect(bodyText()).toContain('当前设置')
    expect(bodyText()).toContain('修改后')
    expect(bodyText()).toContain('保存后不会立即生效')
  })

  it('keeps the long department name bounded and reachable instead of stretching the panel', async () => {
    const longName = '合成超长部门名称验收'.repeat(8)
    api.listDepartments.mockResolvedValue({ ...departmentList(), items: [{ id: 'D1', name: longName, company: 'C1', confirmed: true, members: [] }] })
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: clerkCatalog() })
    api.command.mockResolvedValue(baseline)
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    const label = w.find('.r6-department-row__label')
    expect(label.classes()).toContain('is-clamped')
    expect(w.find('.r6-department-row__more').exists()).toBe(true)
    await w.find('.r6-department-row__more').trigger('click')
    expect(w.find('.r6-department-row__full').text()).toContain(longName)
    expect(w.find('.r6-dept-head h2').attributes('title')).toBe(longName)
  })

  it('keeps a read-only account on reading mode with no edit or confirm action', async () => {
    for (const capability of ['iam.departments.manage', 'iam.roles.assign']) caps.delete(capability)
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: clerkCatalog() })
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(api.command.mock.calls.some(call => call[0] === 'preview_department_role')).toBe(false)
    expect(w.find('.r6-dept-reading').exists()).toBe(true)
    expect(w.findAll('button').find(row => row.text().includes('修改默认设置'))!.attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('只有查看权限')
  })

  it('does not invent follower counts when the impact read fails', async () => {
    api.query.mockResolvedValue({ version: 4, role_key: 'staff', has_role_default: true, department: 'D1', roles: clerkCatalog() })
    api.command.mockRejectedValueOnce(Object.assign(new Error('部门影响读取被拒绝'), { status: 500 }))
    const w = await render(DepartmentsAdminView)
    await flushPromises()
    expect(w.text()).toContain('暂无法核对影响人员')
    expect(w.text()).not.toContain('0 位成员跟随')
    expect(w.find('.r6-dept-facts').exists()).toBe(false)
    expect(w.find('.r6-assignment-summary').text()).toContain('暂无法核对')
  })
})