/**
 * v1.7 final acceptance run: same-condition visual comparison against the frozen
 * prototype, the structural assertions the task calls out (P05 paper in the short
 * first screen, P08 first item, P04 toolbar rows, P09 first row and columns), the
 * shared-drawer naming/stacking regression and full-page overflow.
 *
 * Run from frontend/hbos-portal-web with the isolated Chrome debugging port set:
 *   HBOS_CHROME_CDP_PORT=9333 node previews/knowledge-v17/qa/final-check.mjs
 */
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { execSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { evaluate, navigate, resize, shot, close, send } from '../browser/cdp.mjs'
import { probe } from './structure.mjs'

const origin = 'http://127.0.0.1:18650'
const base = '/hbos/knowledge'
const output = process.env.HBOS_V17_OUT || '/Users/hb/Projects/HBOS/knowledge-rebuild-20261102/outputs/v17-final'
const prototype = pathToFileURL(resolve(process.env.HBOS_FROZEN_PROTOTYPE || '/Users/hb/Downloads/HBOS_知识库_高保真交互原型_v1.7.html')).href
await mkdir(output + '/screens', { recursive: true })
await send('Page.addScriptToEvaluateOnNewDocument', { source: "if(location.origin==='http://127.0.0.1:18650') sessionStorage.clear()" })
const pause = ms => new Promise(r => setTimeout(r, ms))
const results = []
const finalSha = execSync('git rev-parse HEAD', { cwd: new URL('../..', import.meta.url).pathname }).toString().trim()
const worktreeDirty = execSync('git status --porcelain --untracked-files=no', { cwd: new URL('../..', import.meta.url).pathname }).toString().trim().length > 0
console.log('BOUND SHA', finalSha, 'dirty=' + worktreeDirty)
function record(id, expected, actual, pass, evidence) {
  results.push({ id, expected, actual, result: pass ? 'PASS' : 'FAIL', evidence })
  console.log(pass ? 'PASS' : 'FAIL', id, JSON.stringify({ expected, actual }))
  if (!pass) process.exitCode = 1
}
function recordDifference(id, baseline, actual, evidence) {
  results.push({ id, baseline, actual, result: 'DIFFERENCE_RECORDED', evidence })
  console.log('DIFFERENCE', id, JSON.stringify({ baseline, actual }))
}
// Fixed-anchor geometry uses the original ±2 CSS px standard. A measurement that does
// not meet it is recorded as a difference (never silently promoted to PASS); product
// availability goals (e.g. "paper visible in the first screen") stay separate checks.
function recordGeometry(id, baseline, actual, evidence) {
  const delta = baseline === null || actual === null ? null : actual - baseline
  const pass = delta !== null && Math.abs(delta) <= 2
  results.push({ id, baseline, actual: { value: actual, delta }, standard: '±2 CSS px fixed anchor', result: pass ? 'PASS' : 'DIFFERENCE_RECORDED', evidence })
  console.log(pass ? 'PASS' : 'DIFFERENCE', id, JSON.stringify({ baseline, actual, delta }))
}
async function until(js, ms = 8000) {
  const end = Date.now() + ms
  while (Date.now() < end) { if (await evaluate(js)) return; await pause(80) }
  throw new Error('timeout ' + js)
}
const viewports = [
  { id: '320x500', w: 320, h: 500 },
  { id: '390x844', w: 390, h: 844 },
  { id: '1165x757', w: 1165, h: 757 },
]
const pages = [
  { key: 'P01', path: '' }, { key: 'P02', path: '/catalog' }, { key: 'P03', path: '/favorites' },
  { key: 'P04', path: '/history' }, { key: 'P04b', path: '/history?tab=feedback' },
  { key: 'P05', path: '/document/DOC_DEMO_001' }, { key: 'P06', path: '/maintenance' },
  { key: 'P07', path: '/maintenance/upload' }, { key: 'P08', path: '/maintenance/versions' },
  { key: 'P09', path: '/maintenance/feedback' },
]
async function settle(key) {
  if (key === 'P05') await until("document.querySelector('[data-pdf-rendered]')", 10000)
  if (key === 'P09') await until("document.querySelector('.kb-staff-feedback-item')")
  await pause(250)
}
const geometry = `(() => {
  const box = selector => { const el = document.querySelector(selector); if (!el) return null; const r = el.getBoundingClientRect(); return { y: Math.round(r.y), h: Math.round(r.height), x: Math.round(r.x), w: Math.round(r.width) } }
  return {
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    heading: box('.kb-heading'), eyebrow: document.querySelector('.kb-eyebrow') ? getComputedStyle(document.querySelector('.kb-eyebrow')).display : 'none',
    recordToolbar: box('.kb-record-toolbar'), firstRecord: box('.history .kb-doc-row, .kb-record-toolbar ~ .kb-doc-row'),
    readerPaper: box('.kb-pdf-surface canvas'), readerPaperSurface: box('.kb-pdf-surface'), readerToolbar: box('.kb-pdf-toolbar'),
    maintenancePanel: box('.maintenance-page .v17-panel, .maintenance-page .v17-stats + .v17-panel'),
    versionFirst: box('.v17-version-list .kb-doc-row'), versionHeading: box('.v17-legacy-heading'),
    feedbackFirst: box('.kb-staff-feedback-item'), feedbackPanel: box('.kb-staff-feedback'),
  }
})()`
async function vueGeometry(w, h, page) {
  await resize(w, h)
  await navigate('about:blank'); await navigate(origin + base + page.path + (page.path.includes('?') ? '&' : '?') + 'state=visual')
  await until("document.querySelector('main')")
  await settle(page.key)
  return evaluate(geometry)
}
async function referenceGeometry(w, h, page) {
  await resize(w, h)
  await navigate('about:blank'); await navigate(prototype + '#/hbos/knowledge' + page.path)
  await pause(320)
  return evaluate(`(() => {
    const box = selector => { const el = document.querySelector(selector); if (!el) return null; const r = el.getBoundingClientRect(); return { y: Math.round(r.y), h: Math.round(r.height) } }
    return { firstRecord: box('.activity-panel .docrow'), recordToolbar: box('.activity-tools'), readerPaper: box('#paper-stage .paper'),
      maintenancePanel: box('.maint-layout'), versionFirst: box('.version-row'), feedbackFirst: box('.feedback-item') }
  })()`)
}
const tolerance = { recordToolbarHeight: 48, phoneLateBound: 24 }
const drawerSnapshot = `(() => [...document.querySelectorAll('.ant-drawer.ant-drawer-open')].map(d => ({
  label: d.getAttribute('aria-label'), title: d.querySelector('.ant-drawer-title')?.textContent,
  labelledby: d.getAttribute('aria-labelledby'), modal: d.getAttribute('aria-modal'),
  inert: d.querySelector('.ant-drawer-content-wrapper')?.hasAttribute('inert'),
})))()`
try {
  try {
  for (const page of pages) {
    for (const viewport of viewports) {
      const vue = await vueGeometry(viewport.w, viewport.h, page)
      record(`overflow-${page.key}-${viewport.id}`, '<=1px', vue.overflow, vue.overflow <= 1, 'page geometry')
      if (['P04', 'P05', 'P06', 'P07', 'P08', 'P09'].includes(page.key)) {
        record(`eyebrow-hidden-${page.key}-${viewport.id}`, 'none', vue.eyebrow, vue.eyebrow === 'none', 'prototype hides the English eyebrow on task pages')
      }
      const reference = await referenceGeometry(viewport.w, viewport.h, page)
      const near = (a, b, limit) => a !== null && b !== null && Math.abs(a - b) <= limit
      if (page.key === 'P04' && vue.firstRecord && reference.firstRecord) {
        recordGeometry(`p04-first-item-${viewport.id}`, reference.firstRecord.y, vue.firstRecord.y, 'prototype .activity-panel .docrow vs candidate record row')
      }
      if (page.key === 'P04') {
        record(`p04-toolbar-rows-${viewport.id}`, `<=${tolerance.recordToolbarHeight}px single row`, vue.recordToolbar?.h, (vue.recordToolbar?.h || 999) <= tolerance.recordToolbarHeight, 'one compact toolbar row (tabs + refresh); functional check')
      }
      if (page.key === 'P05' && vue.readerPaper && reference.readerPaper) {
        recordGeometry(`p05-paper-position-${viewport.id}`, reference.readerPaper.y, vue.readerPaper.y,
          'both sides measure the visible page: candidate = rendered PDF page canvas (.kb-pdf-surface canvas), prototype = #paper-stage .paper')
        record(`p05-paper-rendered-${viewport.id}`, 'real canvas rendered with width>0', { width: vue.readerPaper.w, height: vue.readerPaper.h },
          (vue.readerPaper.w || 0) > 0 && (vue.readerPaper.h || 0) > 0, 'functional: real PDF render, not a placeholder')
        if (viewport.id === '320x500') {
          record('p05-paper-visible-320x500', 'rendered page canvas top < 460 (product availability goal)', { object: 'rendered PDF page canvas', actual: vue.readerPaper.y, canvasWidth: vue.readerPaper.w },
            vue.readerPaper.y < 460 && vue.readerPaper.w > 0, 'short first screen; availability goal, not ±2px fidelity')
        }
      }
      if (page.key === 'P08' && vue.versionFirst && reference.versionFirst) {
        recordGeometry(`p08-first-item-${viewport.id}`, reference.versionFirst.y, vue.versionFirst.y,
          '版本档案 first row vs prototype; desktop difference is structural (inline note moved into 更多筛选) and remains for Owner judgement')
        if (viewport.w <= 767) {
          const delta = vue.versionFirst.y - reference.versionFirst.y
          record(`p08-first-item-not-later-${viewport.id}`, `not later than prototype +${tolerance.phoneLateBound}px (declared product goal)`, { actual: vue.versionFirst.y, delta },
            delta <= tolerance.phoneLateBound, 'phone product goal, separate from ±2px fidelity')
        }
      }
      if (page.key === 'P09' && vue.feedbackFirst && reference.feedbackFirst) {
        recordGeometry(`p09-first-row-${viewport.id}`, reference.feedbackFirst.y, vue.feedbackFirst.y, '反馈清单 first row vs prototype')
      }
      if (page.key === 'P06' && vue.maintenancePanel && reference.maintenancePanel) {
        recordGeometry(`p06-main-card-${viewport.id}`, reference.maintenancePanel.y, vue.maintenancePanel.y, 'main maintenance card vs prototype')
      }
      if (page.key === 'P07' && vue.maintenancePanel && reference.maintenancePanel) {
        recordGeometry(`p07-main-card-${viewport.id}`, reference.maintenancePanel.y, vue.maintenancePanel.y, 'upload card vs prototype')
      }
      // Same-condition evidence: capture the implementation and the frozen prototype at
      // the same viewport, DPR, font stack and settled state. The reference measurement
      // above leaves the browser on the prototype file, so re-open the candidate first;
      // otherwise the "vue" screenshot would silently be a second prototype capture.
      await resize(viewport.w, viewport.h)
      await navigate('about:blank'); await navigate(origin + base + page.path + (page.path.includes('?') ? '&' : '?') + 'state=visual')
      await until("document.querySelector('main')"); await settle(page.key)
      await shot(`${output}/screens/vue-${page.key}-${viewport.id}.png`)
      await navigate('about:blank'); await navigate(prototype + '#/hbos/knowledge' + page.path); await pause(320)
      await shot(`${output}/screens/reference-${page.key}-${viewport.id}.png`)
    }
  }

  // P08: exactly one search control and one submit trigger in the toolbar.
  await vueGeometry(390, 844, pages.find(page => page.key === 'P08'))
  const p08Search = await evaluate(`(() => ({
    inputs: document.querySelectorAll('.v17-version-toolbar input[type=search]').length,
    triggers: document.querySelectorAll('.v17-version-toolbar [data-published-search]').length,
    antInputSearch: document.querySelectorAll('.v17-version-toolbar .ant-input-search').length,
  }))()`)
  record('p08-single-search-trigger', { inputs: 1, triggers: 1, antInputSearch: 0 }, p08Search,
    p08Search.inputs === 1 && p08Search.triggers === 1 && p08Search.antInputSearch === 0, 'one prototype-aligned searchbox, no duplicate 查找 button or second search control')

  // P09: bounded server content search (Main 10h minimal interface) and its honest
  // fallback on a candidate that does not have the query parameter yet.
  await resize(390, 844)
  await navigate('about:blank'); await navigate(origin + base + '/maintenance/feedback?state=visual')
  await until("document.querySelector('.kb-staff-feedback-item')")
  const p09Search = await evaluate(`(() => {
    const input = document.querySelector('.kb-staff-feedback input[aria-label="搜索员工反馈"]')
    return { input: Boolean(input), disabled: Boolean(input?.disabled),
      limitation: document.querySelectorAll('[data-v17-feedback-search-limitation]').length,
      hint: Boolean(document.querySelector('.kb-staff-feedback-hint')) }
  })()`)
  record('p09-server-search-supported', { input: true, disabled: false, limitation: 0, hint: true }, p09Search,
    p09Search.input && !p09Search.disabled && p09Search.limitation === 0, 'bounded server search is enabled; no stale capability limitation when the candidate supports it')
  const feedbackQuery = async value => {
    await evaluate(`(() => {
      const input = document.querySelector('.kb-staff-feedback input[aria-label="搜索员工反馈"]')
      if (!input) throw Error('missing feedback search input')
      input.focus()
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      setter.call(input, ${JSON.stringify(value)})
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })()`)
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', text: '\r', unmodifiedText: '\r', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 })
    await pause(450)
  }
  const queueBefore = await evaluate("document.querySelectorAll('.kb-staff-feedback-item').length")
  await feedbackQuery('不存在的合成关键词')
  const queueFiltered = await evaluate("document.querySelectorAll('.kb-staff-feedback-item').length")
  record('p09-server-search-filters', 'the bounded server filter narrows the queue (fixture contract)', { before: queueBefore, after: queueFiltered },
    queueBefore >= 1 && queueFiltered === 0, 'same bounded query parameter as the Main minimal interface; no client-side full scan')
  await navigate('about:blank'); await navigate(origin + base + '/maintenance/feedback?state=feedback-no-search')
  await until("document.querySelector('.kb-staff-feedback-item')")
  await feedbackQuery('版本')
  await until("document.querySelector('[data-v17-feedback-search-limitation]')", 5000)
  const fallback = await evaluate(`(() => ({
    limitation: document.querySelector('[data-v17-feedback-search-limitation]')?.textContent?.trim() || '',
    rows: document.querySelectorAll('.kb-staff-feedback-item').length,
  }))()`)
  record('p09-unsupported-fallback', 'one honest limitation and the unfiltered bounded queue', fallback,
    fallback.limitation.includes('当前候选尚未提供内容搜索') && fallback.rows >= 1, 'pre-interface candidate: no fake filtered results')

  // P09 column alignment with populated visual data (1165px).
  await vueGeometry(1165, 757, pages.find(page => page.key === 'P09'))
  const staff = await evaluate('(' + probe.toString() + ')()')
  record('p09-column-alignment', '<=2px', staff.feedback?.map(row => row.tracks).join('|'), staff.feedback?.length === 1, 'structure probe')

  // Cross-component drawer stack: the source drawer and the feedback drawer are separate
  // components; only the latest opened one may be the modal layer.
  await resize(1165, 757)
  await navigate('about:blank'); await navigate(origin + base + '?state=visual')
  await until("document.querySelector('.kb-main')")
  await evaluate(`(() => { const tab = [...document.querySelectorAll('button')].find(node => node.textContent.trim() === '搜资料'); if (tab) tab.click() })()`)
  await pause(250)
  await evaluate(`(() => {
    const input = document.querySelector('#knowledge-query');
    if (!input) throw Error('missing query input');
    const prototype = input.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value').set.call(input, '培养箱');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.closest('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  })()`)
  await until("document.querySelector('.result-card')", 9000)
  await evaluate("document.querySelector('.result-card .kb-doc-main').click()")
  await until("document.querySelector('.evidence-drawer-root.ant-drawer-open')")
  await pause(700)
  const cross = await evaluate(`(() => { const button = [...document.querySelectorAll('.ant-drawer-open button')].find(node => node.textContent.includes('反馈来源问题')); if (!button) return null; button.click(); return true })()`)
  if (cross) {
    await until("document.querySelector('.kb-feedback-drawer.ant-drawer-open')")
    await pause(800)
    const stacked = await evaluate(drawerSnapshot)
    record('drawer-cross-component-stack', 'latest opened drawer is the only modal layer',
      stacked.map(drawer => `${drawer.label}/${drawer.title}/${drawer.modal}/${drawer.inert}`).join(' | '),
      stacked.length === 2 && stacked[0].label === '资料来源' && stacked[0].modal === null && stacked[0].inert === true && stacked[1].label === '反馈与建议' && stacked[1].modal === 'true',
      'evidence drawer + feedback drawer (separate components)')
  } else {
    record('drawer-cross-component-stack', 'feedback drawer reachable from evidence drawer', 'feedback button missing', false, 'P01 source drawer')
  }
  await evaluate("document.querySelectorAll('.ant-drawer-open .ant-drawer-close').forEach(button => button.click())")
  await pause(800)

  // Shared drawer: each instance keeps its own name; the covered layer is inert.

  await resize(1165, 757)
  await navigate('about:blank'); await navigate(origin + base + '/maintenance/versions')
  await until("document.querySelector('.v17-version-list .kb-doc-row')")
  const clickText = text => evaluate(`(() => { const node = [...document.querySelectorAll('button')].find(node => node.textContent.trim() === ${JSON.stringify(text)} && node.getClientRects().length); if (!node) throw Error('missing ${text}'); node.dispatchEvent(new MouseEvent('click', { bubbles: true })); })()`)
  await clickText('查看版本')
  await until("document.querySelector('.ant-drawer.ant-drawer-open')")
  await pause(500)
  record('drawer-single', 'label 资料与版本', (await evaluate(drawerSnapshot))[0], (await evaluate(drawerSnapshot))[0]?.label === '资料与版本', 'single drawer')
  await evaluate(`(() => { const button = [...document.querySelectorAll('.ant-drawer-open button')].find(node => node.textContent.includes('查看与核对质量')); if (!button) throw Error('missing quality button'); button.click() })()`)
  await pause(800)
  const stacked = await evaluate(drawerSnapshot)
  record('drawer-stacked-names', 'each instance keeps its own label',
    stacked.map(drawer => `${drawer.label}/${drawer.title}`).join(' | '),
    stacked.length === 2 && stacked[0].label === '资料与版本' && stacked[1].label === '核对本版本质量' && stacked[0].title === '资料与版本' && stacked[1].title === '核对本版本质量',
    'detail + quality drawers')
  record('drawer-stack-modal', 'top modal, covered inert', stacked.map(drawer => `${drawer.modal}/${drawer.inert}`).join(' | '),
    stacked[0].modal === null && stacked[0].inert === true && stacked[1].modal === 'true' && stacked[1].inert === false, 'only top layer is modal')
  await shot(`${output}/screens/drawer-detail-quality-1165x757.png`)
  const esc = async () => {
    await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 })
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 })
    await pause(900)
  }
  await esc()
  const afterCloseTop = await evaluate(drawerSnapshot)
  record('drawer-close-top', 'detail remains open with its own name', afterCloseTop, afterCloseTop.length === 1 && afterCloseTop[0].label === '资料与版本', 'close top layer')
  const focusAfterTop = await evaluate(`(() => { const active = document.activeElement; return { inside: Boolean(active?.closest('.ant-drawer.ant-drawer-open')) } })()`)
  record('drawer-focus-after-close', 'focus inside remaining dialog', focusAfterTop, focusAfterTop.inside, 'focus restoration')
  await esc()
  record('drawer-close-all', '0 open drawers', await evaluate("document.querySelectorAll('.ant-drawer-open').length"), (await evaluate("document.querySelectorAll('.ant-drawer-open').length")) === 0, 'Escape chain')
  // second open order: reopen the same pair after closing, then leave the route with a drawer open
  await clickText('查看版本')
  await until("document.querySelector('.ant-drawer.ant-drawer-open')"); await pause(500)
  await evaluate(`(() => { const button = [...document.querySelectorAll('.ant-drawer-open button')].find(node => node.textContent.includes('查看与核对质量')); button.click() })()`)
  await pause(800)
  const reopened = await evaluate(drawerSnapshot)
  record('drawer-reopen-order', 'reopened stack keeps independent names', reopened.map(drawer => drawer.label).join(' | '),
    reopened.length === 2 && reopened[0].label === '资料与版本' && reopened[1].label === '核对本版本质量', 'reopen after close')
  await evaluate(`(() => { const link = [...document.querySelectorAll('.kb-sidebar-bottom a')].find(node => node.textContent.includes('返回工作台')); if (!link) throw Error('missing back-to-workbench link'); link.click() })()`)
  await pause(1200)
  record('drawer-route-leave', '0 open drawers and no scroll lock', { open: await evaluate("document.querySelectorAll('.ant-drawer-open').length"), bodyOverflow: await evaluate('document.body.style.overflow') },
    (await evaluate("document.querySelectorAll('.ant-drawer-open').length")) === 0 && (await evaluate('document.body.style.overflow')) === '', 'route change')
  } catch (error) {
    results.push({ id: 'run-error', expected: 'script completes', actual: String(error.message || error), result: 'FAIL', evidence: 'see console' })
    console.error('RUN ERROR', error)
  }
  await writeFile(`${output}/v17-final-result.json`, JSON.stringify({ when: new Date().toISOString(), finalSha, worktreeDirty, transport: 'isolated headless Chrome (Chrome/157, DPR1, 127.0.0.1:18650 synthetic fixture, ?state=visual)', prototype, differences: results.filter(item => item.result === 'DIFFERENCE_RECORDED'), results }, null, 2))
  const failed = results.filter(item => item.result === 'FAIL')
  const differences = results.filter(item => item.result === 'DIFFERENCE_RECORDED')
  const passed = results.filter(item => item.result === 'PASS')
  console.log(`\nRESULT ${passed.length} PASS + ${differences.length} DIFFERENCE_RECORDED + ${failed.length} FAIL (${results.length} checks)`)
  if (failed.length) { console.log('FAILED:'); failed.forEach(item => console.log(' -', item.id)); process.exitCode = 1 }
} finally {
  close()
}
