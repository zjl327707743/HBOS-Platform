<template>
  <section class="lst-page">
    <header class="lst-head">
      <div>
        <span class="page-kicker">ATTENDANCE · 记录</span>
        <h1>{{ payload?.title || navLabel }}</h1>
        <p>{{ payload?.hint }}</p>
      </div>
      <span class="lst-count" v-if="!loading && !error">
        共 <b>{{ payload?.total ?? 0 }}</b> 条
      </span>
    </header>

    <div class="lst-toolbar glass-surface">
      <template v-for="field in filterFields" :key="field">
        <a-select
          v-model:value="filters[field]"
          :options="options[field] || []"
          :placeholder="filterLabel(field)"
          :loading="optionsLoading[field]"
          show-search
          allow-clear
          option-filter-prop="label"
          style="width: 200px"
          @change="reloadFromFirstPage"
        />
      </template>
      <a-button type="primary" :loading="loading" @click="reloadFromFirstPage">查询</a-button>
      <a-button :disabled="loading" @click="reset">重置</a-button>
    </div>

    <a-alert v-if="error" type="error" show-icon :message="error" class="lst-alert" />

    <div v-else class="lst-panel glass-surface">
      <a-table
        :data-source="payload?.rows || []"
        :columns="tableColumns"
        :loading="loading"
        :pagination="pagination"
        :scroll="{ x: scrollWidth }"
        :row-key="rowKey"
        size="middle"
        @change="onTableChange"
      >
        <template #bodyCell="{ column, record, index }">
          <template v-if="column.key === '__idx'">{{ globalIndex(index) }}</template>
          <template v-else-if="columnKind(column.key) === 'status'">
            <a-tag v-if="record[column.key]" :color="statusColor(record[column.key])">
              {{ record[column.key] }}
            </a-tag>
            <span v-else class="lst-zero">—</span>
          </template>
          <template v-else-if="columnKind(column.key) === 'bool'">
            <a-tag :color="record[column.key] ? 'warning' : 'default'">
              {{ record[column.key] ? '是' : '否' }}
            </a-tag>
          </template>
          <template v-else-if="columnKind(column.key) === 'int'">
            <span :class="{ 'lst-zero': !record[column.key] }">{{ record[column.key] || 0 }}</span>
          </template>
          <template v-else-if="isBlank(record[column.key])">
            <span class="lst-zero">—</span>
          </template>
        </template>
      </a-table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  fetchFilterOptions,
  fetchList,
  LIST_PAGE_SIZE,
  type ListColumn,
  type ListPayload,
} from '@/services/attendanceLists'
import { findNavBySlug } from '@/services/attendanceNav'

const route = useRoute()

const payload = ref<ListPayload | null>(null)
const loading = ref(false)
const error = ref('')
const page = ref(1)
const filters = ref<Record<string, string>>({})
const options = ref<Record<string, { value: string; label: string }[]>>({})
const optionsLoading = ref<Record<string, boolean>>({})

const slug = computed(() => String(route.params.slug ?? ''))
const navLabel = computed(() => findNavBySlug(slug.value)?.label || '记录')

// 后端返回的 columns 是权威；筛选字段从列里推断（这些表可筛选的就是几个枚举列）
const filterFields = computed(() => payload.value?.filter_fields ?? [])

function columnKind(key: string): string | undefined {
  return (payload.value?.columns || []).find((c) => c.fieldname === key)?.kind
}

function filterLabel(field: string): string {
  const col = (payload.value?.columns || []).find((c) => c.fieldname === field)
  return col?.label || field
}

interface TableColumn {
  title: string
  key: string
  dataIndex: string
  width: number
  fixed?: 'left'
  align?: 'left' | 'right'
}

const tableColumns = computed<TableColumn[]>(() => {
  const cols: TableColumn[] = [
    { title: '#', key: '__idx', dataIndex: '__idx', width: 64, fixed: 'left' },
  ]
  for (const col of (payload.value?.columns || []) as ListColumn[]) {
    const numeric = col.kind === 'int' || col.kind === 'num'
    cols.push({
      title: col.label,
      key: col.fieldname,
      dataIndex: col.fieldname,
      width: col.width || 120,
      align: numeric ? 'right' : 'left',
    })
  }
  return cols
})

