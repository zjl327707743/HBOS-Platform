import type { DomainEnvelope } from '@/contracts/p1'
import { callFrappeMethod, callFrappePostMethod, callFrappeUploadMethod } from './frappeClient'
import { DomainApiError } from './p1Api'
export interface ImportItem { document_id:string; version_id:string; title:string; filename:string; sha256:string; relationship:string; expected_version:string|null; parse_status:string; progress:number; chunk_count:number; quality_status:string; shared_approved?:boolean; quality_note:string; current_version:string|null; publication_status:string }
export interface ImportBatch { batch_id:string; label:string; department:string; status:string; last_error:string|null; items:ImportItem[]; total:number; page:number; page_size:number; counts:{parsed:number;failed:number;quality_passed:number} }
export interface MaintenanceFeedback { id:string; category:string; note:string; status:string; reply?:string; maintenance_reply?:string; title?:string }
export interface VersionTarget { document_id:string; version_id:string; current_version:string; title:string; department:string; document_number?:string|null }
export interface DepartmentFunnel {department:string;title:string;discovered:number;shared_approved:number;uploaded:number;parsed:number;validated:number;published:number;pending_review:number;isolated:number;sensitive:number;failed:number;sharing_pending:number}
export interface MaintenanceBatchEntry { name:string; label:string; department_key:string; status:string; document_page?:number }
export type MaintenanceLookupState = 'FOUND' | 'NOT_FOUND' | null
/** Bounded server-side maintenance lookup (WP6); never a browser-side full scan. */
export interface MaintenanceLookup {
  published_query?: string
  published_document_id?: string
  published_page?: number
  published_page_size?: number
  batch_query?: string
  batch_document_id?: string
  batch_page?: number
  batch_page_size?: number
}
export interface MaintenanceDashboard {
  department_funnel?:DepartmentFunnel[]
  published_documents:VersionTarget[]
  published_total?:number
  published_matched?:number
  published_truncated?:boolean
  published_page?:number
  published_page_size?:number
  published_has_more?:boolean
  published_query?:string|null
  published_document_id?:string|null
  published_lookup_state?:MaintenanceLookupState
  departments:{key:string;title:string}[]
  batches:MaintenanceBatchEntry[]
  batches_total?:number
  batches_matched?:number
  batches_page?:number
  batches_page_size?:number
  batches_has_more?:boolean
  batch_query?:string|null
  batch_document_id?:string|null
  batch_lookup_state?:MaintenanceLookupState
  batch_scan_truncated?:boolean
  selected:ImportBatch|null
  feedback:{items:MaintenanceFeedback[]}
  import_availability:{can_parse:boolean;can_batch?:boolean;configured:boolean;blocked:boolean}
}
export interface QualityPreview { title:string; fragments:{text:string;location:string}[]; chunk_count:number; source_sha256:string; version_id:string }
const method=(name:string)=>`hb_knowledge_app.hb_knowledge.api.${name}`
const messages:Record<string,string>={SCOPE_REJECTED:'当前账号没有知识维护权限。',AUTHENTICATION_REQUIRED:'登录已失效，请重新登录。',INVALID_REQUEST:'文件或操作无效，请核对格式、大小和当前状态。',IDENTITY_CONFLICT:'身份或当前版本冲突，请选择明确的换版关系。',IMPORT_BUSY:'该批次正在处理，请等待本次完成。',QUALITY_REQUIRED:'请先完成本版本的质量核对。',IMPORT_BUDGET_BLOCKED:'解析费用待核验或预算不可用，解析已暂停。'}
function unwrap<T>(value:DomainEnvelope<T>):T { if(!value.ok||value.data===undefined) { const code=value.error?.code||'SERVICE_ERROR';throw new DomainApiError(code,messages[code]||'维护服务暂不可用。',Boolean(value.error?.retryable)) } return value.data }
const LOOKUP_DOCUMENT_ID=/^DOC_[A-Za-z0-9_-]{1,96}$/
const LOOKUP_CONTROL=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\r\n]/
function lookupText(value:unknown):string {
  if(typeof value!=='string')throw new DomainApiError('INVALID_REQUEST','维护查找参数无效。')
  const normalized=value.trim()
  if(!normalized||[...normalized].length>120||LOOKUP_CONTROL.test(normalized))throw new DomainApiError('INVALID_REQUEST','维护查找参数无效。')
  return normalized
}
function lookupDocumentId(value:unknown):string {
  if(typeof value!=='string'||!LOOKUP_DOCUMENT_ID.test(value))throw new DomainApiError('INVALID_REQUEST','维护查找文档标识无效。')
  return value
}
function lookupPage(value:unknown):number {
  if(!Number.isSafeInteger(value)||(value as number)<1||(value as number)>100000)throw new DomainApiError('INVALID_REQUEST','维护查找页码无效。')
  return value as number
}
function lookupPageSize(value:unknown,maximum:number):number {
  if(!Number.isSafeInteger(value)||(value as number)<1||(value as number)>maximum)throw new DomainApiError('INVALID_REQUEST','维护查找每页数量无效。')
  return value as number
}
function normalizeLookup(lookup:MaintenanceLookup):MaintenanceLookup {
  const value:MaintenanceLookup={}
  if(lookup.published_query!==undefined)value.published_query=lookupText(lookup.published_query)
  if(lookup.published_document_id!==undefined)value.published_document_id=lookupDocumentId(lookup.published_document_id)
  if(lookup.published_page!==undefined)value.published_page=lookupPage(lookup.published_page)
  if(lookup.published_page_size!==undefined)value.published_page_size=lookupPageSize(lookup.published_page_size,50)
  if(lookup.batch_query!==undefined)value.batch_query=lookupText(lookup.batch_query)
  if(lookup.batch_document_id!==undefined)value.batch_document_id=lookupDocumentId(lookup.batch_document_id)
  if(lookup.batch_page!==undefined)value.batch_page=lookupPage(lookup.batch_page)
  if(lookup.batch_page_size!==undefined)value.batch_page_size=lookupPageSize(lookup.batch_page_size,100)
  if(value.published_query!==undefined&&value.published_document_id!==undefined)throw new DomainApiError('INVALID_REQUEST','维护查找参数无效。')
  if(value.batch_query!==undefined&&value.batch_document_id!==undefined)throw new DomainApiError('INVALID_REQUEST','维护查找参数无效。')
  return value
}
/**
 * Read the bounded maintenance dashboard.
 *
 * The 4th argument is additive: callers that do not pass a lookup keep the exact
 * legacy request (default first-1000 published projection and first batch page),
 * so existing pages and tests behave unchanged. When a lookup is supplied it is
 * validated here and forwarded as server-side query/document/pagination params;
 * the browser never widens or scans a projection on its own.
 */
