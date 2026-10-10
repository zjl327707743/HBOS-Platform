<template>
  <section class="product-page lims-coa-page">
    <header class="lims-coa-heading">
      <div>
        <span class="page-kicker">LIMS · 质量凭证</span>
        <h1>
          检验报告
          <small>（COA）</small>
        </h1>
        <p>按样品和批号查阅受控检验报告，报告内容与发布状态来自 LIMS 领域服务。</p>
      </div>
      <a-button :loading="loading" @click="loadCoas">刷新列表</a-button>
    </header>
    <a-alert
      v-if="errorMessage"
      class="lims-result-alert"
      type="error"
      show-icon
      closable
      :message="errorMessage"
      @close="errorMessage = ''"
    />
    <div class="lims-coa-overview" aria-label="报告概览">
      <article
        v-for="card in overviewCards"
        :key="card.label"
        class="glass-surface lims-coa-overview-card"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.caption }}</small>
      </article>
    </div>
    <section class="glass-surface lims-coa-panel" aria-live="polite">
      <div class="section-head">
        <div>
          <h2>报告清单</h2>
          <p>只读查看报告版本、质量标准和签署进度</p>
        </div>
        <span class="lims-readonly-badge">只读视图</span>
      </div>
      <div class="lims-coa-filters" aria-label="报告筛选">
        <a-input-search
          v-model:value="searchInput"
          placeholder="搜索报告号、样品、批号或物料"
          enter-button="搜索"
          allow-clear
          @search="applySearch"
        />
        <a-select :value="statusFilter" aria-label="按报告状态筛选" @change="setStatus">
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option v-for="status in statusOptions" :key="status" :value="status">
            {{ status }}
          </a-select-option>
        </a-select>
        <span class="lims-coa-count">{{ total }} 份报告</span>
      </div>
      <a-table
        :columns="columns"
        :data-source="coas"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: 940 }"
        row-key="coa_id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'coa_id'">
            <strong class="lims-coa-id">{{ record.coa_id }}</strong>
            <small class="lims-coa-subline">{{ record.sample }}</small>
          </template>
          <template v-else-if="column.key === 'material'">
            <span>{{ record.material_name || '—' }}</span>
            <small class="lims-coa-subline">
              {{ record.material_code || '未填物料编码' }}
              · 批号
              {{ record.batch_no || '未填' }}
            </small>
          </template>
          <template v-else-if="column.key === 'report_status'">
            <a-tag :color="statusColor(record.report_status)">{{ record.report_status || '未标记' }}</a-tag>
          </template>
          <template v-else-if="column.key === 'review'">
            <span>{{ record.qa_reviewer || '未审核' }}</span>
            <small class="lims-coa-subline">{{ record.qa_reviewed_at || '—' }}</small>
          </template>
          <template v-else-if="column.key === 'actions'">
            <button type="button" class="lims-text-action" @click="openDetail(record.coa_id)">
              查看报告
              <ArrowRightOutlined />
            </button>
          </template>
        </template>
      </a-table>
      <div v-if="!loading && !coas.length" class="lims-result-empty">
        <FileTextOutlined />
        <h3>当前筛选下暂无检验报告</h3>
        <p>检验结果全部批准后，质量凭证会出现在这里。</p>
      </div>
      <a-button
        v-if="nextCursor"
        class="lims-coa-more"
        block
        :loading="loadingMore"
        @click="loadMore"
      >
        加载更多报告
      </a-button>
    </section>
    <a-drawer
      v-model:open="drawerOpen"
      title="检验报告详情"
      placement="right"
      width="min(720px, 92vw)"
      destroy-on-close
    >
      <div v-if="detailLoading" class="lims-coa-drawer-loading">
        <div class="lims-skeleton-panel"></div>
        <div class="lims-skeleton-panel"></div>
      </div>
      <template v-else-if="detail">
        <div class="lims-coa-document-head">
          <span class="page-kicker">Certificate of Analysis</span>
          <h2>{{ detail.material_name || detail.coa_id }}</h2>
          <p>{{ detail.coa_id }} · 样品 {{ detail.sample }} · 批号 {{ detail.batch_no || '未填' }}</p>
          <a-tag :color="statusColor(detail.report_status)">{{ detail.report_status || '未标记' }}</a-tag>
        </div>
        <a-descriptions class="lims-coa-descriptions" :column="2" bordered size="small">
          <a-descriptions-item label="物料编码">{{ detail.material_code || '—' }}</a-descriptions-item>
          <a-descriptions-item label="质量标准版本">{{ detail.spec_version || '—' }}</a-descriptions-item>
          <a-descriptions-item label="QA 审核人">{{ detail.qa_reviewer || '—' }}</a-descriptions-item>
          <a-descriptions-item label="审核时间">{{ detail.qa_reviewed_at || '—' }}</a-descriptions-item>
          <a-descriptions-item label="发布人">{{ detail.published_by || '—' }}</a-descriptions-item>
          <a-descriptions-item label="发布时间">{{ detail.published_at || '—' }}</a-descriptions-item>
          <a-descriptions-item :span="2" label="备注">{{ detail.remarks || '—' }}</a-descriptions-item>
        </a-descriptions>
        <div class="lims-coa-items-head">
          <div>
            <h3>检验项目结果</h3>
            <p>结果、标准限度和判定均为报告快照</p>
          </div>
          <span>{{ detail.items.length }} 项</span>
        </div>
        <a-table
          :data-source="detail.items"
          :pagination="false"
          :scroll="{ x: 590 }"
          row-key="test_item"
          size="small"
        >
          <a-table-column title="检验项目" key="item_name" data-index="item_name" />
          <a-table-column title="方法 / SOP" key="method_sop" data-index="method_sop" />
          <a-table-column title="标准限度" key="standard" data-index="standard" />
          <a-table-column title="结果" key="result" data-index="result" />
          <a-table-column title="判定" key="verdict" data-index="verdict">
            <template #default="{ text }">
              <a-tag :color="verdictColor(text)">{{ text || '待判定' }}</a-tag>
            </template>
          </a-table-column>
        </a-table>
        <div class="lims-coa-readonly-note">报告为受控质量凭证。Portal 只展示当前账号可见的内容，不在前端重新计算或修改报告。</div>
      </template>
      <a-empty v-else description="报告详情暂时无法加载" />
    </a-drawer>
  </section>
