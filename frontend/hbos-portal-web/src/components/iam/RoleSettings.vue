<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { canIam, iamMessage } from '@/services/iamAccess'
import { listDepartments } from '@/services/iamDepartments'
import { roleQuery, roleCommand, assertRolePreview, type RoleAssignment, type RolePreview, type RoleScope } from '@/services/iamRoles'
import type { DepartmentSummary, RoleEditorSummary } from '@/types/iam'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import ChangeReview from './ChangeReview.vue'
import StatusTag from './StatusTag.vue'
import RoleChoiceGroup from './RoleChoiceGroup.vue'
import ScopeSelector from './ScopeSelector.vue'
import { roleTitle } from '@/services/assignmentPresentation'
import { useAccountProof } from '@/composables/useAccountProof'

const props = withDefaults(defineProps<{
  subjectKind: 'employee' | 'department'
  subjectId: string
  embedded?: boolean
  subjectLabel?: string
}>(), { embedded: false, subjectLabel: '' })
const emit = defineEmits<{ back: []; saved: []; dirty: [boolean]; summary: [value: RoleEditorSummary | null] }>()

const loading = ref(true), busy = ref(false), error = ref(''), scopeError = ref('')
const current = ref<RoleAssignment | null>(null), choice = ref(''), scopeRefs = ref<string[]>([])
const departments = ref<DepartmentSummary[]>([]), companies = ref<Array<{ id: string; name: string }>>([])
const preview = ref<RolePreview | null>(null), original = ref(''), mustRead = ref(false)
const proof = useAccountProof(() => { preview.value = null })
const own = computed(() => props.subjectKind === 'employee')
const canEdit = computed(() => canIam('iam.roles.assign') && canIam(own.value ? 'iam.access.manage' : 'iam.departments.manage'))
const label = computed(() => props.subjectLabel || (own.value ? '这位员工' : props.subjectId))

// The role definition lives in one display adapter; the published catalogue from
// the server decides what may actually be granted. This page never invents an
// ability list from a role name (no hard-coded export or "all management").
const titleFor = (value?: string) => value === 'FOLLOW_DEPARTMENT' ? '跟随部门安排' : value === 'NONE' || value === '' ? '不安排角色' : value === 'LEGACY' ? '沿用已有安排' : roleTitle(value, current.value?.roles?.find(row => row.role_key === value)?.title)

type ResolvedRole = { title?: string; role_key?: string; responsibilities?: RoleScope[]; published_revision?: number; reason?: string }
const resolved = computed(() => (current.value?.selected_role || {}) as ResolvedRole)
const legacyForEmployee = computed(() => current.value?.mode === 'LEGACY')
const legacyForDepartment = computed(() => !own.value && current.value?.has_role_default === false)
const legacyAvailable = computed(() => legacyForEmployee.value || legacyForDepartment.value)

const source = computed(() => ['staff', 'clerk', 'admin'].includes(choice.value) ? 'DIRECT' : choice.value)
const sourceValue = computed({ get: () => source.value, set: (value: string) => setSource(value) })

