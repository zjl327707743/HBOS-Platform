import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick } from 'vue'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import RoleChoiceGroup from '@/components/iam/RoleChoiceGroup.vue'
import ScopeSelector from '@/components/iam/ScopeSelector.vue'
import AssignmentSummary from '@/components/iam/AssignmentSummary.vue'
import EntityName from '@/components/iam/EntityName.vue'
import MemberAccessList from '@/components/iam/MemberAccessList.vue'
import DepartmentNavigator from '@/components/iam/DepartmentNavigator.vue'
import { memberStatus, roleTitle, sourceLabel } from '@/services/assignmentPresentation'

const wrappers: VueWrapper[] = []
async function render(component: object, options: { props?: Record<string, unknown>; slots?: Record<string, string> } = {}) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: defineComponent({ template: '<div />' }) }] })
  await router.push('/hbos/admin/departments'); await router.isReady()
  const wrapper = mount(component, { attachTo: document.body, props: options.props, slots: options.slots, global: { plugins: [Antd, router] } })
  wrappers.push(wrapper); await flushPromises(); return wrapper
}
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); document.body.innerHTML = '' })

describe('v1.4 display adapter: explicit state mapping', () => {
  it('never turns an unknown or missing admission into automatic inheritance or success', () => {
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'SOMETHING_NEW' }).label).toBe('暂无法确认')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT' }).label).toBe('暂无法确认')
    expect(memberStatus({ source: 'UNKNOWN' }).label).toBe('暂无法确认')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'PENDING' }).admissionAction).toBe('confirm')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'REVOKED' }).label).toBe('已撤销确认')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'REVOKED' }).detail).toContain('重新预览')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'CONFIRMED', effective: true }).label).toBe('可使用')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'CONFIRMED', effective: false }).label).toBe('已确认 · 仍受限')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'CONFIRMED' }).label).toContain('实际状态待核对')
    expect(memberStatus({ source: 'NONE' }).detail).toContain('不等于账号停用')
    expect(memberStatus({ source: 'LEGACY' }).label).toBe('沿用原有安排')
    expect(memberStatus({ source: 'DIRECT' }).label).toBe('单独设置')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', accountStatus: 'unopened' }).label).toBe('待开通账号')
    expect(memberStatus({ source: 'FOLLOW_DEPARTMENT', accountStatus: 'disabled' }).detail).toContain('停用不等于撤销')
  })

  it('keeps the user vocabulary for roles, sources and scope type', () => {
    expect(roleTitle('staff')).toBe('普通员工')
    expect(roleTitle('clerk')).toBe('部门考勤员')
    expect(roleTitle('admin')).toBe('考勤管理员')
    expect(roleTitle('')).toBe('角色待核对')
    expect(roleTitle('', '服务端名称')).toBe('服务端名称')
    expect(sourceLabel('FOLLOW_DEPARTMENT')).toBe('跟随部门')
    expect(sourceLabel('NONE')).toBe('未分配')
    expect(sourceLabel('LEGACY')).toBe('历史安排')
  })
})

