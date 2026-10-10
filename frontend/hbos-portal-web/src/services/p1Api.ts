import type {
  DomainEnvelope,
  FeishuLoginStatus,
  KnowledgeEvidence,
  KnowledgeSearchContext,
  KnowledgeSearchResult,
  KnowledgeSavedQuery,
  KnowledgeStatus,
  KnowledgeSpace,
  KnowledgeDocument,
  KnowledgeDocumentPage,
  KnowledgeFeedback,
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
  ANSWER_MODEL_UNAVAILABLE: '回答模型暂时不可用或未通过依据校验。请稍后重试；检索和记录仍可使用。',
  MODEL_NOT_APPROVED: '回答能力尚未获准。',
  ANSWER_BUDGET_BLOCKED: '回答费用待核验或预算不可用，回答已暂停；目录、来源和个人记录仍可查看。',
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
  if (!value || Object.keys(value).some(key => !['request_id','mode','results','context','search_mode'].includes(key)) ||
      value.mode !== 'retrieval' || !Array.isArray(value.results) || value.results.length > 5) throw invalid()
  safeKnowledgeString(value.request_id,128)
  const projected: KnowledgeSearchResult = { request_id:value.request_id, mode:'retrieval', results:value.results.map(validateKnowledgeEvidence) }
  if (value.search_mode !== undefined) {
    if (!['STANDARD','PRECISE'].includes(value.search_mode)) throw invalid()
    projected.search_mode = value.search_mode
  }
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
  searchMode: 'STANDARD' | 'PRECISE' = 'STANDARD',
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
    { query, limit: 5, search_mode: searchMode, ...context, ...(spaceIds ? { space_ids: [...spaceIds] } : {}) },
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

function validateKnowledgeDocument(doc: KnowledgeDocument): void {
  if (!doc || typeof doc !== 'object' || Object.keys(doc).some(k => !['document_id','title','space_id','department','document_number','version','status_note'].includes(k))) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
  for (const key of ['document_id','space_id','department','status_note'] as const) safeKnowledgeString(doc[key],320)
  safeKnowledgeString(doc.title,240,true); safeKnowledgeString(doc.document_number,120,true); safeKnowledgeString(doc.version,80,true)
}

export async function getKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{documents: KnowledgeDocument[]}>>(
    'hb_knowledge_app.hb_knowledge.api.get_documents',
  ))
  if (!data || Object.keys(data).length !== 1 || !Array.isArray(data.documents) || data.documents.length > 1000) throw new DomainApiError('SERVICE_ERROR','资料目录暂时不可用。')
  data.documents.forEach(validateKnowledgeDocument)
  return data.documents
}

export async function getKnowledgeDocumentsPage(query = '', spaceId = '', page = 1, pageSize = 12): Promise<KnowledgeDocumentPage> {
  if (typeof query !== 'string' || [...query].length > 240 || typeof spaceId !== 'string' || spaceId !== spaceId.trim() || !Number.isSafeInteger(page) || page < 1 || !Number.isSafeInteger(pageSize) || pageSize < 1 || pageSize > 50) throw new DomainApiError('INVALID_REQUEST','目录筛选格式无效。')
  if (spaceId) safeKnowledgeString(spaceId,120)
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<KnowledgeDocumentPage>>(
    'hb_knowledge_app.hb_knowledge.api.get_documents_page', { query: query.trim(), space_id: spaceId, page, page_size: pageSize },
  ))
  if (!data || Object.keys(data).some(k => !['documents','total','page','page_size'].includes(k)) || !Array.isArray(data.documents) || data.documents.length > pageSize || !Number.isSafeInteger(data.total) || data.total < 0 || data.total < data.documents.length || data.page !== page || data.page_size !== pageSize) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
  data.documents.forEach(validateKnowledgeDocument)
  if (new Set(data.documents.map(doc => doc.document_id)).size !== data.documents.length || (spaceId && data.documents.some(doc => doc.space_id !== spaceId))) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
  return data
}

