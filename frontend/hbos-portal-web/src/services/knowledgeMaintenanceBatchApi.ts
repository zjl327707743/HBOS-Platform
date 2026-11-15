import type { DomainEnvelope } from '@/contracts/p1'
import { callFrappeMethod, callFrappePostMethod, callFrappeUploadMethod } from './frappeClient'
import { DomainApiError,resolveKnowledgeEvidence } from './p1Api'
import { createDocumentDelivery } from './knowledgeDelivery'

const method=(name:string)=>`hb_knowledge_app.hb_knowledge.api.${name}`
function unwrap<T>(value:DomainEnvelope<T>):T {
  if(!value.ok||value.data===undefined)throw new DomainApiError(value.error?.code||'SERVICE_ERROR',
    value.error?.code==='QUALITY_REQUIRED'?'自动核验尚未通过，请先处理标出的异常。':'维护请求未完成，请保留当前结果后重试。')
  return value.data
}
export interface ManagedSpace {space_id:string;title:string;department:string;template:string;parent_space?:string}
export interface ManagedSample {source_page:number;literal:string;exact_index_match:boolean}
export interface ManagedRow {
  batch_id:string;document_id:string;version_id:string;title:string;filename:string;relative_path:string
  queue:'ORDINARY'|'COMPLEX';status:string;reasons:string[];quality_passed:boolean;publication_status:string
  expected_version:string|null;operation:'replace'|'publish';samples?:ManagedSample[];source_sha256:string;verification_intent?:string|null;resume_safe?:boolean
  validation_retry?:boolean
}
export interface ManagedPipeline {
  scope:string;items:ManagedRow[];total:number;normal_remaining:number;exceptions:number;awaiting_adoption:number
  available:number;batch_count:number;scan_truncated:boolean;net_available_per_hour:number|null;elapsed_seconds:number
  human_interventions:number;controller_continues_without_browser:boolean
}
export interface UploadPrecheck {items:{index:number;filename:string;relative_path:string;state:string;existing_documents:number}[];new:number;duplicates:number;blocked:number}
export interface UploadMetadata {filename:string;relative_path:string;source_sha256:string;bytes:number}
export interface ManagedTemplate {key:string;title:string;parser:string;parser_version:string;implementation_commit?:string;chunk_tokens:number;overlap_percent:number;table_context:number;image_context:number;embedding_model:string;embedding_dimensions:number;profile_sha256:string}
export async function getManagedSpaces(){return unwrap(await callFrappeMethod<DomainEnvelope<{can_manage_spaces:boolean;spaces:ManagedSpace[]}>>(method('get_maintenance_spaces')))}
export async function getManagedTemplates(){return unwrap(await callFrappeMethod<DomainEnvelope<{templates:ManagedTemplate[]}>>(method('get_maintenance_templates')))}
export async function getManagedPipeline(){return unwrap(await callFrappeMethod<DomainEnvelope<ManagedPipeline>>(method('get_maintenance_pipeline')))}
export async function precheckManagedUpload(items:UploadMetadata[],department:string){return unwrap(await callFrappePostMethod<DomainEnvelope<UploadPrecheck>>(method('precheck_knowledge_upload'),{items,department}))}
interface ManagedUploadItem {
  index:number; batch_id?:string; relationship?:string; status:'QUEUED'|'DUPLICATE'|'SOURCE_EXCEPTION'|'REPAIR_REQUIRED'
  job_id?:string|null; queue_error?:string|null
}
export async function uploadManagedGroup(items:{file:File;path:string}[],department:string,spaceId:string,workflowId:string){
  const form=new FormData()
  // Chromium otherwise serializes a directory-selected File with its relative
  // path as the multipart filename. The path is sent in its own field.
  for(const {file} of items)form.append('file',file,file.name)
  form.append('department',department)
  form.append('sharing','1')
  form.append('relative_paths',JSON.stringify(items.map(item=>item.path)))
  form.append('space_id',spaceId)
  form.append('workflow_id',workflowId)
  return unwrap(await callFrappeUploadMethod<DomainEnvelope<{items:ManagedUploadItem[];queued_jobs:number}>>(
    method('upload_knowledge'),form))
}
export async function inspectManagedSource(row:ManagedRow){return unwrap(await callFrappePostMethod<DomainEnvelope<{url:string;filename:string}>>(method('prepare_maintenance_source'),{batch_id:row.batch_id,document_id:row.document_id}))}
export async function createManagedSpace(title:string,source_space_id:string){return unwrap(await callFrappePostMethod<DomainEnvelope<{space_id:string}>>(method('create_knowledge_space'),{title,source_space_id}))}
export async function copyManagedTemplate(space_id:string,source_space_id:string){return unwrap(await callFrappePostMethod<DomainEnvelope<unknown>>(method('copy_knowledge_template'),{space_id,source_space_id}))}
export async function resumeManagedBatch(batch_id:string){return unwrap(await callFrappePostMethod<DomainEnvelope<unknown>>('hb_knowledge_app.hb_knowledge.maintenance_batch.resume_import',{batch_id}))}
export async function approveManagedRows(rows:ManagedRow[],note:string,workflowId:string){
  const first=rows[0]
  if(!first)return
  const pendingReview=rows.filter(row=>!row.quality_passed).map(row=>row.document_id)
  if(pendingReview.length)unwrap(await callFrappePostMethod<DomainEnvelope<unknown>>(method('review_import_batch'),{
    batch_id:first.batch_id,document_ids:pendingReview,checks:['text','numbers','tables','identity'],note,workflow_id:workflowId}))
  const pendingPublication=rows.filter(row=>row.publication_status!=='Published').map(row=>row.document_id)
  if(pendingPublication.length)unwrap(await callFrappePostMethod<DomainEnvelope<unknown>>(method('publish_import'),{
    batch_id:first.batch_id,document_ids:pendingPublication,operation:first.operation,
    ...(first.expected_version?{expected_version:first.expected_version,reason:note}:{}),workflow_id:workflowId}))
}

