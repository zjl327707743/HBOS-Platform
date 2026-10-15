<script setup>
import { computed, ref } from 'vue'
import { state, deptName } from '../model.js'
import { summarizeWorkApp } from '../work-policy.js'
defineProps({ employeeId: { type: String, default: '' } })
const emit = defineEmits(['open'])
const selectedAppId = ref('')
const search = ref('')
const department = ref('all')
const status = ref('all')
const page = ref(1)
const pageSize = 8
const apps = computed(() => state.apps.map(app => {
  const summaries = state.employees.map(employee => summarizeWorkApp(state, 'employee', employee.id, app.id))
  return { ...app, using: summaries.filter(summary => [...summary.actionRows, ...summary.importantRows].some(row => row.enabled && row.available)).length, suspended: summaries.filter(summary => summary.status === 'suspended').length, review: summaries.filter(summary => summary.status === 'review').length }
}))
const business = computed(() => apps.value.filter(app => app.id !== 'platform'))
const management = computed(() => apps.value.filter(app => app.id === 'platform'))
const selectedApp = computed(() => state.apps.find(app => app.id === selectedAppId.value))
const employees = computed(() => state.employees.map(employee => ({ employee, summary: summarizeWorkApp(state, 'employee', employee.id, selectedAppId.value) })).filter(({ employee, summary }) => (!search.value || `${employee.name} ${employee.employeeNumber}`.includes(search.value)) && (department.value === 'all' || employee.departmentId === department.value) && (status.value === 'all' || summary.status === status.value)))
const pagedEmployees = computed(() => employees.value.slice((page.value - 1) * pageSize, page.value * pageSize))
function choose(appId) { selectedAppId.value = appId; page.value = 1 }
function resetPage() { page.value = 1 }
</script>

