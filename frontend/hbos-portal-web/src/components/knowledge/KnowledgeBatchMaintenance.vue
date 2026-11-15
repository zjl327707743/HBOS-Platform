<script setup lang="ts">
import PortalSelect from '@/components/portal/PortalSelect.vue'
import KnowledgeDisclosureSummary from '@/components/knowledge/KnowledgeDisclosureSummary.vue'
import {computed,onBeforeUnmount,onMounted,ref,watch} from 'vue'
import {approveManagedRows,copyManagedTemplate,createManagedSpace,getManagedPipeline,getManagedSpaces,getManagedTemplates,
  inspectManagedSource,precheckManagedUpload,resumeManagedBatch,uploadManagedGroup,verifyManagedReader,type ManagedPipeline,type ManagedRow,type ManagedSpace,type ManagedTemplate} from '@/services/knowledgeMaintenanceBatchApi'

const props=defineProps<{sessionRevision?:number}>()
const emit=defineEmits<{
  (e:'select-batch',id:string):void
  (e:'select-version',row:ManagedRow):void
}>()
interface Picked {file:File;path:string;sha?:string;state:string;attempted:boolean;error?:string}
const spaces=ref<ManagedSpace[]>([]),templates=ref<ManagedTemplate[]>([]),spaceId=ref(''),canManage=ref(false)
const files=ref<Picked[]>([]),sharing=ref(false),prepared=ref(false),busy=ref(false),error=ref(''),notice=ref(''),progress=ref('')
const pipeline=ref<ManagedPipeline|null>(null),selected=ref<string[]>([]),confirmed=ref(false),note=ref('')
const spaceTitle=ref(''),sourceSpace=ref('')
let epoch=0,polling=false,timer:ReturnType<typeof setInterval>|null=null
const target=computed(()=>spaces.value.find(s=>s.space_id===spaceId.value))
const key=(r:ManagedRow)=>r.batch_id+':'+r.document_id
const workflow=()=>Array.from(crypto.getRandomValues(new Uint8Array(16))).map(x=>x.toString(16).padStart(2,'0')).join('')
const ready=computed(()=>pipeline.value?.items.filter(r=>r.status==='READY_FOR_ADOPTION')||[])
const verifyReady=computed(()=>pipeline.value?.items.filter(r=>r.status==='PUBLISHED_RETRIEVAL_PENDING'&&!r.verification_intent)||[])
const chosen=computed(()=>ready.value.filter(r=>selected.value.includes(key(r))))
const sampleRows=computed(()=>chosen.value.slice(0,5))
const sent=computed(()=>files.value.filter(f=>f.state==='已接收'||f.state==='重复复用').length)
function fail(e:unknown){error.value=e instanceof Error?e.message:'维护请求未完成，请检查任务记录。'}
// MC-6 (Main decision ERROR_CONTRACT_IS_SCOPE_REJECTED_POLICY_UNAVAILABLE_INVALID_REQUEST):
// knowledge-space create/copy failures are terminal domain codes. Map the three codes to the
// existing error surface and never retry automatically; unknown errors keep the old message.
const spaceActionErrors:Record<string,string>={
  SCOPE_REJECTED:'当前账号无权执行该知识空间操作（SCOPE_REJECTED）；不会自动重试。',
  POLICY_UNAVAILABLE:'该知识空间操作当前不可用（POLICY_UNAVAILABLE）；不会自动重试。',
  INVALID_REQUEST:'知识空间操作请求无效（INVALID_REQUEST）；请核对后重试。',
}
function failSpaceAction(e:unknown){const code=e&&typeof e==='object'&&'code' in e?(e as {code?:unknown}).code:undefined;if(typeof code==='string'&&spaceActionErrors[code]){error.value=spaceActionErrors[code];return}fail(e)}
function clear(){files.value=[];spaces.value=[];templates.value=[];spaceId.value='';pipeline.value=null;selected.value=[];confirmed.value=false;sharing.value=false;prepared.value=false;note.value='';spaceTitle.value='';sourceSpace.value='';progress.value='';notice.value='';error.value='';busy.value=false;canManage.value=false}
async function refresh(){if(polling)return;const current=epoch;polling=true;try{const p=await getManagedPipeline();if(current===epoch){pipeline.value=p;selected.value=selected.value.filter(k=>p.items.some(r=>key(r)===k&&r.status==='READY_FOR_ADOPTION'))}}catch(e){if(current===epoch)fail(e)}finally{polling=false}}
async function load(){const current=epoch;try{const [s,t]=await Promise.all([getManagedSpaces(),getManagedTemplates()]);if(current!==epoch)return;spaces.value=s.spaces;canManage.value=s.can_manage_spaces;templates.value=t.templates;spaceId.value=s.spaces[0]?.space_id||'';sourceSpace.value=spaceId.value;await refresh()}catch(e){if(current===epoch)fail(e)}}
function pick(event:Event){if(busy.value)return;const input=event.target as HTMLInputElement;files.value=Array.from(input.files||[]).map(file=>({file,path:file.webkitRelativePath||file.name,state:'待预检',attempted:false}));input.value='';prepared.value=false;sharing.value=false;notice.value='';error.value=''}
watch(spaceId,()=>{if(!busy.value){prepared.value=false;sharing.value=false}})
async function precheck(){if(!target.value||busy.value||!files.value.length)return;const current=epoch;busy.value=true;prepared.value=false;error.value='';try{
  const department=target.value.department,valid:Picked[]=[]
  for(const [i,row] of files.value.entries()){
    if(current!==epoch)return;progress.value=`正在核对源文件 ${i+1}/${files.value.length}`
    if(row.file.size>64*1024*1024||row.file.size===0){row.state='需单独处理';row.error='空文件或超过普通上传上限';continue}
    const bytes=await row.file.arrayBuffer();if(current!==epoch)return
    row.sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');valid.push(row)
  }
  for(let offset=0;offset<valid.length;offset+=50){
    const chunk=valid.slice(offset,offset+50)
    const result=await precheckManagedUpload(chunk.map(r=>({filename:r.file.name,relative_path:r.path,source_sha256:r.sha!,bytes:r.file.size})),department)
    if(current!==epoch)return
    for(const resultRow of result.items){const row=chunk[resultRow.index];if(row)row.state=resultRow.state==='SOURCE_EXCEPTION'?'格式或路径需单独处理':resultRow.state==='IDENTITY_REVIEW'?'身份待核查':resultRow.state==='DUPLICATE'?'重复待复用':'可导入'}
  }
  prepared.value=true;progress.value='预检完成；本地目录层级会保留。'
}catch(e){if(current===epoch)fail(e)}finally{if(current===epoch)busy.value=false}}
async function submit(){
  if(!prepared.value||!sharing.value||!target.value||busy.value)return
  const current=epoch,space=target.value,operation=workflow()
  const packets:Picked[][]=[]
  let packet:Picked[]=[]
  let bytes=0
  for(const row of files.value.filter(f=>!f.attempted&&['可导入','重复待复用'].includes(f.state))){
    if(packet.length&&(packet.length===4||bytes+row.file.size>64*1024*1024)){
      packets.push(packet);packet=[];bytes=0
    }
    packet.push(row);bytes+=row.file.size
  }
  if(packet.length)packets.push(packet)
  busy.value=true;error.value=''
  let last=''
  try{
    for(const [index,group] of packets.entries()){
      if(current!==epoch)return
      for(const row of group){row.attempted=true;row.state='正在上传'}
      progress.value=`正在提交第 ${index+1}/${packets.length} 组，共 ${group.length} 份`
      try{
        const result=await uploadManagedGroup(group,space.department,space.space_id,operation)
        if(current!==epoch)return
        if(result.items.length!==group.length||new Set(result.items.map(item=>item.index)).size!==group.length
          ||result.items.some(item=>!group[item.index]))throw new Error('后台接收回执不完整，请核对任务。')
        for(const item of result.items){
          const row=group[item.index]!
          if(item.status==='DUPLICATE')row.state='重复复用'
          else if(item.status==='QUEUED')row.state='已接收'
          else if(item.status==='REPAIR_REQUIRED'){
            row.state='已接收';row.error='文件已保存，自动处理暂缓；详情保留在任务中。'
          }else{
            row.state='需单独处理';row.error=reasons[item.queue_error||'']||'请核对来源、格式或版本关系。'
          }
          if(item.batch_id)last=item.batch_id
        }
      }catch(e){
        if(current!==epoch)return
        for(const row of group){
          row.state='请求待核验'
          row.error=e instanceof Error?e.message:'请在后台任务中核查接收结果。'
        }
      }
    }
    notice.value=`已确认接收或复用 ${sent.value}/${files.value.length} 份。已接收文件由后台继续处理，待核验和异常项保留在清单中。`
    progress.value=''
    if(last)emit('select-batch',last)
    await refresh()
  }finally{if(current===epoch)busy.value=false}
}
function toggle(r:ManagedRow,event:Event){const checked=(event.target as HTMLInputElement).checked;selected.value=checked?[...new Set([...selected.value,key(r)])]:selected.value.filter(k=>k!==key(r));confirmed.value=false}
async function inspect(row:ManagedRow){
  const popup=window.open('about:blank','_blank')
  if(!popup){error.value='浏览器拦截了原件窗口，请允许弹出窗口后重试。';return}
  popup.opener=null
  try{
    const result=await inspectManagedSource(row)
    const url=new URL(result.url,window.location.origin)
    if(url.origin!==window.location.origin)throw new Error('原件地址不可用。')
    popup.location.replace(url.href)
  }catch(e){popup.close();fail(e)}
}
async function resume(row:ManagedRow){if(!row.resume_safe||busy.value)return;busy.value=true;try{await resumeManagedBatch(row.batch_id);notice.value=row.validation_retry?'已排队核验现有结果。':'已接续既有任务，保留已确认结果。';await refresh()}catch(e){fail(e)}finally{busy.value=false}}
async function approve(){
  const reviewNote=note.value.trim()
  if(!chosen.value.length||!confirmed.value||reviewNote.length<3||busy.value)return
  const current=epoch,rows=[...chosen.value],operation=workflow()
  const cohorts=new Map<string,ManagedRow[]>()
  for(const row of rows){
    const group=row.operation==='publish'?row.batch_id:key(row)
    const selected=cohorts.get(group)||[]
    selected.push(row);cohorts.set(group,selected)
  }
  busy.value=true;error.value=''
  let adopted=0
  const failures:string[]=[]
  try{
    for(const [index,group] of [...cohorts.values()].entries()){
      if(current!==epoch)return
      progress.value=`核查发布 ${index+1}/${cohorts.size} 组，共 ${group.length} 份`
      try{await approveManagedRows(group,reviewNote,operation);adopted+=group.length}
      catch(error){failures.push(group.map(row=>row.filename).join('、')+'：'+(error instanceof Error?error.message:'结果待核验'))}
    }
    if(current!==epoch)return
    notice.value=`发布已确认 ${adopted}/${rows.length} 份。${failures.length?'其余项待处理；已确认项保留。':'员工检索可用状态另行核验。'}`
    error.value=failures.join('\n');confirmed.value=false;await refresh()
  }finally{if(current===epoch){busy.value=false;progress.value=''}}
}
async function verifyPublished(){if(!verifyReady.value.length||busy.value)return;const current=epoch,rows=[...verifyReady.value];busy.value=true;let verified=0;const failed:string[]=[];try{
  for(const [i,row] of rows.entries()){if(current!==epoch)return;progress.value=`正在核验员工查阅 ${i+1}/${rows.length}`;try{await verifyManagedReader(row);verified++}catch(e){failed.push(row.filename+'：'+(e instanceof Error?e.message:'查阅结果待核查'))}}
  if(current!==epoch)return;notice.value=`检索、引用、正文与原件核验通过 ${verified}/${rows.length} 份。`;error.value=failed.join('\n');await refresh()
}finally{if(current===epoch){busy.value=false;progress.value=''}}}
async function createSpace(){if(!spaceTitle.value.trim()||!sourceSpace.value||busy.value)return;const current=epoch;busy.value=true;try{const result=await createManagedSpace(spaceTitle.value.trim(),sourceSpace.value);if(current!==epoch)return;await load();if(current!==epoch)return;spaceId.value=result.space_id;spaceTitle.value='';notice.value='知识空间已创建，沿用标准模板与既有写入库。'}catch(e){if(current===epoch)failSpaceAction(e)}finally{if(current===epoch)busy.value=false}}
async function copyTemplate(){if(!spaceId.value||!sourceSpace.value||busy.value)return;const current=epoch;busy.value=true;try{await copyManagedTemplate(spaceId.value,sourceSpace.value);if(current!==epoch)return;await load();notice.value='模板已复制，仅作用于后续新资料。'}catch(e){if(current===epoch)failSpaceAction(e)}finally{if(current===epoch)busy.value=false}}
const labels:Record<string,string>={AVAILABLE:'检索可用',WITHDRAWN:'已撤回',SUPERSEDED:'已被新版替换',READY_FOR_ADOPTION:'待核查发布',PUBLISHED_RETRIEVAL_PENDING:'已发布，待检索验证',REPAIR_REQUIRED:'待修复',RECONCILIATION_REQUIRED:'请求待对账',REVALIDATING:'正在核验现有结果',planned:'待解析',uploaded:'已上传',parse_queued:'处理中','parsed/indexed':'解析完成',quarantined:'需核查',parse_failed:'解析异常'}
const reasons:Record<string,string>={SOURCE_TEXT_OR_NUMBER_COVERAGE_REPAIR:'正文或数字覆盖需修复',ORIGINAL_TABLE_RELATION_REVIEW:'表格关系需核验',ORIGINAL_IMAGE_OR_SCAN_REVIEW:'图示或扫描页需核验',SCANNED_OR_BLANK_PAGE_REVIEW:'扫描或空白页需确认',AUTOMATIC_LIST_NUMBERING_REVIEW:'自动编号需核验',SUPPLEMENTAL_OFFICE_PARTS_REVIEW:'页眉、注释等附属内容需核验',AUTOMATIC_VALIDATION_UNAVAILABLE:'自动核验未完成',SOURCE_CONVERSION_REQUIRED:'原格式需受控转换'}
onMounted(()=>{void load();timer=setInterval(()=>void refresh(),8000)})
watch(()=>props.sessionRevision,()=>{epoch++;clear();void load()})
onBeforeUnmount(()=>{epoch++;if(timer)clearInterval(timer);clear()})
</script>

