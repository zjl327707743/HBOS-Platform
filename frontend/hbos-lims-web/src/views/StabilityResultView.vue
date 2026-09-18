<template>
  <div class="page">
    <StbGateBanner />

    <div class="page-head">
      <div>
        <h1>结果录入与趋势</h1>
        <p class="page-desc">当前生效结果、在途修订、显著变化依据和评估倒计时</p>
      </div>
      <div class="page-actions">
        <a-button @click="auditRef?.show()">
          <template #icon><SafetyCertificateOutlined /></template>
          查看审计
        </a-button>
        <a-button type="primary" @click="toast('已保存为结果草稿（原型）')">
          <template #icon><FormOutlined /></template>
          保存结果草稿
        </a-button>
      </div>
    </div>

    <div class="stb-result-layout">
      <!-- 左：待处理时间点 -->
      <div class="stb-result-col">
        <div class="stb-result-col-head">
          <b>待处理时间点</b>
          <div class="panel-sub" style="margin-top: 4px">8 个检测中 · 3 个待复核</div>
        </div>
        <div
          v-for="r in RESULT_ITEMS"
          :key="r.id"
          class="stb-result-item"
          :class="{ active: current?.id === r.id }"
          @click="current = r"
        >
          <div class="stb-result-item-title">{{ r.title }}</div>
          <div class="stb-result-item-sub">{{ r.sub }}</div>
          <div style="margin-top: 7px"><span :class="toneClass(r.tone)">{{ r.status }}</span></div>
        </div>
      </div>

      <!-- 中：结果表单 -->
      <div class="stb-result-col">
        <template v-if="current">
          <div class="stb-result-col-head">
            <div style="display: flex; justify-content: space-between; gap: 10px; align-items: flex-start">
              <div>
                <b>{{ current.form.title }}</b>
                <div class="panel-sub" style="margin-top: 4px">
                  <span class="mono">{{ current.form.ref }}</span> · {{ current.form.version }}
                </div>
              </div>
              <span :class="toneClass(current.form.versionTone)">{{ current.form.versionStatus }}</span>
            </div>
          </div>
          <div class="stb-result-body">
            <div class="stb-result-meta">
              <div class="stb-result-meta-row"><span>当前生效结果</span><b>{{ current.form.currentResult }}</b></div>
              <div class="stb-result-meta-row"><span>规格冻结快照</span><b>{{ current.form.specSnapshot }}</b></div>
              <div class="stb-result-meta-row"><span>显著变化规则</span><b>{{ current.form.changeRule }}</b></div>
              <div class="stb-result-meta-row"><span>基线</span><b>{{ current.form.baseline }}</b></div>
            </div>

            <div class="stb-form-grid">
              <div class="stb-form-field">
                <label>结果值 *</label>
                <a-input v-model:value="draftValue" />
              </div>
              <div class="stb-form-field">
                <label>单位 *</label>
                <a-select v-model:value="draftUnit" :options="unitOptions" style="width: 100%" />
              </div>
              <div class="stb-form-field">
                <label>结果判定</label>
                <a-select v-model:value="draftVerdict" :options="verdictOptions" style="width: 100%" />
              </div>
              <div class="stb-form-field">
                <label>检测日期 *</label>
                <a-input v-model:value="draftDate" />
              </div>
              <div class="stb-form-field full">
                <label>显著变化依据 / 备注</label>
                <a-textarea v-model:value="draftRemark" :rows="3" />
              </div>
            </div>

            <div class="page-actions" style="margin-top: 14px">
              <a-button size="small" @click="toast('已保存结果草稿（原型）')">保存草稿</a-button>
              <a-button size="small" type="primary" @click="toast('已提交复核，原版仍保持当前生效（原型）')">提交复核</a-button>
            </div>
          </div>
        </template>
        <a-empty v-else description="从左侧选择时间点" style="padding: 48px 0" />
      </div>

      <!-- 右：趋势摘要 -->
      <div class="stb-result-col trend">
        <div class="stb-result-col-head">
          <b>趋势摘要</b>
          <div class="panel-sub" style="margin-top: 4px">只绘制当前生效值；虚线为在途预览</div>
        </div>
        <div ref="trendEl" class="stb-chart sm" style="padding: 8px 11px 0"></div>
        <div class="stb-trend-note">{{ TREND_NOTE }}</div>
        <div class="stb-countdown">
          <div class="stb-countdown-label">{{ COUNTDOWN.label }}</div>
          <strong>{{ COUNTDOWN.value }}</strong>
          <div class="stb-countdown-sub">{{ COUNTDOWN.deadline }}</div>
        </div>
      </div>
    </div>

    <StbAuditDrawer ref="auditRef" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { FormOutlined, SafetyCertificateOutlined } from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbAuditDrawer from '@/components/stability/StbAuditDrawer.vue'
import { COUNTDOWN, RESULT_ITEMS, TREND_NOTE, toneClass, type ResultItem } from '@/demo/stabilityDemo'

const auditRef = ref<InstanceType<typeof StbAuditDrawer> | null>(null)
const current = ref<ResultItem | null>(RESULT_ITEMS[0])

// 表单草稿：切换时间点时按当前记录回填（原型不做真实保存）
const draftValue = ref('')
const draftUnit = ref('%')
const draftVerdict = ref('显著变化候选')
const draftDate = ref('')
const draftRemark = ref('')

const unitOptions = ['%', 'mg', 'mm'].map((v) => ({ value: v, label: v }))
const verdictOptions = ['显著变化候选', '符合趋势', '不参与判定'].map((v) => ({ value: v, label: v }))

function fillDraft(r: ResultItem | null) {
  if (!r) return
  draftValue.value = r.form.value
  draftUnit.value = r.form.unit
  draftVerdict.value = r.form.verdict
  draftDate.value = r.form.testDate
  draftRemark.value = r.form.remark
}
fillDraft(current.value)

watch(current, (r) => {
  fillDraft(r)
  renderTrend()
})

const trendEl = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null

function renderTrend() {
  const r = current.value
  if (!trendEl.value || !r) return
  if (!trendChart) trendChart = echarts.init(trendEl.value)

  const labels = r.trend.map((p) => p.label)
  const effective = r.trend.map((p) => p.effective)
  const lastEffectiveIdx = effective.reduce<number>((acc, v, i) => (v !== null ? i : acc), -1)
  const hasInflight = r.trend.some((p) => p.inflight !== null)

  // 在途预览：沿当前生效值延伸至在途点，虚线提示「不影响当前生效值」
  const inflightSeries = r.trend.map((p, i) => (i <= lastEffectiveIdx ? p.effective : p.inflight))

  const series: echarts.LineSeriesOption[] = [
    {
      name: '当前生效',
      type: 'line',
      data: effective,
      connectNulls: false,
      symbolSize: 7,
      itemStyle: { color: '#0c7c6a' },
      lineStyle: { width: 3 },
    },
  ]
  if (hasInflight) {
    series.push({
      name: '在途预览',
      type: 'line',
      data: inflightSeries,
      connectNulls: false,
      symbolSize: 7,
      itemStyle: { color: '#d1871d' },
      lineStyle: { width: 2, type: 'dashed' },
    })
  }

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 34, right: 14, top: 20, bottom: 26 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: '#d8e2dd' } },
      axisLabel: { color: '#5f726d', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { color: '#eef2f0' } },
      axisLabel: { color: '#5f726d', fontSize: 10 },
    },
    series,
  }, true)
}

function resizeCharts() {
  trendChart?.resize()
}

function toast(msg: string) {
  message.success(msg)
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
