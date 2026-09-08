<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>留样产品</h1>
        <p class="page-desc">留样主数据（附件二《留样产品清单》电子化）：类别、留样量规则、UOM 与观察规则</p>
      </div>
      <div class="page-actions">
        <a-button @click="loadData">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          新增留样产品
        </a-button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <div class="filter-bar">
          <a-select v-model:value="filters.category" placeholder="类别" allow-clear style="width: 130px" size="small" :options="categoryOptions" @change="loadData" />
          <a-input v-model:value="filters.keyword" placeholder="编码 / 名称搜索" allow-clear style="width: 200px" size="small" @pressEnter="loadData" />
          <a-button size="small" @click="loadData">查询</a-button>
        </div>
        <a-table
          :columns="columns"
          :data-source="filteredProducts"
          :loading="loading"
          size="small"
          row-key="name"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'product_code'"><span class="mono">{{ record.product_code }}</span></template>
            <template v-else-if="column.key === 'category'">
              <span class="pill" :class="categoryClass(record.category)">{{ record.category }}</span>
            </template>
            <template v-else-if="column.key === 'qty_rule'">
              {{ record.retention_qty_rule }}
              <span v-if="record.retention_qty_rule === '全检量 2 倍' && record.full_test_qty" class="dim">
                （{{ record.full_test_qty }} {{ record.full_test_qty_uom }}×2）
              </span>
            </template>
            <template v-else-if="column.key === 'flags'">
              <span v-if="record.is_liquid" class="pill pill-red">液体·不留样</span>
              <span v-if="record.is_outsource" class="pill pill-blue">受托方留样</span>
              <span v-if="!record.is_liquid && !record.is_outsource" class="dim">—</span>
            </template>
            <template v-else-if="column.key === 'is_active'">
              <span class="pill" :class="record.is_active ? 'pill-green' : 'pill-gray'">
                {{ record.is_active ? '启用' : '停用' }}
              </span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button type="link" size="small" @click="openEdit(record)">编辑</a-button>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <a-modal v-model:open="showForm" :title="formMode === 'create' ? '新增留样产品' : `编辑 · ${form.product_code}`" :confirmLoading="saving" @ok="handleSave" width="640" ok-text="保存" cancel-text="取消">
      <a-form layout="vertical" style="margin-top: 8px">
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="产品编码" required>
              <a-input v-model:value="form.product_code" :disabled="formMode === 'edit'" placeholder="如 RP001" />
            </a-form-item>
          </a-col>
          <a-col :span="10">
            <a-form-item label="产品名称" required>
              <a-input v-model:value="form.product_name" />
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="类别" required>
              <a-select v-model:value="form.category" :options="categoryOptions" @change="onCategoryChange" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="留样数量规则">
              <a-select v-model:value="form.retention_qty_rule" :options="qtyRuleOptions" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="全检量">
              <a-input-number v-model:value="form.full_test_qty" :min="0" style="width: 100%" placeholder="数值" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="全检量单位">
              <a-select v-model:value="form.full_test_qty_uom" :options="uomOptions" allow-clear placeholder="选择单位" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="默认计量单位（全板块权威）" required>
              <a-select v-model:value="form.default_uom" :options="uomOptions" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="储存条件">
              <a-input v-model:value="form.storage_condition" placeholder="如 常温密封" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="观察规则">
              <a-select v-model:value="form.obs_rule" :options="obsRuleOptions" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-checkbox v-model:checked="form.is_liquid">液体物料（登记硬拦截）</a-checkbox>
          </a-col>
          <a-col :span="8">
            <a-checkbox v-model:checked="form.is_outsource">受托生产（受托方留样）</a-checkbox>
          </a-col>
          <a-col :span="8">
            <a-checkbox v-model:checked="form.is_active">启用</a-checkbox>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { listDoctype, type RetentionProduct } from '@/api/lims'

const products = ref<RetentionProduct[]>([])
const loading = ref(false)
const filters = reactive({ category: undefined as string | undefined, keyword: '' })

const categoryOptions = [
  { value: '关键物料', label: '关键物料' },
  { value: '成品（原料药）', label: '成品（原料药）' },
  { value: '外售产品', label: '外售产品' },
]
const qtyRuleOptions = ['全检量 2 倍', '按实际', '按客户要求'].map((v) => ({ value: v, label: v }))
const uomOptions = ['g', 'kg', 'mg', 'mL', 'L', '瓶', '支', '袋', '桶', '盒', '其他'].map((v) => ({ value: v, label: v }))
const obsRuleOptions = ['每批观察（外售产品）', '每年选 3 批（原料药成品）', '不观察'].map((v) => ({ value: v, label: v }))

