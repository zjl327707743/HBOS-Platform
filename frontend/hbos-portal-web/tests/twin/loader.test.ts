/** Loader and picking lifecycle only; mocked renderer is not a GPU/performance pass. */
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createHash } from 'node:crypto'
import * as T from 'three'
import TwinViewer from '@/components/twin/TwinViewer.vue'
import { createScheduler } from '@/composables/twin/scheduler'
import { makeSession } from '@/composables/twin/session'
import type { TwinManifest } from '@/types/twin'

const loader=vi.hoisted(()=>({parse:vi.fn(),render:vi.fn(),rendererDispose:vi.fn(),controlsDispose:vi.fn()}))
vi.mock('three',async original=>({
  ...await original<typeof import('three')>(),
  WebGLRenderer:class {
    info={memory:{geometries:1,textures:0},render:{triangles:12,calls:1}}
    render=loader.render;dispose=loader.rendererDispose;setSize(){}setPixelRatio(){}
  },
}))
vi.mock('three/examples/jsm/loaders/GLTFLoader.js',()=>({GLTFLoader:class {parseAsync=loader.parse}}))
vi.mock('three/examples/jsm/controls/OrbitControls.js',async()=>{
  const {Vector3}=await import('three')
  return {OrbitControls:class {target=new Vector3();dispose=loader.controlsDispose;update(){}addEventListener(){}removeEventListener(){}}}
})

function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(r=>{resolve=r});return {promise,resolve}}
function object(id:string){const scene=new T.Group(),mesh=new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial());mesh.userData.asset_id=id;scene.add(mesh);return {scene,mesh,dispose:vi.spyOn(mesh.geometry,'dispose')}}
function manifest(id:string,bytes:ArrayBuffer):TwinManifest{return {entry_id:id,label:id,model_sha256:createHash('sha256').update(new Uint8Array(bytes)).digest('hex'),model_size_bytes:bytes.byteLength,model_url:'/api/method/fixture-'+id,mapping_revision:'parts',process_revision:'process'}as TwinManifest}
const bytesA=new Uint8Array([1,2,3]).buffer,bytesB=new Uint8Array([4,5,6]).buffer
let wrapper:VueWrapper|null=null,frames:Map<number,FrameRequestCallback>,serial:number,now:number
beforeEach(()=>{
  vi.resetAllMocks();serial=0;now=100;frames=new Map()
  vi.stubGlobal('crypto',{subtle:{digest:async(_name:string,data:ArrayBuffer)=>Uint8Array.from(createHash('sha256').update(new Uint8Array(data)).digest()).buffer}})
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,arrayBuffer:async()=>url.endsWith('B')?bytesB:bytesA})))
  vi.spyOn(performance,'now').mockImplementation(()=>now)
})
afterEach(()=>{wrapper?.unmount();wrapper=null;vi.restoreAllMocks();vi.unstubAllGlobals()})
async function start(m=manifest('A',bytesA)){
  const scheduler=createScheduler(cb=>{frames.set(++serial,cb);return serial},id=>{frames.delete(id)})
  wrapper=mount(TwinViewer,{props:{manifest:m,process:null,session:makeSession(m,'M606B'),scheduler}})
  await flushPromises()
  return scheduler
}
async function changed(m:TwinManifest){await wrapper!.setProps({manifest:m,session:makeSession(m,'M607B')});await flushPromises()}
function render(){const [id,callback]=[...frames][0]!;frames.delete(id);callback(now)}

it('a late GLTF parse disposes only its own scene after a newer model is shown',async()=>{
  const first=deferred<ReturnType<typeof object>>(),second=deferred<ReturnType<typeof object>>()
  loader.parse.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
  const scheduler=await start();await changed(manifest('B',bytesB))
  const a=object('old-a'),b=object('new-b');second.resolve(b);await flushPromises();render()
  first.resolve(a);await flushPromises()
  expect(a.dispose).toHaveBeenCalledTimes(1);expect(b.dispose).not.toHaveBeenCalled();expect(wrapper!.emitted('ready')).toHaveLength(1)
  wrapper!.unmount();wrapper=null;scheduler.stop();expect(b.dispose).toHaveBeenCalledTimes(1)
})

