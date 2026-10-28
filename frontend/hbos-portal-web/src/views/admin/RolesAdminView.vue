<script setup lang="ts">
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { Modal, message } from 'ant-design-vue'
import {
  TeamOutlined, UserOutlined, CalendarOutlined, CheckCircleFilled, MinusCircleOutlined, SearchOutlined, EditOutlined,
  DashboardOutlined, BankOutlined, ScheduleOutlined, ImportOutlined, SettingOutlined, BarChartOutlined, ExportOutlined,
  EyeOutlined, SafetyCertificateOutlined, ClockCircleOutlined, SwapOutlined,
} from '@ant-design/icons-vue'
import { canIam, iamMessage } from '@/services/iamAccess'
import { loadRoles, roleCommand, assertRolePreview, type AppRole, type RoleFeature, type RolePreview } from '@/services/iamRoles'
import { roleFeatureKey, sameRoleFeatures, roleScopeLabel, roleGroups } from '@/services/rolePresentation'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import PanelFrame from '@/components/iam/PanelFrame.vue'
import ChangeReview from '@/components/iam/ChangeReview.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import { useAccountProof } from '@/composables/useAccountProof'

interface PreviewMember {
  employee: string
  name: string
  employee_number?: string
  source_mode?: string
  before_allowed: boolean
  after_allowed: boolean
  changed: boolean
  reason: string
}
interface RolePreviewView extends RolePreview {
  role?: string
  role_key?: string
  draft_version?: number
  published_release?: string
  features?: RoleFeature[]
  personal_preserved?: number
  members?: PreviewMember[]
}
interface PublishResult { changed?: boolean; release?: string; published_revision?: number; replayed?: boolean }

