<template>
  <div class="page">
    <StbGateBanner
      mode="live"
      note="时间点、计划日期、延期审批与逾期派生均来自 hb_lims_app 稳定性业务服务（R8B）；逾期为派生标识，不改单据状态。"
    />

    <div class="page-head">
      <div>
        <h1>取样与检测计划</h1>
        <p class="page-desc">按时间点管理计划日、实际日、有效截止日和延期审批</p>
      </div>
      <div class="page-actions">
        <a-button :disabled="!can('apply_delay')" @click="delayRef?.show()">
          <template #icon><CalendarOutlined /></template>
          申请延期
        </a-button>
        <a-button type="primary" :disabled="!can('generate_timepoints')" @click="generateOpen = true">
          <template #icon><PlusOutlined /></template>
          生成时间点
        </a-button>
      </div>
    </div>

    <div class="stb-subnav">
      <button :class="{ active: tab === 'board' }" @click="switchTab('board')">月度看板</button>
      <button :class="{ active: tab === 'ledger' }" @click="switchTab('ledger')">计划台账</button>
      <button :class="{ active: tab === 'delay' }" @click="switchTab('delay')">延期审批</button>
    </div>
    <a-alert
      v-if="targetTimepoint"
      :type="targetTimepointMissing ? 'warning' : 'info'"
      show-icon
      :message="targetTimepointMissing ? `来源时间点 ${targetTimepoint} 未找到` : `已定位时间点 ${targetTimepoint}`"
      style="margin-bottom: 12px"
    />

    <!-- 月度看板 -->
    <template v-if="tab === 'board'">
      <div class="filter-bar">
        <a-select v-model:value="conditionFilter" :options="conditionOptions" style="width: 160px" />
        <a-select v-model:value="stateFilter" :options="stateOptions" style="width: 170px" />
        <span class="dim" style="margin-left: auto">看板按计划取样日排布 · 截止日不随取样延期自动顺延</span>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">{{ monthLabel }} 时间点看板</div>
            <div class="panel-sub">共 {{ monthRows.length }} 个计划取样时间点落在本月</div>
          </div>
          <div class="month-switch">
            <a-button size="small" @click="shiftMonth(-1)">
              <template #icon><ArrowLeftOutlined /></template>
            </a-button>
            <span class="month-title">{{ monthLabel }}</span>
            <a-button size="small" @click="shiftMonth(1)">
              <template #icon><ArrowRightOutlined /></template>
            </a-button>
          </div>
        </div>
        <div class="panel-body">
          <a-spin :spinning="loading">
            <a-empty v-if="!boardRows.length" description="本月无计划取样时间点" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            <div v-else class="stb-plan-board">
              <div class="stb-plan-grid" :style="{ gridTemplateColumns: `160px repeat(${dayHeaders.length}, 26px)` }">
                <div class="head">产品 / 条件</div>
                <div v-for="d in dayHeaders" :key="d.key" class="head">{{ d.day }}</div>
                <template v-for="row in boardRows" :key="row.key">
                  <div class="row-label">
                    <b>{{ row.product_name || '—' }}</b>
                    <span>{{ row.condition_type }} · {{ row.batch_no }}</span>
                  </div>
                  <div
                    v-for="d in dayHeaders"
                    :key="d.key"
                    class="stb-plan-cell"
                    :class="{ 'has-dot': !!row.cells[d.key], warn: row.tone[d.key] === 'warn', danger: row.tone[d.key] === 'danger' }"
                    @click="row.item[d.key] && selectTimepoint(row.item[d.key])"
                  >
                    <span v-if="row.cells[d.key]" class="tiny">{{ row.cells[d.key] }}</span>
                  </div>
                </template>
              </div>
            </div>
          </a-spin>
          <div class="stb-plan-legend">
            <span><i style="background: var(--primary)"></i>正常时间点</span>
            <span><i style="background: var(--warn)"></i>临近计划日</span>
            <span><i style="background: var(--danger)"></i>逾期 / 延期</span>
            <span>点击节点查看日期链</span>
          </div>
        </div>
      </div>

      <div class="grid-2" style="margin-top: 16px">
        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">时间点日期链</div>
              <div class="panel-sub">{{ tpDetail ? `${tpDetail.product_name} · ${tpDetail.time_point_label}` : '点击看板或台账中的节点查看' }}</div>
            </div>
            <span v-if="tpDetail" :class="toneClass(statusTone(tpDetail.status))">{{ tpDetail.status }}</span>
          </div>
          <div class="panel-body">
            <a-empty v-if="!tpDetail" description="未选择时间点" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            <template v-else>
              <div class="stb-kv-grid">
                <div class="stb-kv"><label>计划取样日</label><b class="mono">{{ tpDetail.plan_sample_date || '—' }}</b></div>
                <div class="stb-kv"><label>实际取样日</label><b class="mono">{{ tpDetail.actual_sample_date || '未登记' }}</b></div>
                <div class="stb-kv"><label>取样有效截止</label><b class="mono">{{ tpDetail.effective_sample_due || '—' }}</b></div>
                <div class="stb-kv"><label>取样政策上限</label><b class="mono dim">{{ tpDetail.policy_latest_sample_due || '—' }}</b></div>
                <div class="stb-kv"><label>计划检测日</label><b class="mono">{{ tpDetail.plan_test_date || '—' }}</b></div>
                <div class="stb-kv"><label>检测有效截止</label><b class="mono">{{ tpDetail.effective_test_due || '—' }}</b></div>
                <div class="stb-kv"><label>检测政策上限</label><b class="mono dim">{{ tpDetail.policy_latest_test_due || '—' }}</b></div>
                <div class="stb-kv"><label>取样延期上限</label><b class="mono">{{ tpDetail.delay_limit_days ?? 0 }} 天</b></div>
              </div>
              <div class="stb-notice">
                日期链不变式：planned ≤ requested ≤ approved ≤ policy_latest。检测 30 天窗口锚定计划检测日期，不随取样延期顺延。
              </div>
              <div v-if="tpDetail.delays.length" style="margin-top: 12px">
                <h3 style="font-size: 12px; font-weight: 700; margin-bottom: 6px">延期历史</h3>
                <div v-for="(d, i) in tpDetail.delays" :key="i" class="stb-audit-line">
                  <span class="stb-audit-dot" :class="d.status === '已批准' ? '' : (d.status === '已驳回' ? 'red' : 'amber')"></span>
                  <div>
                    <strong>{{ d.delay_type }} · {{ d.status }}</strong>
                    <span>
                      计划 {{ d.planned_due_date }} → 申请 {{ d.requested_due_date }}
                      {{ d.approved_due_date ? '→ 批准 ' + d.approved_due_date : '' }}
                      · 上限 {{ d.policy_latest_due_date }}
                    </span>
                    <span>{{ d.apply_by }} · {{ d.apply_date }}{{ d.reason ? ' · ' + d.reason : '' }}</span>
                  </div>
                </div>
              </div>
              <a-space wrap style="margin-top: 12px">
                <a-button v-for="a in tpActions" :key="a.action" size="small"
                          :type="a.primary ? 'primary' : 'default'" :danger="a.danger"
                          @click="runTpAction(a)">
                  {{ a.label }}
                </a-button>
                <span v-if="!tpActions.length" class="dim">当前状态 / 角色下无可执行动作</span>
              </a-space>
            </template>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">本周到期清单</div>
              <div class="panel-sub">按有效截止日 ≤ 7 天</div>
            </div>
          </div>
          <div class="panel-body no-pad">
            <a-table
              :columns="dueColumns"
              :data-source="weekDue"
              size="small"
              row-key="name"
              :pagination="false"
              :scroll="{ x: 460 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'point'"><span class="mono">{{ record.time_point_label }}</span></template>
                <template v-else-if="column.key === 'due'"><span class="mono">{{ record.due }}</span></template>
                <template v-else-if="column.key === 'status'">
                  <span :class="toneClass(record.tone)">{{ record.state }}</span>
                </template>
              </template>
            </a-table>
            <a-empty v-if="!weekDue.length" description="近 7 天无到期时间点" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 30px 0" />
          </div>
        </div>
      </div>
    </template>

    <!-- 计划台账 -->
    <div v-else-if="tab === 'ledger'" class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">时间点计划台账</div>
          <div class="panel-sub">计划检测日 / 有效截止日 / 政策硬上限三层日期与延期状态并列展示</div>
        </div>
        <span class="pill pill-muted">只读投影</span>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="ledgerColumns"
          :data-source="rows"
          size="small"
          row-key="name"
          :loading="loading"
          :pagination="{ pageSize: 10 }"
          :scroll="{ x: 1320 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'point'">
              <a class="mono" @click="selectTimepoint(record.name)">{{ record.time_point_label }}</a>
            </template>
            <template v-else-if="column.key === 'product'">
              <div class="stb-cell-strong">{{ record.product_name || '—' }}</div>
              <div class="dim mono">{{ record.batch_no || '' }}</div>
            </template>
            <template v-else-if="column.key === 'planned'"><span class="mono">{{ record.plan_test_date || '—' }}</span></template>
            <template v-else-if="column.key === 'effective'"><span class="mono">{{ record.effective_test_due || '—' }}</span></template>
            <template v-else-if="column.key === 'policyLatest'"><span class="mono dim">{{ record.policy_latest_test_due || '不限制' }}</span></template>
            <template v-else-if="column.key === 'sampleDate'">
              <span class="mono" :class="{ dim: !record.actual_sample_date }">{{ record.actual_sample_date || '未登记' }}</span>
            </template>
            <template v-else-if="column.key === 'delay'">
              <span v-if="record.delay_state" :class="toneClass(record.delay_state.includes('待批准') ? 'warn' : 'info')">
                {{ record.delay_state }}
              </span>
              <span v-else class="dim">无</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <span :class="toneClass(statusTone(record.exec_state || record.status))">{{ record.exec_state || record.status }}</span>
            </template>
          </template>
        </a-table>
        <a-empty v-if="!loading && !rows.length" description="暂无时间点" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 40px 0" />
      </div>
    </div>

    <!-- 延期审批 -->
    <div v-else class="panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">延期申请与审批</div>
          <div class="panel-sub">
            申请与批准为独立动作；待批准 {{ delaySummary.pending }} · 已批准 {{ delaySummary.approved }} · 已驳回 {{ delaySummary.rejected }}
          </div>
        </div>
        <a-button size="small" type="primary" :disabled="!can('apply_delay')" @click="delayRef?.show()">申请延期</a-button>
      </div>
      <div class="panel-body no-pad">
        <a-table
          :columns="delayColumns"
          :data-source="delayRows"
          size="small"
          row-key="key"
          :loading="delayLoading"
          :pagination="{ pageSize: 10 }"
          :scroll="{ x: 1320 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'point'">
              <a class="mono" @click="selectTimepoint(record.parent)">{{ record.parent }}</a>
            </template>
            <template v-else-if="column.key === 'product'">
              <div class="stb-cell-strong">{{ record.product_name || '—' }}</div>
              <div class="dim mono">{{ record.batch_no || '' }} · {{ record.time_point_label || '' }}</div>
            </template>
            <template v-else-if="column.key === 'planned'"><span class="mono">{{ record.planned_due_date || '—' }}</span></template>
            <template v-else-if="column.key === 'requested'"><span class="mono">{{ record.requested_due_date || '—' }}</span></template>
            <template v-else-if="column.key === 'approved'">
              <span class="mono" :class="{ dim: !record.approved_due_date }">{{ record.approved_due_date || '—' }}</span>
            </template>
            <template v-else-if="column.key === 'policyLatest'"><span class="mono dim">{{ record.policy_latest_due_date || '不限制' }}</span></template>
            <template v-else-if="column.key === 'status'">
              <span :class="toneClass(delayTone(record.status))">{{ record.status }}</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-space v-if="record.status === '待批准'">
                <a-button v-if="can('approve_delay')" size="small" type="primary"
                          @click="askApproveDelay(record)">批准</a-button>
                <a-button v-if="can('reject_delay')" size="small" danger
                          @click="askRejectDelay(record)">驳回</a-button>
              </a-space>
              <span v-else class="dim">—</span>
            </template>
          </template>
        </a-table>
        <a-empty v-if="!delayLoading && !delayRows.length" description="暂无延期申请" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 40px 0" />
      </div>
    </div>

    <!-- 通用：原因 / 日期输入弹窗（取消时间点 / 驳回延期 / 批准延期） -->
    <a-modal v-model:open="promptOpen" :title="promptTitle" :confirm-loading="promptSaving" @ok="confirmPrompt">
      <a-form layout="vertical" size="small">
        <a-form-item v-if="promptMode === 'approve'" label="批准允许日期 *">
          <a-date-picker v-model:value="promptDate" style="width: 100%" value-format="YYYY-MM-DD" />
        </a-form-item>
        <a-form-item label="原因 *"><a-textarea v-model:value="promptReason" :rows="3" /></a-form-item>
      </a-form>
    </a-modal>

    <!-- 生成时间点 -->
    <a-modal v-model:open="generateOpen" title="生成时间点" :confirm-loading="generateSaving" @ok="confirmGenerate">
      <p class="stb-gate-sub">按样品的方案/通知单条件逐点生成；已存在的节点跳过（幂等），可安全重跑。</p>
      <a-select
        v-model:value="generateSample"
        :options="sampleOptions"
        show-search
        :filter-option="false"
        placeholder="选择稳定性样品"
        style="width: 100%"
      />
    </a-modal>

    <StbDelayDrawer ref="delayRef" :rows="rows" @created="onDelayCreated" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { ArrowLeftOutlined, ArrowRightOutlined, CalendarOutlined, PlusOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbDelayDrawer from '@/components/stability/StbDelayDrawer.vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  approveDelay, canAction, cancelTimepoint, completeSampling, delays, generateTimepoints,
  rejectDelay, samples, schedule, startTesting, timepointDetail,
  type DelayRow, type SampleRow, type ScheduleRow, type TimepointDetail,
} from '@/api/stability'
import { readScalarQuery } from '@/features/todos/todoModel'

