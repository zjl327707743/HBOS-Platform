<template>
  <div class="page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h1>观察任务</h1>
        <p class="page-desc">0 月基线 + 年度外观性状观察 · 应观察清单、N/3 完整性提示 · 演示数据 TEST-HBOS-M2-RET-*</p>
      </div>
      <div class="page-actions">
        <a-button @click="openSelectModal">
          <template #icon><CalendarOutlined /></template>
          观察批选取
        </a-button>
        <a-button
          type="primary"
          :disabled="!canRecord"
          :title="!canRecord ? '当前演示身份不可录入观察记录（Analyst / Manager 可录入）' : ''"
          @click="onAddRecord"
        >
          <template #icon><PlusOutlined /></template>
          新增观察记录
        </a-button>
      </div>
    </div>

    <DemoBar />

    <!-- N/3 完整性条 -->
    <div class="obs-strip" v-if="completeness.length">
      <div class="obs-chip" v-for="c in completeness" :key="c.product">
        <span class="chip-name">{{ c.product }} · {{ c.year }}</span>
        <span class="chip-bar"><i :class="complBarCls(c)" :style="{ width: complBarPct(c) + '%' }"></i></span>
        <span class="chip-num mono">{{ c.cap ? `${c.selected}/${c.cap}` : '每批' }}</span>
        <span class="pill" :class="complPillCls(c)">{{ complPillText(c) }}</span>
      </div>
      <span class="dim">年度各产品已选观察批 N/3 · 超选由后端拦截</span>
    </div>

    <div class="detail-layout">
      <!-- 左：计划看板 -->
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">计划看板</div>
            <div class="panel-sub">单击行载入右侧观察记录 · 应观察未完成优先，异常结论标红</div>
          </div>
          <div class="head-filter page-actions">
            <a-button
              v-for="t in filterTabs"
              :key="t.key"
              size="small"
              :type="filter === t.key ? 'primary' : 'default'"
              @click="filter = t.key"
            >{{ t.label }}</a-button>
          </div>
        </div>
        <div class="panel-body no-pad">
          <a-table
            :columns="columns"
            :data-source="boardRows"
            :pagination="false"
            row-key="name"
            size="small"
            :scroll="{ x: 860 }"
            :row-class-name="rowActiveCls"
            @row-click="selectRow"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
              <template v-else-if="column.key === 'sample'">
                {{ record.sampleName }}<span class="dim"> / {{ record.batch }}</span>
              </template>
              <template v-else-if="column.key === 'offset'"><span class="mono">{{ record.monthOffset }}</span></template>
              <template v-else-if="column.key === 'plan'"><span class="mono">{{ record.planDate }}</span></template>
              <template v-else-if="column.key === 'due'">
                <span class="pill" :class="duePillCls(record.due)">{{ record.due }}</span>
                <div v-if="record.due === '已逾期'" class="obs-overdue">已逾期 {{ overdueDays(record.planDate) }} 天</div>
              </template>
              <template v-else-if="column.key === 'result'">
                <span v-if="record.result" class="pill" :class="resultPillCls(record.result)">{{ record.result }}</span>
                <span v-else class="dim">—</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-button v-if="record.due !== '已完成'" type="link" size="small" @click="selectRow(record)">录入</a-button>
                <a-button v-else type="link" size="small" @click="selectRow(record)">查看</a-button>
              </template>
            </template>
          </a-table>
        </div>
      </div>

      <!-- 右：观察记录 / 录入面板 -->
      <div ref="rightPanel" class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">观察记录</div>
            <div class="panel-sub" v-if="selected"><span class="mono">{{ selected.name }}</span> · <span class="mono">{{ selected.batch }}</span></div>
            <div class="panel-sub" v-else>未选择观察批次</div>
          </div>
          <span v-if="selected" class="pill pill-warn">obs_month {{ selected.monthOffset }}</span>
        </div>
        <div class="panel-body">
          <a-empty v-if="!selected" description="从左侧计划看板选择一行后查看 / 录入观察记录" :image="Empty.PRESENTED_IMAGE_SIMPLE" />

          <!-- 已观察：只读摘要 -->
          <template v-else-if="selected.due === '已完成'">
            <div class="grid-2" style="gap: 10px; margin-bottom: 0">
              <div class="field">
                <label>实际观察日期</label>
                <div class="static mono">{{ selected.observedDate || '—' }}</div>
              </div>
              <div class="field">
                <label>观察结果</label>
                <div class="static" style="padding-top: 6px; padding-bottom: 6px">
                  <span v-if="selected.result" class="pill" :class="resultPillCls(selected.result)">{{ selected.result }}</span>
                  <span v-else class="dim">—</span>
                </div>
              </div>
            </div>
            <div class="grid-2" style="gap: 10px; margin-bottom: 0">
              <div class="field">
                <label>观察人</label>
                <div class="static">{{ selected.observer || '—' }}</div>
              </div>
              <div class="field">
                <label>审核人</label>
                <div class="static">
                  {{ selected.reviewer || '待审核' }}
                  <span v-if="selected.reviewer && selected.reviewer !== '待审核'" class="pill pill-pass" style="margin-left: 6px">已审核</span>
                </div>
              </div>
            </div>
            <div v-if="selected.anomaly" class="field">
              <label>异常描述</label>
              <div class="static">{{ selected.anomaly }}</div>
            </div>
            <div v-if="canReview && selected.reviewer === '待审核'" class="review-zone">
              <span class="dim">当前演示身份为 {{ reviewerRoleLabel }}，可对该条记录审核</span>
              <a-button type="primary" size="small" @click="reviewObs">审核通过</a-button>
            </div>
          </template>

          <!-- 未观察：录入表单 -->
          <template v-else>
            <div class="field">
              <label>观察时间窗</label>
              <div class="static">
                计划日期 <span class="mono">{{ selected.planDate }}</span>
                <span class="dim"> · 观察期至 {{ windowEnd(selected.planDate) }}</span>
              </div>
            </div>
            <div class="field">
              <label>实际观察日期</label>
              <a-date-picker v-model:value="draft.date" value-format="YYYY-MM-DD" style="width: 100%" :disabled="!canRecord" />
            </div>
            <div class="field">
              <label>外观性状</label>
              <a-input v-model:value="draft.appearance" placeholder="如 白色至类白色片剂，外观完整" :disabled="!canRecord" />
            </div>
            <div class="field">
              <label>结果</label>
              <a-radio-group v-model:value="draft.result" :disabled="!canRecord">
                <a-radio value="正常">正常</a-radio>
                <a-radio value="异常">异常</a-radio>
              </a-radio-group>
            </div>
            <div v-if="draft.result === '异常'" class="field">
              <label>异常描述 <span class="dim">（结果异常时必填）</span></label>
              <a-textarea v-model:value="draft.anomaly" :rows="3" placeholder="填写异常表现与报告对象" :disabled="!canRecord" />
            </div>
            <div class="grid-2" style="gap: 10px; margin-bottom: 0">
              <div class="field">
                <label>观察人</label>
                <div class="static">{{ observerLabel }}</div>
              </div>
              <div class="field">
                <label>审核人</label>
                <div class="static">{{ selected.reviewer || '待审核' }}</div>
              </div>
            </div>
            <div v-if="canRecord" class="form-actions">
              <a-button @click="saveDraft">保存草稿</a-button>
              <a-button type="primary" @click="submitObs">提交观察</a-button>
            </div>
            <p v-else class="dim obs-perm-note">当前演示身份无观察录入权限（Analyst / Manager 可录入观察，QA / Manager 可审核）。</p>
          </template>

          <div v-if="selected" class="soe red">职责分离（SoD）：{{ SOD_NOTE }}</div>
        </div>
      </div>
    </div>

    <!-- 观察批选取弹窗 -->
    <a-modal
      v-model:open="selectModal.open"
      title="观察批选取"
      width="560"
      ok-text="提交选取"
      cancel-text="取消"
      @ok="submitSelect"
    >
      <div style="padding-top: 6px">
        <div class="field">
          <label>产品</label>
          <a-select v-model:value="selectModal.product" :options="productOptions" placeholder="选择留样产品" style="width: 100%" />
        </div>
        <div class="grid-2" style="gap: 10px; margin-bottom: 0">
          <div class="field">
            <label>年度</label>
            <a-select v-model:value="selectModal.year" :options="yearOptions" style="width: 100%" />
          </div>
          <div class="field">
            <label>批次（留样批号）</label>
            <a-input v-model:value="selectModal.batch" placeholder="如 T260901" />
          </div>
        </div>
        <div class="field">
          <label>原因</label>
          <a-radio-group v-model:value="selectModal.reason">
            <a-radio value="年度观察批">年度观察批</a-radio>
            <a-radio value="外售产品每批">外售产品每批</a-radio>
            <a-radio value="其他" :disabled="demo.role !== 'manager'">其他（Manager 专用）</a-radio>
          </a-radio-group>
          <p v-if="demo.role !== 'manager'" class="dim" style="margin-top: 4px">「其他」原因仅 Manager 可选：超出年度 N/3 上限的补选需 Manager 审批。</p>
          <p v-else-if="selectModal.reason === '其他'" class="soe blue">「其他」已选中：该原因将绕过年度 N/3 上限，由 Manager 审批后生效。</p>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { CalendarOutlined, PlusOutlined } from '@ant-design/icons-vue'
