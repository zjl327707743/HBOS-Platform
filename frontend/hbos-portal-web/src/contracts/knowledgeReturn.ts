import type {
  KnowledgeAnswer,
  KnowledgeEvidence,
  KnowledgeLawCategory,
  KnowledgeOperationState,
  KnowledgeSearchContext,
} from '@/contracts/p1'

/**
 * In-memory snapshot used when the reader route temporarily replaces the
 * knowledge workspace. Nothing here is persisted outside the running tab: the
 * snapshot disappears on reload, logout or a different signed-in identity.
 */
export interface KnowledgeToolsReturnState {
  question: string
  conversation: string
  turns: (KnowledgeAnswer & { question: string })[]
  queryState: KnowledgeOperationState
}

export interface KnowledgeReturnSnapshot {
  view: 'query' | 'catalog' | 'favorites' | 'history' | 'feedback'
  query: string
  mode: 'ask' | 'search'
  selectedSpace: string
  searchMode: 'STANDARD' | 'PRECISE'
  searchContext: KnowledgeSearchContext | null
  results: KnowledgeEvidence[]
  hasSearched: boolean
  searchState: KnowledgeOperationState
  tools: KnowledgeToolsReturnState | null
  catalog: {
    query: string
    page: number
    lawCategory: KnowledgeLawCategory | ''
    sourceFolder: string
  }
  scrollTop: number
}

export interface ReaderPosition {
  page: number
  /** 0 means "fit the column"; the reader's own scale otherwise. */
  zoom: number
  searchQuery: string
  updatedAt: number
}
