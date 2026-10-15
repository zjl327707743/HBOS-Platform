<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { state, ui, isAdmin, currentUser, deptName, createEmployee } from '../model.js'

const emit = defineEmits(['open'])
const category = ref('employees'), search = ref(''), department = ref('all'), accountStatus = ref('all')
const page = ref(1), subjectPage = ref(1), pageSize = 8
const createOpen = ref(false), formError = ref(''), working = ref(false)
const emptyDraft = () => ({ name: '', employeeNumber: '', company: '', departmentId: undefined, gender: undefined, position: '', birthDate: '', employmentDate: '' })
const draft = reactive(emptyDraft())
const busy = computed(() => ui.busy || working.value)
const confirmedDepartment = item => item && item.confirmed !== false && !['pending', 'unknown', 'unconfirmed'].includes(item.status) && !item.unmapped
const departmentOptions = computed(() => state.depts.map(item => ({ value: item.id, label: `${item.name}${confirmedDepartment(item) ? '' : '（尚未确认）'}`, disabled: !confirmedDepartment(item) })))
const visibleEmployees = computed(() => state.employees.filter(item => isAdmin.value || item.id === currentUser.value?.id))
const pendingAccounts = computed(() => state.nonEmployeeAccounts.filter(item => item.subjectType === 'pending-employee'))
const otherAccounts = computed(() => state.nonEmployeeAccounts.filter(item => item.subjectType !== 'pending-employee'))
const attendanceState = employee => ({ confirmed: ['已关联', 'green'], conflict: ['需处理', 'red'] }[employee.attendanceIdentity?.status] || ['待确认', 'gold'])
const accountState = employee => !employee.accountId ? ['未开通', 'default'] : employee.status === 'disabled' ? ['已停用', 'default'] : ['已开通', 'green']
const rows = computed(() => visibleEmployees.value.filter(item => {
  const query = search.value.trim().toLowerCase()
  return (!query || [item.name, item.employeeNumber, item.username, item.accountId].join(' ').toLowerCase().includes(query))
    && (department.value === 'all' || item.departmentId === department.value)
    && (accountStatus.value === 'all' || (accountStatus.value === 'unopened' ? !item.accountId : item.accountId && item.status === accountStatus.value))
}))
const subjectRows = computed(() => (category.value === 'pending' ? pendingAccounts.value : otherAccounts.value).filter(item => !search.value.trim() || [item.name, item.username, item.accountId].join(' ').toLowerCase().includes(search.value.trim().toLowerCase())))
const totals = computed(() => ({ active: visibleEmployees.value.filter(item => item.accountId && item.status === 'active').length, unopened: visibleEmployees.value.filter(item => !item.accountId).length, attendancePending: visibleEmployees.value.filter(item => item.attendanceIdentity?.status !== 'confirmed').length }))
const columns = [
  { title: '姓名 / 工号', key: 'person', width: '23%' }, { title: '部门 / 岗位', key: 'department', width: '27%' },
  { title: '账号状态', key: 'account', width: '15%' }, { title: '考勤关联', key: 'attendance', width: '15%' }, { title: '操作', key: 'actions', width: '20%' },
]
const subjectColumns = [{ title: '账号名称', key: 'name', width: '27%' }, { title: '登录账号', key: 'login', width: '35%' }, { title: '状态', key: 'status', width: '20%' }, { title: '操作', key: 'actions', width: '18%' }]
const pagination = computed(() => ({ current: page.value, pageSize, total: rows.value.length, showSizeChanger: false, showTotal: total => `共 ${total} 名员工`, onChange: value => { page.value = value } }))
const subjectPagination = computed(() => ({ current: subjectPage.value, pageSize, total: subjectRows.value.length, showSizeChanger: false, showTotal: total => `共 ${total} 个账号`, onChange: value => { subjectPage.value = value } }))
watch([search, department, accountStatus], () => { page.value = 1; subjectPage.value = 1 })
watch(category, () => { search.value = ''; subjectPage.value = 1 })
watch(() => rows.value.length, length => { page.value = Math.min(page.value, Math.max(1, Math.ceil(length / pageSize))) })
watch(() => currentUser.value?.id, () => { createOpen.value = false })
function openEmployee(item, tab = 'basic') { emit('open', item.id, tab, null) }
function beginCreate() { Object.assign(draft, emptyDraft()); formError.value = ''; createOpen.value = true }
async function saveEmployee() {
  if (!isAdmin.value || busy.value) return
  formError.value = ''
  const labels = { name: '姓名', employeeNumber: '工号', company: '公司', departmentId: '主部门', gender: '性别', position: '岗位', birthDate: '生日', employmentDate: '入职日期' }
  const missing = Object.entries(labels).filter(([key]) => !String(draft[key] || '').trim()).map(([, label]) => label)
  if (missing.length) { formError.value = `请填写：${missing.join('、')}。`; return }
  if (!draft.name.startsWith('演示')) { formError.value = '请使用“演示”开头的合成姓名。'; return }
  if (!confirmedDepartment(state.depts.find(item => item.id === draft.departmentId))) { formError.value = '这个部门尚未确认，暂不能用于分配人员或应用权限。'; return }
  if (draft.birthDate >= draft.employmentDate) { formError.value = '生日必须早于入职日期，请核对填写的日期。'; return }
  working.value = true
  try {
    const result = await createEmployee({ ...draft, employeeNumber: String(draft.employeeNumber) })
    if (!result.ok) { formError.value = result.error; return }
    createOpen.value = false
    message.success('员工档案已保存，尚未开通账号。')
  } catch { formError.value = '员工档案未保存，请重试。' }
  finally { working.value = false }
}
</script>

