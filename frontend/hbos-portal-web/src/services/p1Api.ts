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
import { knowledgeLawCategories } from '@/contracts/p1'

export class DomainApiError extends Error {
  code: string
  retryable: boolean
  requestId?: string

  constructor(code: string, message: string, retryable = false, requestId?: string) {
    super(message)
    this.name = 'DomainApiError'
    this.code = code
    this.retryable = retryable
    if (typeof requestId === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(requestId)) this.requestId = requestId
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
  MODEL_TRANSPORT_FAILURE:'回答服务连接失败，请稍后重新提交。检索和个人记录仍可使用。',
  MODEL_REQUEST_FORMAT:'回答服务未接受请求格式，请联系维护人。',
  ANSWER_SCHEMA_INVALID:'回答格式未通过校验，本次未展示回答。请重新提交或查阅来源。',
  CITATION_SUPPORT_FAILED:'回答未通过来源支持校验，本次未展示回答。请查阅来源或调整问题。',
  RETRIEVAL_EMPTY:'没有找到可核实的公司依据，请调整关键词或资料范围。',
  RETRIEVAL_UPSTREAM_FAILED:'资料检索暂时失败，请稍后重试；目录和个人记录仍可查看。',
  SOURCE_VERSION_STALE:'来源已换版、下架或授权变化，请重新检索并核对当前来源。',
  MODEL_UNAVAILABLE:'所选模型配置尚未核验或已撤销，暂不可用。未自动切换其他模型。',
  MODEL_REQUEST_INVALID:'模型服务拒绝了请求格式，请联系维护人。',
  MODEL_AUTH_FAILED:'模型服务认证或授权失败，请联系维护人。',
  MODEL_RATE_LIMITED:'所选模型当前限流，未自动重试或切换模型。',
  MODEL_SERVICE_FAILED:'所选模型服务故障，未自动重试或切换模型。',
  INVALID_REQUEST: '请求格式无效。',
  AUTHENTICATION_REQUIRED: '登录状态已失效，请重新登录。',
  CLIENT_AUTH_FAILED: '登录状态已失效，请重新登录。',
  FORBIDDEN: '当前请求不可访问。',
  SCOPE_REJECTED: '当前请求不可访问。',
  ORIGINAL_ACCESS_DENIED: '不能提供未授权资料或原件。请只查询已共享且有权查阅的资料。',
  EMPTY_SCOPE: '当前没有可用授权资料。',
  EVIDENCE_INVALID: '该证据不可用或已失效。',
  EVIDENCE_REVOKED: '该证据不可用或已失效。',
  EVIDENCE_UNAVAILABLE: '该证据不可用或已失效。',
  POLICY_UNAVAILABLE: '授权服务暂时不可用。',
  UPSTREAM_UNAVAILABLE: '检索服务暂不可用，目录与个人记录仍可查看。',
  RATE_LIMITED: '请求较频繁，请稍后重试。',
  EXTRACTION_LIMITED: '本时段可展示的摘录已达上限。',
  ANSWER_MODEL_UNAVAILABLE: '回答服务暂时不可用，请稍后重试；检索和个人记录仍可使用。',
  MODEL_NOT_APPROVED: '回答能力尚未获准。',
  ANSWER_BUDGET_BLOCKED: '回答费用待核验或预算不可用，回答已暂停；目录、来源和个人记录仍可查看。',
}
function unwrapKnowledge<T>(envelope: DomainEnvelope<T>): T {
  if (!envelope.ok || envelope.data === undefined) {
    const supplied = envelope.error?.code || 'SERVICE_ERROR'
    const code = supplied in KNOWLEDGE_MESSAGES ? supplied : 'SERVICE_ERROR'
    throw new DomainApiError(code, KNOWLEDGE_MESSAGES[code] || '知识服务暂时不可用。', Boolean(envelope.error?.retryable), envelope.error?.request_id)
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
  if (!value || Object.keys(value).some(key => !['request_id','mode','results','context','search_mode','omitted_results'].includes(key)) ||
      value.mode !== 'retrieval' || !Array.isArray(value.results) || value.results.length > 5) throw invalid()
  safeKnowledgeString(value.request_id,128)
  const projected: KnowledgeSearchResult = { request_id:value.request_id, mode:'retrieval', results:value.results.map(validateKnowledgeEvidence) }
  if (value.search_mode !== undefined) {
    if (!['STANDARD','PRECISE'].includes(value.search_mode)) throw invalid()
    projected.search_mode = value.search_mode
  }
  if (value.omitted_results !== undefined) {
    if (!Number.isInteger(value.omitted_results) || (value.omitted_results as number) < 1 || (value.omitted_results as number) > 5) throw invalid()
    projected.omitted_results = value.omitted_results
  }
  // Current P1 legacy DTO may have context={}; canonical R1.1 omits it.
  if (value.context && Object.keys(value.context).length) {
    validateKnowledgeContext(value.context)
    projected.context = { ...value.context }
  }
  return projected
}
// Mirrors the backend CONTEXT_KEYS whitelist. Each key is independent: a scope
// may carry only an asset or only a component, which the backend accepts, so
// requiring equipment_id whenever the context is non-empty rejected valid
// scopes before the request was even sent.
function validateKnowledgeContext(context: KnowledgeSearchContext): void {
  const keys = Object.keys(context).filter(key => (context as Record<string, unknown>)[key] !== undefined)
  if (keys.some(key => !['equipment_id','asset_id','component_id'].includes(key))) {
    throw new DomainApiError('INVALID_REQUEST','设备检索上下文无效。')
  }
  if (context.equipment_id !== undefined && context.equipment_id !== null &&
      !/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(context.equipment_id)) {
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

export const modelAliases=['gpt-6-luna','deepseek-flash','gemini-3.8-flash','kimi-k3'] as const
function validateModelCatalog(data:import('@/contracts/p1').KnowledgeModels) {
  if (!data || Object.keys(data).some(k=>!['default','models','selected_alias'].includes(k)) || data.default!=='gpt-6-luna' || !modelAliases.includes(data.selected_alias) || !Array.isArray(data.models) || data.models.length!==4 || data.models.some((m,i)=>m.alias!==modelAliases[i] || Object.keys(m).some(k=>!['alias','available','reason'].includes(k)) || typeof m.available!=='boolean' || ![null,'CONFIGURATION_NOT_VERIFIED'].includes(m.reason))) throw new DomainApiError('SERVICE_ERROR','模型配置状态无效。')
  return data
}
export async function setKnowledgeModelPreference(alias:import('@/contracts/p1').KnowledgeModelAlias):Promise<void> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{selected_alias:string}>>('hb_knowledge_app.hb_knowledge.api.set_model_preference',{model_alias:alias}))
  if (Object.keys(data).length!==1 || data.selected_alias!==alias) throw new DomainApiError('SERVICE_ERROR','模型偏好保存未确认。')
}
export async function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  const data=unwrapKnowledge(await callFrappeMethod<DomainEnvelope<KnowledgeStatus>>(
    'hb_knowledge_app.hb_knowledge.api.get_status',
  ))
  if (data.model_catalog) validateModelCatalog(data.model_catalog)
  return data
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
  if (!doc || typeof doc !== 'object' || Object.keys(doc).some(k => !['document_id','title','space_id','department','document_number','version','status_note','version_id','download_state','download_note','legal_metadata','source_directories'].includes(k))) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
  for (const key of ['document_id','space_id','department','status_note'] as const) safeKnowledgeString(doc[key],320)
  safeKnowledgeString(doc.title,240,true); safeKnowledgeString(doc.document_number,120,true); safeKnowledgeString(doc.version,80,true)
  if (doc.source_directories !== undefined) {
    if (!Array.isArray(doc.source_directories) || doc.source_directories.length > 50) throw new DomainApiError('SERVICE_ERROR','原目录响应无效。')
    for (const path of doc.source_directories) {
      if (!Array.isArray(path) || !path.length || path.length > 30) throw new DomainApiError('SERVICE_ERROR','原目录响应无效。')
      path.forEach(segment => safeKnowledgeString(segment,240))
    }
  }
  if (doc.version_id !== undefined) safeKnowledgeString(doc.version_id,128)
  // The server states its own decision for this binding; the client only checks
  // the shape, never widens it. 'unavailable' is a real answer (for example an
  // original that could not be mapped), not a defect in the response.
  if (doc.download_state !== undefined && !['available','unavailable'].includes(doc.download_state)) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
  if (doc.download_note !== undefined) safeKnowledgeString(doc.download_note,320)
  if (doc.legal_metadata !== undefined) {
    const legal = doc.legal_metadata
    if (doc.space_id !== 'DEPT_PUBLIC_LAW' || !legal || typeof legal !== 'object' || Array.isArray(legal) || Object.keys(legal).some(k => !['category','level','issuer','published_date','region','applicability','effective_status'].includes(k)) || !knowledgeLawCategories.includes(legal.category) || !['待核','现行有效','已废止'].includes(legal.effective_status)) throw new DomainApiError('SERVICE_ERROR','法规分类响应无效。')
    for (const field of ['level','issuer','region','applicability'] as const) safeKnowledgeString(legal[field],160,true)
    if (legal.published_date != null && (!/^\d{4}-\d{2}-\d{2}$/.test(legal.published_date) || Number.isNaN(Date.parse(legal.published_date)) || new Date(legal.published_date).toISOString().slice(0,10) !== legal.published_date)) throw new DomainApiError('SERVICE_ERROR','法规日期响应无效。')
  }
}

export async function getKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{documents: KnowledgeDocument[]}>>(
    'hb_knowledge_app.hb_knowledge.api.get_documents',
  ))
  if (!data || Object.keys(data).length !== 1 || !Array.isArray(data.documents) || data.documents.length > 1000) throw new DomainApiError('SERVICE_ERROR','资料目录暂时不可用。')
  data.documents.forEach(validateKnowledgeDocument)
  return data.documents
}

