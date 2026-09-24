<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>工作台总览</h1>
        <p>{{ todayLabel }} · 实验室检验运行态势与待办</p>
      </div>
      <div class="page-actions">
        <a-button type="primary" @click="$router.push('/samples')">
          <template #icon><PlusOutlined /></template>
          新建样品登记
        </a-button>
        <a-button @click="$router.push('/tasks')">查看待检任务</a-button>
      </div>
    </div>

    <div v-if="overdueCount > 0" class="alert-strip warn">
      <WarningOutlined />
      <span>{{ overdueCount }} 个检验任务即将超时，{{ oosCount }} 个结果处于 OOS 候选待调查。</span>
      <a @click="$router.push('/tasks')">立即处理</a>
    </div>

    <div class="kpi-grid">
      <div class="kpi">
        <div>
          <div class="label">待检任务</div>
          <div class="value">{{ kpi.pending }} <small>项</small></div>
          <div class="trend up">{{ todayDue }} 项今日到期</div>
        </div>
        <div class="icon teal"><SnippetsOutlined /></div>
      </div>
      <div class="kpi">
        <div>
          <div class="label">检验中</div>
          <div class="value">{{ kpi.testing }} <small>项</small></div>
        </div>
        <div class="icon amber"><ClockCircleOutlined /></div>
      </div>
      <div class="kpi">
        <div>
          <div class="label">待复核</div>
          <div class="value">{{ kpi.review }} <small>项</small></div>
        </div>
        <div class="icon green"><CheckCircleOutlined /></div>
      </div>
      <div class="kpi">
        <div>
          <div class="label">待发布 COA</div>
          <div class="value">{{ kpi.coa }} <small>份</small></div>
        </div>
        <div class="icon red"><FileTextOutlined /></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <div>
            <h3>检验任务按检验组分布</h3>
            <div class="sub">从待检任务看板报表统计</div>
          </div>
          <span class="pill muted">{{ taskCount }} 项任务</span>
        </div>
        <div class="panel-body">
          <div ref="chartEl" class="chart"></div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <h3>任务状态分布</h3>
            <div class="sub">{{ taskCount }} 项任务当前分布</div>
          </div>
        </div>
        <div class="panel-body">
          <div ref="donutEl" class="chart"></div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div>
          <h3>最近样品</h3>
          <div class="sub">最新登记样品（来自样品台账）</div>
        </div>
        <a-button type="link" @click="$router.push('/samples?tab=ledger')">查看全部</a-button>
      </div>
      <div class="panel-body table-wrap">
        <a-table
          :columns="columns"
          :data-source="recentSamples"
          :loading="loading"
          size="small"
          row-key="name"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
            <template v-else-if="column.key === 'batch_no'"><span class="mono">{{ record.batch_no }}</span></template>
            <template v-else-if="column.key === 'priority'">
              <span class="pill" :class="priorityClass(record.priority)">{{ record.priority }}</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <span class="pill" :class="statusClass(record.status)">{{ record.status }}</span>
            </template>
            <template v-else-if="column.key === 'creation'">
              <span class="mono">{{ (record.creation || '').slice(0, 10) }}</span>
            </template>
          </template>
        </a-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import {
  PlusOutlined, WarningOutlined, SnippetsOutlined,
  ClockCircleOutlined, CheckCircleOutlined, FileTextOutlined,
} from '@ant-design/icons-vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useSampleStore } from '@/stores/sample'

const chartEl = ref<HTMLElement>()
const donutEl = ref<HTMLElement>()
let barChart: echarts.ECharts | null = null
let donutChart: echarts.ECharts | null = null

const dashboard = useDashboardStore()
const sampleStore = useSampleStore()

const loading = computed(() => dashboard.loading)

