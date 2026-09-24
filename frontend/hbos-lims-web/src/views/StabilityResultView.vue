<template>
  <div class="page">
    <StbGateBanner mode="live"
              :note="'结果录入、生效指针、显著变化判定与趋势线均来自 R8C 稳定性业务服务；趋势图不含统计控制限（QA 口径待确认）。'" />

    <div class="page-head">
      <div>
        <h1>结果录入与趋势</h1>
        <p class="page-desc">当前生效结果、在途修订、显著变化依据和评估倒计时（真实后端）</p>
      </div>
      <div class="page-actions">
        <a-button @click="auditRef?.show()">
          <template #icon><SafetyCertificateOutlined /></template>
          查看审计
        </a-button>
      </div>
    </div>
    <a-alert
      v-if="targetTimepoint"
      :type="targetTimepointMissing || targetResultMissing ? 'warning' : 'info'"
      show-icon
      :message="targetTimepointMissing ? `来源时间点 ${targetTimepoint} 未找到` : (targetResultMissing ? `时间点 ${targetTimepoint} 已打开，但结果 ${targetResult} 未找到` : `已定位时间点 ${targetTimepoint}${targetResult ? ` · 结果 ${targetResult}` : ''}`)"
      style="margin-bottom: 12px"
    />

    <div class="stb-result-layout">
      <!-- 左：检测中时间点 -->
      <div class="stb-result-col">
        <div class="stb-result-col-head">
          <b>检测中时间点</b>
          <div class="panel-sub" style="margin-top: 4px">{{ tps.length }} 个检测中</div>
        </div>
        <a-spin :spinning="tpLoading">
          <div
            v-for="t in tps"
            :key="String(t.name)"
            class="stb-result-item"
            :class="{ active: current?.name === t.name }"
            @click="openTimepoint(t)"
          >
            <div class="stb-result-item-title">{{ t.product_name }} · {{ t.batch_no }}</div>
            <div class="stb-result-item-sub">{{ t.condition_type }} · {{ t.time_point_label }} · <span class="mono">{{ t.name }}</span></div>
            <div style="margin-top: 7px"><span :class="toneClass(t.status === '检测中' ? 'info' : 'warn')">{{ t.status }}</span></div>
          </div>
          <a-empty v-if="!tpLoading && !tps.length" description="无检测中的时间点" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 20px 0" />
        </a-spin>
      </div>

      <!-- 中：结果表单 -->
      <div class="stb-result-col">
        <template v-if="current">
          <div class="stb-result-col-head">
            <div>
              <b>{{ current.product_name }} · {{ current.time_point_label }}</b>
              <div class="panel-sub" style="margin-top: 4px">
                <span class="mono">{{ current.name }}</span> · {{ current.condition_type }}
              </div>
            </div>
          </div>
          <div class="stb-result-body">
            <div class="stb-result-meta">
              <div class="stb-result-meta-row"><span>时间点状态</span><b>{{ current.status }}</b></div>
              <div class="stb-result-meta-row"><span>计划检测日</span><b>{{ current.plan_test_date || '—' }}</b></div>
              <div class="stb-result-meta-row"><span>检测截止日</span><b>{{ current.effective_test_due || '—' }}</b></div>
            </div>

            <div class="stb-form-grid">
              <div class="stb-form-field">
                <label>检验项目 *</label>
                <a-select v-model:value="form.item" :options="itemOptions" style="width: 100%" />
              </div>
              <div class="stb-form-field">
                <label>结果值 *</label>
                <a-input v-model:value="form.value" />
              </div>
              <div class="stb-form-field">
                <label>检测日期 *</label>
                <a-input v-model:value="form.testDate" placeholder="YYYY-MM-DD" />
              </div>
              <div class="stb-form-field">
                <label>来源</label>
                <a-select v-model:value="form.source" :options="sourceOptions" style="width: 100%" />
              </div>
              <div class="stb-form-field full">
                <label>备注</label>
                <a-textarea v-model:value="form.remark" :rows="2" />
              </div>
            </div>

            <!-- 在途/已批结果 -->
            <div class="stb-result-col-head" style="margin-top: 14px">
              <b>本时间点结果</b>
              <div class="panel-sub" style="margin-top: 4px">实线为当前生效；虚线为在途</div>
            </div>
            <div class="panel-body no-pad">
              <a-table :columns="resultColumns" :data-source="currentResults" size="small"
                       row-key="name" :pagination="false" :scroll="{ x: 560 }" :row-class-name="resultRowClassName">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'item'">{{ record.stability_test_item }}</template>
                  <template v-else-if="column.key === 'value'">
                    <span class="mono">{{ record.result_value }} {{ record.unit || '' }}</span>
                  </template>
                  <template v-else-if="column.key === 'status'">
                    <span :class="toneClass(resultTone(record))">{{ resultStatusLabel(record) }}</span>
                  </template>
                  <template v-else-if="column.key === 'source'">
                    <span :class="record.source_test_result ? 'source-linked' : ''">
                      {{ record.source_test_result ? '业务检验同步' : '稳定性直接录入' }}
                    </span>
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <a-space size="small">
                      <a-button v-if="can('submit_result') && !record.source_test_result && record.status === '草稿'" type="link" size="small"
                                @click="runAction('提交结果', () => submitResult(record.name))">提交</a-button>
                      <a-button v-if="can('review_result') && !record.source_test_result && record.status === '已提交'" type="link" size="small"
                                @click="runAction('复核结果', () => reviewResult(record.name))">复核</a-button>
                      <a-button v-if="can('approve_result') && !record.source_test_result && record.status === '已复核'" type="link" size="small"
                                @click="runAction('批准结果', () => approveResult(record.name))">批准</a-button>
                      <a-button v-if="can('void_result') && !record.source_test_result && record.status !== '已作废' && record.status !== '已修订'" type="link" size="small" danger
                                @click="askReason('作废结果', 'void', record)">作废</a-button>
                    </a-space>
                  </template>
                </template>
              </a-table>
            </div>

            <div class="page-actions" style="margin-top: 14px">
              <a-button size="small" type="primary" :disabled="!can('record_result') || current.status !== '检测中'"
                        @click="submitRecord">录入结果</a-button>
              <span class="panel-sub" v-if="current.status === '检测中'">
                全部必检项目批准后由系统自动完成检测
              </span>
            </div>
          </div>
        </template>
        <a-empty v-else description="从左侧选择时间点" style="padding: 48px 0" />
      </div>

      <!-- 右：趋势摘要 -->
      <div class="stb-result-col trend">
        <div class="stb-result-col-head">
          <b>趋势摘要</b>
          <div class="panel-sub" style="margin-top: 4px">只绘制当前生效值；在途点为虚线预览</div>
        </div>
        <div class="stb-form-grid" style="padding: 8px 11px 0">
          <div class="stb-form-field">
            <label>产品</label>
            <a-select v-model:value="trendProduct" :options="productOptions" style="width: 100%"
                      @change="renderTrend" />
          </div>
          <div class="stb-form-field">
            <label>检验项目</label>
            <a-select v-model:value="trendItem" :options="trendItemOptions" style="width: 100%"
                      @change="renderTrend" />
          </div>
        </div>
        <div ref="trendEl" class="stb-chart sm" style="padding: 8px 11px 0"></div>
        <div class="stb-trend-note">{{ trendNote }}</div>
        <div class="stb-countdown" v-if="advice.advised_months">
          <div class="stb-countdown-label">外推建议（仅供参考）</div>
          <strong>{{ advice.advised_months }} 个月</strong>
          <div class="stb-countdown-sub">{{ advice.branch }}</div>
        </div>
      </div>
    </div>

    <!-- 原因输入弹窗（作废/退回） -->
    <a-modal v-model:open="reasonOpen" :title="reasonTitle" @ok="confirmReason" :confirm-loading="busy">
      <a-textarea v-model:value="reasonText" :rows="3" placeholder="原因必填" />
    </a-modal>

    <StbAuditDrawer ref="auditRef" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbAuditDrawer from '@/components/stability/StbAuditDrawer.vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  approveResult, canAction, products, results,
  reviewResult, submitResult, trend, validityAdvice, voidResult,
  type ResultRow, type TrendData, type ProductRow,
} from '@/api/stability'
import { toneClass } from '@/demo/stabilityDemo'
import { callMethod } from '@/api/client'
import { readScalarQuery } from '@/features/todos/todoModel'

