<template>
  <section class="product-page lims-ledger-page">
    <div class="lims-ledger-heading">
      <div>
        <span class="page-kicker">LIMS · 受控记录</span>
        <h1>检验结果台账</h1>
        <p>限度快照、结果判定和签署链只读展示，所有变更仍须通过检验流程完成。</p>
      </div>
      <a-button :loading="loading" @click="loadLedger">刷新台账</a-button>
    </div>

    <a-alert v-if="errorMessage" class="lims-result-alert" type="error" show-icon closable :message="errorMessage" @close="errorMessage = ''" />

    <section class="lims-ledger-filters glass-surface" aria-label="台账筛选">
      <a-input-search v-model:value="searchInput" placeholder="搜索样品、批号、物料或检验项目" enter-button="搜索" allow-clear @search="applySearch" />
      <a-select :value="statusFilter" aria-label="按记录状态筛选" @change="setStatus">
        <a-select-option value="">全部状态</a-select-option>
        <a-select-option v-for="status in statusOptions" :key="status" :value="status">{{ status }}</a-select-option>
      </a-select>
      <a-select :value="verdictFilter" aria-label="按判定筛选" @change="setVerdict">
        <a-select-option value="">全部判定</a-select-option>
        <a-select-option value="合格">合格</a-select-option>
        <a-select-option value="不合格">不合格</a-select-option>
        <a-select-option value="OOS候选">OOS 候选</a-select-option>
      </a-select>
      <span class="lims-ledger-count">{{ totalSamples }} 个样品 · {{ results.length }} 条结果</span>
    </section>

    <div class="lims-ledger-layout">
      <aside class="lims-ledger-samples glass-surface" aria-label="样品列表">
        <div class="section-head"><div><h2>样品批次</h2><p>选择样品查看受控结果</p></div></div>
        <div v-if="!loading && !samples.length" class="lims-inline-empty">当前筛选下暂无样品</div>
        <button
          v-for="sample in samples"
          :key="sample.name"
          type="button"
          class="lims-ledger-sample"
          :class="{ active: sample.name === selectedSampleId }"
          @click="selectedSampleId = sample.name"
        >
          <span class="lims-ledger-sample-top"><strong>{{ sample.material_name || sample.name }}</strong><a-tag :color="statusColor(sample.status)">{{ sample.status || '未标记' }}</a-tag></span>
          <span class="lims-ledger-sample-meta">{{ sample.name }} · 批号 {{ sample.batch_no || '未填' }}</span>
          <span class="lims-ledger-sample-meta">{{ sample.sample_type || '未分类' }} · 标准 {{ sample.spec_version || sample.specification || '未指定' }}</span>
        </button>
        <a-button v-if="nextCursor" class="lims-ledger-more" block :loading="loadingMore" @click="loadMore">加载更多样品</a-button>
      </aside>

      <section class="lims-ledger-detail glass-surface" aria-live="polite">
        <div v-if="loading" class="lims-ledger-loading"><div class="lims-skeleton-panel"></div><div class="lims-skeleton-panel"></div></div>
        <template v-else-if="selectedSample">
          <div class="section-head lims-ledger-detail-head">
            <div><h2>{{ selectedSample.material_name || selectedSample.name }}</h2><p>{{ selectedSample.name }} · 批号 {{ selectedSample.batch_no || '未填' }} · {{ selectedSample.sample_type || '未分类' }}</p></div>
            <a-tag :color="statusColor(selectedSample.status)">{{ selectedSample.status || '未标记' }}</a-tag>
          </div>
          <div class="lims-ledger-context">
            <span>接收日期：{{ selectedSample.received_date || '—' }}</span>
            <span>检验截止：{{ selectedSample.test_due_date || '—' }}</span>
            <span>质量标准：{{ selectedSample.spec_version || selectedSample.specification || '—' }}</span>
            <span>报告日期：{{ selectedSample.report_date || '未发布' }}</span>
          </div>
          <a-table class="lims-ledger-table" :columns="columns" :data-source="selectedResults" :pagination="false" :scroll="{ x: 820 }" row-key="result_name" size="middle">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'result_name'"><RouterLink :to="{ name: 'lims-result-entry', params: { resultId: record.result_name } }" class="lims-result-link"><strong>{{ record.item_name }}</strong><small>{{ record.result_name }}</small></RouterLink></template>
              <template v-else-if="column.key === 'limits'"><span class="lims-ledger-limit">{{ record.limits_text || '记录型项目' }}</span></template>
              <template v-else-if="column.key === 'display'"><strong>{{ record.display || '待录入' }}</strong></template>
              <template v-else-if="column.key === 'verdict'"><a-tag :color="verdictColor(record.verdict)">{{ record.verdict || '待判定' }}</a-tag></template>
              <template v-else-if="column.key === 'result_status'"><a-tag :color="statusColor(record.result_status)">{{ record.result_status || '未知状态' }}</a-tag></template>
              <template v-else-if="column.key === 'analyst'"><span>{{ record.analyst || '—' }}</span></template>
            </template>
          </a-table>
          <div v-if="!selectedResults.length" class="lims-inline-empty">该样品暂无匹配结果</div>
          <div class="lims-ledger-note">此页面为受控只读台账。限度和判定来自 LIMS 领域服务，前端不重新计算、不覆盖原记录。</div>
        </template>
        <div v-else class="lims-result-empty"><InboxOutlined /><h3>请选择样品</h3><p>从左侧选择一个样品批次，查看检验项目和签署状态。</p></div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useLimsQueryPage } from '@/composables/useLimsQueryPage'
