<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { state, ui, isAdmin, effective, saveDemo, registerDemoApp, deptName, scopeLabel } from '../model'
import AttendancePreview from './AttendancePreview.vue'
import { evaluatePermission } from '../permission'

const props = defineProps({employeeId:{type:String,default:'e1'}})
const employeeId = ref(props.employeeId)
watch(()=>props.employeeId, value=>{employeeId.value=value})
const appId = ref('attendance')
const actionId = ref('*')
const employee = computed(() => state.employees.find(item => item.id === employeeId.value))
const app = computed(() => state.apps.find(item => item.id === appId.value))
const action = computed(() => app.value?.actions.find(item => item.id === actionId.value))
const permissionKey = computed(() => `${appId.value}:${actionId.value}`)
const savedRule = computed(() => employee.value?.exceptions?.[permissionKey.value])
const mode = ref('inherit')
const scopes = ref([])
const namedConfirmed = ref(false)
const qualified = ref(false)
const hasDemoModule = computed(() => state.apps.some(item => item.id === 'equipment'))
const actionOptions = computed(() => [{ value: '*', label: 'APP 整体进入权限' }, ...(app.value?.actions.map(item => ({ value: item.id, label: `${item.name}${item.highRisk ? ' · 高风险' : ''}` })) || [])])
const savedEffective = computed(() => effective(employee.value, appId.value, actionId.value))
const appEffective = computed(() => effective(employee.value, appId.value, '*'))
const inherited = computed(() => {
  const snapshot = JSON.parse(JSON.stringify(state))
  const target = snapshot.employees.find(item => item.id === employeeId.value)
  if (target) delete target.exceptions[permissionKey.value]
  return evaluatePermission(snapshot, target, appId.value, actionId.value)
})
const preview = computed(() => {
  const snapshot = JSON.parse(JSON.stringify(state))
  const target = snapshot.employees.find(item => item.id === employeeId.value)
  if (target) {
    if (mode.value === 'inherit') delete target.exceptions[permissionKey.value]
    else target.exceptions[permissionKey.value] = { mode: mode.value, scope: [...scopes.value], qualified: !!(namedConfirmed.value && qualified.value) }
  }
  return evaluatePermission(snapshot, target, appId.value, actionId.value)
})
const appDenied = computed(() => {
  const own = employee.value?.exceptions?.[`${appId.value}:*`]
  const dept = state.depts.find(item => item.id === employee.value?.departmentId)
  return (own || dept?.presets?.[`${appId.value}:*`])?.mode === 'deny'
})
const permissionRows = computed(() => [{ id: '*', name: 'APP 整体进入', highRisk: false }, ...(app.value?.actions || [])].map(item => ({ ...item, result: effective(employee.value, appId.value, item.id), exception: employee.value?.exceptions?.[`${appId.value}:${item.id}`] })))
const columns = [{ title: '动作', key: 'action', width: 170 }, { title: '有效结果', key: 'result', width: 95 }, { title: '有效数据范围', key: 'scope' }, { title: '授权来源', key: 'source' }, { title: '', key: 'edit', width: 65 }]
function hydrate() {
  const rule = employee.value?.exceptions?.[permissionKey.value]
  mode.value = rule?.mode || 'inherit'
  scopes.value = [...(rule?.scope || [])]
  namedConfirmed.value = !!rule?.qualified
  qualified.value = !!rule?.qualified
}
watch([employeeId, actionId], hydrate)
watch(appId, () => { actionId.value = '*'; hydrate() })
watch(() => state.revision, hydrate)
hydrate()
async function saveException() {
  if (!isAdmin.value) return message.error('仅演示管理员可配置个人权限。')
  if (!employee.value || !app.value) return message.error('请选择已登记的员工与 APP。')
  if ((mode.value === 'allow' || (mode.value === 'deny' && actionId.value !== '*')) && !scopes.value.length) return message.error('空范围拒绝授权：请选择至少一个明确的数据范围。')
  if (mode.value === 'allow' && action.value?.highRisk && (!namedConfirmed.value || !qualified.value || !employee.value.checked)) return message.error('高风险动作须具名确认，并完成资格 / 领域范围校验。')
  const targetId = employeeId.value
  const targetApp = appId.value
  const targetAction = actionId.value
  const selectedMode = mode.value
  const scope = [...scopes.value]
  const checkedHighRisk = !!(namedConfirmed.value && qualified.value)
  const targetName = employee.value.name
  const actionName = actionId.value === '*' ? 'APP 整体' : action.value.name
  const result = await saveDemo(`${targetName}的${app.value.name} · ${actionName}个人权限设为${selectedMode === 'inherit' ? '继承' : selectedMode === 'allow' ? '额外允许' : '明确禁止'}`, () => {
    if (!isAdmin.value) throw new Error('当前演示账号无管理权限。')
    const target = state.employees.find(item => item.id === targetId)
    const targetModule = state.apps.find(item => item.id === targetApp)
    const targetOperation = targetModule?.actions.find(item => item.id === targetAction)
    if (!target || !targetModule || (targetAction !== '*' && !targetOperation)) throw new Error('记录已变化，请重新核对。')
    if ((selectedMode === 'allow' || (selectedMode === 'deny' && targetAction !== '*')) && (!scope.length || scope.some(value => !targetModule.scopes.some(item => item.value === value)))) throw new Error('数据范围无效，保存已拒绝。')
    if (selectedMode === 'allow' && targetOperation?.highRisk && (!checkedHighRisk || !target.checked)) throw new Error('高风险资格 / 领域校验未通过。')
    if (selectedMode === 'inherit') delete target.exceptions[`${targetApp}:${targetAction}`]
    else target.exceptions[`${targetApp}:${targetAction}`] = { mode: selectedMode, scope: scope, ...(targetOperation?.highRisk && selectedMode === 'allow' ? { qualified: true } : {}) }
  })
  if (result.ok) message.success('演示已保存到本机')
  else message.error(result.error)
}
async function removeException() {
  if (!isAdmin.value || !savedRule.value) return
  const targetId = employeeId.value
  const key = permissionKey.value
  const result = await saveDemo(`删除${employee.value.name}的${app.value.name}个人例外，恢复部门继承`, () => {
    if (!isAdmin.value) throw new Error('当前演示账号无管理权限。')
    delete state.employees.find(item => item.id === targetId).exceptions[key]
  })
  if (result.ok) message.success('个人例外已删除，演示已保存到本机')
  else message.error(result.error)
}
async function addModule() {
  if (!isAdmin.value) return message.error('仅演示管理员可注册演示模块。')
  const result = await registerDemoApp()
  if (result.ok) { appId.value = 'equipment'; message.success('设备管理演示模块已注册，尚无授权。') }
  else message.error(result.error)
}
</script>

