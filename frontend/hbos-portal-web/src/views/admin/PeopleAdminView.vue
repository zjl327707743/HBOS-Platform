<script setup lang="ts">
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { computed, getCurrentInstance, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
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
const rows = ref<EmployeeSummary[]>([]), total = ref(0), page = ref(1), category = ref('employees'), search = ref(''), department = ref<string>(), accountStatus = ref(''), loading = ref(true), error = ref(''), metadataError = ref(''), unavailable = ref(false)
const selected = ref(''), selectedTab = ref('basic'), drawerOpen = ref(false), createOpen = ref(false), metadata = ref<EmployeeMetadata | null>(null), creating = ref(false), createError = ref(''), recheck = ref(false)
const overviewNotice = ref('')
const fields = reactive<Record<string, string>>({}), proof = useAccountProof(() => undefined)
let generation = 0, metadataGeneration = 0, disposed = false, timer: ReturnType<typeof setTimeout> | undefined, requestId = '', requestSignature = ''
const unopened = computed(() => rows.value.filter(row => row.account_status === 'unopened').length)
const pending = computed(() => rows.value.filter(needsAssociationReview).length)
const departmentOptions = computed(() => metadata.value?.departments.map(row => ({ value: row.value, label: `${row.label} · ${row.company}` })) || [])
const filtered = computed(() => Boolean(search.value || department.value || accountStatus.value))
const columns = computed(() => category.value === 'employees' ? [{ title: '员工 / 工号', key: 'name', width: '25%' }, { title: '部门 / 岗位', key: 'department', width: '25%' }, { title: '账号状态', key: 'account', width: '15%' }, { title: '需要处理', key: 'task', width: '18%' }, { title: '操作', key: 'action', width: '17%' }] : [{ title: '账号名称', key: 'name', width: '30%' }, { title: '账号主键', dataIndex: 'user_id', width: '45%' }, { title: '分类', key: 'category', width: '25%' }])
const required = [ ['first_name', '姓名', 'Data'], ['employee_number', '工号', 'Data'], ['company', '公司', 'Link'], ['department', '主部门', 'Link'], ['gender', '性别', 'Link'], ['date_of_birth', '出生日期', 'Date'], ['date_of_joining', '入职日期', 'Date'] ]
const formFields = computed(() => {
  // The native Employee insert applies its locked-version naming-series default.
  // Operators provide the business employee number, never an internal series.
  const result = [...(metadata.value?.required_fields || [])].filter(row => !['name', 'naming_series', 'user_id', 'create_user_automatically', 'status'].includes(row.fieldname))
  for (const [fieldname, label, fieldtype] of required) if (!result.some(row => row.fieldname === fieldname)) result.push({ fieldname: fieldname!, label: label!, fieldtype: fieldtype! })
  return result.map(row => ({ ...row, label: required.find(([fieldname]) => fieldname === row.fieldname)?.[1] || row.label }))
})
const canOpenApps = computed(() => canIam('iam.access.read'))
function accountLabel(row: EmployeeSummary) { return row.account_status === 'active' ? '已开通' : row.account_status === 'disabled' ? '已停用' : '待开通' }
function needsAssociationReview(row: EmployeeSummary) { return row.account_status !== 'unopened' && row.attendance_status !== 'confirmed' }
function taskLabel(row: EmployeeSummary) { return row.account_status === 'unopened' ? '开通账号' : needsAssociationReview(row) ? '关联异常，人工核查' : '无需处理' }
function actionTab(row: EmployeeSummary) {
  if (needsAssociationReview(row)) return 'basic'
  if (row.account_status === 'active' && canOpenApps.value) return 'apps'
  if (row.account_status === 'unopened') return 'account'
  return 'basic'
}
function actionLabel(row: EmployeeSummary) {
  if (needsAssociationReview(row)) return '查看关联详情'
  if (row.account_status === 'active' && canOpenApps.value) return '设置应用角色'
  if (row.account_status === 'unopened') return '处理账号'
  return '查看详情'
}
function taskActionable(row: EmployeeSummary) { return row.account_status === 'unopened' || needsAssociationReview(row) }
function taskTab(row: EmployeeSummary) { return row.account_status === 'unopened' ? 'account' : 'basic' }
function taskHint(row: EmployeeSummary) {
  return row.account_status === 'unopened'
    ? '已有员工档案；需核验归属后开通账号。'
    : '本页没有安全确认命令；请按 Employee 与 User 主键人工核查，系统不会按姓名匹配。'
}
function personRow(row: EmployeeSummary) { return { 'data-person-id': row.id } }
function jumpTo(kind: 'unopened' | 'pending') {
  const row = rows.value.find(item => kind === 'unopened' ? item.account_status === 'unopened' : needsAssociationReview(item))
  if (!row) { overviewNotice.value = kind === 'unopened' ? '本页没有待开通账号。' : '本页没有需人工核查的关联异常。'; return }
  overviewNotice.value = kind === 'unopened' ? `已定位本页第一位待开通账号：${row.name}。` : `已定位本页第一位关联异常，需人工核查：${row.name}。`
  void nextTick(() => {
    const root = document.querySelector(window.matchMedia('(max-width:760px)').matches ? '.r6-mobile-people' : '.r6-desktop-people')
    const target = Array.from(root?.querySelectorAll<HTMLElement>('[data-person-id]') || []).find(item => item.dataset.personId === row.id)
    const action = target?.querySelector<HTMLElement>(kind === 'pending' ? '[data-task-action]' : '[data-row-action]')
    action?.focus({ preventScroll: true })
    target?.scrollIntoView?.({ block: 'center' })
  })
}
async function load() {
  const run = ++generation; loading.value = true; error.value = ''; overviewNotice.value = ''; unavailable.value = false
  try {
    const result = await listPeople({ page: page.value, page_size: 20, category: category.value, view_group: viewGroup.value, search: search.value, department: category.value === 'employees' ? department.value : undefined, account_status: category.value === 'employees' ? accountStatus.value : '' })
    if (!disposed && run === generation) { rows.value = result.items; total.value = result.total; groupsAvailable.value = result.groups_available === true; unavailable.value = result.unavailable === true }
  } catch (e) { if (!disposed && run === generation) { rows.value = []; total.value = 0; unavailable.value = false; error.value = iamMessage(e) } }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function loadMetadata() {
  const run = ++metadataGeneration, group = viewGroup.value
  metadataError.value = ''; metadata.value = null
  try { const value = await getEmployeeMetadata(group); if (!disposed && run === metadataGeneration && group === viewGroup.value) metadata.value = value }
  catch (e) { if (!disposed && run === metadataGeneration && group === viewGroup.value) metadataError.value = iamMessage(e) }
}
function changePage(next: number) {
  if (loading.value || !Number.isInteger(next) || next < 1 || next > Math.ceil(total.value / 20)) return
  page.value = next; void load()
}
function open(row: EmployeeSummary, tab = 'basic') { selected.value = row.id; selectedTab.value = tab; drawerOpen.value = true }
function clearFilters() { search.value = ''; department.value = undefined; accountStatus.value = ''; page.value = 1 }
async function beginCreate() { createError.value = ''; recheck.value = false; proof.invalidate(); Object.keys(fields).forEach(key => delete fields[key]); requestId = ''; requestSignature = ''; await loadMetadata(); if (metadataError.value || !metadata.value) return; createOpen.value = true }
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
  const payload = { ...fields, status: 'Active' }
  const signature = JSON.stringify([Object.entries(payload).sort(([left], [right]) => left.localeCompare(right)), metadata.value.version])
  if (!requestId || signature !== requestSignature) { requestId = crypto.randomUUID(); requestSignature = signature }
  creating.value = true; createError.value = ''
  try { await createEmployee(payload, metadata.value.version, requestId); createOpen.value = false; proof.invalidate(); message.success('员工档案已保存，尚未开通账号。'); await load() }
  catch (e) { createError.value = iamMessage(e) + ' 请先核对列表中的工号与建档结果，再决定下一步。'; recheck.value = true; proof.invalidate() }
  finally { creating.value = false }
}
async function recheckCreate() { await Promise.all([load(), loadMetadata()]); if (!error.value && !metadataError.value) { recheck.value = false; createError.value = '已读取最新列表。请先核对工号：已建档请回到列表处理，未建档再确认内容并重新验证本人。' } }
watch([category, department, accountStatus, viewGroup], () => { page.value = 1; void load() })
watch(viewGroup, loadMetadata)
watch(search, () => { page.value = 1; clearTimeout(timer); timer = setTimeout(load, 300) })
watch(() => fields.company, () => { fields.department = '' })
onMounted(() => { void load(); void loadMetadata() })
onBeforeRouteLeave(() => createOpen.value ? closeCreate() : true)
onBeforeUnmount(() => { disposed = true; generation++; metadataGeneration++; clearTimeout(timer); proof.invalidate() })
useManagementViewMemory('PeopleAdminView.vue', { search, department, accountStatus, page, category, viewGroup, compact })
</script>
<template>
  <section class="r6-page r6-people-page" :data-view-instance="viewInstance">
    <output v-if="developmentObservation">本机页面实例 {{ viewInstance }}</output>
    <PageHeading eyebrow="组织管理" title="员工管理" description="找到同事，安排账号与应用角色。"><a-button v-if="canIam('iam.people.create')" type="primary" @click="beginCreate"><PlusOutlined />新增员工档案</a-button></PageHeading>
    <div v-if="category === 'employees'" class="r6-people-overview">
      <div class="r6-surface r6-overview"><span class="r6-overview-icon"><TeamOutlined /></span><div><span>匹配的员工档案</span><strong>{{ loading || error ? '—' : total }}</strong><small>筛选结果</small></div></div>
      <button type="button" class="r6-surface r6-overview" :disabled="loading || Boolean(error) || !unopened" :aria-label="`本页待开通账号 ${unopened} 位，定位第一位`" @click="jumpTo('unopened')"><span class="r6-overview-icon"><KeyOutlined /></span><div><span>本页待开通账号</span><strong>{{ loading || error ? '—' : unopened }}</strong><small>已有档案，核验后开户</small></div><span class="r6-overview-trail">去处理</span></button>
      <button type="button" class="r6-surface r6-overview" :disabled="loading || Boolean(error) || !pending" :aria-label="`本页待核对关联 ${pending} 位，定位第一位`" @click="jumpTo('pending')"><span class="r6-overview-icon"><LinkOutlined /></span><div><span>本页待核对关联</span><strong>{{ loading || error ? '—' : pending }}</strong><small>不含待开通与正常已确认</small></div><span class="r6-overview-trail">去核对</span></button>
    </div>
    <p v-if="category === 'employees' && overviewNotice" class="r6-overview-notice" role="status">{{ overviewNotice }}</p>
    <section class="r6-surface r6-people-panel">
      <a-alert v-if="groupsAvailable" type="info" show-icon message="当前按人员分组展示，统计仅包含所选分组。" />
      <a-tabs v-model:activeKey="category"><a-tab-pane key="employees" tab="员工档案" /><a-tab-pane key="pending" tab="待关联账号" /><a-tab-pane key="other" tab="其他账号" /></a-tabs>
      <div class="r6-filter-toolbar">
        <a-select v-if="groupsAvailable && category === 'employees'" v-model:value="viewGroup" aria-label="员工分组"><a-select-option value="daily">日常员工</a-select-option><a-select-option value="technical">技术验证员工</a-select-option><a-select-option value="all">全部员工</a-select-option></a-select>
        <a-input v-model:value="search" allow-clear class="r6-search" :placeholder="category === 'employees' ? '搜索姓名或工号' : '搜索账号'" aria-label="搜索人员"><template #prefix><SearchOutlined /></template></a-input>
        <a-select v-if="category === 'employees'" v-model:value="department" show-search allow-clear option-filter-prop="label" aria-label="筛选部门" placeholder="全部部门" :options="departmentOptions" />
        <a-select v-if="category === 'employees'" v-model:value="accountStatus" aria-label="账号状态"><a-select-option value="">全部账号状态</a-select-option><a-select-option value="active">已开通</a-select-option><a-select-option value="unopened">待开通</a-select-option><a-select-option value="disabled">已停用</a-select-option></a-select>
        <a-button :aria-pressed="compact" aria-label="切换表格密度" @click="compact = !compact"><ColumnHeightOutlined /></a-button>
      </div>
      <div v-if="filtered && !(category !== 'employees' && unavailable)" class="r6-active-filters"><span>筛选结果 {{ total }} {{ category === 'employees' ? '位' : '个' }}</span><a-tag v-if="search" closable @close="search = ''">搜索：{{ search }}</a-tag><a-tag v-if="department" closable @close="department = undefined">{{ departmentOptions.find(row => row.value === department)?.label || department }}</a-tag><a-tag v-if="accountStatus" closable @close="accountStatus = ''">{{ accountStatus === 'active' ? '已开通' : accountStatus === 'disabled' ? '已停用' : '待开通' }}</a-tag><a-button type="link" @click="clearFilters">清除筛选</a-button></div>
      <div v-if="error || metadataError" class="r6-resource-error"><a-alert :message="error || metadataError" type="warning" show-icon /><a-button @click="load(); loadMetadata()">重试读取</a-button></div>
      <p v-if="category !== 'employees' && !unavailable" class="aux" style="padding:0 24px">{{ category === 'pending' ? '这些账号尚未明确关联员工档案。请先查找已有员工，再在其“登录账号”中输入准确账号并核验归属。' : '服务与应急管理账号独立列示，不计入员工档案。' }}</p>
      <div v-if="category !== 'employees' && unavailable" class="r6-unavailable-state" role="status">
        <a-empty description="当前分类暂不可用" />
        <p>服务端没有返回可列举范围，<strong>不能按零条处理</strong>。此分类需要具名委派范围；当前账号没有对应的具名委派，本页也不会放宽后端范围。</p>
      </div>
      <a-table v-if="category === 'employees' || !unavailable" class="r6-desktop-people" :locale="{ emptyText: '没有符合条件的员工或账号' }" :columns="columns" :data-source="rows" row-key="id" table-layout="fixed" :size="compact ? 'small' : 'middle'" :loading="loading" :sticky="tableSticky" :scroll="{ x: 680 }" :pagination="false" :custom-row="personRow">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'"><div class="r6-employee-cell"><a-avatar :size="40">{{ record.name?.slice(-1) }}</a-avatar><div><button v-if="category === 'employees'" class="iam-name" :aria-label="`查看${record.name}，工号${record.employee_number}`" @click="open(record)"><strong>{{ record.name }}</strong></button><strong v-else>{{ record.name }}</strong><span class="iam-code">{{ record.employee_number || record.id }}</span></div></div></template>
          <template v-else-if="column.key === 'department'">{{ record.department_name }}<span class="iam-code">{{ record.position || '岗位待补充' }}</span></template>
          <template v-else-if="column.key === 'account'"><StatusTag :tone="record.account_status === 'active' ? 'success' : record.account_status === 'unopened' ? 'warning' : 'neutral'">{{ accountLabel(record) }}</StatusTag></template>
          <template v-else-if="column.key === 'task'"><button v-if="taskActionable(record)" type="button" class="r6-task-link" data-task-action :title="taskHint(record)" :aria-label="`${taskLabel(record)}：${record.name}`" @click="open(record, taskTab(record))">{{ taskLabel(record) }}</button><span v-else class="r6-person-task">无需处理</span></template>
          <template v-else-if="column.key === 'action'"><a-button type="link" data-row-action :aria-label="`${actionLabel(record)}：${record.name}`" @click="open(record, actionTab(record))">{{ actionLabel(record) }}</a-button></template>
          <template v-else-if="column.key === 'category'">{{ category === 'pending' ? '员工待关联' : '非员工主体' }}</template>
        </template>
      </a-table>
      <div v-if="category === 'employees' || !unavailable" class="r6-mobile-people">
        <a-skeleton v-if="loading" active />
        <a-empty v-else-if="!rows.length" description="没有符合条件的员工或账号" />
        <article v-for="row in rows" :key="row.id" class="r6-mobile-person" :data-person-id="row.id">
          <div class="r6-employee-cell"><a-avatar :size="40">{{ row.name?.slice(-1) }}</a-avatar><div><button v-if="category === 'employees'" class="iam-name" :aria-label="`查看${row.name}，工号${row.employee_number}`" @click="open(row)"><strong>{{ row.name }}</strong></button><strong v-else>{{ row.name }}</strong><span class="iam-code">{{ row.employee_number || row.id }}</span></div></div>
          <p>{{ category === 'employees' ? `${row.department_name} · ${row.position || '岗位待补充'}` : row.user_id }}</p>
          <div class="r6-mobile-person-foot"><StatusTag :tone="row.account_status === 'active' ? 'success' : row.account_status === 'unopened' ? 'warning' : 'neutral'">{{ accountLabel(row) }}</StatusTag><div class="r6-mobile-actions"><button v-if="taskActionable(row)" type="button" class="r6-task-link" data-task-action :title="taskHint(row)" :aria-label="`${taskLabel(row)}：${row.name}`" @click="open(row, taskTab(row))">{{ taskLabel(row) }}</button><a-button v-if="category === 'employees'" data-row-action :aria-label="`${actionLabel(row)}：${row.name}`" @click="open(row, actionTab(row))">{{ actionLabel(row) }}</a-button></div></div>
        </article>
      </div>
      <footer v-if="category === 'employees' || !unavailable" class="r6-people-foot"><span class="aux">{{ groupsAvailable ? '当前统计以所选分组为准；' : '' }}已停用或个人受限不自动成为待办。</span><a-pagination :current="page" :total="total" :page-size="20" :disabled="loading || !total" :show-size-changer="false" :show-total="(value: number) => `共 ${value} 条`" @change="changePage" /></footer>
    </section>
    <EmployeeDrawer :open="drawerOpen" :employee-id="selected" :initial-tab="selectedTab" @close="drawerOpen = false" @changed="load" />
    <a-modal :open="createOpen" title="新增员工档案" :footer="null" :mask-closable="false" @cancel="closeCreate"><p>此步骤只建立员工档案。已有员工请从列表选择“处理账号”，避免重复建档。</p><a-alert v-if="createError" :message="createError" type="warning" show-icon /><a-button v-if="recheck" @click="recheckCreate">核对最新结果</a-button><OwnAccountVerification password-only @verified="proof.sync" @invalidated="proof.invalidate" /><a-form layout="vertical" @submit.prevent="saveEmployee"><a-form-item v-for="field in formFields" :key="field.fieldname" :label="field.label" required><a-select v-if="options(field.fieldname)" v-model:value="fields[field.fieldname]" :disabled="creating" show-search option-filter-prop="label" :options="options(field.fieldname)" /><a-input v-else v-model:value="fields[field.fieldname]" :disabled="creating" :type="field.fieldtype === 'Date' ? 'date' : 'text'" autocomplete="off" /></a-form-item><a-space><a-button :disabled="creating" @click="closeCreate">取消</a-button><a-button type="primary" html-type="submit" :loading="creating" :disabled="recheck || !proof.valid.value">保存员工档案</a-button></a-space></a-form></a-modal>
  </section>
</template>
<style scoped>
button.r6-overview { width: 100%; font: inherit; color: inherit; text-align: left; cursor: pointer; }
button.r6-overview:disabled { cursor: default; opacity: .68; }
.r6-overview-trail { margin-left: auto; flex: none; color: var(--r6-brand, #5754df); font-size: 12px; white-space: nowrap; }
.r6-overview-notice { margin: -8px 2px 14px; font-size: 12px; line-height: 20px; color: var(--r6-muted, #5f6e86); }
.r6-task-link { border: 0; background: none; padding: 0; color: #896720; font-size: 12px; line-height: 20px; text-align: left; cursor: pointer; }
.r6-task-link:hover { text-decoration: underline; }
.r6-mobile-actions { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.r6-unavailable-state { padding: 30px 24px; text-align: center; }
.r6-unavailable-state p { max-width: 560px; margin: 8px auto 0; color: var(--r6-muted, #5f6e86); font-size: 12px; line-height: 20px; }
@media (max-width: 760px) {
  .r6-overview-trail { display: none; }
  .r6-mobile-actions { margin-left: 0; flex-wrap: wrap; justify-content: flex-end; }
}
</style>
