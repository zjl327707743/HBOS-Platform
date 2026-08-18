<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>COA 报告管理</h1>
        <p>检验报告书（Certificate of Analysis）的创建、审核与发布</p>
      </div>
      <div class="page-actions">
        <a-button type="primary" @click="openCreateDialog">创建 COA</a-button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <a-table
          :columns="columns"
          :data-source="coas"
          :loading="loading"
          size="small"
          row-key="name"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
            <template v-else-if="column.key === 'sample'"><span class="mono">{{ record.sample }}</span></template>
            <template v-else-if="column.key === 'batch_no'"><span class="mono">{{ record.batch_no }}</span></template>
            <template v-else-if="column.key === 'report_status'">
              <span class="pill" :class="statusClass(record.report_status)">{{ record.report_status }}</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button type="link" size="small" @click="previewCoa(record)">预览</a-button>
              <a-button v-if="record.report_status === '草稿'" type="link" size="small" @click="review(record)">审核</a-button>
              <a-button v-if="record.report_status === '已审核'" type="link" size="small" @click="publish(record)">发布</a-button>
              <a-button v-if="record.report_status === '已发布'" type="link" size="small" @click="downloadPdf(record)">PDF</a-button>
            </template>
          </template>
        </a-table>
        <div v-if="!loading && coas.length === 0" class="empty-note">
          暂无 COA 报告。当样品检验完成且结果全部批准后，可在此创建。
        </div>
      </div>
    </div>

    <a-modal v-model:open="showCreate" title="创建 COA" :footer="null" width="420">
      <a-form layout="vertical">
        <a-form-item label="样品">
          <a-select v-model:value="createForm.sample" style="width:100%" show-search placeholder="选择检验完成的样品">
            <a-select-option v-for="s in coaCandidates" :key="s.name" :value="s.name">{{ s.name }}（{{ s.material_name }}）</a-select-option>
          </a-select>
        </a-form-item>
        <div v-if="coaCandidates.length === 0" class="hint">暂无检验完成且结果全部批准的样品</div>
        <div class="modal-footer">
          <a-button @click="showCreate = false">取消</a-button>
          <a-button type="primary" :loading="creating" @click="doCreate">创建</a-button>
        </div>
      </a-form>
    </a-modal>

    <!-- COA 预览 -->
    <a-modal v-model:open="showPreview" :title="`COA 预览 · ${currentCoa?.name || ''}`" :footer="null" width="660">
      <div v-if="currentCoa" class="coa-doc">
        <div class="coa-header">
          <div class="coa-brand">海滨药业 · HBOS</div>
          <div class="coa-title">检验报告书</div>
          <div class="coa-no mono">Certificate No: {{ currentCoa.name }}</div>
        </div>
        <div class="coa-info">
          <div class="coa-row"><span>样品编号</span><span class="mono">{{ currentCoa.sample }}</span></div>
          <div class="coa-row"><span>物料名称</span><span>{{ currentCoa.material_name }}</span></div>
          <div class="coa-row"><span>批号</span><span class="mono">{{ currentCoa.batch_no }}</span></div>
          <div class="coa-row"><span>标准版本</span><span class="mono">{{ currentCoa.spec_version }}</span></div>
        </div>
        <a-table
          :data-source="coaItems"
          :loading="itemsLoading"
          size="small"
          bordered
          :pagination="false"
          row-key="item_name"
        >
          <a-table-column title="检验项目" data-index="item_name" key="item_name" />
          <a-table-column title="标准限度" data-index="limits" key="limits" :width="120" />
          <a-table-column title="检验结果" data-index="result" key="result" :width="100" />
          <a-table-column title="判定" data-index="judgement" key="judgement" :width="90">
            <template #default="{ text }">
              <span class="pill" :class="text === '合格' ? 'pill-pass' : 'pill-danger'">{{ text }}</span>
            </template>
          </a-table-column>
        </a-table>
        <div class="coa-sign">
          <div class="coa-sig-item"><div>检验人</div><div class="mono">{{ currentCoa.sample_analyst || '—' }}</div></div>
          <div class="coa-sig-item"><div>QA 审核</div><div class="mono">{{ currentCoa.qa_reviewer || '—' }}</div></div>
          <div class="coa-sig-item"><div>批准发布</div><div class="mono">{{ currentCoa.published_by || '—' }}</div></div>
        </div>
        <div class="coa-foot">本报告仅对来样负责。电子签名与审计追踪由 HBOS LIMS 系统保障。</div>
      </div>
      <div class="modal-footer">
        <a-button @click="showPreview = false">关闭</a-button>
        <a-button v-if="currentCoa?.report_status === '已发布'" type="primary" @click="downloadPdf(currentCoa)">下载 PDF</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { useCoaStore } from '@/stores/coa'
