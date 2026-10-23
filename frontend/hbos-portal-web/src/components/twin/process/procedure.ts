// Adapted from frozen WUJUN release; provenance hashes are in the private compatibility record.
import type { BindingConfig } from '@/types/twin';
import * as T from 'three';
import {ProcessHardware,washState} from './process-hardware';
import {processNames} from './display-names';
import {FiltrationView} from './filtration-view';
import {evaluateFiltrationDemo} from './filtration-state';
export type ProcedureMode='filtration'|'production'|'cip'|'sip';
export const procedures={filtration:{label:processNames.filtration,duration:40,stages:['过滤']},production:{label:processNames.production,duration:60,stages:['进料','过滤','洗涤','干燥','出料']},cip:{label:processNames.cip,duration:24,stages:['供给管网','罐内冲洗与回液','底部回液排出']},sip:{label:processNames.sip,duration:24,stages:['进气管向下进气','自上而下充满罐体','下部排水管排气']}};
export function phaseAt(mode:ProcedureMode,t:number){const def=procedures[mode],position=Math.max(0,Math.min(def.stages.length-1e-9,t/def.duration*def.stages.length)),index=Math.floor(position);return {index,progress:position-index,label:def.stages[index]};}
export class ProcedureEffects{
 readonly hardware:ProcessHardware;readonly group=new T.Group();readonly particles:T.InstancedMesh;readonly film:T.Mesh;readonly heat:T.Mesh;private dummy=new T.Object3D();
 constructor(readonly view:FiltrationView,config:BindingConfig,sourceMeshes:T.Mesh[]=[]){
  this.hardware=new ProcessHardware(view.group,config,sourceMeshes);this.group.visible=false;this.group.name='procedure_schematic_not_machine_internals';this.group.userData={source:'schematic',real_nozzle_geometry:false};view.group.add(this.group);
  this.particles=new T.InstancedMesh(new T.SphereGeometry(.018,7,5),new T.MeshBasicMaterial({color:0x52c9ed,transparent:true,opacity:.8}),100);this.particles.instanceMatrix.setUsage(T.DynamicDrawUsage);this.group.add(this.particles);
  this.film=new T.Mesh(new T.CylinderGeometry(.97,.97,2.1,48,1,true,Math.PI/2,Math.PI),new T.MeshBasicMaterial({color:0x40bce1,transparent:true,opacity:.16,side:T.DoubleSide,depthWrite:false}));this.film.position.y=1.15;this.group.add(this.film);
  this.heat=new T.Mesh(new T.CylinderGeometry(.93,.93,2.1,48,1,true,Math.PI/2,Math.PI),new T.MeshBasicMaterial({color:0xe8a265,transparent:true,opacity:.12,side:T.DoubleSide,depthWrite:false}));this.heat.position.y=1.15;this.group.add(this.heat);
 }
 update(mode:ProcedureMode,time:number){
  time=Math.max(0,Math.min(procedures[mode].duration,time));
  const {index,progress:p,label}=phaseAt(mode,time);let liquid=0,solid=0,moisture=0,removed=0;this.group.visible=mode!=='filtration';this.particles.visible=false;this.film.visible=false;this.heat.visible=false;
  // Every mutable property is assigned from (mode,time), including hidden layers.
  (this.particles.material as T.MeshBasicMaterial).color.setHex(0x52c9ed);(this.particles.material as T.MeshBasicMaterial).opacity=.8;this.view.liquid.visible=true;this.view.solids.visible=true;this.view.solids.count=240;this.view.solids.scale.set(1,1,1);
  (this.film.material as T.MeshBasicMaterial).opacity=.16;(this.heat.material as T.MeshBasicMaterial).opacity=.12;
  if(mode==='filtration'){this.view.update(evaluateFiltrationDemo(time));}
  else if(mode==='production'){
   const base=evaluateFiltrationDemo(index===0?0:index===1?p*40:40);this.view.update(base);
   if(index===0){liquid=p;solid=p;this.view.solids.count=Math.floor(240*p);this.view.solids.scale.y=Math.max(.02,p);this.view.cake.visible=false;}
   else if(index===1){liquid=base.liquid.remaining;solid=1;this.view.solids.scale.y=1;}
   else if(index===2){liquid=washState(p).liquid;solid=1;this.film.visible=true;(this.film.material as T.MeshBasicMaterial).opacity=.06+.18*Math.sin(Math.PI*p);}
   else if(index===3){liquid=.12*(1-p);solid=1;moisture=1-p;this.particles.visible=true;this.heat.visible=true;}
   else {const q=Math.max(0,(p-.2)/.8);liquid=0;solid=1-q;removed=q;this.view.solids.count=Math.floor(240*(1-q));this.view.cake.scale.y=Math.max(.001,.34*(1-q));this.view.cake.position.y=.09+.17*(1-q);}
   this.view.liquid.scale.y=Math.max(.001,2.1*liquid);this.view.liquid.position.y=.09+1.05*liquid;this.view.liquid.visible=liquid>0;this.view.drops.visible=false;
  }else{
   this.view.update(evaluateFiltrationDemo(0));this.view.solids.visible=false;this.view.cake.visible=false;this.view.drops.visible=false;this.particles.visible=true;this.film.visible=mode==='cip';this.heat.visible=false;// Illustrative continuity: CIP fills, holds, then drains; SIP condensate accumulates.
   const wet= index===0?p:index===1?1:1-p;
   liquid=mode==='cip'?.035*wet:0;this.view.liquid.visible=mode==='cip'&&liquid>0;
   this.view.liquid.scale.y=Math.max(.001,liquid);this.view.liquid.position.y=.09+liquid/2;
   (this.film.material as T.MeshBasicMaterial).opacity=.08+.18*wet;
   (this.heat.material as T.MeshBasicMaterial).opacity=.14+.27*Math.min(1,time/8);
   (this.particles.material as T.MeshBasicMaterial).color.setHex(mode==='sip'?0xd9edf5:0x52c9ed);
   (this.particles.material as T.MeshBasicMaterial).opacity=mode==='sip'?(index===0?.18+.4*p:.75):.8;
  }
  for(let i=0;i<100;i++){const q=(time*.55+i/100)%1,a=i*2.39996;let r=.9,y=2.12-q*1.98;
   if(mode==='sip'){r=.80*Math.sqrt((i+.5)/100);const depth=index===0?.25+.55*p:index===1?.8+1.1*p:1.9;y=2.12-q*depth;}
   if(mode==='cip'&&index===0){r=.08+.83*q;y=2.12-q*1.8;}if(mode==='production'){r=.75*Math.sqrt((i+.5)/100);y=.5+q*1.55;} // moisture markers remain inside unconfirmed boundary
   this.dummy.position.set(r*Math.cos(a),y,r*Math.sin(a));this.dummy.scale.set(mode==='sip'?1.7:mode==='production'?1.8:.8,mode==='sip'?(index===2?2.8:1.7):mode==='cip'?2:1,mode==='sip'?1.7:mode==='production'?1.8:.8);this.dummy.updateMatrix();this.particles.setMatrixAt(i,this.dummy.matrix);
  }
  if(mode==='production'&&index===2&&washState(p).step===2){for(let i=0;i<240;i++){const a=i*2.39996+time*2,r=.85*Math.sqrt((i+.5)/240);this.dummy.position.set(r*Math.cos(a),.18+.65*((i*.618+time*.15)%1),r*Math.sin(a));this.dummy.scale.setScalar(1);this.dummy.updateMatrix();this.view.solids.setMatrixAt(i,this.dummy.matrix);}this.view.solids.instanceMatrix.needsUpdate=true;this.view.solids.computeBoundingSphere();}
  const hardwareLabel=this.hardware.update(mode,time,index,p);this.particles.visible=mode==='production'?index===3:this.particles.visible;this.particles.instanceMatrix.needsUpdate=true;this.particles.computeBoundingSphere();return mode==='filtration'?{label,liquid:null,solid:null,moisture:null,removed:null}:{label:hardwareLabel??label,liquid,solid,moisture,removed};
 }
}
