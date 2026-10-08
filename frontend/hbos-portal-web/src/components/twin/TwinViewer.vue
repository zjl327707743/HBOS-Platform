<template>
  <section ref="viewport" class="twin-viewport" :aria-label="`${manifest.label} 受保护三维工作区`">
    <canvas ref="canvas" tabindex="0" :aria-label="`${manifest.label} 三维模型。拖动旋转，双指缩放，方向键旋转，F 聚焦，R 复位，Esc 清空。`" @keydown="onKeydown" />
    <div class="viewport-label"><span class="source-dot"></span>{{ session.mode === 'browse' ? '设备浏览 · 无现场数据' : '原理演示 / 非现场状态 / 非操作规程' }}</div>
    <div class="viewer-tools" role="toolbar" aria-label="三维查看工具">
      <button title="聚焦所选 (F)" aria-label="聚焦所选部件" :disabled="!hasSelection" @click="focusSelected">◎</button>
      <button title="隔离所选" aria-label="隔离所选部件" :aria-pressed="isolated" :disabled="!hasSelection" @click="toggleIsolate">◫</button>
      <button title="隐藏所选" aria-label="隐藏所选部件" :disabled="!hasSelection" @click="hideSelected">⊖</button>
      <button title="线框" aria-label="切换线框" :aria-pressed="wireframe" @click="toggleWireframe">▧</button>
      <button title="恢复全部" aria-label="恢复全部显隐和材质" @click="restoreAll">↺</button>
      <button title="复位镜头 (R)" aria-label="复位镜头" @click="resetView">⌂</button>
      <button title="全屏 / Esc 退出" aria-label="切换全屏" @click="toggleFullscreen">⛶</button>
    </div>
    <div v-if="loading || error" class="viewer-state" role="status" aria-live="polite">
      <span class="state-mark">{{ error ? '!' : '◌' }}</span>
      <strong>{{ error ? '模型暂时不可用' : '正在校验并载入设备模型' }}</strong>
      <p>{{ error || '仅加载当前会话允许的私有制品' }}</p>
      <button v-if="error && !fatal" @click="loadModel">重试</button>
    </div>
    <div v-if="isolated" class="view-chip">隔离查看 <button @click="restoreAll">恢复全部</button></div>
    <div class="viewer-bottom"><span>拖动旋转 · 双指 / 滚轮缩放 · 点击选择</span><span>展示拟合 · 非工程测量</span></div>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as T from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { DemoSession, ProcessBundle, TwinManifest, ViewerMetrics } from '@/types/twin'
import type { TwinScheduler } from '@/composables/twin/scheduler'
import { DisplayState, disposeTree, effectiveVisible } from './resources'
import { createProduction, type ProductionRuntime } from './process/runtime'