function stateFromCurrent(): { choice: string; scopes: string[] } {
  if (!current.value) return { choice: '', scopes: [] }
  if (own.value) {
    if (current.value.mode === 'LEGACY') return { choice: 'LEGACY', scopes: [] }
    if (current.value.mode === 'DIRECT') return { choice: current.value.role_key || 'staff', scopes: (current.value.responsibilities || []).map(row => row.scope_ref) }
    return { choice: current.value.mode || 'FOLLOW_DEPARTMENT', scopes: [] }
  }
  if (current.value.has_role_default === false) return { choice: 'LEGACY', scopes: [] }
  return { choice: current.value.role_key === 'staff' ? 'staff' : '', scopes: [] }
}
function stateKey(value: string, scopes: string[]) {
  const mode = ['staff', 'clerk', 'admin'].includes(value) ? 'DIRECT' : value
  return JSON.stringify([mode, mode === 'DIRECT' ? value : '', [...scopes].sort()])
}
const dirty = computed(() => Boolean(current.value) && stateKey(choice.value, scopeRefs.value) !== original.value)
const publishedRevision = computed(() => typeof resolved.value.published_revision === 'number' ? resolved.value.published_revision : null)
const effectiveAllowed = computed(() => current.value?.effective_access?.allowed)
const currentLabel = computed(() => {
  if (!current.value) return ''
  if (!own.value) return current.value.has_role_default === false ? '沿用已有安排' : current.value.role_key === 'staff' ? '普通员工' : '不默认开通'
  if (current.value.mode === 'LEGACY') return '沿用已有独立安排'
  if (current.value.mode === 'NONE') return '不安排此角色'
  if (current.value.mode === 'FOLLOW_DEPARTMENT' && !resolved.value.role_key) return '跟随部门安排 · 部门未设默认角色'
  return resolved.value.title || titleFor(current.value.role_key || resolved.value.role_key)
})
const currentSourceText = computed(() => {
  if (!current.value) return ''
  if (!own.value) return '部门默认，仅影响选择跟随部门安排的员工'
  if (current.value.mode === 'FOLLOW_DEPARTMENT') return `跟随 ${deptLabels.value.get(current.value.department || '') || current.value.department || '所属部门'} 的部门安排`
  if (current.value.mode === 'DIRECT') return '为此人单独设置'
  if (current.value.mode === 'NONE') return '不安排此角色'
  return '沿用已有独立安排，不覆盖原权限来源'
})
const currentScopes = computed<RoleScope[]>(() => {
  if (!current.value || !own.value) return []
  if (current.value.mode === 'DIRECT') return current.value.responsibilities || []
  if (current.value.mode === 'FOLLOW_DEPARTMENT') return resolved.value.responsibilities || []
  return []
})
const deptLabels = computed(() => new Map(departments.value.map(row => [row.id, row.name])))
const companyLabels = computed(() => new Map(companies.value.map(row => [row.id, row.name])))
function scopeLabel(scope: { scope_type?: string; scope_ref?: string; label?: string }) {
  if (scope.scope_type === 'SELF') return '仅本人'
  if (scope.scope_type === 'DEPARTMENT') return `${scope.label || deptLabels.value.get(scope.scope_ref || '') || scope.scope_ref || '待核对部门'}（不含下级）`
  if (scope.scope_type === 'COMPANY') return scope.label || companyLabels.value.get(scope.scope_ref || '') || scope.scope_ref || '待核对公司'
  return scope.label || scope.scope_ref || '待核对范围'
}
const currentScopeText = computed(() => {
  if (!own.value) return current.value?.has_role_default === false ? '未覆盖现有安排' : current.value?.role_key === 'staff' ? '跟随者仅查看本人' : '跟随者不从部门默认获得角色功能'
  if (!current.value) return ''
  if (current.value.mode === 'NONE') return '不提供角色功能'
  if (current.value.mode === 'LEGACY') return '以原有独立安排为准'
  if (current.value.mode === 'FOLLOW_DEPARTMENT' && !resolved.value.role_key) return '部门未设默认角色'
  const roleKey = current.value.mode === 'DIRECT' ? current.value.role_key : resolved.value.role_key
  if (roleKey === 'staff' || !roleKey) return roleKey === 'staff' ? '仅本人' : '范围待核对'
  const rows = currentScopes.value
  return rows.length ? rows.map(scopeLabel).join('、') : '负责范围待核对'
})
const currentReason = computed(() => resolved.value.reason && !/沿用已有权限安排/.test(resolved.value.reason) ? resolved.value.reason : '')
const restrictionPattern = /禁止|暂停|期限|失效|过期|停用|待复核|限制|待确认/
const restrictionReasons = computed(() => {
  const rows = new Set<string>()
  for (const row of (current.value?.effective_access?.operations || []) as Array<{ allowed: boolean; reason?: string }>) if (!row.allowed && row.reason && restrictionPattern.test(row.reason)) rows.add(row.reason)
  const reason = current.value?.effective_access?.reason || ''
  if (reason && restrictionPattern.test(reason)) rows.add(reason)
  return [...rows]
})
const effectiveReason = computed(() => {
  const reason = current.value?.effective_access?.reason || ''
  return reason && reason !== currentReason.value && !restrictionReasons.value.includes(reason) ? reason : ''
})
const actualFunctions = computed(() => {
  const rows = (current.value?.effective_access?.operations || []) as Array<{ operation_id?: string; label?: string; scope_type?: string; scope_ref?: string; allowed: boolean }>
  const result = new Map<string, string>()
  for (const row of rows) {
    if (!row.allowed) continue
    const label = row.label || row.operation_id || '已登记功能'
    const scope = scopeLabel(row)
    result.set(`${label}|${scope}`, `${label} · ${scope}`)
  }
  return [...result.values()]
})
const selfReadAllowed = computed(() => {
  const operations = (current.value?.effective_access?.operations || []) as Array<{ operation_id?: string; allowed: boolean; scope_type?: string }>
  return operations.some(row => row.allowed && row.operation_id === 'attendance.read' && row.scope_type === 'SELF')
})
const currentRoleKey = computed(() => {
  if (!current.value) return ''
  if (current.value.mode === 'DIRECT') return current.value.role_key || ''
  if (current.value.mode === 'FOLLOW_DEPARTMENT') return resolved.value.role_key || ''
  return ''
})
const roleScopeSplitVisible = computed(() => Boolean(own.value && current.value && current.value.mode !== 'LEGACY' && ['clerk', 'admin'].includes(currentRoleKey.value)))
const roleScopeSplitCaption = computed(() => currentRoleKey.value === 'clerk' ? '明确负责的部门，不自动包含下级' : '明确负责的一个公司')
const roleStatusCode = computed(() => {
  if (!current.value) return '待核对'
  if (own.value && current.value.mode === 'NONE') return '未安排该角色'
  if (effectiveAllowed.value === false) return '当前暂不可用'
  return '安排已生效'
})
const roleStatusReason = computed(() => effectiveReason.value || currentReason.value || restrictionReasons.value[0] || '')
const editorSummary = computed<RoleEditorSummary | null>(() => {
  if (!current.value) return null
  return {
    source: currentSourceText.value || (own.value ? '来源待核对' : '本部门默认'),
    role: currentLabel.value || '待核对',
    scopes: currentScopeText.value || '待核对',
    functions: actualFunctions.value,
    status: own.value ? roleStatusCode.value : '部门默认已记录',
    reason: roleStatusReason.value,
    publishedRevision: publishedRevision.value,
  }
})
watch(editorSummary, value => emit('summary', value), { deep: true, immediate: true })

