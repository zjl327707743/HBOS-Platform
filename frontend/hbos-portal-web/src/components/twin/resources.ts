import * as T from 'three'

/** Dispose only this tree's resources, once per identity, including instancing. */
export function disposeTree(root: T.Object3D) {
  const geometries = new Set<T.BufferGeometry>(), materials = new Set<T.Material>(), textures = new Set<T.Texture>()
  root.traverse(node => {
    if (node instanceof T.InstancedMesh) node.dispose()
    if (node instanceof T.Mesh) geometries.add(node.geometry)
    if (node instanceof T.Mesh || node instanceof T.Sprite) {
      for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
        materials.add(material)
        for (const value of Object.values(material)) if (value instanceof T.Texture) textures.add(value)
      }
    }
  })
  textures.forEach(t => t.dispose()); materials.forEach(m => m.dispose()); geometries.forEach(g => g.dispose())
  root.removeFromParent(); root.clear()
  return { geometries:geometries.size, materials:materials.size, textures:textures.size }
}
export function effectiveVisible(node: T.Object3D) {
  for (let current: T.Object3D | null = node; current; current = current.parent) if (!current.visible) return false
  return true
}

/** Source visibility and materials are immutable baselines. Display clones are owned here. */
export class DisplayState {
  readonly visibility = new Map<T.Object3D,boolean>()
  readonly materials = new Map<T.Mesh,T.Material | T.Material[]>()
  readonly selected = new Set<T.Object3D>()
  readonly hidden = new Set<T.Object3D>()
  readonly owned = new Set<T.Material>()
  isolated = false; wireframe = false
  constructor(readonly root: T.Object3D) { root.traverse(n => this.visibility.set(n,n.visible)); this.captureMaterials() }
  captureMaterials() { this.materials.clear(); this.root.traverse(n => { if(n instanceof T.Mesh) this.materials.set(n,n.material) }) }
  restoreMaterials() { for (const [mesh, material] of this.materials) mesh.material = material; this.owned.forEach(m=>m.dispose()); this.owned.clear() }
  setSelection(nodes: T.Object3D[]) { this.selected.clear(); for(const n of nodes) this.selected.add(n); this.apply() }
  apply() {
    this.restoreMaterials()
    const chosen = new Set<T.Object3D>(), hidden = new Set<T.Object3D>()
    this.selected.forEach(n=>n.traverse(c=>chosen.add(c))); this.hidden.forEach(n=>n.traverse(c=>hidden.add(c)))
    const cache = new Map<string,T.Material>()
    for (const [node, baseline] of this.visibility) node.visible = baseline && !hidden.has(node) && (!(node instanceof T.Mesh) || !this.isolated || chosen.has(node))
    for (const [mesh, base] of this.materials) {
      const selected = chosen.has(mesh)
      if (!selected && !this.wireframe) continue
      const style = (material:T.Material) => {
        const key = `${material.uuid}:${selected}:${this.wireframe}`
        let clone = cache.get(key)
        if (!clone) {
          clone = material.clone(); const standard = clone as T.MeshStandardMaterial
          if ('wireframe' in standard) standard.wireframe = this.wireframe
          if (selected && standard.emissive) { standard.emissive.set('#6c62ed'); standard.emissiveIntensity = .65 }
          cache.set(key,clone); this.owned.add(clone)
        }
        return clone
      }
      mesh.material = Array.isArray(base) ? base.map(style) : style(base)
    }
  }
  reset() { this.selected.clear(); this.hidden.clear(); this.isolated=false; this.wireframe=false; this.apply() }
  dispose() { this.reset(); this.restoreMaterials(); this.materials.clear(); this.visibility.clear() }
}