import DemoBar from '@/components/retention/DemoBar.vue'
import {
  can, demo, demoPerson, seedObsBoard, seedObsCompleteness, SOD_NOTE,
  type ObsBoardRow, type ObsCompleteness,
} from '@/demo/retentionDemo'

const TODAY = '2026-09-07'
const CURRENT_YEAR = 2026
const EXTRA_PRODUCT = 'TEST 成品片剂B' // 选取弹窗的任意候选产品（不在 N/3 统计清单内）
const OBSERVER_NAME = demoPerson('analyst') // 演示固定观察人（王敏）

type ObsFilter = 'all' | 'due' | 'done'
type ObsSelectReason = '年度观察批' | '外售产品每批' | '其他'

// ---------- 数据（演示副本） ----------
const rows = ref<ObsBoardRow[]>(seedObsBoard())
const completeness = ref<ObsCompleteness[]>(seedObsCompleteness())
const filter = ref<ObsFilter>('all')
const selected = ref<ObsBoardRow | null>(null)
const rightPanel = ref<HTMLElement | null>(null)

const draft = reactive({
  date: TODAY,
  appearance: '',
  result: '正常' as '正常' | '异常',
  anomaly: '',
})

const filterTabs: { key: ObsFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'due', label: '应观察' },
  { key: 'done', label: '已观察' },
]

