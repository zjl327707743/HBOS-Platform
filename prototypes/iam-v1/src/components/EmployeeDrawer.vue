<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { state, ui, allSubjects, currentUser, isAdmin, deptName, saveDemo, activate, transfer, disable, resetPassword, linkExistingAccount } from '../model.js'
import { summarizeWorkApp } from '../work-policy.js'
import AppUsageList from './AppUsageList.vue'
import WorkSettings from './WorkSettings.vue'

const props = defineProps({ open: Boolean, employeeId: { type: String, default: '' }, initialTab: { type: String, default: 'basic' }, appId: { type: String, default: null } })
const emit = defineEmits(['update:open'])
const selected = computed(() => allSubjects.value.find(item => item.id === props.employeeId) || null)
const isEmployee = computed(() => state.employees.some(item => item.id === props.employeeId))
const isPendingAccount = computed(() => selected.value?.subjectType === 'pending-employee')
const tab = ref('basic'), editingApp = ref(null), workSettings = ref(null), operation = ref('')
const formError = ref(''), working = ref(false), busy = computed(() => ui.busy || working.value)
const targetDepartment = ref(''), targetEmployee = ref(''), accountMode = ref('activate'), existingAccount = ref('')
const personnelVerified = ref(false), ownershipVerified = ref(false), confirmOperation = ref(false), temporaryPassword = ref('')
const confirmedDepartment = item => item && item.confirmed !== false && !['pending', 'unknown', 'unconfirmed'].includes(item.status) && !item.unmapped
const departmentOptions = computed(() => state.depts.map(item => ({ value: item.id, label: `${item.name}${confirmedDepartment(item) ? '' : '（尚未确认）'}`, disabled: !confirmedDepartment(item) })))
const availableEmployees = computed(() => state.employees.filter(item => !item.accountId))
const pendingAccountOptions = computed(() => state.nonEmployeeAccounts.filter(item => item.subjectType === 'pending-employee').map(item => ({ value: item.accountId, label: `${item.name} · ${item.username || item.accountId}` })))
const selectedDepartment = computed(() => state.depts.find(item => item.id === selected.value?.departmentId))
const employeeToLink = computed(() => state.employees.find(item => item.id === targetEmployee.value))
const attendanceStatus = computed(() => ({ confirmed: ['已关联', 'green'], conflict: ['需处理', 'red'] }[selected.value?.attendanceIdentity?.status] || ['待确认', 'gold']))
const accountStatus = computed(() => !selected.value?.accountId ? ['未开通', 'default'] : selected.value.status === 'disabled' ? ['已停用', 'default'] : ['已开通', 'green'])
const logs = computed(() => selected.value ? state.logs.filter(item => item.employeeId === selected.value.id || item.subjectId === selected.value.id || (!item.employeeId && !item.subjectId && item.label.includes(selected.value.name))) : [])
const businessText = value => String(value || '').replace(/Employee/g, '员工档案').replace(/User/g, '账号').replace(/Grant/g, '工作设置').replace(/SELF|\bself\b/g, '本人').replace(/\bdeny\b/g, '不允许')
const transferPreviews = computed(() => {
  if (!selected.value || !targetDepartment.value) return []
  const moved = { ...selected.value, departmentId: targetDepartment.value }
  return state.apps.filter(app => app.id !== 'platform').map(app => ({ app, before: summarizeWorkApp(state, 'employee', selected.value, app.id), after: summarizeWorkApp(state, 'employee', moved, app.id) }))
})
const personalSettings = computed(() => transferPreviews.value.filter(item => item.before.hasPersonalOrdinary || item.before.importantRows?.some(row => row.storedRule)))
const retainedRows = summary => [...(summary.actionRows || []).filter(row => row.sourceText?.includes('单独') || row.sourceText?.includes('个人') || row.complex), ...(summary.importantRows || []).filter(row => row.storedRule)]
const arrangementText = summary => summary.status === 'unavailable' ? summary.actionRows.filter(row => row.available).map(row => row.configuredText).join('；') || summary.text : summary.text
const canOpenAccount = computed(() => isAdmin.value && isEmployee.value && !selected.value?.accountId && (selected.value?.checked || personnelVerified.value) && (accountMode.value === 'activate' || existingAccount.value && ownershipVerified.value))
const canLinkPending = computed(() => isAdmin.value && employeeToLink.value && (employeeToLink.value.checked || personnelVerified.value) && ownershipVerified.value)
const operationTitle = computed(() => ({ transfer: '调岗', disable: '停用账号', reset: '重置临时密码', verify: '核验员工资料' }[operation.value] || ''))
const operationAllowed = computed(() => {
  if (busy.value || !isAdmin.value) return false
  if (operation.value === 'transfer') return !!targetDepartment.value && targetDepartment.value !== selected.value?.departmentId && confirmedDepartment(state.depts.find(item => item.id === targetDepartment.value))
  if (operation.value === 'verify') return personnelVerified.value
  return confirmOperation.value
})
watch(() => [props.open, props.employeeId, props.initialTab, props.appId], () => {
  if (!props.open) { temporaryPassword.value = ''; return }
  tab.value = ['basic', 'account', 'apps', 'history'].includes(props.initialTab) ? props.initialTab : 'basic'
  editingApp.value = props.appId
  operation.value = ''; formError.value = ''; personnelVerified.value = false; ownershipVerified.value = false
  confirmOperation.value = false; accountMode.value = 'activate'; existingAccount.value = ''; targetEmployee.value = ''; temporaryPassword.value = ''
}, { immediate: true })
watch(tab, () => { formError.value = '' })
watch(accountMode, () => { formError.value = ''; ownershipVerified.value = false })
watch(() => currentUser.value?.id, () => { temporaryPassword.value = ''; if (props.open) emit('update:open', false) })
async function requestLeave() {
  if (busy.value) return false
  if (editingApp.value && workSettings.value?.requestLeave) return workSettings.value.requestLeave()
  return true
}
async function close() { if (!await requestLeave()) return; temporaryPassword.value = ''; emit('update:open', false) }
function modify(appId) { editingApp.value = appId; tab.value = 'apps'; formError.value = '' }
function finishWorkSettings() { editingApp.value = null; tab.value = 'apps' }
function beginOperation(type) {
  operation.value = type; formError.value = ''; confirmOperation.value = false; personnelVerified.value = false
  targetDepartment.value = selected.value?.departmentId || ''
}
async function verifyPersonnel(employee) {
  if (employee.checked) return { ok: true }
  if (!personnelVerified.value) return { ok: false, error: '请先核对员工资料与企业归属。' }
  return saveDemo(`${employee.name}员工资料与企业归属核验完成`, () => {
    if (!isAdmin.value) throw new Error('仅管理员可核验员工资料')
    state.employees.find(item => item.id === employee.id).checked = true
  })
}
async function openAccount() {
  if (!canOpenAccount.value || busy.value) return
  working.value = true; formError.value = ''
  try {
    const employee = selected.value
    const verified = await verifyPersonnel(employee)
    if (!verified.ok) { formError.value = verified.error; return }
    const result = accountMode.value === 'activate' ? await activate(employee.id) : await linkExistingAccount(employee.id, existingAccount.value)
    if (!result.ok) { formError.value = businessText(result.error); return }
    if (result.temporaryPassword) temporaryPassword.value = result.temporaryPassword
    message.success('演示已保存到本机')
  } catch { formError.value = '账号未开通，请重试。' }
  finally { working.value = false }
}
async function linkPendingAccount() {
  if (!canLinkPending.value || busy.value) return
  working.value = true; formError.value = ''
  try {
    const verified = await verifyPersonnel(employeeToLink.value)
    if (!verified.ok) { formError.value = verified.error; return }
    const result = await linkExistingAccount(employeeToLink.value.id, selected.value.accountId)
    if (!result.ok) { formError.value = businessText(result.error); return }
    message.success('已关联已有员工，账号继续复用。')
    emit('update:open', false)
  } catch { formError.value = '员工关联未保存，请重试。' }
  finally { working.value = false }
}
async function performOperation() {
  if (!operationAllowed.value || !selected.value) return
  working.value = true; formError.value = ''
  try {
    const id = selected.value.id
    let result
    if (operation.value === 'transfer') result = await transfer(id, targetDepartment.value)
    else if (operation.value === 'disable') result = await disable(id)
    else if (operation.value === 'reset') result = await resetPassword(id)
    else if (operation.value === 'verify') result = await verifyPersonnel(selected.value)
    if (!result?.ok) { formError.value = businessText(result?.error || '操作未保存，请重试。'); return }
    if (result.temporaryPassword) temporaryPassword.value = result.temporaryPassword
    operation.value = ''
    message.success('演示已保存到本机')
  } catch { formError.value = '操作未保存，请重试。' }
  finally { working.value = false }
}
defineExpose({ requestLeave })
</script>

