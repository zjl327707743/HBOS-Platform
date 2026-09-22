<template>
  <div class="page">
    <!-- 页头 -->
    <div class="page-head">
      <div>
        <h1>观察任务</h1>
        <p class="page-desc">年度外观性状观察 · 应观察清单、N/3 完整性、观察批选取 · 真实后端</p>
      </div>
      <div class="page-actions">
        <a-button @click="loadBoard()">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button
          :disabled="!canSelect"
          :title="canSelect ? '' : '当前会话角色不可选取观察批（需 LIMS Reviewer / Manager）'"
          @click="openSelectModal"
        >
          <template #icon><CalendarOutlined /></template>
          观察批选取
        </a-button>
        <a-button
          type="primary"
          :disabled="!canRecordTodo"
          :title="recordBtnHint"
          @click="quickStartRecord"
        >
          <template #icon><PlusOutlined /></template>
          录入观察
        </a-button>
      </div>
    </div>
    <a-alert
      v-if="targetSampleName"
      :type="targetSampleMissing || targetObservationMissing ? 'warning' : 'info'"
      show-icon
      :message="targetSampleMissing ? `来源留样 ${targetSampleName} 未找到` : (targetObservationMissing ? `留样 ${targetSampleName} 已打开，但观察记录 ${targetObservationName} 未找到` : `已定位留样 ${targetSampleName}${targetObservationName ? ` · 观察 ${targetObservationName}` : ''}`)"
      style="margin-bottom: 12px"
    />

    <!-- 真实后端说明条 -->
    <a-alert
      type="info"
      show-icon
      message="已接入真实后端 · 观察录入/审核受会话角色与后端校验约束"
      style="margin-bottom: 14px"
    />

    <!-- 完整性条 -->
    <div class="obs-strip" v-if="completeness.length">
      <div class="obs-chip" v-for="c in completeness" :key="`${c.product}-${c.year}`">
        <span class="chip-name">{{ c.product }} · {{ c.year }}</span>
        <span class="chip-bar"><i :class="complBarCls(c)" :style="{ width: complBarPct(c) + '%' }"></i></span>
        <span class="chip-num mono">{{ c.cap !== null ? `${c.selected}/${c.cap}` : '每批' }}</span>
        <span class="pill" :class="complPillCls(c)">{{ complPillText(c) }}</span>
      </div>
    </div>
    <div v-else class="dim obs-strip-empty">暂无已选观察批（在「观察批选取」中纳入留样后此处显示各产品年度完整性）</div>

    <div class="detail-layout">
      <!-- 左：计划看板 -->
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">计划看板</div>
            <div class="panel-sub">单击行载入右侧观察记录 · 待办优先，已逾期标红</div>
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
            :loading="loading"
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
                {{ record.product }}
                <span class="dim" v-if="record.batch">/ {{ record.batch }}</span>
              </template>
              <template v-else-if="column.key === 'offset'">
                <span class="mono">{{ record.monthOffset ?? '—' }}</span>
              </template>
              <template v-else-if="column.key === 'plan'">
                <span class="mono">{{ record.planDate || '—' }}</span>
              </template>
              <template v-else-if="column.key === 'due'">
                <span class="pill" :class="duePillCls(record.due)">{{ record.due }}</span>
                <div v-if="record.due === '已逾期' && record.planDate" class="obs-overdue">
                  已逾期 {{ overDays(record.planDate) }} 天
                </div>
              </template>
              <template v-else-if="column.key === 'result'">
                <span v-if="record.result" class="pill" :class="resultPillCls(record.result)">{{ record.result }}</span>
                <span v-else class="dim">—</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-button type="link" size="small" @click="selectRow(record)">{{ actionText(record.due) }}</a-button>
              </template>
            </template>
          </a-table>
          <a-empty
            v-if="!loading && !rows.length"
            description="暂无观察计划：留样登记时勾选观察样品，或用「观察批选取」将留样纳入计划"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
            style="padding: 24px 0"
          />
        </div>
      </div>

      <!-- 右：观察记录 / 录入面板 -->
      <div ref="rightPanel" class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">观察记录</div>
            <div class="panel-sub" v-if="selected">
              <span class="mono">{{ selected.name }}</span> · {{ selected.product }}
              <span v-if="selected.batch" class="dim">/ {{ selected.batch }}</span>
            </div>
            <div class="panel-sub" v-else>未选择观察批次</div>
          </div>
          <span v-if="selected" class="pill" :class="duePillCls(selected.due)">{{ selected.due }}</span>
        </div>
        <div class="panel-body">
          <a-empty
            v-if="!selected"
            description="从左侧计划看板选择一行后查看 / 录入观察记录"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
          />

          <!-- 待办（应观察 / 已逾期）：录入表单 -->
          <template v-else-if="isTodo(selected)">
            <div class="field">
              <label>观察时间窗</label>
              <div class="static">
                计划日期 <span class="mono">{{ selected.planDate || '—' }}</span>
                <span v-if="selected.due === '已逾期'" class="dim warn-text"> · 已逾期，请尽快观察</span>
              </div>
            </div>
            <div class="field">
              <label>实际观察日期</label>
              <a-date-picker
                v-model:value="draft.date"
                value-format="YYYY-MM-DD"
                style="width: 100%"
                :disabled="!canRecord"
              />
            </div>
            <div class="field">
              <label>外观性状</label>
              <a-input
                v-model:value="draft.appearance"
                placeholder="如 白色至类白色片剂，外观完整"
                :disabled="!canRecord"
              />
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
              <a-textarea
                v-model:value="draft.anomaly"
                :rows="3"
                placeholder="填写异常表现与报告对象"
                :disabled="!canRecord"
              />
            </div>

            <div class="form-actions">
              <a-button type="primary" :disabled="!canRecord" :loading="submitting" @click="submitObs">
                提交观察
              </a-button>
              <a-popconfirm
                title="确认取消该留样的观察批选取？"
                ok-text="确认取消"
                cancel-text="保留"
                @confirm="cancelSelection"
              >
                <a-button danger size="small" :disabled="!canCancel">取消选取</a-button>
              </a-popconfirm>
            </div>
            <p v-if="!canRecord" class="dim obs-perm-note">
              当前会话角色不可录入观察记录（Analyst / Reviewer / Manager 可录入）。
            </p>
            <p v-else class="dim obs-perm-note">
              提交后进入「待审核」，由 Reviewer / QA / Manager 审核通过后锁定并排入下一观察期。
            </p>
          </template>

          <!-- 待审核：只读展示 + 审核 -->
          <template v-else-if="selected.due === '待审核'">
            <a-spin :spinning="historyLoading">
              <template v-if="currentRecord">
                <div class="grid-2" style="gap: 10px; margin-bottom: 0">
                  <div class="field">
                    <label>实际观察日期</label>
                    <div class="static mono">{{ currentRecord.obs_date || '—' }}</div>
                  </div>
                  <div class="field">
                    <label>观察结果</label>
                    <div class="static" style="padding-top: 6px; padding-bottom: 6px">
                      <span v-if="currentRecord.result" class="pill" :class="resultPillCls(currentRecord.result)">
                        {{ currentRecord.result }}
                      </span>
                      <span v-else class="dim">—</span>
                    </div>
                  </div>
                </div>
                <div class="grid-2" style="gap: 10px; margin-bottom: 0">
                  <div class="field">
                    <label>观察人</label>
                    <div class="static">{{ currentRecord.observer || '—' }}</div>
                  </div>
                  <div class="field">
                    <label>审核人</label>
                    <div class="static">待审核</div>
                  </div>
                </div>
                <div v-if="currentRecord.appearance" class="field">
                  <label>外观性状</label>
                  <div class="static">{{ currentRecord.appearance }}</div>
                </div>
                <div v-if="currentRecord.result === '异常'" class="field">
                  <label>异常描述</label>
                  <div class="static">{{ currentRecord.abnormal_note || '—' }}</div>
                  <p class="dim obs-perm-note">异常结论的异常描述由录入人填写，审核时不可修改。</p>
                </div>
              </template>
              <a-empty v-else description="暂无该观察期记录" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </a-spin>

            <div v-if="currentRecord && !currentRecord.reviewed_by" class="review-zone">
              <span class="dim" v-if="canReview">
                当前会话角色可审核该条观察记录
              </span>
              <span class="dim" v-else>
                当前会话角色不可审核（Reviewer / QA / Manager 可审核）
              </span>
              <a-button type="primary" size="small" :disabled="!canReview" :loading="reviewing" @click="reviewObs">
                审核通过
              </a-button>
            </div>
          </template>

          <!-- 已完成 / 计划完成：只读摘要 + 全部观察记录 -->
          <template v-else>
            <template v-if="selected.due === '已完成'">
              <a-spin :spinning="historyLoading">
                <template v-if="currentRecord">
                  <div class="grid-2" style="gap: 10px; margin-bottom: 0">
                    <div class="field">
                      <label>实际观察日期</label>
                      <div class="static mono">{{ currentRecord.obs_date || '—' }}</div>
                    </div>
                    <div class="field">
                      <label>观察结果</label>
                      <div class="static" style="padding-top: 6px; padding-bottom: 6px">
                        <span v-if="currentRecord.result" class="pill" :class="resultPillCls(currentRecord.result)">
                          {{ currentRecord.result }}
                        </span>
                        <span v-else class="dim">—</span>
                      </div>
                    </div>
                  </div>
                  <div class="grid-2" style="gap: 10px; margin-bottom: 0">
                    <div class="field">
                      <label>观察人</label>
                      <div class="static">{{ currentRecord.observer || '—' }}</div>
                    </div>
                    <div class="field">
                      <label>审核人</label>
                      <div class="static">
                        {{ currentRecord.reviewed_by || '待审核' }}
                        <span v-if="currentRecord.reviewed_by && currentRecord.reviewed_date" class="dim">
                          （{{ currentRecord.reviewed_date }}）
                        </span>
                      </div>
                    </div>
                  </div>
                  <div v-if="currentRecord.appearance" class="field">
                    <label>外观性状</label>
                    <div class="static">{{ currentRecord.appearance }}</div>
                  </div>
                  <div v-if="currentRecord.result === '异常'" class="field">
                    <label>异常描述</label>
                    <div class="static">{{ currentRecord.abnormal_note || '—' }}</div>
                  </div>
                </template>
              </a-spin>
            </template>
            <template v-else-if="selected.due === '计划完成'">
              <div class="field">
                <label>计划说明</label>
                <div class="static">
                  该留样的年度观察已覆盖至留样期至，计划完成，无新增观察任务。
                </div>
              </div>
            </template>

            <div v-if="history.length" class="obs-history">
              <div class="section-label">该留样全部观察记录（只读）</div>
              <div class="mini-list">
                <div class="mini-row" v-for="h in history" :key="h.name">
                  <div class="mini-main">
                    <div class="mini-title">
                      <span class="pill" :class="resultPillCls(h.result || '')">{{ h.result || '—' }}</span>
                      <span class="mono">{{ h.name }}</span>
                    </div>
                    <div class="mini-sub">
                      观察月 <span class="mono">{{ h.obs_month }}</span>
                      <span v-if="h.obs_date"> · {{ h.obs_date }}</span>
                      <span v-if="h.observer"> · 观察人 {{ h.observer }}</span>
                      <span v-if="h.reviewed_by"> · 审核人 {{ h.reviewed_by }}</span>
                    </div>
                    <div v-if="h.appearance" class="mini-sub">外观：{{ h.appearance }}</div>
                    <div v-if="h.abnormal_note" class="mini-sub danger-text">异常描述：{{ h.abnormal_note }}</div>
                  </div>
                </div>
              </div>
            </div>
            <a-empty
              v-else-if="!historyLoading"
              description="暂无观察记录"
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
            />
          </template>

          <div v-if="selected" class="soe red">{{ SOD_NOTE }}</div>
        </div>
      </div>
    </div>

    <!-- 观察批选取弹窗 -->
    <a-modal
      v-model:open="modal.open"
      title="观察批选取"
      width="580"
      ok-text="提交选取"
      cancel-text="取消"
      :confirm-loading="submitting"
      @ok="submitSelect"
    >
      <div style="padding-top: 6px">
        <div class="field">
          <label>产品</label>
          <a-select
            v-model:value="modal.product"
            :options="candidateProductOptions"
            placeholder="选择留样产品"
            style="width: 100%"
            @change="onModalProductChange"
          />
        </div>
        <div class="grid-2" style="gap: 10px; margin-bottom: 0">
          <div class="field">
            <label>观察年度</label>
            <a-select v-model:value="modal.year" :options="yearOptions" style="width: 100%" />
          </div>
          <div class="field">
            <label>完整性</label>
            <div class="static" style="padding-top: 6px; padding-bottom: 6px">
              <span v-if="modalCompleteness" class="pill" :class="complPillCls(modalCompleteness)">
                {{ complPillText(modalCompleteness) }}
              </span>
              <span v-if="modalCompleteness && modalCompleteness.cap !== null" class="chip-num mono" style="margin-left: 6px">
                {{ modalCompleteness.selected }}/{{ modalCompleteness.cap }}
              </span>
              <span v-if="modalCompleteness && modalCompleteness.cap === null" class="dim" style="margin-left: 6px">每批观察</span>
              <span v-if="!modalCompleteness" class="dim">—</span>
            </div>
          </div>
        </div>
        <div class="field">
          <label>批次选择（在库 / 部分使用且未纳入观察的候选留样）</label>
          <a-radio-group v-model:value="modal.name" class="cand-group">
            <div class="cand-row" v-for="c in modalCandidates" :key="c.retention_name">
              <a-radio :value="c.retention_name">
                <span class="mono">{{ c.batch_no }}</span>
                <span class="dim"> {{ c.sample_name }} · 留样 {{ c.retention_date }}</span>
              </a-radio>
            </div>
          </a-radio-group>
          <a-empty
            v-if="!modalCandidates.length"
            description="该产品暂无候选留样"
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
            style="margin: 8px 0"
          />
        </div>
        <div class="field">
          <label>选取原因</label>
          <a-radio-group v-model:value="modal.reason">
            <a-radio value="年度观察批（每年 3 批）">年度观察批（每年 3 批）</a-radio>
            <a-radio value="外售产品每批">外售产品每批</a-radio>
            <a-radio value="其他" :disabled="!isManager">其他</a-radio>
          </a-radio-group>
          <p v-if="!isManager" class="dim" style="margin-top: 4px">
            「其他」原因仅 Manager 可选：用于超出年度 N/3 上限等特殊补选。
          </p>
          <p v-else-if="modal.reason === '其他'" class="soe blue">
            「其他」已选中：该原因将绕过年度 N/3 上限（后端对 Manager 校验后放行）。
          </p>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { CalendarOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useRoute } from 'vue-router'
