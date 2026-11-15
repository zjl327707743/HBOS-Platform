const titles=['培养箱使用与日常检查指南','岗位安全培训资料索引','文件版本与引用核对指南','生产现场交接记录说明','新员工入职培训手册','合成资料版本维护流程','合成资料审批指引','合成资料归档流程','合成资料校验说明','合成培训材料','合成设备操作指南','合成记录维护手册']
const rows=titles.map((title,i)=>({document_id:'DOC_SYNTHETIC_'+i,version_id:'V0'+(i%4+1),current_version:'V0'+(i%4+1),title,department:'production',document_number:'DEMO-'+String(i+1).padStart(3,'0')}))
let operations=0, paused=false
const rowsAsItems=rows.map((row,i)=>({document_id:row.document_id,version_id:row.version_id,current_version:row.current_version,title:row.title,filename:row.title+'.pdf',sha256:'synthetic-sha',relationship:'NEW',expected_version:null,parse_status:'parsed/indexed',progress:1,chunk_count:8,quality_status:'Passed',shared_approved:true,quality_note:'',publication_status:'Published',lifecycle_receipt_id:'REC_SYNTHETIC_'+i}))
const pending={document_id:'DOC_SYNTHETIC_PENDING',version_id:'V_PENDING_1',current_version:'V_PENDING_1',title:'合成待核对资料',filename:'合成待核对资料.pdf',relationship:'NEW',parse_status:'parsed/indexed',quality_status:'Pending',quality_note:'',shared_approved:false,publication_status:'Unpublished',progress:1,chunk_count:3}
const visualSeeds = [
  ['培养箱使用与日常检查指南', 'quality', 'DEMO-QC-018', '03'],
  ['岗位安全培训资料索引', 'safety', 'DEMO-EHS-002', '02'],
  ['文件版本与引用核对指南', 'quality', 'DEMO-QA-006', '04'],
  ['生产现场交接记录说明', 'production', 'DEMO-PRD-014', '02'],
  ['新员工入职培训手册', 'hr', 'DEMO-HR-001', '05'],
  ['设备图纸查阅与归档指引', 'production', 'DEMO-EQ-009', '01'],
  ['无菌车间资料使用指引', 'production', 'DEMO-PRD-021', '02'],
  ['药品监管规范条目（演示）', 'law', 'DEMO-LAW-001', '01'],
  ['环保合规资料目录（演示）', 'law', 'DEMO-LAW-002', '01'],
  ['培训记录归档说明', 'hr', 'DEMO-HR-009', '02'],
  ['公共标准条目（演示）', 'law', 'DEMO-LAW-003', '01'],
  ['设备资料索引清单', 'production', 'DEMO-EQ-016', '01'],
]
const visualRows = visualSeeds.map((seed, index) => ({
  document_id: 'DOC_DEMO_' + String(index + 1).padStart(3, '0'),
  version_id: 'V0' + seed[3], current_version: '0' + seed[3], title: seed[0],
  department: seed[1], document_number: seed[2],
}))
for (let n = 13; n <= 27; n++) {
  const base = visualRows[(n - 13) % 7]
  visualRows.push({ ...base, document_id: 'DOC_DEMO_' + String(n).padStart(3, '0'),
    title: base.title.replace(/指南|说明|索引|手册|指引/, '相关记录') + ' · 示例 ' + (n - 12),
    document_number: 'DEMO-REF-' + String(n).padStart(3, '0') })
}
const visualDepartments = [
  { key: 'quality', title: '质量管理部' }, { key: 'safety', title: '安全部门' },
  { key: 'production', title: '生产部门' }, { key: 'hr', title: '人事部门' }, { key: 'law', title: '公共法规' },
]
export async function getMaintenance(batch,page=1,_locate,lookup,state='success'){
  const visual=state==='visual'
  const baseRows=visual?visualRows:rows
  let docs=state==='empty'?[]:baseRows
  if(lookup?.published_query)docs=docs.filter(row=>`${row.title} ${row.document_number}`.includes(lookup.published_query))
  if(lookup?.published_document_id)docs=docs.filter(row=>row.document_id===lookup.published_document_id)
  const detailLookup=Boolean(_locate||lookup?.batch_document_id)
  const selectedItems=detailLookup?rowsAsItems:[pending]
  const selected=batch?{batch_id:batch==='MOCK_BATCH'?'MOCK_BATCH':batch,label:'合成批次',department:'production',status:'Ready',last_error:null,items:selectedItems,total:selectedItems.length,page:1,page_size:12,counts:{parsed:selectedItems.length,failed:0,quality_passed:selectedItems.filter(i=>i.quality_status==='Passed').length}}:null
  const truncated=state==='truncated'
  return {departments:visual?visualDepartments:[{key:'production',title:'合成部门'}],published_documents:docs,published_total:baseRows.length,published_matched:docs.length,published_page:lookup?.published_page||page,published_page_size:truncated?1000:50,published_truncated:truncated,published_has_more:false,published_lookup_state:lookup?.published_document_id?(docs.length?'FOUND':'NOT_FOUND'):null,batches:[{name:'MOCK_BATCH',label:'合成批次',department_key:'production',status:'Ready'}],selected,import_availability:{can_parse:true,can_batch:true,configured:true,blocked:false},department_funnel:[],feedback:{items:[]}}
}
export async function getVersionLineage(documentId,state='success'){
  const visual=state==='visual'
  const target=(visual?visualRows:rows).find(row=>row.document_id===documentId)||(visual?visualRows:rows)[0]
  const current=target.current_version||'V01'
  return {document_id:target.document_id,current_version:current,versions:[
    {version_id:current,enabled:true,created_at:'2026-11-10T09:00:00+08:00',source_hash:'synthetic-current',publication_state:'PUBLISHED',quality_state:'VERIFIED',rollback_eligible:false,superseded_by:null,supersedes:'V02'},
    {version_id:'V02',enabled:true,created_at:'2026-09-18T09:00:00+08:00',source_hash:'synthetic-prior',publication_state:'HISTORICAL',quality_state:'VERIFIED',rollback_eligible:true,superseded_by:current,supersedes:'V01'},
    {version_id:'V01',enabled:true,created_at:'2026-06-02T09:00:00+08:00',source_hash:'synthetic-origin',publication_state:'HISTORICAL',quality_state:'NOT_RECORDED',rollback_eligible:false,superseded_by:'V02',supersedes:null},
  ],total:3,page:1,page_size:12,has_more:false}
}

