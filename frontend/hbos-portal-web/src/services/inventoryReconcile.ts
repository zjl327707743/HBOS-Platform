import {
  callFrappeMethod,
  getDocument,
  postFrappeMethod,
  saveDocument,
  submitDocument,
} from '@/services/frappeClient'

/**
 * 仓储库存 —— 库存对账（ERPNext `Stock Reconciliation`）。**可写、会调账**。
 *
 * ## 它改的是账面，也是财务口径
 *
 * 提交后按差额调整库存，并**记入差异科目**。不是「改个显示值」。
 * 界面必须把这件事说清楚。
 *
 * 本文件不重写任何估值 / 调账规则：账面数走 ERPNext 的
 * `get_stock_balance_for`，差异计算与调账全在服务端。
 */

export const RECONCILE_PURPOSE = 'Stock Reconciliation'

export interface ReconcileRowMeta {
  name: string
  docstatus: number
  purpose: string
  postingDate: string
  postingTime: string
  setWarehouse: string
  items: ReconcileItem[]
}

export interface ReconcileItem {
  itemCode: string
  batchNo: string
  warehouse: string
  /** 单位取自物料主数据，只读 */
  uom: string
  /** 实盘数 —— 用户填的那个 */
  qty: number | null
  /** 账面数 —— 服务端查出来的 */
  currentQty: number | null
}

interface RawReconcile {
  name: string
  docstatus: number
  purpose?: string
  posting_date?: string
  posting_time?: string
  set_warehouse?: string | null
  modified?: string
  items?: Array<{
    item_code?: string
    batch_no?: string
    warehouse?: string
    stock_uom?: string
    qty?: number
    current_qty?: number
  }>
}

function mapItem(row: NonNullable<RawReconcile['items']>[number]): ReconcileItem {
  const num = (v: unknown) => (v === undefined || v === null ? null : Number(v))
  return {
    itemCode: String(row.item_code || ''),
    batchNo: String(row.batch_no || ''),
    warehouse: String(row.warehouse || ''),
    uom: String(row.stock_uom || ''),
    qty: num(row.qty),
    currentQty: num(row.current_qty),
  }
}

function mapDoc(doc: RawReconcile): ReconcileRowMeta {
  return {
    name: doc.name,
    docstatus: Number(doc.docstatus ?? 0),
    purpose: String(doc.purpose || ''),
    postingDate: String(doc.posting_date || ''),
    postingTime: String(doc.posting_time || ''),
    setWarehouse: String(doc.set_warehouse || ''),
    items: (doc.items || []).map(mapItem),
  }
}

export async function getReconciliation(name: string): Promise<ReconcileRowMeta> {
  const doc = await getDocument<RawReconcile>(
    'Stock Reconciliation',
    name,
  )
  return mapDoc(doc)
}

export interface ReconcileListRow {
  name: string
  docstatus: number
  postingDate?: string
  modified?: string
}

export async function listReconciliations(limit = 30): Promise<ReconcileListRow[]> {
  const rows =
    (await callFrappeMethod<
      Array<{ name: string; docstatus?: number; posting_date?: string; modified?: string }> | null
    >('frappe.client.get_list', {
      doctype: 'Stock Reconciliation',
      fields: JSON.stringify(['name', 'docstatus', 'posting_date', 'modified']),
      order_by: 'docstatus asc, modified desc',
      limit_page_length: limit,
    })) || []

  return rows.map((r) => ({
    name: r.name,
    docstatus: Number(r.docstatus ?? 0),
    postingDate: r.posting_date,
    modified: r.modified,
  }))
}

/**
 * 查某个「物料 + 货位 + 批次」的**账面数**。
 *
 * **`row` 参数不能省**：不传它服务端会 500
 * （`AttributeError: 'NoneType' object has no attribute 'use_serial_batch_fields'`，实测）。
 * 形状是 `{use_serial_batch_fields: 1, batch_no: '...'}`。
 *
 * 返回 `null` 表示查不到（物料不存在等），由界面显示成「—」而不是 0——
 * **「不知道」与「是零」必须分得开**。
 */
