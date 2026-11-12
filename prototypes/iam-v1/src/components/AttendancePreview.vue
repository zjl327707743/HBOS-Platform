<script setup>
import { computed, ref, watch } from 'vue'
import { state, ui, currentUser, isAdmin, saveDemo, scopeLabel, deptName } from '../model.js'
import { previewAttendance } from '../permission.js'

const props = defineProps({
  employee: { type: Object, default: null },
  canConfigure: { type: Boolean, default: false }
})

const canEdit = computed(() => props.canConfigure && isAdmin.value)
// An employee's parameter experiment never changes the session subject.
const actor = computed(() => canEdit.value ? props.employee : currentUser.value)
const endpoint = ref('self')
const departmentId = ref('d1')
const injectedEmployeeId = ref('')
const response = ref(null)
const lastRequest = ref(null)
const planError = ref('')
const planNotice = ref('')
const requestLabel = ref('')
const parameterTargets = computed(() => state.employees
  .filter(person => person.employeeId && person.employeeId !== actor.value?.employeeId)
  .map(person => ({ value: person.employeeId, label: `${person.employeeId} · 合成参数` })))
const returnedRows = computed(() => response.value?.ok && Array.isArray(response.value.rows) ? response.value.rows : [])
const responseTotal = computed(() => response.value?.ok ? response.value.total : 0)
const columns = [
  { title: '员工档案标识', dataIndex: 'employeeId', key: 'employeeId', width: 190 },
  { title: '考勤日期', dataIndex: 'date', key: 'date', width: 115 },
  { title: '打卡时间', dataIndex: 'checkIn', key: 'checkIn', width: 95 },
  { title: '考勤状态', dataIndex: 'status', key: 'status', width: 95 },
  { title: '事件时部门', key: 'eventDepartment', width: 180 },
  { title: '部门归属证据', key: 'departmentEvidence', width: 130 }
]
const plans = [
  { id: 'self', label: '方案 1 · 仅本人查看', description: 'APP 范围为本人及两个演示部门，查看范围仅本人；不额外配置导出。', appScope: ['self', 'd1', 'd2'], readScope: ['self'] },
  { id: 'department', label: '方案 2 · 指定部门查看', description: '查看范围为质量研究部，须有已确认的事件时部门归属；不额外配置导出。', appScope: ['self', 'd1', 'd2'], readScope: ['d1'] },
  { id: 'export-denied', label: '方案 3 · 本人查看，导出拒绝', description: '本人可以查看，本人范围的导出明确禁止。导出候选能力仍未接入真实服务。', appScope: ['self', 'd1', 'd2'], readScope: ['self'], denyExport: true },
  { id: 'intersection', label: 'SELF 与部门交集', description: 'APP 范围为质量研究部，查看范围为本人；只返回同时满足两者的合成记录。', appScope: ['d1'], readScope: ['self'] }
]

function clearPreview() {
  response.value = null
  lastRequest.value = null
  requestLabel.value = ''
}
watch(() => [actor.value?.id, actor.value?.employeeId], () => {
  clearPreview()
  endpoint.value = 'self'
  injectedEmployeeId.value = parameterTargets.value[0]?.value || ''
  planError.value = ''
  planNotice.value = ''
}, { immediate: true })

function runRequest(request, label) {
  if (!actor.value || ui.busy) return
  lastRequest.value = { ...request }
  requestLabel.value = label
  response.value = previewAttendance(state, actor.value, request)
}
function query(operation = 'read') {
  runRequest({ operation, endpoint: endpoint.value, requestedEmployeeId: '', requestedDepartmentId: endpoint.value === 'department' ? departmentId.value : '' },
    `${endpoint.value === 'self' ? '本人接口' : '指定部门接口'} · ${operation === 'read' ? '查看判定' : '导出候选判定'}`)
}
function injectParameter() {
  if (!injectedEmployeeId.value) return
  runRequest({ operation: 'read', endpoint: 'self', requestedEmployeeId: injectedEmployeeId.value, requestedDepartmentId: '' }, '本人接口 · 注入他人员工参数')
}
watch(() => state.revision, () => {
  // Re-evaluate after revoke, transfer or a saved exception; never retain old rows.
  if (lastRequest.value && actor.value) response.value = previewAttendance(state, actor.value, lastRequest.value)
})

async function applyPlan(plan) {
  if (!canEdit.value || !actor.value || ui.busy) return
  const targetId = actor.value.id
  const targetName = actor.value.name
  planError.value = ''
  planNotice.value = ''
  const result = await saveDemo(`${targetName}应用考勤合成方案：${plan.label}`, () => {
    if (!isAdmin.value || !props.canConfigure || props.employee?.id !== targetId) throw new Error('查询主体或管理视角已变化，请重新核对。')
    const target = state.employees.find(person => person.id === targetId)
    if (!target) throw new Error('此主体没有员工档案，不能用方案伪造 Employee 关联。')
    target.exceptions ||= {}
    target.exceptions['attendance:*'] = { mode: 'allow', scope: [...plan.appScope] }
    target.exceptions['attendance:read'] = { mode: 'allow', scope: [...plan.readScope] }
    delete target.exceptions['attendance:export']
    if (plan.denyExport) target.exceptions['attendance:export'] = { mode: 'deny', scope: ['self'] }
  })
  if (result.ok) {
    planNotice.value = '演示已保存到本机。方案只调整此员工的考勤例外；其他应用规则保留。'
    endpoint.value = plan.id === 'department' ? 'department' : 'self'
    departmentId.value = 'd1'
    query('read')
  } else planError.value = result.error || '演示方案未保存。'
}

