<template>
  <section class="inventory-page entry-page">
    <div class="entry-head">
      <div>
        <h1>库存对账</h1>
        <p>按实盘数调账。填之前先看到账面是多少——差异自己就出来了。</p>
      </div>
      <div v-if="isExisting" class="entry-head-meta">
        <div class="entry-docno">{{ name }}</div>
        <span class="entry-tag" :class="docstatus === 1 ? 'submitted' : 'draft'">
          {{ docstatus === 1 ? '已调账' : '草稿 · 未调账' }}
        </span>
      </div>
    </div>

    <!-- 列表 -->
    <div v-if="!isExisting" class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>最近对账单</h2>
        <span class="entry-sub">草稿排前面——那是还没调的</span>
      </div>
      <div class="entry-pane-body" style="padding: 0">
        <div v-if="listState === 'loading'" style="padding: 20px" aria-busy="true" aria-label="正在加载对账单">
          <div v-for="n in 5" :key="n" class="entry-skel entry-skel-row"></div>
        </div>
        <div v-else-if="listState === 'error'" class="inventory-state err" style="padding: 32px 20px">
          <StopOutlined class="inventory-state-icon" />
          <h3>取不到对账单列表</h3>
          <p>这次没拿到数据——<b>不代表没有对账单</b>。请重试。</p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="loadList">重试</a-button>
          </div>
        </div>
        <div v-else-if="!entries.length" class="inventory-state" style="padding: 32px 20px">
          <InboxOutlined class="inventory-state-icon" />
          <h3>还没有对账单</h3>
          <p>下面填实盘数就能开第一张。</p>
        </div>
        <table v-else class="entry-table">
          <thead><tr><th>单号</th><th>状态</th><th>过账日期</th></tr></thead>
          <tbody>
            <tr v-for="row in entries" :key="row.name">
              <td>
                <RouterLink class="entry-link" :to="`/hbos/inventory/reconcile/${encodeURIComponent(row.name)}`">
                  {{ row.name }}
                </RouterLink>
              </td>
              <td>
                <span class="entry-tag" :class="row.docstatus === 1 ? 'submitted' : 'draft'">
                  {{ row.docstatus === 1 ? '已调账' : '草稿' }}
                </span>
              </td>
              <td><span class="entry-mono">{{ row.postingDate || '—' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 口径说明 -->
    <div class="entry-verdict info">
      <InfoCircleOutlined />
      <div>
        <b>只填「实盘数」，差额由系统算。</b>
        账面数在你填完物料与货位后自动查出来，差异列立刻跟着变；
        <b>提交后按差额调账，记入差异科目</b>——这是财务口径的调整，不只是改个数字。
      </div>
    </div>

    <!-- ① 基本信息 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>① 基本信息</h2>
        <span class="entry-sub">过账日期决定用哪一天的账面做基准</span>
      </div>
      <div class="entry-pane-body">
        <div class="entry-head-fields">
          <label class="entry-field">
            <span>过账日期 <em>*</em></span>
            <a-date-picker
              v-model:value="postingDate"
              value-format="YYYY-MM-DD"
              style="width: 100%"
              :disabled="readonly"
            />
          </label>
          <label class="entry-field" style="grid-column: span 2">
            <span>默认货位（只用于带出新行）</span>
            <a-select
              v-model:value="setWarehouse"
              show-search
              :filter-option="filterWarehouse"
              placeholder="（不设）"
              allow-clear
              style="width: 100%"
              :disabled="readonly"
              :options="warehouseOptions"
            />
          </label>
        </div>
      </div>
    </div>

    <!-- ② 盘点明细 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>② 盘点明细</h2>
        <span class="entry-sub">一行一个「物料 + 批次 + 货位」</span>
      </div>
      <div class="entry-pane-body" style="padding: 0 0 20px">
        <div class="entry-items-wrap">
          <table class="entry-items">
            <thead>
              <tr>
                <th style="min-width: 140px">物料代码</th>
                <th style="min-width: 130px">批次</th>
                <th style="min-width: 160px">货位</th>
                <th style="width: 70px">单位</th>
                <th class="num" style="width: 110px">账面数</th>
                <th class="num" style="width: 120px">实盘数</th>
                <th class="num" style="width: 120px">差异</th>
                <th style="width: 44px"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in rows" :key="i">
                <td>
                  <a-input
                    v-model:value="row.itemCode"
                    class="entry-mono"
                    placeholder="物料代码"
                    :disabled="readonly"
                    @change="onRowChanged(row)"
                  />
                </td>
                <td>
                  <a-input
                    v-model:value="row.batchNo"
                    class="entry-mono"
                    placeholder="批号"
                    :disabled="readonly"
                    @change="onRowChanged(row)"
                  />
                </td>
                <td>
                  <a-select
                    v-model:value="row.warehouse"
                    show-search
                    :filter-option="filterWarehouse"
                    placeholder="选货位"
                    style="width: 100%"
                    :disabled="readonly"
                    :options="warehouseOptions"
                    @change="onRowChanged(row)"
                  />
                </td>
                <td><span class="entry-mono entry-muted">{{ row.uom || '—' }}</span></td>
                <td class="num">
                  <span class="entry-mono entry-muted">
                    {{ row.currentQty === null ? '—' : fmt(row.currentQty) }}
                  </span>
                </td>
                <td class="num">
                  <a-input-number
                    v-model:value="row.qty"
                    :min="0"
                    :step="0.001"
                    style="width: 100%"
                    :disabled="readonly"
                  />
                </td>
                <td class="num">
                  <span class="entry-diff" :class="diffClass(row)">{{ diffText(row) }}</span>
                </td>
                <td>
                  <a-button v-if="!readonly" type="text" danger aria-label="删除本行" @click="rows.splice(i, 1)">
                    <CloseOutlined />
                  </a-button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div style="padding: 0 20px">
          <a-button v-if="!readonly" size="small" class="entry-mt" @click="addRow">
            <PlusOutlined /> 添加一行
          </a-button>
          <p class="entry-note">
            账面数由 <code class="entry-mono">get_stock_balance_for</code> 查出，与本页无关的估值规则不重写。
            <b>批号管理的物料必须填批次</b>——不填服务端会拒。
          </p>
        </div>
      </div>
    </div>

    <!-- ③ 差异合计 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>③ 差异合计</h2>
        <span class="entry-sub">提交前先看这里</span>
      </div>
      <div class="entry-pane-body">
        <div v-if="summary.unknown" class="entry-verdict warn" style="margin: 0">
          <WarningOutlined />
          <div>
            有 {{ summary.unknown }} 行<b>还没查到账面数</b>（物料或货位没填全，或查不到）。
            这些行<b>不计入下面的差异</b>，也不该直接提交——先补齐。
          </div>
        </div>

        <div v-else-if="!summary.surplus && !summary.shortage" class="entry-verdict ok" style="margin: 0">
          <CheckCircleOutlined />
          <div>
            <b>所有行都对得上。</b>
            {{ summary.matched }} 行实盘数等于账面数，没有差异需要调。
            <b>如果是这样，这张单其实不需要提交</b>——没有差异就没有要调的东西。
          </div>
        </div>

        <div v-else class="entry-verdict warn" style="margin: 0">
          <WarningOutlined />
          <div>
            <b>{{ summary.surplus + summary.shortage }} 行对不上</b>（{{ summary.matched }} 行一致）。
            <div style="margin-top: 8px">
              盘盈合计 <b class="entry-diff plus">{{ fmt(totals.gain) }}</b>
              · 盘亏合计 <b class="entry-diff minus">{{ fmt(totals.loss) }}</b>
            </div>
            <div style="margin-top: 8px">
              <b>差异会记入差异科目</b>——这是财务口径的调整，不只是改个数字。提交前请确认实盘数没错。
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="blockedError" class="entry-verdict err">
      <StopOutlined />
      <div><b>提交未成功。</b><br />{{ blockedError }}</div>
    </div>

    <div v-if="docstatus === 1" class="inventory-dest glass-surface">
      <div class="inventory-state ok" style="padding: 28px 20px">
        <CheckCircleOutlined class="inventory-state-icon" />
        <h3>已调账</h3>
        <p>账面已按实盘数调整，差异记入差异科目。可在库存余额里复核。</p>
        <div class="inventory-state-actions">
          <a-button type="primary" @click="$router.push('/hbos/inventory/report/stock-balance')">
            看库存余额
          </a-button>
          <a-button @click="startNew">再建一张</a-button>
        </div>
      </div>
    </div>

    <div v-else class="entry-actionbar">
      <span class="entry-actionbar-note"><b>提交后按差额调账。</b>提交前请核对实盘数。</span>
      <a-button v-if="isExisting" :loading="discarding" @click="confirmDiscard">
        <DeleteOutlined /> 放弃这张草稿
      </a-button>
      <a-button :loading="saving" @click="save">
        <SaveOutlined /> {{ isExisting ? '保存修改' : '保存草稿' }}
      </a-button>
      <a-button type="primary" size="large" :loading="submitting" :disabled="!canSubmit" @click="confirmSubmit">
        <SendOutlined /> {{ submitting ? '提交中…' : '提交' }}
      </a-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  CloseOutlined,
  DeleteOutlined,
  InboxOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  SaveOutlined,
  SendOutlined,
  StopOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  createReconciliation,
  discardReconciliation,
  fetchCurrentQty,
  getReconciliation,
  listReconciliations,
  submitReconciliation,
  summarizeVariance,
  updateReconciliation,
  varianceOf,
  varianceTotals,
  type ReconcileItem,
  type ReconcileListRow,
  type ReconcileRowMeta,
} from '@/services/inventoryReconcile'
import { getWarehouseSnapshot } from '@/services/inventoryMaster'
import { warehouseShortLabel } from '@/services/inventoryDocs'
import { FrappeHttpError } from '@/services/frappeClient'

const route = useRoute()
const router = useRouter()

const name = computed(() => String(route.params.reconcileName || ''))
const isExisting = computed(() => Boolean(name.value))

const docstatus = ref(0)
const postingDate = ref(todayIso())
const postingTime = ref('12:00:00')
const setWarehouse = ref<string | undefined>(undefined)
const rows = ref<ReconcileItem[]>([])

const listState = ref<'loading' | 'ready' | 'error'>('loading')
const entries = ref<ReconcileListRow[]>([])
const saving = ref(false)
const submitting = ref(false)
const discarding = ref(false)
const blockedError = ref('')
const warehouseOptions = ref<Array<{ value: string; label: string }>>([])

const readonly = computed(() => docstatus.value === 1)
const summary = computed(() => summarizeVariance(rows.value))
const totals = computed(() => varianceTotals(rows.value))
const canSubmit = computed(() =>
  rows.value.some((r) => r.itemCode && r.warehouse && r.qty !== null),
)

function todayIso(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function emptyRow(): ReconcileItem {
  return {
    itemCode: '',
    batchNo: '',
    warehouse: setWarehouse.value || '',
    uom: '',
    qty: null,
    currentQty: null,
  }
}

function addRow() {
  rows.value.push(emptyRow())
}

function fmt(n: number | null): string {
  return n === null ? '—' : Number(n).toFixed(3)
}

function diffText(row: ReconcileItem): string {
  const d = varianceOf(row)
  return d === null ? '—' : (d > 0 ? '+' : '') + d.toFixed(3)
}

function diffClass(row: ReconcileItem): string {
  const d = varianceOf(row)
  if (d === null) return 'zero'
  if (d > 0) return 'plus'
  if (d < 0) return 'minus'
  return 'zero'
}

function filterWarehouse(input: string, option?: { label?: string }) {
  return String(option?.label || '').toLowerCase().includes(input.toLowerCase())
}

// --- 物料/货位/批次任一变化 → 重查账面数（防抖 + 丢弃迟到响应）---
let lookupTimer: ReturnType<typeof setTimeout> | null = null
let lookupSeq = 0

function onRowChanged(_row: ReconcileItem) {
  if (lookupTimer) clearTimeout(lookupTimer)
  lookupTimer = setTimeout(() => void refreshAll(), 350)
}

async function refreshAll() {
  const seq = ++lookupSeq
  // 逐行查（每行有独立批次），并行发起
  const updated = await Promise.all(
    rows.value.map(async (row) => {
      if (!row.itemCode || !row.warehouse) {
        return { ...row, currentQty: null }
      }
      const [qty, uom] = await Promise.all([
        fetchCurrentQty(row.itemCode, row.warehouse, postingDate.value, postingTime.value, row.batchNo),
        lookupUom(row.itemCode),
      ])
      return { ...row, currentQty: qty, uom: uom || row.uom }
    }),
  )
  // 迟到的响应丢弃
  if (seq !== lookupSeq) return
  rows.value = updated
}

async function lookupUom(itemCode: string): Promise<string> {
  try {
    const { callFrappeMethod } = await import('@/services/frappeClient')
    const item = await callFrappeMethod<{ stock_uom?: string } | null>('frappe.client.get_value', {
      doctype: 'Item',
      filters: JSON.stringify({ name: itemCode }),
      fieldname: JSON.stringify(['stock_uom']),
    })
    return String(item?.stock_uom || '')
  } catch {
    return ''
  }
}

async function loadWarehouses() {
  try {
    const snap = await getWarehouseSnapshot()
    warehouseOptions.value = snap.all
      .filter((w) => Number(w.is_group) !== 1) // 分组节点不能存货
      .map((w) => ({ value: w.name, label: warehouseShortLabel(w.name) }))
  } catch {
    warehouseOptions.value = []
  }
}

async function loadList() {
  listState.value = 'loading'
  try {
    entries.value = await listReconciliations()
    listState.value = 'ready'
  } catch {
    listState.value = 'error'
  }
}

function applyDoc(doc: ReconcileRowMeta) {
  docstatus.value = doc.docstatus
  postingDate.value = doc.postingDate || todayIso()
  postingTime.value = doc.postingTime || '12:00:00'
  setWarehouse.value = doc.setWarehouse || undefined
  rows.value = doc.items.length ? doc.items : [emptyRow()]
}

async function loadDoc() {
  try {
    applyDoc(await getReconciliation(name.value))
    void refreshAll()
  } catch {
    docstatus.value = -1
  }
}

function payload() {
  return {
    postingDate: postingDate.value,
    postingTime: postingTime.value,
    setWarehouse: setWarehouse.value || '',
    items: rows.value,
  }
}

function validate(): string | null {
  const filled = rows.value.filter((r) => r.itemCode)
  if (!filled.length) return '至少填一行（物料代码 + 货位 + 实盘数）才能保存。'
  for (const r of filled) {
    if (!r.warehouse) return `明细「${r.itemCode}」还没选货位。`
    if (r.qty === null) return `明细「${r.itemCode}」还没填实盘数。`
  }
  return null
}

async function save() {
  const problem = validate()
  if (problem) {
    Modal.warning({ title: '还不能保存', content: problem })
    return
  }
  saving.value = true
  blockedError.value = ''
  try {
    if (isExisting.value) {
      applyDoc(await updateReconciliation(name.value, payload()))
    } else {
      const created = await createReconciliation(payload())
      void router.replace(`/hbos/inventory/reconcile/${encodeURIComponent(created.name)}`)
    }
  } catch (error) {
    Modal.error({
      title: '保存失败',
      content: error instanceof FrappeHttpError ? error.message : '保存未成功，请重试。',
    })
  } finally {
    saving.value = false
  }
}

function confirmSubmit() {
  if (!canSubmit.value) return
  Modal.confirm({
    title: '提交这张对账单？',
    content:
      '提交后按差额调账——盘盈会增加账面，盘亏会减少账面，差额记入差异科目。这是财务口径的调整，提交前请确认实盘数没错。',
    okText: '确认提交',
    cancelText: '再核对一下',
    onOk: async () => {
      submitting.value = true
      blockedError.value = ''
      try {
        if (isExisting.value) {
          await updateReconciliation(name.value, payload())
          await submitReconciliation(name.value)
          docstatus.value = 1
        } else {
          const created = await createReconciliation(payload())
          await submitReconciliation(created.name)
          void router.replace(`/hbos/inventory/reconcile/${encodeURIComponent(created.name)}`)
          docstatus.value = 1
        }
      } catch (error) {
        blockedError.value =
          error instanceof FrappeHttpError ? error.message : '提交未成功，请重试。'
      } finally {
        submitting.value = false
      }
    },
  })
}

function confirmDiscard() {
  Modal.confirm({
    title: '放弃这张对账单？',
    content: '草稿会连同它上面的明细一起丢弃，不可恢复。账面还没有被调整。',
    okText: '放弃草稿',
    okType: 'danger',
    cancelText: '保留',
    onOk: async () => {
      discarding.value = true
      try {
        await discardReconciliation(name.value)
        void router.push('/hbos/inventory/reconcile')
      } catch (error) {
        Modal.error({
          title: '放弃失败',
          content: error instanceof FrappeHttpError ? error.message : '操作未成功，请重试。',
        })
      } finally {
        discarding.value = false
      }
    },
  })
}

function startNew() {
  void router.push('/hbos/inventory/reconcile')
}

onMounted(async () => {
  await loadWarehouses()
  if (isExisting.value) {
    await loadDoc()
  } else {
    rows.value = [emptyRow()]
    await loadList()
  }
})
</script>
