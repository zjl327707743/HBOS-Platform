<script setup lang="ts">
import { developmentObservation } from '@/services/frappeClient'
import { computed, getCurrentInstance, ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { getPerson } from '@/services/iamPeople'
import { listDepartments } from '@/services/iamDepartments'
import { getEffectiveWork, getWorkSubject, previewAppSettings, saveAppSettings, savedWorkResult, changedWork, fixedSelfScope, type WorkDraft } from '@/services/iamWork'
import { canIam, iamMessage } from '@/services/iamAccess'
import type { WorkApp, WorkChange, WorkPreview, WorkTarget, WorkScope, AppSettings } from '@/types/iam'
import AttendanceAccessSummary from './AttendanceAccessSummary.vue'
const props = defineProps<{ subjectKind: 'employee' | 'department'; subjectId: string; appId: string }>()
const viewInstance = import.meta.env.DEV ? getCurrentInstance()?.uid : undefined
const emit = defineEmits<{ back: []; saved: [] }>()
const app = ref<WorkApp | null>(null), target = ref<WorkTarget | null>(null), loading = ref(true), busy = ref(false), error = ref(''), editing = ref(false), canConfigure = ref(false)
const identity = ref(''), accessState = ref<'normal'|'paused'>('normal'), permissionMode = ref<'department'|'personal'>('department')
const original = ref<WorkChange[]>([]), draft = ref<WorkChange[]>([]), preview = ref<WorkPreview | null>(null)
const explicitlyEdited = ref<Set<string>>(new Set())
let generation = 0
const changes = computed(() => changedWork(original.value, draft.value)), dirty = computed(() => editing.value && (changes.value.length > 0 || explicitlyEdited.value.size > 0 || accessState.value !== (app.value?.suspended ? 'paused' : 'normal') || permissionMode.value !== app.value?.permission_mode))
const ordinary = computed(() => app.value?.operations.filter(row => !row.important && row.available !== false) || []), important = computed(() => app.value?.operations.filter(row => row.important) || [])
const effectiveStatus = computed(() => app.value?.suspended ? '已暂停' : ordinary.value.some(row=>row.enabled) ? `已开通：${ordinary.value.flatMap(row=>row.scopes).every(scope=>scope.scope_type==='SELF') ? '仅本人' : app.value?.summary}` : `未开通：${ordinary.value.find(row=>row.reason)?.reason || '当前没有有效功能授权'}`)
const canManageApp = computed(() => canConfigure.value && canIam(props.subjectKind === 'department' ? 'iam.departments.manage' : 'iam.access.manage') && app.value?.integrated)
const canEditWork = computed(() => canManageApp.value && ordinary.value.some(row => row.editable))
const scopeKey = (scope: WorkScope) => JSON.stringify([scope.scope_type, scope.scope_ref])
function setDraft() { explicitlyEdited.value = new Set(); accessState.value = app.value?.suspended ? 'paused' : 'normal'; permissionMode.value = app.value?.permission_mode || (props.subjectKind === 'department' ? 'personal' : 'department'); original.value = (app.value?.operations.filter(row => row.editable && !row.important) || []).map(row => ({ operation_id: row.operation_id, enabled: row.enabled, scopes: row.scopes.map(({scope_type,scope_ref}) => ({scope_type,scope_ref})) })); draft.value = JSON.parse(JSON.stringify(original.value)); preview.value = null }
async function load(preserve = false) { const run = ++generation; loading.value = true; error.value = ''; try { let subjectName = props.subjectId; if (props.subjectKind === 'employee') { const person = canIam('iam.people.read') ? await getPerson(props.subjectId) : await getWorkSubject(props.subjectId,props.appId); identity.value = `${person.employee.name || '所选员工'} · 工号 ${person.employee.employee_number || '待核对'}`; subjectName = person.employee.user_id || ''; canConfigure.value = Boolean(subjectName) && person.employee.account_status === 'active'; if (!subjectName) throw new Error('尚未开通员工账号，请先完成开户或关联。部门默认安排可在应用清单查看。') } else { const departments = await listDepartments('all'); canConfigure.value = departments.items.some(row => row.id === props.subjectId && row.confirmed === true) }; const next = { subject_type: props.subjectKind === 'employee' ? 'User' as const : 'Department' as const, subject_name: subjectName, app_id: props.appId }; const saved = await getEffectiveWork(next); if (run !== generation) return; target.value = next; app.value = saved; if (!preserve) { setDraft(); editing.value = false } else original.value = saved.operations.filter(row => row.editable && !row.important).map(row => ({ operation_id: row.operation_id, enabled: row.enabled, scopes: row.scopes.map(({scope_type,scope_ref}) => ({scope_type,scope_ref})) })); preview.value = null } catch (e) { if (run === generation) error.value = iamMessage(e) } finally { if (run === generation) loading.value = false } }
function workDraft(): WorkDraft { if (!app.value || !target.value) throw new Error('请先读取已保存设置。'); return { target: target.value, changes: changes.value, expected_version: app.value.version, context_revision: app.value.context_revision } }
function settings(): AppSettings { return {access_state:accessState.value, permission_mode:permissionMode.value, changes:permissionMode.value === 'department' ? [] : (app.value?.permission_mode === 'department' ? draft.value : draft.value.filter(row => explicitlyEdited.value.has(row.operation_id) || changes.value.some(change=>change.operation_id===row.operation_id)))} }
async function prepare() {
  if (busy.value || !canManageApp.value || !dirty.value) return
  error.value = ''; if (settings().changes.some(row => row.enabled && !row.scopes.length)) { error.value = '请为每项功能选择可查看的数据。'; return }
  busy.value = true
  try { preview.value = await previewAppSettings(workDraft(), settings()); if (!preview.value.changed) { preview.value = null; message.info('当前权限无需变更。') } } catch (e) { error.value = iamMessage(e) } finally { busy.value = false }
}
async function commit() {
  if (!preview.value || !canManageApp.value || busy.value) return
  busy.value = true; error.value = ''
  try { const result = await saveAppSettings(workDraft(), settings(), preview.value, crypto.randomUUID()); app.value = savedWorkResult(result,app.value!,target.value!); editing.value=false; setDraft(); message.success('权限已保存。'); emit('saved') } catch (e) { error.value = iamMessage(e); preview.value = null } finally { busy.value = false }
}
function impactResult(row: {result?:string;before?:string;after?:string}) { return row.result || [row.before,row.after].filter(text => typeof text === 'string' && text).join(' → ') || '已按当前安排核对' }
function changeScopes(row: WorkChange, keys: unknown[]) { explicitlyEdited.value.add(row.operation_id); row.scopes = keys.map(key => { const [scope_type, scope_ref] = JSON.parse(String(key)); return {scope_type,scope_ref} }); preview.value = null }
function toggleWork(row: WorkChange) { explicitlyEdited.value.add(row.operation_id); const fixed=fixedSelfScope(ordinary.value.find(item=>item.operation_id===row.operation_id)); row.scopes=row.enabled ? (fixed ? [fixed] : row.scopes) : []; preview.value=null }
async function requestLeave() { if (busy.value) return false; if (!dirty.value) return true; return new Promise<boolean>(resolve => Modal.confirm({ title: '放弃尚未保存的工作草稿？', content: '已保存的安排不受影响。', okText: '放弃草稿', cancelText: '继续编辑', onOk: () => resolve(true), onCancel: () => resolve(false) })) }
async function back() { if (await requestLeave()) emit('back') }
watch(() => [props.subjectKind,props.subjectId,props.appId], () => load(), { immediate: true }); defineExpose({ requestLeave })
</script>
<template>
<section class="work-settings" :data-view-instance="viewInstance"><output v-if="developmentObservation">本机页面实例 {{ viewInstance }}</output>
  <div class="work-head"><a-button :disabled="busy" @click="back">返回应用清单</a-button><h2>{{ app?.title || '应用权限' }}</h2></div>
  <p v-if="identity" class="target-identity">正在设置：{{ identity }}</p>
  <a-alert v-if="error" :message="error" type="warning" show-icon /><a-button v-if="error" :disabled="busy" @click="load(editing)">读取最新设置，保留草稿</a-button>
  <a-skeleton v-if="loading" active />
  <template v-else-if="app">
    <section class="current-result"><h3>{{ effectiveStatus }}</h3><p>权限来源：{{ app.permission_mode === 'personal' ? '为此员工单独设置' : '来自所属部门' }}</p>
      <article v-for="row in ordinary" :key="row.operation_id" class="work-row"><strong>{{ row.label }}</strong><span v-if="!row.enabled">{{row.reason || '当前不可用'}}</span><span v-else-if="!fixedSelfScope(row)">{{row.scopes.map(scope=>scope.label||scope.scope_ref).join('、')}}</span></article>
    </section>
    <AttendanceAccessSummary v-if="app.app_id === 'attendance' && subjectKind === 'employee'" :app="app" />
    <a-alert v-if="!app.integrated || !canConfigure" :message="!app.integrated ? '尚未接入此管理功能。' : '员工账号尚未确认，当前只读。'" type="info" />
    <a-button v-if="!editing && canManageApp" type="primary" @click="setDraft(); editing = true">设置权限</a-button>
    <a-button v-if="!editing && canManageApp && app.suspended" @click="setDraft(); accessState = 'normal'; editing = true">恢复访问</a-button>
    <a-form v-if="editing" layout="vertical" @submit.prevent="prepare">
      <fieldset :disabled="busy || Boolean(preview)">
        <a-form-item v-if="subjectKind === 'employee'" label="权限来源"><a-radio-group v-model:value="permissionMode"><a-radio value="department">使用部门默认权限</a-radio><a-radio value="personal">为此员工单独设置</a-radio></a-radio-group></a-form-item>
        <p v-if="permissionMode === 'department'" class="aux">该应用的普通个人设置将被替换，其他应用和重要权限保留。核对变更时会读取所属部门当前有效权限，并显示实际范围和不可用原因。</p>
        <template v-else>
          <section v-for="row in draft" :key="row.operation_id" class="work-row"><a-checkbox v-model:checked="row.enabled" @change="toggleWork(row)">{{ ordinary.find(item => item.operation_id === row.operation_id)?.label }}</a-checkbox><template v-if="row.enabled && !fixedSelfScope(ordinary.find(item=>item.operation_id===row.operation_id))"><label>可查看的数据</label><a-checkbox-group :value="row.scopes.map(scopeKey)" @change="(values: unknown[]) => changeScopes(row, values)"><a-checkbox v-for="scope in ordinary.find(item => item.operation_id === row.operation_id)?.objects || []" :key="scopeKey(scope)" :value="scopeKey(scope)">{{ scope.label || (scope.scope_type === 'SELF' ? '本人' : scope.scope_ref) }}</a-checkbox></a-checkbox-group></template></section>
        </template>
        <details v-if="subjectKind==='employee'"><summary>暂停此应用</summary><a-form-item label="应用总限制"><a-radio-group v-model:value="accessState"><a-radio value="normal">解除暂停，按有效权限访问</a-radio><a-radio value="paused">暂停此员工使用{{ app.title }}</a-radio></a-radio-group><p class="aux">暂停保留原权限。解除暂停仍受其他禁止和期限限制。</p></a-form-item></details>
      </fieldset>
      <div class="work-footer"><a-button :disabled="busy" @click="editing = false; setDraft()">取消修改</a-button><a-button type="primary" :disabled="!dirty || Boolean(preview)" :loading="busy" html-type="submit">核对变更</a-button></div>
    </a-form>
    <details v-if="important.length"><summary>重要权限（仅查看）</summary><p class="aux">重要权限不会随普通部门权限获得，也不能在此授予。</p><article v-for="row in important" :key="row.operation_id" class="work-row"><strong>{{ row.label }}</strong><span>{{ row.reason || (row.enabled ? '请通过专门流程核验资格与用途' : '未授予') }}</span><small>{{ row.source_text }}</small></article></details>
    <section v-if="preview" class="preview" aria-live="polite"><h3>保存后的实际结果</h3><p>{{ preview.summary }}</p><p>访问状态：{{ preview.after.suspended ? '已暂停' : '正常' }}；权限来源：{{ preview.after.permission_mode === 'personal' ? '为此员工单独设置' : '来自所属部门' }}</p><p v-for="row in preview.after.operations.filter(item => !item.important)" :key="row.operation_id">{{ row.label }}：{{ row.enabled ? row.scopes.map(scope => scope.label || (scope.scope_type === 'SELF' ? '本人' : scope.scope_ref)).join('、') : row.reason || '当前不可用' }}</p>
      <template v-if="subjectKind === 'department' && preview.impact"><p>跟随变化 {{ preview.impact.changed }} 人；个人权限保留 {{ preview.impact.personal_preserved }} 人；不可用 {{ preview.impact.unavailable }} 人。</p><details><summary>查看全部受影响员工</summary><p v-for="(row,index) in preview.impact.employees" :key="index">{{ row.name }}：{{ impactResult(row) }}{{ row.personal_preserved ? '（保留个人权限）' : '' }}</p></details></template>
      <p class="aux">保存时再次核对管理范围、来源、期限和资格；本次变更一次保存。</p><a-button :disabled="busy" @click="preview = null">返回核对</a-button><a-button type="primary" :loading="busy" @click="commit">确认保存</a-button>
    </section>
  </template>
</section>
</template>
<style scoped>
.work-settings{display:grid;gap:16px;min-width:0;width:100%;font-size:16px}.work-head{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.work-head h2{font-size:20px;margin:0}.target-identity{margin:0;font-weight:600}.current-result{display:grid;gap:12px}.current-result h3,.current-result p{margin:0}.work-row{display:grid;gap:8px;padding:16px;border:1px solid var(--hbos-border-subtle,#dce5e0);border-radius:12px}.work-row small,.aux{font-size:14px;color:var(--hbos-text-secondary);line-height:1.6}.work-footer{position:sticky;bottom:0;display:flex;justify-content:flex-end;gap:12px;background:var(--hbos-surface-solid,#fff);padding:16px 0}.preview{padding:20px;border:1px solid #8eaf9c;border-radius:12px;background:#f2f8f4}.preview .ant-btn+.ant-btn{margin-left:12px}summary{cursor:pointer;font-size:14px;font-weight:600}fieldset{border:0;padding:0;margin:0;min-width:0}.ant-radio-group{display:flex;gap:12px;flex-wrap:wrap}
</style>
