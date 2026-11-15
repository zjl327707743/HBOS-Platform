<template>
  <div class="knowledge-page" :data-query-state="mode === 'ask' ? (tools?.queryState || 'idle') : searchState">
    <header class="kb-heading"><div><small class="kb-eyebrow">{{ pageCopy.eyebrow }}</small><h1>{{ pageTitle }}</h1><p>{{ pageCopy.description }}</p></div><a-button v-if="view === 'query'" class="kb-connect-page-action" aria-label="连接个人助手" :disabled="!subjectKey" @click="connectionOpen = true"><LinkOutlined /><span>连接个人助手</span></a-button><RouterLink v-else-if="view === 'favorites'" class="kb-page-action kb-favorites-page-action" aria-label="浏览资料目录" to="/hbos/knowledge/catalog"><FolderOutlined aria-hidden="true" /><span>浏览资料目录</span></RouterLink></header>
    <div v-if="equipmentId || assetId || componentId" class="kb-context"><a-tag v-if="equipmentId">设备上下文 {{ equipmentId }}</a-tag><a-tag v-if="assetId">资产范围 {{ assetId }}</a-tag><a-tag v-if="componentId">组件范围 {{ componentId }}</a-tag></div>
    <a-alert v-if="globalError" :type="globalErrorCode === 'FORBIDDEN' ? 'warning' : 'error'" show-icon :message="globalError" class="kb-alert"><template #action><a-button :loading="statusLoading" @click="refreshStatus">刷新状态</a-button></template></a-alert>
    <a-alert v-if="!globalError && statusError && !pageError && !tools?.hasQueryError && (view !== 'catalog' || !catalogError)" type="error" show-icon :message="statusError" class="kb-alert"><template #action><a-button :loading="statusLoading" @click="refreshStatus">刷新状态</a-button></template></a-alert>
    <template v-if="view === 'query'">
      <a-alert v-if="!globalError && (pageError || (!statusError && !tools?.hasQueryError && queryAvailabilityMessage))" type="error" show-icon :message="pageError || queryAvailabilityMessage" class="kb-alert kb-query-alert"><template #action><a-button :loading="statusLoading" @click="refreshStatus">刷新状态</a-button></template></a-alert>
      <div class="kb-query-grid" :class="{ 'kb-query-start': isQueryStart }">
      <section class="kb-composer hbos-glass-g3" aria-label="知识查询">
        <form class="knowledge-search" @submit.prevent="submitComposer">
          <div class="kb-composer-top"><div class="kb-modes" role="group" aria-label="知识使用方式"><button type="button" :aria-pressed="mode === 'ask'" :disabled="!status?.ask_enabled" @click="setMode('ask')">问知识</button><button type="button" :aria-pressed="mode === 'search'" @click="setMode('search')">搜资料</button></div><label class="sr-only" for="knowledge-space">查询部门范围</label><PortalSelect id="knowledge-space" v-model:value="selectedSpace"
            aria-label="查询部门范围" :options="[{ value: '', label: '全部已共享资料' }, ...spaces.map(space => ({ value: space.space_id, label: space.title }))]" /></div>
          <label class="sr-only" for="knowledge-query">知识问题</label><textarea id="knowledge-query" v-model="query" :maxlength="mode === 'ask' ? 280 : 500" :disabled="working" :placeholder="mode === 'ask' ? (hasConversation ? '继续追问这个问题…' : '描述你想了解的问题…') : '输入资料标题、文号或关键词…'" rows="3" @compositionstart="composing = true" @compositionend="composing = false" @keydown="composerKeydown" />
          <div class="kb-composer-bottom"><label v-if="mode === 'ask'" class="kb-knowledge-only">
            <input v-model="knowledgeOnly" type="checkbox" role="switch" :disabled="working" />
            仅使用知识库 <small aria-hidden="true">{{ knowledgeOnly ? '已开启' : '未开启' }}</small>
          </label><span>{{ mode === 'ask' ? '企业问题核对来源，一般问题明确标示通用 AI' : '直接查找资料与相关依据' }}<small class="kb-keyboard"> · ⌘ / Ctrl + Enter</small></span><a-button type="primary" html-type="submit" :loading="working" :disabled="working || !canSubmit || !query.trim() || inputTooLong">{{ mode === 'ask' ? (hasConversation ? '追问' : '提问') : '搜索' }}<ArrowRightOutlined /></a-button></div>
        </form>
        <div v-if="working || composerNotice" class="kb-composer-notice"><a-button v-if="working" @click="cancelPending">返回编辑</a-button><span role="status">{{ composerNotice }}</span></div>
      </section>
      <section v-if="isQueryStart" class="kb-continue hbos-glass-g1">
        <header><h2>继续查阅</h2><RouterLink to="/hbos/knowledge/history">全部记录</RouterLink></header>
        <ul v-if="tools?.recentRecords?.length">
          <li v-for="item in tools.recentRecords" :key="item.id">
            <button type="button" :disabled="!item.available" @click="tools?.reopen(item.id)">
              <FileTextOutlined /><span>{{ item.query }}</span>
            </button>
          </li>
        </ul>
        <p v-else>已保存的查阅记录会显示在这里。</p>
      </section>
      </div>
      <div v-if="isQueryStart" class="kb-start-grid"><section class="kb-suggestions"><div class="kb-section-title"><h2>从一个问题开始</h2><span>示例问题</span></div><button v-for="q in exampleQuestions" :key="q" type="button" @click="useExample(q)"><span>{{ q }}</span><ArrowRightOutlined /></button></section><section class="kb-help-card hbos-glass-g1"><ReadOutlined /><h2>查找资料，也能继续追问</h2><p>点开回答中的来源核对依据。常用资料可以收藏，方便下次直接查阅。</p><RouterLink to="/hbos/knowledge/catalog">打开资料目录<ArrowRightOutlined /></RouterLink></section></div>
      <section v-if="mode === 'search' && hasSearched" class="kb-panel knowledge-results hbos-glass-g1"><div class="kb-section-title"><h2>相关资料</h2><span>{{ results.length }} 条依据</span></div><p v-if="omittedResults" class="kb-search-omitted" role="status">部分来源因安全展示检查未显示（{{ omittedResults }} 条），可联系维护者复核。</p><a-skeleton v-if="searching" active :paragraph="{rows:4}" /><a-empty v-else-if="!results.length && !pageError" description="未找到相关依据，请换一个关键词或调整部门范围。" /><article v-for="item in results" :key="item.evidence_id" class="kb-doc-row result-card"><div class="kb-doc-icon"><FileTextOutlined /></div><button type="button" class="kb-doc-main" :aria-label="'查看来源 '+item.title" @click="openEvidence(item)"><strong>{{ item.title || '未标注标题' }}</strong><p>{{ item.excerpt }}</p><small>{{ [spaces.find(s => s.space_id === item.space_id)?.title, item.document_number, item.version].filter(Boolean).join(' · ') }}</small></button><div class="kb-doc-actions"><a-button :disabled="working" aria-label="打开文档" data-search-open-document @click="openSearchDocument(item)">打开文档</a-button><a-button type="text" :disabled="working" :aria-label="(tools?.isBookmarked(item) ? '取消收藏 ' : '收藏 ') + item.title" @click="tools?.bookmark(item)"><StarFilled v-if="tools?.isBookmarked(item)" class="kb-star" /><StarOutlined v-else /></a-button><a-button type="text" :disabled="working" aria-label="反馈" @click="tools?.feedback(item)"><MessageOutlined /></a-button><a-button type="text" :disabled="working" aria-label="阅读或下载 " @click="openSearchDocument(item)"><DownloadOutlined /></a-button></div></article></section>
    </template>
    <KnowledgeTools v-if="status?.environment === 'production' && status.can_enter && subjectKey" ref="tools" :subject="subjectKey" :query="query" :selected-space="selectedSpace" :spaces="spaces" :ask-enabled="Boolean(status?.ask_enabled) && status?.answer_availability?.available !== false" :retrieval-blocked="retrievalBlocked" :knowledge-only="knowledgeOnly" :mode="mode" :search-mode="searchMode" :view="view" composer-external @busy="askBusy = $event" @conversation="hasConversation = $event" @new-conversation="clearComposerDraft" @replay="replaySaved" @restored="restoreSaved" @records-view="router.push($event === 'feedback' ? '/hbos/knowledge/history?tab=feedback' : '/hbos/knowledge/history')" @document="showDocumentSummary" @evidence="openCitationEvidence" @upstream-error="refreshStatus" @access-error="applyError" @evidence-invalidated="invalidateEvidence">
      <template #catalog>
        <section class="kb-panel hbos-glass-g1 kb-catalog-panel" aria-label="已共享资料">
          <div class="kb-list-heading">
            <h2>共享资料</h2>
            <span v-if="!catalogLoading && !catalogError" class="kb-list-count">{{ catalogTotal }} 份</span>
            <a-button class="kb-catalog-refresh" :loading="catalogLoading" aria-label="刷新目录" @click="refreshCatalog"><span class="kb-catalog-refresh-label">刷新目录</span><span aria-hidden="true" class="kb-catalog-refresh-icon">↻</span></a-button>
          </div>
          <form class="kb-list-toolbar catalog-filter" @submit.prevent="refreshCatalog">
            <label class="sr-only" for="catalog-query">搜索资料</label>
            <a-input-search id="catalog-query" v-model:value="catalogQuery" :maxlength="240"
              placeholder="搜标题、文号或资料关键词" aria-label="搜索资料" enter-button="搜索"
              @search="refreshCatalog" />
          </form>
          <div class="kb-catalog-categories" role="group" aria-label="资料分类">
            <button type="button" :aria-pressed="!topCategory" @click="catalogCategory = ''">全部</button>
            <button v-for="item in topCategories" :key="item.category_id" type="button"
              :aria-pressed="topCategory?.category_id === item.category_id"
              @click="catalogCategory = item.category_id">{{ item.path[0] }}</button>
          </div>
          <div class="kb-catalog-filters">
            <div class="kb-catalog-filter-field kb-catalog-subcategory">
              <label for="catalog-subcategory">细分类</label>
              <PortalSelect id="catalog-subcategory" aria-label="搜索并选择细分类" searchable
                :value="selectedCategory && selectedCategory.path.length > 1 ? catalogCategory : ''"
                :options="subcategoryOptions" @change="selectSubcategory" />
            </div>
            <div class="kb-catalog-filter-field">
              <label for="catalog-format">文件类型</label>
              <PortalSelect id="catalog-format" v-model:value="catalogFormat"
                :options="[{ value: '', label: '全部类型' }, ...catalogFormats.map(format => ({ value: format, label: format.toUpperCase() }))]" />
            </div>
            <div class="kb-catalog-filter-field">
              <label for="catalog-sort">排序</label>
              <PortalSelect id="catalog-sort" v-model:value="catalogSort" :options="catalogSortOptions" />
            </div>
            <a-button v-if="catalogHasFilters" type="text" @click="clearCatalogFilters">清除筛选</a-button>
          </div>
          <div class="kb-catalog-result" aria-live="polite">
            <span v-if="selectedCategory">已选 {{ selectedCategory.path.join(' / ') }}</span>
            <span v-if="catalogLoading">正在更新</span>
            <span v-else-if="!catalogError">找到 {{ catalogTotal }} 份资料</span>
          </div>
          <a-alert v-if="catalogActionError" type="error" show-icon :message="catalogActionError" />
          <div class="catalog-content" :aria-busy="catalogLoading">
            <a-skeleton v-if="catalogLoading && !catalog.length" active :paragraph="{rows:4}" />
            <a-alert v-else-if="catalogError" type="error" show-icon :message="catalogError">
              <template #action><a-button @click="refreshCatalog">重试</a-button></template>
            </a-alert>
            <a-empty v-else-if="!catalog.length" :description="catalogEmptyText">
              <a-button v-if="catalogHasFilters" @click="clearCatalogFilters">清除筛选</a-button>
            </a-empty>
            <article v-for="doc in catalog" v-show="!catalogError"
              :key="doc.document_id + ':' + doc.version_id" class="kb-doc-row catalog-row">
              <div class="kb-doc-icon" aria-hidden="true"><FileTextOutlined /></div>
              <button :id="'catalog-document-' + doc.document_id" class="kb-doc-main" type="button"
                :title="doc.title || undefined" @click="openCatalogReader(doc)">
                <strong>{{ doc.title || '未标注标题' }}</strong>
                <small v-if="doc.source_directories?.length">{{ doc.source_directories[0]?.join(' / ') }}</small>
                <small v-if="rowMeta(doc)">{{ rowMeta(doc) }}</small>
              </button>
              <div class="kb-doc-actions">
                <a-button size="small" :disabled="!doc.version_id" @click="openCatalogReader(doc)">阅读</a-button>
                <a-button type="text" :disabled="!doc.version_id"
                  :aria-label="(tools?.isBookmarked(doc) ? '取消收藏 ' : '收藏 ') + doc.title"
                  @click="tools?.toggleDocumentBookmark(doc)">
                  <StarFilled v-if="tools?.isBookmarked(doc)" class="kb-star" /><StarOutlined v-else />
                </a-button>
                <a-button type="text" :disabled="!doc.version_id || doc.download_state === 'unavailable'"
                  :loading="catalogDownloading === doc.document_id" :title="doc.download_note || undefined"
                  :aria-label="'下载原文件 ' + doc.title" @click="downloadCatalogOriginal(doc)"><DownloadOutlined /></a-button>
              </div>
            </article>
          </div>
          <div v-if="!catalogError && catalogTotal > 20" class="kb-pagination">
            <a-pagination v-model:current="catalogPage" v-model:page-size="catalogPageSize"
              :page-size-options="['20', '50']" :total="catalogTotal" :show-size-changer="true"
              :disabled="catalogLoading" :show-less-items="true" />
          </div>
        </section>
      </template>
    </KnowledgeTools>
    <p class="kb-page-footnote">依据可展开核对 · 文件按原版式打开，可直接下载原文件<span class="kb-release-note"> · 候选版 D20261102</span></p>
    <KnowledgeConnections :open="connectionOpen" :subject="subjectKey || ''" @close="closeConnection" />
    <EvidenceDrawer :open="drawerOpen" :loading="drawerLoading" :evidence="drawerEvidence" :error="drawerError" :error-code="drawerErrorCode" :version-id="drawerVersionId" :bookmarked="drawerEvidence ? tools?.isBookmarked(drawerEvidence) : false" @close="drawer.close()" @bookmark="tools?.bookmark($event)" @feedback="tools?.feedback($event)" @read="openEvidenceReader" />
    <a-drawer :open="summaryOpen" title="资料详情" width="min(560px, 100vw)" root-class-name="kb-drawer kb-scope" @close="closeSummary"><template v-if="summaryDocument"><h2 class="kb-drawer-title">{{ summaryDocument.title }}</h2><p class="kb-muted">{{ [summaryDocument.document_number, summaryDocument.department, summaryDocument.version].filter(Boolean).join(' · ') }}</p><div class="kb-source-status"><CheckCircleOutlined />当前授权共享版本</div><dl v-if="summaryDocument.legal_metadata" class="kb-legal-details"><template v-for="field in legalDetailFields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ summaryDocument.legal_metadata[field.key] || '未收录' }}</dd></template></dl><div class="kb-source-excerpt"><strong>资料状态</strong><p>{{ summaryDocument.status_note }}</p></div><div class="kb-drawer-actions"><a-button type="primary" data-catalog-open-reader @click="openCatalogReader(summaryDocument)"><ReadOutlined />阅读全文</a-button><a-button :disabled="askBusy" @click="tools?.toggleDocumentBookmark(summaryDocument)"><StarOutlined />{{ tools?.isBookmarked(summaryDocument) ? '取消收藏' : '收藏资料' }}</a-button><a-button data-summary-open-reader @click="openCatalogReader(summaryDocument)"><DownloadOutlined />阅读并下载</a-button></div><p class="kb-muted">打开后会按当前身份与版本核验；原文件可直接下载。</p></template></a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRightOutlined, ReadOutlined, LinkOutlined, FileTextOutlined, FolderOutlined, StarOutlined, StarFilled, MessageOutlined, DownloadOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import type { KnowledgeEvidence, KnowledgeStatus, KnowledgeSpace, KnowledgeDocument, KnowledgeSearchContext, KnowledgeSavedQuery, KnowledgeCatalogCategory, KnowledgeCatalogSort } from '@/contracts/p1'
