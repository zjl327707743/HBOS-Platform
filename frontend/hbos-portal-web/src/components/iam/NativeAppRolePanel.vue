<script setup lang="ts">
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { Modal } from 'ant-design-vue'
import { canIam, iamMessage, iamSession } from '@/services/iamAccess'
import { describeAppRoles, previewAppRoles, saveAppRoles, type AppRoleApp, type AppRolePreview, type AppRoleState } from '@/services/iamAppRoles'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { useAccountProof } from '@/composables/useAccountProof'
const props = defineProps<{ employeeId: string }>()
const emit = defineEmits<{ saved: [] }>()
const state = ref<AppRoleState | null>(null), loading = ref(true), busy = ref(false)
// A failed read must not destroy an open editor; a failed preview/save must not
// replace the whole panel. Keep the two failure surfaces separate.
const loadError = ref(''), actionError = ref('')
const editing = ref<string | null>(null), selected = ref<string[]>([]), preview = ref<AppRolePreview | null>(null)
const acknowledged = ref(false)
const proof = useAccountProof(() => { preview.value = null })
// One request id per edit intent: a retry after a timeout must be replayable.
const requestId = ref('')
let generation = 0
const canManage = () => canIam('iam.access.manage')
const canGrant = () => state.value?.can_grant === true && Boolean(state.value?.scope_envelope)
/** Self-targeting is refused by the write path, so it must not look editable. */
const isSelf = () => Boolean(state.value?.user) && state.value?.user === iamSession.user
/** Grant needs an explicit grantor + proven envelope; revocation never does. */
const canEdit = (app: AppRoleApp) => canManage() && !isSelf() && (canGrant() || app.current.length > 0)
const canSelect = (app: AppRoleApp, role: { role: string; native_scope: string }) =>
  canGrant() || app.current.includes(role.role)
const passwordProof = () => proof.valid.value && proof.method.value === 'password'
const editingApp = () => state.value?.apps.find(app => app.app_id === editing.value) || null
const selectedGrants = () => {
  const app = editingApp()
  if (!app) return []
  return app.roles.filter(role => selected.value.includes(role.role) && !app.current.includes(role.role))
}
/** Mirrors the server gate: any grant in an app that registers a GLOBAL role
 *  needs the explicit scope acknowledgement, even when the added role is scoped. */