const props = defineProps<{ manifest:TwinManifest; process:ProcessBundle | null; session:DemoSession; scheduler:TwinScheduler }>()
const emit = defineEmits<{ select:[assetId:string|null]; ready:[]; fatal:[message:string]; error:[message:string]; manual:[]; metrics:[value:ViewerMetrics]; processError:[message:string]; restore:[] }>()
const canvas=ref<HTMLCanvasElement|null>(null), viewport=ref<HTMLElement|null>(null)
const loading=ref(true), error=ref(''), fatal=ref(false), hasSelection=ref(false), isolated=ref(false), wireframe=ref(false)
let renderer:T.WebGLRenderer|null=null, scene:T.Scene|null=null, camera:T.PerspectiveCamera|null=null, controls:OrbitControls|null=null
let root:T.Object3D|null=null, display:DisplayState|null=null, processRuntime:ProductionRuntime|null=null
let observer:ResizeObserver|null=null, abort:AbortController|null=null, generation=0, disposed=false, dirty=true, userCamera=false
let unsubscribe:(()=>void)|null=null, parseMs=0, downloadMs=0, started=0, firstVisibleMs:number|null=null
const nodes=new Map<string,T.Object3D>(), pointers=new Map<number,{x:number;y:number}>()
let gestureMoved=false
const raycaster=new T.Raycaster(), pointer=new T.Vector2()
const original={position:new T.Vector3(),target:new T.Vector3(),near:.01,far:1000,fov:38}
const invalidate=()=>{dirty=true;props.scheduler.invalidate()}
function selectedNodes(){return display ? [...display.selected] : []}
function syncTools(){hasSelection.value=Boolean(display?.selected.size);isolated.value=Boolean(display?.isolated);wireframe.value=Boolean(display?.wireframe)}
function selectIds(ids:string[], notify=false){display?.setSelection(ids.map(id=>nodes.get(id)).filter((n):n is T.Object3D=>!!n));syncTools();invalidate();if(notify)emit('select',ids[0]||null)}
function clearSelection(){selectIds([],true)}
function frameObject(object:T.Object3D,padding=1.2){
  if(!camera||!controls)return
  object.updateWorldMatrix(true,true)
  const box=new T.Box3().setFromObject(object)
  if(box.isEmpty())return
  const sphere=box.getBoundingSphere(new T.Sphere()), radius=Math.max(sphere.radius,.01)
  const halfVertical=T.MathUtils.degToRad(camera.fov/2), halfHorizontal=Math.atan(Math.tan(halfVertical)*camera.aspect)
  const distance=radius/Math.sin(Math.min(halfVertical,halfHorizontal))*padding
  const direction=new T.Vector3(.85,.52,1).normalize()
  camera.position.copy(sphere.center).addScaledVector(direction,distance)
  controls.target.copy(sphere.center);camera.near=Math.max(distance/2000,.001);camera.far=Math.max(distance*30,100);camera.updateProjectionMatrix();controls.update();invalidate()
}
function resetView(){if(!camera||!controls)return;camera.position.copy(original.position);controls.target.copy(original.target);camera.near=original.near;camera.far=original.far;camera.fov=original.fov;camera.updateProjectionMatrix();controls.update();invalidate()}
function focusIds(ids:string[]){
  if(!scene)return
  const box=new T.Box3()
  for(const id of ids){const node=nodes.get(id);if(node)box.union(new T.Box3().setFromObject(node))}
  if(box.isEmpty()||!camera||!controls)return
  const size=box.getSize(new T.Vector3()),center=box.getCenter(new T.Vector3()),radius=Math.max(size.length()/2,.03)
  const half=Math.min(T.MathUtils.degToRad(camera.fov/2),Math.atan(Math.tan(T.MathUtils.degToRad(camera.fov/2))*camera.aspect))
  camera.position.copy(center).addScaledVector(new T.Vector3(.6,.3,1).normalize(),radius/Math.sin(half)*1.4)
  camera.near=Math.max(radius/2000,.001);camera.far=Math.max(radius*500,100);camera.updateProjectionMatrix();controls.target.copy(center);controls.update();invalidate()
}
function focusSelected(){focusIds(selectedNodes().map(n=>String(n.userData.asset_id)))}
function toggleIsolate(){if(!display||!hasSelection.value)return;display.isolated=!display.isolated;display.apply();syncTools();invalidate()}
function hideSelected(){if(!display)return;for(const n of display.selected)display.hidden.add(n);display.selected.clear();display.apply();syncTools();emit('select',null);invalidate()}
function toggleWireframe(){if(!display)return;display.wireframe=!display.wireframe;display.apply();syncTools();invalidate()}
function restoreAll(){exitProcess();emit('restore');display?.reset();syncTools();emit('select',null);invalidate()}
async function toggleFullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await viewport.value?.requestFullscreen()}catch{error.value='浏览器暂不支持全屏，可继续使用当前视图。'}}
function assetNode(object:T.Object3D){let n:T.Object3D|null=object;while(n&&n!==root?.parent){if(typeof n.userData.asset_id==='string'&&!n.userData.schematic_only)return n;n=n.parent}return null}
function pointerDown(event:PointerEvent){if(event.pointerType==='mouse'&&event.button!==0)return;if(!pointers.size)gestureMoved=false;pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});if(pointers.size>1)gestureMoved=true}
function pointerMove(event:PointerEvent){const start=pointers.get(event.pointerId);if(start&&Math.hypot(event.clientX-start.x,event.clientY-start.y)>6)gestureMoved=true}
function pointerCancel(event:PointerEvent){pointers.delete(event.pointerId);gestureMoved=true}
function pointerUp(event:PointerEvent){
  const start=pointers.get(event.pointerId),wasMultiple=pointers.size>1;pointers.delete(event.pointerId)
  if(!start||gestureMoved||wasMultiple||pointers.size||!canvas.value||!camera||!root||loading.value||error.value)return
  const r=canvas.value.getBoundingClientRect();pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(pointer,camera)
  const hit=raycaster.intersectObject(root,true).find(h=>effectiveVisible(h.object))
  const node=hit?assetNode(hit.object):null
  selectIds(node?[String(node.userData.asset_id)]:[],true)
}
function manual(){userCamera=true;emit('manual')}
function onKeydown(event:KeyboardEvent){
  if(!camera||!controls)return
  const key=event.key.toLowerCase()
  if(!['r','f','escape','+','=','-','arrowleft','arrowright','arrowup','arrowdown'].includes(key))return
  event.preventDefault();manual()
  if(key==='r')resetView();if(key==='f')focusSelected();if(key==='escape')clearSelection()
  if(['+','=','-'].includes(key)){camera.position.sub(controls.target).multiplyScalar(key==='-'?1.12:.89).add(controls.target);controls.update();invalidate()}
  if(key.startsWith('arrow')){const offset=camera.position.clone().sub(controls.target),s=new T.Spherical().setFromVector3(offset);s.theta+=key==='arrowleft'?.12:key==='arrowright'?-.12:0;s.phi=T.MathUtils.clamp(s.phi+(key==='arrowup'?-.12:key==='arrowdown'?.12:0),.08,Math.PI-.08);camera.position.copy(controls.target).add(new T.Vector3().setFromSpherical(s));controls.update();invalidate()}
}
function exitProcess(){
  if(!processRuntime)return
  display?.restoreMaterials();processRuntime.dispose();processRuntime=null;display?.captureMaterials();display?.apply();invalidate()
}
function enterProcess(){
  exitProcess()
  if(!root||!props.process||props.session.mode!=='production')return
  const config=props.process.bindings[props.session.equipmentId]
  if(!config){emit('processError','当前设备尚无兼容的示教绑定。');return}
  display?.reset();display?.restoreMaterials()
  try{processRuntime=createProduction(root,config);display?.captureMaterials();processRuntime.update(props.session.time);syncTools();if(props.session.followCamera)focusIds(config.ids);invalidate()}
  catch{emit('processError','示教目标或版本不兼容，静态模型仍可浏览。')}
}
function cleanupModel(){
  abort?.abort();abort=null;exitProcess();display?.dispose();display=null
  if(root)disposeTree(root);root=null;nodes.clear();hasSelection.value=false;isolated.value=false;wireframe.value=false
}
async function loadModel(){
  const token=++generation;cleanupModel();loading.value=true;error.value='';fatal.value=false;started=performance.now();firstVisibleMs=null
  const controller=new AbortController();abort=controller
  try{
    const response=await fetch(props.manifest.model_url,{credentials:'same-origin',cache:'no-store',signal:controller.signal})
    if(!response.ok){if([401,403,409].includes(response.status)){fatal.value=true;throw new Error('设备权限、会话或模型完整性已失效。')}throw new Error('受保护模型暂时不可用，请重试。')}
    const data=await response.arrayBuffer();downloadMs=performance.now()-started
    const digest=await crypto.subtle.digest('SHA-256',data)
    const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('')
    if(hash!==props.manifest.model_sha256||data.byteLength!==props.manifest.model_size_bytes){fatal.value=true;throw new Error('模型完整性校验失败，已停止展示。')}
    const parsing=performance.now(),gltf=await new GLTFLoader().parseAsync(data,'');parseMs=performance.now()-parsing
    if(disposed||token!==generation||!scene){disposeTree(gltf.scene);return}
    root=gltf.scene;scene.add(root);display=new DisplayState(root)
    root.traverse(n=>{if(typeof n.userData.asset_id==='string')nodes.set(n.userData.asset_id,n)})
    userCamera=false;frameObject(root)
    if(camera&&controls){original.position.copy(camera.position);original.target.copy(controls.target);original.near=camera.near;original.far=camera.far;original.fov=camera.fov}
    loading.value=false;enterProcess();emit('ready');invalidate()
  }catch(reason){
    if(disposed||token!==generation||controller.signal.aborted)return
    loading.value=false;error.value=reason instanceof Error?reason.message:'模型暂时不可用。'
    if(fatal.value){cleanupModel();emit('fatal',error.value)}else emit('error',error.value)
  }
}
function resize(){if(!canvas.value||!renderer||!camera)return;const w=Math.max(canvas.value.clientWidth,1),h=Math.max(canvas.value.clientHeight,1);renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();if(root&&!userCamera&&props.session.mode==='browse'){frameObject(root);if(controls){original.position.copy(camera.position);original.target.copy(controls.target);original.near=camera.near;original.far=camera.far}}invalidate()}
function lost(event:Event){event.preventDefault();generation++;cleanupModel();error.value='图形上下文已丢失。恢复后将重新验证并载入。';loading.value=false;emit('error',error.value)}
function recovered(){if(disposed)return;initializeRenderer();void loadModel()}
function releaseRenderer(){controls?.removeEventListener('change',invalidate);controls?.removeEventListener('start',manual);controls?.dispose();controls=null;renderer?.dispose();renderer=null;scene=null;camera=null}
function initializeRenderer(){
  releaseRenderer();if(!canvas.value)return
  renderer=new T.WebGLRenderer({canvas:canvas.value,antialias:true,powerPreference:'high-performance'});renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;renderer.localClippingEnabled=true
  scene=new T.Scene();scene.background=new T.Color('#e9eff5')
  scene.add(new T.HemisphereLight('#f3f7ff','#6e7f91',2.8));const light=new T.DirectionalLight('#ffffff',3.8);light.position.set(6,10,8);scene.add(light);const fill=new T.DirectionalLight('#b3c7ef',2);fill.position.set(-6,4,-4);scene.add(fill)
  camera=new T.PerspectiveCamera(38,1,.01,1000);controls=new OrbitControls(camera,canvas.value);controls.enableDamping=false;controls.screenSpacePanning=true;controls.addEventListener('change',invalidate);controls.addEventListener('start',manual);resize()
}
watch(()=>[props.session.mode,props.session.equipmentId,props.process],enterProcess)
watch(()=>props.session.followCamera,follow=>{if(follow&&props.process){const c=props.process.bindings[props.session.equipmentId];if(c)focusIds(c.ids)}})
watch(()=>props.manifest.model_sha256,()=>{void loadModel()})
onMounted(()=>{
  initializeRenderer();const c=canvas.value!;c.addEventListener('pointerdown',pointerDown);c.addEventListener('pointermove',pointerMove);c.addEventListener('pointerup',pointerUp);c.addEventListener('pointercancel',pointerCancel);c.addEventListener('webglcontextlost',lost);c.addEventListener('webglcontextrestored',recovered)
  observer=new ResizeObserver(resize);observer.observe(c)
  unsubscribe=props.scheduler.subscribe(()=>{if(disposed||!renderer||!scene||!camera||error.value)return false;if(processRuntime){processRuntime.update(props.session.time);dirty=true}if(dirty){renderer.render(scene,camera);dirty=false;if(root&&!loading.value&&firstVisibleMs===null)firstVisibleMs=performance.now()-started;const info=renderer.info;if(firstVisibleMs!==null)emit('metrics',{geometries:info.memory.geometries,textures:info.memory.textures,triangles:info.render.triangles,calls:info.render.calls,downloadMs,parseMs,firstVisibleMs,ownedMaterials:display?.owned.size||0})}return false})
  void loadModel()
})
onBeforeUnmount(()=>{
  disposed=true;generation++;unsubscribe?.();observer?.disconnect();pointers.clear()
  const c=canvas.value;if(c){c.removeEventListener('pointerdown',pointerDown);c.removeEventListener('pointermove',pointerMove);c.removeEventListener('pointerup',pointerUp);c.removeEventListener('pointercancel',pointerCancel);c.removeEventListener('webglcontextlost',lost);c.removeEventListener('webglcontextrestored',recovered)}
  cleanupModel();releaseRenderer()
})
defineExpose({selectIds,focusIds,focusSelected,toggleIsolate,hideSelected,restoreAll,resetView})
</script>

