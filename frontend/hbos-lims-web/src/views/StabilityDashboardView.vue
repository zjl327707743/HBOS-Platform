<template>
  <div class="page">
    <StbGateBanner />

    <div class="page-head">
      <div>
        <h1>稳定性工作台</h1>
        <p class="page-desc">2026 年 9 月 · 稳定性考察执行态势、临近时间点和质量风险</p>
      </div>
      <div class="page-actions">
        <a-button @click="noticeRef?.show()">
          <template #icon><PlusOutlined /></template>
          新建考察通知
        </a-button>
        <router-link to="/stability/schedule">
          <a-button type="primary">
            <template #icon><CalendarOutlined /></template>
            打开本周计划
          </a-button>
        </router-link>
      </div>
    </div>

    <div class="alert-strip">
      <AlertOutlined />
      <span>{{ DASHBOARD_ALERT }}</span>
      <router-link class="alert-link" to="/stability/schedule">立即处理</router-link>
    </div>

    <div class="stb-kpi-grid">
      <div v-for="k in DASHBOARD_KPIS" :key="k.label" class="stb-kpi">
        <div>
          <div class="stb-kpi-label">{{ k.label }}</div>
          <div class="stb-kpi-value">{{ k.value }} <small v-if="k.unit">{{ k.unit }}</small></div>
          <div class="stb-kpi-hint" :class="hintClass(k.tone)">{{ k.hint }}</div>
        </div>
        <div class="stb-kpi-icon" :class="iconClass(k.tone)">
          <component :is="kpiIcon(k.icon)" />
        </div>
      </div>
    </div>

    <div class="grid-2">
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">时间点执行趋势</div>
            <div class="panel-sub">近 8 周计划时间点与已完成时间点</div>
          </div>
          <span class="pill pill-primary">执行率 {{ EXEC_TREND.rate }}</span>
        </div>
        <div class="panel-body">
          <div ref="trendEl" class="stb-chart"></div>
          <div class="stb-legend-inline">
            <span class="stb-live">● 已完成</span>
            <span>┄ 计划</span>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">需要关注</div>
            <div class="panel-sub">按风险等级排序的待处理事项</div>
          </div>
          <router-link to="/stability/schedule"><a-button size="small">查看计划</a-button></router-link>
        </div>
        <div class="panel-body">
          <div class="stb-risk-list">
            <div v-for="(r, i) in RISK_ITEMS" :key="i" class="stb-risk-item">
              <span class="stb-risk-mark" :class="riskClass(r.tone)"></span>
              <div class="stb-risk-main">
                <div class="stb-risk-title">{{ r.title }}</div>
                <div class="stb-risk-sub">{{ r.sub }}</div>
              </div>
              <span class="stb-risk-tag">{{ r.tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="stb-three-col">
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">近期时间点</div>
            <div class="panel-sub">最近 5 个待处理时间点</div>
          </div>
          <router-link to="/stability/schedule"><a-button size="small">计划台账</a-button></router-link>
        </div>
        <div class="panel-body no-pad">
          <a-table
            :columns="pointColumns"
            :data-source="RECENT_TIMEPOINTS"
            size="small"
            row-key="point"
            :pagination="false"
            :scroll="{ x: 420 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'point'"><span class="mono">{{ record.point }}</span></template>
              <template v-else-if="column.key === 'product'">
                <div class="stb-cell-strong">{{ record.product }}</div>
                <div class="dim mono">{{ record.batch }}</div>
              </template>
              <template v-else-if="column.key === 'planned'"><span class="mono">{{ record.planned }}</span></template>
              <template v-else-if="column.key === 'status'">
                <span :class="toneClass(record.tone)">{{ record.status }}</span>
              </template>
            </template>
          </a-table>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">执行结构</div>
            <div class="panel-sub">按储存条件统计当前样品</div>
          </div>
        </div>
        <div class="panel-body">
          <div v-for="c in CONDITION_STRUCTURE" :key="c.label" class="stb-legend-row">
            <span class="stb-legend-dot" :style="{ background: c.color }"></span>{{ c.label }}
            <b>{{ c.count }}</b>
          </div>
          <div class="progress-track" style="margin-top: 15px">
            <i class="green" style="width: 68%"></i>
          </div>
          <div class="panel-sub" style="margin-top: 7px">当前有效样品 {{ CONDITION_TOTAL }} 个</div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">本周动作</div>
            <div class="panel-sub">按当前角色整理的快捷入口</div>
          </div>
        </div>
        <div class="panel-body">
          <div class="stb-timeline">
            <div v-for="(a, i) in WEEK_ACTIONS" :key="i" class="stb-timeline-item">
              <div class="stb-timeline-date">{{ a.date }}</div>
              <div>
                <div class="stb-timeline-title">{{ a.title }}</div>
                <div class="stb-timeline-sub">{{ a.sub }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <StbNoticeDrawer ref="noticeRef" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import type { Component } from 'vue'
import {
  AlertOutlined, CalendarOutlined, FormOutlined, PlusOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbNoticeDrawer from '@/components/stability/StbNoticeDrawer.vue'
import {
  CONDITION_STRUCTURE, CONDITION_TOTAL, DASHBOARD_ALERT, DASHBOARD_KPIS, EXEC_TREND,
  RECENT_TIMEPOINTS, RISK_ITEMS, WEEK_ACTIONS, toneClass,
  type Kpi, type Tone,
} from '@/demo/stabilityDemo'

const noticeRef = ref<InstanceType<typeof StbNoticeDrawer> | null>(null)
const trendEl = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null

const pointColumns = [
  { title: '时间点', key: 'point', width: 90 },
  { title: '产品 / 批号', key: 'product', width: 170 },
  { title: '计划日', key: 'planned', width: 80 },
  { title: '状态', key: 'status', width: 90 },
]

function hintClass(tone: Tone): string {
  if (tone === 'pass') return 'good'
  if (tone === 'danger') return 'bad'
  return 'warn'
}

function iconClass(tone: Tone): string {
  if (tone === 'pass') return 'green'
  if (tone === 'danger') return 'red'
  if (tone === 'info') return 'teal'
  return 'amber'
}

function kpiIcon(name: Kpi['icon']): Component {
  if (name === 'calendar') return CalendarOutlined
  if (name === 'pen') return FormOutlined
  if (name === 'alert') return AlertOutlined
  return SafetyCertificateOutlined
}

function riskClass(tone: Tone): string {
  if (tone === 'danger') return 'red'
  if (tone === 'warn') return 'amber'
  return 'blue'
}

function renderTrend() {
  if (!trendEl.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendEl.value)
    // 面板标题右侧是「已完成」指示色，与图表主色一致
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 20, bottom: 28 },
      xAxis: {
        type: 'category',
        data: EXEC_TREND.weeks,
        axisLine: { lineStyle: { color: '#d8e2dd' } },
        axisLabel: { color: '#5f726d', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 30,
        splitLine: { lineStyle: { color: '#eef2f0' } },
        axisLabel: { color: '#5f726d', fontSize: 10 },
      },
      series: [
        {
          name: '已完成',
          type: 'line',
          data: EXEC_TREND.done,
          smooth: true,
          symbolSize: 7,
          itemStyle: { color: '#0c7c6a' },
          lineStyle: { width: 3 },
          areaStyle: { color: 'rgba(12,124,106,0.10)' },
        },
        {
          name: '计划',
          type: 'line',
          data: EXEC_TREND.planned,
          smooth: true,
          symbol: 'none',
          itemStyle: { color: '#d1871d' },
          lineStyle: { width: 2, type: 'dashed' },
        },
      ],
    })
  }
}

function resizeCharts() {
  trendChart?.resize()
}

onMounted(() => {
  renderTrend()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  trendChart = null
})
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
</style>
