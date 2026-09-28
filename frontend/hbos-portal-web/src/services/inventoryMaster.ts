import { callFrappeMethod, frappeAssetUrl } from '@/services/frappeClient'
import { runReport } from '@/services/inventoryReports'

/**
 * 仓储库存 —— 主数据浏览（物料 / 货位）。**只读**。
 *
 * 本文件**不写任何主数据**。理由不是「做不了」，是不该由这个前端做：
 *
 * - 物料：**SAP 分配代码**，平台不自造。识别到未知物料时只提示去建档。
 * - 物料上的 HBOS 字段：入库拍照识别的写入路径有明确的「**仅补空、不覆盖人工修正**」
 *   语义，不该在这儿开第二个入口。
 * - 货位：层级直接决定「哪些节点能存货」，改错会破坏出入库落点。
 *
 * 修改入口在 ERPNext 主数据页面（需相应角色）。
 */

// ---------------------------------------------------------------------------
// 物料
// ---------------------------------------------------------------------------

export const ITEM_LIST_LIMIT = 200

export interface ItemRow {
  name: string
  item_name: string
  item_group?: string
  stock_uom?: string
  hbos_product_kind?: string
  hbos_workshop?: string
  hbos_storage_condition?: string
  hbos_shelf_life_type?: string
  hbos_shelf_life_months?: number
  has_batch_no?: number
  disabled?: number
}

const ITEM_FIELDS = [
  'name',
  'item_name',
  'item_group',
  'stock_uom',
  'hbos_product_kind',
  'hbos_workshop',
  'hbos_storage_condition',
  'hbos_shelf_life_type',
  'hbos_shelf_life_months',
  'has_batch_no',
  'disabled',
]

export interface ItemListResult {
  rows: ItemRow[]
  /** 匹配总数。列表最多取 ITEM_LIST_LIMIT 条，所以总数与行数可能不等 */
  total: number
  truncated: boolean
}

/**
 * 搜物料。空关键词返回前 N 条。
 *
 * 用 `or_filters`：用户输入的既可能是代码也可能是名称，不该逼他选一个。
 * 不搜 `item_name` 之外的描述字段——那会让结果变得难解释。
 */
export async function searchItems(keyword: string): Promise<ItemListResult> {
  const q = keyword.trim()
  const base: Record<string, unknown> = {
    doctype: 'Item',
    fields: JSON.stringify(ITEM_FIELDS),
    order_by: 'name asc',
    limit_page_length: ITEM_LIST_LIMIT,
  }

  const params = q
    ? {
        ...base,
        or_filters: JSON.stringify([
          ['name', 'like', `%${q}%`],
          ['item_name', 'like', `%${q}%`],
        ]),
      }
    : base

  const rows = await callFrappeMethod<ItemRow[] | null>('frappe.client.get_list', params)
  const list = rows || []

  // 总数只在真的需要「被截断了吗」时才算，省一次往返
  let total = list.length
  if (list.length >= ITEM_LIST_LIMIT) {
    total = await countItems(q)
  }

  return { rows: list, total, truncated: total > list.length }
}

async function countItems(q: string): Promise<number> {
  const base = { doctype: 'Item' }
  const params = q
    ? {
        ...base,
        or_filters: JSON.stringify([
          ['name', 'like', `%${q}%`],
          ['item_name', 'like', `%${q}%`],
        ]),
      }
    : base
  try {
    const n = await callFrappeMethod<number>('frappe.client.get_count', params)
    return Number(n) || 0
  } catch {
    return 0
  }
}

export async function getItem(itemCode: string): Promise<ItemRow | null> {
  const code = itemCode.trim()
  if (!code) return null
  try {
    const doc = await callFrappeMethod<ItemRow | null>('frappe.client.get', {
      doctype: 'Item',
      name: code,
    })
    return doc && doc.name ? doc : null
  } catch {
    return null
  }
}

/** 物料上「本页认定为缺口」的字段 —— 只列入库流程真的会补的那几个，不泛化 */
export function itemMasterGaps(item: ItemRow): string[] {
  const gaps: string[] = []
  if (!String(item.hbos_storage_condition || '').trim()) gaps.push('储存条件')
  if (!String(item.hbos_workshop || '').trim()) gaps.push('生产车间')
  if (!String(item.hbos_shelf_life_type || '').trim()) gaps.push('效期类型')
  return gaps
}