</template>

<script setup lang="ts">
import { useLimsQueryPage } from '@/composables/useLimsQueryPage'
import { statusColor, verdictColor } from '@/views/limsStatus'
import { computed, ref } from 'vue'
import { ArrowRightOutlined, FileTextOutlined } from '@ant-design/icons-vue'
import { getLimsCoa, listLimsCoas, type LimsCoaDetail, type LimsCoaRow } from '@/services/limsCoa'
const coas = ref<LimsCoaRow[]>([])
const total = ref(0)
const nextCursor = ref<string | null>(null)
const detailLoading = ref(false)
const searchInput = ref('')
const statusFilter = ref('')
const drawerOpen = ref(false)
const detail = ref<LimsCoaDetail | null>(null)
const statusOptions = [
  '草稿',
  '已审核',
  '已发布'
]
const columns = [
  {
    title: '报告编号 / 样品',
    key: 'coa_id',
    width: 220
  },
  {
    title: '物料 / 批号',
    key: 'material',
    width: 220
  },
  {
    title: '质量标准',
    dataIndex: 'spec_version',
    key: 'spec_version',
    width: 110
  },
  {
    title: '状态',
    key: 'report_status',
    width: 100
  },
  {
    title: 'QA 审核',
    key: 'review',
    width: 160
  },
  {
    title: '操作',
    key: 'actions',
    width: 120
  },
]
const overviewCards = computed(() => [
  {
    label: '报告总数',
    value: total.value,
    caption: '当前筛选结果'
  },
  {
    label: '待审核',
    value: coas.value.filter(row => row.report_status === '草稿').length,
    caption: '等待 QA 检查'
  },
  {
    label: '待发布',
    value: coas.value.filter(row => row.report_status === '已审核').length,
    caption: '等待质量负责人'
  },
  {
    label: '已发布',
    value: coas.value.filter(row => row.report_status === '已发布').length,
    caption: '可作为质量凭证'
  },
])
const { loading, loadingMore, errorMessage, updateRoute, runLoad } = useLimsQueryPage({
  path: '/hbos/lims/coa',
  fields: { keyword: { state: searchInput }, status: { state: statusFilter } },
  load: loadCoas,
  failureMessage: '检验报告暂时无法加载，请稍后重试。',
})
async function fetchCoas(append = false) {
  await runLoad(() => listLimsCoas({
    keyword: searchInput.value.trim() || undefined,
    status: statusFilter.value || undefined,
    cursor: append ? nextCursor.value || undefined : undefined
  }), response => {
    coas.value = append ? [...coas.value, ...response.coas] : response.coas
    total.value = response.total
    nextCursor.value = response.next_cursor || null
  }, append, () => {
    coas.value = []
    total.value = 0
    nextCursor.value = null
  })
}
async function loadCoas() {
  await fetchCoas()
}
async function loadMore() {
  await fetchCoas(true)
}
function applySearch(value: string) {
  searchInput.value = value
  void updateRoute()
}
function setStatus(value: string) {
  statusFilter.value = value
  void updateRoute()
}
async function openDetail(coaId: string) {
  drawerOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await getLimsCoa(coaId)
  }
  catch {
    detail.value = null
  }
  finally {
    detailLoading.value = false
  }
}
</script>

