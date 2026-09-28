import {
  callFrappeMethod,
  cancelDocument,
  getDocument,
  postFrappeMethod,
  runDocMethod,
  saveDocument,
  submitDocument,
} from '@/services/frappeClient'

/**
 * 仓储库存 —— 拣货单（ERPNext `Pick List`）。**可写**。
 *
 * ## 拣货单不动账面
 *
 * 它只记录「该从哪个货位拣多少」，**库存不会因为它改变**。
 * 真正移货要另开一张移库单（或领用出库）。界面必须把这件事讲清楚，
 * 否则仓管会以为提交了货就出去了。
 *
 * 本文件不重写任何拣货规则：货位定位走 ERPNext 自己的 `set_item_locations`。
 */

/** 只暴露「内部移货」——ERPNext 还有 `Delivery` 与 `Material Transfer for Manufacture`，
 *  那是销售与生产流程的，仓库不用（与库存单据页同一个口径）。 */
export const PICK_PURPOSE = 'Material Transfer'

export interface PickListRow {
  name: string
  status: string
  docstatus: number
  /** Pick List 没有 `posting_date`，用标准字段 `creation` 当日期 */
  createdAt?: string
  parentWarehouse?: string | null
  modified?: string
}

export interface PickLocation {
  itemCode: string
  qty: number | null
  uom: string
  warehouse: string
  batchNo: string
  /** 该货位的可用量，服务端算的 */
  stockQty: number | null
  pickedQty: number | null
}

export interface PickListDoc {
  name: string
  docstatus: number
  status: string
  purpose: string
  parentWarehouse: string
  locations: PickLocation[]
}

interface RawPickList {
  name: string
  docstatus: number
  status?: string
  purpose?: string
  parent_warehouse?: string | null
  // 没有 posting_date —— 见 listPickLists 注释
  modified?: string
  locations?: Array<{
    item_code?: string
    qty?: number
    uom?: string
    warehouse?: string
    batch_no?: string
    stock_qty?: number
    picked_qty?: number
  }>
}

function mapLocation(row: NonNullable<RawPickList['locations']>[number]): PickLocation {
  return {
    itemCode: String(row.item_code || ''),
    qty: row.qty === undefined || row.qty === null ? null : Number(row.qty),
    uom: String(row.uom || ''),
    warehouse: String(row.warehouse || ''),
    batchNo: String(row.batch_no || ''),
    stockQty: row.stock_qty === undefined || row.stock_qty === null ? null : Number(row.stock_qty),
    pickedQty:
      row.picked_qty === undefined || row.picked_qty === null ? null : Number(row.picked_qty),
  }
}

function mapDoc(doc: RawPickList): PickListDoc {
  return {
    name: doc.name,
    docstatus: Number(doc.docstatus ?? 0),
    status: String(doc.status || ''),
    purpose: String(doc.purpose || ''),
    parentWarehouse: String(doc.parent_warehouse || ''),
    locations: (doc.locations || []).map(mapLocation),
  }
}

export async function getPickList(name: string): Promise<PickListDoc> {
  const doc = await getDocument<RawPickList>('Pick List', name)
  return mapDoc(doc)
}

/**
 * 最近拣货单。
 *
 * Pick List **没有任何 Date/Datetime 字段**（只有标准的 `creation` / `modified`），
 * 照 Stock Entry 写 `posting_date` 会 417 `DataError: 查询过滤条件字段无效…posting_date`，
 * 列表整页打不开。别因为兄弟单据有某个字段就假设它也有。
 */
export async function listPickLists(limit = 30): Promise<PickListRow[]> {
  const rows =
    (await callFrappeMethod<
      Array<{
        name: string
        status?: string
        docstatus?: number
        creation?: string
        parent_warehouse?: string | null
        modified?: string
      }> | null
    >('frappe.client.get_list', {
      doctype: 'Pick List',
      fields: JSON.stringify([
        'name',
        'status',
        'docstatus',
        'creation',
        'parent_warehouse',
        'modified',
      ]),
      order_by: 'docstatus asc, modified desc',
      limit_page_length: limit,
    })) || []

  return rows.map((r) => ({
    name: r.name,
    status: String(r.status || ''),
    docstatus: Number(r.docstatus ?? 0),
    createdAt: r.creation,
    parentWarehouse: r.parent_warehouse,
    modified: r.modified,
  }))
}

export interface PickPayload {
  parentWarehouse: string
  locations: PickLocation[]
}

/**
 * 转成提交给服务端的子表行。
 *
 * `pick_manually: 1` 是**必需的**：不设它时，ERPNext 的 `before_save` 会调用
 * `set_item_locations()`，把用户手填的货位**整个重算**掉。set 上它，
 * 手填的货位才留得住；要重算由用户显式点「定位货位」触发。
 *
 * ## 为什么还要显式带 `uom` 与 `stock_qty`（实测，两个都会出问题）
 *
 * ERPNext 的 Desk 表单会在选物料时把这两个也落库，服务端**不会**替你补：
 *
 * - **`uom`**：界面「单位」列读的就是它。不带 → 存进去是 NULL → 保存后重开，
 *   单位变空（用户明明看到过）。
 * - **`stock_qty`**：`set_item_locations` 用它（**不是 `qty`**）算「还剩多少要拣」——
 *   `get_items_with_location_and_quantity` 里
 *   `remaining_stock_qty = item_doc.stock_qty`（草稿分支），为 0 时 while 循环
 *   一次都不进。于是「定位货位」**把未拣的行全删掉、一行也不填**。
 *   实测：qty=4 的单据点一下就变成 0 行，货位静默丢失。
 *
 * 本页的 UOM 取自物料 `stock_uom`，换算系数为 1，故 `stock_qty === qty`。
 */