// ---------------------------------------------------------------------------
// 货位
// ---------------------------------------------------------------------------

export interface WarehouseRow {
  name: string
  warehouse_name?: string
  parent_warehouse?: string | null
  is_group?: number
  lft?: number
  rgt?: number
  company?: string
  disabled?: number
}

export interface WarehouseTreeNode extends WarehouseRow {
  depth: number
  children: WarehouseTreeNode[]
  /** 供界面显示 —— 分组节点不能存货（见 api.py 的既有规则） */
  isGroup: boolean
}

export interface WarehouseSnapshot {
  /** 全部可见货位（含分组），已按 lft 排序 */
  all: WarehouseRow[]
  /** 树根（父节点不可见或没有父节点的视为根） */
  tree: WarehouseTreeNode[]
  byName: Map<string, WarehouseRow>
  leafCount: number
  groupCount: number
}

/**
 * 取**全部可见货位**并就地建树。
 *
 * 为什么一次取全（而不是像 ERPNext Desk 那样懒加载 `get_children`）：
 *
 * 1. **分组节点的下级汇总是需求**。`get_children` 只给直接子节点，要算
 *    「这个库位下共有多少物料」就得递归 N 次；而全量在手时用 `lft`/`rgt`
 *    一次筛出整棵子树即可。
 * 2. **面包屑链路**同理：有全量就能一路向上找父节点，不必逐级请求。
 * 3. 实测当前 224 个节点、7 个字段，响应体很小；且这是「查主数据」不是高频操作。
 *
 * `frappe.client.get_list` 会按会话过滤——权限受限时可能看不到某节点的父级。
 * 那种情况下该节点**当作根**处理（否则整棵子树会凭空消失）。
 */
export async function getWarehouseSnapshot(): Promise<WarehouseSnapshot> {
  const rows =
    (await callFrappeMethod<WarehouseRow[] | null>('frappe.client.get_list', {
      doctype: 'Warehouse',
      fields: JSON.stringify([
        'name',
        'warehouse_name',
        'parent_warehouse',
        'is_group',
        'lft',
        'rgt',
        'company',
        'disabled',
      ]),
      order_by: 'lft asc',
      limit_page_length: 0,
    })) || []

  const byName = new Map<string, WarehouseRow>()
  for (const row of rows) if (row?.name) byName.set(row.name, row)

  const nodes = new Map<string, WarehouseTreeNode>()
  for (const row of rows) {
    if (!row?.name) continue
    nodes.set(row.name, {
      ...row,
      depth: 0,
      children: [],
      isGroup: Number(row.is_group) === 1,
    })
  }

  const tree: WarehouseTreeNode[] = []
  for (const node of nodes.values()) {
    const parentName = node.parent_warehouse || ''
    const parent = parentName ? nodes.get(parentName) : undefined
    if (parent) parent.children.push(node)
    // 父级不可见（权限过滤）或本就没有父级 → 当根，别让子树消失
    else tree.push(node)
  }

  assignDepth(tree, 0)

  return {
    all: rows,
    tree,
    byName,
    leafCount: rows.filter((r) => Number(r.is_group) !== 1).length,
    groupCount: rows.filter((r) => Number(r.is_group) === 1).length,
  }
}

function assignDepth(nodes: WarehouseTreeNode[], depth: number) {
  for (const node of nodes) {
    node.depth = depth
    assignDepth(node.children, depth + 1)
  }
}

/**
 * 一个货位**能不能被选来存货**。
 *
 * 两条都要满足，缺一不可：
 *
 * 1. **不是分组节点**。分组（`is_group`）只是层级里的目录，没有货架，
 *    选了它单据会被服务端拒（本 App `api.py` 的既有规则）。
 * 2. **没有停用**。ERPNext 对停用货位是**硬拦**的——
 *    `erpnext/stock/utils.py` 的 `validate_disabled_warehouse()` 直接
 *    `frappe.throw("Disabled Warehouse ... cannot be used for this transaction.")`。
 *    所以停用的货位留在下拉里，用户选中就必然提交失败。
 *
 * **这条规则必须只有一份**。此前它写在三个页面里，三份各不相同：
 * `EntryView` / `ReconcileView` 只过滤了分组（漏了停用），
 * `PickView` **两条都没过滤**（连分组都能选，只加了个「（库位）」后缀）。
 * 2026-09-28 实测：ERPNext 建公司时自带的 `Stores - HB` 等四个占位仓
 * 被停用后，仍然出现在入库页的货位下拉最前面。
 */
