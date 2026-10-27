<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import { canIam, iamMessage } from '@/services/iamAccess'
import { listDepartments } from '@/services/iamDepartments'
import { roleQuery, roleCommand, assertRolePreview, type RoleAssignment, type RolePreview, type RoleScope } from '@/services/iamRoles'
import type { DepartmentSummary } from '@/types/iam'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import ChangeReview from './ChangeReview.vue'
import StatusTag from './StatusTag.vue'
import { useAccountProof } from '@/composables/useAccountProof'
const props = defineProps<{ subjectKind: 'employee' | 'department'; subjectId: string }>(), emit = defineEmits<{ back: []; saved: [] }>()
const loading = ref(true), busy = ref(false), error = ref(''), editing = ref(false), current = ref<RoleAssignment | null>(null), choice = ref(''), scopeRefs = ref<string[]>([]), departments = ref<DepartmentSummary[]>([]), companies = ref<Array<{ id: string; name: string }>>([]), preview = ref<RolePreview | null>(null), original = ref(''), mustRead = ref(false)
const proof = useAccountProof(() => { preview.value = null }), canEdit = computed(() => canIam('iam.roles.assign') && canIam(props.subjectKind === 'department' ? 'iam.departments.manage' : 'iam.access.manage'))
const dirty = computed(() => editing.value && JSON.stringify([choice.value, [...scopeRefs.value].sort()]) !== original.value), own = computed(() => props.subjectKind === 'employee')
const source = computed(() => ['staff', 'clerk', 'admin'].includes(choice.value) ? 'DIRECT' : choice.value)
const roles = [{ key: 'staff', title: '普通员工', purpose: '查看自己的考勤', scope: '仅本人' }, { key: 'clerk', title: '部门考勤员', purpose: '协助负责部门核对日常考勤', scope: '明确负责的部门，不包含下级' }, { key: 'admin', title: '考勤管理员', purpose: '在获准公司内办理考勤管理', scope: '明确指定的一个公司' }]
const titleFor = (value?: string) => roles.find(row => row.key === value)?.title || (value === 'FOLLOW_DEPARTMENT' ? '跟随部门默认' : value === 'NONE' || value === '' ? '不安排角色' : '沿用已有安排')
let generation = 0, requestId = '', disposed = false
function reset() { choice.value = own.value ? current.value?.mode === 'DIRECT' ? current.value.role_key : current.value?.mode || 'FOLLOW_DEPARTMENT' : current.value?.has_role_default === false ? 'LEGACY' : current.value?.role_key || ''; scopeRefs.value = current.value?.responsibilities?.map(row => row.scope_ref) || []; original.value = JSON.stringify([choice.value, [...scopeRefs.value].sort()]); preview.value = null; requestId = '' }
async function load(preserve = false) {
  const run = ++generation; loading.value = true; error.value = ''
  try {
    const next = await roleQuery<RoleAssignment>(own.value ? 'get_assignment' : 'get_department_role', own.value ? { employee_id: props.subjectId } : { department: props.subjectId })
    if (disposed || run !== generation) return
    current.value = next
    if (!preserve) { reset(); editing.value = false } else original.value = JSON.stringify([own.value ? next.mode === 'DIRECT' ? next.role_key : next.mode || 'FOLLOW_DEPARTMENT' : next.has_role_default === false ? 'LEGACY' : next.role_key || '', [...(next.responsibilities?.map(row => row.scope_ref) || [])].sort()])
    preview.value = null; mustRead.value = false
    if (canEdit.value) { const scope = await listDepartments('all'); if (disposed || run !== generation) return; departments.value = scope.items.filter(row => row.confirmed); companies.value = scope.companies }
  } catch (e) { if (!disposed && run === generation) error.value = iamMessage(e) }
  finally { if (!disposed && run === generation) loading.value = false }
}
function selectChoice(value: string) { choice.value = value; scopeRefs.value = []; preview.value = null; requestId = '' }
function setSource(value: string) { selectChoice(value === 'DIRECT' ? 'staff' : value) }
function params() {
  if (!current.value) throw new Error('请先读取当前角色。')
  const mode = ['staff', 'clerk', 'admin'].includes(choice.value) ? 'DIRECT' : choice.value
  const responsibilities: RoleScope[] = choice.value === 'clerk' || choice.value === 'admin' ? scopeRefs.value.map(scope_ref => ({ scope_type: choice.value === 'clerk' ? 'DEPARTMENT' : 'COMPANY', scope_ref, include_descendants: 0 })) : []
  return own.value ? { employee_id: props.subjectId, mode, role_key: mode === 'DIRECT' ? choice.value : '', responsibilities, expected_version: current.value.version } : { department: props.subjectId, role_key: choice.value, expected_version: current.value.version }
}
async function prepare() {
  if (busy.value || mustRead.value || !canEdit.value || !dirty.value) return
  if (choice.value === 'clerk' && !scopeRefs.value.length || choice.value === 'admin' && scopeRefs.value.length !== 1) { error.value = '请明确选择负责范围后再核对。'; return }
  busy.value = true; error.value = ''; proof.invalidate()
  try { preview.value = assertRolePreview(await roleCommand<RolePreview>(own.value ? 'preview_assignment' : 'preview_department_role', params())); requestId = crypto.randomUUID() }
  catch (e) { error.value = iamMessage(e) }
  finally { busy.value = false }
}
async function commit() {
  if (busy.value || mustRead.value || !preview.value || !proof.valid.value || !canEdit.value) return
  busy.value = true; error.value = ''
  try { await roleCommand(own.value ? 'save_assignment' : 'save_department_role', { ...params(), context_revision: preview.value.context_revision, request_id: requestId }); proof.invalidate(); editing.value = false; await load(); emit('saved'); message.success('角色安排已保存，已有禁用和限制继续保留。') }
  catch (e) { error.value = iamMessage(e); mustRead.value = true; proof.invalidate(); preview.value = null }
  finally { busy.value = false }
}
async function requestLeave() { if (busy.value) return false; if (!dirty.value) return true; return new Promise<boolean>(resolve => Modal.confirm({ title: '放弃尚未保存的角色安排？', okText: '放弃草稿', cancelText: '继续编辑', onOk: () => { editing.value = false; reset(); resolve(true) }, onCancel: () => resolve(false) })) }
async function cancelEdit() { if (await requestLeave()) { editing.value = false; reset() } }
async function back() { if (await requestLeave()) emit('back') }
watch(() => [props.subjectKind, props.subjectId], () => load(), { immediate: true })
onBeforeUnmount(() => { disposed = true; generation++; proof.invalidate() })
defineExpose({ requestLeave })
</script>
<template>
  <section class="role-settings">
    <div class="role-heading"><a-button :disabled="busy" @click="back">返回应用清单</a-button><h2>{{ own ? '员工考勤角色' : '部门默认考勤角色' }}</h2></div>
    <a-alert v-if="error" :message="error" type="warning" show-icon /><a-button v-if="error || mustRead" :disabled="busy" @click="load(editing)">核对最新安排，保留草稿</a-button>
    <a-skeleton v-if="loading" active />
    <template v-else-if="current">
      <section class="result"><h3>{{ own ? current.effective_access?.allowed ? '当前有可用功能' : '当前暂不可用' : current.has_role_default === false ? '尚未设置角色默认，沿用已有安排' : current.role_key === 'staff' ? '部门默认：普通员工' : '不默认开通角色' }}</h3><p v-if="own">{{ current.effective_access?.reason || '实际功能以当前发布版本和已有访问限制为准。' }}</p><p v-if="own">角色来源：{{ current.mode === 'DIRECT' ? '个人单独指定' : current.mode === 'NONE' ? '未选角色' : current.mode === 'LEGACY' ? '沿用已有独立安排' : '跟随所属部门默认' }} <StatusTag v-if="current.selected_role?.published_revision" tone="success">生效版本 v{{ current.selected_role.published_revision }}</StatusTag></p><RouterLink v-if="own && current.department && canIam('iam.departments.read')" :to="{ path: '/hbos/admin/departments', query: { department: current.department, company: current.company, tab: 'apps' } }">查看所属部门默认</RouterLink><p v-if="!own">部门默认只提供普通员工的基础角色。部门考勤员与考勤管理员需要逐人单独设置。</p></section>
      <a-button v-if="!editing && canEdit" type="primary" @click="reset(); editing = true">{{ own ? '设置角色与范围' : '调整默认角色' }}</a-button>
      <template v-if="editing">
        <a-form layout="vertical" @submit.prevent="prepare"><fieldset :disabled="busy || Boolean(preview) || mustRead">
          <a-form-item v-if="own" label="角色来源"><a-select :value="source" @change="setSource"><a-select-option v-if="current.mode === 'LEGACY'" value="LEGACY" disabled>沿用已有安排</a-select-option><a-select-option value="FOLLOW_DEPARTMENT">跟随部门默认</a-select-option><a-select-option value="DIRECT">为此员工单独设置</a-select-option><a-select-option value="NONE">不安排此角色</a-select-option></a-select></a-form-item>
          <p v-if="own && source === 'FOLLOW_DEPARTMENT'" class="aux">使用主部门当前的默认角色。个人单独安排将被替换，已有禁止和暂停继续保留。</p>
          <div v-if="!own || source === 'DIRECT'" class="r6-role-cards" :class="{ 'is-department': !own }" role="radiogroup" :aria-label="own ? '选择考勤角色' : '部门默认角色'">
            <label v-for="item in own ? roles : roles.slice(0, 1)" :key="item.key" class="r6-role-card"><input type="radio" :name="`role-${subjectKind}-${subjectId}`" :value="item.key" :checked="choice === item.key" @change="selectChoice(item.key)" /><strong>{{ item.title }}</strong><span>{{ item.purpose }}</span><small>{{ item.scope }}</small></label>
            <label v-if="!own" class="r6-role-card"><input type="radio" :name="`role-${subjectKind}-${subjectId}`" value="" :checked="choice === ''" @change="selectChoice('')" /><strong>不默认开通</strong><span>跟随者不从部门默认获得角色功能。</span></label>
          </div>
          <a-form-item v-if="choice === 'clerk'" label="明确负责的部门（不默认含下级）"><a-select v-model:value="scopeRefs" mode="multiple" show-search option-filter-prop="label" :options="departments.map(row => ({ value: row.id, label: row.name + ' · ' + row.company }))" @change="preview = null" /></a-form-item>
          <a-form-item v-if="choice === 'admin'" label="明确负责的一个公司"><a-select :value="scopeRefs[0]" show-search option-filter-prop="label" :options="companies.map(row => ({ value: row.id, label: row.name }))" @change="(value: string) => { scopeRefs = [value]; preview = null }" /></a-form-item>
          <p class="aux">选择角色不会自动开户、解除应用暂停或清除个人禁止。本人查询始终只看本人；实际功能以已发布版本为准。</p>
        </fieldset><a-space wrap><a-button :disabled="busy" @click="cancelEdit">取消修改</a-button><a-button type="primary" html-type="submit" :loading="busy" :disabled="!dirty || Boolean(preview) || mustRead">核对实际结果</a-button></a-space></a-form>
        <ChangeReview :open="Boolean(preview)" :busy="busy" title="核对角色与负责范围" @cancel="preview = null; proof.invalidate()"><section v-if="preview" class="preview" aria-live="polite"><h3>保存后的实际结果</h3><div class="r6-assignment-compare"><div><small>当前安排</small><strong>{{ own ? titleFor(current.mode === 'DIRECT' ? current.role_key : current.mode) : titleFor(current.role_key) }}</strong><p>{{ current.responsibilities?.map(row => row.scope_ref).join('、') }}</p></div><div><small>本次安排</small><strong>{{ titleFor(choice) }}</strong><p>{{ choice === 'staff' ? '仅本人' : scopeRefs.join('、') }}</p></div></div><template v-if="own"><p>{{ preview.after?.allowed ? '有可用功能' : '当前暂不可用' }}：{{ preview.after?.reason || '已核对发布版本、账号和旧限制。' }}</p><p v-for="row in preview.after?.operations" :key="JSON.stringify(row)">{{ row.label || '已登记功能' }} · {{ row.scope_type === 'SELF' ? '本人' : row.scope_ref }}：{{ row.allowed ? '可用' : '不可用' }}</p></template><template v-else><p>跟随默认 {{ preview.reference_count }} 人；实际权限变化 {{ preview.effective_changed_count }} 人；个人安排保留 {{ preview.personal_preserved }} 人。</p><p v-for="row in preview.members" :key="row.employee">{{ row.name }}：{{ row.changed ? '实际权限将变化' : '实际权限保持' }} {{ row.reason }}</p></template><OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" /><a-space wrap><a-button :disabled="busy" @click="preview = null; proof.invalidate()">返回修改</a-button><a-button type="primary" :loading="busy" :disabled="!proof.valid.value || !preview.changed || mustRead" @click="commit">确认保存</a-button></a-space></section></ChangeReview>
      </template>
    </template>
  </section>
</template>
<style scoped>
.role-settings{display:grid;gap:16px;font-size:14px;min-width:0}.role-heading{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.role-heading h2{margin:0;font-size:20px}.result,.preview{border:1px solid #e5e9f2;padding:20px;border-radius:12px}.result h3{margin-top:0}.result p{margin:8px 0;color:var(--hbos-text-secondary)}fieldset{border:0;padding:0;margin:0;min-width:0}.ant-select{width:100%}.preview p{overflow-wrap:anywhere}
</style>
