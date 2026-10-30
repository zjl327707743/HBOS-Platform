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

/**
 * 主数据查询结果 —— **必须区分「没有」和「没查到」**。
 *
 * 早先所有异常都 `catch` 成 `null`，调用方无法区分：
 *   - 物料确实不存在          → 该提示「尚未建档」
 *   - 网络失败 / 会话失效 / 无权限 → 该提示重试或重新登录
 *
 * 后果不只是文案错误：入库页在「未建档」时引导操作员去建档，
 * 而 SAP 物料代码体系下**重复建档会污染库存、批次、报表**。
 */
export type ItemMasterLookup =
  | { kind: 'found'; data: ItemMasterGaps }
  | { kind: 'not_found' }
  | { kind: 'error'; message: string }

/** `frappe.client.get_value` 查物料主数据。查不到 → `not_found`，不是 `null`。 */
export async function lookupItemMaster(itemCode: string): Promise<ItemMasterLookup> {
  const code = itemCode.trim()
  if (!code) return { kind: 'not_found' }

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
    if (!result || Object.keys(result).length === 0) return { kind: 'not_found' }
    return { kind: 'found', data: result as ItemMasterGaps }
  } catch (error) {
    return { kind: 'error', message: describeLookupError(error) }
  }
}

function describeLookupError(error: unknown): string {
  const status = (error as { status?: number } | null)?.status
  if (status === 401) return '登录状态已失效，请重新登录后再试。'
  if (status === 403) return '当前账号没有读取物料主数据的权限，请联系管理员。'
  if (status && status >= 500) return '服务端暂时不可用，请稍后重试。'
  if (status === undefined || status === 0) return '无法连接服务，请检查网络后重试。'
  return '读取物料主数据失败，请重试。'
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
  /** `null` = 本次不动包装构成；数组 = 替换（空数组即清空）。 */
  packaging: PackagingRow[] | null
  label_text?: string
}

export interface CreatedDraft {
  name: string
  docstatus: number
  batch: string
  /** 本次真正补进物料主数据的字段，界面据此如实回显 */
  filled: Array<{ field?: string; label?: string; value?: string }>
}

/**
 * 幂等键 —— **绑定到「一次具体的入库操作」**，不是一个页面级的可变字符串。
 *
 * 早先是模块级变量，只在用户点「再收一张」时重置。于是：建完一张草稿后
 * 从侧边栏离开、再重新进入 `/hbos/inventory/intake`，组件重挂载但模块变量
 * 还留着旧 id —— 5 分钟内下一张草稿会**命中上一张的结果**，返回的是别的单据。
 *
 * 现在的规则：
 *   - 每次进入页面生成一个 nonce（`beginIntakeOperation()`）；
 *   - 请求 id = nonce + 关键字段的哈希。
 *
 * 这样三种情况都对：
 *   同一张草稿因超时重试 → 字段没变 → 同一个 id → 服务端返回原单据；
 *   用户改了物料/批次/数量/照片 → 不同 id → 是另一次操作，建新单；
 *   离开页面再进来 → 新 nonce → 绝不命中旧结果。
 */
let intakeOperationNonce = ''

/** 进入「新入库操作」时调用（页面挂载、点「再收一张」）。 */
export function beginIntakeOperation(): void {
  intakeOperationNonce = randomId()
}

/** 兼容旧调用点：等价于开始一次新操作。 */
export function resetIntakeRequestId(): void {
  beginIntakeOperation()
}

function randomId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/** 同步 FNV-1a —— 只需要稳定的短 id，不需要密码学强度。 */
function hashString(text: string): string {
  let h1 = 0x811c9dc5
  let h2 = 0x01000193
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i)
    h1 = Math.imul(h1 ^ c, 0x01000193) >>> 0
    h2 = Math.imul(h2 + c, 0x85ebca6b) >>> 0
  }
  return h1.toString(36) + h2.toString(36)
}

/**
 * 影响「这是不是同一次入库操作」的字段 —— **凡是会改变建单结果的都要算**。
 *
 * 早先只取 7 个字段（物料/批次/数量/货位/照片/标签原文/包装）。用户改了
 * **来源类型、生产日期、有效期、供应商、生产单位、原厂批号** 后重试，
 * 指纹不变 → 命中旧 request_id → 返回上一张草稿，修改静默丢失。
 *
 * 后端 `_intake_payload_fingerprint` 使用同一组字段（两边必须同步改）。
 */
const FINGERPRINT_FIELDS = [
  'item_code',
  'batch_no',
  'warehouse',
  'file_url',
  'source_type',
  'manufacturing_date',
  'expiry_date',
  'storage_condition',
  'workshop',
  'shelf_life_type',
  'supplier_name',
  'manufacturer',
  'supplier_batch_no',
  'label_text',
] as const

function operationFingerprint(input: DraftInput): string {
  const parts: unknown[] = [String(input.qty)]
  for (const key of FINGERPRINT_FIELDS) {
    parts.push(input[key] ?? null)
  }
  parts.push(input.packaging ?? null)
  return JSON.stringify(parts)
}

function requestIdFor(input: DraftInput): string {
  if (!intakeOperationNonce) beginIntakeOperation()
  return `${intakeOperationNonce.slice(0, 8)}-${hashString(operationFingerprint(input))}`
}

export async function createIntakeDraft(input: DraftInput): Promise<CreatedDraft> {
  return postFrappeMethod<CreatedDraft>(
    'hb_inventory_app.hbos_inventory.api.create_intake_draft',
    {
      ...input,
      // `null` 原样传下去（= 本次不动包装）；只有真的有行时才序列化
      packaging: input.packaging === null ? null : JSON.stringify(input.packaging),
      request_id: requestIdFor(input),
    },
  )
}
