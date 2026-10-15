<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, PlusOutlined, ArrowRightOutlined, UserOutlined } from '@ant-design/icons-vue'
import {
  state, ui, allSubjects, currentUser, isAdmin, deptName, effective, scopeLabel,
  saveDemo, activate, transfer, disable, resetPassword, createEmployee, linkExistingAccount,
} from '../model'
import AccountSecurity from './AccountSecurity.vue'

const emit = defineEmits(['permissions', 'employee-view'])
const search = ref('')
const deptFilter = ref('all')
const statusFilter = ref('all')
const category = ref('employees')
const selectedId = ref(null)
const selected = computed(() => state.employees.find(employee => employee.id === selectedId.value) || null)
const tab = ref('basic')
const action = ref('')
const targetDepartment = ref('')
const checked = ref(false)
const accountTargetId = ref('')
const accountMode = ref('activate')
const linkAccount = ref('')
const ownershipConfirmed = ref(false)
const formError = ref('')
const temp = ref('')
const tempRecipient = ref('')
const subjectId = ref(null)
const accountSubject = computed(() => (state.nonEmployeeAccounts || []).find(subject => subject.id === subjectId.value) || null)
const accountSubjectTab = ref('identity')
const draft = reactive({
  name: '演示员工06', employeeNumber: '', company: '演示公司', departmentId: undefined,
  gender: undefined, birthDate: '', employmentDate: '', position: '',
})
const statuses = {
  active: ['已开通', 'success'], pending: ['尚未开户 / 待关联', 'warning'], disabled: ['已停用', 'default'],
}
const titles = {
  new: '新增合成员工档案', account: '为已有员工开户 / 关联已有账号', verify: '核验企业人员',
  activate: '为已有员工受控开户', link: '关联已有 User', transfer: '调岗影响预览',
  disable: '停用账号', reset: '重置演示临时密码',
}
const visibleEmployees = computed(() => state.employees.filter(employee => isAdmin.value || employee.id === currentUser.value?.id))
const rows = computed(() => visibleEmployees.value.filter(employee => {
  const text = [employee.name, employee.code, employee.employeeId, employee.employeeNumber, employee.accountId, employee.username].join(' ')
  return (!search.value || text.toLowerCase().includes(search.value.toLowerCase()))
    && (deptFilter.value === 'all' || employee.departmentId === deptFilter.value)
    && (statusFilter.value === 'all' || (statusFilter.value === 'unlinked' ? !employee.accountId : employee.status === statusFilter.value && !!employee.accountId))
}))
const activeEmployeeAccounts = computed(() => visibleEmployees.value.filter(employee => employee.accountId && employee.status === 'active'))
const unlinkedEmployees = computed(() => state.employees.filter(employee => !employee.accountId))
const pendingEmployeeUsers = computed(() => (state.nonEmployeeAccounts || []).filter(subject => subject.subjectType === 'pending-employee'))
const nonEmployeeSubjects = computed(() => (state.nonEmployeeAccounts || []).filter(subject => subject.subjectType !== 'pending-employee'))
const accountTarget = computed(() => action.value === 'account' ? state.employees.find(employee => employee.id === accountTargetId.value) : selected.value)
const selectedAccountMode = computed(() => action.value === 'account' ? accountMode.value : action.value)
const accountOptions = computed(() => allSubjects.value.filter(subject => subject.accountId && subject.subjectType !== 'service').map(subject => ({
  value: subject.accountId,
  label: `${subject.accountId} · ${subject.subjectType === 'pending-employee' ? '待 Employee 关联' : `已关联 ${subject.name}（冲突校验）`}`,
})))
const permissions = computed(() => selected.value ? state.apps.map(app => ({ ...app, result: effective(selected.value, app.id, '*') })) : [])
const logs = computed(() => state.logs.filter(log => log.label.includes(selected.value?.name || 'NOT_MATCH')).slice(0, 15))
const canSubmit = computed(() => {
  if (!isAdmin.value || ui.busy) return false
  if (action.value === 'verify') return checked.value
  if (['account', 'activate', 'link'].includes(action.value)) {
    return !!accountTarget.value && !accountTarget.value.accountId
      && (selectedAccountMode.value !== 'link' || (!!linkAccount.value && ownershipConfirmed.value))
  }
  return true
})
const attendanceStatus = identity => ({ confirmed: ['已确认', 'green'], pending: ['待确认', 'orange'], conflict: ['冲突 · 禁止认定归属', 'red'] }[identity?.status] || ['未登记', 'default'])
const employeeStatus = employee => !employee.accountId ? ['尚未开户 / 待关联', 'warning'] : statuses[employee.status] || ['待核对', 'default']
const employeePrimaryKey = employee => employee.employeeId || employee.code || '待核对'