import {
  obsPlan, selectObsBatch, cancelObsBatch, recordObservation, reviewObservation,
  canAction, SOD_NOTE,
  type ObsBoardRow, type ObsCompleteness,
} from '@/api/retention'
import { listDoctype, getDoc } from '@/api/lims'
import { readScalarQuery } from '@/features/todos/todoModel'

// ---------- 类型 ----------
type ObsFilter = 'all' | 'todo' | 'done'

interface ObsRecord {
  name: string
  obs_month: number
  obs_date?: string
  appearance?: string
  result?: string
  abnormal_note?: string
  observer?: string
  reviewed_by?: string
  reviewed_date?: string
}

interface Candidate {
  retention_name: string
  sample_name: string
  batch_no: string
  retention_date: string
  product_name: string
}

// ---------- 常量 ----------
const REASON_ANNUAL = '年度观察批（每年 3 批）'
const REASON_SALE = '外售产品每批'
const CURRENT_YEAR = new Date().getFullYear()

function todayStr(): string {
  const d = new Date()
  const mm = `${d.getMonth() + 1}`.padStart(2, '0')
  const dd = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

// ---------- 会话角色 ----------
const auth = useAuthStore()
const route = useRoute()
const canKey = (action: string): boolean => canAction(auth.user?.roles, action)
const canSelect = computed(() => canKey('select_obs_batch'))
const canCancel = computed(() => canKey('cancel_obs_batch'))
const canRecord = computed(() => canKey('record_observation'))
const canReview = computed(() => canKey('review_observation'))
const isManager = computed(() => {
  const roles = auth.user?.roles ?? []
  return roles.includes('LIMS Manager') || roles.includes('System Manager')
})

// ---------- 数据 ----------
const rows = ref<ObsBoardRow[]>([])
const completeness = ref<ObsCompleteness[]>([])
const loading = ref(false)
const filter = ref<ObsFilter>('all')
const selected = ref<ObsBoardRow | null>(null)
const targetSampleName = ref('')
const targetObservationName = ref('')
const targetSampleMissing = ref(false)
const targetObservationMissing = ref(false)
const rightPanel = ref<HTMLElement | null>(null)
const history = ref<ObsRecord[]>([])
const historyLoading = ref(false)
let historyReq = 0

const draft = reactive({
  date: todayStr(),
  appearance: '',
  result: '正常' as '正常' | '异常',
  anomaly: '',
})
const submitting = ref(false)
const reviewing = ref(false)

const filterTabs: { key: ObsFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'todo', label: '待办' },
  { key: 'done', label: '已完成' },
]

