<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>质量标准库</h1>
        <p>检验项目、限度与方法 SOP 的版本化管理</p>
      </div>
      <div class="page-actions">
        <a-button type="primary" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          新增质量标准
        </a-button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <a-table
          :columns="columns"
          :data-source="specs"
          :loading="loading"
          size="small"
          row-key="name"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
            <template v-else-if="column.key === 'spec_name'">{{ record.spec_name }}</template>
            <template v-else-if="column.key === 'version'"><span class="mono">{{ record.version }}</span></template>
            <template v-else-if="column.key === 'status'">
              <span class="pill" :class="statusClass(record.status)">{{ record.status }}</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button type="link" size="small" @click="previewSpec(record)">明细</a-button>
              <a-button type="link" size="small" @click="openEdit(record)">修订</a-button>
              <a-button v-if="record.status !== '已废止'" type="link" size="small" @click="handleUpgrade(record)">升版</a-button>
              <a-button v-if="record.status === '草稿'" type="link" size="small" @click="handleActivate(record)">生效</a-button>
              <a-button v-if="record.status === '已生效'" type="link" size="small" @click="handleObsolete(record)">废止</a-button>
              <a-button v-if="record.status === '草稿'" type="link" size="small" danger @click="handleDelete(record)">删除</a-button>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 质量标准明细弹窗 -->
    <a-modal v-model:open="showDetail" :title="`质量标准明细 · ${currentSpec?.name || ''}`" :footer="null" width="640">
      <a-descriptions :column="2" size="small" bordered>
        <a-descriptions-item label="规格ID">{{ detailDoc?.spec_code || '—' }}</a-descriptions-item>
        <a-descriptions-item label="规格名称">{{ detailDoc?.spec_name || '—' }}</a-descriptions-item>
        <a-descriptions-item label="物料编码">{{ detailDoc?.material_code || '—' }}</a-descriptions-item>
        <a-descriptions-item label="物料名称">{{ detailDoc?.material_name || '—' }}</a-descriptions-item>
        <a-descriptions-item label="标准依据">{{ detailDoc?.standard_source || '—' }}</a-descriptions-item>
        <a-descriptions-item label="生效日期">{{ detailDoc?.effective_date || '—' }}</a-descriptions-item>
        <a-descriptions-item label="储存条件">{{ detailDoc?.storage_condition || '—' }}</a-descriptions-item>
        <a-descriptions-item label="留样量">{{ detailDoc?.retain_sample_qty || '—' }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <span class="pill" :class="statusClass(detailDoc?.status)">{{ detailDoc?.status || '—' }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="备注">{{ detailDoc?.remarks || '—' }}</a-descriptions-item>
      </a-descriptions>
      <div class="detail-items">
        <h4>检验项目明细</h4>
        <a-table
          :data-source="specItems"
          :loading="specLoading"
          size="small"
          bordered
          :pagination="false"
          row-key="item_name"
        >
          <a-table-column title="检验项目" data-index="item_name" key="item_name" />
          <a-table-column title="方法 / SOP" data-index="method" key="method" />
          <a-table-column title="限度模式" data-index="limits_type" key="limits_type" :width="90" />
          <a-table-column title="限度" data-index="limits" key="limits" :width="120" />
          <a-table-column title="单位" data-index="unit" key="unit" :width="60" />
        </a-table>
      </div>
    </a-modal>

    <!-- 新增 / 修订 / 升版 表单弹窗 -->
    <a-modal
      v-model:open="showForm"
      :title="formMode === 'create' ? '新增质量标准' : formMode === 'upgrade' ? `升版质量标准 · ${form.sourceName} → V${form.newVersion}` : `修订质量标准 · ${form.sourceName}`"
      :confirm-loading="saving"
      width="760"
      @ok="saveSpec"
      @cancel="closeForm"
      ok-text="保存"
      cancel-text="取消"
      destroy-on-close
    >
      <a-form :model="form" layout="vertical" class="spec-form">
        <div class="form-grid">
          <a-form-item label="规格ID *">
            <a-input v-model:value="form.spec_code" placeholder="如 SPEC-FG-001" :disabled="formMode !== 'create'" />
          </a-form-item>
          <a-form-item label="规格名称 *">
            <a-input v-model:value="form.spec_name" placeholder="如 阿司匹林片 质量标准" />
          </a-form-item>
          <a-form-item label="物料编码 *">
            <a-input v-model:value="form.material_code" placeholder="TEST-HBOS-M2-FG-001" />
          </a-form-item>
          <a-form-item label="物料名称 *">
            <a-input v-model:value="form.material_name" placeholder="阿司匹林原料药" />
          </a-form-item>
          <a-form-item label="标准依据">
            <a-select v-model:value="form.standard_source" placeholder="选择标准依据" allow-clear>
              <a-select-option value="中国药典">中国药典</a-select-option>
              <a-select-option value="EP">EP</a-select-option>
              <a-select-option value="USP">USP</a-select-option>
              <a-select-option value="客户标准">客户标准</a-select-option>
              <a-select-option value="企业内控">企业内控</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="生效日期 *">
            <a-date-picker v-model:value="form.effective_date" value-format="YYYY-MM-DD" style="width:100%" />
          </a-form-item>
          <a-form-item label="储存条件">
            <a-input v-model:value="form.storage_condition" placeholder="如 常温、避光、密封保存" />
          </a-form-item>
          <a-form-item label="留样量">
            <a-input v-model:value="form.retain_sample_qty" placeholder="如 12 盒" />
          </a-form-item>
        </div>

        <div class="items-head">
          <h4>检验项目明细 *</h4>
          <a-button type="dashed" size="small" @click="addItemRow">+ 添加检验项目</a-button>
        </div>
        <div v-for="(item, idx) in form.items" :key="idx" class="item-row">
          <a-select
            v-model:value="item.item"
            style="width:180px"
            placeholder="检验项目 *"
            show-search
            option-filter-prop="label"
            @change="(val: string) => onItemSelect(item, val)"
          >
            <a-select-option v-for="ti in testItems" :key="ti.name" :value="ti.name" :label="`${ti.item_name}（${ti.name}）`">
              {{ ti.item_name }}（{{ ti.name }}）
            </a-select-option>
          </a-select>
          <a-input v-model:value="item.item_name" placeholder="项目名称" style="width:110px" />
          <a-input v-model:value="item.method_sop" placeholder="方法/SOP" style="width:130px" />
          <a-select v-model:value="item.limits_type" style="width:100px" placeholder="限度模式">
            <a-select-option value="记录型">记录型</a-select-option>
            <a-select-option value="区间">区间</a-select-option>
            <a-select-option value="上限">上限</a-select-option>
            <a-select-option value="下限">下限</a-select-option>
          </a-select>
          <a-input-number v-if="['区间','下限'].includes(item.limits_type)" v-model:value="item.lower_limit" placeholder="下限" style="width:90px" :precision="2" />
          <a-input-number v-if="['区间','上限'].includes(item.limits_type)" v-model:value="item.upper_limit" placeholder="上限" style="width:90px" :precision="2" />
          <a-input v-model:value="item.unit" placeholder="单位" style="width:60px" />
          <a-button type="text" size="small" danger @click="removeItemRow(idx)">删除</a-button>
        </div>
        <div v-if="!form.items.length" class="empty-items">暂无检验项目，请添加</div>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { listDoctype, getDoc, createSpecification, updateSpecification, activateSpecification, obsoleteSpecification, deleteSpecification } from '@/api/lims'

interface Spec {
  name: string
  spec_name: string
  spec_code: string
  version: string
  status: string
  item_count: number
}

interface SpecItemInput {
  item: string
  item_name: string
  method_sop?: string
  limits_type: string
  lower_limit?: number | null
  upper_limit?: number | null
  unit?: string
}

const specs = ref<Spec[]>([])
const loading = ref(false)
const testItems = ref<{ name: string; item_name: string }[]>([])
const showDetail = ref(false)
const currentSpec = ref<Spec | null>(null)
const detailDoc = ref<any>(null)
const specItems = ref<Record<string, unknown>[]>([])
const specLoading = ref(false)

const showForm = ref(false)
const saving = ref(false)
const formMode = ref<'create' | 'edit' | 'upgrade'>('create')
const form = reactive<{
  spec_code: string
  spec_name: string
  sourceName: string
  newVersion: string
  material_code: string
  material_name: string
  standard_source: string
  effective_date: string
  storage_condition: string
  retain_sample_qty: string
  remarks: string
  items: SpecItemInput[]
}>({
  spec_code: '',
  spec_name: '',
  sourceName: '',
  newVersion: '',
  material_code: '',
  material_name: '',
  standard_source: '',
  effective_date: '',
  storage_condition: '',
  retain_sample_qty: '',
  remarks: '',
  items: [],
})

const columns = [
  { title: '标准编号', key: 'name', dataIndex: 'name', width: 200 },
  { title: '规格名称', key: 'spec_name', dataIndex: 'spec_name' },
  { title: '版本', key: 'version', dataIndex: 'version', width: 70 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 90 },
  { title: '检验项目', key: 'item_count', dataIndex: 'item_count', width: 80, align: 'center' as const },
  { title: '操作', key: 'actions', width: 300 },
]

function statusClass(s: string) {
  return { 已生效: 'pill-pass', 已废止: 'pill-muted', 草稿: 'pill-info' }[s] || 'pill-muted'
}

async function loadSpecs() {
  loading.value = true
  try {
    const rows = await listDoctype<any>('HBOS Specification', ['name', 'spec_code', 'spec_name', 'version', 'status'], {}, 100)
    specs.value = await Promise.all(
      rows.map(async (r) => {
        const doc = await getDoc<any>('HBOS Specification', r.name)
        return {
          name: r.name,
          spec_code: doc.spec_code || r.spec_code,
          spec_name: doc.spec_name || r.spec_name,
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
    detailDoc.value = doc
    specItems.value = (doc.items || []).map((it: any) => ({
      item_name: it.item_name || it.item || '',
      method: it.method_sop || '',
      limits_type: it.limits_type || '',
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

function resetForm() {
  form.spec_code = ''
  form.spec_name = ''
  form.sourceName = ''
  form.material_code = ''
  form.material_name = ''
  form.standard_source = ''
  form.effective_date = ''
  form.storage_condition = ''
  form.retain_sample_qty = ''
  form.remarks = ''
  form.items = []
}

// 新增
function openCreate() {
  resetForm()
  formMode.value = 'create'
  addItemRow()
  showForm.value = true
}

// 修订：载入当前内容
async function openEdit(row: Spec) {
  resetForm()
  formMode.value = 'edit'
  form.sourceName = row.name
  const doc = await getDoc<any>('HBOS Specification', row.name)
  form.spec_code = doc.spec_code || ''
  form.spec_name = doc.spec_name || ''
  form.material_code = doc.material_code || ''
  form.material_name = doc.material_name || ''
  form.standard_source = doc.standard_source || ''
  form.effective_date = doc.effective_date || ''
  form.storage_condition = doc.storage_condition || ''
  form.retain_sample_qty = doc.retain_sample_qty || ''
  form.remarks = doc.remarks || ''
  form.items = (doc.items || []).map((it: any) => ({
    item: it.item || '',
    item_name: it.item_name || it.item || '',
    method_sop: it.method_sop || '',
    limits_type: it.limits_type || '记录型',
    lower_limit: it.lower_limit,
    upper_limit: it.upper_limit,
    unit: it.unit || '',
  }))
  showForm.value = true
}

// 升版：复制当前内容，版本号 +0.1 为新版本
async function openUpgrade(row: Spec) {
  resetForm()
  formMode.value = 'upgrade'
  form.sourceName = row.name
  const doc = await getDoc<any>('HBOS Specification', row.name)
  form.spec_code = doc.spec_code || ''
  form.spec_name = doc.spec_name || ''
  form.material_code = doc.material_code || ''
  form.material_name = doc.material_name || ''
  form.standard_source = doc.standard_source || ''
  form.effective_date = doc.effective_date || ''
  form.storage_condition = doc.storage_condition || ''
  form.retain_sample_qty = doc.retain_sample_qty || ''
  form.remarks = doc.remarks || ''
  form.newVersion = nextVersion(doc.version)
  form.items = (doc.items || []).map((it: any) => ({
    item: it.item || '',
    item_name: it.item_name || it.item || '',
    method_sop: it.method_sop || '',
    limits_type: it.limits_type || '记录型',
    lower_limit: it.lower_limit,
    upper_limit: it.upper_limit,
    unit: it.unit || '',
  }))
  showForm.value = true
}

function nextVersion(ver?: string): string {
  const v = parseFloat(ver || '1.0')
  if (isNaN(v)) return '1.1'
  return String(Math.round((v + 0.1) * 10) / 10)
}

function addItemRow() {
  form.items.push({ item: '', item_name: '', method_sop: '', limits_type: '记录型', lower_limit: null, upper_limit: null, unit: '' })
}
function removeItemRow(idx: number) {
  form.items.splice(idx, 1)
}

// 选中检验项目后自动带出项目名称
function onItemSelect(item: SpecItemInput, val: string) {
  const ti = testItems.value.find((t) => t.name === val)
  if (ti) item.item_name = ti.item_name
}

async function saveSpec() {
  if (!form.spec_code || !form.spec_name) {
    message.warning('请填写规格ID和规格名称')
    return
  }
  if (!form.material_code || !form.material_name) {
    message.warning('请填写物料编码和物料名称')
    return
  }
  if (!form.effective_date) {
    message.warning('请选择生效日期')
    return
  }
  if (!form.items.length || !form.items.some((i) => i.item)) {
    message.warning('请至少添加一个检验项目')
    return
  }
  saving.value = true
  try {
    const payload: any = {
      spec_code: form.spec_code,
      spec_name: form.spec_name,
      material_code: form.material_code,
      material_name: form.material_name,
      standard_source: form.standard_source,
      effective_date: form.effective_date,
      storage_condition: form.storage_condition,
      retain_sample_qty: form.retain_sample_qty,
      items: form.items.filter((i) => i.item).map((i) => ({
        item: i.item,
        item_name: i.item_name,
        method_sop: i.method_sop,
        limits_type: i.limits_type,
        lower_limit: i.lower_limit,
        upper_limit: i.upper_limit,
        unit: i.unit,
      })),
      remarks: form.remarks,
    }
    if (formMode.value === 'create') {
      await createSpecification(payload)
      message.success('质量标准已创建（草稿）')
    } else if (formMode.value === 'edit') {
      await updateSpecification({ ...payload, spec_name: form.sourceName, spec_name_label: form.spec_name })
      message.success('质量标准已修订')
    } else {
      // 升版：基于当前规格复制为新版本（版本号 +0.1）
      await createSpecification({ ...payload, version: form.newVersion })
      message.success(`质量标准已升版为 V${form.newVersion}（草稿）`)
    }
    showForm.value = false
    await loadSpecs()
  } finally {
    saving.value = false
  }
}

// 生效
function handleActivate(row: Spec) {
  Modal.confirm({
    title: '生效质量标准',
    content: `确认将「${row.name}」生效？生效后样品登记可引用。`,
    onOk: async () => {
      try {
        await activateSpecification(row.name)
        message.success('质量标准已生效')
        await loadSpecs()
      } catch {
        /* 拦截器已提示 */
      }
    },
  })
}

// 废止
function handleObsolete(row: Spec) {
  Modal.confirm({
    title: '废止质量标准',
    content: `确认废止「${row.name}」？废止后不可被样品引用。`,
    okType: 'danger',
    onOk: async () => {
      try {
        await obsoleteSpecification(row.name)
        message.success('质量标准已废止')
        await loadSpecs()
      } catch {
        /* 拦截器已提示 */
      }
    },
  })
}

// 删除
function handleDelete(row: Spec) {
  Modal.confirm({
    title: '删除质量标准',
    content: `确认删除草稿「${row.name}」？此操作不可恢复。`,
    okType: 'danger',
    onOk: async () => {
      try {
        await deleteSpecification(row.name)
        message.success('质量标准已删除')
        await loadSpecs()
      } catch {
        /* 拦截器已提示 */
      }
    },
  })
}

function handleUpgrade(row: Spec) {
  openUpgrade(row)
}

function closeForm() {
  showForm.value = false
}

async function loadTestItems() {
  try {
    testItems.value = await listDoctype<any>('HBOS Test Item', ['name', 'item_name'], {}, 100)
  } catch {
    testItems.value = []
  }
}

onMounted(async () => {
  await loadTestItems()
  await loadSpecs()
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

.detail-items { margin-top: 16px; }
.detail-items h4 { font-size: 13px; color: var(--ink); margin-bottom: 8px; }

.spec-form .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.items-head { display: flex; align-items: center; justify-content: space-between; margin: 12px 0 8px; }
.items-head h4 { font-size: 13px; color: var(--ink); }
.item-row { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; flex-wrap: wrap; }
.empty-items { color: var(--muted); font-size: 12px; padding: 12px 0; text-align: center; border: 1px dashed var(--line); border-radius: 6px; }
</style>
