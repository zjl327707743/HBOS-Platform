<template>
  <section class="product-page lims-audit-page">
    <div class="lims-audit-heading">
      <div>
        <span class="page-kicker">LIMS · 质量追溯</span>
        <h1>合规审计追踪</h1>
        <p>记录创建、结果提交、复核、批准和关键变更的只读事件流。</p>
      </div>
      <span class="lims-readonly-badge">只读 · 指纹留存</span>
    </div>

    <a-alert v-if="errorMessage" class="lims-result-alert" type="error" show-icon closable :message="errorMessage" @close="errorMessage = ''" />

    <section class="lims-audit-filters glass-surface" aria-label="审计筛选">
      <a-input-search v-model:value="keyword" placeholder="搜索对象、动作摘要或指纹" enter-button="查询" allow-clear @search="applyFilters" />
      <a-select v-model:value="logType" allow-clear placeholder="全部事件类型" @change="applyFilters">
        <a-select-option v-for="item in logTypes" :key="item" :value="item">{{ item }}</a-select-option>
      </a-select>
      <a-select v-model:value="target" allow-clear placeholder="全部对象" @change="applyFilters">
        <a-select-option v-for="item in targets" :key="item" :value="item">{{ targetLabel(item) }}</a-select-option>
      </a-select>
      <a-button :loading="loading" @click="loadAudit">刷新</a-button>
      <span class="lims-audit-count">{{ total }} 条事件</span>
    </section>

    <section class="lims-audit-panel glass-surface" aria-live="polite">
      <a-table :columns="columns" :data-source="events" :loading="loading" :pagination="false" :scroll="{ x: 980 }" row-key="name" size="middle">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'"><span class="lims-audit-time">{{ (record.created_at || '').slice(0, 16) }}</span></template>
          <template v-else-if="column.key === 'log_type'"><a-tag :color="eventColor(record.log_type)">{{ record.log_type }}</a-tag></template>
          <template v-else-if="column.key === 'doc_name'"><button type="button" class="lims-audit-link" @click="openEvent(record)">{{ record.doc_name }}</button></template>
          <template v-else-if="column.key === 'change'"><span v-if="record.field_changed">{{ fieldLabel(record.field_changed) }}：{{ record.old_value || '—' }} → {{ record.new_value || '—' }}</span><span v-else>动作记录</span></template>
          <template v-else-if="column.key === 'checksum'"><span class="lims-audit-checksum">{{ shorten(record.checksum) }}</span></template>
        </template>
      </a-table>
      <div v-if="!loading && !events.length" class="lims-result-empty"><AuditOutlined /><h3>暂无匹配的审计事件</h3><p>可以调整筛选条件，或等待新的受控操作产生。</p></div>
      <div v-if="nextCursor" class="lims-audit-more"><a-button :loading="loadingMore" @click="loadMore">加载更多事件</a-button></div>
    </section>

    <a-drawer v-model:open="drawerOpen" title="审计事件详情" :width="440" placement="right">
      <template v-if="selectedEvent">
        <dl class="lims-audit-detail">
          <div><dt>事件时间</dt><dd>{{ selectedEvent.created_at || '—' }}</dd></div>
          <div><dt>事件类型</dt><dd>{{ selectedEvent.log_type || '—' }}</dd></div>
          <div><dt>操作人</dt><dd>{{ selectedEvent.user || '—' }}</dd></div>
          <div><dt>对象</dt><dd>{{ targetLabel(selectedEvent.doctype_target) }} · {{ selectedEvent.doc_name }}</dd></div>
          <div><dt>动作摘要</dt><dd>{{ selectedEvent.action_text || '—' }}</dd></div>
          <div><dt>字段变更</dt><dd>{{ selectedEvent.field_changed ? `${fieldLabel(selectedEvent.field_changed)}：${selectedEvent.old_value || '—'} → ${selectedEvent.new_value || '—'}` : '无字段变更' }}</dd></div>
          <div><dt>操作原因</dt><dd>{{ selectedEvent.reason || '—' }}</dd></div>
          <div><dt>记录指纹</dt><dd class="lims-audit-full-checksum">{{ selectedEvent.checksum || '—' }}</dd></div>
        </dl>
      </template>
    </a-drawer>
  </section>
