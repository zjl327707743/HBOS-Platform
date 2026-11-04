<template>
  <section class="product-page lims-spec-page">
    <header class="lims-spec-heading">
      <div>
        <span class="page-kicker">LIMS · 检验依据</span>
        <h1>质量标准</h1>
        <p>查看物料对应的标准版本、检验项目、方法和限度，作为检验过程的只读依据。</p>
      </div>
      <a-button :loading="loading" @click="loadSpecifications">刷新列表</a-button>
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
    <div class="lims-spec-overview" aria-label="质量标准概览">
      <article
        v-for="card in overviewCards"
        :key="card.label"
        class="glass-surface lims-spec-overview-card"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.caption }}</small>
      </article>
    </div>
    <section class="glass-surface lims-spec-panel" aria-live="polite">
      <div class="section-head">
        <div>
          <h2>标准版本清单</h2>
          <p>生效版本用于样品登记和结果判定，历史版本保留追溯</p>
        </div>
        <span class="lims-readonly-badge">只读视图</span>
      </div>
      <div class="lims-spec-filters" aria-label="标准筛选">
        <a-input-search
          v-model:value="searchInput"
          placeholder="搜索标准编号、标准名称、物料或版本"
          enter-button="搜索"
          allow-clear
          @search="applySearch"
        />
        <a-select :value="statusFilter" aria-label="按标准状态筛选" @change="setStatus">
          <a-select-option value="">全部状态</a-select-option>
          <a-select-option v-for="status in statusOptions" :key="status" :value="status">
            {{ status }}
          </a-select-option>
        </a-select>
        <span class="lims-spec-count">{{ total }} 个版本</span>
      </div>
      <a-table
        :columns="columns"
        :data-source="specifications"
        :loading="loading"
        :pagination="false"
        :scroll="{ x: 1060 }"
        row-key="specification_id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'specification_id'">
            <strong>{{ record.spec_code || record.specification_id }}</strong>
            <small class="lims-spec-subline">{{ record.specification_id }}</small>
          </template>
          <template v-else-if="column.key === 'material'">
            <span>{{ record.material_name || '—' }}</span>
            <small class="lims-spec-subline">{{ record.material_code || '未填物料编码' }}</small>
          </template>
          <template v-else-if="column.key === 'version'">
            <span class="lims-spec-version">V{{ record.version || '—' }}</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ record.status || '未标记' }}</a-tag>
          </template>
          <template v-else-if="column.key === 'actions'">
            <button
              type="button"
              class="lims-text-action"
              @click="openDetail(record.specification_id)"
            >
              查看标准
              <ArrowRightOutlined />
            </button>
          </template>
        </template>
      </a-table>
      <div v-if="!loading && !specifications.length" class="lims-result-empty">
        <BookOutlined />
        <h3>当前筛选下暂无质量标准</h3>
        <p>可以调整关键词或状态筛选。</p>
      </div>
      <a-button
        v-if="nextCursor"
        class="lims-spec-more"
        block
        :loading="loadingMore"
        @click="loadMore"
      >
        加载更多标准
      </a-button>
    </section>
    <a-drawer
      v-model:open="drawerOpen"
      title="质量标准详情"
      placement="right"
      width="min(760px, 94vw)"
      destroy-on-close
    >
      <div v-if="detailLoading" class="lims-spec-drawer-loading">
        <div class="lims-skeleton-panel"></div>
        <div class="lims-skeleton-panel"></div>
      </div>
      <template v-else-if="detail">
        <div class="lims-spec-document-head">
          <span class="page-kicker">检验依据 · 版本受控</span>
          <h2>{{ detail.spec_name || detail.spec_code }}</h2>
          <p>
            {{ detail.specification_id }}
            ·
            {{ detail.material_name || '未填物料' }}
            · V
            {{ detail.version || '—' }}
          </p>
          <a-tag :color="statusColor(detail.status)">{{ detail.status || '未标记' }}</a-tag>
        </div>
        <a-descriptions class="lims-spec-descriptions" :column="2" bordered size="small">
          <a-descriptions-item label="规格编号">{{ detail.spec_code || '—' }}</a-descriptions-item>
          <a-descriptions-item label="物料编码">{{ detail.material_code || '—' }}</a-descriptions-item>
          <a-descriptions-item label="标准依据">{{ detail.standard_source || '—' }}</a-descriptions-item>
          <a-descriptions-item label="生效日期">{{ detail.effective_date || '—' }}</a-descriptions-item>
          <a-descriptions-item label="储存条件">{{ detail.storage_condition || '—' }}</a-descriptions-item>
          <a-descriptions-item label="留样量">{{ detail.retain_sample_qty || '—' }}</a-descriptions-item>
          <a-descriptions-item label="被替代版本">{{ detail.supersedes || '无' }}</a-descriptions-item>
          <a-descriptions-item :span="2" label="备注">{{ detail.remarks || '—' }}</a-descriptions-item>
        </a-descriptions>
        <div class="lims-spec-items-head">
          <div>
            <h3>检验项目与限度</h3>
            <p>检验员录入结果时应以此版本为准</p>
          </div>
          <span>{{ detail.items.length }} 项</span>
        </div>
        <a-table
          :data-source="detail.items"
          :pagination="false"
          :scroll="{ x: 640 }"
          row-key="item"
          size="small"
        >
          <a-table-column title="检验项目" key="item_name" data-index="item_name" />
          <a-table-column title="方法 / SOP" key="method_sop" data-index="method_sop" />
          <a-table-column title="限度模式" key="limits_type" data-index="limits_type" />
          <a-table-column title="限度" key="limits_text" data-index="limits_text" />
          <a-table-column title="单位" key="unit" data-index="unit" />
        </a-table>
        <div class="lims-spec-readonly-note">质量标准只读展示。标准新增、修订、生效和废止继续由 LIMS 领域服务和管理端执行。</div>
      </template>
      <a-empty v-else description="质量标准详情暂时无法加载" />
    </a-drawer>
  </section>
