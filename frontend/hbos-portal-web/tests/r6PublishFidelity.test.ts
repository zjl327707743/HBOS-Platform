import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, DOMWrapper, type VueWrapper } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import Antd, { Modal } from 'ant-design-vue'
import Roles from '@/views/admin/RolesAdminView.vue'
import People from '@/views/admin/PeopleAdminView.vue'
import Audit from '@/views/admin/AuditAdminView.vue'
import type { AppRole } from '@/services/iamRoles'
import type { EmployeeSummary } from '@/types/iam'

const api = vi.hoisted(() => ({
  loadRoles: vi.fn(),
  roleCommand: vi.fn(),
  listPeople: vi.fn(),
  getEmployeeMetadata: vi.fn(),
  listAuditEvents: vi.fn(),
  getAuditEvent: vi.fn(),
}))
const permissions = vi.hoisted(() => new Set<string>())

vi.mock('@/services/iamRoles', () => ({
  loadRoles: api.loadRoles,
  roleCommand: api.roleCommand,
  assertRolePreview: (value: unknown) => value,
}))
vi.mock('@/services/iamPeople', () => ({
  listPeople: api.listPeople,
  getEmployeeMetadata: api.getEmployeeMetadata,
  createEmployee: vi.fn(),
}))
vi.mock('@/services/iamAudit', () => ({
  listAuditEvents: api.listAuditEvents,
  getAuditEvent: api.getAuditEvent,
}))
vi.mock('@/services/iamAccess', () => ({
  canIam: (capability: string) => permissions.has(capability),
  hasManagementAccess: () => true,
  iamMessage: (error: Error) => error.message,
}))

const self = { operation_id: 'attendance.read', scope_binding: 'SELF' }
const board = { operation_id: 'attendance.department.board.read', scope_binding: 'RESPONSIBLE_DEPARTMENTS' }
const report = { operation_id: 'attendance.report.monthly.read', scope_binding: 'RESPONSIBLE_DEPARTMENTS' }
const registry = [
  { ...self, title: '查看自己的考勤', group: 'self', allowed: true, integrated: true, reason: '' },
  { ...board, title: '查看部门考勤面板', group: 'board', allowed: true, integrated: true, reason: '' },
  { ...report, title: '查看月度考勤报表', group: 'reports', allowed: true, integrated: true, reason: '' },
]
function role(overrides: Partial<AppRole> = {}): AppRole {
  return {
    id: 'role-clerk', app_id: 'attendance', role_key: 'clerk', title: '部门考勤员', boundary_kind: 'DEPARTMENT',
    draft_version: 4, draft_features: [self, board], published_release: 'release-3', published_revision: 3,
    published_features: [self], releases: [], registry, ...overrides,
  }
}
const pendingRole = role()
const cleanRole = role({ draft_version: 3, draft_features: [self], published_features: [self] })
const adminRole = role({
  id: 'role-admin', role_key: 'admin', title: '考勤管理员', boundary_kind: 'COMPANY',
  draft_version: 2, draft_features: [board], published_release: 'release-admin-1', published_revision: 1,
  published_features: [board],
})

const Verify = defineComponent({
  emits: ['verified', 'invalidated'],
  template: '<button class="verify-test" @click="$emit(\'verified\', {valid:true,expires_in:120,method:\'password\'})">完成测试核验</button>',
})
const DrawerStub = defineComponent({
  name: 'EmployeeDrawerStub',
  props: { open: Boolean, employeeId: String, initialTab: String, initialApp: String },
  template: '<div class="drawer-stub">{{ employeeId }}:{{ initialTab }}</div>',
})

