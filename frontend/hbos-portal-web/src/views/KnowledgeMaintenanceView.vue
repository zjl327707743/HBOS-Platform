<script setup lang="ts">
import KnowledgeDisclosureSummary from '@/components/knowledge/KnowledgeDisclosureSummary.vue'
import { markDrawerDialogRoot, forgetDrawerDialogRoot, syncDrawerDialogStack, topDrawerDialogRoot } from '@/components/knowledge/drawerDialogA11y'
import KnowledgeStaffFeedback from '@/components/knowledge/KnowledgeStaffFeedback.vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftOutlined, SearchOutlined, PlusOutlined, FileTextOutlined, UploadOutlined, ArrowRightOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { DomainApiError, getKnowledgeStatus } from '@/services/p1Api'
import PortalSelect from '@/components/portal/PortalSelect.vue'
import KnowledgeBatchMaintenance from '@/components/knowledge/KnowledgeBatchMaintenance.vue'
import KnowledgeEffectiveTemplate from '@/components/knowledge/KnowledgeEffectiveTemplate.vue'
import type { ManagedRow } from '@/services/knowledgeMaintenanceBatchApi'
import { getMaintenance, getMaintenanceFeedbackPage, getVersionLineage, maintenanceAction, previewImport, uploadKnowledge, planImport, submitImport, getBatchProgress, pauseImport, resumeImport, reclaimImport, type ImportItem, type MaintenanceDashboard, type QualityPreview, type MaintenanceFeedback, type VersionTarget, type VersionLineage, type BatchPlan, type BatchSubmitReceipt, type BatchProgress, type BatchRetrievalVerified, type MaintenanceBatchEntry, type MaintenanceLookupState } from '@/services/knowledgeMaintenanceApi'
const route=useRoute(),router=useRouter()
const props=defineProps<{sessionRevision?:number}>()
const view=computed(()=>route.path.endsWith('/upload')?'upload':route.path.endsWith('/versions')?'versions':route.path.endsWith('/feedback')?'feedback':'manage')
const maintenanceHeading = {
  manage: { title: '资料管理', description: '从资料导入到发布，每一步都清楚可核对。', eyebrow: 'KNOWLEDGE MAINTENANCE' },
  upload: { title: '新增资料', description: '上传原件，核对解析质量，再发布给员工。', eyebrow: 'ADD DOCUMENT' },
  versions: { title: '版本管理', description: '确认每一次换版，保留来源与处理记录。', eyebrow: 'VERSION CONTROL' },
  feedback: { title: '员工反馈', description: '集中核对资料问题，让反馈有清楚的处理结果。', eyebrow: 'EMPLOYEE FEEDBACK' },
}
const heading = computed(() => maintenanceHeading[view.value])
const allowed=ref(false),permissionDenied=ref(false),initialized=ref(false),busy=ref(false),error=ref(''),notice=ref(''),loading=ref(false)
const data=ref<MaintenanceDashboard|null>(null),department=ref('production'),selectedBatch=ref(''),page=ref(1),filter=ref(''),departmentFilter=ref(''),listPage=ref(1)
const file=ref<File|null>(null),sharing=ref(false),replacement=ref<VersionTarget|null>(null),uploadStage=ref(0)
const uploadSteps = ['选择原件', '解析资料', '核对质量', '发布资料']

const uploadStageHeading = ref<HTMLElement | HTMLElement[] | null>(null)
const parseTemplate=ref('auto')
watch(uploadStage, async () => {
  if (view.value !== 'upload') return
  await nextTick()
  const heading = uploadStageHeading.value
  const target = Array.isArray(heading) ? heading[0] : heading
  target?.focus()
})
const maxUploadBytes=computed(()=>data.value?.upload_policy?.max_source_bytes||20*1024*1024)
const uploadSizeLabel=computed(()=>`${Math.floor(maxUploadBytes.value/1024/1024)} MiB`)
const pdfTemplateChoices=computed(()=>data.value?.upload_policy?.native_templates_enabled&&file.value?.name.toLowerCase().endsWith('.pdf')?data.value.upload_policy.templates:[])
const qualityOpen=ref(false),preview=ref<QualityPreview|null>(null),qualityItem=ref<ImportItem|null>(null),checks=ref<string[]>([]),qualityNote=ref(''),operationReason=ref('')
const selectedIds=ref<string[]>([]),bulkQualityOpen=ref(false),bulkChecks=ref<string[]>([]),bulkNote=ref('')
const detailOpen=ref(false),detail=ref<ImportItem|null>(null),detailLoading=ref(false),detailTitle=ref('')
const feedbackReadError = ref(false)
const feedbackOpen=ref(false),selectedFeedback=ref<MaintenanceFeedback|null>(null),reply=ref(''),feedbackItems=ref<MaintenanceFeedback[]>([]),feedbackPage=ref(1),feedbackHasMore=ref(false),feedbackStatus=ref(''),feedbackQuery=ref(''),feedbackSearchUnsupported=ref(false)
const batchManifestText=ref(''),batchManifestName=ref(''),batchManifestOpen=ref(false)
const showAdvancedImport=ref(false), legacyOpen=ref(false)
// Drawer dialogs are marked and layered per instance (see drawerDialogA11y.ts). The
// open order is tracked explicitly because the portal DOM position is fixed on first
// mount, not by which drawer opened last; timers are registered so leaving the route
// cannot let a stale focus restore run after unmount.
const drawerDialogs = {
  detail: { rootClass: 'kb-drawer-detail', label: '资料与版本' },
  quality: { rootClass: 'kb-drawer-quality', label: '核对本版本质量' },
  bulk: { rootClass: 'kb-drawer-bulk-quality', label: '核对所选资料质量' },
  feedback: { rootClass: 'kb-drawer-feedback-review', label: '处理员工反馈' },
  batch: { rootClass: 'v17-batch-drawer', label: '批量处理与任务' },
} as const
type DrawerDialogKey = keyof typeof drawerDialogs
const drawerTimers = new Set<number>()
function scheduleDrawer(fn: () => void, delay: number) {
  const timer = window.setTimeout(() => { drawerTimers.delete(timer); fn() }, delay)
  drawerTimers.add(timer)
}
function clearDrawerTimers() {
  drawerTimers.forEach(timer => window.clearTimeout(timer))
  drawerTimers.clear()
}
function applyDrawerDialog(key: DrawerDialogKey) {
  const spec = drawerDialogs[key]
  markDrawerDialogRoot(spec.rootClass, spec.label, false)
  syncDrawerDialogStack()
}
function forgetDrawerDialog(key: DrawerDialogKey) {
  forgetDrawerDialogRoot(drawerDialogs[key].rootClass)
}
function onDetailDrawerOpenChange(open: boolean) { onDrawerOpenChange('detail', open) }
function onQualityDrawerOpenChange(open: boolean) { onDrawerOpenChange('quality', open) }
function onBulkQualityDrawerOpenChange(open: boolean) { onDrawerOpenChange('bulk', open) }
function onFeedbackDrawerOpenChange(open: boolean) { onDrawerOpenChange('feedback', open) }
function onLegacyDrawerOpenChange(open: boolean) { onDrawerOpenChange('batch', open) }
function onDrawerOpenChange(key: DrawerDialogKey, open: boolean) {
  if (!open) {
    forgetDrawerDialog(key)
    void nextTick(syncDrawerDialogStack)
    return
  }
  void nextTick(() => applyDrawerDialog(key))
  ;[80, 260].forEach(delay => scheduleDrawer(() => applyDrawerDialog(key), delay))
}
// The drawer open state is the source of truth: mark each opened instance, forget the
// closed one and re-rank the remaining layers after every open/close, including re-opens.
const drawerReturnFocus: Partial<Record<DrawerDialogKey, HTMLElement | null>> = {}
let lastInteractionTarget: HTMLElement | null = null
function rememberInteraction(event: MouseEvent) {
  const control = (event.target as HTMLElement | null)?.closest?.('button, a, [role="button"]') as HTMLElement | null
  if (control) lastInteractionTarget = control
}
watch([detailOpen, qualityOpen, bulkQualityOpen, feedbackOpen, legacyOpen], (_now, before) => {
  const flags: Array<[DrawerDialogKey, boolean]> = [
    ['detail', detailOpen.value], ['quality', qualityOpen.value], ['bulk', bulkQualityOpen.value],
    ['feedback', feedbackOpen.value], ['batch', legacyOpen.value],
  ]
  flags.forEach(([key, open], index) => {
    if (open && !(before[index] as boolean)) {
      if (drawerReturnFocus[key]) return
      const active = document.activeElement as HTMLElement | null
      const activeIsEntry = Boolean(active && active !== document.body && !active.closest('.ant-drawer'))
      drawerReturnFocus[key] = activeIsEntry ? active : lastInteractionTarget
      return
    }
    if (!open && (before[index] as boolean)) restoreDrawerFocus(key)
  })
}, { flush: 'pre' })
function releaseDrawerInert() {
  document.querySelectorAll<HTMLElement>('.ant-drawer-content-wrapper[inert]').forEach(wrapper => wrapper.removeAttribute('inert'))
}
function closeDrawer(key: DrawerDialogKey) {
  releaseDrawerInert()
  forgetDrawerDialog(key)
  if (key === 'detail') detailOpen.value = false
  else if (key === 'quality') qualityOpen.value = false
  else if (key === 'bulk') bulkQualityOpen.value = false
  else if (key === 'feedback') feedbackOpen.value = false
  else legacyOpen.value = false
}
function restoreDrawerFocus(key: DrawerDialogKey) {
  const target = drawerReturnFocus[key]
  drawerReturnFocus[key] = null
  const tryRestore = () => {
    syncDrawerDialogStack()
    const top = topDrawerDialogRoot()
    const active = document.activeElement as HTMLElement | null
    if (top) {
      if (active && top.contains(active)) return
      if (target?.isConnected && target.getClientRects().length && !target.closest('[inert]') && top.contains(target)) {
        target.focus({ preventScroll: true })
        return
      }
      const closeButton = top.querySelector<HTMLElement>('.ant-drawer-close, .ant-drawer-title[tabindex]')
      ;(closeButton || top).focus({ preventScroll: true })
      return
    }
    if (target?.isConnected && target.getClientRects().length) {
      target.focus({ preventScroll: true })
      return
    }
    ;(document.querySelector<HTMLElement>('.kb-main, main') as HTMLElement | null)?.focus({ preventScroll: true })
  }
  ;[0, 120, 360, 720].forEach(delay => scheduleDrawer(tryRestore, delay))
}

