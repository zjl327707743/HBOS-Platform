import assert from 'node:assert/strict'
import {evaluate,navigate,shot,close} from './cdp.mjs'
await navigate('http://127.0.0.1:18650/hbos/knowledge/maintenance/upload')
await new Promise(r=>setTimeout(r,650))
const result=await evaluate("({dpr:devicePixelRatio, cssWidth:innerWidth, screenWidth:screen.width, overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth, heading:document.querySelector('h1')?.textContent})")
console.log(result)
assert.equal(result.dpr,2)
assert.ok(result.overflow<=1)
await shot('outputs/结构返工/screens/vue-native-zoom-200-P07.png')
close()