watch(() => currentUser.value?.id, () => {
  selectedId.value = null
  subjectId.value = null
  category.value = 'employees'
  action.value = ''
  closeTemporaryPassword()
})

function open(employee) {
  selectedId.value = employee.id
  tab.value = 'basic'
}
function openSubject(subject) {
  subjectId.value = subject.id
  accountSubjectTab.value = 'identity'
}
function begin(type) {
  if (!isAdmin.value) { message.error('此操作仅向演示管理员开放。'); return }
  action.value = type
  checked.value = false
  ownershipConfirmed.value = false
  linkAccount.value = ''
  formError.value = ''
  targetDepartment.value = state.depts.find(dept => dept.id !== selected.value?.departmentId)?.id || selected.value?.departmentId || ''
  if (type === 'account') {
    accountTargetId.value = ''
    accountMode.value = 'activate'
  }
  if (type === 'new') {
    Object.assign(draft, {
      name: '演示员工06', employeeNumber: '', company: '演示公司', departmentId: undefined,
      gender: undefined, birthDate: '', employmentDate: '', position: '',
    })
  }
}
function beginPendingLink(subject) {
  begin('account')
  accountMode.value = 'link'
  linkAccount.value = subject.accountId
}
function validateNewEmployee() {
  const fields = [
    ['name', '合成姓名'], ['employeeNumber', '工号'], ['company', '公司'], ['departmentId', '主部门'],
    ['gender', '性别'], ['birthDate', '生日'], ['employmentDate', '入职日期'], ['position', '岗位'],
  ]
  const missing = fields.filter(([field]) => !String(draft[field] || '').trim()).map(([, label]) => label)
  if (missing.length) return `请完整填写：${missing.join('、')}。生日和入职日期必须由你手动选择。`
  if (!draft.name.startsWith('演示')) return '仅使用“演示”开头的合成姓名，请勿输入真实员工资料。'
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.birthDate) || !/^\d{4}-\d{2}-\d{2}$/.test(draft.employmentDate)) return '请选择有效的合成生日和入职日期。'
  if (draft.birthDate >= draft.employmentDate) return '合成生日必须早于入职日期，请核对所选值。'
  return ''
}
async function perform() {
  if (!isAdmin.value || ui.busy) return
  formError.value = ''
  let result
  const operation = action.value
  const employee = accountTarget.value || selected.value
  const employeeId = employee?.id
  const name = employee?.name
  if (operation === 'new') {
    formError.value = validateNewEmployee()
    if (formError.value) return
    result = await createEmployee({ ...draft, employeeNumber: String(draft.employeeNumber) })
  } else if (!employee) {
    formError.value = '请选择已有 Employee 档案。'
    return
  } else if (operation === 'verify') {
    result = await saveDemo(`${name}企业人员核验完成（合成）`, () => {
      if (!isAdmin.value || !checked.value) throw new Error('请确认演示管理员权限与企业核验依据。')
      state.employees.find(item => item.id === employeeId).checked = true
    })
  } else if (['account', 'activate', 'link'].includes(operation)) {
    if (employee.accountId) { formError.value = '此 Employee 已关联唯一账号，请复用原账号，不得重复开户。'; return }
    if (selectedAccountMode.value === 'link') {
      if (!linkAccount.value || !ownershipConfirmed.value) { formError.value = '请选择已有 User，并明确确认其与此 Employee 的唯一归属。'; return }
      result = await linkExistingAccount(employeeId, linkAccount.value)
    } else result = await activate(employeeId)
  } else if (operation === 'transfer') result = await transfer(employeeId, targetDepartment.value)
  else if (operation === 'disable') result = await disable(employeeId)
  else if (operation === 'reset') result = await resetPassword(employeeId)
  if (result?.ok) {
    if (operation === 'reset' || (['account', 'activate'].includes(operation) && selectedAccountMode.value === 'activate')) {
      temp.value = result.temporaryPassword || `DEMO-${crypto.randomUUID().slice(0, 8)}-Aa!`
      tempRecipient.value = name
    }
    message.success(operation === 'new' ? '合成 Employee 档案已保存；未创建 User。' : '演示已保存到本机')
    action.value = ''
  } else if (result) {
    formError.value = result.error
    message.error(result.error)
  }
}
function closeTemporaryPassword() {
  temp.value = ''
  tempRecipient.value = ''
}
</script>