const auth = useAuthStore()
const route = useRoute()
const can = (action: string): boolean => canAction(auth.user?.roles, action)

const delayRef = ref<InstanceType<typeof StbDelayDrawer> | null>(null)
const tab = ref<'board' | 'ledger' | 'delay'>('board')
const loading = ref(false)
const rows = ref<ScheduleRow[]>([])
const conditionFilter = ref('全部条件')
const stateFilter = ref('全部执行状态')
const targetTimepoint = ref('')
const targetTimepointMissing = ref(false)

const conditionOptions = ['全部条件', '长期', '加速', '中间', '影响因素-高温', '影响因素-高湿', '影响因素-强光']
  .map((v) => ({ value: v, label: v }))
const stateOptions = ['全部执行状态', '待取样', '待检测', '检测中', '已完成', '已取消', '取样逾期', '检测逾期']
  .map((v) => ({ value: v, label: v }))

function statusTone(status: string): 'pass' | 'warn' | 'danger' | 'info' | 'muted' {
  if (status === '已完成') return 'pass'
  if (status === '已取消') return 'muted'
  if (status === '取样逾期' || status === '检测逾期') return 'danger'
  if (status === '检测中') return 'info'
  if (status === '待取样' || status === '待检测') return 'warn'
  return 'muted'
}
function toneClass(tone: ReturnType<typeof statusTone>): string {
  return `pill pill-${tone}`
}
function delayTone(status: string): 'pass' | 'warn' | 'danger' | 'muted' {
  if (status === '已批准') return 'pass'
  if (status === '已驳回') return 'danger'
  if (status === '待批准') return 'warn'
  return 'muted'
}

