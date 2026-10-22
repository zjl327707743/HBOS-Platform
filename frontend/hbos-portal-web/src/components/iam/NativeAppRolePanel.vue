<script setup lang="ts">
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { canIam, iamMessage } from '@/services/iamAccess'
import { describeAppRoles, previewAppRoles, saveAppRoles, type AppRoleApp, type AppRolePreview, type AppRoleState } from '@/services/iamAppRoles'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { useAccountProof } from '@/composables/useAccountProof'
const props = defineProps<{ employeeId: string }>()
const emit = defineEmits<{ saved: [] }>()
const state = ref<AppRoleState | null>(null), loading = ref(true), busy = ref(false)
// A failed read must not replace an open editor, and a failed preview/save must
// not replace the whole panel: keep the two failure surfaces separate.
const loadError = ref(''), actionError = ref('')
const editing = ref<string | null>(null), selected = ref<string[]>([]), preview = ref<AppRolePreview | null>(null)
const acknowledged = ref(false)
const proof = useAccountProof(() => { preview.value = null })
// One request id per edit intent: a retry after a timeout must be replayable.
const requestId = ref('')
let generation = 0
const canEdit = () => canIam('iam.access.manage') && state.value?.can_grant === true && Boolean(state.value?.scope_envelope)
const passwordProof = () => proof.valid.value && proof.method.value === 'password'
async function load() {
  const run = ++generation
  loading.value = true; loadError.value = ''
  try {
    const next = await describeAppRoles(props.employeeId)
    if (run !== generation) return
    state.value = next
    if (editing.value && !next.apps.some(app => app.app_id === editing.value)) cancel()
  } catch (e) { if (run === generation) { state.value = null; loadError.value = iamMessage(e) } }
  finally { if (run === generation) loading.value = false }
}
function start(app: AppRoleApp) {
  editing.value = app.app_id; selected.value = [...app.current]; preview.value = null
  acknowledged.value = false; actionError.value = ''; requestId.value = ''
}
function cancel() {
  editing.value = null; selected.value = []; preview.value = null; acknowledged.value = false
  actionError.value = ''; requestId.value = ''; proof.invalidate()
}
function toggleRole(role: string) {
  selected.value = selected.value.includes(role) ? selected.value.filter(item => item !== role) : [...selected.value, role]
  // The preview context is computed for an exact role set; keeping it would
  // submit an unpreviewed change with a stale context_revision.
  preview.value = null; actionError.value = ''
}
async function prepare() {
  if (busy.value || !state.value || !editing.value || !acknowledged.value) return
  busy.value = true; actionError.value = ''
  try {
    preview.value = await previewAppRoles(props.employeeId, editing.value, selected.value, state.value.version, acknowledged.value)
    if (!preview.value.changed) actionError.value = '所选角色与当前一致，无需保存。'
  } catch (e) { actionError.value = iamMessage(e); preview.value = null }
  finally { busy.value = false }
}
async function commit() {
  if (busy.value || !state.value || !editing.value || !preview.value || !acknowledged.value) return
  if (!passwordProof()) { actionError.value = '保存需要本人数密码验证（飞书验证不能替代），请在上方重新验证。'; return }
  busy.value = true; actionError.value = ''
  try {
    requestId.value ||= crypto.randomUUID()
    await saveAppRoles(props.employeeId, editing.value, selected.value, state.value.version, preview.value.context_revision, requestId.value, acknowledged.value)
    proof.invalidate(); editing.value = null; selected.value = []; preview.value = null; acknowledged.value = false; requestId.value = ''
    message.success('应用角色已保存，其他应用权限和账号状态保持不变。')
    await load(); emit('saved')
  } catch (e) {
    // Keep the editor and the chosen roles so the operator can re-preview
    // instead of being dropped back to the read state.
    actionError.value = iamMessage(e); preview.value = null
  } finally { busy.value = false }
}
watch(() => props.employeeId, () => { cancel(); void load() }, { immediate: true })
</script>
<template>
  <section class="native-app-roles">
    <a-skeleton v-if="loading" active />
    <template v-else-if="loadError">
      <a-alert :message="loadError" type="warning" show-icon />
      <a-button :disabled="busy" @click="load()">重新读取</a-button>
    </template>
    <template v-else-if="state">
      <p class="aux">这里只调整已登记的跨应用原生角色；考勤角色、账号状态和其他应用授权不受影响。</p>
      <article v-for="app in state.apps" :key="app.app_id" class="app-role-card">
        <header>
          <div>
            <h3>{{ app.title }} <a-tag>{{ app.app_id }}</a-tag></h3>
            <p>{{ app.scope_note }}</p>
          </div>
          <a-button v-if="canEdit() && editing !== app.app_id" :disabled="busy" @click="start(app)">调整原生角色</a-button>
        </header>
        <p class="current">当前：{{ app.current.length ? app.current.join('、') : '无' }}</p>
        <a-alert v-if="!state.can_grant || !state.scope_envelope" type="info" show-icon :message="state.scope_envelope ? state.grant_requirement : '当前员工没有唯一、可核验的公司范围包络（Company User Permission），本轮不能授予 GLOBAL 原生角色。'" />
        <p class="envelope">范围包络：{{ state.scope_envelope ? `公司 ${state.scope_envelope.company}（来自 ${state.scope_envelope.source}）` : '未取得唯一公司包络' }}</p>
        <template v-if="editing === app.app_id">
          <a-alert v-if="app.roles.some(role => role.native_scope === 'GLOBAL')" type="warning" show-icon message="本轮登记角色均为 GLOBAL：进入仓储后按 Frappe 原生权限判断，不能在本页限定公司或仓库范围。" />
          <OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" />
          <div v-for="role in app.roles" :key="role.role" class="role-option">
            <a-checkbox :checked="selected.includes(role.role)" :disabled="busy" @change="toggleRole(role.role)">
              {{ role.title }}（{{ role.role }}）
            </a-checkbox>
            <small>{{ role.summary }}</small>
            <small class="warn">原生范围：{{ role.native_scope }}。{{ role.permissions_note }}</small>
          </div>
          <div class="acknowledge">
            <a-checkbox v-model:checked="acknowledged" :disabled="busy">我确认该原生角色为 GLOBAL，无法按公司/仓库限制；本次授予由站点级授权人显式承担范围风险。</a-checkbox>
          </div>
          <details v-if="app.blocked.length"><summary>本轮不开放的角色</summary><p v-for="row in app.blocked" :key="row.role">{{ row.role }}：{{ row.reason }}</p></details>
          <a-alert v-if="actionError" class="action-error" type="warning" show-icon :message="actionError" />
          <div class="actions">
            <a-button :disabled="busy" @click="cancel">取消</a-button>
            <a-button type="primary" :loading="busy" :disabled="busy || !acknowledged" @click="prepare">预览变更</a-button>
          </div>
          <section v-if="preview" class="preview" aria-live="polite">
            <h4>保存后的差异</h4>
            <p>新增：{{ preview.add.length ? preview.add.join('、') : '无' }}；撤销：{{ preview.remove.length ? preview.remove.join('、') : '无' }}；保留其他角色 {{ preview.other_roles_preserved.length }} 项。</p>
            <p>{{ preview.scope_note }}</p>
            <a-button :disabled="busy" @click="preview = null">返回修改</a-button>
            <a-button type="primary" :loading="busy" :disabled="!passwordProof() || !preview.changed || !acknowledged" @click="commit">确认保存</a-button>
            <p v-if="!passwordProof()" class="aux">保存需要本人数密码验证；飞书验证不能替代。</p>
          </section>
        </template>
      </article>
    </template>
  </section>
</template>
<style scoped>
.native-app-roles{display:grid;gap:16px;font-size:16px}
.app-role-card{border:1px solid var(--hbos-border-subtle);border-radius:12px;padding:16px;display:grid;gap:12px}
.app-role-card header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}
.app-role-card h3{margin:0 0 6px;font-size:16px}
.app-role-card p{margin:0;line-height:1.6}
.role-option,.acknowledge{display:grid;gap:4px;margin:8px 0}
.role-option small{color:var(--hbos-text-secondary);font-size:14px}
.role-option .warn{color:var(--hbos-warning-text,#a15c00)}
.envelope{font-size:14px;color:var(--hbos-text-secondary)}
.actions{display:flex;gap:12px}
.preview{border:1px solid var(--hbos-border-strong);border-radius:10px;padding:16px}
.preview h4{margin:0 0 8px}
.preview .ant-btn{margin-right:12px}
.aux{font-size:14px;color:var(--hbos-text-secondary)}
@media(max-width:700px){.app-role-card header{flex-direction:column}}
</style>