const auth = useAuthStore()
const route = useRoute()
const can = (action: string): boolean => canAction(auth.user?.roles, action)

const auditRef = ref<InstanceType<typeof StbAuditDrawer> | null>(null)
const tpLoading = ref(false)
const tps = ref<Record<string, unknown>[]>([])
const current = ref<Record<string, any> | null>(null)
const currentResults = ref<ResultRow[]>([])
const productRows = ref<ProductRow[]>([])
const targetTimepoint = ref('')
const targetResult = ref('')
const targetTimepointMissing = ref(false)
const targetResultMissing = ref(false)

const form = reactive({ item: '' as string, value: '', testDate: '', source: '自检', remark: '' })
const sourceOptions = ['自检', '出厂全检', '委外'].map((v) => ({ value: v, label: v }))

const resultColumns = [
  { title: '项目', key: 'item', width: 120 },
  { title: '结果', key: 'value', width: 110 },
  { title: '版本', dataIndex: 'revision_no', key: 'rev', width: 60 },
  { title: '状态', key: 'status', width: 100 },
  { title: '来源', key: 'source', width: 110 },
  { title: '显著变化', key: 'sig', dataIndex: 'is_significant_change', width: 70 },
  { title: '操作', key: 'action', width: 215 },
]

const itemOptions = computed(() => {
  const items = (current.value?.test_items as { stability_test_item: string }[] | undefined) || []
  return items.map((i) => ({ value: i.stability_test_item, label: i.stability_test_item }))
})
const productOptions = computed(() =>
  productRows.value.map((p) => ({ value: p.name, label: `${p.product_name}（${p.product_code}）` })))