function syncOpenDrawerDialogs() {
  const openKeys: DrawerDialogKey[] = []
  if (detailOpen.value) openKeys.push('detail')
  if (qualityOpen.value) openKeys.push('quality')
  if (bulkQualityOpen.value) openKeys.push('bulk')
  if (feedbackOpen.value) openKeys.push('feedback')
  if (legacyOpen.value && view.value === 'manage') openKeys.push('batch')
  ;(['detail', 'quality', 'bulk', 'feedback', 'batch'] as DrawerDialogKey[]).forEach(key => {
    if (!openKeys.includes(key)) forgetDrawerDialog(key)
  })
  openKeys.forEach(key => {
    const spec = drawerDialogs[key]
    markDrawerDialogRoot(spec.rootClass, spec.label, false)
  })
  syncDrawerDialogStack()
}
watch([detailOpen, qualityOpen, bulkQualityOpen, feedbackOpen, legacyOpen], () => {
  void nextTick(syncOpenDrawerDialogs)
}, { flush: 'post' })
watch(view, () => {
  clearDrawerTimers()
  ;(['detail', 'quality', 'bulk', 'feedback', 'batch'] as DrawerDialogKey[]).forEach(forgetDrawerDialog)
  void nextTick(syncDrawerDialogStack)
})
const batchEntry = ref<HTMLButtonElement|null>(null)
async function closeBatchPreview() {
  releaseDrawerInert()
  forgetDrawerDialog('batch')
  legacyOpen.value = false
  await nextTick()
  batchEntry.value?.focus({preventScroll:true})
}
const overviewStatus=ref<'published'|'quality'|'sharing'|null>(null)
const overviewMatches = computed(() => {
  const source = publishedLookup.value
    ? publishedLookupRows.value.filter(row=>!departmentFilter.value||row.department===departmentFilter.value)
    : managed.value
  return source.filter(row => {
    switch (overviewStatus.value) {
      case 'published': return row.status === '已发布'
      case 'quality': return row.item?.parse_status === 'parsed/indexed' && row.item.quality_status !== 'Passed' && row.item.publication_status === 'Unpublished'
      case 'sharing': return row.item?.quality_status === 'Passed' && row.item.shared_approved === false && row.item.publication_status === 'Unpublished'
      default: return true
    }
  })
})
const overviewRows=computed(()=>publishedLookup.value ? overviewMatches.value : overviewMatches.value.slice((listPage.value-1)*6,listPage.value*6))
// MC-1 (live since W1): the dashboard returns overview{published_total,
// pending_quality_check, sharing_pending, feedback_pending}. Render server values;
// only fall back to an explicit "-/服务端未提供" when the field is absent (old candidate).
const overviewStats = computed(() => {
  const overview = data.value?.overview
  const live = (value: number | undefined, caption: string) => value === undefined
    ? { value: '-', caption: '服务端未提供' }
    : { value, caption }
  return [
    { key: 'published', title: '当前已发布', ...(overview ? live(overview.published_total, '逻辑文档') : data.value?.published_total === undefined ? { value: '—', caption: '逻辑文档' } : live(data.value.published_total, '逻辑文档')) },
    { key: 'quality', title: '待质量核对', ...live(overview?.pending_quality_check, '待质量核对') },
    { key: 'sharing', title: '共享待确认', ...live(overview?.sharing_pending, '共享待确认') },
    { key: 'feedback', title: '员工反馈', ...live(overview?.feedback_pending, '员工反馈') },
  ] as const
})
function toggleOverviewStatus(key: typeof overviewStats.value[number]['key']) {
  if (key === 'feedback') {
    void router.push('/hbos/knowledge/maintenance/feedback')
    return
  }
  clearPublishedLookup()
  listPage.value=1
  overviewStatus.value=overviewStatus.value===key ? null : key
}
async function openBatchPreview(){
  showAdvancedImport.value=true
  legacyOpen.value=true
  await nextTick()
  document.querySelector<HTMLElement>('.v17-batch-drawer .ant-drawer-close')?.focus()
}
function canSelectRow(id:string){return selectable.value.some(item=>item.document_id===id)}
const batchPlan=ref<BatchPlan|null>(null),batchPlanError=ref(''),batchApproval=ref(''),batchLabel=ref('')
const batchConfirmed = ref(false)
const batchSubmitting=ref(false),batchReceipt=ref<BatchSubmitReceipt|null>(null),batchProgress=ref<BatchProgress|null>(null)
const progressBatchId=ref(''),batchReclaimReason=ref(''),batchActionBusy=ref(false),batchRetryId=ref('')
// WP6: bounded server-side lookup over the two maintenance projections. The
// default dashboard still renders the legacy first-1000/first-100 window; these
// states only hold an explicit server search result so the browser never scans
// pages or widens the projection itself.
interface PublishedLookupView { term:string; documents:VersionTarget[]; matched:number; total:number; page:number; pageSize:number; hasMore:boolean; state:MaintenanceLookupState }
interface BatchLookupView { term:string; batches:MaintenanceBatchEntry[]; matched:number; total:number; page:number; pageSize:number; hasMore:boolean; scanTruncated:boolean; state:MaintenanceLookupState }
const publishedSearch=ref(''),publishedLookup=ref<PublishedLookupView|null>(null),publishedLookupLoading=ref(false),publishedLookupError=ref('')
const batchSearch=ref(''),batchLookup=ref<BatchLookupView|null>(null),batchLookupLoading=ref(false),batchLookupError=ref('')
const replacementSearch=ref(''),replacementLookupDocs=ref<VersionTarget[]>([]),replacementLookupLoading=ref(false),replacementLookupError=ref('')
const detailLookupState=ref<MaintenanceLookupState>(null),detailTarget=ref<VersionTarget|null>(null),selectedPublished=ref<VersionTarget|null>(null)
const DOCUMENT_ID_TERM=/^(?:DOC_[A-Za-z0-9_-]{1,96}|N1DOC-[0-9a-f]{24})$/
const planNames:Record<string,string>={NEW:'新文件（已登记原件）',DUPLICATE:'重复，保留已处理版本',BUSINESS_UPDATE:'业务换版（需原件解析流程）',TECHNICAL_REPAIR:'技术修复（需既有 native 流程）',NEW_UPLOAD_REQUIRED:'需先单文件上传原件',ANOMALY:'异常，需修正清单'}
const planColors:Record<string,string>={NEW:'green',DUPLICATE:'blue',BUSINESS_UPDATE:'orange',TECHNICAL_REPAIR:'purple',NEW_UPLOAD_REQUIRED:'gold',ANOMALY:'red'}
const parseNamesForBatch:Record<string,string>={'planned':'待解析','uploaded':'已上传待解析','parse_queued':'解析中','parse_intent':'请求待核验','parsed/indexed':'解析完成','parse_failed':'解析失败','quarantined':'身份待核对','skipped_duplicate':'重复跳过'}
const receiptNames:Record<string,string>={'VERIFIED':'检索已验证','PENDING':'待员工检索验证','INVALIDATED':'检索验证已失效'}
const receiptReasons:Record<string,string>={WITHDRAWN:'已下架',VERSION_SUPERSEDED:'已换版',UNPUBLISHED:'未发布'}
let progressTimer:ReturnType<typeof setInterval>|null=null
let epoch=0,readSequence=0,feedbackSequence=0
const batch=computed(()=>data.value?.selected)
const selectable=computed(()=>batch.value?.items.filter(i=>i.parse_status==='parsed/indexed'&&i.relationship!=='SAME_CONTENT_SKIP'&&i.publication_status==='Unpublished'&&(!i.current_version||i.current_version===i.version_id))||[])
const selectedItems=computed(()=>selectable.value.filter(i=>selectedIds.value.includes(i.document_id)))
const canPublishSelected=computed(()=>selectedItems.value.length>0&&selectedItems.value.every(i=>i.quality_status==='Passed'&&i.shared_approved===true))
const canApproveSharing=computed(()=>selectedItems.value.length>0&&selectedItems.value.every(i=>i.quality_status==='Passed'&&i.shared_approved===false))
const canParse=computed(()=>data.value?.import_availability.can_parse===true)
const replacements=computed(()=>data.value?.published_documents.filter(i=>i.department===department.value)||[])
const replacementOptions=computed(()=>{
  const seen=new Set<string>(),merged:VersionTarget[]=[]
  // A replacement target chosen from a lookup (or via 上传新修订版) must stay
  // visible even when it is outside the currently loaded projection.
  if(replacement.value&&replacement.value.department===department.value){seen.add(replacement.value.document_id);merged.push(replacement.value)}
  for(const item of [...replacements.value,...replacementLookupDocs.value]){
    if(item.department!==department.value||seen.has(item.document_id))continue
    seen.add(item.document_id);merged.push(item)
  }
  return merged
})
const publishedTotal=computed(()=>data.value?.published_total??data.value?.published_documents.length??0)
const publishedTruncated=computed(()=>Boolean(data.value?.published_truncated))
const batchesTotal=computed(()=>data.value?.batches_total??data.value?.batches.length??0)
// A server lookup result replaces only the selector's option list; the dashboard
// itself is left untouched so detail/withdraw/publish flows keep their state.
const batchOptions=computed(()=>{
  const base=batchLookup.value?batchLookup.value.batches:(data.value?.batches||[])
  if(!selectedBatch.value||base.some(entry=>entry.name===selectedBatch.value))return base
  // Keep the located/selected batch visible after a bounded lookup, even when
  // it is not part of the legacy first-100 projection.
  const current=data.value?.selected
  return [{name:selectedBatch.value,label:current?.label||selectedBatch.value,department_key:current?.department||'',status:current?.status||''},...base]
})
const parseNames:Record<string,string>={'planned':'待解析','uploaded':'待解析','original_stored':'原件已保留（全文另验）','parse_intent':'请求待核验','parse_queued':'解析中','parsed/indexed':'解析完成','parse_failed':'解析失败','quarantined':'身份待核对','skipped_duplicate':'重复，保留原版本'}
const relationships:Record<string,string>={NEW:'新增资料',UPDATE_CONFIRMED:'已确认换版',SAME_CONTENT_SKIP:'相同内容，保留原身份',UPDATE_CANDIDATE:'换版关系待确认',CONFLICT:'身份冲突'}
const departmentName=(key:string)=>data.value?.departments.find(d=>d.key===key)?.title||key
const managed=computed(()=>{
  const docs=(data.value?.published_documents||[]).map(d=>({...d,status:'已发布',item:undefined as ImportItem|undefined}))
  for(const item of batch.value?.items||[])if(!docs.some(d=>d.version_id===item.version_id))docs.unshift({document_id:item.document_id,title:item.title,version_id:item.version_id,current_version:item.current_version||'',department:batch.value?.department||'',status:item.publication_status==='Withdrawn'?'已下架':item.publication_status==='Published'?'已发布':item.quality_status==='Passed'?'待发布':parseNames[item.parse_status]||'待核对',item})
  return docs.filter(d=>(!filter.value||(d.title).toLowerCase().includes(filter.value.trim().toLowerCase()))&&(!departmentFilter.value||d.department===departmentFilter.value))
})
const publishedLookupRows=computed(()=>{
  const documents=publishedLookup.value?.documents||[]
  return documents.map(d=>({...d,status:'已发布',item:undefined as ImportItem|undefined}))
})
const visibleDocs=computed(()=>{
  const term=publishedSearch.value.trim().toLowerCase()
  const matched=(publishedLookup.value?publishedLookupRows.value:managed.value)
    .filter(d=>!term||d.title.toLowerCase().includes(term))
    .filter(d=>!departmentFilter.value||d.department===departmentFilter.value)
  return publishedLookup.value?matched:matched.slice((listPage.value-1)*4,listPage.value*4)
})
// MC-3 (candidate contract inherited from W1): the versions view reads
// GET get_version_lineage for the selected document and renders only the
// server-returned chain. The real service was not available in this workspace, so the
// UI keeps an honest unavailable state for error/denial instead of inferring history.
const lineageDocumentId = ref(''), lineage = ref<VersionLineage | null>(null)
const lineageLoading = ref(false), lineageError = ref(''), lineageSequence = ref(0)
const lineageOptions = computed(() => managed.value.slice(0, 50).map(doc => ({ value: doc.document_id, label: doc.title })))
async function loadLineage(documentId = lineageDocumentId.value) {
  if (!documentId) { lineage.value = null; lineageError.value = ''; return }
  const sequence = ++lineageSequence.value
  lineageLoading.value = true; lineageError.value = ''
  try {
    if (typeof getVersionLineage !== 'function') throw new Error('版本沿革服务未接入。')
    const result = await getVersionLineage(documentId)
    if (sequence !== lineageSequence.value || documentId !== lineageDocumentId.value) return
    lineage.value = result
  } catch (error) {
    if (sequence !== lineageSequence.value || documentId !== lineageDocumentId.value) return
    lineage.value = null
    const denied = error instanceof DomainApiError && ['SCOPE_REJECTED', 'FORBIDDEN', 'AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED'].includes(error.code)
    lineageError.value = denied ? '当前账号无权查看该资料的版本沿革；请确认维护权限。' : error instanceof DomainApiError ? error.message : '版本沿革暂时不可用，请稍后重试。'
  } finally {
    if (sequence === lineageSequence.value) lineageLoading.value = false
  }
}
watch([view, data, lineageDocumentId], () => {
  if (view.value !== 'versions') return
  if (!lineageDocumentId.value) {
    const first = managed.value[0]
    if (first) { lineageDocumentId.value = first.document_id; return }
  }
  if (lineageDocumentId.value) void loadLineage()
})
watch([filter,departmentFilter,publishedLookup,listPage,overviewStatus],()=>{
  selectedIds.value=selectedIds.value.filter(id=>overviewRows.value.some(row=>row.document_id===id))
})
watch([filter,departmentFilter],()=>{listPage.value=1})
watch([selectedBatch,page],()=>{selectedIds.value=[];bulkQualityOpen.value=false})
watch(data,()=>{selectedIds.value=selectedIds.value.filter(id=>selectable.value.some(i=>i.document_id===id))})
watch(department,()=>{replacement.value=null;replacementLookupDocs.value=[];replacementLookupError.value=''})
watch(view,()=>{error.value='';notice.value='';detailOpen.value=false;feedbackOpen.value=false;if(view.value==='feedback')void refreshFeedback()})
function message(e:unknown){return e instanceof Error?e.message:'维护服务暂不可用。'}
function failure(e:unknown){error.value=message(e);if(e instanceof DomainApiError&&['SCOPE_REJECTED','FORBIDDEN','AUTHENTICATION_REQUIRED','CLIENT_AUTH_FAILED'].includes(e.code)){epoch++;data.value=null;preview.value=null;detail.value=null;feedbackItems.value=[];allowed.value=false;permissionDenied.value=true;qualityOpen.value=false;bulkQualityOpen.value=false;selectedIds.value=[];detailOpen.value=false;feedbackOpen.value=false;publishedLookup.value=null;publishedLookupError.value='';batchLookup.value=null;batchLookupError.value='';replacementLookupDocs.value=[];replacementLookupError.value='';detailLookupState.value=null;selectedPublished.value=null}}
async function refresh(){const current=epoch,seq=++readSequence;loading.value=true;error.value='';try{let result=await getMaintenance(selectedBatch.value||undefined,page.value);if(current!==epoch||seq!==readSequence)return;if(!selectedBatch.value&&result.batches.length){selectedBatch.value=result.batches[0]!.name;result=await getMaintenance(selectedBatch.value,1)}if(current===epoch&&seq===readSequence)data.value=result}catch(e){if(current===epoch&&seq===readSequence)failure(e)}finally{if(current===epoch&&seq===readSequence)loading.value=false}}
async function selectManagedBatch(id:string){selectedBatch.value=id;page.value=1;uploadStage.value=1;detailOpen.value=false;await router.push('/hbos/knowledge/maintenance/upload');await refresh()}
async function openManagedVersion(row:ManagedRow){
  const current=epoch
  try{
    const result=await getMaintenance(row.batch_id,1,row.document_id)
    if(current!==epoch)return
    const item=result.selected?.items.find(entry=>entry.document_id===row.document_id&&entry.version_id===row.version_id)
    if(!item||!result.selected)throw new DomainApiError('SOURCE_VERSION_STALE','处理记录已变化，请刷新后重试。')
    selectedBatch.value=row.batch_id
    page.value=result.selected.page
    data.value=result
    await openDetails({title:row.title,document_id:row.document_id,version_id:row.version_id,
      current_version:item.current_version||'',department:result.selected.department,item})
  }catch(e){if(current===epoch)failure(e)}
}
function accessDenied(e:unknown){return e instanceof DomainApiError&&['SCOPE_REJECTED','FORBIDDEN','AUTHENTICATION_REQUIRED','CLIENT_AUTH_FAILED'].includes(e.code)}
function clearPublishedLookup(){publishedLookup.value=null;publishedLookupError.value='';publishedSearch.value='';selectedPublished.value=null}
function clearBatchLookup(){batchLookup.value=null;batchLookupError.value='';batchSearch.value=''}
async function searchPublished(pageNumber=1){
 const term=publishedSearch.value.trim()
 if(!term){publishedLookupError.value='请输入标题、文号、部门，或精确文档 ID（DOC_…）。';return}
 const current=epoch;publishedLookupLoading.value=true;publishedLookupError.value=''
 try{
  const byDocument=DOCUMENT_ID_TERM.test(term)
  const result=await getMaintenance(selectedBatch.value||undefined,page.value,undefined,{...(byDocument?{published_document_id:term}:{published_query:term}),published_page:Math.max(1,pageNumber),published_page_size:50})
  if(current!==epoch)return
  const documents=result.published_documents||[]
  const matched=result.published_matched??documents.length
  const state=result.published_lookup_state??(byDocument?(matched?'FOUND':'NOT_FOUND'):null)
  publishedLookup.value={term,documents,matched,total:result.published_total??publishedTotal.value,page:result.published_page??Math.max(1,pageNumber),pageSize:result.published_page_size??50,hasMore:Boolean(result.published_has_more),state}
  if(byDocument&&documents[0]){selectedPublished.value=documents[0];detailTarget.value=documents[0]}
 }catch(e){if(current!==epoch)return;publishedLookupError.value=message(e);if(accessDenied(e))failure(e)}
 finally{if(current===epoch)publishedLookupLoading.value=false}
}
async function changePublishedPage(next:number){if(publishedLookupLoading.value||!publishedLookup.value||next<1)return;await searchPublished(next)}
async function enterLocatedBatch(entry:MaintenanceBatchEntry,term:string,current:number){
 selectedBatch.value=entry.name
 page.value=entry.document_page&&entry.document_page>0?entry.document_page:1
 const result=await getMaintenance(entry.name,page.value,term)
 if(current!==epoch)return
 data.value=result
 detailLookupState.value=result.selected?'FOUND':'NOT_FOUND'
}
async function searchBatches(pageNumber=1){
 const term=batchSearch.value.trim()
 // Empty term is allowed only to page the default batch projection; a first-page
 // empty search would just duplicate the dashboard's own bounded read.
 if(!term&&pageNumber<=1){batchLookupError.value='请输入批次名称、部门，或精确文档 ID（DOC_…）。';return}
 const current=epoch;batchLookupLoading.value=true;batchLookupError.value=''
 try{
  const byDocument=term?DOCUMENT_ID_TERM.test(term):false
  const result=await getMaintenance(selectedBatch.value||undefined,page.value,undefined,{...(byDocument?{batch_document_id:term}:term?{batch_query:term}:{}),batch_page:Math.max(1,pageNumber),batch_page_size:100})
  if(current!==epoch)return
  const batches=result.batches||[]
  const matched=result.batches_matched??batches.length
  const state=result.batch_lookup_state??(byDocument?(matched?'FOUND':'NOT_FOUND'):null)
  batchLookup.value={term,batches,matched,total:result.batches_total??batchesTotal.value,page:result.batches_page??Math.max(1,pageNumber),pageSize:result.batches_page_size??100,hasMore:Boolean(result.batches_has_more),scanTruncated:Boolean(result.batch_scan_truncated),state}
  if(byDocument&&state==='FOUND'&&batches[0])await enterLocatedBatch(batches[0],term,current)
 }catch(e){if(current!==epoch)return;batchLookupError.value=message(e);if(accessDenied(e))failure(e)}
 finally{if(current===epoch)batchLookupLoading.value=false}
}
async function changeBatchPage(next:number){if(batchLookupLoading.value||!batchLookup.value||next<1)return;await searchBatches(next)}
async function locateBatchFromInput(){
 const term=batchSearch.value.trim()
 if(!DOCUMENT_ID_TERM.test(term)){batchLookupError.value='按文档定位批次请输入精确文档 ID（DOC_…）；已知批次名称请用上方搜索。';return}
 await searchBatches(1)
}
async function searchReplacementDocs(){
 const term=replacementSearch.value.trim()
 if(!term){replacementLookupError.value='请输入标题、文号或精确文档 ID。';return}
 const current=epoch;replacementLookupLoading.value=true;replacementLookupError.value='';replacementLookupDocs.value=[]
 try{
  const byDocument=DOCUMENT_ID_TERM.test(term)
  const result=await getMaintenance(undefined,1,undefined,{...(byDocument?{published_document_id:term}:{published_query:term}),published_page:1,published_page_size:50})
  if(current!==epoch)return
  const matches=result.published_documents||[]
  replacementLookupDocs.value=matches.filter(item=>item.department===department.value)
  if(!replacementLookupDocs.value.length)replacementLookupError.value=matches.length?`找到 ${matches.length} 份已发布资料，但都不属于当前所选部门；请调整部门或改用精确文档 ID。`:'未找到匹配的已发布资料。'
  // An exact document-id lookup names exactly one target: select it directly.
  if(byDocument&&replacementLookupDocs.value.length===1)replacement.value=replacementLookupDocs.value[0]!
 }catch(e){if(current!==epoch)return;replacementLookupError.value=message(e);if(accessDenied(e))failure(e)}
 finally{if(current===epoch)replacementLookupLoading.value=false}
}
function selectReplacement(documentId:string){replacement.value=replacementOptions.value.find(i=>i.document_id===documentId)||replacementLookupDocs.value.find(i=>i.document_id===documentId)||null}
// P09: the Main 10h window adds a bounded, read-only server-side substring filter to
// get_feedback_queue. The UI sends the term so the server performs the filter; it never
// scans the full queue in the browser. An older candidate without the query parameter
// keeps an honest fallback (unfiltered queue + one limitation line), never fake results.
async function refreshFeedback(){const current=epoch,seq=++feedbackSequence;loading.value=true;feedbackReadError.value=false;error.value='';try{
 const result=await getMaintenanceFeedbackPage(feedbackPage.value,feedbackStatus.value,feedbackQuery.value)
 if(current===epoch&&seq===feedbackSequence){feedbackItems.value=result.items;feedbackHasMore.value=result.has_more;feedbackSearchUnsupported.value=false}
 }catch(e){
  if(current===epoch&&seq===feedbackSequence){
   if(feedbackQuery.value&&e instanceof DomainApiError&&e.code==='INVALID_REQUEST'){
    feedbackSearchUnsupported.value=true
    try{
     const fallback=await getMaintenanceFeedbackPage(feedbackPage.value,feedbackStatus.value,'')
     if(current===epoch&&seq===feedbackSequence){feedbackItems.value=fallback.items;feedbackHasMore.value=fallback.has_more;feedbackReadError.value=false}
    }catch(inner){if(current===epoch&&seq===feedbackSequence){feedbackReadError.value=true;failure(inner)}}
   }else{feedbackReadError.value=true;failure(e)}
  }
 }finally{if(current===epoch&&seq===feedbackSequence)loading.value=false}}