function eventDepartment(row) {
  return row.departmentEvidenceConfirmed && row.eventDepartmentId ? deptName(row.eventDepartmentId) : '历史部门待核对'
}
</script>

<template>
  <section class="panel attendance-preview stack" aria-label="合成考勤数据范围预览">
    <div class="preview-heading">
      <div><span class="kicker">ATTENDANCE DATA SCOPE</span><h2>考勤实例预览</h2><p class="muted">在合成记录上观察本人、部门范围与单独导出授权。</p></div>
      <a-tag color="green">R4 A 阶段 · 合成演示</a-tag>
    </div>
    <a-alert type="info" show-icon message="交互原型 / 合成数据 / 尚未连接 HBOS 后端" description="这里只展示前端判定返回的记录。没有调用真实 API、执行 SQL 或生成下载文件。" />

    <div class="actor-card">
      <div><span class="muted">{{ canEdit ? '管理员选中的查询主体' : '当前本人查询主体' }}</span><strong>{{ actor?.name || '暂无登录主体' }}</strong></div>
      <div><span class="muted">员工档案关联</span><strong>{{ actor?.employeeId || '无 Employee 关联' }}</strong></div>
      <div><span class="muted">当前主部门</span><strong>{{ actor?.departmentId ? deptName(actor.departmentId) : '不适用' }}</strong></div>
    </div>
    <p class="contract-note">查询主体保持不变。SELF 指已确认的同一 Employee；本人历史不按当前部门重写。部门查询只接受已确认的事件时部门证据，历史部门不明的记录不向部门范围开放。</p>

    <div v-if="canEdit" class="scenario-plans">
      <div class="section-title"><h3>一键合成方案</h3><span class="muted">先保存例外，再观察返回结果</span></div>
      <div class="plans-grid"><div v-for="plan in plans" :key="plan.id" class="plan-card"><a-button :disabled="!actor || ui.busy" :loading="ui.busy" @click="applyPlan(plan)">{{ plan.label }}</a-button><p>{{ plan.description }}</p><small>APP：{{ plan.appScope.map(scopeLabel).join('、') }}<br />查看：{{ plan.readScope.map(scopeLabel).join('、') }}</small></div></div>
      <a-alert v-if="planError" type="error" show-icon :message="planError" role="alert" />
      <a-alert v-if="planNotice" type="success" show-icon :message="planNotice" />
    </div>

    <div class="query-layout">
      <div class="query-card stack">
        <h3>选择请求范围</h3>
        <a-radio-group v-model:value="endpoint" :disabled="!actor || ui.busy" aria-label="考勤请求范围"><a-radio-button value="self">仅本人</a-radio-button><a-radio-button value="department">指定部门</a-radio-button></a-radio-group>
        <label v-if="endpoint === 'department'" class="field-label">请求的部门<a-select v-model:value="departmentId" :options="state.depts.map(department => ({ value: department.id, label: department.name }))" :disabled="ui.busy" aria-label="请求部门参数" /></label>
        <p class="muted">部门选择只是请求参数，不会获得额外授权，也不自动包含下级部门。</p>
        <div class="query-actions"><a-button type="primary" :disabled="!actor || ui.busy" @click="query('read')">{{ endpoint === 'self' ? '查询本人' : '查询指定部门' }}</a-button><a-button :disabled="!actor || ui.busy" @click="query('export')">单独判定导出</a-button></div>
      </div>
      <div class="query-card injection-card stack">
        <h3>模拟注入他人参数</h3>
        <label class="field-label">注入本人接口的 employee 参数<a-select v-model:value="injectedEmployeeId" :options="parameterTargets" :disabled="!actor || ui.busy || !parameterTargets.length" aria-label="模拟注入的他人员工参数" /></label>
        <p class="muted">此选择只修改请求参数。查询主体仍为上方员工，不能以参数替换当前本人身份。</p>
        <a-button danger :disabled="!actor || ui.busy || !injectedEmployeeId" @click="injectParameter">向本人接口注入他人员工参数</a-button>
      </div>
    </div>

    <div v-if="response" class="response-panel stack" aria-live="polite">
      <div class="response-heading"><div><h3>{{ requestLabel }}</h3><span class="muted">{{ response.operationId || (lastRequest?.operation === 'export' ? 'attendance.export' : 'attendance.read') }}</span></div><a-tag :color="response.ok ? 'green' : 'red'">{{ response.ok ? '允许（合成预览）' : '拒绝（合成预览）' }}</a-tag></div>
      <a-alert :type="response.ok ? 'success' : 'warning'" show-icon :message="response.ok ? '仅返回当前允许范围内的合成投影' : (response.error || '当前请求不在允许范围内')" :description="response.ok && lastRequest?.operation === 'export' ? '这里只观察独立导出判定，没有生成或下载文件。' : '拒绝对象的字段和总数不会显示。'" />
      <div class="response-metadata"><span><b>返回 total：</b>{{ responseTotal }}</span><span><b>最终来源：</b>{{ response.source || '无可用授权来源' }}</span></div>
      <a-table :columns="columns" :data-source="returnedRows" row-key="id" :pagination="false" size="small" :scroll="{ x: 820 }" :locale="{ emptyText: response.ok ? '当前请求没有可返回的合成记录' : '请求已拒绝，不返回记录' }">
        <template #bodyCell="{ column, record }"><template v-if="column.key === 'eventDepartment'">{{ eventDepartment(record) }}</template><template v-else-if="column.key === 'departmentEvidence'"><a-tag :color="record.departmentEvidenceConfirmed ? 'green' : 'orange'">{{ record.departmentEvidenceConfirmed ? '已确认（合成）' : '待核对' }}</a-tag></template></template>
      </a-table>
    </div>
    <a-empty v-else description="选择请求范围并查询，查看允许投影或拒绝原因" :image-style="{ height: '45px' }" />
    <p class="contract-note"><code>attendance.read</code> 是当前已有能力名；<code>attendance.export</code> 为未接入的候选动作。模拟结果不代表真实本人权限、部门隔离、导出权限或历史数据关联已通过验收。</p>
  </section>
