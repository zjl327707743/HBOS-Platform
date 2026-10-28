<template>
  <div class="knowledge-page" :data-query-state="mode === 'ask' ? (tools?.queryState || 'idle') : searchState">
    <header class="kb-heading"><div><h1>{{ pageTitle }}</h1><p>查阅已共享资料，答案与来源一起呈现。</p></div><a-button :disabled="!subjectKey" @click="connectionOpen = true"><LinkOutlined />连接个人助手</a-button></header>
    <div v-if="equipmentId || assetId || componentId" class="kb-context"><a-tag v-if="equipmentId">设备上下文 {{ equipmentId }}</a-tag><a-tag v-if="assetId">资产范围 {{ assetId }}</a-tag><a-tag v-if="componentId">组件范围 {{ componentId }}</a-tag></div>
    <a-alert v-if="globalError" :type="globalErrorCode === 'FORBIDDEN' ? 'warning' : 'error'" show-icon :message="globalError" class="kb-alert"><template #action><a-button :loading="statusLoading" @click="refreshStatus">刷新状态</a-button></template></a-alert>
    <a-alert v-if="!globalError && statusError && !pageError && !tools?.hasQueryError && (view !== 'catalog' || !catalogError)" type="error" show-icon :message="statusError" class="kb-alert"><template #action><a-button :loading="statusLoading" @click="refreshStatus">刷新状态</a-button></template></a-alert>
    <template v-if="view === 'query'">
      <a-alert v-if="!globalError && (pageError || (!statusError && !tools?.hasQueryError && queryAvailabilityMessage))" type="error" show-icon :message="pageError || queryAvailabilityMessage" class="kb-alert kb-query-alert"><template #action><a-button :loading="statusLoading" @click="refreshStatus">刷新状态</a-button></template></a-alert>
      <section v-if="mode === 'search' || !hasConversation" class="kb-composer hbos-glass-g3" aria-label="知识查询">
        <form class="knowledge-search" @submit.prevent="submitComposer">
          <div class="kb-composer-top"><div class="kb-modes" role="group" aria-label="知识使用方式"><button type="button" :aria-pressed="mode === 'ask'" :disabled="!status?.ask_enabled" @click="setMode('ask')">问知识</button><button type="button" :aria-pressed="mode === 'search'" @click="setMode('search')">搜资料</button></div><label class="sr-only" for="knowledge-space">查询部门范围</label><select id="knowledge-space" v-model="selectedSpace" class="kb-scope-select" :disabled="!spaces.length"><option value="">全部已共享资料</option><option v-for="space in spaces" :key="space.space_id" :value="space.space_id">{{ space.title }}</option></select></div>
          <label class="sr-only" for="knowledge-query">知识问题</label><textarea id="knowledge-query" v-model="query" :maxlength="mode === 'ask' ? 280 : 500" :disabled="working" :placeholder="mode === 'ask' ? '描述你想了解的问题…' : '输入资料标题、文号或关键词…'" rows="3" @compositionstart="composing = true" @compositionend="composing = false" @keydown="composerKeydown" />
          <div class="kb-composer-bottom"><span>{{ mode === 'ask' ? '企业问题核对来源，一般问题明确标示通用 AI' : '直接查找资料与相关依据' }}<small class="kb-keyboard"> · ⌘ / Ctrl + Enter</small></span><a-button type="primary" html-type="submit" :loading="working" :disabled="working || !canSubmit || !query.trim() || inputTooLong">{{ mode === 'ask' ? '提问' : '搜索' }}<ArrowRightOutlined /></a-button></div>
        </form>
        <div v-if="working || composerNotice" class="kb-composer-notice"><a-button v-if="working" @click="cancelPending">返回编辑</a-button><span role="status">{{ composerNotice }}</span></div>
      </section>
      <div v-if="mode==='ask'" class="kb-model-controls"><label for="knowledge-model">回答模型</label><select id="knowledge-model" :value="selectedModel" :disabled="working||modelSaving" class="kb-scope-select" @change="changeModel"><option v-for="item in modelChoices" :key="item.alias" :value="item.alias" :disabled="!item.available">{{item.alias}}{{item.available?'':' · 暂不可用'}}</option></select><label class="kb-knowledge-only"><input v-model="knowledgeOnly" type="checkbox" :disabled="working">仅使用知识库</label></div>
      <div v-if="!hasConversation && !hasSearched && !working && !tools?.hasQueryError" class="kb-start-grid"><section class="kb-suggestions"><div class="kb-section-title"><h2>从一个问题开始</h2><span>示例问题</span></div><button v-for="q in exampleQuestions" :key="q" type="button" @click="useExample(q)"><span>{{ q }}</span><ArrowRightOutlined /></button></section><section class="kb-help-card hbos-glass-g1"><ReadOutlined /><h2>查找资料，也能继续追问</h2><p>点开回答中的来源核对依据。常用资料可以收藏，方便下次直接查阅。</p><RouterLink to="/hbos/knowledge/catalog">打开资料目录<ArrowRightOutlined /></RouterLink></section></div>
      <section v-if="mode === 'search' && hasSearched" class="kb-panel knowledge-results hbos-glass-g1"><div class="kb-section-title"><h2>相关资料</h2><span>{{ results.length }} 条依据</span></div><p v-if="omittedResults" class="kb-search-omitted" role="status">部分来源因安全展示检查未显示（{{ omittedResults }} 条），可联系维护者复核。</p><a-skeleton v-if="searching" active :paragraph="{rows:4}" /><a-empty v-else-if="!results.length && !pageError" description="未找到相关依据，请换一个关键词或调整部门范围。" /><article v-for="item in results" :key="item.evidence_id" class="kb-doc-row result-card"><div class="kb-doc-icon"><FileTextOutlined /></div><button type="button" class="kb-doc-main" :aria-label="'查看来源 '+item.title" @click="openEvidence(item)"><strong>{{ item.title || '未标注标题' }}</strong><p>{{ item.excerpt }}</p><small>{{ [spaces.find(s => s.space_id === item.space_id)?.title, item.document_number, item.version].filter(Boolean).join(' · ') }}</small></button><div class="kb-doc-actions"><a-button :disabled="working" aria-label="打开文档" data-search-open-document @click="openSearchDocument(item)">打开文档</a-button><a-button type="text" :disabled="working" :aria-label="(tools?.isBookmarked(item) ? '取消收藏 ' : '收藏 ') + item.title" @click="tools?.bookmark(item)"><StarFilled v-if="tools?.isBookmarked(item)" class="kb-star" /><StarOutlined v-else /></a-button><a-button type="text" :disabled="working" aria-label="反馈" @click="tools?.feedback(item)"><MessageOutlined /></a-button><a-button type="text" :disabled="working" aria-label="阅读或下载 " @click="openSearchDocument(item)"><DownloadOutlined /></a-button></div></article></section>
    </template>
    <KnowledgeTools v-if="status?.environment === 'production' && status.can_enter && subjectKey" ref="tools" :subject="subjectKey" :query="query" :selected-space="selectedSpace" :spaces="spaces" :ask-enabled="Boolean(status?.ask_enabled) && status?.answer_availability?.available !== false" :retrieval-blocked="retrievalBlocked" :model-alias="selectedModel" :knowledge-only="knowledgeOnly" :mode="mode" :search-mode="searchMode" :view="view" composer-external @busy="askBusy = $event" @conversation="hasConversation = $event" @replay="replaySaved" @restored="restoreSaved" @records-view="router.push($event === 'feedback' ? '/hbos/knowledge/history?tab=feedback' : '/hbos/knowledge/history')" @document="showDocumentSummary" @evidence="openCitationEvidence" @upstream-error="refreshStatus" @access-error="applyError" @evidence-invalidated="invalidateEvidence">
      <template #catalog>
        <section class="kb-panel hbos-glass-g1">
          <form class="kb-list-toolbar catalog-filter" @submit.prevent="refreshCatalog"><label class="sr-only" for="catalog-query">查找标题或文号</label><a-input-search id="catalog-query" v-model:value="catalogQuery" placeholder="查找标题或文号" aria-label="查找标题或文号" @search="refreshCatalog" /><label class="sr-only" for="catalog-department">筛选部门</label><select id="catalog-department" v-model="selectedSpace" class="kb-scope-select"><option value="">全部已共享资料</option><option v-for="space in spaces" :key="space.space_id" :value="space.space_id">{{ space.title }}</option></select><template v-if="showLawFilter"><label class="sr-only" for="catalog-law-category">筛选公共法规类别</label><select id="catalog-law-category" v-model="lawCategory" class="kb-scope-select"><option value="">全部法规类别</option><option v-for="category in knowledgeLawCategories" :key="category" :value="category">{{ category }}</option></select></template></form>
          <div class="kb-list-caption catalog-heading"><span>{{ catalogLoading ? '更新中' : `${catalogTotal} 份资料` }}</span><span>登录员工可直接阅读与下载已发布资料</span></div>
          <nav class="kb-source-breadcrumb" aria-label="资料原目录"><a-button type="link" size="small" @click="sourceFolder = 'SOURCE_ROOT'">全部原目录</a-button><template v-for="crumb in sourceDirectory?.breadcrumbs || []" :key="crumb.folder_id"><span aria-hidden="true"> / </span><a-button type="link" size="small" @click="sourceFolder = crumb.folder_id">{{ crumb.name }}</a-button></template></nav>
          <div v-if="sourceDirectory?.children.length" class="kb-source-folders"><a-button v-for="folder in sourceDirectory.children" :key="folder.folder_id" @click="sourceFolder = folder.folder_id">{{ folder.name }}（{{ folder.count }}）</a-button></div>
          <div class="catalog-content" :aria-busy="catalogLoading"><a-skeleton v-if="catalogLoading && !catalog.length" active :paragraph="{rows:4}" /><a-alert v-else-if="catalogError" type="error" show-icon :message="catalogError" /><a-empty v-else-if="!catalog.length" :description="catalogQuery.trim() ? '没有匹配的资料，请调整标题、文号或部门范围。' : '当前范围暂无可查阅的已收录资料。'" /><template v-else><article v-for="doc in catalog" :key="doc.document_id" class="kb-doc-row catalog-row"><div class="kb-doc-icon"><FileTextOutlined /></div><button class="kb-doc-main" type="button" @click="openDocumentSummary(doc)"><strong>{{ doc.title || '未标注标题' }}</strong><p>{{ doc.status_note }}</p><small v-for="(path, pathIndex) in doc.source_directories || []" :key="pathIndex" class="kb-muted">{{ path.join(' / ') }}</small><small v-if="doc.legal_metadata" class="kb-law-meta">{{ [doc.legal_metadata.category, doc.legal_metadata.issuer].filter(Boolean).join(' · ') }}<a-tag v-if="doc.legal_metadata.effective_status === '现行有效'" color="green">现行有效</a-tag><a-tag v-else-if="doc.legal_metadata.effective_status === '已废止'" color="red">已废止</a-tag></small><small>{{ [doc.document_number, doc.department, doc.version].filter(Boolean).join(' · ') }}<a-tag color="green">已共享</a-tag></small></button><div class="kb-doc-actions"><a-button type="text" :disabled="askBusy || !doc.version_id" :aria-label="(tools?.isBookmarked(doc) ? '取消收藏 ' : '收藏 ') + doc.title" @click="tools?.toggleDocumentBookmark(doc)"><StarFilled v-if="tools?.isBookmarked(doc)" class="kb-star" /><StarOutlined v-else /></a-button><a-button type="text" :disabled="askBusy || !doc.version_id" aria-label="阅读并下载 " @click="openCatalogReader(doc)"><DownloadOutlined /></a-button></div></article></template></div>
          <div class="kb-pagination"><a-pagination v-model:current="catalogPage" v-model:page-size="catalogPageSize" :page-size-options="['20', '50']" :total="catalogTotal" :show-size-changer="true" :disabled="catalogLoading" :show-less-items="true" /></div>
        </section>
      </template>
    </KnowledgeTools>
    <p class="kb-page-footnote">依据可展开核对 · 文件按原版式打开，可直接下载原文件</p>
    <KnowledgeConnections :open="connectionOpen" :subject="subjectKey || ''" @close="connectionOpen = false" />
    <EvidenceDrawer :open="drawerOpen" :loading="drawerLoading" :evidence="drawerEvidence" :error="drawerError" :error-code="drawerErrorCode" :version-id="drawerVersionId" :bookmarked="drawerEvidence ? tools?.isBookmarked(drawerEvidence) : false" @close="drawer.close()" @bookmark="tools?.bookmark($event)" @feedback="tools?.feedback($event)" @read="openEvidenceReader" />
    <a-drawer :open="summaryOpen" title="资料详情" width="min(560px, 100vw)" root-class-name="kb-drawer kb-scope" @close="closeSummary"><a-skeleton v-if="summaryLoading" active /><a-alert v-else-if="summaryError" type="warning" show-icon :message="summaryError" /><template v-else-if="summaryDocument"><h2 class="kb-drawer-title">{{ summaryDocument.title }}</h2><p class="kb-muted">{{ [summaryDocument.document_number, summaryDocument.department, summaryDocument.version].filter(Boolean).join(' · ') }}</p><div class="kb-source-status"><CheckCircleOutlined />当前授权共享版本</div><dl v-if="summaryDocument.legal_metadata" class="kb-legal-details"><template v-for="field in legalDetailFields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ summaryDocument.legal_metadata[field.key] || '未收录' }}</dd></template></dl><div class="kb-source-excerpt"><strong>资料状态</strong><p>{{ summaryDocument.status_note }}</p></div><div class="kb-drawer-actions"><a-button type="primary" data-catalog-open-reader @click="openCatalogReader(summaryDocument)"><ReadOutlined />阅读全文</a-button><a-button :disabled="askBusy" @click="tools?.toggleDocumentBookmark(summaryDocument)"><StarOutlined />{{ tools?.isBookmarked(summaryDocument) ? '取消收藏' : '收藏资料' }}</a-button><a-button data-summary-open-reader @click="openCatalogReader(summaryDocument)"><DownloadOutlined />阅读并下载</a-button></div><p class="kb-muted">打开后会按当前身份与版本核验；原文件可直接下载。</p></template></a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRightOutlined, ReadOutlined, LinkOutlined, FileTextOutlined, StarOutlined, StarFilled, MessageOutlined, DownloadOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import type { KnowledgeEvidence, KnowledgeStatus, KnowledgeSpace, KnowledgeDocument, KnowledgeSearchContext, KnowledgeSavedQuery } from '@/contracts/p1'
