<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>审计追踪查询</h1>
        <p>检验结果修订与关键操作的合规审计记录（只读）</p>
      </div>
    </div>

    <div class="filter-bar">
      <a-input v-model:value="filters.search" placeholder="搜索对象 / 修订号" allow-clear style="width:220px" />
      <a-select v-model:value="filters.operator" placeholder="操作人" allow-clear style="width:180px">
        <a-select-option v-for="o in operators" :key="o" :value="o">{{ o }}</a-select-option>
      </a-select>
      <a-range-picker
        v-model:value="filters.dateRange"
        value-format="YYYY-MM-DD"
        style="width:260px"
      />
      <span class="pill muted total-pill">{{ filteredAudits.length }} 条修订记录</span>
    </div>

    <div class="panel">
      <div class="panel-body">
        <a-table
          :columns="columns"
          :data-source="filteredAudits"
          :loading="loading"
          size="small"
          :pagination="{ pageSize: 20 }"
          row-key="revision_name"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'revision_name'"><span class="mono">{{ record.revision_name }}</span></template>
            <template v-else-if="column.key === 'result'"><span class="mono">{{ record.result }}</span></template>
            <template v-else-if="column.key === 'changed_at'"><span class="mono">{{ (record.changed_at || '').slice(0, 16) }}</span></template>
            <template v-else-if="column.key === 'changed_by'"><span class="mono">{{ record.changed_by }}</span></template>
            <template v-else-if="column.key === 'diff'">
              <span class="old">{{ record.old_value || '—' }}</span>
              <span class="arrow">→</span>
              <span class="new">{{ record.new_value || '—' }}</span>
              <span class="field-tag mono">({{ fieldLabel(record.field_changed) }})</span>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && filteredAudits.length === 0" class="empty-note">暂无匹配的审计记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { runReport } from '@/api/lims'

interface AuditRow {
  revision_name: string
  result: string
  field_changed: string
  old_value: string
  new_value: string
  changed_by: string
  changed_at: string
  change_reason: string
}

const audits = ref<AuditRow[]>([])
const loading = ref(false)
const filters = reactive({ search: '', operator: '', dateRange: [] as string[] })

const operators = computed(() => [...new Set(audits.value.map((a) => a.changed_by))])

const columns = [
  { title: '修订号', key: 'revision_name', dataIndex: 'revision_name', width: 170 },
  { title: '结果记录', key: 'result', dataIndex: 'result', width: 170 },
  { title: '修改时间', key: 'changed_at', dataIndex: 'changed_at', width: 160 },
  { title: '操作人', key: 'changed_by', dataIndex: 'changed_by', width: 150 },
  { title: '变更内容', key: 'diff', width: 220 },
  { title: '修订原因', key: 'change_reason', dataIndex: 'change_reason' },
]

const filteredAudits = computed(() => {
  return audits.value.filter((a) => {
    const matchSearch = !filters.search ||
      String(a.result || '').includes(filters.search) ||
      String(a.revision_name || '').includes(filters.search)
    const matchOp = !filters.operator || a.changed_by === filters.operator
    let matchDate = true
    if (filters.dateRange && filters.dateRange.length === 2) {
      const t = String(a.changed_at || '').slice(0, 10)
      matchDate = t >= String(filters.dateRange[0]) && t <= String(filters.dateRange[1])
    }
    return matchSearch && matchOp && matchDate
  })
})

function fieldLabel(f: string) {
  return { result_value: '结果值', raw_value: '原始值', result_text: '结果描述' }[f] || f
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await runReport('审计追踪查询')
    audits.value = (res.result || []) as unknown as AuditRow[]
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page-head { margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; align-items: center; }
.total-pill { margin-left: auto; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-body { padding: 0; }
.panel-body :deep(.ant-table) { font-size: 13px; }
.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }

.old { font-family: var(--mono); color: var(--danger); text-decoration: line-through; font-size: 12px; }
.arrow { font-family: var(--mono); color: var(--muted); margin: 0 4px; }
.new { font-family: var(--mono); color: var(--pass); font-weight: 600; font-size: 12px; }
.field-tag { font-family: var(--mono); color: var(--muted); margin-left: 6px; font-size: 10px; }
</style>
