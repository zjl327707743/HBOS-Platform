<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { state, ui, isAdmin } from '../model.js'
import { summarizeWorkApp, buildWorkDraft, planWorkChanges, planRestoreDepartment, planSuspendApp, planReenableApp, getWorkMetadata } from '../work-policy.js'
import { saveWorkChanges, restoreDepartmentWork, suspendWorkApp, reenableWorkApp } from '../workAccess.js'
import AttendanceCard from './AttendanceCard.vue'

const props = defineProps({ subjectKind: { type: String, default: 'employee' }, subjectId: { type: String, required: true }, appId: { type: String, required: true } })
const emit = defineEmits(['back', 'saved'])
const editing = ref(false)
const draft = reactive({ baseRevision: 0, changes: {}, rows: [] })
const initialRows = ref('')
const error = ref('')
const notice = ref('')
const secondary = ref('')
const acknowledgeImportant = ref(false)
const scopeDetails = ref([])
const summary = computed(() => summarizeWorkApp(state, props.subjectKind, props.subjectId, props.appId))
const metadata = computed(() => getWorkMetadata(state, props.appId))
const canonicalRows = rows => JSON.stringify(rows.map(row => ({ id: row.id, enabled: row.enabled, scope: [...row.scope].sort() })))
const dirty = computed(() => editing.value && canonicalRows(draft.rows) !== initialRows.value)
const plan = computed(() => planWorkChanges(state, props.subjectKind, props.subjectId, props.appId, draft.changes))
const secondaryPlan = computed(() => secondary.value === 'restore' ? planRestoreDepartment(state, props.subjectId, props.appId) : secondary.value === 'suspend' ? planSuspendApp(state, props.subjectId, props.appId) : secondary.value === 'reenable' ? planReenableApp(state, props.subjectId, props.appId, { acknowledgeImportant: true }) : null)
const secondaryTitle = computed(() => ({ restore: '恢复部门安排', suspend: '停用这个应用', reenable: '重新启用这个应用' })[secondary.value])
const sourceRows = computed(() => summary.value.actionRows.filter(row => row.complex || (!row.available && (row.storedRule || row.configuredEnabled))))
const stateTone = computed(() => summary.value.status === 'available' ? 'green' : summary.value.status === 'review' ? 'orange' : 'default')

function hydrate() {
  Object.assign(draft, buildWorkDraft(state, props.subjectKind, props.subjectId, props.appId))
  initialRows.value = canonicalRows(draft.rows)
  error.value = ''
  secondary.value = ''
  acknowledgeImportant.value = false
}
watch(() => [props.subjectKind, props.subjectId, props.appId], () => { editing.value = false; notice.value = ''; hydrate() }, { immediate: true })
watch(() => state.revision, () => { if (!editing.value && !secondary.value) hydrate() })
function update(actionId, field, value) {
  const row = draft.rows.find(item => item.id === actionId)
  row[field] = Array.isArray(value) ? [...value] : value
  draft.changes[actionId] = { enabled: row.enabled, scope: [...row.scope] }
  error.value = ''
}
function startEditing() { hydrate(); notice.value = ''; editing.value = true }
async function requestLeave() {
  if (ui.busy) return false
  if (!dirty.value) return true
  const discard = await new Promise(resolve => Modal.confirm({ title: '放弃尚未保存的更改？', content: '已保存的应用安排不会变化。', okText: '放弃更改', cancelText: '继续修改', onOk: () => resolve(true), onCancel: () => resolve(false) }))
  if (discard) { editing.value = false; hydrate() }
  return discard
}
defineExpose({ requestLeave })
async function back() { if (await requestLeave()) emit('back') }
async function cancel() { if (await requestLeave()) { editing.value = false; hydrate() } }
async function save() {
  if (ui.busy || !isAdmin.value) return
  error.value = ''
  const result = await saveWorkChanges(props.subjectKind, props.subjectId, props.appId, draft.changes, draft.baseRevision)
  if (!result.ok) { error.value = result.error; return }
  editing.value = false
  hydrate()
  notice.value = result.changed ? '更改已保存到本机合成原型。' : '没有更改，继续按原来的安排执行。'
  message.success(notice.value)
  emit('saved', { subjectKind: props.subjectKind, subjectId: props.subjectId, appId: props.appId, changed: result.changed })
}
function openSecondary(type) { secondary.value = type; acknowledgeImportant.value = false; error.value = ''; notice.value = ''; draft.baseRevision = state.revision }
async function confirmSecondary() {
  if (ui.busy || !isAdmin.value) return
  const command = secondary.value === 'restore' ? restoreDepartmentWork : secondary.value === 'suspend' ? suspendWorkApp : reenableWorkApp
  const result = await command(props.subjectId, props.appId, draft.baseRevision, { acknowledgeImportant: acknowledgeImportant.value })
  if (!result.ok) { error.value = result.error; return }
  hydrate()
  notice.value = '应用安排已更新，原有账号和其他应用不受影响。'
  message.success('演示已保存到本机')
  emit('saved', { subjectKind: props.subjectKind, subjectId: props.subjectId, appId: props.appId, changed: result.changed })
}
</script>