export async function getKnowledgeDocumentsPage(query = '', spaceId = '', page = 1, pageSize = 12, lawCategory?: import('@/contracts/p1').KnowledgeLawCategory, folderId?: string): Promise<KnowledgeDocumentPage> {
  if (typeof query !== 'string' || [...query].length > 240 || typeof spaceId !== 'string' || spaceId !== spaceId.trim() || !Number.isSafeInteger(page) || page < 1 || !Number.isSafeInteger(pageSize) || pageSize < 1 || pageSize > 50) throw new DomainApiError('INVALID_REQUEST','目录筛选格式无效。')
  if (spaceId) safeKnowledgeString(spaceId,120)
  if (lawCategory !== undefined && !knowledgeLawCategories.includes(lawCategory)) throw new DomainApiError('INVALID_REQUEST','法规分类格式无效。')
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<KnowledgeDocumentPage>>(
    'hb_knowledge_app.hb_knowledge.api.get_documents_page', { query: query.trim(), space_id: spaceId, page, page_size: pageSize, ...(lawCategory ? { law_category: lawCategory } : {}), ...(folderId !== undefined ? { folder_id: folderId } : {}) },
  ))
  if (!data || Object.keys(data).some(k => !['documents','total','page','page_size','source_directory'].includes(k)) || !Array.isArray(data.documents) || data.documents.length > pageSize || !Number.isSafeInteger(data.total) || data.total < 0 || data.total < data.documents.length || data.page !== page || data.page_size !== pageSize) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
  if (data.source_directory !== undefined) {
    const tree=data.source_directory
    if (!tree || tree.folder_id !== folderId || !Array.isArray(tree.breadcrumbs) || !Array.isArray(tree.children)) throw new DomainApiError('SERVICE_ERROR','原目录响应无效。')
    for (const item of [...tree.breadcrumbs,...tree.children]) {
      safeKnowledgeString(item.name,240)
      if (!/^FOLDER_[a-f0-9]{24}$/.test(item.folder_id)) throw new DomainApiError('SERVICE_ERROR','原目录响应无效。')
    }
    if (tree.children.some(item => !Number.isSafeInteger(item.count) || item.count < 1)) throw new DomainApiError('SERVICE_ERROR','原目录计数无效。')
  }
  data.documents.forEach(validateKnowledgeDocument)
  if (new Set(data.documents.map(doc => doc.document_id)).size !== data.documents.length || (spaceId && data.documents.some(doc => doc.space_id !== spaceId)) || (lawCategory && data.documents.some(doc => doc.legal_metadata?.category !== lawCategory))) throw new DomainApiError('SERVICE_ERROR','资料目录响应无效。')
  return data
}

