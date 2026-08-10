<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>质量标准库</h1>
        <p>检验项目、限度与方法 SOP 的版本化管理</p>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <el-table :data="specs" size="small" stripe v-loading="loading">
          <el-table-column prop="name" label="标准编号" width="240">
            <template #default="{ row }"><span class="mono">{{ row.name }}</span></template>
          </el-table-column>
          <el-table-column prop="version" label="版本" width="80">
            <template #default="{ row }"><span class="mono">{{ row.version }}</span></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <span class="pill" :class="statusClass(row.status)">{{ row.status }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="item_count" label="检验项目" width="90" align="center" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="previewSpec(row)">明细</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="showDetail" :title="`质量标准明细 · ${currentSpec?.name || ''}`" width="560">
      <el-table :data="specItems" size="small" border v-loading="specLoading">
        <el-table-column prop="item_name" label="检验项目" min-width="100" />
        <el-table-column prop="method" label="方法 / SOP" min-width="140" />
        <el-table-column prop="limits" label="限度" width="120" />
        <el-table-column prop="unit" label="单位" width="60" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listDoctype, getDoc } from '@/api/lims'

interface Spec {
  name: string
  version: string
  status: string
  item_count: number
}

const specs = ref<Spec[]>([])
const loading = ref(false)
const showDetail = ref(false)
const currentSpec = ref<Spec | null>(null)
const specItems = ref<Record<string, unknown>[]>([])
const specLoading = ref(false)

function statusClass(s: string) {
  return { 已生效: 'pill-pass', 已停用: 'pill-muted', 草稿: 'pill-info' }[s] || 'pill-muted'
}

async function loadSpecs() {
  loading.value = true
  try {
    const rows = await listDoctype<any>('HBOS Specification', ['name', 'version', 'status'], {}, 100)
    // 统计项目数量
    specs.value = await Promise.all(
      rows.map(async (r) => {
        const doc = await getDoc<any>('HBOS Specification', r.name)
        return {
          name: r.name,
          version: doc.version || r.version,
          status: doc.status || r.status,
          item_count: (doc.items || []).length,
        }
      }),
    )
  } finally {
    loading.value = false
  }
}

async function previewSpec(row: Spec) {
  currentSpec.value = row
  showDetail.value = true
  specLoading.value = true
  try {
    const doc = await getDoc<any>('HBOS Specification', row.name)
    specItems.value = (doc.items || []).map((it: any) => ({
      item_name: it.item_name || it.test_item || it.item || '',
      method: it.method || '',
      unit: it.unit || '—',
      limits: formatLimits(it),
    }))
  } finally {
    specLoading.value = false
  }
}

function formatLimits(row: any): string {
  const type = row.limits_type
  if (type === '记录型') return '记录型'
  if (type === '上限' && row.upper_limit != null) return `≤ ${row.upper_limit}`
  if (type === '下限' && row.lower_limit != null) return `≥ ${row.lower_limit}`
  if (row.lower_limit != null && row.upper_limit != null) return `${row.lower_limit} - ${row.upper_limit}`
  return '—'
}

onMounted(loadSpecs)
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-body { padding: 0; }
.panel-body :deep(.el-table) { --el-table-header-bg-color: var(--surface-2); --el-table-border-color: var(--line); }
</style>
