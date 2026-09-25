<template>
  <section class="inventory-page report-page">
    <div class="report-head">
      <div>
        <h1>{{ meta.title }}</h1>
        <p>{{ meta.sub }}</p>
      </div>
      <div v-if="state === 'ready'" class="report-meta">
        <b>{{ rows.length }}</b>
        行 · 查询于 {{ queriedAt }}
      </div>
    </div>

    <!-- 报表特定说明 -->
    <div v-if="meta.notice" class="report-verdict" :class="meta.notice.tone">
      <WarningOutlined v-if="meta.notice.tone === 'warn'" />
      <InfoCircleOutlined v-else />
      <div v-html="meta.notice.html"></div>
    </div>

    <!-- 筛选栏（EA-5.4 §22：高频铺开，低频进「更多筛选」） -->
    <div class="report-filterbar">
      <label v-for="f in meta.primaryFilters" :key="f.fieldname" class="report-filter"
             :class="{ 'report-filter-inline': f.kind === 'check' }">
        <span v-if="f.kind !== 'check'">{{ f.label }}</span>
        <a-checkbox
          v-if="f.kind === 'check'"
          :checked="Boolean(filters[f.fieldname])"
          @change="(e: any) => setFilter(f.fieldname, e.target.checked)"
        >{{ f.label }}</a-checkbox>
        <a-input-number
          v-else-if="f.kind === 'number'"
          :value="filters[f.fieldname] as number"
          :min="1"
          style="width: 170px"
          @change="(v: any) => setFilter(f.fieldname, v)"
        />
        <a-input
          v-else
          :value="filters[f.fieldname] as string"
          :placeholder="f.placeholder"
          style="width: 210px"
          allow-clear
          @change="(e: any) => setFilter(f.fieldname, e.target.value)"
          @press-enter="run"
        />
        <small v-if="f.description" class="report-filter-hint">{{ f.description }}</small>
      </label>

      <div class="report-filterbar-spacer"></div>

      <div class="report-filterbar-actions">
        <a-popover v-model:open="moreOpen" trigger="click" placement="bottomRight">
          <template #content>
            <div class="report-more">
              <label v-for="f in meta.extraFilters" :key="f.fieldname" class="report-filter">
                <span>{{ f.label }}</span>
                <a-select
                  v-if="f.kind === 'select'"
                  :value="(filters[f.fieldname] as string) || ''"
                  style="width: 200px"
                  @change="(v: any) => setFilter(f.fieldname, v)"
                >
                  <a-select-option v-for="o in f.options || []" :key="o" :value="o">
                    {{ o === '' ? '全部' : o }}
                  </a-select-option>
                </a-select>
                <a-input
                  v-else
                  :value="filters[f.fieldname] as string"
                  :placeholder="f.placeholder"
                  style="width: 200px"
                  allow-clear
                  @change="(e: any) => setFilter(f.fieldname, e.target.value)"
                />
              </label>
            </div>
          </template>
          <a-button>
            <FilterOutlined /> 更多筛选
          </a-button>
        </a-popover>

        <a-button type="primary" :loading="state === 'loading'" @click="run">
          <ReloadOutlined /> 查询
        </a-button>
        <a-button :loading="exporting" @click="doExport">
          <DownloadOutlined /> 导出 Excel
        </a-button>
      </div>
    </div>

    <div class="inventory-dest glass-surface">
      <!-- 查询中：骨架与最终行高同尺寸 -->
      <div v-if="state === 'loading'" style="padding: 20px" aria-busy="true" aria-label="正在查询报表">
        <div v-for="n in 6" :key="n" class="report-skel report-skel-row" :style="{ width: n === 6 ? '64%' : '100%' }"></div>
      </div>

      <!-- 无权限 -->
      <div v-else-if="state === 'denied'" class="inventory-state err" style="padding: 32px 20px">
        <LockOutlined class="inventory-state-icon" />
        <h3>你没有查看这张报表的权限</h3>
        <p>报表按角色放行。若你认为这是配置错误，请联系业务管理员。</p>
        <div class="inventory-state-actions">
          <a-button type="primary" @click="$router.push('/hbos/inventory')">返回库存概览</a-button>
        </div>
      </div>

      <!-- 出错：必须明确否定「没有数据」这个误读 -->
      <div v-else-if="state === 'error'" class="inventory-state err" style="padding: 32px 20px">
        <StopOutlined class="inventory-state-icon" />
        <h3>报表没跑起来</h3>
        <p>
          服务端返回了错误，这次查询没拿到数据。<b>这不是「没有数据」</b>——
          请重试；若反复失败，联系管理员查看错误日志。
        </p>
        <p v-if="errorText" style="color: var(--hbos-text-muted); font-size: var(--hbos-font-meta)">
          {{ errorText }}
        </p>
        <div class="inventory-state-actions">
          <a-button type="primary" @click="run">重新查询</a-button>
        </div>
      </div>

      <!-- 无结果：文案因地制宜，不用千篇一律的「暂无数据」 -->
      <div v-else-if="state === 'empty'" class="inventory-state ok" style="padding: 32px 20px">
        <InboxOutlined class="inventory-state-icon" />
        <h3>{{ meta.emptyTitle }}</h3>
        <p>{{ meta.emptyBody }}</p>
        <div class="inventory-state-actions">
          <a-button @click="clearFilters">清空筛选条件</a-button>
        </div>
      </div>

      <!-- 有数据 -->
      <div v-else>
        <div class="report-table-wrap">
          <table class="report-table">
            <thead>
              <tr>
                <th
                  v-for="col in visibleColumns"
                  :key="col.fieldname"
                  :class="{ num: isNumeric(col) }"

                >
                  {{ col.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in rows" :key="i">
                <td
                  v-for="col in visibleColumns"
                  :key="col.fieldname"
                  :class="{ num: isNumeric(col) }"
                >
                  <component :is="renderCell(col, row[col.fieldname])" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="truncatedNote" class="report-truncated">{{ truncatedNote }}</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import {
  DownloadOutlined,
  FilterOutlined,
  InfoCircleOutlined,
  InboxOutlined,
  LockOutlined,
  ReloadOutlined,
  StopOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  ALWAYS_HIDDEN_WHEN_EMPTY,
  findReport,
  type ReportFilter,
} from '@/data/inventoryReports'
import {
  exportReport,
  runReport,
  type ReportColumn,
} from '@/services/inventoryReports'
import { FrappeHttpError } from '@/services/frappeClient'

const route = useRoute()
const router = useRouter()

const meta = computed(() => findReport(String(route.params.reportId || '')) || findReport('location-detail')!)

type ViewState = 'loading' | 'ready' | 'empty' | 'error' | 'denied'

const state = ref<ViewState>('loading')
const columns = ref<ReportColumn[]>([])
const rows = ref<Array<Record<string, unknown>>>([])
const filters = ref<Record<string, unknown>>({})
const queriedAt = ref('—')
const errorText = ref('')
const moreOpen = ref(false)
const exporting = ref(false)
const truncatedNote = ref('')

// --- 筛选初始化：从 URL 读（可分享、可后退） ---
function initialFilters(): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  const query = route.query

  for (const f of [...meta.value.primaryFilters, ...meta.value.extraFilters]) {
    const raw = query[f.fieldname]
    if (raw !== undefined && raw !== null && raw !== '') {
      out[f.fieldname] = parseFilterValue(f, String(raw))
      continue
    }
    // URL 没带就取默认值
    if (f.kind === 'check') out[f.fieldname] = Boolean(f.defaultChecked)
    else if (f.kind === 'number' && f.defaultValue !== undefined) out[f.fieldname] = f.defaultValue
    else out[f.fieldname] = ''
  }
  // 报表自己声明的字段之外的 query 参数不理会——避免把任意参数透传给服务端
  return out
}

function parseFilterValue(f: ReportFilter, raw: string): unknown {
  if (f.kind === 'check') return raw === '1' || raw === 'true'
  if (f.kind === 'number') {
    const n = Number(raw)
    return Number.isFinite(n) ? n : undefined
  }
  return raw
}

/** 筛选写回 URL：刷新不丢、可分享、可后退 */
function syncUrl() {
  const query: Record<string, string> = {}
  for (const [key, value] of Object.entries(filters.value)) {
    if (value === '' || value === null || value === undefined) continue
    query[key] = typeof value === 'boolean' ? (value ? '1' : '0') : String(value)
  }
  void router.replace({ path: route.path, query })
}

function setFilter(fieldname: string, value: unknown) {
  filters.value = { ...filters.value, [fieldname]: value }
}

function clearFilters() {
  const cleared: Record<string, unknown> = {}
  for (const f of [...meta.value.primaryFilters, ...meta.value.extraFilters]) {
    cleared[f.fieldname] = f.kind === 'check' ? false : ''
  }
  filters.value = cleared
  void run()
}

// --- 列 ---
/** 数值列右对齐（EA-5.4 §21）——扫读时竖列能对 */
function isNumeric(col: ReportColumn): boolean {
  return ['Int', 'Float', 'Currency', 'Percent'].includes(col.fieldtype)
}

/**
 * 只用于呈现的字段类型判断，与 isNumeric 分开：
 * 前者按**服务端给的 fieldtype** 决定对齐，后者按同一份定义决定渲染。
 */
function isDate(col: ReportColumn): boolean {
  return ['Date', 'Datetime'].includes(col.fieldtype)
}

/** 服务端明确算不出、整列必空的字段（目前只有库级盘点那三列由现场填写） */
const hiddenWhenEmpty = computed(() => new Set(ALWAYS_HIDDEN_WHEN_EMPTY[meta.value.id] || []))

/**
 * 要显示的列。
 *
 * **只隐藏「报表明确算不出」的列**（`ALWAYS_HIDDEN_WHEN_EMPTY` 白名单），
 * 不是通用的「空列就藏」——一列里偶尔为空是正常数据，藏了会让人以为报表缺列。
 */
const visibleColumns = computed(() =>
  columns.value.filter((col) => {
    if (!hiddenWhenEmpty.value.has(col.fieldname)) return true
    // 白名单里的列：整列全空才隐藏；万一将来报表真填上了，就照常显示
    return rows.value.some((row) => {
      const v = row[col.fieldname]
      return v !== null && v !== undefined && v !== ''
    })
  }),
)

// --- 单元格渲染 ---
const RELEASE_CLASS: Record<string, string> = {
  待检: 'pending',
  已放行: 'released',
  不放行: 'blocked',
}

const URGENCY_CLASS: Record<string, string> = {
  已过期: 'critical',
  '紧急（≤30 天）': 'critical',
  '关注（≤90 天）': 'warning',
  正常: 'neutral',
}

function isEmptyValue(value: unknown): boolean {
  return value === null || value === undefined || value === ''
}

/**
 * 单元格渲染。
 *
 * 值→语义的映射（放行状态、紧急度）是前端的事；列本身与数值来自服务端。
 * 空值一律显示 `—` 而不是留白——留白会让人怀疑是不是渲染坏了。
 */
function renderCell(col: ReportColumn, value: unknown) {
  if (isEmptyValue(value)) {
    return () => h('span', { class: 'report-dash' }, '—')
  }

  if (col.fieldname === 'release_status') {
    const cls = RELEASE_CLASS[String(value)] || 'neutral'
    return () => h('span', { class: `report-tag ${cls}` }, String(value))
  }

  if (col.fieldname === 'urgency') {
    const cls = URGENCY_CLASS[String(value)] || 'neutral'
    return () => h('span', { class: `report-tag ${cls}` }, String(value))
  }

  if (isNumeric(col)) {
    return () => h('span', { class: 'report-num' }, formatNumber(value, col.precision))
  }

  if (isDate(col)) {
    return () => h('span', { class: 'report-mono' }, String(value))
  }

  // 物料 / 货位 / 批号这类实体，等宽更好扫读
  if (['item_code', 'warehouse', 'batch_no', 'uom', 'supplier_batch_no'].includes(col.fieldname)) {
    return () => h('span', { class: 'report-mono' }, String(value))
  }

  if (col.fieldname === 'item_name') {
    return () => h('span', { class: 'report-strong' }, String(value))
  }

  return () => h('span', {}, String(value))
}

function formatNumber(value: unknown, precision?: number): string {
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  return precision === undefined || precision === null ? String(n) : n.toFixed(precision)
}

// --- 查询 ---
function filtersForServer(): Record<string, unknown> {
  // `''` 与 `false` 都不该作为条件传过去：它们和「不限」是一回事
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(filters.value)) {
    if (value === '' || value === null || value === undefined) continue
    if (value === false) continue
    out[key] = value
  }
  return out
}