<template>
  <div class="permissions-page stack">
    <div class="page-heading"><div><div class="kicker">ACCESS CONTROL</div><h1>个人权限与有效结果</h1><p class="muted">从员工到 APP、动作与数据范围，查看每一次允许或拒绝的原因。</p></div><a-button :disabled="!isAdmin || hasDemoModule" :loading="ui.busy" @click="addModule">{{ hasDemoModule ? '设备演示模块已注册' : '+ 注册演示模块' }}</a-button></div>
    <a-alert v-if="!isAdmin" type="info" show-icon message="当前为只读视图。使用演示管理员登录后，可保存个人例外。" />
    <section class="panel selection-panel">
      <div class="selection-step"><span class="step-number">01</span><div><label>选择具名员工</label><a-select v-model:value="employeeId" :options="state.employees.map(item => ({ value: item.id, label: `${item.name} · ${item.code}` }))" :disabled="ui.busy" /></div></div>
      <div class="selected-person"><div class="person-circle">{{ employee?.name.slice(0, 1) }}</div><div><strong>{{ employee?.name }}</strong><p>{{ deptName(employee?.departmentId) }} · {{ employee?.position }}</p></div><a-tag :color="employee?.status === 'active' ? 'green' : employee?.status === 'pending' ? 'orange' : 'default'">{{ employee?.status === 'active' ? '已开通' : employee?.status === 'pending' ? '待核验 / 未开通' : '已停用' }}</a-tag></div>
    </section>
    <a-alert v-if="employee?.status !== 'active'" type="warning" show-icon message="此账号当前不可访问业务 APP。权限配置不能绕过未开通或停用状态。" />
    <section class="panel app-panel"><div class="section-top"><div class="step-title"><span class="step-number">02</span><h3>选择业务 APP</h3></div><span class="muted">每个模块遵循同一权限契约</span></div><div class="app-grid"><button v-for="item in state.apps" :key="item.id" class="app-card" :class="{ selected: item.id === appId }" :disabled="ui.busy" @click="appId = item.id"><span class="app-symbol" :style="{ background: `${item.color}15`, color: item.color }">{{ item.name.slice(0, 1) }}</span><span><strong>{{ item.name }}</strong><small>{{ item.description }}</small></span><span v-if="item.id === appId" class="selected-check">✓</span></button></div><div v-if="hasDemoModule" class="module-note">设备管理通过合成元数据注册进入同一界面。这里只验证交互契约，未接入真实业务执行器。</div></section>
    <div class="permission-layout">
      <section class="panel editor-panel stack">
        <div class="step-title"><span class="step-number">03</span><h3>动作与个人例外</h3></div>
        <label class="field-label">选择动作<a-select v-model:value="actionId" :options="actionOptions" :disabled="ui.busy" /></label>
        <a-alert v-if="appDenied && actionId !== '*'" type="warning" show-icon message="APP 整体禁止优先。即使本动作额外允许，当前仍无法访问。" description="需先核对 APP 整体规则，动作例外不会绕过上层禁止。" />
        <div class="inheritance-summary"><span class="muted">移除此项个人例外后</span><strong>{{ inherited.allowed ? '继承后允许' : '继承后拒绝' }}</strong><span>{{ inherited.allowed ? inherited.scope.map(scopeLabel).join('、') : inherited.reason }}</span></div>
        <div><label class="field-label">个人三态</label><a-radio-group v-model:value="mode" class="mode-group" :disabled="!isAdmin || ui.busy"><a-radio-button value="inherit">继承</a-radio-button><a-radio-button value="allow">额外允许</a-radio-button><a-radio-button value="deny">明确禁止</a-radio-button></a-radio-group><p class="field-help">继承：无个人例外。动作明确禁止：仅拒绝选中范围的对象。APP 整体禁止才拒绝所有动作与对象。</p></div>
        <div v-if="mode === 'allow' || (mode === 'deny' && actionId !== '*')" class="scope-editor"><div class="step-title"><span class="step-number">04</span><h3>限定数据范围{{mode === 'deny' ? '（仅禁止匹配对象）' : ''}}</h3></div><a-checkbox-group v-model:value="scopes" :options="app?.scopes" :disabled="!isAdmin || ui.busy" /><p class="field-help">只有与 APP 整体范围相交的部分才会生效。空范围拒绝访问，不代表全部。</p><a-alert v-if="!scopes.length" type="warning" show-icon message="请选择明确范围，当前预览结果为拒绝。" /></div>
        <div v-if="action?.highRisk" class="high-risk"><a-tag color="orange">高风险动作</a-tag><strong>{{ action.name }}需要具名校验</strong><p>部门预设不会自动授予。管理员不能通过广泛 APP 权限替代本动作资格与业务领域约束。</p><template v-if="mode === 'allow'"><a-checkbox v-model:checked="namedConfirmed" :disabled="!isAdmin || ui.busy">明确具名授权给 {{ employee?.name }}（{{ employee?.code }}）</a-checkbox><a-checkbox v-model:checked="qualified" :disabled="!isAdmin || ui.busy || !employee?.checked">已核验此员工的操作资格及所选业务领域范围</a-checkbox><span v-if="!employee?.checked" class="deny-text">员工企业身份尚未核验，资格确认不可用。</span><small>此勾选仅演示资格门禁；正式领域校验待后端实现。</small></template><p v-else class="muted">继承不会产生高风险允许；明确禁止继续拒绝。</p></div>
        <div class="editor-actions"><a-button type="primary" :loading="ui.busy" :disabled="!isAdmin" @click="saveException">保存个人权限演示</a-button><a-button v-if="savedRule" danger :disabled="!isAdmin || ui.busy" @click="removeException">删除例外，恢复继承</a-button></div>
      </section>
      <aside class="stack effective-aside">
        <section class="panel effective-panel" :class="{ allowed: preview.allowed }"><div class="kicker">当前编辑预览</div><div class="result-heading"><span class="result-dot">{{ preview.allowed ? '✓' : '—' }}</span><h2>{{ preview.allowed ? '允许访问' : '拒绝访问' }}</h2></div><p class="result-reason">{{ preview.reason }}</p><dl><div><dt>具名员工</dt><dd>{{ employee?.name }}</dd></div><div><dt>APP / 动作</dt><dd>{{ app?.name }} / {{ actionId === '*' ? '整体进入' : action?.name }}</dd></div><div><dt>授权来源</dt><dd>{{ preview.source }}</dd></div><div><dt>有效数据范围</dt><dd>{{ preview.scope.length ? preview.scope.map(scopeLabel).join('、') : '空 · 无可用范围' }}</dd></div></dl><div class="preview-foot">此处随编辑实时计算。点击保存成功后，本机演示记录才会更新。</div></section>
        <section class="panel saved-panel"><h3>已保存的当前结果</h3><div><a-tag :color="savedEffective.allowed ? 'green' : 'default'">{{ savedEffective.allowed ? '允许' : '拒绝' }}</a-tag><span>{{ savedEffective.source }}</span></div><p>{{ savedEffective.allowed ? savedEffective.scope.map(scopeLabel).join('、') : savedEffective.reason }}</p><div class="app-gate"><span class="muted">APP 进入门禁</span><strong>{{ appEffective.allowed ? '允许' : '拒绝' }}</strong><small>{{ appEffective.allowed ? appEffective.scope.map(scopeLabel).join('、') : appEffective.reason }}</small></div></section>
        <div class="contract-note"><strong>判定顺序</strong><p>账号状态 → APP 整体门禁 → 个人明确禁止 → 动作授权 → 高风险资格 → 有效范围交集。</p></div>
      </aside>
    </div>
    <AttendancePreview v-if="appId === 'attendance' && employee" :employee="employee" :can-configure="true"/><section class="panel result-table"><div class="section-top"><div><h3>{{ employee?.name }} · {{ app?.name }}的全部有效结果</h3><p class="muted">保存后同步更新。每个动作都说明权限来源与范围。</p></div><a-tag>只读判定预览</a-tag></div><a-table :columns="columns" :data-source="permissionRows" :pagination="false" row-key="id" :scroll="{ x: 700 }"><template #bodyCell="{ column, record }"><template v-if="column.key === 'action'"><strong>{{ record.name }}</strong><a-tag v-if="record.highRisk" color="orange" class="risk-tag">高风险</a-tag></template><template v-else-if="column.key === 'result'"><a-tag :color="record.result.allowed ? 'green' : 'default'">{{ record.result.allowed ? '允许' : '拒绝' }}</a-tag></template><template v-else-if="column.key === 'scope'"><span v-if="record.result.scope.length">{{ record.result.scope.map(scopeLabel).join('、') }}</span><span v-else class="muted">空范围 · {{ record.result.reason }}</span></template><template v-else-if="column.key === 'source'">{{ record.result.source }}<div v-if="record.exception" class="muted exception-note">已保存个人例外</div></template><template v-else-if="column.key === 'edit'"><a-button type="link" @click="actionId = record.id">查看</a-button></template></template></a-table></section>
  </div>