<style scoped>
.twin-viewport{position:relative;min-width:0;height:610px;overflow:hidden;border-radius:18px;background:#e9eff5;border:1px solid #dce5ee}canvas{width:100%;height:100%;display:block;touch-action:none;cursor:grab}canvas:active{cursor:grabbing}canvas:focus-visible{outline:3px solid #655cf0;outline-offset:-4px}.viewport-label{position:absolute;top:18px;left:18px;max-width:calc(100% - 80px);padding:8px 11px;background:#fffffff0;border-radius:9px;color:#526276;font-size:12px;pointer-events:none}.source-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#9c7b3c;margin-right:8px}.viewer-tools{position:absolute;right:14px;top:16px;display:grid;gap:6px}.viewer-tools button,.view-chip button{border:1px solid #d7e1eb;background:#ffffffed;color:#415875;border-radius:10px;min-width:40px;min-height:40px;font-size:21px;cursor:pointer}.viewer-tools button[aria-pressed=true]{background:#6158d8;color:white}.viewer-tools button:disabled{opacity:.35;cursor:default}.viewer-tools button:focus-visible,.view-chip button:focus-visible{outline:3px solid #655cf0;outline-offset:2px}.viewer-state{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#edf3f9ed;text-align:center;padding:30px;gap:12px;color:#38526f}.viewer-state strong{font-size:18px}.viewer-state p{max-width:360px;margin:0;color:#6e7e91}.viewer-state button{padding:10px 24px;border:1px solid #c7d6e6;border-radius:10px;background:white;cursor:pointer}.state-mark{font-size:38px;color:#736bc1}.viewer-bottom{position:absolute;left:18px;right:18px;bottom:14px;display:flex;justify-content:space-between;gap:10px;color:#66768a;font-size:12px;pointer-events:none}.view-chip{position:absolute;bottom:52px;left:18px;padding:6px 12px;background:white;border-radius:10px;font-size:13px}.view-chip button{font-size:12px;border:0}.twin-viewport:fullscreen{height:100vh;border-radius:0}@media(max-width:700px){.twin-viewport{height:520px}.viewer-bottom{font-size:11px;flex-direction:column}.viewport-label{font-size:11px}.viewer-tools button{min-width:44px;min-height:44px}}
</style>
