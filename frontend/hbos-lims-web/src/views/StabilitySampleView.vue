<template>
  <div class="page">
    <StbGateBanner />

    <div class="page-head">
      <div>
        <h1>样品入箱与台账</h1>
        <p class="page-desc">入箱登记、标签打印、样品状态和库存流水</p>
      </div>
      <div class="page-actions">
        <a-button @click="toast('标签批量打印入口已打开')">
          <template #icon><PrinterOutlined /></template>
          标签打印
        </a-button>
        <a-button type="primary" @click="inboxOpen = true">
          <template #icon><PlusOutlined /></template>
          登记入箱
        </a-button>
      </div>
    </div>

    <div class="stb-kpi-grid">
      <div v-for="k in SAMPLE_KPIS" :key="k.label" class="stb-kpi">
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

    <div class="filter-bar">
      <a-input v-model:value="keyword" placeholder="搜索稳定性样品 / 产品 / 批号" allow-clear style="flex: 1; min-width: 200px" />
      <a-select v-model:value="conditionFilter" :options="conditionOptions" style="width: 160px" />
      <a-select v-model:value="statusFilter" :options="statusOptions" style="width: 150px" />
      <a-button size="small" @click="reset">重置</a-button>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">稳定性样品台账</div>
          <div class="panel-sub">样品状态变化通过 Sample Log 追加记录，当前页只读展示</div>
        </div>
        <span class="pill pill-muted">只读投影</span>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="columns"
          :data-source="filtered"
          size="small"
          row-key="name"
          :pagination="{ pageSize: 10 }"
          :scroll="{ x: 1080 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
            <template v-else-if="column.key === 'product'">
              <div class="stb-cell-strong">{{ record.product }}</div>
              <div class="dim">{{ record.batch }} · {{ record.form }}</div>
            </template>
            <template v-else-if="column.key === 'room'">
              <div>{{ record.condition }}</div>
              <div class="dim mono">{{ record.room }}</div>
            </template>
            <template v-else-if="column.key === 'inDate'"><span class="mono">{{ record.inDate }}</span></template>
            <template v-else-if="column.key === 'status'">
              <span :class="toneClass(record.statusTone)">{{ record.status }}</span>
            </template>
            <template v-else-if="column.key === 'eval'">
              <span :class="toneClass(record.evalTone)">{{ record.eval }}</span>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="openSample(record)">查看</a-button>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 登记入箱 -->
    <a-drawer v-model:open="inboxOpen" title="登记稳定性样品入箱" :width="560" placement="right">
      <p class="stb-gate-sub">只展示字段布局与日期校验提示</p>
      <div class="stb-drawer-section">
        <h3>入箱信息</h3>
        <div class="stb-form-grid">
          <div class="stb-form-field">
            <label>来源样品 *</label>
            <a-select v-model:value="inbox.source" :options="sourceOptions" style="width: 100%" />
          </div>
          <div class="stb-form-field">
            <label>储存条件 *</label>
            <a-select v-model:value="inbox.condition" :options="conditionFullOptions" style="width: 100%" />
          </div>
          <div class="stb-form-field">
            <label>稳定性室 *</label>
            <a-select v-model:value="inbox.room" :options="roomOptions" style="width: 100%" />
          </div>
          <div class="stb-form-field">
            <label>入箱日期 *</label>
            <a-input v-model:value="inbox.inDate" />
          </div>
          <div class="stb-form-field">
            <label>数量 *</label>
            <a-input v-model:value="inbox.qty" />
          </div>
          <div class="stb-form-field">
            <label>单位 *</label>
            <a-select v-model:value="inbox.uom" :options="uomOptions" style="width: 100%" />
          </div>
        </div>
      </div>
      <div class="stb-notice amber">
        若入箱日期超过生产日期 1 个月，保存时必须填写评估结论、评估人和评估日期；不直接拦截入箱。
      </div>
      <template #footer>
        <a-button @click="inboxOpen = false">取消</a-button>
        <a-button type="primary" @click="saveInbox">保存入箱草稿</a-button>
      </template>
    </a-drawer>

    <!-- 样品详情 -->
    <a-drawer v-model:open="sampleOpen" :title="sample?.name || '稳定性样品详情'" :width="560" placement="right">
      <p class="stb-gate-sub">只读投影 · Sample Log 仅追加</p>
      <template v-if="sample">
        <div class="stb-drawer-section">
          <h3>样品摘要</h3>
          <div class="stb-drawer-kv">
            <div><label>产品 / 批号</label><b>{{ sample.product }} / {{ sample.batch }}</b></div>
            <div><label>条件 / 房间</label><b>{{ sample.condition }} / {{ sample.room }}</b></div>
            <div><label>入箱日期</label><b class="mono">{{ sample.inDate }}</b></div>
            <div><label>当前状态</label><b><span :class="toneClass(sample.statusTone)">{{ sample.status }}</span></b></div>
            <div><label>当前数量</label><b>{{ sample.qty }}</b></div>
            <div><label>强制评估</label><b>{{ sample.eval }}</b></div>
          </div>
        </div>
        <div class="stb-drawer-section">
          <h3>Sample Log · 仅追加</h3>
          <div v-for="(l, i) in sample.log" :key="i" class="stb-audit-line">
            <span class="stb-audit-dot"></span>
            <div><strong>{{ l.action }} · {{ l.delta }}</strong><span>{{ l.meta }}</span></div>
          </div>
        </div>
      </template>
      <template #footer>
        <a-button @click="sampleOpen = false">关闭</a-button>
        <a-button type="primary" @click="toast('标签打印入口已触发（原型）')">打印样品标签</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import type { Component } from 'vue'