const columns = [
  { title: '留样编号', key: 'name', dataIndex: 'name', width: 190 },
  { title: '产品 / 批号', key: 'sample', width: 210 },
  { title: '偏移月', key: 'offset', width: 80 },
  { title: '计划日期', key: 'plan', width: 110 },
  { title: '应观察状态', key: 'due', width: 110 },
  { title: '结果', key: 'result', width: 90 },
  { title: '操作', key: 'action', width: 90 },
]

// ---------- 看板筛选 / 工具 ----------
const boardRows = computed(() => {
  if (filter.value === 'todo') return rows.value.filter((r) => r.due !== '已完成' && r.due !== '计划完成')
  if (filter.value === 'done') return rows.value.filter((r) => r.due === '已完成' || r.due === '计划完成')
  return rows.value
})

function isTodo(r: ObsBoardRow): boolean {
  return r.due === '应观察' || r.due === '已逾期'
}

function actionText(due: string): string {
  if (due === '待审核') return '审核'
  if (due === '已完成' || due === '计划完成') return '查看'
  return '录入'
}

function rowActiveCls(r: ObsBoardRow): string {
  return selected.value?.name === r.name ? 'obs-row-active' : ''
}

function duePillCls(due: string): string {
  if (due === '已完成') return 'pill-pass'
  if (due === '待审核' || due === '应观察') return 'pill-warn'
  if (due === '已逾期') return 'pill-danger'
  return 'pill-muted'
}

