import type { DomainEnvelope } from '@/contracts/p1'
import type {
  ReaderBlock,
  ReaderBody,
  ReaderDocument,
  ReaderFailure,
  ReaderNavigation,
  ReaderOpenDocument,
  ReaderSearchMatch,
  ReaderSearchResult,
  ReaderTocEntry,
} from '@/contracts/documentReader'
import { DomainApiError } from '@/services/p1Api'
import { callFrappePostMethod } from '@/services/frappeClient'

const METHODS = {
  open: 'hb_knowledge_app.hb_knowledge.api.open_document',
  page: 'hb_knowledge_app.hb_knowledge.api.read_document_page',
  search: 'hb_knowledge_app.hb_knowledge.api.search_document',
} as const

const DEFAULT_DISCLOSURE =
  '正文来自已授权当前版本的索引文本（安全净化派生），不是原件下载；页码未核验。'

/** Fixed, safe UI copy keyed by server error code. Server messages are never echoed verbatim. */
const READER_MESSAGES: Record<string, string> = {
  DOCUMENT_READ_UNAVAILABLE: '该资料当前不可阅读：可能没有阅读权限、已撤回或版本已变化。',
  UPSTREAM_INVALID_RESULT: '正文服务返回异常，请返回后重新打开该资料。',
  UPSTREAM_SCOPE_VIOLATION: '正文服务授权校验失败，请返回后重新打开该资料。',
  DOCUMENT_FORBIDDEN: '当前账号没有阅读该资料的权限，正文已清除。',
  DOCUMENT_WITHDRAWN: '该资料已撤回，正文不再提供。',
  DOCUMENT_VERSION_STALE: '资料版本已变化，当前阅读版本不再可用。请到资料目录打开当前版本。',
  DOCUMENT_VERSION_AMBIGUOUS: '存在多个可读版本，无法唯一定位当前版本。请从资料目录打开当前版本。',
  DOCUMENT_NOT_PUBLISHED: '该资料尚未发布，正文暂不可阅读。',
  DOCUMENT_READ_PAGE_OUT_OF_RANGE: '页码超出可读范围，已返回第 1 页。',
  INVALID_REQUEST: '阅读请求无效，请返回后重新打开资料。',
  UPSTREAM_UNAVAILABLE: '正文服务暂时不可用，请稍后重试。',
  RETRIEVAL_UPSTREAM_FAILED: '正文服务暂时不可用，请稍后重试。',
  POLICY_UNAVAILABLE: '授权服务暂时不可用，请稍后重试。',
  RATE_LIMITED: '请求较频繁，请稍后再试。',
  AUTHENTICATION_REQUIRED: '登录状态已失效，请重新登录。',
  CLIENT_AUTH_FAILED: '登录状态已失效，请重新登录。',
  FORBIDDEN: '当前账号没有阅读该资料的权限。',
  SCOPE_REJECTED: '当前账号没有阅读该资料的权限。',
  EMPTY_SCOPE: '当前没有可用授权资料。',
  NETWORK_ERROR: '无法连接服务，请检查网络后重试。',
  SERVICE_ERROR: '资料阅读服务暂时不可用，请稍后重试。',
}

const DOCUMENT_STATES = new Set(['WITHDRAWN', 'VERSION_STALE', 'NOT_AUTHORIZED', 'NOT_PUBLISHED', 'VERSION_AMBIGUOUS', 'SUPERSEDED', 'UNKNOWN'])
const STATE_MESSAGES: Record<string, string> = {
  WITHDRAWN: '该资料已撤回，正文不再提供。',
  VERSION_STALE: '资料版本已变化，当前阅读版本不再可用。请到资料目录打开当前版本。',
  NOT_AUTHORIZED: '当前账号没有阅读该资料的权限，正文已清除。',
  NOT_PUBLISHED: '该资料尚未发布，正文暂不可阅读。',
  VERSION_AMBIGUOUS: '存在多个可读版本，无法唯一定位当前版本。请从资料目录打开当前版本。',
}
const UNAVAILABLE_CODES = new Set([
  'DOCUMENT_READ_UNAVAILABLE', 'DOCUMENT_FORBIDDEN', 'DOCUMENT_WITHDRAWN', 'DOCUMENT_VERSION_STALE',
  'DOCUMENT_NOT_PUBLISHED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE', 'AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED',
  'EVIDENCE_UNAVAILABLE', 'EVIDENCE_REVOKED', 'EVIDENCE_INVALID', 'SOURCE_VERSION_STALE',
])
const UPSTREAM_CODES = new Set([
  'UPSTREAM_UNAVAILABLE', 'RETRIEVAL_UPSTREAM_FAILED', 'POLICY_UNAVAILABLE', 'RATE_LIMITED',
  'SERVICE_ERROR', 'NETWORK_ERROR',
])

