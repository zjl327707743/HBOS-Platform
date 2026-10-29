/**
 * RC13 controlled document reader contract (RC13_WORKING_CONTRACTS.md §4).
 *
 * The browser only ever receives logical document/version identities and
 * sanitized derived text. It never receives RAGFlow dataset/document ids,
 * storage paths, original-file URLs or any download channel, so this projection
 * deliberately does not describe those fields at all.
 */

export type ReaderSource = 'ask' | 'search' | 'catalog'

export type ReaderReferenceState = 'CURRENT' | 'SUPERSEDED' | 'WITHDRAWN' | string
export type ReaderAuthorization = 'AUTHORIZED' | 'READ_ONLY' | string
export type ReaderPageNumbering = 'UNAVAILABLE' | 'AVAILABLE' | string

export interface ReaderDocument {
  document_id: string
  version_id: string
  title: string
  document_number: string | null
  space_id: string
  space_title: string | null
  business_version: string | null
  status_note: string | null
  reference_state: ReaderReferenceState
  authorization: ReaderAuthorization
  source_type: string
}

export interface ReaderBlock {
  block_id: string
  ordinal: number
  page_number: number | null
  section: string | null
  text: string
}

export interface ReaderBody {
  origin: string
  page_numbering: ReaderPageNumbering
  derived: boolean
  page: number
  /** null means the server could not verify a page count; never invented here. */
  page_count: number | null
  block_total: number
  blocks: ReaderBlock[]
}

export interface ReaderTocEntry {
  title: string
  ordinal: number
  page_number: number | null
}

export interface ReaderNavigation {
  toc: ReaderTocEntry[]
  toc_source: string | null
  toc_truncated: boolean
}

export interface ReaderOpenDocument {
  document: ReaderDocument
  body: ReaderBody
  navigation: ReaderNavigation
  disclosure: string
}

export interface ReaderSearchMatch {
  ordinal: number
  /** null when the server cannot verify a page; the UI must not invent one. */
  page: number | null
  block_id: string
  snippet: string
}

export interface ReaderSearchResult {
  matches: ReaderSearchMatch[]
  searched_blocks: number
  capped: boolean
}

export type ReaderFailureKind = 'unavailable' | 'upstream' | 'invalid' | 'page-range' | 'error'

export interface ReaderFailure {
  kind: ReaderFailureKind
  code: string
  message: string
  retryable: boolean
  /** Optional server-side stage hint (WITHDRAWN / VERSION_STALE / NOT_AUTHORIZED / NOT_PUBLISHED). */
  state?: string | null
}