export async function fetchCurrentQty(
  itemCode: string,
  warehouse: string,
  postingDate: string,
  postingTime: string,
  batchNo: string,
): Promise<number | null> {
  if (!itemCode || !warehouse) return null
  try {
    const res = await callFrappeMethod<{ qty?: number } | null>(
      'erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for',
      {
        item_code: itemCode,
        warehouse,
        posting_date: postingDate,
        posting_time: postingTime || '12:00:00',
        ...(batchNo ? { batch_no: batchNo } : {}),
        // 必须带：不带会 500（见函数注释）
        row: JSON.stringify({
          use_serial_batch_fields: batchNo ? 1 : 0,
          batch_no: batchNo || undefined,
        }),
      },
    )
    const qty = res?.qty
    return qty === undefined || qty === null ? null : Number(qty)
  } catch {
    return null
  }
}

export interface ReconcilePayload {
  postingDate: string
  postingTime: string
  setWarehouse: string
  items: ReconcileItem[]
}

/**
 * 转成提交给服务端的明细行。
 *
 * **批次必须带上**：实测不带时服务端报
 * `ValidationError: 行号1：请为物料<strong>…</strong>添加序列号和批次包`。
 */
function toWireItems(items: ReconcileItem[]) {
  return items
    .filter((row) => row.itemCode && row.warehouse && row.qty !== null)
    .map((row) => ({
      item_code: row.itemCode,
      warehouse: row.warehouse,
      qty: Number(row.qty ?? 0),
      ...(row.batchNo ? { batch_no: row.batchNo, use_serial_batch_fields: 1 } : {}),
    }))
}

export async function createReconciliation(
  payload: ReconcilePayload,
): Promise<ReconcileRowMeta> {
  const doc = await postFrappeMethod<RawReconcile>('frappe.client.insert', {
    doc: JSON.stringify({
      doctype: 'Stock Reconciliation',
      purpose: RECONCILE_PURPOSE,
      posting_date: payload.postingDate,
      posting_time: payload.postingTime,
      set_posting_time: 1,
      set_warehouse: payload.setWarehouse || undefined,
      items: toWireItems(payload.items),
    }),
  })
  return mapDoc(doc)
}

export async function updateReconciliation(
  name: string,
  payload: ReconcilePayload,
): Promise<ReconcileRowMeta> {
  await saveDocument('Stock Reconciliation', name, {
    purpose: RECONCILE_PURPOSE,
    posting_date: payload.postingDate,
    posting_time: payload.postingTime,
    set_posting_time: 1,
    set_warehouse: payload.setWarehouse || undefined,
    items: toWireItems(payload.items),
  })
  return getReconciliation(name)
}

export async function submitReconciliation(name: string): Promise<void> {
  await submitDocument('Stock Reconciliation', name)
}

export async function discardReconciliation(name: string): Promise<void> {
  await postFrappeMethod('frappe.client.delete', {
    doctype: 'Stock Reconciliation',
    name,
  })
}

// ---------------------------------------------------------------------------
// 差异
// ---------------------------------------------------------------------------

export interface VarianceSummary {
  /** 盘盈行数（实盘 > 账面） */
  surplus: number
  /** 盘亏行数（实盘 < 账面） */
  shortage: number
  /** 对得上的行数 */
  matched: number
  /** 还没查到账面数的行数 —— 单独计，不能混进「对上」 */
  unknown: number
}

export function varianceOf(row: ReconcileItem): number | null {
  if (row.qty === null || row.currentQty === null) return null
  return Number((row.qty - row.currentQty).toFixed(3))
}

export function summarizeVariance(items: ReconcileItem[]): VarianceSummary {
  const out: VarianceSummary = { surplus: 0, shortage: 0, matched: 0, unknown: 0 }
  for (const row of items) {
    if (!row.itemCode) continue
    const diff = varianceOf(row)
    if (diff === null) out.unknown += 1
    else if (diff > 0) out.surplus += 1
    else if (diff < 0) out.shortage += 1
    else out.matched += 1
  }
  return out
}

/** 盘盈合计 / 盘亏合计（**分开算**，不能相加——方向相反，加一起没有意义） */
export function varianceTotals(items: ReconcileItem[]): { gain: number; loss: number } {
  let gain = 0
  let loss = 0
  for (const row of items) {
    const diff = varianceOf(row)
    if (diff === null) continue
    if (diff > 0) gain += diff
    else if (diff < 0) loss += Math.abs(diff)
  }
  return { gain: Number(gain.toFixed(3)), loss: Number(loss.toFixed(3)) }
}
