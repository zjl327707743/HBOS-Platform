<template>
  <a-drawer v-model:open="open" title="登记稳定性样品入箱" :width="620" placement="right">
    <p class="stb-gate-sub">保存后自动按方案/通知单生成时间点；生成失败会在样品上留告警，可手动重跑。</p>

    <div class="stb-drawer-section">
      <h3>考察依据</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>考察通知单 *</label>
          <a-select
            v-model:value="form.notice"
            :options="noticeOptions"
            :loading="loading"
            show-search
            :filter-option="false"
            placeholder="选择已批准的通知单"
            style="width: 100%"
            @change="onNoticeChange"
          />
        </div>
        <div class="stb-form-field">
          <label>稳定性方案{{ yearly ? '（年度类免填）' : ' *' }}</label>
          <a-select
            v-model:value="form.protocol"
            :options="protocolOptions"
            :disabled="yearly"
            :loading="loading"
            placeholder="选择已批准的方案"
            style="width: 100%"
          />
        </div>
        <div class="stb-form-field">
          <label>稳定性产品 *</label>
          <a-select v-model:value="form.stability_product" :options="productOptions" style="width: 100%" disabled />
        </div>
        <div class="stb-form-field">
          <label>品名</label>
          <a-input v-model:value="form.sample_name" placeholder="默认取产品名" />
        </div>
      </div>
    </div>

    <div class="stb-drawer-section">
      <h3>批次与日期</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>批号 *</label>
          <a-input v-model:value="form.batch_no" />
        </div>
        <div class="stb-form-field">
          <label>批量</label>
          <a-input v-model:value="form.batch_size" />
        </div>
        <div class="stb-form-field">
          <label>生产日期</label>
          <a-date-picker v-model:value="form.manufacture_date" style="width: 100%" value-format="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>终结日期</label>
          <a-date-picker v-model:value="form.finish_date" style="width: 100%" value-format="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>送样日期</label>
          <a-date-picker v-model:value="form.send_date" style="width: 100%" value-format="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>全检样送样日期</label>
          <a-date-picker v-model:value="form.full_test_sample_date" style="width: 100%" value-format="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>入箱日期 *</label>
          <a-date-picker v-model:value="form.in_date" style="width: 100%" value-format="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>取样号码</label>
          <a-input v-model:value="form.label_no" placeholder="标签编号/取样号" />
        </div>
      </div>
      <div class="stb-form-hint">
        送样日期距「全检样送样日期」不得超过 3 周（方案 4.1）；两项都填时由后端校验。
      </div>
    </div>

    <div class="stb-drawer-section">
      <h3>储存与数量</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>储存条件 *</label>
          <a-select v-model:value="form.storage_cond" :options="conditionOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>稳定性室 *</label>
          <a-select v-model:value="form.room" :options="roomOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>箱位</label>
          <a-input v-model:value="form.storage_location" placeholder="如 STB-01-A-03" />
        </div>
        <div class="stb-form-field">
          <label>放置方向</label>
          <a-select v-model:value="form.inverted_flag" :options="invertedOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>数量 *</label>
          <a-input-number v-model:value="form.init_qty" :min="0" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>单位</label>
          <a-select v-model:value="form.qty_uom" :options="uomOptions" style="width: 100%" />
        </div>
      </div>
    </div>

    <div v-if="needEvaluation" class="stb-drawer-section">
      <h3 style="color: var(--warn)">进箱超生产 1 个月：强制评估四件套 *</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field full">
          <label>评估结论 *</label>
          <a-textarea v-model:value="form.evaluation_conclusion" :rows="2"
                      placeholder="全检：含量 / 有关物质 / 水分" />
        </div>
        <div class="stb-form-field">
          <label>评估日期 *</label>
          <a-date-picker v-model:value="form.evaluation_date" style="width: 100%" value-format="YYYY-MM-DD" />
        </div>
      </div>
      <div class="stb-form-hint warn">
        入箱不会被拦截，但必须填写评估结论、评估人与评估日期（方案 5.3.1 / 门禁 14），并留审计。
      </div>
    </div>

    <template #footer>
      <a-button @click="open = false">取消</a-button>
      <a-button type="primary" :loading="saving" @click="save">保存并生成时间点</a-button>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  master, notices, products, protocols, registerSample,
  type MasterRow, type NoticeRow, type ProductRow, type ProtocolRow,
} from '@/api/stability'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{ created: [name: string] }>()
const auth = useAuthStore()

const open = ref(false)
const loading = ref(false)
const saving = ref(false)

const noticeList = ref<NoticeRow[]>([])
const protocolList = ref<ProtocolRow[]>([])
const productList = ref<ProductRow[]>([])
const conditionList = ref<MasterRow[]>([])
const roomList = ref<MasterRow[]>([])

const UOM = ['g', 'kg', 'mg', 'mL', 'L', '瓶', '支', '袋', '桶', '盒', '其他']
const YEARLY = '年度持续稳定性考察类'

const form = reactive({
  notice: undefined as string | undefined,
  protocol: undefined as string | undefined,
  stability_product: undefined as string | undefined,
  sample_name: '',
  batch_no: '',
  batch_size: '',
  manufacture_date: undefined as string | undefined,
  finish_date: undefined as string | undefined,
  send_date: undefined as string | undefined,
  full_test_sample_date: undefined as string | undefined,
  in_date: undefined as string | undefined,
  label_no: '',
  storage_cond: undefined as string | undefined,
  room: undefined as string | undefined,
  storage_location: '',
  inverted_flag: '正置',
  init_qty: undefined as number | undefined,
  qty_uom: undefined as string | undefined,
  evaluation_conclusion: '',
  evaluation_date: undefined as string | undefined,
})

