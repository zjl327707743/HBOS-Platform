import assert from 'node:assert/strict'
import { probe } from '../qa/structure.mjs'
import {evaluate,navigate,resize,shot,close,send} from './cdp.mjs'
const origin = 'http://127.0.0.1:18650'
const base = '/hbos/knowledge'
const cases = {P01:'',P02:'/catalog',P03:'/favorites',P04:'/history',P04b:'/history?tab=feedback',P05:'/document/DOC_SYNTHETIC_0',P06:'/maintenance',P07:'/maintenance/upload',P08:'/maintenance/versions',P09:'/maintenance/feedback',D01:'/maintenance',D02:''}
await send('Page.addScriptToEvaluateOnNewDocument', { source: "if (location.origin==='http://127.0.0.1:18650') sessionStorage.clear()" })
const pause=(ms=160)=>new Promise(resolve=>setTimeout(resolve,ms))
async function until(js,ms=3500) {
 const end=Date.now()+ms
 while(Date.now()<end) { if(await evaluate(js)) return; if (js.includes('data-pdf-rendered')) await send('Page.captureScreenshot',{format:'jpeg',quality:20}); await pause(80) }
 throw new Error('未出现 '+js)
}
const click=(text,where='body')=>evaluate(`(()=>{const root=document.querySelector(${JSON.stringify(where)}); const n=[...root.querySelectorAll('button,a')].find(n=>n.getClientRects().length && n.textContent.trim().replace(/\s+/g,'')===${JSON.stringify(text.replace(/\s+/g,''))}); if(!n||n.disabled) throw Error(${JSON.stringify('控件不可操作 '+text)}); n.click()})()`)
const route=async(path)=>{await navigate('about:blank');await navigate(origin+base+path)}
async function key(key,code=key){
 const virtual={Escape:27,Enter:13,Space:32,Tab:9,ArrowDown:40,Home:36,End:35}[code]
 const data={key,code,windowsVirtualKeyCode:virtual,nativeVirtualKeyCode:virtual}
 await send('Input.dispatchKeyEvent',{type:[' ','Enter'].includes(key)?'keyDown':'rawKeyDown',...data,...(key===' '?{text:' ',unmodifiedText:' '}:key==='Enter'?{text:'\r',unmodifiedText:'\r'}:{})})
 await send('Input.dispatchKeyEvent',{type:'keyUp',...data})
}
async function group(label,fn){try{await fn();console.log('PASS',label)}catch(error){console.log('FAIL',label,error.message);process.exitCode=1}}
const viewports=[[1440,1000],[1165,757],[390,844],[320,620],[1919,897],[320,500],[703,897],[1165,400],[1000,757],[901,757],[900,757],[1101,757],[1100,757],[1021,757],[1020,757],[1180,757]]
const full=new Set(['1440x1000','1165x757','390x844','320x620','1919x897','320x500'])
for(const [w,h] of viewports){
 await resize(w,h)
 for(const [id,path] of Object.entries(cases)){
  const size=w+'x'+h
  if(!full.has(size) && !['P01','P05','P07','D02'].includes(id)) continue
  await group(size+' '+id,async()=>{
    await route(path)
    await until("document.querySelector('.kb-main h1')")
    if(id==='D01'||id==='D02'){
      if (id === 'D01') {
        await until("document.querySelector('.v17-batch button')")
        await click('打开批量预演', 'main')
      } else {
        await until("document.querySelector('.kb-connect-page-action:not(:disabled)')")
        await evaluate("document.querySelector('.kb-connect-page-action').click()")
      }
      await until("document.querySelector('.ant-drawer-open')")
      await pause(250)
    }
    if(id==='P05') await until("document.querySelector('[data-pdf-rendered]')",5000)
    if (id==='P09') await until("document.querySelector('.kb-staff-feedback-item')")
    if (id==='P09' && w>767) await evaluate('('+probe.toString()+')()')
    const result=await evaluate(`({ x: document.querySelector('main').getBoundingClientRect().x, y:document.querySelector('main').getBoundingClientRect().y,
      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth, heading:document.querySelector('h1').textContent,
      alerts:[...document.querySelectorAll('[role=alert]')].filter(n=>n.getClientRects().length).map(n=>n.textContent.trim()),
      dialog:[...document.querySelectorAll('.ant-drawer-open .ant-drawer-title')].map(n=>n.textContent) })`)
    if (full.has(size)) await shot(`outputs/结构返工/screens/vue-${id}-${size}.png`)
    console.log('GEOMETRY',size,id,JSON.stringify(result))
    assert.ok(result.overflow<=1,'整页横向溢出 '+result.overflow)
    assert.equal(result.y,w<=767?88:100)
  })
 }
}
await resize(390,844)
await group('手机抽屉遮罩、Esc、焦点、链接与返回',async()=>{
 await route('')
 const trigger='.kb-mobile-trigger'
 await until(`document.querySelector('${trigger}')`)
 await evaluate(`document.querySelector('${trigger}').focus();document.querySelector('${trigger}').click()`)
 await until("document.querySelector('dialog[open] .kb-mobile-close') === document.activeElement")
 await key('Escape')
 await until("!document.querySelector('dialog[open]') && document.activeElement.matches('.kb-mobile-trigger')")
 await evaluate("document.querySelector('.kb-mobile-trigger').click()")
 await send('Input.dispatchMouseEvent',{type:'mousePressed',x:365,y:210,button:'left',clickCount:1})
 await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:365,y:210,button:'left',clickCount:1})
 await until("!document.querySelector('dialog[open]')")
 await evaluate("document.querySelector('.kb-mobile-trigger').click()")
 await shot('outputs/结构返工/screens/vue-shell-menu-390x844.png')
 await click('资料目录','dialog')
 await until("location.pathname.endsWith('/catalog') && !document.querySelector('dialog[open]')")
 await evaluate("history.back()")
 await until("location.pathname==='/hbos/knowledge'")
 await evaluate("history.forward()")
 await until("location.pathname.endsWith('/catalog')")
})
await group('P07 原生详情 Enter、Space、marker 和焦点',async()=>{
 await route('/maintenance/upload')
 const selector='.v17-version-lookup summary'
 await until(`document.querySelector('${selector}')`)
 await evaluate(`document.querySelector('${selector}').focus()`)
 await key('Enter')
 await until("document.querySelector('.v17-version-lookup').open")
 assert.equal(await evaluate(`getComputedStyle(document.querySelector('${selector}')).listStyleType`),'none')
 await shot('outputs/结构返工/screens/vue-P07-lookup-390x844.png')
 await key(' ','Space')
 await until("!document.querySelector('.v17-version-lookup').open && document.activeElement.matches('.v17-version-lookup summary')")
})
await group('普通选择器 Space、ArrowDown、Home、End、Enter、Esc、Tab',async()=>{
 await route('')
 await until("document.querySelector('#knowledge-space')")
 await evaluate("document.querySelector('#knowledge-space').focus()")
 await key(' ','Space');await until("document.querySelector('#knowledge-space').getAttribute('aria-expanded')==='true'")
 await key('End');await key('Home');await key('ArrowDown');await key('Enter')
 await until("document.querySelector('#knowledge-space').textContent.includes('质量管理部')")
 await key('ArrowDown');await key('Escape')
 await until("document.querySelector('#knowledge-space')===document.activeElement && !document.querySelector('[role=listbox]')")
 await key('ArrowDown');await key('Tab')
 await until("document.activeElement.id==='knowledge-query' && !document.querySelector('[role=listbox]')")
})
await group('搜索选择器 Chrome 合成组合输入',async()=>{
 await route('/maintenance/upload')
 await until("document.querySelector('#upload-replacement')")
 await evaluate("document.querySelector('#upload-replacement').focus()")
 await send('Input.imeSetComposition',{text:'培养箱',selectionStart:3,selectionEnd:3})
 assert.equal(await evaluate("document.querySelector('#upload-replacement').getAttribute('aria-expanded')"),'false')
 await send('Input.insertText',{text:'培养箱'})
 await until("document.querySelector('#upload-replacement').getAttribute('aria-expanded')==='true'")
 await until("[...document.querySelectorAll('[role=option]')].some(x=>x.textContent.includes('培养箱'))")
 await key('Escape')
 assert.equal(await evaluate("document.activeElement.id"),'upload-replacement')
})
await group('Reader 权限与未知维护权限',async()=>{
 await route('/maintenance?state=reader')
 await until("document.body.innerText.includes('当前账号没有知识维护权限')")
 assert.equal(await evaluate("document.querySelector('.kb-maintenance-nav')"),null)
 await route('/maintenance?state=timeout')
 await until("document.body.innerText.includes('维护权限状态暂时无法确认')")
})
await group('来源抽屉、真实 PDF 渲染与目录返回',async()=>{
 await route('/catalog')
 await until("document.querySelector('.catalog-row button')")
 await evaluate("document.querySelector('.catalog-row .kb-doc-main').click()")
 await until("location.pathname.includes('/document/') && document.querySelector('[data-pdf-rendered]')",6000)
 await evaluate("document.querySelector('[data-reader-back]').click()")
 await until("location.pathname.endsWith('/catalog') && document.querySelector('.catalog-row button')")
})
close()