<template>
  <a-drawer :open="open" :title="selected?.name || '员工资料'" :width="720" root-class-name="employee-detail-drawer r5-drawer employee-drawer" :mask-closable="!busy" :closable="!busy" :keyboard="!busy" :body-style="{padding: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden'}" :content-wrapper-style="{maxWidth: 'calc(100vw - 32px)'}" @close="close">
    <template v-if="selected">
      <div class="employee-drawer-scroll">
        <template v-if="temporaryPassword"><div class="drawer-inner stack"><h2>一次临时密码</h2><a-alert message="这组演示临时密码仅展示一次。关闭后不可重新读取，丢失请重新重置。" type="info" show-icon /><code class="temporary-token">{{ temporaryPassword }}</code><p class="drawer-note">员工使用密码登录时须先改密；管理员不能查看修改后的当前密码。演示口令仅在当前页面内存中展示。</p></div></template>
        <WorkSettings v-else-if="editingApp" ref="workSettings" class="drawer-inner drawer-work-settings" subject-kind="employee" :subject-id="employeeId" :app-id="editingApp" @back="finishWorkSettings" />
        <div v-else-if="operation" class="drawer-inner stack">
          <button class="drawer-back" :disabled="busy" @click="operation = ''; formError = ''"><ArrowLeftOutlined />返回员工资料</button><h2>{{ operationTitle }}</h2>
          <template v-if="operation === 'transfer'">
            <label class="drawer-field">新主部门<a-select v-model:value="targetDepartment" aria-label="选择新主部门" :options="departmentOptions" :disabled="busy" /></label>
            <div class="transfer-direction"><span>{{ deptName(selected.departmentId) }}</span><span aria-hidden="true">→</span><strong>{{ deptName(targetDepartment) }}</strong></div>
            <p class="drawer-note">原部门普通安排将结束，新部门普通安排将生效。个人特别设置保留；本人历史考勤仍属于本人。</p>
            <div v-for="item in transferPreviews" :key="item.app.id" class="transfer-preview"><h3>{{ item.app.name }}</h3><p v-if="item.before.status === 'unavailable'" class="drawer-note">{{ businessText(item.before.text) }}；下面显示调岗前后的工作安排。</p><div><span>调岗前</span><p>{{ businessText(arrangementText(item.before)) }}</p></div><div><span>调岗后</span><p>{{ businessText(arrangementText(item.after)) }}</p></div></div>
            <div class="preserved-settings"><strong>保留的个人特别设置</strong><ul v-if="personalSettings.length"><li v-for="item in personalSettings" :key="item.app.id">{{ item.app.name }}<ul v-if="retainedRows(item.before).length"><li v-for="row in retainedRows(item.before)" :key="row.id">{{ businessText(row.text) }} · {{ businessText(row.sourceText) }}</li></ul><p v-else>{{ businessText(item.before.sourceText) }}</p></li></ul><p v-else>当前没有个人特别设置。</p></div>
          </template>
          <template v-else-if="operation === 'disable'"><a-alert message="停用后，该员工将不能登录或使用应用；员工档案及历史记录继续保留。" type="warning" show-icon /><a-checkbox v-model:checked="confirmOperation">确认停用 {{ selected.name }} 的账号</a-checkbox></template>
          <template v-else-if="operation === 'reset'"><p class="drawer-note">将生成独立的演示临时密码，只展示一次。员工下次密码登录须先改密；当前密码始终不可查看。</p><a-checkbox v-model:checked="confirmOperation">确认重置 {{ selected.name }} 的临时密码</a-checkbox></template>
          <template v-else-if="operation === 'verify'"><p class="drawer-note">请核对这位员工的工号、公司、主部门及企业人员归属。姓名或拼音相同不能证明身份。</p><a-descriptions :column="1" bordered><a-descriptions-item label="工号">{{ selected.employeeNumber }}</a-descriptions-item><a-descriptions-item label="公司">{{ selected.company }}</a-descriptions-item><a-descriptions-item label="主部门">{{ deptName(selected.departmentId) }}</a-descriptions-item></a-descriptions><a-checkbox v-model:checked="personnelVerified">已核对上述员工资料与企业归属（演示）</a-checkbox></template>
          <a-alert v-if="formError" :message="formError" type="error" show-icon role="alert" />
        </div>
        <div v-else class="drawer-inner">
          <div class="drawer-identity-strip"><span>{{ isEmployee ? `工号 ${selected.employeeNumber || '待确认'}` : isPendingAccount ? '员工归属待确认' : '服务 / 应急管理账号' }}</span><a-tag :color="accountStatus[1]">{{ accountStatus[0] }}</a-tag></div>
          <a-tabs v-model:activeKey="tab" class="employee-detail-tabs">
            <a-tab-pane key="basic" tab="基本资料">
              <template v-if="isEmployee">
                <a-descriptions :column="1" bordered><a-descriptions-item label="姓名">{{ selected.name }}</a-descriptions-item><a-descriptions-item label="工号">{{ selected.employeeNumber || '待确认' }}</a-descriptions-item><a-descriptions-item label="公司">{{ selected.company || '待补充' }}</a-descriptions-item><a-descriptions-item label="主部门">{{ deptName(selected.departmentId) }}</a-descriptions-item><a-descriptions-item label="岗位">{{ selected.position || '待补充' }}</a-descriptions-item><a-descriptions-item label="兼岗">{{ selected.secondaryDepartments?.map(deptName).join('、') || '无' }}</a-descriptions-item><a-descriptions-item label="性别">{{ selected.gender || '待补充' }}</a-descriptions-item><a-descriptions-item label="生日">{{ selected.birthDate || '待补充' }}</a-descriptions-item><a-descriptions-item label="入职日期">{{ selected.employmentDate || '待补充' }}</a-descriptions-item><a-descriptions-item label="考勤关联"><a-tag :color="attendanceStatus[1]">{{ attendanceStatus[0] }}</a-tag></a-descriptions-item></a-descriptions>
                <a-alert v-if="!confirmedDepartment(selectedDepartment)" class="drawer-section" message="这个部门尚未确认，暂不能用于分配人员或应用权限。" type="warning" show-icon /><p class="drawer-note drawer-section">兼岗资料不会自动增加应用安排。尚无打卡数据，不影响已确认的考勤关联。</p>
              </template>
              <template v-else><a-descriptions :column="1" bordered><a-descriptions-item label="账号名称">{{ selected.name }}</a-descriptions-item><a-descriptions-item label="用途">{{ isPendingAccount ? '已完成企业核验，员工归属待确认' : selected.position || '服务 / 应急管理' }}</a-descriptions-item><a-descriptions-item label="员工档案">{{ isPendingAccount ? '待核验后关联已有员工' : '不代表在职员工，不计入员工人数' }}</a-descriptions-item></a-descriptions><p class="drawer-note drawer-section">没有确认对应员工前，不能读取员工考勤数据。</p></template>
              <a-collapse v-if="isAdmin" ghost class="association-info drawer-section"><a-collapse-panel key="association" header="查看关联信息（仅管理员）"><a-descriptions :column="1" bordered><a-descriptions-item label="员工档案编号">{{ selected.employeeId || '不适用' }}<small>Employee.name</small></a-descriptions-item><a-descriptions-item label="登录账号">{{ selected.accountId || '尚未开通' }}<small>User.name / Employee.user_id</small></a-descriptions-item><a-descriptions-item label="登录别名">{{ selected.username || '未设置' }}<small>User.username</small></a-descriptions-item><a-descriptions-item label="考勤人员编号">{{ selected.attendanceIdentity?.externalPersonId || '未登记' }}</a-descriptions-item><a-descriptions-item label="考勤来源">{{ selected.attendanceIdentity?.source || '未登记' }} / {{ selected.attendanceIdentity?.namespace || '未登记' }}</a-descriptions-item><a-descriptions-item label="设备侧人员编号">{{ selected.deviceId || '未登记' }}</a-descriptions-item><a-descriptions-item label="飞书身份">{{ selected.feishuId || '尚未绑定' }}</a-descriptions-item></a-descriptions></a-collapse-panel></a-collapse>
            </a-tab-pane>
            <a-tab-pane key="account" tab="账号与登录">
              <template v-if="isEmployee && !selected.accountId">
                <h2>为 {{ selected.name }} 开通账号</h2><p class="drawer-note">员工档案已在册，无需重新新增。若已有登录账号，请核验后关联，避免重复开通。</p>
                <a-radio-group v-model:value="accountMode" class="account-mode" :disabled="busy"><a-radio-button value="activate">开通账号</a-radio-button><a-radio-button value="link">关联已有账号</a-radio-button></a-radio-group>
                <a-alert v-if="selected.checked" class="drawer-section" message="员工资料与企业归属已核验。" type="success" show-icon /><a-checkbox v-else v-model:checked="personnelVerified" class="drawer-section" :disabled="busy">已核对工号、公司、部门及企业归属（演示）</a-checkbox>
                <template v-if="accountMode === 'link'"><label class="drawer-field drawer-section">选择已有账号<a-select v-model:value="existingAccount" :options="pendingAccountOptions" placeholder="请选择待员工关联的账号" :disabled="busy" @change="ownershipVerified = false" /></label><a-empty v-if="!pendingAccountOptions.length" description="暂无待关联账号" /><a-checkbox v-model:checked="ownershipVerified" class="drawer-section" :disabled="busy || !existingAccount">已按可靠标识确认该账号属于 {{ selected.name }}</a-checkbox></template>
                <p class="drawer-note drawer-section">{{ accountMode === 'activate' ? '开通后仅展示一次独立演示临时密码。员工首次密码登录须改密，并在本人账号内验证绑定飞书。' : '不按姓名或拼音自动认定归属，不抢占已属于其他员工的账号。' }}</p>
              </template>
              <template v-else-if="isPendingAccount">
                <h2>关联已有员工</h2><p class="drawer-note">{{ selected.name }} 的账号已存在。确认对应员工后继续使用这个账号，不另开账号。</p>
                <label class="drawer-field drawer-section">选择已有员工<a-select v-model:value="targetEmployee" :options="availableEmployees.map(item => ({value: item.id, label: `${item.name} · 工号 ${item.employeeNumber || '待确认'}`}))" placeholder="请选择尚无账号的员工" :disabled="busy" @change="personnelVerified = false; ownershipVerified = false" /></label>
                <a-alert v-if="employeeToLink?.checked" class="drawer-section" message="所选员工资料已核验。" type="success" show-icon /><a-checkbox v-else v-model:checked="personnelVerified" class="drawer-section" :disabled="busy || !targetEmployee">已核对所选员工资料与企业归属</a-checkbox><a-checkbox v-model:checked="ownershipVerified" class="drawer-section" :disabled="busy || !targetEmployee">已按可靠标识确认此账号属于所选员工</a-checkbox><a-empty v-if="!availableEmployees.length" description="所有员工均已关联账号，请先核对归属。" />
              </template>
              <template v-else><a-descriptions :column="1" bordered><a-descriptions-item label="登录账号">{{ selected.accountId }}</a-descriptions-item><a-descriptions-item label="登录名">{{ selected.username || '未设置' }}</a-descriptions-item><a-descriptions-item label="账号状态"><a-tag :color="accountStatus[1]">{{ accountStatus[0] }}</a-tag></a-descriptions-item><a-descriptions-item label="密码状态">{{ selected.firstPassword ? '临时密码待首次修改' : '已设置，当前密码不可查看' }}</a-descriptions-item><a-descriptions-item label="飞书绑定">{{ selected.bound ? '已绑定' : '未绑定，由员工本人验证后绑定' }}</a-descriptions-item></a-descriptions><p class="drawer-note drawer-section">管理员可重置临时密码。修改密码、找回和飞书绑定仍由当前账号本人验证，查看此员工不会切换本人身份。</p><div v-if="isAdmin && isEmployee && selected.status === 'active'" class="account-admin-actions drawer-section"><a-button @click="beginOperation('reset')">重置临时密码</a-button><a-button danger @click="beginOperation('disable')">停用账号</a-button></div></template>
              <a-alert v-if="formError" class="drawer-section" :message="formError" type="error" show-icon role="alert" />
            </a-tab-pane>
            <a-tab-pane key="apps" tab="应用使用"><AppUsageList v-if="isEmployee" :employee-id="employeeId" @modify="modify" /><a-empty v-else :description="isPendingAccount ? '员工归属待确认，目前仅提供基础体验。' : '该账号用于服务或应急管理，不按员工分配普通应用。'" /></a-tab-pane>
            <a-tab-pane key="history" tab="变更记录"><a-timeline v-if="logs.length" class="employee-history"><a-timeline-item v-for="item in logs" :key="item.id"><p>{{ businessText(item.label) }}</p><span>{{ item.time }} · {{ item.actor }}</span></a-timeline-item></a-timeline><a-empty v-else description="暂无这位员工的变更记录" /></a-tab-pane>
          </a-tabs>
        </div>
      </div>
      <div v-if="!editingApp || temporaryPassword" class="employee-drawer-footer">
        <template v-if="temporaryPassword"><a-button type="primary" @click="temporaryPassword = ''">已查看，清空临时密码</a-button></template>
        <template v-else-if="operation"><a-button type="primary" :disabled="!operationAllowed" :loading="busy" @click="performOperation">{{ operation === 'transfer' ? '确认调岗' : operation === 'verify' ? '确认核验' : operation === 'disable' ? '确认停用账号' : '确认重置' }}</a-button><a-button :disabled="busy" @click="operation = ''; formError = ''">取消</a-button></template>
        <template v-else-if="tab === 'account' && isEmployee && !selected.accountId"><a-button type="primary" :loading="busy" :disabled="!canOpenAccount" @click="openAccount">{{ accountMode === 'activate' ? '确认开通账号' : '确认关联账号' }}</a-button><a-button :disabled="busy" @click="close">关闭</a-button></template>
        <template v-else-if="tab === 'account' && isPendingAccount"><a-button type="primary" :loading="busy" :disabled="!canLinkPending" @click="linkPendingAccount">确认关联员工</a-button><a-button :disabled="busy" @click="close">关闭</a-button></template>
        <template v-else><a-button v-if="isAdmin && isEmployee && tab === 'basic'" @click="beginOperation('transfer')">调岗</a-button><a-button v-if="isAdmin && isEmployee && tab === 'basic' && !selected.checked" @click="beginOperation('verify')">核验员工资料</a-button><a-button :disabled="busy" @click="close">关闭</a-button></template>
      </div>
    </template>
    <a-empty v-else description="未找到员工或账号，请关闭后重新选择。" />
  </a-drawer>
