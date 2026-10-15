<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, ApartmentOutlined } from '@ant-design/icons-vue'
import { state, ui, isAdmin, deptName } from '../model.js'
import { summarizeWorkApp } from '../work-policy.js'
import WorkSettings from './WorkSettings.vue'

const emit = defineEmits(['open'])
const selectedId = ref('d1')
const activeTab = ref('members')
const departmentSearch = ref('')
const expandedKeys = ref(state.depts.map(department => department.id))
const autoExpandParent = ref(true)
const memberSearch = ref('')
const memberPage = ref(1)
const editingAppId = ref('')
const settings = ref(null)
const selectedDept = computed(() => state.depts.find(department => department.id === selectedId.value))
const confirmed = department => !!department && department.confirmed !== false && department.mapped !== false && !['pending', 'unconfirmed'].includes(department.status)
const selectedConfirmed = computed(() => confirmed(selectedDept.value))
const confirmedCount = computed(() => state.depts.filter(confirmed).length)
const primaryMembers = computed(() => state.employees.filter(employee => employee.departmentId === selectedId.value))
const secondaryMembers = computed(() => state.employees.filter(employee => employee.departmentId !== selectedId.value && employee.secondaryDepartments?.includes(selectedId.value)))
const filteredMembers = computed(() => {
  const query = memberSearch.value.trim().toLocaleLowerCase()
  return primaryMembers.value.filter(employee => !query || [employee.name, employee.employeeNumber, employee.position].some(value => String(value || '').toLocaleLowerCase().includes(query)))
})
const memberPagination = computed(() => ({
  current: memberPage.value, pageSize: 8, total: filteredMembers.value.length, showSizeChanger: false,
  hideOnSinglePage: false, showTotal: total => '共 ' + total + ' 名员工',
  onChange: page => { memberPage.value = page }
}))
const treeData = computed(() => {
  const nodes = new Map(state.depts.map(department => [department.id, {
    key: department.id, title: department.name, confirmed: confirmed(department), children: []
  }]))
  const roots = []
  for (const department of state.depts) {
    const node = nodes.get(department.id)
    const parent = department.parentId !== department.id && nodes.get(department.parentId)
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  const query = departmentSearch.value.trim().toLocaleLowerCase()
  const prune = nodes => nodes.flatMap(node => {
    const children = prune(node.children)
    return !query || node.title.toLocaleLowerCase().includes(query) || children.length ? [{ ...node, children }] : []
  })
  return prune(roots)
})
const ordinaryApps = computed(() => state.apps
  .filter(app => app.id !== 'platform' && app.actions?.some(action => !action.highRisk))
  .map(app => ({ app, summary: summarizeWorkApp(state, 'department', selectedId.value, app.id) })))
const columns = [
  { title: '姓名', key: 'person' },
  { title: '工号', key: 'employeeNumber', width: 116 },
  { title: '账号状态', key: 'account', width: 108 },
  { title: '操作', key: 'open', width: 72 }
]
const appColumns = [
  { title: '应用', key: 'application', width: 136 },
  { title: '本部门通常可以做什么', key: 'arrangement' },
  { title: '操作', key: 'settings', width: 88 }
]
function accountStatus(employee) {
  if (!employee.accountId || employee.status === 'pending') return { text: '未开通', color: 'default' }
  return employee.status === 'disabled' ? { text: '已停用', color: 'default' } : { text: '已开通', color: 'green' }
}
function appStatus(summary) {
  return { color: { available: 'green', none: 'default', suspended: 'default', unavailable: 'orange', review: 'orange' }[summary.status] || 'default', text: summary.statusLabel || '暂未安排' }
}
function openEmployee(employee) { emit('open', employee.id, 'basic', null) }
function expandDepartments(keys) { expandedKeys.value = keys; autoExpandParent.value = false }
async function selectDepartment(keys) {
  const nextId = keys[0]
  if (!nextId || nextId === selectedId.value || ui.busy || !state.depts.some(department => department.id === nextId)) return
  if (editingAppId.value && settings.value && !await settings.value.requestLeave()) return
  selectedId.value = nextId
  editingAppId.value = ''
  memberSearch.value = ''
  memberPage.value = 1
}
function openApplication(appId) {
  if (!selectedConfirmed.value) return message.warning('这个部门尚未确认，暂不能用于分配人员或应用权限。')
  editingAppId.value = appId
}
function backToApplications() { editingAppId.value = '' }
watch(memberSearch, () => { memberPage.value = 1 })
watch(departmentSearch, query => {
  if (query.trim()) { expandedKeys.value = state.depts.map(department => department.id); autoExpandParent.value = true }
})
watch(() => state.depts.map(department => department.id), (ids, previous = []) => {
  expandedKeys.value = [...new Set([...expandedKeys.value.filter(id => ids.includes(id)), ...ids.filter(id => !previous.includes(id))])]
})
watch(() => state.depts, () => {
  if (!selectedDept.value) {
    selectedId.value = state.depts[0]?.id || ''
    editingAppId.value = ''
  }
})
watch(() => filteredMembers.value.length, length => {
  if (memberPage.value > Math.max(1, Math.ceil(length / 8))) memberPage.value = 1
})
</script>

<template>
  <div class="departments-page">
    <div class="page-heading">
      <div><h1>部门管理</h1><p>先查看部门成员，再安排大家通常使用的应用。</p></div>
    </div>
    <div class="department-layout">
      <aside class="panel department-directory" aria-label="部门目录">
        <div class="directory-heading"><ApartmentOutlined /><h2>部门目录</h2></div>
        <a-input v-model:value="departmentSearch" aria-label="搜索部门名称" placeholder="搜索部门" allow-clear :disabled="ui.busy"><template #prefix><SearchOutlined /></template></a-input>
        <div class="department-tree">
          <a-tree v-if="treeData.length" :tree-data="treeData" :selected-keys="[selectedId]" :expanded-keys="expandedKeys" :auto-expand-parent="autoExpandParent" :disabled="ui.busy" block-node @select="selectDepartment" @expand="expandDepartments">
            <template #title="{ title, confirmed: nodeConfirmed }"><span class="tree-label" :aria-label="title"><span class="tree-name">{{ title }}</span><span v-if="!nodeConfirmed" class="tree-pending">待确认</span></span></template>
          </a-tree>
          <a-empty v-else :image-style="{ height: '42px' }" description="没有找到这个部门" />
        </div>
        <div class="directory-count">{{ confirmedCount }} 个已确认<span v-if="confirmedCount !== state.depts.length"> · {{ state.depts.length - confirmedCount }} 个待确认</span></div>
      </aside>

      <section v-if="selectedDept" class="department-detail" aria-label="部门详情">
        <section class="panel department-overview">
          <div class="department-heading"><h2>{{ selectedDept.name }}</h2><a-tag :color="selectedConfirmed ? 'green' : 'orange'">{{ selectedConfirmed ? '已确认' : '待确认' }}</a-tag></div>
          <p v-if="selectedDept.description" class="department-description">{{ selectedDept.description }}</p>
          <div class="department-facts"><span>{{ primaryMembers.length }} 名主部门员工</span><span v-if="secondaryMembers.length">{{ secondaryMembers.length }} 名兼岗员工</span></div>
          <a-alert v-if="!selectedConfirmed" class="confirmation-notice" type="warning" show-icon message="这个部门尚未确认，暂不能用于分配人员或应用权限。" description="可以先查看现有信息；确认部门归属后再进行安排。" />
          <a-alert v-else-if="!isAdmin" class="confirmation-notice" type="info" show-icon message="当前只能查看部门安排，修改需要相应管理权限。" />
        </section>

        <section class="panel department-content">
          <a-tabs v-model:activeKey="activeTab">
            <a-tab-pane key="members" tab="部门成员">
              <div class="member-toolbar"><a-input v-model:value="memberSearch" aria-label="搜索本部门员工姓名或工号" placeholder="搜索姓名或工号" allow-clear><template #prefix><SearchOutlined /></template></a-input><span>{{ filteredMembers.length }} 名员工</span></div>
              <a-table class="department-members-table" :columns="columns" :data-source="filteredMembers" row-key="id" :pagination="memberPagination" table-layout="fixed" :locale="{ emptyText: memberSearch ? '没有找到符合条件的员工' : '这个部门暂时没有主部门员工' }">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'person'"><button type="button" class="employee-link" @click="openEmployee(record)">{{ record.name }}</button><span class="employee-position">{{ record.position || '岗位待确认' }}</span></template>
                  <template v-else-if="column.key === 'employeeNumber'"><span class="employee-number">{{ record.employeeNumber || '未填写' }}</span></template>
                  <template v-else-if="column.key === 'account'"><a-tag :color="accountStatus(record).color">{{ accountStatus(record).text }}</a-tag></template>
                  <template v-else-if="column.key === 'open'"><a-button type="link" @click="openEmployee(record)">查看</a-button></template>
                </template>
              </a-table>
              <details v-if="secondaryMembers.length" class="secondary-members">
                <summary>兼岗员工（{{ secondaryMembers.length }} 名）</summary>
                <p>兼岗只记录任职，不自动获得本部门的应用安排。</p>
                <div v-for="employee in secondaryMembers" :key="employee.id" class="secondary-member"><button type="button" class="employee-link" @click="openEmployee(employee)">{{ employee.name }}</button><span>主部门：{{ deptName(employee.departmentId) }}</span></div>
              </details>
            </a-tab-pane>

            <a-tab-pane key="applications" tab="默认应用">
              <div class="application-introduction"><h3>本部门的日常应用安排</h3><p>这里设置该部门员工通常可以使用的应用。单独为某位员工调整的内容，仍按其个人设置执行。</p><div class="attendance-explanation"><strong>安排给本部门员工，不等于查看所有人的数据。</strong><span>例如，大家都可以使用考勤应用时，通常查看的是各自本人的考勤。</span></div></div>
              <a-alert v-if="!selectedConfirmed" type="info" show-icon message="部门确认后，才能安排默认应用。" />
              <WorkSettings v-else-if="editingAppId" ref="settings" :key="selectedId + ':' + editingAppId" subject-kind="department" :subject-id="selectedId" :app-id="editingAppId" @back="backToApplications" />
              <template v-else>
                <a-table class="default-application-table" :columns="appColumns" :data-source="ordinaryApps" :row-key="record => record.app.id" :pagination="false" table-layout="fixed" :locale="{ emptyText: '暂时没有可安排的普通应用' }">
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'application'"><strong class="application-name">{{ record.app.name }}</strong><a-tag :color="appStatus(record.summary).color">{{ appStatus(record.summary).text }}</a-tag></template>
                    <template v-else-if="column.key === 'arrangement'"><p class="application-result">{{ record.summary.text || record.summary.reason || '暂未安排日常工作' }}</p><details v-if="record.summary.actionRows?.length" class="work-details"><summary>查看具体工作</summary><ul><li v-for="work in record.summary.actionRows" :key="work.id"><strong>{{ work.name }}</strong><span>{{ (work.configuredEnabled ?? work.enabled) ? (work.scopeText || '范围待确认') : '未安排' }}</span></li></ul></details></template>
                    <template v-else-if="column.key === 'settings'"><a-button type="link" :disabled="!isAdmin || !selectedConfirmed || ui.busy" @click="openApplication(record.app.id)">查看设置</a-button></template>
                  </template>
                </a-table>
                <p class="department-save-note">修改时会先列出受到调整的员工、保留个人设置的员工，以及暂时无法使用的员工。核对一次后再保存。</p>
                <p class="important-operation-note">重要库存调整、质量签署和平台管理，需要对具体人员单独核对，不能作为部门普通安排。</p>
              </template>
            </a-tab-pane>
          </a-tabs>
        </section>
      </section>
      <section v-else class="panel no-department"><a-empty description="请从左侧选择一个部门" /></section>
    </div>
  </div>
</template>

<style scoped>
.departments-page{display:flex;flex-direction:column;gap:24px;min-width:0}
.page-heading{margin:0;align-items:flex-start}.page-heading h1{margin-bottom:8px}.page-heading p{margin:0;color:#526059;font-size:16px;line-height:24px}
.department-layout{display:grid;grid-template-columns:280px minmax(0,1fr);gap:24px;align-items:start;min-width:0}
.department-directory{position:sticky;top:136px;padding:16px;min-width:0}
.directory-heading{display:flex;align-items:center;gap:10px;margin-bottom:16px;color:#314c3b}.directory-heading>.anticon{font-size:20px}.directory-heading h2{font-size:20px;line-height:28px;margin:0}
.department-tree{margin:16px -4px 0;max-height:calc(100vh - 360px);overflow:auto;scrollbar-gutter:stable;min-height:60px}.department-directory :deep(.ant-tree){background:transparent;font-size:16px;line-height:24px}.department-directory :deep(.ant-tree-treenode){padding:0 0 8px;align-items:flex-start}.department-directory :deep(.ant-tree-switcher){margin-top:10px;width:20px}.department-directory :deep(.ant-tree-indent-unit){width:16px}.department-directory :deep(.ant-tree-node-content-wrapper){padding:10px 8px;min-height:44px;line-height:24px;min-width:0}.department-directory :deep(.ant-tree-node-selected){background:#e9f2e5}.department-directory :deep(.ant-tree-title){white-space:normal;display:block}
.tree-label{display:flex;flex-direction:column;gap:4px}.tree-name{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere;line-height:24px}.tree-pending{font-size:14px;line-height:22px;color:#846832}.directory-count{padding-top:16px;margin-top:16px;border-top:1px solid #e1e7df;font-size:14px;line-height:22px;color:#59655c}
.department-detail{display:flex;flex-direction:column;gap:24px;min-width:0}.department-overview{padding:24px}.department-heading{display:flex;gap:16px;align-items:flex-start}.department-heading h2{font-size:20px;line-height:28px;overflow-wrap:anywhere;margin:0;min-width:0;flex:1}.department-heading .ant-tag{white-space:nowrap;margin:3px 0 0;font-size:14px;line-height:22px}
.department-description{margin:12px 0 0;font-size:16px;line-height:24px;color:#526059;overflow-wrap:anywhere}.department-facts{display:flex;flex-wrap:wrap;gap:8px 20px;color:#526059;font-size:14px;line-height:22px;margin-top:16px}.confirmation-notice{margin-top:20px}.confirmation-notice :deep(.ant-alert-message),.confirmation-notice :deep(.ant-alert-description){font-size:14px;line-height:22px}
.department-content{padding:0;min-width:0;overflow:hidden}.department-content :deep(.ant-tabs-nav){margin:0;padding:0 24px}.department-content :deep(.ant-tabs-tab){padding:18px 0;font-size:16px;line-height:24px}.department-content :deep(.ant-tabs-tabpane){padding:24px;min-width:0}
.member-toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px}.member-toolbar>.ant-input-affix-wrapper{max-width:320px;flex:1}.member-toolbar>span{white-space:nowrap;font-size:14px;color:#59655c}.department-directory :deep(.ant-input-affix-wrapper),.member-toolbar :deep(.ant-input-affix-wrapper){min-height:40px}
.department-members-table :deep(.ant-table-cell),.default-application-table :deep(.ant-table-cell){font-size:16px;line-height:24px;padding:16px 12px;overflow-wrap:anywhere;vertical-align:middle}.department-members-table :deep(.ant-table-thead .ant-table-cell),.default-application-table :deep(.ant-table-thead .ant-table-cell){font-size:14px;line-height:22px;background:#f6f8f3;color:#526059;font-weight:500}.department-members-table :deep(.ant-tag),.default-application-table :deep(.ant-tag){font-size:14px;line-height:22px;white-space:nowrap;margin:0}.department-members-table :deep(.ant-btn-link),.default-application-table :deep(.ant-btn-link){font-size:16px;line-height:24px;min-height:40px;padding:6px 0;white-space:nowrap}.department-members-table :deep(.ant-pagination){font-size:14px;line-height:22px;flex-wrap:wrap;row-gap:8px;margin-bottom:0}
.employee-link{border:0;background:none;padding:0;color:#2d6444;font-size:16px;line-height:24px;font-weight:500;text-align:left;overflow-wrap:anywhere}.employee-link:hover{text-decoration:underline}.employee-link:focus-visible{outline:2px solid #4c8c68;outline-offset:4px;border-radius:2px}.employee-position{display:block;font-size:14px;line-height:22px;color:#59655c;margin-top:4px}.employee-number{font-variant-numeric:tabular-nums;white-space:nowrap}
.secondary-members{border-top:1px solid #e5e9e1;padding-top:20px;margin-top:24px}.secondary-members>summary,.work-details>summary{cursor:pointer;font-size:14px;line-height:22px;color:#37694a;width:fit-content}.secondary-members>summary:focus-visible,.work-details>summary:focus-visible{outline:2px solid #4c8c68;outline-offset:4px}.secondary-members>p{font-size:14px;line-height:22px;color:#59655c;margin:12px 0}.secondary-member{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:12px 0;border-top:1px solid #edf0e8}.secondary-member>span{font-size:14px;line-height:22px;color:#59655c;overflow-wrap:anywhere;text-align:right;max-width:65%}
.application-introduction{margin-bottom:24px}.application-introduction h3{font-size:20px;line-height:28px;margin:0 0 12px}.application-introduction>p{font-size:16px;line-height:24px;color:#526059;margin:0}.attendance-explanation{background:#f3f7ee;border:1px solid #dfe8d5;padding:16px;border-radius:8px;margin-top:16px;display:flex;flex-direction:column;gap:6px}.attendance-explanation strong{font-weight:500;font-size:16px;line-height:24px}.attendance-explanation span{font-size:14px;line-height:22px;color:#526059}
.application-name{display:block;font-size:16px;line-height:24px;font-weight:500;margin-bottom:8px}.application-result{margin:0;font-size:16px;line-height:24px;overflow-wrap:anywhere}.work-details{margin-top:10px}.work-details ul{padding:0;margin:12px 0 0;list-style:none}.work-details li{display:flex;flex-direction:column;gap:4px;margin-bottom:12px;font-size:14px;line-height:22px}.work-details li strong{font-weight:500}.work-details li span{color:#526059;overflow-wrap:anywhere}.department-save-note,.important-operation-note{font-size:14px;line-height:22px;color:#59655c;margin:20px 0 0}.important-operation-note{padding-top:16px;border-top:1px solid #e5e9e1}.no-department{padding:40px 24px}
@media(max-width:1050px){.department-layout{gap:16px}.department-content :deep(.ant-tabs-tabpane){padding:20px 16px}.department-content :deep(.ant-tabs-nav){padding:0 16px}.department-overview{padding:20px}.department-members-table :deep(.ant-table-cell),.default-application-table :deep(.ant-table-cell){padding-left:8px;padding-right:8px}}
@media(max-width:900px){.department-layout{grid-template-columns:1fr}.department-directory{position:static}.department-tree{max-height:260px}.department-detail{gap:16px}.directory-count{margin-top:12px;padding-top:12px}.department-heading{gap:12px}}
@media(max-width:600px){.department-content :deep(.ant-tabs-tabpane){padding:16px}.department-heading{flex-wrap:wrap}.department-heading h2{flex-basis:100%}.member-toolbar{align-items:flex-start;flex-direction:column;gap:10px}.member-toolbar>.ant-input-affix-wrapper{width:100%;max-width:none}.secondary-member{flex-direction:column;gap:6px}.secondary-member>span{text-align:left;max-width:100%}.department-members-table :deep(.ant-table-content>table){min-width:460px}.department-members-table :deep(.ant-table-content),.default-application-table :deep(.ant-table-content){overflow-x:auto}.default-application-table :deep(.ant-table-content>table){min-width:480px}.department-facts{margin-top:12px}.department-overview{padding:16px}}
</style>