function resultPillCls(result: string): string {
  return result === '正常' ? 'pill-pass' : 'pill-danger'
}

function overDays(dateStr: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000))
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

// ---------- 计划加载 ----------
async function loadBoard(prefer?: string | null) {
  loading.value = true
  try {
    const plan = await obsPlan()
    rows.value = plan.rows
    completeness.value = plan.completeness
    targetSampleName.value = readScalarQuery(route.query.sample) || ''
    targetObservationName.value = readScalarQuery(route.query.observation) || ''
    targetSampleMissing.value = false
    targetObservationMissing.value = false
    const keepName = prefer !== undefined ? prefer : (targetSampleName.value || selected.value?.name || null)
    const next = keepName ? rows.value.find((x) => x.name === keepName) ?? null : null
    selected.value = next
    targetSampleMissing.value = Boolean(targetSampleName.value && !next)
    if (next) {
      await loadHistory(next)
      targetObservationMissing.value = Boolean(
        targetObservationName.value && !history.value.some((record) => record.name === targetObservationName.value),
      )
    }
    else history.value = []
  } catch {
    // 后端错误 / 未登录提示由 axios 拦截器统一弹出
  } finally {
    loading.value = false
  }
}

async function selectRow(r: ObsBoardRow) {
  if (selected.value?.name === r.name) return
  selected.value = r
  if (isTodo(r)) resetDraft()
  await loadHistory(r)
}

