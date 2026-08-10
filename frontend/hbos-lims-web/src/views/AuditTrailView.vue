<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>审计追踪查询</h1>
        <p>检验结果修订与关键操作的合规审计记录（只读）</p>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="search" placeholder="搜索对象 / 操作人" clearable style="width:220px" />
      <el-select v-model="actionFilter" placeholder="操作类型" clearable style="width:150px">
        <el-option v-for="a in actions" :key="a" :label="a" :value="a" />
      </el-select>
      <span class="pill muted total-pill">{{ filteredAudits.length }} 条记录</span>
    </div>

    <div class="panel">
      <div class="panel-body">
        <el-table :data="filteredAudits" size="small" stripe v-loading="loading">
          <el-table-column prop="modified" label="时间" width="160">
            <template #default="{ row }"><span class="mono">{{ (row.modified || '').replace('T', ' ').slice(0, 16) }}</span></template>
          </el-table-column>
          <el-table-column prop="owner" label="操作人" width="160">
            <template #default="{ row }"><span class="mono">{{ row.owner }}</span></template>
          </el-table-column>
          <el-table-column prop="result_name" label="结果记录" min-width="180">
            <template #default="{ row }"><span class="mono">{{ row.result_name }}</span></template>
          </el-table-column>
          <el-table-column prop="rev_no" label="修订号" width="80">
            <template #default="{ row }"><span class="mono">{{ row.rev_no }}</span></template>
          </el-table-column>
          <el-table-column prop="old_value" label="修订前" min-width="110" />
          <el-table-column prop="new_value" label="修订后" min-width="110" />
          <el-table-column prop="reason" label="修订原因" min-width="180" />
        </el-table>
        <div v-if="!loading && filteredAudits.length === 0" class="empty-note">暂无审计记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { runReport } from '@/api/lims'

const audits = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const search = ref('')
const actionFilter = ref('')

const actions = ['修订结果', '提交结果', '复核结果', '批准结果']

const filteredAudits = computed(() => {
  return audits.value.filter((a) => {
    const matchSearch = !search.value ||
      String(a.result_name || '').includes(search.value) ||
      String(a.owner || '').includes(search.value)
    return matchSearch
  })
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await runReport('审计追踪查询')
    audits.value = res.result || []
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
.panel-body :deep(.el-table) { --el-table-header-bg-color: var(--surface-2); --el-table-border-color: var(--line); }
.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }
</style>