const filtered = computed(() =>
  rows.value.filter((r) => {
    if (conditionFilter.value !== '全部条件' && r.condition_type !== conditionFilter.value) return false
    if (stateFilter.value !== '全部执行状态') {
      const state = r.exec_state || r.status
      if (state !== stateFilter.value && r.status !== stateFilter.value) return false
    }
    return true
  }))

// ---- 月度看板 ----
const cursor = ref(new Date())
const monthKey = computed(() =>
  `${cursor.value.getFullYear()}-${String(cursor.value.getMonth() + 1).padStart(2, '0')}`)
const monthLabel = computed(() => `${cursor.value.getFullYear()} 年 ${cursor.value.getMonth() + 1} 月`)
const monthRows = computed(() => filtered.value.filter((r) => String(r.plan_sample_date || '').startsWith(monthKey.value)))
const dayHeaders = computed(() => {
  const y = cursor.value.getFullYear()
  const m = cursor.value.getMonth()
  const days = new Date(y, m + 1, 0).getDate()
  return Array.from({ length: days }, (_, i) => {
    const d = i + 1
    return { day: String(d), key: `${monthKey.value}-${String(d).padStart(2, '0')}` }
  })
})
interface BoardRow {
  key: string
  product_name?: string
  batch_no?: string
  condition_type: string
  cells: Record<string, string>
  tone: Record<string, string>
  item: Record<string, string>
}
const boardRows = computed<BoardRow[]>(() => {
  const map = new Map<string, BoardRow>()
  for (const r of monthRows.value) {
    const key = `${r.product_name || ''}#${r.batch_no || ''}#${r.condition_type}`
    if (!map.has(key)) {
      map.set(key, {
        key, product_name: r.product_name, batch_no: r.batch_no, condition_type: r.condition_type,
        cells: {}, tone: {}, item: {},
      })
    }
    const row = map.get(key)!
    const day = String(r.plan_sample_date || '')
    row.cells[day] = r.time_point_label
    row.tone[day] = (r.exec_state === '取样逾期' || r.exec_state === '检测逾期')
      ? 'danger' : (r.status === '待取样' ? 'warn' : '')
    row.item[day] = r.name
  }
  return [...map.values()]
})
function shiftMonth(step: number) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + step, 1)
}

