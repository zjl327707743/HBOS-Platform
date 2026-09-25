import { callFrappeMethod, frappeAssetUrl, postFrappeMethod } from '@/services/frappeClient'

/**
 * 仓储库存 —— 单据读写（草稿复核页 + 批次页）。
 *
 * 后端 Authority：ERPNext 的 `Stock Entry` / `Batch`，以及本 App 的
 * `doc_gen.regenerate_for_batch`。本文件只做「把 ERPNext 的 whitelisted 方法
 * 包成类型化函数」，**不复制任何业务规则** —— 放行门禁在 `release_gate.py`、
 * 卡片生成在 `doc_gen.py`、权限在各自的 `check_permission` 里。
 *
 * 刻意**只服务「拍照识别建的草稿」**（`Stock Entry.hbos_intake_batch` 非空）。
 * 通用 Stock Entry 表单前端化是另一轮的事，本文件不承担。
 */

/** 放行状态取值，与 `setup.py` 里 Select 的 options 一致 */
export type ReleaseStatus = '待检' | '已放行' | '不放行'

const RELEASE_TONES: Record<ReleaseStatus, 'pending' | 'released' | 'blocked'> = {
  待检: 'pending',
  已放行: 'released',
  不放行: 'blocked',
}

export function releaseTone(status?: string | null): 'pending' | 'released' | 'blocked' | 'neutral' {
  if (!status) return 'neutral'
  return RELEASE_TONES[status as ReleaseStatus] ?? 'neutral'
}

// ---------------------------------------------------------------------------
// 通用读取
// ---------------------------------------------------------------------------

interface FileDoc {
  name: string
  file_name: string
  file_url: string
  creation?: string
  file_size?: number
}

/**
 * 取挂在某单据上的附件。
 *
 * **权限**：`frappe.client.get_list` 会按会话用户过滤，看不到的不会返回——
 * 所以这里不需要也不应该自己判权限。
 */
export async function getAttachments(
  doctype: string,
  name: string,
): Promise<Array<{ name: string; fileName: string; url: string; createdAt?: string; size?: number }>> {
  const rows = await callFrappeMethod<FileDoc[] | null>('frappe.client.get_list', {
    doctype: 'File',
    filters: JSON.stringify({ attached_to_doctype: doctype, attached_to_name: name }),
    fields: JSON.stringify(['name', 'file_name', 'file_url', 'creation', 'file_size']),
    order_by: 'creation desc',
    limit_page_length: 0,
  })

  return (rows || []).map((row) => ({
    name: row.name,
    fileName: row.file_name,
    // 私有文件不能被 Vite 代理，必须拼 Frappe 源地址（见 frappeAssetUrl 的注释）
    url: frappeAssetUrl(row.file_url),
    createdAt: row.creation,
    size: row.file_size,
  }))
}

async function getItemName(itemCode: string): Promise<string> {
  if (!itemCode) return ''
  try {
    const row = await callFrappeMethod<{ item_name?: string } | null>('frappe.client.get_value', {
      doctype: 'Item',
      filters: JSON.stringify({ name: itemCode }),
      fieldname: JSON.stringify(['item_name']),
    })
    return String(row?.item_name || '')
  } catch {
    return ''
  }
}

/** 货位名是 `16-03-211 - HB` 这种，界面只显示短码，与货位卡 / 扫码页口径一致 */
export function warehouseShortLabel(name?: string | null): string {
  return String(name || '').split(' - ')[0] || ''
}

// ---------------------------------------------------------------------------
// 草稿（Stock Entry）
// ---------------------------------------------------------------------------

export interface DraftItem {
  itemCode: string
  itemName: string
  qty: number
  uom: string
  batchNo: string
  warehouse: string
}

export interface IntakeDraft {
  name: string
  docstatus: number
  purpose: string
  batch: string
  item: DraftItem
  remarks?: string
  isIntakeDraft: boolean
}

interface RawStockEntry {
  name: string
  docstatus: number
  purpose?: string
  hbos_intake_batch?: string
  to_warehouse?: string
  remarks?: string
  items?: Array<{
    item_code?: string
    qty?: number
    uom?: string
    stock_uom?: string
    batch_no?: string
    t_warehouse?: string
  }>
}