<template>
  <section class="work-settings" aria-label="应用工作设置">
    <a-button type="text" class="back-button" :disabled="ui.busy" @click="back">← 返回{{ subjectKind === 'department' ? '默认应用' : '应用使用' }}</a-button>
    <div class="work-heading"><div><h2>{{ summary.targetName }} · {{ summary.name }}</h2><p>{{ subjectKind === 'department' ? '安排给本部门员工；数据范围按每一项工作分别设置。' : '按工作需要安排这个应用，其他应用保持原来的设置。' }}</p></div><a-tag :color="stateTone">{{ summary.statusLabel }}</a-tag></div>
    <a-alert v-if="summary.reason" type="info" show-icon :message="summary.text" />
    <a-alert v-if="notice" type="success" show-icon :message="notice" />

    <template v-if="!editing && !secondary">
      <div class="saved-work"><h3>现在可以做什么</h3><p class="business-summary">{{ summary.text }}</p><div v-for="row in summary.actionRows" :key="row.id" class="saved-work-row"><div><strong>{{ row.name }}</strong><span>{{ !row.available ? '暂未开放' : row.enabled ? '范围：' + row.scopeText : summary.status === 'unavailable' && row.configuredEnabled ? '已安排范围，当前暂不能使用' : row.complex ? '有特别范围限制，当前不可使用' : '未安排' }}</span></div><span class="work-source">{{ row.sourceText }}</span></div><div v-if="!summary.actionRows.length" class="muted">这里不安排普通工作。管理能力在独立流程中核定。</div></div>
      <div class="main-action"><a-button v-if="summary.canEdit && !summary.suspended" type="primary" :disabled="!isAdmin || ui.busy" @click="startEditing">修改</a-button><a-button v-if="sourceRows.length" @click="scopeDetails = scopeDetails.length ? [] : ['special']">查看特别安排</a-button></div>
      <AttendanceCard v-if="subjectKind === 'employee' && appId === 'attendance'" :employee-id="subjectId" configuration-preview />
    </template>

    <template v-if="editing">
      <h3 class="edit-question">允许做哪些工作？</h3>
      <div v-for="row in summary.actionRows" :key="row.id" class="work-edit-row">
        <div class="work-edit-title"><a-checkbox :checked="draft.rows.find(item => item.id === row.id)?.enabled" :disabled="!row.editable || !isAdmin || ui.busy" @change="event => update(row.id, 'enabled', event.target.checked)"><strong>{{ row.name }}</strong></a-checkbox><span class="work-source">{{ row.sourceText }}</span></div>
        <template v-if="row.editable && draft.rows.find(item => item.id === row.id)?.enabled"><label class="scope-label">{{ appId === 'inventory' ? (row.id === 'view' ? '可查询的仓库' : '可办理出库的仓库') : appId === 'lims' ? '可查看的检验组' : '可查看的对象' }}</label><a-checkbox-group :value="draft.rows.find(item => item.id === row.id).scope" :options="row.scopeOptions" :disabled="ui.busy || !isAdmin" @change="value => update(row.id, 'scope', value)" /></template>
        <p v-if="!row.editable" class="work-explanation">{{ !row.available ? '暂未开放，不能在这里开启。' : row.reason }}{{ row.complex ? ' 当前安排：' + row.configuredText : '' }}</p>
        <p v-else-if="!draft.rows.find(item => item.id === row.id)?.enabled" class="work-explanation">不允许这项工作。对目前已登记的对象生效；整个应用停用请使用下方单独操作。</p>
      </div>
      <div class="change-preview" aria-live="polite"><h3>更改后</h3><p>{{ plan.ok ? plan.after.text : plan.error }}</p><p v-if="plan.ok && plan.after.status === 'unavailable'" class="work-explanation">以上保存工作安排；账号或档案待确认期间，实际访问仍然拒绝。</p></div>
      <div v-if="subjectKind === 'department' && plan.ok && plan.changed" class="department-impact"><h3>将影响哪些员工</h3><p>将调整 {{ plan.impact.followingChanged }} 名员工的普通安排；{{ plan.impact.personalUnchanged }} 名员工的单独设置保持；{{ plan.impact.unavailable }} 人当前因账号或档案状态暂不可用。</p><p class="work-explanation">同一员工可能同时有部门安排和单独设置，以上数量可重叠；请展开核对具体工作。</p><a-collapse ghost><a-collapse-panel key="affected" header="核对全部受影响员工与具体工作"><div v-for="row in plan.impact.rows" :key="row.id" class="impact-person"><strong>{{ row.name }} <a-tag v-if="row.unavailable">暂不可用</a-tag></strong><p>{{ row.afterText }}</p><div v-for="detail in row.details.filter(item => item.changed || row.keptPersonal)" :key="detail.name"><span>{{ detail.name }}：{{ detail.before }} → {{ detail.after }}</span><small>{{ detail.sourceText }}</small></div></div></a-collapse-panel></a-collapse></div>
    </template>

    <div v-if="secondary && secondaryPlan" class="secondary-confirm"><h3>{{ secondaryTitle }}</h3><p v-if="secondary === 'suspend'">只停用 {{ summary.targetName }} 的{{ summary.name }}；不会停用账号，不影响其他应用或同部门同事。已有工作安排保留。</p><p v-else-if="secondary === 'restore'">只恢复这个员工、这个应用的普通工作安排；下方列明实际恢复结果。重要操作不由普通恢复顺手改写。</p><p v-else>请先核对将恢复的既有工作与对象范围。账号停用、档案待确认和其他限制继续有效。</p><div class="change-preview"><h3>确认后</h3><p>{{ secondaryPlan.after?.text || secondaryPlan.error }}</p><div v-for="row in secondaryPlan.after?.actionRows || []" :key="row.id" class="secondary-row"><span>{{ row.configuredText }}</span><span class="work-source">{{ row.sourceText }}</span></div></div><a-alert v-if="!secondaryPlan.ok" type="warning" show-icon :message="secondaryPlan.error" /><a-alert v-for="warning in secondaryPlan.warnings || []" :key="warning" type="warning" show-icon :message="warning" /><a-checkbox v-if="secondary === 'reenable' && secondaryPlan.warnings?.length" v-model:checked="acknowledgeImportant">我已逐项核对将恢复的既有重要操作或未开放配置；本次没有新增资格或扩大原范围。</a-checkbox></div>

    <a-collapse v-if="sourceRows.length" v-model:activeKey="scopeDetails" class="work-details"><a-collapse-panel key="special" header="特别安排明细"><div v-for="row in sourceRows" :key="row.id" class="detail-row"><strong>{{ row.name }}</strong><p>{{ row.configuredText }}</p><p>{{ row.reason || '这项能力暂未开放日常调整。' }} {{ row.sourceText }}</p><div v-if="row.storedRule?.scope?.length">{{ row.storedRule.mode === 'deny' ? '不允许的对象：' : '单独安排的对象：' }}{{ row.storedRule.scope.map(id => metadata.scopes.find(scope => scope.value === id)?.label || '待核对对象').join('、') }}</div></div><p class="work-explanation">这些特别安排不会被普通勾选自动覆盖。需要精细处理时，先保留本页明细交专门评审核对。</p></a-collapse-panel></a-collapse>
    <a-collapse v-if="summary.importantRows.length" class="important-section"><a-collapse-panel key="important" header="重要操作权限"><p class="work-explanation">这里仅查看已经核定的结果，不能勾选授予资质或平台管理能力。</p><div v-for="row in summary.importantRows" :key="row.id" class="detail-row"><strong>{{ row.name }}</strong><p>{{ row.enabled ? row.text : row.storedRule?.mode === 'allow' ? '已有单独安排，但当前账号、资格或范围条件未满足，不能使用。' : '尚未核定可用权限' }}</p><span class="work-source">{{ row.sourceText }}</span></div></a-collapse-panel></a-collapse>
    <a-alert v-if="error" type="error" show-icon :message="error" class="save-error" />

    <footer class="work-settings-footer">
      <template v-if="editing"><a-button type="primary" :loading="ui.busy" :disabled="!isAdmin || !plan.ok" @click="save">{{ subjectKind === 'department' && plan.changed ? '确认影响并保存更改' : '保存更改' }}</a-button><a-button :disabled="ui.busy" @click="cancel">取消</a-button></template>
      <template v-else-if="secondary"><a-button type="primary" :loading="ui.busy" :disabled="!isAdmin || !secondaryPlan.ok || (secondary === 'reenable' && secondaryPlan.warnings?.length && !acknowledgeImportant)" @click="confirmSecondary">确认{{ secondaryTitle }}</a-button><a-button :disabled="ui.busy" @click="secondary = ''; error = ''">取消</a-button></template>
      <template v-else-if="subjectKind === 'employee' && !metadata?.management"><a-button v-if="summary.hasPersonalOrdinary" type="link" :disabled="!isAdmin || ui.busy" @click="openSecondary('restore')">恢复部门安排</a-button><a-button v-if="summary.suspended" type="link" :disabled="!isAdmin || ui.busy" @click="openSecondary('reenable')">重新启用这个应用</a-button><a-button v-else type="link" danger :disabled="!isAdmin || ui.busy" @click="openSecondary('suspend')">停用这个应用</a-button></template>
    </footer>
  </section>
