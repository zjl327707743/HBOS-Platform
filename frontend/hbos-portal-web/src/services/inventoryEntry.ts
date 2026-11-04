import {
  callFrappeMethod,
  cancelDocument,
  postFrappeMethod,
  saveDocument,
  submitDocument,
} from '@/services/frappeClient'

/**
 * 仓储库存 —— 库存单据（ERPNext `Stock Entry`）。**本页可以写**。
 *
 * 与 `inventoryDocs.ts` 的分工：
 * - `inventoryDocs.ts` 只服务「拍照识别建的草稿」（`hbos_intake_batch` 非空），只读 + 提交；
 * - 本文件服务**仓库自己开的通用单据**（入库 / 领用出库 / 移库），可建可改。
 *
 * 本文件不复制任何业务规则：放行门禁在 `release_gate.py`，默认值由 ERPNext 带。
 */

// ---------------------------------------------------------------------------
// 单据类型
// ---------------------------------------------------------------------------

export interface EntryType {
  /** 前端自己的键，进 URL 与按钮状态 */
  key: string
  label: string
  /** ERPNext `Stock Entry Type` 的 name —— 提交给服务端的就是它 */
  erpType: string
  icon: string
  /** 那一句人话说明「这单在干什么」 */
  hint: string
  /** 是否需要源货位 / 目标货位 */
  needsSource: boolean
  needsTarget: boolean
  /** 是否要做出库放行预检 */
  needsReleaseCheck: boolean
}

/**
 * 只暴露仓库日常用的三种。
 *
 * ERPNext 的 `Stock Entry Type` 实际有 13 种（Manufacture / Repack /
 * Disassemble / Subcontracting 等），那些是生产与委外流程的，仓库不用。
 * 与方案 §5.4 的「其它字段明确不提供」同一个口径：**不给没人用的选项，
 * 比给一堆没人懂的选项干净**。
 *
 * 映射写死在前端是**刻意的**：中文标签是本前端自己的命名层（ERPNext 那边
 * 仍叫 `Material Receipt`），标准类型的名字不会变。若哪天要加类型，改这里。
 */
export const ENTRY_TYPES: EntryType[] = [
  {
    key: 'receipt',
    label: '物料入库',
    erpType: 'Material Receipt',
    icon: 'in',
    hint: '货物进入仓库。只需填目标货位。',
    needsSource: false,
    needsTarget: true,
    needsReleaseCheck: false,
  },
  {
    key: 'issue',
    label: '领用出库',
    erpType: 'Material Issue',
    icon: 'out',
    hint: '货物发出仓库。只需填源货位；<b>提交时会校验批次的 QA 放行手续</b>。',
    needsSource: true,
    needsTarget: false,
    needsReleaseCheck: true,
  },
  {
    key: 'transfer',
    label: '移库',
    erpType: 'Material Transfer',
    icon: 'swap',
    hint: '仓库内部换货位。源与目标都要填，数量不变。',
    needsSource: true,
    needsTarget: true,
    needsReleaseCheck: false,
  },
]

export function findEntryType(erpType?: string | null): EntryType | undefined {
  return ENTRY_TYPES.find((t) => t.erpType === erpType)
}

/**
 * 按前端自己的键（`receipt` / `issue` / `transfer`）找类型。
 *
 * 用于「侧边栏的下一级菜单 → 页面预选类型」：外部传进来的只有这个键
 * （`/hbos/inventory/entry?type=receipt`），拿不到 `erpType`。
 * 认不出来就返回 undefined，由调用方决定回落到什么——**不猜**。
 */
export function findEntryTypeByKey(key?: string | null): EntryType | undefined {
  return ENTRY_TYPES.find((t) => t.key === key)
}

// ---------------------------------------------------------------------------
// 单据读写
// ---------------------------------------------------------------------------

export interface EntryRow {
  name: string
  stockEntryType?: string
  purpose?: string
  docstatus: number
  postingDate?: string
  fromWarehouse?: string | null
  toWarehouse?: string | null
  modified?: string
}

interface RawEntry {
  name: string
  docstatus: number
  stock_entry_type?: string
  purpose?: string
  posting_date?: string
  from_warehouse?: string | null
  to_warehouse?: string | null
  remarks?: string
  modified?: string
  hbos_intake_batch?: string
  items?: RawEntryItem[]
}

interface RawEntryItem {
  name?: string
  item_code?: string
  qty?: number
  uom?: string
  stock_uom?: string
  batch_no?: string
  s_warehouse?: string
  t_warehouse?: string
}

export interface EntryItem {
  itemCode: string
  qty: number | null
  uom: string
  batchNo: string
  sourceWarehouse: string
  targetWarehouse: string
}

