<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { state, ui, isAdmin, saveDemo, deptName, scopeLabel } from '../model'
import { evaluatePermission } from '../permission'

const selectedId = ref('d1')
const selectedDept = computed(() => state.depts.find(dept => dept.id === selectedId.value))
const primaryMembers = computed(() => state.employees.filter(employee => employee.departmentId === selectedId.value))
const secondaryMembers = computed(() => state.employees.filter(employee => employee.secondaryDepartments?.includes(selectedId.value)))
const tree = computed(() => [{ title: '演示组织', key: 'demo', selectable: false, children: [
  ...state.depts.map(dept => ({ title: dept.name, key: dept.id })),
  { title: '新产品项目协同与技术支持中心（未映射）', key: 'unmapped' },
] }])
const statusInfo = status => ({ active: ['已开通', 'green'], pending: ['待核验 / 未开通', 'orange'], disabled: ['已停用', 'default'] }[status] || ['待核对', 'default'])
const modalOpen = ref(false)
const draftApp = ref('attendance')
const draftAction = ref('*')
const draftMode = ref('allow')
const draftScopes = ref([])
const previewed = ref(false)
const activeApp = computed(() => state.apps.find(app => app.id === draftApp.value))
const actionOptions = computed(() => [
  { value: '*', label: 'APP 整体进入权限' },
  ...(activeApp.value?.actions.filter(action => !action.highRisk).map(action => ({ value: action.id, label: action.name })) || []),
])
const presetRows = computed(() => state.apps.filter(app=>app.id!=='platform').flatMap(app => ['*', ...app.actions.filter(action => !action.highRisk).map(action => action.id)].map(actionId => {
  const rule = selectedDept.value?.presets?.[`${app.id}:${actionId}`]
  return { key: `${app.id}:${actionId}`, appId: app.id, appName: app.name, actionId, actionName: actionId === '*' ? 'APP 整体' : app.actions.find(action => action.id === actionId)?.name, mode: rule?.mode || 'unset', scope: rule?.scope || [] }
})))
const resultText = result => result.allowed ? `允许 · ${result.scope.map(scopeLabel).join('、')}` : `拒绝 · ${result.reason}`
const impact = computed(() => {
  if (!selectedDept.value || !activeApp.value) return []
  const nextState = JSON.parse(JSON.stringify(state))
  const nextDept = nextState.depts.find(dept => dept.id === selectedId.value)
  const key = `${draftApp.value}:${draftAction.value}`
  if (draftMode.value === 'unset') delete nextDept.presets[key]
  else nextDept.presets[key] = { mode: draftMode.value, scope: [...draftScopes.value] }
  const actions = draftAction.value === '*' ? ['*', ...activeApp.value.actions.map(action => action.id)] : [draftAction.value]
  return primaryMembers.value.flatMap(employee => actions.map(actionId => {
    const before = evaluatePermission(state, employee, draftApp.value, actionId)
    const after = evaluatePermission(nextState, nextState.employees.find(item => item.id === employee.id), draftApp.value, actionId)
    return { key: `${employee.id}:${actionId}`, name: employee.name, action: actionId === '*' ? 'APP 整体' : activeApp.value.actions.find(action => action.id === actionId)?.name, before, after, changed: before.allowed !== after.allowed || JSON.stringify(before.scope) !== JSON.stringify(after.scope) }
  }))
})
const changedPeople = computed(() => new Set(impact.value.filter(row => row.changed).map(row => row.name)).size)
const impactColumns = [
  { title: '具名员工 / 动作', key: 'employee', width: 150 },
  { title: '保存前', key: 'before' },
  { title: '保存后', key: 'after' },
  { title: '范围差异', key: 'diff', width: 180 },
]
function hydrateDraft() {
  const rule = selectedDept.value?.presets?.[`${draftApp.value}:${draftAction.value}`]
  draftMode.value = rule?.mode || 'unset'
  draftScopes.value = [...(rule?.scope || [])]
  previewed.value = false
}
watch(draftApp, () => { draftAction.value = '*'; hydrateDraft() }, { flush: 'sync' })
watch(draftAction, hydrateDraft, { flush: 'sync' })
watch([draftMode, draftScopes], () => { previewed.value = false }, { deep: true })
function openEditor(row) {
  draftApp.value = row?.appId || 'attendance'
  draftAction.value = row?.actionId || '*'
  hydrateDraft()
  modalOpen.value = true
}
function preview() {
  if (!isAdmin.value) return message.error('仅演示管理员可修改部门预设。')
  if (!selectedDept.value) return message.error('此节点尚未映射，不允许授权。')
  if (activeApp.value?.actions.find(action => action.id === draftAction.value)?.highRisk) return message.error('高风险动作不能通过部门预设授予。')
  previewed.value = true
}
async function savePreset() {
  if (!previewed.value || !isAdmin.value || !selectedDept.value) return
  const departmentId = selectedId.value
  const appId = draftApp.value
  const actionId = draftAction.value
  const mode = draftMode.value
  const scope = [...draftScopes.value]
  const result = await saveDemo(`调整${selectedDept.value.name}的${activeApp.value.name}部门预设（已预览影响）`, () => {
    if (!isAdmin.value) throw new Error('当前演示账号无管理权限。')
    const app = state.apps.find(item => item.id === appId)
    if (!app || app.id==='platform' || (actionId !== '*' && !app.actions.some(action => action.id === actionId && !action.highRisk))) throw new Error('部门预设只接受已注册的普通动作。')
    if ((mode === 'deny' && actionId !== '*' && !scope.length) || scope.some(value => !app.scopes.some(item => item.value === value))) throw new Error('数据范围已变化，请重新预览。')
    const department = state.depts.find(item => item.id === departmentId)
    if (!department) throw new Error('部门未映射，保存已拒绝。')
    if (mode === 'unset') delete department.presets[`${appId}:${actionId}`]
    else department.presets[`${appId}:${actionId}`] = { mode, scope: scope }
  })
  if (result.ok) { message.success('演示已保存到本机'); modalOpen.value = false }
  else message.error(result.error)
}
function difference(row) {
  const added = row.after.scope.filter(scope => !row.before.scope.includes(scope)).map(scopeLabel)
  const removed = row.before.scope.filter(scope => !row.after.scope.includes(scope)).map(scopeLabel)
  if (!row.changed) return '有效权限未变化'
  return [added.length && `增加：${added.join('、')}`, removed.length && `撤销：${removed.join('、')}`, !added.length && !removed.length && `${row.before.allowed ? '允许' : '拒绝'} → ${row.after.allowed ? '允许' : '拒绝'}`].filter(Boolean).join('；')
}
</script>

