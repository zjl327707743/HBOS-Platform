<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>留样工作台总览</h1>
        <p class="page-desc">留样生命周期待办与到期态势 · 真实后端聚合（R7A~C）</p>
      </div>
      <div class="page-actions">
        <a-button @click="loadAll">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <router-link to="/retention/samples">
          <a-button type="primary">
            <template #icon><PlusOutlined /></template>
            留样登记
          </a-button>
        </router-link>
      </div>
    </div>

    <a-alert type="info" show-icon :message="realNote" style="margin-bottom: 14px" />

    <div class="kpi-grid">
      <div class="kpi-card" v-for="k in kpis" :key="k.label">
        <div class="kpi-label">{{ k.label }}</div>
        <div class="kpi-num" :class="k.tone">{{ k.value }}</div>
        <div class="kpi-sub">{{ k.sub }}</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">留样状态分布</div>
            <div class="panel-sub">当前留样生命周期状态（结存/在途/终态）</div>
          </div>
        </div>
        <div class="panel-body"><div ref="statusEl" class="ret-chart"></div></div>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">留样期至趋势 · 未来 12 个月</div>
            <div class="panel-sub">按留样期至月份统计（不含已销毁/已转出）</div>
          </div>
        </div>
        <div class="panel-body"><div ref="dueEl" class="ret-chart"></div></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">观察计划完整性</div>
            <div class="panel-sub">各产品年度已选观察批 N/3（不足提示可补选）</div>
          </div>
          <router-link to="/retention/observations"><a-button type="link">观察任务 →</a-button></router-link>
        </div>
        <div class="panel-body">
          <a-empty v-if="!completeness.length" description="暂无已选观察批" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          <div class="progress-row" v-for="c in completeness" :key="c.product + c.year">
            <div class="progress-main">
              <div class="progress-top">
                <span><strong>{{ c.product }}</strong> <span class="dim">· {{ c.rule }}</span></span>
                <span class="num">{{ c.cap ? `${c.selected}/${c.cap}` : '每批' }}</span>
              </div>
              <div class="progress-track">
                <i :class="c.cap && c.selected < c.cap ? 'amber' : 'green'" :style="{ width: pct(c) + '%' }"></i>
              </div>
            </div>
            <span class="pill" :class="c.cap && c.selected < c.cap ? 'pill-warn' : 'pill-pass'">
              {{ c.cap && c.selected < c.cap ? `可补选 ${c.cap - c.selected} 批` : '完整' }}
            </span>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">审批待办</div>
            <div class="panel-sub">按当前会话角色可办（未登录则空）</div>
          </div>
        </div>
        <div class="panel-body no-pad">
          <div class="mini-list" style="padding: 2px 16px">
            <div class="mini-row" v-for="p in pending" :key="p.key">
              <div class="mini-main">
                <div class="mini-title">
                  <span class="mono">{{ p.name }}</span>
                  <span class="pill" :class="p.tone === 'danger' ? 'pill-danger' : p.tone === 'pass' ? 'pill-pass' : 'pill-warn'">{{ p.status }}</span>
                </div>
                <div class="mini-sub">{{ p.desc }}</div>
              </div>
              <router-link :to="p.link"><a-button size="small">去处理</a-button></router-link>
            </div>
            <a-empty v-if="!pending.length" description="当前角色无待办" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="margin: 8px 0" />
          </div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">处理申请 / 到期处置态势</div>
          <div class="panel-sub">销毁类处理单 deadline 超期自动标红（报表派生口径）</div>
        </div>
        <div class="page-actions">
          <span class="pill pill-warn">临期处置 {{ rowsD.length }}</span>
        </div>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="dColumns"
          :data-source="rowsD"
          size="small"
          row-key="name"
          :pagination="{ pageSize: 8 }"
          :scroll="{ x: 900 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
            <template v-else-if="column.key === 'sample'">
              {{ record.product }} <span class="dim">/ {{ record.batch }}</span>
            </template>
            <template v-else-if="column.key === 'deadline'">
              <span class="mono" :class="overdue(record) ? 'danger-text' : ''">{{ record.deadline || '—' }}</span>
              <div v-if="overdue(record)" class="dim danger-text">已超期 {{ overdueDays(record.deadline) }} 天</div>
            </template>
            <template v-else-if="column.key === 'status'">
              <span class="pill" :class="statusPill(record.status)">{{ record.status }}</span>
            </template>
            <template v-else-if="column.key === 'action'">
              <router-link :to="'/retention/disposal'"><a-button type="link" size="small">详情 →</a-button></router-link>
            </template>
          </template>
        </a-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import { useAuthStore } from '@/stores/auth'