</template>

<style scoped>
.work-settings{display:flex;flex-direction:column;gap:24px;min-width:0;color:#293d31}.back-button{align-self:flex-start;padding-left:0;font-size:14px}.work-heading{display:flex;gap:16px;align-items:flex-start;justify-content:space-between}.work-heading h2{font-size:20px;line-height:28px;margin:0 0 8px;overflow-wrap:anywhere}.work-heading p,.work-explanation{font-size:14px;line-height:22px;color:#637266;margin:0}.work-heading>.ant-tag{font-size:14px;white-space:nowrap;margin:0}.saved-work h3,.change-preview h3,.department-impact h3,.secondary-confirm h3,.edit-question{font-size:16px;line-height:24px;margin:0 0 16px;font-weight:600}.business-summary{font-size:16px;line-height:26px;color:#365c43;margin:0 0 16px}.saved-work-row{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 0;border-top:1px solid #e5ebe4}.saved-work-row>div{display:flex;flex-direction:column;gap:8px}.saved-work-row strong{font-size:16px;line-height:24px}.saved-work-row span,.work-source{font-size:14px;line-height:22px}.work-source{color:#67786c}.main-action{display:flex;gap:16px;flex-wrap:wrap}.work-edit-row{border:1px solid #dde7dd;border-radius:10px;padding:20px;display:flex;flex-direction:column;gap:16px}.work-edit-title{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.work-edit-title :deep(.ant-checkbox-wrapper){font-size:16px;line-height:24px}.scope-label{font-size:14px;line-height:22px;color:#536b59}.work-edit-row :deep(.ant-checkbox-group){display:flex;flex-wrap:wrap;gap:16px}.work-edit-row :deep(.ant-checkbox-wrapper){font-size:14px;line-height:22px}.change-preview{background:#f1f7ee;border:1px solid #d8e6d3;border-radius:10px;padding:20px}.change-preview h3{margin-bottom:8px}.change-preview>p,.department-impact>p,.secondary-confirm>p{font-size:16px;line-height:26px;margin:0}.department-impact{border-top:1px solid #e4ebe2;padding-top:24px}.department-impact :deep(.ant-collapse-header){padding-left:0!important;font-size:14px}.impact-person{padding:16px 0;border-top:1px solid #e3eae1;font-size:14px;line-height:22px}.impact-person p{margin:8px 0}.impact-person>div{display:flex;flex-direction:column;gap:4px;margin-top:12px}.impact-person small{font-size:14px;color:#657769}.secondary-confirm{display:flex;flex-direction:column;gap:16px}.secondary-confirm>h3{margin:0}.secondary-row{display:flex;flex-direction:column;gap:6px;padding-top:16px;font-size:14px;line-height:22px}.work-details,.important-section{background:#fff;border-color:#e0e7dd}.work-details :deep(.ant-collapse-header),.important-section :deep(.ant-collapse-header){font-size:14px;line-height:22px}.detail-row{padding:16px 0;border-top:1px solid #e8ede6;font-size:14px;line-height:22px}.detail-row:first-child{border-top:0}.detail-row>p{margin:8px 0}.work-settings-footer{position:sticky;bottom:0;z-index:5;background:#fff;display:flex;gap:16px;flex-wrap:wrap;border-top:1px solid #dde7da;padding:20px 0 4px;margin-top:auto}.work-settings-footer :deep(.ant-btn),.main-action :deep(.ant-btn){min-height:40px;font-size:14px}.save-error{margin-top:0}@media(max-width:600px){.work-heading,.saved-work-row,.work-edit-title{flex-direction:column;align-items:flex-start}.work-edit-row,.change-preview{padding:16px}.work-settings-footer>.ant-btn{flex:1;white-space:normal;height:auto;min-height:40px}.work-settings{gap:24px}}
</style>
