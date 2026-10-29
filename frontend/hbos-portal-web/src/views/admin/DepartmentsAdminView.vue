<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { listDepartments } from '@/services/iamDepartments'
import { getDepartmentWork } from '@/services/iamWork'
import { canIam, iamMessage, iamSession } from '@/services/iamAccess'
import { roleCommand, roleQuery, assertRolePreview, type DepartmentAdmissionPreview, type RoleAssignment, type RoleImpactMember, type RolePreview, type RoleScope } from '@/services/iamRoles'
import type { DepartmentSummary, WorkApp } from '@/types/iam'
import EmployeeDrawer from '@/components/iam/EmployeeDrawer.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import PanelFrame from '@/components/iam/PanelFrame.vue'
import ChangeReview from '@/components/iam/ChangeReview.vue'
import DepartmentNavigator, { type DepartmentEntry } from '@/components/iam/DepartmentNavigator.vue'
import AppContextSelector from '@/components/iam/AppContextSelector.vue'
import RoleChoiceGroup from '@/components/iam/RoleChoiceGroup.vue'
import ScopeSelector from '@/components/iam/ScopeSelector.vue'
import AssignmentSummary from '@/components/iam/AssignmentSummary.vue'
import MemberAccessList, { type MemberRow } from '@/components/iam/MemberAccessList.vue'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { useAccountProof } from '@/composables/useAccountProof'
import { managementRole, memberStatus, roleTitle, scopeRefsOf, type MemberSource } from '@/services/assignmentPresentation'

const route = useRoute(), router = useRouter()

// Two fixed tabs. The old `tab=apps|members` deep links keep working through
// this explicit map; no legacy value silently changes the task.
type TabKey = 'default' | 'members'
const activeTab = ref<TabKey>(route.query.tab === 'members' ? 'members' : 'default')
const mode = ref<'reading' | 'editing'>('reading')

const viewGroup = ref('daily'), groupsAvailable = ref(false), companies = ref<Array<{ id: string; name: string }>>([]), company = ref('')
const treeSearch = ref(''), directoryFiltersOpen = ref(false)
// Below 1024 the directory becomes a real search selector (§7.2); it must not
// survive as a long list that pushes the panel off-screen on a phone.
const compactDirectory = ref(false)
let directoryQuery: MediaQueryList | null = null
function syncDirectoryMode() { compactDirectory.value = Boolean(directoryQuery?.matches) }
const departments = ref<DepartmentSummary[]>([]), selected = ref(''), apps = ref<WorkApp[]>([]), loading = ref(true), error = ref('')
const employeeId = ref(''), drawerOpen = ref(false)
const activeAppId = ref('attendance')

const current = computed(() => departments.value.find(row => row.id === selected.value))
const canReadApps = computed(() => canIam('iam.access.read'))
const canManageDepartmentRole = computed(() => canIam('iam.departments.manage') && canIam('iam.roles.assign'))
const appEntries = computed(() => [...apps.value].sort((left, right) => left.app_id === 'attendance' ? -1 : right.app_id === 'attendance' ? 1 : left.title.localeCompare(right.title)))
const activeAppTitle = computed(() => appEntries.value.find(row => row.app_id === activeAppId.value)?.title || '考勤管理')
const linkTarget = () => typeof route.query.department === 'string' ? route.query.department : undefined

const departmentOptions = computed(() => departmentEntries.value.map(entry => ({ value: entry.id, label: `${entry.name}${entry.company ? ' · ' + entry.company : ''}` })))
const departmentEntries = computed<DepartmentEntry[]>(() => {
  const query = treeSearch.value.trim().toLowerCase()
  const rows = departments.value.filter(row => !query || row.name.toLowerCase().includes(query) || row.id.toLowerCase().includes(query))
  const byId = new Map(departments.value.map(row => [row.id, row]))
  const depthOf = (row: DepartmentSummary) => {
    let depth = 0
    let parent = row.parent_department ? byId.get(row.parent_department) : undefined
    while (parent && depth < 4) { depth++; parent = parent.parent_department ? byId.get(parent.parent_department) : undefined }
    return depth
  }
  return rows.map(row => ({ id: row.id, name: row.name, depth: depthOf(row), company: row.company, path: row.parent_department ? `${byId.get(row.parent_department)?.name || row.parent_department} / ${row.name}` : row.company }))
})

// ---- department default ----
const departmentCurrent = ref<RoleAssignment | null>(null), departmentChoice = ref(''), departmentScopeRefs = ref<string[]>([])
const departmentPreview = ref<RolePreview | null>(null)
const baselineImpact = ref<RolePreview | null>(null), baselineStatus = ref<'idle' | 'loading' | 'ready' | 'error' | 'unavailable'>('idle'), baselineError = ref('')
const departmentBusy = ref(false), departmentError = ref(''), departmentMustRead = ref(false)
const departmentProof = useAccountProof(() => { departmentPreview.value = null })
let departmentReadGeneration = 0, departmentActionGeneration = 0, departmentRequestId = '', departmentRequestPayload = ''
let refreshOnActivation = false