const trendItemOptions = ref<{ value: string; label: string }[]>([])

const trendProduct = ref('')
const trendItem = ref('')
const trendNote = ref('趋势线为最小二乘拟合；不展示统计控制限（QA 口径待确认）。')
const advice = ref<Record<string, any>>({})

async function load() {
  targetTimepoint.value = readScalarQuery(route.query.timepoint) || ''
  targetResult.value = readScalarQuery(route.query.result) || ''
  tpLoading.value = true
  try {
    const scheduleParams = targetTimepoint.value
      ? { keyword: targetTimepoint.value, limit: 100 }
      : { exec_status: '检测中', limit: 100 }
    const res = await callMethod<{ rows: Record<string, unknown>[] }>(
      'hb_lims_app.hbos_lims.stability_service.get_stability_schedule',
      scheduleParams)
    tps.value = res.rows
    targetTimepointMissing.value = false
    targetResultMissing.value = false
    const target = targetTimepoint.value
      ? tps.value.find((row) => row.name === targetTimepoint.value)
      : undefined
    if (targetTimepoint.value && !target) {
      targetTimepointMissing.value = true
      current.value = null
      currentResults.value = []
    } else if (target) {
      await openTimepoint(target as Record<string, any>)
    } else if (!current.value && tps.value.length) {
      void openTimepoint(tps.value[0] as Record<string, any>)
    }
  } finally {
    tpLoading.value = false
  }
  const prods = await products()
  productRows.value = prods.rows
  if (prods.rows.length && !trendProduct.value) {
    trendProduct.value = prods.rows[0].name
    void loadTrendItems()
  }
}

async function loadTrendItems() {
  if (!trendProduct.value) return
  const res = await callMethod<{ rows: Record<string, unknown>[] }>(
    'hb_lims_app.hbos_lims.stability_service.get_stability_master',
    { doctype: 'HBOS Stability Test Item' })
  const rows = (res.rows || []) as { name: string; item_name?: string }[]
  trendItemOptions.value = rows.map((r) => ({ value: r.name, label: r.item_name || r.name }))
  if (rows.length) {
    trendItem.value = rows[0].name
    void renderTrend()
  }
}

async function openTimepoint(t: Record<string, any>) {
  current.value = t
  const res = await results({ timepoint: t.name, limit: 100 })
  currentResults.value = res.rows
  targetResultMissing.value = Boolean(targetResult.value && !res.rows.some((row) => row.name === targetResult.value))
  if (!form.item) {
    const first = res.rows[0] || (t.test_items as { stability_test_item: string }[] | undefined)?.[0]
    if (first) form.item = (first as { stability_test_item?: string }).stability_test_item || first.stability_test_item
  }
}

function resultRowClassName(record: ResultRow): string {
  return targetResult.value && record.name === targetResult.value ? 'todo-target-row' : ''
}

function resultTone(r: ResultRow): 'pass' | 'muted' | 'warn' {
  if (r.status === '已批准' && r.is_current) return 'pass'
  if (r.status === '已作废' || r.status === '已修订') return 'muted'
  return 'warn'
}
function resultStatusLabel(r: ResultRow): string {
  if (r.status === '已批准') return r.is_current ? '已批准 · 生效' : '已批准'
  return r.status
}