// ---- 本周到期 ----
const weekDue = computed(() => {
  const today = new Date()
  const limit = new Date(today)
  limit.setDate(limit.getDate() + 7)
  const out: { name: string; product_name?: string; time_point_label: string; due: string; state: string; tone: string }[] = []
  for (const r of rows.value) {
    if (r.status === '待取样' && r.effective_sample_due) {
      const d = new Date(r.effective_sample_due)
      if (d >= today && d <= limit) {
        out.push({ name: r.name, product_name: r.product_name, time_point_label: r.time_point_label,
          due: r.effective_sample_due, state: '待取样', tone: 'warn' })
      }
    }
    if ((r.status === '待检测' || r.status === '检测中') && r.effective_test_due) {
      const d = new Date(r.effective_test_due)
      if (d >= today && d <= limit) {
        out.push({ name: r.name, product_name: r.product_name, time_point_label: r.time_point_label,
          due: r.effective_test_due, state: r.status, tone: r.status === '检测中' ? 'info' : 'warn' })
      }
    }
  }
  return out.sort((a, b) => a.due.localeCompare(b.due))
})

const dueColumns = [
  { title: '时间点', key: 'point', width: 90 },
  { title: '产品', dataIndex: 'product_name', key: 'product', width: 150 },
  { title: '截止日', key: 'due', width: 100 },
  { title: '状态', key: 'status', width: 100 },
]
const ledgerColumns = [
  { title: '时间点', key: 'point', width: 90 },
  { title: '产品 / 批号', key: 'product', width: 170 },
  { title: '条件', dataIndex: 'condition_type', key: 'condition', width: 100 },
  { title: '计划检测日', key: 'planned', width: 110 },
  { title: '有效截止日', key: 'effective', width: 110 },
  { title: '政策硬上限', key: 'policyLatest', width: 110 },
  { title: '实际取样日', key: 'sampleDate', width: 110 },
  { title: '延期', key: 'delay', width: 150 },
  { title: '检测窗口', key: 'window', width: 110, customRender: () => '计划日后 30 天内' },
  { title: '状态', key: 'status', width: 100 },
]
const delayColumns = [
  { title: '时间点', key: 'point', width: 160 },
  { title: '产品 / 时间点', key: 'product', width: 180 },
  { title: '类型', dataIndex: 'delay_type', key: 'delayType', width: 100 },
  { title: '原计划日', key: 'planned', width: 110 },
  { title: '申请日', key: 'requested', width: 110 },
  { title: '批准日', key: 'approved', width: 110 },
  { title: '政策硬上限', key: 'policyLatest', width: 110 },
  { title: '申请人', dataIndex: 'apply_by', key: 'applicant', width: 160 },
  { title: '状态', key: 'status', width: 100 },
  { title: '动作', key: 'actions', width: 150, fixed: 'right' },
]