const clock = ref(new Date())
const todayLabel = computed(() => {
  const d = clock.value
  const pad = (n: number) => String(n).padStart(2, '0')
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} 周${weekdays[d.getDay()]} ${pad(d.getHours())}:${pad(d.getMinutes())}`
})
let clockTimer: number | undefined

const kpi = computed(() => dashboard.kpi)
const taskCount = computed(() => dashboard.taskCount)
const overdueCount = computed(() => dashboard.tasksOverdue)
const todayDue = computed(() => dashboard.tasksTodayDue)
const oosCount = computed(() => dashboard.tasksOos)

const recentSamples = computed(() => sampleStore.samples.slice(0, 5))

const columns = [
  { title: '样品编号', key: 'name', width: 180 },
  { title: '物料名称', key: 'material_name' },
  { title: '批号', key: 'batch_no', width: 130 },
  { title: '优先级', key: 'priority', width: 90 },
  { title: '状态', key: 'status', width: 110 },
  { title: '登记日期', key: 'creation', width: 120 },
]

function priorityClass(p: string) {
  return { 特急: 'pill-danger', 加急: 'pill-warn', 常规: 'pill-info' }[p] || 'pill-muted'
}
function statusClass(s: string) {
  return {
    已批准: 'pill-pass', 检验中: 'pill-info', 待复核: 'pill-warn',
    'OOS 候选': 'pill-danger', 已登记: 'pill-muted', 已放行: 'pill-pass',
  }[s] || 'pill-muted'
}

function renderCharts() {
  if (chartEl.value) {
    barChart = echarts.init(chartEl.value)
    barChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 10, top: 20, bottom: 24 },
      xAxis: {
        type: 'category',
        data: dashboard.rhythmByGroup.map((g) => g.label),
        axisLine: { lineStyle: { color: '#d8e2dd' } },
        axisLabel: { color: '#5f726d', fontSize: 11 },
      },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#eef2f0' } }, axisLabel: { color: '#5f726d' } },
      series: [{
        type: 'bar',
        data: dashboard.rhythmByGroup.map((g) => g.value),
        itemStyle: { color: '#0c7c6a', borderRadius: [4, 4, 0, 0] },
        barWidth: 28,
      }],
    })
  }

  if (donutEl.value) {
    donutChart = echarts.init(donutEl.value)
    donutChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, icon: 'circle', textStyle: { fontSize: 11, color: '#5f726d' } },
      series: [{
        type: 'pie',
        radius: ['48%', '68%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
        data: dashboard.distribution.map((d) => ({ value: d.value, name: d.name, itemStyle: { color: d.color } })),
      }],
    })
  }
}

function resizeCharts() {
  barChart?.resize()
  donutChart?.resize()
}

clockTimer = window.setInterval(() => { clock.value = new Date() }, 1000)
onMounted(async () => {
  window.addEventListener('resize', resizeCharts)
  await Promise.all([dashboard.loadAll(), sampleStore.fetchAll()])
  renderCharts()
})
onUnmounted(() => window.clearInterval(clockTimer))
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }

.alert-strip {
  display: flex; align-items: center; gap: 8px;
  background: var(--warn-soft); border: 1px solid #ecd9b4;
  border-radius: var(--radius); padding: 10px 14px;
  font-size: 12px; color: var(--warn); margin-bottom: 14px;
}
.alert-strip a { color: var(--warn); font-weight: 600; cursor: pointer; margin-left: auto; text-decoration: underline; }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; min-height: 100px; }
.kpi { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px; display: flex; align-items: flex-start; justify-content: space-between; }
.kpi .label { color: var(--muted); font-size: 12px; }
.kpi .value { font-size: 26px; font-weight: 700; line-height: 1.2; margin-top: 6px; }
.kpi .value small { font-size: 12px; color: var(--muted); font-weight: 500; }
.kpi .trend { font-size: 11px; margin-top: 4px; }
.kpi .trend.up { color: var(--danger); }
.kpi .trend.down { color: var(--pass); }
.kpi .icon { width: 38px; height: 38px; border-radius: 8px; display: grid; place-items: center; flex: 0 0 38px; font-size: 18px; }
.kpi .icon.teal { background: var(--primary-soft); color: var(--primary); }
.kpi .icon.amber { background: var(--warn-soft); color: var(--warn); }
.kpi .icon.green { background: var(--pass-soft); color: var(--pass); }
.kpi .icon.red { background: var(--danger-soft); color: var(--danger); }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--line); }
.panel-head h3 { font-size: 14px; }
.panel-head .sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.panel-body { padding: 16px; }
.panel-body.table-wrap { padding: 0; }
.panel-body .chart { height: 220px; }
.table-wrap :deep(.ant-table) { font-size: 13px; }

@media (max-width: 1180px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .grid-2 { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .kpi-grid { grid-template-columns: 1fr; } .page-head { flex-direction: column; align-items: flex-start; gap: 8px; } }
</style>