<template>
  <div class="page-heading people-heading"><div><h1>员工管理</h1><p class="muted">查看员工资料、开通账号与应用安排。</p></div><a-button v-if="isAdmin" type="primary" @click="beginCreate"><PlusOutlined />新增员工</a-button></div>
  <div class="people-summary" aria-label="员工统计"><span>员工 <b>{{ visibleEmployees.length }}</b> 人</span><span>已开通 <b>{{ totals.active }}</b></span><span>未开通 <b>{{ totals.unopened }}</b></span><span>考勤待确认或需处理 <b>{{ totals.attendancePending }}</b></span></div>
  <section class="panel people-panel">
    <a-tabs v-model:activeKey="category" class="people-tabs"><a-tab-pane key="employees" :tab="`员工（${visibleEmployees.length}）`" /><a-tab-pane v-if="isAdmin" key="pending" :tab="`待处理（${pendingAccounts.length}）`" /><a-tab-pane v-if="isAdmin" key="other" :tab="`其他账号（${otherAccounts.length}）`" /></a-tabs>
    <div class="people-toolbar"><a-input v-model:value="search" :placeholder="category === 'employees' ? '搜索姓名、工号或登录名' : '搜索账号名称或登录名'" :aria-label="category === 'employees' ? '搜索员工' : '搜索账号'" allow-clear class="people-search"><template #prefix><SearchOutlined /></template></a-input><template v-if="category === 'employees'"><a-select v-model:value="department" aria-label="筛选部门" class="department-filter"><a-select-option value="all">全部部门</a-select-option><a-select-option v-for="item in state.depts" :key="item.id" :value="item.id">{{ item.name }}</a-select-option></a-select><a-select v-model:value="accountStatus" aria-label="筛选账号状态" class="account-filter"><a-select-option value="all">全部账号状态</a-select-option><a-select-option value="active">已开通</a-select-option><a-select-option value="unopened">未开通</a-select-option><a-select-option value="disabled">已停用</a-select-option></a-select></template></div>
    <div v-if="category === 'employees'" class="people-table-region">
      <a-table :columns="columns" :data-source="rows" row-key="id" :pagination="pagination" table-layout="fixed" :locale="{ emptyText: '没有符合条件的员工，请调整搜索或筛选。' }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'person'"><button class="employee-name" :aria-label="`查看${record.name}的完整资料，工号${record.employeeNumber || '待确认'}`" @click="openEmployee(record)"><span class="employee-avatar" aria-hidden="true">{{ record.name.slice(-1) }}</span><span class="employee-name-copy"><strong>{{ record.name }}</strong><small>{{ record.employeeNumber || '工号待确认' }}</small></span></button></template>
          <template v-else-if="column.key === 'department'"><button class="department-name" :aria-label="`查看完整部门及岗位：${deptName(record.departmentId)}，${record.position}`" @click="openEmployee(record)">{{ deptName(record.departmentId) }}</button><span class="cell-secondary">{{ record.position || '岗位待补充' }}</span></template>
          <template v-else-if="column.key === 'account'"><a-tag :color="accountState(record)[1]">{{ accountState(record)[0] }}</a-tag><span v-if="record.firstPassword && record.accountId && record.status === 'active'" class="cell-secondary">首次密码待改</span></template>
          <template v-else-if="column.key === 'attendance'"><a-tag :color="attendanceState(record)[1]">{{ attendanceState(record)[0] }}</a-tag></template>
          <template v-else-if="column.key === 'actions'"><div class="row-actions"><a-button v-if="!record.accountId && isAdmin" type="link" @click="openEmployee(record, 'account')">开通账号</a-button><a-button type="link" @click="openEmployee(record)">查看</a-button></div></template>
        </template>
      </a-table>
    </div>
    <template v-else><p class="category-description">{{ category === 'pending' ? '这些账号尚未确认对应员工，暂不能查看考勤；请核验后关联已有员工。' : '服务和应急管理账号独立列示，不计入员工人数。' }}</p><div class="people-table-region"><a-table :columns="subjectColumns" :data-source="subjectRows" row-key="id" :pagination="subjectPagination" table-layout="fixed" :locale="{ emptyText: category === 'pending' ? '暂无待处理账号。' : '暂无其他账号。' }"><template #bodyCell="{ column, record }"><template v-if="column.key === 'name'"><button class="plain-subject-name" @click="openEmployee(record)">{{ record.name }}</button><span class="cell-secondary">{{ record.subjectType === 'pending-employee' ? '员工待关联' : '服务 / 应急管理' }}</span></template><template v-else-if="column.key === 'login'"><span class="account-text">{{ record.accountId }}</span><span class="cell-secondary">{{ record.username || '未设置登录名' }}</span></template><template v-else-if="column.key === 'status'"><a-tag :color="category === 'pending' ? 'gold' : 'default'">{{ category === 'pending' ? '待确认归属' : record.status === 'disabled' ? '已停用' : '管理用途' }}</a-tag></template><template v-else-if="column.key === 'actions'"><a-button type="link" @click="openEmployee(record, category === 'pending' ? 'account' : 'basic')">{{ category === 'pending' ? '关联员工' : '查看' }}</a-button></template></template></a-table></div></template>
    <p class="people-footnote">考勤关联显示身份核验状态；没有打卡记录不代表尚未关联。</p>
  </section>
  <a-modal v-model:open="createOpen" title="新增员工" :width="680" :confirm-loading="busy" :closable="!busy" :mask-closable="false" ok-text="保存员工档案" cancel-text="取消" @ok="saveEmployee">
    <p class="new-employee-note">仅填写合成演示资料。保存档案后，可再为这位员工开通账号。</p>
    <a-form layout="vertical" class="new-employee-form"><div class="new-employee-grid"><a-form-item label="姓名" required><a-input v-model:value="draft.name" placeholder="例如：演示新同事" :disabled="busy" /></a-form-item><a-form-item label="工号" required><a-input v-model:value="draft.employeeNumber" placeholder="按原编号填写，保留前导零" :disabled="busy" /></a-form-item><a-form-item label="公司" required><a-input v-model:value="draft.company" placeholder="填写合成公司名称" :disabled="busy" /></a-form-item><a-form-item label="主部门" required><a-select v-model:value="draft.departmentId" :options="departmentOptions" placeholder="请选择部门" :disabled="busy" /></a-form-item><a-form-item label="岗位" required><a-input v-model:value="draft.position" placeholder="填写岗位" :disabled="busy" /></a-form-item><a-form-item label="性别" required><a-select v-model:value="draft.gender" :options="['女', '男', '未说明'].map(value => ({ value, label: value }))" placeholder="请选择" :disabled="busy" /></a-form-item><a-form-item label="生日" required><a-date-picker v-model:value="draft.birthDate" value-format="YYYY-MM-DD" placeholder="手动选择生日" :disabled="busy" /></a-form-item><a-form-item label="入职日期" required><a-date-picker v-model:value="draft.employmentDate" value-format="YYYY-MM-DD" placeholder="手动选择入职日期" :disabled="busy" /></a-form-item></div></a-form>
    <a-alert v-if="formError" :message="formError" type="error" show-icon role="alert" />
  </a-modal>