import type { KnowledgeReturnSnapshot, KnowledgeToolsReturnState } from '@/contracts/knowledgeReturn'
import type { ReaderSource } from '@/contracts/documentReader'
import { knowledgeLawCategories } from '@/contracts/p1'
import { DomainApiError, getKnowledgeStatus, getKnowledgeSpaces, getKnowledgeDocumentsPage, searchKnowledge, setKnowledgeModelPreference, modelAliases } from '@/services/p1Api'
import EvidenceDrawer from '@/components/knowledge/EvidenceDrawer.vue'
import KnowledgeTools from '@/components/knowledge/KnowledgeTools.vue'
import KnowledgeConnections from '@/components/knowledge/KnowledgeConnections.vue'
import { useEvidenceResolution } from '@/composables/useEvidenceResolution'
import { usePortalStore } from '@/stores/portal'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'
import { loadWorkspace, saveWorkspace } from '@/services/knowledgeWorkspace'

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
let catalogScrollTop = 0
// The twin layout scrolls the window; the candidate layout scrolls #kt-main-content.
function mainScrollElement(): HTMLElement | null {
  const main = document.querySelector<HTMLElement>('#kt-main-content')
  if (main && main.scrollHeight > main.clientHeight + 1) return main
  const scrolling = document.scrollingElement
  return scrolling instanceof HTMLElement ? scrolling : null
}
function catalogScrollElement() { return mainScrollElement() }
watch(view, (next, previous) => {
  if (previous === 'catalog') catalogScrollTop = catalogScrollElement()?.scrollTop || 0
  viewGeneration++; searchGeneration++; searching.value = false; composing.value = false; statusError.value = ''; pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  if (searchState.value === 'loading' || searchState.value === 'error') { searchState.value = searchState.value === 'loading' ? 'cancelled' : 'idle'; hasSearched.value = false; results.value = [] }
  drawer.close(false); closeSummary()
  if (next === 'catalog') {
    void nextTick(() => { const el = catalogScrollElement(); if (el) el.scrollTop = catalogScrollTop })
    void refreshStatus()
  }
}, { flush: 'sync' })
const portal = usePortalStore()
const returnStore = useKnowledgeReturnStore()
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
const statusLoading = ref(false), statusError = ref('')
const spaces = ref<KnowledgeSpace[]>([])
const selectedSpace = ref('')
const selectedModel=ref<import('@/contracts/p1').KnowledgeModelAlias>('gpt-6-luna'),modelSaving=ref(false),knowledgeOnly=ref(false)
const modelChoices=computed(()=>status.value?.model_catalog?.models || modelAliases.map(alias=>({alias,available:alias==='gpt-6-luna'&&Boolean(status.value?.answer_availability?.available),reason:null})))
async function changeModel(event:Event) {
  const alias=(event.target as HTMLSelectElement).value as import('@/contracts/p1').KnowledgeModelAlias
  if(working.value || modelSaving.value)return
  const subject=subjectGeneration,requestView=viewGeneration,old=selectedModel.value;selectedModel.value=alias;modelSaving.value=true
  try{await setKnowledgeModelPreference(alias);if(subject===subjectGeneration && requestView===viewGeneration && view.value==='query' && mode.value==='ask')composerNotice.value='已保存本人模型选择；每轮回答会显示实际模型。'}
  catch(error){if(subject===subjectGeneration){selectedModel.value=old;if(requestView===viewGeneration&&view.value==='query'||error instanceof DomainApiError&&accessFailureCodes.includes(error.code))applyError(error)}}
  finally{if(subject===subjectGeneration)modelSaving.value=false}
}
const savedScopeNeedsSelection = ref(false)
const mode = ref<'search' | 'ask'>('ask')
const searchMode = ref<'STANDARD' | 'PRECISE'>('STANDARD')
const query = ref(typeof route.query.q === 'string' ? [...route.query.q].slice(0, 500).join('') : '')
const composing = ref(false)
const results = ref<KnowledgeEvidence[]>([])
const omittedResults = ref(0)
const searching = ref(false)
const searchState = ref<import('@/contracts/p1').KnowledgeOperationState>('idle')
const askBusy = ref(false)
const hasSearched = ref(false)
const hasConversation = ref(false)
const working = computed(() => searching.value || askBusy.value)
const inputTooLong = computed(() => [...query.value].length > (mode.value === 'ask' ? 280 : 500))
const pageError = ref<string | null>(null)
const pageErrorCode = ref<string | null>(null)
const globalError = ref<string | null>(null), globalErrorCode = ref<string | null>(null)
const composerNotice = ref('')
const catalog = ref<KnowledgeDocument[]>([])
const catalogTotal = ref(0)
const catalogQuery = ref('')
const sourceFolder = ref('SOURCE_ROOT')
const sourceDirectory = ref<import('@/contracts/p1').KnowledgeSourceDirectory | null>(null)
const lawCategory = ref<import('@/contracts/p1').KnowledgeLawCategory | ''>('')
const showLawFilter = computed(() => spaces.value.some(space => space.space_id === 'DEPT_PUBLIC_LAW') && (!selectedSpace.value || selectedSpace.value === 'DEPT_PUBLIC_LAW'))
const legalDetailFields = [{ key: 'category', label: '法规类别' }, { key: 'level', label: '层级' }, { key: 'issuer', label: '发布机构' }, { key: 'published_date', label: '发布或修订日期' }, { key: 'region', label: '地区' }, { key: 'applicability', label: '适用范围' }, { key: 'effective_status', label: '效力状态' }] as const
const catalogPage = ref(1)
const catalogPageSize = ref(20)
const catalogLoading = ref(false)
const catalogError = ref('')
const tools = ref<InstanceType<typeof KnowledgeTools> | null>(null)
const drawer = useEvidenceResolution(() => subjectKey.value, invalidateEvidence, () => document.getElementById('knowledge-query')?.focus())
const { open: drawerOpen, loading: drawerLoading, evidence: drawerEvidence, error: drawerError, errorCode: drawerErrorCode } = drawer
let subjectGeneration = 0
let searchGeneration = 0
let statusGeneration = 0
let catalogGeneration = 0
let savedRestoreGeneration = 0
let viewGeneration = 0
let catalogTimer: ReturnType<typeof setTimeout> | null = null
const accessFailureCodes = ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE']