let wrappers: VueWrapper[] = []
async function render(component: object, path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(component, {
    attachTo: document.body,
    global: {
      plugins: [Antd, router],
      stubs: { OwnAccountVerification: Verify, EmployeeDrawer: DrawerStub, AccountSecurity: true, AppDiagnostics: true },
    },
  })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
async function click(w: VueWrapper, text: string) {
  const native = Array.from(document.body.querySelectorAll('button')).find(item => item.textContent?.trim() === text)
  const button = w.findAll('button').find(item => item.text().trim() === text) || (native ? new DOMWrapper(native) : undefined)
  expect(button, text).toBeDefined()
  await button!.trigger('click')
  await flushPromises()
}
function button(w: VueWrapper, text: string) {
  return w.findAll('button').find(item => item.text().trim() === text)
}
function modalText() {
  return document.querySelector('.ant-modal-content')?.textContent || ''
}
function employee(overrides: Partial<EmployeeSummary>): EmployeeSummary {
  return {
    id: 'EMP-A', name: '员工甲', employee_number: 'T001', department: 'D1', department_name: '合成部门',
    company: 'C1', position: '测试岗位', user_id: 'user-a', account_status: 'active',
    attendance_status: 'confirmed', version: 'v1', ...overrides,
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  permissions.clear()
  permissions.add('iam.roles.read')
  permissions.add('iam.roles.edit')
  permissions.add('iam.roles.publish')
  permissions.add('iam.people.read')
  permissions.add('iam.access.read')
  permissions.add('iam.audit.read')
  api.loadRoles.mockResolvedValue([structuredClone(pendingRole)])
  api.getEmployeeMetadata.mockResolvedValue({ version: 'meta-1', required_fields: [], companies: [], departments: [], genders: [] })
  api.listPeople.mockResolvedValue({
    items: [
      employee({}),
      employee({ id: 'EMP-B', name: '员工乙', employee_number: 'T002', user_id: null, account_status: 'unopened', attendance_status: 'pending' }),
      employee({ id: 'EMP-C', name: '员工丙', employee_number: 'T003', user_id: 'user-c', account_status: 'disabled', attendance_status: 'pending' }),
    ],
    total: 57, page: 1, page_size: 20,
  })
  api.listAuditEvents.mockResolvedValue({
    items: [{ name: 'EV-1', actor: 'hr@example.test', operation: 'role.publish', subject_type: 'HBOS IAM App Role', subject_name: 'role-1', result: 'success', occurred_at: '2026-10-27 10:00' }],
    total: 1, page: 1, page_size: 20,
  })
})
afterEach(() => {
  wrappers.forEach(wrapper => wrapper.unmount())
  wrappers = []
  document.body.innerHTML = ''
})

describe('R6 role draft to publish fidelity', () => {
  it('explains a clean draft and offers a real read-only impact check instead of a mute disabled action', async () => {
    api.loadRoles.mockResolvedValue([structuredClone(cleanRole)])
    api.roleCommand.mockResolvedValueOnce({
      role_key: 'clerk', role: 'role-clerk', draft_version: 3, published_release: 'release-3', changed: false,
      context_revision: 'a'.repeat(64), reference_count: 0, effective_changed_count: 0, members: [], features: [self],
    })
    const w = await render(Roles, '/hbos/admin/roles')
    expect(w.text()).toContain('当前草稿与当前生效一致')
    expect(w.text()).toContain('先保存草稿，再核对发布影响')
    expect(button(w, '预览发布影响')).toBeUndefined()
    const check = button(w, '核对发布影响')
    expect(check).toBeDefined()
    await check!.trigger('click')
    await flushPromises()
    expect(api.roleCommand).toHaveBeenCalledExactlyOnceWith('preview_role_publish', { role_key: 'clerk', expected_draft_version: 3, expected_release: 'release-3' })
    expect(modalText()).toContain('没有待发布变化')
    const confirm = Array.from(document.body.querySelectorAll('button')).find(item => item.textContent?.trim() === '确认发布') as HTMLButtonElement | undefined
    expect(confirm?.disabled).toBe(true)
  })

  it('will not skip the save step while local edits are dirty', async () => {
    const w = await render(Roles, '/hbos/admin/roles')
    await click(w, '编辑功能')
    await w.findAll('input[type=checkbox]')[0]!.setValue(false)
    expect(w.text()).toContain('先保存草稿，不能直接核对发布影响')
    expect(w.text()).toContain('本地未保存')
    expect(button(w, '预览发布影响')).toBeUndefined()
    expect(button(w, '核对发布影响')).toBeUndefined()
    expect(w.findAll('input[type=checkbox]')[0]!.element).toHaveProperty('checked', false)
    expect(api.roleCommand).not.toHaveBeenCalled()
  })

  it('reviews local draft differences and requires proof before saving the draft', async () => {
    const saved = role({ draft_version: 5, draft_features: [board, report], published_features: [self] })
    api.loadRoles.mockResolvedValueOnce([structuredClone(pendingRole)]).mockResolvedValue([saved])
    api.roleCommand.mockResolvedValueOnce({ changed: true, draft_version: 5 })
    const w = await render(Roles, '/hbos/admin/roles')
    await click(w, '编辑功能')
    await w.findAll('input[type=checkbox]')[0]!.setValue(false)
    const reportRow = w.findAll('.r6-feature-row').find(row => row.text().includes('查看月度考勤报表'))
    expect(reportRow).toBeDefined()
    await reportRow!.find('input[type=checkbox]').setValue(true)
    await click(w, '保存草稿')
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(true)
    expect(api.roleCommand).not.toHaveBeenCalled()
    const text = modalText()
    expect(text).toContain('保存角色修改')
    expect(text).toContain('考勤管理')
    expect(text).toContain('部门考勤员')
    expect(text).toContain('当前待发布草稿')
    expect(text).toContain('v4')
    expect(text).toContain('增加的功能')
    expect(text).toContain('查看月度考勤报表')
    expect(text).toContain('仅限员工明确负责的部门，不包含下级')
    expect(text).toContain('移除的功能')
    expect(text).toContain('查看自己的考勤')
    expect(text).toContain('保存后尚未影响员工')
    expect(text).toContain('仍需核对发布影响并发布')
    const confirm = Array.from(document.body.querySelectorAll('button')).find(item => item.textContent?.trim() === '确认保存草稿') as HTMLButtonElement | undefined
    expect(confirm).toBeDefined()
    expect(confirm!.disabled).toBe(true)
    await click(w, '完成测试核验')
    expect(confirm!.disabled).toBe(false)
    await click(w, '确认保存草稿')
    expect(api.roleCommand).toHaveBeenCalledExactlyOnceWith('save_role_draft', {
      role_key: 'clerk', expected_draft_version: 4, features: [board, report], request_id: expect.any(String),
    })
    expect(api.roleCommand).not.toHaveBeenCalledWith('preview_role_publish', expect.anything())
    expect(api.roleCommand).not.toHaveBeenCalledWith('publish_role', expect.anything())
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(false)
    expect(w.text()).toContain('草稿已保存，尚未影响员工')
    expect(w.text()).toContain('下一步：核对发布影响')
    expect(button(w, '核对发布影响')).toBeDefined()
    expect(w.text()).toContain('待发布草稿 v5')
  })

  it('cancel from the draft review closes without writing and keeps the local selection', async () => {
    const w = await render(Roles, '/hbos/admin/roles')
    await click(w, '编辑功能')
    await w.findAll('input[type=checkbox]')[0]!.setValue(false)
    await click(w, '保存草稿')
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(true)
    expect(api.roleCommand).not.toHaveBeenCalled()
    await click(w, '返回修改')
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(false)
    expect(api.roleCommand).not.toHaveBeenCalled()
    expect(w.findAll('input[type=checkbox]')[0]!.element).toHaveProperty('checked', false)
    await click(w, '保存草稿')
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(true)
    expect(modalText()).toContain('查看自己的考勤')
    expect(api.roleCommand).not.toHaveBeenCalled()
  })

  it('shows the real role, revisions, named feature diffs, scope and affected people before publishing', async () => {
    const context = 'b'.repeat(64)
    api.loadRoles.mockResolvedValue([structuredClone(pendingRole)])
    api.roleCommand.mockImplementation((method: string) => {
      if (method === 'preview_role_publish') {
        return Promise.resolve({
          role_key: 'clerk', role: 'role-clerk', draft_version: 4, published_release: 'release-3', changed: true,
          context_revision: context, reference_count: 3, effective_changed_count: 2, personal_preserved: 1,
          features: [self, board],
          members: [
            { employee: 'EMP-A', name: '员工甲', employee_number: 'T001', source_mode: 'department', before_allowed: true, after_allowed: true, changed: false, reason: '' },
            { employee: 'EMP-B', name: '员工乙', employee_number: 'T002', source_mode: 'direct', before_allowed: true, after_allowed: false, changed: true, reason: '已有个人禁止保留' },
          ],
        })
      }
      if (method === 'publish_role') return Promise.resolve({ changed: true, release: 'release-4', published_revision: 4 })
      return Promise.resolve({})
    })
    const w = await render(Roles, '/hbos/admin/roles')
    await click(w, '核对发布影响')
    expect(api.roleCommand).toHaveBeenCalledWith('preview_role_publish', { role_key: 'clerk', expected_draft_version: 4, expected_release: 'release-3' })
    const text = modalText()
    expect(text).toContain('部门考勤员')
    expect(text).toContain('当前生效版本')
    expect(text).toContain('本次待发布草稿')
    expect(text).toContain('v3')
    expect(text).toContain('v4')
    expect(text).toContain('查看部门考勤面板')
    expect(text).toContain('没有移除功能')
    expect(text).toContain('仅限员工明确负责的部门，不包含下级')
    expect(text).toContain('引用 3 人')
    expect(text).toContain('实际权限变化 2 人')
    expect(text).toContain('员工乙')
    expect(text).toContain('跟随部门安排')
    expect(text).toContain('单独设置')
    expect(text).toContain('已有个人禁止保留')
    expect(text).toContain('已有个人禁止、暂停与期限仍保留')
    expect(api.roleCommand).not.toHaveBeenCalledWith('save_role_draft', expect.anything())
    await click(w, '完成测试核验')
    await click(w, '确认发布')
    expect(api.roleCommand).toHaveBeenLastCalledWith('publish_role', {
      role_key: 'clerk', expected_draft_version: 4, expected_release: 'release-3', context_revision: context, request_id: expect.any(String),
    })
  })

  it('does not publish when the server reports no pending change', async () => {
    api.loadRoles.mockResolvedValue([structuredClone(cleanRole)])
    api.roleCommand.mockResolvedValueOnce({
      role_key: 'clerk', draft_version: 3, published_release: 'release-3', changed: false,
      context_revision: 'c'.repeat(64), reference_count: 0, effective_changed_count: 0, members: [], features: [self],
    })
    const w = await render(Roles, '/hbos/admin/roles')
    await click(w, '核对发布影响')
    const confirm = Array.from(document.body.querySelectorAll('button')).find(item => item.textContent?.trim() === '确认发布') as HTMLButtonElement | undefined
    expect(confirm?.disabled).toBe(true)
    expect(document.body.querySelector('.verify-test')).toBeNull()
    confirm?.click()
    await flushPromises()
    expect(api.roleCommand).not.toHaveBeenCalledWith('publish_role', expect.anything())
    expect(modalText()).toContain('没有待发布变化')
  })

  it('keeps the draft and requires a fresh read when a save resolves after deactivation', async () => {
    let resolveSave!: (value: unknown) => void
    api.loadRoles.mockResolvedValue([structuredClone(pendingRole)])
    api.roleCommand.mockImplementationOnce(() => new Promise(resolve => { resolveSave = resolve }))
    const Host = defineComponent({
      components: { Roles },
      data: () => ({ show: true }),
      template: '<KeepAlive><Roles v-if="show" /><div v-else>其他工作</div></KeepAlive>',
    })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
    await router.push('/hbos/admin/roles'); await router.isReady()
    const w = mount(Host, { attachTo: document.body, global: { plugins: [Antd, router], stubs: { OwnAccountVerification: Verify } } })
    wrappers.push(w)
    await flushPromises()
    await click(w, '编辑功能')
    await w.findAll('input[type=checkbox]')[0]!.setValue(false)
    await click(w, '保存草稿')
    await click(w, '完成测试核验')
    const confirm = Array.from(document.body.querySelectorAll('button')).find(item => item.textContent?.trim() === '确认保存草稿') as HTMLButtonElement | undefined
    expect(confirm).toBeDefined()
    expect(confirm!.disabled).toBe(false)
    confirm!.click()
    await Promise.resolve()
    ;(w.vm as unknown as { show: boolean }).show = false
    await flushPromises()
    expect(w.text()).toContain('其他工作')
    resolveSave({ changed: true, draft_version: 5 })
    await flushPromises()
    ;(w.vm as unknown as { show: boolean }).show = true
    await flushPromises()
    expect(w.text()).toContain('页面切换时操作结果尚未确认')
    expect(w.findAll('input[type=checkbox]')[0]!.element).toHaveProperty('checked', false)
    expect(api.roleCommand).toHaveBeenCalledTimes(1)
    expect(button(w, '保存草稿')!.attributes('disabled')).toBeDefined()
  })

  it('drops a preview that resolves after the cached page is deactivated', async () => {
    let resolvePreview!: (value: unknown) => void
    api.loadRoles.mockResolvedValue([structuredClone(pendingRole)])
    api.roleCommand.mockImplementationOnce(() => new Promise(resolve => { resolvePreview = resolve }))
    const Host = defineComponent({
      components: { Roles },
      data: () => ({ show: true }),
      template: '<KeepAlive><Roles v-if="show" /><div v-else>其他工作</div></KeepAlive>',
    })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
    await router.push('/hbos/admin/roles'); await router.isReady()
    const w = mount(Host, { attachTo: document.body, global: { plugins: [Antd, router], stubs: { OwnAccountVerification: Verify } } })
    wrappers.push(w)
    await flushPromises()
    const trigger = w.findAll('button').find(item => item.text().trim() === '核对发布影响')
    expect(trigger).toBeDefined()
    await trigger!.trigger('click')
    ;(w.vm as unknown as { show: boolean }).show = false
    await flushPromises()
    expect(w.text()).toContain('其他工作')
    resolvePreview({
      role_key: 'clerk', draft_version: 4, published_release: 'release-3', changed: true, context_revision: 'e'.repeat(64),
      reference_count: 1, effective_changed_count: 1, members: [], features: [self, board],
    })
    await flushPromises()
    ;(w.vm as unknown as { show: boolean }).show = true
    await flushPromises()
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(false)
    expect(w.text()).toContain('部门考勤员')
    expect(api.loadRoles).toHaveBeenCalledTimes(1)
  })

  it('hides and rejects history restore during dirty editing, then restores the original cancel flow afterwards', async () => {
    api.loadRoles.mockResolvedValue([structuredClone(role({ releases: [{ name: 'release-2', revision: 2, published_at: '2026-10-01 10:00' }] }))])
    const w = await render(Roles, '/hbos/admin/roles')
    expect(w.text()).toContain('从历史发布内容恢复草稿')
    await click(w, '完成测试核验')
    const vm = w.vm as unknown as {
      editing: boolean; checked: string[]; restore: string; role: AppRole
      restoreDraft: () => Promise<void>; cancelEdit: () => Promise<void>
    }
    vm.editing = true
    vm.checked = []
    vm.restore = 'release-2'
    await nextTick()
    await vm.restoreDraft()
    await flushPromises()
    expect(api.roleCommand).not.toHaveBeenCalledWith('restore_role_release', expect.anything())
    expect(w.text()).not.toContain('从历史发布内容恢复草稿')

    let asked: { title?: string; onOk?: () => void; onCancel?: () => void } | null = null
    const confirm = vi.spyOn(Modal, 'confirm').mockImplementation((config: Record<string, unknown>) => { asked = config as typeof asked; return {} as never })
    const cancel = vm.cancelEdit()
    expect(asked?.title).toContain('放弃尚未保存的角色草稿？')
    asked!.onOk!()
    await cancel
    await flushPromises()
    expect(w.text()).toContain('从历史发布内容恢复草稿')
    confirm.mockRestore()
  })

  it('clears a prepared publish preview when another role is selected', async () => {
    api.loadRoles.mockResolvedValue([structuredClone(pendingRole), structuredClone(adminRole)])
    api.roleCommand.mockResolvedValueOnce({
      role_key: 'clerk', draft_version: 4, published_release: 'release-3', changed: true, context_revision: 'd'.repeat(64),
      reference_count: 1, effective_changed_count: 1, members: [], features: [self, board],
    })
    const w = await render(Roles, '/hbos/admin/roles')
    await click(w, '核对发布影响')
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(true)
    const adminNav = w.findAll('button').find(item => item.text().includes('考勤管理员'))
    expect(adminNav).toBeDefined()
    await adminNav!.trigger('click')
    await flushPromises()
    expect(w.findComponent({ name: 'ChangeReview' }).props('open')).toBe(false)
    expect(w.text()).toContain('考勤管理员')
    expect(api.roleCommand).not.toHaveBeenCalledWith('publish_role', expect.anything())
  })
})

describe('R6 people entries and page-local overview', () => {
  it('routes the name, app-role and account entries to the matching drawer tab', async () => {
    const w = await render(People, '/hbos/admin/people')
    const drawer = w.findComponent(DrawerStub)
    const desktop = w.get('.r6-desktop-people')
    await desktop.get('button[aria-label^="查看员工甲"]').trigger('click')
    await flushPromises()
    expect(drawer.props('employeeId')).toBe('EMP-A')
    expect(drawer.props('initialTab')).toBe('basic')

    await desktop.findAll('button').find(item => item.text() === '设置应用角色')!.trigger('click')
    await flushPromises()
    expect(drawer.props('employeeId')).toBe('EMP-A')
    expect(drawer.props('initialTab')).toBe('apps')

    await desktop.findAll('button').find(item => item.text() === '处理账号')!.trigger('click')
    await flushPromises()
    expect(drawer.props('employeeId')).toBe('EMP-B')
    expect(drawer.props('initialTab')).toBe('account')

    await desktop.findAll('button').find(item => item.text() === '查看关联详情')!.trigger('click')
    await flushPromises()
    expect(drawer.props('employeeId')).toBe('EMP-C')
    expect(drawer.props('initialTab')).toBe('basic')
    expect(w.text()).not.toContain('查看安排')
  })

  it('renders an explicit unavailable scope state instead of a zero-result empty state', async () => {
    const employees = { items: [employee({})], total: 1, page: 1, page_size: 20 }
    api.listPeople.mockImplementation((query: { category?: string }) => Promise.resolve(query.category === 'pending'
      ? { items: [], total: 0, page: 1, page_size: 20, unavailable: true }
      : employees))
    const w = await render(People, '/hbos/admin/people')
    const pendingTab = Array.from(document.body.querySelectorAll<HTMLElement>('.ant-tabs-tab')).find(row => row.textContent?.includes('待关联账号'))
    expect(pendingTab).toBeDefined()
    pendingTab!.click()
    await flushPromises()
    expect(api.listPeople).toHaveBeenLastCalledWith(expect.objectContaining({ category: 'pending' }))
    expect(w.text()).toContain('当前分类暂不可用')
    expect(w.text()).toContain('具名委派范围')
    expect(w.text()).not.toContain('没有符合条件的员工或账号')
    expect(w.text()).not.toContain('这些账号尚未明确关联员工档案')
  })

  it('names a linked unresolved association as manual review and opens the primary-key detail path instead of a fake confirmation', async () => {
    const w = await render(People, '/hbos/admin/people')
    const drawer = w.findComponent(DrawerStub)
    expect(w.text()).not.toContain('核对账号关联')
    const unopenedTask = w.find('button[aria-label="开通账号：员工乙"]')
    expect(unopenedTask.exists()).toBe(true)
    const anomaly = w.find('button[aria-label^="关联异常，人工核查"]')
    expect(anomaly.exists()).toBe(true)
    expect(anomaly.attributes('title')).toContain('本页没有安全确认命令')
    await anomaly.trigger('click')
    await flushPromises()
    expect(drawer.props('employeeId')).toBe('EMP-C')
    expect(drawer.props('initialTab')).toBe('basic')
  })

  it('keeps the overview counts page-local when directing to the first pending row', async () => {
    const w = await render(People, '/hbos/admin/people')
    const cards = w.findAll('.r6-overview')
    expect(cards[1]!.text()).toContain('1')
    expect(cards[2]!.text()).toContain('1')
    const calls = api.listPeople.mock.calls.length
    await cards[1]!.trigger('click')
    await flushPromises()
    expect(api.listPeople).toHaveBeenCalledTimes(calls)
    expect(cards[1]!.text()).toContain('1')
    expect(cards[2]!.text()).toContain('1')
    expect(document.activeElement?.textContent).toContain('处理账号')
    expect(JSON.stringify(api.listPeople.mock.calls)).not.toContain('pending')
  })

  it('counts and jumps only to linked rows whose association is unresolved, never to an unopened account', async () => {
    const w = await render(People, '/hbos/admin/people')
    const cards = w.findAll('.r6-overview')
    expect(cards[2]!.text()).toContain('1')
    await cards[2]!.trigger('click')
    await flushPromises()
    const target = document.activeElement as HTMLElement | null
    expect(target?.getAttribute('aria-label')).toContain('关联异常，人工核查')
    expect(target?.getAttribute('aria-label')).toContain('员工丙')
    expect(target?.getAttribute('aria-label')).not.toContain('员工乙')
  })
})

describe('R6 audit redaction', () => {
  it('never renders password, token or cookie fields from an audit snapshot', async () => {
    api.getAuditEvent.mockResolvedValue({
      name: 'EV-1', actor: 'hr@example.test', operation: 'role.publish', subject_type: 'HBOS IAM App Role',
      subject_name: 'role-1', result: 'success', occurred_at: '2026-10-27 10:00',
      before: { role_key: 'staff', password: 'password-secret-value' },
      after: { token: 'token-secret-value', nested: { cookie: 'cookie-secret-value', allowed: true } },
    })
    const w = await render(Audit, '/hbos/admin/audit')
    await click(w, '查看详情')
    const text = modalText()
    expect(text).toContain('普通员工')
    expect(text).toContain('是')
    expect(text).not.toContain('password-secret-value')
    expect(text).not.toContain('token-secret-value')
    expect(text).not.toContain('cookie-secret-value')
  })
})
