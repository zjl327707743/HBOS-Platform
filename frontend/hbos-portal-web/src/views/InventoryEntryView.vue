<template>
  <section class="inventory-page entry-page">
    <div class="entry-head">
      <div>
        <h1>库存单据</h1>
        <p>入库 / 领用出库 / 移库。选类型后表单会跟着变。</p>
      </div>
      <div v-if="isExisting" class="entry-head-meta">
        <div class="entry-docno">{{ name }}</div>
        <span class="entry-tag" :class="stateTag">
          {{ stateLabel }}
        </span>
      </div>
    </div>

    <!-- 列表（新建时显示）：仓库自建单据的入口 -->
    <div v-if="!isExisting" class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>最近单据</h2>
        <span class="entry-sub">草稿排前面——那是还需要处理的</span>
      </div>
      <div class="entry-pane-body" style="padding: 0">
        <div v-if="listState === 'loading'" style="padding: 20px" aria-busy="true" aria-label="正在加载单据">
          <div v-for="n in 5" :key="n" class="entry-skel entry-skel-row"></div>
        </div>

        <div v-else-if="listState === 'error'" class="inventory-state err" style="padding: 32px 20px">
          <StopOutlined class="inventory-state-icon" />
          <h3>取不到单据列表</h3>
          <p>这次没拿到数据——<b>不代表没有单据</b>。请重试。</p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="loadList">重试</a-button>
          </div>
        </div>

        <div v-else-if="!entries.length" class="inventory-state" style="padding: 32px 20px">
          <InboxOutlined class="inventory-state-icon" />
          <h3>还没有库存单据</h3>
          <p>下面选一个类型就能开第一张。</p>
        </div>

        <table v-else class="entry-table">
          <thead>
            <tr>
              <th>单号</th>
              <th>类型</th>
              <th>日期</th>
              <th>源 → 目标</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in entries" :key="row.name">
              <td>
                <RouterLink class="entry-link" :to="`/hbos/inventory/entry/${encodeURIComponent(row.name)}`">
                  {{ row.name }}
                </RouterLink>
              </td>
              <td>{{ entryTypeLabel(row.stockEntryType) }}</td>
              <td><span class="entry-mono">{{ row.postingDate || '—' }}</span></td>
              <td><span class="entry-mono entry-muted">{{ routeLabel(row) }}</span></td>
              <td>
                <span class="entry-tag" :class="rowState(row).tag">
                  {{ rowState(row).label }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ① 单据类型 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>① 单据类型</h2>
        <span class="entry-sub">{{ isExisting ? '已建单据不能改类型' : '选它决定下面出现哪些字段' }}</span>
      </div>
      <div class="entry-typebar">
        <button
          v-for="t in ENTRY_TYPES"
          :key="t.key"
          type="button"
          class="entry-typebtn"
          :aria-pressed="t.erpType === type.erpType"
          :disabled="isExisting"
          @click="pickType(t)"
        >
          <component :is="iconMap[t.icon]" />{{ t.label }}
        </button>
      </div>
      <div class="entry-pane-body">
        <p class="entry-note" style="margin: 0" v-html="type.hint"></p>
      </div>
    </div>

    <!-- 拍照识别建的草稿：本页不接管 -->
    <div v-if="fromIntake" class="entry-verdict info">
      <InfoCircleOutlined />
      <div>
        这张草稿是「入库拍照识别」建的，有专门的复核页。
        <RouterLink :to="`/hbos/inventory/draft/${encodeURIComponent(name)}`" class="entry-link">
          去草稿复核页
        </RouterLink>
      </div>
    </div>

    <!-- ② 明细 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>② 明细</h2>
        <span class="entry-sub">一行一个「物料 + 批次」</span>
      </div>
      <div class="entry-pane-body" style="padding: 0 0 20px">
        <div class="entry-items-wrap">
          <table class="entry-items">
            <thead>
              <tr>
                <th style="min-width: 150px">物料代码</th>
                <th class="num" style="width: 120px">数量</th>
                <th style="width: 70px">单位</th>
                <th style="min-width: 130px">批次</th>
                <th v-if="type.needsSource" style="min-width: 160px">源货位</th>
                <th v-if="type.needsTarget" style="min-width: 160px">目标货位</th>
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
                    @change="onItemChange(row)"
                  />
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
                <td>
                  <!-- 单位取自物料主数据，不在这里改 -->
                  <span class="entry-mono entry-muted">{{ row.uom || '—' }}</span>
                </td>
                <td>
                  <a-input
                    v-model:value="row.batchNo"
                    class="entry-mono"
                    placeholder="批号"
                    :disabled="readonly"
                  />
                </td>
                <td v-if="type.needsSource">
                  <a-select
                    v-model:value="row.sourceWarehouse"
                    show-search
                    :filter-option="filterWarehouse"
                    placeholder="选源货位"
                    style="width: 100%"
                    :disabled="readonly"
                    :options="warehouseOptions"
                  />
                </td>
                <td v-if="type.needsTarget">
                  <a-select
                    v-model:value="row.targetWarehouse"
                    show-search
                    :filter-option="filterWarehouse"
                    placeholder="选目标货位"
                    style="width: 100%"
                    :disabled="readonly"
                    :options="warehouseOptions"
                  />
                </td>
                <td>
                  <a-button
                    v-if="!readonly"
                    type="text"
                    danger
                    aria-label="删除本行"
                    @click="rows.splice(i, 1)"
                  >
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
            单位取自物料主数据，不在这里改。<b>批号管理</b>的物料必须填批次——
            没有批次就没有货位卡，出库也追不到源头。
          </p>
        </div>
      </div>
    </div>

    <!-- ③ 出库放行预检（仅领用出库） -->
    <div v-if="type.needsReleaseCheck" class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>③ 出库放行预检</h2>
        <span class="entry-sub">提交前就告诉你哪一批出不去</span>
      </div>
      <div class="entry-pane-body">
        <div v-if="!batchNos.length" class="entry-gate entry-gate-idle">
          <div class="entry-gate-head">
            <InfoCircleOutlined />
            <div>明细里填了批号之后，这里会逐个核对它们的放行手续。</div>
          </div>
        </div>

        <div v-else-if="checkState === 'loading'" class="entry-gate entry-gate-idle">
          <div class="entry-gate-head">
            <InfoCircleOutlined />
            <div>正在核对 {{ batchNos.length }} 个批次的放行手续…</div>
          </div>
        </div>

        <div v-else-if="checkState === 'error'" class="entry-gate">
          <div class="entry-gate-head">
            <WarningOutlined />
            <div>
              <b>核对没跑起来。</b>
              这不代表手续齐全——<b>请勿据此提交</b>，先重试一次。
              <div style="margin-top: 12px">
                <a-button size="small" @click="runReleaseCheck">重试核对</a-button>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="entry-gate" :class="{ ok: allReleased }">
          <div class="entry-gate-head">
            <WarningOutlined v-if="!allReleased" />
            <CheckCircleOutlined v-else />
            <div v-if="!allReleased">
              <b>有 {{ blocking.length }} 个批次未取得放行，提交会被拦下。</b>
              下面是每个批次的放行手续核对结果。缺什么在这里就补，别等提交才被打回。
            </div>
            <div v-else>
              <b>{{ checks.length }} 个批次的放行手续齐全，可以提交。</b>
            </div>
          </div>
          <div class="entry-gate-list">
            <div v-for="c in checks" :key="c.batchNo" class="entry-gate-item">
              <span><b>{{ c.batchNo }}</b></span>
              <span v-if="c.ok" class="ok">手续齐全</span>
              <span v-else class="miss">缺：{{ c.missing.join('、') }}</span>
            </div>
          </div>
        </div>

        <p class="entry-note">
          放行状态由 <b>LIMS</b> 写入，仓库侧改不了。缺手续请走 LIMS 完成检验与 COA 发布；
          本页只负责在提交前把话说清楚。
        </p>
      </div>
    </div>

    <!-- 其它信息 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>其它信息</h2>
        <span class="entry-sub">多数情况留空即可</span>
      </div>
      <div class="entry-pane-body">
        <div class="entry-head-fields">
          <label class="entry-field">
            <span>过账日期</span>
            <a-date-picker
              v-model:value="postingDate"
              value-format="YYYY-MM-DD"
              style="width: 100%"
              :disabled="readonly"
            />
          </label>
          <label class="entry-field" style="grid-column: span 2">
            <span>备注</span>
            <a-input v-model:value="remarks" placeholder="选填" :disabled="readonly" />
          </label>
        </div>
        <p class="entry-note">
          附加费用、序列号明细等 ERPNext 字段<b>本页不提供</b>——仓库日常用不到，
          需要时到 ERPNext 原表单里改。
        </p>
      </div>
    </div>

    <!-- 提交被拦：表单继续显示，错误放这里 -->
    <div v-if="blockedError" class="entry-verdict err">
      <LockOutlined />
      <div>
        <b>提交被拦下：{{ blockedError.title }}</b><br />
        <span v-html="blockedError.detail"></span>
        <div style="margin-top: 12px">
          <a-button size="small" @click="$router.push('/hbos/inventory/pending')">
            去看待检批次
          </a-button>
        </div>
      </div>
    </div>

    <!-- 已提交 -->
    <div v-if="docState === 'submitted'" class="inventory-dest glass-surface">
      <div class="inventory-state ok" style="padding: 28px 20px">
        <CheckCircleOutlined class="inventory-state-icon" />
        <h3>已提交</h3>
        <p>账面已入账。入库单还会自动生成货位卡与待检证，挂在对应批次的附件里。</p>
        <div class="inventory-state-actions">
          <a-button type="primary" @click="$router.push('/hbos/inventory/report/stock-balance')">
            看库存余额
          </a-button>
          <a-button @click="startNew">再建一张</a-button>
          <a-button danger :loading="cancelling" @click="confirmCancel">
            <RollbackOutlined /> 取消这张单据
          </a-button>
        </div>
      </div>
    </div>

    <!-- 已取消 -->
    <div v-else-if="docState === 'cancelled'" class="inventory-dest glass-surface">
      <div class="inventory-state" style="padding: 28px 20px">
        <StopOutlined class="inventory-state-icon" />
        <h3>这张单据已取消</h3>
        <p>
          账面已冲销。已取消的单据改不了，需要重做请新建一张。
          <template v-if="cancelledBatch">
            <br /><b>批次上的货位卡 / 待检证不会自动删除</b>——去批次页重新生成即可覆盖。
          </template>
        </p>
        <div class="inventory-state-actions">
          <a-button
            v-if="cancelledBatch"
            type="primary"
            @click="$router.push(`/hbos/inventory/batch/${encodeURIComponent(cancelledBatch)}`)"
          >
            去批次页重新生成卡片
          </a-button>
          <a-button @click="startNew">新建一张</a-button>
          <a-button @click="$router.push('/hbos/inventory/entry')">回单据列表</a-button>
        </div>
      </div>
    </div>

    <!-- 动作条：只读态不出现 -->
    <div v-else class="entry-actionbar">
      <span class="entry-actionbar-note">
        <b>提交后立刻入账。</b>提交前请核对数量与货位。
      </span>
      <a-button v-if="isExisting" :loading="discarding" @click="confirmDiscard">
        <DeleteOutlined /> 放弃这张草稿
      </a-button>
      <a-button :loading="saving" @click="save">
        <SaveOutlined /> {{ isExisting ? '保存修改' : '保存草稿' }}
      </a-button>
      <a-button
        type="primary"
        size="large"
        :loading="submitting"
        :disabled="!canSubmit"
        @click="confirmSubmit"
      >
        <SendOutlined /> {{ submitting ? '提交中…' : '提交' }}
      </a-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import {
  CheckCircleOutlined,
  CloseOutlined,
  DeleteOutlined,
  InfoCircleOutlined,
  InboxOutlined,
  LockOutlined,
  PlusOutlined,
  RollbackOutlined,
  SaveOutlined,
  SendOutlined,
  StopOutlined,
  SwapOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  ENTRY_TYPES,
  cancelStockEntry,
  checkReleaseForBatches,
  createStockEntry,
  discardStockEntry,
  findEntryType,
  findEntryTypeByKey,
  getStockEntry,
  listStockEntries,
  submitStockEntry,
  updateStockEntry,
  type EntryItem,
  type EntryRow,
  type EntryType,
  type ReleaseCheck,
} from '@/services/inventoryEntry'
import { getWarehouseSnapshot } from '@/services/inventoryMaster'
import { docState as docStateOf, warehouseShortLabel } from '@/services/inventoryDocs'
import { FrappeHttpError } from '@/services/frappeClient'

const route = useRoute()
const router = useRouter()

const iconMap: Record<string, unknown> = {
  in: PlusOutlined,
  out: SendOutlined,
  swap: SwapOutlined,
}

// --- 参数 ---
const name = computed(() => String(route.params.entryName || ''))
const isExisting = computed(() => Boolean(name.value))

// --- 状态 ---
const type = ref<EntryType>(ENTRY_TYPES[0]!)
const docstatus = ref(0)
const docState = computed(() => docStateOf(docstatus.value))
/** 已取消的单据既不是草稿也不可编辑——别把它显示成「草稿 · 未入账」 */
const stateTag = computed(
  () => ({ draft: 'draft', submitted: 'submitted', cancelled: 'cancelled' })[docState.value],
)
const stateLabel = computed(
  () =>
    ({
      draft: '草稿 · 未入账',
      submitted: '已提交 · 已入账',
      cancelled: '已取消 · 已冲销',
    })[docState.value],
)
/** 列表行的状态标签：`docstatus` 是 2 的要显示「已取消」，不能落进「草稿」 */
function rowState(row: EntryRow): { tag: string; label: string } {
  const state = docStateOf(row.docstatus)
  return {
    tag: { draft: 'draft', submitted: 'submitted', cancelled: 'cancelled' }[state],
    label: { draft: '草稿', submitted: '已提交', cancelled: '已取消' }[state],
  }
}
/**
 * 提交过的单据里那把批号（去重）。只有**入库**且**恰好一个批号**时，
 * 「已取消」块才给「去批次页重新生成卡片」的按钮 —— 多批号时不知道该去哪个，
 * 就只留文字提示。
 */
const docBatchNos = computed(() =>
  [...new Set(rows.value.map((r) => r.batchNo.trim()).filter(Boolean))].sort(),
)
const cancelledBatch = computed(() =>
  type.value.erpType === 'Material Receipt' && docBatchNos.value.length === 1
    ? docBatchNos.value[0]!
    : '',
)
const fromIntake = ref(false)
const postingDate = ref(todayIso())
const remarks = ref('')
const rows = ref<EntryItem[]>([])

const loading = ref(false)
const saving = ref(false)
const submitting = ref(false)
const discarding = ref(false)
const cancelling = ref(false)
const blockedError = ref<{ title: string; detail: string } | null>(null)

const entries = ref<EntryRow[]>([])
const listState = ref<'loading' | 'ready' | 'error'>('loading')

const checks = ref<ReleaseCheck[]>([])
const checkState = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
const warehouseOptions = ref<Array<{ value: string; label: string }>>([])

const readonly = computed(() => docState.value !== 'draft')

function todayIso(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function emptyRow(): EntryItem {
  return {
    itemCode: '',
    qty: null,
    uom: '',
    batchNo: '',
    sourceWarehouse: '',
    targetWarehouse: '',
  }
}

function addRow() {
  rows.value.push(emptyRow())
}

function entryTypeLabel(erpType?: string | null): string {
  return findEntryType(erpType)?.label || erpType || '—'
}

function routeLabel(row: EntryRow): string {
  const from = row.fromWarehouse ? warehouseShortLabel(row.fromWarehouse) : ''
  const to = row.toWarehouse ? warehouseShortLabel(row.toWarehouse) : ''
  if (from && to) return `${from} → ${to}`
  return from || to || '—'
}

function filterWarehouse(input: string, option?: { label?: string }) {
  return String(option?.label || '').toLowerCase().includes(input.toLowerCase())
}

function pickType(t: EntryType) {
  type.value = t
  // 换类型 = 换表单形态：源/目标列不同，明细里已有的货位要按新形态清掉，
  // 否则会出现「入库单里带着源货位」这种不该提交的组合。
  rows.value = rows.value.map((r) => ({
    ...emptyRow(),
    itemCode: r.itemCode,
    qty: r.qty,
    uom: r.uom,
    batchNo: r.batchNo,
  }))
}

// --- 物料代码变化 → 取单位（单位不让人填）---
let lookupSeq = 0
async function onItemChange(row: EntryItem) {
  const code = String(row.itemCode || '').trim()
  if (!code) {
    row.uom = ''
    return
  }
  const seq = ++lookupSeq
  try {
    const { callFrappeMethod } = await import('@/services/frappeClient')
    const item = await callFrappeMethod<{ stock_uom?: string } | null>('frappe.client.get_value', {
      doctype: 'Item',
      filters: JSON.stringify({ name: code }),
      fieldname: JSON.stringify(['stock_uom']),
    })
    if (seq !== lookupSeq) return
    row.uom = String(item?.stock_uom || '')
  } catch {
    /* 取不到单位不阻塞填写；提交时 ERPNext 会用自己的默认 */
  }
}

// --- 放行预检 ---
const batchNos = computed(() =>
  type.value.needsReleaseCheck
    ? [...new Set(rows.value.map((r) => r.batchNo.trim()).filter(Boolean))]
    : [],
)

const blocking = computed(() => checks.value.filter((c) => !c.ok))
const allReleased = computed(() => checks.value.length > 0 && blocking.value.length === 0)

const canSubmit = computed(() => {
  const filled = rows.value.filter((r) => r.itemCode && (r.qty ?? 0) > 0)
  if (!filled.length) return false
  // 出库要放行预检跑过、且没有拦下的批次
  if (type.value.needsReleaseCheck) {
    if (checkState.value !== 'ready') return false
    if (blocking.value.length) return false
  }
  return true
})

let checkTimer: ReturnType<typeof setTimeout> | null = null
function scheduleReleaseCheck() {
  if (!type.value.needsReleaseCheck) {
    checks.value = []
    checkState.value = 'idle'
    return
  }
  if (checkTimer) clearTimeout(checkTimer)
  // 批号是敲进去的，防抖 400ms —— 每敲一个字符查一次既费又抖
  checkTimer = setTimeout(() => void runReleaseCheck(), 400)
}

async function runReleaseCheck() {
  const wanted = batchNos.value
  if (!wanted.length) {
    checks.value = []
    checkState.value = 'idle'
    return
  }
  checkState.value = 'loading'
  try {
    checks.value = await checkReleaseForBatches(wanted)
    checkState.value = 'ready'
  } catch {
    // 核对失败**不能**当成「手续齐全」。界面会明确说「请勿据此提交」。
    checkState.value = 'error'
  }
}

watch(batchNos, scheduleReleaseCheck)

// --- 加载 ---
async function loadWarehouses() {
  try {
    const snap = await getWarehouseSnapshot()
    warehouseOptions.value = snap.all
      .filter((w) => Number(w.is_group) !== 1) // 分组节点不能存货（api.py 的既有规则）
      .map((w) => ({ value: w.name, label: warehouseShortLabel(w.name) }))
  } catch {
    warehouseOptions.value = []
  }
}

async function loadList() {
  listState.value = 'loading'
  try {
    entries.value = await listStockEntries()
    listState.value = 'ready'
  } catch {
    listState.value = 'error'
  }
}

async function loadEntry() {
  loading.value = true
  blockedError.value = null
  try {
    const doc = await getStockEntry(name.value)
    docstatus.value = doc.docstatus
    fromIntake.value = doc.fromIntake
    type.value = findEntryType(doc.stockEntryType) ?? ENTRY_TYPES[0]!
    postingDate.value = doc.postingDate || todayIso()
    remarks.value = doc.remarks
    rows.value = doc.items.length ? doc.items : [emptyRow()]
    if (type.value.needsReleaseCheck) void runReleaseCheck()
  } catch {
    // 取不到 —— 走统一错误态
    docstatus.value = -1
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadWarehouses()
  if (isExisting.value) {
    await loadEntry()
  } else {
    // 侧边栏的下一级菜单按 `?type=receipt|issue|transfer` 进来预选类型。
    // 认不出来的值**不猜**——静默用第一个类型（物料入库），与「刚进来」一致。
    const preset = findEntryTypeByKey(String(route.query.type || ''))
    if (preset) type.value = preset
    rows.value = [emptyRow()]
    await loadList()
  }
})

// 侧边栏的下一级菜单能在**同一个页面上**切换类型（组件不会重挂载，`onMounted`
// 只跑一次），所以要盯着查询串。已建单据不能改类型——与类型按钮同一条规则。
watch(
  () => route.query.type,
  (value) => {
    if (isExisting.value) return
    const preset = findEntryTypeByKey(String(value || ''))
    if (preset) pickType(preset)
  },
)

// 从「再建一张」切回新建
function startNew() {
  void router.push('/hbos/inventory/entry')
}

// --- 保存 ---
function payload() {
  return {
    stockEntryType: type.value.erpType,
    postingDate: postingDate.value,
    remarks: remarks.value,
    items: rows.value,
  }
}

/** 保存前的基本校验。空明细不能保存 —— 服务端 `items` 是必填（实测）。 */
function validateForSave(): string | null {
  const filled = rows.value.filter((r) => r.itemCode && (r.qty ?? 0) > 0)
  if (!filled.length) return '至少填一行明细（物料代码 + 数量大于 0）才能保存。'
  for (const r of filled) {
    if (type.value.needsSource && !r.sourceWarehouse) {
      return `明细「${r.itemCode}」还没选源货位。`
    }
    if (type.value.needsTarget && !r.targetWarehouse) {
      return `明细「${r.itemCode}」还没选目标货位。`
    }
  }
  return null
}

async function save() {
  const problem = validateForSave()
  if (problem) {
    Modal.warning({ title: '还不能保存', content: problem })
    return
  }

  saving.value = true
  blockedError.value = null
  try {
    if (isExisting.value) {
      await updateStockEntry(name.value, payload())
    } else {
      const created = await createStockEntry(payload())
      void router.replace(`/hbos/inventory/entry/${encodeURIComponent(created.name)}`)
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

// --- 提交 ---
function confirmSubmit() {
  if (!canSubmit.value) return
  const action = type.value.needsReleaseCheck ? '提交这张出库单？' : '提交这张单据？'
  Modal.confirm({
    title: action,
    content:
      '提交后立刻入账。' +
      (type.value.erpType === 'Material Receipt'
        ? '系统还会自动生成货位卡与待检证，挂在对应批次的附件里。'
        : '提交后如需撤销，可在本页取消（会反向过账）。'),
    okText: '确认提交',
    cancelText: '再核对一下',
    onOk: async () => {
      await doSubmit()
    },
  })
}

async function doSubmit() {
  submitting.value = true
  blockedError.value = null
  try {
    // 先存后提：让服务端手里这份与界面一致
    if (isExisting.value) {
      await updateStockEntry(name.value, payload())
      await submitStockEntry(name.value)
      docstatus.value = 1
    } else {
      const created = await createStockEntry(payload())
      await submitStockEntry(created.name)
      void router.replace(`/hbos/inventory/entry/${encodeURIComponent(created.name)}`)
    }
  } catch (error) {
    // 放行门禁抛的中文业务提示优先于英文状态码。
    // **表单继续显示**（这是刻意的）：用户要同时看到「我填了什么」和「为什么失败」。
    const text = error instanceof FrappeHttpError ? error.message : '提交未成功，请重试。'
    blockedError.value = {
      title: text.includes('放行') ? '出库放行校验未通过' : '提交未成功',
      detail: text,
    }
    // 真被门禁拦下时，顺手刷新预检，让「缺什么」与门禁口径一致
    if (text.includes('放行')) void runReleaseCheck()
  } finally {
    submitting.value = false
  }
}

// --- 放弃 ---
function confirmDiscard() {
  Modal.confirm({
    title: '放弃这张草稿？',
    content: '草稿会连同它上面的明细一起丢弃，不可恢复。已提交的单据不能在这里删除。',
    okText: '放弃草稿',
    okType: 'danger',
    cancelText: '保留',
    onOk: async () => {
      discarding.value = true
      try {
        await discardStockEntry(name.value)
        void router.push('/hbos/inventory/entry')
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

// --- 取消已提交的单据 ---
/**
 * 取消会**反向过账**，三种类型动的方向不同，文案必须分开说——
 * 都用一句「确定取消吗」的话，用户按下去之前不知道货会往哪走。
 */
const CANCEL_EFFECT: Record<string, string> = {
  'Material Receipt': '这批货会从目标货位扣回，账面等于没入过。',
  'Material Issue': '这批货会退回原货位，账面等于没领出过。',
  'Material Transfer': '这批货会从目标货位挪回源货位。',
}

function cancelContent(): string {
  const effect = CANCEL_EFFECT[type.value.erpType] || '账面会反向过账，回到提交前的数字。'
  const cards =
    type.value.erpType === 'Material Receipt'
      ? '注意：批次上已生成的「货位卡 / 待检证」不会跟着删除——若这批货要重做，去批次页重新生成一次即可覆盖。'
      : ''
  return `${effect}${cards}取消后这张单据改不了，也不能删（它是审计留痕）。`
}

function confirmCancel() {
  Modal.confirm({
    title: '取消这张单据？',
    content: cancelContent(),
    okText: '确认取消',
    okType: 'danger',
    cancelText: '再想想',
    onOk: async () => {
      cancelling.value = true
      try {
        await cancelStockEntry(name.value)
        // 就地切到「已取消」块——不跳走，用户刚按完就该看到结果
        docstatus.value = 2
      } catch (error) {
        // 权限、依赖、状态不对都由服务端拒；把它的中文提示原样呈现
        Modal.error({
          title: '取消失败',
          content: error instanceof FrappeHttpError ? error.message : '操作未成功，请重试。',
        })
      } finally {
        cancelling.value = false
      }
    },
  })
}
</script>