async function loadHistory(r: ObsBoardRow) {
  const req = ++historyReq
  historyLoading.value = true
  try {
    const list = await listDoctype<ObsRecord>(
      'HBOS Retention Observation',
      ['name', 'obs_month', 'obs_date', 'appearance', 'result', 'abnormal_note', 'observer', 'reviewed_by', 'reviewed_date'],
      { retention_sample: r.name },
      0,
      'obs_month asc',
    )
    if (req !== historyReq) return
    history.value = list
  } catch {
    if (req === historyReq) history.value = []
  } finally {
    if (req === historyReq) historyLoading.value = false
  }
}

const currentRecord = computed<ObsRecord | null>(() => {
  const r = selected.value
  if (!r || r.monthOffset === null || r.monthOffset === undefined) return null
  const m = Number(r.monthOffset)
  return history.value.find((h) => Number(h.obs_month) === m) ?? null
})

function resetDraft() {
  draft.date = todayStr()
  draft.appearance = ''
  draft.result = '正常'
  draft.anomaly = ''
}

// ---------- 录入 / 审核 / 取消 ----------
const canRecordTodo = computed(() =>
  !!selected.value && isTodo(selected.value) && canRecord.value,
)
const recordBtnHint = computed(() => {
  if (!selected.value || !isTodo(selected.value)) return '请先在左侧选择「应观察 / 已逾期」行'
  if (!canRecord.value) return '当前会话角色不可录入观察记录（Analyst / Reviewer / Manager 可录入）'
  return ''
})

