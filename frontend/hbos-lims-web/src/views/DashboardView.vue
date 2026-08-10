<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>工作台总览</h1>
        <p>{{ todayLabel }} · 实验室检验运行态势与待办</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="$router.push('/samples')">
          <el-icon><DocumentAdd /></el-icon>&nbsp;新建样品登记
        </el-button>
        <el-button @click="$router.push('/tasks')">查看待检任务</el-button>
      </div>
    </div>

    <div v-if="overdueCount > 0" class="alert-strip warn">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ overdueCount }} 个检验任务即将超时，{{ oosCount }} 个结果处于 OOS 候选待调查。</span>
      <a @click="$router.push('/tasks')">立即处理</a>
    </div>

    <div v-loading="loading" class="kpi-grid">
      <div class="kpi">
        <div>
          <div class="label">待检任务</div>
          <div class="value">{{ kpi.pending }} <small>项</small></div>
          <div class="trend up">{{ todayDue }} 项今日到期</div>
        </div>
        <div class="icon teal"><el-icon :size="18"><Tickets /></el-icon></div>
      </div>
      <div class="kpi">
        <div>
          <div class="label">检验中</div>
          <div class="value">{{ kpi.testing }} <small>项</small></div>
        </div>
        <div class="icon amber"><el-icon :size="18"><Timer /></el-icon></div>
      </div>
      <div class="kpi">
        <div>
          <div class="label">待复核</div>
          <div class="value">{{ kpi.review }} <small>项</small></div>
        </div>
        <div class="icon green"><el-icon :size="18"><CircleCheck /></el-icon></div>
      </div>
      <div class="kpi">
        <div>
          <div class="label">待发布 COA</div>
          <div class="value">{{ kpi.coa }} <small>份</small></div>
        </div>
        <div class="icon red"><el-icon :size="18"><Document /></el-icon></div>
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
        <el-button text type="primary" @click="$router.push('/samples')">查看全部</el-button>
      </div>
      <div class="panel-body table-wrap">
        <el-table :data="recentSamples" size="small" stripe v-loading="loading">
          <el-table-column prop="name" label="样品编号" width="180">
            <template #default="{ row }"><span class="mono">{{ row.name }}</span></template>
          </el-table-column>
          <el-table-column prop="material_name" label="物料名称" min-width="150" />
          <el-table-column prop="batch_no" label="批号" width="130">
            <template #default="{ row }"><span class="mono">{{ row.batch_no }}</span></template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="90">
            <template #default="{ row }">
              <span class="pill" :class="priorityClass(row.priority)">{{ row.priority }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }">
              <span class="pill" :class="statusClass(row.status)">{{ row.status }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="creation" label="登记日期" width="120">
            <template #default="{ row }"><span class="mono">{{ (row.creation || '').slice(0, 10) }}</span></template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { DocumentAdd, WarningFilled, Tickets, Timer, CircleCheck, Document } from '@element-plus/icons-vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useSampleStore } from '@/stores/sample'

const chartEl = ref<HTMLElement>()
const donutEl = ref<HTMLElement>()
let barChart: echarts.ECharts | null = null
let donutChart: echarts.ECharts | null = null

const dashboard = useDashboardStore()
const sampleStore = useSampleStore()

const loading = computed(() => dashboard.loading)

const todayLabel = computed(() => {
  const now = new Date()
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} 周${weekdays[now.getDay()]}`
})

const kpi = computed(() => dashboard.kpi)
const taskCount = computed(() => dashboard.taskCount)
const overdueCount = computed(() => dashboard.tasksOverdue)
const todayDue = computed(() => dashboard.tasksTodayDue)
const oosCount = computed(() => dashboard.tasksOos)

const recentSamples = computed(() => sampleStore.samples.slice(0, 5))

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

onMounted(async () => {
  window.addEventListener('resize', resizeCharts)
  await Promise.all([dashboard.loadAll(), sampleStore.fetchAll()])
  renderCharts()
})
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
.kpi .icon { width: 38px; height: 38px; border-radius: 8px; display: grid; place-items: center; flex: 0 0 38px; }
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
.table-wrap :deep(.el-table) { --el-table-header-bg-color: var(--surface-2); --el-table-border-color: var(--line); }

@media (max-width: 1180px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } .grid-2 { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .kpi-grid { grid-template-columns: 1fr; } .page-head { flex-direction: column; align-items: flex-start; gap: 8px; } }
</style>