const currentRoleKey = computed(() => {
  const value = departmentCurrent.value
  if (!value) return ''
  if (value.has_role_default === false) return 'LEGACY'
  return ['staff', 'clerk', 'admin'].includes(value.role_key || '') ? value.role_key || '' : ''
})
const currentScopeRefs = computed(() => scopeRefsOf(departmentCurrent.value?.responsibilities))
const departmentDirty = computed(() => Boolean(departmentCurrent.value) && departmentStateKey(departmentChoice.value, departmentScopeRefs.value) !== departmentStateKey(currentRoleKey.value, currentScopeRefs.value))
const baselineLoading = computed(() => baselineStatus.value === 'loading')
const baselineReady = computed(() => baselineStatus.value === 'ready')
const canEnterEdit = computed(() => canManageDepartmentRole.value && baselineReady.value && Boolean(departmentCurrent.value) && !departmentMustRead.value)
const legacyState = computed(() => departmentCurrent.value?.has_role_default === false)

const sourceKind = computed<'FOLLOW_DEPARTMENT' | 'NONE' | 'LEGACY' | 'UNKNOWN'>(() => {
  const value = departmentCurrent.value
  if (!value) return 'UNKNOWN'
  if (value.has_role_default === false) return 'LEGACY'
  return ['staff', 'clerk', 'admin'].includes(value.role_key || '') ? 'FOLLOW_DEPARTMENT' : 'NONE'
})
const currentScopeLabels = computed(() => currentScopeRefs.value.map(scopeLabel))
const departmentStatus = computed<{ label: string; tone: 'neutral' | 'brand' | 'success' | 'warning' | 'error'; detail: string }>(() => {
  if (!departmentCurrent.value) return { label: '暂无法读取', tone: 'warning', detail: '没有可沿用的旧结果。' }
  if (sourceKind.value === 'NONE') return { label: '不分配角色', tone: 'neutral', detail: '员工不会从此部门获得考勤角色。' }
  if (sourceKind.value === 'LEGACY') return { label: '沿用原有安排', tone: 'neutral', detail: '尚未设置新的部门默认。' }
  if (baselineStatus.value === 'loading') return { label: '正在核对', tone: 'neutral', detail: '' }
  if (baselineStatus.value === 'error') return { label: '暂无法核对', tone: 'warning', detail: '影响范围读取失败，未显示任何人数。' }
  if (baselineStatus.value === 'unavailable') return { label: '只读', tone: 'neutral', detail: '当前账号不能核对本部门的影响范围。' }
  const pending = baselineImpact.value?.pending_count
  if (typeof pending === 'number' && pending > 0) return { label: `${pending} 位成员待确认`, tone: 'warning', detail: '确认前不能使用该管理型角色。' }
  if (managementRole(currentRoleKey.value)) return { label: '按成员逐人确认', tone: 'neutral', detail: '实际可用以成员状态为准。' }
  return { label: '跟随者按本人考勤', tone: 'success', detail: '账号、个人禁止与期限另计。' }
})
const pendingCount = computed(() => baselineImpact.value?.pending_count ?? departmentCurrent.value?.admissions?.pending ?? null)
const followerCount = computed(() => baselineImpact.value?.reference_count)
const personalCount = computed(() => baselineImpact.value?.personal_preserved)

const scopeOptions = computed(() => departments.value.filter(row => row.confirmed).map(row => ({ value: row.id, label: `${row.name}${row.company ? ' · ' + row.company : ''}` })))
const companyOptions = computed(() => companies.value.map(row => ({ value: row.id, label: row.name })))
const departmentValidationMessage = computed(() => departmentValidation())
const canPreview = computed(() => canEnterEdit.value && departmentDirty.value && !departmentBusy.value && !departmentPreview.value && !departmentValidationMessage.value)
const canSubmitDepartment = computed(() => Boolean(departmentPreview.value?.changed) && departmentProof.valid.value && departmentProof.method.value === 'password' && !departmentBusy.value && canEnterEdit.value)
const nextDepartmentText = computed(() => departmentText(departmentChoice.value, departmentScopeRefs.value))
const currentDepartmentText = computed(() => departmentText(currentRoleKey.value, currentScopeRefs.value))

