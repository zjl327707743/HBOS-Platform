<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>COA 报告管理</h1>
        <p>检验报告书（Certificate of Analysis）的创建、审核与发布</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openCreateDialog">创建 COA</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <el-table :data="coas" size="small" stripe v-loading="loading">
          <el-table-column prop="name" label="COA 编号" width="190">
            <template #default="{ row }"><span class="mono">{{ row.name }}</span></template>
          </el-table-column>
          <el-table-column prop="sample" label="样品编号" width="190">
            <template #default="{ row }"><span class="mono">{{ row.sample }}</span></template>
          </el-table-column>
          <el-table-column prop="material_name" label="物料名称" min-width="150" />
          <el-table-column prop="batch_no" label="批号" width="130">
            <template #default="{ row }"><span class="mono">{{ row.batch_no }}</span></template>
          </el-table-column>
          <el-table-column prop="report_status" label="状态" width="110">
            <template #default="{ row }">
              <span class="pill" :class="statusClass(row.report_status)">{{ row.report_status }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="qa_reviewer" label="QA 审核人" width="110" />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.report_status === '草稿'" text type="success" size="small" @click="publish">发布</el-button>
              <el-button v-else text type="primary" size="small" @click="downloadPdf(row)">PDF</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!loading && coas.length === 0" class="empty-note">
          暂无 COA 报告。当样品检验完成且结果全部批准后，可在此创建。
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreate" title="创建 COA" width="420">
      <el-form label-position="top">
        <el-form-item label="样品">
          <el-select v-model="createForm.sample" style="width:100%" filterable placeholder="选择检验完成的样品">
            <el-option v-for="s in coaCandidates" :key="s.name" :label="`${s.name}（${s.material_name}）`" :value="s.name" />
          </el-select>
        </el-form-item>
        <div v-if="coaCandidates.length === 0" class="hint">暂无检验完成且结果全部批准的样品</div>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useCoaStore } from '@/stores/coa'
import { useSampleStore } from '@/stores/sample'
import { createCoa, getFileUrl } from '@/api/lims'

const coaStore = useCoaStore()
const sampleStore = useSampleStore()
const coas = computed(() => coaStore.coas)
const loading = computed(() => coaStore.loading)

const showCreate = ref(false)
const creating = ref(false)
const createForm = reactive({ sample: '' })

const coaCandidates = computed(() => sampleStore.samples.filter((s) => ['检验完成', '已放行'].includes(s.status || '')))

function statusClass(s: string) {
  return { 已发布: 'pill-pass', 已审核: 'pill-info', 草稿: 'pill-muted' }[s] || 'pill-muted'
}

function openCreateDialog() {
  showCreate.value = true
}

async function doCreate() {
  if (!createForm.sample) {
    ElMessage.warning('请选择样品')
    return
  }
  creating.value = true
  try {
    const name = await createCoa(createForm.sample)
    ElMessage.success(`COA 创建成功：${name}`)
    showCreate.value = false
    await coaStore.fetchAll(true)
  } finally {
    creating.value = false
  }
}

async function publish() {
  // TODO: 调用 review_coa / publish_coa
  ElMessage.info('COA 审核与发布流程将在联调阶段开放')
}

function downloadPdf(row: any) {
  if (row.pdf_attachment) {
    window.open(getFileUrl(row.pdf_attachment), '_blank')
  } else {
    ElMessage.info('该 COA 尚未生成 PDF 附件')
  }
}

onMounted(async () => {
  await Promise.all([coaStore.fetchAll(), sampleStore.fetchAll()])
})
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-body { padding: 0; }
.panel-body :deep(.el-table) { --el-table-header-bg-color: var(--surface-2); --el-table-border-color: var(--line); }
.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }
.hint { font-size: 12px; color: var(--muted); }
</style>
