export interface DomainErrorPayload {
  code: string
  message: string
  retryable: boolean
  request_id?: string
}

export interface DomainEnvelope<T> {
  ok: boolean
  data?: T
  error?: DomainErrorPayload
}

export type KnowledgeOperationState = 'idle' | 'loading' | 'retrieved' | 'answering' | 'success' | 'no_evidence' | 'error' | 'cancelled'

export interface KnowledgeStatus {
  model_catalog?: KnowledgeModels
  can_enter: boolean
  can_search: boolean
  can_maintain?: boolean
  policy_revision?: string | null
  gateway_configured: boolean
  answer_availability?: { configured: boolean; available: boolean; budget_status?: string }
  ask_enabled: boolean
  mode: 'retrieval'
  search_mode?: 'STANDARD' | 'PRECISE'
  environment?: 'synthetic' | 'production'
  retrieval_availability?: {
    configured: boolean
    status: 'AVAILABLE' | 'OBSERVED_ERROR' | 'UNKNOWN' | 'NOT_CONFIGURED'
    last_success_at: string | null
    observed_at: string | null
    observed_error: 'UPSTREAM_UNAVAILABLE' | null
    blocked: boolean
    expires_at: string | null
    manual_recheck_required: boolean
    budget_status?: 'UNKNOWN' | 'READY' | 'ACCOUNTING_PENDING' | 'EXPIRED' | 'EXHAUSTED' | 'UNAVAILABLE'
  }
}

export interface KnowledgeEvidence {
  document_id: string
  title?: string | null
  version?: string | null
  document_number?: string | null
  status_note?: string | null
  section?: string | null
  page_number?: number | null
  excerpt: string
  evidence_id: string
  space_id?: string
  source_type?: 'COMPANY_CONTROLLED' | 'EXTERNAL_REFERENCE' | 'ORDINARY_INTERNAL_KNOWLEDGE' | 'SYNTHETIC_TEST'
}

export interface KnowledgeSearchResult {
  request_id: string
  mode: 'retrieval'
  search_mode?: 'STANDARD' | 'PRECISE'
  context?: KnowledgeSearchContext
  results: KnowledgeEvidence[]
}

export interface KnowledgeSearchContext {
  equipment_id?: string
  asset_id?: string
  component_id?: string
}

export interface KnowledgeRestored { mode: 'search' | 'ask'; search_mode: 'STANDARD' | 'PRECISE'; results: KnowledgeEvidence[]; turns: (KnowledgeAnswer & {question:string})[] }

export interface KnowledgeSavedQuery {
  document?: KnowledgeDocument
  bookmark_type?: 'Document'
  restored?: KnowledgeRestored
  query: string
  space_ids: string[]
  context?: KnowledgeSearchContext
}

export interface TwinStatus {
  can_enter: boolean
  equipment_ids: string[]
  policy_revision?: string | null
  asset_root_configured: boolean
}

export interface TwinManifest {
  equipment_id: string
  label: string
  site_identity: string
  model_sha256: string
  model_size_bytes: number
  model_revision: string
  viewer_revision: string
  mapping_revision: string
  fit_disclaimer: string
  connection_state: 'not_connected' | string
  model_url: string
}

export interface TwinComponentMapping {
  equipment_id: string
  asset_id: string
  mapping_revision: string
  status: 'verified' | 'unverified' | string
  display_name: string
  component_id?: string | null
  process_step_id?: string | null
  knowledge_link_available: boolean
}

export interface FeishuLoginStatus {
  configured: boolean
  provider: 'feishu'
  pkce_enabled: boolean
  audience?: 'enterprise_internal_members'
  auto_provision_internal?: boolean
  missing: string[]
}
export interface KnowledgeSpace {
  space_id: string
  title: string
  document_count: number
}

export const knowledgeLawCategories = ['国家法律法规', 'GMP与药品监管', '药典与技术标准', '地方政策', '安全环保', '待分类'] as const
export type KnowledgeLawCategory = typeof knowledgeLawCategories[number]
export interface KnowledgeLegalMetadata {
  category: KnowledgeLawCategory
  level: string | null
  issuer: string | null
  published_date: string | null
  region: string | null
  applicability: string | null
  effective_status: '待核' | '现行有效' | '已废止'
}

export interface KnowledgeDocument {
  document_id: string
  title: string | null
  space_id: string
  department: string
  document_number: string | null
  version: string | null
  status_note: string
  version_id?: string
  legal_metadata?: KnowledgeLegalMetadata
  download_state?: 'permission_required'
  download_note?: string
}

export interface KnowledgeDocumentPage {
  documents: KnowledgeDocument[]
  total: number
  page: number
  page_size: number
}

export interface KnowledgeFeedback {
  id: string
  category: string
  note: string
  status: 'Pending' | 'In Review' | 'Resolved'
  reply?: string
  created_at: string
  updated_at: string
}

export interface KnowledgeActivity {
  answer_origin?: 'KNOWLEDGE' | 'GENERAL' | null
  model_alias?: KnowledgeModelAlias | null
  id: string
  query: string
  created_at: string
  available: boolean
  titles: (string | null)[]
  document_ids?: string[]
  version_ids?: string[]
  bookmark_type?: 'Document' | 'Evidence'
}
export interface KnowledgeAnswer {
  answer_origin?: 'KNOWLEDGE' | 'GENERAL'
  model_alias?: KnowledgeModelAlias | null
  request_id: string
  turn_id: string
  conversation_id?: string
  mode: 'internal_reference_generation' | 'authorized_generation' | 'general_generation'
  answer_status: 'REFERENCE_ANSWERED' | 'INSUFFICIENT_EVIDENCE' | 'GENERAL_ANSWERED'
  answerable: boolean
  answer: string
  citations: (KnowledgeEvidence & { citation_label: string })[]
}

export type KnowledgeModelAlias = 'gpt-6-luna' | 'deepseek-flash' | 'gemini-3.8-flash' | 'kimi-k3'
export interface KnowledgeModels { default: 'gpt-6-luna'; selected_alias: KnowledgeModelAlias; models: {alias:KnowledgeModelAlias;available:boolean;reason:null|'CONFIGURATION_NOT_VERIFIED'}[] }