export interface StockEntryDraft {
  name: string
  docstatus: number
  stockEntryType: string
  purpose: string
  postingDate: string
  remarks: string
  items: EntryItem[]
  /** 拍照识别建的草稿 —— 本页不接管它（那有专门的复核页） */
  fromIntake: boolean
}

function mapItem(row: RawEntryItem): EntryItem {
  return {
    itemCode: String(row.item_code || ''),
    qty: row.qty === undefined || row.qty === null ? null : Number(row.qty),
    uom: String(row.uom || row.stock_uom || ''),
    batchNo: String(row.batch_no || ''),
    sourceWarehouse: String(row.s_warehouse || ''),
    targetWarehouse: String(row.t_warehouse || ''),
  }
}

export async function getStockEntry(name: string): Promise<StockEntryDraft> {
  const doc = await callFrappeMethod<RawEntry | null>('frappe.client.get', {
    doctype: 'Stock Entry',
    name,
  })
  if (!doc || !doc.name) throw new Error('找不到这张单据。')

  return {
    name: doc.name,
    docstatus: Number(doc.docstatus ?? 0),
    stockEntryType: String(doc.stock_entry_type || ''),
    purpose: String(doc.purpose || ''),
    postingDate: String(doc.posting_date || ''),
    remarks: String(doc.remarks || ''),
    items: (doc.items || []).map(mapItem),
    // 判据与后端一致：hbos_intake_batch 非空即来自拍照识别
    fromIntake: Boolean(doc.hbos_intake_batch),
  }
}

/** 最近单据列表。草稿排前面——那是还需要人处理的。 */
export async function listStockEntries(limit = 30): Promise<EntryRow[]> {
  const rows =
    (await callFrappeMethod<
      Array<{
        name: string
        stock_entry_type?: string
        purpose?: string
        docstatus?: number
        posting_date?: string
        from_warehouse?: string | null
        to_warehouse?: string | null
        modified?: string
      }> | null
    >('frappe.client.get_list', {
      doctype: 'Stock Entry',
      fields: JSON.stringify([
        'name',
        'stock_entry_type',
        'purpose',
        'docstatus',
        'posting_date',
        'from_warehouse',
        'to_warehouse',
        'modified',
      ]),
      // 草稿优先，其次按修改时间倒序
      order_by: 'docstatus asc, modified desc',
      limit_page_length: limit,
    })) || []

  return rows.map((r) => ({
    name: r.name,
    stockEntryType: r.stock_entry_type,
    purpose: r.purpose,
    docstatus: Number(r.docstatus ?? 0),
    postingDate: r.posting_date,
    fromWarehouse: r.from_warehouse,
    toWarehouse: r.to_warehouse,
    modified: r.modified,
  }))
}

export interface EntryPayload {
  stockEntryType: string
  postingDate: string
  remarks: string
  items: EntryItem[]
}

function toWireItems(items: EntryItem[], type: EntryType) {
  return items
    .filter((row) => row.itemCode && (row.qty ?? 0) > 0)
    .map((row) => ({
      item_code: row.itemCode,
      qty: Number(row.qty ?? 0),
      // 批号管理的物料必须有批次；空串会让 ERPNext 报「批号必填」
      ...(row.batchNo ? { batch_no: row.batchNo, use_serial_batch_fields: 1 } : {}),
      ...(type.needsSource && row.sourceWarehouse ? { s_warehouse: row.sourceWarehouse } : {}),
      ...(type.needsTarget && row.targetWarehouse ? { t_warehouse: row.targetWarehouse } : {}),
    }))
}

/**
 * 建一张新草稿。
 *
 * **`items` 是必填**（实测：空 items 的 insert 会以
 * `MandatoryError: [Stock Entry, MAT-STE-...]: items` 失败）。
 * 所以**不存在「空草稿」**——界面上必须先填至少一行才能保存。
 *
 * 实测服务端会自动带出 `company`（= hb）与 `purpose`（由 stock_entry_type 推导），
 * 命名系列也自动分配，**前端不需要传这些**。
 */
export async function createStockEntry(payload: EntryPayload): Promise<{ name: string }> {
  const type: EntryType = findEntryType(payload.stockEntryType) ?? ENTRY_TYPES[0]!
  const doc = await postFrappeMethod<{ name: string }>('frappe.client.insert', {
    doc: JSON.stringify({
      doctype: 'Stock Entry',
      stock_entry_type: payload.stockEntryType,
      posting_date: payload.postingDate,
      remarks: payload.remarks,
      items: toWireItems(payload.items, type),
    }),
  })
  return { name: String(doc?.name || '') }
}

/**
 * 改已有草稿。
 *
 * **在服务端的全文上覆盖要改的字段**（`saveDocument` 内部先 `get` 再 `save`）——
 * 不能只传这几个字段：`frappe.client.save` 走 `frappe.get_doc(dict)`，
 * 会把没传的字段清空。
 */