const departmentOptions = computed(() => {
  const rows = departments.value.filter(row => row.confirmed).map(row => ({ value: row.id, label: `${row.name} · ${companyLabels.value.get(row.company) || row.company}` }))
  const seen = new Set(rows.map(row => row.value))
  for (const scope of [...(current.value?.responsibilities || []), ...currentScopes.value]) {
    if (scope.scope_type !== 'DEPARTMENT' || !scope.scope_ref || seen.has(scope.scope_ref)) continue
    seen.add(scope.scope_ref)
    rows.push({ value: scope.scope_ref, label: `${deptLabels.value.get(scope.scope_ref) || scope.scope_ref} · 待核对公司` })
  }
  return rows
})
const companyOptions = computed(() => {
  const rows = companies.value.map(row => ({ value: row.id, label: row.name }))
  const seen = new Set(rows.map(row => row.value))
  for (const scope of [...(current.value?.responsibilities || []), ...currentScopes.value]) if (scope.scope_type === 'COMPANY' && scope.scope_ref && !seen.has(scope.scope_ref)) { seen.add(scope.scope_ref); rows.push({ value: scope.scope_ref, label: companyLabels.value.get(scope.scope_ref) || scope.scope_ref }) }
  if (current.value?.company && !seen.has(current.value.company)) rows.push({ value: current.value.company, label: companyLabels.value.get(current.value.company) || current.value.company })
  return rows
})

function resetState() {
  const state = stateFromCurrent()
  choice.value = state.choice
  scopeRefs.value = state.scopes
  original.value = stateKey(state.choice, state.scopes)
  preview.value = null
  requestId = ''
  requestPayload = ''
  proof.invalidate()
}
function setSource(value: string) {
  preview.value = null
  requestPayload = ''
  if (!own.value) { choice.value = value; scopeRefs.value = []; return }
  if (value === 'DIRECT') choice.value = current.value?.mode === 'DIRECT' && ['staff', 'clerk', 'admin'].includes(current.value.role_key) ? current.value.role_key : 'staff'
  else choice.value = value
  scopeRefs.value = []
}
function selectRole(value: string) {
  choice.value = value
  scopeRefs.value = []
  preview.value = null
  requestPayload = ''
}
function selectScope(values: string[]) {
  scopeRefs.value = values
  preview.value = null
  requestPayload = ''
}
function stateForSave() {
  const mode = ['staff', 'clerk', 'admin'].includes(choice.value) ? 'DIRECT' : choice.value
  return { mode, roleKey: mode === 'DIRECT' ? choice.value : '' }
}
function validationMessage() {
  if (!current.value) return '请先读取当前角色安排。'
  if (own.value) {
    if (choice.value === 'LEGACY') return '当前沿用已有独立安排；请选择跟随部门、个人单独设置或不安排角色后再核对。'
    if (!['FOLLOW_DEPARTMENT', 'NONE', 'staff', 'clerk', 'admin'].includes(choice.value)) return '请选择一种明确的角色来源。'
    if (choice.value === 'clerk' && !scopeRefs.value.length) return '部门考勤员必须明确选择至少一个负责部门，且不包含下级部门；请按实际组织选择。'
    if (choice.value === 'admin' && scopeRefs.value.length !== 1) return '考勤管理员必须明确选择一个负责公司。'
  } else {
    if (choice.value === 'LEGACY') return '当前部门尚未设置默认角色；请选择普通员工或不默认开通后再核对。'
    if (!['staff', ''].includes(choice.value)) return '部门默认只能选择普通员工或不默认开通。'
  }
  return ''
}
function params() {
  if (!current.value) throw new Error('请先读取当前角色。')
  const state = stateForSave()
  const responsibilities: RoleScope[] = (own.value && state.mode === 'DIRECT' && ['clerk', 'admin'].includes(state.roleKey))
    ? scopeRefs.value.map(scope_ref => ({ scope_type: state.roleKey === 'clerk' ? 'DEPARTMENT' : 'COMPANY', scope_ref, include_descendants: 0 }))
    : []
  return own.value
    ? { employee_id: props.subjectId, mode: state.mode, role_key: state.mode === 'DIRECT' ? state.roleKey : '', responsibilities, expected_version: current.value.version }
    : { department: props.subjectId, role_key: choice.value, expected_version: current.value.version }
}
function nextLabel() {
  if (own.value) {
    if (source.value === 'FOLLOW_DEPARTMENT') return '跟随部门安排'
    if (source.value === 'NONE') return '不安排此角色'
    if (source.value === 'LEGACY') return '沿用已有安排'
    return titleFor(choice.value)
  }
  if (choice.value === 'LEGACY') return '沿用已有安排'
  return choice.value === 'staff' ? '普通员工' : '不默认开通'
}
function nextScopeText() {
  if (!own.value) {
    if (choice.value === 'LEGACY') return '不覆盖现有跟随安排'
    return choice.value === 'staff' ? '跟随者仅查看本人' : '跟随者不从部门默认获得角色功能'
  }
  if (source.value === 'FOLLOW_DEPARTMENT') return previewAfterScopeText.value || '使用所属部门当前默认的负责范围'
  if (source.value === 'NONE' || source.value === 'LEGACY') return '不提供角色功能'
  if (choice.value === 'staff') return '仅本人'
  if (!scopeRefs.value.length) return '负责范围尚未选择'
  return scopeRefs.value.map(scope_ref => scopeLabel({ scope_type: choice.value === 'clerk' ? 'DEPARTMENT' : 'COMPANY', scope_ref })).join('、')
}
const previewTitle = computed(() => own.value ? '核对应用角色安排' : '核对部门默认安排')
const added = computed(() => {
  if (!preview.value?.before || !preview.value?.after) return []
  const before = new Set(preview.value.before.operations.filter(row => row.allowed).map(row => [row.operation_id, row.scope_type, row.scope_ref].join('|')))
  return preview.value.after.operations.filter(row => row.allowed && !before.has([row.operation_id, row.scope_type, row.scope_ref].join('|')))
})
const removed = computed(() => {
  if (!preview.value?.before || !preview.value?.after) return []
  const after = new Set(preview.value.after.operations.filter(row => row.allowed).map(row => [row.operation_id, row.scope_type, row.scope_ref].join('|')))
  return preview.value.before.operations.filter(row => row.allowed && !after.has([row.operation_id, row.scope_type, row.scope_ref].join('|')))
})
const previewMembers = computed(() => preview.value?.members || [])
const previewAfterScopeText = computed(() => {
  if (!preview.value?.after) return ''
  const rows = preview.value.after.operations.filter(row => row.allowed)
  const scopes = new Map<string, { scope_type: string; scope_ref: string }>()
  for (const row of rows) scopes.set(`${row.scope_type}|${row.scope_ref}`, { scope_type: row.scope_type, scope_ref: row.scope_ref })
  if (!scopes.size) return '当前暂不可用'
  return [...scopes.values()].map(scopeLabel).join('、')
})
const canSubmit = computed(() => Boolean(preview.value?.changed) && proof.valid.value && proof.method.value === 'password' && !mustRead.value && !busy.value && canEdit.value)
const previewScopeText = computed(() => own.value ? (preview.value?.after?.allowed ? '保存后按当前发布版本和已有限制判定可用功能。' : preview.value?.after?.reason || '当前暂不可用。') : '保存前已核对跟随者与实际影响。')

