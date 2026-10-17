// Adapted from frozen WUJUN release; provenance hashes are in the private compatibility record.
import * as T from 'three';
import type { BindingConfig } from '@/types/twin';
export type RouteSpec={id:string;kind:string;points:number[][];radius:number;status:string;boundary:string;source_object_ids:string[]};
/** Coordinates are local display fits, never surveyed pipe coordinates. Each device is configured separately. */
export function routeSpecs(config:BindingConfig):RouteSpec[]{const equipment=config.source_key,cfg=config.routes;if(!cfg)return [];return Object.entries(cfg).map(([id,points])=>({id:'WD'+equipment+'_process_visual_pipe_'+id,kind:id,points,radius:['feed','vacuum','cip_return','steam_supply','vent_boundary'].includes(id)?.075:.05,status:'schematic_route_pending',boundary:'open_boundary',source_object_ids:config.network_groups[id]?.source_object_ids??[]}));}
/** Piecewise straight centerline: same path is used for pipe, core and moving markers. */
export function pipeCurve(points:number[][]){const c=new T.CurvePath<T.Vector3>();for(let i=1;i<points.length;i++)c.add(new T.LineCurve3(new T.Vector3().fromArray(points[i-1]!),new T.Vector3().fromArray(points[i]!)));return c;}
export function networkState(mode:string,index:number,p:number){const washStep=Math.min(5,Math.floor(p*6));const keys:string[]=[];let medium='none',caption='';
 if(mode==='production'){if(index===0){keys.push('feed');medium='feed_raw_liquid';caption='原液 · 长进料管 → 罐内';}if(index===2){medium='wash_solvent';caption='洗涤液 · 生产进料主管 → 罐内';if(washStep===0)keys.push('feed');}if(index===3){keys.push('vacuum');medium='extracted_gas';caption='干燥 · 夹套加热 + 气体上升 → 真空抽出';}}
 if(mode==='cip'){medium='cleaning_liquid';caption=['清洗液 · 供给主干 → 顶部三路','清洗液 · 三路进入 → 罐壁冲洗 → 底部回液','清洗液 · 底部回液 → 开放边界'][index]!;if(index<2)keys.push('wash_supply_main','wash_top_branch_1','wash_top_branch_2','wash_top_branch_3');if(index<2)keys.push('feed','vacuum');if(index>0)keys.push('cip_return');}
 if(mode==='sip'){medium='sterilization_steam';caption=['蒸汽 · 进气管向下进入','蒸汽 · 自上而下逐步充满罐体','蒸汽 · 下部排水管排出（下游待核）'][index]!;if(index<2)keys.push('steam_supply');if(index===2)keys.push('cip_return');}
 return {keys,medium,caption};}