it('unmount invalidates a pending parse and removes its scheduler listener',async()=>{
  const pending=deferred<ReturnType<typeof object>>();loader.parse.mockReturnValue(pending.promise)
  const scheduler=await start();wrapper!.unmount();wrapper=null
  const late=object('late');pending.resolve(late);await flushPromises()
  expect(late.dispose).toHaveBeenCalledTimes(1);expect(scheduler.listenerCount).toBe(0);expect(loader.rendererDispose).toHaveBeenCalledTimes(1);expect(loader.controlsDispose).toHaveBeenCalledTimes(1);scheduler.stop()
})

it('records first visible time once and denies a tampered model before parsing',async()=>{
  const current=object('current');loader.parse.mockResolvedValue(current)
  const scheduler=await start();now=150;render()
  const first=(wrapper!.emitted('metrics')![0]![0]as {firstVisibleMs:number}).firstVisibleMs
  now=900;(wrapper!.vm as unknown as {resetView:()=>void}).resetView();render()
  expect((wrapper!.emitted('metrics')!.at(-1)![0]as {firstVisibleMs:number}).firstVisibleMs).toBe(first)
  wrapper!.unmount();wrapper=null;scheduler.stop();loader.parse.mockClear()
  const invalid={...manifest('A',bytesA),model_sha256:'incorrect'};const other=await start(invalid)
  expect(loader.parse).not.toHaveBeenCalled();expect(wrapper!.emitted('fatal')).toHaveLength(1);other.stop()
})

it('does not pick during drag, multi-touch or hidden ancestor intersections',async()=>{
  const current=object('visible'),hidden=new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial()),parent=new T.Group()
  hidden.userData.asset_id='hidden';parent.visible=false;parent.add(hidden);current.scene.add(parent);loader.parse.mockResolvedValue(current)
  const scheduler=await start();render()
  vi.spyOn(T.Raycaster.prototype,'intersectObject').mockReturnValue([{object:hidden},{object:current.mesh}]as T.Intersection[])
  const canvas=wrapper!.get('canvas').element
  vi.spyOn(canvas,'getBoundingClientRect').mockReturnValue({left:0,top:0,width:600,height:610}as DOMRect)
  const pointer=(type:string,id:number,x:number,y:number)=>{const event=new Event(type);Object.assign(event,{pointerId:id,clientX:x,clientY:y,pointerType:'touch',button:0});canvas.dispatchEvent(event)}
  pointer('pointerdown',1,10,10);pointer('pointermove',1,30,10);pointer('pointerup',1,30,10);expect(wrapper!.emitted('select')).toBeUndefined()
  pointer('pointerdown',1,10,10);pointer('pointerdown',2,12,12);pointer('pointerup',2,12,12);pointer('pointerup',1,10,10);expect(wrapper!.emitted('select')).toBeUndefined()
  pointer('pointerdown',1,10,10);pointer('pointerup',1,10,10)
  expect(wrapper!.emitted('select')!.at(-1)).toEqual(['visible'])
  await wrapper!.get('canvas').trigger('keydown',{key:'Escape'});expect(wrapper!.emitted('select')!.at(-1)).toEqual([null]);scheduler.stop()
})

it('clears the model on context loss and revalidates it on restoration',async()=>{
  const original=object('old'),replacement=object('recovered');loader.parse.mockResolvedValueOnce(original).mockResolvedValueOnce(replacement)
  const scheduler=await start();render();const canvas=wrapper!.get('canvas').element
  const lost=new Event('webglcontextlost',{cancelable:true});canvas.dispatchEvent(lost)
  expect(lost.defaultPrevented).toBe(true);expect(original.dispose).toHaveBeenCalledTimes(1)
  expect(wrapper!.emitted('contextLost')).toHaveLength(1)
  canvas.dispatchEvent(new Event('webglcontextrestored'));await flushPromises();render()
  expect(fetch).toHaveBeenCalledTimes(2);expect(replacement.dispose).not.toHaveBeenCalled();expect(wrapper!.emitted('ready')).toHaveLength(2);scheduler.stop()
})