function searchFeedback(){feedbackPage.value=1;void refreshFeedback()}
watch(feedbackPage,refreshFeedback);watch(feedbackStatus,()=>{feedbackPage.value=1;void refreshFeedback()})
async function act(work:()=>Promise<unknown>,success:string){if(busy.value)return;const current=epoch;busy.value=true;error.value='';notice.value='';try{await work();if(current!==epoch)return;notice.value=success;await refresh();if(detail.value){const item=batch.value?.items.find(i=>i.version_id===detail.value?.version_id);if(item)detail.value=item}}catch(e){if(current===epoch)failure(e)}finally{if(current===epoch)busy.value=false}}
function chooseOriginal(chosen: File | null) {
  notice.value = ''
  error.value = ''
  parseTemplate.value = 'auto'
  file.value = null
  if (!chosen) return
  if (!/\.(pdf|doc|docx|xlsx|pptx|txt|md)$/i.test(chosen.name)) {
    error.value = '请选择 PDF、Word、Excel、PowerPoint 或文本文件。'
    return
  }
  if (chosen.size > maxUploadBytes.value) {
    error.value = `单份资料超过 ${uploadSizeLabel.value}，请选择较小文件或使用维护员批量入口。`
    return
  }
  file.value = chosen
}
function chooseFile(event: Event) {
  const input = event.target as HTMLInputElement
  chooseOriginal(input.files?.[0] ?? null)
  input.value = ''
}
function dropOriginal(event: DragEvent) {
  if (!busy.value) chooseOriginal(event.dataTransfer?.files[0] ?? null)
}
async function upload(){if(!file.value||!sharing.value)return;if(file.value.size>maxUploadBytes.value){error.value=`单份资料超过 ${uploadSizeLabel.value}，请重新选择文件。`;return}await act(async()=>{const result=await uploadKnowledge(file.value!,department.value,sharing.value,replacement.value||undefined,parseTemplate.value);selectedBatch.value=result.batch_id;data.value=null;page.value=1;file.value=null;sharing.value=false;replacement.value=null;parseTemplate.value='auto';uploadStage.value=1},'上传结果已保存，自动处理与异常状态见任务记录。')}
watch(batchManifestText, () => {
  batchConfirmed.value = false
  batchPlan.value = null
}, { flush: 'sync' })
function batchAvailable(){return data.value?.import_availability?.can_batch===true}
function chooseManifest(event:Event){const input=event.target as HTMLInputElement;const chosen=input.files?.[0]||null;batchPlanError.value='';if(!chosen)return;if(chosen.size>4*1024*1024){batchPlanError.value='清单文件超过 4 MB，请拆分批次。';return}batchManifestName.value=chosen.name;const reader=new FileReader();reader.onload=()=>{batchManifestText.value=String(reader.result||'');batchManifestOpen.value=true};reader.readAsText(chosen,'utf-8')}
async function previewBatch(){const source=batchManifestText.value;batchConfirmed.value=false;batchPlan.value=null;batchPlanError.value='';batchReceipt.value=null;batchProgress.value=null;stopProgressTimer();batchActionBusy.value=true;try{let manifest:unknown;try{manifest=JSON.parse(batchManifestText.value)}catch{batchPlanError.value='清单不是有效 JSON。';return}const result=await planImport(manifest);if(source!==batchManifestText.value)return;batchPlan.value=result;if(!batchApproval.value.trim())batchApproval.value='';batchLabel.value=batchPlan.value.label||batchManifestName.value.replace(/\.json$/i,'')}catch(e){batchPlanError.value=message(e)}finally{batchActionBusy.value=false}}
async function submitBatch(){const plan=batchPlan.value;if(!plan||!plan.submittable||!batchConfirmed.value||batchSubmitting.value)return;const approval=batchApproval.value.trim();if(approval.length<3){batchPlanError.value='提交前请填写可追溯的批准引用（至少三个字符）。';return}batchSubmitting.value=true;batchPlanError.value='';try{const receipt=await submitImport(plan.plan_sha256,approval,batchLabel.value.trim()||undefined);batchReceipt.value=receipt;notice.value=receipt.replayed?'同一预演已提交过，返回原批次，未重复上传或解析。':'批量入库已登记并按每四份一组排队。';progressBatchId.value=receipt.batches[0]?.batch_id||'';await refreshBatchProgress(true)}catch(e){batchPlanError.value=message(e)}finally{batchSubmitting.value=false}}
async function refreshBatchProgress(silent=false){const id=progressBatchId.value;if(!id)return;try{const value=await getBatchProgress(id);if(id!==progressBatchId.value)return;batchProgress.value=value}catch(e){if(!silent)failure(e)}}
function stopProgressTimer(){if(progressTimer){clearInterval(progressTimer);progressTimer=null}}
function syncProgressTimer(){stopProgressTimer();if(batchProgress.value?.job?.status==='Running')progressTimer=setInterval(()=>void refreshBatchProgress(true),4000)}
watch(()=>batchProgress.value?.job?.status,()=>syncProgressTimer())
watch(progressBatchId,value=>{batchProgress.value=null;stopProgressTimer();if(value)void refreshBatchProgress(true)})
async function pauseBatch(){const current=batchProgress.value;if(!current||batchActionBusy.value)return;batchActionBusy.value=true;try{const result=await pauseImport(current.batch_id);notice.value=result.pause_requested?'暂停请求已登记，解析会在安全点停止，不中断进行中的解析。':'批次已暂停，控制器不会再领取新组。';await refreshBatchProgress(true)}catch(e){failure(e)}finally{batchActionBusy.value=false}}
async function resumeBatch(){const current=batchProgress.value;if(!current||batchActionBusy.value)return;batchActionBusy.value=true;try{await resumeImport(current.batch_id);notice.value='恢复请求已登记，沿用原批次与任务继续。';await refreshBatchProgress(true)}catch(e){failure(e)}finally{batchActionBusy.value=false}}
async function reclaimBatch(){const current=batchProgress.value;if(!current)return;if(batchReclaimReason.value.trim().length<3){batchPlanError.value='回收过期租约前请填写至少三个字符的原因。';return}batchActionBusy.value=true;try{const result=await reclaimImport(current.batch_id,batchReclaimReason.value.trim());notice.value=result.total?('已回收过期租约，租约代数更新为 '+result.reclaimed[0]?.new_lease_generation+'；旧持有者的迟到写入会被拒绝。'):'当前没有可回收的过期租约（仍有效或已终态）。';batchReclaimReason.value='';await refreshBatchProgress(true)}catch(e){failure(e)}finally{batchActionBusy.value=false}}
async function retryBatchItem(item:{document_id:string}){const current=batchProgress.value;if(!current||batchRetryId.value)return;batchRetryId.value=item.document_id;try{await maintenanceAction('queue_import',{batch_id:current.batch_id,document_ids:[item.document_id],operation:'retry'});notice.value='失败项已单独排队重试。';await refreshBatchProgress(true)}catch(e){failure(e)}finally{batchRetryId.value=''}}
const canPauseBatch=computed(()=>{const job=batchProgress.value?.job;return Boolean(job&&((job.status==='Queued')||(job.status==='Running'&&!job.pause_requested)))})
const canResumeBatch=computed(()=>{const current=batchProgress.value;if(!current?.job)return false;return current.status==='Paused'||(current.job.status==='Running'&&current.job.pause_requested)||['Blocked','Failed'].includes(current.status)})
const canReclaimBatch=computed(()=>Boolean(batchProgress.value?.job&&batchProgress.value.job.lease_expired))
function receiptLabel(item:{retrieval_verified:BatchRetrievalVerified|null}){const receipt=item.retrieval_verified;if(!receipt)return '';if(receipt.status==='INVALIDATED')return receiptNames.INVALIDATED+'（'+(receiptReasons[receipt.reason||'']||'状态变化')+'）';return receiptNames[receipt.status]||''}
function receiptColor(item:{retrieval_verified:BatchRetrievalVerified|null}){const status=item.retrieval_verified?.status;return status==='VERIFIED'?'green':status==='INVALIDATED'?'red':'default'}
function toggleSelected(id:string,checked:boolean){selectedIds.value=checked?[...new Set([...selectedIds.value,id])]:selectedIds.value.filter(value=>value!==id)}
function openBulkQuality(){if(!selectedItems.value.length)return;bulkChecks.value=[];bulkNote.value='';bulkQualityOpen.value=true}
async function confirmBulkQuality(){if(bulkChecks.value.length!==4||bulkNote.value.trim().length<3||!selectedItems.value.length)return;const ids=selectedItems.value.map(i=>i.document_id);await act(()=>maintenanceAction('review_import_batch',{batch_id:selectedBatch.value,document_ids:ids,checks:bulkChecks.value,note:bulkNote.value.trim()}),'所选资料质量核对已保存，可一次确认发布。');if(!error.value)bulkQualityOpen.value=false}
async function holdBulkQuality(){if(bulkNote.value.trim().length<3||!selectedItems.value.length)return;const ids=selectedItems.value.map(i=>i.document_id);await act(()=>maintenanceAction('hold_import_quality',{batch_id:selectedBatch.value,document_ids:ids,note:bulkNote.value.trim()}),'所选资料保留待复核，质量通过前不能发布。');if(!error.value)bulkQualityOpen.value=false}
async function approveSharingSelected(){if(!canApproveSharing.value)return;const ids=selectedItems.value.map(i=>i.document_id);await act(async()=>{const result=await maintenanceAction('approve_import_sharing',{batch_id:selectedBatch.value,document_ids:ids,note:'维护员明确确认所选资料已获准内部共享，不含未批准的个人、保密或受限内容。'}) as {batch_id:string};selectedBatch.value=result.batch_id;page.value=1},'共享确认已登记，请单独确认发布。')}
async function publishSelected(){if(!canPublishSelected.value)return;const ids=selectedItems.value.map(i=>i.document_id);await act(()=>maintenanceAction('publish_import',{batch_id:selectedBatch.value,document_ids:ids,operation:'publish'}),'所选合格资料已发布，员工可按授权检索。')}
function changeBatch(){if(busy.value)return;page.value=1;detailOpen.value=false;epoch++;void refresh()}
function args(item:ImportItem){return {batch_id:selectedBatch.value,document_id:item.document_id}}
async function openQuality(item:ImportItem, inline = false){qualityOpen.value=!inline;if(inline)uploadStage.value=2;qualityItem.value=item;preview.value=null;checks.value=[];qualityNote.value='';const current=epoch;try{const result=await previewImport(selectedBatch.value,item.document_id);if(current===epoch&&(qualityOpen.value||(view.value==='upload'&&uploadStage.value===2))&&qualityItem.value?.version_id===item.version_id)preview.value=result}catch(e){if(current===epoch)failure(e)}}
function closeQuality(){if(busy.value)return;qualityOpen.value=false;preview.value=null;qualityItem.value=null}
async function confirmQuality(){const item=qualityItem.value;if(!item||checks.value.length!==4||qualityNote.value.trim().length<3)return;await act(()=>maintenanceAction('review_import',{...args(item),checks:checks.value,note:qualityNote.value.trim()}),'本版本质量核对已保存，发布需要单独确认。');if(!error.value){closeQuality();if(view.value==='upload')uploadStage.value=3}}
async function publish(item:ImportItem){
  const operation=item.publication_status==='Withdrawn'?'restore':item.current_version&&item.current_version!==item.version_id?'replace':'publish'
  const reason=operationReason.value.trim()
  if(operation!=='publish'&&reason.length<3){error.value='换版或恢复前请填写至少三个字的操作原因。';return}
  await act(()=>maintenanceAction('publish_import',{
    batch_id:selectedBatch.value,document_ids:[item.document_id],operation,
    expected_version:item.current_version,reason:reason||undefined,
    expected_lifecycle_receipt:operation==='restore'?item.lifecycle_receipt_id||undefined:undefined,
  }),'发布状态已更新，员工可按当前授权版本查询。')
}
async function withdraw(item:ImportItem){
  const reason=operationReason.value.trim()
  if(reason.length<3){error.value='下架前请填写至少三个字的操作原因。';return}
  await act(()=>maintenanceAction('withdraw_import',{
    ...args(item),expected_version:item.current_version,reason,
    expected_lifecycle_receipt:item.lifecycle_receipt_id||undefined,
  }),'资料已下架，旧来源与收藏将立即重新核验。')
}
async function queue(item:ImportItem){await act(()=>maintenanceAction('queue_import',{batch_id:selectedBatch.value,document_ids:[item.document_id],operation:item.parse_status==='parse_failed'?'retry':'parse'}),'解析已排队，请刷新查看实际处理进度。')}
// A document opened from the published list may live in another batch, so the
// lookup still spans batches. Each request names the document and the server
// returns the page it sits on, so a batch costs one request instead of one per
// page: the old sweep measured 63 requests / 42 s end to end.
const DETAIL_SCAN_MAX_BATCHES=6
function matchesDoc(item:ImportItem,doc:{document_id:string;version_id?:string}){
 return item.document_id===doc.document_id&&(!doc.version_id||item.version_id===doc.version_id)&&item.relationship!=='SAME_CONTENT_SKIP'
}
function findLoaded(doc:{document_id:string;version_id?:string}){
 return (data.value?.selected?.items||[]).find(i=>matchesDoc(i,doc))||null
}
function batchLookupMetadataPresent(result:MaintenanceDashboard){
 return result.batch_lookup_state!==undefined||result.batches_matched!==undefined||result.batch_query!==undefined||result.batch_document_id!==undefined
}
/**
 * Bounded server locate: one `batch_document_id` query names the batch and the
 * page inside it, then the existing `batch_id + locate=document_id` request
 * opens that page. Only an older response without lookup metadata falls back to
 * the previous 6-batch scan, so legacy behaviour stays compatible.
 */