<template>
  <div class="page-heading">
    <div>
      <div class="kicker">EMPLOYEE & IDENTITY</div>
      <h1>人员管理<span class="heading-pill">合成演示</span></h1>
      <p class="muted">先有 Employee 员工档案，再明确关联唯一 User；尚未开户的员工同样在册。</p>
    </div>
    <div v-if="isAdmin" class="heading-actions">
      <a-button type="primary" size="large" @click="begin('account')">为已有员工开户 / 关联已有账号</a-button>
      <a-button @click="begin('new')"><PlusOutlined />新增 Employee 档案</a-button>
    </div>
  </div>

  <div class="stats-row">
    <div class="stat"><span>员工档案总数</span><strong>{{ visibleEmployees.length }}<small>个 Employee</small></strong><p>包含尚未开户的合成员工</p></div>
    <div class="stat"><span>已开通员工账号</span><strong>{{ activeEmployeeAccounts.length }}<small>个 User</small></strong><p><i class="dot green" />已关联 Employee 且状态可用</p></div>
    <div class="stat"><span>待账号关联的员工</span><strong>{{ visibleEmployees.filter(employee => !employee.accountId).length }}<small>个 Employee</small></strong><p><i class="dot amber" />有员工档案，尚无关联账号</p></div>
    <div class="stat"><span>非员工主体</span><strong>{{ isAdmin ? nonEmployeeSubjects.length : '—' }}<small>个账号</small></strong><p>服务 / 应急管理员单独分类</p></div>
  </div>

  <section class="panel people-panel">
    <a-tabs v-model:activeKey="category" class="category-tabs">
      <a-tab-pane key="employees" :tab="`Employee 档案（${visibleEmployees.length}）`">
        <div class="panel-title"><h2>企业员工档案</h2><span class="muted">{{ rows.length }} 条结果 · 点击姓名查看详情</span></div>
        <div class="toolbar">
          <a-input v-model:value="search" placeholder="搜索合成姓名、工号、档案编号或账号" aria-label="搜索 Employee 员工档案" allow-clear style="width:340px"><template #prefix><SearchOutlined /></template></a-input>
          <a-select v-model:value="deptFilter" aria-label="部门筛选" style="width:180px"><a-select-option value="all">全部部门</a-select-option><a-select-option v-for="dept in state.depts" :key="dept.id" :value="dept.id">{{ dept.name }}</a-select-option></a-select>
          <a-select v-model:value="statusFilter" aria-label="账号关联状态筛选" style="width:175px"><a-select-option value="all">全部账号状态</a-select-option><a-select-option value="active">已开通员工账号</a-select-option><a-select-option value="unlinked">尚未开户 / 待关联</a-select-option><a-select-option value="disabled">已停用账号</a-select-option></a-select>
        </div>
        <div class="table-scroll">
          <table class="people-table">
            <thead><tr><th>姓名 / 员工工号</th><th>主部门 / 岗位</th><th>Employee–User 关联</th><th>飞书绑定</th><th>核对状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="employee in rows" :key="employee.id">
                <td><button class="person-link" @click="open(employee)"><span class="avatar">{{ employee.name.slice(-2) }}</span><span><b>{{ employee.name }}</b><small>{{ employee.employeeNumber || '工号待核对' }}</small></span></button></td>
                <td><b class="department-text">{{ deptName(employee.departmentId) }}</b><small>{{ employee.position }}<span v-if="employee.secondaryDepartments?.length"> · 兼岗 {{ employee.secondaryDepartments.map(deptName).join('、') }}</span></small></td>
                <td><a-tag :color="employeeStatus(employee)[1]">{{ employeeStatus(employee)[0] }}</a-tag><small>{{ employee.accountId ? '已有 User，复用原账号' : '档案已存在，无需重复增人' }}</small><small v-if="employee.firstPassword && employee.accountId && employee.status === 'active'">首次密码待改密</small></td>
                <td><span :class="employee.bound ? 'binding-good' : 'muted'"><i class="dot" :class="employee.bound ? 'green' : 'gray'" />{{ employee.bound ? '已绑定' : '未绑定' }}</span></td>
                <td><a-tag v-if="!employee.checked" color="orange">待核对</a-tag><span v-else class="muted">已核验（演示）</span></td>
                <td><a-button type="link" @click="open(employee)">查看<ArrowRightOutlined /></a-button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <a-empty v-if="!rows.length" description="没有符合筛选条件的合成员工档案" />
        <div class="table-footer">工号按字符串展示，保留前导零。姓名、拼音、手机号和邮箱相同均不作为自动绑定依据。</div>
      </a-tab-pane>

      <a-tab-pane v-if="isAdmin" key="pending-users" :tab="`待 Employee 关联 User（${pendingEmployeeUsers.length}）`">
        <div class="category-content stack">
          <div class="panel-title"><h2>账号已存在，员工归属待确认</h2><span class="muted">不计入 Employee 档案总数</span></div>
          <a-alert type="warning" show-icon message="本企业身份可先开户，Employee 归属未证实时不创建虚假档案、不授予考勤数据。" description="请按可靠工号 / 来源命名空间核验后，关联已有 Employee。不得按姓名或拼音自动选择第一条。" />
          <div v-for="subject in pendingEmployeeUsers" :key="subject.id" class="subject-row">
            <div><strong>{{ subject.name }}</strong><span class="identity-value">{{ subject.accountId }}</span><small>登录别名：{{ subject.username || '尚未设置' }} · Employee.user_id 尚未确认</small></div>
            <a-tag color="orange">待员工关联 · 考勤拒绝</a-tag>
            <div class="subject-actions"><a-button @click="openSubject(subject)">查看账号</a-button><a-button type="primary" @click="beginPendingLink(subject)">关联已有 Employee</a-button></div>
          </div>
          <a-empty v-if="!pendingEmployeeUsers.length" description="暂无待 Employee 关联的合成账号" />
        </div>
      </a-tab-pane>

      <a-tab-pane v-if="isAdmin" key="non-employees" :tab="`非员工主体（${nonEmployeeSubjects.length}）`">
        <div class="category-content stack">
          <div class="panel-title"><h2>非员工账号</h2><span class="muted">独立分类，不伪造 Employee</span></div>
          <a-alert type="info" show-icon message="服务账号与应急管理员不代表在职员工。没有明确 Employee 关联时，不提供“我的考勤”数据。" />
          <div v-for="subject in nonEmployeeSubjects" :key="subject.id" class="subject-row">
            <div><strong>{{ subject.name }}</strong><span class="identity-value">{{ subject.accountId }}</span><small>{{ subject.subjectType === 'service' ? '服务 / 应急管理主体' : '非员工主体' }} · 无 Employee</small></div>
            <a-tag>不计员工人数</a-tag><a-button @click="openSubject(subject)">查看账号与安全状态</a-button>
          </div>
          <a-empty v-if="!nonEmployeeSubjects.length" description="暂无非员工合成账号" />
        </div>
      </a-tab-pane>
    </a-tabs>
  </section>

  <div class="quiet-note"><UserOutlined /><div><b>管理他人安全资料与本人账号安全分开</b><p>管理员可重置临时密码；本人改密、找回及绑定由当前账号完成，不能替换会话主体。</p></div></div>

  <a-drawer :open="!!selected" :title="`${selected?.name || ''} · Employee 详情`" :width="720" :destroy-on-close="true" @close="selectedId = null">
    <template v-if="selected">
      <a-alert message="R4 定向补充 / 合成数据 / 尚未连接 HBOS 后端" type="info" show-icon />
      <a-tabs v-model:activeKey="tab">
        <a-tab-pane key="basic" tab="基本资料">
          <a-descriptions :column="1" bordered size="small">
            <a-descriptions-item label="员工档案编号">{{ employeePrimaryKey(selected) }}</a-descriptions-item>
            <a-descriptions-item label="工号（字符串）">{{ selected.employeeNumber || '待核对' }}</a-descriptions-item>
            <a-descriptions-item label="公司">{{ selected.company || '待核对' }}</a-descriptions-item>
            <a-descriptions-item label="主部门">{{ deptName(selected.departmentId) }}</a-descriptions-item>
            <a-descriptions-item label="兼岗">{{ selected.secondaryDepartments?.map(deptName).join('、') || '无' }} · 不自动叠加主部门预设</a-descriptions-item>
            <a-descriptions-item label="岗位">{{ selected.position }}</a-descriptions-item>
            <a-descriptions-item label="性别">{{ selected.gender || '待补充' }}</a-descriptions-item>
            <a-descriptions-item v-if="isAdmin" label="合成生日">{{ selected.birthDate || '待补充' }}</a-descriptions-item>
            <a-descriptions-item label="入职日期">{{ selected.employmentDate || '待补充' }}</a-descriptions-item>
            <a-descriptions-item label="账号关联状态"><a-tag :color="employeeStatus(selected)[1]">{{ employeeStatus(selected)[0] }}</a-tag>{{ selected.accountId ? '已关联唯一 User' : 'Employee 已存在，尚未关联 User' }}</a-descriptions-item>
            <a-descriptions-item label="企业人员核验">{{ selected.checked ? '已核验（演示）' : '待核对' }}</a-descriptions-item>
          </a-descriptions>
          <div v-if="isAdmin" class="action-grid">
            <a-button v-if="!selected.checked" @click="begin('verify')">核验企业人员</a-button>
            <a-button v-if="!selected.accountId" type="primary" @click="begin('activate')">为已有员工开户</a-button>
            <a-button v-if="!selected.accountId" @click="begin('link')">关联已有账号</a-button>
            <a-button @click="begin('transfer')">调岗</a-button>
            <a-button v-if="selected.accountId && selected.status === 'active'" @click="begin('reset')">重置临时密码</a-button>
            <a-button v-if="selected.accountId && selected.status === 'active'" danger @click="begin('disable')">停用账号</a-button>
          </div>
          <p class="detail-note">管理员预开通不自动绑定飞书；员工登录原账号后自行验证绑定。本企业飞书首次开户也必须明确关联 Employee，才能读取本人考勤。</p>
        </a-tab-pane>

        <a-tab-pane v-if="isAdmin" key="identity" tab="身份与业务关联">
          <div class="identity-chain">考勤来源身份 → Employee.name ← Employee.user_id → User.name</div>
          <a-descriptions :column="1" bordered size="small">
            <a-descriptions-item label="Employee.name">{{ employeePrimaryKey(selected) }}</a-descriptions-item>
            <a-descriptions-item label="演示 code">{{ selected.code }}</a-descriptions-item>
            <a-descriptions-item label="Employee.employee_number"><code>{{ selected.employeeNumber || '未登记' }}</code><div class="field-note">保留前导零，不转换为数值。</div></a-descriptions-item>
            <a-descriptions-item label="主部门 / Company">{{ deptName(selected.departmentId) }} / {{ selected.company || '待核对' }}</a-descriptions-item>
            <a-descriptions-item label="User.name（账号主键）"><span class="identity-value">{{ selected.accountId || '尚未开户 / 未关联' }}</span></a-descriptions-item>
            <a-descriptions-item label="User.username（登录别名）">{{ selected.username || '未设置' }}<div class="field-note">拼音别名不是 Employee 主键，也不用于考勤归属。</div></a-descriptions-item>
            <a-descriptions-item label="Employee.user_id">{{ selected.accountId || '空 · 未关联' }}<div class="field-note">{{ selected.accountId ? '当前明确关联同一 User；不会因姓名变化重写档案主键。' : '需要受控开户，或核验后关联已存在 User；不会自动增人。' }}</div></a-descriptions-item>
            <a-descriptions-item label="飞书绑定"><a-tag :color="selected.bound ? 'green' : 'orange'">{{ selected.bound ? '已绑定' : '未绑定' }}</a-tag><span class="identity-value">{{ selected.bound ? selected.feishuId : '由本人登录后验证绑定' }}</span><div class="field-note">通讯录导出的用户 ID 未经核验不能视为 OAuth open_id。</div></a-descriptions-item>
          </a-descriptions>
          <h3 class="identity-subheading">考勤来源关联</h3>
          <a-descriptions :column="1" bordered size="small">
            <a-descriptions-item label="来源 source">{{ selected.attendanceIdentity?.source || '未登记' }}</a-descriptions-item>
            <a-descriptions-item label="来源命名空间 namespace"><span class="identity-value">{{ selected.attendanceIdentity?.namespace || '未登记' }}</span></a-descriptions-item>
            <a-descriptions-item label="外部人员 ID"><code>{{ selected.attendanceIdentity?.externalPersonId || '未登记' }}</code><div class="field-note">只在所属来源 / 企业命名空间内核验唯一性。</div></a-descriptions-item>
            <a-descriptions-item label="来源工号 employee_num"><code>{{ selected.attendanceIdentity?.employeeNum || '未登记' }}</code></a-descriptions-item>
            <a-descriptions-item label="关联确认状态"><a-tag :color="attendanceStatus(selected.attendanceIdentity)[1]">{{ attendanceStatus(selected.attendanceIdentity)[0] }}</a-tag></a-descriptions-item>
            <a-descriptions-item label="Attendance Device ID">{{ selected.deviceId || '未登记' }}<div class="field-note">设备侧标识、工号与来源人员 ID 语义不同，不强行改为同一值。</div></a-descriptions-item>
          </a-descriptions>
          <a-alert class="identity-alert" type="warning" show-icon message="无可靠关联或身份冲突时拒绝考勤数据；姓名匹配不产生归属证明。" description="本页只展示合成关联，不查询或改写真实 Employee、User、打卡或考勤记录。" />
        </a-tab-pane>

        <a-tab-pane key="security" tab="账号安全">
          <AccountSecurity v-if="selected.accountId" :employee="selected" />
          <a-empty v-else description="Employee 档案已存在，但尚无 User 账号；请先受控开户或关联已有账号。" />
        </a-tab-pane>
        <a-tab-pane key="permissions" tab="有效权限">
          <div v-for="app in permissions" :key="app.id" class="permission-summary"><b>{{ app.name }}</b><a-tag :color="app.result.allowed ? 'green' : 'default'">{{ app.result.allowed ? '可进入' : '不可进入' }}</a-tag><p>{{ app.result.source }} · {{ app.result.scope.map(scopeLabel).join('、') || app.result.reason }}</p><div v-for="operation in app.actions" :key="operation.id" class="compact-right"><span>{{ operation.name }}</span><span>{{ effective(selected, app.id, operation.id).allowed ? '允许' : '禁止' }} · {{ effective(selected, app.id, operation.id).source }}</span></div></div>
          <a-button v-if="isAdmin" type="primary" @click="emit('permissions', selected.id); selectedId = null">配置此人员权限</a-button>
        </a-tab-pane>
        <a-tab-pane v-if="isAdmin" key="history" tab="变更记录"><a-timeline><a-timeline-item v-for="log in logs" :key="log.id"><b>{{ log.label }}</b><p class="muted">{{ log.time }} · {{ log.actor }}</p></a-timeline-item></a-timeline><a-empty v-if="!logs.length" description="暂无此员工的演示变更" /></a-tab-pane>
      </a-tabs>
    </template>
  </a-drawer>

  <a-drawer :open="!!accountSubject && isAdmin" :title="`${accountSubject?.name || ''} · 账号主体`" :width="700" :destroy-on-close="true" @close="subjectId = null">
    <template v-if="accountSubject && isAdmin">
      <a-alert :type="accountSubject.subjectType === 'pending-employee' ? 'warning' : 'info'" show-icon :message="accountSubject.subjectType === 'pending-employee' ? '已有 User，Employee 归属尚未确认；考勤默认拒绝。' : '非员工主体，没有为其伪造 Employee 档案。'" />
      <a-tabs v-model:activeKey="accountSubjectTab">
        <a-tab-pane key="identity" tab="账号身份"><a-descriptions :column="1" bordered size="small"><a-descriptions-item label="主体类型">{{ accountSubject.subjectType === 'pending-employee' ? '待 Employee 关联 User' : '服务 / 应急管理主体' }}</a-descriptions-item><a-descriptions-item label="User.name">{{ accountSubject.accountId }}</a-descriptions-item><a-descriptions-item label="User.username">{{ accountSubject.username || '未设置' }}</a-descriptions-item><a-descriptions-item label="Employee 关联">无 · 不计入员工人数</a-descriptions-item><a-descriptions-item label="飞书绑定">{{ accountSubject.bound ? '已绑定合成身份' : '未绑定' }}</a-descriptions-item></a-descriptions><a-button v-if="accountSubject.subjectType === 'pending-employee'" class="identity-alert" type="primary" @click="beginPendingLink(accountSubject); subjectId = null">核验并关联已有 Employee</a-button></a-tab-pane>
        <a-tab-pane key="security" tab="账号安全"><AccountSecurity :employee="accountSubject" /></a-tab-pane>
      </a-tabs>
    </template>
  </a-drawer>

  <a-modal :open="!!action" :title="titles[action]" :width="action === 'new' ? 660 : 590" :confirm-loading="ui.busy" :closable="!ui.busy" :mask-closable="!ui.busy" :ok-button-props="{ disabled: !canSubmit }" :ok-text="action === 'new' ? '仅保存合成 Employee 档案' : '确认演示操作'" cancel-text="取消" @ok="perform" @cancel="action = ''">
    <div class="operation-body stack">
      <template v-if="action === 'new'">
        <a-alert type="info" show-icon message="仅新增合成员工档案，不自动创建 User。" description="以下必填资料由你明确填写。生日和入职日期不提供默认值，不使用虚构日期补齐真实人员。" />
        <a-form layout="vertical" class="employee-form">
          <div class="form-grid">
            <a-form-item label="合成姓名" required><a-input v-model:value="draft.name" placeholder="演示员工06" :disabled="ui.busy" /></a-form-item>
            <a-form-item label="工号（字符串，保留前导零）" required><a-input v-model:value="draft.employeeNumber" placeholder="例如 00106，由你明确填写" :disabled="ui.busy" /></a-form-item>
            <a-form-item label="公司" required><a-input v-model:value="draft.company" placeholder="仅合成公司" :disabled="ui.busy" /></a-form-item>
            <a-form-item label="主部门" required><a-select v-model:value="draft.departmentId" placeholder="选择合成部门" :options="state.depts.map(dept => ({ value: dept.id, label: dept.name }))" :disabled="ui.busy" /></a-form-item>
            <a-form-item label="性别" required><a-select v-model:value="draft.gender" placeholder="明确选择" :options="['女', '男', '未说明'].map(value => ({ value, label: value }))" :disabled="ui.busy" /></a-form-item>
            <a-form-item label="岗位" required><a-input v-model:value="draft.position" placeholder="填写合成岗位" :disabled="ui.busy" /></a-form-item>
            <a-form-item label="合成生日（手动选择）" required><a-date-picker v-model:value="draft.birthDate" value-format="YYYY-MM-DD" placeholder="请选择合成生日" :disabled="ui.busy" style="width:100%" /></a-form-item>
            <a-form-item label="合成入职日期（手动选择）" required><a-date-picker v-model:value="draft.employmentDate" value-format="YYYY-MM-DD" placeholder="请选择合成入职日期" :disabled="ui.busy" style="width:100%" /></a-form-item>
          </div>
        </a-form>
      </template>
      <template v-if="['account', 'activate', 'link'].includes(action)">
        <template v-if="action === 'account'"><label class="form-label">已有 Employee 档案<a-select v-model:value="accountTargetId" aria-label="选择需要开户或关联账号的已有员工" placeholder="请选择已有员工" :disabled="ui.busy" :options="unlinkedEmployees.map(employee => ({ value: employee.id, label: `${employee.name} · 工号 ${employee.employeeNumber || '待核对'}` }))" @change="ownershipConfirmed = false" /></label><a-empty v-if="!unlinkedEmployees.length" description="所有合成员工均已关联账号，请复用原账号。" /><a-radio-group v-if="accountTarget" v-model:value="accountMode" :disabled="ui.busy" @change="ownershipConfirmed = false; formError = ''"><a-radio-button value="activate">为已有员工开户</a-radio-button><a-radio-button value="link">关联已有账号</a-radio-button></a-radio-group></template>
        <div v-if="accountTarget" class="identity-target"><strong>{{ accountTarget.name }}</strong><span>Employee.name：{{ employeePrimaryKey(accountTarget) }}</span><span>工号：<code>{{ accountTarget.employeeNumber || '待核对' }}</code> · {{ deptName(accountTarget.departmentId) }}</span></div>
        <a-alert v-if="accountTarget && selectedAccountMode === 'activate'" :type="accountTarget.checked ? 'info' : 'warning'" show-icon :message="accountTarget.checked ? '受控创建唯一合成 User，并关联此已有 Employee。' : '此人员待核对；请先完成企业人员核验，开户会被拒绝。'" description="若员工已经通过本企业飞书首次开户，请改用“关联已有账号”，避免重复建户。管理员预开通后，由员工自行验证绑定飞书。" />
        <template v-if="accountTarget && selectedAccountMode === 'link'">
          <p class="detail-note">选择已存在的 User，核验唯一归属。已关联其他 Employee 的账号会被拒绝，不能抢占。</p>
          <label class="form-label">明确选择已有 User<a-select v-model:value="linkAccount" placeholder="请选择现有合成账号" aria-label="选择已存在的合成 User" :options="accountOptions" :disabled="ui.busy" @change="ownershipConfirmed = false" /></label>
          <a-empty v-if="!accountOptions.length" description="没有可选择的合成 User；本操作不会凭姓名自动创建账号。" />
          <a-checkbox v-model:checked="ownershipConfirmed" :disabled="ui.busy || !linkAccount">已按可靠标识确认此 User 与 {{ accountTarget.name }} 的唯一归属，不以姓名 / 拼音相同认定</a-checkbox>
          <a-alert v-if="!accountTarget.checked" type="warning" show-icon message="该 Employee 仍待企业人员核验，关联会被拒绝。" />
        </template>
      </template>
      <a-checkbox v-if="action === 'verify'" v-model:checked="checked">已核对合成名册、工号、公司 / 部门及企业人员归属（无真实写入）</a-checkbox>
      <template v-if="action === 'transfer'"><label class="form-label">新主部门<a-select v-model:value="targetDepartment" aria-label="新主部门" :disabled="ui.busy" :options="state.depts.map(dept => ({ value: dept.id, label: dept.name }))" /></label><div class="impact-box"><b>{{ deptName(selected?.departmentId) }} → {{ deptName(targetDepartment) }}</b><p>原主部门普通继承失效，新部门普通预设生效；个人例外保留，高风险不自动授予。Employee 主键与本人历史归属不改变。</p><div v-for="app in state.apps" :key="app.id"><span>{{ app.name }}：</span>{{ effective({ ...selected, departmentId: targetDepartment }, app.id, '*').allowed ? '新部门可进入' : '新部门不可进入' }}</div></div></template>
      <a-alert v-if="action === 'disable'" message="停用后模拟登录与业务访问拒绝，Employee 及历史记录保留。真实会话撤销与后端拒绝尚未接入。" type="warning" show-icon />
      <a-alert v-if="action === 'reset'" message="将只展示一次新的随机合成临时密码，下次密码入口必须先改密；管理员无法读取员工现用密码。" type="info" show-icon />
      <a-alert v-if="formError" :message="formError" type="error" show-icon />
    </div>
  </a-modal>

  <a-modal :open="!!temp" :title="`${tempRecipient || ''} · 一次演示临时密码`" :footer="null" :mask-closable="false" @cancel="closeTemporaryPassword">
    <a-alert message="仅合成演示。仅在当前前端页面展示，关闭后不可重新读取。请勿用于真实系统。" type="warning" show-icon />
    <p class="temporary-password">{{ temp }}</p>
    <p class="detail-note">未写入日志、文件或本机持久存储，也未发送给他人。员工使用密码备用入口后，先完成首次改密；丢失后走重置流程。</p>
    <a-button type="primary" @click="closeTemporaryPassword">已查看，关闭演示密码</a-button>
  </a-modal>