const drawerVersionId = computed<string | null>(() => {
  const evidence: unknown = drawerEvidence.value
  if (!evidence || typeof evidence !== 'object') return null
  const value = (evidence as { version_id?: unknown }).version_id
  return typeof value === 'string' && value.trim() ? value : null
})

// Returning from the reader must put this workspace back exactly where it was
// without asking again or regenerating an answer. The snapshot is consumed once
// and dropped when it belongs to another signed-in identity.
// A reload, a browser discard or a fresh mount inside the same tab restores the
// last navigation state for this identity. A reader return (below) wins over it.
const savedWorkspace = loadWorkspace(subjectKey.value)
const restoredReturn = returnStore.takeFor(subjectKey.value)
let restoredTools: KnowledgeToolsReturnState | null = null
let restoredScrollTop = 0
let scrollRestored = true
let scrollFromWorkspace = false
if (!restoredReturn && savedWorkspace) {
  if (typeof savedWorkspace.query === 'string' && !route.query.q) query.value = [...savedWorkspace.query].slice(0, 500).join('')
  if (savedWorkspace.mode === 'ask' || savedWorkspace.mode === 'search') mode.value = savedWorkspace.mode
  if (typeof savedWorkspace.selectedSpace === 'string') selectedSpace.value = savedWorkspace.selectedSpace
  if (typeof savedWorkspace.catalogQuery === 'string') catalogQuery.value = savedWorkspace.catalogQuery
  if (Number.isSafeInteger(savedWorkspace.catalogPage) && savedWorkspace.catalogPage >= 1) catalogPage.value = savedWorkspace.catalogPage
  if ([20, 50].includes(savedWorkspace.catalogPageSize)) catalogPageSize.value = savedWorkspace.catalogPageSize
  if (typeof savedWorkspace.lawCategory === 'string') lawCategory.value = savedWorkspace.lawCategory as import('@/contracts/p1').KnowledgeLawCategory | ''
  if (typeof savedWorkspace.sourceFolder === 'string') sourceFolder.value = savedWorkspace.sourceFolder
  restoredScrollTop = Number.isFinite(savedWorkspace.scrollTop) ? savedWorkspace.scrollTop : 0
  scrollRestored = restoredScrollTop <= 0
  scrollFromWorkspace = true
  catalogScrollTop = savedWorkspace.view === 'catalog' ? restoredScrollTop : 0
}
if (restoredReturn && restoredReturn.view === view.value) {
  mode.value = restoredReturn.mode
  searchMode.value = restoredReturn.searchMode
  selectedSpace.value = restoredReturn.selectedSpace
  savedContext.value = restoredReturn.searchContext
  query.value = restoredReturn.query
  results.value = restoredReturn.results
  hasSearched.value = restoredReturn.hasSearched
  searchState.value = restoredReturn.searchState
  catalogQuery.value = restoredReturn.catalog.query
  catalogPage.value = restoredReturn.catalog.page
  lawCategory.value = restoredReturn.catalog.lawCategory
  sourceFolder.value = restoredReturn.catalog.sourceFolder
  restoredTools = restoredReturn.tools
  restoredScrollTop = restoredReturn.scrollTop
  scrollRestored = restoredScrollTop <= 0
}