function scopeLabel(ref: string) {
  const department = departments.value.find(row => row.id === ref)
  if (department) return `${department.name}（不含下级）`
  const companyRow = companies.value.find(row => row.id === ref)
  return companyRow?.name || ref || '待核对'
}
function departmentText(choice: string, scopes: string[]) {
  if (choice === 'LEGACY') return '沿用原有安排'
  if (choice === 'staff') return '普通员工 · 仅本人'
  if (choice === 'clerk') return `部门考勤员 · ${scopes.map(scopeLabel).join('、') || '负责范围待选择'}`
  if (choice === 'admin') return `考勤管理员 · ${scopes.map(scopeLabel).join('、') || '负责公司待选择'}`
  return '不通过部门分配'
}
function countText(value?: number) { return typeof value === 'number' ? String(value) : '暂无法核对' }
function departmentStateKey(choice: string, scopes: string[]) { return JSON.stringify([choice, [...scopes].sort()]) }
function currentRoleAndScopes() {
  if (!departmentCurrent.value) return { role: '', scopes: [] as string[] }
  if (departmentCurrent.value.has_role_default === false) return { role: 'LEGACY', scopes: [] as string[] }
  return { role: departmentCurrent.value.role_key || '', scopes: scopeRefsOf(departmentCurrent.value.responsibilities) }
}
function resetDraft() {
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
  activeAppId.value = 'attendance'; mode.value = 'reading'
  closeAdmission()
  departmentProof.invalidate()
}
function departmentValidation(): string {
  if (!departmentCurrent.value) return ''
  if (departmentChoice.value === 'LEGACY') return '当前沿用原有安排；请先选择明确的分配方式。'
  if (!['staff', 'clerk', 'admin', ''].includes(departmentChoice.value)) return '请选择分配方式。'
  if (departmentChoice.value === 'clerk' && !departmentScopeRefs.value.length) return '部门考勤员必须明确选择至少一个负责部门（不含下级）。'
  if (departmentChoice.value === 'admin' && departmentScopeRefs.value.length !== 1) return '考勤管理员必须明确选择一个公司。'
  return ''
}
async function confirmDiscardDraft() {
  if (!departmentDirty.value) return true
  return new Promise<boolean>(resolve => Modal.confirm({
    title: '放弃尚未保存的部门默认？',
    content: '已保存的部门默认与个人安排不受影响。',
    okText: '放弃草稿', cancelText: '继续编辑',
    onOk: () => { resetDraft(); mode.value = 'reading'; resolve(true) },
    onCancel: () => resolve(false),
  }))
}
async function cancelEdit() {
  if (!await confirmDiscardDraft()) return
  mode.value = 'reading'
}
async function enterEdit() {
  if (!canEnterEdit.value) return
  mode.value = 'editing'
  await nextTick()
  document.querySelector<HTMLElement>('[data-dept-edit-first]')?.focus()
}
async function requestLeave() {
  if (departmentBusy.value) return false
  if (!await confirmDiscardDraft()) return false
  if (admissionTarget.value) return false
  return true
}
function chooseMode(next: 'department' | 'none') {
  if (departmentBusy.value || departmentPreview.value) return
  if (next === 'none') { departmentChoice.value = ''; departmentScopeRefs.value = [] }
  else if (!['staff', 'clerk', 'admin'].includes(departmentChoice.value)) { departmentChoice.value = 'staff'; departmentScopeRefs.value = [] }
  departmentPreview.value = null; departmentError.value = ''
}
const modeChoice = computed(() => ['staff', 'clerk', 'admin'].includes(departmentChoice.value) ? 'department' : departmentChoice.value === '' ? 'none' : '')
function chooseRole(key: string) {
  if (departmentBusy.value || departmentPreview.value) return
  departmentChoice.value = key
  departmentScopeRefs.value = []
  departmentPreview.value = null
  departmentError.value = ''
}
function setScopeRefs(values: string[]) {
  departmentScopeRefs.value = values
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
    if (!keep) resetDraft()
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
  if (departmentBusy.value || departmentMustRead.value || !canEnterEdit.value || !departmentDirty.value || departmentPreview.value) return
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
    const pending = preview.pending_count || 0
    departmentRequestId = ''; departmentRequestPayload = ''
    departmentMustRead.value = false
    mode.value = 'reading'
    await loadDepartmentRole(); await loadApps()
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    if (pending > 0) {
      message.success(`默认设置已保存，${pending} 位成员待确认。`)
      activeTab.value = 'members'
    } else {
      message.success('默认设置已保存。')
    }
  } catch (e) {
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    departmentError.value = iamMessage(e); departmentMustRead.value = true
    departmentProof.invalidate(); departmentPreview.value = null
  } finally { if (run === departmentActionGeneration) departmentBusy.value = false }
}
function closeDepartmentPreview() { departmentPreview.value = null; departmentProof.invalidate() }

// ---- per-member admission (still one person at a time) ----
const admissionTarget = ref<{ employee: string; name: string; number?: string; action: 'confirm' | 'revoke' } | null>(null)
const admissionPreview = ref<DepartmentAdmissionPreview | null>(null)
const admissionBusy = ref(false), admissionError = ref('')
const admissionProof = useAccountProof(() => { admissionPreview.value = null })
let admissionRequestId = '', admissionRequestSignature = ''

const admissionTitle = computed(() => admissionTarget.value?.action === 'revoke' ? '撤销角色确认' : '确认成员角色')
const canSubmitAdmission = computed(() => Boolean(admissionPreview.value?.changed) && admissionProof.valid.value && admissionProof.method.value === 'password' && !admissionBusy.value)
async function openAdmission(member: { employee: string; name?: string; employeeNumber?: string }, action: 'confirm' | 'revoke') {
  if (!departmentCurrent.value) return
  admissionTarget.value = { employee: member.employee, name: member.name || member.employee, number: member.employeeNumber, action }
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
    message.success(admissionTarget.value.action === 'revoke' ? '角色确认已撤销。' : '已确认该成员的角色；实际可用以服务端结果为准。')
    closeAdmission()
    await loadDepartmentRole(true)
  } catch (e) { admissionError.value = iamMessage(e); admissionProof.invalidate() } finally { admissionBusy.value = false }
}