const columns = [
  { title: '产品编码', key: 'product_code', dataIndex: 'product_code', width: 140 },
  { title: '产品名称', key: 'product_name', dataIndex: 'product_name' },
  { title: '类别', key: 'category', width: 110 },
  { title: '留样数量规则', key: 'qty_rule', width: 200 },
  { title: '默认单位', key: 'default_uom', dataIndex: 'default_uom', width: 80 },
  { title: '观察规则', key: 'obs_rule', dataIndex: 'obs_rule', width: 160 },
  { title: '标记', key: 'flags', width: 150 },
  { title: '状态', key: 'is_active', width: 70 },
  { title: '操作', key: 'actions', width: 70 },
]

const filteredProducts = computed(() => {
  let list = products.value
  if (filters.category) list = list.filter((p) => p.category === filters.category)
  if (filters.keyword) {
    const kw = filters.keyword.toLowerCase()
    list = list.filter((p) => p.product_code?.toLowerCase().includes(kw) || p.product_name?.toLowerCase().includes(kw))
  }
  return list
})

async function loadData() {
  loading.value = true
  try {
    products.value = await listDoctype<RetentionProduct>('HBOS Retention Product', ['*'], {}, 0, 'modified desc')
  } catch {
    message.error('加载留样产品失败')
  } finally {
    loading.value = false
  }
}

function categoryClass(category: string): string {
  if (category === '成品（原料药）') return 'pill-blue'
  if (category === '外售产品') return 'pill-amber'
  return 'pill-green'
}

function onCategoryChange(val: string) {
  if (val === '外售产品') form.obs_rule = '每批观察（外售产品）'
}

// ---- 表单 ----
const showForm = ref(false)
const saving = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const form = reactive({
  name: '',
  product_code: '',
  product_name: '',
  category: '关键物料',
  retention_qty_rule: '全检量 2 倍',
  full_test_qty: undefined as number | undefined,
  full_test_qty_uom: undefined as string | undefined,
  default_uom: 'g',
  storage_condition: '',
  obs_rule: '不观察',
  is_liquid: false,
  is_outsource: false,
  is_active: true,
})

function openCreate() {
  Object.assign(form, {
    name: '', product_code: '', product_name: '', category: '关键物料',
    retention_qty_rule: '全检量 2 倍', full_test_qty: undefined, full_test_qty_uom: undefined,
    default_uom: 'g', storage_condition: '', obs_rule: '不观察',
    is_liquid: false, is_outsource: false, is_active: true,
  })
  formMode.value = 'create'
  showForm.value = true
}

function openEdit(record: RetentionProduct) {
  Object.assign(form, {
    name: record.name,
    product_code: record.product_code,
    product_name: record.product_name,
    category: record.category,
    retention_qty_rule: record.retention_qty_rule,
    full_test_qty: record.full_test_qty ?? undefined,
    full_test_qty_uom: record.full_test_qty_uom || undefined,
    default_uom: record.default_uom,
    storage_condition: record.storage_condition || '',
    obs_rule: record.obs_rule,
    is_liquid: !!record.is_liquid,
    is_outsource: !!record.is_outsource,
    is_active: !!record.is_active,
  })
  formMode.value = 'edit'
  showForm.value = true
}

async function handleSave() {
  if (!form.product_code || !form.product_name) {
    message.warning('请填写产品编码与名称')
    return
  }
  if (formMode.value === 'create' && products.value.some((p) => p.product_code === form.product_code)) {
    message.warning('产品编码已存在（唯一约束）')
    return
  }
  saving.value = true
  try {
    const { createDoc, updateDoc } = await import('@/api/lims')
    if (formMode.value === 'create') {
      await createDoc('HBOS Retention Product', {
        product_code: form.product_code,
        product_name: form.product_name,
        category: form.category,
        retention_qty_rule: form.retention_qty_rule,
        full_test_qty: form.full_test_qty ?? 0,
        full_test_qty_uom: form.full_test_qty_uom || '',
        default_uom: form.default_uom,
        storage_condition: form.storage_condition,
        obs_rule: form.obs_rule,
        is_liquid: form.is_liquid ? 1 : 0,
        is_outsource: form.is_outsource ? 1 : 0,
        is_active: form.is_active ? 1 : 0,
      })
      message.success('留样产品已创建')
    } else {
      await updateDoc('HBOS Retention Product', form.name, {
        product_name: form.product_name,
        category: form.category,
        retention_qty_rule: form.retention_qty_rule,
        full_test_qty: form.full_test_qty ?? 0,
        full_test_qty_uom: form.full_test_qty_uom || '',
        default_uom: form.default_uom,
        storage_condition: form.storage_condition,
        obs_rule: form.obs_rule,
        is_liquid: form.is_liquid ? 1 : 0,
        is_outsource: form.is_outsource ? 1 : 0,
        is_active: form.is_active ? 1 : 0,
      })
      message.success('留样产品已更新（审计留痕）')
    }
    showForm.value = false
    await loadData()
  } catch (e: any) {
    message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.filter-bar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
.dim { color: #9ca3af; font-size: 12px; }
.pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; white-space: nowrap; }
.pill-green { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.pill-amber { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.pill-blue { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.pill-red { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.pill-gray { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
</style>