import { useSampleStore } from '@/stores/sample'
import { createCoa, reviewCoa, publishCoa, getDoc, getFileUrl } from '@/api/lims'

const coaStore = useCoaStore()
const sampleStore = useSampleStore()
const coas = computed(() => coaStore.coas)
const loading = computed(() => coaStore.loading)

const showCreate = ref(false)
const creating = ref(false)
const createForm = reactive({ sample: '' })

const coaCandidates = computed(() => sampleStore.samples.filter((s) => ['检验完成', '已放行'].includes(s.status || '')))

const showPreview = ref(false)
const currentCoa = ref<any>(null)
const coaItems = ref<any[]>([])
const itemsLoading = ref(false)

const columns = [
  { title: 'COA 编号', key: 'name', dataIndex: 'name', width: 190 },
  { title: '样品编号', key: 'sample', dataIndex: 'sample', width: 190 },
  { title: '物料名称', key: 'material_name', dataIndex: 'material_name' },
  { title: '批号', key: 'batch_no', dataIndex: 'batch_no', width: 130 },
  { title: '状态', key: 'report_status', dataIndex: 'report_status', width: 100 },
  { title: 'QA 审核人', key: 'qa_reviewer', dataIndex: 'qa_reviewer', width: 110 },
  { title: '操作', key: 'actions', width: 180 },
]

function statusClass(s: string) {
  return { 已发布: 'pill-pass', 已审核: 'pill-info', 草稿: 'pill-muted' }[s] || 'pill-muted'
}

function openCreateDialog() {
  showCreate.value = true
}

async function doCreate() {
  if (!createForm.sample) {
    message.warning('请选择样品')
    return
  }
  creating.value = true
  try {
    const name = await createCoa(createForm.sample)
    message.success(`COA 创建成功：${name}`)
    showCreate.value = false
    await coaStore.fetchAll(true)
  } finally {
    creating.value = false
  }
}

async function previewCoa(row: any) {
  currentCoa.value = row
  showPreview.value = true
  itemsLoading.value = true
  try {
    const full = await getDoc<any>('HBOS COA', row.name)
    currentCoa.value = full
    const items = (full.items || []).map((it: any) => ({
      item_name: it.item_name || it.test_item || '—',
      limits: it.limits || '—',
      result: it.result || '—',
      judgement: it.judgement || '—',
    }))
    coaItems.value = items
  } catch {
    coaItems.value = []
  } finally {
    itemsLoading.value = false
  }
}

async function review(row: any) {
  try {
    await reviewCoa(row.name)
    message.success(`COA ${row.name} 已审核`)
    await coaStore.fetchAll(true)
  } catch {
    // 拦截器已提示
  }
}

async function publish(row: any) {
  try {
    await publishCoa(row.name)
    message.success(`COA ${row.name} 已发布，PDF 已生成`)
    await coaStore.fetchAll(true)
  } catch {
    // 拦截器已提示
  }
}

function downloadPdf(row: any) {
  if (row.pdf_attachment) {
    window.open(getFileUrl(row.pdf_attachment), '_blank')
  } else {
    message.info('该 COA 尚未生成 PDF 附件')
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
.panel-body :deep(.ant-table) { font-size: 13px; }
.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }
.hint { font-size: 12px; color: var(--muted); }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }

.coa-doc { font-size: 13px; }
.coa-header { text-align: center; border-bottom: 2px solid var(--ink); padding-bottom: 12px; margin-bottom: 14px; }
.coa-brand { font-size: 11px; color: var(--muted); }
.coa-title { font-size: 20px; font-weight: 700; letter-spacing: 4px; margin-top: 4px; }
.coa-no { font-size: 11px; color: var(--muted); margin-top: 4px; }
.coa-info { display: grid; gap: 6px; margin-bottom: 14px; }
.coa-row { display: flex; justify-content: space-between; font-size: 12px; }
.coa-row span:first-child { color: var(--muted); }
.coa-sign { display: flex; justify-content: space-between; margin-top: 24px; }
.coa-sig-item { text-align: center; font-size: 12px; color: var(--muted); flex: 1; }
.coa-sig-item .mono { color: var(--ink); font-weight: 600; margin-top: 4px; }
.coa-foot { margin-top: 18px; font-size: 10px; color: var(--muted); text-align: center; }
</style>