export async function getIntakeDraft(name: string): Promise<IntakeDraft> {
  const doc = await callFrappeMethod<RawStockEntry | null>('frappe.client.get', {
    doctype: 'Stock Entry',
    name,
  })
  if (!doc || !doc.name) throw new Error('找不到这张草稿。')

  // 首行即全部：拍照识别建的草稿固定单物料（见 api.create_intake_draft）
  const row = (doc.items || [])[0] || {}
  const itemCode = String(row.item_code || '')
  const itemName = await getItemName(itemCode)

  return {
    name: doc.name,
    docstatus: Number(doc.docstatus ?? 0),
    purpose: String(doc.purpose || ''),
    batch: String(doc.hbos_intake_batch || ''),
    remarks: doc.remarks,
    // 判据与后端一致：hbos_intake_batch 非空即代表来源是拍照识别
    isIntakeDraft: Boolean(doc.hbos_intake_batch),
    item: {
      itemCode,
      itemName,
      qty: Number(row.qty ?? 0),
      uom: String(row.uom || row.stock_uom || ''),
      batchNo: String(row.batch_no || doc.hbos_intake_batch || ''),
      warehouse: String(row.t_warehouse || doc.to_warehouse || ''),
    },
  }
}

/**
 * 提交草稿。
 *
 * 只传 `{doctype, name}` —— `frappe.client.submit` 内部走
 * `frappe.get_doc(dict)`，带 name 时**按名字重新加载**，不会用前端手里的副本
 * 覆盖服务端。所以不存在「拿着过期数据提交」的风险。
 *
 * 提交会**立刻入账**，并由 `doc_gen.generate_for_stock_entry`（挂在
 * `Stock Entry.on_submit`）自动生成货位卡 / 待检证。放行门禁
 * (`release_gate.py`) **不拦 Material Receipt**——待检物料本就该能入库。
 */
export async function submitIntakeDraft(name: string): Promise<void> {
  await postFrappeMethod('frappe.client.submit', {
    doc: JSON.stringify({ doctype: 'Stock Entry', name }),
  })
}

/**
 * 放弃草稿（删除）。
 *
 * `frappe.client.delete` → `check_permission_and_not_submitted`：走
 * `check_permission("delete")`，且**已提交的单据会被拒**。所以这个方法
 * 天然只能删草稿，不需要前端另设防线。
 *
 * **不会连带删除批次**：`_ensure_batch` 是「确保存在、已存在只补空」，
 * 批次可能在这张草稿之前就有了。所以界面上的确认文案必须说清这点。
 */
export async function discardIntakeDraft(name: string): Promise<void> {
  await postFrappeMethod('frappe.client.delete', {
    doctype: 'Stock Entry',
    name,
  })
}

// ---------------------------------------------------------------------------
// 批次（Batch）
// ---------------------------------------------------------------------------

export interface BatchPackaging {
  containerType: string
  unitWeight: number
  count: number
}

export interface BatchDetail {
  name: string
  batchId: string
  itemCode: string
  itemName: string
  manufacturingDate?: string | null
  expiryDate?: string | null

  /** 自产 / 外购 —— 决定「本批信息」三项是否必需 */
  sourceType?: string | null

  releaseStatus?: string | null
  releaseDate?: string | null
  certificateNo?: string | null
  limsReference?: string | null
  releaseSource?: string | null

  supplierName?: string | null
  manufacturer?: string | null
  supplierBatchNo?: string | null
  storageCondition?: string | null
  workshop?: string | null
  shelfLifeType?: string | null

  packaging: BatchPackaging[]
  labelText: string
}

interface RawBatch {
  name: string
  batch_id?: string
  item?: string
  item_name?: string
  manufacturing_date?: string | null
  expiry_date?: string | null
  hbos_source_type?: string | null
  hbos_release_status?: string | null
  hbos_release_date?: string | null
  hbos_certificate_no?: string | null
  hbos_lims_reference?: string | null
  hbos_release_source?: string | null
  hbos_supplier_name?: string | null
  hbos_manufacturer?: string | null
  hbos_supplier_batch_no?: string | null
  hbos_storage_condition?: string | null
  hbos_workshop?: string | null
  hbos_shelf_life_type?: string | null
  hbos_label_text?: string | null
  hbos_packaging?: Array<{
    container_type?: string
    unit_weight?: number
    count?: number
  }>
}

