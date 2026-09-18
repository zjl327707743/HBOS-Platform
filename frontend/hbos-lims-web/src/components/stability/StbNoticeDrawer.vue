<template>
  <a-drawer v-model:open="open" title="新建稳定性考察通知" :width="600" placement="right">
    <p class="stb-gate-sub">保存为草稿后，按通知单状态机走「注册人员复核 → 提交 → QC 经理确认 → 批准」。</p>

    <div class="stb-drawer-section">
      <h3>基础信息</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>产品 *</label>
          <a-select
            v-model:value="form.stability_product"
            :options="productOptions"
            :loading="loading"
            show-search
            :filter-option="false"
            placeholder="选择已启用的稳定性产品"
            style="width: 100%"
            @search="searchProducts"
            @change="onProductChange"
          />
        </div>
        <div class="stb-form-field">
          <label>考察分类</label>
          <a-input :value="selectedProduct?.category || '按产品主数据带出'" disabled />
        </div>
        <div class="stb-form-field full">
          <label>考察原因 *</label>
          <a-textarea
            v-model:value="form.study_reason"
            :rows="2"
            placeholder="填写申请依据、批次来源或补充说明"
          />
        </div>
      </div>
    </div>

    <div class="stb-drawer-section">
      <h3>试验条件 *（{{ form.study_conditions.length }} 个）</h3>
      <div v-for="(c, i) in form.study_conditions" :key="i" class="stb-form-row">
        <a-select v-model:value="c.condition_type" :options="conditionTypeOptions" style="width: 150px" placeholder="条件类型" />
        <a-select
          v-model:value="c.storage_cond"
          :options="conditionOptions"
          style="flex: 1"
          placeholder="储存条件"
          show-search
          :filter-option="false"
          @search="searchConditions"
        />
        <a-input v-model:value="c.remark" style="width: 150px" placeholder="备注（可选）" />
        <a-button type="text" danger :disabled="form.study_conditions.length <= 1" @click="form.study_conditions.splice(i, 1)">
          <template #icon><MinusCircleOutlined /></template>
        </a-button>
      </div>
      <a-button size="small" @click="addCondition">
        <template #icon><PlusOutlined /></template>
        添加条件
      </a-button>
      <div v-if="multiCondition" class="stb-form-hint warn">
        条件超过 2 个：必须填写「补充原因」，且提交前须经注册人员复核（register_review）。
      </div>
    </div>

    <div class="stb-drawer-section">
      <h3>考察批次 *（{{ form.batches.length }} 批）</h3>
      <div v-for="(b, i) in form.batches" :key="i" class="stb-form-row">
        <a-input v-model:value="b.batch_no" style="flex: 1" placeholder="批次号" />
        <a-input v-model:value="b.batch_size" style="width: 140px" placeholder="批量（可选）" />
        <a-date-picker v-model:value="b.manufacture_date" style="width: 150px" value-format="YYYY-MM-DD" placeholder="生产日期" />
        <a-button type="text" danger :disabled="form.batches.length <= 1" @click="form.batches.splice(i, 1)">
          <template #icon><MinusCircleOutlined /></template>
        </a-button>
      </div>
      <a-button size="small" @click="form.batches.push({ batch_no: '', batch_size: '', manufacture_date: undefined })">
        <template #icon><PlusOutlined /></template>
        添加批次
      </a-button>
      <div v-if="batchHint" class="stb-form-hint">{{ batchHint }}</div>
    </div>

    <div class="stb-drawer-section">
      <h3>数量与包装</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>考察用量</label>
          <a-input-number v-model:value="form.qty" :min="0" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>单位</label>
          <a-select v-model:value="form.qty_uom" :options="uomOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field full">
          <label>包装描述</label>
          <a-input v-model:value="form.pack_desc" placeholder="如 30 片/瓶" />
        </div>
      </div>
    </div>

    <div v-if="multiCondition" class="stb-drawer-section">
      <h3>补充原因 *</h3>
      <a-textarea
        v-model:value="form.extra_condition_reason"
        :rows="2"
        placeholder="说明条件超过 2 个的依据（法规要求 / 客户要求等）"
      />
    </div>

    <div class="stb-notice">
      保存草稿后由受控业务方法写入；批准时写入冻结快照，此后标准/方法/限度只读。
    </div>

    <template #footer>
      <a-button @click="open = false">取消</a-button>
      <a-button type="primary" :loading="saving" @click="saveDraft">保存草稿</a-button>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { createNotice, master, products, type MasterRow, type ProductRow } from '@/api/stability'

const emit = defineEmits<{ created: [name: string] }>()

const open = ref(false)
const loading = ref(false)
const saving = ref(false)

const productList = ref<ProductRow[]>([])
const conditionList = ref<MasterRow[]>([])

const UOM_OPTIONS = ['g', 'kg', 'mg', 'mL', 'L', '瓶', '支', '袋', '桶', '盒', '其他']
const CONDITION_TYPES = ['长期', '加速', '中间', '影响因素-高温', '影响因素-高湿', '影响因素-强光']