</template>

<script setup lang="ts">
import { useLimsQueryPage } from '@/composables/useLimsQueryPage'
import { ref } from 'vue'
import { AuditOutlined } from '@ant-design/icons-vue'
import { listLimsAudit, type LimsAuditEvent } from '@/services/limsAudit'

const events = ref<LimsAuditEvent[]>([])
const targets = ref<string[]>([])
const total = ref(0)
const nextCursor = ref<string | null>(null)

const keyword = ref('')
const logType = ref('')
const target = ref('')
const drawerOpen = ref(false)
const selectedEvent = ref<LimsAuditEvent | null>(null)
const logTypes = ['创建', '修改', '删除', '登记入库', '提交', '复核', '批准', '修订', '放行', '拒绝', 'OOS', '仪器使用', '规格生效', '规格废止', '越权拦截', 'SoD 拦截']
const columns = [
  { title: '时间', key: 'created_at', width: 150 },
  { title: '事件类型', key: 'log_type', width: 110 },
  { title: '对象', key: 'doc_name', width: 180 },
  { title: '操作人', dataIndex: 'user', key: 'user', width: 140 },
  { title: '动作摘要', dataIndex: 'action_text', key: 'action_text', width: 240 },
  { title: '字段变更', key: 'change', width: 250 },
  { title: '记录指纹', key: 'checksum', width: 130 },
]

const { loading, loadingMore, errorMessage, updateRoute, runLoad } = useLimsQueryPage({
  path: '/hbos/lims/audit',
  fields: { keyword: { state: keyword }, log_type: { state: logType }, target: { state: target } },
  load: loadAudit,
  failureMessage: '审计事件暂时无法加载，可能是当前账号没有查看权限。',
})

async function fetchAudit(append = false) {
  await runLoad(
    () => listLimsAudit({
      keyword: keyword.value.trim() || undefined,
      log_type: logType.value || undefined,
      doctype_target: target.value || undefined,
      cursor: append ? nextCursor.value || undefined : undefined,
    }),
    (response) => {
      events.value = append ? [...events.value, ...response.events] : response.events
      targets.value = response.targets
      total.value = response.total
      nextCursor.value = response.next_cursor || null
    },
    append,
    () => {
      events.value = []
      total.value = 0
      nextCursor.value = null
    },
  )
}

async function loadAudit() {
  await fetchAudit()
}
async function loadMore() {
  await fetchAudit(true)
}
function applyFilters() { void updateRoute() }
function openEvent(event: LimsAuditEvent) { selectedEvent.value = event; drawerOpen.value = true }
function shorten(value: string) { return value && value.length > 14 ? `${value.slice(0, 6)}…${value.slice(-6)}` : value || '—' }
function targetLabel(value: string) { return ({ 'HBOS Sample': '样品登记', 'HBOS Sample Task': '检验任务', 'HBOS Test Result': '检测记录', 'HBOS Result Revision': '结果修订', 'HBOS COA': 'COA 报告', 'HBOS Specification': '质量标准' } as Record<string, string>)[value] || value }
function fieldLabel(value: string) { return ({ result_status: '记录状态', result_value: '结果值', result_text: '结果描述', verdict: '判定', status: '状态', approver: '批准人', reviewer: '复核人' } as Record<string, string>)[value] || value }
function eventColor(value: string) { return { 提交: 'processing', 复核: 'warning', 批准: 'success', OOS: 'error', 删除: 'error', 'SoD 拦截': 'error', '越权拦截': 'error' }[value] || 'default' }

</script>