let generation = 0, actionGeneration = 0, requestId = '', requestPayload = '', disposed = false
const subjectIdentity = () => `${props.subjectKind}:${props.subjectId}`
async function load(preserve = false) {
  const run = ++generation
  const subject = subjectIdentity()
  const keep = preserve && Boolean(current.value)
  loading.value = true
  if (!keep) { error.value = ''; scopeError.value = ''; preview.value = null; mustRead.value = false; proof.invalidate() }
  try {
    const next = await roleQuery<RoleAssignment>(own.value ? 'get_assignment' : 'get_department_role', own.value ? { employee_id: props.subjectId } : { department: props.subjectId })
    if (disposed || run !== generation || subject !== subjectIdentity()) return
    current.value = next
    scopeError.value = ''
    if (!keep) resetState()
    else {
      original.value = stateKey(stateFromCurrent().choice, stateFromCurrent().scopes)
      preview.value = null
      mustRead.value = false
      error.value = ''
      proof.invalidate()
    }
    if (canIam('iam.departments.read')) {
      try {
        const scope = await listDepartments('all')
        if (disposed || run !== generation || subject !== subjectIdentity()) return
        departments.value = scope.items.filter(row => row.confirmed)
        companies.value = scope.companies
      } catch (e) {
        if (!disposed && run === generation && subject === subjectIdentity()) scopeError.value = iamMessage(e)
      }
    }
  } catch (e) {
    if (!disposed && run === generation && subject === subjectIdentity()) { error.value = iamMessage(e); if (keep) mustRead.value = true }
  } finally {
    if (!disposed && run === generation && subject === subjectIdentity()) loading.value = false
  }
}
async function prepare() {
  if (busy.value || mustRead.value || !canEdit.value || !dirty.value) return
  const invalid = validationMessage()
  if (invalid) { error.value = invalid; return }
  const run = ++actionGeneration
  const subject = subjectIdentity()
  const expectedVersion = current.value?.version
  busy.value = true; error.value = ''; proof.invalidate()
  try {
    const payload = params()
    const signature = JSON.stringify(payload)
    if (requestId && requestPayload !== signature) { requestId = ''; requestPayload = '' }
    const next = assertRolePreview(await roleCommand<RolePreview>(own.value ? 'preview_assignment' : 'preview_department_role', payload))
    if (disposed || run !== actionGeneration || subject !== subjectIdentity() || expectedVersion !== current.value?.version) return
    if (!requestId) requestId = crypto.randomUUID()
    requestPayload = signature
    preview.value = next
  } catch (e) {
    if (disposed || run !== actionGeneration || subject !== subjectIdentity()) return
    error.value = iamMessage(e)
    const status = (e as { status?: number }).status
    if (status === 409 || status === 500) mustRead.value = true
    proof.invalidate()
    preview.value = null
  } finally {
    if (run === actionGeneration) busy.value = false
  }
}
async function commit() {
  if (busy.value || mustRead.value || !preview.value || !proof.valid.value || proof.method.value !== 'password' || !canEdit.value || !preview.value.changed) return
  const run = ++actionGeneration
  const subject = subjectIdentity()
  const snapshot = preview.value
  const payload = { ...params(), context_revision: snapshot.context_revision, request_id: requestId }
  busy.value = true; error.value = ''
  try {
    await roleCommand(own.value ? 'save_assignment' : 'save_department_role', payload)
    if (disposed || run !== actionGeneration || subject !== subjectIdentity()) return
    proof.invalidate()
    preview.value = null
    requestId = ''; requestPayload = ''
    await load()
    if (disposed || run !== actionGeneration || subject !== subjectIdentity()) return
    emit('saved')
    message.success('角色安排已保存，已有暂停、个人禁止与期限限制继续保留。')
  } catch (e) {
    if (disposed || run !== actionGeneration || subject !== subjectIdentity()) return
    error.value = iamMessage(e)
    mustRead.value = true
    proof.invalidate()
    preview.value = null
  } finally {
    if (run === actionGeneration) busy.value = false
  }
}
function closePreview() { preview.value = null; proof.invalidate() }
async function requestLeave() {
  if (busy.value) return false
  if (!dirty.value) return true
  return new Promise<boolean>(resolve => Modal.confirm({
    title: '放弃尚未保存的角色安排？',
    content: '已保存的安排不受影响；本次选择会被清除。',
    okText: '放弃草稿', cancelText: '继续编辑',
    onOk: () => { resetState(); resolve(true) },
    onCancel: () => resolve(false),
  }))
}
async function cancelEdit() { if (await requestLeave()) { if (!dirty.value) resetState(); error.value = '' } }
async function back() { if (await requestLeave()) emit('back') }
function isDirty() { return dirty.value }
watch(dirty, value => emit('dirty', value), { immediate: true })
watch(() => [props.subjectKind, props.subjectId], () => {
  actionGeneration++; busy.value = false
  current.value = null; choice.value = ''; scopeRefs.value = []; original.value = ''; preview.value = null
  departments.value = []; companies.value = []; mustRead.value = false; error.value = ''; scopeError.value = ''; requestId = ''; requestPayload = ''
  proof.invalidate()
  void load(false)
}, { immediate: true, flush: 'sync' })
onBeforeUnmount(() => { disposed = true; generation++; proof.invalidate() })
defineExpose({ requestLeave, isDirty, loadLatest: () => load(true) })
</script>

