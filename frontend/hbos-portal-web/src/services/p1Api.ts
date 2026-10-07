import type {
  DomainEnvelope,
  FeishuLoginStatus,
  KnowledgeEvidence,
  KnowledgeSearchContext,
  KnowledgeSearchResult,
  KnowledgeStatus,
  TwinComponentMapping,
  TwinManifest,
  TwinStatus,
} from '@/contracts/p1'
import { callFrappeMethod, callFrappePostMethod } from '@/services/frappeClient'

export class DomainApiError extends Error {
  code: string
  retryable: boolean

  constructor(code: string, message: string, retryable = false) {
    super(message)
    this.name = 'DomainApiError'
    this.code = code
    this.retryable = retryable
  }
}

function unwrap<T>(envelope: DomainEnvelope<T>): T {
  if (!envelope.ok || envelope.data === undefined) {
    throw new DomainApiError(
      envelope.error?.code || 'SERVICE_ERROR',
      envelope.error?.message || '服务返回了无效响应。',
      Boolean(envelope.error?.retryable),
    )
  }
  return envelope.data
}

const KNOWLEDGE_MESSAGES: Record<string, string> = {
  INVALID_REQUEST: '请求格式无效。',
  AUTHENTICATION_REQUIRED: '登录状态已失效，请重新登录。',
  CLIENT_AUTH_FAILED: '登录状态已失效，请重新登录。',
  FORBIDDEN: '当前请求不可访问。',
  SCOPE_REJECTED: '当前请求不可访问。',
  EMPTY_SCOPE: '当前没有可用授权资料。',
  EVIDENCE_INVALID: '该证据不可用或已失效。',
  EVIDENCE_REVOKED: '该证据不可用或已失效。',
  EVIDENCE_UNAVAILABLE: '该证据不可用或已失效。',
  POLICY_UNAVAILABLE: '授权服务暂时不可用。',
  UPSTREAM_UNAVAILABLE: '知识服务暂时不可用。',
  RATE_LIMITED: '请求较频繁，请稍后重试。',
  EXTRACTION_LIMITED: '本时段可展示的摘录已达上限。',
}
function unwrapKnowledge<T>(envelope: DomainEnvelope<T>): T {
  if (!envelope.ok || envelope.data === undefined) {
    const supplied = envelope.error?.code || 'SERVICE_ERROR'
    const code = supplied in KNOWLEDGE_MESSAGES ? supplied : 'SERVICE_ERROR'
    throw new DomainApiError(code, KNOWLEDGE_MESSAGES[code] || '知识服务暂时不可用。', Boolean(envelope.error?.retryable))
  }
  return envelope.data
}
function safeKnowledgeString(value: unknown, maximum: number, nullable = false): void {
  if (nullable && (value === null || value === undefined)) return
  if (typeof value !== 'string' || [...value].length > maximum) throw new DomainApiError('SERVICE_ERROR', '知识服务返回了无效响应。')
  let text = value.normalize('NFKC')
  try { for (let i = 0; i < 3; i++) text = decodeURIComponent(text) } catch { /* reject literal encoded paths below */ }
  if (/(?:[a-z][a-z0-9+.-]*:\/\/|www\.|(?:javascript|data|mailto):|(?:^|[\s"'(])\/\S+|[a-z]:[\\/]|\.{2}[\\/]|%2f|%5c|\\u[0-9a-f]{4}|[<>]|&(?:lt|gt|#x?[\da-f]+);)/i.test(text)) {
    throw new DomainApiError('SERVICE_ERROR', '知识服务返回了无效响应。')
  }
}
function validateKnowledgeEvidence(value: unknown): KnowledgeEvidence {
  const invalid = () => new DomainApiError('SERVICE_ERROR', '知识服务返回了无效响应。')
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw invalid()
  const item = value as Record<string, unknown>
  const fields = new Set(['document_id','title','version','status_note','section','page_number','excerpt','evidence_id','space_id','source_type'])
  if (Object.keys(item).some(key => !fields.has(key))) throw invalid()
  for (const key of ['document_id','excerpt','evidence_id']) {
    safeKnowledgeString(item[key], key === 'excerpt' ? 500 : 128)
    if (!(item[key] as string).trim()) throw invalid()
  }
  for (const [key, maximum] of [['title',240],['version',80],['status_note',320],['section',240]] as const) {
    safeKnowledgeString(item[key], maximum, true)
  }
  if (item.page_number != null && (!Number.isInteger(item.page_number) || (item.page_number as number) < 1 || (item.page_number as number) > 100000)) throw invalid()
  if ((item.space_id === undefined) !== (item.source_type === undefined)) throw invalid()
  if (item.space_id !== undefined) {
    safeKnowledgeString(item.space_id, 120)
    if (!['COMPANY_CONTROLLED','EXTERNAL_REFERENCE','ORDINARY_INTERNAL_KNOWLEDGE','SYNTHETIC_TEST'].includes(String(item.source_type))) throw invalid()
  }
  return { ...item } as unknown as KnowledgeEvidence
}
function validateKnowledgeSearch(value: KnowledgeSearchResult): KnowledgeSearchResult {
  const invalid = () => new DomainApiError('SERVICE_ERROR', '知识服务返回了无效响应。')
  if (!value || Object.keys(value).some(key => !['request_id','mode','results','context'].includes(key)) ||
      value.mode !== 'retrieval' || !Array.isArray(value.results) || value.results.length > 5) throw invalid()
  safeKnowledgeString(value.request_id,128)
  const projected: KnowledgeSearchResult = { request_id:value.request_id, mode:'retrieval', results:value.results.map(validateKnowledgeEvidence) }
  // Current P1 legacy DTO may have context={}; canonical R1.1 omits it.
  if (value.context && Object.keys(value.context).length) {
    validateKnowledgeContext(value.context)
    projected.context = { ...value.context }
  }
  return projected
}
function validateKnowledgeContext(context: KnowledgeSearchContext): void {
  const keys = Object.keys(context).filter(key => (context as Record<string, unknown>)[key] !== undefined)
  if (keys.some(key => !['equipment_id','asset_id','component_id'].includes(key)) ||
      (keys.length > 0 && !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(context.equipment_id || ''))) {
    throw new DomainApiError('INVALID_REQUEST','设备检索上下文无效。')
  }
  for (const value of Object.values(context)) if (value !== undefined) safeKnowledgeString(value,200)
}
function abortable<T>(work: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return work
  return new Promise((resolve, reject) => {
    const aborted = () => reject(new DOMException('Cancelled', 'AbortError'))
    signal.addEventListener('abort',aborted,{once:true})
    work.then(value => { signal.removeEventListener('abort',aborted); if (!signal.aborted) resolve(value) },
              error => { signal.removeEventListener('abort',aborted); if (!signal.aborted) reject(error) })
    if (signal.aborted) aborted()
  })
}

export async function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  return unwrapKnowledge(await callFrappeMethod<DomainEnvelope<KnowledgeStatus>>(
    'hb_knowledge_app.hb_knowledge.api.get_status',
  ))
}

export async function searchKnowledge(
  query: string,
  context: KnowledgeSearchContext = {},
): Promise<KnowledgeSearchResult> {
  validateKnowledgeContext(context)
  return validateKnowledgeSearch(unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<KnowledgeSearchResult>>(
    'hb_knowledge_app.hb_knowledge.api.search',
    { query, limit: 5, ...context },
  )))
}

export async function resolveKnowledgeEvidence(evidenceId: string, signal?: AbortSignal): Promise<KnowledgeEvidence> {
  if (signal?.aborted) throw new DOMException('Cancelled','AbortError')
  const response = await abortable(callFrappePostMethod<DomainEnvelope<KnowledgeEvidence>>(
    'hb_knowledge_app.hb_knowledge.api.resolve_evidence',
    { evidence_id: evidenceId },
  ), signal)
  return validateKnowledgeEvidence(unwrapKnowledge(response))
}

export async function getTwinStatus(): Promise<TwinStatus> {
  return unwrap(await callFrappeMethod<DomainEnvelope<TwinStatus>>(
    'hb_twin_app.hb_twin.api.get_status',
  ))
}

export async function getTwinManifest(equipmentId = 'M607B'): Promise<TwinManifest> {
  return unwrap(await callFrappeMethod<DomainEnvelope<TwinManifest>>(
    'hb_twin_app.hb_twin.api.get_manifest',
    { equipment_id: equipmentId },
  ))
}

export async function getTwinComponentMapping(
  equipmentId: string,
  assetId: string,
): Promise<TwinComponentMapping> {
  return unwrap(await callFrappeMethod<DomainEnvelope<TwinComponentMapping>>(
    'hb_twin_app.hb_twin.api.get_component_mapping',
    { equipment_id: equipmentId, asset_id: assetId },
  ))
}

export async function getFeishuLoginStatus(): Promise<FeishuLoginStatus> {
  return callFrappeMethod<FeishuLoginStatus>('hbos_portal.auth.feishu.get_status')
}