const columns = [
  { title: '留样编号', key: 'name', dataIndex: 'name', width: 200 },
  { title: '产品 / 批号', key: 'sample', width: 175 },
  { title: '偏移月', key: 'offset', dataIndex: 'monthOffset', width: 70 },
  { title: '计划日期', key: 'plan', dataIndex: 'planDate', width: 100 },
  { title: '应观察状态', key: 'due', width: 120 },
  { title: '结果', key: 'result', width: 90 },
  { title: '操作', key: 'action', width: 80 },
]

// ---------- 角色能力 ----------
const canRecord = computed(() => can(demo.role, 'obs_record'))
const canReview = computed(() => can(demo.role, 'obs_review'))
const reviewerRoleLabel = computed(() => (demo.role === 'qa' ? 'QA' : demo.role === 'manager' ? 'Manager' : demo.role))
const observerLabel = `${OBSERVER_NAME}（Analyst）`

// ---------- 看板筛选 ----------
const boardRows = computed(() =>
  rows.value.filter((r) => {
    if (filter.value === 'due') return r.due !== '已完成'
    if (filter.value === 'done') return r.due === '已完成'
    return true
  }),
)

function rowActiveCls(r: ObsBoardRow): string {
  return selected.value?.name === r.name ? 'obs-row-active' : ''
}

function selectRow(r: ObsBoardRow) {
  if (selected.value?.name === r.name) return
  selected.value = r
  if (r.due !== '已完成') resetDraft()
}

function resetDraft() {
  draft.date = TODAY
  draft.appearance = ''
  draft.result = '正常'
  draft.anomaly = ''
}

// ---------- 完整性条 ----------
function complBarPct(c: ObsCompleteness): number {
  if (c.cap === null) return 100
  return Math.min(100, Math.round((c.selected / c.cap) * 100))
}
function complBarCls(c: ObsCompleteness): string {
  return c.cap !== null && c.selected < c.cap ? 'amber' : 'green'
}
function complPillCls(c: ObsCompleteness): string {
  return c.cap !== null && c.selected < c.cap ? 'pill-warn' : 'pill-pass'
}
function complPillText(c: ObsCompleteness): string {
  return c.cap !== null && c.selected < c.cap ? `可补选 ${c.cap - c.selected} 批` : '完整'
}