export async function previewImport(){return {title:pending.title,fragments:[{text:'这是一段仅供视觉核对的合成文本。',location:'示例片段'}],chunk_count:1,source_sha256:'demo',version_id:pending.version_id}}
export async function maintenanceAction(name){if(name==='queue_import')pending.parse_status='parsed/indexed';if(name==='review_import'||name==='review_import_batch')pending.quality_status='Passed';if(name==='approve_import_sharing')pending.shared_approved=true;if(name==='publish_import')pending.publication_status='Published';return {batch_id:'MOCK_BATCH'}}
export async function uploadKnowledge(file){pending.title=file.name;pending.filename=file.name;pending.parse_status='uploaded';pending.quality_status='Pending';pending.shared_approved=true;pending.publication_status='Unpublished';return {batch_id:'MOCK_BATCH',relationship:'NEW'}}
export async function planImport(manifest){const items=(manifest.items||[]).slice(0,64).map((it,index)=>({index,title:it.title||`合成条目 ${index+1}`,filename:it.title||'合成文件',department:'production',target:{title:'合成空间'},pages:1,page_methods:['文本'],disposition:index===1?'DUPLICATE':'NEW',submittable:true,conflict_reason:null}));return {schema:'MOCK',plan_sha256:'SYNTHETIC_PLAN',readonly:true,label:'合成批次',department:'production',departments:['production'],sharing_confirmed:true,items,counts:{total:items.length,new:Math.max(0,items.length-1),duplicate:Math.min(1,items.length)},groups:[],blocking_anomalies:0,submittable:items.length>0,next_action:'submit'}}
export async function submitImport(plan_sha256,approval_ref,label){operations++;return {schema:'MOCK',plan_sha256,approval_ref,label:label||'合成批次',submitted_at:Date.now(),actor_hash:'SYNTHETIC',replayed:operations>1,batches:[{batch_id:'MOCK_BATCH',department:'production',documents:1,queued_documents:1,status:'Queued',kind:'derivative'}]}}
export async function getBatchProgress(){return {schema:'MOCK',batch_id:'MOCK_BATCH',label:'合成批次',department:'production',status:paused?'Paused':'Ready',last_error:null,job:{id:'MOCK_JOB',status:paused?'Paused':'Ready',operation:'parse',lease_generation:1,lease_expires_at:null,lease_expired:false,pause_requested:false,requested_at:null,reclaims:0,document_ids:[pending.document_id]},items:[],total:0,page:1,limit:20,counts:{parsed:0,failed:0,queued:0,verified:0,invalidated:0}}}
export async function pauseImport(){paused=true;return {batch_id:'MOCK_BATCH',status:'Paused',pause_requested:false}}
export async function resumeImport(){paused=false;return {batch_id:'MOCK_BATCH',status:'Ready'}}
export async function reclaimImport(){return {reclaimed:[],total:0}}
