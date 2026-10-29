<template>
  <div class="knowledge-document-page">
    <DocumentReader
      :from="from"
      :document="document"
      :body="body"
      :page="page"
      :page-count="pageCount"
      :loading="loading"
      :page-loading="pageLoading"
      :failure="failure"
      :page-failure="pageFailure"
      v-model:search-query="searchQuery"
      :searching="searching"
      :search-ran="searchRan"
      :search-message="searchMessage"
      :matches="matches"
      :highlight-block-id="highlightBlockId"
      :highlight-query="highlightQuery"
      :preview-url="delivery.previewUrl"
      :preview-kind="delivery.previewKind"
      :preview-filename="delivery.previewFilename"
      :preview-unavailable="delivery.previewUnavailable"
      :preparing="delivery.preparing"
      :preparing-message="delivery.preparingMessage"
      :can-download="delivery.canDownload"
      :download-busy="delivery.downloadBusy"
      :download-reason="delivery.downloadReason"
      :notice="delivery.notice"
      :position="position"
      :renew-preview="renewPreview"
      @back="goBack"
      @retry="retry"
      @retry-page="retryPage"
      @prev="prev"
      @next="next"
      @go-page="goToPage"
      @search="runSearch"
      @clear-search="clearSearch"
      @jump-match="jumpToMatch"
      @download="downloadOriginal"
      @access-lost="accessLost"
      @page-change="rememberPage"
      @zoom-change="rememberZoom"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { ReaderSource } from '@/contracts/documentReader'
import { useDocumentReader } from '@/composables/useDocumentReader'
import { useKnowledgeReturnStore } from '@/stores/knowledgeReturn'
import { usePortalStore } from '@/stores/portal'
import DocumentReader from '@/components/knowledge/DocumentReader.vue'
import {
  createDocumentDelivery,
  deliveryFailureMessage,
  fetchDocumentCapabilities,
  isRetryableDelivery,
} from '@/services/knowledgeDelivery'
import type { DocumentCapabilities } from '@/services/knowledgeDelivery'
import { DomainApiError } from '@/services/p1Api'

/**
 * One file, opened like a file.
 *
 * The page asks for a preview the moment it opens - there is no separate
 * "prepare" step - and silently renews the short-lived ticket when a fetch is
 * refused. Reading position (file page + zoom) is remembered per document and
 * version, so coming back to the tab or returning from another page resumes
 * where the reader was.
 */
const route = useRoute()
const router = useRouter()
const portal = usePortalStore()
const returnStore = useKnowledgeReturnStore()

const subjectKey = computed(() => portal.user?.id || null)
const documentId = computed(() => String(route.params.documentId || ''))
const versionId = computed(() => {
  const value = route.query.version_id
  return typeof value === 'string' && value.trim() ? value.trim() : null
})
const from = computed<ReaderSource>(() => {
  const value = String(route.query.from || '')
  return value === 'ask' || value === 'search' || value === 'catalog' ? value : 'search'
})

const reader = useDocumentReader(() => subjectKey.value)
const {
  document, body, loading, pageLoading, page, pageCount,
  failure, pageFailure, searchQuery, searching, searchRan, searchFailure, matches,
  searchedBlocks, searchCapped, highlightBlockId, highlightQuery,
  open, goToPage, runSearch, clearSearch, jumpToMatch,
} = reader

const searchMessage = computed(() => {
  if (searching.value) return '正在查找…'
  if (searchFailure.value) return searchFailure.value.message
  if (!searchRan.value) return ''
  const term = searchQuery.value.trim()
  if (!matches.value.length) return `未在检索文本中找到“${term}”。`
  return `找到 ${matches.value.length} 处 · 已检索 ${searchedBlocks.value} 段${searchCapped.value ? '（仅检索部分）' : ''}`
})

// ---- file view state --------------------------------------------------------
interface DeliveryState {
  capabilities: DocumentCapabilities | null
  loadingCapabilities: boolean
  preparing: boolean
  preparingMessage: string
  previewUrl: string | null
  previewKind: 'ORIGINAL_PDF' | 'DERIVED_PDF' | null
  previewFilename: string
  previewUnavailable: string
  downloadBusy: boolean
  canDownload: boolean
  downloadReason: string
  notice: string
}
const delivery = reactive<DeliveryState>({
  capabilities: null,
  loadingCapabilities: false,
  preparing: false,
  preparingMessage: '',
  previewUrl: null,
  previewKind: null,
  previewFilename: '',
  previewUnavailable: '',
  downloadBusy: false,
  canDownload: false,
  downloadReason: '',
  notice: '',
})
let deliveryGeneration = 0
let previewRequest: Promise<string | null> | null = null
let lastPreviewKind: 'preview' | 'download' | null = null