</template>
<style scoped>
.employee-drawer-scroll{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain}.drawer-inner{padding:24px}.drawer-work-settings{min-height:100%;box-sizing:border-box}.drawer-inner h2{font-size:20px;line-height:28px;margin:0 0 16px}.drawer-identity-strip{display:flex;justify-content:space-between;align-items:center;gap:16px;color:#617065;font-size:14px;line-height:22px;margin-bottom:14px}.employee-detail-tabs :deep(.ant-tabs-tab){font-size:16px;padding:12px 0}.employee-detail-tabs :deep(.ant-tabs-nav){margin-bottom:24px}.employee-detail-tabs :deep(.ant-descriptions-item-label),.employee-detail-tabs :deep(.ant-descriptions-item-content),.drawer-inner :deep(.ant-descriptions-item-label),.drawer-inner :deep(.ant-descriptions-item-content){font-size:14px;line-height:22px;padding:13px 16px;overflow-wrap:anywhere}.drawer-inner :deep(.ant-descriptions-item-label){width:142px;white-space:nowrap;color:#66746a;background:#f8faf7}.drawer-inner :deep(.ant-descriptions-item-content){font-size:16px;color:#334a3b}.drawer-inner :deep(.ant-tag){font-size:14px;line-height:24px}.drawer-note{font-size:14px;line-height:22px;color:#65746a;margin:0}.drawer-section{margin-top:24px}.stack{display:flex;flex-direction:column;gap:16px}.drawer-field{display:flex;flex-direction:column;gap:8px;font-size:14px;line-height:22px;color:#53695a}.drawer-inner :deep(.ant-checkbox-wrapper){font-size:14px;line-height:22px}.account-mode{display:flex;margin-top:24px}.account-mode :deep(.ant-radio-button-wrapper){flex:1;text-align:center;font-size:16px;height:40px;line-height:38px}.account-admin-actions{display:flex;flex-wrap:wrap;gap:12px}.employee-drawer-footer{flex-shrink:0;display:flex;gap:12px;align-items:center;flex-wrap:wrap;border-top:1px solid #e3e9e1;background:white;padding:16px 24px}.employee-drawer-footer .ant-btn{min-width:96px;font-size:16px;height:40px}.temporary-token{font-family:ui-monospace,SFMono-Regular,monospace;font-size:24px;line-height:34px;overflow-wrap:anywhere;background:#f0f6ef;border:1px solid #dce7da;border-radius:8px;padding:20px;color:#2f5e3d}.drawer-back{display:flex;align-items:center;gap:8px;border:0;background:none;color:#4e795d;font:inherit;font-size:14px;padding:0;cursor:pointer;align-self:flex-start}.drawer-back:focus-visible{outline:2px solid #5b9870;outline-offset:5px}.transfer-direction{display:flex;gap:12px;flex-wrap:wrap;font-size:16px;line-height:24px;border:1px solid #e1e8de;background:#f7faf5;border-radius:8px;padding:16px}.transfer-direction span:first-child{color:#6b7b6d}.transfer-direction strong{font-weight:500;color:#3a6345}.transfer-preview{padding:16px;border:1px solid #e2e8df;border-radius:8px}.transfer-preview h3{font-size:16px;line-height:24px;margin:0 0 12px;font-weight:600}.transfer-preview>div{display:grid;grid-template-columns:64px 1fr;gap:12px;margin-top:10px}.transfer-preview>div>span{font-size:14px;color:#778275}.transfer-preview p{font-size:16px;line-height:24px;margin:0;overflow-wrap:anywhere}.preserved-settings{padding:16px;background:#f7faf5;border-radius:8px;font-size:14px;line-height:22px;color:#5c6d5e}.preserved-settings strong{color:#3b5940;font-weight:500}.preserved-settings ul{margin:12px 0 0;padding-left:20px}.preserved-settings li+li{margin-top:10px}.preserved-settings p{margin:10px 0 0}.association-info :deep(.ant-collapse-header){padding-left:0!important;font-size:14px!important}.association-info :deep(.ant-collapse-content-box){padding:0!important}.association-info small{display:block;color:#819080;font-size:14px;line-height:22px;margin-top:4px}.employee-history p{margin:0 0 6px;font-size:16px;line-height:24px}.employee-history span{font-size:14px;color:#798578}.drawer-inner :deep(.ant-alert){font-size:14px;line-height:22px}.drawer-inner :deep(.ant-btn),.drawer-inner :deep(.ant-select){font-size:16px}
@media(max-width:700px){.drawer-inner{padding:16px}.employee-drawer-footer{padding:16px}.drawer-inner :deep(.ant-descriptions-item-label){width:115px;padding:12px}.drawer-inner :deep(.ant-descriptions-item-content){padding:12px}.employee-detail-tabs :deep(.ant-tabs-tab){font-size:14px}.employee-detail-tabs :deep(.ant-tabs-nav-list){gap:0}.employee-detail-tabs :deep(.ant-tabs-tab+.ant-tabs-tab){margin-left:20px}.temporary-token{font-size:20px}.transfer-preview>div{grid-template-columns:1fr;gap:4px}}
:global(.employee-detail-drawer .ant-drawer-title){font-size:20px;line-height:28px;overflow-wrap:anywhere}:global(.employee-detail-drawer .ant-drawer-header){padding:20px 24px}
@media(max-width:700px){:global(.employee-detail-drawer .ant-drawer-content-wrapper){width:100vw!important;max-width:100vw!important}}
</style>
