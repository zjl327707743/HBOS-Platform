import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { createServer, resolveConfig, transformWithEsbuild } from 'vite'
import { parse, compileScript } from '@vue/compiler-sfc'
import axios from 'axios'
import postcss from 'postcss'
import { createSSRApp, createRenderer, defineComponent, h, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { renderToString } from '@vue/server-renderer'
import { checkMockTemplate } from '../../../scripts/portal/mock_content_gate.mjs'

const root = fileURLToPath(new URL('..', import.meta.url))
let server, api, client, results, access, mode, errors, handler
const originalAdapter = axios.defaults.adapter
const calls = []
const ok = data => ({ ok: true, data: { data } })
const task = (id, status = '已完成', action = 'eval_trend') => ({ task_id: id, app_id: 'lims', title: id, status, action, priority: 'normal', deep_link: '/hbos/lims/tasks', assignment_type: 'direct' })
const app = { id: 'lims', shortTitle: 'LIMS', capabilityTasks: true, capabilitySummary: true }

before(async () => {
  axios.defaults.adapter = async config => {
    calls.push(config)
    const message = config.url.endsWith('hbos_portal.api.csrf.get_token')
      ? { ok: true, data: { csrf_token: 'test-csrf' } }
      : await handler(config)
    return { data: { message }, status: 200, statusText: 'OK', headers: {}, config }
  }
  server = await createServer({ root, configFile: `${root}/vite.config.ts`,
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, include: [] }, appType: 'custom',
    plugins: [{ name: 'client-view-for-runtime-tests',
      resolveId(id) { if (id.startsWith('virtual:client-view/')) return `\0${id}.ts` },
      async load(id) {
        if (!id.startsWith('\0virtual:client-view/')) return
        const file = id.slice('\0virtual:client-view/'.length, -3)
        const { descriptor } = parse(readFileSync(`${root}/src/views/${file}`, 'utf8'))
        const compiled = compileScript(descriptor, { id: file, inlineTemplate: true })
        return (await transformWithEsbuild(compiled.content, `${file}.ts`, { loader: 'ts' })).code
      },
    }, { name: 'ssr-cjs-locale', enforce: 'pre', transform(code, id) {
      if (id.endsWith('/src/App.vue')) return code.replace('ant-design-vue/es/locale/zh_CN', 'ant-design-vue/lib/locale/zh_CN.js')
    } }] })
  api = await server.ssrLoadModule('/src/services/portalApi.ts')
  client = await server.ssrLoadModule('/src/services/frappeClient.ts')
  results = await server.ssrLoadModule('/src/services/limsResults.ts')
  access = await server.ssrLoadModule('/src/services/limsResultAccess.ts')
  mode = await server.ssrLoadModule('/src/contracts/dataMode.ts')
  errors = await server.ssrLoadModule('/src/services/portalErrors.ts')
})
after(async () => { axios.defaults.adapter = originalAdapter; await server?.close() })

test('Desk origin follows the development proxy, keeps explicit overrides and stays same-origin in production', async () => {
  const keys = ['VITE_PORTAL_DATA_MODE', 'VITE_FRAPPE_APP_ORIGIN', 'VITE_FRAPPE_PROXY_TARGET']
  const original = Object.fromEntries(keys.map(key => [key, process.env[key]]))
  try {
    process.env.VITE_PORTAL_DATA_MODE = 'frappe'
    for (const [command, origin, proxy, expected] of [
      ['serve', '', 'http://127.0.0.1:18091', 'http://127.0.0.1:18091'],
      ['serve', 'https://hbos.example.test', 'http://127.0.0.1:8080', 'https://hbos.example.test'],
      ['build', '', 'http://127.0.0.1:8080', ''],
    ]) {
      process.env.VITE_FRAPPE_APP_ORIGIN = origin
      process.env.VITE_FRAPPE_PROXY_TARGET = proxy
      const config = await resolveConfig({ root, configFile: `${root}/vite.config.ts`, mode: 'development' }, command)
      assert.equal(config.define['import.meta.env.VITE_FRAPPE_APP_ORIGIN'], JSON.stringify(expected))
    }
  } finally {
    for (const key of keys) {
      if (original[key] === undefined) delete process.env[key]
      else process.env[key] = original[key]
    }
  }
})