</template>

<style scoped>
.selection-panel{display:flex;align-items:center;justify-content:space-between;gap:26px}.selection-step{display:flex;align-items:center;gap:14px;min-width:320px}.selection-step>div{display:flex;flex-direction:column;gap:7px;flex:1}.selection-step label{font-size:12px;color:#687a6d}.step-number{display:grid;place-items:center;width:28px;height:28px;flex-shrink:0;color:#759d7f;background:#edf4ec;border-radius:9px;font-size:11px;font-weight:700}.selected-person{display:flex;align-items:center;gap:12px}.selected-person strong{font-size:15px}.selected-person p{margin:4px 0 0;color:#859187;font-size:12px}.person-circle{width:42px;height:42px;display:grid;place-items:center;background:#e8f0e9;border-radius:50%;color:#527959}.section-top{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-bottom:20px}.section-top h3,.step-title h3,.saved-panel h3{margin:0}.section-top p{margin:5px 0 0}.step-title{display:flex;align-items:center;gap:10px}.app-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.app-card{display:flex;align-items:center;gap:11px;text-align:left;padding:16px 13px;border-radius:12px;border:1px solid #e4ebe4;background:#fff;cursor:pointer;position:relative;min-height:90px;transition:border-color .15s,background .15s}.app-card:hover{border-color:#afcbb3}.app-card.selected{border-color:#87b891;background:#f5faf3;box-shadow:0 0 0 1px #87b891}.app-card:disabled{cursor:default}.app-symbol{width:35px;height:38px;flex-shrink:0;display:grid;place-items:center;border-radius:10px;font-size:14px;font-weight:600}.app-card strong{font-size:13px;color:#42584a;display:block}.app-card small{display:block;font-size:10px;color:#849086;margin-top:5px;line-height:1.5}.selected-check{position:absolute;right:8px;top:5px;color:#719d7c;font-size:11px}.module-note{margin-top:16px;color:#75847a;background:#f7f9f5;padding:12px 14px;border-radius:9px;font-size:12px}.permission-layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:20px;align-items:start}.field-label{display:flex;flex-direction:column;gap:8px;font-size:13px;font-weight:600;color:#4d6354}.inheritance-summary{display:flex;flex-direction:column;gap:6px;padding:16px 18px;background:#f7f9f5;border:1px solid #e4ebe1;border-radius:10px;font-size:12px;line-height:1.6}.inheritance-summary strong{font-size:14px;color:#556d5c}.mode-group{display:flex;margin-top:10px}.mode-group :deep(.ant-radio-button-wrapper){flex:1;text-align:center;padding:0 10px;font-size:12px}.field-help{font-size:12px;color:#849085;line-height:1.8;margin:10px 0 0}.scope-editor{border-top:1px solid #e8eee7;padding-top:20px}.scope-editor :deep(.ant-checkbox-group){display:flex;flex-wrap:wrap;gap:12px 22px;margin-top:20px}.scope-editor .ant-alert{margin-top:14px}.high-risk{display:flex;flex-direction:column;gap:12px;background:#fffaf2;border:1px solid #f0e5ce;padding:18px;border-radius:12px;font-size:12px}.high-risk>.ant-tag{width:max-content;margin:0}.high-risk strong{font-size:14px;color:#896b35}.high-risk p{margin:0;color:#887958;line-height:1.8}.high-risk small{color:#9a8a6a;font-size:11px}.deny-text{color:#a47541}.editor-actions{display:flex;flex-wrap:wrap;gap:10px;padding-top:6px}.effective-panel{border-color:#eadfd2;background:#fffcf6}.effective-panel.allowed{border-color:#cfe2cc;background:#f5fbf2}.result-heading{display:flex;align-items:center;gap:12px;margin:18px 0 10px}.result-heading h2{margin:0;font-size:24px;color:#8c6d41}.allowed .result-heading h2{color:#40734d}.result-dot{display:grid;place-items:center;width:32px;height:32px;border-radius:50%;background:#f4e8d2;color:#9d7c43;font-size:19px}.allowed .result-dot{background:#daedd4;color:#4c8159}.result-reason{font-size:12px;color:#898172;line-height:1.8;margin-bottom:22px}.effective-panel dl{margin:0}.effective-panel dl>div{display:flex;flex-direction:column;gap:5px;margin-top:16px;font-size:12px}.effective-panel dt{color:#8a948a}.effective-panel dd{margin:0;color:#4f6655;line-height:1.7}.preview-foot{border-top:1px solid #e4e9dc;margin-top:24px;padding-top:15px;color:#89917f;font-size:11px;line-height:1.8}.saved-panel h3{font-size:14px;margin-bottom:15px}.saved-panel>div{font-size:12px}.saved-panel>p{font-size:12px;color:#7c897f;line-height:1.8}.app-gate{display:flex;flex-direction:column;gap:6px;border-top:1px solid #e6ece5;padding-top:15px;margin-top:15px}.app-gate strong{color:#62776a}.app-gate small{color:#8b978d;line-height:1.6}.contract-note{padding:4px 10px;color:#849184;font-size:12px;line-height:1.8}.contract-note strong{color:#6e7d70}.contract-note p{margin:5px 0}.result-table :deep(.ant-table-cell){font-size:12px;line-height:1.8}.risk-tag{font-size:10px;margin-left:7px}.exception-note{font-size:10px}.permissions-page .page-heading>.ant-btn{flex-shrink:0}@media(max-width:1150px){.app-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.permission-layout{grid-template-columns:minmax(0,1fr) 300px}.selection-step{min-width:260px}.selected-person>.ant-tag{display:none}}@media(max-width:900px){.permission-layout{grid-template-columns:1fr}.effective-aside{display:grid;grid-template-columns:1fr 1fr}.contract-note{grid-column:1/-1}.selection-panel{align-items:flex-start}.selected-person{align-items:flex-start}.selected-person .person-circle{display:none}}@media(max-width:650px){.selection-panel{flex-direction:column;gap:18px}.selection-step{min-width:0;width:100%}.effective-aside{display:flex;flex-direction:column}.app-grid{grid-template-columns:1fr 1fr}.app-card{padding:14px 10px;gap:8px}.app-symbol{width:28px}.section-top{align-items:flex-start}.section-top>.muted{display:none}.editor-actions>.ant-btn{width:100%}.permissions-page .page-heading{flex-direction:column;align-items:flex-start}}
</style>
