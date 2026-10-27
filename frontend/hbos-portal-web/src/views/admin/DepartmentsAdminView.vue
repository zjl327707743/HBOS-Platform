<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { listDepartments } from '@/services/iamDepartments'
import { getDepartmentWork } from '@/services/iamWork'
import { canIam, iamMessage, iamSession } from '@/services/iamAccess'
import { roleQuery, roleCommand, assertRolePreview, type RoleAssignment, type RolePreview } from '@/services/iamRoles'
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
const viewGroup = ref('daily'), groupsAvailable = ref(false), companies = ref<Array<{ id: string; name: string }>>([]), company = ref(''), treeSearch = ref(''), expanded = ref<string[]>([])
const departments = ref<DepartmentSummary[]>([]), selected = ref(''), apps = ref<WorkApp[]>([]), editingApp = ref<string | null>(null), search = ref(''), page = ref(1), loading = ref(true), error = ref(''), employeeId = ref(''), drawerOpen = ref(false)
const settings = ref<InstanceType<typeof WorkSettings> | null>(null)
const current = computed(() => departments.value.find(row => row.id === selected.value))
const members = computed(() => (current.value?.members || []).filter(row => !search.value || [row.name, row.employee_number, row.position].join(' ').toLowerCase().includes(search.value.toLowerCase())))
const otherApps = computed(() => apps.value.filter(row => row.app_id !== 'attendance'))
const canReadApps = computed(() => canIam('iam.access.read'))
const canManageDepartmentRole = computed(() => canIam('iam.departments.manage') && canIam('iam.roles.assign'))
const columns = [{ title: '姓名 / 工号', key: 'name', width: '30%' }, { title: '岗位', dataIndex: 'position', width: '28%' }, { title: '账号状态', key: 'status', width: '22%' }, { title: '操作', key: 'action', width: '20%' }]
const linkTarget = () => typeof route.query.department === 'string' ? route.query.department : undefined

const departmentCurrent = ref<RoleAssignment | null>(null), departmentChoice = ref(''), departmentPreview = ref<RolePreview | null>(null)
const baselineImpact = ref<RolePreview | null>(null), baselineStatus = ref<'idle' | 'loading' | 'ready' | 'error' | 'unavailable'>('idle'), baselineError = ref('')
const departmentBusy = ref(false), departmentError = ref(''), departmentMustRead = ref(false)
const departmentProof = useAccountProof(() => { departmentPreview.value = null })
let departmentReadGeneration = 0, departmentActionGeneration = 0, departmentRequestId = '', departmentRequestPayload = ''

const departmentDirty = computed(() => Boolean(departmentCurrent.value) && departmentChoice.value !== currentDepartmentChoice())
const baselineLoading = computed(() => baselineStatus.value === 'loading')
const baselineLegacy = computed(() => departmentCurrent.value?.has_role_default === false)
const currentDepartmentText = computed(() => !departmentCurrent.value ? '待核对' : departmentCurrent.value.has_role_default === false ? '沿用已有安排' : departmentCurrent.value.role_key === 'staff' ? '普通员工' : '不默认开通')
const nextDepartmentText = computed(() => departmentChoice.value === 'LEGACY' ? '沿用已有安排' : departmentChoice.value === 'staff' ? '普通员工' : '不默认开通')
const canSubmitDepartment = computed(() => Boolean(departmentPreview.value?.changed) && departmentProof.valid.value && departmentProof.method.value === 'password' && !departmentBusy.value && !departmentMustRead.value && canManageDepartmentRole.value)
const baselineMembers = computed(() => baselineImpact.value?.members || [])
const candidateMembers = computed(() => departmentPreview.value?.members || [])
const baselineRestrictions = computed(() => baselineLegacy.value ? [] : baselineMembers.value.filter(row => /禁止|暂停|期限|失效|过期|停用|待复核|限制|待确认/.test(row.reason || '')))