<style scoped>
.lims-coa-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.lims-coa-heading h1 {
  margin: 6px 0 4px;
  font-size: clamp(24px, 3vw, 34px);
  letter-spacing: -.02em;
}
.lims-coa-heading h1 small {
  font-size: .55em;
  color: var(--hbos-text-muted);
  font-weight: 600;
}
.lims-coa-heading p {
  margin: 0;
  color: var(--hbos-text-muted);
  font-size: 13px;
}
.lims-coa-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.lims-coa-overview-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 16px 18px;
  border-radius: 16px;
}
.lims-coa-overview-card span,.lims-coa-overview-card small {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-coa-overview-card strong {
  font-size: 26px;
  color: var(--hbos-text-primary);
}
.lims-coa-overview-card small {
  color: var(--hbos-text-secondary);
}
.lims-coa-panel {
  padding: 20px;
  border-radius: 18px;
}
.lims-coa-filters {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 150px auto;
  gap: 10px;
  align-items: center;
  margin: 14px 0 16px;
}
.lims-coa-count {
  color: var(--hbos-text-muted);
  font-size: 12px;
  text-align: right;
}
.lims-coa-id,.lims-coa-subline {
  display: block;
}
.lims-coa-subline {
  margin-top: 4px;
  color: var(--hbos-text-muted);
  font-size: 11px;
}
.lims-text-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 36px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--brand-lims, #087f72);
  font-weight: 600;
  cursor: pointer;
}
.lims-text-action:hover {
  color: var(--hbos-text-primary);
}
.lims-coa-more {
  margin-top: 14px;
}
.lims-coa-document-head {
  position: relative;
  padding: 4px 0 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--hbos-border-default);
}
.lims-coa-document-head h2 {
  margin: 8px 0 3px;
}
.lims-coa-document-head p {
  margin: 0 0 10px;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-coa-descriptions {
  margin-bottom: 20px;
}
.lims-coa-items-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin: 20px 0 10px;
}
.lims-coa-items-head h3 {
  margin: 0;
  font-size: 16px;
}
.lims-coa-items-head p {
  margin: 4px 0 0;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-coa-items-head > span {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-coa-readonly-note {
  margin-top: 18px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(8,127,114,.07);
  color: var(--hbos-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}
.lims-coa-drawer-loading {
  display: grid;
  gap: 12px;
}
.lims-coa-drawer-loading .lims-skeleton-panel {
  min-height: 100px;
}
@media (max-width:760px) {
  .lims-coa-heading {
    flex-direction: column;
  }
  .lims-coa-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .lims-coa-panel {
    padding: 14px;
  }
  .lims-coa-filters {
    grid-template-columns: 1fr;
  }
  .lims-coa-count {
    text-align: left;
  }
  .lims-coa-heading :deep(.ant-btn) {
    width: 100%;
  }
}
</style>