test('data mode whitelist rejects omitted/misspelled/case/space values and production Mock', () => {
  for (const value of [undefined, '', 'FRAPPE', 'frape', ' mock']) assert.throws(() => mode.resolvePortalDataMode(value))
  assert.equal(mode.resolvePortalDataMode('frappe'), 'frappe')
  assert.equal(mode.resolvePortalDataMode('mock'), 'mock')
  assert.throws(() => mode.validatePortalBuildMode('mock', 'build', 'production'))
  assert.equal(mode.validatePortalBuildMode('mock', 'build', 'mock'), 'mock')
})

test('task status respects explicit task state and actionable domain transitions', () => {
  assert.equal(api.normalizeTaskStatus('waiting', 'any'), 'waiting')
  assert.equal(api.normalizeTaskStatus('done', 'any'), 'done')
  assert.equal(api.normalizeTaskStatus('已完成', 'eval_trend'), 'open')
  assert.equal(api.normalizeTaskStatus('已批准', 'execute_usage'), 'open')
  assert.equal(api.normalizeTaskStatus('已关闭'), 'done')
  assert.equal(api.normalizeTaskStatus('等待中'), 'waiting')
})

test('Portal task aggregation follows all cursor pages and single-page tasks expose cursor/total', async () => {
  calls.length = 0
  handler = config => ok({ tasks: config.params.cursor ? [task('21', 'waiting'), task('22', 'done')] : Array.from({ length: 20 }, (_, i) => task(String(i))), total: 22, next_cursor: config.params.cursor ? null : '20' })
  const first = await api.getFrappeTaskPage(app, { view: 'my-review', limit: 20 })
  assert.equal(first.items.length, 20)
  assert.equal(first.nextCursor, '20')
  assert.equal(first.total, 22)
  const batch = await api.getFrappeTasksForApps([app])
  assert.equal(batch.items.length, 22)
  assert.equal(batch.items.at(-2).status, 'waiting')
  assert.equal(batch.items.at(-1).status, 'done')
  assert.deepEqual(batch.errors, [])
  assert.ok(calls.some(call => call.params.cursor === '20'))
})

test('partial task/summary failures keep good items and surface trace ids', async () => {
  const failed = { ...app, id: 'failed', shortTitle: '失败应用' }
  handler = config => config.params.app_id === 'failed'
    ? { ok: false, error: { code: 'PROVIDER_ERROR', message: 'internal SQL must not leak', trace_id: 'TRACE-PARTIAL', retryable: true } }
    : ok(config.url.includes('get_summary') ? { metrics: [{ id: 'count', label: '工作数', value: 2, tone: 'info' }] } : { tasks: [task('one')], total: 1 })
  for (const batch of [await api.getFrappeTasksForApps([app, failed]), await api.getFrappeSummariesForApps([app, failed])]) {
    assert.equal(batch.items.length, 1)
    assert.equal(batch.errors.length, 1)
    assert.match(batch.errors[0].message, /TRACE-PARTIAL/)
    assert.doesNotMatch(batch.errors[0].message, /SQL/)
  }
})

test('bad pagination cursor raises a visible partial failure rather than hanging or claiming complete', async () => {
  handler = () => ok({ tasks: [task('one')], next_cursor: 'repeat', total: 30 })
  const batch = await api.getFrappeTasksForApps([app])
  assert.equal(batch.items.length, 1)
  assert.equal(batch.errors.length, 1)
})

test('result list passes cursor and filters so records past 50 remain reachable', async () => {
  handler = config => ok({ results: config.params.cursor ? [{ result_name: '51' }] : Array.from({ length: 50 }, (_, i) => ({ result_name: String(i) })), total: 51, next_cursor: config.params.cursor ? null : '50' })
  const first = await results.listLimsResults({ keyword: 'batch', status: '已提交' })
  const second = await results.listLimsResults({ keyword: 'batch', status: '已提交', cursor: first.next_cursor })
  assert.equal(first.results.length + second.results.length, 51)
  assert.equal(second.next_cursor, null)
  assert.equal(calls.at(-1).params.keyword, 'batch')
  assert.equal(calls.at(-1).params.status, '已提交')
})