/** A reader transport/projection failure; `state` keeps the optional server stage hint. */
export class DocumentReaderError extends DomainApiError {
  state: string | null

  constructor(code: string, message: string, retryable = false, state: string | null = null) {
    super(code, message, retryable)
    this.name = 'DocumentReaderError'
    this.state = state
  }
}

class InvalidReaderResponse extends DocumentReaderError {
  constructor() {
    super('SERVICE_ERROR', '资料阅读服务返回了无效响应。', false)
    this.name = 'InvalidReaderResponse'
  }
}

function invalid(): never {
  throw new InvalidReaderResponse()
}

function abortError() {
  return new DOMException('Cancelled', 'AbortError')
}

function abortable<T>(work: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return work
  if (signal.aborted) return Promise.reject(abortError())
  return new Promise((resolve, reject) => {
    const aborted = () => reject(abortError())
    signal.addEventListener('abort', aborted, { once: true })
    work.then(
      value => { signal.removeEventListener('abort', aborted); if (!signal.aborted) resolve(value) },
      error => { signal.removeEventListener('abort', aborted); if (!signal.aborted) reject(error) },
    )
  })
}

function unwrap<T>(envelope: DomainEnvelope<T> | null | undefined): T {
  if (!envelope || envelope.ok !== true || envelope.data === undefined) {
    const raw = (envelope?.error || {}) as unknown as Record<string, unknown>
    const supplied = typeof raw.code === 'string' && raw.code in READER_MESSAGES ? raw.code : 'SERVICE_ERROR'
    const state =
      typeof raw.state === 'string' && DOCUMENT_STATES.has(raw.state) ? raw.state
        : typeof raw.stage === 'string' && DOCUMENT_STATES.has(raw.stage) ? raw.stage
          : null
    throw new DocumentReaderError(
      supplied,
      (state && STATE_MESSAGES[state]) || READER_MESSAGES[supplied] || READER_MESSAGES.SERVICE_ERROR!,
      Boolean(raw.retryable),
      state,
    )
  }
  return envelope.data
}

// ---- field helpers: this is the single mapping layer between the BFF payload
// and the view. Unknown server fields are dropped here so the browser can never
// render a physical identifier even if a future backend adds one by mistake.

function textField(value: unknown, maximum: number, nullable = true): string | null {
  if (value === undefined || value === null) {
    if (nullable) return null
    invalid()
  }
  if (typeof value !== 'string' || [...value].length > maximum) invalid()
  return value as string
}

function requiredText(value: unknown, maximum: number): string {
  const result = textField(value, maximum, false)
  if (result === null || !result.trim()) invalid()
  return result
}

function identifier(value: unknown, maximum: number, nullable = true): string | null {
  const result = textField(value, maximum, nullable)
  if (result === null) return null
  if (!result.trim() || /\s/.test(result)) invalid()
  return result
}

function integer(value: unknown, minimum: number, maximum: number): number {
  if (!Number.isSafeInteger(value) || (value as number) < minimum || (value as number) > maximum) invalid()
  return value as number
}

function nullableInteger(value: unknown, minimum: number, maximum: number): number | null {
  if (value === undefined || value === null) return null
  return integer(value, minimum, maximum)
}

function asArray(value: unknown, maximum: number): unknown[] {
  if (!Array.isArray(value) || value.length > maximum) invalid()
  return value
}

function mapDocument(value: unknown, requestedVersionId: string | null): ReaderDocument {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  const documentId = identifier(record.document_id, 120, false)
  // The server resolves the current authorized version when the entry has no
  // VER_ id; the returned identity is then authoritative for page/search calls.
  const versionId = identifier(record.version_id, 128) || requestedVersionId
  if (!documentId || !versionId) invalid()
  return {
    document_id: documentId,
    version_id: versionId,
    title: textField(record.title, 240) || '',
    document_number: textField(record.document_number, 120),
    space_id: identifier(record.space_id, 120) || '',
    space_title: textField(record.space_title, 120),
    business_version: textField(record.business_version, 80),
    status_note: textField(record.status_note, 320),
    reference_state: textField(record.reference_state, 64) || 'UNKNOWN',
    authorization: textField(record.authorization, 64) || 'UNKNOWN',
    source_type: textField(record.source_type, 64) || 'UNKNOWN',
  }
}