function quickStartRecord() {
  const r = selected.value
  if (!r || !isTodo(r)) {
    message.warning('请先在左侧计划看板选择一条「应观察 / 已逾期」待办')
    return
  }
  if (!canRecord.value) return
  resetDraft()
  message.info(`已就绪：录入 ${r.name} 的观察记录`)
  rightPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function submitObs() {
  const r = selected.value
  if (!r || !isTodo(r) || r.monthOffset === null || r.monthOffset === undefined) return
  if (!draft.appearance.trim()) {
    message.warning('请填写外观性状')
    return
  }
  if (draft.result === '异常' && !draft.anomaly.trim()) {
    message.warning('结果异常时必须填写异常描述')
    return
  }
  submitting.value = true
  try {
    await recordObservation({
      retention_name: r.name,
      obs_month: Number(r.monthOffset),
      obs_date: draft.date || todayStr(),
      appearance: draft.appearance.trim(),
      result: draft.result,
      abnormal_note: draft.result === '异常' ? draft.anomaly.trim() : undefined,
    })
    message.success(`观察记录已录入：${r.name}（${draft.result}），待审核`)
    resetDraft()
    await loadBoard(r.name)
  } catch {
    // 后端校验错误由 axios 拦截器提示
  } finally {
    submitting.value = false
  }
}

async function reviewObs() {
  const r = selected.value
  if (!r || r.due !== '待审核' || r.monthOffset === null || r.monthOffset === undefined) return
  reviewing.value = true
  try {
    await reviewObservation(r.name, Number(r.monthOffset))
    message.success(`观察记录审核通过：${r.name}（观察月 ${r.monthOffset}），已锁定并排入下一观察期`)
    selected.value = null
    await loadBoard()
  } catch {
    // 后端校验错误由 axios 拦截器提示
  } finally {
    reviewing.value = false
  }
}

async function cancelSelection() {
  const r = selected.value
  if (!r) return
  if (!canCancel.value) return
  try {
    await cancelObsBatch(r.name)
    message.success(`已取消「${r.name}」观察批选取，该留样退出观察计划`)
    selected.value = null
    await loadBoard()
  } catch {
    // 已产生观察记录时后端会拒绝取消
  }
}

// ---------- 观察批选取弹窗 ----------
const candidates = ref<Candidate[]>([])
const productRules = ref<Record<string, string>>({})
const yearOptions = [{ value: CURRENT_YEAR, label: `${CURRENT_YEAR} 年` }]
const modal = reactive({
  open: false,
  product: '',
  year: CURRENT_YEAR,
  reason: REASON_ANNUAL as string,
  name: '',
})

const candidateProductOptions = computed(() => {
  const seen = new Set<string>()
  const opts: { value: string; label: string }[] = []
  for (const c of candidates.value) {
    if (!seen.has(c.product_name)) {
      seen.add(c.product_name)
      opts.push({ value: c.product_name, label: c.product_name })
    }
  }
  return opts
})

const modalCandidates = computed(() =>
  candidates.value.filter((c) => c.product_name === modal.product),
)

const modalCompleteness = computed<ObsCompleteness | null>(() => {
  const hit = completeness.value.find((c) => c.product === modal.product && c.year === modal.year)
  if (hit) return hit
  const rule = productRules.value[modal.product]
  if (rule === '每年选 3 批（原料药成品）') {
    return { product: modal.product, rule: '年度观察批', year: modal.year, selected: 0, cap: 3 }
  }
  if (rule === '每批观察（外售产品）') {
    return { product: modal.product, rule: '每批观察', year: modal.year, selected: 0, cap: null }
  }
  return null
})

function applyReasonForProduct(productName: string) {
  const rule = productRules.value[productName]
  if (rule === '每年选 3 批（原料药成品）') modal.reason = REASON_ANNUAL
  else if (rule === '每批观察（外售产品）') modal.reason = REASON_SALE
  else modal.reason = REASON_ANNUAL
}

async function loadCandidates(): Promise<Candidate[]> {
  const metaCache = new Map<string, { product_name: string; obs_rule: string }>()
  const samples = await listDoctype<Record<string, unknown>>(
    'HBOS Retention Sample',
    ['*'],
    { observed_flag: 0, status: ['in', ['在库', '部分使用']] },
    0,
    'retention_date desc',
  )
  const out: Candidate[] = []
  for (const s of samples) {
    const pid = String(s.retention_product || '')
    if (!pid) continue
    let meta = metaCache.get(pid)
    if (!meta) {
      const product = await getDoc<{ product_name: string; obs_rule: string }>('HBOS Retention Product', pid)
      meta = { product_name: product.product_name || '', obs_rule: product.obs_rule || '' }
      metaCache.set(pid, meta)
    }
    if (meta.obs_rule === '不观察') continue
    out.push({
      retention_name: String(s.name || ''),
      sample_name: String(s.sample_name || ''),
      batch_no: String(s.batch_no || ''),
      retention_date: String(s.retention_date || ''),
      product_name: meta.product_name,
    })
    productRules.value[meta.product_name] = meta.obs_rule
  }
  return out
}

async function openSelectModal() {
  if (!canSelect.value) return
  submitting.value = false
  try {
    candidates.value = await loadCandidates()
  } catch {
    return
  }
  if (!candidates.value.length) {
    message.info('暂无候选留样：请先在「留样登记」登记在库留样（状态 在库/部分使用、未纳入观察），或在「留样产品」页维护观察规则')
    return
  }
  const first = candidates.value[0]
  modal.product = first.product_name
  modal.name = first.retention_name
  modal.year = CURRENT_YEAR
  applyReasonForProduct(modal.product)
  modal.open = true
}

function onModalProductChange() {
  if (!modalCandidates.value.some((c) => c.retention_name === modal.name)) {
    modal.name = modalCandidates.value[0]?.retention_name ?? ''
  }
  applyReasonForProduct(modal.product)
}

async function submitSelect() {
  if (!modal.name) {
    message.warning('请选择要纳入观察计划的批次')
    return
  }
  const compl = modalCompleteness.value
  const rule = productRules.value[modal.product]
  if (modal.reason === REASON_ANNUAL && rule && rule !== '每年选 3 批（原料药成品）') {
    message.warning('「年度观察批（每年 3 批）」仅适用于观察规则为每年选 3 批的产品')
    return
  }
  if (modal.reason === REASON_SALE && rule && rule !== '每批观察（外售产品）') {
    message.warning('「外售产品每批」仅适用于每批观察的外售产品')
    return
  }
  if (
    modal.reason === REASON_ANNUAL
    && compl && compl.cap !== null && compl.selected >= compl.cap
  ) {
    message.warning(`${modal.product} ${modal.year} 年年度观察批已达上限 ${compl.cap} 批（${compl.selected}/${compl.cap}），如需补选请由 Manager 用「其他」原因操作`)
    return
  }
  const cand = candidates.value.find((c) => c.retention_name === modal.name)
  submitting.value = true
  try {
    await selectObsBatch(modal.name, modal.year, modal.reason)
    message.success(`观察批选取成功：${modal.product} · ${modal.year} 年 · 批号 ${cand?.batch_no || modal.name} · ${modal.reason}`)
    modal.open = false
    await loadBoard()
  } catch {
    // 后端校验错误由 axios 拦截器提示
  } finally {
    submitting.value = false
  }
}

void loadBoard()
</script>

<style scoped>
.obs-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.obs-strip-empty {
  margin-bottom: 14px;
  font-size: 12px;
}
.obs-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: var(--surface);
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

.form-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.obs-perm-note { margin-top: 4px; }

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

.obs-history { margin-top: 4px; }
.obs-history .mini-sub.danger-text { color: var(--danger); }

.cand-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 240px;
  overflow: auto;
  padding-right: 4px;
}
.cand-row {
  display: flex;
  align-items: center;
  padding: 5px 6px;
  border: 1px solid var(--line);
  border-radius: 6px;
  margin-bottom: 6px;
}
.cand-row:hover { background: var(--surface-2); }

.mono { font-family: var(--mono); font-size: 12px; }

:deep(.obs-row-active) > td { background: var(--primary-soft); }
:deep(.obs-row-active:hover) > td { background: var(--primary-soft); }
</style>
