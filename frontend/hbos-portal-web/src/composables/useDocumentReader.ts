import { computed, onScopeDispose, ref, watch } from 'vue'
import type {
  ReaderBody,
  ReaderDocument,
  ReaderFailure,
  ReaderNavigation,
  ReaderSearchMatch,
} from '@/contracts/documentReader'
import {
  classifyReaderFailure,
  openKnowledgeDocument,
  readKnowledgeDocumentPage,
  searchKnowledgeDocument,
} from '@/services/documentReaderApi'

export interface DocumentReaderTarget {
  documentId: string
  versionId?: string | null
  page?: number
  search?: string
}

function isAbort(error: unknown) {
  return Boolean(error && typeof error === 'object' && (error as { name?: unknown }).name === 'AbortError')
}

function normalizePage(value: unknown): number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 1 && value <= 100000 ? value : 1
}

/**
 * Reader state machine for one authorized document.
 *
 * Every request is generation-guarded so a late answer from a previous
 * document/page/identity can never overwrite the view. An unreadable response
 * clears the body; an upstream failure keeps the last successfully read page
 * and offers a retry, never a fabricated empty document.
 */
export function useDocumentReader(subjectKey: () => string | null) {
  const document = ref<ReaderDocument | null>(null)
  const body = ref<ReaderBody | null>(null)
  const navigation = ref<ReaderNavigation | null>(null)
  const disclosure = ref('')
  const loading = ref(false)
  const pageLoading = ref(false)
  const page = ref(1)
  const failure = ref<ReaderFailure | null>(null)
  const pageFailure = ref<ReaderFailure | null>(null)

  const searchQuery = ref('')
  const searching = ref(false)
  const searchRan = ref(false)
  const searchFailure = ref<ReaderFailure | null>(null)
  const matches = ref<ReaderSearchMatch[]>([])
  const searchedBlocks = ref(0)
  const searchCapped = ref(false)
  const highlightBlockId = ref<string | null>(null)
  const highlightQuery = ref('')

  const pageCount = computed(() => body.value?.page_count ?? null)
  const blockTotal = computed(() => body.value?.block_total ?? 0)
  const hasBody = computed(() => Boolean(body.value && body.value.blocks.length > 0))
  const emptyBody = computed(() => Boolean(document.value && body.value && body.value.blocks.length === 0))
  const canPrev = computed(() => body.value !== null && page.value > 1 && !pageLoading.value)
  const canNext = computed(() => body.value !== null && pageCount.value !== null && page.value < pageCount.value && !pageLoading.value)

  let generation = 0
  let searchGeneration = 0
  let controller: AbortController | null = null
  let target: DocumentReaderTarget | null = null
  let resolvedVersionId: string | null = null

  function abortPending() {
    controller?.abort()
    controller = null
  }

  function reset() {
    generation++
    searchGeneration++
    abortPending()
    document.value = null
    body.value = null
    navigation.value = null
    disclosure.value = ''
    loading.value = false
    pageLoading.value = false
    page.value = 1
    failure.value = null
    pageFailure.value = null
    searchQuery.value = ''
    searching.value = false
    searchRan.value = false
    searchFailure.value = null
    matches.value = []
    searchedBlocks.value = 0
    searchCapped.value = false
    highlightBlockId.value = null
    highlightQuery.value = ''
    target = null
    resolvedVersionId = null
  }

  function adopt(result: Awaited<ReturnType<typeof openKnowledgeDocument>>) {
    document.value = result.document
    resolvedVersionId = result.document.version_id
    body.value = result.body
    navigation.value = result.navigation
    disclosure.value = result.disclosure
    page.value = result.body.page
    failure.value = null
    pageFailure.value = null
  }

  function clearForUnavailable(next: ReaderFailure) {
    // An unreadable document must not keep stale body text on screen.
    body.value = null
    navigation.value = null
    failure.value = next
    pageFailure.value = null
    page.value = 1
    matches.value = []
    searchRan.value = false
    highlightBlockId.value = null
    highlightQuery.value = ''
  }

  function currentTarget(): DocumentReaderTarget | null {
    if (!target) return null
    return { ...target, versionId: resolvedVersionId }
  }

  async function fetchPage(pageNumber: number): Promise<void> {
    const requestTarget = currentTarget()
    if (!requestTarget) return
    const subject = subjectKey()
    abortPending()
    controller = new AbortController()
    const current = ++generation
    pageLoading.value = true
    pageFailure.value = null
    try {
      const result = await readKnowledgeDocumentPage(requestTarget, pageNumber, controller.signal)
      if (current !== generation || subject !== subjectKey()) return
      adopt(result)
    } catch (error) {
      if (current !== generation || subject !== subjectKey()) return
      if (isAbort(error)) return
      const classified = classifyReaderFailure(error)
      if (classified.kind === 'page-range' && pageNumber !== 1) {
        pageFailure.value = { ...classified, message: '页码超出可读范围，已返回第 1 页。' }
        await fetchPage(1)
        return
      }
      if (classified.kind === 'unavailable' || classified.kind === 'invalid') {
        clearForUnavailable(classified)
        return
      }
      // Upstream outage: keep the last successfully read page and offer retry.
      pageFailure.value = classified
    } finally {
      if (current === generation) pageLoading.value = false
    }
  }

  async function open(nextTarget: DocumentReaderTarget): Promise<void> {
    reset()
    // Keep only the identities: page/search are one-shot navigation inputs and
    // must not leak into the page/search request bodies.
    target = { documentId: nextTarget.documentId, versionId: nextTarget.versionId ?? null }
    const subject = subjectKey()
    if (!subject) {
      failure.value = { kind: 'unavailable', code: 'AUTHENTICATION_REQUIRED', message: '登录状态已失效，请重新登录。', retryable: false }
      return
    }
    abortPending()
    controller = new AbortController()
    const current = ++generation
    loading.value = true
    try {
      const result = await openKnowledgeDocument(
        { documentId: nextTarget.documentId, versionId: nextTarget.versionId ?? null },
        controller.signal,
      )
      if (current !== generation || subject !== subjectKey()) return
      adopt(result)
      const wanted = normalizePage(nextTarget.page)
      if (wanted > 1) {
        // Read the requested deep-linked page after the first authorized open.
        loading.value = false
        await fetchPage(wanted)
      }
      if (nextTarget.search) {
        searchQuery.value = nextTarget.search
        void runSearch(nextTarget.search)
      }
    } catch (error) {
      if (current !== generation || subject !== subjectKey()) return
      if (isAbort(error)) return
      const classified = classifyReaderFailure(error)
      if (classified.kind === 'unavailable' || classified.kind === 'invalid') clearForUnavailable(classified)
      else failure.value = classified
    } finally {
      if (current === generation) loading.value = false
    }
  }

  async function goToPage(pageNumber: number): Promise<void> {
    if (!body.value && !failure.value) return
    const count = pageCount.value
    let next = Number.isFinite(pageNumber) ? Math.trunc(pageNumber) : 1
    if (next < 1) next = 1
    if (count !== null && count > 0) next = Math.min(next, count)
    if (next === page.value && body.value) return
    await fetchPage(next)
  }

  async function retry(): Promise<void> {
    if (!target) return
    if (!body.value) {
      await open(target)
      return
    }
    await fetchPage(page.value)
  }

  async function retrySearch(): Promise<void> {
    await runSearch(searchQuery.value)
  }

  async function runSearch(term?: string): Promise<void> {
    const query = (term ?? searchQuery.value).trim()
    searchQuery.value = query
    const length = [...query].length
    if (!length) {
      searchFailure.value = { kind: 'invalid', code: 'INVALID_REQUEST', message: '请输入要查找的内容。', retryable: false }
      searchRan.value = false
      matches.value = []
      return
    }
    if (length > 120) {
      searchFailure.value = { kind: 'invalid', code: 'INVALID_REQUEST', message: '查找内容请控制在 120 字以内。', retryable: false }
      return
    }
    const requestTarget = currentTarget()
    if (!requestTarget) return
    const subject = subjectKey()
    const current = ++searchGeneration
    searching.value = true
    searchFailure.value = null
    searchRan.value = false
    matches.value = []
    searchedBlocks.value = 0
    searchCapped.value = false
    try {
      const result = await searchKnowledgeDocument(requestTarget, query, 20)
      if (current !== searchGeneration || subject !== subjectKey()) return
      matches.value = result.matches
      searchedBlocks.value = result.searched_blocks
      searchCapped.value = result.capped
      searchRan.value = true
    } catch (error) {
      if (current !== searchGeneration || subject !== subjectKey()) return
      if (isAbort(error)) return
      const classified = classifyReaderFailure(error)
      searchFailure.value = classified.kind === 'invalid'
        ? { ...classified, message: '查找内容无法检索，请换一个不含链接或标记的关键词。' }
        : classified
    } finally {
      if (current === searchGeneration) searching.value = false
    }
  }

  function clearSearch() {
    searchGeneration++
    searchQuery.value = ''
    searchRan.value = false
    searchFailure.value = null
    matches.value = []
    searchedBlocks.value = 0
    searchCapped.value = false
    highlightBlockId.value = null
    highlightQuery.value = ''
  }

  async function jumpToMatch(match: ReaderSearchMatch): Promise<void> {
    highlightBlockId.value = match.block_id
    highlightQuery.value = searchQuery.value.trim()
    if (match.page === null || match.page === undefined) {
      searchFailure.value = {
        kind: 'invalid', code: 'INVALID_REQUEST',
        message: '该匹配暂无法核验页码，请使用上一页/下一页查找该段正文。', retryable: false,
      }
      return
    }
    if (match.page !== page.value) await goToPage(match.page)
  }

  function clearHighlight() {
    highlightBlockId.value = null
    highlightQuery.value = ''
  }

  watch(subjectKey, () => reset(), { flush: 'sync' })
  onScopeDispose(() => {
    generation++
    searchGeneration++
    abortPending()
  })

  return {
    document,
    body,
    navigation,
    disclosure,
    loading,
    pageLoading,
    page,
    pageCount,
    blockTotal,
    hasBody,
    emptyBody,
    canPrev,
    canNext,
    failure,
    pageFailure,
    searchQuery,
    searching,
    searchRan,
    searchFailure,
    matches,
    searchedBlocks,
    searchCapped,
    highlightBlockId,
    highlightQuery,
    open,
    goToPage,
    retry,
    retrySearch,
    runSearch,
    clearSearch,
    jumpToMatch,
    clearHighlight,
    reset,
  }
}
