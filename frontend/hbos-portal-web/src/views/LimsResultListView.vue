<template>
  <section class="product-page lims-result-list">
    <div class="lims-result-list-heading">
      <div>
        <span class="page-kicker">LIMS · 结果管理</span>
        <h1>检验结果清单</h1>
        <p>从样品、批次和检验项目进入结果上下文；提交、复核和批准由 LIMS 服务校验。</p>
      </div>
      <a-button :loading="loading" @click="loadResults()"><ReloadOutlined /> 刷新清单</a-button>
    </div>

    <a-alert v-if="errorMessage" class="lims-result-alert" type="error" show-icon closable :message="errorMessage" @close="errorMessage = ''" />

    <section class="lims-result-filters glass-surface" aria-label="结果筛选">
      <a-input-search
        v-model:value="searchInput"
        class="lims-result-search"
        placeholder="搜索记录号、样品、批次、物料或项目"
        enter-button="搜索"
        allow-clear
        @search="applySearch"
      >
        <template #prefix><SearchOutlined /></template>
      </a-input-search>
      <label>
        <span>记录状态</span>
        <a-select :value="statusFilter" aria-label="按记录状态筛选" @change="setStatus">
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option v-for="status in statusOptions" :key="status" :value="status">{{ status }}</a-select-option>
        </a-select>
      </label>
      <label>
        <span>判定</span>
        <a-select :value="verdictFilter" aria-label="按判定筛选" @change="setVerdict">
          <a-select-option value="">全部判定</a-select-option>
          <a-select-option value="合格">合格</a-select-option>
          <a-select-option value="不合格">不合格</a-select-option>
          <a-select-option value="OOS候选">OOS 候选</a-select-option>
          <a-select-option value="不适用">不适用</a-select-option>
        </a-select>
      </label>
      <span class="lims-result-count">{{ total }} 条记录</span>
    </section>

    <section class="lims-result-panel glass-surface" aria-live="polite">
      <div class="section-head">
        <div><h2>结果记录</h2><p>冻结限度、判定和签署链在记录详情中完整展示</p></div>
        <span class="lims-readonly-badge">结果状态只读投影</span>
      </div>

      <a-table
        :columns="columns"
        :data-source="results"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: 900 }"
        row-key="result_name"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'result_name'">
            <RouterLink class="lims-result-link" :to="{ name: 'lims-result-entry', params: { resultId: record.result_name } }">
              <strong>{{ record.result_name }}</strong><small>{{ record.item_name }}</small>
            </RouterLink>
          </template>
          <template v-else-if="column.key === 'sample'">
            <span class="lims-result-cell-main">{{ record.sample }}</span><small>{{ record.material_name }} · {{ record.batch_no || '未填批号' }}</small>
          </template>
          <template v-else-if="column.key === 'result_value'">
            <span class="lims-result-value">{{ record.display || '待录入' }}</span>
          </template>
          <template v-else-if="column.key === 'verdict'">
            <a-tag :color="verdictColor(record.verdict)">{{ record.verdict || '待判定' }}</a-tag>
          </template>
          <template v-else-if="column.key === 'result_status'">
            <a-tag :color="statusColor(record.result_status)">{{ record.result_status || '未知状态' }}</a-tag>
          </template>
          <template v-else-if="column.key === 'actions'">
            <RouterLink class="lims-result-action" :to="{ name: 'lims-result-entry', params: { resultId: record.result_name } }">查看记录 <ArrowRightOutlined /></RouterLink>
          </template>
        </template>
      </a-table>

      <div v-if="!loading && !results.length" class="lims-result-empty">
        <InboxOutlined /><h3>当前筛选下没有结果记录</h3><p>可以调整关键词或状态筛选，或等待 LIMS 返回新的记录。</p>
      </div>
      <div class="lims-pagination" aria-live="polite">
        <span>已加载 {{ results.length }} / {{ total }} 条</span>
        <a-button v-if="nextCursor" :loading="loadingMore" :disabled="loading" @click="loadResults(true)">加载更多</a-button>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { useLimsQueryPage } from '@/composables/useLimsQueryPage'
import { statusColor, verdictColor } from '@/views/limsStatus'
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ArrowRightOutlined, InboxOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue'
import { listLimsResults, type LimsResultRow } from '@/services/limsResults'

const results = ref<LimsResultRow[]>([])
const total = ref(0)
const nextCursor = ref<string | null>(null)

const searchInput = ref('')
const statusFilter = ref('')
const verdictFilter = ref('')
const statusOptions = ['草稿', '已提交', '已复核', '已批准', '已修订']
const columns = [
  { title: '记录 / 项目', key: 'result_name', width: 185 },
  { title: '样品 / 批次', key: 'sample', width: 225 },
  { title: '结果值', key: 'result_value', width: 125 },
  { title: '判定', key: 'verdict', width: 105 },
  { title: '状态', key: 'result_status', width: 105 },
  { title: '操作', key: 'actions', width: 120 },
]

const { loading, loadingMore, errorMessage, updateRoute, runLoad } = useLimsQueryPage({
  path: '/hbos/lims/results',
  fields: { keyword: { state: searchInput }, status: { state: statusFilter }, verdict: { state: verdictFilter } },
  load: loadResults,
  failureMessage: '检验结果暂时无法加载，请稍后重试。',
})

async function loadResults(append = false) {
  if (append && !nextCursor.value) return
  await runLoad(
    () => listLimsResults({
      cursor: append ? nextCursor.value || undefined : undefined,
      keyword: searchInput.value.trim() || undefined,
      status: statusFilter.value || undefined,
      verdict: verdictFilter.value || undefined,
    }),
    (response) => {
      results.value = append ? [...new Map([...results.value, ...response.results].map(row => [row.result_name, row])).values()] : response.results
      nextCursor.value = response.next_cursor || null
      total.value = response.total
    },
    append,
    () => {
      nextCursor.value = null
      results.value = []
      total.value = 0
    },
  )
}

function applySearch(value: string) { searchInput.value = value; void updateRoute() }
function setStatus(value: string) { statusFilter.value = value; void updateRoute() }
function setVerdict(value: string) { verdictFilter.value = value; void updateRoute() }

</script>