export async function getMaintenance(batch_id?:string,page=1,locate?:string,lookup?:MaintenanceLookup):Promise<MaintenanceDashboard> {
  if(!Number.isSafeInteger(page)||page<1||page>100000)throw new DomainApiError('INVALID_REQUEST','维护分页参数无效。')
  if(locate!==undefined&&typeof locate!=='string')throw new DomainApiError('INVALID_REQUEST','维护查找参数无效。')
  const params:Record<string,unknown>={batch_id,page,page_size:12,...(locate?{locate}:{})}
  if(lookup)Object.assign(params,normalizeLookup(lookup))
  return unwrap(await callFrappeMethod<DomainEnvelope<MaintenanceDashboard>>(method('get_maintenance'),params))
}
export async function maintenanceAction(name:string,args:Record<string,unknown>):Promise<unknown> { return unwrap(await callFrappePostMethod<DomainEnvelope<unknown>>(method(name),args)) }
export async function getMaintenanceFeedbackPage(page=1,status=''):Promise<{items:MaintenanceFeedback[];page:number;page_size:number;has_more:boolean}> {
  const data=unwrap(await callFrappeMethod<DomainEnvelope<{items:MaintenanceFeedback[];page:number;page_size:number;has_more:boolean}>>(method('get_feedback_queue'),{page,page_size:6,status}))
  if(!Array.isArray(data.items)||data.items.length>6||data.page!==page||data.page_size!==6||typeof data.has_more!=='boolean')throw new DomainApiError('SERVICE_ERROR','反馈分页响应无效。')
  return data
}
export async function previewImport(batch_id:string,document_id:string):Promise<QualityPreview> { return unwrap(await callFrappePostMethod<DomainEnvelope<QualityPreview>>(method('preview_import'),{batch_id,document_id})) }
export async function uploadKnowledge(file:File,department:string,sharing:boolean,replace?:VersionTarget):Promise<{batch_id:string;relationship:string}> { const form=new FormData();form.append('file',file);form.append('department',department);form.append('sharing',sharing?'1':'0');if(replace){form.append('replace_document',replace.document_id);form.append('expected_version',replace.current_version||replace.version_id)}return unwrap(await callFrappeUploadMethod<DomainEnvelope<{batch_id:string;relationship:string}>>(method('upload_knowledge'),form)) }

