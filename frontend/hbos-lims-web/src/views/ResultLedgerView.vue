<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>检验结果台账</h1>
        <p>按样品汇总全部检验项目结果，随录入与任务流转同步更新</p>
      </div>
      <div class="page-actions">
        <a-button @click="loadData">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </div>
    </div>

    <div class="filter-bar">
      <a-input v-model:value="search" placeholder="搜索样品名称 / 批号 / 检验编号" allow-clear style="width:260px" />
      <a-select v-model:value="statusFilter" placeholder="全部状态" allow-clear style="width:140px">
        <a-select-option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</a-select-option>
      </a-select>
      <span class="pill muted total-pill">{{ filteredRows.length }} 个样品</span>
    </div>

    <div class="panel">
      <div class="panel-body">
        <a-table
          :columns="columns"
          :data-source="filteredRows"
          :loading="loading"
          size="small"
          row-key="sample_name"
          :pagination="{ pageSize: 20 }"
          :scroll="{ x: true }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'material_name'">
              <span class="link-text" @click="openSample">{{ record.material_name }}</span>
            </template>
            <template v-else-if="column.key === 'batch_no'"><span class="mono">{{ record.batch_no || '—' }}</span></template>
            <template v-else-if="column.key === 'sample_name'"><span class="mono">{{ record.sample_name }}</span></template>
            <template v-else-if="column.key === 'report_date'"><span class="mono">{{ record.report_date || '—' }}</span></template>
            <template v-else-if="column.key === 'request_date'"><span class="mono">{{ record.request_date || '—' }}</span></template>
            <template v-else-if="column.key === 'status'">
              <span class="pill" :class="statusClass(record.status)">{{ record.status }}</span>
            </template>
            <template v-else-if="record[column.key] !== undefined && column.key.startsWith('item_')">
              <span class="mono">{{ record[column.key]?.value ?? '—' }}</span>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && filteredRows.length === 0" class="empty-note">暂无检验结果记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { listDoctype } from '@/api/lims'

interface ItemCell {
  value: string
  verdict: string
  status: string
}

interface LedgerRow {
  sample_name: string
  material_name: string
  batch_no: string
  report_date: string
  request_date: string
  status: string
  verdict: string
  [key: string]: unknown
}