</template>

<script setup lang="ts">
import { useLimsQueryPage } from '@/composables/useLimsQueryPage'
import { statusColor } from '@/views/limsStatus'
import { computed, ref } from 'vue'
import { ArrowRightOutlined, BookOutlined } from '@ant-design/icons-vue'
import {
  getLimsSpecification,
  listLimsSpecifications,
  type LimsSpecificationDetail,
  type LimsSpecificationRow,
} from '@/services/limsSpecifications'
const specifications = ref<LimsSpecificationRow[]>([])
const total = ref(0)
const nextCursor = ref<string | null>(null)
const detailLoading = ref(false)
const searchInput = ref('')
const statusFilter = ref('')
const drawerOpen = ref(false)
const detail = ref<LimsSpecificationDetail | null>(null)
const statusOptions = [
  '草稿',
  '已生效',
  '已废止'
]
const columns = [
  {
    title: '标准编号',
    key: 'specification_id',
    width: 210
  },
  {
    title: '标准名称',
    dataIndex: 'spec_name',
    key: 'spec_name',
    width: 220
  },
  {
    title: '物料',
    key: 'material',
    width: 190
  },
  {
    title: '版本',
    key: 'version',
    width: 80
  },
  {
    title: '标准依据',
    dataIndex: 'standard_source',
    key: 'standard_source',
    width: 110
  },
  {
    title: '生效日期',
    dataIndex: 'effective_date',
    key: 'effective_date',
    width: 120
  },
  {
    title: '状态',
    key: 'status',
    width: 100
  },
  {
    title: '操作',
    key: 'actions',
    width: 125
  },
]
const overviewCards = computed(() => [
  {
    label: '标准版本',
    value: total.value,
    caption: '当前筛选结果'
  },
  {
    label: '已生效',
    value: specifications.value.filter(row => row.status === '已生效').length,
    caption: '可供样品引用'
  },
  {
    label: '草稿',
    value: specifications.value.filter(row => row.status === '草稿').length,
    caption: '等待管理维护'
  },
  {
    label: '已废止',
    value: specifications.value.filter(row => row.status === '已废止').length,
    caption: '保留历史追溯'
  },
])
const { loading, loadingMore, errorMessage, updateRoute, runLoad } = useLimsQueryPage({
  path: '/hbos/lims/specifications',
  fields: { keyword: { state: searchInput }, status: { state: statusFilter } },
  load: loadSpecifications,
  failureMessage: '质量标准暂时无法加载，请稍后重试。',
})
async function fetchSpecifications(append = false) {
  await runLoad(() => listLimsSpecifications({
    keyword: searchInput.value.trim() || undefined,
    status: statusFilter.value || undefined,
    cursor: append ? nextCursor.value || undefined : undefined
  }), response => {
    specifications.value = append ? [...specifications.value, ...response.specifications] : response.specifications
    total.value = response.total
    nextCursor.value = response.next_cursor || null
  }, append, () => {
    specifications.value = []
    total.value = 0
    nextCursor.value = null
  })
}
async function loadSpecifications() {
  await fetchSpecifications()
}
async function loadMore() {
  await fetchSpecifications(true)
}
function applySearch(value: string) {
  searchInput.value = value
  void updateRoute()
}
function setStatus(value: string) {
  statusFilter.value = value
  void updateRoute()
}
async function openDetail(specificationId: string) {
  drawerOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await getLimsSpecification(specificationId)
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
.lims-spec-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}
.lims-spec-heading h1 {
  margin: 6px 0 4px;
  font-size: clamp(24px, 3vw, 34px);
  letter-spacing: -.02em;
}
.lims-spec-heading p {
  margin: 0;
  color: var(--hbos-text-muted);
  font-size: 13px;
}
.lims-spec-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.lims-spec-overview-card {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 16px 18px;
  border-radius: 16px;
}
.lims-spec-overview-card span,.lims-spec-overview-card small {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-spec-overview-card strong {
  font-size: 26px;
  color: var(--hbos-text-primary);
}
.lims-spec-overview-card small {
  color: var(--hbos-text-secondary);
}
.lims-spec-panel {
  padding: 20px;
  border-radius: 18px;
}
.lims-spec-filters {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 150px auto;
  gap: 10px;
  align-items: center;
  margin: 14px 0 16px;
}
.lims-spec-count {
  color: var(--hbos-text-muted);
  font-size: 12px;
  text-align: right;
}
.lims-spec-subline {
  display: block;
  margin-top: 4px;
  color: var(--hbos-text-muted);
  font-size: 11px;
}
.lims-spec-version {
  color: var(--brand-lims, #087f72);
  font-weight: 700;
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
.lims-spec-more {
  margin-top: 14px;
}
.lims-spec-document-head {
  padding: 4px 0 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--hbos-border-default);
}
.lims-spec-document-head h2 {
  margin: 8px 0 3px;
}
.lims-spec-document-head p {
  margin: 0 0 10px;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-spec-descriptions {
  margin-bottom: 20px;
}
.lims-spec-items-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin: 20px 0 10px;
}
.lims-spec-items-head h3 {
  margin: 0;
  font-size: 16px;
}
.lims-spec-items-head p {
  margin: 4px 0 0;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-spec-items-head > span {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.lims-spec-readonly-note {
  margin-top: 18px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(8,127,114,.07);
  color: var(--hbos-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}
.lims-spec-drawer-loading {
  display: grid;
  gap: 12px;
}
.lims-spec-drawer-loading .lims-skeleton-panel {
  min-height: 100px;
}
@media (max-width:760px) {
  .lims-spec-heading {
    flex-direction: column;
  }
  .lims-spec-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .lims-spec-panel {
    padding: 14px;
  }
  .lims-spec-filters {
    grid-template-columns: 1fr;
  }
  .lims-spec-count {
    text-align: left;
  }
  .lims-spec-heading :deep(.ant-btn) {
    width: 100%;
  }
}
</style>
