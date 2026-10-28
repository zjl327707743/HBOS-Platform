<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { onBeforeRouteLeave } from 'vue-router'
import { getPerson, getEmployeeMetadata, previewLink, linkUser, createUser, transferEmployee, previewTransferEmployee, type TransferPreview, disableUser, resetTemporaryPassword } from '@/services/iamPeople'
import { getWorkSubject, getWorkSummary } from '@/services/iamWork'
import { canIam, iamMessage, iamSession } from '@/services/iamAccess'
import type { EmployeeDetail, EmployeeMetadata, OwnershipEvidence, WorkSummary } from '@/types/iam'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { useAccountProof } from '@/composables/useAccountProof'
import { cycleDialogTab } from '@/services/dialogKeyboard'
import AppUsageList from './AppUsageList.vue'
import NativeAppRolePanel from './NativeAppRolePanel.vue'
import WorkSettings from './WorkSettings.vue'
import RoleSettings from './RoleSettings.vue'
import ChangeReview from './ChangeReview.vue'
import StatusTag from './StatusTag.vue'
import AppAccessAction from './AppAccessAction.vue'

const props = withDefaults(defineProps<{ open: boolean; employeeId: string; initialTab?: string; initialApp?: string | null }>(), { initialTab: 'basic', initialApp: null })
const emit = defineEmits<{ close: []; changed: [] }>()
const person = ref<EmployeeDetail | null>(null), metadata = ref<EmployeeMetadata | null>(null)
const tab = ref<'basic' | 'account' | 'apps'>('basic'), editingApp = ref<string | null>(null)
const loading = ref(true), busy = ref(false), error = ref(''), secret = ref(''), mustRead = ref(false)
const roleSettings = ref<InstanceType<typeof RoleSettings> | null>(null), settings = ref<InstanceType<typeof WorkSettings> | null>(null)
const nativeRoles = ref<InstanceType<typeof NativeAppRolePanel> | null>(null), legacyApps = ref<InstanceType<typeof AppUsageList> | null>(null)
const transferPreview = ref<TransferPreview | null>(null), action = ref(''), assistOpen = ref(false)
const targetUser = ref(''), department = ref(''), evidence = ref('')
const accountMode = ref<'create' | 'link'>('create'), belongs = ref(false), accountReview = ref(false), accountDone = ref(false)
const roleDirty = ref(false), lowToolsOpen = ref(false), appsVisited = ref(false)
const work = ref<WorkSummary | null>(null), workLoading = ref(false), workError = ref('')
const proof = useAccountProof(() => { secret.value = '' })
let generation = 0, workGeneration = 0, accountRequestId = '', accountPreviewVersion = '', assistRequestId = '', assistRequestAction = ''
let returnFocus: HTMLElement | null = null
const drawerBody = ref<HTMLElement | null>(null)
let focusRoot: HTMLElement | null = null
function onDrawerTab(event: KeyboardEvent) { if (focusRoot && props.open) cycleDialogTab(event, focusRoot) }
function releaseFocusCycle() { focusRoot?.removeEventListener('keydown', onDrawerTab, true); focusRoot = null }
watch(() => props.open, open => { if (open && document.activeElement instanceof HTMLElement) returnFocus = document.activeElement }, { flush: 'sync' })
function afterOpenChange(open: boolean) {
  releaseFocusCycle()
  if (open && props.open) { focusRoot = drawerBody.value?.closest<HTMLElement>('.iam-employee-drawer') || null; focusRoot?.addEventListener('keydown', onDrawerTab, true) }
  if (!open && !props.open && returnFocus?.isConnected) { returnFocus.focus({ preventScroll: true }); returnFocus = null }
}
const employee = computed(() => person.value?.employee)
const capabilities = computed(() => ({ link: canIam('iam.people.link'), provision: canIam('iam.people.provision'), transfer: canIam('iam.people.transfer'), disable: canIam('iam.people.disable'), reset: canIam('iam.people.reset') }))
const canReadAccess = computed(() => canIam('iam.access.read'))
const canProvisionAccount = computed(() => capabilities.value.provision)
const canLinkAccount = computed(() => capabilities.value.link)
function hasField(object: Record<string, unknown> | undefined, key: string) { return Boolean(object && Object.prototype.hasOwnProperty.call(object, key) && object[key] !== undefined) }
const accountUserIdText = computed(() => {
  const id = person.value?.account?.user_id
  if (typeof id === 'string' && id) return id
  if (employee.value?.user_id) return '账号标识待核对'
  return '尚未开通'
})
const accountUsernameText = computed(() => hasField(person.value?.account as Record<string, unknown> | undefined, 'username') ? (person.value?.account.username || '未设置') : '待核对')
const feishuBoundText = computed(() => typeof person.value?.account?.feishu_bound === 'boolean' ? (person.value.account.feishu_bound ? '已绑定' : '未绑定') : '待核对')
const initialPasswordText = computed(() => typeof person.value?.account?.initial_password_pending === 'boolean' ? (person.value.account.initial_password_pending ? '等待本人设置' : '无待设置标记') : '待核对')
const associationText = computed(() => typeof person.value?.association?.user_id === 'string' && person.value.association.user_id ? '已关联当前员工' : '关联待核对')
const linkedUserText = computed(() => typeof person.value?.association?.user_id === 'string' ? (person.value.association.user_id || '尚未关联') : '待核对')
const linkedUserPrimary = computed(() => {
  const candidates = [person.value?.association?.user_id, person.value?.account?.user_id, employee.value?.user_id]
  return candidates.find(value => typeof value === 'string' && value) || '尚未关联'
})
const associationNeedsReview = computed(() => Boolean(employee.value && !person.value?.configuration_only && employee.value.account_status !== 'unopened' && employee.value.attendance_status !== 'confirmed'))
const associationStatusText = computed(() => employee.value?.attendance_status === 'confirmed' ? '考勤关联已确认' : employee.value?.account_status === 'unopened' ? '待开通登录账号' : person.value?.configuration_only ? '关联状态不可核对' : '关联异常，人工核查')
const associationStatusTone = computed(() => employee.value?.attendance_status === 'confirmed' ? 'success' : employee.value?.account_status === 'unopened' || person.value?.configuration_only ? 'neutral' : 'warning')
const accountValid = computed(() => {
  const modeAllowed = accountMode.value === 'create' ? canProvisionAccount.value : canLinkAccount.value
  return Boolean(employee.value) && !employee.value?.user_id && modeAllowed && belongs.value && evidence.value.trim().length >= 12 && (accountMode.value === 'create' || targetUser.value.trim().length > 0)
})
const canConfirmAccount = computed(() => accountValid.value && proof.valid.value && proof.method.value === 'password' && !busy.value && !mustRead.value)
const otherApps = computed(() => (work.value?.apps || []).filter(app => app.app_id !== 'attendance'))
const attendanceApp = computed(() => (work.value?.apps || []).find(app => app.app_id === 'attendance' && app.integrated) || null)
const showAttendanceOps = computed(() => Boolean(iamSession.rolesEnabled && canIam('iam.access.manage') && work.value?.subject_type === 'User' && attendanceApp.value))
const assistTitle = computed(() => ({ transfer: '调整主部门', disable: '停用此员工账号', reset: '重置临时密码' } as Record<string, string>)[action.value] || '账号协助')
const canExecuteAssist = computed(() => proof.valid.value && proof.method.value === 'password' && !busy.value && !mustRead.value && (action.value !== 'transfer' || (Boolean(department.value) && Boolean(transferPreview.value))))
const accountStatusText = computed(() => employee.value?.account_status === 'disabled' ? '登录账号已停用' : employee.value?.user_id || person.value?.account?.user_id ? '登录账号已开通' : '登录账号尚未开通')