async function submitRecord() {
  const t = current.value
  if (!t) return
  if (!form.item) { message.warning('请选择检验项目'); return }
  if (!String(form.value).trim()) { message.warning('结果值必填'); return }
  if (!form.testDate.trim()) { message.warning('检测日期必填'); return }
  await runAction('录入结果', async () => {
    await recordResultSafe(t.name as string)
  })
}
async function recordResultSafe(tpName: string) {
  const { recordResult } = await import('@/api/stability')
  await recordResult(tpName, form.item, form.value, form.testDate, undefined, form.source,
                     form.remark || undefined)
  await openTimepoint(current.value as Record<string, any>)
}

const reasonOpen = ref(false)
const reasonTitle = ref('')
const reasonText = ref('')
const reasonKind = ref<'void'>('void')
const reasonTarget = ref<ResultRow | null>(null)
function askReason(title: string, kind: 'void', record: ResultRow) {
  reasonTitle.value = title
  reasonKind.value = kind
  reasonTarget.value = record
  reasonText.value = ''
  reasonOpen.value = true
}
async function confirmReason() {
  const r = reasonTarget.value
  if (!r) return
  if (!reasonText.value.trim()) { message.warning('原因必填'); return }
  await runAction(reasonTitle.value, async () => {
    if (reasonKind.value === 'void') await voidResult(r.name, reasonText.value.trim())
  })
  await openTimepoint(current.value as Record<string, any>)
}

const busy = ref(false)
async function runAction(label: string, fn: () => Promise<unknown>) {
  busy.value = true
  try {
    await fn()
    message.success(`${label}已完成`)
  } catch {
    // 错误由 client 拦截层弹出（SoD / 越权 / 状态机 / 校验）
  } finally {
    busy.value = false
  }
}

// ---- 趋势与外推 ----

const trendEl = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null

async function renderTrend() {
  if (!trendProduct.value || !trendItem.value) return
  let data: TrendData | null = null
  try {
    data = await trend(trendProduct.value, trendItem.value)
  } catch {
    return
  }
  trendNote.value = data.note
  if (!trendEl.value) return
  if (!trendChart) trendChart = echarts.init(trendEl.value)
  const labels = data.series.map((p) => p.label)
  const effective = data.series.map((p) => (p.is_current ? p.result_value : null))
  const inflight = data.series.map((p) => (p.status !== '已批准' ? p.result_value : null))
  const series: echarts.LineSeriesOption[] = [{
    name: '当前生效',
    type: 'line',
    data: effective,
    connectNulls: false,
    symbolSize: 7,
    itemStyle: { color: '#0c7c6a' },
    lineStyle: { width: 3 },
  }]
  if (inflight.some((v) => v !== null)) {
    series.push({
      name: '在途',
      type: 'line',
      data: inflight,
      connectNulls: false,
      symbolSize: 6,
      itemStyle: { color: '#d1871d' },
      lineStyle: { width: 2, type: 'dashed' },
    })
  }
  if (data.trend_line) {
    const { slope, intercept } = data.trend_line
    series.push({
      name: '线性趋势线',
      type: 'line',
      data: labels.map((_, i) => Number((intercept + slope * i).toFixed(3))),
      symbol: 'none',
      itemStyle: { color: '#8aa39b' },
      lineStyle: { width: 1.5, type: 'dotted' },
    })
  }
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 34, right: 14, top: 20, bottom: 26 },
    xAxis: {
      type: 'category', data: labels,
      axisLine: { lineStyle: { color: '#d8e2dd' } },
      axisLabel: { color: '#5f726d', fontSize: 10 },
    },
    yAxis: {
      type: 'value', scale: true,
      splitLine: { lineStyle: { color: '#eef2f0' } },
      axisLabel: { color: '#5f726d', fontSize: 10 },
    },
    series,
  }, true)
  try {
    const adv = await validityAdvice(trendProduct.value)
    advice.value = adv as Record<string, any>
  } catch {
    advice.value = {}
  }
}

function resizeCharts() { trendChart?.resize() }

onMounted(() => {
  void auth.checkSession()
  void load()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  trendChart = null
})
</script>

<style scoped>
:deep(.todo-target-row) > td { background: var(--primary-soft); }
</style>
