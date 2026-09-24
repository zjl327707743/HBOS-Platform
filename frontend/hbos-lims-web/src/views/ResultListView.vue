<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>检验结果清单</h1>
        <p>全部检测记录的录入、复核与批准入口</p>
      </div>
    </div>

    <div class="filter-bar">
      <a-input v-model:value="search" placeholder="搜索记录号 / 样品 / 项目" allow-clear style="width:240px" />
      <a-select v-model:value="statusFilter" placeholder="全部状态" allow-clear style="width:140px">
        <a-select-option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</a-select-option>
      </a-select>
      <a-select v-model:value="verdictFilter" placeholder="全部判定" allow-clear style="width:140px">
        <a-select-option value="合格">合格</a-select-option>
        <a-select-option value="不合格">不合格</a-select-option>
        <a-select-option value="不适用">不适用</a-select-option>
      </a-select>
      <span class="pill muted total-pill">{{ filteredResults.length }} 条记录</span>
    </div>

    <div class="panel">
      <div class="panel-body">
        <a-table
          :columns="columns"
          :data-source="filteredResults"
          :loading="loading"
          size="small"
          row-key="result_name"
          :pagination="{ pageSize: 20 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'result_name'"><span class="mono">{{ record.result_name }}</span></template>
            <template v-else-if="column.key === 'sample'"><span class="mono">{{ record.sample }}</span></template>
            <template v-else-if="column.key === 'result_value'">
              <span class="mono">{{ record.result_value != null ? `${record.result_value}${record.unit || ''}` : '—' }}</span>
            </template>
            <template v-else-if="column.key === 'verdict'">
              <span class="pill" :class="verdictClass(record.verdict)">{{ record.verdict || '—' }}</span>
            </template>
            <template v-else-if="column.key === 'result_status'">
              <span class="pill" :class="statusClass(record.result_status)">{{ record.result_status }}</span>
            </template>
            <template v-else-if="column.key === 'analyst'"><span class="mono">{{ record.analyst }}</span></template>
            <template v-else-if="column.key === 'actions'">
              <a-button type="link" size="small" @click="openResult(record)">录入/查看</a-button>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && filteredResults.length === 0" class="empty-note">暂无检测记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { runReport } from '@/api/lims'

interface ResultRow {
  result_name: string
  sample: string
  batch_no: string
  item_name: string
  result_value: number | null
  unit: string
  verdict: string
  analyst: string
  result_status: string
}

const router = useRouter()
const results = ref<ResultRow[]>([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const verdictFilter = ref('')

const statusOptions = ['草稿', '已提交', '已复核', '已批准', '已修订']

const columns = [
  { title: '记录号', key: 'result_name', dataIndex: 'result_name', width: 170 },
  { title: '样品编号', key: 'sample', dataIndex: 'sample', width: 190 },
  { title: '检验项目', key: 'item_name', dataIndex: 'item_name' },
  { title: '结果值', key: 'result_value', dataIndex: 'result_value', width: 100 },
  { title: '判定', key: 'verdict', dataIndex: 'verdict', width: 90 },
  { title: '状态', key: 'result_status', dataIndex: 'result_status', width: 100 },
  { title: '检验员', key: 'analyst', dataIndex: 'analyst', width: 140 },
  { title: '操作', key: 'actions', width: 100 },
]

const filteredResults = computed(() => {
  return results.value.filter((r) => {
    const s = String(r.result_name) + String(r.sample) + String(r.item_name)
    const matchSearch = !search.value || s.includes(search.value)
    const matchStatus = !statusFilter.value || r.result_status === statusFilter.value
    const matchVerdict = !verdictFilter.value || r.verdict === verdictFilter.value
    return matchSearch && matchStatus && matchVerdict
  })
})

function openResult(row: ResultRow) {
  router.push(`/results/${row.result_name}`)
}

function statusClass(s: string) {
  return {
    草稿: 'pill-muted', 已提交: 'pill-info', 已复核: 'pill-warn',
    已批准: 'pill-pass', 已修订: 'pill-danger',
  }[s] || 'pill-muted'
}
function verdictClass(v: string) {
  return { 合格: 'pill-pass', 不合格: 'pill-danger', 不适用: 'pill-info' }[v] || 'pill-muted'
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await runReport('检验结果清单')
    results.value = (res.result || []) as unknown as ResultRow[]
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-head { margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.total-pill { margin-left: auto; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-body { padding: 0; }
.panel-body :deep(.ant-table) { font-size: 13px; }
.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }
</style>