// ---------- 状态 pill / 日期工具 ----------
function duePillCls(d: ObsBoardRow['due']): string {
  if (d === '已完成') return 'pill-pass'
  if (d === '应观察') return 'pill-warn'
  return 'pill-danger'
}
function resultPillCls(r: string): string {
  return r === '正常' ? 'pill-pass' : 'pill-danger'
}
function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}
function daysBetween(from: string, to: string): number {
  const [fy, fm, fd] = from.split('-').map(Number)
  const [ty, tm, td] = to.split('-').map(Number)
  return Math.round((new Date(ty, tm - 1, td).getTime() - new Date(fy, fm - 1, fd).getTime()) / 86400000)
}
function overdueDays(planDate: string): number {
  return daysBetween(planDate, TODAY)
}
function addYears(day: string, n: number): string {
  const [y, m, d] = day.split('-').map(Number)
  const dt = new Date(y + n, m - 1, d)
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())}`
}
function windowEnd(planDate: string): string {
  return addYears(planDate, 3)
}

// ---------- 新增观察记录 / 提交 / 审核 ----------
function onAddRecord() {
  if (!canRecord.value) return
  const cur = selected.value
  if (!cur) {
    message.warning('请先在左侧计划看板选择一条「应观察 / 已逾期」记录')
    return
  }
  if (cur.due === '已完成') {
    message.warning('当前所选记录已观察完成，请改选「应观察 / 已逾期」行')
    return
  }
  resetDraft()
  message.info(`已就绪：录入 ${cur.name} 的观察记录`)
  nextTick(() => {
    rightPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

function saveDraft() {
  if (!selected.value || selected.value.due === '已完成') return
  message.info('观察记录已存为草稿（演示，不落库）')
}

function submitObs() {
  const r = selected.value
  if (!r || r.due === '已完成') return
  if (!draft.appearance.trim()) {
    message.warning('请填写外观性状')
    return
  }
  if (draft.result === '异常' && !draft.anomaly.trim()) {
    message.warning('结果异常时必须填写异常描述')
    return
  }
  const reviewer = canReview.value ? demoPerson() : '待审核'
  Object.assign(r, {
    due: '已完成' as const,
    result: draft.result,
    anomaly: draft.result === '异常' ? draft.anomaly.trim() : '',
    observedDate: draft.date || TODAY,
    observer: OBSERVER_NAME,
    reviewer,
  })
  rows.value = [...rows.value]
  message.success(`观察记录已提交：${r.name}（结果 ${draft.result}）`)
}

function reviewObs() {
  const r = selected.value
  if (!r || r.due !== '已完成' || r.reviewer !== '待审核') return
  r.reviewer = demoPerson()
  rows.value = [...rows.value]
  message.success('观察记录审核通过，已记审核人并锁定')
}

// ---------- 观察批选取弹窗 ----------
const yearOptions = [{ value: CURRENT_YEAR, label: `${CURRENT_YEAR} 年` }]
const productOptions = computed(() => {
  const names = completeness.value.map((c) => c.product)
  if (!names.includes(EXTRA_PRODUCT)) names.push(EXTRA_PRODUCT)
  return names.map((n) => ({ value: n, label: n }))
})
const selectModal = reactive({
  open: false,
  product: undefined as string | undefined,
  year: CURRENT_YEAR,
  batch: '',
  reason: '年度观察批' as ObsSelectReason,
})

function openSelectModal() {
  selectModal.product = completeness.value[0]?.product
  selectModal.year = CURRENT_YEAR
  selectModal.batch = ''
  selectModal.reason = '年度观察批'
  selectModal.open = true
}

function submitSelect() {
  const product = selectModal.product
  if (!product) {
    message.warning('请选择产品')
    return
  }
  if (!selectModal.batch.trim()) {
    message.warning('请填写批次号')
    return
  }
  const item = completeness.value.find((c) => c.product === product)
  if (item && item.cap !== null && item.selected >= item.cap) {
    message.error(`${product} ${selectModal.year} 年已达 N/3 上限（${item.selected}/${item.cap}），后端拦截本次选取并还原`)
    return
  }
  if (item) {
    item.selected += 1
    completeness.value = [...completeness.value]
  }
  message.success(`观察批选取已提交：${product} · ${selectModal.year} 年 · 批次 ${selectModal.batch} · 原因「${selectModal.reason}」`)
  selectModal.open = false
}
</script>

<style scoped>
.obs-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.obs-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
}
.chip-name { color: var(--ink); font-weight: 600; }
.chip-bar {
  width: 64px;
  height: 5px;
  background: #e7eeea;
  border-radius: 3px;
  overflow: hidden;
}
.chip-bar i { display: block; height: 100%; border-radius: 3px; }
.chip-bar i.green { background: var(--pass); }
.chip-bar i.amber { background: var(--warn); }
.chip-num { font-size: 12px; }

.obs-overdue {
  margin-top: 3px;
  font-size: 11px;
  color: var(--danger);
}

.head-filter { display: flex; gap: 6px; flex-wrap: wrap; }

.form-actions { display: flex; gap: 8px; }
.obs-perm-note { margin-top: 2px; }

.review-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: var(--info-soft);
  border: 1px solid #c3d9ef;
  border-radius: 6px;
  padding: 8px 10px;
  margin-top: 2px;
}

:deep(.obs-row-active) > td { background: var(--primary-soft); }
:deep(.obs-row-active:hover) > td { background: var(--primary-soft); }
</style>