const router = useRouter()
const rows = ref<LedgerRow[]>([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')

const statusOptions = ['已登记', '检验中', '检验完成', '已放行', '已拒绝', 'OOS锁定', '草稿']

// 动态列：样品信息列 + 各检测项目列 + 判定/状态
const columns = computed(() => {
  const cols: Record<string, unknown>[] = [
    { title: '样品名称', key: 'material_name', dataIndex: 'material_name', width: 180, fixed: 'left' },
    { title: '样品批号', key: 'batch_no', dataIndex: 'batch_no', width: 150 },
    { title: '检验编号', key: 'sample_name', dataIndex: 'sample_name', width: 180 },
    { title: '报告日期', key: 'report_date', dataIndex: 'report_date', width: 110 },
    { title: '生产日期', key: 'prod_date', dataIndex: 'prod_date', width: 110 },
    { title: '请验日期', key: 'request_date', dataIndex: 'request_date', width: 110 },
    { title: '批数量', key: 'batch_qty', dataIndex: 'batch_qty', width: 90 },
    { title: '有效期/复验期至', key: 'expiry_date', dataIndex: 'expiry_date', width: 140 },
  ]
  itemNames.value.forEach((name) => {
    cols.push({ title: name, key: `item_${name}`, dataIndex: `item_${name}`, width: 110 })
  })
  cols.push({ title: '判定', key: 'verdict', dataIndex: 'verdict', width: 90 })
  cols.push({ title: '状态', key: 'status', dataIndex: 'status', width: 100, fixed: 'right' })
  return cols
})

const itemNames = ref<string[]>([])

const filteredRows = computed(() => {
  return rows.value.filter((r) => {
    const s = String(r.material_name || '') + String(r.batch_no || '') + String(r.sample_name || '')
    const matchSearch = !search.value || s.includes(search.value)
    const matchStatus = !statusFilter.value || r.status === statusFilter.value
    return matchSearch && matchStatus
  })
})

function openSample() {
  router.push(`/samples`)
}

function statusClass(s: string) {
  return {
    已批准: 'pill-pass', 已放行: 'pill-pass', 检验中: 'pill-info',
    检验完成: 'pill-primary', 已登记: 'pill-muted', 草稿: 'pill-muted',
    已拒绝: 'pill-danger', 'OOS锁定': 'pill-danger',
  }[s] || 'pill-muted'
}

// 汇总样品台账：样品 + COA(报告日期) + 检测记录按项目透视
async function loadData() {
  loading.value = true
  try {
    const [samples, results, coas, tasks] = await Promise.all([
      listDoctype<any>('HBOS Sample', ['name', 'material_name', 'batch_no', 'creation', 'status'], {}, 200),
      listDoctype<any>(
        'HBOS Test Result',
        ['sample', 'item_name', 'result_value', 'unit', 'verdict', 'result_status'],
        {},
        500,
      ),
      listDoctype<any>('HBOS COA', ['sample', 'report_status', 'published_at'], {}, 200),
      listDoctype<any>('HBOS Sample Task', ['test_item', 'item_name', 'creation'], {}, 500, 'creation asc'),
    ])

    // 检测记录按样品 + 项目透视
    const coaMap = new Map<string, string>()
    coas.forEach((c: any) => {
      if (c.report_status === '已发布' && c.published_at) {
        coaMap.set(c.sample, String(c.published_at).slice(0, 10))
      }
    })

    // 项目列顺序：按检测任务创建顺序（含量测定→水分→干燥失重），反映检验项目顺序
    const taskOrder: string[] = []
    tasks.forEach((t: any) => {
      const n = t.item_name || ''
      if (n && !taskOrder.includes(n)) taskOrder.push(n)
    })

    const resultBySample = new Map<string, Record<string, ItemCell>>()
    const names = new Set<string>()
    results.forEach((r: any) => {
      if (!r.sample) return
      const name = r.item_name || ''
      names.add(name)
      const itemName = `item_${name}`
      if (!resultBySample.has(r.sample)) resultBySample.set(r.sample, {})
      const cells = resultBySample.get(r.sample)!
      // 取已批准/已提交的最新记录值（优先非草稿）
      if (!cells[itemName] || (r.result_status !== '草稿' && cells[itemName].status === '草稿')) {
        cells[itemName] = {
          value: r.result_value != null ? `${r.result_value}${r.unit || ''}` : '—',
          verdict: r.verdict || '',
          status: r.result_status || '',
        }
      }
    })
    // 项目列顺序：任务顺序优先，未知项目按出现顺序
    const ordered = taskOrder.filter((n) => names.has(n))
    Array.from(names).forEach((n) => {
      if (!ordered.includes(n)) ordered.push(n)
    })
    itemNames.value = ordered

    rows.value = (samples as any[]).map((s) => {
      const row: LedgerRow = {
        sample_name: s.name,
        material_name: s.material_name || '',
        batch_no: s.batch_no || '',
        report_date: coaMap.get(s.name) || '',
        prod_date: '', // 后端暂未存储，留空
        request_date: s.creation ? String(s.creation).slice(0, 10) : '',
        batch_qty: '', // 后端暂未存储，留空
        expiry_date: '', // 后端暂未存储，留空
        status: s.status || '',
        verdict: '',
      }
      const cells = resultBySample.get(s.name) || {}
      itemNames.value.forEach((name) => {
        row[`item_${name}`] = cells[`item_${name}`] || null
      })
      // 汇总判定：取已批准项目判定；如有不合格则不合格
      const approved = Object.values(cells)
      if (approved.some((c) => c.verdict === '不合格')) {
        row.verdict = '不合格'
      } else if (approved.some((c) => c.verdict === '合格')) {
        row.verdict = '合格'
      } else if (approved.length > 0) {
        row.verdict = '不适用'
      }
      return row
    })
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.total-pill { margin-left: auto; }
.link-text { color: var(--primary); cursor: pointer; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-body { padding: 0; }
.panel-body :deep(.ant-table) { font-size: 13px; }
.panel-body :deep(.ant-table-thead th) { white-space: nowrap; }
.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }
</style>