const needsAck = () => {
  const app = editingApp()
  if (!app || !selectedGrants().length) return false
  return app.roles.some(role => role.native_scope === 'GLOBAL')
}
const ackText = () => {
  const app = editingApp()
  const global = (app?.roles || []).filter(role => role.native_scope === 'GLOBAL').map(role => role.role)
  const granted = selectedGrants().filter(role => role.native_scope === 'GLOBAL').map(role => role.role)
  return granted.length
    ? `我确认 ${granted.join('、')} 为 GLOBAL 原生角色，无法按公司/仓库限制；本次授予由站点级授权人显式承担范围风险。`
    : `我知悉该应用登记了 ${global.join('、')} 等 GLOBAL 原生角色（无法按公司/仓库限制）；本次新增角色随该应用一并生效，范围风险由站点级授权人显式承担。`
}
async function load(options: { resync?: boolean } = {}) {
  const run = ++generation
  loading.value = true; loadError.value = ''
  try {
    const next = await describeAppRoles(props.employeeId)
    if (run !== generation) return
    state.value = next
    const edited = next.apps.find(app => app.app_id === editing.value)
    if (editing.value && !edited) cancel()
    else if (edited && options.resync) {
      // Only a conflict reload invalidates the intent: the selection was captured
      // against the previous current/version, and keeping it would silently turn
      // a concurrent grant into a removal. A plain retry keeps the draft.
      selected.value = [...edited.current]; preview.value = null
      acknowledged.value = false; requestId.value = ''
      actionError.value = '已重新读取最新角色状态，此前的未保存选择已作废，请重新勾选并预览。'
    }
  } catch (e) {
    // Keep the last good state (and the open editor) for rendering; surface the
    // failure without pretending the editor is still based on fresh data.
    if (run === generation) loadError.value = iamMessage(e)
  } finally { if (run === generation) loading.value = false }
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
  // A different role set is a different intent: drop the stale preview and the
  // idempotency key, otherwise a replay of the previous payload is rejected.
  preview.value = null; requestId.value = ''; actionError.value = ''
  // Any change of the selected role set invalidates the previous consent (the
  // text names the roles). Re-tick the box for the new intent.
  acknowledged.value = false
}
async function prepare() {
  if (busy.value || !state.value || !editing.value) return
  if (needsAck() && !acknowledged.value) { actionError.value = '授予 GLOBAL 原生角色前，需要显式确认范围风险。'; return }
  busy.value = true; actionError.value = ''
  try {
    preview.value = await previewAppRoles(props.employeeId, editing.value, selected.value, state.value.version, needsAck() ? acknowledged.value : false)
    if (!preview.value.changed) actionError.value = '所选角色与当前一致，无需保存。'
  } catch (e) {
    actionError.value = iamMessage(e); preview.value = null
    const conflict = e as { status?: number; code?: string }
    const retryable = conflict.code === 'READ_CONFLICT' || /正在完成另一项管理操作|稍后重试/.test(String((e as Error)?.message || ''))
    if (conflict.status === 409 && !retryable) {
      // The preview context can only be rebuilt from a fresh read; the retained
      // request id no longer matches the new payload anyway.
      requestId.value = ''
      await load({ resync: true })
    }
  } finally { busy.value = false }
}
async function commit() {
  if (busy.value || !state.value || !editing.value || !preview.value) return
  if (needsAck() && !acknowledged.value) { actionError.value = '授予 GLOBAL 原生角色前，需要显式确认范围风险。'; return }
  if (!passwordProof()) { actionError.value = '保存需要本人数密码验证（飞书验证不能替代），请在上方重新验证。'; return }
  busy.value = true; actionError.value = ''
  try {
    requestId.value ||= crypto.randomUUID()
    // The preview is the authoritative read: use its version, not the one read
    // when the drawer opened.
    await saveAppRoles(props.employeeId, editing.value, selected.value, preview.value.version, preview.value.context_revision, requestId.value, needsAck() ? acknowledged.value : false)
    proof.invalidate(); editing.value = null; selected.value = []; preview.value = null; acknowledged.value = false; requestId.value = ''
    message.success('应用角色已保存，其他应用权限和账号状态保持不变。')
    // Reload the panel's own read model so `current`/`version` are fresh even if
    // the parent keeps this mounted; emit for the drawer's own refresh.
    await load(); emit('saved')
  } catch (e) {
    const conflict = e as { status?: number; code?: string }
    // A retryable 409 (contention / read conflict) is not a stale intent: keep
    // the draft. Only a real version/preview mismatch invalidates the selection.
    const retryable = conflict.code === 'READ_CONFLICT' || /正在完成另一项管理操作|稍后重试/.test(String((e as Error)?.message || ''))
    // The transport rewrites CONFLICT to VALIDATION_ERROR while keeping 409, so
    // "non-retryable 409" is the reliable staleness signal here (same rule as prepare()).
    const stale = conflict.status === 409 && !retryable
    const inconclusive = !stale && !retryable && (!conflict.status || conflict.status >= 500 || ['NETWORK_ERROR', 'SERVICE_ERROR', 'RATE_LIMITED'].includes(conflict.code || ''))
    actionError.value = inconclusive
      ? `${iamMessage(e)}（结果尚未确认：请重新验证本人密码后再次预览并提交，同一请求编号会被复用以免重复授权。）`
      : iamMessage(e)
    if (inconclusive || retryable) {
      // Keep preview + id: an identical retry can be collapsed by the server.
      if (inconclusive) proof.invalidate()
    } else {
      preview.value = null; requestId.value = ''
      if (stale) await load({ resync: true })
    }
  } finally { busy.value = false }
}
function dirty () {
  const app = editingApp()
  if (!app) return false
  return preview.value !== null || acknowledged.value || JSON.stringify([...selected.value].sort()) !== JSON.stringify([...app.current].sort())
}
async function requestLeave () {
  if (busy.value) return false
  if (!dirty()) return true
  return new Promise<boolean>(resolve => Modal.confirm({
    title: '放弃尚未保存的原生角色调整？',
    content: '已保存的角色和其他应用权限不受影响。',
    okText: '放弃调整', cancelText: '继续编辑',
    onOk: () => resolve(true), onCancel: () => resolve(false),
  }))
}
watch(() => props.employeeId, () => { cancel(); void load() }, { immediate: true })
defineExpose({ requestLeave, busy })
</script>
<template>
  <section class="native-app-roles">
    <a-alert v-if="loadError" class="load-error" type="warning" show-icon :message="loadError" />
    <a-button v-if="loadError" :disabled="busy" @click="load()">重新读取</a-button>
    <a-skeleton v-if="loading && !state" active />
    <template v-if="state">
      <p class="aux">这里只调整已登记的跨应用原生角色；考勤角色、账号状态和其他应用授权不受影响。</p>
      <article v-for="app in state.apps" :key="app.app_id" class="app-role-card">
        <header>
          <div>
            <h3>{{ app.title }} <a-tag>{{ app.app_id }}</a-tag></h3>
            <p>{{ app.scope_note }}</p>
          </div>
          <a-button v-if="canEdit(app) && editing !== app.app_id" :disabled="busy" @click="start(app)">调整原生角色</a-button>
        </header>
        <p class="current">当前：{{ app.current.length ? app.current.join('、') : '无' }}</p>
        <a-alert v-if="isSelf()" type="info" show-icon message="不能为自己的账号调整原生角色；此页对本人只读。" />
        <a-alert v-else-if="!state.can_grant || !state.scope_envelope" type="info" show-icon :message="state.scope_envelope ? state.grant_requirement : '当前员工没有唯一、可核验的公司范围包络（Company User Permission）；可以撤销既有角色，但不能新增 GLOBAL 原生角色。'" />
        <p class="envelope">范围包络：{{ state.scope_envelope ? `公司 ${state.scope_envelope.company}（来自 ${state.scope_envelope.source}）` : '未取得唯一公司包络' }}</p>
        <template v-if="editing === app.app_id">
          <a-alert v-if="app.roles.some(role => role.native_scope === 'GLOBAL')" type="warning" show-icon message="本轮登记角色均为 GLOBAL：进入仓储后按 Frappe 原生权限判断，不能在本页限定公司或仓库范围。" />
          <OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" />
          <div v-for="role in app.roles" :key="role.role" class="role-option">
            <a-checkbox :checked="selected.includes(role.role)" :disabled="busy || !canSelect(app, role)" @change="toggleRole(role.role)">
              {{ role.title }}（{{ role.role }}）
            </a-checkbox>
            <small>{{ role.summary }}</small>
            <small class="warn">原生范围：{{ role.native_scope }}。{{ role.permissions_note }}</small>
          </div>
          <div v-if="needsAck()" class="acknowledge">
            <a-checkbox v-model:checked="acknowledged" :disabled="busy">{{ ackText() }}</a-checkbox>
          </div>
          <details v-if="app.blocked.length"><summary>本轮不开放的角色</summary><p v-for="row in app.blocked" :key="row.role">{{ row.role }}：{{ row.reason }}</p></details>
          <a-alert v-if="actionError" class="action-error" type="warning" show-icon :message="actionError" />
          <div class="actions">
            <a-button :disabled="busy" @click="cancel">取消</a-button>
            <a-button type="primary" :loading="busy" :disabled="busy || (needsAck() && !acknowledged)" @click="prepare">预览变更</a-button>
          </div>
          <section v-if="preview" class="preview" aria-live="polite">
            <h4>保存后的差异</h4>
            <p>新增：{{ preview.add.length ? preview.add.join('、') : '无' }}；撤销：{{ preview.remove.length ? preview.remove.join('、') : '无' }}；保留其他角色 {{ preview.other_roles_preserved.length }} 项。</p>
            <p>{{ preview.scope_note }}</p>
            <a-button :disabled="busy" @click="preview = null">返回修改</a-button>
            <a-button type="primary" :loading="busy" :disabled="!passwordProof() || !preview.changed || (needsAck() && !acknowledged)" @click="commit">确认保存</a-button>
            <p v-if="!passwordProof()" class="aux">保存需要本人数密码验证；飞书验证不能替代。</p>
          </section>
        </template>
      </article>
    </template>
  </section>
</template>
<style scoped>
.native-app-roles{display:grid;gap:16px;font-size:16px}
.load-error{margin-bottom:4px}
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
