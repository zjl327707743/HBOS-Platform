import { afterEach, describe, expect, it, vi } from 'vitest'
import * as T from 'three'
import { applySourcePresentation, DisplayState, disposeTree, effectiveVisible } from '@/components/twin/resources'
import { createProduction } from '@/components/twin/process/runtime'
import { createScheduler } from '@/composables/twin/scheduler'
import { contextKey, knowledgeQuery, makeSession, seek } from '@/composables/twin/session'
import type { BindingConfig, TwinManifest, TwinMapping } from '@/types/twin'

afterEach(()=>vi.restoreAllMocks())
const manifest={entry_id:'M606B',model_sha256:'model-a',mapping_revision:'parts-a',process_revision:'process-a'} as TwinManifest

describe('Twin context and knowledge compatibility',()=>{
  it('keeps independent equipment, model, mapping and process sessions',()=>{
    const first=makeSession(manifest,'M606B'),other=makeSession(manifest,'M607B')
    seek(first,32)
    expect(other.time).toBe(0);expect(other.paused).toBe(true)
    for(const key of ['entry_id','model_sha256','mapping_revision','mapping_sha256','process_revision','process_sha256','binding_revision','camera_revision','demo_revision','demo_seed'])expect(contextKey({...manifest,[key]:'new'},'M606B')).not.toBe(first.contextKey)
    for(const [value,expected]of [[-1,0],[70,60],[NaN,0],[Infinity,0]]){seek(first,value!);expect(first.time).toBe(expected)}
  })
  it('preserves q/auto and sends no candidate, stale or cross-entry business identity',()=>{
    const mapped={entry_id:'M606B',equipment_id:'M606B',model_sha256:'model-a',mapping_revision:'parts-a',status:'verified',asset_id:'invented-node',component_id:'approved-component',knowledge_link_available:true} as TwinMapping
    const old=knowledgeQuery('M606B',null,manifest)
    expect(old).toMatchObject({equipment_id:'M606B',auto:'1'});expect(old.q).toContain('M606B')
    for(const change of [{status:'candidate'},{entry_id:'DUAL'},{equipment_id:'M607B'},{model_sha256:'old'},{mapping_revision:'old'},{knowledge_link_available:false}])expect(knowledgeQuery('M606B',{...mapped,...change},manifest)).toEqual(old)
    expect(knowledgeQuery('M606B',mapped,manifest)).toMatchObject({asset_id:'invented-node',component_id:'approved-component'})
  })
})

it('owns one frame loop, sleeps when idle and cancels it on exit',()=>{
  let serial=0
  const frames=new Map<number,FrameRequestCallback>(),cancel=vi.fn((id:number)=>frames.delete(id))
  const scheduler=createScheduler(cb=>{frames.set(++serial,cb);return serial},cancel)
  let animate=true
  const times:number[]=[]
  const unsubscribe=scheduler.subscribe(dt=>{times.push(dt);return animate})
  const flush=(time:number)=>{const [id,callback]=[...frames][0]!;frames.delete(id);callback(time)}
  for(let i=0;i<100;i++)scheduler.invalidate()
  expect(frames.size).toBe(1);flush(1000);flush(1016);flush(9000)
  expect(times).toEqual([0,.016,.1]);expect(frames.size).toBe(1)
  animate=false;flush(9016);expect(frames.size).toBe(0)
  scheduler.invalidate();flush(12000);expect(times.at(-1)).toBe(0)
  unsubscribe();scheduler.invalidate();scheduler.stop()
  expect(cancel).toHaveBeenCalled();expect(scheduler.listenerCount).toBe(0);expect(scheduler.pendingFrames).toBe(0)
})

describe('Twin display resource ownership',()=>{
  it('honors frozen mutual-exclusion metadata before capturing the reset baseline',()=>{
    const root=new T.Group(),material=new T.MeshStandardMaterial({opacity:0,transparent:true,depthWrite:false}),geometry=new T.BoxGeometry()
    material.userData={mutually_exclusive_source:true,restore_opacity:1}
    const source=new T.Mesh(geometry,material),replacement=new T.Mesh(geometry,material)
    source.userData.replaced_by_site_group='A';replacement.userData.site_revision_group='A';root.add(source,replacement)
    applySourcePresentation(root);const state=new DisplayState(root)
    expect(source.visible).toBe(false);expect(replacement.visible).toBe(true);expect(material.opacity).toBe(1);expect(material.transparent).toBe(false)
    state.setSelection([source]);state.isolated=true;state.wireframe=true;state.apply();state.reset()
    expect(effectiveVisible(source)).toBe(false);expect(replacement.material).toBe(material);expect(replacement.visible).toBe(true)
    state.dispose();disposeTree(root)
  })
  it('restores source visibility and materials after isolate, hide and wireframe',()=>{
    const root=new T.Group(),group=new T.Group(),material=new T.MeshStandardMaterial(),geometry=new T.BoxGeometry()
    const visible=new T.Mesh(geometry,material),hidden=new T.Mesh(geometry,material),sibling=new T.Mesh(geometry,material)
    hidden.visible=false;group.add(visible,hidden);root.add(group,sibling)
    const state=new DisplayState(root),dispose=vi.spyOn(material,'dispose')
    for(let i=0;i<40;i++){
      state.setSelection([group]);state.isolated=true;state.wireframe=true;state.apply()
      expect(effectiveVisible(sibling)).toBe(false);expect(effectiveVisible(hidden)).toBe(false);expect(visible.material).not.toBe(material)
      state.hidden.add(group);state.apply();expect(effectiveVisible(visible)).toBe(false)
      state.reset();expect(visible.material).toBe(material);expect(sibling.visible).toBe(true);expect(hidden.visible).toBe(false);expect(state.owned.size).toBe(0)
    }
    expect(dispose).not.toHaveBeenCalled();state.dispose();disposeTree(root);expect(dispose).toHaveBeenCalledTimes(1)
  })
  it('disposes shared textures, geometry and instanced resources only once',()=>{
    const root=new T.Group(),geometry=new T.BoxGeometry(),texture=new T.Texture(),material=new T.MeshStandardMaterial({map:texture})
    const instance=new T.InstancedMesh(geometry,material,3);root.add(instance,new T.Mesh(geometry,material))
    const spies=[vi.spyOn(texture,'dispose'),vi.spyOn(material,'dispose'),vi.spyOn(geometry,'dispose'),vi.spyOn(instance,'dispose')]
    expect(disposeTree(root)).toEqual({geometries:1,materials:1,textures:1});spies.forEach(spy=>expect(spy).toHaveBeenCalledTimes(1))
    expect(root.children).toHaveLength(0)
  })
})

