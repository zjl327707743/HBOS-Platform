<script setup lang="ts">
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { canIam, iamMessage } from '@/services/iamAccess'
import { describeAppRoles, previewAppRoles, saveAppRoles, type AppRoleApp, type AppRolePreview, type AppRoleState } from '@/services/iamAppRoles'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import { useAccountProof } from '@/composables/useAccountProof'
const props = defineProps<{ employeeId: string }>()
const emit = defineEmits<{ saved: [] }>()
const state = ref<AppRoleState | null>(null), loading = ref(true), busy = ref(false), error = ref('')
const editing = ref<string | null>(null), selected = ref<string[]>([]), preview = ref<AppRolePreview | null>(null)
const acknowledged = ref(false)
const proof = useAccountProof(() => { preview.value = null })
let generation = 0
const canEdit = () => canIam('iam.access.manage') && state.value?.can_grant === true
async function load(preserve = false) {
  const run = ++generation
  loading.value = true; error.value = ''
  try {
    const next = await describeAppRoles(props.employeeId)
    if (run !== generation) return
    state.value = next
    if (!preserve) { editing.value = null; selected.value = []; preview.value = null; acknowledged.value = false }
  } catch (e) { if (run === generation) { state.value = null; error.value = iamMessage(e) } }
  finally { if (run === generation) loading.value = false }
}
function start(app: AppRoleApp) { editing.value = app.app_id; selected.value = [...app.current]; preview.value = null; acknowledged.value = false; error.value = '' }
function cancel() { editing.value = null; selected.value = []; preview.value = null; acknowledged.value = false; proof.invalidate() }
async function prepare() {
  if (busy.value || !state.value || !editing.value || !acknowledged.value) return
  busy.value = true; error.value = ''
  try {
    preview.value = await previewAppRoles(props.employeeId, editing.value, selected.value, state.value.version, acknowledged.value)
  } catch (e) { error.value = iamMessage(e); preview.value = null }
  finally { busy.value = false }
}
async function commit() {
  if (busy.value || !state.value || !editing.value || !preview.value || !proof.valid.value || !acknowledged.value) return
  busy.value = true; error.value = ''
  try {
    await saveAppRoles(props.employeeId, editing.value, selected.value, state.value.version, preview.value.context_revision, crypto.randomUUID(), acknowledged.value)
    proof.invalidate(); editing.value = null; selected.value = []; preview.value = null; acknowledged.value = false
    message.success('应用角色已保存，其他应用权限和账号状态保持不变。')
    await load(); emit('saved')
  } catch (e) { error.value = iamMessage(e); preview.value = null }
  finally { busy.value = false }
}
watch(() => props.employeeId, () => load(), { immediate: true })
</script>
<template>
  <section class="native-app-roles">
    <a-skeleton v-if="loading" active />
    <a-alert v-else-if="error" :message="error" type="warning" show-icon />
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
        <a-alert v-if="!state.can_grant" type="info" show-icon :message="state.grant_requirement" />
        <p class="envelope">范围包络：{{ state.scope_envelope ? `公司 ${state.scope_envelope.company}（来自 ${state.scope_envelope.source}）` : '无法证明唯一公司包络，页面不会允许授予' }}</p>
        <template v-if="editing === app.app_id">
          <a-alert type="warning" show-icon message="本轮登记角色均为 GLOBAL：进入仓储后按 Frappe 原生权限判断，不能在本页限定公司或仓库范围。" />
          <OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" />
          <label v-for="role in app.roles" :key="role.role" class="role-option">
            <a-checkbox :checked="selected.includes(role.role)" :disabled="busy" @change="selected = selected.includes(role.role) ? selected.filter(r => r !== role.role) : [...selected, role.role]">
              {{ role.title }}（{{ role.role }}）
            </a-checkbox>
            <small>{{ role.summary }}</small>
            <small class="warn">原生范围：{{ role.native_scope }}。{{ role.permissions_note }}</small>
          </label>
          <label class="acknowledge">
            <a-checkbox v-model:checked="acknowledged" :disabled="busy">我确认该原生角色为 GLOBAL，无法按公司/仓库限制；本次授予由站点级授权人显式承担范围风险。</a-checkbox>
          </label>
          <details v-if="app.blocked.length"><summary>本轮不开放的角色</summary><p v-for="row in app.blocked" :key="row.role">{{ row.role }}：{{ row.reason }}</p></details>
          <div class="actions">
            <a-button :disabled="busy" @click="cancel">取消</a-button>
            <a-button type="primary" :loading="busy" :disabled="busy || !acknowledged" @click="prepare">预览变更</a-button>
          </div>
          <section v-if="preview" class="preview" aria-live="polite">
            <h4>保存后的差异</h4>
            <p>新增：{{ preview.add.length ? preview.add.join('、') : '无' }}；撤销：{{ preview.remove.length ? preview.remove.join('、') : '无' }}；保留其他角色 {{ preview.other_roles_preserved.length }} 项。</p>
            <p>{{ preview.scope_note }}</p>
            <a-button :disabled="busy" @click="preview = null">返回修改</a-button>
            <a-button type="primary" :loading="busy" :disabled="!proof.valid.value || !preview.changed || !acknowledged" @click="commit">确认保存</a-button>
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
