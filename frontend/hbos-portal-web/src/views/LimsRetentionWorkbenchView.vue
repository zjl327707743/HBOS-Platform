<template>
  <section class="retention-page">
    <header class="retention-heading">
      <div>
        <span class="page-kicker">LIMS · 留样管理</span>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>
      <div class="retention-heading-actions">
        <span class="readonly-note">
          <SafetyCertificateOutlined />
          数据由留样业务服务提供
        </span>
        <a-button :loading="loading" @click="loadData">
          <ReloadOutlined />
          刷新
        </a-button>
      </div>
    </header>
    <nav class="retention-tabs" aria-label="留样管理分区">
      <RouterLink v-for="tab in tabs" :key="tab.path" :to="tab.path" exact-active-class="active">
        <component :is="tab.icon" />
        {{ tab.label }}
      </RouterLink>
    </nav>
    <a-alert
      v-if="errorMessage"
      class="retention-alert"
      type="error"
      show-icon
      :message="errorMessage"
      closable
      @close="errorMessage = ''"
    />
    <template v-if="section === 'workbench'">
      <section class="retention-kpis" aria-label="留样概览">
        <article
          v-for="card in kpiCards"
          :key="card.label"
          class="glass-surface retention-kpi"
          :class="`tone-${card.tone}`"
        >
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.caption }}</small>
        </article>
      </section>
      <section class="retention-work-grid">
        <article class="glass-surface retention-panel attention-panel">
          <div class="section-head">
            <div>
              <h2>今天先处理</h2>
              <p>按检验员的工作顺序，把需要动作的留样放在前面。</p>
            </div>
            <span class="panel-count">{{ attentionItems.length }} 项</span>
          </div>
          <div v-if="attentionItems.length" class="attention-list">
            <button
              v-for="item in attentionItems"
              :key="item.id"
              type="button"
              class="attention-item"
              @click="openAttention(item)"
            >
              <span class="attention-icon" :class="`attention-${item.tone}`">
                <component :is="item.icon" />
              </span>
              <span class="attention-copy">
                <strong>{{ item.title }}</strong>
                <small>{{ item.subtitle }}</small>
              </span>
              <span class="attention-status" :class="`status-${statusTone(item.status)}`">
                {{ item.status }}
              </span>
              <ArrowRightOutlined />
            </button>
          </div>
          <div v-else class="retention-empty">
            <CheckCircleOutlined />
            <strong>当前没有需要优先处理的留样</strong>
            <span>观察、使用和处理申请会在这里集中提醒。</span>
          </div>
        </article>
        <article class="glass-surface retention-panel flow-panel">
          <div class="section-head">
            <div>
              <h2>留样流程</h2>
              <p>从登记入库到观察、使用和处理，全程保留批次线索。</p>
            </div>
          </div>
          <div class="flow-steps">
            <RouterLink
              v-for="step in flowSteps"
              :key="step.label"
              :to="step.path"
              class="flow-step"
            >
              <span class="flow-number">{{ step.number }}</span>
              <span>
                <strong>{{ step.label }}</strong>
                <small>{{ step.caption }}</small>
              </span>
              <ArrowRightOutlined />
            </RouterLink>
          </div>
          <div class="lab-tip">
            <ExperimentOutlined />
            <span>
              <strong>检验员提示</strong>
              <br />
              先扫批号或留样编号，再从右侧查看结存、储存条件和下次观察日期。
            </span>
          </div>
        </article>
      </section>
      <section class="glass-surface retention-panel work-summary-panel">
        <div class="section-head">
          <div>
            <h2>留样库存概览</h2>
            <p>只显示当前账号可查看的批次，数量为业务服务实时派生值。</p>
          </div>
          <RouterLink class="text-link" to="/hbos/lims/retains/samples">
            查看全部台账
            <ArrowRightOutlined />
          </RouterLink>
        </div>
        <a-table
          :columns="sampleColumns"
          :data-source="samples.slice(0, 5)"
          :loading="loading"
          :pagination="false"
          row-key="name"
          size="middle"
          :scroll="{ x: 860 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'sample'">
              <strong>{{ record.product_name || record.sample_name }}</strong>
              <small class="subline">{{ record.sample_name }} · {{ record.batch_no }}</small>
            </template>
            <template v-else-if="column.key === 'stock'">
              <span class="stock-value">{{ record.available_qty }} {{ record.qty_uom }}</span>
              <small class="subline">总量 {{ record.current_qty }} · 预占 {{ record.reserved_qty }}</small>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
            </template>
            <template v-else-if="column.key === 'due'">
              <span :class="dueClass(record.retention_due_date)">{{ record.retention_due_date || '—' }}</span>
            </template>
          </template>
        </a-table>
      </section>
    </template>
    <template v-else-if="section === 'samples'">
      <section class="glass-surface retention-panel">
        <div class="section-head">
          <div>
            <h2>留样登记与台账</h2>
            <p>批次、结存、储存位置和留样期至集中查看。</p>
          </div>
          <span class="panel-count">{{ envelope.samples_total }} 条</span>
        </div>
        <div class="retention-filters">
          <a-input-search
            v-model:value="keyword"
            placeholder="搜索留样编号、产品、样品或批号"
            enter-button="查询"
            allow-clear
            @search="applyFilters"
          />
          <a-select v-model:value="status" allow-clear placeholder="全部状态" @change="applyFilters">
            <a-select-option v-for="item in sampleStatuses" :key="item" :value="item">
              {{ item }}
            </a-select-option>
          </a-select>
          <a-button @click="clearFilters">清空</a-button>
        </div>
        <a-table
          :columns="sampleColumnsDetailed"
          :data-source="samples"
          :loading="loading"
          :pagination="false"
          row-key="name"
          size="middle"
          :scroll="{ x: 1120 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'sample'">
              <strong>{{ record.product_name || record.sample_name }}</strong>
              <small class="subline">{{ record.name }} · {{ record.sample_name }}</small>
            </template>
            <template v-else-if="column.key === 'stock'">
              <span class="stock-value">{{ record.available_qty }} {{ record.qty_uom }}</span>
              <small class="subline">总量 {{ record.current_qty }} · 预占 {{ record.reserved_qty }}</small>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
            </template>
            <template v-else-if="column.key === 'due'">
              <span :class="dueClass(record.retention_due_date)">{{ record.retention_due_date || '—' }}</span>
            </template>
            <template v-else-if="column.key === 'action'">
              <button type="button" class="text-action" @click="openSample(record)">
                查看详情
                <ArrowRightOutlined />
              </button>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && !samples.length" class="retention-empty">
          <InboxOutlined />
          <strong>当前筛选下没有留样记录</strong>
          <span>可以调整关键词或状态，或等待新的留样登记进入台账。</span>
        </div>
      </section>
    </template>
    <template v-else-if="section === 'products'">
      <section class="glass-surface retention-panel">
        <div class="section-head">
          <div>
            <h2>留样产品规则</h2>
            <p>检验员登记时使用的留样量、储存和观察规则，只读查看。</p>
          </div>
          <span class="panel-count">{{ envelope.products_total }} 个产品</span>
        </div>
        <div class="retention-filters">
          <a-input-search
            v-model:value="keyword"
            placeholder="搜索产品编码、名称或类别"
            enter-button="查询"
            allow-clear
            @search="applyFilters"
          />
          <a-select v-model:value="active" allow-clear placeholder="全部产品">
            <a-select-option value="启用">启用</a-select-option>
            <a-select-option value="停用">停用</a-select-option>
          </a-select>
          <a-button @click="applyFilters">查询</a-button>
        </div>
        <a-table
          :columns="productColumns"
          :data-source="products"
          :loading="loading"
          :pagination="false"
          row-key="name"
          size="middle"
          :scroll="{ x: 980 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'product'">
              <strong>{{ record.product_name }}</strong>
              <small class="subline">{{ record.product_code }} · {{ record.category }}</small>
            </template>
            <template v-else-if="column.key === 'active'">
              <a-tag :color="record.is_active ? 'success' : 'default'">
                {{ record.is_active ? '启用' : '停用' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'rule'">
              <span>{{ record.retention_qty_rule || '—' }}</span>
              <small class="subline">
                {{ record.full_test_qty ? `${record.full_test_qty} ${record.full_test_qty_uom}` : '按实际填写' }}
              </small>
            </template>
            <template v-else-if="column.key === 'observation'">
              <span>{{ observationLabel(record.obs_rule) }}</span>
              <small class="subline">{{ record.storage_condition || '未维护储存条件' }}</small>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && !products.length" class="retention-empty">
          <BookOutlined />
          <strong>当前没有可查看的留样产品规则</strong>
          <span>产品规则由 LIMS 管理端维护。</span>
        </div>
      </section>
    </template>
    <template v-else-if="section === 'observations'">
      <section class="retention-observation-grid">
        <article class="glass-surface retention-panel">
          <div class="section-head">
            <div>
              <h2>观察任务</h2>
              <p>先看时间和结果，再决定录入或复核；本页不直接改变观察记录。</p>
            </div>
            <span class="panel-count">{{ observations.length }} 项</span>
          </div>
          <a-table
            :columns="observationColumns"
            :data-source="observations"
            :loading="loading"
            :pagination="false"
            row-key="name"
            size="middle"
            :scroll="{ x: 900 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'sample'">
                <strong>{{ record.product }}</strong>
                <small class="subline">{{ record.sampleName }} · {{ record.batch }}</small>
              </template>
              <template v-else-if="column.key === 'due'">
                <a-tag :color="dueColor(record.due)">{{ record.due }}</a-tag>
              </template>
              <template v-else-if="column.key === 'result'">
                <span
                  v-if="record.result"
                  :class="record.result === '异常' ? 'danger-text' : 'success-text'"
                >
                  {{ record.result }}
                </span>
                <span v-else class="muted-text">待观察</span>
              </template>
            </template>
          </a-table>
          <div v-if="!loading && !observations.length" class="retention-empty">
            <ExperimentOutlined />
            <strong>暂无观察计划</strong>
            <span>符合规则的留样进入观察计划后会出现在这里。</span>
          </div>
        </article>
        <aside class="glass-surface retention-panel completeness-panel">
          <div class="section-head">
            <div>
              <h2>年度完整性</h2>
              <p>原料药年度观察按产品查看选择进度。</p>
            </div>
          </div>
          <div v-if="completeness.length" class="completeness-list">
            <div
              v-for="item in completeness"
              :key="`${item.product}-${item.year}`"
              class="completeness-item"
            >
              <div>
                <strong>{{ item.product }}</strong>
                <small>{{ item.year }} · {{ item.rule }}</small>
              </div>
              <span class="completeness-number">
                {{ item.cap === null ? item.selected : `${item.selected}/${item.cap}` }}
              </span>
              <div class="completeness-bar">
                <i
                  :style="{ width: `${item.cap ? Math.min(100, item.selected / item.cap * 100) : 100}%` }"
                >

                </i>
              </div>
            </div>
          </div>
          <div v-else class="retention-empty compact">
            <CalendarOutlined />
            <span>暂无年度观察选择记录</span>
          </div>
        </aside>
      </section>
    </template>
    <template v-else>
      <section class="glass-surface retention-panel">
        <div class="section-head">
          <div>
            <h2>{{ section === 'usage' ? '使用申请' : '处理申请' }}</h2>
            <p>
              {{ section === 'usage' ? '查看留样使用申请和审批节点，取样执行仍由领域服务控制。' : '查看销毁、续留等处理申请及审批进度，处理动作受职责分离约束。' }}
            </p>
          </div>
          <span class="panel-count">{{ currentRows.length }} 条</span>
        </div>
        <div class="retention-filters">
          <a-input-search
            v-model:value="keyword"
            :placeholder="section === 'usage' ? '搜索申请单、产品或批号' : '搜索处理单、产品或批号'"
            enter-button="查询"
            allow-clear
            @search="applyLocalSearch"
          />
          <a-select
            v-model:value="status"
            allow-clear
            placeholder="全部状态"
            @change="applyLocalSearch"
          >
            <a-select-option v-for="item in currentStatuses" :key="item" :value="item">
              {{ item }}
            </a-select-option>
          </a-select>
          <a-button @click="clearFilters">清空</a-button>
        </div>
        <a-table
          :columns="section === 'usage' ? usageColumns : disposalColumns"
          :data-source="filteredRows"
          :loading="loading"
          :pagination="false"
          row-key="name"
          size="middle"
          :scroll="{ x: 1060 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'apply'">
              <strong>{{ record.name }}</strong>
              <small class="subline">{{ record.product }} · {{ record.batch }}</small>
            </template>
            <template v-else-if="column.key === 'qty'">
              <span>{{ record.qty }} {{ record.uom }}</span>
              <small class="subline">结存 {{ record.current_qty }} · 预占 {{ record.reserved_qty }}</small>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
            </template>
            <template v-else-if="column.key === 'deadline'">
              <span :class="dueClass(record.deadline)">{{ record.deadline || '—' }}</span>
            </template>
            <template v-else-if="column.key === 'action'">
              <button type="button" class="text-action" @click="openApplication(record)">
                查看详情
                <ArrowRightOutlined />
              </button>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && !filteredRows.length" class="retention-empty">
          <FileProtectOutlined />
          <strong>当前没有申请记录</strong>
          <span>申请单由既有留样流程产生，Portal 先提供清晰的只读追踪。</span>
        </div>
      </section>
    </template>
    <a-drawer
      v-model:open="drawerOpen"
      :title="drawerTitle"
      placement="right"
      width="min(560px, 94vw)"
      destroy-on-close
    >
      <template v-if="selectedSample">
        <div class="drawer-hero">
          <span class="page-kicker">留样批次</span>
          <h2>{{ selectedSample.product_name || selectedSample.sample_name }}</h2>
          <p>{{ selectedSample.name }} · {{ selectedSample.batch_no }}</p>
          <a-tag :color="statusColor(selectedSample.status)">{{ selectedSample.status }}</a-tag>
        </div>
        <a-descriptions bordered size="small" :column="1">
          <a-descriptions-item label="留样量">
            {{ selectedSample.retention_qty }}
            {{ selectedSample.qty_uom }}
          </a-descriptions-item>
          <a-descriptions-item label="当前可用">
            {{ selectedSample.available_qty }}
            {{ selectedSample.qty_uom }}
            （总量
            {{ selectedSample.current_qty }}
            ，预占
            {{ selectedSample.reserved_qty }}
            ）
          </a-descriptions-item>
          <a-descriptions-item label="留样期至">
            {{ selectedSample.retention_due_date || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="观察计划">
            {{ selectedSample.obs_rule || '不观察' }}
            ·
            {{ selectedSample.next_obs_due_date || '暂无下次计划' }}
          </a-descriptions-item>
          <a-descriptions-item label="储存条件">
            {{ selectedSample.storage_condition || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="储存位置">{{ selectedSample.storage_location || '—' }}</a-descriptions-item>
        </a-descriptions>
        <div class="readonly-drawer-note">
          <SafetyCertificateOutlined />
          该详情页只读。登记、库存调整、观察录入和处理申请继续由留样领域服务执行。
        </div>
      </template>
      <template v-else-if="selectedApplication">
        <div class="drawer-hero">
          <span class="page-kicker">{{ section === 'usage' ? '留样使用申请' : '留样处理申请' }}</span>
          <h2>{{ selectedApplication.product }}</h2>
          <p>{{ selectedApplication.name }} · {{ selectedApplication.batch }}</p>
          <a-tag :color="statusColor(selectedApplication.status)">{{ selectedApplication.status }}</a-tag>
        </div>
        <a-descriptions bordered size="small" :column="1">
          <a-descriptions-item label="关联留样">{{ selectedApplication.retention_name }}</a-descriptions-item>
          <a-descriptions-item label="申请数量">
            {{ selectedApplication.qty }}
            {{ selectedApplication.uom }}
          </a-descriptions-item>
          <a-descriptions-item label="申请人">
            {{ selectedApplication.applicant || '—' }}
            ·
            {{ selectedApplication.applicant_date || '—' }}
          </a-descriptions-item>
          <a-descriptions-item v-if="selectedUsage" label="触发场景">
            {{ selectedUsage.scenario }}
            ·
            {{ selectedApplication.reason || '未填写原因' }}
          </a-descriptions-item>
          <a-descriptions-item v-else-if="selectedDisposal" label="处理类型">
            {{ selectedDisposal.type }}
            ·
            {{ selectedApplication.reason || '未填写原因' }}
          </a-descriptions-item>
          <a-descriptions-item v-if="selectedDisposal" label="处理方式">
            {{ selectedDisposal.method || '—' }}
            ·
            {{ selectedDisposal.location || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="结存快照">
            当前
            {{ selectedApplication.current_qty }}
            {{ selectedApplication.uom }}
            · 预占
            {{ selectedApplication.reserved_qty }}
            {{ selectedApplication.uom }}
          </a-descriptions-item>
        </a-descriptions>
        <div class="readonly-drawer-note">
          <SafetyCertificateOutlined />
          Portal 只展示申请链路和审批状态，不代替 QC、QA、QM 的签署，也不绕过 SoD 校验。
        </div>
      </template>
    </a-drawer>
  </section>
</template>

<script setup lang="ts">
import { statusColor } from '@/views/limsStatus'
import { computed, onMounted, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRightOutlined,
  BookOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FileProtectOutlined,
  InboxOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import {
  getLimsRetention,
  type LimsRetentionEnvelope,
  type LimsRetentionDisposal,
  type LimsRetentionSample,
  type LimsRetentionUsage,
} from '@/services/limsRetention'
type RetentionSection = 'workbench' | 'samples' | 'products' | 'observations' | 'usage' | 'disposal'

interface RetentionAttentionItem {
  id: string
  title: string
  subtitle: string
  status: string
  tone: 'danger' | 'info' | 'warning'
  icon: Component
  path: string
}
const route = useRoute()
const router = useRouter()
const portal = usePortalStore()
const loading = ref(true)
const errorMessage = ref('')
const keyword = ref('')
const status = ref('')
const active = ref('')
const envelope = ref<LimsRetentionEnvelope>({
  samples: [],
  samples_total: 0,
  samples_next_cursor: null,
  products: [],
  products_total: 0,
  products_next_cursor: null,
  observations: [],
  observation_completeness: [],
  usage: { rows: [], total: 0 },
  disposal: { rows: [], total: 0 },
  summary: {
    sample_total: 0,
    in_stock: 0,
    observed: 0,
    near_due_30: 0,
    pending_usage: 0,
    pending_disposal: 0,
    due_observation: 0
  },
  section: 'workbench'
})
const drawerOpen = ref(false)
const selectedSample = ref<LimsRetentionSample | null>(null)
const selectedApplication = ref<LimsRetentionUsage | LimsRetentionDisposal | null>(null)

const selectedUsage = computed(() => selectedApplication.value && 'scenario' in selectedApplication.value ? selectedApplication.value : null)
const selectedDisposal = computed(() => selectedApplication.value && 'type' in selectedApplication.value ? selectedApplication.value : null)
const section = computed<RetentionSection>(() => ({
  'lims-retains': 'workbench',
  'lims-retains-samples': 'samples',
  'lims-retains-products': 'products',
  'lims-retains-observations': 'observations',
  'lims-retains-usage': 'usage',
  'lims-retains-disposal': 'disposal'
} as Record<string, RetentionSection>)[String(route.name)] || 'workbench')
const pageTitle = computed(() => ({
  workbench: '留样工作台',
  samples: '留样登记与台账',
  products: '留样产品规则',
  observations: '观察任务',
  usage: '使用申请',
  disposal: '处理申请'
}[section.value] || '留样管理'))
const pageDescription = computed(() => ({
  workbench: '把留样库存、观察计划和申请审批放在同一个检验工作台。',
  samples: '按批次查看留样量、结存、储存位置和留样期至。',
  products: '以产品规则为依据，快速确认留样量、储存条件和观察频次。',
  observations: '按计划日期关注应观察、待审核和已完成的留样观察。',
  usage: '追踪留样使用申请的库存确认、QC、QA、QM 审批节点。',
  disposal: '追踪销毁、续留等处理申请的审批和时限。'
}[section.value] || '留样管理'))
const tabs = [
  {
    path: '/hbos/lims/retains',
    label: '工作台',
    icon: DatabaseOutlined
  },
  {
    path: '/hbos/lims/retains/samples',
    label: '登记与台账',
    icon: InboxOutlined
  },
  {
    path: '/hbos/lims/retains/products',
    label: '产品规则',
    icon: BookOutlined
  },
  {
    path: '/hbos/lims/retains/observations',
    label: '观察任务',
    icon: ExperimentOutlined
  },
  {
    path: '/hbos/lims/retains/usage',
    label: '使用申请',
    icon: FileProtectOutlined
  },
  {
    path: '/hbos/lims/retains/disposal',
    label: '处理申请',
    icon: SafetyCertificateOutlined
  }
]
const flowSteps = [
  {
    number: '01',
    label: '登记与台账',
    caption: '批次入库、结存',
    path: '/hbos/lims/retains/samples'
  },
  {
    number: '02',
    label: '观察任务',
    caption: '计划、结果、审核',
    path: '/hbos/lims/retains/observations'
  },
  {
    number: '03',
    label: '使用申请',
    caption: '库存确认与审批',
    path: '/hbos/lims/retains/usage'
  },
  {
    number: '04',
    label: '处理申请',
    caption: '销毁、续留、监督',
    path: '/hbos/lims/retains/disposal'
  }
]
const samples = computed(() => envelope.value.samples)
const products = computed(() => envelope.value.products)
const observations = computed(() => envelope.value.observations)
const completeness = computed(() => envelope.value.observation_completeness)
const usage = computed(() => envelope.value.usage.rows)
const disposal = computed(() => envelope.value.disposal.rows)
const currentRows = computed(() => section.value === 'usage' ? usage.value : disposal.value)
const filteredRows = computed(() => {
  const needle = keyword.value.trim().toLowerCase()
  const effectiveStatus = currentStatuses.value.includes(status.value) ? status.value : ''
  return currentRows.value.filter((row) => {
    if (effectiveStatus && row.status !== effectiveStatus) return false
    const searchable = `${row.name} ${row.product} ${row.batch} ${row.retention_name}`.toLowerCase()
    return !needle || searchable.includes(needle)
  })
})
const currentStatuses = computed(() => [...new Set(currentRows.value.map(row => row.status).filter(Boolean))])
const sampleStatuses = [
  '在库',
  '部分使用',
  '已用尽',
  '待处理',
  '已销毁',
  '已转出'
]
const kpiCards = computed(() => [
  {
    label: '在库留样',
    value: envelope.value.summary.in_stock,
    caption: '含部分使用批次',
    tone: 'success'
  },
  {
    label: '待观察',
    value: envelope.value.summary.due_observation,
    caption: '应观察或待审核',
    tone: 'info'
  },
  {
    label: '使用申请',
    value: envelope.value.summary.pending_usage,
    caption: '尚未执行的申请',
    tone: 'warning'
  },
  {
    label: '处理申请',
    value: envelope.value.summary.pending_disposal,
    caption: '需要审批或处理',
    tone: 'critical'
  },
  {
    label: '30 日临期',
    value: envelope.value.summary.near_due_30,
    caption: '留样期至临近批次',
    tone: 'critical'
  }
])
const attentionItems = computed(() => {
  const rows: RetentionAttentionItem[] = []
  observations.value.filter(row => [
    '已逾期',
    '待审核',
    '应观察'
  ].includes(row.due)).slice(0, 3).forEach(row => rows.push({
    id: `obs-${row.name}`,
    title: row.due === '待审核' ? '观察记录待复核' : row.due === '已逾期' ? '观察任务已逾期' : '今日观察计划',
    subtitle: `${row.product} · ${row.batch}`,
    status: row.due,
    tone: row.due === '已逾期' ? 'danger' : 'info',
    icon: ExperimentOutlined,
    path: '/hbos/lims/retains/observations'
  }))
  usage.value.filter(row => ![
    '已执行',
    '已驳回',
    '已取消'
  ].includes(row.status)).slice(0, 2).forEach(row => rows.push({
    id: `use-${row.name}`,
    title: '使用申请待处理',
    subtitle: `${row.product} · ${row.qty} ${row.uom}`,
    status: row.status,
    tone: 'warning',
    icon: FileProtectOutlined,
    path: '/hbos/lims/retains/usage'
  }))
  disposal.value.filter(row => ![
    '已完成',
    '已驳回',
    '已取消'
  ].includes(row.status)).slice(0, 2).forEach(row => rows.push({
    id: `dsp-${row.name}`,
    title: '处理申请待处理',
    subtitle: `${row.product} · ${row.type}`,
    status: row.status,
    tone: 'danger',
    icon: SafetyCertificateOutlined,
    path: '/hbos/lims/retains/disposal'
  }))
  return rows.slice(0, 6)
})
const sampleColumns = [
  {
    title: '留样批次',
    key: 'sample',
    width: 280
  },
  {
    title: '结存可用',
    key: 'stock',
    width: 170
  },
  {
    title: '留样期至',
    key: 'due',
    dataIndex: 'retention_due_date',
    width: 140
  },
  {
    title: '状态',
    key: 'status',
    width: 110
  }
]
const sampleColumnsDetailed = [...sampleColumns, {
    title: '操作',
    key: 'action',
    width: 110
  }]
const productColumns = [
  {
    title: '产品',
    key: 'product',
    width: 260
  },
  {
    title: '状态',
    key: 'active',
    width: 90
  },
  {
    title: '留样量规则',
    key: 'rule',
    width: 190
  },
  {
    title: '观察与储存',
    key: 'observation',
    width: 280
  }
]
const observationColumns = [
  {
    title: '观察批次',
    key: 'sample',
    width: 280
  },
  {
    title: '计划日期',
    dataIndex: 'planDate',
    key: 'planDate',
    width: 130
  },
  {
    title: '状态',
    key: 'due',
    width: 110
  },
  {
    title: '结果',
    key: 'result',
    width: 100
  },
  {
    title: '留样状态',
    dataIndex: 'status',
    key: 'status',
    width: 110
  }
]
const usageColumns = [
  {
    title: '申请单',
    key: 'apply',
    width: 260
  },
  {
    title: '申请数量',
    key: 'qty',
    width: 180
  },
  {
    title: '触发场景',
    dataIndex: 'scenario',
    key: 'scenario',
    width: 150
  },
  {
    title: '状态',
    key: 'status',
    width: 130
  },
  {
    title: '操作',
    key: 'action',
    width: 110
  }
]
const disposalColumns = [
  {
    title: '处理申请',
    key: 'apply',
    width: 260
  },
  {
    title: '处理数量',
    key: 'qty',
    width: 180
  },
  {
    title: '处理类型',
    dataIndex: 'type',
    key: 'type',
    width: 170
  },
  {
    title: '时限',
    key: 'deadline',
    width: 130
  },
  {
    title: '状态',
    key: 'status',
    width: 130
  },
  {
    title: '操作',
    key: 'action',
    width: 110
  }
]
const drawerTitle = computed(() => selectedSample.value ? '留样批次详情' : section.value === 'usage' ? '使用申请详情' : '处理申请详情')
async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    if (!portal.user)
      await portal.bootstrap()
    envelope.value = await getLimsRetention({
      section: section.value,
      keyword: keyword.value.trim() || undefined,
      status: section.value === 'samples' ? status.value || undefined : undefined,
      active: section.value === 'products' ? active.value || undefined : undefined
    })
  } catch {
    errorMessage.value = '留样数据暂时无法加载，请检查当前账号的查看权限后重试。'
  } finally {
    loading.value = false
  }
}
function applyFilters() {
  void router.replace({
    query: {
      ...(keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
      ...(status.value ? { status: status.value } : {}),
      ...(active.value ? { active: active.value } : {})
    }
  })
}
function applyLocalSearch() {
}
function clearFilters() {
  keyword.value = ''
  status.value = ''
  active.value = ''
  void router.replace({ query: {} })
}
function readQuery() {
  keyword.value = typeof route.query.keyword === 'string' ? route.query.keyword : ''
  status.value = typeof route.query.status === 'string' ? route.query.status : ''
  active.value = typeof route.query.active === 'string' ? route.query.active : ''
}
function openSample(row: LimsRetentionSample) {
  selectedSample.value = row
  selectedApplication.value = null
  drawerOpen.value = true
}
function openApplication(row: LimsRetentionUsage | LimsRetentionDisposal) {
  selectedApplication.value = row
  selectedSample.value = null
  drawerOpen.value = true
}
function openAttention(item: RetentionAttentionItem) {
  void router.push(item.path)
}
function statusTone(value: string) {
  return [
    '已逾期',
    '待处理',
    '待QC批准',
    '待QA审核'
  ].includes(value) ? 'critical' : ['待审核', '应观察'].includes(value) ? 'warning' : 'success'
}
function dueColor(value: string) {
  return value === '已逾期' ? 'error' : value === '待审核' ? 'warning' : value === '已完成' ? 'success' : 'processing'
}
function dueClass(value?: string | null) {
  return value && value < new Date().toISOString().slice(0, 10) ? 'danger-text' : 'muted-text'
}
function observationLabel(value: string) {
  return value?.replace('（外售产品）', '') || '不观察'
}
onMounted(async () => {
  readQuery()
  await loadData()
})
watch(() => route.fullPath, async () => {
  readQuery()
  await loadData()
})
</script>

<style scoped>
.retention-page {
  display: grid;
  gap: 16px;
  padding-bottom: 32px;
}
.retention-heading {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-start;
}
.retention-heading h1 {
  margin: 6px 0 5px;
  font-size: clamp(26px,3vw,36px);
  letter-spacing: -.03em;
}
.retention-heading p {
  margin: 0;
  color: var(--hbos-text-muted);
  font-size: 13px;
}
.retention-heading-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.readonly-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.retention-tabs {
  display: flex;
  gap: 4px;
  overflow: auto;
  padding: 4px;
  border: 1px solid var(--hbos-border-default);
  border-radius: 14px;
  background: rgba(255,255,255,.42);
}
.retention-tabs a {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 10px;
  white-space: nowrap;
  color: var(--hbos-text-muted);
  font-size: 13px;
  text-decoration: none;
}
.retention-tabs a:hover,.retention-tabs a.active {
  color: var(--lims-ink);
  background: rgba(8,127,114,.1);
}
.retention-alert {
  margin: 0;
}
.retention-kpis {
  display: grid;
  grid-template-columns: repeat(5,minmax(0,1fr));
  gap: 12px;
}
.retention-kpi {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 16px 18px;
  border-radius: 16px;
  border-top: 3px solid var(--tone,#087f72);
}
.retention-kpi span,.retention-kpi small {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.retention-kpi strong {
  color: var(--hbos-text-primary);
  font-size: 28px;
  line-height: 1.1;
}
.tone-success {
  --tone: #0f9f72;
}
.tone-info {
  --tone: #1386c8;
}
.tone-warning {
  --tone: #d89124;
}
.tone-critical {
  --tone: #d65f5f;
}
.retention-work-grid {
  display: grid;
  grid-template-columns: minmax(0,1.2fr) minmax(320px,.8fr);
  gap: 16px;
}
.retention-panel {
  padding: 20px;
  border-radius: 18px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 14px;
  margin-bottom: 14px;
}
.section-head h2 {
  margin: 0;
  font-size: 18px;
}
.section-head p {
  margin: 5px 0 0;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.panel-count {
  color: var(--hbos-text-muted);
  font-size: 12px;
  white-space: nowrap;
}
.attention-list {
  display: grid;
  gap: 8px;
}
.attention-item {
  display: grid;
  grid-template-columns: 34px minmax(0,1fr) auto 18px;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 62px;
  padding: 9px 10px;
  border: 1px solid var(--hbos-border-default);
  border-radius: 12px;
  color: inherit;
  text-align: left;
  background: rgba(255,255,255,.5);
  cursor: pointer;
}
.attention-item:hover {
  border-color: rgba(8,127,114,.38);
  background: #fff;
}
.attention-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
}
.attention-info {
  color: #147da8;
  background: #e9f7fc;
}
.attention-warning {
  color: #a96714;
  background: #fff4df;
}
.attention-danger {
  color: #b74444;
  background: #fff0ef;
}
.attention-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}
.attention-copy strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.attention-copy small,.subline {
  display: block;
  color: var(--hbos-text-muted);
  font-size: 11px;
}
.attention-status {
  font-size: 11px;
  white-space: nowrap;
}
.status-critical {
  color: #bb4e4e;
}
.status-warning {
  color: #a96714;
}
.status-success {
  color: #168463;
}
.flow-steps {
  display: grid;
  gap: 2px;
}
.flow-step {
  display: grid;
  grid-template-columns: 34px minmax(0,1fr) 18px;
  gap: 10px;
  align-items: center;
  min-height: 58px;
  padding: 8px 4px;
  color: inherit;
  text-decoration: none;
  border-bottom: 1px solid rgba(120,145,170,.16);
}
.flow-step:last-child {
  border-bottom: 0;
}
.flow-step:hover strong {
  color: var(--lims-ink);
}
.flow-number {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: var(--lims-ink);
  background: rgba(8,127,114,.1);
  font: 700 11px ui-monospace,monospace;
}
.flow-step span:nth-child(2) {
  display: grid;
  gap: 3px;
}
.flow-step small {
  color: var(--hbos-text-muted);
  font-size: 11px;
}
.lab-tip,.readonly-drawer-note {
  display: flex;
  gap: 10px;
  padding: 12px;
  margin-top: 14px;
  border-radius: 12px;
  color: var(--hbos-text-secondary);
  background: rgba(8,127,114,.07);
  font-size: 12px;
  line-height: 1.6;
}
.lab-tip > .anticon,.readonly-drawer-note > .anticon {
  flex: none;
  color: var(--lims-green);
  font-size: 18px;
  margin-top: 2px;
}
.retention-filters {
  display: grid;
  grid-template-columns: minmax(240px,1fr) 160px auto;
  gap: 10px;
  margin-bottom: 16px;
}
.retention-empty {
  display: grid;
  justify-items: center;
  gap: 7px;
  min-height: 160px;
  padding: 32px 16px;
  color: var(--hbos-text-muted);
  text-align: center;
}
.retention-empty > .anticon {
  color: var(--lims-green);
  font-size: 30px;
}
.retention-empty strong {
  color: var(--hbos-text-primary);
  font-size: 15px;
}
.retention-empty span {
  font-size: 12px;
}
.retention-empty.compact {
  min-height: 120px;
}
.stock-value {
  color: var(--lims-ink);
  font-weight: 700;
}
.text-action,.text-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 0;
  color: var(--lims-ink);
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
}
.text-action:hover,.text-link:hover {
  color: var(--hbos-text-primary);
}
.danger-text {
  color: #bd4e4e;
  font-weight: 650;
}
.success-text {
  color: #168463;
  font-weight: 650;
}
.muted-text {
  color: var(--hbos-text-muted);
}
.retention-observation-grid {
  display: grid;
  grid-template-columns: minmax(0,1fr) 320px;
  gap: 16px;
}
.completeness-list {
  display: grid;
  gap: 14px;
}
.completeness-item {
  display: grid;
  grid-template-columns: minmax(0,1fr) auto;
  gap: 6px 10px;
  align-items: center;
}
.completeness-item > div:first-child {
  display: grid;
  gap: 4px;
}
.completeness-item small {
  color: var(--hbos-text-muted);
  font-size: 11px;
}
.completeness-number {
  color: var(--lims-ink);
  font: 700 16px ui-monospace,monospace;
}
.completeness-bar {
  grid-column: 1 / -1;
  height: 7px;
  overflow: hidden;
  border-radius: 99px;
  background: rgba(8,127,114,.1);
}
.completeness-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg,#3dc4a2,#087f72);
}
.drawer-hero {
  padding-bottom: 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--hbos-border-default);
}
.drawer-hero h2 {
  margin: 7px 0 4px;
  font-size: 22px;
}
.drawer-hero p {
  margin: 0 0 10px;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.page-kicker {
  color: var(--lims-ink);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .08em;
  text-transform: uppercase;
}
@media (max-width:980px) {
  .retention-kpis {
    grid-template-columns: repeat(3,minmax(0,1fr));
  }
  .retention-work-grid,.retention-observation-grid {
    grid-template-columns: 1fr;
  }
  .completeness-panel {
    order: -1;
  }
}
@media (max-width:700px) {
  .retention-heading {
    flex-direction: column;
  }
  .retention-heading-actions {
    width: 100%;
    justify-content: space-between;
  }
  .retention-kpis {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }
  .retention-kpi strong {
    font-size: 24px;
  }
  .retention-panel {
    padding: 14px;
  }
  .retention-filters {
    grid-template-columns: 1fr;
  }
  .retention-tabs {
    margin-inline: -4px;
  }
  .retention-tabs a {
    padding: 0 11px;
  }
  .attention-item {
    grid-template-columns: 34px minmax(0,1fr) 18px;
  }
  .attention-status {
    display: none;
  }
}
</style>
