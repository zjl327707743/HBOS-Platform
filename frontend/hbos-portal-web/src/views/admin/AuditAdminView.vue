<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useManagementViewMemory } from '@/composables/useManagementViewMemory'
import { listAuditEvents, getAuditEvent, type AuditSubjectFilter } from '@/services/iamAudit'
import { auditOperations, auditOperationLabel, auditResultLabel } from '@/services/auditPresentation'
import { iamMessage } from '@/services/iamAccess'
import type { AuditEvent, AuditEventDetail } from '@/types/iam'
import PageHeading from '@/components/iam/PageHeading.vue'
import ResourceState from '@/components/iam/ResourceState.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import AuditSnapshot from '@/components/iam/AuditSnapshot.vue'
const rows = ref<AuditEvent[]>([]), page = ref(1), total = ref(0), loading = ref(true), error = ref('')
const subjectType = ref<string>(), subjectName = ref(''), dateFrom = ref(''), dateTo = ref(''), operation = ref<string>(), resultFilter = ref<string>()
const selected = ref<AuditEvent | null>(null), detail = ref<AuditEventDetail | null>(null), detailLoading = ref(false), detailError = ref('')
const appliedType = ref<string>(), appliedName = ref(''), appliedFrom = ref(''), appliedTo = ref(''), appliedOperation = ref<string>(), appliedResult = ref<string>()
// Defence in depth for the audit dialog: the server already redacts before/after
// snapshots, and the browser must not turn a future projection mistake into a
// visible password, token, proof or check-in body. Safe state markers are kept.
const secretKey = /password(?!_state)|token|proof|secret|cookie|authorization|(^|_)sid($|_)|checkin|attendance_records/i
const safeException = new Set(['temporary_password_state', 'first_password_required', 'created_checkins'])
function safeSnapshot(value: unknown, depth = 0): unknown {
  if (depth > 10) return '内容过深，已省略'
  if (Array.isArray(value)) return value.slice(0, 1000).map(item => safeSnapshot(item, depth + 1))
  if (value && typeof value === 'object') {
    const result: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value)) {
      if (secretKey.test(key) && !safeException.has(key)) continue
      result[key] = safeSnapshot(item, depth + 1)
    }
    return result
  }
  if (typeof value === 'string' && value.length > 1000) return value.slice(0, 1000) + '…'
  return value
}
const redactedDetail = computed(() => detail.value ? { ...detail.value, before: safeSnapshot(detail.value.before), after: safeSnapshot(detail.value.after) } : null)
const columns = [{ title:'时间',dataIndex:'occurred_at',width:170 }, { title:'操作者',dataIndex:'actor',width:170 }, { title:'对象',key:'subject',width:200 }, { title:'操作',key:'operation',width:190 }, { title:'结果',key:'result',width:100 }, { title:'详情',key:'detail',width:90 }]
let generation = 0, detailGeneration = 0, disposed = false
function query(): AuditSubjectFilter { return { subject_type:appliedType.value, subject_name:appliedName.value, date_from:appliedFrom.value, date_to:appliedTo.value, operation:appliedOperation.value, result:appliedResult.value } }
async function load() {
  const run = ++generation; loading.value = true; error.value = ''
  try { const value = await listAuditEvents(page.value,20,query()); if (!disposed && run === generation) { rows.value = value.items; total.value = value.total } }
  catch (e) { if (!disposed && run === generation) { rows.value = []; total.value = 0; error.value = iamMessage(e) } }
  finally { if (!disposed && run === generation) loading.value = false }
}
async function apply() {
  if (Boolean(subjectType.value) !== Boolean(subjectName.value.trim())) { error.value = '请同时选择对象类型并填写准确标识，或清除筛选查看全部可见记录。'; return }
  if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) { error.value = '开始日期不能晚于结束日期。'; return }
  appliedType.value = subjectType.value; appliedName.value = subjectName.value.trim(); appliedFrom.value = dateFrom.value; appliedTo.value = dateTo.value; appliedOperation.value = operation.value; appliedResult.value = resultFilter.value; page.value = 1; await load()
}
function clear() { subjectType.value = undefined; subjectName.value = ''; dateFrom.value = ''; dateTo.value = ''; operation.value = undefined; resultFilter.value = undefined; void apply() }
function changePage(next: number) {
  if (loading.value || !Number.isInteger(next) || next < 1 || next > Math.ceil(total.value / 20)) return
  page.value = next; void load()
}
async function openDetail(row: AuditEvent) {
  const run = ++detailGeneration; selected.value = row; detail.value = null; detailError.value = ''; detailLoading.value = true
  if (!row.name) { detailError.value = '记录标识缺失，请重新读取列表。'; detailLoading.value = false; return }
  try { const value = await getAuditEvent(row.name); if (!disposed && run === detailGeneration) { if (value.subject_type !== row.subject_type || value.subject_name !== row.subject_name) throw new Error('记录对象已变化，请重新读取列表后核对。'); detail.value = value } }
  catch (e) { if (!disposed && run === detailGeneration) detailError.value = iamMessage(e) }
  finally { if (!disposed && run === detailGeneration) detailLoading.value = false }
}
function closeDetail() { detailGeneration++; selected.value = null; detail.value = null; detailError.value = ''; detailLoading.value = false }
useManagementViewMemory('AuditAdminView.vue', { subjectType,subjectName,dateFrom,dateTo,operation,resultFilter,appliedType,appliedName,appliedFrom,appliedTo,appliedOperation,appliedResult,page })
onMounted(load)
onBeforeUnmount(() => { disposed = true; generation++; rows.value = []; closeDetail() })
</script>
<template>
  <section class="r6-page r6-audit-page">
    <PageHeading eyebrow="管理记录" title="变更记录" description="核对谁在何时调整了账号、角色与工作安排。" />
    <section class="r6-surface">
      <a-form class="r6-audit-filter r6-audit-query" layout="vertical" @submit.prevent="apply">
        <a-form-item label="对象类型"><a-select v-model:value="subjectType" allow-clear aria-label="筛选对象类型" placeholder="全部对象"><a-select-option value="Employee">员工档案</a-select-option><a-select-option value="User">登录账号</a-select-option><a-select-option value="Department">部门</a-select-option><a-select-option value="HBOS IAM App Role">应用角色</a-select-option></a-select></a-form-item>
        <a-form-item label="对象标识"><a-input v-model:value="subjectName" allow-clear aria-label="准确对象标识" placeholder="填写准确标识" /></a-form-item>
        <a-form-item label="开始日期"><a-input v-model:value="dateFrom" type="date" aria-label="审计开始日期" /></a-form-item>
        <a-form-item label="结束日期（含当天）"><a-input v-model:value="dateTo" type="date" aria-label="审计结束日期" /></a-form-item>
        <a-form-item label="操作"><a-select v-model:value="operation" allow-clear show-search option-filter-prop="label" aria-label="筛选变更操作" placeholder="全部操作" :options="auditOperations" /></a-form-item>
        <a-form-item label="结果"><a-select v-model:value="resultFilter" allow-clear aria-label="筛选变更结果" placeholder="全部结果"><a-select-option value="success">成功</a-select-option><a-select-option value="refused">被拒绝</a-select-option><a-select-option value="conflict">冲突</a-select-option></a-select></a-form-item>
        <a-space wrap><a-button type="primary" html-type="submit" :loading="loading">查询记录</a-button><a-button @click="clear">清除筛选</a-button></a-space>
      </a-form>
      <p class="aux">仅显示当前账号获准读取的脱敏记录；日期、操作、结果及对象筛选遵循同一读取范围。</p>
      <ResourceState :loading="loading" :error="error" @retry="load">
        <a-table class="r6-desktop-people" :columns="columns" :data-source="rows" row-key="name" :scroll="{x:920}" :pagination="false"><template #bodyCell="{column,record}"><template v-if="column.key==='subject'">{{record.subject_name}}<span class="iam-code">{{record.subject_type}}</span></template><template v-else-if="column.key==='operation'">{{auditOperationLabel(record.operation)}}</template><template v-else-if="column.key==='result'"><StatusTag :tone="record.result==='success'?'success':'warning'">{{auditResultLabel(record.result)}}</StatusTag></template><template v-else-if="column.key==='detail'"><button class="r6-audit-row-button" :aria-label="`查看${record.occurred_at}的变更记录`" @click="openDetail(record)">查看详情</button></template></template></a-table>
        <div class="r6-mobile-people"><a-empty v-if="!rows.length" description="暂无可见变更记录" /><article v-for="row in rows" :key="row.name" class="r6-mobile-person"><strong>{{auditOperationLabel(row.operation)}}</strong><p>{{row.subject_name}}</p><p>{{row.occurred_at}} · {{row.actor}}</p><a-button @click="openDetail(row)">查看详情</a-button></article></div>
        <footer class="r6-people-foot"><span class="aux">共 {{total}} 条可见记录</span><a-pagination :current="page" :total="total" :page-size="20" :disabled="loading || !total" :show-size-changer="false" @change="changePage" /></footer>
      </ResourceState>
    </section>
    <a-modal :open="Boolean(selected)" title="变更记录详情" :width="880" :footer="null" @cancel="closeDetail">
      <a-descriptions v-if="selected" :column="1" class="r6-audit-detail" bordered><a-descriptions-item label="时间">{{selected.occurred_at}}</a-descriptions-item><a-descriptions-item label="操作者">{{selected.actor}}</a-descriptions-item><a-descriptions-item label="对象">{{selected.subject_type}} · {{selected.subject_name}}</a-descriptions-item><a-descriptions-item label="操作">{{auditOperationLabel(selected.operation)}}</a-descriptions-item><a-descriptions-item label="结果">{{auditResultLabel(selected.result)}}</a-descriptions-item><a-descriptions-item label="说明">{{selected.reason || '未提供附加说明'}}</a-descriptions-item></a-descriptions>
      <ResourceState :loading="detailLoading" :error="detailError" @retry="selected && openDetail(selected)"><p class="aux">仅显示脱敏后的前后快照；密码、令牌、验证凭证、Cookie 与签到明细不展示。</p><div v-if="redactedDetail" class="r6-assignment-compare"><section><h3>变更前</h3><AuditSnapshot :value="redactedDetail.before" /></section><section><h3>变更后</h3><AuditSnapshot :value="redactedDetail.after" /></section></div></ResourceState>
      <a-button @click="closeDetail">关闭</a-button>
    </a-modal>
  </section>
</template>
