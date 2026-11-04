<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { ApartmentOutlined, FilterOutlined } from '@ant-design/icons-vue'

// The department directory is a bounded list, not a long explanation page: search
// is always visible, filters are secondary, and very long names keep two lines
// with a real (keyboard/touch) control to read the whole name and its path.
export interface DepartmentEntry { id: string; name: string; depth: number; path?: string; company?: string }
const props = withDefaults(defineProps<{
  entries: DepartmentEntry[]
  selected: string
  search: string
  filtersOpen?: boolean
  groupsAvailable?: boolean
  viewGroup?: string
  companies?: Array<{ id: string; name: string }>
  company?: string
  disabled?: boolean
}>(), { filtersOpen: false, groupsAvailable: false, viewGroup: 'daily', companies: () => [], company: '', disabled: false })
const emit = defineEmits<{
  select: [id: string]
  'update:search': [value: string]
  'update:filtersOpen': [value: boolean]
  'update:viewGroup': [value: string]
  'update:company': [value: string]
}>()
const expanded = ref<string[]>([])
const rowsRef = ref<HTMLElement | null>(null)
const rows = computed(() => props.entries.map(row => ({
  ...row,
  long: [...row.name].length > 30,
  open: expanded.value.includes(row.id),
})))
function toggleOpen(id: string) {
  expanded.value = expanded.value.includes(id) ? expanded.value.filter(value => value !== id) : [...expanded.value, id]
}
async function selectRow(id: string) {
  if (props.disabled || id === props.selected) return
  emit('select', id)
  await nextTick()
}
// Keep the current department reachable without hunting in the list.
async function reveal() {
  await nextTick()
  const list = rowsRef.value
  if (!list) return
  const row = list.querySelector<HTMLElement>('[aria-current="page"]')?.closest<HTMLElement>('.r6-department-row')
  if (!row) return
  const listRect = list.getBoundingClientRect(), rowRect = row.getBoundingClientRect()
  if (rowRect.top < listRect.top) list.scrollTop -= listRect.top - rowRect.top
  else if (rowRect.bottom > listRect.bottom) list.scrollTop += rowRect.bottom - listRect.bottom
}
watch(() => props.selected, reveal, { flush: 'post' })
watch(rows, reveal, { flush: 'post' })
onMounted(reveal)
watch(() => props.entries, rowsNow => {
  const ids = new Set(rowsNow.map(row => row.id))
  expanded.value = expanded.value.filter(id => ids.has(id))
})
</script>
<template>
  <div class="r6-department-directory">
    <div class="r6-department-directory__head">
      <h3>部门目录</h3>
      <a-button type="text" class="r6-department-directory__filter" :aria-expanded="filtersOpen" @click="emit('update:filtersOpen', !filtersOpen)"><FilterOutlined /> 筛选</a-button>
    </div>
    <a-input :value="search" placeholder="搜索部门" aria-label="搜索部门" allow-clear class="r6-department-directory__search" @update:value="(value: string) => emit('update:search', value)" />
    <div v-if="filtersOpen" class="r6-department-directory__filters">
      <a-select v-if="groupsAvailable" :value="viewGroup" aria-label="部门分组" @change="(value: string) => emit('update:viewGroup', value)">
        <a-select-option value="daily">日常组织</a-select-option>
        <a-select-option value="technical">技术验证夹具</a-select-option>
        <a-select-option value="all">全部部门</a-select-option>
      </a-select>
      <a-select v-if="companies.length > 1" :value="company" aria-label="部门所属公司" @change="(value: string) => emit('update:company', value)">
        <a-select-option v-for="item in companies" :key="item.id" :value="item.id">{{ item.name }}</a-select-option>
      </a-select>
    </div>
    <nav ref="rowsRef" class="r6-department-rows" aria-label="部门列表">
      <div v-for="item in rows" :key="item.id" class="r6-department-row" :class="{ selected: selected === item.id, long: item.long }" :style="{ '--department-indent': `${Math.min(item.depth, 3) * 12}px` }">
        <button type="button" class="r6-department-row__main" :aria-current="selected === item.id ? 'page' : undefined" :aria-label="`选择部门 ${item.name}`" :disabled="disabled" @click="selectRow(item.id)">
          <ApartmentOutlined aria-hidden="true" />
          <span class="r6-department-row__label" :class="{ 'is-clamped': item.long && !item.open }">{{ item.name }}</span>
        </button>
        <button v-if="item.long" type="button" class="r6-department-row__more" :aria-expanded="item.open" :aria-label="`${item.open ? '收起' : '展开'}部门完整名称：${item.name}`" @click="toggleOpen(item.id)">{{ item.open ? '收起' : '完整名称' }}</button>
        <p v-if="item.long && item.open" class="r6-department-row__full">{{ item.name }}<small v-if="item.path">{{ item.path }}</small></p>
      </div>
      <a-empty v-if="!rows.length" description="没有匹配的部门" />
    </nav>
  </div>
</template>
