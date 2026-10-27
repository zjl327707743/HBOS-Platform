<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { listDepartments } from '@/services/iamDepartments'
import { getDepartmentWork } from '@/services/iamWork'
import { canIam, iamMessage, iamSession } from '@/services/iamAccess'
import type { DepartmentSummary, WorkApp } from '@/types/iam'
import WorkSettings from '@/components/iam/WorkSettings.vue'
import EmployeeDrawer from '@/components/iam/EmployeeDrawer.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import PanelFrame from '@/components/iam/PanelFrame.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
const route = useRoute(), activeTab = ref(canIam('iam.access.read') ? 'apps' : 'members')
const viewGroup = ref('daily'), groupsAvailable = ref(false), companies = ref<Array<{id:string;name:string}>>([]), company = ref(''), treeSearch = ref(''), expanded = ref<string[]>([])
const departments = ref<DepartmentSummary[]>([]), selected = ref(''), apps = ref<WorkApp[]>([]), editingApp = ref<string | null>(null), search = ref(''), page = ref(1), loading = ref(true), error = ref(''), employeeId = ref(''), drawerOpen = ref(false)
const settings = ref<InstanceType<typeof WorkSettings> | null>(null)
const current = computed(() => departments.value.find(row => row.id === selected.value))
const members = computed(() => (current.value?.members || []).filter(row => !search.value || [row.name, row.employee_number, row.position].join(' ').toLowerCase().includes(search.value.toLowerCase())))
const columns = [{title:'姓名 / 工号',key:'name',width:'30%'},{title:'岗位',dataIndex:'position',width:'28%'},{title:'账号状态',key:'status',width:'22%'},{title:'操作',key:'action',width:'20%'}]
const linkTarget = () => typeof route.query.department === 'string' ? route.query.department : undefined
const tree = computed(() => {
  const included = new Set<string>(), query = treeSearch.value.trim().toLowerCase()
  for (const row of departments.value.filter(row => !query || row.name.toLowerCase().includes(query))) {
    let item: DepartmentSummary | undefined = row
    while (item && !included.has(item.id)) { included.add(item.id); item = departments.value.find(parent => parent.id === item!.parent_department) }
  }
  // A visited set also keeps malformed organizational cycles from recursing forever.
  const visited = new Set<string>()
  const build = (parent: string | null): unknown[] => departments.value.filter(row => !visited.has(row.id) && included.has(row.id) && ((row.parent_department || null) === parent || parent === null && row.parent_department && !departments.value.some(item => item.id === row.parent_department))).map(row => { visited.add(row.id); return { key: row.id, title: row.name, children: build(row.id) } })
  return build(null)
})
const expandedKeys = computed(() => treeSearch.value ? departments.value.filter(row => departments.value.some(item => item.parent_department === row.id)).map(row => row.id) : expanded.value)
let generation = 0, appRead = 0, disposed = false
function revealSelection() { let row = current.value; const keys = new Set(expanded.value); while (row?.parent_department && !keys.has(row.parent_department)) { keys.add(row.parent_department); row = departments.value.find(item => item.id === row!.parent_department) }; expanded.value = [...keys] }
async function loadApps() {
  const run = ++appRead, id = selected.value; apps.value = []
  if (!canIam('iam.access.read') || !id) return
  const result = await getDepartmentWork(id)
  if (disposed || run !== appRead || selected.value !== id) return
  apps.value = result.apps
  if (current.value?.confirmed && !editingApp.value && iamSession.rolesEnabled && activeTab.value === 'apps' && result.apps.some(row => row.app_id === 'attendance' && row.integrated)) editingApp.value = 'attendance'
}
async function applyLink() {
  const id = linkTarget(); if (!id) return
  const run = generation
  if (!departments.value.some(row => row.id === id)) { const data = await listDepartments(viewGroup.value, id, company.value || undefined); if (disposed || run !== generation) return; departments.value = data.items }
  if (!departments.value.some(row => row.id === id)) { editingApp.value = null; activeTab.value = 'members'; error.value = '该部门或应用当前不可查看，已返回可用部门。'; return }
  selected.value = id; revealSelection()
  activeTab.value = route.query.tab === 'apps' && canIam('iam.access.read') ? 'apps' : 'members'
  await loadApps()
  if (disposed || run !== generation) return
  const app = typeof route.query.app === 'string' ? route.query.app : ''
  editingApp.value = current.value?.confirmed && activeTab.value === 'apps' && app && apps.value.some(row => row.app_id === app && row.integrated) ? app : current.value?.confirmed && activeTab.value === 'apps' && iamSession.rolesEnabled && apps.value.some(row => row.app_id === 'attendance' && row.integrated) ? 'attendance' : null
  if (app && editingApp.value !== app) error.value = '该部门或应用当前不可查看，已返回可用部门。'
}
async function load() {
  if (settings.value && !await settings.value.requestLeave()) return
  const run = ++generation; loading.value = true; error.value = ''
  try {
    const data = await listDepartments(viewGroup.value, linkTarget(), company.value || undefined)
    if (disposed || run !== generation) return
    departments.value = data.items; companies.value = data.companies; company.value = data.selected_company || ''; groupsAvailable.value = data.groups_available === true
    if (!departments.value.some(row => row.id === selected.value)) selected.value = (departments.value.find(row => row.confirmed && row.members?.length) || departments.value.find(row => row.members?.length) || departments.value[0])?.id || ''
    revealSelection(); await loadApps(); if (disposed || run !== generation) return; await applyLink()
  } catch (e) { if (!disposed && run === generation) error.value = iamMessage(e) }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function select(keys: unknown[]) {
  const id = String(keys[0] || ''); if (!id || id === selected.value || settings.value && !await settings.value.requestLeave()) return
  selected.value = id; editingApp.value = null; search.value = ''; page.value = 1
  try { await loadApps() } catch (e) { if (!disposed) error.value = iamMessage(e) }
}
async function changeCompany(value: string) { if (settings.value && !await settings.value.requestLeave()) return; company.value = value; selected.value = ''; expanded.value = []; editingApp.value = null; await load() }
async function changeGroup(value: string) { if (settings.value && !await settings.value.requestLeave()) return; viewGroup.value = value; selected.value = ''; expanded.value = []; editingApp.value = null; await load() }
async function changeTab(value: string) { if (settings.value && !await settings.value.requestLeave()) return; activeTab.value = value }
onBeforeRouteLeave(() => settings.value ? settings.value.requestLeave() : true)
onBeforeRouteUpdate(() => settings.value ? settings.value.requestLeave() : true)
watch(() => route.query, () => { if (!loading.value) void applyLink().catch(e => { if (!disposed) error.value = iamMessage(e) }) })
useManagementViewMemory('DepartmentsAdminView.vue', { viewGroup, company, treeSearch, selected, activeTab, search, page })
onMounted(load)
onBeforeUnmount(() => { disposed = true; generation++; appRead++; apps.value = []; departments.value = [] })
</script>
<template>
  <section class="r6-page r6-departments-page">
    <PageHeading eyebrow="组织管理" title="部门安排" description="给部门提供基础安排，特殊职责为员工单独设置。" />
    <div v-if="error" class="r6-resource-error"><a-alert :message="error" type="warning" show-icon /><a-button @click="load">重试读取</a-button></div>
    <a-skeleton v-if="loading" active />
    <div v-else class="r6-dual-panels">
      <PanelFrame as="aside" region="department-list" label="组织部门目录" class="r6-navigation r6-department-tree">
        <template #header><h3>选择部门</h3><a-select v-if="groupsAvailable" :value="viewGroup" aria-label="部门分组" style="margin-bottom:12px" @change="changeGroup"><a-select-option value="daily">日常组织</a-select-option><a-select-option value="technical">技术验证夹具</a-select-option><a-select-option value="all">全部部门</a-select-option></a-select><a-select v-if="companies.length > 1" :value="company" aria-label="部门所属公司" style="margin-bottom:12px" @change="changeCompany"><a-select-option v-for="item in companies" :key="item.id" :value="item.id">{{ item.name }}</a-select-option></a-select><a-input v-model:value="treeSearch" placeholder="搜索部门" aria-label="搜索组织部门" allow-clear /></template>
        <a-tree :tree-data="tree" :selected-keys="[selected]" :expanded-keys="expandedKeys" block-node @expand="(keys: unknown[]) => expanded = keys.map(String)" @select="select"><template #title="{ title }"><span :title="title">{{ title }}</span></template></a-tree>
        <template #footer>主部门默认与个人单独安排分别核对。</template>
      </PanelFrame>
      <PanelFrame region="department-detail" label="部门默认安排与成员">
        <template v-if="current" #header><div class="r6-department-title"><h2>{{ current.name }}</h2><p>{{ current.company }} · 主部门员工 {{ current.members?.length || 0 }} 人</p></div><StatusTag v-if="!current.confirmed" tone="warning">尚未确认，暂不安排人员或权限</StatusTag><a-radio-group :value="activeTab" @change="(event: {target:{value:string}}) => changeTab(event.target.value)" button-style="solid" style="margin-top:16px"><a-radio-button v-if="canIam('iam.access.read')" value="apps">默认角色与应用</a-radio-button><a-radio-button value="members">部门成员</a-radio-button></a-radio-group></template>
        <template v-if="current">
          <template v-if="activeTab === 'apps' && canIam('iam.access.read')">
            <WorkSettings v-if="editingApp" :key="selected + ':' + editingApp" ref="settings" subject-kind="department" :subject-id="selected" :app-id="editingApp" @back="editingApp = null" @saved="loadApps" />
            <template v-else><a-alert type="info" show-icon message="部门默认只包含普通工作角色" description="个人单独设置保持；重要权限不会随部门自动获得。" /><article v-for="app in apps" :key="app.app_id" class="r6-department-app"><div><strong>{{ app.title }}</strong><p>{{ app.integrated ? app.summary : '尚未接入此管理功能，暂不能在此调整。' }}</p></div><a-button v-if="app.integrated" :disabled="!current.confirmed" @click="editingApp = app.app_id">{{ canIam('iam.departments.manage') ? '设置安排' : '查看安排' }}</a-button></article><a-empty v-if="!apps.length" description="暂无可见应用安排" /></template>
          </template>
          <template v-else><div class="iam-toolbar"><a-input v-model:value="search" class="iam-search" placeholder="搜索姓名、工号或岗位" aria-label="搜索部门成员" allow-clear @change="page = 1" /></div><a-table :columns="columns" :data-source="members" row-key="id" table-layout="fixed" :scroll="{ x: 520 }" :pagination="{ current: page, pageSize: 10, total: members.length, showSizeChanger: false, onChange: (value: number) => page = value }"><template #bodyCell="{ column, record }"><template v-if="column.key === 'name'"><button v-if="canIam('iam.people.read')" class="iam-name" :aria-label="`查看${record.name}，工号${record.employee_number}`" @click="employeeId = record.id; drawerOpen = true"><strong>{{ record.name }}</strong></button><strong v-else>{{ record.name }}</strong><span class="iam-code">{{ record.employee_number }}</span></template><template v-else-if="column.key === 'status'"><StatusTag :tone="record.account_status === 'active' ? 'success' : 'neutral'">{{ record.account_status === 'active' ? '已开通' : record.account_status === 'disabled' ? '已停用' : '未开通' }}</StatusTag></template><template v-else-if="column.key === 'action'"><a-button v-if="canIam('iam.people.read')" type="link" @click="employeeId = record.id; drawerOpen = true">查看安排</a-button><span v-else class="aux">仅成员状态</span></template></template></a-table><p class="aux">此处仅列主部门成员；兼岗不会自动叠加所属部门权限。</p></template>
        </template>
        <a-empty v-else description="暂无可管理部门" />
        <template #footer><span class="aux">保存前以服务端预览核对跟随者、单独安排与已有禁止。</span></template>
      </PanelFrame>
    </div>
    <EmployeeDrawer :open="drawerOpen" :employee-id="employeeId" @close="drawerOpen = false" @changed="load" />
  </section>
</template>