// 考察分类 → 最少批次（与后端 stability_contract.CATEGORY_MIN_BATCHES 对齐，仅作填写提示）
const CATEGORY_MIN_BATCHES: Record<string, number> = {
  '新产品/工艺验证类': 3, '变更类': 1, '年度持续稳定性考察类': 1, '其它类': 1,
}
// 考察分类 → 必备条件（与 stability_contract.CATEGORY_REQUIRED_CONDITION_TYPES 对齐）
const CATEGORY_REQUIRED: Record<string, string[]> = {
  '新产品/工艺验证类': ['长期', '加速'], '变更类': ['长期'],
  '年度持续稳定性考察类': ['长期'], '其它类': ['长期'],
}

const form = reactive({
  stability_product: undefined as string | undefined,
  study_reason: '',
  study_conditions: [{ condition_type: '长期', storage_cond: undefined as string | undefined, remark: '' }],
  batches: [{ batch_no: '', batch_size: '', manufacture_date: undefined as string | undefined }],
  qty: undefined as number | undefined,
  qty_uom: undefined as string | undefined,
  pack_desc: '',
  extra_condition_reason: '',
})

const productOptions = computed(() =>
  productList.value.map((p) => ({ value: p.name, label: `${p.product_name}（${p.product_code}）` })))
const selectedProduct = computed(() =>
  productList.value.find((p) => p.name === form.stability_product))
const conditionOptions = computed(() =>
  conditionList.value.map((c) => ({
    value: c.name, label: `${c.description || c.name}（${c.condition_type}）`,
  })))
const conditionTypeOptions = CONDITION_TYPES.map((v) => ({ value: v, label: v }))
const uomOptions = UOM_OPTIONS.map((v) => ({ value: v, label: v }))

const multiCondition = computed(() => form.study_conditions.length > 2)
const batchHint = computed(() => {
  const cat = selectedProduct.value?.category
  if (!cat) return ''
  const min = CATEGORY_MIN_BATCHES[cat] ?? 1
  const req = CATEGORY_REQUIRED[cat] || []
  const parts = []
  if (min > 1) parts.push(`分类「${cat}」至少 ${min} 批`)
  if (req.length) parts.push(`必须包含条件：${req.join(' / ')}`)
  return parts.join('；')
})

function addCondition() {
  form.study_conditions.push({ condition_type: '长期', storage_cond: undefined, remark: '' })
}

function onProductChange() {
  const p = selectedProduct.value
  if (p) {
    form.qty_uom = p.default_uom
    form.pack_desc = p.pack_desc || ''
  }
}

async function loadProducts(keyword?: string) {
  try {
    const res = await products(keyword)
    productList.value = res.rows
  } catch {
    // 错误已由 client 拦截层弹出
  }
}

async function loadConditions(keyword?: string) {
  try {
    const res = await master('HBOS Stability Condition', keyword)
    conditionList.value = res.rows
  } catch {
    // 错误已由 client 拦截层弹出
  }
}

function searchProducts(kw: string) {
  void loadProducts(kw)
}
function searchConditions(kw: string) {
  void loadConditions(kw)
}

async function show() {
  open.value = true
  loading.value = true
  try {
    await Promise.all([loadProducts(), loadConditions()])
  } finally {
    loading.value = false
  }
}
defineExpose({ show })

function reset() {
  form.stability_product = undefined
  form.study_reason = ''
  form.study_conditions = [{ condition_type: '长期', storage_cond: undefined, remark: '' }]
  form.batches = [{ batch_no: '', batch_size: '', manufacture_date: undefined }]
  form.qty = undefined
  form.qty_uom = undefined
  form.pack_desc = ''
  form.extra_condition_reason = ''
}

async function saveDraft() {
  if (!form.stability_product) return message.warning('请选择产品')
  if (!form.study_reason.trim()) return message.warning('考察原因必填')
  if (form.study_conditions.some((c) => !c.storage_cond)) return message.warning('每个条件都必须选择储存条件')
  if (form.batches.some((b) => !b.batch_no.trim())) return message.warning('批次号必填')
  if (multiCondition.value && !form.extra_condition_reason.trim()) {
    return message.warning('条件超过 2 个时必须填写补充原因')
  }

  saving.value = true
  try {
    const res = await createNotice({
      stability_product: form.stability_product,
      study_reason: form.study_reason.trim(),
      study_conditions: form.study_conditions.map((c) => ({
        condition_type: c.condition_type, storage_cond: c.storage_cond!, remark: c.remark,
      })),
      batches: form.batches.map((b) => ({
        batch_no: b.batch_no.trim(), batch_size: b.batch_size, manufacture_date: b.manufacture_date,
      })),
      extra_condition_reason: multiCondition.value ? form.extra_condition_reason.trim() : undefined,
      qty: form.qty,
      qty_uom: form.qty_uom,
      pack_desc: form.pack_desc,
    })
    message.success(`已创建通知单草稿 ${res.name}`)
    open.value = false
    reset()
    emit('created', res.name)
  } catch {
    // 具体错误已由 client 拦截层弹出（含后端校验与越权拦截）
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.stb-form-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
.stb-form-hint { font-size: 12px; color: var(--muted); margin-top: 8px; }
.stb-form-hint.warn { color: var(--warn); }
</style>