function normalizeTab(value: string): 'basic' | 'account' | 'apps' {
  if ((value === 'apps' || value === 'app') && canReadAccess.value) return 'apps'
  if (value === 'account') return person.value?.configuration_only ? 'basic' : 'account'
  return 'basic'
}
function evidenceOwnership(): OwnershipEvidence {
  return {
    employee_number: employee.value!.employee_number,
    company: employee.value!.company,
    account_user_id: accountMode.value === 'create' ? person.value!.account.proposed_user_id || '' : targetUser.value.trim(),
    reference: evidence.value.trim(),
  }
}
async function loadWork() {
  if (!canReadAccess.value || !employee.value) { work.value = null; return }
  const run = ++workGeneration
  workLoading.value = true; workError.value = ''
  try {
    const data = await getWorkSummary(props.employeeId)
    if (run === workGeneration) work.value = data
  } catch (e) {
    if (run === workGeneration) { work.value = null; workError.value = iamMessage(e) }
  } finally {
    if (run === workGeneration) workLoading.value = false
  }
}
async function load() {
  const run = ++generation
  loading.value = true; error.value = ''
  try {
    const detail: EmployeeDetail = canIam('iam.people.read')
      ? await getPerson(props.employeeId)
      : await getWorkSubject(props.employeeId, props.initialApp || 'attendance').then(data => ({ employee: data.employee, account: { user_id: data.account.user_id }, association: { employee_id: data.employee.id, user_id: data.account.user_id }, history: [], configuration_only: true }))
    if (run !== generation) return
    person.value = detail
    mustRead.value = false
    if (detail.configuration_only && tab.value === 'account') tab.value = 'basic'
    if (!detail.employee.user_id) {
      editingApp.value = null
      if (!canProvisionAccount.value && canLinkAccount.value) accountMode.value = 'link'
      else if (canProvisionAccount.value && !canLinkAccount.value) accountMode.value = 'create'
    }
    if (canReadAccess.value) void loadWork()
  } catch (e) {
    if (run === generation) { person.value = null; error.value = iamMessage(e) }
  } finally {
    if (run === generation) loading.value = false
  }
}
async function readLatest() {
  transferPreview.value = null
  accountPreviewVersion = ''
  proof.invalidate()
  await load()
}
function nativeRoleBusy() { return nativeRoles.value?.busy === true }
function beginAccount(mode: 'create' | 'link') {
  if (mode === 'create' && !canProvisionAccount.value) return
  if (mode === 'link' && !canLinkAccount.value) return
  accountMode.value = mode
  accountReview.value = false
  proof.invalidate()
  error.value = ''
}
function openAccountReview() {
  if (mustRead.value) { message.info('请先读取最新资料并核对上次操作结果。'); return }
  if (nativeRoleBusy()) { message.info('原生角色正在保存，请等待完成后再处理账号。'); return }
  if ((accountMode.value === 'create' && !canProvisionAccount.value) || (accountMode.value === 'link' && !canLinkAccount.value)) { error.value = '当前账号没有这项账号处理权限。'; return }
  if (!accountValid.value) {
    error.value = accountMode.value === 'link'
      ? '请填写已有账号主键、至少12字的明确归属依据，并勾选已核对归属；不能按姓名自动认领。'
      : '请填写至少12字的明确归属依据，并勾选已核对归属。'
    return
  }
  error.value = ''; proof.invalidate(); accountReview.value = true
}
async function runAccount() {
  if (!employee.value || busy.value || mustRead.value || nativeRoleBusy() || !canConfirmAccount.value || (accountMode.value === 'create' && !canProvisionAccount.value) || (accountMode.value === 'link' && !canLinkAccount.value)) return
  if (evidence.value.trim().length < 12) { error.value = '请填写至少12个字的明确归属核验依据；姓名相同不能作为归属证明。'; return }
  if (accountMode.value === 'link' && !targetUser.value.trim()) { error.value = '请输入已有账号的原始 User 主键。'; return }
  busy.value = true; error.value = ''
  try {
    let expectedVersion = employee.value.version
    if (accountMode.value === 'link') {
      if (!accountPreviewVersion) accountPreviewVersion = (await previewLink(employee.value.id, targetUser.value.trim(), evidenceOwnership())).version
      expectedVersion = accountPreviewVersion
    }
    accountRequestId ||= crypto.randomUUID()
    const result = accountMode.value === 'create'
      ? await createUser(employee.value.id, evidenceOwnership(), employee.value.version, accountRequestId)
      : await linkUser(employee.value.id, targetUser.value.trim(), evidenceOwnership(), expectedVersion, accountRequestId)
    proof.invalidate()
    secret.value = result.temporary_password || ''
    accountDone.value = true
    accountReview.value = false
    accountRequestId = ''; accountPreviewVersion = ''
    evidence.value = ''; targetUser.value = ''; belongs.value = false; accountMode.value = 'create'
    await load()
    message.success('员工账号操作已完成。')
    emit('changed')
  } catch (e) {
    error.value = iamMessage(e)
    mustRead.value = true
    proof.invalidate()
    accountReview.value = false
  } finally {
    busy.value = false
  }
}
async function openAssist(kind: string) {
  if (mustRead.value) { message.info('请先读取最新资料并核对上次操作结果。'); return }
  if (nativeRoleBusy()) { message.info('原生角色正在保存，请等待完成后再执行账号操作。'); return }
  if (assistRequestAction !== kind) { assistRequestId = ''; assistRequestAction = kind }
  action.value = kind; assistOpen.value = true; transferPreview.value = null; department.value = ''; error.value = ''; proof.invalidate()
  if (kind === 'transfer') {
    try { metadata.value = await getEmployeeMetadata(employee.value?.verification_group === 'technical' ? 'technical' : 'daily') }
    catch (e) { error.value = iamMessage(e) }
  }
}
function closeAssist() { assistOpen.value = false; action.value = ''; transferPreview.value = null; proof.invalidate() }
async function readTransfer() {
  if (!employee.value || !department.value || busy.value) return
  busy.value = true; error.value = ''
  try { transferPreview.value = await previewTransferEmployee(employee.value.id, department.value, employee.value.version) }
  catch (e) { error.value = iamMessage(e); transferPreview.value = null }
  finally { busy.value = false }
}
watch(department, () => { transferPreview.value = null })
watch([accountMode, targetUser, evidence, belongs], () => { accountRequestId = ''; accountPreviewVersion = '' })
async function executeAssist() {
  if (!employee.value || busy.value || mustRead.value || nativeRoleBusy() || !canExecuteAssist.value) return
  if (action.value === 'transfer' && (!department.value || !transferPreview.value)) { error.value = '请选择现有目标部门并核对调岗影响。'; return }
  busy.value = true; error.value = ''
  try {
    assistRequestId ||= crypto.randomUUID()
    const row = employee.value
    const result = action.value === 'transfer'
      ? await transferEmployee(row.id, department.value, row.version, assistRequestId, transferPreview.value!.context_revision)
      : action.value === 'disable' ? await disableUser(row.id, row.version, assistRequestId) : await resetTemporaryPassword(row.id, row.version, assistRequestId)
    proof.invalidate(); secret.value = result.temporary_password || ''
    assistOpen.value = false; action.value = ''; assistRequestId = ''; assistRequestAction = ''
    await load()
    message.success('员工账号操作已完成。')
    emit('changed')
  } catch (e) {
    error.value = iamMessage(e)
    mustRead.value = true
    proof.invalidate()
    assistOpen.value = false
    transferPreview.value = null
  } finally {
    busy.value = false
  }
}
async function openLowApp(appId: string) {
  if (nativeRoles.value?.busy) { message.info('原生角色正在保存，请等待完成后再切换设置。'); return }
  if (nativeRoles.value && !await nativeRoles.value.requestLeave()) return
  editingApp.value = appId
}
async function onRoleSaved() { roleDirty.value = false; await loadWork(); emit('changed') }
function onRoleDirty(value: boolean) { roleDirty.value = value }
async function close() {
  if (busy.value || (roleSettings.value && !await roleSettings.value.requestLeave()) || (settings.value && !await settings.value.requestLeave()) || (nativeRoles.value && !await nativeRoles.value.requestLeave())) return false
  if (accountReview.value || (!employee.value?.user_id && (belongs.value || evidence.value || targetUser.value))) {
    const leave = await new Promise<boolean>(resolve => Modal.confirm({ title: '放弃尚未提交的账号核对？', content: '员工档案与其他应用安排不受影响。', okText: '放弃', cancelText: '继续填写', onOk: () => resolve(true), onCancel: () => resolve(false) }))
    if (!leave) return false
  }
  if (assistOpen.value && action.value === 'transfer' && department.value) {
    const leave = await new Promise<boolean>(resolve => Modal.confirm({ title: '放弃尚未提交的调岗核对？', content: '员工部门尚未改变。', okText: '放弃', cancelText: '继续核对', onOk: () => resolve(true), onCancel: () => resolve(false) }))
    if (!leave) return false
  }
  secret.value = ''; proof.invalidate(); emit('close'); return true
}
watch(tab, value => { if (value === 'apps') appsVisited.value = true })
watch(() => [props.open, props.employeeId], () => {
  generation++; workGeneration++; person.value = null; secret.value = ''; action.value = ''; assistOpen.value = false; error.value = ''
  accountReview.value = false; accountDone.value = false; belongs.value = false; evidence.value = ''; targetUser.value = ''; accountMode.value = 'create'; accountRequestId = ''; accountPreviewVersion = ''; assistRequestId = ''; assistRequestAction = ''
  transferPreview.value = null; department.value = ''; metadata.value = null; roleDirty.value = false; work.value = null; workError.value = ''; mustRead.value = false; appsVisited.value = false
  proof.invalidate()
  if (props.open && props.employeeId) {
    tab.value = normalizeTab(props.initialApp ? 'apps' : props.initialTab)
    editingApp.value = tab.value === 'apps' && props.initialApp && (!iamSession.rolesEnabled || props.initialApp !== 'attendance') ? props.initialApp : null
    appsVisited.value = tab.value === 'apps'
    lowToolsOpen.value = false
    void load()
  }
}, { immediate: true })
onBeforeRouteLeave(() => props.open ? close() : true)
onBeforeUnmount(() => { generation++; workGeneration++; secret.value = ''; proof.invalidate(); releaseFocusCycle() })
</script>

