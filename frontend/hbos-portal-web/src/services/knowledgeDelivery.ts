/**
 * RC14 frozen delivery interfaces (see .rc14/INTERFACES.md).
 *
 * Every delivery is a short-lived same-origin ticket URL. The browser never
 * receives physical ids, storage paths or long-lived tokens; the server
 * re-validates identity, action authorization, current version, withdrawal and
 * hash on every document_content request, so a previously prepared preview or
 * download may still be refused and the UI must offer to prepare it again.
 */
import type { DomainEnvelope } from '@/contracts/p1'
import { DomainApiError } from '@/services/p1Api'
import { callFrappePostMethod } from '@/services/frappeClient'

const CAPABILITIES_METHOD = 'hb_knowledge_app.hb_knowledge.api.document_capabilities'
const DELIVERY_METHOD = 'hb_knowledge_app.hb_knowledge.api.create_document_delivery'
const CONTENT_PATH = '/api/method/hb_knowledge_app.hb_knowledge.api.document_content'

export type DeliveryKind = 'ORIGINAL_PDF' | 'DERIVED_PDF' | 'ORIGINAL_FILE'

export interface DocumentCapabilities {
  document_id: string
  version_id: string
  can_read: true
  can_preview: boolean
  can_download: boolean
  preview_kind: 'ORIGINAL_PDF' | 'DERIVED_PDF' | null
  preview_reason: string | null
  download_reason: string | null
}

export interface DocumentDelivery {
  content_url: string
  expires_at: number
  filename: string
  content_type: string
  sha256: string
  kind: DeliveryKind
}

export type DeliveryFailureReason =
  | 'DOWNLOAD_NOT_AUTHORIZED'
  | 'ASSET_UNAVAILABLE'
  | 'ASSET_HASH_MISMATCH'
  | 'ASSET_TOO_LARGE'
  | 'PREVIEW_UNAVAILABLE'
  | 'TICKET_EXPIRED'

const DELIVERY_MESSAGES: Record<DeliveryFailureReason, string> = {
  DOWNLOAD_NOT_AUTHORIZED: '当前账号没有这份资料的下载授权；如需下载请按原文档流程申请。',
  ASSET_UNAVAILABLE: '原始文件暂不可用，可能未完成导入或已下架。',
  ASSET_HASH_MISMATCH: '文件校验不一致，系统已阻止本次提供，请联系维护人复核。',
  ASSET_TOO_LARGE: '文件超过当前可提供的体积上限，暂不能预览或下载。',
  PREVIEW_UNAVAILABLE: '该资料暂不支持原版式预览，可继续阅读正文。',
  TICKET_EXPIRED: '预览或下载准备已过期，请重新准备一次。',
}

const FAILURE_REASONS = new Set(Object.keys(DELIVERY_MESSAGES))

function invalid(): never {
  throw new DomainApiError('SERVICE_ERROR', '资料提供服务返回了无效响应。')
}

function identifier(value: unknown, maximum: number): string {
  if (typeof value !== 'string' || !value.trim() || /\s/.test(value) || value.length > maximum) invalid()
  return value as string
}

function filename(value: unknown): string {
  if (typeof value !== 'string' || !value.trim() || value.length > 240 || /[\x00-\x1f\x7f/\\]/.test(value)) invalid()
  return value
}

export function deliveryReasonMessage(value: string | null | undefined): string {
  return value && FAILURE_REASONS.has(value) ? DELIVERY_MESSAGES[value as DeliveryFailureReason] : '暂不可用，请联系资料维护人核对。'
}

function optionalReason(value: unknown): string | null {
  if (value === undefined || value === null) return null
  if (typeof value !== 'string' || [...value].length > 200) invalid()
  return value
}

function mapCapabilities(value: unknown): DocumentCapabilities {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  if (record.can_read !== true) invalid()
  const previewKind = record.preview_kind === undefined || record.preview_kind === null
    ? null
    : record.preview_kind
  if (previewKind !== null && previewKind !== 'ORIGINAL_PDF' && previewKind !== 'DERIVED_PDF') invalid()
  if (typeof record.can_preview !== 'boolean' || typeof record.can_download !== 'boolean') invalid()
  // A claimed capability without a kind (preview) is inconsistent; only trust
  // the flags the server actually set.
  if (record.can_preview === true && previewKind === null) invalid()
  return {
    document_id: identifier(record.document_id, 120),
    version_id: identifier(record.version_id, 128),
    can_read: true,
    can_preview: record.can_preview,
    can_download: record.can_download,
    preview_kind: previewKind as DocumentCapabilities['preview_kind'],
    preview_reason: optionalReason(record.preview_reason),
    download_reason: optionalReason(record.download_reason),
  }
}