export async function getBatch(name: string): Promise<BatchDetail> {
  const doc = await callFrappeMethod<RawBatch | null>('frappe.client.get', {
    doctype: 'Batch',
    name,
  })
  if (!doc || !doc.name) throw new Error('找不到这个批次。')

  const itemCode = String(doc.item || '')
  // Batch 上通常已带 item_name；没有才回查主数据
  const itemName = String(doc.item_name || '') || (await getItemName(itemCode))

  return {
    name: doc.name,
    batchId: String(doc.batch_id || doc.name),
    itemCode,
    itemName,
    manufacturingDate: doc.manufacturing_date,
    expiryDate: doc.expiry_date,
    sourceType: doc.hbos_source_type,
    releaseStatus: doc.hbos_release_status,
    releaseDate: doc.hbos_release_date,
    certificateNo: doc.hbos_certificate_no,
    limsReference: doc.hbos_lims_reference,
    releaseSource: doc.hbos_release_source,
    supplierName: doc.hbos_supplier_name,
    manufacturer: doc.hbos_manufacturer,
    supplierBatchNo: doc.hbos_supplier_batch_no,
    storageCondition: doc.hbos_storage_condition,
    workshop: doc.hbos_workshop,
    shelfLifeType: doc.hbos_shelf_life_type,
    packaging: (doc.hbos_packaging || []).map((row) => ({
      containerType: String(row.container_type || ''),
      unitWeight: Number(row.unit_weight ?? 0),
      count: Number(row.count ?? 0),
    })),
    labelText: String(doc.hbos_label_text || ''),
  }
}

export interface BatchStockRow {
  warehouse: string
  warehouseLabel: string
  actualQty: number
}

/** 该批次当前在哪些货位、各有多少——来自 ERPNext 的 `Bin` */
export async function getBatchStock(batchName: string): Promise<BatchStockRow[]> {
  const rows = await callFrappeMethod<
    Array<{ warehouse?: string; actual_qty?: number }> | null
  >('frappe.client.get_list', {
    doctype: 'Bin',
    filters: JSON.stringify({ batch_no: batchName }),
    fields: JSON.stringify(['warehouse', 'actual_qty']),
    order_by: 'warehouse asc',
    limit_page_length: 0,
  })

  return (rows || []).map((row) => ({
    warehouse: String(row.warehouse || ''),
    warehouseLabel: warehouseShortLabel(row.warehouse),
    actualQty: Number(row.actual_qty ?? 0),
  }))
}

/**
 * 该批次有没有**已提交**的拍照识别入库单。
 *
 * 用途：区分两种情况——「入库单还没提交」（所以卡片本就不该有）与
 * 「提交了但卡片没生成出来」。两者的下一步动作完全不同，不能共用一句文案。
 */
export async function hasSubmittedIntakeEntry(batchName: string): Promise<boolean> {
  if (!batchName) return false
  try {
    const rows = await callFrappeMethod<Array<{ name: string }> | null>(
      'frappe.client.get_list',
      {
        doctype: 'Stock Entry',
        filters: JSON.stringify({ hbos_intake_batch: batchName, docstatus: 1 }),
        fields: JSON.stringify(['name']),
        limit_page_length: 1,
      },
    )
    return Boolean(rows && rows.length)
  } catch {
    // 查不到就当作「不知道」，由调用方给中性文案——不猜
    return false
  }
}

/**
 * 重新生成货位卡 / 待检证。
 *
 * 为什么必须把这个能力搬到前端：`doc_gen.generate_for_stock_entry` 挂在
 * `on_submit` 上，而且**刻意吞掉异常**（生成 PDF 失败绝不能回滚入库），
 * 只写 Error Log。所以生成失败时操作员必须有地方重试，否则就卡死了。
 */
export async function regenerateBatchCards(batchName: string): Promise<{ file?: string }> {
  return postFrappeMethod<{ file?: string }>(
    'hb_inventory_app.hbos_inventory.doc_gen.regenerate_for_batch',
    { batch_name: batchName },
  )
}