export async function getKnowledgeFeedback(): Promise<KnowledgeFeedback[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{items: KnowledgeFeedback[]}>>('hb_knowledge_app.hb_knowledge.api.get_feedback'))
  if (!data || Object.keys(data).length !== 1 || !Array.isArray(data.items) || data.items.length > 100) throw new DomainApiError('SERVICE_ERROR','反馈记录暂时不可用。')
  data.items.forEach(item => {
    if (!item || typeof item !== 'object' || Object.keys(item).some(k => !['id','category','note','status','created_at','updated_at','reply'].includes(k)) || !['Pending','In Review','Resolved'].includes(item.status)) throw new DomainApiError('SERVICE_ERROR','反馈记录响应无效。')
    safeKnowledgeString(item.id,128); safeKnowledgeString(item.category,120); safeKnowledgeString(item.note,500)
    safeKnowledgeString(item.created_at,80); safeKnowledgeString(item.updated_at,80); safeKnowledgeString(item.reply,500,true)
  })
  return data.items
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
export async function openKnowledgeSaved(id: string): Promise<KnowledgeSavedQuery> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<KnowledgeSavedQuery>>('hb_knowledge_app.hb_knowledge.api.open_saved',{activity_id:id}))
  const invalid = () => new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  if (!data || typeof data !== 'object' || Object.keys(data).some(key => !['query','space_ids','context','restored'].includes(key))) throw invalid()
  safeKnowledgeString(data.query,500)
  if (!Array.isArray(data.space_ids) || data.space_ids.length > 20 || new Set(data.space_ids).size !== data.space_ids.length) throw invalid()
  data.space_ids.forEach(s => { safeKnowledgeString(s,120); if (!s.trim() || s !== s.trim()) throw invalid() })
  const projected: KnowledgeSavedQuery = { query: data.query, space_ids: [...data.space_ids] }
  if ('context' in data) {
    if (!data.context || typeof data.context !== 'object' || Array.isArray(data.context) || Object.keys(data.context).some(key => !['equipment_id','asset_id','component_id'].includes(key))) throw invalid()
    validateKnowledgeContext(data.context)
    if (Object.keys(data.context).length) projected.context = { ...data.context }
  }
  if (data.restored) {
    const r=data.restored
    if (!['ask','search'].includes(r.mode) || !['STANDARD','PRECISE'].includes(r.search_mode) || !Array.isArray(r.turns) || r.turns.length>10 || !Array.isArray(r.results) || r.results.length>5 || Object.keys(r).some(k=>!['mode','search_mode','results','turns'].includes(k))) throw invalid()
    r.results.forEach(validateKnowledgeEvidence)
    r.turns.forEach(t=>{const {question,...answer}=t;safeKnowledgeString(question,500);validateKnowledgeAnswer(answer)})
    projected.restored=r
  }
  return projected
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
export async function askKnowledgeReference(question: string, space?: string, conversation?: string, searchMode: 'STANDARD' | 'PRECISE' = 'STANDARD'): Promise<import('@/contracts/p1').KnowledgeAnswer> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<import('@/contracts/p1').KnowledgeAnswer>>('hb_knowledge_app.hb_knowledge.api.ask',{question,search_mode:searchMode,...(space?{space_ids:[space]}:{}),...(conversation?{conversation_id:conversation}:{})}))
  return validateKnowledgeAnswer(data,space)
}
function validateKnowledgeAnswer(data: import('@/contracts/p1').KnowledgeAnswer, space?: string): import('@/contracts/p1').KnowledgeAnswer {
  if (Object.keys(data).some(k => !['request_id','turn_id','conversation_id','mode','answer_status','answerable','answer','citations'].includes(k)) || !Array.isArray(data.citations) || data.citations.length>5) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  safeKnowledgeString(data.answer,2000);safeKnowledgeString(data.turn_id,128)
  safeKnowledgeString(data.request_id,128)
  if (data.conversation_id !== undefined) { safeKnowledgeString(data.conversation_id,128); if (data.conversation_id !== data.turn_id) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。') }
  const answered=data.mode==='internal_reference_generation' && data.answer_status==='REFERENCE_ANSWERED' && data.answerable===true && data.citations.length>0
  const refusalMessages=['当前授权资料不足以形成回答。','无法可靠定位前一回答中的具体条目。请指出步骤名称或关键词后再问；当前资料不足以直接回答这个追问。']
  const insufficient=data.mode==='authorized_generation' && data.answer_status==='INSUFFICIENT_EVIDENCE' && data.answerable===false && refusalMessages.includes(data.answer) && data.citations.length===0
  if (!answered && !insufficient) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  data.citations.forEach(c => { const {citation_label,...e}=c; if (!/^C[1-5]$/.test(citation_label)) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。');validateKnowledgeEvidence(e) })
  if (new Set(data.citations.map(c => c.citation_label)).size !== data.citations.length || (space && data.citations.some(c => c.space_id !== undefined && c.space_id !== space))) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  return data
}

export interface PersonalConnection { id: string; label: string; client: 'OpenClaw' | 'Hermes'; stage: string; expires_at: string; revoked: boolean; expired: boolean; last_used_at: string | null }
export interface ConnectionInfo { items: PersonalConnection[]; endpoint: string; auth_type: string; ttl_days: number; tools: string[]; deployment: string; query_blocked: boolean; client_versions: Record<string,string>; client_verification: Record<string,string> }
export async function getKnowledgeConnections(): Promise<ConnectionInfo> {
  const data=unwrapKnowledge(await callFrappeMethod<DomainEnvelope<ConnectionInfo>>('hb_knowledge_app.hb_knowledge.api.get_connections'))
  if (!Array.isArray(data.items) || data.items.length>50 || !Array.isArray(data.tools) || data.tools.length!==4 || typeof data.endpoint!=='string') throw new DomainApiError('SERVICE_ERROR','连接信息无效。')
  const endpoint=new URL(data.endpoint)
  if (endpoint.pathname!=='/mcp' || endpoint.search || endpoint.hash || (endpoint.protocol!=='https:' && !['localhost','knowledge-r2.localhost','127.0.0.1'].includes(endpoint.hostname))) throw new DomainApiError('SERVICE_ERROR','连接地址无效。')
  return data
}
export async function createKnowledgeConnection(label: string, client: string): Promise<{ id: string; token: string; expires_at: string }> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{id:string;token:string;expires_at:string}>>('hb_knowledge_app.hb_knowledge.api.create_connection',{label,client_name:client}))
  if (!/^hbos_mcp_[0-9a-f]{32}\.[A-Za-z0-9_-]{43}$/.test(data.token) || !/^[0-9a-f]{32}$/.test(data.id)) throw new DomainApiError('SERVICE_ERROR','连接凭据无效。')
  return data
}
export async function revokeKnowledgeConnection(id: string): Promise<void> { unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{revoked:boolean}>>('hb_knowledge_app.hb_knowledge.api.revoke_connection',{connection_id:id})) }