</template>

<style scoped>
.attendance-preview{margin-top:22px}.stack{display:flex;flex-direction:column;gap:16px}.preview-heading,.section-title,.response-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.preview-heading .kicker{display:block;margin-bottom:7px}.preview-heading p{font-size:12px;margin:6px 0 0}.preview-heading>.ant-tag{margin:0;white-space:nowrap}.actor-card{display:grid;grid-template-columns:1fr 1.3fr 1fr;gap:18px;background:#f6f9f4;border:1px solid #e1eadc;border-radius:9px;padding:16px 18px}.actor-card>div{min-width:0}.actor-card span{display:block;font-size:11px;margin-bottom:7px}.actor-card strong{font-size:13px;font-weight:500;overflow-wrap:anywhere}.contract-note{font-size:11px;color:#768671;line-height:1.8;margin:0}.contract-note code{font-size:11px;color:#5b7558;background:#f0f5ed;padding:1px 4px;border-radius:3px}.scenario-plans{border-top:1px solid #e8eee3;padding-top:18px;display:flex;flex-direction:column;gap:14px}.section-title{align-items:center}.section-title h3,.query-card h3,.response-heading h3{font-size:14px;margin:0}.section-title span{font-size:11px}.plans-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.plan-card{border:1px solid #e4ebdf;border-radius:9px;padding:15px;background:#fcfdfa}.plan-card>.ant-btn{max-width:100%;height:auto;min-height:32px;white-space:normal;text-align:left}.plan-card p{font-size:11px;color:#74846e;line-height:1.8;margin:10px 0 7px}.plan-card small{display:block;color:#87967f;font-size:10px;line-height:1.8}.query-layout{display:grid;grid-template-columns:1fr 1fr;gap:16px}.query-card{padding:18px;border:1px solid #e0e9da;background:#fcfefa;border-radius:9px}.query-card p{font-size:11px;line-height:1.8;margin:0}.query-card .field-label{display:flex;flex-direction:column;gap:9px;font-size:11px;color:#52674a}.query-card :deep(.ant-select){width:100%}.query-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:auto}.injection-card{background:#fffdf8;border-color:#e9e3d4}.injection-card>.ant-btn{align-self:flex-start;white-space:normal;height:auto;min-height:32px;text-align:left}.response-panel{border-top:1px solid #e3ebdc;padding-top:20px}.response-heading{align-items:center}.response-heading span.muted{display:block;font-size:11px;margin-top:6px}.response-metadata{display:flex;flex-wrap:wrap;gap:10px 28px;font-size:12px;color:#62745a}.response-metadata b{font-weight:500;color:#47613e}.response-panel :deep(.ant-table-cell){font-size:11px;overflow-wrap:anywhere}.attendance-preview :deep(.ant-empty){margin:14px 0}.attendance-preview :deep(.ant-empty-description){font-size:12px;color:#879780}@media(max-width:1050px){.actor-card{grid-template-columns:1fr 1fr}.actor-card>div:last-child{grid-column:1/-1}.query-layout{grid-template-columns:1fr}}@media(max-width:760px){.preview-heading,.section-title{flex-direction:column;gap:10px}.actor-card,.plans-grid{grid-template-columns:1fr}.actor-card>div:last-child{grid-column:auto}.response-heading{align-items:flex-start}.query-card{padding:15px}.response-metadata{flex-direction:column;gap:8px}.attendance-preview{padding:18px}}
</style>