function toWireLocations(locations: PickLocation[]) {
  return locations
    .filter((row) => row.itemCode && (row.qty ?? 0) > 0)
    .map((row) => {
      const qty = Number(row.qty ?? 0)
      return {
        item_code: row.itemCode,
        qty,
        // 单位与 stock_qty 都要落库：前者是「单位」列，后者是「定位货位」的重算基准
        ...(row.uom ? { uom: row.uom } : {}),
        stock_qty: qty,
        ...(row.warehouse ? { warehouse: row.warehouse } : {}),
        ...(row.batchNo ? { batch_no: row.batchNo, use_serial_batch_fields: 1 } : {}),
      }
    })
}

export interface CreatedPick {
  name: string
  locations: PickLocation[]
}

export async function createPickList(payload: PickPayload): Promise<CreatedPick> {
  const doc = await postFrappeMethod<RawPickList>('frappe.client.insert', {
    doc: JSON.stringify({
      doctype: 'Pick List',
      purpose: PICK_PURPOSE,
      pick_manually: 1,
      parent_warehouse: payload.parentWarehouse || undefined,
      locations: toWireLocations(payload.locations),
    }),
  })
  return { name: String(doc?.name || ''), locations: (doc?.locations || []).map(mapLocation) }
}

export async function updatePickList(name: string, payload: PickPayload): Promise<PickListDoc> {
  await saveDocument('Pick List', name, {
    purpose: PICK_PURPOSE,
    pick_manually: 1,
    parent_warehouse: payload.parentWarehouse || undefined,
    locations: toWireLocations(payload.locations),
  })
  return getPickList(name)
}

/**
 * 「定位货位」——让 ERPNext 自己按库存、预留、批次规则去找货。
 *
 * **单据必须已保存过**：`set_item_locations` 是单据方法，它按 `dt` + `dn`
 * 去库里加载文档（与 `frappe.client.submit` 的 `get_doc(dict)` 语义相反）。
 * 新建时直接调用会失败——所以界面上的按钮在「还没保存」时是禁用的，
 * 并把「先保存再定位」说明摆在旁边。
 *
 * 它会**替换掉当前所有未拣的行**（这是 ERPNext 的定义），返回重算后的文档。
 */
export async function locatePickList(name: string): Promise<PickListDoc> {
  const result = await runDocMethod<{ docs?: RawPickList[] }>(
    'Pick List',
    name,
    'set_item_locations',
    { save: 1 },
  )
  const doc = result?.docs?.[0]
  if (!doc) {
    // 服务端没回文档时，回读一次，别让界面拿到空
    return getPickList(name)
  }
  return mapDoc(doc)
}

/**
 * 「定位」为什么什么都没找到。
 *
 * `set_item_locations` 的搜索范围来自 `parent_warehouse` 或 `work_order`——
 * **两个都没有时它无处可搜**，会把未拣的行清掉且一行也不填（实测）。
 *
 * 这与「范围内确实没货」是**两回事**，界面必须分开说：
 * 前者是操作没做全（去设范围），后者是事实（去入库）。
 */
export function explainEmptyLocate(parentWarehouse: string): string | null {
  if (parentWarehouse) return null
  return '还没选「查找范围」。不选范围，系统不知道去哪找——请先选一个库位或货位，再定位。'
}

export async function submitPickList(name: string): Promise<void> {
  await submitDocument('Pick List', name)
}

/**
 * 取消一张已提交的拣货单。
 *
 * **不动账面**——拣货单本身只是锁定「去哪几个货位拣多少」，不产生库存流水。
 * 取消的效果是解锁：解除对货位的锁定、把状态置为 `Cancelled`，之后可以重新建一张。
 * 已经把货挪走要靠**移库单**，那是另一张单据的事。
 */
export async function cancelPickList(name: string): Promise<void> {
  await cancelDocument('Pick List', name)
}

/** 放弃草稿。已提交的会被服务端拒——要先取消。 */
export async function discardPickList(name: string): Promise<void> {
  await postFrappeMethod('frappe.client.delete', { doctype: 'Pick List', name })
}

// ---------------------------------------------------------------------------
// 凑不凑得够
// ---------------------------------------------------------------------------

export interface PickShortage {
  itemCode: string
  required: number
  located: number
  gap: number
}

/**
 * 逐物料比较「要拣多少」与「定位到多少」。
 *
 * **定位会替换掉明细行**，所以「要拣数量」在调用前先记下来，事后拿它比对——
 * 否则用户填的数字会被 ERPNext 算出的行冲掉，就无从判断够不够了。
 */
export function findShortages(
  required: Record<string, number>,
  locations: PickLocation[],
): PickShortage[] {
  const located: Record<string, number> = {}
  for (const row of locations) {
    if (!row.itemCode) continue
    located[row.itemCode] = (located[row.itemCode] || 0) + Number(row.qty || 0)
  }

  return Object.entries(required)
    .map(([itemCode, need]) => {
      const got = Number((located[itemCode] || 0).toFixed(3))
      const gap = Number((need - got).toFixed(3))
      return { itemCode, required: need, located: got, gap }
    })
    .filter((row) => row.gap > 0)
}