import {
  usageList, disposalList, obsPlan, canAction,
  type UsageRow, type DisposalRow, type ObsCompleteness,
} from '@/api/retention'
import { listDoctype } from '@/api/lims'

const auth = useAuthStore()
const realNote = '已接入真实后端（R7A~C）：留样/观察/使用/处理均来自后端数据与业务方法；审批操作受会话角色与后端 SoD 约束。'

const rowsU = ref<UsageRow[]>([])
const rowsD = ref<DisposalRow[]>([])
const completeness = ref<ObsCompleteness[]>([])
const samples = ref<{ name: string; status: string; retention_due_date?: string }[]>([])

// ECharts 实例（状态分布 + 到期趋势）
const statusEl = ref<HTMLElement>()
const dueEl = ref<HTMLElement>()
let statusChart: echarts.ECharts | null = null
let dueChart: echarts.ECharts | null = null

function can(key: string): boolean {
  return canAction(auth.user?.roles, key)
}

async function loadAll() {
  try {
    const [u, d, plan, s] = await Promise.all([
      usageList(), disposalList(), obsPlan(),
      listDoctype<{ name: string; status: string; retention_due_date?: string }>(
        'HBOS Retention Sample', ['name', 'status', 'retention_due_date'], {}, 0, 'retention_date desc'),
    ])
    rowsU.value = u.rows
    rowsD.value = d.rows
    completeness.value = plan.completeness
    samples.value = s
    renderCharts()
  } catch (e: any) {
    message.error((e && e.message) || '加载工作台失败（需登录）')
  }
}

const kpis = computed(() => {
  const inStock = samples.value.filter((x) => x.status === '在库' || x.status === '部分使用').length
  const dueList = samples.value.filter((x) => x.retention_due_date && x.status !== '已销毁' && x.status !== '已转出')
  const inApproval = (s: string) => s.startsWith('待')
  const in30 = dueList.filter((x) => {
    const d = new Date(x.retention_due_date as string).getTime()
    return d >= Date.now() && d <= Date.now() + 30 * 86400_000
  }).length
  const overdue = rowsD.value.filter((r) => r.deadline && overdueDays(r.deadline) > 0).length
  return [
    { label: '在库留样', value: inStock, sub: '', tone: 'good' },
    { label: '待处理/待执行', value: rowsD.value.filter((r) => r.status === '待执行' || r.status === '待处理').length, sub: '处理链在途', tone: 'warn' },
    { label: '临期 30 天内', value: in30, sub: '', tone: 'danger' },
    { label: '审批在途', value: rowsU.value.filter((r) => inApproval(r.status)).length + rowsD.value.filter((r) => inApproval(r.status)).length, sub: '', tone: 'info' },
    { label: '销毁超期', value: overdue, sub: 'deadline 已过', tone: 'danger' },
    { label: '处理单总数', value: rowsD.value.length, sub: '', tone: 'pass' },
  ]
})

const pending = computed(() => {
  const list: { key: string; name: string; status: string; desc: string; link: string; tone: string }[] = []
  for (const u of rowsU.value) {
    const action = uAction(u.status)
    if (action && can(action)) {
      list.push({
        key: 'u' + u.name, name: u.name, status: u.status,
        desc: `${u.product} · ${u.batch} · 使用 ${u.qty} ${u.uom} · ${u.scenario}`,
        link: '/retention/usage',
        tone: u.status === '已批准' ? 'pass' : 'warn',
      })
    }
  }
  for (const d of rowsD.value) {
    const action = dAction(d)
    if (action && can(action)) {
      list.push({
        key: 'd' + d.name, name: d.name, status: d.status,
        desc: `${d.product} · ${d.batch} · ${d.type}`,
        link: '/retention/disposal',
        tone: d.deadline && overdueDays(d.deadline) > 0 ? 'danger' : 'warn',
      })
    }
  }
  return list
})