const scrollWidth = computed(() =>
  tableColumns.value.reduce((sum, c) => sum + (Number(c.width) || 120), 0),
)

const pagination = computed(() => ({
  current: page.value,
  pageSize: LIST_PAGE_SIZE,
  total: payload.value?.total ?? 0,
  size: 'small' as const,
  showSizeChanger: false,
  showTotal: (total: number) => `共 ${total} 条`,
}))

function globalIndex(index: number) {
  return (page.value - 1) * LIST_PAGE_SIZE + index + 1
}

function isBlank(value: unknown) {
  return value === null || value === undefined || value === ''
}

/** 状态色：只按语义归类，不为每个取值发明颜色（避免一屏五颜六色）。 */
function statusColor(value: unknown): string {
  const v = String(value)
  if (/已通过|已核实|成功|完成|生效|正常/.test(v)) return 'success'
  if (/不通过|失败|拒绝|已撤回|异常/.test(v)) return 'error'
  if (/待|进行中|解析中/.test(v)) return 'processing'
  if (/停用|已删除|草稿/.test(v)) return 'default'
  return 'blue'
}

/**
 * 行唯一键。
 *
 * 优先用 `name`——那是 DocType 的稳定主键，也是唯一可靠的去重依据。
 * 四个列表的 spec 现在都显式带上了 `name` 字段（见 list_data.LIST_SPECS），
 * 所以正常情况下走的都是第一个分支。
 *
 * 兜底到整行 JSON：仅在字段缺失时用到，且它**不能保证唯一**——
 * 两行显示值完全相同就会撞键。故这是安全网，不是常态。
 */
function rowKey(record: Record<string, unknown>, index: number): string {
  return String(record.name ?? `${index}:${JSON.stringify(record)}`)
}

async function loadOptions() {
  for (const field of filterFields.value) {
    if (options.value[field]) continue
    optionsLoading.value[field] = true
    try {
      options.value[field] = await fetchFilterOptions(slug.value, field)
    } catch {
      options.value[field] = []
    } finally {
      optionsLoading.value[field] = false
    }
  }
}

function activeFilters(): Record<string, string> {
  const out: Record<string, string> = {}
  for (const field of filterFields.value) {
    const v = filters.value[field]
    if (v) out[field] = v
  }
  return out
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    payload.value = await fetchList(
      slug.value,
      activeFilters(),
      (page.value - 1) * LIST_PAGE_SIZE,
      LIST_PAGE_SIZE,
    )
    // 筛选字段由后端给出（白名单），首屏拿到后即可渲染筛选条
    await loadOptions()
  } catch (cause) {
    payload.value = null
    error.value = (cause instanceof Error && cause.message) || '列表加载失败'
  } finally {
    loading.value = false
  }
}

function reloadFromFirstPage() {
  page.value = 1
  load()
}

function reset() {
  filters.value = {}
  reloadFromFirstPage()
}

function onTableChange(pag: { current?: number }) {
  const next = pag.current ?? 1
  if (next === page.value) return
  page.value = next
  load()
}

onMounted(load)

// 侧栏切到另一个列表：重置筛选与页码（否则会带着上一张表的条件去查）
watch(slug, (value) => {
  if (!value) return
  payload.value = null
  filters.value = {}
  page.value = 1
  options.value = {}
  load()
})
</script>

<style scoped>
.lst-page { display: grid; gap: 16px; }

.lst-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.lst-head h1 { margin: 6px 0 4px; font-size: 30px; line-height: 38px; }
.lst-head p { margin: 0; font-size: 14px; line-height: 22px; color: var(--hbos-text-secondary); max-width: 70ch; }
.lst-count { font-size: 12px; color: var(--hbos-text-muted); font-variant-numeric: tabular-nums; }
.lst-count b { font-size: 20px; color: var(--hbos-text-primary); }

.lst-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: var(--hbos-radius-card);
}
.lst-alert { margin: 0; }

.lst-panel {
  padding: 12px;
  border-radius: var(--hbos-radius-card);
  overflow: hidden;
}

.lst-zero { color: var(--hbos-text-muted); opacity: .5; }

@media (max-width: 720px) {
  .lst-head h1 { font-size: 20px; line-height: 28px; }
  .lst-toolbar > * { flex: 1 1 140px; }
}
</style>
