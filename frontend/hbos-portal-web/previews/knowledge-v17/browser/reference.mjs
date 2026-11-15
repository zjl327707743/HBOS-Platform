import {evaluate,navigate,resize,shot,prototype,close} from './cdp.mjs'
const base='#/hbos/knowledge'
const routes={P01:'',P02:'/catalog',P03:'/favorites',P04:'/history',P04b:'/history?tab=feedback',P05:'/document/DOC_DEMO_001',P06:'/maintenance',P07:'/maintenance/upload',P08:'/maintenance/versions',P09:'/maintenance/feedback',D01:'/maintenance',D02:''}
for (const [w,h] of [[1440,1000],[1165,757],[390,844],[320,620],[1919,897],[320,500]]) {
 await resize(w,h)
 for(const [key,route] of Object.entries(routes)){
  await navigate("about:blank"); await navigate(prototype+base+route)
  if(key==='D01'||key==='D02') console.log(key,await evaluate(`[...document.querySelectorAll('[data-act]')].filter(x=>x.textContent.includes('${key==='D01'?'批量':'连接个人助手'}')).map(x=>x.dataset.act)`))
  if(key==='D01') await evaluate("Array.from(document.querySelectorAll('main button')).find(x=>x.textContent.includes('受控')||x.textContent.includes('批量'))?.click()")
  if(key==='D02') await evaluate("document.querySelector('main [data-act=connect]')?.click()")
  console.log(w,h,key,await evaluate("({heading:document.querySelector('h1')?.innerText,modal:document.querySelector('.modal h2')?.innerText,main:document.querySelector('main')?.getBoundingClientRect().y})"))
  if(key==='D01'||key==='D02') await new Promise(resolve=>setTimeout(resolve,450))
  await shot(`outputs/结构返工/screens/reference-${key}-${w}x${h}.png`)
 }
}
close()