</template>
<style scoped>
.people-heading h1{margin:0 0 8px}.people-summary{display:flex;flex-wrap:wrap;gap:12px 24px;margin:0 0 24px;padding:12px 0;font-size:14px;line-height:22px;color:#59675f;border-bottom:1px solid #dfe5e0}.people-summary b{font-size:16px;font-weight:600;color:#2c4838;margin:0 3px}.people-panel{padding:0!important;overflow:hidden}.people-tabs{padding:0 24px}.people-tabs :deep(.ant-tabs-nav){margin:0}.people-tabs :deep(.ant-tabs-content-holder){display:none}.people-tabs :deep(.ant-tabs-tab){font-size:16px;padding:18px 0}.people-toolbar{display:flex;gap:12px;flex-wrap:wrap;padding:24px;align-items:center}.people-search{width:320px;max-width:100%}.department-filter{width:200px;max-width:100%}.account-filter{width:180px;max-width:100%}.people-table-region{overflow-x:auto;max-width:100%}.people-table-region :deep(.ant-table){font-size:16px;line-height:24px}.people-table-region :deep(.ant-table-thead>tr>th){font-size:14px;color:#66736b;background:#f6f8f5;padding:14px 16px;white-space:nowrap}.people-table-region :deep(.ant-table-tbody>tr>td){padding:16px;vertical-align:middle}.people-table-region :deep(.ant-table-tbody>tr>td:first-child),.people-table-region :deep(.ant-table-thead>tr>th:first-child){padding-left:24px}.people-table-region :deep(.ant-table-pagination){padding:0 24px;margin:20px 0}.employee-name{display:flex;align-items:center;gap:10px;width:100%;border:0;background:none;text-align:left;padding:0;cursor:pointer;color:#294b39;font:inherit}.employee-avatar{width:34px;height:34px;display:grid;place-items:center;flex-shrink:0;background:#eaf2eb;border-radius:10px;color:#55765c;font-size:14px}.employee-name-copy{min-width:0}.employee-name-copy strong{font-weight:500;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;line-height:24px;overflow-wrap:anywhere}.employee-name-copy small,.cell-secondary{display:block;font-size:14px;line-height:22px;color:#6f7b73;margin-top:4px}.employee-name-copy small{white-space:nowrap}.department-name{border:0;background:transparent;padding:0;text-align:left;color:#374d40;font:inherit;cursor:pointer;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}.row-actions{display:flex;gap:2px;align-items:center;flex-wrap:wrap}.row-actions .ant-btn{padding:0 4px;font-size:16px;height:32px;white-space:nowrap}.people-panel :deep(.ant-tag){font-size:14px;line-height:24px;padding:0 6px;margin-right:0;white-space:nowrap}.people-footnote{margin:0;padding:16px 24px;border-top:1px solid #edf0eb;font-size:14px;line-height:22px;color:#768178}.category-description{padding:0 24px;font-size:14px;line-height:22px;color:#6c786f}.plain-subject-name{border:0;background:none;padding:0;text-align:left;font:inherit;color:#356246;cursor:pointer;overflow-wrap:anywhere}.account-text{overflow-wrap:anywhere;font-size:14px;line-height:22px}.new-employee-note{font-size:14px;line-height:22px;color:#637368;margin-bottom:24px}.new-employee-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}.new-employee-form :deep(.ant-form-item-label>label){font-size:14px}.new-employee-form :deep(.ant-picker){width:100%}.employee-name:focus-visible,.department-name:focus-visible,.plain-subject-name:focus-visible{outline:2px solid #5f9871;outline-offset:4px;border-radius:4px}
@media(max-width:1100px){.people-search{width:100%}.department-filter,.account-filter{flex:1;min-width:180px}.employee-name{gap:7px}.employee-avatar{display:none}.people-table-region :deep(.ant-table-tbody>tr>td){padding:14px 12px}.people-table-region :deep(.ant-table-thead>tr>th){padding-left:12px;padding-right:12px}}
@media(max-width:700px){.people-tabs,.people-toolbar{padding-left:16px;padding-right:16px}.people-table-region :deep(.ant-table){min-width:690px}.people-heading{flex-wrap:wrap;gap:16px}.new-employee-grid{grid-template-columns:1fr}.people-summary{gap:8px 18px}.people-footnote{padding:16px}.people-tabs :deep(.ant-tabs-tab){font-size:14px}}
</style>
