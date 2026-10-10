<template>
  <div class="knowledge-page">
    <header class="kb-heading"><div><h1>{{ pageTitle }}</h1><p>从已共享资料中查找依据，答案与来源一起呈现。</p></div><a-button :disabled="!subjectKey" @click="connectionOpen = true"><LinkOutlined />连接个人助手</a-button></header>
    <div v-if="equipmentId || assetId || componentId" class="kb-context"><a-tag v-if="equipmentId">设备上下文 {{ equipmentId }}</a-tag><a-tag v-if="assetId">资产范围 {{ assetId }}</a-tag><a-tag v-if="componentId">组件范围 {{ componentId }}</a-tag></div>
    <a-alert v-if="pageError || retrievalBlocked || (status?.answer_availability?.available === false && mode === 'ask')" :type="pageErrorCode === 'FORBIDDEN' ? 'warning' : 'error'" show-icon :message="pageError || '查询暂不可用，请稍后重试；目录与个人记录仍可查看。'" class="kb-alert"><template #action><a-button :loading="statusLoading" @click="refreshStatus">刷新状态</a-button></template></a-alert>
    <template v-if="view === 'query'">
      <section v-if="mode === 'search' || !hasConversation" class="kb-composer hbos-glass-g3" aria-label="知识查询">
        <form class="knowledge-search" @submit.prevent="submitComposer">
          <div class="kb-composer-top"><div class="kb-modes" role="group" aria-label="知识使用方式"><button type="button" :aria-pressed="mode === 'ask'" :disabled="!status?.ask_enabled" @click="setMode('ask')">问知识</button><button type="button" :aria-pressed="mode === 'search'" @click="setMode('search')">搜资料</button></div><label class="sr-only" for="knowledge-space">查询部门范围</label><select id="knowledge-space" v-model="selectedSpace" class="kb-scope-select" :disabled="!spaces.length"><option value="">全部已共享资料</option><option v-for="space in spaces" :key="space.space_id" :value="space.space_id">{{ space.title }}</option></select></div>
          <label class="sr-only" for="knowledge-query">知识问题</label><textarea id="knowledge-query" v-model="query" :maxlength="mode === 'ask' ? 280 : 500" :disabled="working" :placeholder="mode === 'ask' ? '描述你想了解的问题…' : '输入资料标题、文号或关键词…'" rows="3" @compositionstart="composing = true" @compositionend="composing = false" @keydown="composerKeydown" />
          <div class="kb-composer-bottom"><span>{{ mode === 'ask' ? '回答附带可核对的资料来源' : '直接查找资料与相关依据' }}<small class="kb-keyboard"> · ⌘ / Ctrl + Enter</small></span><a-button type="primary" html-type="submit" :loading="working" :disabled="working || !canSubmit || !query.trim() || inputTooLong">{{ mode === 'ask' ? '提问' : '搜索' }}<ArrowRightOutlined /></a-button></div>
        </form>
        <div v-if="working || composerNotice" class="kb-composer-notice"><a-button v-if="working" @click="cancelPending">返回编辑</a-button><span role="status">{{ composerNotice }}</span></div>
      </section>
      <div v-if="!hasConversation && !hasSearched && !working" class="kb-start-grid"><section class="kb-suggestions"><div class="kb-section-title"><h2>从一个问题开始</h2><span>示例问题</span></div><button v-for="q in exampleQuestions" :key="q" type="button" @click="useExample(q)"><span>{{ q }}</span><ArrowRightOutlined /></button></section><section class="kb-help-card hbos-glass-g1"><ReadOutlined /><h2>查找资料，也能继续追问</h2><p>点开回答中的来源核对依据。常用资料可以收藏，方便下次直接查阅。</p><RouterLink to="/hbos/knowledge/catalog">打开资料目录<ArrowRightOutlined /></RouterLink></section></div>
      <section v-if="mode === 'search' && hasSearched" class="kb-panel knowledge-results hbos-glass-g1"><div class="kb-section-title"><h2>相关资料</h2><span>{{ results.length }} 条依据</span></div><a-skeleton v-if="searching" active :paragraph="{rows:4}" /><a-empty v-else-if="!results.length && !pageError" description="未找到相关依据，请换一个关键词或调整部门范围。" /><article v-for="item in results" :key="item.evidence_id" class="kb-doc-row result-card"><div class="kb-doc-icon"><FileTextOutlined /></div><button type="button" class="kb-doc-main" :aria-label="'查看来源 '+item.title" @click="openEvidence(item)"><strong>{{ item.title || '未标注标题' }}</strong><p>{{ item.excerpt }}</p><small>{{ spaces.find(s => s.space_id === item.space_id)?.title }} · {{ item.document_number || '文号待核' }} · {{ item.version || '版本待核' }}</small></button><div class="kb-doc-actions"><a-button type="text" :disabled="working" :aria-label="(tools?.isBookmarked(item) ? '取消收藏 ' : '收藏 ') + item.title" @click="tools?.bookmark(item)"><StarFilled v-if="tools?.isBookmarked(item)" class="kb-star" /><StarOutlined v-else /></a-button><a-button type="text" :disabled="working" aria-label="反馈" @click="tools?.feedback(item)"><MessageOutlined /></a-button><a-tooltip title="待部门文档下载权限上线"><a-button type="text" disabled aria-label="下载，待部门权限上线"><DownloadOutlined /></a-button></a-tooltip></div></article></section>
    </template>
    <KnowledgeTools v-if="status?.environment === 'production' && status.can_enter && subjectKey" ref="tools" :subject="subjectKey" :query="query" :selected-space="selectedSpace" :spaces="spaces" :ask-enabled="Boolean(status?.ask_enabled) && status?.answer_availability?.available !== false" :retrieval-blocked="retrievalBlocked" :mode="mode" :search-mode="searchMode" :view="view" composer-external @busy="askBusy = $event" @conversation="hasConversation = $event" @replay="replaySaved" @restored="restoreSaved" @records-view="router.push($event === 'feedback' ? '/hbos/knowledge/history?tab=feedback' : '/hbos/knowledge/history')" @document="showDocumentSummary" @evidence="drawer.show" @upstream-error="refreshStatus" @access-error="applyError" @evidence-invalidated="invalidateEvidence">
      <template #catalog>
        <section class="kb-panel hbos-glass-g1">
          <form class="kb-list-toolbar catalog-filter" @submit.prevent="refreshCatalog"><label class="sr-only" for="catalog-query">查找标题或文号</label><a-input-search id="catalog-query" v-model:value="catalogQuery" placeholder="查找标题或文号" aria-label="查找标题或文号" @search="refreshCatalog" /><label class="sr-only" for="catalog-department">筛选部门</label><select id="catalog-department" v-model="selectedSpace" class="kb-scope-select"><option value="">全部已共享资料</option><option v-for="space in spaces" :key="space.space_id" :value="space.space_id">{{ space.title }}</option></select></form>
          <div class="kb-list-caption catalog-heading"><span>{{ catalogLoading ? '更新中' : `${catalogTotal} 份资料` }}</span><span>下载待部门权限上线</span></div>
          <div class="catalog-content" :aria-busy="catalogLoading"><a-skeleton v-if="catalogLoading" active :paragraph="{rows:4}" /><a-alert v-else-if="catalogError" type="error" show-icon :message="catalogError" /><a-empty v-else-if="!catalog.length" :description="catalogQuery.trim() ? '没有匹配的资料，请调整标题、文号或部门范围。' : '当前范围暂无可查阅的已收录资料。'" /><template v-else><article v-for="doc in catalog" :key="doc.document_id" class="kb-doc-row catalog-row"><div class="kb-doc-icon"><FileTextOutlined /></div><button class="kb-doc-main" type="button" @click="openDocumentSummary(doc)"><strong>{{ doc.title || '未标注标题' }}</strong><p>{{ doc.status_note }}</p><small>{{ doc.document_number || '文号待核' }} · {{ doc.department }} · {{ doc.version || '版本待核' }}<a-tag color="green">已共享</a-tag></small></button><div class="kb-doc-actions"><a-button type="text" :disabled="askBusy || !doc.version_id" :aria-label="(tools?.isBookmarked(doc) ? '取消收藏 ' : '收藏 ') + doc.title" @click="tools?.toggleDocumentBookmark(doc)"><StarFilled v-if="tools?.isBookmarked(doc)" class="kb-star" /><StarOutlined v-else /></a-button><a-tooltip title="待部门文档下载权限上线"><a-button type="text" disabled aria-label="下载，待部门权限上线"><DownloadOutlined /></a-button></a-tooltip></div></article></template></div>
          <div class="kb-pagination"><a-pagination v-model:current="catalogPage" :page-size="catalogPageSize" :total="catalogTotal" :show-size-changer="false" :disabled="catalogLoading" :show-less-items="true" /></div>
        </section>
      </template>
    </KnowledgeTools>
    <p class="kb-page-footnote">依据可展开核对 · 原件下载待部门权限上线</p>
    <KnowledgeConnections :open="connectionOpen" :subject="subjectKey || ''" @close="connectionOpen = false" />
    <EvidenceDrawer :open="drawerOpen" :loading="drawerLoading" :evidence="drawerEvidence" :error="drawerError" :error-code="drawerErrorCode" :bookmarked="drawerEvidence ? tools?.isBookmarked(drawerEvidence) : false" @close="drawer.close()" @bookmark="tools?.bookmark($event)" @feedback="tools?.feedback($event)" />
    <a-drawer :open="summaryOpen" title="资料详情" width="min(560px, 100vw)" root-class-name="kb-drawer kb-scope" @close="closeSummary"><a-skeleton v-if="summaryLoading" active /><a-alert v-else-if="summaryError" type="warning" show-icon :message="summaryError" /><template v-else-if="summaryDocument"><h2 class="kb-drawer-title">{{ summaryDocument.title }}</h2><p class="kb-muted">{{ summaryDocument.document_number || '文号待核' }} · {{ summaryDocument.department }} · {{ summaryDocument.version || '版本待核' }}</p><div class="kb-source-status"><CheckCircleOutlined />当前授权共享版本</div><div class="kb-source-excerpt"><strong>资料状态</strong><p>{{ summaryDocument.status_note }}</p></div><div class="kb-drawer-actions"><a-button :disabled="askBusy" @click="tools?.toggleDocumentBookmark(summaryDocument)"><StarOutlined />{{ tools?.isBookmarked(summaryDocument) ? '取消收藏' : '收藏资料' }}</a-button><a-button disabled><DownloadOutlined />下载</a-button></div><p class="kb-muted">待部门文档下载权限上线</p></template></a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRightOutlined, ReadOutlined, LinkOutlined, FileTextOutlined, StarOutlined, StarFilled, MessageOutlined, DownloadOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import type { KnowledgeEvidence, KnowledgeStatus, KnowledgeSpace, KnowledgeDocument, KnowledgeSearchContext, KnowledgeSavedQuery } from '@/contracts/p1'
