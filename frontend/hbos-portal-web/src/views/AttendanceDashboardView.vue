<template>
  <section class="product-page app-product-page">
    <div class="att-hero glass-hero">
      <div>
        <span class="page-kicker">ATTENDANCE · 考勤管理</span>
        <h1>考勤异常仪表盘</h1>
        <p>{{ data?.date_range || '本周' }} · 数据来自考勤判定引擎的落库结果，本页只做展示投影</p>
      </div>
      <a-space>
        <a-range-picker
          v-model:value="range"
          :allow-clear="false"
          @change="load"
        />
        <a-button type="primary" :loading="loading" @click="load">查询</a-button>
      </a-space>
    </div>

    <a-alert v-if="error" type="error" show-icon :message="error" class="att-error" />
    <a-spin v-else :spinning="loading">
      <div class="att-metrics">
        <article v-for="m in metrics" :key="m.id" class="att-stat glass-surface">
          <i class="att-rule"></i>
          <span>{{ m.label }}</span>
          <strong :style="{ color: m.color }">{{ m.value }}</strong>
          <small>{{ m.hint }}</small>
        </article>
      </div>

      <div class="att-grid">
        <section class="section-panel glass-surface">
          <div class="section-head">
            <div><h2>迟到 Top 15</h2><p>按本月迟到次数排序</p></div>
          </div>
          <div v-if="!topLate.length" class="att-empty">本区间无迟到记录</div>
          <ol v-else class="att-rank">
            <li v-for="(r, i) in topLate" :key="r.name">
              <b>{{ i + 1 }}</b>
              <span class="att-rank-name">{{ r.name }}</span>
              <span class="att-bar"><i :style="{ width: pct(r.count, maxLate) + '%' }"></i></span>
              <em>{{ r.count }}</em>
            </li>
          </ol>
        </section>

        <section class="section-panel glass-surface">
          <div class="section-head">
            <div><h2>缺勤 Top 15</h2><p>按本月缺勤天数排序</p></div>
          </div>
          <div v-if="!topAbsent.length" class="att-empty">本区间无缺勤记录</div>
          <ol v-else class="att-rank">
            <li v-for="(r, i) in topAbsent" :key="r.name">
              <b>{{ i + 1 }}</b>
              <span class="att-rank-name">{{ r.name }}</span>
              <span class="att-bar att-bar--critical"><i :style="{ width: pct(r.count, maxAbsent) + '%' }"></i></span>
              <em>{{ r.count }}</em>
            </li>
          </ol>
        </section>

        <section class="section-panel glass-surface">
          <div class="section-head">
            <div><h2>每日异常趋势</h2><p>{{ data?.date_range }}</p></div>
          </div>
          <svg class="att-trend" :viewBox="`0 0 ${trendW} ${trendH}`" preserveAspectRatio="none">
            <polyline :points="trendPoints('late')" class="att-line att-line--warning" />
            <polyline :points="trendPoints('absent')" class="att-line att-line--critical" />
          </svg>
          <div class="att-legend">
            <span><i class="dot dot--warning"></i>迟到</span>
            <span><i class="dot dot--critical"></i>缺勤</span>
          </div>
        </section>

        <section class="section-panel glass-surface">
          <div class="section-head">
            <div><h2>部门异常分布</h2><p>异常合计前 10 个部门</p></div>
          </div>
          <div v-if="!depts.length" class="att-empty">本区间无部门异常</div>
          <ul v-else class="att-dept">
            <li v-for="d in depts" :key="d.name">
              <span class="att-dept-name">{{ d.name }}</span>
              <span class="att-dept-bars">
                <i class="seg seg--warning" :style="{ flex: d.late }" :title="`迟到 ${d.late}`"></i>
                <i class="seg seg--muted" :style="{ flex: d.early }" :title="`早退 ${d.early}`"></i>
                <i class="seg seg--critical" :style="{ flex: d.absent }" :title="`缺勤 ${d.absent}`"></i>
              </span>
              <em>{{ d.total }}</em>
            </li>
          </ul>
        </section>
      </div>

      <section class="section-panel glass-surface att-table-panel">
        <div class="section-head">
          <div>
            <h2>异常明细排行</h2>
            <p>共 {{ data?.table_rows?.length || 0 }} 人；0 值不标色，只标确有异常的项</p>
          </div>
        </div>
        <a-table
          :data-source="data?.table_rows || []"
          :pagination="{ pageSize: 20, size: 'small' }"
          row-key="num"
          size="middle"
          :scroll="{ y: 520 }"
        >
          <a-table-column title="排名" key="idx" :width="70">
            <template #default="{ index }">{{ index + 1 }}</template>
          </a-table-column>
          <a-table-column title="工号" data-index="num" key="num" :width="120" />
          <a-table-column title="姓名" data-index="name" key="name" :width="110" />
          <a-table-column title="部门" data-index="dept" key="dept" />
          <a-table-column title="迟到" key="late" align="right" :width="90">
            <template #default="{ record }">
              <a-tag v-if="record.late_count" color="orange">{{ record.late_count }}</a-tag>
              <span v-else class="att-zero">0</span>
            </template>
          </a-table-column>
          <a-table-column title="早退" key="early" align="right" :width="90">
            <template #default="{ record }">
              <a-tag v-if="record.early_count" color="orange">{{ record.early_count }}</a-tag>
              <span v-else class="att-zero">0</span>
            </template>
          </a-table-column>
          <a-table-column title="缺勤" key="absent" align="right" :width="90">
            <template #default="{ record }">
              <a-tag v-if="record.absent_count" color="red">{{ record.absent_count }}</a-tag>
              <span v-else class="att-zero">0</span>
            </template>
          </a-table-column>
          <a-table-column title="异常合计" key="total" align="right" :width="110">
            <template #default="{ record }"><b>{{ record.total_anomaly }}</b></template>
          </a-table-column>
        </a-table>
      </section>
    </a-spin>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import dayjs, { type Dayjs } from 'dayjs'