import { statusColor, verdictColor } from '@/views/limsStatus'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { InboxOutlined } from '@ant-design/icons-vue'
import { listLimsLedger, type LimsLedgerResult, type LimsLedgerSample } from '@/services/limsLedger'

const samples = ref<LimsLedgerSample[]>([])
const results = ref<LimsLedgerResult[]>([])
const selectedSampleId = ref('')
const totalSamples = ref(0)
const nextCursor = ref<string | null>(null)

const searchInput = ref('')
const statusFilter = ref('')
const verdictFilter = ref('')
const statusOptions = ['草稿', '已登记', '检验中', '检验完成', '已放行', 'OOS锁定']
const columns = [
  { title: '检验项目', key: 'result_name', width: 190 },
  { title: '冻结限度', key: 'limits', width: 150 },
  { title: '结果', key: 'display', width: 120 },
  { title: '判定', key: 'verdict', width: 100 },
  { title: '检验人', key: 'analyst', width: 140 },
  { title: '状态', key: 'result_status', width: 110 },
]

const selectedSample = computed(() => samples.value.find((sample) => sample.name === selectedSampleId.value) || null)
const selectedResults = computed(() => results.value.filter((result) => result.sample === selectedSampleId.value))

const { loading, loadingMore, errorMessage, updateRoute, runLoad } = useLimsQueryPage({
  path: '/hbos/lims/ledger',
  fields: { keyword: { state: searchInput }, status: { state: statusFilter }, verdict: { state: verdictFilter } },
  load: loadLedger,
  failureMessage: '受控台账暂时无法加载，请稍后重试。',
})

async function fetchLedger(append = false) {
  await runLoad(
    () => listLimsLedger({
      keyword: searchInput.value.trim() || undefined,
      status: statusFilter.value || undefined,
      verdict: verdictFilter.value || undefined,
      cursor: append ? nextCursor.value || undefined : undefined,
    }),
    (response) => {
      samples.value = append ? [...samples.value, ...response.samples] : response.samples
      results.value = append ? [...results.value, ...response.results] : response.results
      totalSamples.value = response.total_samples
      nextCursor.value = response.next_cursor || null
      if (!selectedSampleId.value || !samples.value.some((sample) => sample.name === selectedSampleId.value)) selectedSampleId.value = samples.value[0]?.name || ''
    },
    append,
    () => {
      samples.value = []
      results.value = []
      totalSamples.value = 0
      selectedSampleId.value = ''
      nextCursor.value = null
    },
  )
}

async function loadLedger() {
  await fetchLedger()
}
async function loadMore() {
  await fetchLedger(true)
}
function applySearch(value: string) { searchInput.value = value; void updateRoute() }
function setStatus(value: string) { statusFilter.value = value; void updateRoute() }
function setVerdict(value: string) { verdictFilter.value = value; void updateRoute() }

</script>