import type { KnowledgeReturnSnapshot, KnowledgeToolsReturnState } from '@/contracts/knowledgeReturn'
import type { ReaderSource } from '@/contracts/documentReader'
import { DomainApiError, getKnowledgeStatus, getKnowledgeSpaces, getKnowledgeEmployeeCatalogPage, searchKnowledge } from '@/services/p1Api'
import PortalSelect from '@/components/portal/PortalSelect.vue'
import EvidenceDrawer from '@/components/knowledge/EvidenceDrawer.vue'
import KnowledgeTools from '@/components/knowledge/KnowledgeTools.vue'
import KnowledgeConnections from '@/components/knowledge/KnowledgeConnections.vue'
import { useEvidenceResolution } from '@/composables/useEvidenceResolution'
import { usePortalStore } from '@/stores/portal'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'
import { loadWorkspace, saveWorkspace } from '@/services/knowledgeWorkspace'
import { createDocumentDelivery, startDocumentDownload } from '@/services/knowledgeDelivery'

const route = useRoute()
const router = useRouter()
const props = defineProps<{sessionRevision?:number}>()
const view = computed<'query'|'catalog'|'favorites'|'history'|'feedback'>(() => route.path?.endsWith('/catalog') ? 'catalog' : route.path?.endsWith('/favorites') ? 'favorites' : route.path?.endsWith('/history') ? (route.query.tab === 'feedback' ? 'feedback' : 'history') : 'query')
const pageTitle = computed(() => ({query:'知识库',catalog:'资料目录',favorites:'我的收藏',history:'我的记录',feedback:'我的记录'}[view.value]))
const pageCopy = computed(() => ({
  query: { eyebrow: 'KNOWLEDGE WORKSPACE', description: '查阅已共享资料，答案与来源一起呈现。' },
  catalog: { eyebrow: 'DOCUMENT LIBRARY', description: '从目录查找资料，核对版本后再使用。' },
  favorites: { eyebrow: 'MY COLLECTION', description: '把常用资料留在手边，重新打开时核对当前来源。' },
  history: { eyebrow: 'MY ACTIVITY', description: '继续之前的查阅，也可以查看反馈处理进展。' },
  feedback: { eyebrow: 'MY ACTIVITY', description: '继续之前的查阅，也可以查看反馈处理进展。' },
})[view.value])
const catalogSortOptions: { value: KnowledgeCatalogSort; label: string }[] = [
  { value: 'relevance', label: '相关性' }, { value: 'title', label: '标题升序' }, { value: 'title_desc', label: '标题降序' },
]
const isQueryStart = computed(() => !hasConversation.value && !hasSearched.value && !working.value && !tools.value?.hasQueryError)
const exampleQuestions = ['培养箱使用前需要检查哪些项目？','在哪里查找岗位安全培训资料？','如何确认引用的是当前版本？']
const summaryOpen = ref(false)
const summaryDocument = ref<KnowledgeDocument | null>(null)
function closeSummary() {
  summaryOpen.value = false
  summaryDocument.value = null
}
function showDocumentSummary(doc: KnowledgeDocument) {
  summaryDocument.value = doc
  summaryOpen.value = true
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
let queryScrollTop = 0
watch(view, (next, previous) => {
  if (previous === 'catalog') catalogScrollTop = catalogScrollElement()?.scrollTop || 0
  if (previous === 'query') queryScrollTop = mainScrollElement()?.scrollTop || 0
  catalogActionError.value = ''; catalogDownloading.value = ''
  viewGeneration++; searchGeneration++; searching.value = false; composing.value = false; statusError.value = ''; pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  if (searchState.value === 'loading' || searchState.value === 'error') { searchState.value = searchState.value === 'loading' ? 'cancelled' : 'idle'; hasSearched.value = false; results.value = [] }
  drawer.close(false); closeSummary()
  if (next === 'catalog') {
    void nextTick(() => { const el = catalogScrollElement(); if (el) el.scrollTop = catalogScrollTop })
    void refreshStatus()
  } else if (next === 'query') {
    void nextTick(() => { const el = mainScrollElement(); if (el) el.scrollTop = queryScrollTop })
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
watch(() => route.query.connect, value => {
  if (value === '1') connectionOpen.value = true
}, { immediate: true })
function closeConnection() {
  connectionOpen.value = false
  if (route.query.connect !== '1') return
  const query = { ...route.query }
  delete query.connect
  void router.replace({ query })
  void nextTick(() => document.querySelector<HTMLElement>('.kb-mobile-trigger, .kb-sidebar a[href$="connect=1"]')?.focus())
}
const status = ref<KnowledgeStatus | null>(null)
const statusLoading = ref(false), statusError = ref('')
const spaces = ref<KnowledgeSpace[]>([])
const selectedSpace = ref('')
const knowledgeOnly = ref(false)
const savedScopeNeedsSelection = ref(false)
const mode = ref<'search' | 'ask'>('ask')
const searchMode = ref<'STANDARD' | 'PRECISE'>('STANDARD')
const query = ref(typeof route.query.q === 'string' ? [...route.query.q].slice(0, 500).join('') : '')
const modeDrafts = { ask: '', search: '' }
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
const catalog = ref<(KnowledgeDocument & { file_formats: string[] })[]>([])
const catalogTotal = ref(0)
const catalogQuery = ref('')
const catalogCategory = ref('')
const catalogFormat = ref('')
const catalogSort = ref<KnowledgeCatalogSort>('relevance')
function restoreCatalogFilters(category: unknown, format: unknown, sort: unknown) {
  if (typeof category === 'string' && /^FOLDER_[a-f0-9]{24}$/.test(category)) catalogCategory.value = category
  if (typeof format === 'string' && /^[a-z0-9]{1,12}$/.test(format)) catalogFormat.value = format
  if (sort === 'title' || sort === 'title_desc' || sort === 'relevance') catalogSort.value = sort
}
const catalogCategories = ref<KnowledgeCatalogCategory[]>([])
const catalogFormats = ref<string[]>([])
const catalogActionError = ref('')
const catalogDownloading = ref('')
const topCategories = computed(() => catalogCategories.value.filter(item => item.path.length === 1))
const selectedCategory = computed(() => catalogCategories.value.find(item => item.category_id === catalogCategory.value))
const topCategory = computed(() => topCategories.value.find(item => item.path[0] === selectedCategory.value?.path[0]))
const subcategoryOptions = computed(() => [
  { value: '', label: '全部细分类' },
  ...catalogCategories.value
    .filter(item => item.path.length > 1 && (!topCategory.value || item.path[0] === topCategory.value.path[0]))
    .map(item => ({ value: item.category_id, label: item.path.join(' / ') })),
])
const catalogHasFilters = computed(() => Boolean(catalogCategory.value || catalogFormat.value ||
  catalogSort.value !== 'relevance' || catalogQuery.value.trim()))
const catalogEmptyText = computed(() => catalogHasFilters.value
  ? '当前条件没有匹配的资料。' : '当前没有可查阅的已共享资料。')
function clearCatalogFilters() {
  catalogCategory.value = ''
  catalogFormat.value = ''
  catalogSort.value = 'relevance'
  catalogQuery.value = ''
}
function selectSubcategory(value: unknown) {
  if (typeof value === 'string') catalogCategory.value = value || topCategory.value?.category_id || ''
}
function rowMeta(doc: KnowledgeDocument & { file_formats: string[] }): string {
  return [...doc.file_formats.map(format => format.toUpperCase()), doc.document_number, doc.version].filter(Boolean).join(' · ')
}
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
let restoredCatalogFocus = ''
let scrollRestored = true
let scrollFromWorkspace = false
if (savedWorkspace?.modeDrafts) {
  modeDrafts.ask = typeof savedWorkspace.modeDrafts.ask === 'string' ? [...savedWorkspace.modeDrafts.ask].slice(0, 280).join('') : ''
  modeDrafts.search = typeof savedWorkspace.modeDrafts.search === 'string' ? [...savedWorkspace.modeDrafts.search].slice(0, 500).join('') : ''
}
if (!restoredReturn && savedWorkspace) {
  if (typeof savedWorkspace.query === 'string' && !route.query.q) query.value = [...savedWorkspace.query].slice(0, 500).join('')
  if (savedWorkspace.mode === 'ask' || savedWorkspace.mode === 'search') mode.value = savedWorkspace.mode
  if (typeof savedWorkspace.selectedSpace === 'string') selectedSpace.value = savedWorkspace.selectedSpace
  if (typeof savedWorkspace.catalogQuery === 'string') catalogQuery.value = savedWorkspace.catalogQuery
  if (Number.isSafeInteger(savedWorkspace.catalogPage) && savedWorkspace.catalogPage >= 1) catalogPage.value = savedWorkspace.catalogPage
  if ([20, 50].includes(savedWorkspace.catalogPageSize)) catalogPageSize.value = savedWorkspace.catalogPageSize
  restoreCatalogFilters(savedWorkspace.sourceFolder, savedWorkspace.catalogFormat, savedWorkspace.catalogSort)
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
  if (restoredReturn.catalog.pageSize === 20 || restoredReturn.catalog.pageSize === 50) catalogPageSize.value = restoredReturn.catalog.pageSize
  restoreCatalogFilters(restoredReturn.catalog.sourceFolder, restoredReturn.catalog.format, restoredReturn.catalog.sort)
  restoredCatalogFocus = restoredReturn.catalog.focusDocument || ''
  restoredTools = restoredReturn.tools
  restoredScrollTop = restoredReturn.scrollTop
  scrollRestored = restoredScrollTop <= 0
}
// The knowledge-only switch is navigation state, not conversation content, so
// it belongs to the workspace rather than the in-memory return snapshot. Apply
// it in every restore path (reload and reader return) and accept only a real
// boolean: an older cache without the field means "off", and a malformed value
// must never silently enable it.
if (savedWorkspace) knowledgeOnly.value = savedWorkspace.knowledgeOnly === true
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

const retrievalBlocked = computed(() => Boolean(status.value?.retrieval_availability?.blocked))
const queryAvailabilityMessage = computed(() => retrievalBlocked.value ? '查询暂不可用，请稍后重试；目录与个人记录仍可查看。' : mode.value === 'ask' && status.value?.answer_availability?.available === false ? '回答服务暂时不可用，可切换搜资料查找依据。' : '')
const canSubmit = computed(() => Boolean(subjectKey.value && status.value?.can_enter && status.value?.can_search && status.value?.gateway_configured && !retrievalBlocked.value && !savedScopeNeedsSelection.value && (mode.value === 'search' || (status.value?.ask_enabled && status.value?.answer_availability?.available !== false))))
watch(subjectKey, () => {
  subjectGeneration++; searchGeneration++; statusGeneration++; catalogGeneration++; savedRestoreGeneration++; drawer.close(false); closeSummary()
  if (catalogTimer) clearTimeout(catalogTimer)
  modeDrafts.ask = ''; modeDrafts.search = ''; knowledgeOnly.value=false; status.value = null; statusLoading.value = false; statusError.value = ''; results.value = []; query.value = ''; composing.value = false
  searching.value = false; searchState.value = 'idle'; askBusy.value = false; hasConversation.value = false; composerNotice.value = ''; globalError.value = null; globalErrorCode.value = null
  savedContext.value = null; savedScopeNeedsSelection.value = false
  catalogCategories.value = []; catalogFormats.value = []; catalogDownloading.value = ''; catalogActionError.value = ''
  clearCatalogFilters()
  spaces.value = []; catalog.value = []; catalogTotal.value = 0; selectedSpace.value = ''; catalogPage.value = 1
  catalogScrollTop = 0; queryScrollTop = 0
  catalogLoading.value = false; catalogError.value = ''; pageError.value = null; pageErrorCode.value = null; hasSearched.value = false
  if (subjectKey.value) void refreshStatus()
}, { flush: 'sync' })
watch(selectedSpace, () => {
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false; searchState.value = 'idle'
  pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  if (selectedSpace.value) savedScopeNeedsSelection.value = false
}, { flush: 'sync' })
watch(() => [route.query.equipment_id, route.query.asset_id, route.query.component_id], () => { savedContext.value = null }, { flush: 'sync' })
watch([equipmentId, assetId, componentId], () => {
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false; searchState.value = 'idle'
  tools.value?.newConversation(); pageError.value = null; pageErrorCode.value = null
}, { flush: 'sync' })
watch([catalogQuery, catalogCategory, catalogFormat, catalogSort], () => {
  catalogPage.value = 1; catalogGeneration++; catalog.value = []; catalogTotal.value = 0; catalogError.value = ''; catalogLoading.value = true
  catalogActionError.value = ''
  if (catalogTimer) clearTimeout(catalogTimer)
  catalogTimer = setTimeout(() => { catalogTimer = null; void refreshCatalog() }, 200)
}, { flush: 'sync' })
watch(catalogPage, () => {
  catalog.value = []
  void refreshCatalog()
})
watch([query, mode, selectedSpace, catalogQuery, catalogPage, catalogPageSize, catalogCategory, catalogFormat, catalogSort, knowledgeOnly], () => {
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
    catalogGeneration++; catalog.value = []; catalogTotal.value = 0; catalogCategories.value = []; catalogFormats.value = []; spaces.value = []; status.value = null
  }
}
function invalidateEvidence(code?: string) {
  results.value = []; closeSummary(); tools.value?.invalidateSources()
  if (code && accessFailureCodes.includes(code)) applyError(new DomainApiError(code, '当前来源不可访问，请重新确认登录状态与资料权限。'))
}
function setMode(value: 'search' | 'ask') {
  if (value === mode.value || (value === 'ask' && !status.value?.ask_enabled)) return
  if (working.value) { composerNotice.value = '查询进行中，请先返回编辑后再切换。'; return }
  modeDrafts[mode.value] = query.value
  query.value = modeDrafts[value]
  searchGeneration++; results.value = []; hasSearched.value = false
  mode.value = value; searchState.value = 'idle'; composing.value = false; drawer.close(false); pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  void nextTick(() => document.getElementById('knowledge-query')?.focus())
}
function cancelPending() {
  searchGeneration++; searching.value = false; searchState.value = 'cancelled'; hasSearched.value = false; results.value = []; pageError.value = null; pageErrorCode.value = null; tools.value?.cancelPending(); askBusy.value = false
  composerNotice.value = '已返回编辑，晚响应不会覆盖当前页面。'
}
function composerKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  if (composing.value || event.isComposing || event.keyCode === 229) return
  if (mode.value === 'ask') { if (event.ctrlKey || event.metaKey) { event.preventDefault(); void submitComposer() } }
  else if (!event.shiftKey) { event.preventDefault(); void submitComposer() }
}
function clearComposerDraft() {
  query.value = ''
  pageError.value = null
  pageErrorCode.value = null
  composerNotice.value = ''
}
async function submitComposer() {
  savedRestoreGeneration++
  if (composing.value || working.value || !query.value.trim() || inputTooLong.value) return
  if (savedScopeNeedsSelection.value) { applyError(new DomainApiError('INVALID_REQUEST', '请选择一个明确的部门后再提交。')); return }
  if (mode.value === 'ask') {
    if (!canSubmit.value) { applyError(new DomainApiError(retrievalBlocked.value || !status.value?.can_search || !status.value?.gateway_configured ? 'UPSTREAM_UNAVAILABLE' : 'ANSWER_MODEL_UNAVAILABLE', queryAvailabilityMessage.value || '回答服务暂时不可用，可切换搜资料查找依据。')); return }
    pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''; if (await tools.value?.ask(query.value)) query.value = ''
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
  // Reopening a saved record normally replaces the composer. The exception is
  // the record of the conversation already open: its latest restored turn is
  // the open conversation's turn pointer, so the unsent draft stays. Capture
  // both identities before the route change; the guards below still decide
  // whether this restore may happen at all.
  const openTurn = tools.value?.snapshotState().conversation || ''
  const openDraft = query.value
  const restoredTurn = data.restored.mode === 'ask' ? data.restored.turns[data.restored.turns.length - 1]?.turn_id || '' : ''
  const keepDraft = Boolean(openTurn && openTurn === restoredTurn)
  const current = ++savedRestoreGeneration, subject = subjectKey.value
  await router.push('/hbos/knowledge')
  if (current !== savedRestoreGeneration || subject !== subjectKey.value || view.value !== 'query') return
  searchGeneration++; drawer.close(false); searching.value = false
  selectedSpace.value = data.space_ids.length === 1 ? data.space_ids[0]! : ''
  savedContext.value = { ...(data.context || {}) }; savedScopeNeedsSelection.value = data.space_ids.length > 1
  searchMode.value = data.restored.search_mode; setMode(data.restored.mode); query.value = data.restored.mode === 'search' ? data.query : keepDraft ? openDraft : ''
  pageError.value = null; pageErrorCode.value = null
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
    modeDrafts: { ...modeDrafts, [mode.value]: query.value },
    selectedSpace: selectedSpace.value,
    catalogQuery: catalogQuery.value,
    catalogPage: catalogPage.value,
    catalogPageSize: catalogPageSize.value,
    sourceFolder: catalogCategory.value || 'SOURCE_ROOT',
    catalogFormat: catalogFormat.value,
    catalogSort: catalogSort.value,
    knowledgeOnly: knowledgeOnly.value,
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
function captureReturnState(focusDocument?: string) {
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
      sourceFolder: catalogCategory.value || 'SOURCE_ROOT',
      format: catalogFormat.value,
      sort: catalogSort.value,
      pageSize: catalogPageSize.value,
      focusDocument,
    },
    scrollTop: mainScrollElement()?.scrollTop || 0,
  }
  returnStore.capture(subjectKey.value, snapshot)
}
function readerTurn(): string | undefined {
  const conversation = tools.value?.snapshotState().conversation
  return conversation || undefined
}
function trustedPhysicalPage(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 1 && value <= 10000 ? value : null
}
function openReader(payload: { document_id: string; version_id?: string | null; physical_page?: number | null }, from: ReaderSource) {
  if (!payload?.document_id) return
  captureReturnState(from === 'catalog' ? payload.document_id : undefined)
  drawer.close(false)
  closeSummary()
  const turn = from === 'ask' ? readerTurn() : undefined
  const physicalPage = trustedPhysicalPage(payload.physical_page)
  void router.push({
    name: 'knowledge-document',
    params: { documentId: payload.document_id },
    query: {
      from,
      ...(payload.version_id ? { version_id: payload.version_id } : {}),
      ...(physicalPage ? { physical_page: String(physicalPage) } : {}),
      ...(turn ? { turn } : {}),
    },
  })
}
function openEvidenceReader(payload: { documentId: string; versionId?: string; physicalPage?: number }) {
  openReader({ document_id: payload.documentId, version_id: payload.versionId ?? null, physical_page: payload.physicalPage ?? null }, drawerOrigin.value)
}
function openSearchDocument(item: KnowledgeEvidence) {
  const versionId = (item as KnowledgeEvidence & { version_id?: string | null }).version_id || null
  openReader({ document_id: item.document_id, version_id: versionId, physical_page: item.page_number ?? null }, 'search')
}
function openCatalogReader(doc: KnowledgeDocument) {
  openReader({ document_id: doc.document_id, version_id: doc.version_id || null }, 'catalog')
}
async function downloadCatalogOriginal(doc: KnowledgeDocument) {
  if (!doc.version_id || doc.download_state === 'unavailable' || catalogDownloading.value) return
  const subject = subjectGeneration, requestView = viewGeneration
  catalogDownloading.value = doc.document_id
  catalogActionError.value = ''
  try {
    const delivery = await createDocumentDelivery(doc.document_id, doc.version_id, 'download')
    if (subject === subjectGeneration && requestView === viewGeneration) startDocumentDownload(delivery)
  } catch (error) {
    if (subject !== subjectGeneration || requestView !== viewGeneration) return
    if (error instanceof DomainApiError && accessFailureCodes.includes(error.code)) applyError(error)
    else catalogActionError.value = error instanceof DomainApiError ? error.message : '原文件下载未完成，请重试。'
  } finally {
    if (subject === subjectGeneration && requestView === viewGeneration) catalogDownloading.value = ''
  }
}
let catalogPending: { key: string; promise: ReturnType<typeof getKnowledgeEmployeeCatalogPage> } | null = null
async function refreshCatalog() {
  if (catalogTimer) { clearTimeout(catalogTimer); catalogTimer = null }
  if (!subjectKey.value || view.value !== 'catalog' || status.value?.environment !== 'production') return
  const generation = ++catalogGeneration
  const subject = subjectKey.value
  catalogLoading.value = true; catalogError.value = ''
  const filters = {
    query: catalogQuery.value,
    category_ids: catalogCategory.value ? [catalogCategory.value] : [],
    format: catalogFormat.value || null,
    sort: catalogSort.value,
  }
  const args = [filters, catalogPage.value, catalogPageSize.value] as const
  const key = JSON.stringify([subject, subjectGeneration, status.value?.policy_revision, ...args])
  // Enter can emit both search and form-submit while the filter debounce is
  // pending. Share only the identical in-flight read; never cache its result
  // or share a request across an identity, policy or browsing-range change.
  let pending = catalogPending
  try {
    if (!pending || pending.key !== key) {
      pending = {key, promise: getKnowledgeEmployeeCatalogPage(...args)}
      catalogPending = pending
    }
    const data = await pending.promise
    if (generation !== catalogGeneration || subject !== subjectKey.value) return
    catalogCategories.value = data.category_options
    catalogFormats.value = data.format_options
    catalog.value = data.documents
    catalogTotal.value = data.total_documents
    const lastPage = Math.max(1, Math.ceil(data.total_documents / catalogPageSize.value))
    if (catalogPage.value > lastPage) catalogPage.value = lastPage
  } catch (error) {
    if (generation === catalogGeneration && subject === subjectKey.value) {
      if (error instanceof DomainApiError && error.code === 'SCOPE_REJECTED' && catalogCategory.value) {
        catalogCategory.value = ''
        return
      }
      catalog.value = []; catalogTotal.value = 0; catalogError.value = error instanceof DomainApiError ? error.message : '资料目录暂时不可用。'
      if (error instanceof DomainApiError && accessFailureCodes.includes(error.code)) applyError(error)
    }
  } finally {
    if (catalogPending === pending) catalogPending = null
    if (generation === catalogGeneration) catalogLoading.value = false
  }
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
    if (!current.can_enter || (status.value?.policy_revision && status.value.policy_revision !== current.policy_revision)) { catalogGeneration++; catalog.value = []; catalogTotal.value = 0; catalogCategories.value = []; catalogFormats.value = []; catalogScrollTop = 0 }
    globalError.value = null; globalErrorCode.value = null; statusError.value = ''
    status.value = current
    spaces.value = current.can_enter ? currentSpaces : []
    if (selectedSpace.value && !currentSpaces.some(space => space.space_id === selectedSpace.value)) selectedSpace.value = ''
    if (!current.ask_enabled && mode.value === 'ask') {
      if (route.query.q && !modeDrafts.search) modeDrafts.search = query.value
      setMode('search')
    }
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
  // Wait for the session, then load whatever this route actually shows. The
  // catalogue route used to render its caption with no rows until a filter
  // changed, because only refreshStatus() ran here.
  await refreshStatus()
  await applyReturnedScroll()
  if (view.value === 'catalog' && restoredCatalogFocus) {
    const target = document.getElementById('catalog-document-' + restoredCatalogFocus) ?? document.getElementById('catalog-query')
    target?.focus({ preventScroll: true })
    restoredCatalogFocus = ''
  }
  saveWorkspaceNow(workspaceState())
})
</script>

<style scoped>
.kb-release-note{opacity:.55;font-size:11px}
.kb-answer-settings { display:flex; align-items:center; flex-wrap:wrap; gap:12px; margin:16px 0 24px; color:var(--hbos-text-muted); font-size:14px; }
.kb-catalog-categories, .kb-catalog-filters { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin-top:12px; }
.kb-catalog-categories button { min-height:40px; padding:6px 14px; background:transparent; border:1px solid var(--hbos-border,#dbe5e9); border-radius:8px; color:inherit; cursor:pointer; }
.kb-catalog-categories button[aria-pressed="true"] { background:#e9f7f4; border-color:#94c9be; color:#076c60; font-weight:600; }
.kb-catalog-filter-field { display: flex; align-items: center; gap: 8px; min-width: 0; }
.kb-catalog-filter-field label { white-space: nowrap; }
.kb-catalog-subcategory :deep(.v10-choice) { width: min(225px, 100%); }
.kb-catalog-result { display:flex; flex-wrap:wrap; justify-content:space-between; gap:6px 16px; min-height:24px; margin-top:16px; color:var(--hbos-text-muted); }
.kb-catalog-result span:last-child { margin-left:auto; }
.kb-catalog-refresh-icon { display: none; }
.kb-favorites-page-action { gap: 8px; }
.catalog-row.kb-doc-row { padding-block:12px; }
.catalog-row .kb-doc-main { min-height:44px; }
.catalog-row .kb-doc-main strong { overflow-wrap:anywhere; }
.kb-catalog-panel .catalog-filter :deep(.ant-input-search) { width: 100%; max-width: none; }
.catalog-row .kb-doc-main small { display:block; overflow-wrap:anywhere; }
.kb-catalog-categories button:focus-visible, .catalog-row .kb-doc-main:focus-visible { outline:2px solid #087c6e; outline-offset:2px; }
@media (max-width:480px) {
  .kb-catalog-categories button { min-height:36px; }
  .kb-catalog-filter-field { flex: 1 0 auto; }
  .kb-catalog-filter-field :deep(.v10-choice) { flex: 1; }
  .kb-catalog-subcategory { flex-basis: 100%; }
  .kb-catalog-filters :deep(.v10-choice-trigger) { padding-inline: 8px 32px; }
  .kb-catalog-filters :deep(.v10-choice-cue) { right: 8px; }
  .kb-connect-page-action { min-width: 44px; height: 44px; }
  .kb-connect-page-action > span:not(.anticon) { display: none; }
  .kb-favorites-page-action { width: 44px; flex: none; }
  .kb-favorites-page-action > span:not(.anticon) { display: none; }
  .catalog-row .kb-doc-actions :deep(.ant-btn) { min-width:44px; min-height:44px; }
}
@media (max-width: 360px) {
  .kb-catalog-refresh-label { display: none; }
  .kb-catalog-refresh-icon { display: inline; }
}
</style>