function resetDelivery() {
  deliveryGeneration++
  previewRequest = null
  lastPreviewKind = null
  Object.assign(delivery, {
    capabilities: null, loadingCapabilities: false, preparing: false, preparingMessage: '',
    previewUrl: null, previewKind: null, previewFilename: '', previewUnavailable: '',
    downloadBusy: false, canDownload: false, downloadReason: '', notice: '',
  })
}

function currentVersion(): string | null {
  return document.value?.version_id || versionId.value || null
}

function humanReason(reason: string | null | undefined): string {
  if (!reason) return ''
  if (reason === 'ASSET_TOO_LARGE') return '原文件较大，当前不能在线提供。'
  if (reason === 'ASSET_UNAVAILABLE') return '原文件暂不可用，可能未完成归档。'
  if (reason === 'PREVIEW_UNAVAILABLE') return '这份资料还没有可用的原版式预览。'
  if (reason === 'ASSET_HASH_MISMATCH') return '文件校验不一致，系统已停止提供，请联系维护人复核。'
  if (reason === 'ORIGINAL_WITHHELD') return '这份原件按资料管理规定不开放下载。'
  if (reason === 'DOWNLOAD_NOT_AUTHORIZED') return '当前账号不能下载这份原件。'
  return ''
}

async function loadCapabilities() {
  if (!documentId.value || !document.value) return
  const generation = deliveryGeneration, subject = subjectKey.value
  delivery.loadingCapabilities = true
  try {
    const capabilities = await fetchDocumentCapabilities(documentId.value, currentVersion())
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return
    delivery.capabilities = capabilities
    delivery.canDownload = capabilities.can_download
    delivery.downloadReason = humanReason(capabilities.download_reason)
    if (!capabilities.can_preview) {
      delivery.previewUnavailable = humanReason(capabilities.preview_reason) || '这份资料暂不支持原版式预览，可下载原文件查看。'
    }
  } catch {
    if (generation === deliveryGeneration && subject === subjectKey.value) delivery.capabilities = null
  } finally {
    if (generation === deliveryGeneration && subject === subjectKey.value) delivery.loadingCapabilities = false
  }
}

/** Ask for a fresh ticket; never shown to the reader as a ticket. */
async function requestPreview(): Promise<string | null> {
  if (!documentId.value || !document.value) return null
  const generation = deliveryGeneration, subject = subjectKey.value
  delivery.preparing = true
  delivery.preparingMessage = '正在准备原版式…'
  delivery.previewUnavailable = ''
  try {
    const value = await createDocumentDelivery(documentId.value, currentVersion(), 'preview')
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return null
    delivery.previewUrl = value.content_url
    delivery.previewKind = value.kind === 'DERIVED_PDF' ? 'DERIVED_PDF' : 'ORIGINAL_PDF'
    delivery.previewFilename = value.filename
    delivery.preparing = false
    delivery.preparingMessage = ''
    return value.content_url
  } catch (error) {
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return null
    delivery.preparing = false
    delivery.preparingMessage = ''
    if (error instanceof DomainApiError && ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE'].includes(error.code)) {
      accessLost()
      return null
    }
    const reason = error instanceof DomainApiError ? error.code : ''
    delivery.previewUnavailable = humanReason(reason) || deliveryFailureMessage(error)
    return null
  }
}

function ensurePreview() {
  if (delivery.previewUrl || delivery.preparing) return
  previewRequest = requestPreview()
  void previewRequest
}

/** Called by the file view when its short-lived ticket lapses mid-read. */
async function renewPreview(): Promise<string | null> {
  if (delivery.preparing) return previewRequest
  return requestPreview()
}