<template>
  <a-drawer root-class-name="iam-employee-drawer" :open="open" :width="780" :closable="false" :mask-closable="false" :keyboard="true" :body-style="{ padding: '24px 28px 28px' }" @close="close" @after-open-change="afterOpenChange">
    <template #title>
      <div class="drawer-top">
        <div class="drawer-identity-block">
          <span class="drawer-eyebrow">员工详情</span>
          <div class="drawer-identity">
            <a-avatar :size="44" class="drawer-avatar">{{ (employee?.name || '员').slice(-1) }}</a-avatar>
            <div>
              <h2 id="employee-detail-title">{{ employee?.name || '员工资料' }}</h2>
              <p>{{ employee?.employee_number || '工号待核对' }} <span>·</span> {{ employee?.department_name || employee?.department || '部门待核对' }} <span>·</span> {{ employee?.company || '公司待核对' }}</p>
            </div>
          </div>
        </div>
        <a-button type="text" class="drawer-close" aria-label="关闭员工详情" @click="close">关闭</a-button>
      </div>
      <a-tabs :active-key="tab" class="drawer-tabs" @change="(value: string) => tab = normalizeTab(value)">
        <a-tab-pane key="basic" tab="员工资料" />
        <a-tab-pane v-if="person && !person.configuration_only" key="account" tab="登录账号" />
        <a-tab-pane v-if="person && canReadAccess" key="apps" tab="应用角色" />
      </a-tabs>
    </template>
    <div ref="drawerBody" class="employee-drawer">
      <a-alert v-if="error" :message="error" type="warning" show-icon />
      <a-button v-if="error && person" :disabled="busy" @click="readLatest">读取最新资料，保留选择</a-button>
      <a-skeleton v-if="loading" active />
      <section v-if="secret" class="secret"><strong>本次临时密码，仅当次显示</strong><a-input-password :value="secret" readonly autocomplete="off" /><p>请私下交付已核验本人；关闭抽屉后不能重新读取。</p><a-button @click="secret = ''">已交付，隐藏</a-button></section>
      <template v-else-if="person && employee">
        <template v-if="tab === 'basic'">
          <div class="drawer-section-heading"><h3>基本资料</h3><StatusTag :tone="associationStatusTone">{{ associationStatusText }}</StatusTag></div>
          <a-alert v-if="associationNeedsReview" class="r6-association-review" type="warning" show-icon message="关联异常，需人工核查" :description="`Employee 主键：${employee.id}；User 主键：${linkedUserPrimary}。本页没有安全确认命令，不能在此完成账号关联确认；请管理员按上述真实主键人工核查。系统不会按姓名自动匹配，也不会调用关联接口。`" />
          <a-descriptions :column="1" bordered size="middle">
            <a-descriptions-item label="姓名">{{ employee.name }}</a-descriptions-item>
            <a-descriptions-item label="工号">{{ employee.employee_number || '待核对' }}</a-descriptions-item>
            <a-descriptions-item label="所属公司">{{ employee.company }}</a-descriptions-item>
            <a-descriptions-item label="所属部门">{{ employee.department_name || employee.department || '待核对' }}</a-descriptions-item>
            <a-descriptions-item label="岗位">{{ employee.position || '待补充' }}</a-descriptions-item>
          </a-descriptions>
          <div class="drawer-section-heading spaced"><h3>关联与下一步</h3></div>
          <div v-if="!person.configuration_only" class="detail-link-card">
            <div><strong>{{ accountStatusText }}</strong><p>{{ employee.user_id ? `登录账号：${employee.user_id}` : '已有员工档案，无需重复新增；核对归属后再开通或关联。' }}</p></div>
            <a-button @click="tab = 'account'">查看账号</a-button>
          </div>
          <div class="detail-link-card">
            <div><strong>考勤管理</strong><p>安排这位同事的考勤角色、来源与负责范围；不影响其他应用。</p></div>
            <a-button v-if="canReadAccess" @click="tab = 'apps'">设置角色</a-button>
            <a-button v-else disabled>无读取权限</a-button>
          </div>
          <div v-if="capabilities.transfer && !person.configuration_only" class="drawer-inline-tools">
            <a-button @click="openAssist('transfer')">调整主部门</a-button>
            <span>调岗前会读取真实影响预览，单独安排与个人限制保留。</span>
          </div>
          <details v-if="!person.configuration_only" class="drawer-details">
            <summary>关联详情</summary>
            <a-descriptions :column="1">
              <a-descriptions-item label="Employee 主键">{{ employee.id }}</a-descriptions-item>
              <a-descriptions-item label="原始工号">{{ employee.employee_number }}</a-descriptions-item>
              <a-descriptions-item label="User 主键">{{ linkedUserText }}</a-descriptions-item>
              <a-descriptions-item label="登录别名">{{ accountUsernameText }}</a-descriptions-item>
              <a-descriptions-item label="飞书">{{ feishuBoundText }}</a-descriptions-item>
              <a-descriptions-item label="考勤身份核验">{{ employee.attendance_status === 'confirmed' ? '明确关联已确认' : employee.account_status === 'unopened' ? '尚未开通，暂不判断关联' : '已有关联但未确认，需人工核查' }}</a-descriptions-item>
            </a-descriptions>
          </details>
          <details class="drawer-details">
            <summary>变更记录</summary>
            <a-empty v-if="!person.history.length" description="暂无可见的脱敏变更记录" />
            <p v-for="(event, index) in person.history" :key="index">{{ event.occurred_at }} · {{ event.operation }} · {{ event.reason }}</p>
          </details>
        </template>

        <template v-else-if="tab === 'account' && !person.configuration_only">
          <template v-if="!employee.user_id">
            <div class="inline-notice"><div><strong>已有员工档案，无需重复新增</strong><p>核对这位同事的账号归属，再选择开通或关联；不会按姓名自动认领。</p></div></div>
            <template v-if="canProvisionAccount || canLinkAccount">
              <a-steps class="account-steps" size="small" :current="accountDone ? 2 : accountReview ? 1 : 0" :items="[{ title: '核对与选择' }, { title: '确认开通' }, { title: '完成' }]" />
              <h3 class="field-section-title"><span>如何处理登录账号</span></h3>
              <a-radio-group :value="accountMode" class="account-choice" aria-label="登录账号处理方式" @change="(event: { target: { value: 'create' | 'link' } }) => beginAccount(event.target.value)">
                <a-radio v-if="canProvisionAccount" value="create"><span><strong>开通新的登录账号</strong><small>确认这位同事尚无可用账号；完成后只保留这一份员工档案。</small></span></a-radio>
                <a-radio v-if="canLinkAccount" value="link"><span><strong>关联已有的登录账号</strong><small>已有账号时保留原账号与历史记录，按准确账号标识关联。</small></span></a-radio>
              </a-radio-group>
              <a-form layout="vertical" class="account-form" @submit.prevent="openAccountReview">
                <a-form-item v-if="accountMode === 'link'" label="已有账号标识（User 主键）" required>
                  <a-input v-model:value="targetUser" :disabled="busy || mustRead" autocomplete="off" placeholder="请输入已核对的已有账号 User 主键" />
                  <span class="field-help">按准确标识关联，不按姓名自动匹配。</span>
                </a-form-item>
                <a-form-item label="归属核对依据" required>
                  <a-textarea v-model:value="evidence" :disabled="busy || mustRead" :maxlength="500" :rows="3" placeholder="例如：已核对工号、所属公司与目标账号的归属记录编号" />
                  <span class="field-help">至少12个字；不要填写口令、验证码或临时密码。</span>
                </a-form-item>
              </a-form>
              <a-checkbox :checked="belongs" :disabled="busy || mustRead" @change="(event: { target: { checked: boolean } }) => belongs = event.target.checked">已核对 {{ employee.employee_number || '该员工' }} 的工号、公司与账号归属</a-checkbox>
              <div class="account-form-actions">
                <a-button type="primary" :disabled="!accountValid || busy || mustRead" @click="openAccountReview">{{ accountMode === 'create' ? '核对并开通' : '核对并关联' }}</a-button>
              </div>
            </template>
            <a-alert v-else type="info" show-icon message="当前账号可以查看员工账号状态，但没有开户或关联权限。" description="如需处理登录账号，请联系有相应管理范围的负责人。" />
          </template>
          <template v-else>
            <div class="account-status-card">
              <div><h3>{{ accountStatusText }}</h3><p>{{ accountUserIdText }}</p></div>
              <StatusTag :tone="employee.account_status === 'active' ? 'success' : 'neutral'">{{ employee.account_status === 'active' ? '可登录' : employee.account_status === 'disabled' ? '已停用' : '状态待核对' }}</StatusTag>
            </div>
            <a-alert v-if="accountDone" show-icon type="success" message="账号处理完成，员工档案没有重复创建。" />
            <div class="drawer-section-heading spaced"><h3>账号与关联</h3></div>
            <a-descriptions :column="1" bordered size="middle">
              <a-descriptions-item label="登录账号">{{ accountUserIdText }}</a-descriptions-item>
              <a-descriptions-item label="登录名">{{ accountUsernameText }}</a-descriptions-item>
              <a-descriptions-item label="飞书登录">{{ feishuBoundText }}</a-descriptions-item>
              <a-descriptions-item label="首次密码">{{ initialPasswordText }}</a-descriptions-item>
              <a-descriptions-item label="关联状态">{{ associationText }}</a-descriptions-item>
            </a-descriptions>
            <div class="drawer-next-step"><h3>下一步：安排应用角色</h3><p>账号可用后，再确认这位同事的考勤角色与负责范围。</p><a-button type="primary" :disabled="employee.account_status !== 'active' || !canReadAccess" @click="tab = 'apps'">设置应用角色</a-button></div>
            <details class="drawer-details">
              <summary>更多账号协助</summary>
              <p>管理员协助操作单独验证本人密码；员工本人的登录与安全仍由本人在“个人中心”维护。</p>
              <div class="account-actions">
                <a-button v-if="capabilities.reset && employee.account_status !== 'disabled'" @click="openAssist('reset')">受控重置临时密码</a-button>
                <a-button v-if="capabilities.disable && employee.account_status !== 'disabled'" danger @click="openAssist('disable')">停用此员工账号</a-button>
              </div>
            </details>
          </template>
        </template>

        <div v-if="appsVisited && canReadAccess" v-show="tab === 'apps'" class="employee-apps-panel">
          <WorkSettings v-if="editingApp" ref="settings" subject-kind="employee" :subject-id="employeeId" :app-id="editingApp" @back="editingApp = null" @saved="loadWork(); emit('changed')" />
          <div v-show="!editingApp">
          <template v-if="iamSession.rolesEnabled">
            <a-alert v-if="employee.account_status !== 'active'" type="warning" show-icon message="登录账号尚未可用" description="应用角色可在此核对；账号可用前实际功能不会生效。" />
            <RoleSettings ref="roleSettings" embedded subject-kind="employee" :subject-id="employeeId" :subject-label="employee.name" @dirty="onRoleDirty" @saved="onRoleSaved" />
            <section v-if="showAttendanceOps && attendanceApp" class="r6-attendance-more">
              <div class="field-section-title"><h3>更多考勤操作</h3><span>低频 · 独立于角色保存</span></div>
              <article class="r6-other-app">
                <div>
                  <strong>{{ attendanceApp.title }}</strong><StatusTag :tone="attendanceApp.suspended ? 'warning' : 'neutral'">{{ attendanceApp.suspended ? '已临时禁用' : '可单独暂停' }}</StatusTag>
                  <p>临时暂停或恢复此员工的考勤访问；不改变角色和负责范围，也不会停用账号。</p>
                  <small class="app-note">只影响考勤应用，独立于上面的应用角色保存。</small>
                </div>
                <div class="r6-other-actions">
                  <AppAccessAction v-if="work && work.subject_type === 'User'" :app="attendanceApp" :target="{ subject_type: work.subject_type, subject_name: work.subject_name, app_id: attendanceApp.app_id }" @saved="loadWork" />
                </div>
              </article>
            </section>
            <section class="r6-other-apps">
              <div class="field-section-title"><h3>其他已接入应用</h3><span>不改变应用角色</span></div>
              <a-skeleton v-if="workLoading" active />
              <a-alert v-else-if="workError" :message="workError" type="warning" show-icon />
              <a-empty v-else-if="!otherApps.length" description="暂无其他已接入应用" />
              <article v-for="app in otherApps" :key="app.app_id" class="r6-other-app">
                <div><strong>{{ app.title }}</strong><StatusTag :tone="app.integrated ? 'brand' : 'neutral'">{{ app.integrated ? '已接入' : '尚未接入' }}</StatusTag><p>{{ app.integrated ? app.summary : '原有业务入口保持现有授权，暂不能在此调整。' }}</p><small v-if="app.synthetic" class="app-note">隔离合成规则验证，非库存业务接入</small><small v-if="app.source_text" class="app-note">{{ app.source_text }}</small></div>
                <div class="r6-other-actions">
                  <a-button v-if="app.integrated" @click="openLowApp(app.app_id)">设置安排</a-button>
                  <AppAccessAction v-if="app.integrated && work && work.subject_type === 'User' && canIam('iam.access.manage')" :app="app" :target="{ subject_type: work.subject_type, subject_name: work.subject_name, app_id: app.app_id }" @saved="loadWork" />
                </div>
              </article>
            </section>
            <details class="drawer-details low-tools" :open="lowToolsOpen" @toggle="(event: Event) => lowToolsOpen = (event.target as HTMLDetailsElement).open">
              <summary>原生角色与兼容入口</summary>
              <p>原生角色仍按原有权限核验，仅作为兼容入口；不应替代上面的考勤应用角色。</p>
              <NativeAppRolePanel v-if="employee.user_id && canIam('iam.access.manage')" ref="nativeRoles" :employee-id="employeeId" @saved="load" />
              <p v-else class="aux">员工账号可用后，可由有权限的管理员在此核对原生角色。</p>
            </details>
          </template>
          <template v-else>
            <a-alert type="info" show-icon message="应用角色功能尚未启用" description="以下保留原有应用权限兼容入口。" />
            <AppUsageList ref="legacyApps" :employee-id="employeeId" :configuration-app-id="person.configuration_only ? initialApp || 'attendance' : undefined" :can-edit="Boolean(employee.user_id) && canIam('iam.access.manage')" @modify="openLowApp" />
            <NativeAppRolePanel v-if="employee.user_id && canIam('iam.access.manage')" ref="nativeRoles" :employee-id="employeeId" @saved="load" />
          </template>
          </div>
        </div>
      </template>
      <a-button v-if="!loading && !person" @click="load">重试读取</a-button>
    </div>
    <template #footer><div class="r6-drawer-footer"><span>{{ tab === 'apps' && iamSession.rolesEnabled && roleDirty ? '应用角色有未保存的修改' : `当前对象：${employee?.name || '读取中'} · ${employee?.employee_number || ''}` }}</span><a-button :disabled="busy" @click="close">关闭详情</a-button></div></template>
  </a-drawer>

  <ChangeReview :open="accountReview" :title="accountMode === 'link' ? '确认关联已有登录账号' : '确认开通登录账号'" :busy="busy" @cancel="accountReview = false; proof.invalidate()">
    <section v-if="person && employee" class="drawer-review">
      <a-descriptions :column="1" bordered size="small">
        <a-descriptions-item label="员工">{{ employee.name }} · {{ employee.employee_number }}</a-descriptions-item>
        <a-descriptions-item label="所属公司">{{ employee.company }}</a-descriptions-item>
        <a-descriptions-item label="处理方式">{{ accountMode === 'create' ? '开通新的登录账号' : '关联已有登录账号' }}</a-descriptions-item>
        <a-descriptions-item v-if="accountMode === 'link'" label="已有账号">{{ targetUser }}</a-descriptions-item>
        <a-descriptions-item label="归属核对依据">{{ evidence }}</a-descriptions-item>
      </a-descriptions>
      <a-alert class="spaced" show-icon type="info" message="保留这份员工档案，完成后可安排应用角色" description="保存时服务端会重新校验管理范围、归属、版本和本人密码验证。" />
      <OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" />
      <div class="role-modal-actions"><a-button :disabled="busy" @click="accountReview = false; proof.invalidate()">返回修改</a-button><a-button type="primary" :disabled="!canConfirmAccount" :loading="busy" @click="runAccount">{{ accountMode === 'link' ? '确认关联' : '确认开通' }}</a-button></div>
    </section>
  </ChangeReview>

  <ChangeReview :open="assistOpen" :title="assistTitle" :busy="busy" @cancel="closeAssist">
    <section v-if="employee" class="drawer-review">
      <a-alert v-if="error" :message="error" type="warning" show-icon />
      <template v-if="action === 'transfer'">
        <p class="review-lead">{{ employee.name }} 当前主部门：{{ employee.department_name || employee.department || '待核对' }}。调岗会重新计算部门默认权限。</p>
        <a-select v-model:value="department" :disabled="busy" :options="metadata?.departments" placeholder="选择现有目标部门" aria-label="目标主部门" style="width:100%" />
        <a-button class="spaced-small" :disabled="!department || busy" @click="readTransfer">核对调岗影响</a-button>
        <section v-if="transferPreview" class="transfer-preview" aria-live="polite">
          <h4>{{ transferPreview.from_department }} → {{ transferPreview.to_department }}</h4>
          <article v-for="(effect, index) in transferPreview.effects" :key="index"><strong>{{ effect.app }} · {{ effect.operation }}</strong><p>失去：{{ effect.lost.map(scope => scope.label || (scope.scope_type === 'SELF' ? '本人' : scope.scope_ref)).join('、') || '无' }}；新增：{{ effect.gained.map(scope => scope.label || (scope.scope_type === 'SELF' ? '本人' : scope.scope_ref)).join('、') || '无' }}</p><p v-if="!effect.after_allowed">调岗后不可用：{{ effect.reason }}</p></article>
          <p>为此员工单独设置的权限保留；重要权限不会随部门自动授予。工号、账号及历史考勤归属保留。</p>
          <p v-if="transferPreview.may_require_login">原生员工保存可能更新账号安全状态，员工可能需要重新登录。</p>
          <p v-if="transferPreview.unlinked">员工尚未开户，本次只调整部门，不授予账号访问。</p>
        </section>
      </template>
      <template v-else-if="action === 'disable'"><a-alert show-icon type="warning" message="仅停用此员工账号，并撤销相关会话" description="员工档案和历史业务记录保留；应用角色安排本身不会因此被删除。" /></template>
      <template v-else><a-alert show-icon type="warning" message="受控重置临时密码" description="新临时密码只在成功后当次显示；关闭抽屉后不能重新读取。" /></template>
      <OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" />
      <div class="role-modal-actions"><a-button :disabled="busy" @click="closeAssist">返回</a-button><a-button type="primary" danger :disabled="!canExecuteAssist" :loading="busy" @click="executeAssist">{{ action === 'transfer' ? '确认调岗' : action === 'disable' ? '确认停用' : '确认重置' }}</a-button></div>
    </section>
  </ChangeReview>