<template>
  <div class="departments-page stack">
    <div class="page-heading">
      <div><div class="kicker">ORGANIZATION</div><h1>部门与继承预设</h1><p class="muted">部门定义普通权限的起点；主岗继承，兼岗记录单独展示。</p></div>
      <a-tag color="green">全部为合成演示资料</a-tag>
    </div>
    <a-alert v-if="!isAdmin" type="info" show-icon message="当前为只读视图。使用演示管理员登录后，可调整部门权限预设。" />
    <div class="department-layout">
      <aside class="panel organization-panel">
        <div class="section-top"><h3>组织目录</h3><a-tag>{{ state.depts.length }} 个已映射部门</a-tag></div>
        <a-tree :tree-data="tree" :selected-keys="[selectedId]" :default-expanded-keys="['demo']" block-node @select="keys => { if (keys.length) selectedId = keys[0] }" />
        <div class="organization-foot">长名称完整展示。未映射节点保留待核对状态，不据此自动授权。</div>
      </aside>
      <main v-if="selectedDept" class="stack">
        <section class="panel department-summary">
          <div><div class="kicker">已映射 · 演示部门</div><h2>{{ selectedDept.name }}</h2><p class="muted">{{ selectedDept.description }}</p></div>
          <div class="member-count"><strong>{{ primaryMembers.length }}</strong><span>主岗成员</span></div>
        </section>
        <section class="panel">
          <div class="section-top"><h3>主岗成员</h3><span class="muted">普通权限由本部门继承</span></div>
          <div class="member-list">
            <div v-for="employee in primaryMembers" :key="employee.id" class="member-row">
              <div class="person-avatar">{{ employee.name.slice(0, 1) }}</div>
              <div class="person-main"><strong>{{ employee.name }}</strong><span>{{ employee.position }} · {{ employee.code }}</span></div>
              <a-tag :color="statusInfo(employee.status)[1]">{{ statusInfo(employee.status)[0] }}</a-tag>
            </div>
          </div>
          <div class="secondary-section">
            <div class="section-top"><h4>兼岗记录</h4><a-tag>不自动叠加部门权限</a-tag></div>
            <div v-if="secondaryMembers.length" class="secondary-list"><div v-for="employee in secondaryMembers" :key="employee.id"><strong>{{ employee.name }}</strong><span class="muted">主岗：{{ deptName(employee.departmentId) }} · 本部门兼岗</span></div></div>
            <a-empty v-else description="本部门暂无合成兼岗记录" />
          </div>
        </section>
        <section class="panel">
          <div class="section-top"><div><h3>普通权限预设</h3><p class="muted">APP 进入权限与动作、范围同时成立，员工才可以访问。</p></div><a-button type="primary" :disabled="!isAdmin" @click="openEditor()">调整预设</a-button></div>
          <div class="preset-list">
            <div v-for="row in presetRows" :key="row.key" class="preset-row">
              <div><strong>{{ row.appName }}</strong><span class="muted">{{ row.actionName }}</span></div>
              <a-tag :color="row.mode === 'allow' ? 'green' : row.mode === 'deny' ? 'red' : 'default'">{{ row.mode === 'allow' ? '允许' : row.mode === 'deny' ? '禁止' : '未授予' }}</a-tag>
              <span class="preset-scopes">{{ row.mode === 'allow' ? (row.scope.length ? row.scope.map(scopeLabel).join('、') : '空范围 · 有效结果拒绝') : '—' }}</span>
              <a-button type="link" :disabled="!isAdmin" @click="openEditor(row)">编辑</a-button>
            </div>
          </div>
          <a-alert class="rule-alert" type="warning" show-icon message="质量签署、重要调账、平台管理等高风险动作不能由部门自动授予。" description="请到个人权限页面，具名核验资格与领域范围后单独配置。" />
        </section>
      </main>
      <section v-else class="panel unmapped-state"><a-tag color="orange">待核对 / 只读</a-tag><h2>新产品项目协同与技术支持中心</h2><p>此合成节点没有对应的受控部门映射。成员、主兼岗及负责人需核对后才能进入导入候选。</p><a-alert type="warning" show-icon message="当前不会创建部门、迁移人员或自动授权。" /></section>
    </div>
    <a-modal v-model:open="modalOpen" title="调整部门普通权限预设" :width="940" :mask-closable="!ui.busy" :closable="!ui.busy" @cancel="previewed = false">
      <div class="preset-editor stack">
        <a-alert type="info" show-icon :message="`${selectedDept?.name} · 仅影响主岗普通继承；个人明确例外继续保留。`" />
        <div class="editor-grid"><label>业务 APP<a-select v-model:value="draftApp" :options="state.apps.filter(app=>app.id!=='platform').map(app => ({ value: app.id, label: app.name }))" :disabled="ui.busy" /></label><label>预设动作<a-select v-model:value="draftAction" :options="actionOptions" :disabled="ui.busy" /></label></div>
        <label class="field-label">预设结果</label>
        <a-radio-group v-model:value="draftMode" :disabled="ui.busy"><a-radio-button value="unset">不授予</a-radio-button><a-radio-button value="allow">允许</a-radio-button><a-radio-button value="deny">明确禁止</a-radio-button></a-radio-group>
        <div v-if="draftMode === 'allow' || (draftMode === 'deny' && draftAction !== '*')" class="scope-box"><strong>{{draftMode === 'deny' ? '仅禁止匹配对象的范围' : '允许范围'}}</strong><a-checkbox-group v-model:value="draftScopes" :options="activeApp?.scopes" :disabled="ui.busy" /><p class="muted">可保留空范围；空范围始终拒绝访问，不代表全部。</p></div>
        <a-alert v-if="draftMode === 'allow' && !draftScopes.length" type="warning" show-icon message="当前范围为空，保存后此预设不会产生可用访问权限。" />
        <div v-if="previewed" class="impact-preview"><div class="section-top"><h3>影响预览</h3><a-tag color="green">{{ changedPeople }} 位员工的有效权限变化</a-tag></div><p class="muted">逐一列出主岗具名员工，兼岗不参与继承。未开通与停用账号继续拒绝访问。</p><a-table :columns="impactColumns" :data-source="impact" :pagination="false" size="small" :scroll="{ x: 720, y: 320 }"><template #bodyCell="{ column, record }"><template v-if="column.key === 'employee'"><strong>{{ record.name }}</strong><div class="muted">{{ record.action }}</div></template><template v-else-if="column.key === 'before'"><span :class="record.before.allowed ? 'allow-text' : 'muted'">{{ resultText(record.before) }}</span></template><template v-else-if="column.key === 'after'"><span :class="record.after.allowed ? 'allow-text' : 'deny-text'">{{ resultText(record.after) }}</span></template><template v-else-if="column.key === 'diff'">{{ difference(record) }}</template></template></a-table><div class="preview-note">保存范围：仅本机合成演示。正式服务的权限判定与审计仍待 Owner 确认原型后实施。</div></div>
      </div>
      <template #footer><a-button :disabled="ui.busy" @click="modalOpen = false">取消</a-button><a-button v-if="!previewed" type="primary" :disabled="!isAdmin" @click="preview">预览受影响员工</a-button><a-button v-else type="primary" :loading="ui.busy" :disabled="!isAdmin" @click="savePreset">确认影响并保存演示</a-button></template>
    </a-modal>
  </div>