// RC13 batch pipeline: preview -> submit -> fenced progress -> retrieval receipt.
export type BatchDisposition='NEW'|'DUPLICATE'|'BUSINESS_UPDATE'|'TECHNICAL_REPAIR'|'NEW_UPLOAD_REQUIRED'|'ANOMALY'
export interface BatchPageChecks { quality_pass?:boolean; visual_review?:{reviewer?:string;notes?:string;pages?:number[]}; sparse_pages?:number[]; gap_pages?:number[] }
export interface BatchPlanItem { index:number; source_sha256:string; disposition:BatchDisposition; submittable:boolean; conflict_reason:string|null; detail?:string|null; pages:number; page_methods:string[]; text_sha256?:string; document_id:string|null; version_id:string|null; expected_current_version:string|null; filename:string; title:string; department:string; target:{space_id:string;title:string;department:string}; evidence:{source_sha256:string;source_ref?:string;page_count?:number;text_sha256?:string;page_methods?:string[];page_checks?:BatchPageChecks;sharing_confirmed?:boolean} }
export interface BatchPlan { schema:string; plan_sha256:string; readonly:boolean; label:string|null; department:string|null; departments:string[]; sharing_confirmed:boolean; items:BatchPlanItem[]; counts:Record<string,number>; groups:{department:string;documents:number;jobs:number;duplicate_documents:number}[]; blocking_anomalies:number; submittable:boolean; next_action:string }
export interface BatchSubmitBatch { batch_id:string; department:string; documents:number; queued_documents:number; job_id:string|null; status:string; active_job:string|null; kind:'derivative'|'duplicate' }
export interface BatchSubmitReceipt { schema:string; plan_sha256:string; approval_ref:string; label:string; submitted_at:number; actor_hash:string; source_scope?:string; batches:BatchSubmitBatch[]; replayed:boolean }
export interface BatchRetrievalVerified { status:'PENDING'|'VERIFIED'|'INVALIDATED'; at?:number; query_sha256?:string|null; evidence_id_hash?:string|null; receipt_sha256?:string|null; reason?:string }
export interface BatchProgressItem { document_id:string; version_id:string; title:string; filename:string; department:string; status:string; progress:number; chunk_count:number; error_code:string|null; publication_status:string; retrieval_verified:BatchRetrievalVerified|null }
export interface BatchProgressJob { id:string|null; status:string|null; operation:string|null; lease_generation:number; lease_expires_at:number|null; lease_expired:boolean; pause_requested:boolean; requested_at:number|null; reclaims:number; document_ids:string[]; source_scope?:string }
export interface BatchProgress { schema:string; batch_id:string; label:string; department:string; status:string; last_error:string|null; job:BatchProgressJob|null; items:BatchProgressItem[]; total:number; page:number; limit:number; counts:{parsed:number;failed:number;queued:number;verified:number;invalidated:number} }
const batchMethod=(name:string)=>`hb_knowledge_app.hb_knowledge.maintenance_batch.${name}`
const batchMessages:Record<string,string>={BATCH_PLAN_BLOCKED:'预演清单仍有冲突或异常，请修正后重新预演。',BATCH_PLAN_STALE:'预演已过期或与当前资料状态不一致，请重新预演。',BATCH_DERIVATIVE_ROOT_UNCONFIGURED:'批量入库的派生文件共享目录尚未配置，提交未执行。',EVIDENCE_UNAVAILABLE:'服务端未核验到真实员工检索与来源解析记录，收据未写入。'}
function batchUnwrap<T>(value:DomainEnvelope<T>):T { if(!value.ok||value.data===undefined){const code=value.error?.code||'SERVICE_ERROR';throw new DomainApiError(code,batchMessages[code]||messages[code]||'维护服务暂不可用。',Boolean(value.error?.retryable))} return value.data }
export async function planImport(manifest:unknown):Promise<BatchPlan> { return batchUnwrap(await callFrappePostMethod<DomainEnvelope<BatchPlan>>(batchMethod('plan_import'),{manifest})) }
export async function submitImport(plan_sha256:string,approval_ref:string,label?:string):Promise<BatchSubmitReceipt> { return batchUnwrap(await callFrappePostMethod<DomainEnvelope<BatchSubmitReceipt>>(batchMethod('submit_import'),{plan_sha256,approval_ref,...(label?{label}:{})})) }
export async function getBatchProgress(batch_id:string,page=1,limit=20):Promise<BatchProgress> { return batchUnwrap(await callFrappeMethod<DomainEnvelope<BatchProgress>>(batchMethod('batch_progress'),{batch_id,page,limit})) }
export async function pauseImport(batch_id:string):Promise<{batch_id:string;status:string;pause_requested:boolean;note?:string}> { return batchUnwrap(await callFrappePostMethod<DomainEnvelope<{batch_id:string;status:string;pause_requested:boolean;note?:string}>>(batchMethod('pause_import'),{batch_id})) }
export async function resumeImport(batch_id:string):Promise<{batch_id:string;status:string;operation?:string}> { return batchUnwrap(await callFrappePostMethod<DomainEnvelope<{batch_id:string;status:string;operation?:string}>>(batchMethod('resume_import'),{batch_id})) }
export async function reclaimImport(batch_id:string,reason:string):Promise<{reclaimed:{batch_id:string;new_lease_generation:number}[];total:number}> { return batchUnwrap(await callFrappePostMethod<DomainEnvelope<{reclaimed:{batch_id:string;new_lease_generation:number}[];total:number}>>(batchMethod('reclaim_import'),{batch_id,reason})) }
