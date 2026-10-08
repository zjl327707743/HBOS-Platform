import type { DemoSession, TwinManifest, TwinMapping } from '@/types/twin'
export function contextKey(m: TwinManifest, equipment: string) { return [m.entry_id, equipment, m.model_sha256, m.mapping_revision, m.mapping_sha256, m.process_revision, m.process_sha256, m.binding_revision, m.camera_revision, m.demo_revision, m.demo_seed].join(':') }
export function makeSession(m: TwinManifest, equipment: string): DemoSession { return { contextKey: contextKey(m,equipment), equipmentId: equipment, mode:'browse', time:0, paused:true, speed:1, followCamera:false } }
export function seek(session: DemoSession, time: number) { session.time = Math.max(0, Math.min(60, Number.isFinite(time) ? time : 0)) }
export function knowledgeQuery(equipment: string, mapping: TwinMapping | null, m: TwinManifest) {
  const query: Record<string,string> = { equipment_id:equipment, q:`${equipment} 设备维护、工艺与接口`, auto:'1' }
  if (mapping?.entry_id === m.entry_id && mapping.equipment_id === equipment && mapping.model_sha256 === m.model_sha256 && mapping.mapping_revision === m.mapping_revision && mapping.status === 'verified' && mapping.knowledge_link_available && mapping.component_id) {
    query.asset_id = mapping.asset_id; query.component_id = mapping.component_id
  }
  return query
}
export class Generation {
  private value = 0
  next() { return ++this.value }
  isCurrent(value: number) { return value === this.value }
}