const tree = computed(() => {
  const included = new Set<string>(), query = treeSearch.value.trim().toLowerCase()
  for (const row of departments.value.filter(row => !query || row.name.toLowerCase().includes(query))) {
    let item: DepartmentSummary | undefined = row
    while (item && !included.has(item.id)) { included.add(item.id); item = departments.value.find(parent => parent.id === item!.parent_department) }
  }
  const visited = new Set<string>()
  const build = (parent: string | null): unknown[] => departments.value.filter(row => !visited.has(row.id) && included.has(row.id) && ((row.parent_department || null) === parent || parent === null && row.parent_department && !departments.value.some(item => item.id === row.parent_department))).map(row => { visited.add(row.id); return { key: row.id, title: row.name, children: build(row.id) } })
  return build(null)
})
const expandedKeys = computed(() => treeSearch.value ? departments.value.filter(row => departments.value.some(item => item.parent_department === row.id)).map(row => row.id) : expanded.value)

let generation = 0, appRead = 0, linkRead = 0, routeRevision = 0, disposed = false
function revealSelection() { let row = current.value; const keys = new Set(expanded.value); while (row?.parent_department && !keys.has(row.parent_department)) { keys.add(row.parent_department); row = departments.value.find(item => item.id === row!.parent_department) }; expanded.value = [...keys] }
function currentDepartmentChoice() {
  if (!departmentCurrent.value) return ''
  return departmentCurrent.value.has_role_default === false ? 'LEGACY' : departmentCurrent.value.role_key === 'staff' ? 'staff' : ''
}
function countText(value?: number) { return typeof value === 'number' ? String(value) : '待核对' }
function resetDepartmentDraft() {
  departmentChoice.value = currentDepartmentChoice()
  departmentPreview.value = null
  departmentError.value = ''
  departmentRequestId = ''; departmentRequestPayload = ''
  departmentProof.invalidate()
}
function clearDepartmentState() {
  departmentReadGeneration++; departmentActionGeneration++; departmentBusy.value = false
  departmentCurrent.value = null; departmentChoice.value = ''; departmentPreview.value = null
  baselineImpact.value = null; baselineStatus.value = 'idle'; baselineError.value = ''
  departmentError.value = ''; departmentMustRead.value = false
  departmentRequestId = ''; departmentRequestPayload = ''
  departmentProof.invalidate()
}
async function confirmDiscardDepartmentDraft() {
  if (!departmentDirty.value) return true
  return new Promise<boolean>(resolve => Modal.confirm({
    title: '放弃尚未保存的部门默认安排？',
    content: '已保存的部门默认与个人安排不受影响。',
    okText: '放弃草稿', cancelText: '继续编辑',
    onOk: () => { resetDepartmentDraft(); resolve(true) },
    onCancel: () => resolve(false),
  }))
}
async function requestLeave() {
  if (departmentBusy.value) return false
  if (!await confirmDiscardDepartmentDraft()) return false
  if (settings.value && !await settings.value.requestLeave()) return false
  return true
}
async function cancelDepartmentEdit() {
  if (!departmentDirty.value) { resetDepartmentDraft(); return }
  await confirmDiscardDepartmentDraft()
}
async function loadDepartmentRole(preserve = false) {
  const id = selected.value
  if (!id || !iamSession.rolesEnabled || !canReadApps.value) { clearDepartmentState(); return }
  const run = ++departmentReadGeneration
  const keep = preserve && Boolean(departmentCurrent.value)
  if (!keep) { departmentCurrent.value = null; departmentChoice.value = ''; departmentPreview.value = null; departmentMustRead.value = false; departmentError.value = ''; departmentRequestId = ''; departmentRequestPayload = '' }
  baselineImpact.value = null; baselineError.value = ''; baselineStatus.value = 'loading'
  departmentPreview.value = null
  try {
    const next = await roleQuery<RoleAssignment>('get_department_role', { department: id })
    if (disposed || run !== departmentReadGeneration || selected.value !== id) return
    departmentCurrent.value = next
    if (!keep) resetDepartmentDraft()
    else { departmentMustRead.value = false; departmentError.value = ''; departmentProof.invalidate() }
    if (!canManageDepartmentRole.value) { baselineStatus.value = 'unavailable'; return }
    try {
      const impact = assertRolePreview(await roleCommand<RolePreview>('preview_department_role', { department: id, role_key: next.role_key || '', expected_version: next.version }))
      if (disposed || run !== departmentReadGeneration || selected.value !== id) return
      baselineImpact.value = impact
      baselineStatus.value = 'ready'
    } catch (e) {
      if (disposed || run !== departmentReadGeneration || selected.value !== id) return
      baselineImpact.value = null
      baselineError.value = iamMessage(e)
      baselineStatus.value = 'error'
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
  if (departmentBusy.value || departmentMustRead.value || !canManageDepartmentRole.value || !departmentDirty.value) return
  if (!['staff', ''].includes(departmentChoice.value)) { departmentError.value = '请选择普通员工或不默认开通后再核对。'; return }
  const run = ++departmentActionGeneration
  const id = selected.value, version = departmentCurrent.value?.version, choice = departmentChoice.value
  if (!id || version === undefined) { departmentError.value = '请先读取当前部门默认。'; return }
  departmentBusy.value = true; departmentError.value = ''; departmentProof.invalidate()
  try {
    const payload = { department: id, role_key: choice, expected_version: version }
    const signature = JSON.stringify(payload)
    if (departmentRequestId && departmentRequestPayload !== signature) { departmentRequestId = ''; departmentRequestPayload = '' }
    const next = assertRolePreview(await roleCommand<RolePreview>('preview_department_role', payload))
    if (disposed || run !== departmentActionGeneration || selected.value !== id || departmentChoice.value !== choice || departmentCurrent.value?.version !== version) return
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
  } finally {
    if (run === departmentActionGeneration) departmentBusy.value = false
  }
}
async function commitDepartmentRole() {
  if (!canSubmitDepartment.value || !departmentCurrent.value || !departmentPreview.value) return
  const run = ++departmentActionGeneration
  const id = selected.value, version = departmentCurrent.value.version, choice = departmentChoice.value
  const preview = departmentPreview.value
  departmentBusy.value = true; departmentError.value = ''
  try {
    await roleCommand('save_department_role', { department: id, role_key: choice, expected_version: version, context_revision: preview.context_revision, request_id: departmentRequestId })
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    departmentProof.invalidate()
    departmentPreview.value = null
    departmentRequestId = ''; departmentRequestPayload = ''
    departmentMustRead.value = false
    await loadDepartmentRole()
    await loadApps()
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    message.success('部门默认安排已保存，已有个人安排和限制继续保留。')
  } catch (e) {
    if (disposed || run !== departmentActionGeneration || selected.value !== id) return
    departmentError.value = iamMessage(e)
    departmentMustRead.value = true
    departmentProof.invalidate()
    departmentPreview.value = null
  } finally {
    if (run === departmentActionGeneration) departmentBusy.value = false
  }
}
function closeDepartmentPreview() { departmentPreview.value = null; departmentProof.invalidate() }

async function loadApps() {
  const run = ++appRead, id = selected.value; apps.value = []
  if (!canReadApps.value || !id) return
  try {
    const result = await getDepartmentWork(id)
    if (disposed || run !== appRead || selected.value !== id) return
    apps.value = result.apps
    if (!iamSession.rolesEnabled && current.value?.confirmed && activeTab.value === 'apps' && !editingApp.value && apps.value.some(row => row.app_id === 'attendance' && row.integrated)) editingApp.value = 'attendance'
    if (editingApp.value && !apps.value.some(row => row.app_id === editingApp.value && row.integrated)) editingApp.value = null
  } catch (e) {
    if (!disposed && run === appRead) { apps.value = []; error.value = iamMessage(e) }
  }
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
async function applyLink() {
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
  selected.value = target.department; revealSelection()
  activeTab.value = target.tab === 'apps' && canReadApps.value ? 'apps' : 'members'
  await loadApps()
  if (!currentTarget()) return
  if (iamSession.rolesEnabled) {
    editingApp.value = current.value?.confirmed && activeTab.value === 'apps' && target.app && target.app !== 'attendance' && apps.value.some(row => row.app_id === target.app && row.integrated) ? target.app : null
    if (target.app && target.app !== 'attendance' && editingApp.value !== target.app) error.value = '该部门或应用当前不可查看，已返回可用部门。'
  } else {
    editingApp.value = current.value?.confirmed && activeTab.value === 'apps' && target.app && apps.value.some(row => row.app_id === target.app && row.integrated) ? target.app : current.value?.confirmed && activeTab.value === 'apps' && apps.value.some(row => row.app_id === 'attendance' && row.integrated) ? 'attendance' : null
    if (target.app && editingApp.value !== target.app) error.value = '该部门或应用当前不可查看，已返回可用部门。'
  }
}
async function load() {
  if (!await requestLeave()) return
  const run = ++generation, routeAtStart = routeRevision; loading.value = true; error.value = ''
  try {
    const data = await listDepartments(viewGroup.value, linkTarget(), company.value || undefined)
    if (disposed || run !== generation || routeAtStart !== routeRevision) return
    departments.value = data.items; companies.value = data.companies; company.value = data.selected_company || ''; groupsAvailable.value = data.groups_available === true
    if (!departments.value.some(row => row.id === selected.value)) selected.value = (departments.value.find(row => row.confirmed && row.members?.length) || departments.value.find(row => row.members?.length) || departments.value[0])?.id || ''
    revealSelection(); await loadApps(); if (disposed || run !== generation || routeAtStart !== routeRevision) return; await applyLink()
  } catch (e) { if (!disposed && run === generation && routeAtStart === routeRevision) error.value = iamMessage(e) }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function select(keys: unknown[]) {
  const id = String(keys[0] || ''); if (!id || id === selected.value || !await requestLeave()) return
  selected.value = id; editingApp.value = null; search.value = ''; page.value = 1
  try { await loadApps() } catch (e) { if (!disposed) error.value = iamMessage(e) }
}
async function changeCompany(value: string) { if (!await requestLeave()) return; company.value = value; selected.value = ''; expanded.value = []; editingApp.value = null; await load() }
async function changeGroup(value: string) { if (!await requestLeave()) return; viewGroup.value = value; selected.value = ''; expanded.value = []; editingApp.value = null; await load() }
function changeTab(value: string) { activeTab.value = value }
function openOtherApp(appId: string) { editingApp.value = appId }
watch(selected, () => {
  clearDepartmentState()
  if (selected.value && iamSession.rolesEnabled && canReadApps.value) void loadDepartmentRole()
}, { flush: 'post' })
onBeforeRouteLeave(() => requestLeave())
onBeforeRouteUpdate(() => requestLeave())
watch(() => route.query, () => { routeRevision++; if (!loading.value) void applyLink().catch(e => { if (!disposed) error.value = iamMessage(e) }) })
useManagementViewMemory('DepartmentsAdminView.vue', { viewGroup, company, treeSearch, selected, activeTab, search, page })
onMounted(load)
onBeforeUnmount(() => { disposed = true; generation++; appRead++; linkRead++; departmentReadGeneration++; departmentActionGeneration++; apps.value = []; departments.value = [] })
</script>

<template>
  <section class="r6-page r6-departments-page">
    <PageHeading eyebrow="组织管理" title="部门安排" description="为部门设置基础默认，特殊职责逐人设置。" />
    <div v-if="error" class="r6-resource-error"><a-alert :message="error" type="warning" show-icon /><a-button @click="load">重试读取</a-button></div>
    <a-skeleton v-if="loading" active />
    <div v-else class="r6-dual-panels">
      <PanelFrame as="aside" region="department-list" label="组织部门目录" class="r6-navigation r6-department-tree">
        <template #header><h3>选择部门</h3><a-select v-if="groupsAvailable" :value="viewGroup" aria-label="部门分组" style="margin-bottom:12px" @change="changeGroup"><a-select-option value="daily">日常组织</a-select-option><a-select-option value="technical">技术验证夹具</a-select-option><a-select-option value="all">全部部门</a-select-option></a-select><a-select v-if="companies.length > 1" :value="company" aria-label="部门所属公司" style="margin-bottom:12px" @change="changeCompany"><a-select-option v-for="item in companies" :key="item.id" :value="item.id">{{ item.name }}</a-select-option></a-select><a-input v-model:value="treeSearch" placeholder="搜索部门" aria-label="搜索组织部门" allow-clear /></template>
        <a-tree :tree-data="tree" :selected-keys="[selected]" :expanded-keys="expandedKeys" block-node @expand="(keys: unknown[]) => expanded = keys.map(String)" @select="select"><template #title="{ title }"><span :title="title">{{ title }}</span></template></a-tree>
        <template #footer>部门默认与个人单独安排分别核对。</template>
      </PanelFrame>
      <PanelFrame region="department-detail" label="部门默认安排与成员">
        <template v-if="current" #header><div class="r6-department-title"><h2>{{ current.name }}</h2><p>{{ current.company }} · 当前可见主部门成员 {{ current.members?.length || 0 }} 人（仅当前部门）</p></div><StatusTag v-if="!current.confirmed" tone="warning">尚未确认，暂不安排人员或权限</StatusTag><a-radio-group :value="activeTab" @change="(event: { target: { value: string } }) => changeTab(event.target.value)" button-style="solid" style="margin-top:16px"><a-radio-button v-if="canReadApps" value="apps">默认角色与应用</a-radio-button><a-radio-button value="members">部门成员</a-radio-button></a-radio-group></template>
        <div v-show="activeTab === 'apps' && canReadApps && current">
          <WorkSettings v-if="editingApp && current?.confirmed" :key="selected + ':' + editingApp" ref="settings" subject-kind="department" :subject-id="selected" :app-id="editingApp" @back="editingApp = null" @saved="loadApps" />
          <div v-show="!editingApp">
          <template v-if="current">
            <template v-if="current.confirmed">
              <template v-if="iamSession.rolesEnabled">
                <div v-if="departmentError" class="r6-resource-error"><a-alert :message="departmentError" type="warning" show-icon /><a-button :disabled="departmentBusy" @click="loadDepartmentRole(true)">读取最新部门安排，保留草稿</a-button></div>
                <p class="r6-dept-lead">部门默认只提供普通员工的基础角色，仅影响选择跟随部门安排的员工；个人安排和已有限制保留。</p>
                <a-radio-group v-if="canManageDepartmentRole && departmentCurrent" v-model:value="departmentChoice" :disabled="departmentBusy || departmentMustRead || Boolean(departmentPreview)" class="department-default-options" aria-label="部门默认角色">
                  <a-radio v-if="baselineLegacy" value="LEGACY" disabled><span><strong>沿用已有安排</strong><small>当前未设置新的部门默认，保留现有跟随安排。</small></span><StatusTag tone="neutral">只读</StatusTag></a-radio>
                  <a-radio value="staff"><span><strong>普通员工</strong><small>跟随者可查看自己的考勤，不查看同部门其他人。</small></span></a-radio>
                  <a-radio value=""><span><strong>不默认开通</strong><small>跟随者不从部门默认获得角色功能。</small></span></a-radio>
                </a-radio-group>
                <div v-else-if="!departmentCurrent" class="r6-dept-readonly"><strong>当前部门默认待核对</strong><StatusTag tone="neutral">待核对</StatusTag><p>读取失败或尚未完成，请重试核对或查看部门成员。</p></div>
                <div v-else class="r6-dept-readonly"><strong>{{ currentDepartmentText }}</strong><StatusTag tone="neutral">只读</StatusTag><p>当前账号可以查看部门默认，但不能核对或保存新的默认。</p></div>

                <div class="r6-dept-counts" aria-label="当前部门默认影响">
                  <div><strong>{{ countText(baselineImpact?.reference_count) }}</strong><span>跟随人数</span></div>
                  <div><strong>{{ countText(baselineImpact?.personal_preserved) }}</strong><span>单独安排保留</span></div>
                </div>
                <p v-if="baselineLoading" class="r6-dept-note" role="status">正在核对当前跟随范围…</p>
                <div v-else-if="baselineStatus === 'error'" class="r6-dept-baseline-error"><a-alert :message="baselineError" type="warning" show-icon /><div class="r6-dept-baseline-actions"><a-button @click="loadDepartmentRole(true)">重试核对</a-button><a-button @click="changeTab('members')">查看部门成员</a-button></div></div>
                <p v-else-if="baselineStatus === 'unavailable'" class="r6-dept-note">当前账号不能核对跟随人数，可在部门成员中查看人员。</p>
                <template v-else-if="baselineStatus === 'ready'">
                  <div class="r6-dept-follow-head"><h4>跟随此安排的同事</h4><a-button type="link" @click="changeTab('members')">查看部门成员</a-button></div>
                  <ul v-if="baselineMembers.length" class="r6-dept-followers"><li v-for="member in baselineMembers" :key="member.employee"><strong>{{ member.name }}</strong><span>{{ member.before_allowed ? '当前有可用考勤' : '当前暂不可用' }}</span></li></ul>
                  <p v-else-if="(baselineImpact?.reference_count || 0) === 0" class="r6-dept-note">当前没有跟随者。</p>
                  <div v-else class="r6-dept-baseline-error"><p class="r6-dept-note">核对结果未返回跟随成员名单。</p><a-button @click="changeTab('members')">查看部门成员</a-button></div>
                  <details v-if="baselineRestrictions.length" class="r6-dept-restrictions"><summary>已有限制详情（{{ baselineRestrictions.length }}）</summary><p v-for="member in baselineRestrictions" :key="member.employee"><strong>{{ member.name }}</strong>：{{ member.reason }}</p></details>
                </template>
              </template>
              <template v-else>
                <a-alert type="info" show-icon message="应用角色功能尚未启用" description="以下保留原有应用权限兼容入口，不新增角色选择。" />
                <article v-for="app in apps" :key="app.app_id" class="r6-department-app"><div><strong>{{ app.title }}</strong><p>{{ app.integrated ? app.summary : '尚未接入此管理功能，暂不能在此调整。' }}</p></div><a-button v-if="app.integrated" :disabled="!current.confirmed" @click="openOtherApp(app.app_id)">{{ canIam('iam.departments.manage') ? '设置安排' : '查看安排' }}</a-button></article>
              </template>
              <section v-if="iamSession.rolesEnabled && otherApps.length" class="r6-dept-other-apps">
                <div class="field-section-title"><h3>其他应用安排</h3><span>不改变考勤默认</span></div>
                <article v-for="app in otherApps" :key="app.app_id" class="r6-department-app"><div><strong>{{ app.title }}</strong><p>{{ app.integrated ? app.summary : '尚未接入此管理功能，暂不能在此调整。' }}</p></div><a-button v-if="app.integrated" :disabled="!current.confirmed" @click="openOtherApp(app.app_id)">{{ canIam('iam.departments.manage') ? '设置安排' : '查看安排' }}</a-button></article>
              </section>
            </template>
            <a-alert v-else type="warning" show-icon message="部门尚未确认，暂不安排默认角色或人员" description="请先完成部门确认；部门成员仍可在下方查看。" />
          </template>
          </div>
        </div>
        <div v-show="activeTab === 'members' && current">
          <div class="iam-toolbar"><a-input v-model:value="search" class="iam-search" placeholder="搜索姓名、工号或岗位" aria-label="搜索部门成员" allow-clear @change="page = 1" /></div>
          <a-table :columns="columns" :data-source="members" row-key="id" table-layout="fixed" :scroll="{ x: 520 }" :pagination="{ current: page, pageSize: 10, total: members.length, showSizeChanger: false, onChange: (value: number) => page = value }"><template #bodyCell="{ column, record }"><template v-if="column.key === 'name'"><button v-if="canIam('iam.people.read')" class="iam-name" :aria-label="`查看${record.name}的应用角色，工号${record.employee_number}`" @click="employeeId = record.id; drawerOpen = true"><strong>{{ record.name }}</strong></button><strong v-else>{{ record.name }}</strong><span class="iam-code">{{ record.employee_number }}</span></template><template v-else-if="column.key === 'status'"><StatusTag :tone="record.account_status === 'active' ? 'success' : 'neutral'">{{ record.account_status === 'active' ? '已开通' : record.account_status === 'disabled' ? '已停用' : '未开通' }}</StatusTag></template><template v-else-if="column.key === 'action'"><a-button v-if="canIam('iam.people.read')" type="link" @click="employeeId = record.id; drawerOpen = true">查看应用角色</a-button><span v-else class="aux">仅成员状态</span></template></template></a-table><p class="aux">此处仅列主部门成员；兼岗不会自动叠加所属部门权限。个人单独安排与限制逐人核对。</p>
        </div>
        <a-empty v-if="!current" description="暂无可管理部门" />
        <template #footer>
          <div v-if="activeTab === 'apps' && iamSession.rolesEnabled && current?.confirmed && !editingApp" class="r6-dept-role-actions">
            <span>{{ departmentDirty ? '有未保存的修改' : departmentMustRead ? '请先读取最新部门安排' : '与当前部门默认一致' }}</span>
            <div>
              <a-button v-if="canManageDepartmentRole" :disabled="departmentBusy" @click="cancelDepartmentEdit">取消修改</a-button>
              <a-button v-if="canManageDepartmentRole" type="primary" :disabled="!departmentDirty || departmentMustRead || departmentBusy || baselineLoading || !departmentCurrent || Boolean(departmentPreview)" :loading="departmentBusy" @click="prepareDepartmentRole">核对部门变化</a-button>
              <span v-else class="aux">只读</span>
            </div>
          </div>
          <span v-else class="aux">保存前会核对跟随者、单独安排与已有限制；个人暂停与禁止不会因部门默认解除。</span>
        </template>
      </PanelFrame>
    </div>
    <EmployeeDrawer :open="drawerOpen" :employee-id="employeeId" initial-tab="apps" :initial-app="'attendance'" @close="drawerOpen = false" @changed="load" />
    <ChangeReview :open="Boolean(departmentPreview)" :busy="departmentBusy" title="核对部门默认安排" @cancel="closeDepartmentPreview">
      <section v-if="departmentPreview" class="role-preview" aria-live="polite">
        <div class="role-preview-subject"><strong>{{ current?.name }}</strong><span>部门默认 · 仅影响选择跟随部门安排的员工</span></div>
        <div class="r6-assignment-compare"><div><small>当前安排</small><strong>{{ currentDepartmentText }}</strong><p>当前已保存的部门默认</p></div><div><small>本次安排</small><strong>{{ nextDepartmentText }}</strong><p>个人安排和已有限制保留</p></div></div>
        <div class="role-department-impact"><div><strong>{{ countText(departmentPreview.reference_count) }}</strong><span>跟随默认</span></div><div><strong>{{ countText(departmentPreview.effective_changed_count) }}</strong><span>实际权限变化</span></div><div><strong>{{ countText(departmentPreview.personal_preserved) }}</strong><span>个人安排保留</span></div></div>
        <p>跟随默认 {{ countText(departmentPreview.reference_count) }} 人；实际权限变化 {{ countText(departmentPreview.effective_changed_count) }} 人；个人安排保留 {{ countText(departmentPreview.personal_preserved) }} 人。</p>
        <p v-if="!candidateMembers.length" class="role-scope-caption">核对结果未返回跟随者名单。</p>
        <ul v-else class="role-member-list"><li v-for="member in candidateMembers" :key="member.employee"><strong>{{ member.name }}</strong><span>{{ member.changed ? '实际权限将变化' : '实际权限保持' }} {{ member.reason }}</span></li></ul>
        <OwnAccountVerification password-only @verified="departmentProof.sync" @invalidated="departmentProof.invalidate" />
        <div class="role-modal-actions"><a-button :disabled="departmentBusy" @click="closeDepartmentPreview">返回修改</a-button><a-button type="primary" :disabled="!canSubmitDepartment" :loading="departmentBusy" @click="commitDepartmentRole">确认保存</a-button></div>
      </section>
    </ChangeReview>
  </section>
</template>

<style scoped>
.r6-dept-lead{margin:0 0 16px;color:var(--r6-secondary,#566780);font-size:13px;line-height:21px}.department-default-options{display:grid;gap:10px;width:100%;margin-bottom:18px}.department-default-options :deep(.ant-radio-wrapper){display:flex;align-items:flex-start;margin:0;padding:15px 16px;border:1px solid #e5e9f2;border-radius:11px;min-height:76px;white-space:normal}.department-default-options :deep(.ant-radio-wrapper-checked){border-color:#bab5ea;background:#f7f6ff}.department-default-options :deep(.ant-radio-wrapper-disabled){background:#f8f9fc;border-color:#e5e9f2}.department-default-options :deep(.ant-radio){margin-top:4px;flex:none}.department-default-options strong,.department-default-options small{display:block}.department-default-options strong{font-size:14px}.department-default-options small{margin-top:4px;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}.department-default-options .r6-status-tag{margin-left:8px}.r6-dept-readonly{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:14px 16px;border:1px solid #e5e9f2;border-radius:10px;background:#f8f9fc}.r6-dept-readonly p{margin:0;color:var(--r6-muted,#5f6e86);font-size:12px;flex-basis:100%}.r6-dept-counts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:18px 0}.r6-dept-counts>div{padding:16px 18px;border:1px solid #e5e9f2;border-radius:12px;background:#f8f9fc}.r6-dept-counts strong{display:block;font-size:26px;line-height:34px}.r6-dept-counts span{display:block;margin-top:4px;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:19px}.r6-dept-follow-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:16px 0 6px}.r6-dept-follow-head h4{margin:0;font-size:14px}.r6-dept-followers{list-style:none;margin:0;padding:0;display:grid;gap:8px}.r6-dept-followers li{display:flex;justify-content:space-between;gap:12px;padding:11px 13px;border:1px solid #e5e9f2;border-radius:9px;font-size:13px}.r6-dept-followers span{color:var(--r6-muted,#5f6e86);font-size:12px}.r6-dept-note{margin:10px 0 0;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px}.r6-dept-baseline-error{display:grid;gap:10px;justify-items:start;margin-top:12px}.r6-dept-baseline-actions{display:flex;gap:8px;flex-wrap:wrap}.r6-dept-restrictions{margin-top:14px;border-top:1px solid #e5e9f2;padding-top:10px}.r6-dept-restrictions summary{cursor:pointer;font-size:12px;color:var(--r6-muted,#5f6e86);min-height:34px;display:flex;align-items:center}.r6-dept-restrictions p{margin:5px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}.r6-dept-role-actions{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.r6-dept-role-actions>span{color:var(--r6-muted,#5f6e86);font-size:12px}.r6-dept-role-actions>div{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.r6-dept-other-apps{margin-top:22px;border-top:1px solid #e5e9f2;padding-top:6px}.r6-dept-other-apps .field-section-title{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:16px 0 6px}.r6-dept-other-apps .field-section-title h3{margin:0;font-size:15px}.r6-dept-other-apps .field-section-title span{color:var(--r6-muted,#5f6e86);font-size:12px}.r6-dept-other-apps .r6-department-app:last-child{border-bottom:0}.r6-department-app>div{min-width:0}.r6-department-app strong{font-size:14px}.r6-department-app p{margin:5px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}.r6-department-app .ant-btn{flex:none}.role-preview{display:grid;gap:14px}.role-preview-subject{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline}.role-preview-subject strong{font-size:16px}.role-preview-subject span{color:var(--r6-muted,#5f6e86);font-size:12px}.role-department-impact{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.role-department-impact>div{padding:12px;border:1px solid #e5e9f2;border-radius:10px;background:#f8f9fc}.role-department-impact strong{display:block;font-size:22px;line-height:30px}.role-department-impact span{display:block;margin-top:4px;color:var(--r6-muted,#5f6e86);font-size:11px;line-height:18px}.role-member-list{list-style:none;margin:0;padding:0;display:grid;gap:8px}.role-member-list li{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;padding:10px 12px;border:1px solid #e5e9f2;border-radius:8px;font-size:12px}.role-member-list span{color:var(--r6-secondary,#566780)}.role-scope-caption{margin:0;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px}.role-modal-actions{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;padding-top:14px;border-top:1px solid #e5e9f2}@media(max-width:760px){.r6-dept-counts,.role-department-impact{grid-template-columns:1fr}.r6-dept-follow-head{align-items:flex-start}.r6-dept-followers li{flex-wrap:wrap}.r6-dept-role-actions{align-items:flex-start}.r6-dept-role-actions>div{width:100%;justify-content:flex-end}}
</style>