const selectedNotice = computed(() => noticeList.value.find((n) => n.name === form.notice))
const selectedProduct = computed(() => productList.value.find((p) => p.name === form.stability_product))
const yearly = computed(() => selectedProduct.value?.category === YEARLY)

const noticeOptions = computed(() =>
  noticeList.value.map((n) => ({
    value: n.name, label: `${n.name}${n.product_name ? ' · ' + n.product_name : ''}`,
  })))
const protocolOptions = computed(() =>
  protocolList.value
    .filter((p) => !form.notice || p.notice === form.notice)
    .map((p) => ({ value: p.name, label: `${p.name}（v${p.version}）` })))
const productOptions = computed(() =>
  productList.value.map((p) => ({ value: p.name, label: `${p.product_name}（${p.product_code}）` })))
const conditionOptions = computed(() =>
  conditionList.value.map((c) => ({
    value: c.name, label: `${c.description || c.name}（${c.condition_type}）`,
  })))
const roomOptions = computed(() =>
  roomList.value.map((r) => ({ value: r.name, label: (r.room_name as string) || r.name })))
const uomOptions = UOM.map((v) => ({ value: v, label: v }))
const invertedOptions = ['正置', '倒置'].map((v) => ({ value: v, label: v }))

/** 入箱 − 生产 > 1 个月 → 需强制评估（与后端同口径） */
const needEvaluation = computed(() => {
  const inD = form.in_date
  const mfg = form.manufacture_date
  if (!inD || !mfg) return false
  const d1 = new Date(inD)
  const d2 = new Date(mfg)
  const limit = new Date(d2)
  limit.setMonth(limit.getMonth() + 1)
  return d1 > limit
})

function onNoticeChange() {
  const n = selectedNotice.value
  if (!n) return
  form.stability_product = n.stability_product
  if (n.category === YEARLY) {
    form.protocol = undefined
  } else {
    const match = protocolList.value.find((p) => p.notice === n.name)
    form.protocol = match?.name
  }
  const p = productList.value.find((x) => x.name === n.stability_product)
  if (p) {
    form.qty_uom = p.default_uom
    form.sample_name = form.sample_name || p.product_name
  }
}

async function show() {
  open.value = true
  loading.value = true
  try {
    const [ns, prods, conds, rooms, protos] = await Promise.all([
      notices({ status: '已批准', limit: 200 }),
      products(),
      master('HBOS Stability Condition'),
      master('HBOS Stability Room'),
      protocols({ status: '已批准', limit: 200 }),
    ])
    noticeList.value = ns.rows
    productList.value = prods.rows
    conditionList.value = conds.rows
    roomList.value = rooms.rows
    protocolList.value = protos.rows
  } catch {
    // 错误已由 client 拦截层弹出
  } finally {
    loading.value = false
  }
}
defineExpose({ show })

async function save() {
  if (!form.notice) return message.warning('请选择考察通知单')
  if (!yearly.value && !form.protocol) return message.warning('请选择稳定性方案')
  if (!form.stability_product) return message.warning('未取到产品，请确认通知单是否已批准')
  if (!form.batch_no.trim()) return message.warning('批号必填')
  if (!form.in_date) return message.warning('入箱日期必填')
  if (!form.init_qty || form.init_qty <= 0) return message.warning('数量必须大于 0')
  if (!form.storage_cond) return message.warning('请选择储存条件')
  if (needEvaluation.value) {
    if (!form.evaluation_conclusion.trim()) return message.warning('超期进箱必须填写评估结论')
    if (!form.evaluation_date) return message.warning('超期进箱必须填写评估日期')
  }

  saving.value = true
  try {
    const res = await registerSample({
      notice: form.notice,
      protocol: yearly.value ? undefined : form.protocol,
      stability_product: form.stability_product,
      sample_name: form.sample_name || undefined,
      batch_no: form.batch_no.trim(),
      batch_size: form.batch_size || undefined,
      manufacture_date: form.manufacture_date,
      finish_date: form.finish_date,
      send_date: form.send_date,
      full_test_sample_date: form.full_test_sample_date,
      in_date: form.in_date,
      label_no: form.label_no || undefined,
      storage_cond: form.storage_cond,
      room: form.room,
      storage_location: form.storage_location || undefined,
      inverted_flag: form.inverted_flag,
      init_qty: form.init_qty,
      qty_uom: form.qty_uom,
      evaluation_conclusion: needEvaluation.value ? form.evaluation_conclusion.trim() : undefined,
      evaluated_by: needEvaluation.value ? auth.user?.name : undefined,
      evaluation_date: needEvaluation.value ? form.evaluation_date : undefined,
    })
    message.success(`已登记入箱 ${res.name}`)
    open.value = false
    reset()
    emit('created', res.name)
  } catch {
    // 具体错误已由 client 拦截层弹出（含 3 周 / 评估四件套 / 状态前置等后端校验）
  } finally {
    saving.value = false
  }
}

function reset() {
  form.notice = undefined
  form.protocol = undefined
  form.stability_product = undefined
  form.sample_name = ''
  form.batch_no = ''
  form.batch_size = ''
  form.manufacture_date = undefined
  form.finish_date = undefined
  form.send_date = undefined
  form.full_test_sample_date = undefined
  form.in_date = undefined
  form.label_no = ''
  form.storage_cond = undefined
  form.room = undefined
  form.storage_location = ''
  form.inverted_flag = '正置'
  form.init_qty = undefined
  form.qty_uom = undefined
  form.evaluation_conclusion = ''
  form.evaluation_date = undefined
}
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.stb-form-hint { font-size: 12px; color: var(--muted); margin-top: 8px; }
.stb-form-hint.warn { color: var(--warn); }
</style>