export class ProcessNetwork{
 readonly group=new T.Group();enabled=true;
 readonly routes:{spec:RouteSpec;curve:T.Curve<T.Vector3>;shell:T.Mesh;core:T.Mesh;markers:T.InstancedMesh;length:number}[]=[];
 readonly sources=new Map<T.Mesh,{original:T.Material|T.Material[];cloned:T.Material|T.Material[];background:T.Material|T.Material[];kinds:Set<string>}>();
 private dummy=new T.Object3D();state=networkState('production',0,0);
 constructor(parent:T.Group,readonly config:BindingConfig,sourceMeshes:T.Mesh[]=[]){const equipment=config.source_key;this.group.name='WD'+equipment+'_process_network';parent.add(this.group);
 const specs=routeSpecs(config);const groups=config.network_groups;
 for(const [kind,g] of Object.entries<any>(groups)){for(const id of g.source_object_ids){const m=sourceMeshes.find(m=>m.userData.asset_id===id);if(!m)continue;if(this.sources.has(m)){this.sources.get(m)!.kinds.add(kind);continue;}const clone=(mat:T.Material)=>{const c=mat.clone() as T.MeshStandardMaterial;c.transparent=true;c.opacity=.20;c.depthWrite=false;return c;};const dim=(mat:T.Material)=>{const c=mat.clone() as T.MeshStandardMaterial;if(c.color)c.color.multiplyScalar(.66);if(c.roughness!==undefined)c.roughness=Math.max(.38,c.roughness);return c;};this.sources.set(m,{original:m.material,background:Array.isArray(m.material)?m.material.map(dim):dim(m.material),cloned:Array.isArray(m.material)?m.material.map(clone):clone(m.material),kinds:new Set([kind])});}
 // Only straight cylinders that passed the source-vertex fit get source-bound fluid cores.
 for(const c of g.cores)specs.push({id:'WD'+equipment+'_source_core_'+c.source_object_id,kind,points:c.points,radius:c.radius,status:'engineering_endpoint_pending',boundary:'open_boundary',source_object_ids:[c.source_object_id]});}
 for(const spec of specs){const curve=pipeCurve(spec.points),length=curve.getLength(),source=spec.id.includes('_source_core_');const shell=new T.Mesh(new T.TubeGeometry(curve,Math.max(20,Math.ceil(length*30)),spec.radius,10,false),new T.MeshStandardMaterial({color:0x54747f,metalness:.8,roughness:.28,transparent:true,opacity:.26,depthWrite:false}));shell.name=spec.id;shell.userData={...spec,process_visual_pipe:!source,dimensions:'display_fit_not_measured'};const core=new T.Mesh(new T.TubeGeometry(curve,Math.max(20,Math.ceil(length*30)),spec.radius*.55,8,false),new T.MeshBasicMaterial({color:0x1389ed,transparent:true,opacity:.94,depthWrite:false}));const count=Math.max(12,Math.ceil(length*12));const markers=new T.InstancedMesh(new T.SphereGeometry(spec.radius*.69,8,6),new T.MeshBasicMaterial({color:0x66d9ff}),count);markers.instanceMatrix.setUsage(T.DynamicDrawUsage);this.group.add(shell,core,markers);this.routes.push({spec,curve,shell,core,markers,length});}
 this.update('production',0,0,0);
 }
 update(mode:string,time:number,index:number,p:number){this.state=networkState(mode,index,p);const active=new Set(this.enabled?this.state.keys:[]);
 for(const [m,s] of this.sources)m.material=[...s.kinds].some(k=>active.has(k))?s.cloned:this.enabled?s.background:s.original;
 for(const r of this.routes){const on=active.has(r.spec.kind),source=r.spec.id.includes('_source_core_');r.shell.visible=!source&&(on||['feed','vacuum'].includes(r.spec.kind));(r.shell.material as T.MeshStandardMaterial).opacity=on?.23:.85;r.core.visible=on;r.markers.visible=on;(r.core.material as T.MeshBasicMaterial).opacity=mode==='sip'?.15:.94;
 const gas=mode==='sip'||mode==='production'&&r.spec.kind==='vacuum',color=gas?0xd9edf5:r.spec.kind==='condensate'?0x8ae9ee:0x227ac2;(r.core.material as T.MeshBasicMaterial).color.setHex(color);(r.markers.material as T.MeshBasicMaterial).color.setHex(gas?0xf5fbff:0x91d5ef);
 const speed=this.state.medium==='wash_solvent'?.75:this.state.medium==='feed_raw_liquid'?1.15:gas?1.45:1;for(let i=0;i<r.markers.count;i++){const u=(time*speed/r.length+i/r.markers.count)%1;this.dummy.position.copy(r.curve.getPoint(u));this.dummy.scale.setScalar(1);this.dummy.updateMatrix();r.markers.setMatrixAt(i,this.dummy.matrix);}r.markers.instanceMatrix.needsUpdate=true;r.markers.computeBoundingSphere();}
 return this.state;
 }
 disposeVisuals(){this.group.removeFromParent();this.group.traverse(o=>{if(o instanceof T.Mesh){o.geometry.dispose();for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();}});}
 restore(){for(const [m,s] of this.sources){m.material=s.original;for(const mat of Array.isArray(s.cloned)?s.cloned:[s.cloned])mat.dispose();}for(const s of this.sources.values())for(const mat of Array.isArray(s.background)?s.background:[s.background])mat.dispose();this.sources.clear();}
}