<template>
  <section class="kb-panel hbos-glass-g1 managed-batch" aria-labelledby="managed-batch-title">
    <h2 id="managed-batch-title">批量导入与日常维护</h2>
    <p class="muted">选择文件或文件夹，先检查重复与版本关系，再连续处理。已接收的后台任务在关闭页面后继续运行。</p>
    <p v-if="error" role="alert" class="error">{{error}}</p><p v-if="notice" role="status">{{notice}}</p><p v-if="progress" role="status">{{progress}}</p>
    <fieldset :disabled="busy"><legend>资料归属与文件</legend>
      <label>知识空间<PortalSelect v-model:value="spaceId" aria-label="批量导入知识空间" :options="spaces.map(space => ({ value: space.space_id, label: space.title }))" /></label>
      <div class="actions"><label class="file-pick">选择多个文件<input type="file" multiple aria-label="选择批量资料文件" @change="pick"/></label><label class="file-pick">选择文件夹<input type="file" webkitdirectory multiple aria-label="选择资料文件夹" @change="pick"/></label></div>
      <p v-if="files.length">已选 {{files.length}} 份，已确认接收或复用 {{sent}} 份。</p>
      <ul v-if="files.length" class="file-list"><li v-for="(row,i) in files" :key="i"><span>{{row.path}}</span><span>{{row.state}}</span><small v-if="row.error" class="error">{{row.error}}</small></li></ul>
      <div class="actions"><button type="button" :disabled="!files.length||!target" @click="precheck">检查重复与目录</button><label class="check"><input v-model="sharing" type="checkbox"/>已确认所选资料获准内部共享</label><button type="button" :disabled="!prepared||!sharing||!target" @click="submit">批量上传并自动处理</button></div>
    </fieldset>
    <div v-if="pipeline" class="metrics" aria-label="后台批处理指标"><div><strong>{{pipeline.normal_remaining}}</strong><span>正常剩余</span></div><div><strong>{{pipeline.exceptions}}</strong><span>异常待修</span></div><div><strong>{{pipeline.awaiting_adoption}}</strong><span>待采用</span></div><div><strong>{{pipeline.net_available_per_hour ?? '待测'}}</strong><span>净可用 / 小时</span></div><div><strong>{{pipeline.human_interventions}}</strong><span>人工介入</span></div></div>
    <p class="muted">此处统计维护页已接收的任务；解析、发布与检索可用分别记录。</p>
    <div class="actions"><button type="button" :disabled="busy" @click="refresh">刷新后台任务</button><button v-if="ready.length" type="button" :disabled="busy" @click="selected=ready.slice(0,50).map(key);confirmed=false">选择前 50 份合格资料</button><button v-if="verifyReady.length" type="button" :disabled="busy" @click="verifyPublished">批量验证员工查阅</button></div>
    <ul v-if="pipeline?.items.length" class="jobs"><li v-for="row in pipeline.items" :key="key(row)"><label v-if="row.status==='READY_FOR_ADOPTION'"><input type="checkbox" :checked="selected.includes(key(row))" :disabled="busy" :aria-label="'选择采用 '+row.title" @change="toggle(row,$event)"/></label><div><strong>{{row.title}}</strong><p class="muted">{{row.relative_path}}</p><span>{{row.queue==='COMPLEX'?'复杂资料支线':'普通资料'}} · {{labels[row.status]||'等待状态核对'}}</span><p v-for="reason in row.reasons" :key="reason" class="error">{{reasons[reason]||'处理证据待核查，请查看任务详情'}}</p></div><button v-if="row.resume_safe" type="button" :disabled="busy" @click="resume(row)">{{row.validation_retry?'重新核验已有结果':'接续处理'}}</button><button v-if="['AVAILABLE','WITHDRAWN','PUBLISHED_RETRIEVAL_PENDING'].includes(row.status)" type="button" :disabled="busy" @click="emit('select-version',row)">资料版本</button><button v-else type="button" :disabled="busy" @click="emit('select-batch',row.batch_id)">任务详情</button></li></ul>
    <section v-if="chosen.length" class="review" aria-label="批量核查发布"><h3>核查 {{chosen.length}} 份资料</h3><p>自动核验已覆盖全文和数字。请抽查以下 {{sampleRows.length}} 份原件，再确认发布；发现问题时保留待修。</p><article v-for="row in sampleRows" :key="key(row)"><strong>{{row.title}}</strong><button type="button" :disabled="busy" @click="inspect(row)">查看原件</button><blockquote v-for="(sample,i) in row.samples" :key="i">第 {{sample.source_page}} 个原件内容单元：{{sample.literal}} <small>{{sample.exact_index_match?'与索引一致':'需核查'}}</small></blockquote></article><label class="check"><input v-model="confirmed" type="checkbox" :disabled="busy"/>已核对抽查原件的正文、数字、结构及版本关系</label><label>核查说明<textarea v-model="note" maxlength="500" :disabled="busy" placeholder="记录抽查结果或换版原因，至少三个字"/></label><button type="button" :disabled="busy||!confirmed||note.trim().length<3" @click="approve">批量核查并发布</button></section>
    <details><KnowledgeDisclosureSummary>已固定的资料模板</KnowledgeDisclosureSummary><p class="muted">每份文档实际生效的设置和解析记录见任务详情。</p><article v-for="template in templates" :key="template.key"><strong>{{template.title}}</strong><p>{{template.parser}} · 切块 {{template.chunk_tokens}} Token · Overlap {{template.overlap_percent}}% · 表格上下文 {{template.table_context}} · 图像上下文 {{template.image_context}}</p><p>Embedding {{template.embedding_model}} / {{template.embedding_dimensions}} 维</p><p v-if="template.implementation_commit">RAGFlow <code>{{template.implementation_commit}}</code></p></article></details>
    <details v-if="canManage"><KnowledgeDisclosureSummary>管理：知识空间与模板</KnowledgeDisclosureSummary><p class="muted">标准空间沿用已有写入库与共享角色；新增分类无需创建新的物理资料库。</p><label>模板来源<PortalSelect v-model:value="sourceSpace" aria-label="模板来源" :options="spaces.map(space => ({ value: space.space_id, label: space.title }))" /></label><label>新空间名称<input v-model="spaceTitle" maxlength="120" :disabled="busy"/></label><div class="actions"><button type="button" :disabled="busy||spaceTitle.trim().length<2||!sourceSpace" @click="createSpace">创建标准空间并复制模板</button><button type="button" :disabled="busy||!spaceId||!sourceSpace||spaceId===sourceSpace" @click="copyTemplate">复制到当前空间的后续资料</button></div></details>
    <details><KnowledgeDisclosureSummary>既有任务与版本操作</KnowledgeDisclosureSummary><p class="muted">点击“任务详情”可查看逐文档实际模板、异常和核查记录；换版、撤回与恢复沿用资料版本管理。</p></details>
  </section>
