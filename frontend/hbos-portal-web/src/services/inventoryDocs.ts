import {
  callFrappeMethod,
  cancelDocument,
  frappeAssetUrl,
  postFrappeMethod,
  submitDocument,
} from '@/services/frappeClient'
import { runReport } from '@/services/inventoryReports'

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

interface ItemMasterInfo {
  itemName: string
  storageCondition: string
  workshop: string
  shelfLifeType: string
}

const EMPTY_ITEM_MASTER: ItemMasterInfo = {
  itemName: '',
  storageCondition: '',
  workshop: '',
  shelfLifeType: '',
}

/**
 * 「储存条件 / 生产车间 / 效期类型」是**物料主数据**字段 —— `setup.py` 把它们
 * 建在 `Item` 上，**`Batch` 上没有这三个字段**。从批次上读只会得到 undefined，
 * 「本批信息」永远空白；而打印件（`print_utils` 也是从 `Item` 取）却有值 ——
 * 同一份事实两处不一致。
 *
 * 所以回查 `Item`。**一次取回四个字段**，不拆成四趟请求。
 */
async function getItemMasterInfo(itemCode: string): Promise<ItemMasterInfo> {
  if (!itemCode) return EMPTY_ITEM_MASTER
  try {
    const row = await callFrappeMethod<{
      item_name?: string
      hbos_storage_condition?: string | null
      hbos_workshop?: string | null
      hbos_shelf_life_type?: string | null
    } | null>('frappe.client.get_value', {
      doctype: 'Item',
      filters: JSON.stringify({ name: itemCode }),
      fieldname: JSON.stringify([
        'item_name',
        'hbos_storage_condition',
        'hbos_workshop',
        'hbos_shelf_life_type',
      ]),
    })
    return {
      itemName: String(row?.item_name || ''),
      storageCondition: String(row?.hbos_storage_condition || ''),
      workshop: String(row?.hbos_workshop || ''),
      shelfLifeType: String(row?.hbos_shelf_life_type || ''),
    }
  } catch {
    return EMPTY_ITEM_MASTER
  }
}

/** 货位名是 `16-03-211 - HB` 这种，界面只显示短码，与货位卡 / 扫码页口径一致 */
export function warehouseShortLabel(name?: string | null): string {
  return String(name || '').split(' - ')[0] || ''
}

/** 单据的三态。**不能只判「是不是 1」**：已取消（2）既不是草稿也不是已提交。 */
export type DocState = 'draft' | 'submitted' | 'cancelled'

/**
 * `docstatus` → 三态。
 *
 * 用 `docstatus === 1 ? '已提交' : '草稿'` 这种二元判断，会把**已取消**的单据
 * 显示成「草稿」、并当成可编辑——已取消的单据既不该显示成草稿，也不该能改
 * （改了服务端会拒，界面白让用户点）。
 */