import { fetchAttendanceDashboard, type AttendanceDashboardData } from '@/services/attendance'

const data = ref<AttendanceDashboardData | null>(null)
const loading = ref(false)
const error = ref('')
const range = ref<[Dayjs, Dayjs]>([dayjs().startOf('week').add(1, 'day'), dayjs().endOf('week').add(1, 'day')])

// 令牌里的 status 色，与门户其它页面同源（tokens.css）
const C_WARNING = 'var(--hbos-status-warning)'
const C_CRITICAL = 'var(--hbos-status-critical)'
const C_SUCCESS = 'var(--hbos-status-success)'
const C_TEXT = 'var(--hbos-text-primary)'

const metrics = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    { id: 'late', label: '迟到', value: d.total_late, color: C_WARNING, hint: '人次' },
    { id: 'early', label: '早退', value: d.total_early, color: C_TEXT, hint: '人次' },
    { id: 'absent', label: '缺勤', value: d.total_absent, color: C_CRITICAL, hint: '人天' },
    { id: 'people', label: '异常人员', value: d.anomaly_people, color: C_TEXT, hint: '人' },
    { id: 'rate', label: '出勤率', value: d.attendance_rate + '%', color: C_SUCCESS, hint: '区间内' },
    { id: 'total', label: '总人数', value: d.total_employees, color: C_TEXT, hint: '在职' },
  ]
})

function zip(names: string[] = [], counts: number[] = []) {
  return names.map((name, i) => ({ name, count: counts[i] ?? 0 }))
}
const topLate = computed(() => zip(data.value?.top_late_names, data.value?.top_late_counts))
const topAbsent = computed(() => zip(data.value?.top_absent_names, data.value?.top_absent_counts))
const maxLate = computed(() => Math.max(1, ...topLate.value.map((r) => r.count)))
const maxAbsent = computed(() => Math.max(1, ...topAbsent.value.map((r) => r.count)))

const depts = computed(() => {
  const d = data.value
  if (!d) return []
  return (d.dept_names || []).map((name, i) => {
    const late = d.dept_late?.[i] ?? 0
    const early = d.dept_early?.[i] ?? 0
    const absent = d.dept_absent?.[i] ?? 0
    return { name, late, early, absent, total: late + early + absent }
  })
})

// ---- 趋势折线：手写 SVG，不引图表库 ----
// 门户刻意不带图表依赖（LIMS 页同样是内联 SVG），4 条序列用折线足够表达。
const trendW = 640
const trendH = 160
const trendMax = computed(() => {
  const d = data.value
  if (!d) return 1
  return Math.max(1, ...(d.trend_late || []), ...(d.trend_absent || []))
})

