// Adapted from frozen WUJUN release; provenance hashes are in the private compatibility record.
import * as T from 'three';
import type { BindingConfig } from '@/types/twin';
export class FiltrationBinding{
 readonly saved=new Map<T.Mesh,{material:T.Material|T.Material[];geometry:T.BufferGeometry;visible:boolean;parent:T.Object3D|null;matrix:number[]}>();
 readonly trimmed=new Map<T.Mesh,T.BufferGeometry>();readonly clones=new Set<T.Material>();readonly matrix=new T.Matrix4();readonly planes:T.Plane[];readonly record:Record<string,unknown>;
 cutaway=false;readonly hiddenRear=new Map<T.Mesh,boolean>();readonly auxiliary=new Map<T.Mesh,T.Material|T.Material[]>();readonly auxiliaryClones=new Map<T.Mesh,T.Material|T.Material[]>();
 constructor(readonly meshes:T.Mesh[],readonly group:T.Group,readonly config:BindingConfig){
  const equipment=config.source_key,vesselIds=config.ids,anchorId=config.anchor;
  const targets=meshes.filter(m=>vesselIds.includes(m.userData.asset_id));
  if(targets.length!==5)throw new Error('Vessel binding requires all 5 registered shell IDs: '+equipment);
  const anchor=targets.find(m=>m.userData.asset_id===anchorId)!;anchor.updateWorldMatrix(true,false);const b=new T.Box3().setFromObject(anchor),center=b.getCenter(new T.Vector3()),size=b.getSize(new T.Vector3());
  // Bound to the narrow cylinder, not the equipment/HMI/pipe-rack envelope.
  const radius=Math.min(size.x,size.z)*config.radius,verticalScale=size.y*config.vertical;
  const origin=new T.Vector3(center.x,b.min.y+size.y*config.origin,center.z);
  const front=new T.Vector3(...config.front).normalize(),up=new T.Vector3(0,1,0),right=new T.Vector3().crossVectors(up,front).normalize();
  this.matrix.makeBasis(right,up,front).scale(new T.Vector3(radius,verticalScale,radius)).setPosition(origin);
  group.matrixAutoUpdate=false;group.matrix.copy(this.matrix);group.updateMatrixWorld(true);
  const local=[new T.Plane(new T.Vector3(0,0,-1),.08),new T.Plane(new T.Vector3(0,-1,0),-.16),new T.Plane(new T.Vector3(0,1,0),-2.25)];
  this.planes=local.map(p=>p.clone().applyMatrix4(this.matrix));
  for(const mesh of targets)this.saved.set(mesh,{material:mesh.material,geometry:mesh.geometry,visible:mesh.visible,parent:mesh.parent,matrix:mesh.matrixWorld.toArray()});
  // Rear fittings previously read as two floating internal plates in the front window.
  const rearIds:string[]=[];
  const rearPlane=new T.Plane(new T.Vector3(0,0,-1),-1.12).applyMatrix4(this.matrix);
  const inverse=this.matrix.clone().invert();
  // The two apparent internal plates are inward faces merged into source shell meshes.
  // Keep originals; omit only deep internal triangles from a cutaway-only index copy.
  for(const mesh of targets.filter(m=>m.userData.asset_id===config.trim_id)){const geometry=mesh.geometry,index=geometry.index,position=geometry.getAttribute('position');if(!index)continue;const transform=inverse.clone().multiply(mesh.matrixWorld),kept:number[]=[];let omitted=0;
   for(let i=0;i<index.count;i+=3){const points=[0,1,2].map(k=>new T.Vector3().fromBufferAttribute(position,index.getX(i+k)).applyMatrix4(transform));const c=points[0]!.clone().add(points[1]!).add(points[2]!).multiplyScalar(1/3);if(Math.hypot(c.x,c.z)<1.24&&c.y>-.02&&c.y<1.6){omitted++;continue;}kept.push(index.getX(i),index.getX(i+1),index.getX(i+2));}
   if(omitted){const copy=geometry.clone();copy.setIndex(kept);this.trimmed.set(mesh,copy);}
  }

  for(const m of meshes){const localBox=new T.Box3().setFromObject(m).applyMatrix4(inverse),c=localBox.getCenter(new T.Vector3());
   const discharge=Math.abs(c.x)<.95&&c.z>1.2&&c.z<3.2&&c.y>-.95&&c.y<.65;
   if(!rearIds.includes(m.userData.asset_id)&&!discharge)continue;
   if(rearIds.includes(m.userData.asset_id))this.hiddenRear.set(m,m.visible);this.auxiliary.set(m,m.material);const clone=(mat:T.Material)=>{const copy=mat.clone();if(rearIds.includes(m.userData.asset_id)){copy.clippingPlanes=[rearPlane];copy.side=T.DoubleSide;}else{copy.transparent=true;copy.opacity=.12;copy.depthWrite=false;}return copy;};this.auxiliaryClones.set(m,Array.isArray(m.material)?m.material.map(clone):clone(m.material));
  }
  this.record={equipment,source_parent:equipment==='101'?'EQP101.dwg':'EQP102.dwg',status:'display_fit_not_measured',anchor_asset_id:anchorId,target_asset_ids:vesselIds,anchor_world_matrix:anchor.matrixWorld.toArray(),anchor_bounds:{min:b.min.toArray(),max:b.max.toArray()},radius_display_units:radius,vertical_scale:verticalScale,origin_world:origin.toArray(),front_world:front.toArray(),demo_to_world:this.matrix.toArray(),world_to_demo:this.matrix.clone().invert().toArray(),local_clip_planes:local.map(p=>[...p.normal.toArray(),p.constant]),world_clip_planes:this.planes.map(p=>[...p.normal.toArray(),p.constant]),clip_operation:'intersection of negative halfspaces: front window only between local y=-0.16 and 2.25',filter_local_y:.04,liquid_top_max:2.19,liquid_direction_region_y:[-.115,-.015],boundary:'user-review schematic route: central bottom drainage, front discharge, left vacuum; exact dimensions and downstream connectivity unknown',auxiliary_visual_targets:[...this.auxiliary.keys()].map(m=>m.userData.asset_id),hidden_rear_fittings:[...this.hiddenRear.keys()].map(m=>m.userData.asset_id),cutaway_internal_triangle_filter:[...this.trimmed.keys()].map(m=>m.userData.asset_id),source_file_geometry_modified:false,source_parent_modified:false,real_inner_diameter:null,HDS1400_used:false};
 }
 setCutaway(enabled:boolean){for(const [m,v] of this.hiddenRear)m.visible=enabled?false:v;this.cutaway=enabled;this.group.visible=enabled;for(const [m,mat] of this.auxiliary)m.material=enabled?this.auxiliaryClones.get(m)!:mat;
  for(const [mesh,saved] of this.saved){mesh.visible=saved.visible;mesh.geometry=enabled?(this.trimmed.get(mesh)??saved.geometry):saved.geometry;if(!enabled){mesh.material=saved.material;continue;}
   const clone=(mat:T.Material)=>{const copy=mat.clone();copy.name='demo_in_situ_clip_'+mat.name;copy.clippingPlanes=this.planes;copy.clipIntersection=true;copy.side=T.DoubleSide;if(mesh.userData.asset_id===this.config.transparent_id){copy.transparent=true;copy.opacity=.16;copy.depthWrite=false;}this.clones.add(copy);return copy;};
   // Reuse the same cloned array on each toggle, dispose only at exit.
   const existing=mesh.userData.demoClippedMaterial as T.Material|T.Material[]|undefined;
   const mats=existing??(Array.isArray(saved.material)?saved.material.map(clone):clone(saved.material));mesh.userData.demoClippedMaterial=mats;mesh.material=mats;
  }
 }
 audit(){return {targets:this.saved.size,cutaway:this.cutaway,cloned_materials:this.clones.size,source_transforms_preserved:[...this.saved].every(([m,s])=>m.parent===s.parent&&JSON.stringify(m.matrixWorld.toArray())===JSON.stringify(s.matrix)),only_registered_targets:this.meshes.filter(m=>this.clones.has(Array.isArray(m.material)?m.material[0]!:m.material)).every(m=>this.config.ids.includes(m.userData.asset_id)),matrix:this.group.matrixWorld.toArray()};}
 dispose(){for(const [m,v] of this.hiddenRear)m.visible=v;for(const [m,mat] of this.auxiliary)m.material=mat;for(const mat of this.auxiliaryClones.values())(Array.isArray(mat)?mat:[mat]).forEach(m=>m.dispose());for(const [m,s] of this.saved){m.material=s.material;m.geometry=s.geometry;m.visible=s.visible;delete m.userData.demoClippedMaterial;}this.clones.forEach(m=>m.dispose());this.clones.clear();this.trimmed.forEach(g=>g.dispose());this.trimmed.clear();}
}