import { message } from 'ant-design-vue'
import {
  AlertOutlined, CalendarOutlined, FormOutlined, PlusOutlined, PrinterOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import { SAMPLE_KPIS, SAMPLES, toneClass, type Kpi, type SampleRow, type Tone } from '@/demo/stabilityDemo'

const keyword = ref('')
const conditionFilter = ref('全部储存条件')
const statusFilter = ref('全部状态')

const conditionOptions = ['全部储存条件', '长期', '加速', '中间'].map((v) => ({ value: v, label: v }))
const statusOptions = ['全部状态', '在箱', '部分取样', '待处理'].map((v) => ({ value: v, label: v }))

const filtered = computed(() =>
  SAMPLES.filter((s) => {
    const kw = keyword.value.trim()
    if (kw && !`${s.name}${s.product}${s.batch}`.includes(kw)) return false
    if (conditionFilter.value !== '全部储存条件' && s.condition !== conditionFilter.value) return false
    if (statusFilter.value !== '全部状态' && s.status !== statusFilter.value) return false
    return true
  }),
)

function reset() {
  keyword.value = ''
  conditionFilter.value = '全部储存条件'
  statusFilter.value = '全部状态'
}

function toast(msg: string) {
  message.success(msg)
}

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

const columns = [
  { title: '样品编号', key: 'name', width: 220 },
  { title: '产品 / 批号', key: 'product', width: 190 },
  { title: '条件 / 房间', key: 'room', width: 130 },
  { title: '入箱日期', key: 'inDate', width: 120 },
  { title: '数量', key: 'qty', dataIndex: 'qty', width: 90 },
  { title: '状态', key: 'status', width: 110 },
  { title: '评估', key: 'eval', width: 110 },
  { title: '操作', key: 'action', width: 80, fixed: 'right' },
] as const

// ---- 登记入箱 ----
const inboxOpen = ref(false)
const inbox = reactive({
  source: 'TEST-HBOS-M2-SMP-0101',
  condition: '长期 · 25±2℃ / 60±5%RH',
  room: 'STB-RM-01',
  inDate: '2026-09-15',
  qty: '12',
  uom: '盒',
})
const sourceOptions = ['TEST-HBOS-M2-SMP-0101', 'TEST-HBOS-M2-SMP-0102'].map((v) => ({ value: v, label: v }))
const conditionFullOptions = ['长期 · 25±2℃ / 60±5%RH', '加速 · 40±2℃ / 75±5%RH'].map((v) => ({ value: v, label: v }))
const roomOptions = ['STB-RM-01', 'STB-RM-02'].map((v) => ({ value: v, label: v }))
const uomOptions = ['盒', '瓶', '支'].map((v) => ({ value: v, label: v }))

function saveInbox() {
  inboxOpen.value = false
  message.success('原型入口：入箱草稿未落库，正式动作需由受控业务方法完成')
}

// ---- 样品详情 ----
const sampleOpen = ref(false)
const sample = ref<SampleRow | null>(null)

function openSample(row: SampleRow) {
  sample.value = row
  sampleOpen.value = true
}
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
</style>
