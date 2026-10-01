import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import { createPinia, setActivePinia } from 'pinia'
import { createSSRApp, createRenderer, defineComponent, nextTick, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { renderToString } from '@vue/server-renderer'
import { AxiosError } from 'axios'

const root = fileURLToPath(new URL('..', import.meta.url))
let server, usePortalStore, checkPortalAccess, useDebouncedSearch, useLimsQueryPage, isSafeInternalPath
let fixture
const emptyData = () => ({ user: { id: 'test-user' }, branding: null, apps: [], heroMetrics: [], tasks: [], businessPulse: [], twinStatuses: [], limsQueue: [] })
const source = (file) => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8')

before(async () => {
  server = await createServer({
    root,
    configFile: `${root}/vite.config.ts`,
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    optimizeDeps: { noDiscovery: true, include: [] },
    appType: 'custom',
    plugins: [{
      name: 'portal-provider-test-fixture',
      enforce: 'pre',
      transform(_code, id) {
        if (!id.endsWith('/services/portalProvider.ts')) return
        return `
          export const portalDataSource = 'frappe';
          export const searchPortal = async () => [];
          export const resolveBusinessRoute = async (_appId, path) => path;
          export const getPortalData = () => globalThis.__portalReviewFixture.data();
          export const getPortalSummaries = (...args) => globalThis.__portalReviewFixture.summaries(...args);
          export const getPortalTasks = (...args) => globalThis.__portalReviewFixture.tasks(...args);
        `
      },
    }],
  })
  ;({ usePortalStore } = await server.ssrLoadModule('/src/stores/portal.ts'))
  ;({ checkPortalAccess } = await server.ssrLoadModule('/src/router/portalGuard.ts'))
  ;({ useDebouncedSearch } = await server.ssrLoadModule('/src/composables/useDebouncedSearch.ts'))
  ;({ useLimsQueryPage } = await server.ssrLoadModule('/src/composables/useLimsQueryPage.ts'))
  ;({ isSafeInternalPath } = await server.ssrLoadModule('/src/services/internalPath.ts'))
})
after(async () => {
  delete globalThis.__portalReviewFixture
  await server?.close()
})

function freshPortal() {
  fixture = { data: async () => emptyData(), summaries: async () => [], tasks: async () => [] }
  globalThis.__portalReviewFixture = fixture
  setActivePinia(createPinia())
  return usePortalStore()
}
const limsRoute = { meta: { requiresAuth: true, appId: 'lims', limsCapability: 'results' }, fullPath: '/hbos/lims/results?status=已提交' }
const rejection = (status, data = {}) => new AxiosError('request failed', 'ERR_BAD_RESPONSE', undefined, undefined, { status, data })

for (const error of [rejection(500), new Error('network unavailable')]) {
  test(`bootstrap ${error.response?.status || 'network failure'} preserves requested LIMS error route`, async () => {
    const portal = freshPortal()
    fixture.data = async () => { throw error }
    assert.equal(await checkPortalAccess(limsRoute, portal, 'frappe'), true)
    assert.ok(portal.bootstrapError)
    assert.deepEqual(portal.apps, [])
    assert.equal(portal.authenticated, true)
  })
}
for (const error of [rejection(401), rejection(403, { code: 'UNAUTHENTICATED' })]) {
  test(`bootstrap ${error.response.status} unauthenticated redirects to login`, async () => {
    const portal = freshPortal()
    fixture.data = async () => { throw error }
    assert.deepEqual(await checkPortalAccess(limsRoute, portal, 'frappe'), { name: 'login', query: { redirect: limsRoute.fullPath } })
  })
}
test('successful bootstrap still denies missing app and missing semantic capability', async () => {
  const portal = freshPortal()
  assert.deepEqual(await checkPortalAccess(limsRoute, portal, 'frappe'), { name: 'forbidden' })
  portal.apps = [{ id: 'lims', capabilities: ['results'], accessCapabilities: [] }]
  assert.deepEqual(await checkPortalAccess(limsRoute, portal, 'frappe'), { name: 'forbidden' })
  portal.apps = [{ id: 'lims', capabilities: ['results'], accessCapabilities: ['lims.results.read'] }]
  assert.equal(await checkPortalAccess(limsRoute, portal, 'frappe'), true)
})
test('retry recovers bootstrap and reinstates access checks', async () => {
  const portal = freshPortal()
  fixture.data = async () => { throw rejection(500) }
  assert.equal(await checkPortalAccess(limsRoute, portal, 'frappe'), true)
  fixture.data = async () => emptyData()
  await portal.bootstrap()
  assert.equal(portal.bootstrapError, null)
  assert.deepEqual(await checkPortalAccess(limsRoute, portal, 'frappe'), { name: 'forbidden' })
})
test('detached background refresh failures are caught and retain last successful data', async () => {
  const portal = freshPortal()
  portal.tasks = [{ taskId: 'last-success' }]
  portal.heroMetrics = [{ id: 'last-metric' }]
  fixture.tasks = async () => { throw new Error('task provider failed') }
  fixture.summaries = async () => { throw new Error('summary provider failed') }
  await Promise.all([portal.refreshTasks(), portal.refreshSummaries()])
  assert.equal(portal.tasks[0].taskId, 'last-success')
  assert.equal(portal.heroMetrics[0].id, 'last-metric')
  assert.ok(portal.tasksError)
  assert.ok(portal.summariesError)
  assert.equal(portal.tasksLoading, false)
  assert.equal(portal.summariesLoading, false)
  fixture.tasks = fixture.summaries = async () => []
  await Promise.all([portal.refreshTasks(), portal.refreshSummaries()])
  assert.equal(portal.tasksError, null)
  assert.equal(portal.summariesError, null)
})

const renderer = createRenderer({
  createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
  insert() {}, remove() {}, setText() {}, setElementText() {}, patchProp() {},
  parentNode: () => null, nextSibling: () => null,
})
function mount(setup, plugins = []) {
  const app = renderer.createApp(defineComponent({ setup() { setup(); return () => null } }))
  for (const plugin of plugins) app.use(plugin)
  app.mount({})
  return app
}
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

test('search debounces rapid typing and rejects old responses, close cancels pending search', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const query = ref(''), open = ref(false), calls = []
  let search
  const app = mount(() => {
    search = useDebouncedSearch(query, open, (value) => {
      const request = deferred(); calls.push({ value, ...request }); return request.promise
    })
  })
  open.value = true
  await nextTick()
  query.value = 'A'; query.value = 'AB'; query.value = 'ABC'
  t.mock.timers.tick(279)
  assert.deepEqual(calls.map((call) => call.value), [''])
  t.mock.timers.tick(1)
  assert.deepEqual(calls.map((call) => call.value), ['', 'ABC'])
  calls[1].resolve(['new']); await nextTick()
  calls[0].resolve(['old']); await nextTick()
  assert.deepEqual(search.results.value, ['new'])
  query.value = 'closed-query'; open.value = false; await nextTick()
  t.mock.timers.tick(300)
  assert.equal(calls.length, 2)
  app.unmount()
})
test('search failures show an error and unmount cancels pending requests', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const query = ref(''), open = ref(false)
  let search, calls = 0
  const app = mount(() => { search = useDebouncedSearch(query, open, async () => { calls++; throw new Error('offline') }) })
  open.value = true; await nextTick(); await nextTick()
  assert.ok(search.errorMessage.value)
  assert.equal(search.loading.value, false)
  query.value = 'cancel'; app.unmount(); t.mock.timers.tick(300)
  assert.equal(calls, 1)
})
test('query pages restore URL state, reload on navigation, and ignore stale page responses', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  usePortalStore().user = { id: 'test-user' }
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/query', component: { render: () => null } }] })
  await router.push('/query?keyword=initial&status=已提交')
  const keyword = ref(''), status = ref(''), requests = [], commits = []
  let page
  const load = () => page.runLoad(() => { const request = deferred(); requests.push(request); return request.promise }, (value) => commits.push(value))
  const app = mount(() => { page = useLimsQueryPage({ path: '/query', fields: { keyword: { state: keyword }, status: { state: status } }, load, failureMessage: 'failed' }) }, [pinia, router])
  assert.equal(keyword.value, 'initial')
  assert.equal(status.value, '已提交')
  keyword.value = 'next'
  await page.updateRoute(); await nextTick()
  assert.match(router.currentRoute.value.fullPath, /keyword=next/)
  requests[1].resolve('new'); await nextTick()
  requests[0].resolve('old'); await nextTick()
  assert.deepEqual(commits, ['new'])
  const failed = page.runLoad(async () => { throw new Error('failed') }, () => assert.fail('must not commit'))
  await failed
  assert.equal(page.errorMessage.value, 'failed')
  assert.equal(page.loading.value, false)
  app.unmount()
})
test('redirect safety rejects slash tricks, traversal and malformed encoding', () => {
  for (const value of ['//evil.test', '/\\evil.test', '/a\\b', '/%2f%2fevil.test', '/a/../b', '/%2e%2e/b', '/%5cevil.test', '/bad%']) assert.equal(isSafeInternalPath(value), false, value)
  for (const value of ['/hbos', '/hbos/lims/results?status=已提交', '/hbos/lims#results']) assert.equal(isSafeInternalPath(value), true, value)
})
test('LIMS view tokens resolve globally or have a fallback, including teleported drawers', () => {
  const tokens = source('theme/tokens.css')
  const defined = new Set([...tokens.matchAll(/(--[\w-]+)\s*:/g)].map((match) => match[1]))
  assert.ok(defined.has('--lims-ink'))
  assert.ok(defined.has('--lims-green'))
  for (const file of ['LimsCoaView.vue', 'LimsQualityStandardsView.vue', 'LimsRetentionWorkbenchView.vue', 'LimsStabilityWorkbenchView.vue']) {
    for (const match of source(`views/${file}`).matchAll(/var\((--[\w-]+)([^)]*)\)/g)) assert.ok(defined.has(match[1]) || match[2].includes(','), `${file}: ${match[1]}`)
  }
})
test('all Ant Design template tags have registered components, including nested exports', async () => {
  const { antdComponents } = await server.ssrLoadModule('/src/components/antdComponents.ts')
  const app = renderer.createApp({ render: () => null })
  for (const component of antdComponents) app.use(component)
  function scan(dir) {
    for (const item of readdirSync(dir, { withFileTypes: true })) {
      const file = `${dir}/${item.name}`
      if (item.isDirectory()) scan(file)
      else if (item.name.endsWith('.vue')) {
        for (const match of readFileSync(file, 'utf8').matchAll(/<(a-[a-z-]+)\b/g)) {
          const name = match[1].split('-').map((part) => part[0].toUpperCase()+part.slice(1)).join('')
          assert.ok(app.component(name), `${file}: ${name}`)
        }
      }
    }
  }
  scan(`${root}/src`)
})

// Render the actual shell: a degraded bootstrap must never mount business content.
test('degraded LIMS shell renders its retry banner and hides the business route', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const portal = usePortalStore()
  portal.bootstrapError = 'HBOS 初始化失败，请稍后重试。'
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/hbos', component: { render: () => null } }, { path: '/hbos/lims', component: { render: () => 'BUSINESS_CONTENT_MARKER' } }] })
  await router.push('/hbos/lims')
  const { default: shell } = await server.ssrLoadModule('/src/components/layout/LimsLayout.vue')
  const { antdComponents } = await server.ssrLoadModule('/src/components/antdComponents.ts')
  const app = createSSRApp(shell)
  app.use(pinia); app.use(router)
  for (const component of antdComponents) app.use(component)
  const html = await renderToString(app)
  assert.match(html, /HBOS 初始化失败/)
  assert.match(html, /重试/)
  assert.doesNotMatch(html, /BUSINESS_CONTENT_MARKER/)
})
