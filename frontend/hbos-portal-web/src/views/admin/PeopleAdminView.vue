<script setup lang="ts">
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { computed, getCurrentInstance, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { Modal, message } from 'ant-design-vue'
import { SearchOutlined, PlusOutlined, TeamOutlined, KeyOutlined, LinkOutlined, ColumnHeightOutlined } from '@ant-design/icons-vue'
import { listPeople, getEmployeeMetadata, createEmployee } from '@/services/iamPeople'
import { canIam, iamMessage } from '@/services/iamAccess'
import { developmentObservation } from '@/services/frappeClient'
import type { EmployeeSummary, EmployeeMetadata } from '@/types/iam'
import EmployeeDrawer from '@/components/iam/EmployeeDrawer.vue'
import OwnAccountVerification from '@/components/account/OwnAccountVerification.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import { useAccountProof } from '@/composables/useAccountProof'
const tableSticky = { offsetHeader: 0, getContainer: () => document.querySelector('.portal-route-content') as HTMLElement }
const viewInstance = import.meta.env.DEV ? getCurrentInstance()?.uid : undefined
const viewGroup = ref('daily'), groupsAvailable = ref(false), compact = ref(false)
const rows = ref<EmployeeSummary[]>([]), total = ref(0), page = ref(1), category = ref('employees'), search = ref(''), department = ref<string>(), accountStatus = ref(''), loading = ref(true), error = ref(''), metadataError = ref('')
const selected = ref(''), selectedTab = ref('basic'), drawerOpen = ref(false), createOpen = ref(false), metadata = ref<EmployeeMetadata | null>(null), creating = ref(false), createError = ref(''), recheck = ref(false)
const fields = reactive<Record<string, string>>({}), proof = useAccountProof(() => undefined)
let generation = 0, disposed = false, timer: ReturnType<typeof setTimeout> | undefined, requestId = ''
const unopened = computed(() => rows.value.filter(row => row.account_status === 'unopened').length)
const pending = computed(() => rows.value.filter(row => row.attendance_status !== 'confirmed').length)
const departmentOptions = computed(() => metadata.value?.departments.map(row => ({ value: row.value, label: `${row.label} · ${row.company}` })) || [])
const filtered = computed(() => Boolean(search.value || department.value || accountStatus.value))
const columns = computed(() => category.value === 'employees' ? [{ title: '员工 / 工号', key: 'name', width: '25%' }, { title: '部门 / 岗位', key: 'department', width: '25%' }, { title: '账号状态', key: 'account', width: '15%' }, { title: '需要处理', key: 'task', width: '18%' }, { title: '操作', key: 'action', width: '17%' }] : [{ title: '账号名称', key: 'name', width: '30%' }, { title: '账号主键', dataIndex: 'user_id', width: '45%' }, { title: '分类', key: 'category', width: '25%' }])
const required = [ ['first_name', '名字', 'Data'], ['employee_number', '工号', 'Data'], ['company', '公司', 'Link'], ['department', '主部门', 'Link'], ['gender', '性别', 'Link'], ['date_of_birth', '出生日期', 'Date'], ['date_of_joining', '入职日期', 'Date'] ]
const formFields = computed(() => {
  const result = [...(metadata.value?.required_fields || [])].filter(row => !['name', 'user_id', 'create_user_automatically', 'status'].includes(row.fieldname))
  for (const [fieldname, label, fieldtype] of required) if (!result.some(row => row.fieldname === fieldname)) result.push({ fieldname: fieldname!, label: label!, fieldtype: fieldtype! })
  return result
})
function accountLabel(row: EmployeeSummary) { return row.account_status === 'active' ? '已开通' : row.account_status === 'disabled' ? '已停用' : '待开通' }
function taskLabel(row: EmployeeSummary) { return row.account_status === 'unopened' ? '开户 / 关联' : row.attendance_status !== 'confirmed' ? '核对员工关联' : '无需处理' }
async function load() {
  const run = ++generation; loading.value = true; error.value = ''
  try {
    const result = await listPeople({ page: page.value, page_size: 20, category: category.value, view_group: viewGroup.value, search: search.value, department: category.value === 'employees' ? department.value : undefined, account_status: category.value === 'employees' ? accountStatus.value : '' })
    if (!disposed && run === generation) { rows.value = result.items; total.value = result.total; groupsAvailable.value = result.groups_available === true }
  } catch (e) { if (!disposed && run === generation) { rows.value = []; total.value = 0; error.value = iamMessage(e) } }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function loadMetadata() { metadataError.value = ''; try { const value = await getEmployeeMetadata(viewGroup.value); if (!disposed) metadata.value = value } catch (e) { if (!disposed) metadataError.value = iamMessage(e) } }
function open(row: EmployeeSummary, tab = 'basic') { selected.value = row.id; selectedTab.value = tab; drawerOpen.value = true }
function clearFilters() { search.value = ''; department.value = undefined; accountStatus.value = ''; page.value = 1 }
async function beginCreate() { createError.value = ''; recheck.value = false; proof.invalidate(); Object.keys(fields).forEach(key => delete fields[key]); requestId = crypto.randomUUID(); await loadMetadata(); if (metadataError.value || !metadata.value) return; createOpen.value = true }
function options(field: string) { return field === 'company' ? metadata.value?.companies : field === 'department' ? metadata.value?.departments.filter(row => !fields.company || row.company === fields.company) : field === 'gender' ? metadata.value?.genders : undefined }
async function closeCreate() {
  if (creating.value) return false
  if (Object.values(fields).some(value => value.trim())) {
    const leave = await new Promise<boolean>(resolve => Modal.confirm({ title: '放弃尚未保存的员工档案？', okText: '放弃填写', cancelText: '继续填写', onOk: () => resolve(true), onCancel: () => resolve(false) }))
    if (!leave) return false
  }
  createOpen.value = false; proof.invalidate(); return true
}
async function saveEmployee() {
  if (creating.value || recheck.value || !metadata.value || !proof.valid.value) return
  const missing = formFields.value.filter(row => !fields[row.fieldname]?.trim()).map(row => row.label)
  if (missing.length) { createError.value = `请填写：${missing.join('、')}。`; return }
  creating.value = true; createError.value = ''
  try { await createEmployee({ ...fields, status: 'Active' }, metadata.value.version, requestId); createOpen.value = false; proof.invalidate(); message.success('员工档案已保存，尚未开通账号。'); await load() }
  catch (e) { createError.value = iamMessage(e) + ' 请先核对列表与最新元数据，再决定是否重试。'; recheck.value = true; proof.invalidate() }
  finally { creating.value = false }
}
async function recheckCreate() { await Promise.all([load(), loadMetadata()]); if (!error.value && !metadataError.value) { recheck.value = false; createError.value = '已读取最新列表和元数据。请核对工号是否已存在，再重新验证本人；重试沿用原请求编号。' } }
watch([category, department, accountStatus, viewGroup], () => { page.value = 1; void load() })
watch(viewGroup, loadMetadata)
watch(search, () => { page.value = 1; clearTimeout(timer); timer = setTimeout(load, 300) })
watch(() => fields.company, () => { fields.department = '' })
onMounted(() => { void load(); void loadMetadata() })
onBeforeRouteLeave(() => createOpen.value ? closeCreate() : true)
onBeforeUnmount(() => { disposed = true; generation++; clearTimeout(timer); proof.invalidate() })
useManagementViewMemory('PeopleAdminView.vue', { search, department, accountStatus, page, category, viewGroup, compact })
</script>
<template>
  <section class="r6-page r6-people-page" :data-view-instance="viewInstance">
    <output v-if="developmentObservation">本机页面实例 {{ viewInstance }}</output>
    <PageHeading eyebrow="组织管理" title="员工管理" description="找到同事，安排账号与应用角色。"><a-button v-if="canIam('iam.people.create')" type="primary" @click="beginCreate"><PlusOutlined />新增员工档案</a-button></PageHeading>
    <div v-if="category === 'employees'" class="r6-people-overview">
      <div class="r6-surface r6-overview"><span class="r6-overview-icon"><TeamOutlined /></span><div><span>匹配的员工档案</span><strong>{{ loading || error ? '—' : total }}</strong><small>服务端筛选结果</small></div></div>
      <div class="r6-surface r6-overview"><span class="r6-overview-icon"><KeyOutlined /></span><div><span>本页待开通账号</span><strong>{{ loading || error ? '—' : unopened }}</strong><small>已有档案，核验后开户</small></div></div>
      <div class="r6-surface r6-overview"><span class="r6-overview-icon"><LinkOutlined /></span><div><span>本页待核对关联</span><strong>{{ loading || error ? '—' : pending }}</strong><small>不含正常已确认的员工</small></div></div>
    </div>
    <section class="r6-surface r6-people-panel">
      <a-alert v-if="groupsAvailable" type="info" show-icon message="当前站点含隔离验收对象。合成员工不代表公司全员。" />
      <a-tabs v-model:activeKey="category"><a-tab-pane key="employees" tab="员工档案" /><a-tab-pane key="pending" tab="待关联账号" /><a-tab-pane key="other" tab="其他账号" /></a-tabs>
      <div class="r6-filter-toolbar">
        <a-select v-if="groupsAvailable && category === 'employees'" v-model:value="viewGroup" aria-label="员工分组"><a-select-option value="daily">日常员工</a-select-option><a-select-option value="technical">技术验证夹具</a-select-option><a-select-option value="all">全部员工</a-select-option></a-select>
        <a-input v-model:value="search" allow-clear class="r6-search" :placeholder="category === 'employees' ? '搜索姓名或工号' : '搜索账号'" aria-label="搜索人员"><template #prefix><SearchOutlined /></template></a-input>
        <a-select v-if="category === 'employees'" v-model:value="department" show-search allow-clear option-filter-prop="label" aria-label="筛选部门" placeholder="全部部门" :options="departmentOptions" />
        <a-select v-if="category === 'employees'" v-model:value="accountStatus" aria-label="账号状态"><a-select-option value="">全部账号状态</a-select-option><a-select-option value="active">已开通</a-select-option><a-select-option value="unopened">待开通</a-select-option><a-select-option value="disabled">已停用</a-select-option></a-select>
        <a-button :aria-pressed="compact" aria-label="切换表格密度" @click="compact = !compact"><ColumnHeightOutlined /></a-button>
      </div>
      <div v-if="filtered" class="r6-active-filters"><span>筛选结果 {{ total }} {{ category === 'employees' ? '位' : '个' }}</span><a-tag v-if="search" closable @close="search = ''">搜索：{{ search }}</a-tag><a-tag v-if="department" closable @close="department = undefined">{{ departmentOptions.find(row => row.value === department)?.label || department }}</a-tag><a-tag v-if="accountStatus" closable @close="accountStatus = ''">{{ accountStatus === 'active' ? '已开通' : accountStatus === 'disabled' ? '已停用' : '待开通' }}</a-tag><a-button type="link" @click="clearFilters">清除筛选</a-button></div>
      <div v-if="error || metadataError" class="r6-resource-error"><a-alert :message="error || metadataError" type="warning" show-icon /><a-button @click="load(); loadMetadata()">重试读取</a-button></div>
      <p v-if="category !== 'employees'" class="aux" style="padding:0 24px">{{ category === 'pending' ? '这些账号尚未明确关联员工档案。请先查找已有员工，再在其“账号与登录”中输入准确账号并核验归属。' : '服务与应急管理账号独立列示，不计入员工档案。' }}</p>
      <a-table class="r6-desktop-people" :locale="{ emptyText: '没有符合条件的员工或账号' }" :columns="columns" :data-source="rows" row-key="id" table-layout="fixed" :size="compact ? 'small' : 'middle'" :loading="loading" :sticky="tableSticky" :scroll="{ x: 680 }" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'"><div class="r6-employee-cell"><a-avatar :size="40">{{ record.name?.slice(-1) }}</a-avatar><div><button v-if="category === 'employees'" class="iam-name" :aria-label="`查看${record.name}，工号${record.employee_number}`" @click="open(record)"><strong>{{ record.name }}</strong></button><strong v-else>{{ record.name }}</strong><span class="iam-code">{{ record.employee_number || record.id }}</span></div></div></template>
          <template v-else-if="column.key === 'department'">{{ record.department_name }}<span class="iam-code">{{ record.position || '岗位待补充' }}</span></template>
          <template v-else-if="column.key === 'account'"><StatusTag :tone="record.account_status === 'active' ? 'success' : record.account_status === 'unopened' ? 'warning' : 'neutral'">{{ accountLabel(record) }}</StatusTag></template>
          <template v-else-if="column.key === 'task'"><span class="r6-person-task">{{ taskLabel(record) }}</span></template>
          <template v-else-if="column.key === 'action'"><a-button type="link" @click="open(record, record.user_id ? 'basic' : 'account')">{{ record.user_id ? '查看安排' : '开户 / 关联' }}</a-button></template>
          <template v-else-if="column.key === 'category'">{{ category === 'pending' ? '员工待关联' : '非员工主体' }}</template>
        </template>
      </a-table>
      <div class="r6-mobile-people"><a-skeleton v-if="loading" active /><a-empty v-else-if="!rows.length" description="没有符合条件的员工或账号" /><article v-for="row in rows" :key="row.id" class="r6-mobile-person"><div class="r6-employee-cell"><a-avatar :size="40">{{ row.name?.slice(-1) }}</a-avatar><div><button v-if="category === 'employees'" class="iam-name" @click="open(row)"><strong>{{ row.name }}</strong></button><strong v-else>{{ row.name }}</strong><span class="iam-code">{{ row.employee_number || row.id }}</span></div></div><p>{{ category === 'employees' ? `${row.department_name} · ${row.position || '岗位待补充'}` : row.user_id }}</p><div class="r6-mobile-person-foot"><StatusTag :tone="row.account_status === 'active' ? 'success' : 'warning'">{{ accountLabel(row) }}</StatusTag><a-button v-if="category === 'employees'" @click="open(row, row.user_id ? 'basic' : 'account')">{{ row.user_id ? '查看安排' : '开户 / 关联' }}</a-button></div></article></div>
      <footer class="r6-people-foot"><span class="aux">{{ groupsAvailable ? '合成对象按站点分组显示；' : '' }}已停用或个人受限不自动成为待办。</span><a-pagination v-model:current="page" :total="total" :page-size="20" :show-size-changer="false" :show-total="(value: number) => `共 ${value} 条`" @change="load" /></footer>
    </section>
    <EmployeeDrawer :open="drawerOpen" :employee-id="selected" :initial-tab="selectedTab" @close="drawerOpen = false" @changed="load" />
    <a-modal :open="createOpen" title="新增员工档案" :footer="null" :mask-closable="false" @cancel="closeCreate"><p>此步骤只建立员工档案。已有员工请从列表选择“开户 / 关联”，避免重复建档。</p><a-alert v-if="createError" :message="createError" type="warning" show-icon /><a-button v-if="recheck" @click="recheckCreate">核对服务端结果</a-button><OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" /><a-form layout="vertical" @submit.prevent="saveEmployee"><a-form-item v-for="field in formFields" :key="field.fieldname" :label="field.label" required><a-select v-if="options(field.fieldname)" v-model:value="fields[field.fieldname]" :disabled="creating" show-search option-filter-prop="label" :options="options(field.fieldname)" /><a-input v-else v-model:value="fields[field.fieldname]" :disabled="creating" :type="field.fieldtype === 'Date' ? 'date' : 'text'" autocomplete="off" /></a-form-item><a-space><a-button :disabled="creating" @click="closeCreate">取消</a-button><a-button type="primary" html-type="submit" :loading="creating" :disabled="recheck || !proof.valid.value">保存员工档案</a-button></a-space></a-form></a-modal>
  </section>
</template>
