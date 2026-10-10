import type { DomainEnvelope } from '@/contracts/p1'
import { callFrappeMethod, callFrappePostMethod, callFrappeUploadMethod } from './frappeClient'
import { DomainApiError } from './p1Api'
export interface ImportItem { document_id:string; version_id:string; title:string; filename:string; sha256:string; relationship:string; expected_version:string|null; parse_status:string; progress:number; chunk_count:number; quality_status:string; quality_note:string; current_version:string|null; publication_status:string }
export interface ImportBatch { batch_id:string; label:string; department:string; status:string; last_error:string|null; items:ImportItem[]; total:number; page:number; page_size:number; counts:{parsed:number;failed:number;quality_passed:number} }
export interface MaintenanceFeedback { id:string; category:string; note:string; status:string; reply?:string; maintenance_reply?:string; title?:string }
export interface VersionTarget { document_id:string; version_id:string; current_version:string; title:string; department:string }
export interface MaintenanceDashboard { published_documents:VersionTarget[]; departments:{key:string;title:string}[]; batches:{name:string;label:string;department_key:string;status:string}[]; selected:ImportBatch|null; feedback:{items:MaintenanceFeedback[]}; import_availability:{can_parse:boolean;configured:boolean;blocked:boolean} }
export interface QualityPreview { title:string; fragments:{text:string;location:string}[]; chunk_count:number; source_sha256:string; version_id:string }
const method=(name:string)=>`hb_knowledge_app.hb_knowledge.api.${name}`
const messages:Record<string,string>={SCOPE_REJECTED:'当前账号没有知识维护权限。',AUTHENTICATION_REQUIRED:'登录已失效，请重新登录。',INVALID_REQUEST:'文件或操作无效，请核对格式、大小和当前状态。',IDENTITY_CONFLICT:'身份或当前版本冲突，请选择明确的换版关系。',IMPORT_BUSY:'该批次正在处理，请等待本次完成。',QUALITY_REQUIRED:'请先完成本版本的质量核对。',IMPORT_BUDGET_BLOCKED:'解析费用待核验或预算不可用，解析已暂停。'}
function unwrap<T>(value:DomainEnvelope<T>):T { if(!value.ok||value.data===undefined) { const code=value.error?.code||'SERVICE_ERROR';throw new DomainApiError(code,messages[code]||'维护服务暂不可用。',Boolean(value.error?.retryable)) } return value.data }
export async function getMaintenance(batch_id?:string,page=1):Promise<MaintenanceDashboard> { return unwrap(await callFrappeMethod<DomainEnvelope<MaintenanceDashboard>>(method('get_maintenance'),{batch_id,page,page_size:12})) }
export async function maintenanceAction(name:string,args:Record<string,unknown>):Promise<unknown> { return unwrap(await callFrappePostMethod<DomainEnvelope<unknown>>(method(name),args)) }
export async function getMaintenanceFeedbackPage(page=1,status=''):Promise<{items:MaintenanceFeedback[];page:number;page_size:number;has_more:boolean}> {
  const data=unwrap(await callFrappeMethod<DomainEnvelope<{items:MaintenanceFeedback[];page:number;page_size:number;has_more:boolean}>>(method('get_feedback_queue'),{page,page_size:6,status}))
  if(!Array.isArray(data.items)||data.items.length>6||data.page!==page||data.page_size!==6||typeof data.has_more!=='boolean')throw new DomainApiError('SERVICE_ERROR','反馈分页响应无效。')
  return data
}
export async function previewImport(batch_id:string,document_id:string):Promise<QualityPreview> { return unwrap(await callFrappePostMethod<DomainEnvelope<QualityPreview>>(method('preview_import'),{batch_id,document_id})) }
export async function uploadKnowledge(file:File,department:string,sharing:boolean,replace?:VersionTarget):Promise<{batch_id:string;relationship:string}> { const form=new FormData();form.append('file',file);form.append('department',department);form.append('sharing',sharing?'1':'0');if(replace){form.append('replace_document',replace.document_id);form.append('expected_version',replace.current_version||replace.version_id)}return unwrap(await callFrappeUploadMethod<DomainEnvelope<{batch_id:string;relationship:string}>>(method('upload_knowledge'),form)) }