// ---- members tab rows (server facts only) ----
const memberRows = computed<MemberRow[]>(() => {
  const impact = baselineImpact.value
  const rows: MemberRow[] = []
  const seen = new Set<string>()
  const admState = (member: RoleImpactMember) => member.admission_state
  for (const member of impact?.members || []) {
    if (!member.employee || seen.has(member.employee)) continue
    seen.add(member.employee)
    const status = memberStatus({
      source: 'FOLLOW_DEPARTMENT', admissionState: admState(member),
      effective: member.before_allowed, reason: member.reason,
    })
    rows.push({
      employee: member.employee, name: member.name, employeeNumber: member.employee_number,
      source: 'FOLLOW_DEPARTMENT',
      roleName: roleTitleOf(currentRoleKey.value),
      scopeText: currentScopeLabels.value.join('、') || (currentRoleKey.value === 'staff' ? '仅本人' : '负责范围待核对'),
      status,
      canConfirm: Boolean(canManageDepartmentRole.value) && status.admissionAction === 'confirm' && admState(member) !== 'AUTO',
      canRevoke: Boolean(canManageDepartmentRole.value) && status.admissionAction === 'revoke',
      personalException: false,
    })
  }
  for (const person of impact?.personal || []) {
    if (!person.employee || seen.has(person.employee)) continue
    seen.add(person.employee)
    const source: MemberSource = person.mode === 'DIRECT' ? 'DIRECT' : person.mode === 'NONE' ? 'NONE' : person.mode === 'LEGACY' ? 'LEGACY' : 'UNKNOWN'
    rows.push({
      employee: person.employee, name: person.name, employeeNumber: person.employee_number,
      source,
      roleName: source === 'DIRECT' ? '按个人设置' : source === 'NONE' ? '不分配角色' : '以原有安排为准',
      scopeText: source === 'DIRECT' ? '由个人单独设置决定' : '未通过部门默认',
      status: memberStatus({ source, reason: person.reason }),
      canConfirm: false, canRevoke: false, personalException: true,
    })
  }
  if (!rows.length && !baselineReady.value) {
    for (const member of current.value?.members || []) {
      if (seen.has(member.id)) continue
      seen.add(member.id)
      rows.push({
        employee: member.id, name: member.name, employeeNumber: member.employee_number,
        source: 'UNKNOWN',
        roleName: '暂无法确认',
        scopeText: '暂无法读取',
        status: memberStatus({ source: 'UNKNOWN', accountStatus: member.account_status }),
        canConfirm: false, canRevoke: false, personalException: false,
      })
    }
  }
  return rows.sort((left, right) => left.name.localeCompare(right.name, 'zh-Hans-CN'))
})
const memberTotal = computed(() => {
  if (baselineReady.value) return baselineImpact.value?.reference_count !== undefined ? (baselineImpact.value.reference_count + (baselineImpact.value.personal_preserved || 0)) : null
  return current.value?.member_count ?? current.value?.members?.length ?? null
})
const memberUnavailable = computed(() => baselineStatus.value === 'unavailable' && memberRows.value.length === 0)
const memberError = computed(() => baselineStatus.value === 'error' ? (baselineError.value || '暂无法读取成员权限') : '')

function roleTitleOf(key: string) {
  return key ? roleTitle(key) : '不分配角色'
}
function viewMember(member: MemberRow) {
  if (!canIam('iam.people.read')) return
  employeeId.value = member.employee
  drawerOpen.value = true
}
function openRoleDefinitions() { void router.push('/hbos/admin/roles') }
function openDepartmentAudit() { void router.push({ path: '/hbos/admin/audit', query: { subject_type: 'Department', subject_name: selected.value } }) }

// ---- application context ----
async function loadApps() {
  const run = ++appRead, id = selected.value; apps.value = []
  if (!canReadApps.value || !id) return
  try {
    const result = await getDepartmentWork(id)
    if (disposed || run !== appRead || selected.value !== id) return
    apps.value = result.apps
  } catch (e) { if (!disposed && run === appRead) { apps.value = []; error.value = iamMessage(e) } }
}

// ---- routing / loading ----
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
  if (!departments.value.some(row => row.id === target.department)) { activeTab.value = 'members'; error.value = '该部门或应用当前不可查看，已返回可用部门。'; return }
  const selectionChanged = selected.value !== target.department
  if (selectionChanged) { selected.value = target.department; clearDepartmentState() }
  activeTab.value = target.tab === 'members' ? 'members' : 'default'
  await loadApps()
  if (!currentTarget()) return
  if (selectionChanged || refreshRole) await loadDepartmentRole()
  if (!currentTarget()) return
  if (target.app && target.app !== 'attendance') error.value = '该部门或应用当前不可查看，已返回可用部门。'
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
  selected.value = id; clearDepartmentState(); activeTab.value = 'default'; mode.value = 'reading'; error.value = ''
  try { await loadApps(); if (!disposed && selected.value === id) await loadDepartmentRole() } catch (e) { if (!disposed) error.value = iamMessage(e) }
}
async function changeCompany(value: string) { if (!await requestLeave()) return; company.value = value; selected.value = ''; await load() }
async function changeGroup(value: string) { if (!await requestLeave()) return; viewGroup.value = value; selected.value = ''; await load() }
function changeTab(value: TabKey) {
  if (departmentBusy.value) return
  if (value === 'members' && mode.value === 'editing' && departmentDirty.value) { departmentError.value = '请先保存或取消当前的默认修改，再处理成员权限。'; return }
  activeTab.value = value
}