import { DomainApiError, getKnowledgeStatus, getKnowledgeSpaces, getKnowledgeDocumentsPage, searchKnowledge } from '@/services/p1Api'
import EvidenceDrawer from '@/components/knowledge/EvidenceDrawer.vue'
import KnowledgeTools from '@/components/knowledge/KnowledgeTools.vue'
import KnowledgeConnections from '@/components/knowledge/KnowledgeConnections.vue'
import { useEvidenceResolution } from '@/composables/useEvidenceResolution'
import { usePortalStore } from '@/stores/portal'

const route = useRoute()
const router = useRouter()
const props = defineProps<{sessionRevision?:number}>()
const view = computed<'query'|'catalog'|'favorites'|'history'|'feedback'>(() => route.path?.endsWith('/catalog') ? 'catalog' : route.path?.endsWith('/favorites') ? 'favorites' : route.path?.endsWith('/history') ? (route.query.tab === 'feedback' ? 'feedback' : 'history') : 'query')
const pageTitle = computed(() => ({query:'知识库',catalog:'资料目录',favorites:'我的收藏',history:'我的记录',feedback:'我的记录'}[view.value]))
const exampleQuestions = ['培养箱使用前需要检查哪些项目？','在哪里查找岗位安全培训资料？','如何确认引用的是当前版本？']
const summaryOpen = ref(false), summaryLoading = ref(false), summaryError = ref(''), summaryDocument = ref<KnowledgeDocument|null>(null)
let summaryGeneration = 0
function closeSummary() { summaryGeneration++; summaryOpen.value=false; summaryLoading.value=false; summaryDocument.value=null; summaryError.value='' }
function showDocumentSummary(doc: KnowledgeDocument) { summaryDocument.value=doc; summaryError.value=''; summaryLoading.value=false; summaryOpen.value=true }
async function openDocumentSummary(doc: KnowledgeDocument) {
  const generation=++summaryGeneration, subject=subjectKey.value
  summaryOpen.value=true; summaryLoading.value=true; summaryDocument.value=null; summaryError.value=''
  try {
    const page = await getKnowledgeDocumentsPage(doc.title || '',doc.space_id,1,50)
    if (generation!==summaryGeneration || subject!==subjectKey.value) return
    const current=page.documents.find(d=>d.document_id===doc.document_id && d.version_id===doc.version_id)
    if (!current) throw new DomainApiError('EVIDENCE_UNAVAILABLE','资料已换版、下架或授权已变化，请刷新目录。')
    summaryDocument.value=current
  } catch (e) { if (generation===summaryGeneration) { summaryError.value=e instanceof DomainApiError?e.message:'资料核验暂不可用。'; if (e instanceof DomainApiError && accessFailureCodes.includes(e.code)) applyError(e) } }
  finally { if (generation===summaryGeneration) summaryLoading.value=false }
}
function useExample(value:string) { query.value=value; void submitComposer() }
watch(view,()=>{ drawer.close(false); closeSummary(); if (view.value==='catalog') void refreshCatalog() })
const portal = usePortalStore()
const subjectKey = computed(() => portal.user?.id || null)
const savedContext = ref<KnowledgeSearchContext | null>(null)
const currentContext = computed<KnowledgeSearchContext>(() => savedContext.value ?? {
  equipment_id: typeof route.query.equipment_id === 'string' ? route.query.equipment_id : undefined,
  asset_id: typeof route.query.asset_id === 'string' ? route.query.asset_id : undefined,
  component_id: typeof route.query.component_id === 'string' ? route.query.component_id : undefined,
})
const equipmentId = computed(() => currentContext.value.equipment_id || '')
const assetId = computed(() => currentContext.value.asset_id || '')
const componentId = computed(() => currentContext.value.component_id || '')
const connectionOpen = ref(false)
const status = ref<KnowledgeStatus | null>(null)
const statusLoading = ref(false)
const spaces = ref<KnowledgeSpace[]>([])
const selectedSpace = ref('')
const savedScopeNeedsSelection = ref(false)
const mode = ref<'search' | 'ask'>('ask')
const searchMode = ref<'STANDARD' | 'PRECISE'>('STANDARD')
const query = ref(typeof route.query.q === 'string' ? [...route.query.q].slice(0, 500).join('') : '')
const composing = ref(false)
const results = ref<KnowledgeEvidence[]>([])
const searching = ref(false)
const askBusy = ref(false)
const hasSearched = ref(false)
const hasConversation = ref(false)
const working = computed(() => searching.value || askBusy.value)
const inputTooLong = computed(() => [...query.value].length > (mode.value === 'ask' ? 280 : 500))
const pageError = ref<string | null>(null)
const pageErrorCode = ref<string | null>(null)
const composerNotice = ref('')
const catalog = ref<KnowledgeDocument[]>([])
const catalogTotal = ref(0)
const catalogQuery = ref('')
const catalogPage = ref(1)
const catalogPageSize = 4
const catalogLoading = ref(false)
const catalogError = ref('')
const tools = ref<InstanceType<typeof KnowledgeTools> | null>(null)
const drawer = useEvidenceResolution(() => subjectKey.value, invalidateEvidence, () => document.getElementById('knowledge-query')?.focus())
const { open: drawerOpen, loading: drawerLoading, evidence: drawerEvidence, error: drawerError, errorCode: drawerErrorCode } = drawer
let subjectGeneration = 0
let searchGeneration = 0
let statusGeneration = 0
let catalogGeneration = 0
let catalogTimer: ReturnType<typeof setTimeout> | null = null
const accessFailureCodes = ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE']