const compact=(text:string)=>text.normalize('NFKC').replace(/\s+/gu,'')
function contentCase(row:ManagedRow){
  const options=(row.samples||[]).filter(s=>s.exact_index_match&&compact(s.literal).length>=24
    && !compact(s.literal).startsWith(compact(row.title)))
    .sort((a,b)=>Number(/\d/.test(b.literal))-Number(/\d/.test(a.literal))||b.literal.length-a.literal.length)
  for(const sample of options){
    const literal=sample.literal.trim().normalize('NFC')
    const words=[...new Set(literal.match(/[a-zA-Z][a-zA-Z-]{3,}|[\u3400-\u9fff]{2,6}/g)||[])]
    if(words.length<3)continue
    const terms=words.slice(0,Math.min(5,words.length-1))
    const query=terms.join(' ')
    const anchor=compact(literal).slice(0,100)
    if(terms.length>=2&&!compact(query).includes(anchor)&&!compact(query).includes(compact(row.title)))return{query,anchor}
  }
  throw new Error('尚无可自动核验的原件内容见证，请在任务详情核对。')
}

export async function verifyManagedReader(row:ManagedRow){
  const {query,anchor}=contentCase(row)
  const queryHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(query))))
    .map(x=>x.toString(16).padStart(2,'0')).join('')
  const identity={batch_id:row.batch_id,document_id:row.document_id,version_id:row.version_id,query_sha256:queryHash}
  const intent=unwrap(await callFrappePostMethod<DomainEnvelope<{status:string;request_id?:string}>>(
    method('begin_maintenance_reader_check'),identity))
  if(intent.status==='ALREADY_VERIFIED')return
  if(intent.status!=='READY'||!intent.request_id)throw new Error('上次查阅请求待对账，未重复发起。')
  const search=unwrap(await callFrappePostMethod<DomainEnvelope<{results:{document_id:string;excerpt:string;evidence_id:string}[]}>>(
    method('search'),{query,limit:5,search_mode:'STANDARD'},{'X-HBOS-Request-ID':intent.request_id}))
  const hit=search.results.find(r=>r.document_id===row.document_id&&compact(r.excerpt).includes(anchor))
  if(!hit)throw new Error('普通检索前五条未同时匹配资料与原件内容，待修复检索。')
  const source=await resolveKnowledgeEvidence(hit.evidence_id)
  if(source.document_id!==row.document_id||!compact(source.excerpt).includes(anchor))throw new Error('引用未能复开同一资料内容。')
  const opened=unwrap(await callFrappePostMethod<DomainEnvelope<{document:{document_id:string;version_id:string};body:{blocks:unknown[]}}>>(
    method('open_document'),{document_id:row.document_id,version_id:row.version_id}))
  if(opened.document.document_id!==row.document_id||opened.document.version_id!==row.version_id||!opened.body.blocks.length)
    throw new Error('正文未能打开当前版本。')
  for(const purpose of ['preview','download'] as const){
    const asset=await createDocumentDelivery(row.document_id,row.version_id,purpose)
    if(purpose==='download'&&asset.sha256!==row.source_sha256)throw new Error('原件校验不一致。')
    const response=await fetch(asset.content_url,{credentials:'same-origin',cache:'no-store',headers:{Range:'bytes=0-7'}})
    if(response.status!==206||!response.headers.get('Content-Range'))throw new Error('未取得已核验原件字节。')
    const bytes=await response.arrayBuffer()
    if(!bytes.byteLength||(purpose==='preview'&&!new TextDecoder().decode(bytes).startsWith('%PDF-')))
      throw new Error('原文预览内容未通过核验。')
  }
  const proof=unwrap(await callFrappePostMethod<DomainEnvelope<{receipt:{status:string;reader_paths_verified:boolean}}>>(
    'hb_knowledge_app.hb_knowledge.maintenance_batch.record_retrieval_verified',{...identity,evidence_id:hit.evidence_id}))
  if(proof.receipt.status!=='VERIFIED'||proof.receipt.reader_paths_verified!==true)throw new Error('查阅回执未完成。')
}