<template>
  <section class="permissions-overview">
    <template v-if="!selectedApp">
      <div class="page-heading"><div><h1>应用权限</h1><p class="muted">先选择应用，查看哪些员工可以使用，再按工作需要调整。</p></div></div>
      <section class="panel application-overview"><h2>业务应用</h2><div class="overview-apps"><button v-for="app in business" :key="app.id" class="overview-app" @click="choose(app.id)"><span class="overview-symbol" :style="{ color: app.color, backgroundColor: app.color + '15' }">{{ app.name.slice(0, 1) }}</span><strong>{{ app.name }}</strong><span class="overview-count">{{ app.using }} 位员工可以使用</span><span v-if="app.suspended" class="overview-note">{{ app.suspended }} 人已单独停用</span><span v-else-if="app.review" class="overview-note">{{ app.review }} 人的特别安排需核对</span><span v-else class="overview-note">按工作与各自的数据范围安排</span><span class="overview-link">查看员工 →</span></button></div><a-empty v-if="!business.length" description="尚无已登记的业务应用" /></section>
      <section v-if="management.length" class="panel management-overview"><h2>平台管理</h2><p>管理能力独立核定，不随部门普通应用安排获得。</p><button v-for="app in management" :key="app.id" class="management-app" @click="choose(app.id)"><strong>{{ app.name }}</strong><span>{{ app.using }} 位员工有已核定的能力</span><span>查看 →</span></button></section>
    </template>
    <template v-else>
      <a-button type="text" class="overview-back" @click="selectedAppId = ''">← 返回应用总览</a-button>
      <div class="page-heading"><div><h1>{{ selectedApp.name }}</h1><p class="muted">查看每位员工现在可以做什么；修改会进入同一个员工详情。</p></div></div>
      <section class="panel application-employees">
        <div class="overview-toolbar"><a-input v-model:value="search" aria-label="搜索员工姓名或工号" placeholder="搜索姓名或工号" allow-clear @change="resetPage" /><a-select v-model:value="department" aria-label="按部门筛选员工" :options="[{ value: 'all', label: '全部部门' }, ...state.depts.filter(dept => dept.confirmed !== false).map(dept => ({ value: dept.id, label: dept.name }))]" @change="resetPage" /><a-select v-model:value="status" aria-label="按应用使用状态筛选" :options="[{value:'all',label:'全部使用状态'},{value:'available',label:'可以使用'},{value:'none',label:'未开通'},{value:'suspended',label:'已停用'},{value:'unavailable',label:'暂不可用'},{value:'review',label:'设置需处理'}]" @change="resetPage" /></div>
        <div class="employee-results">{{ employees.length }} 位员工 · 未开户的员工档案也在列表中</div>
        <div class="overview-table-scroll"><table class="overview-table"><thead><tr><th>员工 / 工号</th><th>部门</th><th>现在可以做什么</th><th>设置来源</th><th>操作</th></tr></thead><tbody><tr v-for="{ employee, summary } in pagedEmployees" :key="employee.id"><td><button class="employee-name" :aria-label="employee.name + '，查看完整员工资料'" @click="emit('open', employee.id, 'apps', selectedAppId)"><strong>{{ employee.name }}</strong><span>{{ employee.employeeNumber }}</span></button></td><td>{{ deptName(employee.departmentId) }}</td><td><a-tag :color="summary.status === 'available' ? 'green' : summary.status === 'review' ? 'orange' : 'default'">{{ summary.statusLabel }}</a-tag><p>{{ summary.text }}</p></td><td>{{ summary.sourceText }}<details v-if="summary.sources.length > 1"><summary>查看每项工作</summary><div v-for="row in summary.actionRows" :key="row.id">{{ row.name }}：{{ row.sourceText }}</div></details></td><td><a-button @click="emit('open', employee.id, 'apps', selectedAppId)">{{ selectedApp.id === 'platform' ? '查看' : '修改' }}</a-button></td></tr></tbody></table></div>
        <a-empty v-if="!employees.length" description="没有符合筛选条件的员工" />
        <div class="overview-pagination"><a-pagination v-model:current="page" :page-size="pageSize" :total="employees.length" :show-size-changer="false" :hide-on-single-page="true" /></div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.permissions-overview{display:flex;flex-direction:column;gap:24px;min-width:0}.permissions-overview .page-heading{margin-bottom:0}.permissions-overview .page-heading p{font-size:16px;line-height:24px}.application-overview>h2,.management-overview>h2{font-size:20px;line-height:28px;margin:0 0 24px}.overview-apps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}.overview-app{display:flex;flex-direction:column;align-items:flex-start;text-align:left;gap:12px;padding:24px;border:1px solid #dfe8db;border-radius:12px;background:#fff;color:#2d4434;min-width:0}.overview-app:hover,.overview-app:focus-visible{border-color:#729b76;background:#f7fbf3}.overview-symbol{height:44px;width:44px;border-radius:12px;display:grid;place-items:center;font-size:20px}.overview-app>strong{font-size:20px;line-height:28px}.overview-count{font-size:16px;line-height:24px}.overview-note,.overview-link{font-size:14px;line-height:22px}.overview-note{color:#68776b}.overview-link{margin-top:4px;color:#477354}.management-overview>p{font-size:14px;line-height:22px;color:#68776b;margin:0 0 24px}.management-app{display:flex;gap:24px;justify-content:space-between;align-items:center;width:100%;text-align:left;border:1px solid #e1e7dd;background:#fafcf8;border-radius:10px;padding:20px;font-size:16px;line-height:24px;color:#42584a}.management-app>span{font-size:14px;color:#687b6b}.overview-back{padding-left:0;align-self:flex-start;font-size:14px}.overview-toolbar{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}.overview-toolbar>.ant-input-affix-wrapper{width:320px;max-width:100%;min-height:40px}.overview-toolbar>.ant-select{width:200px;max-width:100%}.overview-toolbar :deep(.ant-select-selector){min-height:40px}.employee-results{font-size:14px;line-height:22px;color:#67796a;margin-bottom:16px}.overview-table-scroll{overflow-x:auto}.overview-table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:14px;line-height:22px}.overview-table th{text-align:left;font-weight:500;color:#67776b;background:#f4f7f1;padding:16px;border-bottom:1px solid #e2e8de}.overview-table th:nth-child(1){width:150px}.overview-table th:nth-child(2){width:130px}.overview-table th:nth-child(4){width:130px}.overview-table th:last-child{width:96px}.overview-table td{padding:20px 16px;border-bottom:1px solid #e7ece4;vertical-align:top;overflow-wrap:anywhere}.overview-table td:first-child,.overview-table td:last-child{white-space:nowrap}.overview-table td>.ant-tag{font-size:14px;line-height:22px;margin:0 0 8px}.overview-table td p{font-size:16px;line-height:24px;margin:0}.employee-name{border:0;background:none;padding:0;color:#314936;text-align:left;display:flex;flex-direction:column;gap:8px;font-size:16px;line-height:24px}.employee-name>span{font-size:14px;color:#6f7f73}.overview-table details{font-size:14px;margin-top:8px}.overview-table summary{cursor:pointer;color:#4e7656}.overview-table details>div{margin-top:12px}.overview-table .ant-btn{min-height:40px;font-size:14px}.overview-pagination{display:flex;justify-content:flex-end;margin-top:24px}@media(max-width:1200px){.overview-apps{grid-template-columns:repeat(2,minmax(0,1fr))}.overview-table th:nth-child(1){width:125px}.overview-table th:nth-child(2){width:115px}.overview-table th:nth-child(4){width:120px}.overview-table td,.overview-table th{padding-left:12px;padding-right:12px}}@media(max-width:780px){.overview-apps{grid-template-columns:1fr}.management-app{flex-wrap:wrap;gap:12px}.overview-toolbar>.ant-input-affix-wrapper{width:100%}.overview-toolbar>.ant-select{flex:1;min-width:180px}.overview-table{min-width:660px}.overview-app{padding:20px}.overview-table td p{font-size:16px}}
.overview-table td:first-child{white-space:normal}.employee-name{max-width:100%}.employee-name>strong{white-space:normal;overflow-wrap:anywhere}.employee-name>span{white-space:nowrap}
</style>
