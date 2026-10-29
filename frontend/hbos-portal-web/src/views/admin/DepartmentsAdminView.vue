<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { ApartmentOutlined, CalendarOutlined, FilterOutlined, InfoCircleOutlined, RightOutlined, SafetyCertificateOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons-vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { listDepartments } from '@/services/iamDepartments'
import { getDepartmentWork } from '@/services/iamWork'
import { canIam, iamMessage, iamSession } from '@/services/iamAccess'
import { roleQuery, roleCommand, assertRolePreview, type RoleAssignment, type RolePreview, type DepartmentAdmissionPreview, type RoleScope, type RoleImpactMember } from '@/services/iamRoles'
import type { DepartmentSummary, WorkApp } from '@/types/iam'
import WorkSettings from '@/components/iam/WorkSettings.vue'
import EmployeeDrawer from '@/components/iam/EmployeeDrawer.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import PanelFrame from '@/components/iam/PanelFrame.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import ChangeReview from '@/components/iam/ChangeReview.vue'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { useAccountProof } from '@/composables/useAccountProof'

const route = useRoute(), activeTab = ref(canIam('iam.access.read') ? 'apps' : 'members')
const viewGroup = ref('daily'), groupsAvailable = ref(false), companies = ref<Array<{ id: string; name: string }>>([]), company = ref(''), treeSearch = ref(''), directoryFiltersOpen = ref(false)
const departments = ref<DepartmentSummary[]>([]), selected = ref(''), apps = ref<WorkApp[]>([]), editingApp = ref<string | null>(null), search = ref(''), page = ref(1), loading = ref(true), error = ref(''), employeeId = ref(''), drawerOpen = ref(false)
const settings = ref<InstanceType<typeof WorkSettings> | null>(null)
const current = computed(() => departments.value.find(row => row.id === selected.value))
const members = computed(() => (current.value?.members || []).filter(row => !search.value || [row.name, row.employee_number, row.position].join(' ').toLowerCase().includes(search.value.toLowerCase())))
const activeAppId = ref('attendance')
const appEntries = computed(() => [...apps.value].sort((left, right) => left.app_id === 'attendance' ? -1 : right.app_id === 'attendance' ? 1 : left.title.localeCompare(right.title)))
const integratedApps = computed(() => appEntries.value.filter(row => row.integrated))
const unintegratedApps = computed(() => appEntries.value.filter(row => !row.integrated))
const activeAppTitle = computed(() => appEntries.value.find(row => row.app_id === activeAppId.value)?.title || (activeAppId.value === 'attendance' ? '考勤管理' : activeAppId.value))
const visibleMemberCount = computed(() => current.value?.member_count ?? current.value?.members?.length)
const canReadApps = computed(() => canIam('iam.access.read'))
const canManageDepartmentRole = computed(() => canIam('iam.departments.manage') && canIam('iam.roles.assign'))
const columns = [{ title: '姓名 / 工号', key: 'name', width: '30%' }, { title: '岗位', dataIndex: 'position', width: '28%' }, { title: '账号状态', key: 'status', width: '22%' }, { title: '操作', key: 'action', width: '20%' }]
const linkTarget = () => typeof route.query.department === 'string' ? route.query.department : undefined

const ROLE_META = {
  staff: { key: 'staff', title: '普通员工', purpose: '跟随者可查看自己的考勤', scope: '仅本人', icon: UserOutlined, capability: '每名跟随者只读取本人考勤记录与月度结果' },
  clerk: { key: 'clerk', title: '部门考勤员', purpose: '协助负责部门核对日常考勤', scope: '明确负责的部门，不含下级', icon: TeamOutlined, capability: '部门考勤面板与指定部门员工考勤' },
  admin: { key: 'admin', title: '考勤管理员', purpose: '在获准公司内办理考勤管理', scope: '明确指定的一个公司', icon: SafetyCertificateOutlined, capability: '公司考勤、班次、更正与导出；不是平台管理员' },
} as const
const ROLE_KEYS = ['staff', 'clerk', 'admin'] as const

const departmentRoleCatalog = ref<Array<{ role_key: string; title: string; boundary_kind: string; grantable: boolean; reason?: string }>>([])
const roleCards = computed(() => ROLE_KEYS.map(key => {
  const meta = ROLE_META[key], catalog = departmentRoleCatalog.value.find(row => row.role_key === key)
  return { ...meta, grantable: catalog ? catalog.grantable : true, reason: catalog?.reason || '' }
}))
const departmentCurrent = ref<RoleAssignment | null>(null), departmentChoice = ref(''), departmentScopeRefs = ref<string[]>([])
const departmentPreview = ref<RolePreview | null>(null)
const baselineImpact = ref<RolePreview | null>(null), baselineStatus = ref<'idle' | 'loading' | 'ready' | 'error' | 'unavailable'>('idle'), baselineError = ref('')
const departmentBusy = ref(false), departmentError = ref(''), departmentMustRead = ref(false)
const departmentProof = useAccountProof(() => { departmentPreview.value = null })
let departmentReadGeneration = 0, departmentActionGeneration = 0, departmentRequestId = '', departmentRequestPayload = ''
let refreshOnActivation = false

const currentRoleKey = computed(() => {
  if (!departmentCurrent.value) return ''
  if (departmentCurrent.value.has_role_default === false) return 'LEGACY'
  return ['staff', 'clerk', 'admin'].includes(departmentCurrent.value.role_key) ? departmentCurrent.value.role_key : ''
})
const currentScopeRefs = computed(() => (departmentCurrent.value?.responsibilities || []).map(row => row.scope_ref))
const departmentDirty = computed(() => Boolean(departmentCurrent.value) && departmentStateKey(departmentChoice.value, departmentScopeRefs.value) !== departmentStateKey(currentRoleKey.value, currentScopeRefs.value))
const baselineLoading = computed(() => baselineStatus.value === 'loading')
const departmentHasScope = computed(() => canManageDepartmentRole.value && baselineStatus.value === 'ready' && Boolean(departmentCurrent.value))
const departmentCanEdit = computed(() => departmentHasScope.value && !departmentMustRead.value)
const baselineLegacy = computed(() => departmentCurrent.value?.has_role_default === false)
const currentDepartmentText = computed(() => departmentText(currentRoleKey.value, currentScopeRefs.value))
const nextDepartmentText = computed(() => departmentText(departmentChoice.value, departmentScopeRefs.value))
const departmentReadOnlyMessage = computed(() => {
  if (baselineLoading.value) return '正在核对部门默认和跟随范围，请稍候。'
  if (baselineStatus.value === 'error') return baselineError.value || '当前无法核对部门影响范围，请重试。'
  if (baselineError.value) return baselineError.value
  return '当前账号只有查看权限，部门成员和个人安排仍可查看。'
})
const departmentFooterMessage = computed(() => departmentMustRead.value ? '请先读取最新部门安排；当前草稿会保留。' : baselineStatus.value === 'error' ? '暂无法读取当前部门安排；未显示任何计数。' : '当前账号没有该部门的修改权限；已有个人安排与限制保持不变。')
const departmentFooterStateText = computed(() => {
  if (departmentMustRead.value) return '暂无法确认最新内容；草稿已保留'
  if (baselineStatus.value === 'error') return '暂无法读取当前部门安排'
  if (!canManageDepartmentRole.value) return '只读：当前账号没有该部门的修改权限'
  if (baselineStatus.value === 'unavailable') return '只读：当前账号不能核对这个部门的影响范围'
  if (baselineStatus.value === 'loading') return '正在核对当前部门安排…'
  if (departmentDirty.value) return '有未保存的修改'
  if (departmentPreview.value) return '已打开影响预览'
  return '与当前部门默认一致 · 未修改'
})
const departmentValidationMessage = computed(() => departmentValidation())
const departmentPrimaryReason = computed(() => {
  if (!departmentCanEdit.value) return ''
  if (departmentBusy.value) return '正在处理，请稍候'
  if (departmentMustRead.value) return '请先读取最新部门安排'
  if (!departmentCurrent.value) return '请先读取当前部门默认'
  if (departmentPreview.value) return '请先完成预览中的保存或返回修改'
  return departmentValidationMessage.value
})
const canSubmitDepartment = computed(() => Boolean(departmentPreview.value?.changed) && departmentProof.valid.value && departmentProof.method.value === 'password' && !departmentBusy.value && departmentCanEdit.value)
const baselineMembers = computed(() => baselineImpact.value?.members || [])
const baselinePersonal = computed(() => baselineImpact.value?.personal || [])
const candidateMembers = computed(() => departmentPreview.value?.members || [])
const candidatePersonal = computed(() => departmentPreview.value?.personal || [])
const baselineRestrictions = computed(() => baselineMembers.value.filter(row => /禁止|暂停|期限|失效|过期|停用|待复核|限制|待确认准入/.test(row.reason || '')))
const isManagementDefault = computed(() => departmentCurrent.value?.has_role_default !== false && ['clerk', 'admin'].includes(departmentCurrent.value?.role_key || ''))
const departmentScopeOptions = computed(() => departments.value.filter(row => row.confirmed).map(row => ({ value: row.id, label: `${row.name}${row.company ? ' · ' + row.company : ''}` })))
const companyScopeOptions = computed(() => companies.value.map(row => ({ value: row.id, label: row.name })))
const scopeHint = computed(() => departmentChoice.value === 'clerk' ? '必须明确选择部门，不含下级' : departmentChoice.value === 'admin' ? '恰好一个公司，不是平台管理员' : '无需另外选择')

type DepartmentTreeNode = { key: string; title: string; children: DepartmentTreeNode[] }
type DepartmentEntry = { id: string; name: string; depth: number }
const tree = computed<DepartmentTreeNode[]>(() => {
  const included = new Set<string>(), query = treeSearch.value.trim().toLowerCase()
  for (const row of departments.value.filter(row => !query || row.name.toLowerCase().includes(query))) {
    let item: DepartmentSummary | undefined = row
    while (item && !included.has(item.id)) { included.add(item.id); item = departments.value.find(parent => parent.id === item!.parent_department) }
  }
  const visited = new Set<string>()
  const build = (parent: string | null): DepartmentTreeNode[] => departments.value.filter(row => !visited.has(row.id) && included.has(row.id) && ((row.parent_department || null) === parent || parent === null && row.parent_department && !departments.value.some(item => item.id === row.parent_department))).map(row => { visited.add(row.id); return { key: row.id, title: row.name, children: build(row.id) } })
  return build(null)
})
const departmentEntries = computed<DepartmentEntry[]>(() => {
  const flatten = (nodes: DepartmentTreeNode[], depth = 0): DepartmentEntry[] => nodes.flatMap(node => [
    { id: node.key, name: node.title, depth },
    ...flatten(node.children, depth + 1),
  ])
  return flatten(tree.value)
})

const admissionTarget = ref<{ employee: string; name: string; number?: string; action: 'confirm' | 'revoke' } | null>(null)
const admissionPreview = ref<DepartmentAdmissionPreview | null>(null)
const admissionBusy = ref(false), admissionError = ref('')
const admissionProof = useAccountProof(() => { admissionPreview.value = null })
let admissionRequestId = '', admissionRequestSignature = ''

let generation = 0, appRead = 0, linkRead = 0, routeRevision = 0, disposed = false
function departmentStateKey(choice: string, scopes: string[]) { return JSON.stringify([choice, [...scopes].sort()]) }
function scopeLabel(ref: string) {
  const department = departments.value.find(row => row.id === ref)
  if (department) return `${department.name}（不含下级）`
  const companyRow = companies.value.find(row => row.id === ref)
  return companyRow?.name || ref || '待核对'
}
function departmentText(choice: string, scopes: string[]) {
  if (choice === 'LEGACY') return '沿用已有安排'
  if (choice === 'staff') return '普通员工 · 仅本人'
  if (choice === 'clerk') return `部门考勤员 · ${scopes.map(scopeLabel).join('、') || '负责范围待选择'}`
  if (choice === 'admin') return `考勤管理员 · ${scopes.map(scopeLabel).join('、') || '负责公司待选择'}`
  return '不通过部门分配 · 不从此部门获得考勤角色'
}
function countText(value?: number) { return typeof value === 'number' ? String(value) : '待核对' }
function currentRoleAndScopes() {
  if (!departmentCurrent.value) return { role: '', scopes: [] as string[] }
  if (departmentCurrent.value.has_role_default === false) return { role: 'LEGACY', scopes: [] as string[] }
  return { role: departmentCurrent.value.role_key || '', scopes: (departmentCurrent.value.responsibilities || []).map(row => row.scope_ref) }
}
function resetDepartmentDraft() {
  const state = currentRoleAndScopes()
  departmentChoice.value = state.role; departmentScopeRefs.value = [...state.scopes]
  departmentPreview.value = null; departmentError.value = ''
  departmentRequestId = ''; departmentRequestPayload = ''
  departmentProof.invalidate()
}
function clearDepartmentState() {
  departmentReadGeneration++; departmentActionGeneration++; departmentBusy.value = false
  departmentCurrent.value = null; departmentChoice.value = ''; departmentScopeRefs.value = []; departmentPreview.value = null
  baselineImpact.value = null; baselineStatus.value = 'idle'; baselineError.value = ''
  departmentError.value = ''; departmentMustRead.value = false
  departmentRequestId = ''; departmentRequestPayload = ''
  departmentRoleCatalog.value = []
  activeAppId.value = 'attendance'; editingApp.value = null
  closeAdmission()
  departmentProof.invalidate()
}
async function confirmDiscardDepartmentDraft() {
  if (!departmentDirty.value) return true
  return new Promise<boolean>(resolve => Modal.confirm({
    title: '放弃尚未保存的部门默认角色？',
    content: '已保存的部门默认与个人安排不受影响。',
    okText: '放弃草稿', cancelText: '继续编辑',
    onOk: () => { resetDepartmentDraft(); resolve(true) },
    onCancel: () => resolve(false),
  }))
}
async function requestLeave() {
  if (departmentBusy.value) return false
  if (!await confirmDiscardDepartmentDraft()) return false
  if (admissionTarget.value) return false
  if (settings.value && !await settings.value.requestLeave()) return false
  return true
}
async function cancelDepartmentEdit() {
  if (!departmentDirty.value) { resetDepartmentDraft(); return }
  await confirmDiscardDepartmentDraft()
}
function departmentValidation(): string {
  if (!departmentCurrent.value) return ''
  if (departmentChoice.value === 'LEGACY') return '当前沿用已有安排；请选择一个明确的角色后再核对。'
  if (!['staff', 'clerk', 'admin', ''].includes(departmentChoice.value)) return '请选择部门默认角色。'
  if (departmentChoice.value === 'clerk' && !departmentScopeRefs.value.length) return '部门考勤员必须明确选择至少一个负责部门（不含下级）。'
  if (departmentChoice.value === 'admin' && departmentScopeRefs.value.length !== 1) return '考勤管理员必须明确选择一个公司。'
  return ''
}
function chooseRole(key: string) {
  if (key === 'LEGACY' || departmentBusy.value || departmentMustRead.value || departmentPreview.value) return
  const catalog = departmentRoleCatalog.value.find(row => row.role_key === key)
  if (catalog && !catalog.grantable) { departmentError.value = catalog.reason || '当前账号不能授予这个角色。'; return }
  departmentChoice.value = key
  departmentScopeRefs.value = []
  departmentPreview.value = null
  departmentError.value = ''
}
function setScopeRefs(values: unknown) {
  departmentScopeRefs.value = Array.isArray(values) ? values.map(String) : values ? [String(values)] : []
  departmentPreview.value = null
}
function departmentResponsibilities(): RoleScope[] {
  if (departmentChoice.value === 'clerk') return departmentScopeRefs.value.map(scope_ref => ({ scope_type: 'DEPARTMENT', scope_ref, include_descendants: 0 }))
  if (departmentChoice.value === 'admin') return departmentScopeRefs.value.slice(0, 1).map(scope_ref => ({ scope_type: 'COMPANY', scope_ref, include_descendants: 0 }))
  return []
}
async function loadDepartmentRole(preserve = false) {
  const id = selected.value
  if (!id || !iamSession.rolesEnabled || !canReadApps.value) { clearDepartmentState(); return }
  const run = ++departmentReadGeneration
  const keep = preserve && Boolean(departmentCurrent.value)
  if (!keep) { departmentCurrent.value = null; departmentChoice.value = ''; departmentScopeRefs.value = []; departmentPreview.value = null; departmentMustRead.value = false; departmentError.value = ''; departmentRequestId = ''; departmentRequestPayload = '' }
  baselineImpact.value = null; baselineError.value = ''; baselineStatus.value = 'loading'
  departmentPreview.value = null
  try {
    const next = await roleQuery<RoleAssignment>('get_department_role', { department: id })
    if (disposed || run !== departmentReadGeneration || selected.value !== id) return
    departmentCurrent.value = next
    departmentRoleCatalog.value = next.roles || []
    if (!keep) resetDepartmentDraft()
    else { departmentMustRead.value = false; departmentError.value = ''; departmentProof.invalidate() }
    if (!canManageDepartmentRole.value) { baselineStatus.value = 'unavailable'; return }
    const state = currentRoleAndScopes()
    try {
      const impact = assertRolePreview(await roleCommand<RolePreview>('preview_department_role', {
        department: id, role_key: state.role === 'LEGACY' ? '' : state.role,
        responsibilities: state.role === 'clerk' || state.role === 'admin'
          ? state.scopes.map(scope_ref => ({ scope_type: state.role === 'clerk' ? 'DEPARTMENT' : 'COMPANY', scope_ref, include_descendants: 0 }))
          : [],
        expected_version: next.version,
      }))
      if (disposed || run !== departmentReadGeneration || selected.value !== id) return
      baselineImpact.value = impact
      baselineStatus.value = 'ready'
    } catch (e) {
      if (disposed || run !== departmentReadGeneration || selected.value !== id) return
      baselineImpact.value = null
      const status = (e as { status?: number }).status
      baselineError.value = status === 403
        ? '当前账号不能核对这个部门的影响范围。请联系具备该部门权限的其他管理员处理。'
        : iamMessage(e)
      baselineStatus.value = status === 403 ? 'unavailable' : 'error'
    }
  } catch (e) {
    if (disposed || run !== departmentReadGeneration || selected.value !== id) return
    baselineImpact.value = null
    baselineError.value = iamMessage(e)
    baselineStatus.value = 'error'
    if (keep) departmentMustRead.value = true
  }
}
async function prepareDepartmentRole() {
  if (departmentBusy.value || departmentMustRead.value || !departmentCanEdit.value || !departmentDirty.value) return
  const invalid = departmentValidation()
  if (invalid) { departmentError.value = invalid; return }
  const run = ++departmentActionGeneration
  const id = selected.value, version = departmentCurrent.value?.version, choice = departmentChoice.value
  const responsibilities = departmentResponsibilities()
  if (!id || version === undefined) { departmentError.value = '请先读取当前部门默认。'; return }
  departmentBusy.value = true; departmentError.value = ''; departmentProof.invalidate()
  try {
    const payload = { department: id, role_key: choice === 'LEGACY' ? '' : choice, responsibilities, expected_version: version }
    const signature = JSON.stringify(payload)
    if (departmentRequestId && departmentRequestPayload !== signature) { departmentRequestId = ''; departmentRequestPayload = '' }
    const next = await roleCommand<RolePreview>('preview_department_role', payload)
    if (disposed || run !== departmentActionGeneration || selected.value !== id || departmentChoice.value !== choice || departmentCurrent.value?.version !== version) return
    assertRolePreview(next)
    if (!departmentRequestId) departmentRequestId = crypto.randomUUID()
    departmentRequestPayload = signature
    departmentPreview.value = next
  } catch (e) {
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    departmentError.value = iamMessage(e)
    const status = (e as { status?: number }).status
    if (status === 409 || status === 500) departmentMustRead.value = true
    departmentProof.invalidate()
    departmentPreview.value = null
  } finally { if (run === departmentActionGeneration) departmentBusy.value = false }
}
async function commitDepartmentRole() {
  if (!canSubmitDepartment.value || !departmentCurrent.value || !departmentPreview.value) return
  const run = ++departmentActionGeneration
  const id = selected.value, version = departmentCurrent.value.version, choice = departmentChoice.value
  const preview = departmentPreview.value
  departmentBusy.value = true; departmentError.value = ''
  try {
    await roleCommand('save_department_role', {
      department: id, role_key: choice === 'LEGACY' ? '' : choice, responsibilities: departmentResponsibilities(),
      expected_version: version, context_revision: preview.context_revision, request_id: departmentRequestId,
    })
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    departmentProof.invalidate(); departmentPreview.value = null
    departmentRequestId = ''; departmentRequestPayload = ''
    departmentMustRead.value = false
    await loadDepartmentRole(); await loadApps()
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    message.success('部门默认角色已保存；管理型角色需逐人确认准入后才生效，已有个人安排和限制继续保留。')
  } catch (e) {
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    departmentError.value = iamMessage(e); departmentMustRead.value = true
    departmentProof.invalidate(); departmentPreview.value = null
  } finally { if (run === departmentActionGeneration) departmentBusy.value = false }
}
function closeDepartmentPreview() { departmentPreview.value = null; departmentProof.invalidate() }

const admissionTitle = computed(() => admissionTarget.value?.action === 'revoke' ? '撤销部门管理角色准入' : '确认部门管理角色准入')
const canSubmitAdmission = computed(() => Boolean(admissionPreview.value?.changed) && admissionProof.valid.value && admissionProof.method.value === 'password' && !admissionBusy.value)
async function openAdmission(member: Partial<RoleImpactMember> & { employee: string }, action: 'confirm' | 'revoke') {
  if (!departmentCurrent.value) return
  admissionTarget.value = { employee: member.employee, name: member.name || member.employee, number: member.employee_number, action }
  admissionPreview.value = null; admissionError.value = ''; admissionProof.invalidate()
  admissionBusy.value = true
  try {
    const preview = await roleCommand<DepartmentAdmissionPreview>('preview_department_admission', {
      department: selected.value, employee_id: member.employee, expected_version: departmentCurrent.value.version, action,
    })
    if (!admissionTarget.value || admissionTarget.value.employee !== member.employee) return
    admissionPreview.value = preview
  } catch (e) { admissionError.value = iamMessage(e) } finally { admissionBusy.value = false }
}
function closeAdmission() { admissionRequestId = ''; admissionRequestSignature = ''; admissionPreview.value = null; admissionTarget.value = null; admissionError.value = ''; admissionProof.invalidate() }
async function commitAdmission() {
  if (!admissionTarget.value || !admissionPreview.value || !canSubmitAdmission.value) return
  admissionBusy.value = true; admissionError.value = ''
  try {
    const signature = JSON.stringify([admissionPreview.value.admission_hash, admissionTarget.value.action, departmentCurrent.value?.version])
    if (!admissionRequestId || admissionRequestSignature !== signature) { admissionRequestId = crypto.randomUUID(); admissionRequestSignature = signature }
    await roleCommand('save_department_admission', {
      department: selected.value, employee_id: admissionTarget.value.employee, action: admissionTarget.value.action,
      expected_version: departmentCurrent.value?.version, context_revision: admissionPreview.value.context_revision, request_id: admissionRequestId,
    })
    admissionProof.invalidate()
    message.success(admissionTarget.value.action === 'revoke' ? '部门管理角色准入已撤销。' : '准入已确认；刷新后按已发布角色与服务端结果生效。')
    closeAdmission()
    await loadDepartmentRole()
  } catch (e) { admissionError.value = iamMessage(e); admissionProof.invalidate() } finally { admissionBusy.value = false }
}

function viewEmployeeAssignment(id: string) {
  if (!canIam('iam.people.read')) return
  employeeId.value = id
  drawerOpen.value = true
}
function revealSelectedDepartment() {
  if (typeof document === 'undefined') return
  const row = document.querySelector<HTMLElement>('.r6-department-row[aria-current="page"]')
  const panel = row?.closest<HTMLElement>('.r6-panel-scroll')
  if (!row || !panel) return
  const panelRect = panel.getBoundingClientRect()
  const rowRect = row.getBoundingClientRect()
  if (rowRect.top < panelRect.top) panel.scrollTop -= panelRect.top - rowRect.top
  else if (rowRect.bottom > panelRect.bottom) panel.scrollTop += rowRect.bottom - panelRect.bottom
}
watch([loading, selected, departmentEntries], async () => { if (loading.value) return; await nextTick(); revealSelectedDepartment() }, { flush: 'post' })

async function loadApps() {
  const run = ++appRead, id = selected.value; apps.value = []
  if (!canReadApps.value || !id) return
  try {
    const result = await getDepartmentWork(id)
    if (disposed || run !== appRead || selected.value !== id) return
    apps.value = result.apps
    if (editingApp.value && !apps.value.some(row => row.app_id === editingApp.value && row.integrated)) editingApp.value = null
  } catch (e) { if (!disposed && run === appRead) { apps.value = []; error.value = iamMessage(e) } }
}
function routeLinkTarget() {
  return {
    department: linkTarget() || '',
    tab: typeof route.query.tab === 'string' ? route.query.tab : '',
    app: typeof route.query.app === 'string' ? route.query.app : '',
    viewGroup: viewGroup.value,
    company: company.value,
  }
}
async function applyLink(refreshRole = false) {
  const target = routeLinkTarget()
  const run = ++linkRead
  if (!target.department) return
  const currentTarget = () => !disposed && run === linkRead && routeLinkTarget().department === target.department && routeLinkTarget().tab === target.tab && routeLinkTarget().app === target.app && routeLinkTarget().viewGroup === target.viewGroup && routeLinkTarget().company === target.company
  if (!departments.value.some(row => row.id === target.department)) {
    const data = await listDepartments(target.viewGroup, target.department, target.company || undefined)
    if (!currentTarget()) return
    departments.value = data.items
  }
  if (!currentTarget()) return
  if (!departments.value.some(row => row.id === target.department)) { editingApp.value = null; activeTab.value = 'members'; error.value = '该部门或应用当前不可查看，已返回可用部门。'; return }
  const selectionChanged = selected.value !== target.department
  if (selectionChanged) { selected.value = target.department; clearDepartmentState() }
  activeTab.value = target.tab === 'apps' && canReadApps.value ? 'apps' : 'members'
  await loadApps()
  if (!currentTarget()) return
  if (selectionChanged || refreshRole) await loadDepartmentRole()
  if (!currentTarget()) return
  editingApp.value = current.value?.confirmed && activeTab.value === 'apps' && target.app && target.app !== 'attendance' && apps.value.some(row => row.app_id === target.app && row.integrated) ? target.app : null
  activeAppId.value = editingApp.value || 'attendance'
  if (target.app && target.app !== 'attendance' && editingApp.value !== target.app) error.value = '该部门或应用当前不可查看，已返回可用部门。'
}
async function load() {
  if (!await requestLeave()) return
  const run = ++generation, routeAtStart = routeRevision; loading.value = true; error.value = ''
  try {
    const data = await listDepartments(viewGroup.value, linkTarget(), company.value || undefined)
    if (disposed || run !== generation || routeAtStart !== routeRevision) return
    departments.value = data.items; companies.value = data.companies; company.value = data.selected_company || ''; groupsAvailable.value = data.groups_available === true
    if (!departments.value.some(row => row.id === selected.value)) selected.value = (departments.value.find(row => row.confirmed && row.members?.length) || departments.value.find(row => row.members?.length) || departments.value[0])?.id || ''
    clearDepartmentState()
    if (linkTarget()) await applyLink(true)
    else {
      const id = selected.value
      await loadApps()
      if (disposed || run !== generation || routeAtStart !== routeRevision || selected.value !== id) return
      await loadDepartmentRole()
    }
  } catch (e) { if (!disposed && run === generation && routeAtStart === routeRevision) error.value = iamMessage(e) }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function selectDepartment(id: string) {
  if (!id || id === selected.value || !await requestLeave()) return
  selected.value = id; clearDepartmentState(); editingApp.value = null; search.value = ''; page.value = 1; error.value = ''
  try { await loadApps(); if (!disposed && selected.value === id) await loadDepartmentRole() } catch (e) { if (!disposed) error.value = iamMessage(e) }
}
async function changeCompany(value: string) { if (!await requestLeave()) return; company.value = value; selected.value = ''; editingApp.value = null; await load() }
async function changeGroup(value: string) { if (!await requestLeave()) return; viewGroup.value = value; selected.value = ''; editingApp.value = null; await load() }
function changeTab(value: string) { activeTab.value = value }
function openOtherApp(appId: string) { void selectApp(appId) }
async function selectApp(appId: string) {
  if (appId === activeAppId.value) return
  if (settings.value && !await settings.value.requestLeave()) return
  const entry = appEntries.value.find(row => row.app_id === appId)
  if (!entry?.integrated) return
  activeAppId.value = appId
  departmentError.value = ''
  editingApp.value = appId === 'attendance' ? null : appId
}
onBeforeRouteLeave(() => requestLeave())
onBeforeRouteUpdate(() => requestLeave())
watch(() => route.query, () => { routeRevision++; if (!loading.value) void applyLink().catch(e => { if (!disposed) error.value = iamMessage(e) }) })
useManagementViewMemory('DepartmentsAdminView.vue', { viewGroup, company, treeSearch, selected, activeTab, search, page })
if (treeSearch.value) directoryFiltersOpen.value = true
onMounted(load)
onDeactivated(() => { refreshOnActivation = true })
onActivated(() => { if (!refreshOnActivation) return; refreshOnActivation = false; void load() })
onBeforeUnmount(() => { disposed = true; generation++; appRead++; linkRead++; departmentReadGeneration++; departmentActionGeneration++; apps.value = []; departments.value = [] })
</script>

<template>
  <section class="r6-page r6-departments-page">
    <PageHeading eyebrow="组织管理" title="部门应用权限" description="设置本部门员工在各应用中的默认权限。" />
    <a-skeleton v-if="loading" active />
    <div v-else class="r6-dual-panels">
      <PanelFrame as="aside" region="department-list" label="组织部门目录" class="r6-navigation r6-department-tree">
        <template #header>
          <div class="r6-department-directory-heading">
            <h3>选择部门</h3>
            <a-button type="text" class="r6-department-filter-toggle" :aria-expanded="directoryFiltersOpen" @click="directoryFiltersOpen = !directoryFiltersOpen"><FilterOutlined />筛选部门</a-button>
          </div>
          <div v-if="directoryFiltersOpen" class="r6-department-filters">
            <a-select v-if="groupsAvailable" :value="viewGroup" aria-label="部门分组" @change="changeGroup"><a-select-option value="daily">日常组织</a-select-option><a-select-option value="technical">技术验证夹具</a-select-option><a-select-option value="all">全部部门</a-select-option></a-select>
            <a-select v-if="companies.length > 1" :value="company" aria-label="部门所属公司" @change="changeCompany"><a-select-option v-for="item in companies" :key="item.id" :value="item.id">{{ item.name }}</a-select-option></a-select>
            <a-input v-model:value="treeSearch" placeholder="搜索部门" aria-label="搜索组织部门" allow-clear />
          </div>
        </template>
        <nav class="r6-department-rows" aria-label="部门列表">
          <button v-for="item in departmentEntries" :key="item.id" type="button" class="r6-department-row" :class="{ selected: selected === item.id }" :aria-current="selected === item.id ? 'page' : undefined" :style="{ '--department-indent': `${Math.min(item.depth, 4) * 14}px` }" @click="selectDepartment(item.id)">
            <ApartmentOutlined aria-hidden="true" /><span>{{ item.name }}</span><RightOutlined aria-hidden="true" />
          </button>
          <a-empty v-if="!departmentEntries.length" description="没有匹配的部门" />
        </nav>
        <template #footer>部门默认与个人单独安排分别核对。</template>
      </PanelFrame>
      <PanelFrame region="department-detail" label="部门应用默认权限与成员">
        <template v-if="current" #header>
          <div class="r6-department-panel-heading">
            <div class="r6-department-title">
              <h2>{{ current.name }}</h2>
              <p class="r6-dept-app-subtitle"><CalendarOutlined aria-hidden="true" />{{ activeAppTitle }} · 部门默认权限</p>
              <p class="r6-dept-meta">{{ current.company }} · 主部门可见成员 {{ countText(visibleMemberCount) }} 人（仅当前部门）</p>
            </div>
            <div class="r6-department-view-toggle">
              <span class="r6-dept-panel-icon" aria-hidden="true"><CalendarOutlined /></span>
              <StatusTag v-if="!current.confirmed" tone="warning">尚未确认，暂不安排人员或权限</StatusTag>
              <a-button v-if="activeTab === 'apps' && canReadApps" type="text" @click="changeTab('members')">查看部门成员</a-button>
              <a-button v-else-if="activeTab === 'members' && canReadApps" type="text" @click="changeTab('apps')">返回部门应用权限</a-button>
            </div>
          </div>
        </template>
        <div v-if="error" class="r6-resource-error r6-resource-error-inline"><a-alert :message="error" type="warning" show-icon /><a-button @click="load">重试读取</a-button></div>
        <div v-show="activeTab === 'apps' && canReadApps && current">
          <WorkSettings v-if="editingApp && current?.confirmed" :key="selected + ':' + editingApp" ref="settings" subject-kind="department" :subject-id="selected" :app-id="editingApp" @back="selectApp('attendance')" @saved="loadApps" />
          <div v-show="!editingApp">
          <template v-if="current">
            <template v-if="current.confirmed">
              <template v-if="iamSession.rolesEnabled">
                <template v-if="integratedApps.length > 1">
                  <div class="r6-dept-app-switch" role="tablist" aria-label="选择已接入应用">
                    <button v-for="app in integratedApps" :key="app.app_id" type="button" role="tab" class="r6-dept-app-chip" :class="{ selected: activeAppId === app.app_id }" :aria-selected="activeAppId === app.app_id" @click="selectApp(app.app_id)"><strong>{{ app.title }}</strong><small>已接入</small></button>
                  </div>
                </template>
                <div v-if="departmentError" class="r6-resource-error"><a-alert :message="departmentError" type="warning" show-icon /><a-button :disabled="departmentBusy" @click="loadDepartmentRole(true)">读取最新部门安排，保留草稿</a-button></div>

                <template v-if="activeAppId === 'attendance'">
                  <div class="r6-dept-task-line">设置本部门跟随员工在考勤中的默认角色与负责范围。<details class="r6-dept-details"><summary>说明与兼容状态</summary><p>部门默认只提供该角色的普通安排；个人单独设置、个人禁止、暂停与期限保留，其他应用按各自授权分别管理。</p><p v-if="baselineLegacy">当前状态：沿用已有考勤权限。选择并保存新的部门默认前不会自动转换；具体影响以服务端预览为准。</p><p>“已确认准入”只表示该员工被纳入管理员确认的部门管理角色；未确认或上下文变化时不授予功能。计数均来自服务端，基线不伪造 0。</p></details></div>

                <template v-if="departmentHasScope">
                  <div class="field-section-title"><h3>默认角色</h3><span>与员工页使用同一已发布角色目录</span></div>
                  <div class="r6-role-cards is-department" role="radiogroup" aria-label="部门默认考勤角色">
                    <label v-for="item in roleCards" :key="item.key" class="r6-role-card" :class="{ selected: departmentChoice === item.key, disabled: !item.grantable }">
                      <span class="role-card-icon"><component :is="item.icon" /></span>
                      <input type="radio" :name="`dept-role-${selected}`" :value="item.key" :checked="departmentChoice === item.key" :disabled="!item.grantable || departmentBusy || departmentMustRead || Boolean(departmentPreview)" @change="chooseRole(item.key)" />
                      <strong>{{ item.title }}</strong>
                      <span>{{ item.purpose }}</span>
                      <small>{{ item.scope }}</small>
                      <p class="role-card-capability">{{ item.grantable ? item.capability : (item.reason || '当前账号不能授予这个角色') }}</p>
                    </label>
                    <label class="r6-role-card" :class="{ selected: departmentChoice === '' }">
                      <span class="role-card-icon"><InfoCircleOutlined /></span>
                      <input type="radio" :name="`dept-role-${selected}`" value="" :checked="departmentChoice === ''" :disabled="departmentBusy || departmentMustRead || Boolean(departmentPreview)" @change="chooseRole('')" />
                      <strong>不通过部门分配</strong>
                      <span>不从此部门获得考勤角色</span>
                      <small>不等于停用账号或禁止个人单独授权</small>
                      <p class="role-card-capability">登录账号、个人安排与其他应用保持不变</p>
                    </label>
                  </div>

                  <div class="field-section-title"><h3>负责范围</h3><span>{{ scopeHint }}</span></div>
                  <div v-if="departmentChoice === 'staff'" class="role-self-scope"><strong>仅本人</strong><span>每名跟随员工只读取其本人考勤，不读取同部门其他人。</span></div>
                  <template v-else-if="departmentChoice === 'clerk'">
                    <a-select :value="departmentScopeRefs" mode="multiple" show-search option-filter-prop="label" :options="departmentScopeOptions" placeholder="搜索并选择负责部门，可多选" aria-label="负责部门" :disabled="departmentBusy || departmentMustRead || Boolean(departmentPreview)" @update:value="setScopeRefs" />
                    <p class="role-scope-caption">已选择 {{ departmentScopeRefs.length }} 个部门{{ departmentScopeRefs.length ? '，仅限这些部门' : '' }}。不会自动包含下级部门。</p>
                  </template>
                  <template v-else-if="departmentChoice === 'admin'">
                    <a-select :value="departmentScopeRefs[0]" show-search option-filter-prop="label" :options="companyScopeOptions" placeholder="选择一个负责公司" aria-label="负责公司" :disabled="departmentBusy || departmentMustRead || Boolean(departmentPreview)" @update:value="setScopeRefs" />
                    <p class="role-scope-caption">只限所选公司，不授予平台管理能力、System Manager 或其他应用原生角色。</p>
                  </template>
                  <div v-else class="role-self-scope"><strong>不通过部门分配</strong><span>不从本部门获得考勤角色；登录账号、个人安排和其他应用不变。</span></div>
                </template>
                <div v-else-if="!canManageDepartmentRole" class="r6-dept-readonly r6-dept-permission-state">
                  <strong>{{ currentDepartmentText }}</strong><StatusTag tone="neutral">只读</StatusTag>
                  <p>{{ departmentReadOnlyMessage }}</p>
                </div>
                <div v-else-if="!departmentCurrent" class="r6-dept-readonly">
                  <strong>暂无法读取当前部门安排</strong><StatusTag tone="warning">读取失败</StatusTag>
                  <p>未显示任何跟随人数或权限结果；请重试读取，不沿用旧状态。</p>
                  <div class="r6-dept-baseline-actions"><a-button :disabled="departmentBusy" @click="loadDepartmentRole(true)">重试读取部门安排</a-button></div>
                </div>
                <div v-else class="r6-dept-readonly r6-dept-permission-state">
                  <strong>{{ currentDepartmentText }}</strong>
                  <StatusTag tone="warning">{{ baselineStatus === 'loading' ? '正在读取' : baselineStatus === 'error' ? '暂无法读取' : '只读' }}</StatusTag>
                  <p>{{ departmentReadOnlyMessage }}</p>
                  <div v-if="baselineStatus === 'error'" class="r6-dept-baseline-actions"><a-button :disabled="departmentBusy" @click="loadDepartmentRole(true)">重试读取影响范围</a-button></div>
                </div>

                <template v-if="baselineStatus === 'ready'">
                  <div class="r6-dept-counts r6-dept-counts-four" aria-label="当前部门默认影响">
                    <div><strong>{{ countText(baselineImpact?.reference_count) }}</strong><span>跟随部门默认</span><small>服务端预览</small></div>
                    <div><strong>{{ countText(baselineImpact?.personal_preserved) }}</strong><span>个人例外</span><small>保持不变</small></div>
                    <div><strong>{{ countText(baselineImpact?.pending_count) }}</strong><span>待确认准入</span><small>管理型角色</small></div>
                    <div class="r6-dept-count-pending"><strong>{{ departmentPreview ? countText(departmentPreview.effective_changed_count) : '保存前预览' }}</strong><span>实际权限变化</span><small>由服务端核对</small></div>
                  </div>
                  <p v-if="baselineLoading" class="r6-dept-note" role="status">正在读取当前跟随范围…</p>
                  <template v-else-if="baselineStatus === 'ready'">
                    <div class="r6-dept-follow-head"><h4>影响人员</h4><span>{{ isManagementDefault ? '管理型默认需逐人确认准入' : '普通默认自动继承' }}</span></div>
                    <ul v-if="baselineMembers.length" class="r6-dept-followers">
                      <li v-for="member in baselineMembers" :key="member.employee">
                        <div class="r6-dept-follower-main"><a-avatar :size="34">{{ member.name?.slice(-1) || '员' }}</a-avatar><div><strong>{{ member.name }}</strong><small>{{ member.employee_number || '员工档案' }}</small></div></div>
                        <StatusTag v-if="member.admission_state === 'PENDING'" tone="warning">待确认准入</StatusTag>
                        <StatusTag v-else-if="member.admission_state === 'CONFIRMED'" tone="success">已确认准入</StatusTag>
                        <StatusTag v-else tone="neutral">自动继承</StatusTag>
                        <span class="r6-dept-follower-reason">{{ member.changed ? '实际权限将变化' : (member.reason || '现有权限保持') }}</span>
                        <div class="r6-dept-follower-actions">
                          <a-button v-if="member.admission_state === 'PENDING' && canManageDepartmentRole" size="small" type="primary" :disabled="departmentBusy" @click="openAdmission(member, 'confirm')">确认准入</a-button>
                          <a-button v-if="member.admission_state === 'CONFIRMED' && canManageDepartmentRole" size="small" :disabled="departmentBusy" @click="openAdmission(member, 'revoke')">撤销准入</a-button>
                          <a-button v-if="canIam('iam.people.read')" type="link" @click="viewEmployeeAssignment(member.employee)">查看安排</a-button>
                        </div>
                      </li>
                    </ul>
                    <p v-else-if="(baselineImpact?.reference_count || 0) === 0" class="r6-dept-note">当前没有跟随部门默认的成员。</p>
                    <div v-else class="r6-dept-baseline-error"><p class="r6-dept-note">核对结果未返回跟随成员名单。</p></div>
                    <details v-if="baselinePersonal.length || baselineRestrictions.length" class="r6-dept-restrictions">
                      <summary>个人例外与已有限制（{{ baselinePersonal.length + baselineRestrictions.length }}）</summary>
                      <p v-for="person in baselinePersonal" :key="person.employee"><strong>{{ person.name }}</strong>：{{ person.reason || '个人单独设置或既有安排保留' }}</p>
                      <p v-for="member in baselineRestrictions" :key="'r-' + member.employee"><strong>{{ member.name }}</strong>：{{ member.reason }}</p>
                    </details>
                  </template>
                </template>
                <div v-else-if="baselineStatus === 'error'" class="r6-dept-note">暂无法读取部门影响范围；未显示任何计数，也不沿用旧数据。</div>
                </template>

                <section v-else class="r6-dept-app-unavailable">
                  <div class="application-heading"><span class="app-icon"><CalendarOutlined /></span><div><h3>{{ activeAppTitle }}</h3><p>这个应用尚未接入统一部门角色与范围。</p></div><StatusTag tone="neutral">尚未接入</StatusTag></div>
                  <a-alert type="info" show-icon message="本页只显示注册状态，不提供开关" description="不能把“有入口”当作已授权；本页不会为该应用保存部门默认或个人权限。" />
                </section>

                <details v-if="unintegratedApps.length" class="r6-dept-unintegrated">
                  <summary>其他应用（未接入本管理页）</summary>
                  <p>以下应用的原应用权限不变，本页不对其授权或保存：{{ unintegratedApps.map(app => app.title).join('、') }}。</p>
                </details>
              </template>
              <template v-else>
                <a-alert type="info" show-icon message="应用角色功能尚未启用" description="以下保留原有应用权限兼容入口，不新增角色选择。" />
                <article v-for="app in apps" :key="app.app_id" class="r6-department-app"><div><strong>{{ app.title }}</strong><p>{{ app.integrated ? app.summary : '尚未接入此管理功能，暂不能在此调整。' }}</p></div><a-button v-if="app.integrated" :disabled="!current.confirmed" @click="openOtherApp(app.app_id)">{{ canIam('iam.departments.manage') ? '设置安排' : '查看安排' }}</a-button></article>
              </template>
            </template>
            <a-alert v-else type="warning" show-icon message="部门尚未确认，暂不安排默认角色或人员" description="请先完成部门确认；部门成员仍可在下方查看。" />
          </template>
          </div>
        </div>
        <div v-show="activeTab === 'members' && current">
          <div class="iam-toolbar"><a-input v-model:value="search" class="iam-search" placeholder="搜索姓名、工号或岗位" aria-label="搜索部门成员" allow-clear @change="page = 1" /></div>
          <a-table :columns="columns" :data-source="members" row-key="id" table-layout="fixed" :scroll="{ x: 520 }" :pagination="{ current: page, pageSize: 10, total: members.length, showSizeChanger: false, onChange: (value: number) => page = value }"><template #bodyCell="{ column, record }"><template v-if="column.key === 'name'"><button v-if="canIam('iam.people.read')" class="iam-name" :aria-label="`查看${record.name}的应用角色，工号${record.employee_number}`" @click="employeeId = record.id; drawerOpen = true"><strong>{{ record.name }}</strong></button><strong v-else>{{ record.name }}</strong><span class="iam-code">{{ record.employee_number }}</span></template><template v-else-if="column.key === 'status'"><StatusTag :tone="record.account_status === 'active' ? 'success' : 'neutral'">{{ record.account_status === 'active' ? '已开通' : record.account_status === 'disabled' ? '已停用' : '未开通' }}</StatusTag></template><template v-else-if="column.key === 'action'"><a-button v-if="canIam('iam.people.read')" type="link" @click="employeeId = record.id; drawerOpen = true">查看应用角色</a-button><span v-else class="aux">仅成员状态</span></template></template></a-table>
          <p class="aux">此处仅列主部门成员；兼岗不会自动叠加所属部门权限。个人单独安排与限制逐人核对。</p>
        </div>
        <a-empty v-if="!current" description="暂无可管理部门" />
        <template #footer>
          <template v-if="activeTab === 'apps' && iamSession.rolesEnabled && current?.confirmed">
            <div v-if="editingApp" class="r6-dept-role-actions"><span>其他应用沿用各自原有授权；保存由该应用设置页完成。</span></div>
            <div v-else class="r6-dept-role-actions">
              <span>{{ departmentFooterStateText }}</span>
              <div class="r6-dept-footer-actions">
                <span v-if="departmentPrimaryReason && departmentDirty" class="r6-dept-primary-reason">{{ departmentPrimaryReason }}</span>
                <a-button v-if="departmentDirty" :disabled="departmentBusy" @click="cancelDepartmentEdit">取消修改</a-button>
                <a-button v-if="departmentCanEdit" type="primary" :disabled="!departmentDirty || departmentMustRead || departmentBusy || !departmentCurrent || Boolean(departmentPreview)" :loading="departmentBusy" @click="prepareDepartmentRole">预览影响</a-button>
                <span v-else class="aux">只读</span>
              </div>
            </div>
          </template>
          <span v-else class="aux">{{ activeTab === 'apps' ? departmentFooterMessage : '保存前会核对跟随者、个人安排与已有限制；个人暂停与禁止不会因部门默认解除。' }}</span>
        </template>
      </PanelFrame>
    </div>
    <EmployeeDrawer :open="drawerOpen" :employee-id="employeeId" initial-tab="apps" :initial-app="'attendance'" @close="drawerOpen = false" @changed="load" />

    <ChangeReview :open="Boolean(departmentPreview)" :busy="departmentBusy" title="核对部门默认角色与范围" @cancel="closeDepartmentPreview">
      <section v-if="departmentPreview" class="role-preview" aria-live="polite">
        <div class="role-preview-subject"><strong>{{ current?.name }}</strong><span>{{ activeAppTitle }} · 部门默认；管理型角色保存后需逐人确认准入</span></div>
        <div class="r6-assignment-compare"><div><small>当前安排</small><strong>{{ currentDepartmentText }}</strong><p>当前已保存的部门默认</p></div><div><small>本次安排</small><strong>{{ nextDepartmentText }}</strong><p>个人安排和已有限制保留</p></div></div>
        <div class="role-department-impact">
          <div><strong>{{ countText(departmentPreview.reference_count) }}</strong><span>跟随默认</span></div>
          <div><strong>{{ countText(departmentPreview.effective_changed_count) }}</strong><span>实际权限变化</span></div>
          <div><strong>{{ countText(departmentPreview.personal_preserved) }}</strong><span>个人安排保留</span></div>
          <div><strong>{{ countText(departmentPreview.pending_count) }}</strong><span>待确认准入</span></div>
        </div>
        <p v-if="isManagementDefault" class="role-scope-caption">管理型角色需要逐人确认准入；未确认的跟随者在确认前不会获得新增管理权限，也不会回落旧原生宽权限。</p>
        <ul v-if="candidateMembers.length" class="role-member-list"><li v-for="member in candidateMembers" :key="member.employee"><strong>{{ member.name }}</strong><span>{{ member.admission_state === 'PENDING' ? '待确认准入' : member.admission_state === 'CONFIRMED' ? '已确认准入' : '自动继承' }} · {{ member.changed ? '实际权限将变化' : '实际权限保持' }} {{ member.reason }}</span></li></ul>
        <p v-else class="role-scope-caption">核对结果未返回跟随者名单。</p>
        <ul v-if="candidatePersonal.length" class="role-member-list"><li v-for="person in candidatePersonal" :key="'p-' + person.employee"><strong>{{ person.name }}</strong><span>个人例外保留 · {{ person.reason }}</span></li></ul>
        <OwnAccountVerification password-only @verified="departmentProof.sync" @invalidated="departmentProof.invalidate" />
        <div class="role-modal-actions"><a-button :disabled="departmentBusy" @click="closeDepartmentPreview">返回修改</a-button><a-button type="primary" :disabled="!canSubmitDepartment" :loading="departmentBusy" @click="commitDepartmentRole">确认保存</a-button></div>
      </section>
    </ChangeReview>

    <ChangeReview :open="Boolean(admissionTarget)" :busy="admissionBusy" :title="admissionTitle" @cancel="closeAdmission">
      <section v-if="admissionTarget" class="role-preview" aria-live="polite">
        <div class="role-preview-subject"><strong>{{ admissionTarget.name }}</strong><span v-if="admissionTarget.number">{{ admissionTarget.number }}</span><span>{{ admissionTarget.action === 'revoke' ? '撤销部门管理角色准入' : '确认部门管理角色准入' }}</span></div>
        <a-alert v-if="admissionError" :message="admissionError" type="warning" show-icon />
        <a-skeleton v-if="admissionBusy && !admissionPreview" active />
        <template v-else-if="admissionPreview">
          <div class="r6-assignment-compare">
            <div><small>确认前</small><strong>{{ admissionPreview.before.allowed ? '当前已有可用功能（按现有来源）' : '当前不可用' }}</strong><p>{{ admissionPreview.before.reason || '按当前角色、范围与限制判定' }}</p></div>
            <div><small>{{ admissionTarget.action === 'revoke' ? '撤销后' : '确认准入后' }}</small><strong>{{ admissionPreview.after.allowed ? '按已发布角色生效' : '暂不可用' }}</strong><p>{{ admissionPreview.after.reason || '按服务端结果与既有限制判定' }}</p></div>
          </div>
          <p class="role-scope-caption">角色：{{ admissionPreview.role_key === 'clerk' ? '部门考勤员' : admissionPreview.role_key === 'admin' ? '考勤管理员' : admissionPreview.role_key }}；范围：{{ (admissionPreview.responsibilities || []).map(scope => scopeLabel(scope.scope_ref)).join('、') || '待核对' }}。确认或撤销只改变本部门管理角色准入；个人禁止、暂停、期限和其他应用保持不变。</p>
          <OwnAccountVerification password-only @verified="admissionProof.sync" @invalidated="admissionProof.invalidate" />
          <div class="role-modal-actions"><a-button :disabled="admissionBusy" @click="closeAdmission">返回</a-button><a-button type="primary" :disabled="!canSubmitAdmission" :loading="admissionBusy" @click="commitAdmission">{{ admissionTarget.action === 'revoke' ? '确认撤销' : '确认准入' }}</a-button></div>
        </template>
      </section>
    </ChangeReview>
  </section>
</template>

<style scoped>
.r6-dept-task-line{margin:0 0 4px;color:var(--r6-secondary,#566780);font-size:13px;line-height:21px}
.r6-dept-details{margin-top:6px;font-size:12px;line-height:20px;color:var(--r6-muted,#5f6e86)}
.r6-dept-details summary{cursor:pointer;min-height:30px;display:flex;align-items:center}
.r6-dept-details p{margin:6px 0 0}
.r6-role-cards.is-department{margin-top:12px}
.r6-role-cards.is-department .r6-role-card{min-height:126px}
.r6-role-cards.is-department .r6-role-card.disabled{opacity:.72;cursor:not-allowed}
.r6-dept-app-subtitle{display:flex;align-items:center;gap:7px;margin:5px 0 0;color:#4d5f8a;font-size:14px;line-height:22px;font-weight:600}
.r6-dept-app-subtitle .anticon{font-size:15px;color:#6f6bd6}
.r6-dept-meta{margin:3px 0 0;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:19px;overflow-wrap:anywhere}
.r6-dept-panel-icon{display:grid;place-items:center;width:40px;height:42px;flex:none;border-radius:12px;background:linear-gradient(145deg,#eee8ff,#f0f3ff);border:1px solid #e4ddf7;color:#7862cd;font-size:20px}
.r6-dept-app-switch{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 16px}
.r6-dept-app-chip{display:flex;align-items:center;gap:8px;min-height:38px;padding:7px 12px;border:1px solid #e3e7f0;border-radius:10px;background:#fff;color:#34456e;font:inherit;font-size:13px;line-height:20px;cursor:pointer}
.r6-dept-app-chip.selected{border-color:#cdc7f3;background:#f3f0ff}
.r6-dept-app-chip small{color:var(--r6-muted,#5f6e86);font-size:11px}
.r6-dept-unintegrated{margin-top:18px;border-top:1px solid #e5e9f2;padding-top:10px;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px}
.r6-dept-unintegrated summary{cursor:pointer;min-height:36px;display:flex;align-items:center}
.r6-dept-unintegrated p{margin:6px 0 0}
.r6-dept-counts-four{grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.r6-dept-counts-four>div{padding:14px 16px}
.r6-dept-counts-four strong{font-size:24px;line-height:32px}
.r6-dept-counts-four>div small{display:block;margin-top:3px;color:var(--r6-muted,#5f6e86);font-size:11px;line-height:18px}
.r6-dept-count-pending strong{font-size:14px!important;line-height:32px!important;color:#6b5fc4}
.r6-dept-follow-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:16px 0 6px}
.r6-dept-follow-head h4{margin:0;font-size:14px}
.r6-dept-follow-head span{color:var(--r6-muted,#5f6e86);font-size:12px}
.r6-dept-followers{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.r6-dept-followers li{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:11px 13px;border:1px solid #e5e9f2;border-radius:9px;font-size:13px}
.r6-dept-follower-main{display:flex;align-items:center;gap:10px;min-width:160px;flex:1}
.r6-dept-follower-main>div{min-width:0}
.r6-dept-follower-main strong,.r6-dept-follower-main small{display:block;overflow-wrap:anywhere}
.r6-dept-follower-main small{margin-top:2px;color:var(--r6-muted,#5f6e86);font-size:11px;line-height:18px}
.r6-dept-follower-reason{color:var(--r6-muted,#5f6e86);font-size:12px;line-height:19px;min-width:120px;flex:1}
.r6-dept-follower-actions{display:flex;align-items:center;gap:6px;flex:none}
.r6-dept-footer-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}
.r6-dept-primary-reason{color:var(--r6-muted,#5f6e86);font-size:12px;line-height:19px}
.r6-dept-readonly{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:14px 16px;border:1px solid #e5e9f2;border-radius:10px;background:#f8f9fc}
.r6-dept-readonly p{margin:0;color:var(--r6-muted,#5f6e86);font-size:12px;flex-basis:100%}
.r6-dept-baseline-actions{display:flex;gap:8px;flex-wrap:wrap}
.r6-dept-note{margin:10px 0 0;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px}
.r6-dept-restrictions{margin-top:14px;border-top:1px solid #e5e9f2;padding-top:10px}
.r6-dept-restrictions summary{cursor:pointer;font-size:12px;color:var(--r6-muted,#5f6e86);min-height:34px;display:flex;align-items:center}
.r6-dept-restrictions p{margin:5px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}
.r6-dept-app-unavailable{display:grid;gap:14px}
.r6-department-app>div{min-width:0}
.r6-department-app strong{font-size:14px}
.r6-department-app p{margin:5px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}
.r6-department-app .ant-btn{flex:none}
.role-preview{display:grid;gap:14px}
.role-preview-subject{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}
.role-preview-subject strong{font-size:16px}
.role-preview-subject span{color:var(--r6-muted,#5f6e86);font-size:12px}
.role-department-impact{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.role-department-impact>div{padding:12px;border:1px solid #e5e9f2;border-radius:10px;background:#f8f9fc}
.role-department-impact strong{display:block;font-size:22px;line-height:30px}
.role-department-impact span{display:block;margin-top:4px;color:var(--r6-muted,#5f6e86);font-size:11px;line-height:18px}
.role-member-list{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.role-member-list li{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;padding:10px 12px;border:1px solid #e5e9f2;border-radius:8px;font-size:12px}
.role-member-list span{color:var(--r6-secondary,#566780)}
.role-scope-caption{margin:0;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px}
.role-modal-actions{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;padding-top:14px;border-top:1px solid #e5e9f2}
.r6-department-directory-heading{display:flex;align-items:center;justify-content:space-between;gap:8px}
.r6-department-directory-heading h3{margin:0;font-size:14px}
.r6-department-filter-toggle{height:32px;padding-inline:8px;color:var(--r6-secondary,#566780);font-size:12px}
.r6-department-filters{display:grid;gap:10px;margin-top:14px;padding-top:14px;border-top:1px solid #e8ebf3}
.r6-department-filters :deep(.ant-select){width:100%}
.r6-department-rows{display:grid;align-content:start;gap:5px}
.r6-department-row{display:flex;align-items:center;gap:12px;width:100%;min-height:48px;padding:11px 12px;padding-inline-start:calc(12px + var(--department-indent,0px));border:1px solid transparent;border-radius:9px;background:transparent;color:var(--r6-secondary,#566780);text-align:left;cursor:pointer;transition:background .16s ease,border-color .16s ease,color .16s ease}
.r6-department-row:hover{background:#f7f6ff;color:var(--r6-brand,#5b55e7)}
.r6-department-row.selected{background:#f0ecff;border-color:#e4dcfa;color:#5f53bf}
.r6-department-row>span{flex:1;min-width:0;overflow-wrap:anywhere}
.r6-department-row>.anticon:first-child{flex:none;font-size:15px}
.r6-department-row>.anticon:last-child{flex:none;margin-left:auto;font-size:9px}
.r6-department-panel-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
.r6-department-title{min-width:0}
.r6-department-title h2{margin:0;font-size:20px;line-height:28px;font-weight:600}
.r6-department-title p{margin:4px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:19px;overflow-wrap:anywhere}
.r6-department-view-toggle{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex:none}
.r6-department-view-toggle .ant-btn{padding-inline:10px}
.department-default-options{display:grid;gap:10px;width:100%;margin-bottom:18px}
.r6-dept-role-actions{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.r6-dept-role-actions>span{color:var(--r6-muted,#5f6e86);font-size:12px}
.r6-dept-role-actions>div{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
@media(max-width:1280px){.r6-dept-counts-four,.role-department-impact{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){
  .r6-dept-panel-icon{display:none}
  .r6-dept-app-switch{gap:6px;margin-bottom:14px;flex-wrap:nowrap;overflow-x:auto;padding-bottom:2px}
  .r6-dept-app-chip{min-height:44px;padding:8px 10px;flex:none}
  .r6-dept-footer-actions{width:auto;justify-content:flex-end}
  .r6-dept-counts-four,.role-department-impact{grid-template-columns:1fr}
  .r6-department-tree :deep(.r6-panel-scroll){overflow:visible;padding:14px 12px}
  .r6-department-tree :deep(.r6-panel-header){display:none}
  .r6-department-tree :deep(.r6-panel-footer){display:none}
  .r6-department-rows{display:flex;gap:8px;overflow-x:auto;align-content:initial;padding-bottom:2px}
  .r6-department-row{flex:none;width:auto;min-height:44px;padding:9px 11px;white-space:nowrap}
  .r6-department-row>span{flex:none;max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;overflow-wrap:normal}
  .r6-department-row>.anticon:last-child{display:none}
  .r6-department-filter-toggle{display:none}
  .r6-department-filters{display:none!important}
  .r6-dept-follower-actions{width:100%;justify-content:flex-end}
  .r6-department-panel-heading{flex-direction:column;gap:8px}
  .r6-department-view-toggle{width:100%;justify-content:flex-end}
}
</style>