function uAction(status: string): string | null {
  const map: Record<string, string> = {
    待库存确认: 'usage_confirm', 待QC批准: 'usage_qc', 待QA批准: 'usage_qa',
    待QM批准: 'usage_qm', 已批准: 'usage_execute',
  }
  return map[status] || null
}
function dAction(d: DisposalRow): string | null {
  if (d.status === '待QC主管审核' || d.status === '待QC负责人审核') return 'disposal_qc'
  if (d.status === '待QA审核') return 'disposal_qa'
  if (d.status === '待QM批准') return 'disposal_qm'
  if (d.status === '待执行') return d.type === '留样期满继续留样' ? 'disposal_handler' : 'disposal_handler'
  return null
}

function overdue(d: DisposalRow): boolean {
  return !!d.deadline && overdueDays(d.deadline) > 0
}
function overdueDays(dateStr: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400_000))
}

function pct(c: ObsCompleteness): number {
  if (!c.cap) return 100
  return Math.min(100, Math.round((c.selected / c.cap) * 100))
}
function statusPill(s: string): string {
  if (s === '已完成' || s === '已销毁') return 'pill-pass'
  if (s === '待执行') return 'pill-primary'
  if (s.startsWith('待')) return 'pill-warn'
  return 'pill-muted'
}

const STATUS_META: { label: string; color: string; keys: string[] }[] = [
  { label: '在库', color: '#1d8a5b', keys: ['在库'] },
  { label: '部分使用', color: '#2b6cb0', keys: ['部分使用'] },
  { label: '待处理', color: '#d1871d', keys: ['待处理'] },
  { label: '已用尽', color: '#8a9a94', keys: ['已用尽'] },
  { label: '已转出', color: '#6b7f78', keys: ['已转出'] },
  { label: '已销毁', color: '#c24d3f', keys: ['已销毁'] },
]

const statusDist = computed(() =>
  STATUS_META
    .map((s) => ({ name: s.label, value: samples.value.filter((x) => s.keys.includes(x.status)).length, itemStyle: { color: s.color } }))
    .filter((d) => d.value > 0))

const dueTrend = computed(() => {
  const now = new Date()
  const months: string[] = []
  const counts: number[] = []
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    months.push(key)
    counts.push(samples.value.filter((x) => x.retention_due_date
      && x.status !== '已销毁' && x.status !== '已转出'
      && String(x.retention_due_date).startsWith(key)).length)
  }
  return { months, counts }
})

function renderCharts() {
  if (statusEl.value && !statusChart) statusChart = echarts.init(statusEl.value)
  if (statusEl.value && statusChart) {
    statusChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, icon: 'circle', textStyle: { fontSize: 11, color: '#5f726d' } },
      series: [{
        type: 'pie', radius: ['46%', '68%'], center: ['50%', '46%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold' } },
        data: statusDist.value,
      }],
    }, true)
  }
  if (dueEl.value && !dueChart) dueChart = echarts.init(dueEl.value)
  if (dueEl.value && dueChart) {
    dueChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 14, top: 24, bottom: 26 },
      xAxis: {
        type: 'category', data: dueTrend.value.months,
        axisLine: { lineStyle: { color: '#d8e2dd' } },
        axisLabel: { color: '#5f726d', fontSize: 10 },
      },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#eef2f0' } }, axisLabel: { color: '#5f726d' } },
      series: [{
        type: 'bar', data: dueTrend.value.counts,
        itemStyle: { color: '#d1871d', borderRadius: [4, 4, 0, 0] }, barWidth: 16,
      }],
    }, true)
  }
}

function resizeCharts() {
  statusChart?.resize()
  dueChart?.resize()
}

const dColumns = [
  { title: '处理单号', key: 'name', width: 200 },
  { title: '产品 / 批号', key: 'sample', width: 220 },
  { title: '类型', key: 'type', dataIndex: 'type', width: 150 },
  { title: '层级', key: 'level', width: 90, customRender: ({ record }: { record: DisposalRow }) => (record.qa_manager_required ? '5 级' : '4 级·跳过') },
  { title: '销毁时限', key: 'deadline', width: 150 },
  { title: '状态', key: 'status', width: 120 },
  { title: '操作', key: 'action', width: 80 },
]

async function boot() {
  window.addEventListener('resize', resizeCharts)
  await loadAll()
}
onMounted(boot)
onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  statusChart?.dispose()
  dueChart?.dispose()
  statusChart = null
  dueChart = null
})
</script>

<style scoped>
.ret-chart { width: 100%; height: 232px; }
@media (max-width: 900px) { .ret-chart { height: 200px; } }
</style>