async function locateBatchForDocument(doc:{document_id:string;version_id?:string},current:number){
 let located:MaintenanceDashboard
 try{located=await getMaintenance(undefined,1,undefined,{batch_document_id:doc.document_id,batch_page:1,batch_page_size:100})}
 catch(e){if(accessDenied(e))throw e;return undefined}
 if(current!==epoch||!detailOpen.value)return null
 if(!batchLookupMetadataPresent(located))return undefined
 if(located.batch_lookup_state==='NOT_FOUND'){detailLookupState.value='NOT_FOUND';return null}
 const entry=located.batches[0]
 if(located.batch_lookup_state!=='FOUND'||!entry)return null
 const targetPage=entry.document_page&&entry.document_page>0?entry.document_page:1
 const result=await getMaintenance(entry.name,targetPage,doc.document_id)
 if(current!==epoch||!detailOpen.value)return null
 const item=result.selected?.items.find(i=>matchesDoc(i,doc))
 if(!item)return null
 selectedBatch.value=entry.name;page.value=result.selected?.page||targetPage;data.value=result;detailLookupState.value='FOUND'
 return item
}
async function findAcrossBatches(doc:{document_id:string;version_id?:string},current:number){
 const located=await locateBatchForDocument(doc,current)
 if(located!==undefined)return located
 const batches=(data.value?.batches||[]).slice(0,DETAIL_SCAN_MAX_BATCHES)
 for(const candidate of batches){
  let result
  try{result=await getMaintenance(candidate.name,1,doc.document_id)}catch{continue}
  if(current!==epoch||!detailOpen.value)return null
  const item=result.selected?.items.find(i=>matchesDoc(i,doc))
  if(item){selectedBatch.value=candidate.name;page.value=result.selected?.page||1;data.value=result;return item}
 }
 return null
}
async function openDetails(doc:{title:string;document_id:string;version_id?:string;current_version?:string;department?:string;document_number?:string|null;item?:ImportItem}){
 detailOpen.value=true;detail.value=null;detailTitle.value=doc.title;detailLoading.value=true;operationReason.value='';detailLookupState.value=null;const current=epoch
 detailTarget.value={document_id:doc.document_id,version_id:doc.version_id||'',current_version:doc.current_version||'',title:doc.title,department:doc.department||'',document_number:doc.document_number}
 try{
  if(doc.item){detail.value=doc.item;return}
  // A document opened from the page it is already listed on needs no request.
  // The old sweep re-read the whole dashboard once per page of every batch to
  // find a row that was, in most cases, already in hand.
  const loaded=findLoaded(doc);if(loaded){detail.value=loaded;return}
  const found=await findAcrossBatches(doc,current)
  if(found){detail.value=found;return}
 }catch(e){if(current===epoch)failure(e)}finally{if(current===epoch)detailLoading.value=false}
}
async function newRevision(){
 const documentId=detail.value?.document_id
 const target=data.value?.published_documents.find(d=>d.document_id===documentId)
  ||(detailTarget.value?.document_id===documentId?detailTarget.value:undefined)
  ||publishedLookup.value?.documents.find(d=>d.document_id===documentId)
  ||(selectedPublished.value?.document_id===documentId?selectedPublished.value:undefined)
 if(!target)return
 department.value=target.department;await nextTick();replacement.value=target;uploadStage.value=0;detailOpen.value=false;await router.push('/hbos/knowledge/maintenance/upload')
}
function openFeedback(item:MaintenanceFeedback){selectedFeedback.value=item;reply.value=item.maintenance_reply||item.reply||'';feedbackOpen.value=true}
async function reviewFeedback(status:string){const item=selectedFeedback.value;if(!item)return;await act(()=>maintenanceAction('review_feedback',{activity_id:item.id,status,reply:reply.value}),'反馈处理已保存，提交人可查看状态和回复。');if(!error.value){feedbackOpen.value=false;await refreshFeedback()}}
async function revalidate(){const current=epoch;try{const status=await getKnowledgeStatus();if(current!==epoch)return;allowed.value=Boolean(status.can_maintain);permissionDenied.value=!allowed.value;if(!allowed.value){failure(new DomainApiError('FORBIDDEN','当前账号没有知识维护权限。'));return}clearPublishedLookup();clearBatchLookup();replacementLookupDocs.value=[];replacementLookupError.value='';detailLookupState.value=null;await refresh();if(view.value==='feedback')await refreshFeedback()}catch(e){failure(e)}finally{if(current===epoch)initialized.value=true}}
watch(()=>props.sessionRevision,()=>{void revalidate()})
onMounted(() => { document.addEventListener('click', rememberInteraction, true); void revalidate() })
onBeforeUnmount(()=>{document.removeEventListener('click', rememberInteraction, true);clearDrawerTimers();epoch++;readSequence++;feedbackSequence++;stopProgressTimer()})
</script>
<template>
 <div class="maintenance-page">
  <header class="kb-heading">
    <div><small class="kb-eyebrow">{{ heading.eyebrow }}</small><h1>{{ heading.title }}</h1><p>{{ heading.description }}</p></div>
    <a-button v-if="view==='upload'" class="v17-return" aria-label="返回资料管理" @click="router.push('/hbos/knowledge/maintenance')"><ArrowLeftOutlined/><span>返回资料管理</span></a-button>
    <a-button v-else-if="view==='manage' || view==='versions'" type="primary" class="v17-add"
      :aria-label="view==='versions' ? '上传新修订版' : '新增资料'" @click="uploadStage=0;router.push('/hbos/knowledge/maintenance/upload')">
      <UploadOutlined v-if="view==='versions'"/><PlusOutlined v-else/><span>{{ view==='versions' ? '上传新修订版' : '新增资料' }}</span>
    </a-button>
  </header>
  <a-alert v-if="error" type="error" :message="error" show-icon class="kb-alert"/><a-alert v-if="notice" type="success" :message="notice" show-icon class="kb-alert"/>
  <a-skeleton v-if="!initialized" active/>
  <a-result v-else-if="permissionDenied" status="403" title="当前账号没有知识维护权限" sub-title="请使用获分配维护权限的本人账号登录。"/>
  <div v-else-if="!allowed" class="v17-permission-unknown" role="alert"><p>维护权限状态暂时无法确认，这不是“没有权限”。当前网络或知识状态接口暂时不可用。</p><a-button size="small" @click="revalidate">重试</a-button></div>
  <template v-else>
   <template v-if="view==='manage'">
    <div class="v17-stats" aria-label="资料概览">
     <button v-for="stat in overviewStats" :key="stat.key" type="button" class="v17-stat"
      :aria-pressed="stat.key==='feedback'?undefined:overviewStatus===stat.key" @click="toggleOverviewStatus(stat.key)">
      <small>{{stat.title}}</small><strong>{{stat.value ?? '—'}}</strong><span>{{stat.caption}}</span>
     </button>
    </div>
    <section class="v17-panel" aria-label="资料清单">
     <div class="v17-panel-heading"><div><h2>资料清单</h2><p>当前资料与处理状态集中核对</p></div><div class="v17-batch"><span>受控清单批量导入</span><button ref="batchEntry" type="button" @click="openBatchPreview"><UploadOutlined aria-hidden="true"/> 打开批量预演</button><small>先预演，识别重复、换版、异常与需补原件项</small></div></div>
     <details class="v17-guide"><KnowledgeDisclosureSummary>发布前的三项检查</KnowledgeDisclosureSummary><div class="v17-guide-grid"><p><strong>保留原件与身份</strong><br>确认新增或换版关系</p><p><strong>核对解析质量</strong><br>正文、数字、表格与文件身份</p><p><strong>批准共享并发布</strong><br>质量通过不等于获准共享</p></div></details>
     <form class="v17-filters" @submit.prevent="searchPublished(1)">
      <label class="v17-search">
       <SearchOutlined aria-hidden="true"/>
       <input v-model="publishedSearch" placeholder="标题、文号、部门或文档 ID" aria-label="服务端查找资料"/>
       <button type="submit" data-published-search :disabled="publishedLookupLoading" aria-label="搜索资料"><SearchOutlined aria-hidden="true"/></button>
      </label>
      <PortalSelect v-model:value="departmentFilter" aria-label="筛选已加载资料部门" :options="[{value:'',label:'全部已共享资料'},...(data?.departments.map(dept=>({value:dept.key,label:dept.title}))||[])]"/>
      <button v-if="publishedLookup" type="button" @click="clearPublishedLookup">清除搜索</button>
      <button v-if="overviewStatus" type="button" @click="overviewStatus=null;listPage=1">清除状态筛选</button>
     </form>
     <p class="v17-hint">已发布资料在版本详情中维护；只有已解析的待发布资料可批量选择。部门和状态筛选仅作用于已加载资料。</p>
     <p v-if="!publishedLookup&&data?.published_truncated" class="v17-hint" data-v17-published-projection>服务端仅投影前 {{data?.published_page_size||data?.published_documents?.length||0}} 份，可在上方搜索定位。</p>
     <p v-if="publishedLookupError" role="alert">{{publishedLookupError}}</p>
     <a-alert v-if="publishedLookup?.state==='NOT_FOUND'" type="warning" show-icon class="kb-alert" data-v17-published-not-found message="没有找到该文档 ID 对应的已发布资料；请核对文档标识，或改用标题/文号搜索。"/>
     <p v-else-if="publishedLookup&&!publishedLookup.documents?.length&&!loading" class="v17-hint" data-v17-published-empty>没有匹配的已发布资料，请调整关键词或改用精确文档 ID。</p>
     <div v-if="selectedItems.length" class="v17-actions">
      <span>已选 {{selectedItems.length}} 份</span>
      <button type="button" :disabled="busy" @click="openBulkQuality">核对质量</button>
      <a-popconfirm title="确认所选资料获准内部共享？" @confirm="approveSharingSelected">
       <button type="button" :disabled="busy||!canApproveSharing">批准共享</button>
      </a-popconfirm>
      <a-popconfirm title="确认向员工发布所选资料？" @confirm="publishSelected">
       <button type="button" :disabled="busy||!canPublishSelected">发布所选</button>
      </a-popconfirm>
      <button type="button" @click="selectedIds=[]">取消选择</button>
     </div>
     <div class="v17-table-wrap"><table><thead><tr><th><input type="checkbox" aria-label="选择本页可处理资料" :disabled="!overviewRows.some(row=>canSelectRow(row.document_id))" @change="(event:any)=>{selectedIds=event.target.checked ? overviewRows.filter(row=>canSelectRow(row.document_id)).map(row=>row.document_id):[]}" /></th><th>资料名称</th><th>状态</th><th>部门 / 版本</th><th>操作</th></tr></thead><tbody><tr v-for="doc in overviewRows" :key="doc.document_id+doc.version_id"><td><input type="checkbox" :aria-label="'选择 '+doc.title" :disabled="!canSelectRow(doc.document_id)" :checked="selectedIds.includes(doc.document_id)" @change="(event:any)=>toggleSelected(doc.document_id,event.target.checked)" /></td><td><button class="v17-title" type="button" @click="openDetails(doc)">{{doc.title}}<small>{{doc.document_number || ''}}</small></button></td><td><span class="v17-tag">{{doc.status}}</span></td><td>{{departmentName(doc.department)}}<small>{{doc.version_id}}</small></td><td><button class="v17-view" type="button" @click="openDetails(doc)">查看</button></td></tr></tbody></table></div>
     <p v-if="!loading&&!overviewRows.length&&!publishedLookup" class="v17-hint">当前范围没有资料，可调整筛选或新增资料。</p>
     <div class="v17-pagination"><span>{{publishedLookup ? `匹配 ${publishedLookup.matched} 份` : `已加载 ${overviewMatches.length} 份`}} · 第 {{publishedLookup?.page || listPage}} 页</span><div><button :disabled="publishedLookup ? publishedLookup.page<=1 : listPage<=1" @click="publishedLookup ? changePublishedPage(publishedLookup.page-1) : listPage--">上一页</button><button :disabled="publishedLookup ? !publishedLookup.hasMore : listPage*6>=overviewMatches.length" @click="publishedLookup ? changePublishedPage(publishedLookup.page+1) : listPage++">下一页</button></div></div>
    </section>
   </template>
   <component :is="view==='manage' ? 'a-drawer' : 'div'" v-if="view==='versions' || (view==='manage' && legacyOpen)" :open="legacyOpen" @after-open-change="onLegacyDrawerOpenChange" title="批量处理与任务" width="min(600px, calc(100vw - 24px))" root-class-name="v17-batch-drawer kb-drawer kb-scope kb-inset-drawer" @close="closeBatchPreview">

   <details v-if="view==='manage'&&data?.department_funnel?.length" class="kb-panel hbos-glass-g1 maintenance-funnel"><KnowledgeDisclosureSummary>部门资料处理统计</KnowledgeDisclosureSummary><section class="funnel-grid" aria-label="部门资料处理统计"><article v-for="row in data.department_funnel" :key="row.department" class="kb-panel hbos-glass-g1"><h2>{{row.title}}</h2><dl><template v-for="stat in [{key:'discovered',label:'发现资料（去重）'},{key:'shared_approved',label:'获准共享'},{key:'uploaded',label:'已上传'},{key:'parsed',label:'已解析'},{key:'validated',label:'质量已核对'},{key:'published',label:'已发布（逻辑文档）'},{key:'pending_review',label:'待审核'},{key:'failed',label:'解析失败'},{key:'isolated',label:'隔离'},{key:'sharing_pending',label:'共享待批'}] as const" :key="stat.key"><div><dt>{{stat.label}}</dt><dd>{{row[stat.key]}}</dd></div></template></dl><p v-if="row.sensitive" class="kb-muted">隔离中 {{row.sensitive}} 项涉及敏感内容。</p></article></section></details>
   <section v-if="view==='manage'&&showAdvancedImport" class="kb-panel hbos-glass-g1 batch-import-panel" aria-label="既有受控清单任务">
    <h2>批量预演与入库</h2>
    <p class="kb-muted">先对受控清单（JSON）做只读预演，确认每份资料是新文件、重复、换版、技术修复或异常，再按预演摘要提交。资料按已核准的原件和处理方式分批登记；预演不会开始解析或发布。</p>
    <a-alert v-if="!batchAvailable()" type="warning" show-icon message="批量预演尚未配置（缺少来源白名单或派生文件共享目录），当前只能使用单文件新增资料。"/>
    <template v-if="batchAvailable()">
     <label class="batch-manifest-picker"><UploadOutlined/><strong>{{batchManifestName||'选择清单 JSON 文件'}}</strong><span>获准资料与处理说明 · 单批最多 64 项</span><input type="file" accept=".json,application/json" aria-label="选择批量入库清单" @change="chooseManifest"/></label>
     <button type="button" class="kb-disclosure-summary batch-disclosure" :disabled="batchActionBusy"
       :aria-expanded="batchManifestOpen" aria-controls="kb-batch-manifest-text" @click="batchManifestOpen=!batchManifestOpen">
       <span class="kb-disclosure-mark" aria-hidden="true">{{ batchManifestOpen ? '−' : '＋' }}</span>
       <span>直接粘贴清单 JSON</span><span class="kb-disclosure-state" aria-hidden="true">{{ batchManifestOpen ? '收起' : '展开' }}</span>
     </button>
     <a-textarea v-show="batchManifestOpen" id="kb-batch-manifest-text" v-model:value="batchManifestText" :auto-size="{minRows:6,maxRows:14}" placeholder='{"schema_version":2,"department":"production","sharing_confirmed":true,"items":[…]}' class="batch-manifest-text"/>
     <div class="batch-toolbar"><a-button type="primary" :disabled="batchActionBusy||!batchManifestText.trim()" :loading="batchActionBusy" @click="previewBatch">预演清单</a-button><span class="kb-muted">只读预演，不写入任何资料。</span></div>
     <a-alert v-if="batchPlanError" type="error" :message="batchPlanError" show-icon class="kb-alert"/>
     <template v-if="batchPlan">
      <div class="batch-summary"><a-tag :color="batchPlan.submittable?'green':'red'">{{batchPlan.submittable?'可提交':'存在阻断项'}}</a-tag><span v-for="key in ['total','new','duplicate','business_update','technical_repair','new_upload_required','anomaly'] as const" :key="key" class="batch-count">{{key==='total'?'合计':(planNames[(key==='business_update'?'BUSINESS_UPDATE':key==='technical_repair'?'TECHNICAL_REPAIR':key==='new_upload_required'?'NEW_UPLOAD_REQUIRED':key==='anomaly'?'ANOMALY':key==='duplicate'?'DUPLICATE':'NEW')]||key)}} {{batchPlan.counts[key]||0}}</span><code class="batch-digest">plan_sha256 {{batchPlan.plan_sha256}}</code></div>
      <div class="batch-plan-rows"><article v-for="item in batchPlan.items" :key="item.index" class="batch-plan-row"><div class="batch-plan-main"><strong>{{item.title}}</strong><span class="kb-muted">{{item.department}} · {{item.target.title}} · {{item.pages}} 页 · {{item.page_methods.join(' / ')||'页面方法未提供'}}</span><small v-if="!item.submittable" class="batch-block">{{item.conflict_reason||'不可编排'}}<template v-if="item.detail">：{{item.detail}}</template></small></div><a-tag :color="planColors[item.disposition]">{{planNames[item.disposition]}}</a-tag></article></div>
      <p v-if="batchPlan.blocking_anomalies" class="kb-muted">仍有 {{batchPlan.blocking_anomalies}} 项阻断：异常、待上传或需既有流程的资料不会被提交。请修正清单后重新预演。</p>
      <div class="batch-submit"><label>批准引用<a-input v-model:value="batchApproval" :maxlength="200" placeholder="例如 OWNER_RC13_20261027_BATCH_A"/></label><label>批次名称<a-input v-model:value="batchLabel" :maxlength="160" placeholder="可选，用于维护列表"/></label><label class="batch-confirmation"><input v-model="batchConfirmed" type="checkbox" :disabled="batchSubmitting" data-batch-confirmation />已核对本次预演结果和批准依据</label><a-button type="primary" :disabled="!batchPlan.submittable||!batchConfirmed||batchApproval.trim().length<3||batchSubmitting" :loading="batchSubmitting" @click="submitBatch">提交批量入库</a-button></div>
     </template>
     <template v-if="batchReceipt">
      <h3>已登记批次</h3>
      <p class="kb-muted">同一预演摘要重复提交只会返回原批次，不会重复上传、嵌入或发布{{batchReceipt.replayed?'（本次为重放）':''}}。</p>
      <div class="batch-receipt"><article v-for="entry in batchReceipt.batches" :key="entry.batch_id"><code>{{entry.batch_id}}</code><span>{{entry.department}} · {{entry.documents}} 份 · 排队 {{entry.queued_documents}} 份 · {{entry.kind==='duplicate'?'重复登记':'解析处理'}}</span><a-button size="small" @click="progressBatchId=entry.batch_id">查看进度</a-button></article></div>
     </template>
     <template v-if="batchProgress">
      <div class="batch-progress-head"><h3>批次进度</h3><span>{{batchProgress.batch_id}} · {{batchProgress.status}}<template v-if="batchProgress.job"> · 任务 {{batchProgress.job.status}} · 租约代数 {{batchProgress.job.lease_generation}}<template v-if="batchProgress.job.pause_requested"> · 已请求暂停</template><template v-if="batchProgress.job.lease_expired"> · 租约已过期</template></template></span><a-button size="small" :disabled="batchActionBusy" @click="refreshBatchProgress()">刷新进度</a-button></div>
      <p v-if="batchProgress.job?.status==='Running'" class="kb-muted">处理中，每 4 秒自动刷新一次进度；完成后停止轮询。</p>
      <p v-else class="kb-muted">仅在任务运行中自动轮询；当前状态需手动刷新。</p>
      <div class="batch-actions"><a-button :disabled="batchActionBusy||!canPauseBatch" @click="pauseBatch">暂停</a-button><a-button :disabled="batchActionBusy||!canResumeBatch" @click="resumeBatch">恢复</a-button><label>回收原因<a-input v-model:value="batchReclaimReason" :maxlength="200" placeholder="回收过期租约前填写原因"/></label><a-button danger :disabled="batchActionBusy||!canReclaimBatch" @click="reclaimBatch">回收过期租约</a-button></div>
      <div class="batch-progress-rows"><article v-for="item in batchProgress.items" :key="item.version_id" class="batch-progress-row"><div class="batch-plan-main"><strong>{{item.title}}</strong><span class="kb-muted">{{parseNamesForBatch[item.status]||item.status}} · 发布状态 {{item.publication_status}}<template v-if="item.error_code"> · 错误码 {{item.error_code}}</template></span><small v-if="item.retrieval_verified?.reason" class="kb-muted">检索收据失效原因：{{receiptReasons[item.retrieval_verified.reason]||item.retrieval_verified.reason}}</small></div><a-tag v-if="item.retrieval_verified" :color="receiptColor(item)">{{receiptLabel(item)}}</a-tag><a-tag v-else color="default">未发布/未验证</a-tag><a-button v-if="item.status==='parse_failed'" size="small" :loading="batchRetryId===item.document_id" :disabled="Boolean(batchRetryId)" @click="retryBatchItem(item)">重试</a-button></article></div>
      <p class="kb-muted">「检索已验证」只在服务端核验到真实员工检索与来源解析记录后写入；维护页不能勾选或声明该收据。撤回或换版后收据标记失效但不删除历史。</p>
     </template>
    </template>
   </section>
   <details v-if="view==='manage'" class="kb-panel hbos-glass-g1 maintenance-batch-entry"><KnowledgeDisclosureSummary>批量新增与处理任务</KnowledgeDisclosureSummary><KnowledgeBatchMaintenance :session-revision="props.sessionRevision" @select-batch="selectManagedBatch" @select-version="openManagedVersion"/></details>
   <section v-if="view==='manage'||view==='versions'" class="kb-panel hbos-glass-g1">

    <div v-if="view==='versions'" class="v17-panel-heading v17-legacy-heading"><div><h2>版本档案</h2><p>先核对资料身份，再查看版本沿革与发布状态。</p></div><span class="v17-panel-count">{{publishedLookup ? publishedLookup.matched : (data?.published_total ?? managed.length)}} 份</span></div>
    <div v-show="view==='versions'" class="v17-version-list">
    <div class="v17-version-toolbar">
     <form class="v17-version-search" role="search" @submit.prevent="searchPublished(1)">
      <SearchOutlined aria-hidden="true"/>
      <input v-model="publishedSearch" type="search" placeholder="查找资料标题、文号或精确文档 ID" aria-label="服务端查找已发布资料" data-published-query/>
      <button type="submit" :disabled="publishedLookupLoading" data-published-search aria-label="查找"><SearchOutlined aria-hidden="true"/></button>
     </form>
     <a-button v-if="publishedLookup" :disabled="publishedLookupLoading" data-published-reset @click="clearPublishedLookup">返回默认列表</a-button>
     <details class="v17-version-more">
      <KnowledgeDisclosureSummary>更多筛选</KnowledgeDisclosureSummary>
      <div class="v17-version-more-body">
       <PortalSelect v-model:value="departmentFilter" :options="[{label:'全部部门',value:''},...(data?.departments.map(d=>({label:d.title,value:d.key}))||[])]" aria-label="筛选维护部门"/>
       <button v-if="departmentFilter" type="button" @click="departmentFilter=''">清除部门筛选</button>
       <button type="button" class="v17-version-refresh" :disabled="loading" @click="refresh"><ReloadOutlined/>刷新资料</button>
       <span v-if="data" class="v17-version-projection" data-published-projection>当前显示 {{data.published_documents.length}} 份 · 第 {{data.published_page||1}} 页<template v-if="data.published_has_more"> · 还有更多</template><template v-if="publishedTruncated"> · 服务端仅投影前 {{data?.published_page_size||data?.published_documents.length||0}} 份，可用上方查找定位</template></span>
      </div>
     </details>
    </div>
    <p class="v17-version-note" data-version-note>当前与历史版本分开核验 · 已发布 {{data ? publishedTotal : '—'}} 份</p>
    <a-alert v-if="publishedLookupError" type="warning" show-icon :message="publishedLookupError" class="kb-alert"/>
    <p v-if="publishedLookup" class="kb-muted" data-published-lookup-meta>服务端匹配 {{publishedLookup.matched}} 份 / 共 {{publishedLookup.total}} 份 · 第 {{publishedLookup.page}} 页 · 每页 {{publishedLookup.pageSize}} 条<template v-if="publishedLookup.hasMore"> · 还有更多</template></p>
    <a-skeleton v-if="loading" active :paragraph="{rows:4}"/>
    <template v-else>
     <a-alert v-if="publishedLookup?.state==='NOT_FOUND'" type="warning" show-icon class="kb-alert" data-published-not-found message="没有找到该文档 ID 对应的已发布资料；请核对文档标识，或改用标题/文号搜索。"/>
     <a-alert v-else-if="publishedLookup&&!publishedLookup.documents.length" type="info" show-icon class="kb-alert" data-published-empty message="没有匹配的已发布资料，请调整关键词或改用精确文档 ID。"/>
     <article v-for="doc in visibleDocs" :key="doc.document_id" class="kb-doc-row v17-version-row"><div class="kb-doc-icon"><FileTextOutlined/></div><button class="kb-doc-main" @click="openDetails(doc)"><strong>{{doc.title}}</strong><p>{{doc.item?relationships[doc.item.relationship]||'资料处理记录':'当前已共享资料，查看解析质量与版本状态。'}}</p><small>{{[departmentName(doc.department), doc.document_number, doc.version_id].filter(Boolean).join(' · ')}} <a-tag :color="doc.status==='已发布'?'green':'default'">{{doc.status}}</a-tag></small></button><a-button size="small" :aria-label="'查看版本 '+doc.title" @click="openDetails(doc)"><FileTextOutlined/><span class="v17-version-view-label">查看版本</span></a-button></article>
     <a-empty v-if="!visibleDocs.length&&!publishedLookup" description="当前筛选没有资料。"/>
    </template>
    <div v-if="publishedLookup" class="kb-pagination"><a-button :disabled="publishedLookup.page<=1||publishedLookupLoading" data-published-prev @click="changePublishedPage(publishedLookup.page-1)">上一页</a-button><span>第 {{publishedLookup.page}} 页 · 共 {{publishedLookup.matched}} 份匹配</span><a-button :disabled="!publishedLookup.hasMore||publishedLookupLoading" data-published-next @click="changePublishedPage(publishedLookup.page+1)">下一页</a-button></div>
    <div v-else-if="managed.length>4" class="kb-pagination"><a-pagination v-model:current="listPage" :total="managed.length" :page-size="4" :show-size-changer="false"/></div>
    <details v-if="view==='versions'" class="v17-version-lineage">
     <KnowledgeDisclosureSummary>版本沿革与回滚候选</KnowledgeDisclosureSummary>
     <div class="v17-version-lineage-head"><p class="kb-muted">候选契约 GET get_version_lineage：只展示服务端返回的版本链，不推断；真实服务可用性未在本机验证。</p><PortalSelect v-model:value="lineageDocumentId" :options="lineageOptions" aria-label="选择资料查看版本沿革" style="width:min(320px,100%)"/></div>
     <a-skeleton v-if="lineageLoading" active :paragraph="{rows:3}"/>
     <a-alert v-else-if="lineageError" type="warning" show-icon class="kb-alert" data-v17-lineage-unavailable :message="lineageError"/>
     <template v-else-if="lineage">
      <p class="kb-muted" data-v17-lineage-meta>当前版本 {{lineage.current_version}} · 共 {{lineage.total}} 个版本 · 第 {{lineage.page}} 页<template v-if="lineage.has_more"> · 还有更多</template></p>
      <div class="v17-table-wrap"><table data-v17-lineage-list><thead><tr><th>版本</th><th>发布状态</th><th>质量状态</th><th>回滚候选</th><th>前序 / 后继</th><th>创建时间</th></tr></thead><tbody><tr v-for="entry in lineage.versions" :key="entry.version_id" data-v17-lineage-row><td>{{entry.version_id}}</td><td>{{entry.publication_state}}</td><td>{{entry.quality_state}}</td><td>{{entry.rollback_eligible?'是':'否'}}</td><td>{{entry.supersedes||'—'}} / {{entry.superseded_by||'—'}}</td><td>{{entry.created_at||'—'}}</td></tr></tbody></table></div>
     </template>
     <p v-else class="kb-muted">选择资料后显示服务端版本沿革。</p>
    </details>
    </div>

    <details><KnowledgeDisclosureSummary>批次审核与发布</KnowledgeDisclosureSummary><p class="kb-muted">选择同一批次的解析完成资料核对质量。共享待批资料需另行确认，未解析、隔离或换版资料需分别处理。</p>
     <div class="kb-maintenance-lookup"><a-input-search v-model:value="batchSearch" placeholder="服务端查找：批次名称、部门，或按精确文档 ID 定位" aria-label="服务端查找批次" data-batch-query @search="searchBatches(1)"/><a-button :loading="batchLookupLoading" data-batch-search @click="searchBatches(1)">查找</a-button><a-button :loading="batchLookupLoading" data-batch-locate @click="locateBatchFromInput">按文档定位</a-button><a-button v-if="batchLookup" :disabled="batchLookupLoading" data-batch-reset @click="clearBatchLookup">恢复默认列表</a-button></div>
     <a-alert v-if="batchLookupError" type="warning" show-icon :message="batchLookupError" class="kb-alert"/>
     <p class="kb-muted" data-batch-meta>共 {{batchesTotal}} 个批次 · 当前显示 {{batchOptions.length}} 个<template v-if="batchLookup"> · 服务端匹配 {{batchLookup.matched}} 个 · 第 {{batchLookup.page}} 页<template v-if="batchLookup.hasMore"> · 还有更多</template><template v-if="batchLookup.scanTruncated"> · 服务端仅扫描前 1000 个批次</template></template><template v-else> · 第 {{data?.batches_page||1}} 页<template v-if="data?.batches_has_more"> · 还有更多（可用上方查找或下一页）</template><template v-if="data?.batch_scan_truncated"> · 服务端仅扫描前 1000 个批次</template></template></p>
     <a-alert v-if="batchLookup?.state==='NOT_FOUND'" type="warning" show-icon class="kb-alert" data-batch-not-found message="没有找到包含该文档的处理批次；该资料可能来自历史批次，仍可查看当前版本。"/>
     <PortalSelect v-model:value="selectedBatch" :disabled="busy" style="width:100%" placeholder="选择处理任务" :options="batchOptions.map(b=>({value:b.name,label:b.label}))" @change="changeBatch"/>
     <div v-if="batchLookup" class="kb-pagination"><a-button :disabled="batchLookup.page<=1||batchLookupLoading" data-batch-prev @click="changeBatchPage(batchLookup.page-1)">上一页</a-button><span>第 {{batchLookup.page}} 页 · 共 {{batchLookup.matched}} 个匹配</span><a-button :disabled="!batchLookup.hasMore||batchLookupLoading" data-batch-next @click="changeBatchPage(batchLookup.page+1)">下一页</a-button></div>
     <div v-else-if="data?.batches_has_more" class="kb-pagination"><a-button disabled data-batch-default-prev>上一页</a-button><span>第 {{data?.batches_page||1}} 页 · 共 {{batchesTotal}} 个批次</span><a-button :disabled="batchLookupLoading||!data?.batches_has_more" data-batch-default-next @click="searchBatches((data?.batches_page||1)+1)">下一页</a-button></div>
     <p v-if="batch" class="kb-muted">{{batch.total}} 项 · 解析完成 {{batch.counts.parsed}} · 待核对 {{batch.total-batch.counts.quality_passed}}</p><div v-if="batch" class="bulk-toolbar"><a-button :disabled="busy||!selectable.length" @click="selectedIds=selectable.map(i=>i.document_id)">选择本页解析完成候选</a-button><span>已选 {{selectedItems.length}} 项</span><a-button :disabled="busy||!selectedItems.length" @click="openBulkQuality">批量核对质量</a-button><a-popconfirm v-if="canApproveSharing" title="确认所选资料已获准内部共享，且不含未批准的个人、保密或受限内容？本操作保留原待批记录。" ok-text="确认获准共享" cancel-text="取消" @confirm="approveSharingSelected"><a-button :disabled="busy||!canApproveSharing">确认所选已获准共享</a-button></a-popconfirm><a-popconfirm :title="'确认所选 '+selectedItems.length+' 份已获准共享且质量合格，发布到当前候选？'" ok-text="确认发布" cancel-text="取消" @confirm="publishSelected"><a-button type="primary" :disabled="busy||!canPublishSelected">发布所选资料</a-button></a-popconfirm></div><article v-for="item in batch?.items" :key="item.version_id" class="advanced-row"><a-checkbox v-if="selectable.some(i=>i.document_id===item.document_id)" :checked="selectedIds.includes(item.document_id)" :disabled="busy" :aria-label="'选择资料：'+item.title" @change="(event:any)=>toggleSelected(item.document_id,event.target.checked)"/><span>{{item.title}} · {{parseNames[item.parse_status]}}{{item.shared_approved===false?' · 共享待批':''}}</span><a-button @click="detail=item;detailTitle=item.title;detailOpen=true">查看</a-button></article><a-pagination v-if="batch" v-model:current="page" :total="batch.total" :page-size="12" :show-size-changer="false" @change="refresh"/></details>
   </section>
   </component>
   <section v-if="view==='upload'" class="v17-panel v17-upload" aria-label="新增资料工作区">
    <ol class="v17-steps" aria-label="资料发布步骤">
     <li v-for="(label,index) in uploadSteps" :key="label" :class="{done:index<uploadStage}" :aria-current="index===uploadStage?'step':undefined">
      <span aria-hidden="true">0{{index+1}}</span>{{label}}
     </li>
    </ol>
    <template v-if="uploadStage===0">
     <div class="v17-upload-grid v17-upload-identity">
      <div>
       <label for="upload-department">归属部门</label>
       <PortalSelect id="upload-department" v-model:value="department" :options="data?.departments.map(d=>({value:d.key,label:d.title}))||[]" aria-label="上传资料所属部门"/>
      </div>
      <div>
       <label for="upload-replacement">新增还是换版</label>
       <PortalSelect id="upload-replacement" searchable :value="replacement?.document_id||''" :options="[{value:'',label:'新增独立资料'},...replacementOptions.map(i=>({value:i.document_id,label:'替换：'+i.title}))]" aria-label="新增还是换版" @change="selectReplacement" />
       <details class="v17-version-lookup">
        <KnowledgeDisclosureSummary>查找更多已发布版本</KnowledgeDisclosureSummary>
        <div class="kb-maintenance-lookup" data-replacement-lookup>
         <a-input-search v-model:value="replacementSearch" placeholder="标题、文号或精确文档 ID" aria-label="服务端查找换版目标" @search="searchReplacementDocs"/>
         <a-button :loading="replacementLookupLoading" data-replacement-search @click="searchReplacementDocs">查找</a-button>
        </div>
        <p v-if="replacementLookupError" role="alert" data-replacement-error>{{replacementLookupError}}</p>
        <p v-else-if="replacementLookupDocs.length" data-replacement-hint>找到 {{replacementLookupDocs.length}} 份本部门已发布资料，已加入上方“版本关系”选项。</p>
       </details>
      </div>
     </div>
     <div class="v17-upload-grid v17-upload-content">
      <section>
       <h2 ref="uploadStageHeading" tabindex="-1">选择原件</h2>
       <label class="v17-upload-drop" @dragover.prevent @drop.prevent="dropOriginal">
        <UploadOutlined aria-hidden="true"/>
        <strong>{{file?.name||'选择或拖入一份文件'}}</strong>
        <small>PDF、Word、Excel、PowerPoint 或文本 · 不超过 {{uploadSizeLabel}}</small>
        <input type="file" accept=".pdf,.doc,.docx,.xlsx,.pptx,.txt,.md" aria-label="选择资料文件" @change="chooseFile"/>
       </label>
       <label v-if="pdfTemplateChoices.length" class="version-label">解析方式
        <PortalSelect v-model:value="parseTemplate" :options="pdfTemplateChoices.map(t=>({value:t.key,label:t.title}))" aria-label="PDF解析方式"/>
       </label>
      </section>
      <section class="v17-sharing v17-sharing-original">
       <h2>确认共享范围</h2>
       <p>完成解析和四项质量核对后，还需确认发布。</p>
       <a-checkbox v-model:checked="sharing">我已确认本次资料获准内部共享</a-checkbox>
       <p class="v17-upload-safety">选择换版时，当前已发布版本将保持可用，直到新修订版确认发布。</p>
      </section>
     </div>
     <div class="v17-upload-action"><span>{{file ? '确认共享范围后继续。' : '先选择文件，再开始解析。'}}</span><a-button type="primary" :loading="busy" :disabled="!file||!sharing" @click="upload">上传并检查重复 <ArrowRightOutlined/></a-button></div>
    </template>
    <template v-else-if="uploadStage===1">
     <div class="v17-upload-grid v17-upload-content">
      <section>
       <h2 ref="uploadStageHeading" tabindex="-1">解析资料</h2>
       <a-alert v-if="!canParse" type="warning" message="解析服务暂不可用，已上传资料保留，可核对已有结果。"/>
       <article v-for="item in batch?.items" :key="item.version_id" class="progress-item">
        <strong>{{item.title}}</strong>
        <p>{{relationships[item.relationship]}} · {{parseNames[item.parse_status]}}</p>
        <KnowledgeEffectiveTemplate :value="item.effective_template" :quality="item.automatic_quality"/>
        <a-progress v-if="item.parse_status==='parse_queued'" :percent="Math.round(item.progress*100)"/>
        <a-button v-if="['planned','uploaded','parse_failed'].includes(item.parse_status)&&item.relationship!=='SAME_CONTENT_SKIP'" :disabled="busy||!canParse" @click="queue(item)">{{item.parse_status==='parse_failed'?'重试解析':'开始解析'}}</a-button>
        <a-button v-if="item.parse_status==='parsed/indexed'&&item.relationship!=='SAME_CONTENT_SKIP'" type="primary" :disabled="busy" @click="openQuality(item,true)">前往质量核对</a-button>
        <a-button v-if="item.relationship==='SAME_CONTENT_SKIP'" @click="router.push('/hbos/knowledge/maintenance/versions')">查看当前版本</a-button>
       </article>
      </section>
      <section class="v17-sharing"><h2>下一步：核对原件与提取内容</h2><p>解析完成后，请逐项检查正文、数字、表格关系和文件版本。离开页面后，已提交的后台任务继续运行。</p></section>
     </div>
     <div class="v17-upload-action"><span>进度由处理服务提供。</span><a-button :loading="loading" :disabled="busy" @click="refresh">刷新进度</a-button></div>
    </template>
    <template v-else-if="uploadStage===2">
     <div class="v17-upload-grid v17-upload-content">
      <section>
       <h2 ref="uploadStageHeading" tabindex="-1">原文对照</h2>
       <p>请对照获准原件核对。片段顺序不能当作原页码。</p>
       <template v-if="preview">
        <blockquote v-for="(fragment,index) in preview.fragments" :key="index" class="quality-fragment">{{fragment.text}}<small>{{fragment.location}}</small></blockquote>
       </template>
       <a-skeleton v-else-if="!error" active/>
       <label class="version-label">核对记录<a-textarea v-model:value="qualityNote" :maxlength="500" :rows="3" placeholder="记录核对结果与限制，至少 3 个字"/></label>
      </section>
      <section class="v17-sharing">
       <h2>四项质量核对</h2>
       <p>全部确认，并填写核对记录后才能继续。</p>
       <a-checkbox-group v-model:value="checks" class="quality-checks">
        <a-checkbox value="text">正文与否定语</a-checkbox>
        <a-checkbox value="numbers">数字、单位和条件</a-checkbox>
        <a-checkbox value="tables">表格与条款关系</a-checkbox>
        <a-checkbox value="identity">文件和版本身份</a-checkbox>
       </a-checkbox-group>
      </section>
     </div>
     <div class="v17-upload-action"><span>质量核对不会自动发布资料。</span><a-button type="primary" :disabled="!preview||checks.length!==4||qualityNote.trim().length<3" :loading="busy" @click="confirmQuality">保存质量核对</a-button></div>
    </template>
    <template v-else>
     <div class="v17-upload-grid v17-upload-content" v-for="item in batch?.items" :key="item.version_id">
      <section>
       <h2 ref="uploadStageHeading" tabindex="-1">确认发布范围</h2>
       <dl class="v17-publish-meta">
        <dt>资料名称</dt><dd>{{item.title}}</dd><dt>归属部门</dt><dd>{{departmentName(batch?.department||department)}}</dd>
        <dt>版本关系</dt><dd>{{relationships[item.relationship]}}</dd><dt>质量核对</dt><dd>{{item.quality_status==='Passed'?'已核对':'待核对'}}</dd>
        <dt>共享范围</dt><dd>{{item.shared_approved===true?'已批准':'待确认'}}</dd><dt>发布状态</dt><dd>{{item.publication_status==='Published'?'已发布':'未发布'}}</dd>
       </dl>
      </section>
      <section class="v17-sharing">
       <h2>记录发布原因</h2><p>解析完成、质量通过和共享批准是独立条件。</p>
       <label class="version-label">发布说明<a-textarea v-model:value="operationReason" :maxlength="500" :rows="3" placeholder="填写本次发布或换版原因"/></label>
       <p v-if="item.shared_approved!==true">请先在资料管理中核对共享授权。</p>
      </section>
      <div class="v17-upload-action v17-upload-full">
       <span>{{item.publication_status==='Published'?'当前版本已发布。':'暂不发布时，当前已发布版本继续有效。'}}</span>
       <div class="v17-actions">
        <a-button @click="router.push('/hbos/knowledge/maintenance')">{{item.publication_status==='Published'?'返回资料管理':'暂不发布'}}</a-button>
        <a-popconfirm v-if="item.parse_status==='parsed/indexed'&&item.quality_status==='Passed'&&item.shared_approved===true&&item.publication_status!=='Published'" title="确认本版本已核对并获准共享，发布给员工？" ok-text="确认发布" cancel-text="取消" @confirm="publish(item)">
         <a-button type="primary" :disabled="busy||operationReason.trim().length<3">确认发布</a-button>
        </a-popconfirm>
       </div>
      </div>
     </div>
    </template>
   </section>
   <KnowledgeStaffFeedback v-if="view==='feedback'" v-model:status="feedbackStatus" v-model:page="feedbackPage" v-model:query="feedbackQuery"
     :items="feedbackItems" :loading="loading" :failed="feedbackReadError" :has-more="feedbackHasMore"
     :search-unsupported="feedbackSearchUnsupported"
     @search="searchFeedback" @refresh="refreshFeedback" @open="openFeedback" />
  </template>
  <p v-if="view!=='feedback'" class="kb-page-footnote">发布与版本操作均保留审核记录，旧来源会重新核验。</p>
  <a-drawer :open="detailOpen" @after-open-change="onDetailDrawerOpenChange" title="资料与版本" width="min(560px, 100vw)" root-class-name="kb-drawer kb-scope kb-drawer-detail" @close="closeDrawer('detail')"><h2>{{detailTitle}}</h2><a-alert v-if="detailLookupState==='NOT_FOUND'" type="warning" show-icon class="kb-alert" data-detail-lookup-not-found message="服务端未找到该资料对应的处理批次；该资料可能来自历史批次，仍可查看当前已发布版本。"/><a-skeleton v-if="detailLoading" active/><template v-else-if="detail"><div class="kb-version-card"><a-tag :color="detail.publication_status==='Published'?'green':'default'">{{detail.publication_status==='Published'?'当前已发布':detail.publication_status==='Withdrawn'?'已下架':'未发布'}}</a-tag><strong>{{parseNames[detail.parse_status]}} · {{detail.quality_status==='Passed'?'质量已核对':'质量待核对'}}</strong></div><KnowledgeEffectiveTemplate :value="detail.effective_template" :quality="detail.automatic_quality"/><p class="kb-muted">{{relationships[detail.relationship]}}。替换或下架后，旧来源与收藏需重新核验。</p><label>操作原因<a-input v-model:value="operationReason" :maxlength="500" placeholder="换版、下架或恢复前填写原因"/></label><div class="kb-drawer-actions"><a-button v-if="detail.parse_status==='parsed/indexed'" @click="openQuality(detail)">查看与核对质量</a-button><a-button v-if="['planned','uploaded','parse_failed'].includes(detail.parse_status)" :disabled="!canParse||busy" @click="queue(detail)">开始解析</a-button><a-popconfirm v-if="detail.quality_status==='Passed'&&detail.shared_approved===true&&detail.publication_status!=='Published'" title="确认核对质量并获准共享，执行发布操作？" ok-text="确认操作" cancel-text="取消" @confirm="publish(detail)"><a-button type="primary" :disabled="busy">{{detail.publication_status==='Withdrawn'?'恢复发布':'确认发布 / 换版'}}</a-button></a-popconfirm><a-popconfirm v-if="detail.publication_status==='Published'" title="下架后员工不能展开该版本来源，确认下架？" ok-text="确认下架" cancel-text="取消" @confirm="withdraw(detail)"><a-button danger :disabled="busy">下架资料</a-button></a-popconfirm><a-button @click="newRevision"><UploadOutlined/>上传新修订版</a-button></div><a-alert v-if="error" type="error" :message="error"/><details><KnowledgeDisclosureSummary>高级：处理任务记录</KnowledgeDisclosureSummary><p class="kb-muted">任务 {{selectedBatch}} · 版本 {{detail.version_id}}</p></details></template><p v-else class="kb-muted">当前版本可由员工查阅。未找到本页可维护的处理记录，请选择已登记任务。</p></a-drawer>
  <a-drawer :open="qualityOpen" @after-open-change="onQualityDrawerOpenChange" title="核对本版本质量" width="min(700px, 100vw)" root-class-name="kb-drawer kb-scope kb-drawer-quality" :mask-closable="!busy" :closable="!busy" @close="closeDrawer('quality')"><template v-if="preview"><h2>{{preview.title}}</h2><p class="kb-muted">对照获准原资料核对数字、单位、否定语和表格关系。片段顺序不能当作原页码。</p><blockquote v-for="(fragment,index) in preview.fragments" :key="index" class="quality-fragment">{{fragment.text}}<small>{{fragment.location}}</small></blockquote><a-checkbox-group v-model:value="checks" class="quality-checks"><a-checkbox value="text">正文与否定语</a-checkbox><a-checkbox value="numbers">数字、单位和条件</a-checkbox><a-checkbox value="tables">表格与条款关系</a-checkbox><a-checkbox value="identity">文件和版本身份</a-checkbox></a-checkbox-group><a-textarea v-model:value="qualityNote" :maxlength="500" :auto-size="{minRows:3,maxRows:7}" placeholder="记录核对结果与限制"/><a-button type="primary" :disabled="checks.length!==4||qualityNote.trim().length<3" :loading="busy" @click="confirmQuality">保存质量核对</a-button></template><a-alert v-else-if="error" type="error" :message="error"/><a-skeleton v-else active/></a-drawer>
  <a-drawer :open="bulkQualityOpen" @after-open-change="onBulkQualityDrawerOpenChange" title="核对所选资料质量" width="min(620px, 100vw)" root-class-name="kb-drawer kb-scope kb-drawer-bulk-quality" :mask-closable="!busy" :closable="!busy" @close="closeDrawer('bulk')"><p>本次仅核对所选 {{selectedItems.length}} 份。请先对照原资料和来源预览，例外项可取消选择。</p><article v-for="item in selectedItems" :key="item.document_id" class="advanced-row"><span>{{item.title}}</span><a-button :disabled="busy" @click="openQuality(item)">查看来源</a-button></article><a-checkbox-group v-model:value="bulkChecks" class="quality-checks"><a-checkbox value="text">正文与否定语已逐项核对</a-checkbox><a-checkbox value="numbers">数字、单位和条件已逐项核对</a-checkbox><a-checkbox value="tables">表格与条款关系已逐项核对</a-checkbox><a-checkbox value="identity">身份、版本和共享范围已逐项核对</a-checkbox></a-checkbox-group><a-textarea v-model:value="bulkNote" :maxlength="500" :auto-size="{minRows:3,maxRows:7}" placeholder="记录本批准批次的质量核对结果与限制"/><a-button type="primary" :disabled="busy||bulkChecks.length!==4||bulkNote.trim().length<3||!selectedItems.length" :loading="busy" @click="confirmBulkQuality">保存所选质量核对</a-button><a-button :disabled="busy||bulkNote.trim().length<3||!selectedItems.length" @click="holdBulkQuality">保留所选待复核</a-button><a-alert v-if="error" type="error" :message="error"/></a-drawer>
  <a-drawer :open="feedbackOpen" @after-open-change="onFeedbackDrawerOpenChange" title="处理员工反馈" width="min(520px, 100vw)" root-class-name="kb-drawer kb-scope kb-drawer-feedback-review" @close="closeDrawer('feedback')"><template v-if="selectedFeedback"><h2>{{selectedFeedback.category}}</h2><p>{{selectedFeedback.note}}</p><p class="kb-muted">回复只向提交人和维护人展示。</p><a-textarea v-model:value="reply" :rows="5" :maxlength="500" placeholder="填写处理结果或回复…"/><div class="kb-drawer-actions"><a-button :disabled="busy" @click="reviewFeedback('In Review')">标记处理中</a-button><a-button type="primary" :disabled="busy||!reply.trim()" :loading="busy" @click="reviewFeedback('Resolved')">回复并完成</a-button></div><a-alert v-if="error" type="error" :message="error"/></template></a-drawer>
 </div>