</template>

<style scoped>
.managed-batch{padding:24px;margin-bottom:24px;min-width:0}.managed-batch h2{margin-top:0}.managed-batch label{display:grid;gap:6px;margin:12px 0}.managed-batch fieldset{border:1px solid var(--hbos-border-default);border-radius:12px;padding:16px;min-width:0}.managed-batch input:not([type=checkbox]),.managed-batch select,.managed-batch textarea{max-width:100%;min-height:40px;padding:8px;border:1px solid var(--hbos-border-default);border-radius:8px;background:var(--hbos-bg-surface,#fff);color:inherit}.managed-batch button{min-height:40px;padding:8px 14px;border:1px solid var(--hbos-border-default);border-radius:8px;background:var(--hbos-bg-surface,#fff);color:inherit;cursor:pointer}.managed-batch button:disabled{opacity:.55;cursor:default}.managed-batch button:focus-visible,.managed-batch input:focus-visible,.managed-batch select:focus-visible,.managed-batch summary:focus-visible{outline:2px solid var(--hbos-brand-aqua);outline-offset:3px}.actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.managed-batch .check{display:flex;align-items:center;gap:8px}.muted,small{color:var(--hbos-text-muted)}.error{color:var(--hbos-status-danger,#a62d37);white-space:pre-line;overflow-wrap:anywhere}.file-list,.jobs{list-style:none;padding:0;max-height:420px;overflow:auto}.file-list li{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;border-bottom:1px solid var(--hbos-border-default);padding:8px 0;overflow-wrap:anywhere}.file-list small{width:100%}.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-top:20px}.metrics div{display:grid;gap:4px}.metrics strong{font-size:24px}.metrics span{font-size:13px;color:var(--hbos-text-muted)}.jobs li{display:flex;align-items:flex-start;gap:12px;padding:16px 0;border-bottom:1px solid var(--hbos-border-default)}.jobs li>div{flex:1;min-width:0;overflow-wrap:anywhere}.jobs p{margin:4px 0}.managed-batch details{border-top:1px solid var(--hbos-border-default);padding-top:16px;margin-top:20px}.managed-batch summary{cursor:pointer;min-height:32px}.review{margin-top:20px;padding:16px;border:1px solid var(--hbos-border-default);border-radius:12px}.review article{margin:16px 0}.review article>button{margin-left:12px}.review blockquote{margin:8px 0;padding-left:12px;border-left:3px solid var(--hbos-border-default);overflow-wrap:anywhere;white-space:pre-wrap}@media(max-width:700px){.managed-batch{padding:16px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.jobs li{flex-wrap:wrap}.jobs li>div{flex-basis:70%}.actions{align-items:stretch}.actions>button{width:100%}}
</style>