<template>
  <section class="role-settings" :class="{ 'is-embedded': embedded }" :aria-label="own ? '员工考勤角色安排' : '部门默认考勤角色'">
    <div v-if="!embedded" class="role-heading"><a-button :disabled="busy" @click="back">返回应用清单</a-button><h2>{{ own ? `${label} · 考勤角色` : `${label} · 部门默认考勤角色` }}</h2></div>
    <a-alert v-if="scopeError" :message="scopeError" type="info" show-icon />
    <div v-if="error" class="role-error"><a-alert :message="error" type="warning" show-icon /><a-button v-if="error" :disabled="busy || loading" @click="load(true)">读取最新安排，保留草稿</a-button></div>
    <a-skeleton v-if="loading" active />
    <template v-else-if="current">
      <section class="role-current" aria-live="polite">
        <div>
          <span class="role-current-label">{{ own ? '当前安排' : '当前部门默认' }}</span>
          <strong>{{ currentLabel }}</strong>
          <p>{{ currentSourceText }}<span v-if="currentScopeText"> · </span>{{ currentScopeText }}</p>
          <p v-if="currentReason" class="role-reason">{{ currentReason }}</p>
          <p v-if="effectiveReason" class="role-reason">{{ effectiveReason }}</p>
          <div v-if="own && actualFunctions.length" class="role-effective"><span>当前实际可用功能（按已发布角色与服务端结果）</span><ul><li v-for="item in actualFunctions" :key="item">{{ item }}</li></ul></div>
          <div v-if="roleScopeSplitVisible" class="role-scope-split" aria-label="本人与明确负责范围">
            <div>
              <span>本人考勤</span>
              <strong>{{ selfReadAllowed ? '已包含：可查看本人考勤' : '已发布角色未包含本人考勤读取' }}</strong>
              <small v-if="!selfReadAllowed" class="role-scope-warning">不能只凭角色名称推断；需由角色管理员核对已发布功能。</small>
              <small v-else>该范围来自已发布角色的实际功能，不是页面推断。</small>
            </div>
            <div>
              <span>明确负责</span>
              <strong>{{ currentScopeText }}</strong>
              <small>{{ roleScopeSplitCaption }}；主部门变动不会自动扩大负责范围。</small>
            </div>
          </div>
        </div>
        <div class="role-current-tags">
          <StatusTag v-if="publishedRevision" tone="success">发布版本 v{{ publishedRevision }}</StatusTag>
          <StatusTag v-if="own && effectiveAllowed === true" tone="success">有可用功能</StatusTag>
          <StatusTag v-else-if="own && effectiveAllowed === false" tone="warning">当前暂不可用</StatusTag>
          <StatusTag v-if="!canEdit" tone="neutral">只读</StatusTag>
        </div>
      </section>

      <details v-if="restrictionReasons.length" class="role-restriction" aria-label="已有访问限制">
        <summary>已有限制（{{ restrictionReasons.length }}）</summary>
        <p v-for="reason in restrictionReasons" :key="reason">{{ reason }}</p>
        <p>保存角色来源或负责范围，不会解除已有的暂停、个人禁止或期限限制。</p>
      </details>
      <p v-else class="role-caveat">保存角色来源或负责范围，不会解除已有的暂停、个人禁止或期限限制。</p>

      <template v-if="canEdit && own">
        <fieldset :disabled="busy || mustRead || Boolean(preview)">
          <template v-if="own">
            <div class="field-section-title"><h3>角色来源</h3><span>只采用一种安排</span></div>
            <a-radio-group v-model:value="sourceValue" class="source-options" aria-label="角色来源">
              <a-radio-button v-if="legacyAvailable" value="LEGACY">沿用已有安排</a-radio-button>
              <a-radio-button value="FOLLOW_DEPARTMENT">跟随部门安排</a-radio-button>
              <a-radio-button value="DIRECT">为此人单独设置</a-radio-button>
              <a-radio-button value="NONE">不安排此角色</a-radio-button>
            </a-radio-group>
            <p class="role-scope-caption">单独设置只替换此人的考勤默认，不影响其他应用；返回部门安排不会解除已有的禁止与暂停。</p>
            <div v-if="source === 'FOLLOW_DEPARTMENT'" class="role-follow-note">
              <strong>跟随部门安排</strong>
              <p>使用所属部门当前的默认角色。单独设置只替换此人的考勤默认，不影响其他应用；个人安排和已有限制保留。</p>
            </div>
            <div v-else-if="source === 'NONE'" class="role-follow-note">
              <strong>不安排此角色</strong>
              <p>这位员工不通过角色获得考勤功能；登录账号、其他应用和个人限制不变。</p>
            </div>
            <div v-else-if="source === 'LEGACY'" class="role-follow-note">
              <strong>沿用已有安排（只读）</strong>
              <p>当前仍沿用已有独立安排。要改为明确安排，请选择上方来源；本页不会自动改写。</p>
            </div>
            <template v-else>
              <div class="field-section-title role-role-title"><h3>选择考勤角色</h3><span>与部门页使用同一已发布角色目录</span></div>
              <RoleChoiceGroup :model-value="choice" :catalog="current.roles || null" :disabled="busy || mustRead || Boolean(preview)" :name="`role-${subjectKind}-${subjectId}`" label="选择考勤角色" @update:model-value="selectRole" />
              <div class="field-section-title role-scope-title"><h3>负责范围</h3><span v-if="choice === 'clerk'">不自动包含下级部门</span><span v-else-if="choice === 'admin'">仅限一个公司</span><span v-else>无需另外选择</span></div>
              <ScopeSelector :role-key="choice" :model-value="scopeRefs" :departments="departmentOptions" :companies="companyOptions" :disabled="busy || mustRead || Boolean(preview)" :loading="Boolean(loading)" @update:model-value="selectScope" />
            </template>
          </template>
          <div class="role-actions">
            <span class="role-draft-state" role="status">{{ dirty ? '有未保存的修改' : '与当前安排一致' }}</span>
            <span v-if="!dirty" class="role-disabled-reason">{{ mustRead ? '请先读取最新安排' : '没有未保存的修改' }}</span>
            <a-button v-if="dirty" :disabled="busy" @click="cancelEdit">取消修改</a-button>
            <a-button type="primary" :disabled="!dirty || mustRead || busy || Boolean(preview)" :loading="busy" @click="prepare">{{ own ? '核对实际结果' : '预览影响' }}</a-button>
          </div>
        </fieldset>
        <div class="role-state-distinction" aria-label="三种状态的区别">
          <strong>三种状态分开处理</strong>
          <ul>
            <li><b>不安排该角色</b>：不通过角色获得考勤功能；登录账号和其他应用不变。</li>
            <li><b>暂停考勤应用</b>：临时不能使用考勤，角色与负责范围保留；在应用操作中单独确认。</li>
            <li><b>停用账号</b>：整个登录账号不可用，须在“登录账号”页单独处理。</li>
          </ul>
        </div>
      </template>
      <p v-else-if="canEdit" class="role-readonly">部门默认只在“部门应用权限”页设置一次；本页不再提供第二套部门编辑器，避免同一对象两处配置不一致。<RouterLink to="/hbos/admin/departments">前往部门应用权限</RouterLink></p>
      <p v-else class="role-readonly">只读：当前账号没有分配或修改角色安排的权限，页面不提供可提交的角色选择。</p>
    </template>

    <ChangeReview :open="Boolean(preview)" :busy="busy" :title="previewTitle" @cancel="closePreview">
      <section v-if="preview" class="role-preview" aria-live="polite">
        <div class="role-preview-subject"><strong>{{ label }}</strong><span>{{ own ? '考勤管理 · 只修改这位员工的安排' : '部门默认 · 只影响跟随部门安排的员工' }}</span></div>
        <div class="r6-assignment-compare">
          <div><small>当前安排</small><strong>{{ currentLabel }}</strong><p>{{ currentSourceText }}</p><strong>{{ currentScopeText }}</strong></div>
          <div><small>本次安排</small><strong>{{ nextLabel() }}</strong><p>{{ own ? (source === 'FOLLOW_DEPARTMENT' ? '跟随部门安排' : source === 'DIRECT' ? '为此人单独设置' : source === 'NONE' ? '不安排此角色' : '沿用已有安排') : '部门默认' }}</p><strong>{{ nextScopeText() }}</strong></div>
        </div>
        <template v-if="own">
          <div class="role-diff">
            <div v-if="added.length"><span class="role-diff-label added">新增 {{ added.length }} 项可用功能</span><ul><li v-for="row in added" :key="`${row.operation_id}-${row.scope_type}-${row.scope_ref}`">{{ row.label || '已登记功能' }} · {{ scopeLabel(row) }}</li></ul></div>
            <div v-if="removed.length"><span class="role-diff-label removed">减少 {{ removed.length }} 项可用功能</span><ul><li v-for="row in removed" :key="`${row.operation_id}-${row.scope_type}-${row.scope_ref}`">{{ row.label || '已登记功能' }} · {{ scopeLabel(row) }}</li></ul></div>
            <p v-if="!added.length && !removed.length">本次只调整角色来源或负责范围，功能清单没有变化。</p>
          </div>
          <p class="role-preview-effect">{{ previewScopeText }}</p>
          <details class="role-preview-restriction"><summary>{{ restrictionReasons.length ? '原有个人限制仍保留' : '个人限制说明' }}</summary><p v-for="reason in restrictionReasons" :key="reason">{{ reason }}</p><p>本页保存不会解除已有的暂停、个人禁止或期限限制。</p></details>
        </template>
        <template v-else>
          <div class="role-department-impact">
            <div><strong>{{ preview.reference_count ?? '待核对' }}</strong><span>跟随默认（服务端核对）</span></div>
            <div><strong>{{ preview.effective_changed_count ?? '待核对' }}</strong><span>实际权限变化</span></div>
            <div><strong>{{ preview.personal_preserved ?? '待核对' }}</strong><span>个人安排保留</span></div>
          </div>
          <p>跟随默认 {{ preview.reference_count ?? '待核对' }} 人；实际权限变化 {{ preview.effective_changed_count ?? '待核对' }} 人；个人安排保留 {{ preview.personal_preserved ?? '待核对' }} 人。</p>
          <p v-if="!previewMembers.length" class="role-scope-caption">服务端未返回跟随者名单；保存后以实际读取结果为准。</p>
          <ul v-else class="role-member-list"><li v-for="member in previewMembers" :key="member.employee"><strong>{{ member.name }}</strong><span>{{ member.changed ? '实际权限将变化' : '实际权限保持' }} {{ member.reason }}</span></li></ul>
          <p class="role-scope-caption">个人单独安排与已有禁止保留；部门默认不会自动分配部门考勤员或考勤管理员。</p>
        </template>
        <OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" />
        <div class="role-modal-actions">
          <a-button :disabled="busy" @click="closePreview">返回修改</a-button>
          <a-button type="primary" :disabled="!canSubmit" :loading="busy" @click="commit">确认保存</a-button>
        </div>
      </section>
    </ChangeReview>
  </section>
