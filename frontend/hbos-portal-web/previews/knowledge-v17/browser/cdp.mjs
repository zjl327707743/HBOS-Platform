import fs from 'node:fs/promises'
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'
const port = process.env.HBOS_CHROME_CDP_PORT
if (!/^\d+$/.test(port || '')) throw new Error('Set HBOS_CHROME_CDP_PORT to the isolated Chrome debugging port.')
const targets = await (await fetch('http://127.0.0.1:'+port+'/json/list')).json()
const target = targets.find(item => item.type === 'page')
export const websocket = new WebSocket(target.webSocketDebuggerUrl)
const ws = websocket
await new Promise(resolve=>ws.addEventListener('open',resolve,{once:true}))
let id=0
const waiting=new Map()
ws.addEventListener('message',e=>{const r=JSON.parse(e.data);if(waiting.has(r.id)){const [resolve,reject]=waiting.get(r.id);waiting.delete(r.id);r.error?reject(r.error):resolve(r.result)}})
export const send=(method,params={})=>new Promise((resolve,reject)=>{waiting.set(++id,[resolve,reject]);ws.send(JSON.stringify({id,method,params}))})
export async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
export async function navigate(url){await send('Page.navigate',{url});await new Promise(r=>setTimeout(r,220));await evaluate('document.fonts.ready.then(()=>true)')}
export const resize=(width,height)=>send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false})
export async function shot(path) {
  const drawerGeometry = `[...document.querySelectorAll('.ant-drawer-open .ant-drawer-content-wrapper')]
      .every(drawer => {
        const rect = drawer.getBoundingClientRect();
        return rect.width > 0 && rect.left >= -1 && rect.right <= innerWidth + 1 &&
          !drawer.getAnimations().some(animation => animation.playState === 'running');
      })`
  const deadline = Date.now() + 3000
  let frames = 0
  while (frames < 2 && Date.now() < deadline) {
    await send('Page.captureScreenshot', {format:'jpeg', quality:20})
    frames = await evaluate(drawerGeometry) ? frames + 1 : 0
    if (frames < 2) await new Promise(resolve => setTimeout(resolve, 60))
  }
  if (frames < 2) throw new Error(`Drawer did not settle before capture: ${path}`)
  const {data} = await send('Page.captureScreenshot', {format:'png'})
  await fs.writeFile(path, Buffer.from(data, 'base64'))
}
export const prototype = pathToFileURL(resolve(process.env.HBOS_FROZEN_PROTOTYPE || 'work/package/prototype.html')).href
export function close(){ws.close()}