</template>
<style scoped>
.v17-breadcrumb{font-size:12px;color:#71839d;margin:0 0 24px}.v17-breadcrumb span{margin:0 10px;color:#9baac0}.v17-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:26px 0 20px}.v17-stat{min-height:95px;padding:14px 18px;border:1px solid #fff;border-radius:14px;background:linear-gradient(128deg,#fffffff0,#ffffffb3 48%,#f0f4ffcc);box-shadow:0 12px 32px #24314e0a;display:grid;grid-template-columns:1fr auto;align-items:center;gap:3px 14px}.v17-stat small{font-size:12px;color:#6c7f98}.v17-stat strong{font-size:24px;line-height:1.2;grid-column:2;grid-row:1/3;color:#405877}.v17-stat span{font-size:10px;color:#8b98aa;grid-column:1}.v17-panel{padding:24px;border-radius:20px;background:linear-gradient(128deg,#fffffff0,#ffffffb3 48%,#f0f4ffcc);border:1px solid #fffffff5;box-shadow:0 16px 40px #34446b08;color:#253650}.v17-panel-heading{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:18px}.v17-panel-heading h2{font-size:16px;color:#17253c;margin:0}.v17-panel-heading p{font-size:12px;color:#8090a5;margin:4px 0 0}.v17-batch{display:grid;grid-template-columns:auto auto;gap:3px 14px;align-items:center}.v17-batch span{font-size:13px;font-weight:600;color:#4a5e7a}.v17-batch small{font-size:11px;color:#8191a8;grid-column:1}.v17-batch button{grid-column:2;grid-row:1/3}.v17-panel button:not(.v17-title):not(.v17-view){min-height:40px;border:1px solid #ced7e5;border-radius:10px;background:#ffffffc4;padding:8px 14px;color:#405773;cursor:pointer}.v17-panel button:disabled{opacity:.45;cursor:not-allowed}.v17-guide{margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #e2e8f1;font-size:12px;color:#71829a}.v17-guide summary{cursor:pointer;line-height:24px}.v17-guide summary span{font-size:10px;margin-left:8px}.v17-guide-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.v17-filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:17px}.v17-search{flex:1 1 350px;max-width:600px}.v17-search input,.v17-filters select{width:100%;height:44px;border:1px solid #ced7e5;border-radius:10px;background:#ffffffc4;padding:0 12px;font-size:14px;color:#405773}.v17-filters select{width:auto;min-width:150px}.v17-hint{font-size:10px;color:#96a1b4;margin:0 0 14px}.v17-table-wrap{overflow:auto;overscroll-behavior:contain}.v17-table-wrap table{border-collapse:collapse;width:100%;min-width:680px;text-align:left;font-size:12px}.v17-table-wrap th{font-size:11px;color:#7c8da3;font-weight:500;padding:12px;background:#f6f8fc88;border-bottom:1px solid #e6eaf3}.v17-table-wrap td{padding:16px 12px;border-bottom:1px solid #e5eaf380;color:#7b8ca3}.v17-table-wrap th:first-child,.v17-table-wrap td:first-child{width:44px;text-align:center}.v17-table-wrap th:last-child,.v17-table-wrap td:last-child{width:70px;text-align:right}.v17-table-wrap td small{display:block;font-size:10px;color:#8998ad;margin-top:3px}.v17-title,.v17-view{border:0;background:none;cursor:pointer}.v17-title{text-align:left;color:#405773;font-size:13px}.v17-view{color:#5b50e8;font-weight:600}.v17-tag{background:#e9f7f2;color:#308871;border:1px solid #cdebe0;border-radius:6px;padding:4px 8px;font-size:10px}.v17-pagination{display:flex;justify-content:space-between;align-items:center;gap:10px;padding-top:16px;margin-top:12px;border-top:1px solid #e1e7f1;color:#7c8da4;font-size:11px}.v17-pagination div,.v17-actions{display:flex;gap:8px;flex-wrap:wrap}.maintenance-page :deep(.kb-heading .ant-btn-primary){background:linear-gradient(135deg,#725de8,#5645ce);border:0;min-height:44px;border-radius:10px}@media(max-width:900px){.v17-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.v17-panel-heading{align-items:flex-start;flex-wrap:wrap}}@media(max-width:600px){.v17-stats{display:flex;overflow:auto}.v17-stat{flex:0 0 155px}.v17-panel{padding:16px}.v17-batch{width:100%}.v17-guide-grid{grid-template-columns:1fr}.v17-pagination{flex-wrap:wrap}}

.maintenance-funnel{margin-bottom:16px}.maintenance-funnel>summary{cursor:pointer;min-height:44px;display:flex;align-items:center;font-weight:600}.maintenance-batch-entry{margin-bottom:16px}.maintenance-batch-entry>summary{cursor:pointer;font-weight:600;min-height:44px;display:flex;align-items:center}.funnel-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:16px}.funnel-grid .kb-panel{padding:14px 18px}.funnel-grid dl{gap:6px 12px!important}.funnel-grid dd{font-size:16px!important;margin:0!important}.funnel-grid h2{font-size:20px;margin:0 0 16px}.funnel-grid dl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:0}.funnel-grid dl>div{min-width:0}.funnel-grid dt{font-size:12px;color:var(--hbos-text-muted)}.funnel-grid dd{font-size:22px;margin:4px 0 0}.bulk-toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:16px 0}.maintenance-page{min-width:0}.kb-maintenance-lookup{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0 12px}.kb-maintenance-lookup>.ant-input-search{flex:1 1 320px;min-width:0}.operation-reason{display:grid;gap:8px;margin:20px 0;font-size:14px}.version-label{display:grid;gap:8px;margin:20px 0}.advanced-row{display:flex;justify-content:space-between;gap:16px;padding:16px 0;border-bottom:1px solid var(--hbos-border-default);font-size:14px}.advanced-row>span{min-width:0;overflow-wrap:anywhere}.kb-progress-record{display:grid;grid-template-columns:1fr auto;gap:16px;padding:24px;background:#f4f8fa;border-radius:16px;margin-top:24px;font-size:14px}.progress-item{margin:24px 0}.quality-fragment{border-left:3px solid var(--hbos-brand-aqua);padding:16px;margin:16px 0;white-space:pre-wrap;overflow-wrap:anywhere;font-size:16px;line-height:28px;background:#f7f9fc}.quality-fragment small{display:block;color:var(--hbos-text-muted);font-size:12px;margin-top:8px}.quality-checks{display:flex;flex-direction:column;gap:12px;margin:24px 0}.quality-checks+.ant-input{margin-bottom:24px}.kb-upload-body>.ant-checkbox-wrapper{margin-top:20px}.kb-upload-body>label{font-size:14px}.kb-file-picker:focus-within{outline:2px solid var(--hbos-brand-aqua);outline-offset:3px}.kb-drawer label .ant-input{margin-top:12px}.kb-list-toolbar h2{font-size:20px;line-height:28px;margin:0}
.batch-import-panel h2{font-size:20px;margin:0 0 8px}.batch-import-panel h3{font-size:16px;margin:24px 0 8px}.batch-manifest-picker{display:flex;flex-direction:column;gap:4px;padding:20px;border:1px dashed var(--hbos-border-default);border-radius:16px;cursor:pointer;margin:16px 0}.batch-manifest-picker:focus-within{outline:2px solid var(--hbos-brand-aqua);outline-offset:3px}.batch-manifest-picker input{position:absolute;width:1px;height:1px;opacity:0}.batch-manifest-picker span{font-size:12px;color:var(--hbos-text-muted)}.batch-manifest-text{margin:8px 0 16px}.batch-toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:12px 0}.batch-summary{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:16px;background:#f4f8fa;border-radius:16px;margin:12px 0;font-size:13px}.batch-digest{overflow-wrap:anywhere;font-size:11px;color:var(--hbos-text-muted);width:100%}.batch-count{white-space:nowrap}.batch-plan-row,.batch-progress-row{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid var(--hbos-border-default)}.batch-plan-main{display:flex;flex-direction:column;gap:2px;min-width:0;overflow-wrap:anywhere}.batch-block{color:#b44}.batch-submit{display:grid;gap:12px;margin:20px 0;max-width:520px}.batch-submit label,.batch-actions label{display:grid;gap:6px;font-size:13px}.batch-receipt article{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:8px 0;font-size:13px}.batch-receipt code{overflow-wrap:anywhere}.batch-progress-head{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:20px}.batch-progress-head h3{margin:0}.batch-progress-head span{font-size:13px;color:var(--hbos-text-muted);overflow-wrap:anywhere}.batch-actions{display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap;margin:16px 0}.batch-actions label{min-width:220px}
@media(max-width:900px){.funnel-grid{grid-template-columns:1fr}}
@media(max-width:600px){.kb-progress-record{padding:16px;gap:12px}.advanced-row{flex-wrap:wrap}}
/* P08: one primary toolbar; scope/refresh/lineage stay reachable as secondary entries. */
.v17-version-projection{flex:1 1 100%;font-size:11px;line-height:16px;color:#8090a5}
.v17-panel-heading.v17-legacy-heading{margin-bottom:8px;align-items:center;flex-wrap:nowrap}
.v17-panel-heading.v17-legacy-heading h2{font-size:16px;line-height:22px}
.v17-panel-heading.v17-legacy-heading p{font-size:11px;line-height:15px;margin-top:1px}
.v17-version-more{margin:0}
.v17-version-more summary{display:inline-flex;align-items:center;gap:4px;min-height:38px;padding:0 8px;border:1px solid #d5deea;border-radius:10px;font-size:12px;color:#405773;list-style:none}
.v17-version-more summary .kb-disclosure-state{display:none}
.v17-version-more summary .kb-disclosure-mark{flex-basis:20px;height:20px}
.v17-version-more summary::-webkit-details-marker{display:none}
@media(max-width:600px){
 .v17-panel-heading.v17-legacy-heading{align-items:center;flex-wrap:nowrap}
}

.v17-version-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:1px}
.v17-version-toolbar > .ant-btn{height:38px;min-height:38px}
.v17-version-search{display:flex;align-items:center;gap:8px;flex:1 1 320px;min-width:0;height:40px;padding:0 6px 0 12px;border:1px solid #ced7e5;border-radius:10px;background:#ffffffc4;color:#405773}
.v17-version-search input{flex:1 1 auto;min-width:0;height:100%;border:0;background:transparent;font:inherit;font-size:14px;color:#405773;outline:none}
.v17-version-search button{flex:none;display:grid;place-items:center;width:30px;height:30px;border:0;border-radius:8px;background:#efeaff;color:#5144bd;cursor:pointer}
.v17-version-search button:disabled{opacity:.5;cursor:not-allowed}
.v17-version-row .kb-doc-main p{font-size:12px}
@media(max-width:600px){ .v17-version-view-label{display:none} }
.v17-version-more-body{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
.v17-version-more-body .ant-input-search{flex:1 1 240px;min-width:0}
.v17-version-refresh{display:inline-flex;align-items:center;justify-content:center;gap:4px;min-height:38px;padding:0 10px;border:1px solid #ced7e5;border-radius:10px;background:#ffffffc4;color:#405773;font:inherit;font-size:12px;cursor:pointer}
.v17-version-refresh:disabled{opacity:.5;cursor:not-allowed}
.v17-version-note{margin:6px 0 10px;font-size:11px;line-height:17px;color:#8090a5}
.v17-version-row .kb-doc-main p{font-size:12px}
.v17-version-lineage{margin-top:20px;border-top:1px solid #e2e8f1;padding-top:14px}
.v17-version-lineage-head{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-top:12px}
.v17-version-lineage-head p{margin:0}
@media(max-width:600px){
 .v17-version-toolbar{gap:8px}
 .v17-version-search{flex:1 1 100%}
 .v17-version-refresh{min-height:34px;font-size:11px}
 .v17-version-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:10px}
 .v17-version-row .kb-doc-icon{grid-column:1}
 .v17-version-row .kb-doc-main{grid-column:2;min-width:0}
 .v17-version-row > .ant-btn{grid-column:3;justify-self:end;align-self:center;margin:0}
}
</style>