</template>

<style scoped>
.role-legacy-state{padding:13px 15px;border:1px solid #e3e7f0;border-radius:10px;background:#f8f9fc;margin:0 0 14px}
.role-legacy-state>div{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.role-legacy-state strong{font-size:13px;line-height:21px;color:#34456e}
.role-legacy-state p{margin:6px 0 0;color:var(--r6-secondary);font-size:12px;line-height:20px}
.role-scope-split{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px;padding-top:12px;border-top:1px solid #e5e9f2}
.role-scope-split>div{min-width:0;padding:13px 15px;border:1px solid #e5e9f2;border-radius:10px;background:#fff}
.role-scope-split span{display:block;color:var(--r6-muted);font-size:11px;line-height:18px}
.role-scope-split strong{display:block;margin-top:3px;font-size:14px;line-height:22px;color:#192a45;overflow-wrap:anywhere}
.role-scope-split small{display:block;margin-top:5px;color:var(--r6-muted);font-size:11px;line-height:18px}
.role-scope-warning{color:#94600e!important}
.role-state-distinction{margin-top:2px;padding:13px 15px;border:1px solid #efe2c7;border-radius:10px;background:#fffbf2;color:#836e49}
.role-state-distinction strong{display:block;font-size:12px;line-height:20px;color:#906722}
.role-state-distinction ul{margin:6px 0 0;padding-left:18px;font-size:12px;line-height:20px}
.role-state-distinction b{font-weight:600}
.role-disabled-reason{align-self:center;color:var(--r6-muted);font-size:12px;line-height:19px}
@media(max-width:760px){.role-scope-split{grid-template-columns:1fr}}
.role-settings{display:grid;gap:16px;font-size:14px;min-width:0}.role-settings.is-embedded{gap:18px}.role-heading{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.role-heading h2{margin:0;font-size:20px}.role-error{display:grid;gap:10px;justify-items:start}.role-current{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;padding:17px 20px;border:1px solid #e8eaf3;border-radius:12px;background:#f7f8fc;min-width:0}.role-current>div{min-width:0}.role-current-label{display:block;margin-bottom:4px;color:var(--r6-muted);font-size:12px}.role-current strong{font-size:15px;overflow-wrap:anywhere}.role-current p{margin:6px 0 0;color:var(--r6-secondary);font-size:13px;line-height:21px;overflow-wrap:anywhere}.role-current .role-reason{color:var(--r6-muted);font-size:12px}.role-effective{margin-top:12px;padding-top:10px;border-top:1px solid #e5e9f2}.role-effective span{display:block;color:var(--r6-muted);font-size:11px;margin-bottom:4px}.role-effective ul{list-style:none;margin:0;padding:0;display:grid;gap:3px;color:var(--r6-secondary);font-size:12px;line-height:19px}.role-card-icon{display:grid;place-items:center;width:28px;height:30px;border-radius:8px;background:#f0f2f8;color:#7a72bf;font-size:16px}.role-card-capability{margin:2px 0 0!important;color:var(--r6-muted)!important;font-size:11px!important;line-height:18px!important}.role-current-tags{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end;flex:none}.role-caveat,.role-readonly,.role-withheld{margin:0;padding:12px 14px;border:1px solid #efe2c7;border-radius:10px;background:#fffbf2;color:#836e49;font-size:12px;line-height:20px}.role-readonly{background:#f7f8fc;border-color:#e5e9f2;color:var(--r6-secondary)}.role-withheld{border-color:#dfe4f8;background:#f4f6ff;color:#525c88}.role-restriction{padding:14px 16px;border:1px solid #efe2c7;border-radius:10px;background:#fffbf2;color:#906722;font-size:12px;line-height:20px}.role-restriction summary{cursor:pointer;font-size:12px;min-height:30px;display:flex;align-items:center}.role-restriction p{margin:5px 0 0}.field-section-title{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:22px 0 12px}.field-section-title h3{margin:0;font-size:15px}.field-section-title>span{font-size:12px;color:var(--r6-muted);text-align:right}.role-role-title{margin-top:20px}.role-scope-title{margin-top:18px}.source-options{display:flex;width:100%}.source-options :deep(.ant-radio-button-wrapper){flex:1;display:flex;align-items:center;justify-content:center;padding:0 10px;font-size:13px;white-space:nowrap;background:#fff;text-align:center;height:auto;min-height:40px;line-height:20px}.source-options :deep(.ant-radio-button-wrapper-checked){background:#f1efff!important;box-shadow:none!important}.role-follow-note{padding:17px 18px;border:1px dashed #d6d5eb;border-radius:12px;margin-top:16px;background:#fafaff}.role-follow-note strong{font-size:14px}.role-follow-note p{margin:7px 0 0;color:var(--r6-secondary);font-size:12px;line-height:20px}.r6-role-cards{margin:14px 0 0}.r6-role-card{align-content:start;cursor:pointer}.r6-role-card.selected{border-color:#b6a6ff;background:#f6f2ff;box-shadow:0 0 0 1px #b6a6ff}.r6-role-card ul{list-style:none;margin:2px 0 0;padding:0;display:grid;gap:2px;color:var(--r6-muted);font-size:11px;line-height:18px}.role-self-scope{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:13px 15px;border:1px solid #e5e9f2;border-radius:10px;background:#f5f7fb}.role-self-scope span{color:var(--r6-muted);font-size:12px}.role-scope-caption{margin:10px 0 0;color:var(--r6-muted);font-size:12px;line-height:20px}.department-default-options{display:grid;gap:10px;width:100%}.department-default-options :deep(.ant-radio-wrapper){display:flex;align-items:flex-start;margin:0;padding:15px 16px;border:1px solid #e5e9f2;border-radius:11px;min-height:76px}.department-default-options :deep(.ant-radio-wrapper-checked){border-color:#bab5ea;background:#f7f6ff}.department-default-options :deep(.ant-radio){margin-top:4px}.department-default-options strong,.department-default-options small{display:block}.department-default-options strong{font-size:14px}.department-default-options small{margin-top:4px;color:var(--r6-secondary);font-size:12px;line-height:20px}.role-actions{display:flex;align-items:center;justify-content:flex-end;gap:10px;flex-wrap:wrap;margin-top:20px;padding-top:16px;border-top:1px solid #e5e9f2}.role-draft-state{margin-right:auto;color:var(--r6-muted);font-size:12px}.role-preview{display:grid;gap:14px}.role-preview-subject{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}.role-preview-subject strong{font-size:16px}.role-preview-subject span{color:var(--r6-muted);font-size:12px}.r6-assignment-compare>div{min-width:0}.r6-assignment-compare p{margin:6px 0 0;overflow-wrap:anywhere}.r6-assignment-compare strong{display:block;margin-top:8px;overflow-wrap:anywhere}.role-diff{padding:4px 2px}.role-diff-label{display:inline-flex;margin-top:8px;font-size:13px;font-weight:600}.role-diff-label.added{color:#227451}.role-diff-label.removed{color:#ad4b60}.role-diff ul{margin:8px 0 0;padding-left:18px;color:var(--r6-secondary);font-size:12px;line-height:22px;overflow-wrap:anywhere}.role-diff p{margin:4px 0 0;color:var(--r6-secondary);font-size:12px}.role-preview-effect{margin:0;color:var(--r6-secondary);font-size:13px;line-height:21px}.role-preview-restriction{padding:13px 15px;border:1px solid #efe2c7;border-radius:10px;background:#fffbf2;color:#836e49;font-size:12px;line-height:20px}.role-preview-restriction summary{cursor:pointer;font-weight:600;min-height:28px;display:flex;align-items:center}.role-preview-restriction p{margin:5px 0 0}.role-department-impact{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.role-department-impact>div{padding:12px;border:1px solid #e5e9f2;border-radius:10px;background:#f8f9fc}.role-department-impact strong{display:block;font-size:22px;line-height:30px}.role-department-impact span{display:block;margin-top:4px;color:var(--r6-muted);font-size:11px;line-height:18px}.role-member-list{list-style:none;margin:0;padding:0;display:grid;gap:8px}.role-member-list li{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;padding:10px 12px;border:1px solid #e5e9f2;border-radius:8px;font-size:12px}.role-member-list span{color:var(--r6-secondary)}.role-modal-actions{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;padding-top:14px;border-top:1px solid #e5e9f2}.full-width{width:100%}fieldset{border:0;padding:0;margin:0;min-width:0}.ant-select{width:100%}@media(max-width:760px){.source-options{display:grid;grid-template-columns:1fr}.source-options :deep(.ant-radio-button-wrapper){border-radius:8px!important;margin:0 0 6px}.role-current{flex-direction:column}.role-current-tags{justify-content:flex-start}.role-department-impact{grid-template-columns:1fr}.role-actions{justify-content:stretch}.role-actions .ant-btn{flex:1}.role-draft-state{width:100%;margin:0}}
</style>
