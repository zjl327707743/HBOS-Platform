import type {
  DomainEnvelope,
  FeishuLoginStatus,
  KnowledgeEvidence,
  KnowledgeSearchContext,
  KnowledgeSearchResult,
  KnowledgeStatus,
  TwinComponentMapping,
  TwinManifest,
  TwinStatus,
} from '@/contracts/p1'
import { callFrappeMethod, callFrappePostMethod } from '@/services/frappeClient'

export class DomainApiError extends Error {
  code: string
  retryable: boolean

  constructor(code: string, message: string, retryable = false) {
    super(message)
    this.name = 'DomainApiError'
    this.code = code
    this.retryable = retryable
  }
}

function unwrap<T>(envelope: DomainEnvelope<T>): T {
  if (!envelope.ok || envelope.data === undefined) {
    throw new DomainApiError(
      envelope.error?.code || 'SERVICE_ERROR',
      envelope.error?.message || '服务返回了无效响应。',
      Boolean(envelope.error?.retryable),
    )
  }
  return envelope.data
}

export async function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  return unwrap(await callFrappeMethod<DomainEnvelope<KnowledgeStatus>>(
    'hb_knowledge_app.hb_knowledge.api.get_status',
  ))
}

export async function searchKnowledge(
  query: string,
  context: KnowledgeSearchContext = {},
): Promise<KnowledgeSearchResult> {
  return unwrap(await callFrappePostMethod<DomainEnvelope<KnowledgeSearchResult>>(
    'hb_knowledge_app.hb_knowledge.api.search',
    { query, limit: 5, ...context },
  ))
}

export async function resolveKnowledgeEvidence(evidenceId: string): Promise<KnowledgeEvidence> {
  return unwrap(await callFrappePostMethod<DomainEnvelope<KnowledgeEvidence>>(
    'hb_knowledge_app.hb_knowledge.api.resolve_evidence',
    { evidence_id: evidenceId },
  ))
}

export async function getTwinStatus(): Promise<TwinStatus> {
  return unwrap(await callFrappeMethod<DomainEnvelope<TwinStatus>>(
    'hb_twin_app.hb_twin.api.get_status',
  ))
}

export async function getTwinManifest(equipmentId = 'M607B'): Promise<TwinManifest> {
  return unwrap(await callFrappeMethod<DomainEnvelope<TwinManifest>>(
    'hb_twin_app.hb_twin.api.get_manifest',
    { equipment_id: equipmentId },
  ))
}

export async function getTwinComponentMapping(
  equipmentId: string,
  assetId: string,
): Promise<TwinComponentMapping> {
  return unwrap(await callFrappeMethod<DomainEnvelope<TwinComponentMapping>>(
    'hb_twin_app.hb_twin.api.get_component_mapping',
    { equipment_id: equipmentId, asset_id: assetId },
  ))
}

export async function getFeishuLoginStatus(): Promise<FeishuLoginStatus> {
  return callFrappeMethod<FeishuLoginStatus>('hbos_portal.auth.feishu.get_status')
}
