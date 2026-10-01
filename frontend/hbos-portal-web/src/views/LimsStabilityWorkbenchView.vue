<template>
  <section class="product-page lims-stability-page">
    <header class="stability-heading">
      <div>
        <span class="page-kicker">LIMS · 稳定性考察</span>
        <h1>{{ pageTitle }}</h1>
        <p>{{ pageDescription }}</p>
      </div>
      <div class="stability-heading-actions">
        <span class="readonly-note">
          <SafetyCertificateOutlined />
          {{ envelope.scope || '数据由稳定性业务服务提供' }}
        </span>
        <a-button :loading="loading" @click="loadData">
          <ReloadOutlined />
          刷新
        </a-button>
      </div>
    </header>
    <nav class="stability-tabs" aria-label="稳定性管理分区">
      <RouterLink v-for="tab in tabs" :key="tab.path" :to="tab.path" exact-active-class="active">
        <component :is="tab.icon" />
        {{ tab.label }}
      </RouterLink>
    </nav>
    <a-alert
      v-if="errorMessage"
      class="stability-alert"
      type="error"
      show-icon
      closable
      :message="errorMessage"
      @close="errorMessage = ''"
    />
    <template v-if="section === 'workbench'">
      <section class="stability-kpis" aria-label="稳定性概览">
        <article
          v-for="card in kpiCards"
          :key="card.label"
          class="glass-surface stability-kpi"
          :class="`tone-${card.tone}`"
        >
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.caption }}</small>
        </article>
      </section>
      <section class="stability-work-grid">
        <article class="glass-surface stability-panel attention-panel">
          <div class="section-head">
            <div>
              <h2>今天先处理</h2>
              <p>按取样、检测、逾期的优先顺序安排检验工作。</p>
            </div>
            <span class="panel-count">{{ attentionRows.length }} 项</span>
          </div>
          <div v-if="attentionRows.length" class="stability-attention-list">
            <button
              v-for="row in attentionRows"
              :key="row.name"
              type="button"
              class="stability-attention-item"
              @click="openSchedule(row)"
            >
              <span class="attention-icon" :class="`attention-${rowTone(row)}`">
                <WarningOutlined v-if="rowTone(row) === 'danger'" />
                <ClockCircleOutlined v-else />
              </span>
              <span class="attention-copy">
                <strong>{{ row.product_name || '未命名产品' }} · {{ row.time_point_label || '时间点' }}</strong>
                <small>
                  {{ row.batch_no || row.stability_sample }}
                  ·
                  {{ row.condition_type }}
                  ·
                  {{ row.room || '稳定性室' }}
                </small>
              </span>
              <a-tag :color="statusColor(row.exec_state || row.status)">
                {{ row.exec_state || row.status }}
              </a-tag>
              <ArrowRightOutlined />
            </button>
          </div>
          <div v-else class="stability-empty">
            <CheckCircleOutlined />
            <strong>当前没有需要优先处理的时间点</strong>
            <span>计划取样与检测截止日会在这里提醒。</span>
          </div>
        </article>
        <article class="glass-surface stability-panel">
          <div class="section-head">
            <div>
              <h2>执行进度</h2>
              <p>稳定性时间点按当前状态分布。</p>
            </div>
            <RouterLink class="text-link" to="/hbos/lims/stability/schedule">
              查看计划
              <ArrowRightOutlined />
            </RouterLink>
          </div>
          <div class="progress-pipeline">
            <div v-for="item in progressItems" :key="item.label" class="progress-item">
              <span class="progress-dot" :class="item.tone"></span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.label }}</small>
            </div>
          </div>
          <div class="stability-lab-tip">
            <ExperimentOutlined />
            <span>
              <strong>检验员提示</strong>
              <br />
              先核对稳定性室、储存条件和批号，再进入对应时间点；延期只显示在日期链中，不改变原始计划。
            </span>
          </div>
        </article>
      </section>
      <section class="stability-three-grid">
        <article class="glass-surface stability-panel">
          <div class="section-head">
            <div>
              <h2>稳定性室</h2>
              <p>当前账号可查看的环境资源</p>
            </div>
            <EnvironmentOutlined class="section-icon" />
          </div>
          <div class="room-card">
            <strong>稳定性室 {{ envelope.dashboard.master.room ? 'A / B' : '—' }}</strong>
            <span>启用房间 {{ envelope.dashboard.master.room || 0 }} 个</span>
            <small>温湿度记录与设备状态由稳定性业务服务维护</small>
          </div>
        </article>
        <article class="glass-surface stability-panel">
          <div class="section-head">
            <div>
              <h2>检验项目</h2>
              <p>趋势与结果使用的稳定性项目</p>
            </div>
            <MedicineBoxOutlined class="section-icon" />
          </div>
          <div class="room-card">
            <strong>{{ envelope.dashboard.master.test_item || 0 }} 个启用项目</strong>
            <span>产品 {{ envelope.dashboard.product_count || 0 }} 个</span>
            <small>项目映射、方法和规格版本受控</small>
          </div>
        </article>
        <article class="glass-surface stability-panel">
          <div class="section-head">
            <div>
              <h2>趋势观察</h2>
              <p>已批准结果的变化线索</p>
            </div>
            <LineChartOutlined class="section-icon" />
          </div>
          <RouterLink class="trend-entry" to="/hbos/lims/stability/trend">
            <strong>打开趋势分析</strong>
            <span>
              按产品、项目和条件查看结果序列
              <ArrowRightOutlined />
            </span>
          </RouterLink>
        </article>
      </section>
    </template>
    <template v-else-if="section === 'schedule'">
      <section class="glass-surface stability-panel">
        <div class="section-head">
          <div>
            <h2>取样与检测计划</h2>
            <p>计划日期、实际日期、有效截止和逾期状态集中查看。</p>
          </div>
          <span class="panel-count">{{ scheduleRows.length }} 个时间点</span>
        </div>
        <div class="stability-filters">
          <a-input-search
            v-model:value="keyword"
            placeholder="搜索产品、样品、批号或时间点"
            enter-button="查询"
            allow-clear
            @search="loadData"
          />
          <a-select v-model:value="status" allow-clear placeholder="全部状态" @change="loadData">
            <a-select-option value="待取样">待取样</a-select-option>
            <a-select-option value="待检测">待检测</a-select-option>
            <a-select-option value="检测中">检测中</a-select-option>
            <a-select-option value="已完成">已完成</a-select-option>
            <a-select-option value="检测逾期">检测逾期</a-select-option>
          </a-select>
          <a-input v-model:value="month" placeholder="计划月份，如 2026-10" @pressEnter="loadData" />
          <a-button @click="clearFilters">清空</a-button>
        </div>
        <a-table
          :columns="scheduleColumns"
          :data-source="scheduleRows"
          :loading="loading"
          row-key="name"
          size="middle"
          :pagination="false"
          :locale="tableLocale"
          :scroll="{ x: 1220 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'point'">
              <strong>{{ record.product_name || '—' }}</strong>
              <small class="subline">
                {{ record.batch_no || record.stability_sample }}
                ·
                {{ record.condition_type }}
                ·
                {{ record.time_point_label }}
              </small>
            </template>
            <template v-else-if="column.key === 'dates'">
              <span>{{ record.plan_sample_date || '—' }}</span>
              <small class="subline">检测 {{ record.plan_test_date || '—' }}</small>
            </template>
            <template v-else-if="column.key === 'state'">
              <a-tag :color="statusColor(record.exec_state || record.status)">
                {{ record.exec_state || record.status }}
              </a-tag>
              <small v-if="record.delay_state" class="subline">{{ record.delay_state }}</small>
            </template>
            <template v-else-if="column.key === 'action'">
              <button type="button" class="text-action" @click="openSchedule(record)">
                查看日期链
                <ArrowRightOutlined />
              </button>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && !scheduleRows.length" class="stability-empty">
          <InboxOutlined />
          <strong>当前筛选下暂无时间点</strong>
          <span>调整月份、状态或关键词后重试。</span>
        </div>
      </section>
    </template>
    <template v-else-if="section === 'samples'">
      <section class="glass-surface stability-panel">
        <div class="section-head">
          <div>
            <h2>样品入箱与台账</h2>
            <p>批次、储存条件、稳定性室和当前结存只读查看。</p>
          </div>
          <span class="panel-count">{{ envelope.samples.total }} 个样品</span>
        </div>
        <div class="stability-filters">
          <a-input-search
            v-model:value="keyword"
            placeholder="搜索样品、产品或批号"
            enter-button="查询"
            allow-clear
            @search="loadData"
          />
          <a-select v-model:value="status" allow-clear placeholder="全部状态" @change="loadData">
            <a-select-option value="在箱">在箱</a-select-option>
            <a-select-option value="待评价">待评价</a-select-option>
            <a-select-option value="已完成">已完成</a-select-option>
          </a-select>
          <a-button @click="clearFilters">清空</a-button>
        </div>
        <a-table
          :columns="sampleColumns"
          :data-source="envelope.samples.rows"
          :loading="loading"
          row-key="name"
          size="middle"
          :pagination="false"
          :locale="tableLocale"
          :scroll="{ x: 1120 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'sample'">
              <strong>{{ record.product_name || '—' }}</strong>
              <small class="subline">
                {{ record.sample_name || record.name }}
                ·
                {{ record.batch_no || '—' }}
              </small>
            </template>
            <template v-else-if="column.key === 'storage'">
              <span>{{ record.room || '—' }}</span>
              <small class="subline">{{ record.storage_location || record.storage_cond || '—' }}</small>
            </template>
            <template v-else-if="column.key === 'qty'">
              <strong>{{ record.current_qty ?? '—' }} {{ record.qty_uom || '' }}</strong>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <button type="button" class="text-action" @click="openSample(record)">
                查看样品
                <ArrowRightOutlined />
              </button>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && !envelope.samples.rows.length" class="stability-empty">
          <InboxOutlined />
          <strong>当前筛选下暂无样品</strong>
          <span>样品入箱后会在这里形成稳定性台账。</span>
        </div>
      </section>
    </template>
    <template v-else-if="section === 'results'">
      <section class="glass-surface stability-panel">
        <div class="section-head">
          <div>
            <h2>稳定性结果</h2>
            <p>按时间点和检验项目查看当前版本结果，异常变化单独提示。</p>
          </div>
          <span class="panel-count">{{ envelope.results.total }} 条结果</span>
        </div>
        <div class="stability-filters">
          <a-input-search
            v-model:value="keyword"
            placeholder="搜索结果编号、项目或样品"
            enter-button="查询"
            allow-clear
            @search="loadData"
          />
          <a-select v-model:value="status" allow-clear placeholder="全部状态" @change="loadData">
            <a-select-option value="待复核">待复核</a-select-option>
            <a-select-option value="已批准">已批准</a-select-option>
            <a-select-option value="已退回">已退回</a-select-option>
          </a-select>
          <a-button @click="clearFilters">清空</a-button>
        </div>
        <a-table
          :columns="resultColumns"
          :data-source="envelope.results.rows"
          :loading="loading"
          row-key="name"
          size="middle"
          :pagination="false"
          :locale="tableLocale"
          :scroll="{ x: 1160 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'item'">
              <strong>{{ record.item_snapshot || record.stability_test_item || '—' }}</strong>
              <small class="subline">
                {{ record.stability_sample || '—' }}
                ·
                {{ record.timepoint || '—' }}
              </small>
            </template>
            <template v-else-if="column.key === 'value'">
              <strong>{{ record.result_value ?? '—' }} {{ record.unit || '' }}</strong>
              <small class="subline">限度 {{ record.spec_limit || '—' }}</small>
            </template>
            <template v-else-if="column.key === 'state'">
              <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
              <a-tag v-if="record.is_significant_change" color="orange">显著变化</a-tag>
              <a-tag v-if="record.oos_flag || record.oot_flag" color="red">需关注</a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <button type="button" class="text-action" @click="openResult(record)">
                查看结果
                <ArrowRightOutlined />
              </button>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && !envelope.results.rows.length" class="stability-empty">
          <InboxOutlined />
          <strong>当前筛选下暂无稳定性结果</strong>
          <span>结果批准后会进入趋势与结果台账。</span>
        </div>
      </section>
    </template>
    <template v-else-if="section === 'trend'">
      <section class="glass-surface stability-panel">
        <div class="section-head">
          <div>
            <h2>稳定性趋势分析</h2>
            <p>仅展示当前版本、已批准结果；规格限来自结果冻结快照。</p>
          </div>
          <span class="lims-readonly-badge">只读分析</span>
        </div>
        <div class="trend-filters">
          <a-select
            v-model:value="trendProduct"
            show-search
            placeholder="选择稳定性产品"
            @change="refreshTrend"
          >
            <a-select-option
              v-for="item in envelope.products.rows"
              :key="item.name"
              :value="item.name"
            >
              {{ item.product_name || item.product_code || item.name }}
            </a-select-option>
          </a-select>
          <a-select
            v-model:value="trendItem"
            show-search
            placeholder="选择检验项目"
            @change="refreshTrend"
          >
            <a-select-option
              v-for="item in envelope.test_items.rows"
              :key="item.name"
              :value="item.name"
            >
              {{ item.item_name || item.item_code || item.name }}
            </a-select-option>
          </a-select>
          <a-select
            v-model:value="trendCondition"
            allow-clear
            placeholder="全部储存条件"
            @change="refreshTrend"
          >
            <a-select-option value="长期">长期</a-select-option>
            <a-select-option value="加速">加速</a-select-option>
            <a-select-option value="中间">中间</a-select-option>
          </a-select>
        </div>
        <div v-if="trendLoading" class="stability-empty">
          <a-spin />
          <span>正在读取趋势数据…</span>
        </div>
        <template v-else-if="envelope.trend && envelope.trend.series.length">
          <div class="trend-summary">
            <span>产品：{{ envelope.trend.product || selectedProductName }}</span>
            <span>项目：{{ envelope.trend.stability_test_item || selectedItemName }}</span>
            <span>规格限：{{ envelope.trend.spec?.text || '未设置' }}</span>
            <span v-if="envelope.trend.trend_line">
              R²
              {{ Number(envelope.trend.trend_line.r2 || 0).toFixed(2) }}
            </span>
          </div>
          <div class="trend-chart">
            <svg viewBox="0 0 760 300" role="img" aria-label="稳定性结果趋势图">
              <line x1="52" y1="24" x2="52" y2="248" />
              <line x1="52" y1="248" x2="730" y2="248" />
              <line
                v-if="trendUpperY !== null"
                x1="52"
                :y1="trendUpperY"
                x2="730"
                :y2="trendUpperY"
                class="spec-line"
              />
              <polyline :points="trendPolyline" class="trend-line" fill="none" />
              <circle
                v-for="point in chartPoints"
                :key="point.name"
                :cx="point.cx"
                :cy="point.cy"
                r="6"
                :class="{ significant: point.significant }"
              />
              <text
                v-for="point in chartPoints"
                :key="`${point.name}-label`"
                :x="point.cx"
                y="274"
                text-anchor="middle"
              >
                {{ point.label }}
              </text>
            </svg>
          </div>
          <div class="trend-note">
            <LineChartOutlined />
            <span>{{ envelope.trend.note || '趋势仅供检验员观察，结论仍以质量部门审核为准。' }}</span>
          </div>
        </template>
        <div v-else class="stability-empty">
          <LineChartOutlined />
          <strong>请选择产品和检验项目</strong>
          <span>选择后将加载已批准结果的时间点序列。</span>
        </div>
      </section>
    </template>
    <a-drawer
      v-model:open="drawerOpen"
      :title="drawerTitle"
      placement="right"
      width="min(720px, 94vw)"
      destroy-on-close
    >
      <template v-if="selectedSchedule">
        <div class="drawer-hero">
          <span class="page-kicker">稳定性时间点</span>
          <h2>
            {{ selectedSchedule.product_name || '未命名产品' }}
            ·
            {{ selectedSchedule.time_point_label || '时间点' }}
          </h2>
          <p>
            {{ selectedSchedule.name }}
            ·
            {{ selectedSchedule.batch_no || selectedSchedule.stability_sample }}
          </p>
          <a-tag :color="statusColor(selectedSchedule.exec_state || selectedSchedule.status)">
            {{ selectedSchedule.exec_state || selectedSchedule.status }}
          </a-tag>
        </div>
        <a-descriptions bordered size="small" :column="2">
          <a-descriptions-item label="储存条件">
            {{ selectedSchedule.storage_cond || selectedSchedule.condition_type || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="稳定性室">{{ selectedSchedule.room || '—' }}</a-descriptions-item>
          <a-descriptions-item label="计划取样日">
            {{ selectedSchedule.plan_sample_date || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="实际取样日">
            {{ selectedSchedule.actual_sample_date || '未登记' }}
          </a-descriptions-item>
          <a-descriptions-item label="计划检测日">
            {{ selectedSchedule.plan_test_date || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="实际检测日">
            {{ selectedSchedule.actual_test_date || '未登记' }}
          </a-descriptions-item>
          <a-descriptions-item label="取样有效截止">
            {{ selectedSchedule.effective_sample_due || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="检测有效截止">
            {{ selectedSchedule.effective_test_due || '—' }}
          </a-descriptions-item>
        </a-descriptions>
        <div class="readonly-drawer-note">
          <SafetyCertificateOutlined />
          这是只读日期链。取样、检测、延期审批等动作仍由稳定性领域服务按角色执行。
        </div>
      </template>
      <template v-else-if="selectedSample">
        <div class="drawer-hero">
          <span class="page-kicker">稳定性样品</span>
          <h2>{{ selectedSample.product_name || '未命名产品' }}</h2>
          <p>{{ selectedSample.name }} · {{ selectedSample.batch_no || '—' }}</p>
        </div>
        <a-descriptions bordered size="small" :column="2">
          <a-descriptions-item label="样品名称">{{ selectedSample.sample_name || '—' }}</a-descriptions-item>
          <a-descriptions-item label="状态">{{ selectedSample.status }}</a-descriptions-item>
          <a-descriptions-item label="储存条件">
            {{ selectedSample.storage_cond || selectedSample.condition_snapshot || '—' }}
          </a-descriptions-item>
          <a-descriptions-item label="稳定性室">{{ selectedSample.room || '—' }}</a-descriptions-item>
          <a-descriptions-item label="存放位置">{{ selectedSample.storage_location || '—' }}</a-descriptions-item>
          <a-descriptions-item label="当前结存">
            {{ selectedSample.current_qty ?? '—' }}
            {{ selectedSample.qty_uom || '' }}
          </a-descriptions-item>
          <a-descriptions-item label="入箱日期">{{ selectedSample.in_date || '—' }}</a-descriptions-item>
          <a-descriptions-item label="起始日期">{{ selectedSample.start_date || '—' }}</a-descriptions-item>
        </a-descriptions>
      </template>
      <template v-else-if="selectedResult">
        <div class="drawer-hero">
          <span class="page-kicker">稳定性结果</span>
          <h2>{{ selectedResult.item_snapshot || selectedResult.stability_test_item || '检验项目' }}</h2>
          <p>
            {{ selectedResult.name }}
            ·
            {{ selectedResult.stability_sample }}
            ·
            {{ selectedResult.timepoint }}
          </p>
          <a-tag :color="statusColor(selectedResult.status)">{{ selectedResult.status }}</a-tag>
        </div>
        <a-descriptions bordered size="small" :column="2">
          <a-descriptions-item label="结果值">
            {{ selectedResult.result_value ?? '—' }}
            {{ selectedResult.unit || '' }}
          </a-descriptions-item>
          <a-descriptions-item label="规格限">{{ selectedResult.spec_limit || '—' }}</a-descriptions-item>
          <a-descriptions-item label="检验日期">{{ selectedResult.test_date || '—' }}</a-descriptions-item>
          <a-descriptions-item label="检验员">{{ selectedResult.analyst || '—' }}</a-descriptions-item>
          <a-descriptions-item label="规格版本">{{ selectedResult.spec_version || '—' }}</a-descriptions-item>
          <a-descriptions-item label="显著变化">
            {{ selectedResult.is_significant_change ? selectedResult.significant_change_basis || '是' : '否' }}
          </a-descriptions-item>
        </a-descriptions>
        <div class="readonly-drawer-note">
          <SafetyCertificateOutlined />
          结果详情只读展示，修订、复核和批准仍由领域服务控制。
        </div>
      </template>
    </a-drawer>
  </section>
</template>

<script setup lang="ts">
import { statusColor } from '@/views/limsStatus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  EnvironmentOutlined,
  ExperimentOutlined,
  InboxOutlined,
  LineChartOutlined,
  MedicineBoxOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import {
  getLimsStability,
  type LimsStabilityEnvelope,
  type StabilityResultRow,
  type StabilitySampleRow,
  type StabilityScheduleRow,
} from '@/services/limsStability'
const route = useRoute()
const portal = usePortalStore()
const loading = ref(true)
const trendLoading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const status = ref('')
const month = ref('')
const drawerOpen = ref(false)
const selectedSchedule = ref<StabilityScheduleRow | null>(null)
const selectedSample = ref<StabilitySampleRow | null>(null)
const selectedResult = ref<StabilityResultRow | null>(null)
const trendProduct = ref('')
const trendItem = ref('')
const trendCondition = ref('')
const emptyDashboard = {
  notice_pending: 0,
  notice_approved: 0,
  protocol_pending: 0,
  protocol_approved: 0,
  product_count: 0,
  sample_count: 0,
  timepoint_count: 0,
  result_count: 0,
  timepoint_by_status: {},
  master: {
    condition: 0,
    room: 0,
    test_item: 0
  },
  scope: '稳定性数据'
}
const emptyEnvelope: LimsStabilityEnvelope = {
  section: 'workbench',
  dashboard: emptyDashboard,
  schedule: { rows: [], summary: {} },
  samples: { rows: [], total: 0 },
  results: { rows: [], total: 0 },
  products: { rows: [], total: 0 },
  test_items: { rows: [], total: 0 },
  trend: null,
  scope: '稳定性数据'
}
const envelope = ref<LimsStabilityEnvelope>(emptyEnvelope)
const tableLocale = { emptyText: '暂无数据' }
const section = computed(() => {
  const name = String(route.name || 'lims-stability')
  return name.endsWith('-schedule') ? 'schedule' : name.endsWith('-samples') ? 'samples' : name.endsWith('-results') ? 'results' : name.endsWith('-trend') ? 'trend' : 'workbench'
})
const tabs = [
  {
    label: '稳定性工作台',
    path: '/hbos/lims/stability',
    icon: ExperimentOutlined
  },
  {
    label: '取样与检测计划',
    path: '/hbos/lims/stability/schedule',
    icon: ClockCircleOutlined
  },
  {
    label: '样品入箱台账',
    path: '/hbos/lims/stability/samples',
    icon: DatabaseOutlined
  },
  {
    label: '稳定性结果',
    path: '/hbos/lims/stability/results',
    icon: SafetyCertificateOutlined
  },
  {
    label: '趋势分析',
    path: '/hbos/lims/stability/trend',
    icon: LineChartOutlined
  }
]
const pageTitle = computed(() => tabs.find(tab => tab.path.endsWith(section.value === 'workbench' ? '/stability' : `/${section.value}`))?.label || '稳定性工作台')
const pageDescription = computed(() => ({
  workbench: '稳定性考察的取样、检测、环境和趋势工作台',
  schedule: '按时间点管理计划日、实际日和有效截止日',
  samples: '查看样品入箱、储存条件和当前结存',
  results: '查看稳定性检验结果与显著变化提示',
  trend: '按产品、项目和储存条件观察结果变化',
})[section.value])
const scheduleRows = computed(() => envelope.value.schedule.rows)
const attentionRows = computed(() => scheduleRows.value.filter(row => row.status !== '已完成').slice(0, 5))
const kpiCards = computed(() => [
  {
    label: '待处理时间点',
    value: Number(envelope.value.dashboard.timepoint_by_status?.wait_sample || 0) + Number(envelope.value.dashboard.timepoint_by_status?.wait_test || 0),
    caption: '待取样 + 待检测',
    tone: 'warning'
  },
  {
    label: '正在检测',
    value: envelope.value.dashboard.timepoint_by_status?.testing || 0,
    caption: '已取样，结果未完成',
    tone: 'info'
  },
  {
    label: '检测逾期',
    value: envelope.value.schedule.summary?.test_overdue || 0,
    caption: '需要优先跟进',
    tone: 'danger'
  },
  {
    label: '稳定性样品',
    value: envelope.value.dashboard.sample_count || 0,
    caption: '当前可追溯样品',
    tone: 'success'
  }
])
const progressItems = computed(() => [
  {
    label: '待取样',
    value: envelope.value.dashboard.timepoint_by_status?.wait_sample || 0,
    tone: 'blue'
  },
  {
    label: '待检测',
    value: envelope.value.dashboard.timepoint_by_status?.wait_test || 0,
    tone: 'amber'
  },
  {
    label: '检测中',
    value: envelope.value.dashboard.timepoint_by_status?.testing || 0,
    tone: 'green'
  },
  {
    label: '已完成',
    value: envelope.value.dashboard.timepoint_by_status?.done || 0,
    tone: 'gray'
  }
])
const scheduleColumns = [
  {
    title: '产品 / 时间点',
    key: 'point',
    width: 260
  },
  {
    title: '计划日期',
    key: 'dates',
    width: 180
  },
  {
    title: '储存条件',
    dataIndex: 'storage_cond',
    key: 'storage_cond',
    width: 150
  },
  {
    title: '稳定性室',
    dataIndex: 'room',
    key: 'room',
    width: 120
  },
  {
    title: '执行状态',
    key: 'state',
    width: 150
  },
  {
    title: '查看',
    key: 'action',
    width: 120
  }
]
const sampleColumns = [
  {
    title: '产品 / 批号',
    key: 'sample',
    width: 270
  },
  {
    title: '储存位置',
    key: 'storage',
    width: 190
  },
  {
    title: '当前结存',
    key: 'qty',
    width: 130
  },
  {
    title: '入箱日期',
    dataIndex: 'in_date',
    key: 'in_date',
    width: 130
  },
  {
    title: '状态',
    key: 'status',
    width: 120
  },
  {
    title: '查看',
    key: 'action',
    width: 120
  }
]
const resultColumns = [
  {
    title: '检验项目 / 时间点',
    key: 'item',
    width: 260
  },
  {
    title: '结果值',
    key: 'value',
    width: 170
  },
  {
    title: '检验日期',
    dataIndex: 'test_date',
    key: 'test_date',
    width: 130
  },
  {
    title: '状态',
    key: 'state',
    width: 190
  },
  {
    title: '查看',
    key: 'action',
    width: 120
  }
]
const drawerTitle = computed(() => selectedSchedule.value ? '时间点日期链' : selectedSample.value ? '稳定性样品详情' : '稳定性结果详情')
const selectedProductName = computed(() => envelope.value.products.rows.find(item => item.name === trendProduct.value)?.product_name || trendProduct.value)
const selectedItemName = computed(() => envelope.value.test_items.rows.find(item => item.name === trendItem.value)?.item_name || trendItem.value)
const chartPoints = computed(() => {
  const series = envelope.value.trend?.series || []
  if (!series.length)
    return []
  const ys = series.map(item => Number(item.y ?? item.result_value ?? 0))
  const min = Math.min(...ys)
  const max = Math.max(...ys, min + 1)
  return series.map((item, index) => ({
    ...item,
    cx: 70 + (index * 630) / Math.max(1, series.length - 1),
    cy: 224 - ((Number(item.y ?? item.result_value ?? 0) - min) / (max - min)) * 176,
    significant: Boolean(item.is_significant_change)
  }))
})
const trendPolyline = computed(() => chartPoints.value.map(point => `${point.cx},${point.cy}`).join(' '))
const trendUpperY = computed(() => {
  const upper = envelope.value.trend?.spec?.upper
  const points = chartPoints.value
  if (upper === undefined || !points.length)
    return null
  const ys = points.map(item => Number(item.y ?? item.result_value ?? 0))
  const min = Math.min(...ys)
  const max = Math.max(...ys, min + 1)
  return 224 - ((Number(upper) - min) / (max - min)) * 176
})
function rowTone(row: StabilityScheduleRow) {
  return row.sample_overdue || row.test_overdue || row.exec_state?.includes('逾期') ? 'danger' : row.status === '检测中' ? 'info' : 'warning'
}
async function loadData() {
  loading.value = true
  errorMessage.value = ''
  try {
    if (!portal.user)
      await portal.bootstrap()
    envelope.value = await getLimsStability({
      section: section.value,
      keyword: keyword.value.trim() || undefined,
      status: section.value === 'schedule' ? undefined : status.value || undefined,
      exec_status: section.value === 'schedule' ? status.value || undefined : undefined,
      month: month.value.trim() || undefined
    })
    if (section.value === 'trend') {
      trendProduct.value ||= envelope.value.products.rows[0]?.name || ''
      trendItem.value ||= envelope.value.test_items.rows[0]?.name || ''
      if (trendProduct.value && trendItem.value)
        await refreshTrend()
    }
  } catch {
    errorMessage.value = '稳定性数据暂时无法加载，请检查当前账号的查看权限后重试。'
  } finally {
    loading.value = false
  }
}
async function refreshTrend() {
  if (!trendProduct.value || !trendItem.value)
    return
  trendLoading.value = true
  try {
    envelope.value = await getLimsStability({
      section: 'trend',
      stability_product: trendProduct.value,
      stability_test_item: trendItem.value,
      condition_type: trendCondition.value || undefined
    })
  } catch {
    errorMessage.value = '趋势数据暂时无法加载，请稍后重试。'
  } finally {
    trendLoading.value = false
  }
}
function clearFilters() {
  keyword.value = ''
  status.value = ''
  month.value = ''
  loadData()
}
function openSchedule(row: StabilityScheduleRow) {
  selectedSchedule.value = row
  selectedSample.value = null
  selectedResult.value = null
  drawerOpen.value = true
}
function openSample(row: StabilitySampleRow) {
  selectedSample.value = row
  selectedSchedule.value = null
  selectedResult.value = null
  drawerOpen.value = true
}
function openResult(row: StabilityResultRow) {
  selectedResult.value = row
  selectedSample.value = null
  selectedSchedule.value = null
  drawerOpen.value = true
}
watch(section, () => {
  keyword.value = ''
  status.value = ''
  month.value = ''
  drawerOpen.value = false
  loadData()
})
onMounted(loadData)
</script>

<style scoped>
.lims-stability-page {
  display: grid;
  gap: 18px;
  padding: 24px clamp(16px,3vw,42px) 44px;
  color: var(--hbos-text-primary);
}
.stability-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}
.stability-heading h1 {
  margin: 6px 0 5px;
  font-size: clamp(25px,3vw,36px);
  letter-spacing: -.03em;
}
.stability-heading p {
  margin: 0;
  color: var(--hbos-text-muted);
  font-size: 13px;
}
.stability-heading-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 10px;
}
.readonly-note {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.stability-tabs {
  display: flex;
  gap: 6px;
  overflow: auto;
  padding: 4px;
  border: 1px solid rgba(120,145,170,.18);
  border-radius: 14px;
  background: rgba(255,255,255,.62);
}
.stability-tabs a {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex: none;
  padding: 9px 14px;
  color: var(--hbos-text-muted);
  border-radius: 10px;
  text-decoration: none;
  font-size: 12px;
  font-weight: 700;
}
.stability-tabs a.active {
  color: var(--lims-ink);
  background: rgba(8,127,114,.1);
}
.stability-alert {
  margin-top: -4px;
}
.stability-kpis {
  display: grid;
  grid-template-columns: repeat(4,minmax(0,1fr));
  gap: 14px;
}
.stability-kpi {
  display: grid;
  gap: 7px;
  min-height: 116px;
  padding: 18px;
  border-radius: 16px;
}
.stability-kpi span,.stability-kpi small {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.stability-kpi strong {
  font-size: 32px;
  line-height: 1;
  letter-spacing: -.04em;
}
.tone-warning strong {
  color: #b46e12;
}
.tone-danger strong {
  color: #ba4b4b;
}
.tone-info strong {
  color: #227ca9;
}
.tone-success strong {
  color: #198465;
}
.stability-work-grid,.stability-three-grid {
  display: grid;
  grid-template-columns: minmax(0,1.28fr) minmax(340px,.72fr);
  gap: 16px;
}
.stability-three-grid {
  grid-template-columns: repeat(3,minmax(0,1fr));
}
.stability-panel {
  min-width: 0;
  padding: 18px;
  border-radius: 16px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 16px;
}
.section-head h2 {
  margin: 0 0 5px;
  font-size: 16px;
}
.section-head p {
  margin: 0;
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.panel-count,.lims-readonly-badge {
  color: var(--lims-ink);
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
}
.section-icon {
  color: var(--lims-ink);
  font-size: 20px;
}
.stability-attention-list {
  display: grid;
  gap: 5px;
}
.stability-attention-item {
  display: grid;
  grid-template-columns: 36px minmax(0,1fr) auto 18px;
  gap: 10px;
  align-items: center;
  padding: 10px 8px;
  border: 0;
  border-bottom: 1px solid rgba(120,145,170,.14);
  background: transparent;
  text-align: left;
  cursor: pointer;
}
.stability-attention-item:hover {
  background: rgba(8,127,114,.05);
}
.attention-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
}
.attention-danger {
  color: #ba4b4b;
  background: #fff0ef;
}
.attention-info {
  color: #227ca9;
  background: #eaf7fc;
}
.attention-warning {
  color: #a76a16;
  background: #fff5e3;
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
.progress-pipeline {
  display: grid;
  grid-template-columns: repeat(4,1fr);
  gap: 8px;
  padding: 14px 4px 6px;
}
.progress-item {
  display: grid;
  justify-items: center;
  gap: 5px;
  padding: 12px 4px;
  border-radius: 12px;
  background: rgba(120,145,170,.06);
}
.progress-item strong {
  font-size: 21px;
}
.progress-item small {
  color: var(--hbos-text-muted);
  font-size: 11px;
}
.progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.progress-dot.blue {
  background: #3a86c8;
}
.progress-dot.amber {
  background: #d1871d;
}
.progress-dot.green {
  background: #168463;
}
.progress-dot.gray {
  background: #94a3b8;
}
.stability-lab-tip,.trend-note,.readonly-drawer-note {
  display: flex;
  gap: 9px;
  margin-top: 16px;
  padding: 12px;
  color: var(--hbos-text-secondary);
  border-radius: 12px;
  background: rgba(8,127,114,.07);
  font-size: 12px;
  line-height: 1.6;
}
.stability-lab-tip > .anticon,.trend-note > .anticon,.readonly-drawer-note > .anticon {
  color: var(--lims-green);
  font-size: 18px;
}
.room-card {
  display: grid;
  gap: 9px;
  padding: 15px;
  border-radius: 12px;
  background: linear-gradient(135deg,rgba(8,127,114,.08),rgba(255,255,255,.5));
}
.room-card strong {
  font-size: 17px;
}
.room-card span,.room-card small {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.trend-entry {
  display: grid;
  gap: 8px;
  padding: 16px;
  color: inherit;
  text-decoration: none;
  border: 1px solid rgba(8,127,114,.18);
  border-radius: 12px;
  background: rgba(8,127,114,.04);
}
.trend-entry strong {
  color: var(--lims-ink);
}
.trend-entry span {
  color: var(--hbos-text-muted);
  font-size: 12px;
}
.stability-empty {
  display: grid;
  justify-items: center;
  gap: 7px;
  min-height: 150px;
  padding: 30px 12px;
  color: var(--hbos-text-muted);
  text-align: center;
}
.stability-empty > .anticon {
  color: var(--lims-green);
  font-size: 30px;
}
.stability-empty strong {
  color: var(--hbos-text-primary);
  font-size: 14px;
}
.stability-filters,.trend-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 15px;
}
.stability-filters .ant-input-search {
  flex: 1 1 300px;
  min-width: 220px;
}
.trend-filters .ant-select {
  min-width: 230px;
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
.trend-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 9px 18px;
  padding: 11px 13px;
  color: var(--hbos-text-secondary);
  border-radius: 10px;
  background: rgba(120,145,170,.07);
  font-size: 12px;
}
.trend-chart {
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(120,145,170,.16);
  border-radius: 12px;
  background: linear-gradient(180deg,rgba(255,255,255,.75),rgba(235,247,245,.45));
}
.trend-chart svg {
  display: block;
  width: 100%;
  height: auto;
  min-height: 240px;
}
.trend-chart line {
  stroke: rgba(100,120,140,.35);
  stroke-width: 1;
}
.trend-chart text {
  fill: var(--hbos-text-muted);
  font-size: 12px;
}
.trend-chart .trend-line {
  stroke: var(--lims-green);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.trend-chart circle {
  fill: #fff;
  stroke: var(--lims-green);
  stroke-width: 3;
}
.trend-chart circle.significant {
  fill: #fff2d8;
  stroke: #c87819;
}
.trend-chart .spec-line {
  stroke: #c87819;
  stroke-dasharray: 5 4;
}
@media (max-width:980px) {
  .stability-kpis {
    grid-template-columns: repeat(2,minmax(0,1fr));
  }
  .stability-work-grid,.stability-three-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width:700px) {
  .lims-stability-page {
    padding: 16px 12px 32px;
  }
  .stability-heading {
    flex-direction: column;
  }
  .stability-heading-actions {
    width: 100%;
    justify-content: space-between;
  }
  .stability-kpis {
    gap: 9px;
  }
  .stability-kpi {
    min-height: 100px;
    padding: 13px;
  }
  .stability-kpi strong {
    font-size: 25px;
  }
  .stability-panel {
    padding: 14px;
  }
  .stability-tabs a {
    padding: 8px 11px;
  }
  .stability-attention-item {
    grid-template-columns: 34px minmax(0,1fr) 18px;
  }
  .stability-attention-item .ant-tag {
    display: none;
  }
  .progress-pipeline {
    grid-template-columns: repeat(2,1fr);
  }
  .stability-filters,.trend-filters {
    display: grid;
    grid-template-columns: 1fr;
  }
  .trend-filters .ant-select {
    width: 100%;
  }
}
</style>