// ---- 时间点详情与动作 ----
const tpDetail = ref<TimepointDetail | null>(null)
async function selectTimepoint(name: string) {
  try {
    tpDetail.value = await timepointDetail(name)
  } catch {
    // 具体错误已由 client 拦截层弹出
  }
}

interface UiAction { action: string; label: string; primary?: boolean; danger?: boolean }
const tpActions = computed<UiAction[]>(() => {
  const d = tpDetail.value
  if (!d) return []
  const out: UiAction[] = []
  const push = (a: UiAction) => { if (can(a.action)) out.push(a) }
  if (d.status === '待取样') {
    push({ action: 'complete_sampling', label: '取样完成', primary: true })
  }
  if (d.status === '待检测') {
    push({ action: 'start_testing', label: '开始检测', primary: true })
  }
  if (['待取样', '待检测', '检测中'].includes(d.status)) {
    push({ action: 'apply_delay', label: '申请延期' })
    push({ action: 'cancel_timepoint', label: '取消时间点', danger: true })
  }
  return out
})

async function runTpAction(a: UiAction) {
  const d = tpDetail.value
  if (!d) return
  if (a.action === 'apply_delay') {
    delayRef.value?.show(d.name)
    return
  }
  if (a.action === 'cancel_timepoint') {
    openPrompt('cancel', `取消时间点 · ${d.name}`)
    return
  }
  try {
    if (a.action === 'complete_sampling') await completeSampling(d.name)
    else if (a.action === 'start_testing') await startTesting(d.name)
    message.success('操作已完成')
    await Promise.all([load(), selectTimepoint(d.name)])
    if (tab.value === 'delay') await loadDelays()
  } catch {
    // 具体错误已由 client 拦截层弹出（含结果前向守卫 / 状态机）
  }
}

