<template>
  <section class="product-page app-product-page">
    <div class="board-hero glass-hero">
      <div>
        <span class="page-kicker">ATTENDANCE · 部门看板</span>
        <h1>部门看板</h1>
        <p v-if="payload">
          {{ payload.meta.date }} · {{ payload.meta.mode === 'review' ? '历史回顾' : '实时' }}
          <template v-if="payload.meta.mode === 'live'">（{{ payload.meta.now_hm }}）</template>
          · 范围 {{ payload.meta.scope }}
        </p>
      </div>
      <a-space wrap>
        <a-select
          v-model:value="department"
          style="width: 200px"
          :options="deptOptions"
          placeholder="全部部门"
          allow-clear
          @change="load"
        />
        <a-date-picker v-model:value="pickDate" :allow-clear="false" @change="load" />
        <a-button type="primary" :loading="loading" @click="load">查询</a-button>
        <a-checkbox v-model:checked="onlyAttention" @change="load">只看异常</a-checkbox>
      </a-space>
    </div>

    <a-alert v-if="error" type="error" show-icon :message="error" class="board-error" />
    <a-spin v-else :spinning="loading">
      <template v-if="payload">
        <div class="board-kpi">
          <article class="board-stat board-stat--hero glass-surface">
            <i class="board-rule"></i>
            <strong>{{ payload.stats.attendance_rate ?? '—' }}<small v-if="payload.stats.attendance_rate != null">%</small></strong>
            <span>出勤率</span>
          </article>
          <article v-for="c in kpis" :key="c.key" class="board-stat glass-surface">
            <i class="board-rule"></i>
            <strong :class="c.tone">{{ c.value }}</strong>
            <span>{{ c.label }}</span>
          </article>
        </div>

        <p v-if="others.length" class="board-note">
          其他：{{ others.map((o) => `${o.label} ${o.value}`).join(' · ') }}
          <em>（不计入未打卡）</em>
        </p>

        <section class="section-panel glass-surface">
          <div class="section-head">
            <div>
              <h2>部门概览</h2>
              <p>点击部门行展开人员明细</p>
            </div>
          </div>
          <a-table
            :data-source="deptRows"
            :pagination="false"
            row-key="dept"
            size="middle"
            :scroll="{ y: 560 }"
            :expanded-row-keys="expanded"
            @expand="onExpand"
          >
            <a-table-column title="部门" data-index="dept" key="dept">
              <template #default="{ record }">
                <a-button type="link" size="small" @click="toggle(record.dept)">
                  <CaretRightOutlined :class="['board-caret', { 'is-open': expanded.includes(record.dept) }]" />
                  {{ record.dept }}
                </a-button>
              </template>
            </a-table-column>
            <a-table-column v-for="col in deptCols" :key="col.key" :title="col.title" :width="88" align="right">
              <template #default="{ record }">
                <b v-if="record[col.key] && col.emphasize" :class="`tone-${col.tone}`">{{ record[col.key] }}</b>
                <span v-else-if="record[col.key]">{{ record[col.key] }}</span>
                <span v-else class="board-zero">0</span>
              </template>
            </a-table-column>
          </a-table>
        </section>

        <section v-if="expanded.length" class="section-panel glass-surface board-detail-panel">
          <div class="section-head">
            <div><h2>人员明细</h2><p>{{ expanded.join(' · ') }}</p></div>
          </div>
          <a-table
            :data-source="detailRows"
            :pagination="{ pageSize: 30, size: 'small', showSizeChanger: false }"
            row-key="num"
            size="small"
          >
            <a-table-column title="工号" data-index="num" :width="130" />
            <a-table-column title="姓名" data-index="name" :width="120" />
            <a-table-column title="部门" data-index="dept" :width="160" />
            <a-table-column title="应出勤" data-index="expected_label" :width="170" />
            <a-table-column title="状态" key="state" :width="150">
              <template #default="{ record }">
                <a-tag :color="tagColor(record.state, record.anomaly_hidden)">{{ record.label }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="到岗" key="first" :width="90">
              <template #default="{ record }">{{ record.first_hm || '—' }}</template>
            </a-table-column>
            <a-table-column title="卡数" data-index="card_count" :width="70" align="right" />
            <a-table-column title="备注" key="note">
              <template #default="{ record }">
                <span class="board-note-cell">{{ noteOf(record) || '—' }}</span>
              </template>
            </a-table-column>
          </a-table>
        </section>
      </template>
    </a-spin>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import dayjs, { type Dayjs } from 'dayjs'
import { CaretRightOutlined } from '@ant-design/icons-vue'
import { fetchBoard, type BoardPayload, type BoardRow } from '@/services/attendanceBoard'

const payload = ref<BoardPayload | null>(null)
const loading = ref(false)
const error = ref('')
const department = ref<string | undefined>(undefined)
const pickDate = ref<Dayjs>(dayjs())
const onlyAttention = ref(false)
const expanded = ref<string[]>([])

const deptOptions = computed(() =>
  (payload.value?.departments || []).map((d) => ({ value: d.name, label: `${d.name}（${d.count}）` })),
)

/**
 * KPI 口径与 Desk 版逐项一致。`bad`/`warn` 只用于确有异常的桶——
 * 出勤率单独作为主数字放最前，不参与这组平级卡。
 */
const kpis = computed(() => {
  const s = payload.value?.stats
  if (!s) return []
  return [
    { key: 'expected', label: '应出勤', value: s.expected, tone: '', emphasize: false },
    { key: 'present', label: '已到岗', value: s.present, tone: '', emphasize: false },
    { key: 'late', label: '迟到', value: s.late, tone: 'critical', emphasize: true },
    { key: 'noCard', label: '未打卡', value: s.noCard, tone: 'warning', emphasize: true },
    { key: 'absent', label: '缺勤', value: s.absent, tone: 'critical', emphasize: true },
    { key: 'leave', label: '请假', value: s.leave, tone: '', emphasize: false },
    { key: 'rest', label: '休息', value: s.rest, tone: '', emphasize: false },
  ]
})

/** 非预警桶单列一行，避免与「未打卡」混淆（9 点时这两类人最多）。 */
const others = computed(() => {
  const s = payload.value?.stats
  if (!s) return []
  return [
    { key: 'outOnly', label: '仅下班卡', value: s.outOnly },
    { key: 'unknownTime', label: '班次未定', value: s.unknownTime },
    { key: 'notStarted', label: '未开始', value: s.notStarted },
  ].filter((o) => o.value)
})

const deptCols = [
  { key: 'total', title: '在册' },
  { key: 'expected', title: '应出勤' },
  { key: 'present', title: '已到岗' },
  { key: 'late', title: '迟到', tone: 'critical', emphasize: true },
  { key: 'noCard', title: '无打卡', tone: 'warning', emphasize: true },
  { key: 'absent', title: '缺勤', tone: 'critical', emphasize: true },
  { key: 'leave', title: '请假' },
]

const deptRows = computed(() => payload.value?.dept_stats || [])

/** 只看异常时过滤明细；部门表保留全部（否则看不到「正常」部门有多少人）。 */
const detailRows = computed(() => {
  const rows = payload.value?.rows || []
  const scoped = rows.filter((r) => expanded.value.includes(r.dept))
  return onlyAttention.value ? scoped.filter((r) => ATTENTION_STATES.has(r.state)) : scoped
})

// 与后端 state 串一一对应；只用于「只看异常」过滤，不改判定
const ATTENTION_STATES = new Set([
  'late', 'absent_day', 'absent_expected', 'no_pair', 'fact_none', 'out_offwindow', 'out_only',
])

/** 把后端备注里的长句压成短标记；空注释直接不显示。 */
const NOTE_MAP: Record<string, string> = {
  '以 HRMS 考勤结果为准': '',
  '班次起算点待排班/规则确认，仅记录打卡事实': '班次待定',
  '仅记录打卡事实，不判到点/迟到（班次起算点待排班/规则确认）': '班次待定',
  '当日有排班/固定班次但无配对考勤记录，未判缺勤': '未判缺勤',
  '当日有卡但无 HRMS 配对考勤结果': '无配对考勤',
  '班次时段内无卡，未定性为缺勤，请以月度考勤汇总为准': '未定性缺勤',
}
function noteOf(row: BoardRow) {
  const n = row.note || ''
  return n in NOTE_MAP ? NOTE_MAP[n] : n
}

/** 状态配色沿用 Desk 版语义：只给确凿定性上色，其余走中性琥珀。 */
function tagColor(state: string, hidden: boolean) {
  if (hidden) return 'default'
  if (state === 'late' || state === 'absent_day') return 'red'
  if (state === 'present' || state === 'out_day' || state === 'fact_present') return 'green'
  if (state === 'leave') return 'purple'
  if (state === 'rest') return 'blue'
  if (state === 'exempt') return 'default'
  return 'orange'
}

function toggle(dept: string) {
  const i = expanded.value.indexOf(dept)
  if (i >= 0) expanded.value.splice(i, 1)
  else expanded.value.push(dept)
}
function onExpand(open: boolean, record: { dept: string }) {
  if (open) {
    if (!expanded.value.includes(record.dept)) expanded.value.push(record.dept)
  } else {
    expanded.value = expanded.value.filter((d) => d !== record.dept)
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    payload.value = await fetchBoard(department.value || undefined, pickDate.value.format('YYYY-MM-DD'))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载部门看板失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.board-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 24px 26px;
  border-radius: var(--hbos-radius-hero);
  margin-bottom: 16px;
}
.board-hero h1 { margin: 8px 0 6px; font-size: 30px; line-height: 38px; }
.board-hero p { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); }
.board-error { margin-bottom: 16px; }

.board-kpi {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.board-stat {
  position: relative;
  padding: 20px 16px;
  border-radius: var(--hbos-radius-card);
  text-align: center;
  transition: transform var(--hbos-motion-fast) var(--hbos-ease-standard),
    box-shadow var(--hbos-motion-fast) var(--hbos-ease-standard);
}
.board-stat:hover { transform: translateY(-4px); box-shadow: var(--hbos-shadow-card-hover); }
.board-rule {
  display: block;
  height: 3px;
  width: 32px;
  margin: 0 auto 12px;
  border-radius: var(--hbos-radius-pill);
  background: var(--hbos-domain-attendance);
  opacity: .55;
}
.board-stat--hero .board-rule { opacity: 1; }
.board-stat strong {
  display: block;
  font-size: 30px;
  line-height: 38px;
  font-variant-numeric: tabular-nums;
  color: var(--hbos-text-primary);
}
.board-stat strong small { font-size: 16px; margin-left: 2px; }
.board-stat span { display: block; margin-top: 4px; font-size: 12px; color: var(--hbos-text-muted); }
.board-stat strong.tone-critical { color: var(--hbos-status-critical); }
.board-stat strong.tone-warning { color: var(--hbos-status-warning); }

.board-note { margin: 0 2px 16px; font-size: 12px; line-height: 20px; color: var(--hbos-text-secondary); }
.board-note em { font-style: normal; color: var(--hbos-text-muted); margin-left: 6px; }

.board-caret { transition: transform var(--hbos-motion-fast) var(--hbos-ease-standard); }
.board-caret.is-open { transform: rotate(90deg); }
.board-zero { color: var(--hbos-text-muted); opacity: .5; }
.tone-critical { color: var(--hbos-status-critical); }
.tone-warning { color: var(--hbos-status-warning); }
.board-detail-panel { margin-top: 16px; margin-bottom: 24px; }
.board-note-cell { color: var(--hbos-text-secondary); }

@media (max-width: 720px) {
  .board-hero h1 { font-size: 20px; line-height: 28px; }
}
</style>