function validateRecordPage(value: unknown): void {
  const invalid=()=>new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw invalid()
  const data=value as Record<string,unknown>
  if (Object.keys(data).some(k=>!['items','page','page_size','has_more'].includes(k))) throw invalid()
  if (['page','page_size','has_more'].some(k=>k in data)) {
    if (!Number.isSafeInteger(data.page) || Number(data.page)<1 || !Number.isSafeInteger(data.page_size) || Number(data.page_size)<1 || Number(data.page_size)>50 || typeof data.has_more!=='boolean' || !Array.isArray(data.items) || data.items.length>Number(data.page_size)) throw invalid()
  }
}
export async function getKnowledgeFeedback(): Promise<KnowledgeFeedback[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{items: KnowledgeFeedback[]}>>('hb_knowledge_app.hb_knowledge.api.get_feedback'))
  validateRecordPage(data)
  if (!Array.isArray(data.items) || data.items.length > 100) throw new DomainApiError('SERVICE_ERROR','反馈记录暂时不可用。')
  data.items.forEach(item => {
    if (!item || typeof item !== 'object' || Object.keys(item).some(k => !['id','category','note','status','created_at','updated_at','reply'].includes(k)) || !['Pending','In Review','Resolved'].includes(item.status)) throw new DomainApiError('SERVICE_ERROR','反馈记录响应无效。')
    safeKnowledgeString(item.id,128); safeKnowledgeString(item.category,120); safeKnowledgeString(item.note,500)
    safeKnowledgeString(item.created_at,80); safeKnowledgeString(item.updated_at,80); safeKnowledgeString(item.reply,500,true)
  })
  return data.items
}

