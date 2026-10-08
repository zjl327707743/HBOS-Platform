export type EquipmentId = string
export interface CatalogEntry { entry_id: string; entity_type: 'device' | 'scene'; equipment_ids: string[]; label: string; availability: string }
export interface Catalog { schema: string; catalog_revision: string; entries: CatalogEntry[] }
export interface TwinManifest extends Omit<CatalogEntry, 'availability'> {
  model_sha256: string; model_size_bytes: number; model_revision: string
  mapping_revision: string; mapping_sha256: string; process_revision: string; process_sha256: string
  binding_revision: string; camera_revision: string; demo_revision: string; demo_seed: number
  model_url: string; review_only: boolean; truth: Record<string, string>
}
export interface CandidateGroup { group_id: string; equipment_id: string | null; label: string; status: 'candidate'; asset_ids: string[]; excluded_references: number }
export interface TwinParts { entry_id: string; model_sha256: string; mapping_revision: string; groups: CandidateGroup[] }
export interface TwinMapping { entry_id: string; equipment_id: string; asset_id: string; model_sha256: string; mapping_revision: string; status: string; display_name: string; component_id: string | null; knowledge_link_available: boolean }
export interface NetworkGroup { source_object_ids: string[]; cores: { source_object_id: string; points: number[][]; radius: number }[] }
export interface BindingConfig { trim_id: string; transparent_id: string; ids: string[]; anchor: string; front: [number, number, number]; radius: number; vertical: number; origin: number; source_key: string; routes: Record<string, number[][]>; network_groups: Record<string, NetworkGroup> }
export interface ProcessBundle { entry_id: string; model_sha256: string; mapping_revision: string; process_revision: string; binding_revision: string; modes: string[]; bindings: Record<string, BindingConfig> }
export interface DemoSession { contextKey: string; equipmentId: string; mode: 'browse' | 'production'; time: number; paused: boolean; speed: number; followCamera: boolean }
export interface ViewerMetrics { geometries: number; textures: number; triangles: number; calls: number; parseMs: number; downloadMs: number; firstVisibleMs: number; ownedMaterials: number }