describe('v1.4 shared components', () => {
  it('renders three role cards only, never a fourth card, and blocks an unknown catalogue entry', async () => {
    const w = await render(RoleChoiceGroup, { props: {
      modelValue: 'staff', name: 'role-test',
      catalog: [
        { role_key: 'staff', title: '普通员工', boundary_kind: 'SELF', grantable: true, published_revision: 3 },
        { role_key: 'clerk', title: '部门考勤员', boundary_kind: 'DEPARTMENT', grantable: false, reason: '角色尚未发布，暂不能授予。' },
      ],
    } })
    const cards = w.findAll('.r6-choice-card')
    expect(cards).toHaveLength(3)
    expect(cards.map(card => card.attributes('data-role'))).toEqual(['staff', 'clerk', 'admin'])
    expect(w.findAll('input[type="radio"]').map(input => (input.element as HTMLInputElement).value)).toEqual(['staff', 'clerk', 'admin'])
    expect(cards[1].find('input').attributes('disabled')).toBeDefined()
    expect(cards[1].text()).toContain('角色尚未发布，暂不能授予')
    expect(cards[2].find('input').attributes('disabled')).toBeDefined()
    expect(cards[2].text()).toContain('角色目录暂无法读取，不能授予')
    expect(w.text()).toContain('已发布 v3')
    // Selecting a blocked card must not emit a change.
    await cards[1].find('input').trigger('click')
    expect(w.emitted('update:modelValue')).toBeUndefined()
    await cards[0].find('input').trigger('click')
    expect(w.emitted('update:modelValue')).toBeUndefined()
  })

  it('asks for an explicit responsible scope per role and never pre-fills it', async () => {
    const clerk = await render(ScopeSelector, { props: { roleKey: 'clerk', modelValue: [], departments: [{ value: 'D1', label: '生产一部' }] } })
    expect(clerk.find('.r6-scope-control').exists()).toBe(true)
    expect(clerk.text()).toContain('必须明确选择负责部门')
    expect(clerk.text()).toContain('尚未选择负责部门')
    expect(clerk.text()).toContain('不自动包含下级部门')
    clerk.unmount()

    const admin = await render(ScopeSelector, { props: { roleKey: 'admin', modelValue: [], companies: [{ value: 'C1', label: '公司甲' }] } })
    expect(admin.text()).toContain('只能选择一个公司')
    expect(admin.text()).toContain('不授予平台管理能力')
    admin.unmount()

    const staff = await render(ScopeSelector, { props: { roleKey: 'staff', modelValue: [] } })
    expect(staff.text()).toContain('只读取本人考勤与月度结果')
    expect(staff.text()).toContain('不读取同部门其他人')
    expect(staff.find('.r6-scope-control').exists()).toBe(false)
    staff.unmount()

    const none = await render(ScopeSelector, { props: { roleKey: '', modelValue: [] } })
    expect(none.text()).toContain('不通过部门分配角色')
    none.unmount()
  })

  it('shows the four facts separately and states that a confirmation is not effective access', async () => {
    const w = await render(AssignmentSummary, { props: {
      source: 'FOLLOW_DEPARTMENT', roleKey: 'clerk', boundaryKind: 'DEPARTMENT',
      scopes: [{ scope_type: 'DEPARTMENT', scope_ref: 'D1' }, { scope_type: 'DEPARTMENT', scope_ref: 'D2' }],
      scopeLabels: ['生产一部（不含下级）', '生产二部（不含下级）'],
      statusLabel: '2 位成员待确认', statusTone: 'warning',
      reasons: ['已有禁止或临时禁用仍然生效。'],
    } })
    const facts = w.findAll('[data-fact]')
    expect(facts.map(row => row.attributes('data-fact'))).toEqual(['source', 'role', 'scope', 'status'])
    expect(w.text()).toContain('跟随部门默认')
    expect(w.text()).toContain('部门考勤员')
    expect(w.text()).toContain('生产一部（不含下级）、生产二部（不含下级）')
    expect(w.text()).toContain('2 位成员待确认')
    expect(w.text()).toContain('限制仍保留')
    expect(w.text()).not.toContain('全权限')
  })

  it('bounds a long name to two lines and keeps the full value reachable by a real control', async () => {
    const longName = '合成超长姓名验收'.repeat(8)
    const w = await render(EntityName, { props: { name: longName, meta: 'T-001', interactive: true } })
    expect(w.find('.r6-entity-name__label').classes()).not.toContain('is-clamped')
    const details = w.find('details.r6-entity-name__more')
    expect(details.exists()).toBe(true)
    expect(details.find('summary').text()).toBe('查看完整名称')
    expect(details.text()).toContain(longName)
    expect(w.find('.r6-entity-name__meta').text()).toContain('T-001')
    await w.find('.r6-entity-name__label').trigger('click')
    expect(w.emitted('activate')).toHaveLength(1)
  })

  it('lists member rows with explicit states, filters and per-person actions only', async () => {
    const rows = [
      { employee: 'E1', name: '待确认员工', employeeNumber: 'T1', source: 'FOLLOW_DEPARTMENT' as const, roleName: '部门考勤员', scopeText: '生产一部（不含下级）', status: memberStatus({ source: 'FOLLOW_DEPARTMENT', admissionState: 'PENDING' }), canConfirm: true, canRevoke: false, personalException: false },
      { employee: 'E2', name: '单独员工', employeeNumber: 'T2', source: 'DIRECT' as const, roleName: '按个人设置', scopeText: '由个人单独设置决定', status: memberStatus({ source: 'DIRECT' }), canConfirm: false, canRevoke: false, personalException: true },
    ]
    const w = await render(MemberAccessList, { props: { rows, total: 4 } })
    expect(w.text()).toContain('待确认角色')
    expect(w.text()).toContain('单独设置')
    expect(w.text()).toContain('另有 2 位未返回权限明细')
    expect(w.findAll('.r6-members__table button').filter(row => row.text() === '确认角色')).toHaveLength(1)
    const confirm = w.findAll('.r6-members__table button').find(row => row.text() === '确认角色')!
    await confirm.trigger('click')
    expect(w.emitted('confirm')).toHaveLength(1)
    // Filtering by source narrows the list without inventing rows.
    const selects = w.findAllComponents({ name: 'ASelect' })
    selects[0].vm.$emit('update:value', 'DIRECT')
    await nextTick()
    expect(w.text()).toContain('单独员工')
    expect(w.text()).not.toContain('待确认员工')
  })

  it('never renders a zero follower count when the read failed', async () => {
    const w = await render(MemberAccessList, { props: { rows: [], loading: false, error: '部门成员读取失败' } })
    expect(w.text()).toContain('部门成员读取失败')
    expect(w.find('.r6-members__table').exists()).toBe(false)
    const unavailable = await render(MemberAccessList, { props: { rows: [], unavailable: true } })
    expect(unavailable.text()).toContain('暂无法读取本部门成员权限')
    expect(unavailable.text()).toContain('未按 0 人处理')
  })

  it('keeps department names bounded in the directory and exposes the full path on demand', async () => {
    const longName = '合成超长部门名称验收'.repeat(6)
    const w = await render(DepartmentNavigator, { props: {
      entries: [
        { id: 'D1', name: '生产一部', depth: 0 },
        { id: 'D2', name: longName, depth: 1, path: '海滨公司 / ' + longName },
      ],
      selected: 'D2', search: '',
    } })
    const rows = w.findAll('.r6-department-row')
    expect(rows).toHaveLength(2)
    expect(rows[1].find('.r6-department-row__label').classes()).toContain('is-clamped')
    expect(rows[1].find('.r6-department-row__more').attributes('aria-expanded')).toBe('false')
    await rows[1].find('.r6-department-row__more').trigger('click')
    expect(rows[1].find('.r6-department-row__full').text()).toContain(longName)
    expect(rows[1].find('.r6-department-row__full').text()).toContain('海滨公司')
    // Search is always present, not hidden behind an explanation.
    expect(w.find('[aria-label="搜索部门"]').exists()).toBe(true)
    expect(rows[0].find('.r6-department-row__more').exists()).toBe(false)
  })
})

describe('v1.4 status tone: never green for an unusable or unknown state', () => {
  it('maps unusable, limited, unknown and usable states to distinct tones', async () => {
    const { statusTone } = await import('@/services/assignmentPresentation')
    expect(statusTone('当前暂不可用')).toBe('warning')
    expect(statusTone('已确认 · 仍受限')).toBe('warning')
    expect(statusTone('待核对')).toBe('warning')
    expect(statusTone('待确认角色')).toBe('warning')
    expect(statusTone('已撤销确认')).toBe('warning')
    expect(statusTone('安排已生效')).toBe('success')
    expect(statusTone('可使用')).toBe('success')
    expect(statusTone(undefined)).toBe('neutral')
    expect(statusTone('')).toBe('neutral')
    expect(statusTone('可使用', true)).toBe('warning')
  })
})