async function applyReturnedScroll() {
  if (scrollRestored) return
  await nextTick()
  if (scrollRestored) return
  // An answered conversation renders only after the status check. Wait for that
  // content before measuring, otherwise the saved position is clamped to a short page.
  if (view.value === 'query' && restoredTools) return
  if (scrollFromWorkspace && view.value === 'catalog' && catalogLoading.value) return
  const element = mainScrollElement()
  if (element) element.scrollTop = restoredScrollTop
  else if (typeof window.scrollTo === 'function') window.scrollTo(0, restoredScrollTop)
  scrollRestored = true
}

watch(tools, value => {
  if (!value || !restoredTools) return
  const snapshot = restoredTools
  restoredTools = null
  value.restoreState(snapshot)
  scrollRestored = false
  void applyReturnedScroll()
}, { flush: 'post' })

const currentScopeLabel = computed(() => spaces.value.find(s => s.space_id === selectedSpace.value)?.title || '全部已收录资料')
const retrievalBlocked = computed(() => Boolean(status.value?.retrieval_availability?.blocked))
const queryAvailabilityMessage = computed(() => retrievalBlocked.value ? '查询暂不可用，请稍后重试；目录与个人记录仍可查看。' : mode.value === 'ask' && status.value?.answer_availability?.available === false ? '回答服务暂时不可用，可切换搜资料查找依据。' : '')
const canSubmit = computed(() => Boolean(subjectKey.value && status.value?.can_enter && status.value?.can_search && status.value?.gateway_configured && !retrievalBlocked.value && !modelSaving.value && !savedScopeNeedsSelection.value && (mode.value === 'search' || (status.value?.ask_enabled && status.value?.answer_availability?.available !== false))))
watch(subjectKey, () => {
  subjectGeneration++; searchGeneration++; statusGeneration++; catalogGeneration++; savedRestoreGeneration++; drawer.close(false); closeSummary()
  if (catalogTimer) clearTimeout(catalogTimer)
  selectedModel.value='gpt-6-luna';modelSaving.value=false;knowledgeOnly.value=false; status.value = null; statusLoading.value = false; statusError.value = ''; results.value = []; query.value = ''; composing.value = false
  searching.value = false; searchState.value = 'idle'; askBusy.value = false; hasConversation.value = false; composerNotice.value = ''; globalError.value = null; globalErrorCode.value = null
  savedContext.value = null; savedScopeNeedsSelection.value = false
  sourceFolder.value = 'SOURCE_ROOT'; sourceDirectory.value = null
  spaces.value = []; catalog.value = []; catalogTotal.value = 0; selectedSpace.value = ''; catalogQuery.value = ''; lawCategory.value = ''; catalogPage.value = 1
  catalogScrollTop = 0
  catalogLoading.value = false; catalogError.value = ''; pageError.value = null; pageErrorCode.value = null; hasSearched.value = false
  if (subjectKey.value) void refreshStatus()
}, { flush: 'sync' })
watch(selectedSpace, () => {
  if (selectedSpace.value && selectedSpace.value !== 'DEPT_PUBLIC_LAW') lawCategory.value = ''
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false; searchState.value = 'idle'
  pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  if (selectedSpace.value) savedScopeNeedsSelection.value = false
}, { flush: 'sync' })
watch(() => [route.query.equipment_id, route.query.asset_id, route.query.component_id], () => { savedContext.value = null }, { flush: 'sync' })
watch([equipmentId, assetId, componentId], () => {
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false; searchState.value = 'idle'
  tools.value?.newConversation(); pageError.value = null; pageErrorCode.value = null
}, { flush: 'sync' })
watch([catalogQuery, selectedSpace, lawCategory, sourceFolder], () => {
  catalogPage.value = 1; catalogGeneration++; catalog.value = []; catalogTotal.value = 0; catalogError.value = ''; catalogLoading.value = true
  if (catalogTimer) clearTimeout(catalogTimer)
  catalogTimer = setTimeout(() => { catalogTimer = null; void refreshCatalog() }, 200)
}, { flush: 'sync' })
watch(catalogPage, () => { if (catalogTimer) clearTimeout(catalogTimer); catalogTimer = null; void refreshCatalog() })
watch([query, mode, selectedSpace, catalogQuery, catalogPage, catalogPageSize, lawCategory, sourceFolder], () => {
  saveWorkspaceNow(workspaceState())
})
watch(catalogPageSize, () => { if (catalogPage.value !== 1) catalogPage.value = 1; else void refreshCatalog() })
onBeforeUnmount(() => {
  subjectGeneration++; searchGeneration++; statusGeneration++; catalogGeneration++; savedRestoreGeneration++; drawer.close(false); closeSummary()
  if (catalogTimer) clearTimeout(catalogTimer)
})