export async function getKnowledgeActivity(kind: 'History' | 'Bookmark'): Promise<import('@/contracts/p1').KnowledgeActivity[]> {
  const data = unwrapKnowledge(await callFrappeMethod<DomainEnvelope<{items: import('@/contracts/p1').KnowledgeActivity[]}>>('hb_knowledge_app.hb_knowledge.api.get_activity', {kind}))
  validateRecordPage(data)
  if (!Array.isArray(data.items) || data.items.length > 30) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  validateKnowledgeActivities(data.items)
  return data.items
}
export interface KnowledgeRecordPage<T> { items: T[]; page: number; page_size: number; has_more: boolean }
function validateKnowledgeActivities(items: import('@/contracts/p1').KnowledgeActivity[]): void {
  items.forEach(item => {
    if (Object.keys(item).some(k => !['id','query','created_at','available','titles','document_ids','version_ids','bookmark_type','answer_origin','model_alias'].includes(k)) || typeof item.available !== 'boolean' || !Array.isArray(item.titles) || (item.answer_origin!=null && !['KNOWLEDGE','GENERAL'].includes(item.answer_origin)) || (item.model_alias!=null && !modelAliases.includes(item.model_alias))) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
    safeKnowledgeString(item.id,128);safeKnowledgeString(item.query,500);safeKnowledgeString(item.created_at,80)
    item.titles.forEach(t => safeKnowledgeString(t,240,true))
    for (const key of ['document_ids','version_ids'] as const) {
      if (item[key] !== undefined) {
        if (!Array.isArray(item[key]) || item[key]!.length !== item.titles.length) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
        item[key]!.forEach(id => safeKnowledgeString(id,128))
      }
    }
    if (item.bookmark_type !== undefined && !['Document','Evidence'].includes(item.bookmark_type)) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  })
 }