const currentScopeLabel = computed(() => spaces.value.find(s => s.space_id === selectedSpace.value)?.title || '全部已收录资料')
const retrievalBlocked = computed(() => Boolean(status.value?.retrieval_availability?.blocked))
const canSubmit = computed(() => Boolean(subjectKey.value && status.value?.can_enter && status.value?.can_search && status.value?.gateway_configured && !retrievalBlocked.value && !savedScopeNeedsSelection.value && (mode.value === 'search' || (status.value?.ask_enabled && status.value?.answer_availability?.available !== false))))
watch(subjectKey, () => {
  subjectGeneration++; searchGeneration++; statusGeneration++; catalogGeneration++; drawer.close(false); closeSummary()
  if (catalogTimer) clearTimeout(catalogTimer)
  status.value = null; statusLoading.value = false; results.value = []; query.value = ''; composing.value = false
  searching.value = false; askBusy.value = false; hasConversation.value = false; composerNotice.value = ''
  savedContext.value = null; savedScopeNeedsSelection.value = false
  spaces.value = []; catalog.value = []; catalogTotal.value = 0; selectedSpace.value = ''; catalogQuery.value = ''; catalogPage.value = 1
  catalogLoading.value = false; catalogError.value = ''; pageError.value = null; pageErrorCode.value = null; hasSearched.value = false
  if (subjectKey.value) void refreshStatus()
}, { flush: 'sync' })
watch(selectedSpace, () => {
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false
  pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  if (selectedSpace.value) savedScopeNeedsSelection.value = false
}, { flush: 'sync' })
watch(() => [route.query.equipment_id, route.query.asset_id, route.query.component_id], () => { savedContext.value = null }, { flush: 'sync' })
watch([equipmentId, assetId, componentId], () => {
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false
  tools.value?.newConversation(); pageError.value = null; pageErrorCode.value = null
}, { flush: 'sync' })
watch([catalogQuery, selectedSpace], () => {
  catalogPage.value = 1; catalogGeneration++; catalog.value = []; catalogTotal.value = 0; catalogError.value = ''; catalogLoading.value = true
  if (catalogTimer) clearTimeout(catalogTimer)
  catalogTimer = setTimeout(() => { catalogTimer = null; void refreshCatalog() }, 200)
}, { flush: 'sync' })
watch(catalogPage, () => { if (catalogTimer) clearTimeout(catalogTimer); catalogTimer = null; void refreshCatalog() })
onBeforeUnmount(() => {
  subjectGeneration++; searchGeneration++; statusGeneration++; catalogGeneration++; drawer.close(false); closeSummary()
  if (catalogTimer) clearTimeout(catalogTimer)
})

