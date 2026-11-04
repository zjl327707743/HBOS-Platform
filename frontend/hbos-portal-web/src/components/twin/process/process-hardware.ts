// Adapted from frozen WUJUN release; provenance hashes are in the private compatibility record.
import type { BindingConfig } from '@/types/twin';
import {ProcessNetwork} from "./process-network";
import * as T from 'three';
/** User-reviewed functional topology; dimensions and internal geometry remain illustrative. */
export function washState(p:number){const step=Math.min(5,Math.floor(p*6)),q=Math.min(1,p*6-step);return {step,q,label:['洗涤液沿生产进料主管进入','搅拌桨下降','搅拌混合','搅拌桨上升','底部抽滤排液','保留固体'][step],liquid:step===0?.12+.48*q:step<4?.6:step===4?.6-.48*q:.12,lift:step===1?1-q:step===2?0:step===3?q:1};}
export class ProcessHardware {
 network:ProcessNetwork; group=new T.Group(); agitator=new T.Group();plug=new T.Group();coil:T.Mesh;flows:{mesh:T.InstancedMesh;curve:T.Curve<T.Vector3>;kind:string}[]=[];dummy=new T.Object3D();
 constructor(parent:T.Group,readonly config:BindingConfig,sourceMeshes:T.Mesh[]=[]){parent.add(this.group);this.group.name='field_revision_schematic_hardware';this.group.userData={source:'schematic_candidate',dimensions:'display_fit_not_measured'};
 const metal=new T.MeshStandardMaterial({color:0xc0d4d9,metalness:.75,roughness:.28,side:T.DoubleSide});
 const add=(g:T.BufferGeometry,m:T.Material,pos:number[],parent=this.group)=>{const mesh=new T.Mesh(g,m);mesh.position.fromArray(pos);parent.add(mesh);return mesh;};
 const route=(kind:string,points:number[][],radius=.045)=>{const curve=new T.CatmullRomCurve3(points.map(p=>new T.Vector3(p[0]!*(kind==='discharge'&&this.config.source_key==='101'?-1:1),p[1]!,p[2]!)),false,'centripetal');const pipe=add(new T.TubeGeometry(curve,90,radius,10,false),new T.MeshStandardMaterial({color:0xbed8df,metalness:.4,roughness:.25,transparent:true,opacity:.32,depthWrite:false}),[0,0,0]);pipe.name=kind+'_pipe';const mesh=new T.InstancedMesh(new T.SphereGeometry(radius*.7,8,6),new T.MeshBasicMaterial({color:kind==='vacuum'?0xe2f5ff:kind==='discharge'?0xf4c36d:0x269fff}),36);this.group.add(mesh);this.flows.push({mesh,curve,kind});};
 this.network=new ProcessNetwork(this.group,config,sourceMeshes);
 route('drain',[[0,.02,0],[0,-1.45,0],[.3,-1.65,.2],[1.65,-1.65,.2]],.065);

 route('discharge',[[-.14,-.10,.5],[-.28,-.10,.95],[-.47,-.10,1.55],[-.47,-1.25,1.55]],.16);
 // Rear half inner liner leaves an unobstructed window; coil lives between inner and outer skins.
 add(new T.CylinderGeometry(1.02,1.02,2.18,64,1,true,Math.PI/2,Math.PI),new T.MeshStandardMaterial({color:0x9ac7d3,transparent:true,opacity:.18,side:T.DoubleSide,depthWrite:false}),[0,1.16,0]);
 const pts=[];for(let i=0;i<=480;i++){const a=i/480*Math.PI*12;pts.push(new T.Vector3(1.20*Math.cos(a),.12+2.05*i/480,1.20*Math.sin(a)));}
 this.coil=add(new T.TubeGeometry(new T.CatmullRomCurve3(pts),480,.025,7,false),new T.MeshStandardMaterial({color:0xd3a064,metalness:.65,roughness:.3}),[0,0,0]);this.coil.name='jacket_helical_heat_path';
 this.group.add(this.agitator);add(new T.CylinderGeometry(.045,.045,2.2,16),metal,[0,1.1,0],this.agitator);
 // Swept S-shaped ribbon, user-requested silhouette; dimensions remain illustrative.
 const outline=new T.Shape();const samples=64,width=.19;const curveS=(t:number)=>new T.Vector2(.94*t,.34*Math.sin(Math.PI*t));
 for(let i=0;i<=samples;i++){const t=-1+2*i/samples,c=curveS(t),n=new T.Vector2(-.34*Math.PI*Math.cos(Math.PI*t),.94).normalize().multiplyScalar(width/2);const v=c.add(n);if(i===0)outline.moveTo(v.x,v.y);else outline.lineTo(v.x,v.y);}
 for(let i=samples;i>=0;i--){const t=-1+2*i/samples,c=curveS(t),n=new T.Vector2(-.34*Math.PI*Math.cos(Math.PI*t),.94).normalize().multiplyScalar(-width/2);const v=c.add(n);outline.lineTo(v.x,v.y);}outline.closePath();
 const blade=add(new T.ExtrudeGeometry(outline,{depth:.12,bevelEnabled:true,bevelSize:.012,bevelThickness:.01,bevelSegments:2,steps:1}),metal,[0,.06,0],this.agitator);blade.rotation.x=Math.PI/2;blade.name='S_shaped_agitator_blade';
 this.agitator.name='telescoping_agitator';
 this.group.add(this.plug);const plug=add(new T.CylinderGeometry(.135,.135,.26,24),metal,[0,0,0],this.plug);plug.rotation.x=Math.PI/2;this.plug.name='retractable_discharge_plug';
 }
 update(mode:string,time:number,index:number,p:number){const wash=washState(p);const production=mode==='production';const mixing=production&&(index===2&&wash.step===2||index===3||index===4&&p>.2);const lift=production&&index===2?wash.lift:production&&(index===3||index===4)?0:1;
 this.agitator.position.y=.37+lift*.65;this.agitator.rotation.y=mixing?time*2:0;const retract=production&&index===4?Math.min(1,p*5)*.75:0;this.plug.position.set(-.29-retract*.287,-.10,.97+retract*.958);this.plug.rotation.y=-.291;
 const hot=production&&index===3&&this.config.source_key==='102';const mat=this.coil.material as T.MeshStandardMaterial;mat.color.setHex(hot?0xff963c:0xb9a383);mat.emissive.setHex(hot?0x743000:0);mat.emissiveIntensity=hot?.5:0;this.coil.visible=hot;
 for(const {mesh,curve,kind} of this.flows){mesh.visible=kind==='feed'?production&&(index===0||index===2&&wash.step===0):kind==='drain'?mode==='filtration'||production&&(index===1||index===2&&wash.step===4):kind==='vacuum'?production&&index===3:production&&index===4&&p>.2;
 for(let i=0;i<36;i++){const q=(time*(kind==='feed'&&index===2?.24:.4)+i/36)%1;this.dummy.position.copy(curve.getPoint(q));this.dummy.scale.setScalar(kind==='vacuum'?1.3:1);this.dummy.updateMatrix();mesh.setMatrixAt(i,this.dummy.matrix);}mesh.instanceMatrix.needsUpdate=true;mesh.computeBoundingSphere();}
 this.network.update(mode,time,index,p);if(this.config.source_key==='101'){this.plug.position.x*=-1;this.plug.rotation.y*=-1;if(production&&index===3)this.network.state.caption='干燥 · 加热边界待核 + 气体上升 → 真空抽出';}return this.network.state.caption&&!(production&&index===2)?this.network.state.caption:production&&index===2?wash.label:production&&index===0?'原液进入 · 顶部共用入管':production&&index===3?'加热与抽真空原理示意':production&&index===4?'堵头后退 · 搅拌辅助出料':null;
 }
}
