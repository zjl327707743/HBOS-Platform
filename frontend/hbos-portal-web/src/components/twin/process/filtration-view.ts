// Adapted from frozen WUJUN release; provenance hashes are in the private compatibility record.
import * as T from 'three';
import {demoConfig,type DemoState} from './filtration-state';
export class FiltrationView{
 scene=new T.Scene();camera=new T.PerspectiveCamera(36,1,.01,100);group=new T.Group();
 liquid:T.Mesh;cake:T.Mesh;collector:T.Mesh;solids:T.InstancedMesh;drops:T.InstancedMesh;
 private dummy=new T.Object3D();
 constructor(readonly inSitu=false){
  this.scene.background=new T.Color('#152f3b');this.group.name='schematic_demo';this.group.userData={schematic_only:true};this.scene.add(this.group,new T.HemisphereLight(0xffffff,0x587a87,2.5));const light=new T.DirectionalLight(0xffffff,3);light.position.set(3,6,4);this.scene.add(light);
  this.camera.position.set(3.6,3.15,8.8);this.camera.lookAt(0,.3,0);
  const label=document.createElement('canvas');label.width=1024;label.height=96;const ctx=label.getContext('2d')!;ctx.fillStyle='#ffe2a6';ctx.font='32px sans-serif';ctx.textAlign='center';ctx.fillText('内部为简化原理示意，非实机剖面',512,42);ctx.font='23px sans-serif';ctx.fillText('SCHEMATIC ONLY · NO FIELD DATA',512,80);const texture=new T.CanvasTexture(label);const title=new T.Sprite(new T.SpriteMaterial({map:texture,depthTest:false}));title.name='demo_warning';title.userData={asset_id:title.name,schematic_only:true};title.position.set(0,2.97,0);title.scale.set(3.25,.305,1);this.group.add(title);
  const mat=(color:number,opacity=1)=>new T.MeshStandardMaterial({color,roughness:.35,metalness:.08,transparent:opacity<1,opacity,depthWrite:opacity===1,side:T.DoubleSide});
  const add=(id:string,g:T.BufferGeometry,m:T.Material,y=0)=>{const o=new T.Mesh(g,m);o.name=id;o.userData={asset_id:id,schematic_only:true};o.position.y=y;this.group.add(o);return o;};
  add('demo_cutaway_wall',new T.CylinderGeometry(1.05,1.05,2.65,64,1,true,Math.PI/2,Math.PI),mat(0x7aafbf,.23),1.38);
  add('demo_filter_surface',new T.CylinderGeometry(1,1,.08,64),mat(0xb8d9db),.04);
  // Grid only expresses a permeable plane; spacing is not a pore size.
  for(let i=-8;i<=8;i++){const x=i*.11,h=Math.sqrt(1-x*x)*2;const m=add(`demo_filter_grid_${i}`,new T.BoxGeometry(.016,.008,h),mat(0x35606b),.086);m.position.x=x;}
  this.liquid=add('demo_liquid',new T.CylinderGeometry(.98,.98,1,64),mat(0x38b5df,.38));
  this.cake=add('demo_wet_solid_layer',new T.CylinderGeometry(.96,.96,1,64),mat(0xb69559));
  add('demo_collection_wall',new T.CylinderGeometry(1.05,1.05,1.65,64,1,true,Math.PI/2,Math.PI),mat(0x7aafbf,.25),-1.3);
  add('demo_collection_base',new T.CylinderGeometry(1.05,1.05,.06,64),mat(0x608b98),-2.14);
  this.collector=add('demo_collected_liquid',new T.CylinderGeometry(.98,.98,1,64),mat(0x269fcf,.8));
  this.solids=new T.InstancedMesh(new T.IcosahedronGeometry(demoConfig.particleRadius,0),mat(0xf6c772),demoConfig.particles);this.solids.name='demo_solid_particles';this.group.add(this.solids);
  this.drops=new T.InstancedMesh(new T.SphereGeometry(.024,8,6),mat(0x62ddff),48);this.drops.name='demo_liquid_tracers';this.group.add(this.drops);
  if(inSitu){
   for(const name of ['demo_cutaway_wall','demo_collection_wall','demo_collection_base','demo_collected_liquid','demo_warning']){const o=this.group.getObjectByName(name)!;this.group.remove(o);if(o instanceof T.Mesh){o.geometry.dispose();(o.material as T.Material).dispose();}if(o instanceof T.Sprite){o.material.map?.dispose();o.material.dispose();}}
   add('demo_unconfirmed_boundary',new T.CylinderGeometry(.85,.85,.008,48),mat(0x2996a8,.3),-.15);
  }
  for(const o of [this.solids,this.drops]){o.userData={asset_id:o.name,schematic_only:true};o.instanceMatrix.setUsage(T.DynamicDrawUsage);}
 }
 update(s:DemoState){
  const h=demoConfig.liquidHeight*s.liquid.remaining;this.liquid.scale.y=h;this.liquid.position.y=.09+h/2;
  const cake=demoConfig.cakeHeight*s.solid.retained;this.cake.visible=cake>0;this.cake.scale.y=Math.max(cake,.001);this.cake.position.y=.09+cake/2;
  const collected=s.liquid.collected*1.6;this.collector.visible=!this.inSitu&&collected>0;this.collector.scale.y=Math.max(collected,.001);this.collector.position.y=-2.1+collected/2;
  s.particles.forEach((p,i)=>{this.dummy.position.set(p.x,p.y,p.z);this.dummy.scale.setScalar(1);this.dummy.updateMatrix();this.solids.setMatrixAt(i,this.dummy.matrix);});
  this.solids.instanceMatrix.needsUpdate=true;this.solids.computeBoundingSphere();
  // Tracers are non-quantitative flow markers, excluded from visual inventory.
  this.drops.visible=s.time>0&&s.progress<1;
  for(let i=0;i<48;i++){const phase=(s.time*.6+i/48)%1,a=i*2.39996,r=.7*Math.sqrt((i+.5)/48);this.dummy.position.set(r*Math.cos(a),this.inSitu?-.015-phase*.10:.2-phase*2.25,r*Math.sin(a));this.dummy.scale.set(1,2,1);this.dummy.updateMatrix();this.drops.setMatrixAt(i,this.dummy.matrix);}
  this.drops.instanceMatrix.needsUpdate=true;this.drops.computeBoundingSphere();
 }
 render(renderer:T.WebGLRenderer,x:number,w:number,h:number){this.camera.aspect=w/h;this.camera.updateProjectionMatrix();renderer.setViewport(x,0,w,h);renderer.setScissor(x,0,w,h);renderer.render(this.scene,this.camera);}
 dispose(){this.group.traverse(o=>{if(o instanceof T.InstancedMesh)o.dispose();if(o instanceof T.Sprite){o.material.map?.dispose();o.material.dispose();}if(o instanceof T.Mesh){o.geometry.dispose();(Array.isArray(o.material)?o.material:[o.material]).forEach(m=>m.dispose());}});this.group.clear();}
}