// ---- 延期审批 ----
const delayRows = ref<DelayRow[]>([])
const delayLoading = ref(false)
const delaySummary = ref({ pending: 0, approved: 0, rejected: 0 })
async function loadDelays() {
  delayLoading.value = true
  try {
    await load()
    const res = await delays({ limit: 300 })
    delayRows.value = res.rows.map((r, i) => ({ ...r, key: `${r.parent}-${r.delay_type}-${i}` }))
    delaySummary.value = res.summary
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    delayLoading.value = false
  }
}

// ---- 通用提示弹窗 ----
const promptOpen = ref(false)
const promptMode = ref<'reason' | 'approve'>('reason')
const promptTitle = ref('')
const promptReason = ref('')
const promptDate = ref<string | undefined>(undefined)
const promptSaving = ref(false)
let promptTarget: DelayRow | null = null
let promptTp: string | null = null

function openPrompt(mode: 'cancel' | 'reject' | 'approve', title: string, target?: DelayRow) {
  promptMode.value = mode === 'approve' ? 'approve' : 'reason'
  promptTitle.value = title
  promptReason.value = ''
  promptDate.value = undefined
  promptTarget = target || null
  promptTp = mode === 'cancel' ? (tpDetail.value?.name || null) : (target?.parent || null)
  promptOpen.value = true
}