test('search partial failures retain results and report incomplete providers', async () => {
  handler = () => ({ ok: true, data: { results: [{ app_id: 'lims', title: 'found', deep_link: '/hbos/lims' }], provider_errors: [{ app_id: 'other', code: 'PROVIDER_ERROR', trace_id: 'TRACE-SEARCH' }] } })
  const batch = await api.searchFrappePortal('query')
  assert.equal(batch.items.length, 1)
  assert.match(batch.errors[0].message, /TRACE-SEARCH/)
})

test('logout uses authenticated POST with CSRF and session timeout', async () => {
  handler = () => 'Logged Out'
  client.clearCachedCsrfToken()
  await client.logout()
  const call = calls.at(-1)
  assert.equal(call.url, '/api/method/logout')
  assert.equal(call.method, 'post')
  assert.equal(call.withCredentials, true)
  assert.equal(call.headers.get('X-Frappe-CSRF-Token'), 'test-csrf')
  assert.equal(call.timeout, 15000)
})

test('read-only labels and actions match mode, capability, status and backend OOS policy', () => {
  const capabilities = ['lims.results.submit', 'lims.results.review', 'lims.results.approve']
  assert.equal(access.resultAccess('mock', capabilities, '草稿').readonlyReason, '演示模式只读')
  assert.equal(access.resultAccess('frappe', capabilities, '草稿').submit, true)
  assert.equal(access.resultAccess('frappe', capabilities, '已批准').submit, false)
  assert.doesNotMatch(access.resultAccess('frappe', [], '草稿').readonlyReason, /演示/)
  assert.equal(access.resultAccess('frappe', capabilities, '已提交', '不合格').review, true)
  assert.equal(access.resultAccess('frappe', capabilities, '已复核', '不合格').approve, false)
  assert.equal(access.resultAccess('frappe', capabilities, '已复核', '合格', true).approve, false)
})

test('Mock gate rejects unguarded demo content and accepts explicit ancestor guards', () => {
  assert.deepEqual(checkMockTemplate('<div><span>扫码入库</span></div>'), ['扫码入库'])
  assert.deepEqual(checkMockTemplate(`<div v-if="portal.dataSource === 'mock'"><span>扫码入库</span></div>`), [])
  assert.deepEqual(checkMockTemplate('<div><span>正常业务</span></div>'), [])
})

test('CSS navigation has no gap at 767/767.98/768/769 and sidebar owns a scrollable region', () => {
  const css = readFileSync(`${root}/src/styles/global.css`, 'utf8')
  const parsed = postcss.parse(css)
  function display(selector, width) {
    let value
    parsed.walkRules(rule => {
      if (!rule.selector.split(',').map(x => x.trim()).includes(selector)) return
      for (let parent = rule.parent; parent; parent = parent.parent) {
        if (parent.type === 'atrule' && parent.name === 'media') {
          const max = parent.params.match(/max-width:\s*([\d.]+)px/)
          const min = parent.params.match(/min-width:\s*([\d.]+)px/)
          if ((max && width > Number(max[1])) || (min && width < Number(min[1]))) return
        }
      }
      rule.walkDecls('display', decl => { value = decl.value })
    })
    return value
  }
  for (const width of [767, 767.98, 768, 769]) {
    for (const [side, mobile] of [['.app-local-sidebar', '.mobile-app-nav'], ['.portal-sidebar', '.mobile-portal-nav']]) {
      assert.ok(display(side, width) !== 'none' || display(mobile, width) !== 'none', `${width}px: ${side}/${mobile}`)
    }
  }
  const nav = []; parsed.walkRules('.app-local-nav', rule => rule.walkDecls(decl => nav.push([decl.prop, decl.value])))
  assert.ok(nav.some(([prop, value]) => prop === 'overflow-y' && value === 'auto'))
  assert.ok(nav.some(([prop, value]) => prop === 'min-height' && value === '0'))
})

