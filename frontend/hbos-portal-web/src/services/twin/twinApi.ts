import { callFrappeMethod, FrappeRequestError } from '@/services/frappeClient'
import type { Catalog, TwinManifest, TwinParts, TwinMapping, ProcessBundle } from '@/types/twin'

export class TwinError extends Error {
  constructor(public code: string, message: string) { super(message); this.name = 'TwinError' }
}
async function request<T>(method: string, params?: Record<string, unknown>): Promise<T> {
  const result = await callFrappeMethod<{ ok: boolean; data?: T; error?: { code: string; message: string } }>(`hb_twin_app.hb_twin.api.${method}`, params)
  if (!result.ok || !result.data) throw new TwinError(result.error?.code || 'SERVICE_ERROR', result.error?.message || '设备资源暂时不可用。')
  return result.data
}
export function protectedFailure(error: unknown): boolean {
  return (error instanceof FrappeRequestError && ['UNAUTHENTICATED', 'FORBIDDEN'].includes(error.code)) || (error instanceof TwinError && ['FORBIDDEN', 'MEMBERS_PENDING', 'ASSET_INTEGRITY_FAILED', 'ASSET_INVALID', 'ASSET_REVISION_MISMATCH'].includes(error.code))
}
export function contextParams(m: TwinManifest) {
  return { entry_id: m.entry_id, expected_model_sha256: m.model_sha256, expected_mapping_revision: m.mapping_revision }
}
export const getCatalog = () => request<Catalog>('get_catalog')
export const getManifest = (entryId: string, expectedModelSha?: string) => request<TwinManifest>('get_entry_manifest', { entry_id: entryId, ...(expectedModelSha ? {expected_model_sha256:expectedModelSha} : {}) })
export const getParts = (m: TwinManifest) => request<TwinParts>('get_entry_parts', contextParams(m))
export const getMapping = (m: TwinManifest, equipmentId: string, assetId: string) => request<TwinMapping>('get_entry_mapping', { ...contextParams(m), equipment_id: equipmentId, asset_id: assetId })
export const getProcess = (m: TwinManifest) => request<ProcessBundle>('get_entry_process', { ...contextParams(m), expected_process_revision: m.process_revision })