</template>

<style scoped>
.heading-pill{font-size:12px;vertical-align:middle;margin-left:12px;font-weight:500;color:#4d7762;background:#e9f3ec;padding:5px 9px;border-radius:6px}.heading-actions{display:flex;align-items:flex-end;flex-direction:column;gap:10px;flex-shrink:0}.heading-actions>.ant-btn:first-child{font-size:12px}.category-tabs :deep(.ant-tabs-nav){margin:0 24px 22px}.category-tabs :deep(.ant-tabs-tab){font-size:12px}.category-tabs :deep(.ant-tabs-tabpane)>.panel-title,.category-tabs :deep(.ant-tabs-tabpane)>.toolbar{padding:0 24px}.category-content{padding:0 24px 24px}.category-content>.panel-title{margin-bottom:0}.subject-row{display:flex;align-items:center;gap:14px;border:1px solid #e5ece3;border-radius:10px;padding:18px}.subject-row>div:first-child{display:flex;flex:1;flex-direction:column;gap:7px;min-width:0}.subject-row strong{font-size:13px}.subject-row small{font-size:11px;color:#82917e;line-height:1.7}.subject-actions{display:flex;flex-wrap:wrap;gap:8px}.identity-value{overflow-wrap:anywhere;font-size:12px;color:#536e5b}.binding-good{color:#396c55}.action-grid{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}.detail-note{font-size:12px;color:#788a7d;line-height:1.9;margin:18px 0 0}.identity-chain{margin:4px 0 18px;background:#edf5ed;border:1px solid #dce9da;border-radius:9px;padding:14px 16px;font-size:12px;color:#4e795b;line-height:1.8;overflow-wrap:anywhere}.field-note{font-size:11px;color:#879587;line-height:1.8;margin-top:5px}.identity-subheading{font-size:14px;margin:25px 0 15px;color:#49664f}.identity-alert{margin-top:20px}.permission-summary{border-bottom:1px solid #e5eee9;padding:14px 0}.permission-summary b{margin-right:12px}.permission-summary p{font-size:12px;color:#7c8c7d;margin:12px 0}.compact-right{display:flex;justify-content:space-between;gap:12px;font-size:12px;margin:7px 0}.impact-box{padding:16px;background:#f0f7f3;border-radius:10px;font-size:12px;line-height:1.9}.impact-box p{margin:10px 0;color:#738875}.temporary-password{font-size:24px;background:#eff6f1;padding:18px;text-align:center;font-family:monospace;overflow-wrap:anywhere}.form-label{display:flex;flex-direction:column;gap:9px;font-size:12px;color:#5b725e}.identity-target{display:flex;flex-direction:column;gap:7px;padding:15px 17px;background:#f5f9f2;border:1px solid #e3ebde;border-radius:9px;color:#778b76;font-size:12px}.identity-target strong{font-size:14px;color:#456a4e}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:0 18px}.employee-form :deep(.ant-form-item){margin-bottom:17px}.employee-form :deep(.ant-form-item-label>label){font-size:12px}.operation-body>.detail-note{margin:0}code{font-family:ui-monospace,SFMono-Regular,monospace;font-size:12px;color:#50785a}@media(max-width:1100px){.heading-actions{align-items:flex-start}.page-heading{flex-wrap:wrap}.subject-row{flex-wrap:wrap}.subject-actions{width:100%;justify-content:flex-end}}@media(max-width:650px){.heading-actions,.heading-actions>.ant-btn{width:100%}.heading-actions>.ant-btn{white-space:normal;height:auto;min-height:36px;padding:9px 12px}.form-grid{grid-template-columns:1fr}.subject-actions>.ant-btn{flex:1}.category-tabs :deep(.ant-tabs-nav){margin-left:16px;margin-right:16px}.category-content{padding-left:16px;padding-right:16px}.category-content>.panel-title{align-items:flex-start;flex-direction:column}.category-content>.panel-title>.muted{line-height:1.8}.compact-right{flex-direction:column;gap:5px}.temporary-password{font-size:19px}}
</style>