async function downloadOriginal() {
  if (!documentId.value || !document.value || delivery.downloadBusy) return
  const generation = deliveryGeneration, subject = subjectKey.value
  delivery.downloadBusy = true
  delivery.notice = ''
  lastPreviewKind = 'download'
  try {
    const value = await createDocumentDelivery(documentId.value, currentVersion(), 'download')
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return
    const link = window.document.createElement('a')
    link.href = value.content_url
    link.download = value.filename
    link.rel = 'noopener'
    window.document.body.appendChild(link)
    link.click()
    setTimeout(() => link.remove(), 0)
    delivery.notice = value.kind === 'ORIGINAL_FILE'
      ? '已开始下载原文件，文件由服务端核验当前身份与版本后提供。'
      : '已开始下载。'
  } catch (error) {
    if (generation !== deliveryGeneration || subject !== subjectKey.value) return
    if (error instanceof DomainApiError && ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE'].includes(error.code)) {
      accessLost(); return
    }
    delivery.notice = '下载未完成：' + (humanReason(error instanceof DomainApiError ? error.code : '') || deliveryFailureMessage(error))
    if (isRetryableDelivery(error)) delivery.notice += ' 可以再点一次下载。'
  } finally {
    if (generation === deliveryGeneration && subject === subjectKey.value) delivery.downloadBusy = false
  }
}

function accessLost() {
  deliveryGeneration++
  reader.reset()
  resetDelivery()
  failure.value = { kind: 'unavailable', code: 'SCOPE_REJECTED', message: '当前账号不能继续阅读这份资料，请重新登录或从资料目录重新打开。', retryable: false }
}

// ---- position ---------------------------------------------------------------
const position = ref({ page: 1, zoom: 0 })
let saveTimer: ReturnType<typeof setTimeout> | null = null

function storedPosition() {
  const subject = subjectKey.value
  return returnStore.positionFor(subject, documentId.value, versionId.value)
    || returnStore.positionFor(subject, documentId.value, null)
}

function rememberPage(value: number) {
  position.value.page = Math.max(1, Math.round(value || 1))
  scheduleRemember()
}

function rememberZoom(value: number) {
  position.value.zoom = value > 0 ? value : 0
  scheduleRemember()
}

function scheduleRemember() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(rememberPosition, 250)
}

function rememberPosition() {
  if (!documentId.value || !document.value) return
  const value = { page: position.value.page, zoom: position.value.zoom, searchQuery: searchQuery.value.trim() }
  const resolved = document.value?.version_id || versionId.value || null
  returnStore.rememberPosition(subjectKey.value, documentId.value, resolved, value)
  if (resolved && resolved !== versionId.value) returnStore.rememberPosition(subjectKey.value, documentId.value, null, value)
}

function openCurrent() {
  const saved = storedPosition()
  position.value = { page: saved && saved.page >= 1 ? saved.page : 1, zoom: saved?.zoom || 0 }
  void open({ documentId: documentId.value, versionId: versionId.value, page: position.value.page })
}

function goBack() {
  rememberPosition()
  const fallback = from.value === 'catalog' ? '/hbos/knowledge/catalog' : '/hbos/knowledge'
  const historyState = window.history.state as { back?: unknown } | null
  const back = historyState && typeof historyState.back === 'string' ? historyState.back : ''
  if (back.startsWith('/hbos/knowledge')) router.back()
  else void router.push(fallback)
}

function retry() { void reader.retry() }
function retryPage() { void reader.retry() }
function prev() { void goToPage(page.value - 1) }
function next() { void goToPage(page.value + 1) }

watch([documentId, versionId], () => { resetDelivery(); openCurrent() }, { immediate: true })
watch(() => [document.value?.document_id, document.value?.version_id, loading.value], () => {
  if (loading.value || !document.value) return
  void loadCapabilities().then(ensurePreview)
  if (delivery.capabilities && !delivery.capabilities.can_preview && !delivery.previewUrl) ensurePreview()
})
// The ticket lapses silently while the tab is open; coming back just renews it.
function onVisible() { if (window.document.visibilityState === 'visible' && !delivery.previewUrl) ensurePreview() }
onMounted(() => window.document.addEventListener('visibilitychange', onVisible))
onBeforeUnmount(() => {
  window.document.removeEventListener('visibilitychange', onVisible)
  if (saveTimer) clearTimeout(saveTimer)
  rememberPosition()
})
</script>

<style scoped>
.knowledge-document-page { min-width: 0; }
</style>