test('actual real-mode home/header/App render no fake scan, room, connection or Mock banner', async () => {
  const pinia = createPinia(); setActivePinia(pinia)
  const { usePortalStore } = await server.ssrLoadModule('/src/stores/portal.ts')
  const portal = usePortalStore()
  portal.user = { id: 'real-user', displayName: '真实用户' }
  portal.authenticated = true
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/hbos', component: { render: () => null } }] })
  await router.push('/hbos')
  const { antdComponents } = await server.ssrLoadModule('/src/components/antdComponents.ts')
  for (const file of ['views/PortalHome.vue', 'components/layout/GlobalHeader.vue', 'App.vue']) {
    const { default: component } = await server.ssrLoadModule(`/src/${file}`)
    const appInstance = createSSRApp(component, file.includes('GlobalHeader') ? { apps: [], avatarText: '真' } : {})
    appInstance.use(pinia); appInstance.use(router)
    for (const component of antdComponents) appInstance.use(component)
    const html = await renderToString(appInstance)
    assert.doesNotMatch(html, /扫码入库|LIVE READY|演示模式只读|演示数据|已连接|A \/ B/)
    if (file.includes('PortalHome')) assert.match(html, /会话已验证/)
  }
})


test('actual result/task pages load more, then discard cursors when URL filters change', async () => {
  const { usePortalStore } = await server.ssrLoadModule('/src/stores/portal.ts')
  for (const [file, path, label] of [
    ['LimsResultListView.vue', '/hbos/lims/results', 'results'],
    ['LimsTaskBoardView.vue', '/hbos/lims/tasks', 'tasks'],
  ]) {
    const nodes = []
    const renderer = createRenderer({
      createElement(tag) { const node = { tag, props: {}, children: [], text: '', active: true }; nodes.push(node); return node },
      createText(text) { return { text, active: true } }, createComment() { return { text: '', active: true } },
      insert(node, parent) { node.parent = parent; parent.children?.push(node) },
      remove(node) { node.active = false }, setText(node, text) { node.text = text },
      setElementText(node, text) { node.text = text }, patchProp(node, key, _old, value) { node.props[key] = value },
      parentNode(node) { return node.parent }, nextSibling() { return null },
    })
    const pinia = createPinia(); setActivePinia(pinia)
    const portal = usePortalStore(); portal.user = { id: 'test-user' }; portal.apps = [app]
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path, component: { render: () => null } },
      { name: 'lims-result-entry', path: '/hbos/lims/results/:resultId', component: { render: () => null } },
    ] })
    await router.push(path)
    const requested = []
    handler = config => {
      requested.push({ ...config.params })
      return ok(label === 'results'
        ? { results: [{ result_name: config.params.cursor ? '51' : '1' }], total: 51, next_cursor: config.params.cursor ? null : '50' }
        : { tasks: [task(config.params.cursor ? '21' : '1')], total: 21, next_cursor: config.params.cursor ? null : '20' })
    }
    const { default: page } = await server.ssrLoadModule(`virtual:client-view/${file}`)
    const instance = renderer.createApp(page); instance.use(pinia); instance.use(router)
    const tags = new Set([...readFileSync(`${root}/src/views/${file}`, 'utf8').matchAll(/<(a-[a-z-]+)\b/g)].map(match => match[1]))
    for (const tag of tags) {
      const name = tag.split('-').map(part => part[0].toUpperCase() + part.slice(1)).join('')
      instance.component(name, defineComponent({ name, inheritAttrs: false,
        setup(_props, { attrs, slots }) { return () => h(name === 'AButton' ? 'button' : 'div', attrs, slots.default?.()) },
      }))
    }
    const originalHTMLElement = globalThis.HTMLElement
    globalThis.HTMLElement = class {}
    try {
      instance.mount({ children: [] })
      const flush = async () => { await new Promise(resolve => setImmediate(resolve)); for (let i = 0; i < 20; i++) await nextTick() }
      const text = node => node.text + (node.children || []).map(text).join('')
      await flush()
      const more = nodes.find(node => node.active && node.tag === 'button' && text(node).includes('加载更多'))
      assert.ok(more, `${file}: missing pagination button; requests=${JSON.stringify(requested)}; text=${nodes.map(text).join("|")}`)
      await more.props.onClick(); await flush()
      assert.equal(requested.at(-1).cursor, label === 'results' ? '50' : '20')
      await router.replace({ path, query: { status: '已提交' } }); await flush()
      assert.equal(requested.at(-1).cursor, undefined)
      assert.equal(requested.at(-1).status, '已提交')
    } finally { instance.unmount(); globalThis.HTMLElement = originalHTMLElement }
  }
})