export function docState(docstatus: number | null | undefined): DocState {
  const value = Number(docstatus ?? 0)
  if (value === 1) return 'submitted'
  if (value === 2) return 'cancelled'
  return 'draft'
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
  const master = await getItemMasterInfo(itemCode)

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
      itemName: master.itemName,
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
 * **先读全文再提交**（`submitDocument` 内部会做）——早先这里只传
 * `{doctype, name}`，那是**错的**：`frappe.client.submit` 走
 * `frappe.get_doc(dict)`，把传进去的 dict 当文档用，不会按名字去库里加载，
 * 于是既缺 `modified`（报 TimestampMismatch）又缺 `purpose`（报校验失败）。
 * 实测两种写法的差别见 `frappeClient.getDocument` 的注释。
 *
 * 提交会**立刻入账**，并由 `doc_gen.generate_for_stock_entry`（挂在
 * `Stock Entry.on_submit`）自动生成货位卡 / 待检证。放行门禁
 * (`release_gate.py`) **不拦 Material Receipt**——待检物料本就该能入库。
 */
export async function submitIntakeDraft(name: string): Promise<void> {
  await submitDocument('Stock Entry', name)
}

/**
 * 取消**已提交**的拍照识别入库单。
 *
 * 与入库单（`inventoryEntry.cancelStockEntry`）是同一条 `Stock Entry` 的取消路径，
 * 只是入口不同（这张是从拍照识别页提交的）。
 *
 * **取消不会删掉批次上已生成的货位卡 / 待检证**：`doc_gen.generate_for_stock_entry`
 * 挂在 `on_submit` 上，没有对应的 `on_cancel` 清理。所以界面必须提示用户
 * 「卡片还在，要重新生成去批次页」，而不是让它悄悄留着。
 */
export async function cancelIntakeDraft(name: string): Promise<void> {
  await cancelDocument('Stock Entry', name)
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
  // 储存条件 / 生产车间 / 效期类型**不在 Batch 上**，是 Item 的字段（见 getItemMasterInfo）
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
  const master = await getItemMasterInfo(itemCode)
  const itemName = String(doc.item_name || '') || master.itemName

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
    // 三项取自**物料主数据**，不是批次（见 getItemMasterInfo）
    storageCondition: master.storageCondition,
    workshop: master.workshop,
    shelfLifeType: master.shelfLifeType,
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
  itemCode: string
  itemName: string
  qty: number
  uom: string
}

/**
 * 该批次当前在哪些货位、各有多少。
 *
 * ## 为什么走报表，而不是直接查 Bin
 *
 * **`Bin` 上没有 `batch_no` 字段**。ERPNext v16 起批次级库存存在
 * `Serial and Batch Entry`，拿 `Bin` 按 `batch_no` 过滤会直接 417
 * （`DataError: 查询过滤条件字段无效…batch_no`）。
 *
 * 本 App 的「按批号查货位」报表已经用对了数据源，且与报表页口径天然一致，
 * 所以直接复用，**不另写一套批次库存 SQL**。
 *
 * 报表的 `batch_no` 是 **LIKE 模糊匹配**，所以这里要再按精确批号筛一遍——
 * 否则 `B2607` 会把 `B26071`、`B26072` 一起带出来。这一层筛在客户端做，
 * 因为模糊匹配是报表给使用者的便利，而这里要的是这一批的准确事实。
 *
 * **失败必须抛出去**，不能 `catch` 成空数组：那会让界面显示「当前没有库存」，
 * 而事实是「查不出来」——把故障读成空，与把空读成故障是同一类错误。
 */
export async function getBatchStock(batchName: string): Promise<BatchStockRow[]> {
  if (!batchName) return []

  const result = await runReport('按批号查货位', { batch_no: batchName })

  return result.rows
    .filter((row) => String(row.batch_no || '') === batchName)
    .map((row) => ({
      warehouse: String(row.warehouse || ''),
      warehouseLabel: warehouseShortLabel(String(row.warehouse || '')),
      itemCode: String(row.item_code || ''),
      itemName: String(row.item_name || ''),
      qty: Number(row.qty ?? 0),
      uom: String(row.uom || ''),
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

// ---------------------------------------------------------------------------
// 待检批次工作台（只读）
// ---------------------------------------------------------------------------

export interface PendingBatchRow {
  batchNo: string
  itemCode: string
  itemName: string
  expiryDate?: string | null
  sourceType?: string | null
  releaseStatus?: string | null

  /** 有库存时才由报表补得出；无库存时为 null —— **「没有」与「不知道」要分得开** */
  daysLeft: number | null
  urgency: string | null
  warehouse: string | null
  qty: number | null
  uom: string | null
}

export interface PendingBatchList {
  rows: PendingBatchRow[]
  /** `Batch` 里标「待检」的**全部**批次 —— 权威数字 */
  total: number
  /** 其中当前**有库存**的批次 —— 由效能报表补得出的那些 */
  withStock: number
}

/**
 * 待检批次工作台的数据。
 *
 * ## 为什么两个来源合起来用（本页最关键的一处设计）
 *
 * 两个数**对不上**，而且必须两个都取：
 *
 * | 来源 | 实测结果 | 含义 |
 * |---|---|---|
 * | `Batch.hbos_release_status = 待检` | **15** | 系统里标着待检的**全部**批次 |
 * | 「效期预警」报表 + `release_status=待检` | **4** | **当前有库存**的待检批次 |
 *
 * 差 11 个的原因是：效期预警 join `Serial and Batch Entry` 且要求
 * `sum(qty) != 0` —— **没有库存的批次它一条都不给**。
 *
 * 只取报表（4）会**静默丢掉 11 个**：页面写「4 批待检」而系统里是 15 批，
 * 用户对不上却查不出为什么。只取 Batch（15）又拿不到「剩余天数 / 紧急度」
 * 这些报表已经算好的字段。
 *
 * 所以：**以 `Batch` 为权威清单，用报表数据补充有库存的那些**，
 * 并把两个数字都显示出来。**差异是可见的，不是被藏掉的。**
 */
export async function getPendingReleaseBatches(): Promise<PendingBatchList> {
  const batches =
    (await callFrappeMethod<
      Array<{
        name: string
        item?: string
        item_name?: string
        expiry_date?: string | null
        hbos_source_type?: string | null
        hbos_release_status?: string | null
      }> | null
    >('frappe.client.get_list', {
      doctype: 'Batch',
      filters: JSON.stringify({ hbos_release_status: '待检' }),
      fields: JSON.stringify([
        'name',
        'item',
        'item_name',
        'expiry_date',
        'hbos_source_type',
        'hbos_release_status',
      ]),
      order_by: 'expiry_date asc, name asc',
      limit_page_length: 0,
    })) || []

  // 补充信息：报表只给「有库存」的，所以窗口开到 10 年，别让远期到期的被窗口切掉
  const enrichment = new Map<
    string,
    { daysLeft: number; urgency: string; warehouse: string; qty: number; uom: string }
  >()
  const report = await runReport('效期预警', {
    within_days: 3650,
    include_expired: 1,
    release_status: '待检',
  })
  for (const row of report.rows) {
    const batchNo = String(row.batch_no || '')
    if (!batchNo) continue
    enrichment.set(batchNo, {
      daysLeft: Number(row.days_left ?? 0),
      urgency: String(row.urgency || ''),
      warehouse: String(row.warehouse || ''),
      qty: Number(row.qty ?? 0),
      uom: String(row.uom || ''),
    })
  }

  const rows: PendingBatchRow[] = batches.map((b) => {
    const extra = enrichment.get(b.name)
    return {
      batchNo: b.name,
      itemCode: String(b.item || ''),
      itemName: String(b.item_name || ''),
      expiryDate: b.expiry_date,
      sourceType: b.hbos_source_type,
      releaseStatus: b.hbos_release_status,
      daysLeft: extra ? extra.daysLeft : null,
      urgency: extra ? extra.urgency : null,
      warehouse: extra ? extra.warehouse : null,
      qty: extra ? extra.qty : null,
      uom: extra ? extra.uom : null,
    }
  })

  // 有库存的排前面（那才是真要去处理的），同组内按剩余天数升序
  rows.sort((a, b) => {
    if ((a.qty !== null) !== (b.qty !== null)) return a.qty !== null ? -1 : 1
    return (a.daysLeft ?? Number.MAX_SAFE_INTEGER) - (b.daysLeft ?? Number.MAX_SAFE_INTEGER)
  })

  return { rows, total: rows.length, withStock: rows.filter((r) => r.qty !== null).length }
}

// ---------------------------------------------------------------------------
// 批次列表（选择器用）
// ---------------------------------------------------------------------------

export interface BatchListRow {
  name: string
  itemCode: string
  itemName: string
  expiryDate?: string | null
  sourceType?: string | null
  releaseStatus?: string | null
}

export interface BatchListResult {
  rows: BatchListRow[]
  total: number
}

export const BATCH_LIST_LIMIT = 200

/**
 * 搜批次。空关键词回最近的 N 个。
 *
 * 与物料页同一口径：代码与名称都能搜，用 `or_filters`。
 * 排序按 `modified desc`——刚建的批次最可能就是要找的那个
 * （批次的建立刚刚发生在入库时）。
 */
export async function searchBatches(keyword: string): Promise<BatchListResult> {
  const q = keyword.trim()
  const base: Record<string, unknown> = {
    doctype: 'Batch',
    fields: JSON.stringify([
      'name',
      'item',
      'item_name',
      'expiry_date',
      'hbos_source_type',
      'hbos_release_status',
    ]),
    order_by: 'modified desc',
    limit_page_length: BATCH_LIST_LIMIT,
  }

  const params = q
    ? {
        ...base,
        or_filters: JSON.stringify([
          ['name', 'like', `%${q}%`],
          ['item', 'like', `%${q}%`],
          ['item_name', 'like', `%${q}%`],
        ]),
      }
    : base

  const raw =
    (await callFrappeMethod<
      Array<{
        name: string
        item?: string
        item_name?: string
        expiry_date?: string | null
        hbos_source_type?: string | null
        hbos_release_status?: string | null
      }> | null
    >('frappe.client.get_list', params)) || []

  return {
    rows: raw.map((r) => ({
      name: r.name,
      itemCode: String(r.item || ''),
      itemName: String(r.item_name || ''),
      expiryDate: r.expiry_date,
      sourceType: r.hbos_source_type,
      releaseStatus: r.hbos_release_status,
    })),
    total: raw.length,
  }
}