const items = ref<AppRole[]>([])
const selected = ref('clerk')
const loading = ref(true)
const busy = ref(false)
const busyWrite = ref(false)
const error = ref('')
const readNotice = ref('')
const editing = ref(false)
const checked = ref<string[]>([])
const draftReviewOpen = ref(false)
const preview = ref<RolePreviewView | null>(null)
const restore = ref('')
const versionTab = ref('published')
const search = ref('')
const mustRead = ref(false)
const lastDraftAction = ref<'save' | 'restore' | ''>('')
const active = ref(true)
const needsReload = ref(false)
const role = computed(() => items.value.find(row => row.role_key === selected.value))
const proof = useAccountProof()
const canEdit = computed(() => canIam('iam.roles.edit'))
const canPublish = computed(() => canIam('iam.roles.publish'))
const hasPasswordProof = computed(() => proof.valid.value && proof.method.value === 'password')
const dirty = computed(() => editing.value && JSON.stringify([...checked.value].sort()) !== JSON.stringify(role.value?.draft_features.map(roleFeatureKey).sort()))
const unpublished = computed(() => Boolean(role.value && !sameRoleFeatures(role.value.draft_features, role.value.published_features)))
const displayed = computed(() => role.value ? editing.value ? checked.value : (versionTab.value === 'draft' ? role.value.draft_features : role.value.published_features).map(roleFeatureKey) : [])
const featureGroups = computed(() => {
  const registry = role.value?.registry || [], knownGroups = roleGroups.map(([key, title]) => ({ key, title })) as Array<{ key: string; title: string }>
  for (const item of registry) if (!knownGroups.some(group => group.key === item.group)) knownGroups.push({ key: item.group, title: '其他已登记功能' })
  return knownGroups.map(group => ({ ...group, rows: registry.filter(row => row.allowed && row.group === group.key && (!search.value || row.title.toLowerCase().includes(search.value.toLowerCase()))) })).filter(group => group.rows.length)
})
const descriptions: Record<string, string> = { staff: '查看自己的考勤', clerk: '协助负责部门核对日常考勤', admin: '在明确获准的公司内办理考勤管理' }
const icons = { staff: UserOutlined, clerk: TeamOutlined, admin: ScheduleOutlined }
const groupIcons: Record<string, unknown> = {
  self: UserOutlined, board: DashboardOutlined, records: TeamOutlined, company: BankOutlined,
  schedule: ScheduleOutlined, correction: EditOutlined, import: ImportOutlined, rules: SettingOutlined,
  reports: BarChartOutlined, export: ExportOutlined,
}
const roleIcon = computed(() => icons[role.value?.role_key as keyof typeof icons] || UserOutlined)
const reviewMode = computed<'draft' | 'publish' | null>(() => draftReviewOpen.value ? 'draft' : preview.value ? 'publish' : null)
const reviewOpen = computed(() => reviewMode.value !== null)
const statusTone = computed<'brand' | 'warning' | 'success' | 'neutral'>(() => editing.value ? 'brand' : unpublished.value ? 'warning' : role.value?.published_revision ? 'success' : 'neutral')
const statusLabel = computed(() => editing.value ? '正在修改草稿' : unpublished.value ? '草稿尚未生效' : role.value?.published_revision ? '当前生效' : '尚未发布')
const pendingTitle = computed(() => {
  const version = role.value?.draft_version
  if (lastDraftAction.value === 'save') return `待发布草稿 v${version} 已保存，尚未生效`
  if (lastDraftAction.value === 'restore') return `历史内容已恢复为草稿 v${version}，尚未生效`
  return `待发布草稿 v${version} 尚未生效`
})
const pendingDetail = computed(() => {
  const liveVersion = role.value?.published_revision ? `当前生效 v${role.value.published_revision}` : '当前没有已发布版本'
  if (!canPublish.value) return `${liveVersion}。请联系有发布权限的负责人查看员工影响并发布此草稿。`
  return `${liveVersion}。点击“查看发布影响”只会显示预览，不会改变员工权限；确认发布草稿 v${role.value?.draft_version} 后，员工才会使用新版本。`
})
const cleanCopy = computed(() => {
  if (!role.value?.published_revision) {
    if (canEdit.value && canPublish.value) return '尚无当前生效版本；先保存草稿，再查看发布影响。'
    if (canEdit.value) return '尚无当前生效版本；可先保存草稿，请有发布权限的负责人查看影响。'
    return '尚无当前生效版本。'
  }
  if (canEdit.value && canPublish.value) return '当前草稿与当前生效一致；先保存草稿，再查看发布影响。'
  if (canEdit.value) return '当前草稿与当前生效一致；可先保存草稿，请有发布权限的负责人查看影响。'
  return '当前草稿与当前生效一致。'
})
const publishPreviewCopy = computed(() => {
  if (!preview.value?.changed || !role.value) return ''
  const liveVersion = role.value.published_revision ? `当前生效版本 v${role.value.published_revision}` : '当前没有已发布版本'
  return `这一步只展示预览，不会改变员工权限。${liveVersion} → 待发布草稿 v${role.value.draft_version}；本人验证并点击“发布草稿 v${role.value.draft_version} 并生效”后，员工才会使用新版本。`
})
const publishButtonLabel = computed(() => role.value ? `发布草稿 v${role.value.draft_version} 并生效` : '确认发布')
function diffFeatures(before: RoleFeature[], after: RoleFeature[]) {
  return {
    added: after.filter(row => !before.some(old => roleFeatureKey(old) === roleFeatureKey(row))),
    removed: before.filter(row => !after.some(next => roleFeatureKey(next) === roleFeatureKey(row))),
  }
}
const added = computed<RoleFeature[]>(() => role.value ? diffFeatures(role.value.published_features, role.value.draft_features).added : [])
const removed = computed<RoleFeature[]>(() => role.value ? diffFeatures(role.value.published_features, role.value.draft_features).removed : [])
const checkedFeatures = computed<RoleFeature[]>(() => role.value ? role.value.registry.filter(row => checked.value.includes(roleFeatureKey(row))).map(({ operation_id, scope_binding }) => ({ operation_id, scope_binding })) : [])
const workingDiff = computed(() => role.value ? diffFeatures(role.value.draft_features, checkedFeatures.value) : { added: [], removed: [] })
const summaryDiff = computed(() => editing.value ? workingDiff.value : { added: added.value, removed: removed.value })
let generation = 0, viewEpoch = 0, disposed = false, requestId = ''
function groupIcon(key: string) { return groupIcons[key] || SettingOutlined }
function requestReloadOnReturn() {
  if (!active.value || !needsReload.value || loading.value || busy.value || error.value) return
  needsReload.value = false
  void load(editing.value)
}
function reset() {
  checked.value = role.value?.draft_features.map(roleFeatureKey) || []
  preview.value = null
  draftReviewOpen.value = false
  restore.value = ''
  requestId = ''
  mustRead.value = false
  error.value = ''
  readNotice.value = ''
  lastDraftAction.value = ''
  needsReload.value = false
  proof.invalidate()
}
async function load(preserve = false) {
  const run = ++generation, epoch = viewEpoch, previousSelected = selected.value
  loading.value = true
  error.value = ''
  try {
    const result = await loadRoles()
    if (disposed || run !== generation) return
    if (epoch !== viewEpoch) { needsReload.value = true; return }
    items.value = result
    if (!items.value.some(row => row.role_key === selected.value)) selected.value = items.value[0]?.role_key || ''
    if (!preserve || selected.value !== previousSelected) reset()
    preview.value = null
    draftReviewOpen.value = false
    mustRead.value = false
    needsReload.value = false
  } catch (e) {
    if (!disposed && run === generation) {
      if (epoch !== viewEpoch) needsReload.value = true
      else error.value = iamMessage(e)
    }
  } finally {
    if (!disposed && run === generation) {
      loading.value = false
      requestReloadOnReturn()
    }
  }
}
async function leave() {
  if (busy.value) return false
  if (!dirty.value) return true
  return new Promise<boolean>(resolve => Modal.confirm({
    title: '放弃尚未保存的角色草稿？',
    content: '已保存的待发布内容仍会保留在本页；未保存的勾选会丢弃。',
    okText: '放弃未保存修改',
    cancelText: '继续编辑',
    onOk: () => { editing.value = false; reset(); resolve(true) },
    onCancel: () => resolve(false),
  }))
}
async function cancelEdit() { if (await leave()) { editing.value = false; reset() } }
async function select(key: string) {
  if (busy.value || loading.value || mustRead.value || key === selected.value) return
  if (!await leave()) return
  viewEpoch++
  selected.value = key
  editing.value = false
  versionTab.value = 'published'
  reset()
}
function toggle(key: string) {
  if (busy.value || mustRead.value) return
  checked.value = checked.value.includes(key) ? checked.value.filter(value => value !== key) : [...checked.value, key]
  preview.value = null
  draftReviewOpen.value = false
  requestId = ''
  readNotice.value = ''
}
function showTab(value: string) {
  if (editing.value || busy.value) return
  versionTab.value = value
  preview.value = null
  draftReviewOpen.value = false
}
function featureName(row: RoleFeature) {
  return role.value?.registry.find(item => roleFeatureKey(item) === roleFeatureKey(row))?.title || row.operation_id
}
function memberMode(value?: string) {
  return value === 'department' || value === 'FOLLOW_DEPARTMENT' ? '跟随部门安排' : value === 'direct' || value === 'DIRECT' ? '单独设置' : value === 'NONE' ? '不安排此角色' : value === 'legacy' || value === 'LEGACY' ? '沿用已有安排' : '角色来源待核对'
}
function openSaveReview() {
  if (!role.value || busy.value || loading.value || mustRead.value || error.value || !canEdit.value || !editing.value || !dirty.value) return
  preview.value = null
  proof.invalidate()
  readNotice.value = ''
  draftReviewOpen.value = true
}
function closeReview() {
  if (busy.value) return
  draftReviewOpen.value = false
  preview.value = null
  proof.invalidate()
}
function openPublishReview() {
  if (!role.value || busy.value || loading.value || mustRead.value || error.value || editing.value || !canPublish.value) return
  draftReviewOpen.value = false
  void prepare()
}
async function saveDraft() {
  if (!role.value || !draftReviewOpen.value || busy.value || mustRead.value || !hasPasswordProof.value || !canEdit.value || !dirty.value || !editing.value) return
  const run = viewEpoch, roleKey = selected.value, expected = role.value.draft_version
  const features = role.value.registry.filter(row => checked.value.includes(roleFeatureKey(row))).map(({ operation_id, scope_binding }) => ({ operation_id, scope_binding }))
  busy.value = true
  busyWrite.value = true
  error.value = ''
  requestId ||= crypto.randomUUID()
  try {
    await roleCommand('save_role_draft', { role_key: roleKey, expected_draft_version: expected, features, request_id: requestId })
    if (disposed || run !== viewEpoch) return
    proof.invalidate()
    draftReviewOpen.value = false
    editing.value = false
    await load()
    if (disposed || run !== viewEpoch) return
    if (error.value) { mustRead.value = true; return }
    versionTab.value = 'draft'
    lastDraftAction.value = 'save'
    if (unpublished.value) message.success(`待发布草稿 v${role.value?.draft_version} 已保存，尚未生效。下一步：查看发布影响。`)
    else message.info('草稿已保存；当前草稿与当前生效一致，没有待发布变化。')
  } catch (e) {
    if (disposed || run !== viewEpoch) return
    error.value = iamMessage(e)
    mustRead.value = true
    proof.invalidate()
    draftReviewOpen.value = false
  } finally {
    busy.value = false
    busyWrite.value = false
    requestReloadOnReturn()
  }
}
async function prepare() {
  if (!role.value || busy.value || loading.value || mustRead.value || error.value || editing.value || dirty.value || !canPublish.value) return
  const run = viewEpoch
  busy.value = true
  error.value = ''
  preview.value = null
  draftReviewOpen.value = false
  requestId = ''
  proof.invalidate()
  try {
    const raw = await roleCommand<RolePreviewView>('preview_role_publish', { role_key: selected.value, expected_draft_version: role.value.draft_version, expected_release: role.value.published_release })
    if (disposed || run !== viewEpoch) return
    const checkedPreview = assertRolePreview(raw as unknown as RolePreview) as unknown as RolePreviewView
    if ((checkedPreview.role_key && checkedPreview.role_key !== selected.value)
      || (checkedPreview.draft_version !== undefined && checkedPreview.draft_version !== role.value.draft_version)
      || (checkedPreview.published_release !== undefined && String(checkedPreview.published_release) !== role.value.published_release)
      || (checkedPreview.features && !sameRoleFeatures(checkedPreview.features, role.value.draft_features))) throw new Error('当前角色或草稿已变化，请重新读取后再查看发布影响。')
    for (const count of [checkedPreview.reference_count, checkedPreview.effective_changed_count, checkedPreview.personal_preserved]) {
      if (count !== undefined && (!Number.isInteger(count) || count < 0)) throw new Error('发布影响人数无法确认，请重新读取后再核对。')
    }
    for (const person of checkedPreview.members || []) {
      if (typeof person.changed !== 'boolean' || typeof person.before_allowed !== 'boolean' || typeof person.after_allowed !== 'boolean') throw new Error('发布影响人员无法确认，请重新读取后再核对。')
    }
    preview.value = checkedPreview
    requestId = checkedPreview.changed ? crypto.randomUUID() : ''
  } catch (e) {
    if (disposed || run !== viewEpoch) return
    error.value = iamMessage(e)
  } finally {
    busy.value = false
    requestReloadOnReturn()
  }
}
async function publish() {
  if (!role.value || !preview.value || !preview.value.changed || busy.value || mustRead.value || !hasPasswordProof.value || !canPublish.value) return
  const run = viewEpoch, contextRevision = preview.value.context_revision
  busy.value = true
  busyWrite.value = true
  error.value = ''
  requestId ||= crypto.randomUUID()
  try {
    const result = await roleCommand<PublishResult>('publish_role', {
      role_key: selected.value,
      expected_draft_version: role.value.draft_version,
      expected_release: role.value.published_release,
      context_revision: contextRevision,
      request_id: requestId,
    })
    if (disposed || run !== viewEpoch) return
    proof.invalidate()
    preview.value = null
    requestId = ''
    await load()
    if (disposed || run !== viewEpoch) return
    if (error.value) { mustRead.value = true; return }
    versionTab.value = 'published'
    if (result?.changed === false) {
      readNotice.value = '没有待发布变化，未创建新版本。'
      message.info('没有待发布变化。')
    } else {
      const revision = role.value?.published_revision
      readNotice.value = `已发布；当前生效版本 ${revision ? `v${revision}` : '已更新'}。`
      message.success('角色发布已确认。')
    }
  } catch (e) {
    if (disposed || run !== viewEpoch) return
    error.value = iamMessage(e)
    mustRead.value = true
    proof.invalidate()
    preview.value = null
    requestId = ''
  } finally {
    busy.value = false
    busyWrite.value = false
    requestReloadOnReturn()
  }
}
async function restoreDraft() {
  if (editing.value || dirty.value) return
  if (!role.value || !restore.value || busy.value || mustRead.value || !hasPasswordProof.value || !canEdit.value) return
  const run = viewEpoch
  busy.value = true
  busyWrite.value = true
  error.value = ''
  requestId ||= crypto.randomUUID()
  try {
    await roleCommand('restore_role_release', { role_key: selected.value, source_release: restore.value, expected_draft_version: role.value.draft_version, request_id: requestId })
    if (disposed || run !== viewEpoch) return
    editing.value = false
    draftReviewOpen.value = false
    proof.invalidate()
    await load()
    if (disposed || run !== viewEpoch) return
    if (error.value) { mustRead.value = true; return }
    versionTab.value = 'draft'
    lastDraftAction.value = 'restore'
    if (unpublished.value) message.success(`历史内容已恢复为草稿 v${role.value?.draft_version}，尚未生效。下一步：查看发布影响。`)
    else message.info('历史内容已恢复为草稿；当前草稿与当前生效一致，没有待发布变化。')
  } catch (e) {
    if (disposed || run !== viewEpoch) return
    error.value = iamMessage(e)
    mustRead.value = true
    proof.invalidate()
  } finally {
    busy.value = false
    busyWrite.value = false
    requestReloadOnReturn()
  }
}
async function recheckAfterError() {
  if (busy.value) return
  const preserve = editing.value
  await load(preserve)
  if (error.value) return
  readNotice.value = preserve
    ? '已读取最新角色与草稿；本地选择仍保留。请核对后再验证并保存。'
    : '已读取最新角色、草稿与当前生效版本。请核对后再操作。'
  versionTab.value = preserve ? 'draft' : (unpublished.value ? 'draft' : 'published')
}
// KeepAlive retains the same subject's unsaved draft across workspace/app tabs.
// A role change or explicit cancel still asks before discarding it.
onBeforeRouteLeave(async to => {
  if (busyWrite.value) return false
  if (to.path.startsWith('/hbos/admin')) return true
  return leave()
})
onDeactivated(() => {
  active.value = false
  viewEpoch++
  proof.invalidate()
  draftReviewOpen.value = false
  preview.value = null
  readNotice.value = ''
  if (loading.value) needsReload.value = true
  if (busyWrite.value) {
    error.value = '页面切换时操作结果尚未确认。请先核对最新结果，确认保存或发布状态后再继续。'
    mustRead.value = true
  } else {
    requestId = ''
  }
})
onActivated(() => { active.value = true; requestReloadOnReturn() })
onMounted(() => { active.value = true; void load() })
onBeforeUnmount(() => {
  active.value = false
  viewEpoch++
  disposed = true
  generation++
  proof.invalidate()
  checked.value = []
  preview.value = null
  draftReviewOpen.value = false
  requestId = ''
})
useManagementViewMemory('RolesAdminView.vue', { selected, versionTab, search })
</script>
<template>
  <section class="r6-page r6-roles-page">
    <PageHeading eyebrow="应用管理" title="角色与权限" description="定义每个角色能做什么，再将角色安排给合适的同事。" />
    <div v-if="error" class="r6-resource-error" role="alert">
      <a-alert :message="error" type="warning" show-icon />
      <p class="aux">请先读取最新角色，确认当前状态后再继续；确认前不要重复提交。</p>
      <a-button :disabled="busy" @click="recheckAfterError">{{ editing ? '核对最新结果，保留编辑' : '核对最新结果' }}</a-button>
    </div>
    <a-alert v-if="readNotice" class="r6-role-read-notice" :message="readNotice" type="info" show-icon closable @close="readNotice = ''" />
    <a-skeleton v-if="loading" active />
    <div v-else class="r6-dual-panels">
      <PanelFrame as="aside" region="role-navigation" label="应用与角色模板" class="r6-navigation">
        <template #header>
          <p class="aux">选择应用</p>
          <div class="r6-role-app"><span class="r6-role-app-icon"><CalendarOutlined /></span><a-select value="attendance" aria-label="角色所属应用"><a-select-option value="attendance">考勤管理</a-select-option></a-select></div>
          <p class="aux" style="margin:20px 0 0">角色模板 · {{ items.length }}</p>
        </template>
        <div class="r6-choice-list"><button v-for="item in items" :key="item.role_key" :disabled="busy || loading || mustRead" :aria-pressed="selected === item.role_key" @click="select(item.role_key)"><span class="r6-choice-icon"><component :is="icons[item.role_key as keyof typeof icons] || UserOutlined" /></span><span><strong>{{ item.title }}</strong><small>{{ item.boundary_kind === 'SELF' ? '仅本人' : item.boundary_kind === 'DEPARTMENT' ? '指定部门' : '指定公司' }}</small></span></button></div>
        <template #footer>角色定义功能，员工设置负责范围。</template>
      </PanelFrame>
      <PanelFrame v-if="role" region="role-detail" label="角色功能与职责">
        <template #header>
          <div class="r6-role-head">
            <div class="r6-role-heading-title"><span class="r6-role-hero"><component :is="roleIcon" /></span><div><h2>{{ role.title }}</h2><p>{{ descriptions[role.role_key] || '按注册的功能与范围安排工作' }}</p></div></div>
            <a-button v-if="canEdit && !editing" :disabled="busy || mustRead" @click="reset(); editing = true; versionTab = 'draft'"><EditOutlined />编辑功能</a-button>
            <StatusTag v-else-if="editing" tone="brand">正在编辑</StatusTag>
          </div>
          <div class="r6-role-boundary"><span><EyeOutlined />可查看：{{ role.boundary_kind === 'SELF' ? '仅本人' : role.boundary_kind === 'DEPARTMENT' ? '明确负责的部门' : '明确负责的一个公司' }}</span><span><SafetyCertificateOutlined />{{ role.role_key === 'admin' ? '不授予平台管理能力' : role.role_key === 'clerk' ? '不包含下级部门' : '不查看他人资料' }}</span></div>
          <div v-if="unpublished && !editing" class="r6-pending-banner">
            <span class="r6-pending-icon"><ClockCircleOutlined /></span>
            <div><strong>{{ pendingTitle }}</strong><p>{{ pendingDetail }}</p></div>
            <a-button v-if="canPublish" type="primary" :disabled="busy || mustRead || Boolean(error)" @click="openPublishReview">查看发布影响</a-button>
          </div>
          <div class="r6-role-versions"><a-button :aria-pressed="versionTab === 'published' && !editing" :disabled="editing" @click="showTab('published')">当前生效版本</a-button><a-button :aria-pressed="versionTab === 'draft' || editing" :disabled="editing" @click="showTab('draft')">待发布草稿 <span v-if="unpublished"> · 有变更</span></a-button><span>{{ editing ? `编辑中 · 待发布草稿 v${role.draft_version}` : versionTab === 'published' ? role.published_revision ? `当前生效 v${role.published_revision}` : '尚无当前生效版本' : `待发布草稿 v${role.draft_version} · 尚未生效` }}</span></div>
        </template>
        <div v-if="editing" class="r6-editing-guide"><EditOutlined /><span>勾选或取消功能后先保存草稿；保存后查看哪些员工权限会变化，再确认发布。</span></div>
        <div class="r6-feature-toolbar"><h3>功能与职责 <small class="aux">{{ displayed.length }} 项{{ editing ? '已选择' : versionTab === 'published' ? '已启用' : '在草稿' }}</small></h3><a-input v-model:value="search" allow-clear placeholder="搜索功能" aria-label="搜索角色功能"><template #prefix><SearchOutlined /></template></a-input></div>
        <div class="r6-feature-groups"><details v-for="group in featureGroups" :key="group.key" class="r6-feature-group" open><summary><span class="r6-group-icon"><component :is="groupIcon(group.key)" /></span><strong>{{ group.title }}</strong><small>{{ group.rows.filter(row => displayed.includes(roleFeatureKey(row))).length }} / {{ group.rows.length }}</small></summary><div v-for="row in group.rows" :key="roleFeatureKey(row)" class="r6-feature-row"><a-checkbox v-if="editing" :checked="checked.includes(roleFeatureKey(row))" :disabled="busy || mustRead || !row.allowed" @change="toggle(roleFeatureKey(row))">{{ row.title }}</a-checkbox><div v-else class="r6-feature-read" :class="{ 'is-off': !displayed.includes(roleFeatureKey(row)) }"><CheckCircleFilled v-if="displayed.includes(roleFeatureKey(row))" /><MinusCircleOutlined v-else /><span>{{ row.title }}</span><span>{{ displayed.includes(roleFeatureKey(row)) ? '已启用' : '未启用' }}</span></div><small>{{ !row.allowed ? '超过此角色上限' : !row.integrated ? row.reason : roleScopeLabel(row.scope_binding) }}</small></div></details></div>
        <a-empty v-if="!featureGroups.length" description="没有匹配的功能" />
        <div v-if="editing || versionTab === 'draft'" class="r6-role-change-summary" aria-live="polite">
          <span class="r6-summary-title"><SwapOutlined />变更摘要</span>
          <span class="r6-role-diff added">增加 {{ summaryDiff.added.length }} 项</span>
          <span class="r6-role-diff removed">移除 {{ summaryDiff.removed.length }} 项</span>
          <span class="r6-summary-effect">{{ editing ? '保存后仍需发布' : '尚未生效' }}</span>
          <p v-if="editing" class="aux">当前待发布草稿 v{{ role.draft_version }}（基于当前生效 {{ role.published_revision ? `v${role.published_revision}` : '尚无' }}）；本地未保存 {{ checked.length }} 项。</p>
          <p v-else class="aux">待发布草稿 v{{ role.draft_version }} 尚未生效；下一步：查看发布影响。</p>
        </div>
        <details v-if="role.registry.some(row => !row.allowed)" class="r6-profile-tools"><summary>不在此角色范围内的功能</summary><p v-for="row in role.registry.filter(item => !item.allowed)" :key="roleFeatureKey(row)" class="aux">{{ row.title }} · 超过此角色上限</p></details>
        <ChangeReview :open="reviewOpen" :busy="busy" :title="reviewMode === 'draft' ? '保存角色修改' : '发布前查看影响'" @cancel="closeReview">
          <section v-if="reviewMode === 'draft' && role" class="r6-publish-review" aria-live="polite">
            <div class="r6-publish-subject">
              <span class="r6-publish-hero"><component :is="roleIcon" /></span>
              <div><p class="aux">考勤管理 · 应用角色</p><h3>{{ role.title }}</h3><p>保存为待发布草稿，当前员工使用方式不变。</p></div>
              <StatusTag tone="brand">尚未生效</StatusTag>
            </div>
            <div class="r6-publish-versions">
              <section><span>当前待发布草稿</span><strong>v{{ role.draft_version }}</strong><small>{{ role.draft_features.length }} 项功能</small></section>
              <span class="r6-publish-arrow" aria-hidden="true">→</span>
              <section class="next"><span>本地未保存选择</span><strong>{{ checked.length }} 项</strong><small>保存后仍为待发布</small></section>
            </div>
            <div class="r6-publish-grid">
              <section class="r6-publish-diff added"><h4>增加的功能 <span>{{ workingDiff.added.length }}</span></h4><ul v-if="workingDiff.added.length"><li v-for="row in workingDiff.added" :key="roleFeatureKey(row)"><strong>{{ featureName(row) }}</strong><small>{{ roleScopeLabel(row.scope_binding) }}</small></li></ul><p v-else>没有增加功能</p></section>
              <section class="r6-publish-diff removed"><h4>移除的功能 <span>{{ workingDiff.removed.length }}</span></h4><ul v-if="workingDiff.removed.length"><li v-for="row in workingDiff.removed" :key="roleFeatureKey(row)"><strong>{{ featureName(row) }}</strong><small>{{ roleScopeLabel(row.scope_binding) }}</small></li></ul><p v-else>没有移除功能</p></section>
            </div>
            <a-alert type="info" show-icon message="保存后草稿仍未生效。还需查看员工影响并确认发布。" />
            <p class="aux">差异仅比较当前已读取的草稿；确认保存时会重新校验草稿版本。</p>
          </section>
          <section v-else-if="reviewMode === 'publish' && preview && role" class="r6-publish-review" aria-live="polite">
            <div class="r6-publish-subject">
              <span class="r6-publish-hero"><component :is="roleIcon" /></span>
              <div><p class="aux">考勤管理 · 应用角色</p><h3>{{ role.title }}</h3><p>{{ preview.changed ? publishPreviewCopy : '当前草稿与当前生效版本一致；本次只查看影响，不会创建新版本。' }}</p></div>
              <StatusTag :tone="preview.changed ? 'warning' : 'success'">{{ preview.changed ? '发布前核对' : '没有待发布变化' }}</StatusTag>
            </div>
            <div class="r6-publish-versions">
              <section><span>当前生效版本</span><strong>{{ role.published_revision ? `v${role.published_revision}` : '尚无' }}</strong><small>{{ role.published_features.length }} 项功能</small></section>
              <span class="r6-publish-arrow" aria-hidden="true">→</span>
              <section class="next"><span>待发布草稿（尚未生效）</span><strong>v{{ role.draft_version }}</strong><small>{{ role.draft_features.length }} 项功能</small></section>
            </div>
            <template v-if="preview.changed">
              <div class="r6-publish-grid">
                <section class="r6-publish-diff added"><h4>新增功能 <span>{{ added.length }}</span></h4><ul v-if="added.length"><li v-for="row in added" :key="roleFeatureKey(row)"><strong>{{ featureName(row) }}</strong><small>{{ roleScopeLabel(row.scope_binding) }}</small></li></ul><p v-else>没有新增功能</p></section>
                <section class="r6-publish-diff removed"><h4>移除功能 <span>{{ removed.length }}</span></h4><ul v-if="removed.length"><li v-for="row in removed" :key="roleFeatureKey(row)"><strong>{{ featureName(row) }}</strong><small>{{ roleScopeLabel(row.scope_binding) }}</small></li></ul><p v-else>没有移除功能</p></section>
              </div>
              <section class="r6-publish-impact">
                <div class="r6-publish-impact-head"><h3>员工影响</h3><span class="aux">本次预览</span></div>
                <p class="r6-publish-counts"><strong>已安排 {{ preview.reference_count ?? '未返回' }} 人使用此角色</strong><span>；</span><strong>其中 {{ preview.effective_changed_count ?? '未返回' }} 人的实际权限会改变</strong>。</p>
                <p v-if="preview.personal_preserved !== undefined" class="aux">已有个人限制保留 {{ preview.personal_preserved }} 人；个人禁止、暂停与期限不会因本次发布自动解除。</p>
                <div v-if="preview.members?.length" class="r6-publish-members">
                  <article v-for="person in preview.members" :key="person.employee" class="r6-publish-member">
                    <div><strong>{{ person.name }}</strong><small v-if="person.employee_number">{{ person.employee_number }}</small><p>{{ memberMode(person.source_mode) }} · {{ person.before_allowed ? '当前可用' : '当前不可用' }} → {{ person.after_allowed ? '发布后可用' : '发布后不可用' }}</p><p v-if="person.reason">{{ person.reason }}</p></div>
                    <StatusTag :tone="person.changed ? 'warning' : 'neutral'">{{ person.changed ? '实际权限将变化' : '实际权限保持' }}</StatusTag>
                  </article>
                </div>
                <p v-else-if="preview.reference_count === 0" class="aux">当前没有员工使用此角色。</p>
                <p v-else-if="!preview.members" class="aux">未返回逐人清单；请查看使用人数与实际权限变化人数，重新查看后再决定是否发布。</p>
              </section>
              <a-alert type="warning" show-icon message="确认发布后生效；已有个人禁止、暂停与期限仍保留。" />
            </template>
            <div v-else class="r6-publish-empty">
              <strong>没有待发布变化</strong>
              <p>当前草稿与当前生效版本一致，没有可发布差异。请返回功能清单，调整并保存草稿后重新查看发布影响。</p>
            </div>
          </section>
          <a-alert v-if="error" class="spaced" type="warning" show-icon :message="error" />
          <OwnAccountVerification v-if="reviewMode === 'draft' || (reviewMode === 'publish' && preview?.changed)" password-only @verified="proof.sync" @invalidated="proof.invalidate" />
          <p v-if="reviewMode === 'publish' && !canPublish" class="aux">当前账号没有发布能力，不能确认发布。</p>
          <div v-if="reviewMode" class="r6-modal-actions">
            <a-button :disabled="busy" @click="closeReview">{{ reviewMode === 'draft' ? '返回修改' : '返回角色' }}</a-button>
            <a-button v-if="reviewMode === 'draft'" type="primary" :loading="busy" :disabled="!hasPasswordProof || busy || mustRead" @click="saveDraft">确认保存草稿</a-button>
            <a-button v-else-if="reviewMode === 'publish'" type="primary" :loading="busy" :disabled="!preview?.changed || !hasPasswordProof || busy || mustRead || !canPublish" @click="publish">{{ publishButtonLabel }}</a-button>
          </div>
        </ChangeReview>
        <details v-if="role.releases.length && canEdit && !editing" class="r6-profile-tools"><summary>从历史发布内容恢复草稿</summary><OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" /><a-select v-model:value="restore" aria-label="历史发布版本" style="width:100%" @change="requestId = ''"><a-select-option v-for="release in role.releases" :key="release.name" :value="release.name">v{{ release.revision }} · {{ release.published_at }}</a-select-option></a-select><a-button :disabled="!restore || !hasPasswordProof || busy || mustRead" @click="restoreDraft">恢复为草稿</a-button><p class="aux">恢复只写入草稿，不会自动发布；还需查看发布影响、本人验证并确认发布。</p></details>
        <template #footer>
          <div class="r6-role-foot">
            <StatusTag :tone="statusTone">{{ statusLabel }}</StatusTag>
            <div v-if="editing" class="r6-role-actions"><span class="r6-save-state"><span class="r6-save-dot" :class="{ dirty }" />{{ dirty ? '有未保存的修改' : '尚未修改功能' }}</span><a-button :disabled="busy" @click="cancelEdit">取消修改</a-button><a-button type="primary" :disabled="!dirty || busy || mustRead" @click="openSaveReview">保存草稿</a-button></div>
            <div v-else class="r6-role-actions"><span v-if="!unpublished" class="aux">{{ cleanCopy }}</span><a-button v-if="!unpublished && canPublish" :disabled="busy || mustRead || Boolean(error)" @click="openPublishReview">查看发布影响</a-button></div>
          </div>
        </template>
      </PanelFrame>
      <a-empty v-else description="暂无获准查看的角色" />
    </div>
  </section>
