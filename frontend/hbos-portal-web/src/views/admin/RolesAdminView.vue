<script setup lang="ts">
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { computed, onBeforeUnmount, onDeactivated, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { Modal, message } from 'ant-design-vue'
import { TeamOutlined, UserOutlined, CalendarOutlined, CheckCircleFilled, MinusCircleOutlined, SearchOutlined, EditOutlined } from '@ant-design/icons-vue'
import { canIam, iamMessage } from '@/services/iamAccess'
import { loadRoles, roleCommand, assertRolePreview, type AppRole, type RolePreview } from '@/services/iamRoles'
import { roleFeatureKey, sameRoleFeatures, roleScopeLabel, roleGroups } from '@/services/rolePresentation'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import PanelFrame from '@/components/iam/PanelFrame.vue'
import ChangeReview from '@/components/iam/ChangeReview.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import { useAccountProof } from '@/composables/useAccountProof'
const items = ref<AppRole[]>([]), selected = ref('clerk'), loading = ref(true), busy = ref(false), error = ref(''), editing = ref(false), checked = ref<string[]>([]), preview = ref<RolePreview | null>(null), restore = ref(''), versionTab = ref('published'), search = ref(''), mustRead = ref(false)
const role = computed(() => items.value.find(row => row.role_key === selected.value)), proof = useAccountProof(() => { preview.value = null })
const dirty = computed(() => editing.value && JSON.stringify([...checked.value].sort()) !== JSON.stringify(role.value?.draft_features.map(roleFeatureKey).sort()))
const unpublished = computed(() => Boolean(role.value && !sameRoleFeatures(role.value.draft_features, role.value.published_features)))
const displayed = computed(() => role.value ? editing.value ? checked.value : (versionTab.value === 'draft' ? role.value.draft_features : role.value.published_features).map(roleFeatureKey) : [])
const featureGroups = computed(() => {
  const registry = role.value?.registry || [], knownGroups = roleGroups.map(([key, title]) => ({ key, title })) as Array<{key: string; title: string}>
  for (const item of registry) if (!knownGroups.some(group => group.key === item.group)) knownGroups.push({ key: item.group, title: '其他已登记功能' })
  return knownGroups.map(group => ({ ...group, rows: registry.filter(row => row.allowed && row.group === group.key && (!search.value || row.title.toLowerCase().includes(search.value.toLowerCase()))) })).filter(group => group.rows.length)
})
const descriptions: Record<string, string> = { staff: '查看自己的考勤', clerk: '协助负责部门核对日常考勤', admin: '在明确获准的公司内办理考勤管理' }
const icons = { staff: UserOutlined, clerk: TeamOutlined, admin: CalendarOutlined }
const added = computed(() => role.value?.draft_features.filter(row => !role.value?.published_features.some(before => roleFeatureKey(before) === roleFeatureKey(row))) || [])
const removed = computed(() => role.value?.published_features.filter(row => !role.value?.draft_features.some(after => roleFeatureKey(after) === roleFeatureKey(row))) || [])
let generation = 0, disposed = false, requestId = ''
function reset() { checked.value = role.value?.draft_features.map(roleFeatureKey) || []; preview.value = null; restore.value = ''; requestId = '' }
async function load(preserve = false) {
  const run = ++generation; loading.value = true; error.value = ''
  try { const result = await loadRoles(); if (disposed || run !== generation) return; items.value = result; if (!items.value.some(row => row.role_key === selected.value)) selected.value = items.value[0]?.role_key || ''; if (!preserve) reset(); preview.value = null; mustRead.value = false }
  catch (e) { if (!disposed && run === generation) error.value = iamMessage(e) }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function leave() { if (busy.value) return false; if (!dirty.value) return true; return new Promise<boolean>(resolve => Modal.confirm({ title: '放弃尚未保存的角色草稿？', okText: '放弃草稿', cancelText: '继续编辑', onOk: () => { editing.value = false; reset(); resolve(true) }, onCancel: () => resolve(false) })) }
async function cancelEdit() { if (await leave()) { editing.value = false; reset() } }
async function select(key: string) { if (!await leave()) return; selected.value = key; editing.value = false; versionTab.value = 'published'; reset(); proof.invalidate() }
function toggle(key: string) { checked.value = checked.value.includes(key) ? checked.value.filter(value => value !== key) : [...checked.value, key]; preview.value = null }
async function save() {
  if (!role.value || busy.value || mustRead.value || !proof.valid.value || !canIam('iam.roles.edit') || !dirty.value) return
  busy.value = true; error.value = ''; requestId ||= crypto.randomUUID()
  try { await roleCommand('save_role_draft', { role_key: selected.value, expected_draft_version: role.value.draft_version, features: role.value.registry.filter(row => checked.value.includes(roleFeatureKey(row))).map(({ operation_id, scope_binding }) => ({ operation_id, scope_binding })), request_id: requestId }); editing.value = false; proof.invalidate(); await load(); versionTab.value = 'draft'; message.success('草稿已保存，员工现有权限尚未改变。') }
  catch (e) { error.value = iamMessage(e); mustRead.value = true; proof.invalidate() }
  finally { busy.value = false }
}
async function prepare() {
  if (!role.value || busy.value || mustRead.value || !unpublished.value || !canIam('iam.roles.publish')) return
  busy.value = true; error.value = ''; proof.invalidate()
  try { preview.value = assertRolePreview(await roleCommand<RolePreview>('preview_role_publish', { role_key: selected.value, expected_draft_version: role.value.draft_version, expected_release: role.value.published_release })); requestId = crypto.randomUUID() }
  catch (e) { error.value = iamMessage(e) }
  finally { busy.value = false }
}
async function publish() {
  if (!role.value || !preview.value || busy.value || mustRead.value || !proof.valid.value || !canIam('iam.roles.publish')) return
  busy.value = true; error.value = ''
  try { await roleCommand('publish_role', { role_key: selected.value, expected_draft_version: role.value.draft_version, expected_release: role.value.published_release, context_revision: preview.value.context_revision, request_id: requestId }); proof.invalidate(); await load(); versionTab.value = 'published'; message.success('角色已发布，后续请求使用新版本。') }
  catch (e) { error.value = iamMessage(e); mustRead.value = true; proof.invalidate(); preview.value = null }
  finally { busy.value = false }
}
async function restoreDraft() {
  if (!role.value || !restore.value || busy.value || mustRead.value || !proof.valid.value || !canIam('iam.roles.edit')) return
  busy.value = true; error.value = ''; requestId ||= crypto.randomUUID()
  try { await roleCommand('restore_role_release', { role_key: selected.value, source_release: restore.value, expected_draft_version: role.value.draft_version, request_id: requestId }); editing.value = false; proof.invalidate(); await load(); versionTab.value = 'draft'; message.success('历史内容已恢复为草稿，请核对影响后发布。') }
  catch (e) { error.value = iamMessage(e); mustRead.value = true; proof.invalidate() }
  finally { busy.value = false }
}
// KeepAlive retains the same subject's unsaved draft across workspace/app tabs.
// A role change or explicit cancel still asks before discarding it.
onBeforeRouteLeave(() => !busy.value)
onDeactivated(() => { proof.invalidate(); preview.value = null; requestId = '' })
onMounted(() => load())
onBeforeUnmount(() => { disposed = true; generation++; proof.invalidate(); checked.value = []; preview.value = null })
useManagementViewMemory('RolesAdminView.vue', { selected, versionTab, search })
</script>
<template>
  <section class="r6-page r6-roles-page">
    <PageHeading eyebrow="应用管理" title="角色与权限" description="定义每个角色能做什么，再将角色安排给合适的同事。" />
    <div v-if="error" class="r6-resource-error"><a-alert :message="error" type="warning" show-icon /><a-button :disabled="busy" @click="load(editing)">核对服务端结果，保留编辑</a-button></div>
    <a-skeleton v-if="loading" active />
    <div v-else class="r6-dual-panels">
      <PanelFrame as="aside" region="role-navigation" label="应用与角色模板" class="r6-navigation">
        <template #header><p class="aux">选择应用</p><a-select value="attendance" aria-label="角色所属应用"><a-select-option value="attendance">考勤管理</a-select-option></a-select><p class="aux" style="margin:20px 0 0">角色模板 · {{ items.length }}</p></template>
        <div class="r6-choice-list"><button v-for="item in items" :key="item.role_key" :disabled="busy" :aria-pressed="selected === item.role_key" @click="select(item.role_key)"><span class="r6-choice-icon"><component :is="icons[item.role_key as keyof typeof icons] || UserOutlined" /></span><span><strong>{{ item.title }}</strong><small>{{ item.boundary_kind === 'SELF' ? '仅本人' : item.boundary_kind === 'DEPARTMENT' ? '指定部门' : '指定公司' }}</small></span></button></div>
        <template #footer>角色定义功能，员工设置负责范围。</template>
      </PanelFrame>
      <PanelFrame v-if="role" region="role-detail" label="角色功能与职责">
        <template #header><div class="r6-role-head"><div><h2>{{ role.title }}</h2><p>{{ descriptions[role.role_key] || '按注册的功能与范围安排工作' }}</p></div><a-button v-if="canIam('iam.roles.edit') && !editing" :disabled="busy || mustRead" @click="reset(); editing = true; versionTab = 'draft'"><EditOutlined />编辑功能</a-button></div><div class="r6-role-boundary"><span>可查看：{{ role.boundary_kind === 'SELF' ? '仅本人' : role.boundary_kind === 'DEPARTMENT' ? '明确负责的部门' : '明确负责的一个公司' }}</span><span v-if="role.boundary_kind === 'DEPARTMENT'">不包含下级部门</span></div><div class="r6-role-versions"><a-button :aria-pressed="versionTab === 'published' && !editing" :disabled="editing" @click="versionTab = 'published'">当前生效</a-button><a-button :aria-pressed="versionTab === 'draft' || editing" :disabled="editing" @click="versionTab = 'draft'">待发布修改 <span v-if="unpublished"> · 有变更</span></a-button><span>{{ versionTab === 'published' && !editing ? role.published_revision ? `生效版本 v${role.published_revision}` : '尚无发布版本' : `草稿 v${role.draft_version} · 尚未影响员工` }}</span></div></template>
        <div class="r6-feature-toolbar"><h3>功能与职责 <small class="aux">{{ displayed.length }} 项已启用</small></h3><a-input v-model:value="search" allow-clear placeholder="搜索功能" aria-label="搜索角色功能"><template #prefix><SearchOutlined /></template></a-input></div>
        <a-alert v-if="editing" type="info" show-icon message="修改先保存为草稿，不改变当前员工权限。发布前需再次核对实际影响。" />
        <a-alert v-if="role.registry.some(row => row.allowed && !row.integrated)" type="info" show-icon message="部分功能仍在接入。清单保留全部功能，包含待接入功能的草稿不能发布。" />
        <div class="r6-feature-groups"><details v-for="group in featureGroups" :key="group.key" class="r6-feature-group" open><summary>{{ group.title }}<small>{{ group.rows.filter(row => displayed.includes(roleFeatureKey(row))).length }} / {{ group.rows.length }}</small></summary><div v-for="row in group.rows" :key="roleFeatureKey(row)" class="r6-feature-row"><a-checkbox v-if="editing" :checked="checked.includes(roleFeatureKey(row))" :disabled="busy || mustRead || !row.allowed" @change="toggle(roleFeatureKey(row))">{{ row.title }}</a-checkbox><div v-else class="r6-feature-read" :class="{ 'is-off': !displayed.includes(roleFeatureKey(row)) }"><CheckCircleFilled v-if="displayed.includes(roleFeatureKey(row))" /><MinusCircleOutlined v-else /><span>{{ row.title }}</span><span>{{ displayed.includes(roleFeatureKey(row)) ? '已启用' : '未启用' }}</span></div><small>{{ !row.allowed ? '超过此角色上限' : !row.integrated ? row.reason : roleScopeLabel(row.scope_binding) }}</small></div></details></div>
        <a-empty v-if="!featureGroups.length" description="没有匹配的功能" /><details v-if="role.registry.some(row => !row.allowed)" class="r6-profile-tools"><summary>不在此角色范围内的功能</summary><p v-for="row in role.registry.filter(item => !item.allowed)" :key="roleFeatureKey(row)" class="aux">{{ row.title }} · 超过此角色上限</p></details>
        <OwnAccountVerification v-if="editing && canIam('iam.roles.edit')" password-only @verified="proof.sync" @invalidated="proof.invalidate" />
        <ChangeReview :open="Boolean(preview)" :busy="busy" title="核对角色发布影响" @cancel="preview = null; proof.invalidate()"><section v-if="preview" aria-live="polite"><h3>发布影响</h3><p>新增 {{ added.length }} 项功能；移除 {{ removed.length }} 项功能。</p><p>引用该角色 {{ preview.reference_count }} 人；实际权限变化 {{ preview.effective_changed_count }} 人。</p><p v-for="person in preview.members" :key="person.employee">{{ person.name }}：{{ person.changed ? '权限将变化' : '当前实际权限保持' }}{{ person.reason ? '，' + person.reason : '' }}</p><OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" /><a-space wrap><a-button :disabled="busy" @click="preview = null; proof.invalidate()">取消发布</a-button><a-button type="primary" :loading="busy" :disabled="!proof.valid.value || !preview.changed || mustRead" @click="publish">确认发布</a-button></a-space></section></ChangeReview>
        <details v-if="role.releases.length && canIam('iam.roles.edit')" class="r6-profile-tools"><summary>从历史发布内容恢复草稿</summary><OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" /><a-select v-model:value="restore" aria-label="历史发布版本" style="width:100%" @change="requestId = ''"><a-select-option v-for="release in role.releases" :key="release.name" :value="release.name">v{{ release.revision }} · {{ release.published_at }}</a-select-option></a-select><a-button :disabled="!restore || !proof.valid.value || busy || mustRead" @click="restoreDraft">恢复为草稿</a-button><p class="aux">恢复仍需重新预览、确认发布才改变员工权限。</p></details>
        <template #footer><div class="r6-role-foot"><StatusTag :tone="unpublished ? 'warning' : 'success'">{{ editing ? '正在修改草稿' : unpublished ? '有待发布修改' : role.published_revision ? '当前安排已发布' : '尚未发布' }}</StatusTag><a-space wrap><template v-if="editing"><a-button :disabled="busy" @click="cancelEdit">取消修改</a-button><a-button type="primary" :loading="busy" :disabled="!dirty || !proof.valid.value || mustRead" @click="save">保存草稿</a-button></template><a-button v-else-if="canIam('iam.roles.publish')" :disabled="!unpublished || mustRead" :loading="busy" @click="prepare">预览发布影响</a-button></a-space></div></template>
      </PanelFrame>
      <a-empty v-else description="暂无获准查看的角色" />
    </div>
  </section>
</template>