export async function getKnowledgeActivityPage(kind: 'History' | 'Bookmark', page=1, pageSize=6): Promise<KnowledgeRecordPage<import('@/contracts/p1').KnowledgeActivity>> {
  if (!Number.isSafeInteger(page) || page<1 || !Number.isSafeInteger(pageSize) || pageSize<1 || pageSize>50) throw new DomainApiError('INVALID_REQUEST','记录分页无效。')
  const data=unwrapKnowledge(await callFrappeMethod<DomainEnvelope<KnowledgeRecordPage<import('@/contracts/p1').KnowledgeActivity>>>('hb_knowledge_app.hb_knowledge.api.get_activity',{kind,page,page_size:pageSize}))
  validateRecordPage(data)
  if (data.page!==page || data.page_size!==pageSize) throw new DomainApiError('SERVICE_ERROR','记录分页响应无效。')
  validateKnowledgeActivities(data.items)
  return data
}
export async function saveKnowledgeDocumentBookmark(documentId:string,versionId:string): Promise<void> {
  safeKnowledgeString(documentId,120); safeKnowledgeString(versionId,120)
  unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{id:string}>>('hb_knowledge_app.hb_knowledge.api.save_document_bookmark',{document_id:documentId,version_id:versionId}))
}
export async function getKnowledgeFeedbackPage(page=1,pageSize=6): Promise<KnowledgeRecordPage<KnowledgeFeedback>> {
  if (!Number.isSafeInteger(page) || page<1 || !Number.isSafeInteger(pageSize) || pageSize<1 || pageSize>50) throw new DomainApiError('INVALID_REQUEST','反馈分页无效。')
  const data=unwrapKnowledge(await callFrappeMethod<DomainEnvelope<KnowledgeRecordPage<KnowledgeFeedback>>>('hb_knowledge_app.hb_knowledge.api.get_feedback',{page,page_size:pageSize}))
  validateRecordPage(data)
  if (data.page!==page || data.page_size!==pageSize) throw new DomainApiError('SERVICE_ERROR','反馈分页响应无效。')
  for (const item of data.items) {
    if (!item || typeof item !== 'object' || Object.keys(item).some(k=>!['id','category','note','status','created_at','updated_at','reply'].includes(k)) || !['Pending','In Review','Resolved'].includes(item.status)) throw new DomainApiError('SERVICE_ERROR','反馈响应无效。')
    safeKnowledgeString(item.id,128);safeKnowledgeString(item.note,500);safeKnowledgeString(item.category,120);safeKnowledgeString(item.created_at,80);safeKnowledgeString(item.updated_at,80);safeKnowledgeString(item.reply,500,true)
  }
  return data
}
export async function openKnowledgeSaved(id: string): Promise<KnowledgeSavedQuery> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<KnowledgeSavedQuery>>('hb_knowledge_app.hb_knowledge.api.open_saved',{activity_id:id}))
  const invalid = () => new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  if (!data || typeof data !== 'object' || Object.keys(data).some(key => !['query','space_ids','context','restored','document','bookmark_type'].includes(key))) throw invalid()
  safeKnowledgeString(data.query,500)
  if (!Array.isArray(data.space_ids) || data.space_ids.length > 20 || new Set(data.space_ids).size !== data.space_ids.length) throw invalid()
  data.space_ids.forEach(s => { safeKnowledgeString(s,120); if (!s.trim() || s !== s.trim()) throw invalid() })
  const projected: KnowledgeSavedQuery = { query: data.query, space_ids: [...data.space_ids] }
  if ('document' in data || 'bookmark_type' in data) {
    if (data.bookmark_type !== 'Document' || !data.document || data.restored || data.context || data.space_ids.length !== 1 || data.document.space_id !== data.space_ids[0]) throw invalid()
    validateKnowledgeDocument(data.document)
    projected.document=data.document;projected.bookmark_type='Document'
  }
  if ('context' in data) {
    if (!data.context || typeof data.context !== 'object' || Array.isArray(data.context) || Object.keys(data.context).some(key => !['equipment_id','asset_id','component_id'].includes(key))) throw invalid()
    validateKnowledgeContext(data.context)
    if (Object.keys(data.context).length) projected.context = { ...data.context }
  }
  if (data.restored) {
    const r=data.restored
    if (!['ask','search'].includes(r.mode) || !['STANDARD','PRECISE'].includes(r.search_mode) || !Array.isArray(r.turns) || r.turns.length>10 || !Array.isArray(r.results) || r.results.length>5 || Object.keys(r).some(k=>!['mode','search_mode','results','turns'].includes(k))) throw invalid()
    r.results.forEach(validateKnowledgeEvidence)
    r.turns.forEach(t=>{const {question,...answer}=t;safeKnowledgeString(question,500);validateKnowledgeAnswer(answer,undefined,true)})
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
export async function askKnowledgeReference(question: string, space?: string, conversation?: string, searchMode: 'STANDARD' | 'PRECISE' = 'STANDARD', modelAlias:import('@/contracts/p1').KnowledgeModelAlias='gpt-6-luna',knowledgeOnly=false): Promise<import('@/contracts/p1').KnowledgeAnswer> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<import('@/contracts/p1').KnowledgeAnswer>>('hb_knowledge_app.hb_knowledge.api.ask',{question,search_mode:searchMode,model_alias:modelAlias,knowledge_only:knowledgeOnly,...(space?{space_ids:[space]}:{}),...(conversation?{conversation_id:conversation}:{})}))
  const answer=validateKnowledgeAnswer(data,space)
  if (answer.model_alias!==modelAlias || (knowledgeOnly && answer.answer_origin==='GENERAL')) throw new DomainApiError('SERVICE_ERROR','回答与本次模型或知识库选择不一致。')
  return answer
}
function validateKnowledgeAnswer(data: import('@/contracts/p1').KnowledgeAnswer, space?: string,historical=false): import('@/contracts/p1').KnowledgeAnswer {
  if (!data || typeof data!=='object' || Array.isArray(data)) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  if (Object.keys(data).some(k => !['request_id','turn_id','conversation_id','mode','answer_status','answerable','answer','citations','answer_origin','model_alias'].includes(k)) || !Array.isArray(data.citations) || data.citations.length>5 || !(modelAliases.includes(data.model_alias as any)||(historical&&data.model_alias===null)) || !['KNOWLEDGE','GENERAL'].includes(data.answer_origin || '')) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  safeKnowledgeString(data.answer,2000);safeKnowledgeString(data.turn_id,128)
  safeKnowledgeString(data.request_id,128)
  if (data.conversation_id !== undefined) { safeKnowledgeString(data.conversation_id,128); if (data.conversation_id !== data.turn_id) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。') }
  const answered=data.mode==='internal_reference_generation' && ['GENERATED_WITH_SOURCES','REFERENCE_ANSWERED'].includes(data.answer_status) && data.answerable===true && data.citations.length>0
  // INSUFFICIENT_EVIDENCE now carries a scope-aware next step instead of a
  // fixed sentence, so its answer text is no longer whitelisted here.
  const insufficient=data.mode==='authorized_generation' && data.answer_status==='INSUFFICIENT_EVIDENCE' && data.answerable===false && data.citations.length===0
  const general=data.mode==='general_generation' && data.answer_status==='GENERAL_ANSWERED' && data.answerable===true && data.answer_origin==='GENERAL' && data.citations.length===0 && !/\[C[1-5]\]/.test(data.answer)
  const referenceOnly=data.mode==='reference_only' && data.answer_status==='REFERENCE_ONLY' && data.answerable===false && data.citations.length>0 && ['仅供参考，请核对获准依据。','已找到并核实以下资料，但本次未形成可核验的归纳。请先查看来源。'].includes(data.answer)
  // Degraded but readable states: sources are shown, no natural synthesis is claimed.
  const excerpts=data.mode==='reference_excerpts' && data.answer_status==='REFERENCE_EXCERPTS' && data.answerable===false && data.citations.length>0
  const catalog=data.mode==='catalog_results' && data.answer_status==='CATALOG_RESULTS' && data.answerable===true && data.citations.length===0
  const clarification=data.mode==='clarification' && data.answer_status==='CLARIFIED' && data.answerable===false && data.citations.length===0
  const failed=data.mode==='failed' && data.answer_status==='FAILED' && data.answerable===false && data.citations.length>0
  if ((!answered && !insufficient && !general && !referenceOnly && !excerpts && !catalog && !clarification && !failed) || ((answered || insufficient || referenceOnly || excerpts || catalog || clarification || failed) && data.answer_origin!=='KNOWLEDGE')) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  data.citations.forEach(c => { const {citation_label,...e}=c; if (!/^C[1-5]$/.test(citation_label)) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。');validateKnowledgeEvidence(e) })
  if (new Set(data.citations.map(c => c.citation_label)).size !== data.citations.length || (space && data.citations.some(c => c.space_id !== undefined && c.space_id !== space))) throw new DomainApiError('SERVICE_ERROR','知识服务返回了无效响应。')
  return data
}

export interface PersonalConnection { id: string; label: string; client: 'OpenClaw' | 'Hermes'; stage: string; expires_at: string; revoked: boolean; expired: boolean; last_used_at: string | null; knowledge_used_at?:string|null; is_test?:boolean; verification_state?:'CLIENT_NOT_VERIFIED'|'SERVER_READY'|'CLIENT_CONNECTED'|'KNOWLEDGE_USED'; client_receipt?:{connection_id:string;client:string;challenge_id:string;authenticated_at:string|null;tools_at:string|null;search_request_id:string|null;evidence_request_id:string|null;knowledge_used_at:string|null;assurance:string} | null }
export interface ConnectionInfo { items: PersonalConnection[]; endpoint: string; auth_type: string; ttl_days: number; tools: string[]; deployment: string; query_blocked: boolean; client_versions: Record<string,string>; client_verification: Record<string,string> }
export async function getKnowledgeConnections(): Promise<ConnectionInfo> {
  const data=unwrapKnowledge(await callFrappeMethod<DomainEnvelope<ConnectionInfo>>('hb_knowledge_app.hb_knowledge.api.get_connections'))
  if (!Array.isArray(data.items) || data.items.length>50 || !Array.isArray(data.tools) || data.tools.length!==4 || typeof data.endpoint!=='string') throw new DomainApiError('SERVICE_ERROR','连接信息无效。')
  const endpoint=new URL(data.endpoint)
  if (endpoint.pathname!=='/mcp' || endpoint.search || endpoint.hash || endpoint.username || endpoint.password || !['http:','https:'].includes(endpoint.protocol) || (endpoint.protocol!=='https:' && !['localhost','knowledge-r2.localhost','127.0.0.1'].includes(endpoint.hostname))) throw new DomainApiError('SERVICE_ERROR','连接地址无效。')
  const tools=['list_knowledge_spaces','search_knowledge','get_evidence','ask_knowledge']
  if (new Set(data.tools).size!==4 || data.tools.some(t=>!tools.includes(t))) throw new DomainApiError('SERVICE_ERROR','连接工具范围无效。')
  for (const item of data.items) {
    if (!item || !/^[0-9a-f]{32}$/.test(item.id) || !['OpenClaw','Hermes'].includes(item.client) || typeof item.revoked!=='boolean' || typeof item.expired!=='boolean') throw new DomainApiError('SERVICE_ERROR','连接状态无效。')
    safeKnowledgeString(item.label,80);safeKnowledgeString(item.stage,80)
    if (item.verification_state && !['CLIENT_NOT_VERIFIED','SERVER_READY','CLIENT_CONNECTED','KNOWLEDGE_USED'].includes(item.verification_state)) throw new DomainApiError('SERVICE_ERROR','客户端收据无效。')
    const receipt=item.client_receipt
    if (receipt && (receipt.connection_id!==item.id || receipt.client!==item.client || !/^[0-9a-f]{32}$/.test(receipt.challenge_id) || receipt.assurance!=='BOUND_CHALLENGE_TOOL_CALLS')) throw new DomainApiError('SERVICE_ERROR','客户端收据无效。')
    if (receipt) for (const key of ['authenticated_at','tools_at','knowledge_used_at'] as const) if (receipt[key]!==null && (typeof receipt[key]!=='string' || !Number.isFinite(Date.parse(receipt[key]!)))) throw new DomainApiError('SERVICE_ERROR','客户端收据时间无效。')
    if (item.verification_state==='CLIENT_CONNECTED' && (!receipt?.authenticated_at || !receipt.tools_at)) throw new DomainApiError('SERVICE_ERROR','客户端收据未完成。')
    if (item.knowledge_used_at!==undefined && item.knowledge_used_at!==null && (typeof item.knowledge_used_at!=='string'||!Number.isFinite(Date.parse(item.knowledge_used_at)))) throw new DomainApiError('SERVICE_ERROR','最近使用时间无效。')
    if (item.is_test!==undefined && typeof item.is_test!=='boolean') throw new DomainApiError('SERVICE_ERROR','连接状态无效。')
    if (item.verification_state==='KNOWLEDGE_USED' && !item.knowledge_used_at && (!receipt?.authenticated_at || !receipt.tools_at || !receipt.search_request_id || !receipt.evidence_request_id || !receipt.knowledge_used_at)) throw new DomainApiError('SERVICE_ERROR','来源收据未完成。')
  }
  return data
}
export async function createKnowledgeConnection(label: string, client: string): Promise<{ id: string; token: string; expires_at: string;challenge_id?:string;challenge_expires_at?:string }> {
  const data=unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{id:string;token:string;expires_at:string;challenge_id?:string;challenge_expires_at?:string}>>('hb_knowledge_app.hb_knowledge.api.create_connection',{label,client_name:client}))
  if (!/^hbos_mcp_[0-9a-f]{32}\.[A-Za-z0-9_-]{43}$/.test(data.token) || !/^[0-9a-f]{32}$/.test(data.id)) throw new DomainApiError('SERVICE_ERROR','连接凭据无效。')
  return data
}
export async function revokeKnowledgeConnection(id: string): Promise<void> { unwrapKnowledge(await callFrappePostMethod<DomainEnvelope<{revoked:boolean}>>('hb_knowledge_app.hb_knowledge.api.revoke_connection',{connection_id:id})) }