async function run() {
  syncUrl()
  state.value = 'loading'
  errorText.value = ''
  truncatedNote.value = ''

  try {
    const result = await runReport(meta.value.reportName, filtersForServer())
    columns.value = result.columns
    rows.value = result.rows
    queriedAt.value = timeLabel()

    if (!result.rows.length) {
      state.value = 'empty'
      return
    }

    // 报表若开了合计行会被上面过滤掉——如实说明，不静默少渲染
    if (result.columns.length && !result.rows.length) {
      truncatedNote.value = '服务端返回了合计行，已略过。'
    }

    state.value = 'ready'
  } catch (error) {
    // 无权限与其它错误分开呈现：用户的下一步动作完全不同
    if (error instanceof FrappeHttpError && (error.status === 403 || error.status === 417)) {
      state.value = 'denied'
      return
    }
    state.value = 'error'
    errorText.value = error instanceof FrappeHttpError ? error.message : ''
  }
}

function timeLabel(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function doExport() {
  exporting.value = true
  try {
    await exportReport(meta.value.reportName, filtersForServer())
  } catch (error) {
    Modal.error({
      title: '导出失败',
      content: error instanceof Error ? error.message : '导出未成功，请重试。',
    })
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  filters.value = initialFilters()
  void run()
})

// 报表之间切换（同一个组件，只是路由参数变了）时重来一遍
watch(
  () => route.params.reportId,
  () => {
    filters.value = initialFilters()
    void run()
  },
)
</script>