export async function updateStockEntry(
  name: string,
  payload: EntryPayload,
): Promise<void> {
  const type: EntryType = findEntryType(payload.stockEntryType) ?? ENTRY_TYPES[0]!
  await saveDocument('Stock Entry', name, {
    stock_entry_type: payload.stockEntryType,
    posting_date: payload.postingDate,
    remarks: payload.remarks,
    items: toWireItems(payload.items, type),
  })
}

/**
 * 提交。与 `inventoryDocs.submitIntakeDraft` 同一条路——
 * **先读全文再提交**（见 `frappeClient.submitDocument`）。
 *
 * 出库（`Material Issue`）会被 `release_gate.validate_release` 校验，
 * 缺放行手续时抛错；调用方要把这条错误原样呈现给用户。
 */
export async function submitStockEntry(name: string): Promise<void> {
  await submitDocument('Stock Entry', name)
}

/**
 * 取消一张**已提交**的库存单据（入库 / 领用出库 / 移库）。账面反向过账。
 *
 * 三种类型取消后各自会发生什么，界面必须说清（本文件不重复写文案，由调用方给）：
 * 入库把货从目标货位扣回、出库把货退回原货位、移库把货从目标挪回源货位。
 *
 * **没有 `before_cancel` 守卫**：`release_gate.validate_release` 只挂 `before_submit`，
 * 所以取消不受放行门禁阻拦。这是现状，不是遗漏——若将来要求「取消出库也要有放行
 * 手续」，那是新规则。
 */
export async function cancelStockEntry(name: string): Promise<void> {
  await cancelDocument('Stock Entry', name)
}

/** 放弃草稿。已提交的会被服务端拒（`check_permission_and_not_submitted`）。 */
export async function discardStockEntry(name: string): Promise<void> {
  await postFrappeMethod('frappe.client.delete', {
    doctype: 'Stock Entry',
    name,
  })
}

// ---------------------------------------------------------------------------
// 出库放行预检
// ---------------------------------------------------------------------------

export interface ReleaseCheck {
  batchNo: string
  ok: boolean
  /** 缺什么，逐项列出——与 `release_gate.py` 的六项要求一一对应 */
  missing: string[]
}

const RELEASE_FIELDS = [
  'hbos_release_status',
  'hbos_release_date',
  'hbos_certificate_no',
  'hbos_certificate_file',
  'hbos_lims_reference',
  'hbos_release_source',
]

/**
 * 对一批批号做放行手续预检。
 *
 * **判据必须与 `release_gate.py` 完全一致**——那边要求六项齐全：
 * 放行状态 = 已放行、放行日期、合格证编号、合格证附件、LIMS 引用、来源 = LIMS。
 * 这里少判一项，就会出现「预检说没事、提交被拦」；多判一项则相反。
 * 所以六项的文案与顺序都照抄那边，改动时**两边一起改**。
 *
 * 这是本页的主要价值：Desk 只在 `before_submit` 才说，这里在填写阶段就说。
 */
export async function checkReleaseForBatches(batchNos: string[]): Promise<ReleaseCheck[]> {
  const wanted = [...new Set(batchNos.map((b) => b.trim()).filter(Boolean))]
  if (!wanted.length) return []

  const rows =
    (await callFrappeMethod<
      Array<Record<string, unknown>> | null
    >('frappe.client.get_list', {
      doctype: 'Batch',
      filters: JSON.stringify({ name: ['in', wanted] }),
      fields: JSON.stringify(['name', ...RELEASE_FIELDS]),
      limit_page_length: 0,
    })) || []

  const byName = new Map(rows.map((r) => [String(r.name), r]))

  return wanted.map((batchNo) => {
    const row = byName.get(batchNo)
    if (!row) {
      // 批次都不存在——如实说，不当作「手续齐全」
      return { batchNo, ok: false, missing: ['批次不存在'] }
    }

    const missing: string[] = []
    if (String(row.hbos_release_status || '') !== '已放行') {
      missing.push(`放行状态为「${row.hbos_release_status || '未设置'}」`)
    }
    if (!String(row.hbos_release_date || '').trim()) missing.push('无放行日期')
    if (!String(row.hbos_certificate_no || '').trim()) missing.push('无合格证编号')
    if (!String(row.hbos_certificate_file || '').trim()) missing.push('无合格证附件')
    if (!String(row.hbos_lims_reference || '').trim()) missing.push('无 LIMS 放行引用')
    if (String(row.hbos_release_source || '').trim() !== 'LIMS') missing.push('放行来源不是 LIMS')

    return { batchNo, ok: missing.length === 0, missing }
  })
}