export function isSelectableWarehouse(row: WarehouseRow): boolean {
  return Number(row.is_group) !== 1 && Number(row.disabled) !== 1
}

/** 可选货位（非分组 + 未停用），保持 snapshot 的 `lft` 顺序 */
export function selectableWarehouses(snapshot: WarehouseSnapshot): WarehouseRow[] {
  return snapshot.all.filter(isSelectableWarehouse)
}

/**
 * 分组节点的**整棵子树**（含自身）。
 *
 * 用 `lft` / `rgt` 判断包含关系，与报表 `_warehouse_scope` 同一套口径——
 * 别在两处各写一种「谁是下级」的算法。
 */
export function subtreeOf(snapshot: WarehouseSnapshot, rootName: string): WarehouseRow[] {
  const root = snapshot.byName.get(rootName)
  if (!root) return []
  const lft = Number(root.lft)
  const rgt = Number(root.rgt)
  if (!Number.isFinite(lft) || !Number.isFinite(rgt)) {
    return [root]
  }
  return snapshot.all.filter((row) => {
    const l = Number(row.lft)
    const r = Number(row.rgt)
    return Number.isFinite(l) && Number.isFinite(r) && l >= lft && r <= rgt
  })
}

/** 从根到该货位的链路，用于面包屑 */
export function warehouseChain(snapshot: WarehouseSnapshot, name: string): WarehouseRow[] {
  const chain: WarehouseRow[] = []
  const seen = new Set<string>()
  let current = snapshot.byName.get(name)
  while (current && !seen.has(current.name)) {
    seen.add(current.name)
    chain.unshift(current)
    const parentName = current.parent_warehouse || ''
    current = parentName ? snapshot.byName.get(parentName) : undefined
  }
  return chain
}

export interface StockRow {
  warehouse: string
  warehouseLabel: string
  itemCode: string
  itemName: string
  batchNo: string
  qty: number
  uom: string
}

/**
 * 指定货位（或其整棵子树）的当前库存。
 *
 * ## 为什么走报表，而不是直接查 Bin
 *
 * **`Bin` 上没有 `batch_no` 字段**。ERPNext v16 起，批次级库存不再挂在 `Bin` 上，
 * 而在 `Serial and Batch Entry`。拿 `Bin` 按 `batch_no` 过滤会得到
 * `DataError: 查询过滤条件字段无效…batch_no`（实测 417）。
 *
 * 本 App 的「货位明细表」报表已经用对了数据源（`Serial and Batch Entry` join
 * `Serial and Batch Bundle`），而且它的 `_warehouse_scope` **已经**按 `lft/rgt`
 * 展开整棵子树——正是这里要的行为。所以直接复用，不另写一套 SQL：
 * **同一个问题不要有两个算法**（`subtreeOf` 那份客户端计算因此也不再需要）。
 *
 * 传 `include_children: 1` 对叶子节点同样正确：树的 lft/rgt 区间退化成它自己。
 */
export async function getWarehouseStock(warehouseName: string): Promise<StockRow[]> {
  if (!warehouseName) return []

  const result = await runReport('货位明细表', {
    warehouse: warehouseName,
    include_children: 1,
  })

  return result.rows.map((row) => {
    const warehouse = String(row.warehouse || '')
    return {
      warehouse,
      warehouseLabel: warehouse.split(' - ')[0] || '',
      itemCode: String(row.item_code || ''),
      itemName: String(row.item_name || ''),
      batchNo: String(row.batch_no || ''),
      qty: Number(row.qty ?? 0),
      uom: String(row.uom || ''),
    }
  })
}

/**
 * 货位二维码 PDF 的打印地址。
 *
 * **必须是 Frappe 源的绝对地址**：新开页签不会带上 Portal 源下的 cookie，
 * 相对路径会打到 Vite 上且没有会话。`download_pdf` 内部按会话校验读权限
 * （实测访客返回 403）。
 */
export function warehouseQrUrl(warehouseName: string): string {
  const params = new URLSearchParams({
    doctype: 'Warehouse',
    name: warehouseName,
    format: 'HBOS 货位二维码',
  })
  return frappeAssetUrl(`/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`)
}
