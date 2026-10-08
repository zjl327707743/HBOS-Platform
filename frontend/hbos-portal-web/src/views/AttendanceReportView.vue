<template>
  <section class="rep-page">
    <header class="rep-head">
      <div>
        <span class="page-kicker">ATTENDANCE · 报表</span>
        <h1>{{ spec?.title || '报表' }}</h1>
        <p>{{ spec?.hint }}</p>
      </div>
      <span class="rep-count" v-if="!loading && !error">
        共 <b>{{ payload?.total ?? 0 }}</b> 行
      </span>
    </header>

    <!-- 筛选条：antd 组件，与门户其余部分同一套控件 -->
    <div class="rep-toolbar glass-surface">
      <template v-if="spec?.filters.includes('month')">
        <a-select v-model:value="filters.month" :options="monthOptions" style="width: 96px" />
      </template>
      <template v-if="spec?.filters.includes('year')">
        <a-select v-model:value="filters.year" :options="yearOptions" style="width: 104px" />
      </template>
      <template v-if="spec?.filters.includes('date-range') && !spec?.filters.includes('month')">
        <a-range-picker v-model:value="range" :allow-clear="true" />
      </template>
      <template v-if="spec?.filters.includes('department')">
        <a-select
          v-model:value="filters.department"
          :options="departmentOptions"
          :loading="departmentsLoading"
          show-search
          allow-clear
          option-filter-prop="label"
          placeholder="全部部门"
          style="width: 200px"
        />
      </template>
      <a-button type="primary" :loading="loading" @click="load">查询</a-button>
      <a-button :disabled="loading" @click="reset">重置</a-button>
    </div>

    <a-alert
      v-if="error"
      type="error"
      show-icon
      :message="error"
      class="rep-alert"
    />

    <div v-else class="rep-panel glass-surface">
      <a-table
        :data-source="payload?.data || []"
        :columns="tableColumns"
        :loading="loading"
        :pagination="pagination"
        :scroll="{ x: scrollWidth }"
        :row-key="rowKey"
        size="middle"
        @change="onTableChange"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.key === '__idx'">{{ rowIndex(index) }}</template>
          <template v-else-if="isDetail(column.key)">
            <span v-if="!record[column.key]" class="rep-zero">—</span>
            <span v-else class="rep-days">
              <span
                v-for="day in days(record[column.key])"
                :key="day"
                class="rep-day"
                :class="'tone-' + toneOf(column.key)"
              >{{ day }}</span>
            </span>
          </template>
          <template v-else-if="isNumeric(record[column.key])">
            <span :class="{ 'rep-zero': !record[column.key] }">{{ record[column.key] || 0 }}</span>
          </template>
        </template>
      </a-table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import dayjs, { type Dayjs } from 'dayjs'
import { callFrappeMethod } from '@/services/frappeClient'
import {
  fetchReport,
  findReport,
  type ReportColumn,
  type ReportPayload,
} from '@/services/attendanceReports'

const route = useRoute()

const payload = ref<ReportPayload | null>(null)
const loading = ref(false)
const error = ref('')
const page = ref(1)

const slug = computed(() => String(route.params.slug ?? ''))
const spec = computed(() => findReport(slug.value))

const today = dayjs()
// 默认窗口按报表给：不加日期过滤时这些报表会全量返回（打卡流水实测 61815 行），
// 首屏要等好几秒。spec.defaultRangeDays 为空则用「本月」。
const initialRange = (): [Dayjs, Dayjs] | null => {
  const days = spec.value?.defaultRangeDays
  if (!days) return [today.startOf('month'), today.endOf('month')]
  return [today.subtract(days - 1, 'day').startOf('day'), today.endOf('day')]
}
const range = ref<[Dayjs, Dayjs] | null>(initialRange())

const filters = ref<Record<string, string>>({
  month: String(today.month() + 1),
  year: String(today.year()),
  department: '',
})

const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: `${i + 1}月`,
}))
const yearOptions = ['2024', '2025', '2026', '2027'].map((y) => ({ value: y, label: y }))

// 部门下拉复用既有的只读接口，不新造数据源
const departments = ref<{ department: string; cnt: number }[]>([])
const departmentsLoading = ref(false)
const departmentOptions = computed(() => [
  { value: '', label: '全部部门' },
  ...departments.value.map((d) => ({
    value: d.department,
    label: `${d.department}（${d.cnt}人）`,
  })),
])

const detailFields = computed(() => spec.value?.detailFields ?? [])
function isDetail(key: string) {
  return detailFields.value.includes(key)
}
function toneOf(key: string) {
  return spec.value?.detailTones[key] ?? 'muted'
}
function days(value: unknown): string[] {
  return String(value ?? '').trim().split(/\s+/).filter(Boolean)
}
function isNumeric(value: unknown) {
  return typeof value === 'number'
}

// 表格列：索引列 + 报表列。宽度沿用报表自己的定义，明细列给足空间。
interface TableColumn {
  title: string
  key: string
  dataIndex: string
  width: number
  fixed?: 'left'
  align?: 'left' | 'right' | 'center'
}

const tableColumns = computed<TableColumn[]>(() => {
  const cols: TableColumn[] = [
    { title: '#', key: '__idx', dataIndex: '__idx', width: 60, fixed: 'left' },
  ]
  for (const col of (payload.value?.columns ?? []) as ReportColumn[]) {
    const key = col.fieldname
    cols.push({
      title: col.label,
      key,
      dataIndex: key,
      width: isDetail(key) ? 260 : col.width || 110,
      // 整型右对齐：数字列对齐后才能被纵向扫描比较
      align: col.fieldtype === 'Int' ? 'right' : undefined,
    })
  }
  return cols
})