</template>
<style scoped>
.r6-role-read-notice { margin-bottom: 16px; }
.r6-role-app { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.r6-role-app-icon { display: grid; place-items: center; flex: none; width: 30px; height: 32px; border-radius: 9px; color: #fff; background: linear-gradient(140deg, #7663e9, #7976df); font-size: 16px; }
.r6-role-app .ant-select { flex: 1; min-width: 0; }
.r6-role-heading-title { display: flex; align-items: center; gap: 14px; min-width: 0; }
.r6-role-heading-title > div { min-width: 0; }
.r6-role-hero, .r6-publish-hero { display: grid; place-items: center; flex: none; width: 46px; height: 48px; border: 1px solid #e4ddf7; border-radius: 13px; color: #7862cd; background: linear-gradient(145deg, #eee8ff, #f0f3ff); font-size: 24px; }
.r6-role-boundary > span { display: inline-flex; align-items: center; gap: 6px; }
.r6-role-boundary .anticon { color: #8c83b6; }
.r6-pending-banner { display: flex; align-items: center; gap: 12px; margin-top: 16px; padding: 14px 16px; border: 1px solid #f0e1c2; border-radius: 10px; background: #fffaf0; }
.r6-pending-banner > div { flex: 1; min-width: 0; }
.r6-pending-banner strong { display: block; font-size: 13px; color: var(--r6-ink); }
.r6-pending-banner p { margin: 4px 0 0; font-size: 12px; line-height: 20px; color: #806e4c; }
.r6-pending-banner > .ant-btn { flex: none; }
.r6-pending-icon { display: grid; place-items: center; flex: none; width: 34px; height: 36px; border-radius: 10px; color: #a8781f; background: #fff1d6; font-size: 18px; }
.r6-editing-guide { display: flex; align-items: flex-start; gap: 8px; margin: 0 0 16px; padding: 11px 12px; border-radius: 8px; color: #665aa7; background: #f4f2fe; font-size: 12px; line-height: 20px; }
.r6-editing-guide .anticon { margin-top: 3px; flex: none; }
.r6-group-icon { display: grid; place-items: center; flex: none; width: 27px; height: 28px; border-radius: 7px; color: #8681b6; background: #eeedf8; font-size: 15px; }
.r6-role-change-summary { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--r6-line); font-size: 12px; color: var(--r6-secondary); }
.r6-summary-title { display: inline-flex; align-items: center; gap: 6px; color: var(--r6-secondary); }
.r6-summary-effect { margin-left: auto; color: var(--r6-muted); }
.r6-role-change-summary > p { flex-basis: 100%; margin: 0; }
.r6-role-diff { display: inline-flex; padding: 1px 6px; border-radius: 4px; background: #eff2f7; }
.r6-role-diff.added { color: #227451; background: #eaf7f0; }
.r6-role-diff.removed { color: #ad4b60; background: #fdf0f3; }
.r6-save-state { display: inline-flex; align-items: center; gap: 6px; color: var(--r6-muted); }
.r6-save-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #8792a5; }
.r6-save-dot.dirty { background: #b28330; }
.r6-publish-review { --r6-brand: #5754df; --r6-ink: #192a45; --r6-secondary: #566780; --r6-muted: #5f6e86; --r6-line: #e5e9f2; display: grid; gap: 16px; }
.r6-publish-subject { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.r6-publish-subject > div { min-width: 0; flex: 1; }
.r6-publish-subject h3 { margin: 2px 0 0; font-size: 19px; line-height: 27px; }
.r6-publish-subject p { margin: 5px 0 0; font-size: 12px; line-height: 20px; color: var(--r6-secondary); }
.r6-publish-hero { width: 46px; height: 48px; }
.r6-publish-versions { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); gap: 12px; align-items: stretch; }
.r6-publish-versions > section { display: grid; gap: 4px; padding: 14px 16px; border: 1px solid #e3e7f0; border-radius: 12px; background: #f8f9fc; }
.r6-publish-versions > section.next { border-color: #ddd6f3; background: #f6f3ff; }
.r6-publish-versions span { font-size: 11px; color: var(--r6-muted); }
.r6-publish-versions strong { font-size: 20px; line-height: 28px; color: var(--r6-ink); }
.r6-publish-versions small { font-size: 11px; line-height: 18px; color: var(--r6-secondary); }
.r6-publish-arrow { align-self: center; color: var(--r6-muted); }
.r6-publish-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.r6-publish-diff { min-width: 0; padding: 14px 16px; border: 1px solid #dcece3; border-radius: 12px; background: #f4faf7; }
.r6-publish-diff.removed { border-color: #f0dfe5; background: #fdf4f6; }
.r6-publish-diff h4 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 13px; color: #347254; }
.r6-publish-diff.removed h4 { color: #ad5468; }
.r6-publish-diff h4 span { margin-left: auto; font-size: 12px; }
.r6-publish-diff ul { margin: 10px 0 0; padding: 0 0 0 16px; max-height: 180px; overflow: auto; font-size: 12px; line-height: 22px; color: var(--r6-secondary); }
.r6-publish-diff li + li { margin-top: 4px; }
.r6-publish-diff li strong { display: block; font-weight: 500; color: var(--r6-ink); overflow-wrap: anywhere; }
.r6-publish-diff li small { display: block; font-size: 11px; color: var(--r6-muted); overflow-wrap: anywhere; }
.r6-publish-diff p { margin: 10px 0 0; font-size: 12px; color: var(--r6-muted); }
.r6-publish-impact { padding: 14px 16px; border: 1px solid var(--r6-line); border-radius: 12px; }
.r6-publish-impact-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.r6-publish-impact-head h3 { margin: 0; font-size: 15px; }
.r6-publish-counts { margin: 8px 0 0; font-size: 13px; line-height: 22px; color: var(--r6-secondary); }
.r6-publish-counts strong { color: var(--r6-ink); }
.r6-publish-members { margin-top: 10px; border-top: 1px solid var(--r6-line); }
.r6-publish-member { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--r6-line); }
.r6-publish-member:last-child { border-bottom: 0; }
.r6-publish-member > div { min-width: 0; flex: 1; }
.r6-publish-member strong { font-size: 13px; font-weight: 600; }
.r6-publish-member small { margin-left: 8px; font-size: 11px; color: var(--r6-muted); }
.r6-publish-member p { margin: 4px 0 0; font-size: 12px; line-height: 20px; color: var(--r6-secondary); overflow-wrap: anywhere; }
.r6-publish-member > .r6-status-tag { flex: none; }
.r6-publish-empty { padding: 16px; border: 1px solid #d8ecdf; border-radius: 12px; background: #f4faf7; }
.r6-publish-empty strong { color: #176d50; }
.r6-publish-empty p { margin: 6px 0 0; font-size: 12px; line-height: 20px; color: var(--r6-secondary); }
.r6-modal-actions { display: flex; justify-content: flex-end; gap: 12px; padding-top: 16px; border-top: 1px solid var(--r6-line); }
.r6-role-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.spaced { margin-top: 4px; }
@media (max-width: 760px) {
  .r6-role-heading-title { align-items: flex-start; }
  .r6-role-hero { width: 37px; height: 40px; border-radius: 11px; font-size: 20px; }
  .r6-pending-banner { flex-wrap: wrap; align-items: flex-start; }
  .r6-pending-banner > div { min-width: 180px; }
  .r6-pending-banner > .ant-btn { width: 100%; }
  .r6-role-change-summary { align-items: flex-start; }
  .r6-summary-effect { margin-left: 0; }
  .r6-publish-versions, .r6-publish-grid { grid-template-columns: 1fr; }
  .r6-publish-arrow { display: none; }
  .r6-publish-subject { flex-direction: column; }
  .r6-publish-member { flex-direction: column; }
  .r6-modal-actions .ant-btn { flex: 1; }
}
</style>