function trendPoints(kind: 'late' | 'absent') {
  const d = data.value
  if (!d) return ''
  const values = (kind === 'late' ? d.trend_late : d.trend_absent) || []
  if (!values.length) return ''
  const stepX = values.length > 1 ? trendW / (values.length - 1) : 0
  return values
    .map((v, i) => {
      const x = i * stepX
      const y = trendH - (v / trendMax.value) * (trendH - 12) - 6
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

function pct(value: number, max: number) {
  return Math.round((value / max) * 100)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [start, end] = range.value
    data.value = await fetchAttendanceDashboard(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'))
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载考勤数据失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.att-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding: 24px 26px;
  border-radius: var(--hbos-radius-hero);
  margin-bottom: 16px;
}
.att-hero h1 { margin: 8px 0 6px; font-size: 30px; line-height: 38px; }
.att-hero p { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); }
.att-error { margin-bottom: 16px; }

.att-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.att-stat {
  position: relative;
  padding: 20px 16px;
  border-radius: var(--hbos-radius-card);
  text-align: center;
  transition: transform var(--hbos-motion-fast) var(--hbos-ease-standard),
    box-shadow var(--hbos-motion-fast) var(--hbos-ease-standard);
}
.att-stat:hover { transform: translateY(-4px); box-shadow: var(--hbos-shadow-card-hover); }
.att-rule {
  display: block;
  height: 3px;
  width: 32px;
  margin: 0 auto 12px;
  border-radius: var(--hbos-radius-pill);
  background: var(--hbos-domain-attendance);
}
.att-stat span { display: block; font-size: 12px; color: var(--hbos-text-muted); }
.att-stat strong { display: block; margin-top: 6px; font-size: 30px; line-height: 38px; font-variant-numeric: tabular-nums; }
.att-stat small { display: block; margin-top: 4px; font-size: 12px; color: var(--hbos-text-muted); }

.att-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

/* Top 15 用横条而非图表：可读性更好，也不需要图表库 */
.att-rank { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.att-rank li { display: grid; grid-template-columns: 24px 1fr 1.4fr 40px; align-items: center; gap: 10px; font-size: 14px; }
.att-rank b { color: var(--hbos-text-muted); font-weight: 500; font-size: 12px; text-align: right; }
.att-rank-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.att-bar { display: block; height: 10px; border-radius: var(--hbos-radius-pill); background: rgba(65, 91, 138, .08); overflow: hidden; }
.att-bar i { display: block; height: 100%; border-radius: var(--hbos-radius-pill); background: var(--hbos-status-warning); }
.att-bar--critical i { background: var(--hbos-status-critical); }
.att-rank em { text-align: right; font-style: normal; font-variant-numeric: tabular-nums; color: var(--hbos-text-secondary); }

.att-trend { width: 100%; height: 160px; display: block; }
.att-line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.att-line--warning { stroke: var(--hbos-status-warning); }
.att-line--critical { stroke: var(--hbos-status-critical); }
.att-legend { display: flex; gap: 18px; margin-top: 10px; font-size: 12px; color: var(--hbos-text-muted); }
.att-legend .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.dot--warning { background: var(--hbos-status-warning); }
.dot--critical { background: var(--hbos-status-critical); }

.att-dept { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.att-dept li { display: grid; grid-template-columns: 1fr 1.6fr 40px; align-items: center; gap: 12px; font-size: 14px; }
.att-dept-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.att-dept-bars { display: flex; height: 10px; border-radius: var(--hbos-radius-pill); overflow: hidden; background: rgba(65, 91, 138, .08); }
.att-dept-bars .seg { display: block; height: 100%; min-width: 0; }
.seg--warning { background: var(--hbos-status-warning); }
.seg--muted { background: var(--hbos-status-neutral); }
.seg--critical { background: var(--hbos-status-critical); }
.att-dept em { text-align: right; font-style: normal; font-variant-numeric: tabular-nums; color: var(--hbos-text-secondary); }

.att-table-panel { margin-bottom: 24px; }
.att-zero { color: var(--hbos-text-muted); opacity: .5; }
.att-empty { padding: 28px 0; text-align: center; color: var(--hbos-text-muted); font-size: 14px; }

@media (max-width: 720px) {
  .att-hero h1 { font-size: 20px; line-height: 28px; }
  .att-grid { grid-template-columns: 1fr; }
}
</style>