function mapBlock(value: unknown): ReaderBlock {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  return {
    block_id: requiredText(record.block_id, 128),
    ordinal: integer(record.ordinal, 1, 1000000),
    page_number: nullableInteger(record.page_number, 1, 100000),
    section: textField(record.section, 240),
    // Contract bound is 4000 cp per block; the 500 cp evidence projection must
    // never be applied to reader body text.
    text: textField(record.text, 4000, false) || '',
  }
}

function mapBody(value: unknown): ReaderBody {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  const page = integer(record.page, 1, 100000)
  const pageCount = nullableInteger(record.page_count, 0, 100000)
  if (pageCount !== null && pageCount > 0 && page > pageCount) invalid()
  const blocks = asArray(record.blocks, 64)
    .map(mapBlock)
    .filter(block => block.text.trim().length > 0)
  const blockTotal = record.block_total === undefined || record.block_total === null
    ? blocks.length
    : integer(record.block_total, 0, 1000000)
  return {
    origin: textField(record.origin, 64) || 'UNKNOWN',
    page_numbering: textField(record.page_numbering, 32) || 'UNAVAILABLE',
    derived: record.derived === true,
    page,
    page_count: pageCount,
    block_total: blockTotal,
    blocks,
  }
}

function mapTocEntry(value: unknown): ReaderTocEntry {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  return {
    title: requiredText(record.title, 240),
    ordinal: integer(record.ordinal, 1, 1000000),
    page_number: nullableInteger(record.page_number, 1, 100000),
  }
}

function mapNavigation(value: unknown): ReaderNavigation {
  if (value === undefined || value === null) return { toc: [], toc_source: null, toc_truncated: false }
  if (typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  return {
    toc: asArray(record.toc ?? [], 200).map(mapTocEntry),
    toc_source: textField(record.toc_source, 64),
    toc_truncated: record.toc_truncated === true,
  }
}

function mapOpenDocument(value: unknown, requestedVersionId: string | null): ReaderOpenDocument {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  return {
    document: mapDocument(record.document, requestedVersionId),
    body: mapBody(record.body),
    navigation: mapNavigation(record.navigation),
    disclosure: textField(record.disclosure, 1000) || DEFAULT_DISCLOSURE,
  }
}

function mapSearchMatch(value: unknown): ReaderSearchMatch {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  return {
    ordinal: integer(record.ordinal, 1, 1000000),
    page: nullableInteger(record.page, 1, 100000),
    block_id: requiredText(record.block_id, 128),
    // Contract snippet bound is 240 cp; allow the full server snippet window and
    // never truncate it in the client.
    snippet: textField(record.snippet, 500, false) || '',
  }
}

function mapSearchResult(value: unknown): ReaderSearchResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  const record = value as Record<string, unknown>
  return {
    matches: asArray(record.matches ?? [], 100).map(mapSearchMatch),
    searched_blocks: record.searched_blocks === undefined || record.searched_blocks === null
      ? 0
      : integer(record.searched_blocks, 0, 1000000),
    capped: record.capped === true,
  }
}

// ---- request input validation ------------------------------------------------

export interface ReaderDocumentTarget {
  documentId: string
  versionId?: string | null
}

function normalizeDocumentId(value: unknown): string {
  if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$/.test(value)) {
    throw new DomainApiError('INVALID_REQUEST', '资料标识无效。')
  }
  return value
}

function normalizeVersionId(value: unknown): string | null {
  if (value === undefined || value === null || value === '') return null
  if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) {
    throw new DomainApiError('INVALID_REQUEST', '资料版本标识无效。')
  }
  return value
}

function requestBody(target: ReaderDocumentTarget, versionId: string | null): Record<string, unknown> {
  const body: Record<string, unknown> = { document_id: normalizeDocumentId(target.documentId) }
  // version_id is optional by contract: when an entry only knows the document
  // identity, the server resolves the current authorized version inside the
  // same snapshot. The resolved id comes back as document.version_id.
  if (versionId) body.version_id = versionId
  return body
}

export async function openKnowledgeDocument(
  target: ReaderDocumentTarget,
  signal?: AbortSignal,
): Promise<ReaderOpenDocument> {
  const versionId = normalizeVersionId(target.versionId)
  if (signal?.aborted) throw abortError()
  const envelope = await abortable(
    callFrappePostMethod<DomainEnvelope<unknown>>(METHODS.open, requestBody(target, versionId)),
    signal,
  )
  return mapOpenDocument(unwrap(envelope), versionId)
}