function askApproveDelay(row: DelayRow) {
  openPrompt('approve', `批准延期 · ${row.parent}`, row)
}
function askRejectDelay(row: DelayRow) {
  openPrompt('reject', `驳回延期 · ${row.parent}`, row)
}

async function confirmPrompt() {
  promptSaving.value = true
  try {
    if (promptTarget) {
      if (promptMode.value === 'approve') {
        if (!promptDate.value) { message.warning('批准日期必填'); return }
        await approveDelay(promptTarget.parent!, promptTarget.delay_type, promptDate.value)
      } else {
        if (!promptReason.value.trim()) { message.warning('原因必填'); return }
        await rejectDelay(promptTarget.parent!, promptTarget.delay_type, promptReason.value.trim())
      }
      message.success('操作已完成')
      promptOpen.value = false
      await loadDelays()
      if (promptTp) await selectTimepoint(promptTp)
    } else if (promptTp) {
      if (!promptReason.value.trim()) { message.warning('取消原因必填'); return }
      await cancelTimepoint(promptTp, promptReason.value.trim())
      message.success('时间点已取消')
      promptOpen.value = false
      await Promise.all([load(), selectTimepoint(promptTp)])
    }
  } catch {
    // 具体错误已由 client 拦截层弹出（含 SoD / 日期链 / 状态机）
  } finally {
    promptSaving.value = false
  }
}

function onDelayCreated(name: string) {
  void loadDelays()
  void selectTimepoint(name)
}

// ---- 生成时间点 ----
const generateOpen = ref(false)
const generateSaving = ref(false)
const generateSample = ref<string | undefined>(undefined)
const sampleRows = ref<SampleRow[]>([])
const sampleOptions = computed(() =>
  sampleRows.value.map((s) => ({
    value: s.name, label: `${s.product_name || ''} ${s.batch_no}（${s.status}）`,
  })))
watch(generateOpen, async (v) => {
  if (!v) return
  try {
    sampleRows.value = (await samples({ limit: 200 })).rows
  } catch {
    // 具体错误已由 client 拦截层弹出
  }
})
async function confirmGenerate() {
  if (!generateSample.value) { message.warning('请选择样品'); return }
  generateSaving.value = true
  try {
    const res = await generateTimepoints(generateSample.value)
    message.success(`已生成 ${res.created} 个时间点（已存在的跳过）`)
    generateOpen.value = false
    await load()
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    generateSaving.value = false
  }
}

// ---- 数据 ----
async function load() {
  loading.value = true
  try {
    const res = await schedule({ limit: 1000 })
    rows.value = res.rows
    targetTimepoint.value = readScalarQuery(route.query.timepoint) || ''
    targetTimepointMissing.value = false
    if (targetTimepoint.value) {
      const target = rows.value.find((row) => row.name === targetTimepoint.value)
      targetTimepointMissing.value = !target
      if (target) await selectTimepoint(target.name)
      else tpDetail.value = null
    }
  } catch {
    if (!auth.user) message.warning('未登录（Guest）：计划数据不可用，请先在 Frappe Desk 登录后刷新。')
    else if (!auth.user?.roles?.length) message.warning('当前会话尚未取到角色，列表加载可能受限。')
    else message.error('加载取样与检测计划失败')
  } finally {
    loading.value = false
  }
}

function switchTab(key: 'board' | 'ledger' | 'delay') {
  tab.value = key
  if (key === 'delay') void loadDelays()
}

onMounted(() => {
  void auth.checkSession()
  void load()
})
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.month-switch { display: flex; align-items: center; gap: 7px; }
.month-title { min-width: 96px; text-align: center; font-weight: 700; font-size: 12px; color: var(--ink); }
</style>