let generation = 0, appRead = 0, linkRead = 0, routeRevision = 0, disposed = false
onBeforeRouteLeave(() => requestLeave())
onBeforeRouteUpdate(() => requestLeave())
watch(() => route.query, () => { routeRevision++; if (!loading.value) void applyLink().catch(e => { if (!disposed) error.value = iamMessage(e) }) })
useManagementViewMemory('DepartmentsAdminView.vue', { viewGroup, company, treeSearch, selected, search: treeSearch })
onMounted(() => {
  directoryQuery = window.matchMedia('(max-width: 1023px)')
  syncDirectoryMode()
  directoryQuery.addEventListener('change', syncDirectoryMode)
  void load()
})
onDeactivated(() => { refreshOnActivation = true })
onActivated(() => { if (!refreshOnActivation) return; refreshOnActivation = false; void load() })
onBeforeUnmount(() => {
  disposed = true; generation++; appRead++; linkRead++; departmentReadGeneration++; departmentActionGeneration++; departments.value = []; apps.value = []
  directoryQuery?.removeEventListener('change', syncDirectoryMode); directoryQuery = null
})
</script>

<template>
  <section class="r6-page r6-departments-page">
    <PageHeading eyebrow="管理中心" title="部门应用权限" description="为部门设置默认角色，特殊职责到员工中单独安排。" />
    <a-skeleton v-if="loading" active />
    <div v-else class="r6-dual-panels">
      <PanelFrame v-if="!compactDirectory" as="aside" region="department-list" label="组织部门目录" class="r6-navigation r6-department-tree">
        <DepartmentNavigator
          :entries="departmentEntries" :selected="selected" :search="treeSearch"
          :filters-open="directoryFiltersOpen" :groups-available="groupsAvailable" :view-group="viewGroup"
          :companies="companies" :company="company" :disabled="departmentBusy"
          @select="selectDepartment" @update:search="value => treeSearch = value"
          @update:filters-open="value => directoryFiltersOpen = value"
          @update:view-group="changeGroup" @update:company="changeCompany" />
      </PanelFrame>

      <PanelFrame region="department-detail" label="部门应用权限与成员">
        <template v-if="current" #header>
          <div class="r6-dept-panel-heading">
            <div class="r6-dept-head">
              <div v-if="compactDirectory" class="r6-dept-picker">
                <span>部门</span>
                <a-select :value="selected" :options="departmentOptions" show-search option-filter-prop="label" aria-label="选择部门" :disabled="departmentBusy" @update:value="selectDepartment" />
                <a-select v-if="groupsAvailable" :value="viewGroup" aria-label="部门分组" :disabled="departmentBusy" @change="changeGroup">
                  <a-select-option value="daily">日常组织</a-select-option>
                  <a-select-option value="technical">技术验证夹具</a-select-option>
                  <a-select-option value="all">全部部门</a-select-option>
                </a-select>
              </div>
              <h2 :title="current.name">{{ current.name }}</h2>
              <p>{{ current.company || '公司待核对' }}<template v-if="typeof memberTotal === 'number'"> · 可见成员 {{ memberTotal }} 人</template></p>
              <AppContextSelector v-model="activeAppId" :apps="appEntries.map(row => ({ app_id: row.app_id, title: row.title, integrated: row.integrated }))" />
            </div>
          </div>
          <div class="r6-dept-tabs" role="tablist" aria-label="部门权限视图">
            <button type="button" role="tab" :aria-selected="activeTab === 'default'" @click="changeTab('default')">默认设置</button>
            <button type="button" role="tab" :aria-selected="activeTab === 'members'" @click="changeTab('members')">
              成员权限 <span v-if="pendingCount" class="r6-dept-tabs__count">待确认 {{ pendingCount }}</span>
            </button>
          </div>
        </template>

        <div v-if="error" class="r6-resource-error r6-resource-error-inline"><a-alert :message="error" type="warning" show-icon /><a-button @click="load">重试读取</a-button></div>

        <!-- 默认设置：阅读态（默认进入） -->
        <div v-if="current && activeTab === 'default'" class="r6-dept-page-body">
          <template v-if="iamSession.rolesEnabled && current.confirmed">
            <template v-if="mode === 'reading'">
              <div class="r6-dept-reading">
                <p v-if="legacyState" class="r6-dept-reading__lead"><strong>尚未设置部门默认。</strong>当前成员继续沿用原有安排；保存前不会自动转换，也不回落旧的宽权限。</p>
                <AssignmentSummary
                  :source="sourceKind" :role-key="sourceKind === 'LEGACY' ? '' : currentRoleKey"
                  :role-name="sourceKind === 'LEGACY' ? '' : roleTitleOf(currentRoleKey)"
                  :boundary-kind="currentRoleKey === 'staff' ? 'SELF' : currentRoleKey === 'clerk' ? 'DEPARTMENT' : currentRoleKey === 'admin' ? 'COMPANY' : null"
                  :scopes="departmentCurrent?.responsibilities || []" :scope-labels="currentScopeLabels"
                  :status-label="departmentStatus.label" :status-tone="departmentStatus.tone" :status-detail="departmentStatus.detail"
                  :source-detail="legacyState ? '当前状态' : '本部门默认'" />
                <ul v-if="typeof followerCount === 'number' || typeof personalCount === 'number' || (typeof pendingCount === 'number' && pendingCount > 0)" class="r6-dept-facts">
                  <li v-if="typeof followerCount === 'number'"><strong>{{ followerCount }}</strong> 位成员跟随部门默认</li>
                  <li v-if="typeof personalCount === 'number'"><strong>{{ personalCount }}</strong> 位个人例外保留，不受此次变化影响</li>
                  <li v-if="typeof pendingCount === 'number' && pendingCount > 0"><strong>{{ pendingCount }}</strong> 位成员待确认角色</li>
                </ul>
                <div v-if="baselineStatus === 'error'" class="r6-dept-empty">
                  <p>暂无法核对影响人员；未显示任何人数，也不沿用旧数据。</p>
                  <a-button :disabled="departmentBusy" @click="loadDepartmentRole(true)">重试读取</a-button>
                </div>
                <div v-else-if="baselineStatus === 'unavailable'" class="r6-dept-empty">
                  <p>当前账号只有查看权限，不能核对本部门的实际影响；成员与个人安排仍可查看。</p>
                </div>
                <div v-if="typeof pendingCount === 'number' && pendingCount > 0" class="r6-dept-pending">
                  <p>有 {{ pendingCount }} 位成员需要确认后才能使用此角色。</p>
                  <a-button @click="changeTab('members')">查看待确认成员</a-button>
                </div>
                <div class="r6-dept-reading__actions">
                  <a-button @click="openRoleDefinitions">查看角色功能</a-button>
                  <a-button @click="openDepartmentAudit">查看本部门变更</a-button>
                </div>
                <details class="r6-dept-help">
                  <summary>权限如何生效</summary>
                  <ul>
                    <li>部门默认只影响选择“跟随部门”的成员；单独设置的成员不受此次修改影响。</li>
                    <li>管理型角色（部门考勤员、考勤管理员）需要逐人确认后才可使用。</li>
                    <li>账号未开通、个人禁止、暂停与期限仍按服务端结果限制实际可用。</li>
                  </ul>
                </details>
              </div>
            </template>

            <!-- 默认设置：编辑态 -->
            <template v-else>
              <div class="r6-dept-editing">
                <div class="r6-dept-edit-head"><strong>正在修改 · 未保存</strong><span>保存前不会改变任何人；预览后仍需本人验证。</span></div>
                <div class="r6-dept-field">
                  <h3>分配方式</h3>
                  <div class="r6-dept-mode" role="radiogroup" aria-label="分配方式">
                    <label class="r6-dept-mode__choice" :data-selected="modeChoice === 'department'">
                      <input type="radio" :name="`dept-mode-${selected}`" value="department" :checked="modeChoice === 'department'" :disabled="departmentBusy || Boolean(departmentPreview)" data-dept-edit-first @change="chooseMode('department')" />
                      <span><strong>使用部门默认角色</strong><span>跟随本部门的成员获得所选角色与负责范围。</span></span>
                    </label>
                    <label class="r6-dept-mode__choice" :data-selected="modeChoice === 'none'">
                      <input type="radio" :name="`dept-mode-${selected}`" value="none" :checked="modeChoice === 'none'" :disabled="departmentBusy || Boolean(departmentPreview)" @change="chooseMode('none')" />
                      <span><strong>不通过部门分配</strong><span>不从此部门获得考勤角色；登录账号、个人安排与其他应用保持不变。</span></span>
                    </label>
                  </div>
                </div>

                <div v-if="modeChoice === 'department'" class="r6-dept-field">
                  <h3>默认角色<small>与员工页使用同一已发布角色目录</small></h3>
                  <RoleChoiceGroup :model-value="departmentChoice" :catalog="departmentCurrent?.roles || []" :disabled="departmentBusy || Boolean(departmentPreview)" :name="`dept-role-${selected}`" label="部门默认考勤角色" @update:model-value="chooseRole" />
                </div>

                <div class="r6-dept-field">
                  <h3>负责范围<small>{{ departmentChoice === 'clerk' ? '不自动包含下级部门' : departmentChoice === 'admin' ? '仅限一个公司' : '无需另外选择' }}</small></h3>
                  <ScopeSelector :role-key="departmentChoice" :model-value="departmentScopeRefs" :departments="scopeOptions" :companies="companyOptions" :disabled="departmentBusy || Boolean(departmentPreview)" :error="departmentValidationMessage && departmentChoice !== 'staff' ? departmentValidationMessage : ''" :loading="baselineLoading" @update:model-value="setScopeRefs" />
                </div>

                <div v-if="managementRole(departmentChoice)" class="r6-dept-edit-head" role="note">
                  <strong>生效方式</strong><span>保存后，请在“成员权限”中确认可使用此角色的人员。</span>
                </div>

                <p v-if="departmentError" class="r6-field-error" role="alert">{{ departmentError }}</p>
                <details class="r6-dept-help">
                  <summary>权限如何生效</summary>
                  <ul>
                    <li>部门默认只影响选择“跟随部门”的成员；单独设置、个人禁止、暂停与期限保持不变。</li>
                    <li>改变角色或范围会使已有预览与确认失效，需要重新核对。</li>
                    <li>保存只提交本次默认，不会自动确认任何成员。</li>
                  </ul>
                </details>
              </div>
            </template>
          </template>

          <div v-else-if="!current.confirmed" class="r6-dept-empty">
            <p>部门尚未确认，暂不安排默认角色或人员。</p>
          </div>
          <div v-else class="r6-dept-empty">
            <p>应用角色功能尚未启用；本页保留原有应用权限兼容入口，不新增角色选择。</p>
          </div>
        </div>

        <!-- 成员权限 -->
        <div v-else-if="current && activeTab === 'members'" class="r6-dept-page-body">
          <p class="r6-dept-reading__lead">谁跟随部门、谁单独设置、谁还不能使用，以及下一步做什么。</p>
          <MemberAccessList
            :rows="memberRows" :loading="baselineLoading" :error="memberError" :unavailable="memberUnavailable" :total="memberTotal"
            @confirm="row => openAdmission({ employee: row.employee, name: row.name, employeeNumber: row.employeeNumber }, 'confirm')"
            @revoke="row => openAdmission({ employee: row.employee, name: row.name, employeeNumber: row.employeeNumber }, 'revoke')"
            @view="viewMember" @retry="loadDepartmentRole(true)" />
        </div>

        <a-empty v-if="!current" description="暂无可管理部门" />

        <template #footer>
          <div class="r6-dept-footer-bar">
            <span v-if="activeTab === 'default'">
              <template v-if="mode === 'editing'">{{ departmentDirty ? '有未保存的修改' : '与当前部门默认一致' }}</template>
              <template v-else-if="legacyState">尚未设置部门默认</template>
              <template v-else-if="sourceKind === 'NONE'">当前不通过部门分配角色</template>
              <template v-else>当前默认：{{ currentDepartmentText }}</template>
            </span>
            <span v-else>成员确认逐人进行；不会自动确认下一位。</span>
            <div class="r6-dept-footer-bar__buttons">
              <template v-if="activeTab === 'default'">
                <template v-if="mode === 'editing'">
                  <a-button :disabled="departmentBusy" @click="cancelEdit">取消修改</a-button>
                  <a-button type="primary" :disabled="!canPreview" :loading="departmentBusy" :title="departmentValidationMessage || (departmentDirty ? '' : '没有未保存的修改')" @click="prepareDepartmentRole">预览变更</a-button>
                </template>
                <a-button v-else type="primary" :disabled="!canEnterEdit" :title="canEnterEdit ? '' : (baselineLoading ? '正在核对当前安排' : !canManageDepartmentRole ? '当前账号没有修改权限' : departmentMustRead ? '请先读取最新安排' : '暂无法修改')" @click="enterEdit">{{ legacyState ? '设置部门默认' : '修改默认设置' }}</a-button>
              </template>
            </div>
          </div>
        </template>
      </PanelFrame>
    </div>

    <EmployeeDrawer :open="drawerOpen" :employee-id="employeeId" initial-tab="apps" :initial-app="'attendance'" @close="drawerOpen = false" @changed="loadDepartmentRole(true)" />

    <ChangeReview :open="Boolean(departmentPreview)" :busy="departmentBusy" title="确认部门默认权限" @cancel="closeDepartmentPreview">
      <section v-if="departmentPreview" class="r6-dept-review" aria-live="polite">
        <div class="r6-dept-review__subject">
          <strong>{{ current?.name }} · {{ activeAppTitle }}</strong>
          <span>{{ current?.company }}<template v-if="current?.id"> · 部门标识 {{ current?.id }}</template></span>
        </div>
        <div class="r6-assignment-compare">
          <div><small>当前设置</small><strong>{{ currentDepartmentText }}</strong><p>{{ legacyState ? '尚未设置部门默认' : '当前已保存的部门默认' }}</p></div>
          <div><small>修改后</small><strong>{{ nextDepartmentText }}</strong><p>个人安排与已有限制保留</p></div>
        </div>
        <div class="r6-dept-impact">
          <div><strong>{{ countText(departmentPreview.reference_count) }}</strong><span>跟随默认</span></div>
          <div><strong>{{ countText(departmentPreview.effective_changed_count) }}</strong><span>实际权限变化</span></div>
          <div><strong>{{ countText(departmentPreview.personal_preserved) }}</strong><span>个人安排保留</span></div>
          <div><strong>{{ countText(departmentPreview.pending_count) }}</strong><span>待确认角色</span></div>
        </div>
        <p v-if="managementRole(departmentChoice)" class="r6-dept-reading__lead">管理型角色保存后不会立即生效：需在成员权限中逐人确认；确认后仍受账号、个人禁止、暂停与期限限制。</p>
        <ul v-if="(departmentPreview.members || []).length" class="r6-dept-review__members">
          <li v-for="member in departmentPreview.members || []" :key="member.employee">
            <strong>{{ member.name }}</strong>
            <span>{{ member.admission_state === 'PENDING' ? '待确认角色' : member.admission_state === 'CONFIRMED' ? '已确认' : member.admission_state === 'AUTO' ? '跟随部门' : '状态待核对' }} · {{ member.changed ? '实际权限将变化' : '实际权限保持' }}<template v-if="member.reason"> · {{ member.reason }}</template></span>
          </li>
        </ul>
        <p v-else class="r6-dept-reading__lead">服务端未返回跟随者名单；保存后以实际读取结果为准。</p>
        <ul v-if="(departmentPreview.personal || []).length" class="r6-dept-review__members">
          <li v-for="person in departmentPreview.personal || []" :key="'p-' + person.employee"><strong>{{ person.name }}</strong><span>个人例外保留 · {{ person.reason }}</span></li>
        </ul>
        <OwnAccountVerification password-only @verified="departmentProof.sync" @invalidated="departmentProof.invalidate" />
        <div class="role-modal-actions">
          <a-button :disabled="departmentBusy" @click="closeDepartmentPreview">返回修改</a-button>
          <a-button type="primary" :disabled="!canSubmitDepartment" :loading="departmentBusy" @click="commitDepartmentRole">确认保存</a-button>
        </div>
      </section>
    </ChangeReview>

    <ChangeReview :open="Boolean(admissionTarget)" :busy="admissionBusy" :title="admissionTitle" @cancel="closeAdmission">
      <section v-if="admissionTarget" class="r6-dept-review" aria-live="polite">
        <div class="r6-dept-review__subject"><strong>{{ admissionTarget.name }}</strong><span v-if="admissionTarget.number">{{ admissionTarget.number }}</span><span>{{ admissionTarget.action === 'revoke' ? '撤销本部门管理角色确认' : '确认本部门管理角色' }}</span></div>
        <a-alert v-if="admissionError" :message="admissionError" type="warning" show-icon />
        <a-skeleton v-if="admissionBusy && !admissionPreview" active />
        <template v-else-if="admissionPreview">
          <div class="r6-assignment-compare">
            <div><small>确认前</small><strong>{{ admissionPreview.before.allowed ? '当前已有可用功能（按现有来源）' : '当前不可用' }}</strong><p>{{ admissionPreview.before.reason || '按当前角色、范围与限制判定' }}</p></div>
            <div><small>{{ admissionTarget.action === 'revoke' ? '撤销后' : '确认后' }}</small><strong>{{ admissionPreview.after.allowed ? '按已发布角色生效' : '暂不可用' }}</strong><p>{{ admissionPreview.after.reason || '按服务端结果与既有限制判定' }}</p></div>
          </div>
          <p class="r6-dept-reading__lead">角色：{{ roleTitleOf(admissionPreview.role_key) }}；范围：{{ (admissionPreview.responsibilities || []).map(scope => scopeLabel(scope.scope_ref)).join('、') || '待核对' }}。确认或撤销只改变本部门管理角色；个人禁止、暂停、期限与其他应用保持不变。</p>
          <OwnAccountVerification password-only @verified="admissionProof.sync" @invalidated="admissionProof.invalidate" />
          <div class="role-modal-actions">
            <a-button :disabled="admissionBusy" @click="closeAdmission">返回</a-button>
            <a-button type="primary" :disabled="!canSubmitAdmission" :loading="admissionBusy" @click="commitAdmission">{{ admissionTarget.action === 'revoke' ? '确认撤销' : '确认角色' }}</a-button>
          </div>
        </template>
      </section>
    </ChangeReview>
  </section>
</template>

<style scoped>
.r6-dept-picker { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.r6-dept-picker > span { color: var(--r6-muted); font-size: 12px; line-height: 20px; }
.r6-dept-picker :deep(.ant-select) { min-width: 0; flex: 1 1 180px; max-width: 320px; }
.r6-dept-panel-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.r6-dept-facts { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px 18px; color: var(--r6-secondary); font-size: 14px; line-height: 22px; }
.r6-dept-facts strong { color: var(--r6-ink); font-size: 16px; }
.r6-assignment-compare > div { min-width: 0; overflow-wrap: anywhere; }
.role-modal-actions { display: flex; justify-content: flex-end; gap: 10px; flex-wrap: wrap; padding-top: 14px; border-top: 1px solid var(--r6-line); }
@media (max-width: 760px) {
  .r6-dept-panel-heading { flex-direction: column; }
}
</style>
