import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { evaluate, navigate, resize, shot, close } from '../browser/cdp.mjs'
import { probe } from './structure.mjs'

const origin = 'http://127.0.0.1:18650'
const feedback = '/hbos/knowledge/maintenance/feedback'
const output = process.env.HBOS_STRUCTURE_OUTPUT || 'outputs/结构返工/after'
await mkdir(output, { recursive: true })
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
async function wait(expression) {
  for (let n = 0; n < 60; n++) {
    if (await evaluate(expression)) return
    await pause(80)
  }
  throw new Error('Missing ready state: ' + expression)
}
async function cold(path) {
  await navigate('about:blank')
  await navigate(origin + path)
}
async function check(label, count) {
  await wait("document.querySelector('.kb-staff-feedback-item')")
  const hasMenu = await evaluate("Boolean(document.querySelector('.kb-mobile-trigger'))")
  if (hasMenu) {
    await evaluate("document.querySelector('.kb-mobile-trigger').click()")
    await wait("document.querySelector('dialog[open] .kb-sidebar-bottom')")
  }
  const result = await evaluate('(' + probe.toString() + ')()')
  if (count !== undefined) assert.equal(result.feedback.length, count)
  assert.equal(await evaluate(`(() => {
    const brand = document.querySelector('.kb-header-brand .v10-brand').getBoundingClientRect()
    const badge = document.querySelector('.kb-header-brand .kb-synthetic').getBoundingClientRect()
    return brand.right <= badge.left + 1 || brand.bottom <= badge.top + 1
  })()`), true, 'brand and fixture badge overlap')
  const footer = await evaluate(`(() => {
    const footer = document.querySelector('.kb-sidebar-bottom')
    const sidebar = footer.closest('aside')
    const last = footer.querySelector('a:last-child')
    last.focus()
    last.scrollIntoView({ block: 'nearest', behavior: 'instant' })
    return {
      focused: document.activeElement === last,
      visible: last.getBoundingClientRect().bottom <= sidebar.getBoundingClientRect().bottom + 2,
    }
  })()`)
  assert.deepEqual(footer, { focused: true, visible: true })
  await shot(output + '/sidebar-' + label + '.png')
  if (hasMenu) await evaluate("document.querySelector('dialog[open] .kb-mobile-close').click()")
  await evaluate("document.querySelector('.kb-sidebar')?.scrollTo(0, 0)")
  await shot(output + '/feedback-' + label + '.png')
  console.log('PASS', label, JSON.stringify(result))
  return result.feedback
}
try {
  if (process.env.HBOS_NATIVE_ZOOM === '200') {
    await cold(feedback + '?state=feedback-long')
    assert.equal(await evaluate('devicePixelRatio'), 2)
    await check('native-200-long')
  } else {
    await resize(1165, 757)
    await cold(feedback)
    const expected = await check('direct')
    for (const [label, start] of [['after-upload', '/hbos/knowledge/maintenance/upload'], ['after-query', '/hbos/knowledge'], ['after-portal', '/hbos']]) {
      await cold(start)
      if (label === 'after-portal') {
        await wait("document.querySelector('main')")
        await navigate(origin + '/hbos/knowledge')
      }
      await wait(`document.querySelector('.kb-sidebar a[href="${feedback}"]')`)
      await evaluate(`document.querySelector('.kb-sidebar a[href="${feedback}"]').click()`)
      assert.deepEqual(await check(label), expected)
    }
    await evaluate('history.back()')
    await wait(`location.pathname !== '${feedback}'`)
    await evaluate('history.forward()')
    assert.deepEqual(await check('forward'), expected)
    await navigate(origin + feedback)
    assert.deepEqual(await check('reload'), expected)
    await cold(feedback + '?state=feedback-one')
    await check('one', 1)
    await cold(feedback + '?state=empty')
    await wait("document.querySelector('.kb-staff-feedback .ant-empty')")
    assert.equal(await evaluate("document.querySelectorAll('.kb-staff-feedback-item').length"), 0)
    await shot(output + '/feedback-empty.png')
    console.log('PASS empty')
    for (const [w,h] of [[1440,1000],[390,844],[320,620],[1165,400]]) {
      await resize(w,h)
      await cold(feedback + '?state=feedback-long')
      await check(w + 'x' + h + '-long')
    }
  }
} finally {
  close()
}