function applyError(error: unknown) {
  const apiError = error instanceof DomainApiError ? error : null
  pageErrorCode.value = apiError?.code || 'SERVICE_ERROR'; pageError.value = apiError?.message || '知识服务暂时不可用。'
  if (accessFailureCodes.includes(pageErrorCode.value)) {
    results.value = []; drawer.close(false); closeSummary(); tools.value?.invalidateSources()
    catalogGeneration++; catalog.value = []; catalogTotal.value = 0; spaces.value = []; status.value = null
  }
}
function invalidateEvidence(code?: string) {
  results.value = []; closeSummary(); tools.value?.invalidateSources()
  if (code && accessFailureCodes.includes(code)) applyError(new DomainApiError(code, '当前来源不可访问，请重新确认登录状态与资料权限。'))
}
function setMode(value: 'search' | 'ask') {
  if (value === mode.value || (value === 'ask' && !status.value?.ask_enabled)) return
  if (working.value) cancelPending()
  searchGeneration++; results.value = []; hasSearched.value = false
  mode.value = value; composing.value = false; drawer.close(false); pageError.value = null; pageErrorCode.value = null
  void nextTick(() => document.getElementById('knowledge-query')?.focus())
}
function cancelPending() {
  searchGeneration++; searching.value = false; hasSearched.value = false; results.value = []; tools.value?.cancelPending(); askBusy.value = false
  composerNotice.value = '已返回编辑，晚响应不会覆盖当前页面。'
}
function startNewQuestion() { tools.value?.newConversation(); query.value = ''; composerNotice.value = ''; document.getElementById('knowledge-query')?.focus() }
function selectDepartment(id: string) { selectedSpace.value = id; document.getElementById('knowledge-query')?.focus() }
function composerKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  if (composing.value || event.isComposing || event.keyCode === 229) return
  if (mode.value === 'ask') { if (event.ctrlKey || event.metaKey) { event.preventDefault(); void submitComposer() } }
  else { event.preventDefault(); void submitComposer() }
}
async function submitComposer() {
  if (composing.value || working.value || !query.value.trim() || inputTooLong.value) return
  if (savedScopeNeedsSelection.value) { applyError(new DomainApiError('INVALID_REQUEST', '请选择一个明确的部门后再提交。')); return }
  if (mode.value === 'ask') {
    if (!canSubmit.value) { applyError(new DomainApiError('UPSTREAM_UNAVAILABLE', '检索服务暂不可用，目录与个人记录仍可查看。')); return }
    composerNotice.value = ''; await tools.value?.ask(query.value)
  } else await submitSearch()
}
async function submitSearch() {
  const normalized = query.value.trim()
  if (!normalized || searching.value || !subjectKey.value) return
  if (savedScopeNeedsSelection.value) { applyError(new DomainApiError('INVALID_REQUEST', '请选择一个明确的部门后再提交。')); return }
  if (!canSubmit.value) { applyError(new DomainApiError('UPSTREAM_UNAVAILABLE', '检索服务暂不可用，目录与个人记录仍可查看。')); return }
  const generation = ++searchGeneration
  const subject = subjectKey.value
  const scope = selectedSpace.value
  drawer.close(false); searching.value = true; hasSearched.value = true; pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''; results.value = []
  try {
    const response = await searchKnowledge(normalized, { ...currentContext.value }, scope ? [scope] : undefined, searchMode.value)
    if (generation === searchGeneration && subject === subjectKey.value && scope === selectedSpace.value) { results.value = response.results; void tools.value?.refresh() }
  } catch (error) {
    if (generation === searchGeneration && subject === subjectKey.value) { applyError(error); if (pageErrorCode.value === 'UPSTREAM_UNAVAILABLE') void refreshStatus() }
  } finally { if (generation === searchGeneration) searching.value = false }
}
function restoreSaved(data: KnowledgeSavedQuery) {
  if (!data.restored) return
  void router.push('/hbos/knowledge')
  searchGeneration++; drawer.close(false); searching.value=false
  selectedSpace.value=data.space_ids.length===1 ? data.space_ids[0]! : ''
  savedContext.value={...(data.context || {})}; savedScopeNeedsSelection.value=data.space_ids.length>1
  searchMode.value='STANDARD'; setMode(data.restored.mode); query.value=data.query
  results.value=data.restored.results; hasSearched.value=data.restored.mode==='search'
  composerNotice.value='已核验当前来源并恢复记录；未触发模型。'
}
watch(searchMode,()=>{searchGeneration++;results.value=[];hasSearched.value=false;drawer.close(false);tools.value?.newConversation()}, {flush:'sync'})
async function replaySaved(value: string, scope: string[], context: KnowledgeSearchContext = {}) {
  void router.push('/hbos/knowledge')
  setMode('search'); tools.value?.newConversation()
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false
  selectedSpace.value = scope.length === 1 ? scope[0]! : ''
  savedContext.value = { ...context }; query.value = value
  savedScopeNeedsSelection.value = scope.length > 1 || (scope.length === 1 && !spaces.value.some(space => space.space_id === scope[0]))
  if (savedScopeNeedsSelection.value) {
    selectedSpace.value = ''
    composerNotice.value = scope.length > 1 ? '这条记录包含多个部门。请选择一个部门后再提交；不会自动检索。' : '这条记录原来的部门当前不可选。请选择一个明确部门后再提交；不会自动检索。'
    return
  }
  await nextTick()
  await submitSearch()
}
async function openEvidence(item: KnowledgeEvidence) { await drawer.show(item.evidence_id) }
async function refreshCatalog() {
  if (catalogTimer) { clearTimeout(catalogTimer); catalogTimer = null }
  if (!subjectKey.value || status.value?.environment !== 'production') return
  const generation = ++catalogGeneration
  const subject = subjectKey.value
  catalogLoading.value = true; catalogError.value = ''
  try {
    const data = await getKnowledgeDocumentsPage(catalogQuery.value, selectedSpace.value, catalogPage.value, catalogPageSize)
    if (generation !== catalogGeneration || subject !== subjectKey.value) return
    catalog.value = data.documents; catalogTotal.value = data.total
    const lastPage = Math.max(1, Math.ceil(data.total / catalogPageSize))
    if (catalogPage.value > lastPage) catalogPage.value = lastPage
  } catch (error) {
    if (generation === catalogGeneration && subject === subjectKey.value) {
      catalog.value = []; catalogTotal.value = 0; catalogError.value = error instanceof DomainApiError ? error.message : '资料目录暂时不可用。'
      if (error instanceof DomainApiError && accessFailureCodes.includes(error.code)) applyError(error)
    }
  } finally { if (generation === catalogGeneration) catalogLoading.value = false }
}
async function refreshStatus() {
  if (!subjectKey.value) return
  const generation = ++statusGeneration
  const subject = subjectGeneration
  statusLoading.value = true
  try {
    const [current, currentSpaces] = await Promise.all([getKnowledgeStatus(), getKnowledgeSpaces()])
    if (generation !== statusGeneration || subject !== subjectGeneration || !subjectKey.value) return
    if (!current.can_enter || !current.can_search || (status.value?.policy_revision && status.value.policy_revision !== current.policy_revision)) {
      searchGeneration++; results.value = []; hasSearched.value = false; searching.value = false; drawer.close(false); tools.value?.newConversation()
    }
    if (!current.can_enter) { catalogGeneration++; catalog.value = []; catalogTotal.value = 0 }
    status.value = current; spaces.value = current.can_enter ? currentSpaces : []
    if (selectedSpace.value && !currentSpaces.some(space => space.space_id === selectedSpace.value)) selectedSpace.value = ''
    if (!current.ask_enabled && mode.value === 'ask') setMode('search')
    if (current.can_enter && current.environment === 'production' && view.value === 'catalog') await refreshCatalog()
    // Page loads and deep-link prefills never call a model.
  } catch (error) { if (generation === statusGeneration && subject === subjectGeneration) applyError(error) }
  finally { if (generation === statusGeneration) statusLoading.value = false }
}
watch(() => props.sessionRevision, () => { void refreshStatus() })
onMounted(refreshStatus)
</script>
