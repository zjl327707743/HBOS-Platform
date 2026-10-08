import type {
  DomainEnvelope,
  FeishuLoginStatus,
  KnowledgeEvidence,
  KnowledgeSearchContext,
  KnowledgeSearchResult,
  KnowledgeStatus,
  KnowledgeSpace,
  KnowledgeDocument,
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
  UPSTREAM_UNAVAILABLE: '检索服务暂不可用，目录与个人记录仍可查看。',
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
  if (/(?:[a-z][a-z0-9+.-]*:\/\/|www\.|(?:javascript|data|mailto):|(?:^|[\s"'(])\/\S+|[a-z]:[\\/]|\.{2}[\\/]|%2f|%5c|\\u[0-9a-f]{4}|<\s*(?:\/?[a-z!])[^>]*>|&(?:lt|gt|#x?[\da-f]+);)/i.test(text)) {
    throw new DomainApiError('SERVICE_ERROR', '知识服务返回了无效响应。')
  }
}
function validateKnowledgeEvidence(value: unknown): KnowledgeEvidence {
  const invalid = () => new DomainApiError('SERVICE_ERROR', '知识服务返回了无效响应。')
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw invalid()
  const item = value as Record<string, unknown>
  const fields = new Set(['document_id','title','version','status_note','section','page_number','excerpt','evidence_id','space_id','source_type','document_number'])
  if (Object.keys(item).some(key => !fields.has(key))) throw invalid()
  for (const key of ['document_id','excerpt','evidence_id']) {
    safeKnowledgeString(item[key], key === 'excerpt' ? 500 : 128)
    if (!(item[key] as string).trim()) throw invalid()
  }
  for (const [key, maximum] of [['title',240],['version',80],['status_note',320],['section',240],['document_number',120]] as const) {
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
  spaceIds?: string[],
): Promise<KnowledgeSearchResult> {
  validateKnowledgeContext(context)
  if (spaceIds !== undefined) {
    if (!Array.isArray(spaceIds) || spaceIds.length < 1 || spaceIds.length > 20 || new Set(spaceIds).size !== spaceIds.length) {
      throw new DomainApiError('INVALID_REQUEST', '检索空间无效。')
    }
    for (const id of spaceIds) { safeKnowledgeString(id, 120); if (!id.trim() || id !== id.trim()) throw new DomainApiError('INVALID_REQUEST', '检索空间无效。') }
  }
  return validateKnowledgeSearch(unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<KnowledgeSearchResult>>(
    'hb_knowledge_app.hb_knowledge.api.search',
    { query, limit: 5, ...context, ...(spaceIds ? { space_ids: [...spaceIds] } : {}) },
  )))
}

export async function getKnowledgeSpaces(): Promise<KnowledgeSpace[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{ spaces: KnowledgeSpace[] }>>(
    'hb_knowledge_app.hb_knowledge.api.get_spaces',
  ))
  const invalid = () => new DomainApiError('SERVICE_ERROR', '知识服务返回了无效响应。')
  if (!data || Object.keys(data).length !== 1 || !Array.isArray(data.spaces) || data.spaces.length > 100) throw invalid()
  const seen = new Set<string>()
  return data.spaces.map(space => {
    if (!space || Object.keys(space).length !== 3 || Object.keys(space).some(key => !['space_id','title','document_count'].includes(key))) throw invalid()
    safeKnowledgeString(space.space_id, 120); safeKnowledgeString(space.title, 120)
    if (!space.space_id.trim() || !space.title.trim() || seen.has(space.space_id) || !Number.isSafeInteger(space.document_count) || space.document_count < 0) throw invalid()
    seen.add(space.space_id)
    return { space_id: space.space_id, title: space.title, document_count: space.document_count }
  })
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

export async function getKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{documents: KnowledgeDocument[]}>>(
    'hb_knowledge_app.hb_knowledge.api.get_documents',
  ))
  if (!data || Object.keys(data).length !== 1 || !Array.isArray(data.documents) || data.documents.length > 1000) throw new DomainApiError('SERVICE_ERROR','资料目录暂时不可用。')
  for (const doc of data.documents) {
    if (Object.keys(doc).some(k => !['document_id','title','space_id','department','document_number','version','status_note'].includes(k))) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
    for (const key of ['document_id','space_id','department','status_note'] as const) safeKnowledgeString(doc[key],320)
    safeKnowledgeString(doc.title,240,true); safeKnowledgeString(doc.document_number,120,true); safeKnowledgeString(doc.version,80,true)
  }
  return data.documents
}

export async function getKnowledgeActivity(kind: 'History' | 'Bookmark'): Promise<import('@/contracts/p1').KnowledgeActivity[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{items: import('@/contracts/p1').KnowledgeActivity[]}>>('hb_knowledge_app.hb_knowledge.api.get_activity', {kind}))
  if (!Array.isArray(data.items) || data.items.length > 30) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  data.items.forEach(item => {
    if (Object.keys(item).some(k => !['id','query','created_at','available','titles'].includes(k)) || typeof item.available !== 'boolean' || !Array.isArray(item.titles)) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
    safeKnowledgeString(item.id,128);safeKnowledgeString(item.query,500);safeKnowledgeString(item.created_at,80)
    item.titles.forEach(t => safeKnowledgeString(t,240,true))
  })
  return data.items
}
export async function openKnowledgeSaved(id: string): Promise<{query: string;space_ids: string[]}> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{query: string;space_ids: string[]}>>('hb_knowledge_app.hb_knowledge.api.open_saved',{activity_id:id}))
  safeKnowledgeString(data.query,500)
  if (!Array.isArray(data.space_ids)) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  data.space_ids.forEach(s => safeKnowledgeString(s,120));return data
}
export async function removeKnowledgeSaved(id: string): Promise<void> {
  unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{removed:boolean}>>('hb_knowledge_app.hb_knowledge.api.remove_saved',{activity_id:id}))
}
export async function saveKnowledgeBookmark(evidence: string, query: string): Promise<void> {
  unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{id:string}>>('hb_knowledge_app.hb_knowledge.api.save_bookmark',{evidence_id:evidence,query}))
}
export async function sendKnowledgeFeedback(evidence: string | undefined, category: string, note: string): Promise<void> {
  unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{id:string}>>('hb_knowledge_app.hb_knowledge.api.submit_feedback',{evidence_id:evidence,category,note}))
}
export async function askKnowledgeReference(question: string, space?: string, conversation?: string): Promise<import('@/contracts/p1').KnowledgeAnswer> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<import('@/contracts/p1').KnowledgeAnswer>>('hb_knowledge_app.hb_knowledge.api.ask',{question,...(space?{space_ids:[space]}:{}),...(conversation?{conversation_id:conversation}:{})}))
  if (Object.keys(data).some(k => !['request_id','turn_id','conversation_id','mode','answer_status','answerable','answer','citations'].includes(k)) || !Array.isArray(data.citations) || data.citations.length>5) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  safeKnowledgeString(data.answer,2000);safeKnowledgeString(data.turn_id,128)
  const answered=data.mode==='internal_reference_generation' && data.answer_status==='REFERENCE_ANSWERED' && data.answerable===true && data.citations.length>0
  const insufficient=data.mode==='authorized_generation' && data.answer_status==='INSUFFICIENT_EVIDENCE' && data.answerable===false && data.answer==='当前授权资料不足以形成回答。' && data.citations.length===0
  if (!answered && !insufficient) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  data.citations.forEach(c => { const {citation_label,...e}=c; if (!/^C[1-5]$/.test(citation_label)) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。');validateKnowledgeEvidence(e) })
  return data
}
