<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>留样登记与台账</h1>
        <p class="page-desc">批次留样全生命周期：登记入库、库存结存、留样期至与观察计划</p>
      </div>
      <div class="page-actions">
        <a-button @click="loadData">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" @click="openRegister">
          <template #icon><PlusOutlined /></template>
          新增留样登记
        </a-button>
      </div>
    </div>

    <div class="stat-row">
      <div class="stat-card">
        <div class="stat-label">在库留样</div>
        <div class="stat-value">{{ stats.inStock }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">待处理</div>
        <div class="stat-value warn">{{ stats.pending }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">临期（90 天内到期）</div>
        <div class="stat-value danger">{{ stats.expiring }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">观察样品</div>
        <div class="stat-value">{{ stats.observed }}</div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-body">
        <div class="filter-bar">
          <a-select v-model:value="filters.category" placeholder="类别" allow-clear style="width: 130px" size="small" :options="categoryOptions" @change="loadData" />
          <a-select v-model:value="filters.status" placeholder="状态" allow-clear style="width: 110px" size="small" :options="statusOptions" @change="loadData" />
          <a-select v-model:value="filters.expireRange" placeholder="临期范围" allow-clear style="width: 130px" size="small" :options="expireRangeOptions" @change="loadData" />
          <a-input v-model:value="filters.batch_no" placeholder="批号搜索" allow-clear style="width: 160px" size="small" @pressEnter="loadData" />
          <a-button size="small" @click="loadData">查询</a-button>
        </div>
        <a-table
          :columns="columns"
          :data-source="rows"
          :loading="loading"
          size="small"
          row-key="name"
          :pagination="{ pageSize: 20, showTotal: (t: number) => `共 ${t} 条` }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
            <template v-else-if="column.key === 'status'">
              <span class="pill" :class="statusClass(record.status)">{{ record.status }}</span>
            </template>
            <template v-else-if="column.key === 'qty'">
              {{ record.retention_qty }} {{ record.qty_uom }}
            </template>
            <template v-else-if="column.key === 'stock'">
              <span :class="{ 'stock-warn': record.available_qty <= 0 && record.status === '在库' }">
                {{ record.current_qty }}{{ record.reserved_qty > 0 ? `（预占 ${record.reserved_qty}）` : '' }}
              </span>
            </template>
            <template v-else-if="column.key === 'available'">
              <span class="mono" :class="record.available_qty > 0 ? 'stock-ok' : 'stock-warn'">{{ record.available_qty }}</span>
            </template>
            <template v-else-if="column.key === 'observed'">
              <span class="pill" :class="record.observed_flag ? 'pill-green' : 'pill-gray'">
                {{ record.observed_flag ? '是' : '否' }}
              </span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-button type="link" size="small" @click="showDetail(record)">明细</a-button>
              <a-button v-if="record.status === '在库' || record.status === '部分使用'" type="link" size="small" @click="openAdjust(record)">调整结存</a-button>
            </template>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 登记弹窗 -->
    <a-modal v-model:open="showForm" title="新增留样登记" :confirmLoading="saving" @ok="handleRegister" width="620" ok-text="登记入库" cancel-text="取消">
      <a-form layout="vertical" style="margin-top: 8px">
        <a-form-item label="留样产品" required>
          <a-select
            v-model:value="form.retention_product"
            show-search
            option-filter-prop="label"
            placeholder="选择留样产品（先在留样产品页维护）"
            :options="productOptions"
            @change="onProductChange"
          />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="批号" required>
              <a-input v-model:value="form.batch_no" placeholder="生产批号" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="容器序号">
              <a-input-number v-model:value="form.container_no" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="留样日期" required>
              <a-date-picker v-model:value="form.retention_date" value-format="YYYY-MM-DD" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="期限类型">
              <a-select v-model:value="form.expiry_type" :options="expiryTypeOptions" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="有效期 / 复验期">
              <a-date-picker v-model:value="form.expiry_date" value-format="YYYY-MM-DD" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="留样期至（不填自动算）">
              <a-date-picker v-model:value="form.retention_due_date" value-format="YYYY-MM-DD" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item :label="`留样量${formUnit ? '（' + formUnit + '）' : ''}`" required>
              <a-input v-model:value="form.retention_qty" placeholder="数值（2 倍可自动算）" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="最小包装件数">
              <a-input-number v-model:value="form.package_count" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="储存位置编号">
              <a-input v-model:value="form.storage_location" placeholder="如 RET-A-01" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="来源">
              <a-input v-model:value="form.source" placeholder="如 生产车间 / 供应商" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="观察样品">
              <a-checkbox v-model:checked="form.observed_flag">纳入观察计划</a-checkbox>
            </a-form-item>
          </a-col>
        </a-row>
        <a-alert v-if="formNote" :message="formNote" type="info" show-icon style="margin-bottom: 12px" />
        <a-form-item label="备注">
          <a-textarea v-model:value="form.remarks" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 明细抽屉 -->
    <a-drawer v-model:open="detailOpen" :title="`留样明细 · ${current?.name || ''}`" width="560">
      <a-descriptions :column="2" size="small" bordered>
        <a-descriptions-item label="留样编号"><span class="mono">{{ current?.name }}</span></a-descriptions-item>
        <a-descriptions-item label="状态">
          <span class="pill" :class="statusClass(current?.status)">{{ current?.status }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="样品名称">{{ current?.sample_name }}</a-descriptions-item>
        <a-descriptions-item label="物料编码">{{ current?.material_code }}</a-descriptions-item>
        <a-descriptions-item label="批号">{{ current?.batch_no }}</a-descriptions-item>
        <a-descriptions-item label="容器序号">{{ current?.container_no }}</a-descriptions-item>
        <a-descriptions-item label="类别">{{ current?.category }}</a-descriptions-item>
        <a-descriptions-item label="留样量">{{ current?.retention_qty }} {{ current?.qty_uom }}</a-descriptions-item>
        <a-descriptions-item label="当前结存">{{ current?.current_qty }} {{ current?.qty_uom }}</a-descriptions-item>
        <a-descriptions-item label="预占量">{{ current?.reserved_qty }} {{ current?.qty_uom }}</a-descriptions-item>
        <a-descriptions-item label="留样日期">{{ current?.retention_date }}</a-descriptions-item>
        <a-descriptions-item label="留样期至">{{ current?.retention_due_date || '—' }}</a-descriptions-item>
        <a-descriptions-item label="观察样品">{{ current?.observed_flag ? '是' : '否' }}</a-descriptions-item>
        <a-descriptions-item label="储存条件">{{ current?.storage_condition || '—' }}</a-descriptions-item>
        <a-descriptions-item label="储存位置">{{ current?.storage_location || '—' }}</a-descriptions-item>
        <a-descriptions-item label="包装">{{ current?.package_count ? current.package_count + ' 件' : '—' }} {{ current?.package_spec || '' }}</a-descriptions-item>
        <a-descriptions-item label="关联检验样品">{{ current?.source_sample || '—' }}</a-descriptions-item>
        <a-descriptions-item label="留样人">{{ current?.retained_by }}</a-descriptions-item>
        <a-descriptions-item label="备注" :span="2">{{ current?.remarks || '—' }}</a-descriptions-item>
      </a-descriptions>

      <h4 style="margin: 16px 0 8px">库存操作流水</h4>
      <a-table
        v-if="detailLogs.length"
        :data-source="detailLogs"
        size="small"
        bordered
        :pagination="false"
        row-key="name"
      >
        <a-table-column title="日期" data-index="transaction_date" :width="100" />
        <a-table-column title="操作" data-index="transaction_type" :width="90" />
        <a-table-column title="变动量" data-index="qty_delta" :width="80" />
        <a-table-column title="结存" data-index="remaining_qty" :width="80" />
        <a-table-column title="经手人" data-index="operator" :width="120" />
        <a-table-column title="备注" data-index="remarks" />
      </a-table>
      <a-empty v-else description="暂无流水" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
    </a-drawer>

    <!-- 手动调整弹窗 -->
    <a-modal v-model:open="showAdjust" title="手动调整结存（仅 Manager）" :confirmLoading="adjusting" @ok="handleAdjust" ok-text="确认调整" cancel-text="取消">
      <a-form layout="vertical" style="margin-top: 8px">
        <a-form-item :label="`当前结存（${current?.qty_uom || ''}）`">
          <a-input :value="current?.current_qty" disabled />
        </a-form-item>
        <a-form-item label="调整后结存" required>
          <a-input-number v-model:value="adjustForm.new_qty" style="width: 100%" :min="0" />
        </a-form-item>
        <a-form-item label="调整原因" required>
          <a-textarea v-model:value="adjustForm.reason" :rows="2" placeholder="必填，将写入审计日志" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { listDoctype, getDoc, registerRetention, adjustRetentionStock, type RetentionProduct, type RetentionSample } from '@/api/lims'

interface LedgerRow extends RetentionSample {
  available_qty: number
}

const rows = ref<LedgerRow[]>([])
const products = ref<RetentionProduct[]>([])
const loading = ref(false)

const filters = reactive({ category: undefined as string | undefined, status: undefined as string | undefined, expireRange: undefined as string | undefined, batch_no: '' })

const categoryOptions = [
  { value: '关键物料', label: '关键物料' },
  { value: '成品（原料药）', label: '成品（原料药）' },
  { value: '外售产品', label: '外售产品' },
]
const statusOptions = ['在库', '部分使用', '已用尽', '待处理', '已销毁', '已转出'].map((s) => ({ value: s, label: s }))
const expireRangeOptions = [
  { value: 'exp30', label: '30 天内到期' },
  { value: 'exp90', label: '90 天内到期' },
  { value: 'over', label: '已超期' },
]
const expiryTypeOptions = [
  { value: '有效期至', label: '有效期至' },
  { value: '复验期至', label: '复验期至' },
]

const columns = [
  { title: '留样编号', key: 'name', dataIndex: 'name', width: 150 },
  { title: '样品名称', key: 'sample_name', dataIndex: 'sample_name' },
  { title: '批号', key: 'batch_no', dataIndex: 'batch_no', width: 110 },
  { title: '容器', key: 'container_no', dataIndex: 'container_no', width: 55 },
  { title: '类别', key: 'category', dataIndex: 'category', width: 100 },
  { title: '留样日期', key: 'retention_date', dataIndex: 'retention_date', width: 100 },
  { title: '留样量', key: 'qty', width: 100 },
  { title: '结存（预占）', key: 'stock', width: 120 },
  { title: '可用量', key: 'available', width: 90 },
  { title: '留样期至', key: 'retention_due_date', dataIndex: 'retention_due_date', width: 100 },
  { title: '观察', key: 'observed', width: 60 },
  { title: '状态', key: 'status', width: 80 },
  { title: '操作', key: 'actions', width: 130 },
]

const productOptions = computed(() =>
  products.value.filter((p) => p.is_active && !p.is_liquid).map((p) => ({
    value: p.name, label: `${p.product_code} · ${p.product_name}（${p.category}）`,
  })))

const stats = computed(() => {
  const today = new Date()
  const in90d = new Date(today.getTime() + 90 * 86400_000)
  return {
    inStock: rows.value.filter((r) => r.status === '在库' || r.status === '部分使用').length,
    pending: rows.value.filter((r) => r.status === '待处理').length,
    expiring: rows.value.filter((r) => {
      if (!r.retention_due_date || r.status === '已销毁' || r.status === '已转出') return false
      return new Date(r.retention_due_date) <= in90d
    }).length,
    observed: rows.value.filter((r) => r.observed_flag).length,
  }
})

async function loadData() {
  loading.value = true
  try {
    const conditions: Record<string, unknown> = {}
    if (filters.category) conditions.category = filters.category
    if (filters.status) conditions.status = filters.status
    const list = await listDoctype<RetentionSample>('HBOS Retention Sample', ['*'], conditions, 0, 'retention_date desc')
    let filtered = filters.batch_no
      ? list.filter((r) => r.batch_no?.includes(filters.batch_no))
      : list
    // 临期范围（客户端推导，与统计条口径一致）
    if (filters.expireRange) {
      const now = Date.now()
      const in30 = now + 30 * 86400_000
      const in90 = now + 90 * 86400_000
      filtered = filtered.filter((r) => {
        if (!r.retention_due_date || r.status === '已销毁' || r.status === '已转出') return false
        const due = new Date(r.retention_due_date).getTime()
        if (filters.expireRange === 'over') return due < now
        return due <= (filters.expireRange === 'exp30' ? in30 : in90)
      })
    }
    rows.value = filtered.map((r) => ({ ...r, available_qty: (r.current_qty || 0) - (r.reserved_qty || 0) }))
  } catch (e) {
    message.error('加载留样台账失败')
  } finally {
    loading.value = false
  }
}

async function loadProducts() {
  products.value = await listDoctype<RetentionProduct>('HBOS Retention Product', ['*'], {}, 0, 'modified desc')
}

function statusClass(status?: string): string {
  if (status === '在库' || status === '部分使用') return 'pill-green'
  if (status === '待处理') return 'pill-amber'
  if (status === '已销毁' || status === '已转出' || status === '已用尽') return 'pill-gray'
  return 'pill-gray'
}

// ---- 登记表单 ----
const showForm = ref(false)
const saving = ref(false)
const formUnit = ref('')
const formNote = ref('')
const form = reactive({
  retention_product: undefined as string | undefined,
  batch_no: '',
  container_no: 1,
  retention_date: new Date().toISOString().slice(0, 10),
  expiry_type: '有效期至',
  expiry_date: undefined as string | undefined,
  retention_due_date: undefined as string | undefined,
  retention_qty: undefined as string | undefined,
  package_count: undefined as number | undefined,
  storage_location: '',
  source: '',
  observed_flag: false,
  remarks: '',
})

function openRegister() {
  Object.assign(form, {
    retention_product: undefined, batch_no: '', container_no: 1,
    retention_date: new Date().toISOString().slice(0, 10),
    expiry_type: '有效期至', expiry_date: undefined, retention_due_date: undefined,
    retention_qty: undefined, package_count: undefined, storage_location: '',
    source: '', observed_flag: false, remarks: '',
  })
  formUnit.value = ''
  formNote.value = ''
  showForm.value = true
}

function onProductChange(val: string) {
  const p = products.value.find((x) => x.name === val)
  formUnit.value = p?.default_uom || ''
  if (p?.is_outsource) {
    formNote.value = '该产品为受托生产，登记后将直接以「已转出」状态落位（不经在库）。'
  } else if (p?.retention_qty_rule === '全检量 2 倍' && p.full_test_qty) {
    if (p.full_test_qty_uom === p.default_uom) {
      form.retention_qty = String(p.full_test_qty * 2)
      formNote.value = `已按全检量 ${p.full_test_qty} ${p.default_uom} × 2 自动计算，请人工复核。`
    } else {
      formNote.value = `全检量单位（${p.full_test_qty_uom}）与默认单位（${p.default_uom}）不一致，请人工填写留样量。`
    }
  } else if (p?.is_liquid) {
    formNote.value = ''
  } else {
    formNote.value = ''
  }
}

async function handleRegister() {
  if (!form.retention_product || !form.batch_no || !form.retention_date) {
    message.warning('请填写留样产品、批号、留样日期')
    return
  }
  if (form.retention_qty === undefined || form.retention_qty === '') {
    message.warning('请填写留样量')
    return
  }
  saving.value = true
  try {
    const res = await registerRetention({
      retention_product: form.retention_product,
      batch_no: form.batch_no,
      retention_date: form.retention_date,
      retention_qty: Number(form.retention_qty),
      package_count: form.package_count ?? null,
      source: form.source || undefined,
      expiry_type: form.expiry_type,
      expiry_date: form.expiry_date || undefined,
      retention_due_date: form.retention_due_date || undefined,
      storage_location: form.storage_location || undefined,
      observed_flag: form.observed_flag ? 1 : 0,
      container_no: form.container_no || 1,
      remarks: form.remarks || undefined,
    })
    message.success(`留样登记成功：${res.name}（${res.qty} ${formUnit.value}，${res.status}）`)
    if (res.note) message.info(res.note, 5)
    showForm.value = false
    await loadData()
  } catch (e: any) {
    message.error(e?.message || '登记失败')
  } finally {
    saving.value = false
  }
}

// ---- 明细 ----
const detailOpen = ref(false)
const current = ref<LedgerRow | null>(null)
const detailLogs = ref<Record<string, unknown>[]>([])

async function showDetail(record: LedgerRow) {
  current.value = record
  detailOpen.value = true
  const doc = await getDoc<RetentionSample & { stock_logs?: Record<string, unknown>[] }>('HBOS Retention Sample', record.name)
  detailLogs.value = (doc.stock_logs || []).slice().reverse()
}

// ---- 手动调整 ----
const showAdjust = ref(false)
const adjusting = ref(false)
const adjustForm = reactive({ new_qty: undefined as number | undefined, reason: '' })

function openAdjust(record: LedgerRow) {
  current.value = record
  adjustForm.new_qty = record.current_qty
  adjustForm.reason = ''
  showAdjust.value = true
}

async function handleAdjust() {
  if (!current.value) return
  if (adjustForm.new_qty === undefined || !adjustForm.reason) {
    message.warning('请填写调整后结存与原因')
    return
  }
  adjusting.value = true
  try {
    await adjustRetentionStock(current.value.name, adjustForm.new_qty, adjustForm.reason)
    message.success('调整成功，已写入流水与审计日志')
    showAdjust.value = false
    await loadData()
  } catch (e: any) {
    message.error(e?.message || '调整失败')
  } finally {
    adjusting.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadData(), loadProducts()])
})
</script>

<style scoped>
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}
.stat-card {
  background: var(--panel, #fff);
  border: 1px solid var(--line, #e5e7eb);
  border-radius: 10px;
  padding: 14px 16px;
}
.stat-label { font-size: 12px; color: #6b7280; }
.stat-value { font-size: 26px; font-weight: 700; margin-top: 4px; }
.stat-value.warn { color: #d97706; }
.stat-value.danger { color: #dc2626; }

.filter-bar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
.stock-warn { color: #dc2626; font-weight: 600; }
.stock-ok { color: var(--pass); font-weight: 600; }
.pill {
  display: inline-block; padding: 1px 8px; border-radius: 999px;
  font-size: 12px; white-space: nowrap;
}
.pill-green { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }
.pill-amber { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.pill-gray { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
</style>
