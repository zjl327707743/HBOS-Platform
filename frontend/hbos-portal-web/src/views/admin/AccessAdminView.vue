<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { AppstoreOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { getRegisteredApps, listAppPeople, type RegisteredApp } from '@/services/iamWork'
import { iamMessage } from '@/services/iamAccess'
import type { EmployeeSummary } from '@/types/iam'
import EmployeeDrawer from '@/components/iam/EmployeeDrawer.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import PortalSelect from '@/components/portal/PortalSelect.vue'
import PortalState from '@/components/portal/PortalState.vue'
import { employeeGroups } from '@/components/iam/managementChoices'

const viewGroup = ref('daily'), groupsAvailable = ref(false)
const apps = ref<RegisteredApp[]>([]), rows = ref<EmployeeSummary[]>([])
const selectedApp = ref(''), search = ref(''), page = ref(1), total = ref(0)
const loading = ref(false), registryLoading = ref(true), error = ref(''), registryError = ref('')
const employeeId = ref(''), drawerOpen = ref(false)
const current = computed(() => apps.value.find(app => app.id === selectedApp.value))
let generation = 0, registryGeneration = 0, timer: ReturnType<typeof setTimeout> | undefined, reload = false
const columns = [
  { title: '员工 / 工号', key: 'name', width: '32%' },
  { title: '部门', dataIndex: 'department_name', width: '28%' },
  { title: '账号状态', key: 'account', width: '20%' },
  { title: '操作', key: 'action', width: '20%' },
]
function open(record: EmployeeSummary) {
  employeeId.value = record.id
  drawerOpen.value = true
}
const statusText = (row: EmployeeSummary) => row.account_status === 'active' ? '已开通' : row.account_status === 'disabled' ? '已停用' : '待开通'
async function load() {
  const run = ++generation
  error.value = ''
  rows.value = []
  total.value = 0
  if (!current.value?.integrated) { loading.value = false; return }
  loading.value = true
  try {
    const data = await listAppPeople(current.value.id, { page: page.value, page_size: 20, search: search.value, view_group: viewGroup.value })
    if (run !== generation) return
    rows.value = data.items
    total.value = data.total
    groupsAvailable.value = data.groups_available === true
  } catch (e) { if (run === generation) error.value = iamMessage(e) }
  finally { if (run === generation) loading.value = false }
}
async function loadApps() {
  const run = ++registryGeneration
  registryLoading.value = true
  registryError.value = ''
  try {
    const data = await getRegisteredApps()
    if (run !== registryGeneration) return
    apps.value = data.apps.filter(app => app.id !== 'iam' && (!app.synthetic || app.integrated))
    if (!apps.value.some(app => app.id === selectedApp.value)) selectedApp.value = apps.value.find(app => app.integrated)?.id || apps.value[0]?.id || ''
    await load()
  } catch (e) { if (run === registryGeneration) registryError.value = iamMessage(e) }
  finally { if (run === registryGeneration) registryLoading.value = false }
}
function selectApp(app: RegisteredApp) {
  if (app.id === selectedApp.value) return
  selectedApp.value = app.id
  page.value = 1
  void load()
}
function changePage(value: number) { page.value = value; void load() }
watch(search, () => { page.value = 1; clearTimeout(timer); timer = setTimeout(load, 300) })
watch(viewGroup, () => { page.value = 1; void load() })
onMounted(loadApps)
onDeactivated(() => { clearTimeout(timer); generation++; registryGeneration++; reload = true; drawerOpen.value = false })
onActivated(() => { if (reload) { reload = false; void loadApps() } })
onBeforeUnmount(() => { clearTimeout(timer); generation++; registryGeneration++ })
</script>

<template>
  <section class="r6-page v10-access-page">
    <PageHeading title="其他应用权限" description="查看各应用的权限设置。未接入的应用仍按原方式管理。" />
    <a-skeleton v-if="registryLoading" active aria-label="正在读取应用注册信息" />
    <PortalState v-else-if="registryError" kind="error" title="应用权限入口暂不可用" :description="registryError" retry @retry="loadApps" />
    <template v-else-if="current">
      <div class="v10-access-apps" aria-label="应用">
        <button v-for="app in apps" :key="app.id" type="button" :aria-pressed="selectedApp === app.id" @click="selectApp(app)">
          <AppstoreOutlined aria-hidden="true" />
          <span><strong>{{ app.title }}</strong><small>{{ app.synthetic ? '隔离合成规则验证' : app.integrated ? '角色与负责范围管理' : '保留原有业务授权' }}</small></span>
          <StatusTag :tone="app.integrated ? 'success' : 'warning'">{{ app.integrated ? '已接入' : '未接入' }}</StatusTag>
        </button>
      </div>
      <section class="r6-surface v10-access-panel">
        <header><h2>{{ current.title }}</h2><p>{{ current.integrated ? '选择员工，查看应用角色与访问范围。' : '请在原业务应用中查看或调整此应用的访问设置。' }}</p></header>
        <template v-if="current.integrated">
          <div class="iam-toolbar">
            <a-input v-model:value="search" class="v10-search-field" placeholder="搜索姓名、工号、账号或部门" aria-label="搜索应用员工" allow-clear><template #prefix><SearchOutlined /></template></a-input>
            <PortalSelect v-if="groupsAvailable" :value="viewGroup" :options="employeeGroups" aria-label="员工分组" @change="viewGroup = $event" />
          </div>
          <PortalState v-if="error" kind="error" title="暂时无法读取员工权限" :description="error" retry @retry="load" />
          <a-table v-else class="r6-desktop-people" :columns="columns" :data-source="rows" row-key="id" table-layout="fixed" :loading="loading" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'"><button type="button" class="iam-name" :aria-label="`查看${record.name}的应用权限，工号${record.employee_number}`" @click="open(record)"><strong>{{ record.name }}</strong></button><span class="iam-code">{{ record.employee_number }}</span></template>
              <StatusTag v-else-if="column.key === 'account'" :tone="record.account_status === 'active' ? 'success' : 'warning'">{{ statusText(record) }}</StatusTag>
              <a-button v-else-if="column.key === 'action'" size="small" @click="open(record)">查看权限</a-button>
            </template>
          </a-table>
          <div v-if="!error" class="r6-mobile-people">
            <a-skeleton v-if="loading" active />
            <PortalState v-else-if="!rows.length" title="没有匹配的员工" />
            <article v-for="record in rows" :key="record.id" class="r6-mobile-person">
              <strong>{{ record.name }}</strong><p>{{ record.employee_number }} · {{ record.department_name }}</p>
              <div class="r6-mobile-person-foot"><StatusTag :tone="record.account_status === 'active' ? 'success' : 'warning'">{{ statusText(record) }}</StatusTag><a-button size="small" @click="open(record)">查看权限</a-button></div>
            </article>
          </div>
          <a-pagination v-if="total > 20" :current="page" :page-size="20" :total="total" :show-size-changer="false" :disabled="loading" @change="changePage" />
        </template>
        <PortalState v-else title="尚未接入此管理功能" description="原有业务权限由对应应用管理。" />
      </section>
    </template>
    <PortalState v-else title="当前没有可管理的应用" description="应用范围以服务器返回的授权为准。" />
    <EmployeeDrawer :open="drawerOpen" :employee-id="employeeId" initial-tab="apps" :initial-app="current?.integrated ? selectedApp : null" @close="drawerOpen = false" @changed="load" />
  </section>
</template>