function syntheticDevice(key:string){
  const scene=new T.Scene(),root=new T.Group(),imported=new T.Group(),material=new T.MeshStandardMaterial(),geometry=new T.CylinderGeometry(1000,1000,2200,16)
  imported.scale.setScalar(.001);imported.position.set(-35,0,37);root.add(imported);scene.add(root)
  const ids=Array.from({length:5},(_,i)=>`fixture-${key}-${i}`)
  for(const [i,id]of ids.entries()){const mesh=new T.Mesh(geometry,material);mesh.userData.asset_id=id;mesh.position.y=i*40;imported.add(mesh)}
  root.updateWorldMatrix(true,true)
  const config:BindingConfig={source_key:key,ids,anchor:ids[0]!,trim_id:ids[3]!,transparent_id:ids[4]!,front:[0,0,1],radius:.45,vertical:.8,origin:.1,
    routes:{feed:[[0,4,0],[0,2,0]],vacuum:[[-1,2,0],[-2,3,0]]},network_groups:{}}
  return {scene,root,config,material,geometry}
}
function visualSnapshot(root:T.Object3D){
  root.updateWorldMatrix(true,true)
  const snapshot:unknown[]=[]
  root.traverse(n=>{
    const row:unknown[]=[n.name,n.visible,n.position.toArray(),n.rotation.toArray(),n.scale.toArray()]
    if(n instanceof T.Mesh){row.push(...(Array.isArray(n.material)?n.material:[n.material]).map(m=>{
      const v=m as T.MeshStandardMaterial;return [v.opacity,v.color?.getHex(),v.emissive?.getHex(),v.emissiveIntensity,v.transparent,v.depthWrite]
    }))}
    if(n instanceof T.InstancedMesh)row.push(n.count,Array.from(n.instanceMatrix.array))
    snapshot.push(row)
  })
  return snapshot
}
describe('production absolute time and restoration',()=>{
  it.each(['101','102'])('device %s repeats forward/backward seek without changing source transforms',key=>{
    vi.spyOn(HTMLCanvasElement.prototype,'getContext').mockReturnValue({fillText(){}} as unknown as CanvasRenderingContext2D)
    const {scene,root,config,material,geometry}=syntheticDevice(key)
    const transforms=root.children[0]!.children.map(n=>n.matrixWorld.toArray())
    const disposeOriginal=vi.spyOn(material,'dispose'),runtime=createProduction(root,config)
    const times=[0,5.1,12,20,24.1,28.5,32.9,36,45.9,59.9,60],expected=new Map<number,unknown[]>()
    for(const time of times){runtime.update(time);expected.set(time,visualSnapshot(runtime.focusObject))}
    for(const time of [...times].reverse()){runtime.update(time);expect(visualSnapshot(runtime.focusObject)).toEqual(expected.get(time));runtime.update(time);expect(visualSnapshot(runtime.focusObject)).toEqual(expected.get(time))}
    runtime.update(42)
    expect(runtime.focusObject.getObjectByName('jacket_helical_heat_path')!.visible).toBe(key==='102')
    runtime.dispose();runtime.dispose()
    expect(scene.children).toEqual([root]);expect(root.children[0]!.children.map(n=>n.matrixWorld.toArray())).toEqual(transforms)
    root.traverse(n=>{if(n instanceof T.Mesh){expect(n.material).toBe(material);expect(n.geometry).toBe(geometry);expect(n.userData.demoClippedMaterial).toBeUndefined()}})
    expect(disposeOriginal).not.toHaveBeenCalled();disposeTree(root)
  })
  it('rejects missing targets before allocating a process scene',()=>{
    const {scene,root,config}=syntheticDevice('101');root.children[0]!.children[0]!.removeFromParent()
    expect(()=>createProduction(root,config)).toThrow('Incomplete production binding');expect(scene.children).toEqual([root]);disposeTree(root)
  })
})
