import { callFrappeMethod, postFrappeMethod, uploadFrappeFile } from '@/services/frappeClient'

/**
 * 入库拍照识别 —— 前端侧接口层。
 *
 * 后端 Authority：`hb_inventory_app.hbos_inventory.api`。
 * 本文件只做「把接口包成类型化函数」，**不复制任何业务规则**——规则（不伪造、
 * 只出草稿、仅补空、不自动建档、代码形近纠错要多命中不猜）都在后端。
 */

// ---------------------------------------------------------------------------
// 上下文
// ---------------------------------------------------------------------------

export interface IntakeBackend {
  available: boolean
  reason?: string
}

export interface IntakeService {
  available: boolean
  reason: string
  backends: Record<string, IntakeBackend>
  default_backend: string
}

export interface IntakeWarehouse {
  value: string
  label: string
  parent?: string
}

export interface IntakeContext {
  service: IntakeService
  source_types: string[]
  warehouses: IntakeWarehouse[]
  company?: string
}

export async function getIntakeContext(): Promise<IntakeContext> {
  return callFrappeMethod<IntakeContext>(
    'hb_inventory_app.hbos_inventory.api.get_intake_context',
  )
}

// ---------------------------------------------------------------------------
// 识别
// ---------------------------------------------------------------------------

export interface RecognizeResult {
  fields: Record<string, string | null>
  raw_fields?: Record<string, string | null>
  hints?: Record<string, string[]>
  confidence?: Record<string, number>
  raw_text?: string
  needs_review?: boolean
  master_item_name?: string
  request_id?: string
}

export async function recognizeLabel(
  fileUrl: string,
  sourceType: string,
): Promise<RecognizeResult> {
  return callFrappeMethod<RecognizeResult>(
    'hb_inventory_app.hbos_inventory.api.recognize_label',
    { file_url: fileUrl, source_type: sourceType },
  )
}

// ---------------------------------------------------------------------------
// 主数据回显（物料级三字段）
// ---------------------------------------------------------------------------

export interface ItemMasterGaps {
  hbos_storage_condition?: string | null
  hbos_workshop?: string | null
  hbos_shelf_life_type?: string | null
}

/** 物料不存在时返回 null —— 界面据此提示「尚未建档」，**不自动建档**。 */
export async function lookupItemMaster(
  itemCode: string,
): Promise<ItemMasterGaps | null> {
  const code = itemCode.trim()
  if (!code) return null

  try {
    const result = await postFrappeMethod<ItemMasterGaps | Record<string, never>>(
      'frappe.client.get_value',
      {
        doctype: 'Item',
        filters: JSON.stringify({ name: code }),
        fieldname: JSON.stringify([
          'hbos_storage_condition',
          'hbos_workshop',
          'hbos_shelf_life_type',
        ]),
      },
    )
    // 查不到时 Frappe 返回空对象 {}，不是 null
    if (!result || Object.keys(result).length === 0) return null
    return result as ItemMasterGaps
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// 照片上传
// ---------------------------------------------------------------------------

export interface UploadedFile {
  file_url: string
  name: string
}

/**
 * 上传标签照片。照片作为**草稿的原始凭证**，私有存储（`is_private=1`）。
 *
 * 端点用相对路径即可：它走的是共享 axios 实例，`baseURL` 为空时经 Portal 代理转发，
 * 设了 `VITE_FRAPPE_BASE_URL` 时自动补成绝对地址。
 */
export async function uploadLabelPhoto(file: File): Promise<UploadedFile> {
  const message = await uploadFrappeFile('/api/method/upload_file', file, {
    is_private: '1',
    folder: 'Home',
  })
  const fileUrl = String(message.file_url || '')
  if (!fileUrl) throw new Error('照片上传失败：服务端未返回文件地址')
  return { file_url: fileUrl, name: String(message.name || '') }
}

// ---------------------------------------------------------------------------
// 生成草稿
// ---------------------------------------------------------------------------

export interface PackagingRow {
  container_type: string
  unit_weight: number
  count: number
}

export interface DraftInput {
  item_code: string
  batch_no: string
  qty: string | number
  warehouse: string
  file_url: string
  file_name?: string
  source_type?: string
  manufacturing_date?: string | null
  expiry_date?: string | null
  storage_condition?: string | null
  workshop?: string | null
  shelf_life_type?: string | null
  supplier_name?: string | null
  manufacturer?: string | null
  supplier_batch_no?: string | null
  packaging: PackagingRow[]
  label_text?: string
}

export interface CreatedDraft {
  name: string
  docstatus: number
  batch: string
  /** 本次真正补进物料主数据的字段，界面据此如实回显 */
  filled: Array<{ field?: string; label?: string; value?: string }>
}

export async function createIntakeDraft(input: DraftInput): Promise<CreatedDraft> {
  return postFrappeMethod<CreatedDraft>(
    'hb_inventory_app.hbos_inventory.api.create_intake_draft',
    {
      ...input,
      packaging: JSON.stringify(input.packaging || []),
    },
  )
}