const scrollWidth = computed(() =>
  tableColumns.value.reduce((sum, c) => sum + (Number(c.width) || 110), 0),
)

const pagination = computed(() => ({
  current: page.value,
  pageSize: spec.value?.pageSize ?? 50,
  total: payload.value?.total ?? 0,
  size: 'small' as const,
  showSizeChanger: false,
  showTotal: (total: number) => `共 ${total} 行`,
}))

// 行号要跨页连续。AntD 传给 #bodyCell 的 index 是**页内下标**，
// 直接用会让第 2 页又从 1 开始。列表页用的是 globalIndex，这里与之对齐。
function rowIndex(index: number) {
  return (page.value - 1) * (spec.value?.pageSize ?? 50) + index + 1
}

function onTableChange(pag: { current?: number }) {
  const next = pag.current ?? 1
  if (next === page.value) return
  page.value = next
  load()
}

/**
 * 行唯一键。
 *
 * 不能用 employee_number：**打卡流水与考勤结果里一个人有多行**（一人多天、
 * 一天多卡），拿它当 key 会产生重复键，翻页时行会串。
 * 故按「有哪几个区分字段就用哪几个」拼：员工 + 日期/时间，逐级退让。
 */
function rowKey(record: Record<string, unknown>): string {
  const parts = [
    record.employee,
    record.import_log,
    record.attendance_date,
    record.time,
    record.employee_number,
  ].filter((v) => v !== undefined && v !== null && v !== '')
  return parts.length ? parts.join('|') : JSON.stringify(record)
}

async function loadDepartments() {
  if (departments.value.length) return
  departmentsLoading.value = true
  try {
    departments.value = await callFrappeMethod(
      'hb_attendance_app.hbos_attendance.page.hbos_employee_management.employee_management_data.get_departments',
    )
  } catch {
    // 部门列表拉不到不该阻断报表本身，静默降级为「只有全部部门」
  } finally {
    departmentsLoading.value = false
  }
}

function buildFilters(): Record<string, string> {
  const out: Record<string, string> = {}
  const f = spec.value
  if (!f) return out
  if (f.filters.includes('month') && filters.value.month) out.month = filters.value.month
  if (f.filters.includes('year') && filters.value.year) out.year = filters.value.year
  if (f.filters.includes('department') && filters.value.department) {
    out.department = filters.value.department
  }
  // 月度汇总的月份/年份与日期区间互斥（报表内部 if/elif），故月度报表不传区间
  if (f.filters.includes('date-range') && !f.filters.includes('month') && range.value) {
    out.from_date = range.value[0].format('YYYY-MM-DD')
    out.to_date = range.value[1].format('YYYY-MM-DD')
  }
  return out
}

async function load() {
  const target = spec.value
  if (!target) {
    error.value = '未知的报表'
    return
  }
  loading.value = true
  error.value = ''
  try {
    payload.value = await fetchReport(target, buildFilters(), (page.value - 1) * pageSize())
  } catch (cause) {
    payload.value = null
    error.value = (cause instanceof Error && cause.message) || '报表加载失败'
  } finally {
    loading.value = false
  }
}

function pageSize() {
  return spec.value?.pageSize ?? 50
}

function reset() {
  filters.value.month = String(today.month() + 1)
  filters.value.year = String(today.year())
  filters.value.department = ''
  range.value = initialRange()
  page.value = 1
  load()
}

onMounted(() => {
  loadDepartments()
  load()
})

// 从侧栏切到另一张报表时：把**所有**与上一张表相关的状态清掉，再取数。
// （组件被复用不会重新 mount。）
//
// 为什么必须清 filters：`department` 四张表都有，若不清，在月度汇总选了
// 「生产部」再切到打卡流水，新表会**带着旧部门条件**——看起来像数据缺失，
// 而用户以为自己什么都没选。页码同理，否则会停在上一次的页上。
watch(slug, (value) => {
  if (!value || !findReport(value)) return
  payload.value = null
  error.value = ''
  page.value = 1
  filters.value = {
    month: String(today.month() + 1),
    year: String(today.year()),
    department: '',
  }
  range.value = initialRange()
  load()
})
</script>

<style scoped>
.rep-page { display: grid; gap: 16px; }

.rep-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.rep-head h1 { margin: 6px 0 4px; font-size: 30px; line-height: 38px; }
.rep-head p { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); max-width: 70ch; }
.rep-count { font-size: 12px; color: var(--hbos-text-muted); font-variant-numeric: tabular-nums; }
.rep-count b { font-size: 20px; color: var(--hbos-text-primary); }

.rep-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: var(--hbos-radius-card);
}
.rep-alert { margin: 0; }

.rep-panel {
  padding: 12px;
  border-radius: var(--hbos-radius-card);
  overflow: hidden;
}

/* 数字右对齐 + 等宽，表格才能被纵向扫描 */
.rep-zero { color: var(--hbos-text-muted); opacity: .5; }

.rep-days { display: inline-flex; flex-wrap: wrap; gap: 3px; }
.rep-day {
  display: inline-block;
  padding: 1px 6px;
  border-radius: var(--hbos-radius-sm);
  font-size: 12px;
  line-height: 18px;
  font-variant-numeric: tabular-nums;
}
.rep-day.tone-critical { background: rgba(237, 90, 114, .12); color: var(--hbos-status-critical); }
.rep-day.tone-warning  { background: rgba(244, 165, 35, .14); color: #b8770a; }
.rep-day.tone-success  { background: rgba(27, 188, 134, .12); color: var(--hbos-status-success); }
.rep-day.tone-muted    { background: rgba(114, 130, 157, .12); color: var(--hbos-text-muted); }

@media (max-width: 720px) {
  .rep-head h1 { font-size: 20px; line-height: 28px; }
  .rep-toolbar > * { flex: 1 1 140px; }
}
</style>
