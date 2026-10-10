<template>
  <section class="inventory-page entry-page">
    <div class="entry-head">
      <div>
        <h1>拣货单</h1>
        <p>填要拣的物料与数量，系统告诉你它们在哪些货位。</p>
      </div>
      <div v-if="isExisting" class="entry-head-meta">
        <div class="entry-docno">{{ name }}</div>
        <span class="entry-tag" :class="stateTag">
          {{ stateLabel }}
        </span>
      </div>
    </div>

    <!-- 列表 -->
    <div v-if="!isExisting" class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>最近拣货单</h2>
        <span class="entry-sub">草稿排前面——那是还需要处理的</span>
      </div>
      <div class="entry-pane-body" style="padding: 0">
        <div v-if="listState === 'loading'" style="padding: 20px" aria-busy="true" aria-label="正在加载拣货单">
          <div v-for="n in 5" :key="n" class="entry-skel entry-skel-row"></div>
        </div>

        <div v-else-if="listState === 'error'" class="inventory-state err" style="padding: 32px 20px">
          <StopOutlined class="inventory-state-icon" />
          <h3>取不到拣货单列表</h3>
          <p>这次没拿到数据——<b>不代表没有拣货单</b>。请重试。</p>
          <div class="inventory-state-actions">
            <a-button type="primary" @click="loadList">重试</a-button>
          </div>
        </div>

        <div v-else-if="!entries.length" class="inventory-state" style="padding: 32px 20px">
          <InboxOutlined class="inventory-state-icon" />
          <h3>还没有拣货单</h3>
          <p>下面填要拣的物料就能开第一张。</p>
        </div>

        <table v-else class="entry-table">
          <thead>
            <tr><th>单号</th><th>状态</th><th>范围</th><th>日期</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in entries" :key="row.name">
              <td>
                <RouterLink class="entry-link" :to="`/hbos/inventory/pick/${encodeURIComponent(row.name)}`">
                  {{ row.name }}
                </RouterLink>
              </td>
              <td>
                <span class="entry-tag" :class="rowTag(row.docstatus)">
                  {{ pickStatusLabel(row.status) }}
                </span>
              </td>
              <td><span class="entry-mono entry-muted">{{ shortLabel(row.parentWarehouse) || '全部货位' }}</span></td>
              <td><span class="entry-mono">{{ (row.createdAt || '').slice(0, 10) || '—' }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ① 范围 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>① 范围</h2>
        <span class="entry-sub">从哪个仓库范围内找货</span>
      </div>
      <div class="entry-pane-body">
        <div class="entry-head-fields">
          <label class="entry-field">
            <span>查找范围</span>
            <a-select
              v-model:value="parentWarehouse"
              show-search
              :filter-option="filterWarehouse"
              placeholder="全部货位"
              allow-clear
              style="width: 100%"
              :disabled="readonly"
              :options="warehouseOptions"
            />
          </label>
          <label class="entry-field" style="grid-column: span 2">
            <span>说明</span>
            <span class="entry-note" style="margin: 0">
              范围选一个<b>库位</b>时，定位会在它的全部下级货位里找——与报表的「含下级」同一套口径。
            </span>
          </label>
        </div>
      </div>
    </div>

    <!-- ② 要拣什么 -->
    <div class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>② 要拣什么</h2>
        <span class="entry-sub">货位要么自己填，要么点「定位货位」让系统找</span>
      </div>
      <div class="entry-pane-body" style="padding: 0 0 20px">
        <div class="entry-items-wrap">
          <table class="entry-items">
            <thead>
              <tr>
                <th style="min-width: 150px">物料代码</th>
                <th class="num" style="width: 120px">要拣数量</th>
                <th style="width: 70px">单位</th>
                <th style="min-width: 160px">货位</th>
                <th style="min-width: 130px">批次</th>
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
                <td><span class="entry-mono entry-muted">{{ row.uom || '—' }}</span></td>
                <td>
                  <a-select
                    v-model:value="row.warehouse"
                    show-search
                    :filter-option="filterWarehouse"
                    placeholder="选货位（或先填一个再定位）"
                    allow-clear
                    style="width: 100%"
                    :disabled="readonly"
                    :options="warehouseOptions"
                  />
                </td>
                <td>
                  <a-input v-model:value="row.batchNo" class="entry-mono" placeholder="批号" :disabled="readonly" />
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
          <a-button v-if="!readonly" size="small" class="entry-mt" @click="rows.push(emptyRow())">
            <PlusOutlined /> 添加一行
          </a-button>

          <a-button
            size="small"
            class="entry-mt"
            style="margin-left: 12px"
            :loading="locating"
            :disabled="readonly || !canLocate"
            @click="locate"
          >
            <AimOutlined /> 定位货位
          </a-button>

          <!--
            「定位货位」的两个前提，必须写在按钮旁边而不是等点了才报错。
            **这里刻意不提「货位可留空」**——实测：ERPNext v16 的
            `Pick List.before_save` 只要 locations 非空就会跑 `validate_warehouses`，
            空货位行 `insert` 必报 `Row 1: Warehouse is required`（与 pick_manually
            无关，见 pick_list.py 的 before_save）。所以「先存空行、再定位」走不通，
            定位前必须先把这张单存下来，而存下来就得有货位。
          -->
          <p class="entry-note">
            <template v-if="!isExisting">
              <b>先填货位，再保存。</b>空货位行存不进去（服务端会报「Warehouse is
              required」）。「定位货位」是 ERPNext 的单据方法，需要单据已有单号——
              所以先填一个货位存下来，再用定位改。
            </template>
            <template v-else-if="!parentWarehouse">
              <b>先选「查找范围」，再定位。</b>不选范围，系统不知道去哪找——它靠
              <code class="entry-mono">parent_warehouse</code> 决定搜索范围。
            </template>
            <template v-else>
              「定位货位」调的是 ERPNext 自己的 <code class="entry-mono">set_item_locations</code>——
              它按库存、预留、批次规则去找，与本页无关的规则一条都不重写。
              <b>它会替换掉下面所有还没拣的行。</b>
            </template>
          </p>
        </div>
      </div>
    </div>

    <!-- ③ 定位结果 -->
    <div v-if="shortages.length || locations.length" class="inventory-dest glass-surface">
      <div class="entry-pane-head">
        <h2>③ 定位结果</h2>
        <span class="entry-sub">逐条列出每个货位能拣多少</span>
      </div>
      <div class="entry-pane-body">
        <div v-if="locateEmptyReason" class="entry-verdict warn" style="margin: 0 0 16px">
          <WarningOutlined />
          <div><b>定位没找到任何货位。</b><br />{{ locateEmptyReason }}</div>
        </div>

        <div v-else-if="shortages.length" class="entry-verdict err" style="margin: 0 0 16px">
          <WarningOutlined />
          <div>
            <b>有 {{ shortages.length }} 项凑不够。</b>
            <div v-for="s in shortages" :key="s.itemCode" style="margin-top: 6px">
              <span class="entry-mono">{{ s.itemCode }}</span>：要拣 {{ fmt(s.required) }}，
              全部货位加起来只有 {{ fmt(s.located) }}——<b>差 {{ fmt(s.gap) }}</b>。
            </div>
            可以改小数量，或先在库存单据里入库。
          </div>
        </div>
        <div v-else-if="locations.length" class="entry-verdict ok" style="margin: 0 0 16px">
          <CheckCircleOutlined />
          <div><b>都够。</b>下面是逐货位的分配结果。</div>
        </div>

        <table v-if="locations.length" class="entry-items">
          <thead>
            <tr>
              <th>物料</th><th>货位</th><th>批次</th>
              <th class="num">可拣</th><th class="num">已拣</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(l, i) in locations" :key="i">
              <td class="entry-mono">{{ l.itemCode }}</td>
              <td class="entry-mono">{{ shortLabel(l.warehouse) }}</td>
              <td class="entry-mono">{{ l.batchNo || '—' }}</td>
              <td class="num entry-mono">{{ l.qty === null ? '—' : fmt(l.qty) }}</td>
              <td class="num entry-mono">{{ l.pickedQty ? fmt(l.pickedQty) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 提交被拦 -->
    <div v-if="blockedError" class="entry-verdict err">
      <StopOutlined />
      <div><b>提交未成功。</b><br />{{ blockedError }}</div>
    </div>

    <!-- 已提交 -->
    <div v-if="docState === 'submitted'" class="inventory-dest glass-surface">
      <div class="inventory-state ok" style="padding: 28px 20px">
        <CheckCircleOutlined class="inventory-state-icon" />
        <h3>已提交拣货单</h3>
        <p>接下来按货位把货拣出来，再开一张<b>移库单</b>把货挪到目标货位。拣货单本身不动库存。</p>
        <div class="inventory-state-actions">
          <a-button type="primary" @click="$router.push('/hbos/inventory/entry')">去建移库单</a-button>
          <a-button @click="startNew">再建一张</a-button>
          <a-button danger :loading="cancelling" @click="confirmCancel">
            <RollbackOutlined /> 取消这张拣货单
          </a-button>
        </div>
      </div>
    </div>

    <!-- 已取消 -->
    <div v-else-if="docState === 'cancelled'" class="inventory-dest glass-surface">
      <div class="inventory-state" style="padding: 28px 20px">
        <StopOutlined class="inventory-state-icon" />
        <h3>这张拣货单已取消</h3>
        <p>已取消的拣货单改不了，需要重做请新建一张。</p>
        <div class="inventory-state-actions">
          <a-button type="primary" @click="startNew">新建一张</a-button>
          <a-button @click="$router.push('/hbos/inventory/pick')">回拣货单列表</a-button>
        </div>
      </div>
    </div>

    <div v-else class="entry-actionbar">
      <span class="entry-actionbar-note">
        <b>先保存，再定位。</b>提交后拣货单锁定，货位不再变。
      </span>
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
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import {
  AimOutlined,
  CheckCircleOutlined,
  CloseOutlined,
  DeleteOutlined,
  InboxOutlined,
  PlusOutlined,
  RollbackOutlined,
  SaveOutlined,
  SendOutlined,
  StopOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  cancelPickList,
  createPickList,
  discardPickList,
  findShortages,
  getPickList,
  listPickLists,
  explainEmptyLocate,
  locatePickList,
  submitPickList,
  type PickListRow,
  type PickLocation,
  type PickShortage,
} from '@/services/inventoryPick'
import { getWarehouseSnapshot, selectableWarehouses } from '@/services/inventoryMaster'
import { docState as docStateOf, warehouseShortLabel } from '@/services/inventoryDocs'
import { FrappeHttpError } from '@/services/frappeClient'

const route = useRoute()
const router = useRouter()

const name = computed(() => String(route.params.pickName || ''))
const isExisting = computed(() => Boolean(name.value))

const docstatus = ref(0)
const status = ref('')
const parentWarehouse = ref<string | undefined>(undefined)
const rows = ref<Array<{ itemCode: string; qty: number | null; uom: string; warehouse: string; batchNo: string }>>([])

/** 上次定位前记下的「要拣数量」，用于事后判断够不够 —— 定位会替换掉明细行 */
const required = ref<Record<string, number>>({})
const locations = ref<PickLocation[]>([])
const shortages = ref<PickShortage[]>([])

const listState = ref<'loading' | 'ready' | 'error'>('loading')
const entries = ref<PickListRow[]>([])
const saving = ref(false)
const submitting = ref(false)
const discarding = ref(false)
const cancelling = ref(false)
const locating = ref(false)
const blockedError = ref('')
const warehouseOptions = ref<Array<{ value: string; label: string }>>([])

const docState = computed(() => docStateOf(docstatus.value))
/** 列表行的标签配色：docstatus=2 要灰调（已取消），不能落进「草稿」的琥珀色 */
function rowTag(docstatusValue: number): string {
  return { draft: 'draft', submitted: 'submitted', cancelled: 'cancelled' }[
    docStateOf(docstatusValue)
  ] as string
}
/** 已取消的拣货单也要灰调，别落进「草稿」的琥珀色 */
const stateTag = computed(
  () => ({ draft: 'draft', submitted: 'submitted', cancelled: 'cancelled' })[docState.value],
)
const stateLabel = computed(() =>
  docState.value === 'draft' ? '草稿 · 未拣' : pickStatusLabel(status.value),
)
const readonly = computed(() => docStateOf(docstatus.value) !== 'draft')
/**
 * 「定位货位」的两个前提：
 * 1. 单据已存在 —— `set_item_locations` 是单据方法，按 dt+dn 从库里加载；
 * 2. **已选「查找范围」** —— 它靠 `parent_warehouse` 决定去哪搜，
 *    没范围就无处可搜，会把未拣的行清掉且一行也不填（实测）。
 */
const canLocate = computed(
  () => isExisting.value && !readonly.value && Boolean(parentWarehouse.value),
)

/** 定位回来一行都没有时的解释（与「库存不够」分开） */
const locateEmptyReason = ref('')
const canSubmit = computed(() =>
  rows.value.some((r) => r.itemCode && (r.qty ?? 0) > 0),
)

function emptyRow() {
  return { itemCode: '', qty: null as number | null, uom: '', warehouse: '', batchNo: '' }
}

function fmt(n: number | null): string {
  return n === null ? '—' : Number(n).toFixed(3)
}

function shortLabel(v?: string | null): string {
  return warehouseShortLabel(v || '')
}

function pickStatusLabel(v?: string | null): string {
  const map: Record<string, string> = {
    Draft: '草稿',
    Open: '待拣',
    'Partly Delivered': '部分已发',
    Completed: '已完成',
    Cancelled: '已取消',
  }
  return map[String(v || '')] || String(v || '草稿')
}

function filterWarehouse(input: string, option?: { label?: string }) {
  return String(option?.label || '').toLowerCase().includes(input.toLowerCase())
}

async function onItemChange(row: (typeof rows.value)[number]) {
  const code = String(row.itemCode || '').trim()
  if (!code) {
    row.uom = ''
    return
  }
  try {
    const { callFrappeMethod } = await import('@/services/frappeClient')
    const item = await callFrappeMethod<{ stock_uom?: string } | null>('frappe.client.get_value', {
      doctype: 'Item',
      filters: JSON.stringify({ name: code }),
      fieldname: JSON.stringify(['stock_uom']),
    })
    row.uom = String(item?.stock_uom || '')
  } catch {
    /* 取不到不阻塞 */
  }
}

async function loadWarehouses() {
  try {
    const snap = await getWarehouseSnapshot()
    // 能选的货位 = 非分组 + 未停用（规则见 inventoryMaster.isSelectableWarehouse）。
    // 早先这里直接 `.map()` 铺全部，**分组节点也能被选进拣货单**——选了服务端会拒。
    warehouseOptions.value = selectableWarehouses(snap).map((w) => ({
      value: w.name,
      label: shortLabel(w.name),
    }))
  } catch {
    warehouseOptions.value = []
  }
}

async function loadList() {
  listState.value = 'loading'
  try {
    entries.value = await listPickLists()
    listState.value = 'ready'
  } catch {
    listState.value = 'error'
  }
}

function applyDoc(doc: Awaited<ReturnType<typeof getPickList>>) {
  docstatus.value = doc.docstatus
  status.value = doc.status
  parentWarehouse.value = doc.parentWarehouse || undefined
  locations.value = doc.locations
  rows.value = doc.locations.length
    ? doc.locations.map((l) => ({
        itemCode: l.itemCode,
        qty: l.qty,
        uom: l.uom,
        warehouse: l.warehouse,
        batchNo: l.batchNo,
      }))
    : [emptyRow()]
  recomputeShortages()
}

async function loadDoc() {
  try {
    applyDoc(await getPickList(name.value))
  } catch {
    docstatus.value = -1
  }
}

function recomputeShortages() {
  // 只在「有定位过」时判断够不够——没定位过时 located 为空，会说全都缺
  if (!Object.keys(required.value).length) {
    shortages.value = []
    return
  }
  shortages.value = findShortages(required.value, locations.value)
}

function payload() {
  return {
    parentWarehouse: parentWarehouse.value || '',
    locations: rows.value.map((r) => ({
      itemCode: r.itemCode,
      qty: r.qty,
      uom: r.uom,
      warehouse: r.warehouse,
      batchNo: r.batchNo,
      stockQty: null,
      pickedQty: null,
    })),
  }
}

function validate(): string | null {
  if (!rows.value.some((r) => r.itemCode && (r.qty ?? 0) > 0)) {
    return '至少填一行（物料代码 + 数量大于 0）才能保存。'
  }
  // 货位必填：ERPNext 的 `before_save` 只要有明细行就会跑 `validate_warehouses`
  // （`pick_list.py`，与 `pick_manually` 无关），空货位行 insert 必报
  // 「Row N: Warehouse is required」。所以在这里先拦一道，给中文提示，
  // 别让用户填完一整张单才吃到一个英文行号报错。
  if (rows.value.some((r) => r.itemCode && (r.qty ?? 0) > 0 && !String(r.warehouse || '').trim())) {
    return '每一行都要选货位。想让它自己找，先填一个货位存下来，再点「定位货位」重算。'
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
      applyDoc(await update())
    } else {
      const created = await createPickList(payload())
      // 记住要拣数量，供定位后比对
      rememberRequired()
      void router.replace(`/hbos/inventory/pick/${encodeURIComponent(created.name)}`)
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

async function update() {
  const { updatePickList } = await import('@/services/inventoryPick')
  return updatePickList(name.value, payload())
}

function rememberRequired() {
  const map: Record<string, number> = {}
  for (const r of rows.value) {
    const code = r.itemCode.trim()
    if (!code) continue
    map[code] = (map[code] || 0) + Number(r.qty ?? 0)
  }
  required.value = map
}

async function locate() {
  if (!canLocate.value) return
  // 定位会替换明细行，所以先把「要拣多少」记下来，否则无从判断够不够
  rememberRequired()
  locating.value = true
  blockedError.value = ''
  try {
    // 定位前先落盘：set_item_locations 按 dt+dn 从库里加载，读的是**已保存**的内容
    await update()
    const doc = await locatePickList(name.value)
    applyDoc(doc)
    // 「一行都没定位到」与「定位到了但不够」必须分开说——原因和下一步都不同
    if (!doc.locations.length) {
      locateEmptyReason.value =
        explainEmptyLocate(parentWarehouse.value || '') ||
        '在所选范围内没有找到这些物料的可用货位。可能是范围内确实没有库存，或货位下没有该批次。'
    } else {
      locateEmptyReason.value = ''
    }
  } catch (error) {
    blockedError.value =
      error instanceof FrappeHttpError ? error.message : '定位未成功，请重试。'
  } finally {
    locating.value = false
  }
}

function confirmSubmit() {
  if (!canSubmit.value) return
  Modal.confirm({
    title: '提交这张拣货单？',
    content:
      '提交后拣货单锁定，货位不再变。注意：拣货单本身不动账面——把货挪走要另开一张移库单。',
    okText: '确认提交',
    cancelText: '再核对一下',
    onOk: async () => {
      submitting.value = true
      blockedError.value = ''
      try {
        if (isExisting.value) await update()
        const target = isExisting.value ? name.value : (await createPickList(payload())).name
        await submitPickList(target)
        if (!isExisting.value) void router.replace(`/hbos/inventory/pick/${encodeURIComponent(target)}`)
        docstatus.value = 1
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
    title: '放弃这张拣货单？',
    content: '草稿会连同它上面的明细一起丢弃，不可恢复。',
    okText: '放弃草稿',
    okType: 'danger',
    cancelText: '保留',
    onOk: async () => {
      discarding.value = true
      try {
        await discardPickList(name.value)
        void router.push('/hbos/inventory/pick')
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

/**
 * 取消已提交的拣货单。
 *
 * 文案要讲清一件事：**它不动账面**。否则用户会以为「取消 = 把货挪回去」，
 * 而挪货是移库单的事。
 */
function confirmCancel() {
  Modal.confirm({
    title: '取消这张拣货单？',
    content:
      '拣货单本身不动账面，取消只是解开它对货位的锁定，之后可以重新建一张。' +
      '取消后这张单据改不了，也不能删（它是审计留痕）。',
    okText: '确认取消',
    okType: 'danger',
    cancelText: '再想想',
    onOk: async () => {
      cancelling.value = true
      try {
        await cancelPickList(name.value)
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

function startNew() {
  void router.push('/hbos/inventory/pick')
}

/**
 * 把页面恢复到「新建」状态。
 *
 * **必须在换单号时显式重置**：「再建一张」只是 push 到 `/pick`——同一条路由记录、
 * 只有参数变了，Vue 不会重挂载组件，`onMounted` 不再跑。不重置的话 `docstatus`
 * 还是旧单据的（已取消的会继续显示「已取消」块）、`rows` 还是旧明细，
 * 刷新一次才干净（Owner 实测报的）。
 */
function resetToNew() {
  docstatus.value = 0
  status.value = ''
  parentWarehouse.value = undefined
  locations.value = []
  shortages.value = []
  blockedError.value = ''
  locateEmptyReason.value = ''
  required.value = {}
  rows.value = [emptyRow()]
}

onMounted(async () => {
  await loadWarehouses()
  if (isExisting.value) {
    await loadDoc()
  } else {
    resetToNew()
    await loadList()
  }
})

// 从「已建单据」回到「新建」时组件不重挂载（同一条路由记录），所以要自己重置。
watch(isExisting, async (nowExisting) => {
  if (nowExisting) {
    await loadDoc()
  } else {
    resetToNew()
    await loadList()
  }
})
</script>