export async function readKnowledgeDocumentPage(
  target: ReaderDocumentTarget,
  page: number,
  signal?: AbortSignal,
): Promise<ReaderOpenDocument> {
  const versionId = normalizeVersionId(target.versionId)
  if (!Number.isSafeInteger(page) || page < 1 || page > 100000) {
    throw new DomainApiError('INVALID_REQUEST', '页码无效。')
  }
  if (signal?.aborted) throw abortError()
  const envelope = await abortable(
    callFrappePostMethod<DomainEnvelope<unknown>>(METHODS.page, { ...requestBody(target, versionId), page }),
    signal,
  )
  return mapOpenDocument(unwrap(envelope), versionId)
}

export async function searchKnowledgeDocument(
  target: ReaderDocumentTarget,
  query: string,
  limit = 20,
  signal?: AbortSignal,
): Promise<ReaderSearchResult> {
  const versionId = normalizeVersionId(target.versionId)
  const normalized = typeof query === 'string' ? query.trim() : ''
  if (!normalized || [...normalized].length > 120) {
    throw new DomainApiError('INVALID_REQUEST', '查找内容请控制在 120 字以内。')
  }
  if (!Number.isSafeInteger(limit) || limit < 1 || limit > 20) {
    throw new DomainApiError('INVALID_REQUEST', '查找结果数量无效。')
  }
  if (signal?.aborted) throw abortError()
  const envelope = await abortable(
    callFrappePostMethod<DomainEnvelope<unknown>>(METHODS.search, {
      ...requestBody(target, versionId), query: normalized, limit,
    }),
    signal,
  )
  return mapSearchResult(unwrap(envelope))
}

// ---- failure classification --------------------------------------------------

const UNAVAILABLE_MESSAGES: Record<string, string> = {
  WITHDRAWN: '该资料已撤回，正文不再提供。',
  VERSION_STALE: '资料版本已变化，当前阅读版本不再可用。请到资料目录打开当前版本。',
  NOT_AUTHORIZED: '当前账号没有阅读该资料的权限，正文已清除。',
  NOT_PUBLISHED: '该资料尚未发布，正文暂不可阅读。',
  VERSION_AMBIGUOUS: '存在多个可读版本，无法唯一定位当前版本。请从资料目录打开当前版本。',
}

/**
 * Distinguish "cannot read" from "temporarily broken" from "invalid request".
 * A read that is not allowed must clear the body view; an upstream outage is
 * retryable and must never be presented as "no content".
 */
export function classifyReaderFailure(error: unknown): ReaderFailure {
  if (error instanceof DomainApiError) {
    const state = typeof (error as unknown as { state?: unknown }).state === 'string'
      ? String((error as unknown as { state: string }).state)
      : null
    if (state && UNAVAILABLE_MESSAGES[state]) {
      return { kind: 'unavailable', code: error.code, message: UNAVAILABLE_MESSAGES[state]!, retryable: false, state }
    }
    if (error.code === 'DOCUMENT_READ_PAGE_OUT_OF_RANGE') {
      return { kind: 'page-range', code: error.code, message: READER_MESSAGES.DOCUMENT_READ_PAGE_OUT_OF_RANGE!, retryable: true }
    }
    if (error.code === 'INVALID_REQUEST') {
      return { kind: 'invalid', code: error.code, message: READER_MESSAGES.INVALID_REQUEST!, retryable: false }
    }
    if (UNAVAILABLE_CODES.has(error.code)) {
      return { kind: 'unavailable', code: error.code, message: READER_MESSAGES[error.code] || READER_MESSAGES.DOCUMENT_READ_UNAVAILABLE!, retryable: false }
    }
    if (UPSTREAM_CODES.has(error.code)) {
      return { kind: 'upstream', code: error.code, message: READER_MESSAGES[error.code] || READER_MESSAGES.UPSTREAM_UNAVAILABLE!, retryable: true }
    }
    return {
      kind: 'error',
      code: error.code,
      message: READER_MESSAGES[error.code] || READER_MESSAGES.SERVICE_ERROR!,
      retryable: Boolean(error.retryable),
    }
  }
  return { kind: 'upstream', code: 'SERVICE_ERROR', message: READER_MESSAGES.UPSTREAM_UNAVAILABLE!, retryable: true }
}
