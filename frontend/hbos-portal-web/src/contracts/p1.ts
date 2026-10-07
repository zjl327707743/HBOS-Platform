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

export interface KnowledgeStatus {
  can_enter: boolean
  can_search: boolean
  policy_revision?: string | null
  gateway_configured: boolean
  ask_enabled: boolean
  mode: 'retrieval'
}

export interface KnowledgeEvidence {
  document_id: string
  title?: string | null
  version?: string | null
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
  context?: KnowledgeSearchContext
  results: KnowledgeEvidence[]
}

export interface KnowledgeSearchContext {
  equipment_id?: string
  asset_id?: string
  component_id?: string
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