function validateContentUrl(value: unknown): string {
  if (typeof value !== 'string') invalid()
  let parsed: URL
  try {
    parsed = new URL(value as string, window.location.origin)
  } catch {
    invalid()
  }
  if (parsed.origin !== window.location.origin) invalid()
  if (parsed.pathname !== CONTENT_PATH) invalid()
  if (!/^[A-Za-z0-9_-]{43}$/.test(parsed.searchParams.get('ticket') || '') || [...parsed.searchParams.keys()].length !== 1) invalid()
  if (parsed.username || parsed.password || parsed.searchParams.get('token')) invalid()
  return parsed.href
}

function mapDelivery(value: unknown): DocumentDelivery {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  if (Object.keys(record).some(key => !['content_url', 'expires_at', 'filename', 'content_type', 'sha256', 'kind'].includes(key))) invalid()
  if (!Number.isSafeInteger(record.expires_at) || (record.expires_at as number) <= 0) invalid()
  if (typeof record.sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(record.sha256)) invalid()
  if (!['application/pdf', 'application/octet-stream'].includes(record.content_type as string)) invalid()
  const kind = record.kind
  if (kind !== 'ORIGINAL_PDF' && kind !== 'DERIVED_PDF' && kind !== 'ORIGINAL_FILE') invalid()
  return {
    content_url: validateContentUrl(record.content_url),
    expires_at: record.expires_at as number,
    filename: filename(record.filename),
    content_type: identifier(record.content_type, 120),
    sha256: identifier(record.sha256, 128),
    kind,
  }
}

function unwrapDelivery<T>(envelope: DomainEnvelope<T> | null | undefined): T {
  if (!envelope || envelope.ok !== true || envelope.data === undefined) {
    const error = (envelope?.error || {}) as unknown as Record<string, unknown>
    if (error.code === 'DOCUMENT_DELIVERY_UNAVAILABLE') {
      const reason = typeof error.state === 'string' && FAILURE_REASONS.has(error.state)
        ? (error.state as DeliveryFailureReason)
        : 'ASSET_UNAVAILABLE'
      throw new DomainApiError(reason, DELIVERY_MESSAGES[reason])
    }
    if (error.code === 'DOCUMENT_RANGE_NOT_SATISFIABLE') {
      throw new DomainApiError('DOCUMENT_RANGE_NOT_SATISFIABLE', '本次预览请求超出文件范围，请重新准备预览。')
    }
    const supplied = typeof error.code === 'string' ? error.code : 'SERVICE_ERROR'
    throw new DomainApiError(supplied, typeof error.message === 'string' && error.message ? '资料预览或下载暂不可用，请稍后重试。' : '资料预览或下载暂不可用，请稍后重试。')
  }
  return envelope.data
}

export function deliveryFailureMessage(error: unknown): string {
  if (error instanceof DomainApiError) return error.message
  return '资料预览或下载暂不可用，请稍后重试。'
}

/** True when the failure is a stale ticket the user can retry by preparing again. */
export function isRetryableDelivery(error: unknown): boolean {
  return error instanceof DomainApiError &&
    ['TICKET_EXPIRED', 'DOCUMENT_RANGE_NOT_SATISFIABLE', 'UPSTREAM_UNAVAILABLE', 'RATE_LIMITED', 'SERVICE_ERROR', 'NETWORK_ERROR'].includes(error.code)
}

export async function fetchDocumentCapabilities(
  documentId: string,
  versionId?: string | null,
): Promise<DocumentCapabilities> {
  const payload: Record<string, unknown> = { document_id: documentId }
  if (versionId) payload.version_id = versionId
  return mapCapabilities(unwrapDelivery(await callFrappePostMethod<DomainEnvelope<unknown>>(CAPABILITIES_METHOD, payload)))
}

export async function createDocumentDelivery(
  documentId: string,
  versionId: string | null,
  purpose: 'preview' | 'download',
): Promise<DocumentDelivery> {
  const payload: Record<string, unknown> = { document_id: documentId, purpose }
  if (versionId) payload.version_id = versionId
  return mapDelivery(unwrapDelivery(await callFrappePostMethod<DomainEnvelope<unknown>>(DELIVERY_METHOD, payload)))
}