</template>

<style scoped>
.department-layout{display:grid;grid-template-columns:270px minmax(0,1fr);gap:20px;align-items:start}.organization-panel{position:sticky;top:20px;padding:22px 16px}.section-top{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:18px}.section-top h3,.section-top h4{margin:0}.section-top p{margin:6px 0 0}.organization-foot{border-top:1px solid #e5ebe6;margin:22px 4px 0;padding-top:18px;color:#738378;font-size:12px;line-height:1.8}.organization-panel :deep(.ant-tree){background:transparent}.organization-panel :deep(.ant-tree-title){white-space:normal;line-height:1.65}.organization-panel :deep(.ant-tree-node-content-wrapper){padding:7px 8px;min-height:38px}.organization-panel :deep(.ant-tree-node-selected){background:#e4f1e7!important}.department-summary{display:flex;justify-content:space-between;gap:20px;align-items:center}.department-summary h2{margin:8px 0}.member-count{display:flex;flex-direction:column;align-items:center;border-left:1px solid #e3eae4;padding-left:32px;color:#6f8074;white-space:nowrap}.member-count strong{font-size:34px;color:#356849;line-height:1.2}.member-count span{font-size:12px;margin-top:7px}.member-row{display:flex;align-items:center;gap:12px;padding:13px 0;border-top:1px solid #eff2ef}.member-row:first-child{border-top:0}.person-avatar{width:38px;height:38px;display:grid;place-items:center;background:#e6efe7;color:#477555;border-radius:12px;font-weight:600}.person-main{display:flex;flex:1;flex-direction:column;gap:3px}.person-main span{color:#7c8b81;font-size:12px}.secondary-section{border-top:1px dashed #dbe5dd;margin-top:16px;padding-top:23px}.secondary-list>div{display:flex;gap:15px;padding:12px 0}.secondary-section :deep(.ant-empty){margin:12px 0;color:#8b998f}.preset-row{display:grid;grid-template-columns:minmax(130px,1.2fr) 74px minmax(150px,1.4fr) 50px;gap:12px;align-items:center;padding:14px 0;border-top:1px solid #edf2ee}.preset-row>div:first-child{display:flex;flex-direction:column;gap:4px}.preset-row .ant-tag{margin:0;width:max-content}.preset-scopes{font-size:13px;color:#5f7566}.rule-alert{margin-top:20px}.unmapped-state{padding:48px;min-height:350px}.unmapped-state h2{margin:20px 0 12px}.unmapped-state p{color:#758379;line-height:1.8;max-width:580px}.editor-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.editor-grid label{display:flex;flex-direction:column;gap:8px;color:#53655a;font-size:13px}.field-label{font-weight:600;color:#44584a}.scope-box{background:#f5f8f4;border:1px solid #e2ebe2;border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:15px}.scope-box p{margin:0;font-size:12px}.scope-box :deep(.ant-checkbox-group){display:flex;gap:12px 20px;flex-wrap:wrap}.impact-preview{border-top:1px solid #e4ebe5;padding-top:20px}.impact-preview>.muted{font-size:12px}.impact-preview :deep(.ant-table-cell){font-size:12px;line-height:1.7}.allow-text{color:#36784f}.deny-text{color:#926b3d}.preview-note{margin-top:15px;padding:12px 14px;background:#f6f8f5;color:#77857b;font-size:12px;border-radius:8px}@media(max-width:1000px){.department-layout{grid-template-columns:230px minmax(0,1fr)}.preset-row{grid-template-columns:1fr 65px}.preset-scopes{grid-column:1}.preset-row .ant-btn{grid-column:2}}@media(max-width:760px){.department-layout{grid-template-columns:1fr}.organization-panel{position:static}.department-summary{align-items:flex-start}.member-count{padding-left:20px}.editor-grid{grid-template-columns:1fr}.secondary-list>div{flex-direction:column;gap:5px}.unmapped-state{padding:24px}}
</style>