function applyError(error: unknown) {
  const apiError = error instanceof DomainApiError ? error : null
  const code = apiError?.code || 'SERVICE_ERROR', message = apiError?.message || '知识服务暂时不可用。'
  if (accessFailureCodes.includes(code)) { globalErrorCode.value = code; globalError.value = message; pageError.value = null; pageErrorCode.value = null }
  else { pageErrorCode.value = code; pageError.value = message }
  if (accessFailureCodes.includes(code)) {
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
  mode.value = value; searchState.value = 'idle'; composing.value = false; drawer.close(false); pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  void nextTick(() => document.getElementById('knowledge-query')?.focus())
}
function cancelPending() {
  searchGeneration++; searching.value = false; searchState.value = 'cancelled'; hasSearched.value = false; results.value = []; pageError.value = null; pageErrorCode.value = null; tools.value?.cancelPending(); askBusy.value = false
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
  savedRestoreGeneration++
  if (composing.value || working.value || !query.value.trim() || inputTooLong.value) return
  if (savedScopeNeedsSelection.value) { applyError(new DomainApiError('INVALID_REQUEST', '请选择一个明确的部门后再提交。')); return }
  if (mode.value === 'ask') {
    if (!canSubmit.value) { applyError(new DomainApiError(retrievalBlocked.value || !status.value?.can_search || !status.value?.gateway_configured ? 'UPSTREAM_UNAVAILABLE' : 'ANSWER_MODEL_UNAVAILABLE', queryAvailabilityMessage.value || '回答服务暂时不可用，可切换搜资料查找依据。')); return }
    pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''; await tools.value?.ask(query.value)
  } else await submitSearch()
}
async function submitSearch() {
  savedRestoreGeneration++
  const normalized = query.value.trim()
  if (!normalized || searching.value || !subjectKey.value) return
  if (savedScopeNeedsSelection.value) { applyError(new DomainApiError('INVALID_REQUEST', '请选择一个明确的部门后再提交。')); return }
  if (!canSubmit.value) { applyError(new DomainApiError('UPSTREAM_UNAVAILABLE', '检索服务暂不可用，目录与个人记录仍可查看。')); return }
  const generation = ++searchGeneration
  const subject = subjectKey.value
  const scope = selectedSpace.value
  drawer.close(false); searching.value = true; searchState.value = 'loading'; hasSearched.value = true; pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''; results.value = []; omittedResults.value = 0
  try {
    const response = await searchKnowledge(normalized, { ...currentContext.value }, scope ? [scope] : undefined, searchMode.value)
    if (generation === searchGeneration && subject === subjectKey.value && scope === selectedSpace.value) { results.value = response.results; omittedResults.value = response.omitted_results ?? 0; searchState.value = response.results.length ? 'retrieved' : 'no_evidence'; void tools.value?.refresh() }
  } catch (error) {
    if (generation === searchGeneration && subject === subjectKey.value) { searchState.value = 'error'; applyError(error); if (['UPSTREAM_UNAVAILABLE', 'RETRIEVAL_UPSTREAM_FAILED'].includes(pageErrorCode.value || '')) void refreshStatus() }
  } finally { if (generation === searchGeneration) searching.value = false }
}
async function restoreSaved(data: KnowledgeSavedQuery) {
  if (!data.restored) return
  const current = ++savedRestoreGeneration, subject = subjectKey.value
  await router.push('/hbos/knowledge')
  if (current !== savedRestoreGeneration || subject !== subjectKey.value || view.value !== 'query') return
  searchGeneration++; drawer.close(false); searching.value = false
  selectedSpace.value = data.space_ids.length === 1 ? data.space_ids[0]! : ''
  savedContext.value = { ...(data.context || {}) }; savedScopeNeedsSelection.value = data.space_ids.length > 1
  searchMode.value = 'STANDARD'; setMode(data.restored.mode); query.value = data.query
  results.value = data.restored.results; hasSearched.value = data.restored.mode === 'search'
  searchState.value = data.restored.mode === 'search' ? (data.restored.results.length ? 'retrieved' : 'no_evidence') : 'idle'
  await nextTick()
  if (current !== savedRestoreGeneration || subject !== subjectKey.value || view.value !== 'query') return
  tools.value?.restoreSnapshot(data.restored)
  composerNotice.value = '已核验当前来源并恢复记录；未触发模型。'
}
watch(searchMode,()=>{searchGeneration++;results.value=[];hasSearched.value=false;drawer.close(false);tools.value?.newConversation()}, {flush:'sync'})
async function replaySaved(value: string, scope: string[], context: KnowledgeSearchContext = {}) {
  void router.push('/hbos/knowledge')
  setMode('search'); tools.value?.newConversation()
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false; searchState.value = 'idle'
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
const drawerOrigin = ref<ReaderSource>('ask')
function openCitationEvidence(evidenceId: string) {
  drawerOrigin.value = 'ask'
  void drawer.show(evidenceId)
}
async function openEvidence(item: KnowledgeEvidence) {
  drawerOrigin.value = 'search'
  await drawer.show(item.evidence_id)
}
// The three entry points all capture the same workspace snapshot and then enter
// the single controlled reader route. The reader resolves the current authorized
// version when the entry (citation/search) only carries a document identity.
function workspaceState(): import('@/services/knowledgeWorkspace').KnowledgeWorkspaceState {
  return {
    query: query.value,
    mode: mode.value,
    selectedSpace: selectedSpace.value,
    catalogQuery: catalogQuery.value,
    catalogPage: catalogPage.value,
    catalogPageSize: catalogPageSize.value,
    lawCategory: lawCategory.value,
    sourceFolder: sourceFolder.value,
    view: view.value,
    scrollTop: mainScrollElement()?.scrollTop || 0,
    positions: {},
  }
}
function saveWorkspaceNow(value: import('@/services/knowledgeWorkspace').KnowledgeWorkspaceState) {
  const subject = subjectKey.value
  if (!subject) return
  // Behaviour state only; the reader positions live in their own store and are
  // merged back from what is already stored for this identity.
  const prior = loadWorkspace(subject)
  saveWorkspace(subject, { ...value, positions: prior?.positions || {} })
}
function captureReturnState() {
  saveWorkspaceNow(workspaceState())
  const snapshot: KnowledgeReturnSnapshot = {
    view: view.value,
    query: query.value,
    mode: mode.value,
    selectedSpace: selectedSpace.value,
    searchMode: searchMode.value,
    searchContext: savedContext.value ? { ...savedContext.value } : null,
    results: results.value.map(item => ({ ...item })),
    hasSearched: hasSearched.value,
    searchState: searchState.value,
    tools: tools.value?.snapshotState() ?? null,
    catalog: {
      query: catalogQuery.value,
      page: catalogPage.value,
      lawCategory: lawCategory.value,
      sourceFolder: sourceFolder.value,
    },
    scrollTop: mainScrollElement()?.scrollTop || 0,
  }
  returnStore.capture(subjectKey.value, snapshot)
}
function readerTurn(): string | undefined {
  const conversation = tools.value?.snapshotState().conversation
  return conversation || undefined
}
function openReader(payload: { document_id: string; version_id?: string | null }, from: ReaderSource) {
  if (!payload?.document_id) return
  captureReturnState()
  drawer.close(false)
  closeSummary()
  const turn = from === 'ask' ? readerTurn() : undefined
  void router.push({
    name: 'knowledge-document',
    params: { documentId: payload.document_id },
    query: {
      from,
      ...(payload.version_id ? { version_id: payload.version_id } : {}),
      ...(turn ? { turn } : {}),
    },
  })
}
function openEvidenceReader(payload: { documentId: string; versionId?: string }) {
  openReader({ document_id: payload.documentId, version_id: payload.versionId ?? null }, drawerOrigin.value)
}
function openSearchDocument(item: KnowledgeEvidence) {
  const versionId = (item as KnowledgeEvidence & { version_id?: string | null }).version_id || null
  openReader({ document_id: item.document_id, version_id: versionId }, 'search')
}
function openCatalogReader(doc: KnowledgeDocument) {
  openReader({ document_id: doc.document_id, version_id: doc.version_id || null }, 'catalog')
}
async function refreshCatalog() {
  if (catalogTimer) { clearTimeout(catalogTimer); catalogTimer = null }
  if (!subjectKey.value || status.value?.environment !== 'production') return
  const generation = ++catalogGeneration
  const subject = subjectKey.value
  catalogLoading.value = true; catalogError.value = ''
  try {
    const data = await getKnowledgeDocumentsPage(catalogQuery.value, selectedSpace.value, catalogPage.value, catalogPageSize.value, lawCategory.value || undefined, sourceFolder.value)
    if (generation !== catalogGeneration || subject !== subjectKey.value) return
    sourceDirectory.value = data.source_directory || null; catalog.value = data.documents; catalogTotal.value = data.total
    const lastPage = Math.max(1, Math.ceil(data.total / catalogPageSize.value))
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
  const subject = subjectGeneration, requestView = viewGeneration
  statusLoading.value = true
  try {
    const [current, currentSpaces] = await Promise.all([getKnowledgeStatus(), getKnowledgeSpaces()])
    if (generation !== statusGeneration || subject !== subjectGeneration || !subjectKey.value) return
    if (!current.can_enter || !current.can_search || (status.value?.policy_revision && status.value.policy_revision !== current.policy_revision)) {
      searchGeneration++; results.value = []; hasSearched.value = false; searching.value = false; drawer.close(false); tools.value?.newConversation()
    }
    if (!current.can_enter || (status.value?.policy_revision && status.value.policy_revision !== current.policy_revision)) { catalogGeneration++; catalog.value = []; catalogTotal.value = 0; catalogScrollTop = 0 }
    globalError.value = null; globalErrorCode.value = null; statusError.value = ''
    status.value = current
    if(current.model_catalog)selectedModel.value=current.model_catalog.selected_alias; spaces.value = current.can_enter ? currentSpaces : []
    if (selectedSpace.value && !currentSpaces.some(space => space.space_id === selectedSpace.value)) selectedSpace.value = ''
    if (!current.ask_enabled && mode.value === 'ask') setMode('search')
    if (current.can_enter && current.environment === 'production' && view.value === 'catalog') await refreshCatalog()
    // Page loads and deep-link prefills never call a model.
  } catch (error) {
    if (generation === statusGeneration && subject === subjectGeneration) {
      if (error instanceof DomainApiError && accessFailureCodes.includes(error.code)) applyError(error)
      else if (requestView === viewGeneration) statusError.value = '知识状态暂时无法刷新，请稍后重试。'
    }
  }
  finally { if (generation === statusGeneration) statusLoading.value = false }
}
watch(() => props.sessionRevision, () => { void refreshStatus() })
onMounted(async () => {
  await refreshStatus()
  await applyReturnedScroll()
  saveWorkspaceNow(workspaceState())
})
</script>

<style scoped>
.kb-source-breadcrumb{display:flex;flex-wrap:wrap;align-items:center;margin:8px 0}.kb-source-folders{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 16px}.kb-source-folders button{height:auto;white-space:normal;text-align:left;max-width:100%}
</style>