</template>

<style scoped>
.drawer-top{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.drawer-identity-block{min-width:0}.drawer-eyebrow{display:block;margin-bottom:4px;color:var(--r6-muted,#5f6e86);font-size:11px;letter-spacing:.5px}.drawer-identity{display:flex;align-items:center;gap:13px;min-width:0}.drawer-avatar{background:#eeedff;color:#5754df;font-size:16px;flex:none}.drawer-identity h2{margin:0;font-size:21px;line-height:30px;font-weight:600;overflow-wrap:anywhere}.drawer-identity p{margin:4px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px;overflow-wrap:anywhere}.drawer-identity p span{margin-inline:7px;color:#a5acc1}.drawer-close{flex:none;color:var(--r6-secondary,#566780)}.drawer-tabs{margin-top:4px}.employee-drawer{display:grid;gap:16px;font-size:14px;min-width:0}.drawer-section-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px}.drawer-section-heading h3{margin:0;font-size:16px}.drawer-section-heading.spaced{margin-top:24px}.detail-link-card{display:flex;align-items:center;gap:14px;padding:17px 0;border-bottom:1px solid #e5e9f2}.detail-link-card>div{flex:1;min-width:0}.detail-link-card strong{font-size:14px;font-weight:500}.detail-link-card p{margin:5px 0 0;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px;overflow-wrap:anywhere}.drawer-inline-tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:16px 0;border-bottom:1px solid #e5e9f2}.drawer-inline-tools span{color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px}.drawer-details{margin-top:4px;border-top:1px solid #e5e9f2;padding-top:12px}.drawer-details summary{cursor:pointer;font-weight:600;font-size:13px;min-height:36px;display:flex;align-items:center}.drawer-details p{color:var(--r6-secondary,#566780);font-size:12px;line-height:20px;overflow-wrap:anywhere}.inline-notice{display:flex;align-items:flex-start;gap:10px;padding:14px 16px;border:1px solid #dfe4f8;border-radius:10px;background:#f4f6ff;color:#525c88;font-size:13px;line-height:21px}.inline-notice strong{font-size:14px}.inline-notice p{margin:5px 0 0;font-size:12px;line-height:20px}.account-steps{margin:22px 0 8px}.field-section-title{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:16px 0 12px;font-size:16px}.account-choice{display:grid;gap:11px;width:100%;margin-bottom:18px}.account-choice :deep(.ant-radio-wrapper){display:flex;align-items:flex-start;margin:0;padding:15px 17px;border:1px solid #e5e9f2;border-radius:12px;min-height:76px;white-space:normal}.account-choice :deep(.ant-radio-wrapper-checked){border-color:#bab5ea;background:#f7f6ff}.account-choice :deep(.ant-radio){margin-top:4px;flex:none}.account-choice strong,.account-choice small{display:block}.account-choice strong{font-size:14px;font-weight:500}.account-choice small{margin-top:5px;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}.account-form{margin-top:6px}.account-form :deep(.ant-input),.account-form :deep(.ant-input-affix-wrapper),.account-form :deep(textarea){font-size:14px}.field-help{display:block;margin-top:5px;color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px}.account-form-actions{display:flex;justify-content:flex-end;margin-top:18px}.account-status-card{display:flex;align-items:center;gap:16px;padding:20px 22px;border:1px solid #e3ece6;border-radius:14px;background:#f7faf8}.account-status-card>div{flex:1;min-width:0}.account-status-card h3{margin:0;font-size:16px}.account-status-card p{margin:5px 0 0;color:var(--r6-secondary,#566780);font-size:13px;overflow-wrap:anywhere}.drawer-next-step{margin-top:24px;padding:22px;border:1px solid #e5e1f6;border-radius:14px;background:linear-gradient(120deg,#f7f5ff,#fbfcff)}.drawer-next-step h3{margin:0;font-size:16px}.drawer-next-step p{margin:8px 0 16px;color:var(--r6-secondary,#566780);font-size:13px;line-height:21px}.account-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}.secret{display:grid;gap:12px;margin-top:20px;padding:20px;border:1px solid #d6e3da;border-radius:12px;background:#f4f8f5}.secret p{margin:0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}.r6-other-apps{margin-top:22px;border-top:1px solid #e5e9f2;padding-top:6px}.r6-other-app{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:15px 0;border-bottom:1px solid #e5e9f2}.r6-other-app>div{min-width:0}.r6-other-app strong{font-size:14px;margin-right:8px}.r6-other-app p{margin:5px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px;overflow-wrap:anywhere}.r6-other-app .app-note{display:block;margin-top:4px;color:var(--r6-muted,#5f6e86);font-size:11px;line-height:18px}.r6-other-actions{display:flex;align-items:center;gap:8px;flex:none}.low-tools{margin-top:20px}.r6-drawer-footer{display:flex;align-items:center;justify-content:space-between;gap:12px}.r6-drawer-footer span{color:var(--r6-muted,#5f6e86);font-size:12px;line-height:20px;overflow-wrap:anywhere}.drawer-review{display:grid;gap:16px}.drawer-review .review-lead{margin:0;color:var(--r6-secondary,#566780);font-size:13px;line-height:21px}.drawer-review .spaced-small{margin-top:8px}.role-modal-actions{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;padding-top:14px;border-top:1px solid #e5e9f2}.transfer-preview{display:grid;gap:10px;padding:16px;border:1px solid #e5e9f2;border-radius:12px;background:#f8f9fc}.transfer-preview h4{margin:0;font-size:14px}.transfer-preview article{padding-top:10px;border-top:1px solid #e5e9f2}.transfer-preview p{margin:5px 0 0;color:var(--r6-secondary,#566780);font-size:12px;line-height:20px}.spaced{margin-top:4px}.employee-drawer :deep(.ant-descriptions-item-content){overflow-wrap:anywhere;font-size:14px}.employee-drawer :deep(.ant-descriptions-item-label){font-size:12px}.employee-drawer :deep(.ant-tabs-nav){position:sticky;top:-24px;z-index:3;background:#fff}
.r6-attendance-more{margin-top:18px;border-top:1px solid #e5e9f2;padding-top:14px}
.r6-association-review{margin-bottom:16px}
@media (max-width:760px){:global(.iam-employee-drawer .ant-drawer-content-wrapper){width:100%!important;max-width:100vw}.drawer-top{gap:8px}.drawer-identity h2{font-size:19px}.drawer-identity p{font-size:11px}.drawer-close{padding-inline:6px}.detail-link-card{flex-wrap:wrap;align-items:flex-start}.detail-link-card .ant-btn{margin-left:0}.account-status-card{flex-wrap:wrap}.r6-other-app{flex-wrap:wrap}.r6-other-actions{margin-left:0}.r6-drawer-footer{flex-wrap:wrap}}
</style>
