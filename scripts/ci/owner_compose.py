#!/usr/bin/env python3
"""Reviewed textual composition adapter. EXECUTE ONLY on a disposable GitHub runner.
No application code is imported or executed by this script. Tests run separately.
Usage: python3 /path/owner_compose.py single SHA --evidence-dir /tmp/composition
       python3 /path/owner_compose.py full --evidence-dir /tmp/composition
Unknown conflicts are preserved and stop the run. No whole-file ours/theirs reset.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BASE = '45658fe4b84d8fb7dd4433c459aa30572e0d13d3'
REFS = {
    '42': 'dc478b67b5164770fd356dc7d97e7ba03a360fe1',
    '43': 'e6d3f6c785850007a6ab68e7092810b0e323f6fa',
    '46': 'bfa3b4c1380d488c062477d6c9c42c5ea804b19a',
    '39': '136e90dc102cc40d294650b8f463ac2e709c92cb',
}
PREFIX = 'frontend/hbos-portal-web/'
ROUTER = PREFIX + 'src/router/index.ts'
SESSION = PREFIX + 'src/composables/usePortalSession.ts'
MOBILE = PREFIX + 'src/components/layout/MobileAppNav.vue'
DOMAIN = PREFIX + 'src/components/layout/MobileDomainNav.vue'
APPS = PREFIX + 'src/components/portal/AppCenter.vue'
CLIENT = PREFIX + 'src/services/frappeClient.ts'
STORE = PREFIX + 'src/stores/portal.ts'
CSS = PREFIX + 'src/styles/global.css'
LIMS_BLOB = '0850f2b26b67fa0286b20ef791c51d205c2ffb5e'
GENERIC_BLOB = '2862f63f650b999d4e4a7e0b107b12e647886663'
KNOWN = {'42': set(), '43': {ROUTER, SESSION},
         '46': {ROUTER, MOBILE, APPS}, '39': {ROUTER, MOBILE, CLIENT, STORE, CSS}}
ITEM = "        { path: 'inventory/item/:itemCode?', name: 'inventory-item-readonly', component: () => import('@/views/InventoryItemReadOnlyView.vue'), meta: { title: '仓储 · 物料只读浏览' } },\n"
EXTRA_HUNKS = {'services/frappeClient.ts': [('7c1aca23d78689a86b8e394bd11ec94560ddaa50d89f8947a357e7d3be5f88e1', 'b5a65e74437f2cca6c9b48b9243b70ef34acac37fdcae4abf9aa704fac30cb8a'), ('37552ed2a0ab68a52c3d4d8a5d243b9d3989d7a52fd7ab513429b65d9ee1e644', '7c0d1ddccd2a79fb9ff62ce1a12781c926fef329a3985a5be29805378bb32e97')], 'stores/portal.ts': [('9655f3597db250bb78917edf0da222774d5b3c0a1d4f217ce7facfb83538f6ad', '5a7f817a00a8fa1e366812e021e614667e0f168c04348c3786478daf127b2c0d'), ('e542ecb44241fe6d4443d9f8a0ff2c368879d18c32e3edbc1f9490ab9441b07e', '80d721006143744894ffddfc0fe0f1b85f8fbd5a37536e82ef2469c2dd23bd44'), ('a0de4edc2935737ef7beae6e65cb5e78d24c984ef77ea1ee3da8f0e535e7692c', '5e473731f45ec3706e276b66114b80581dc2f39c788518e3fbd6e9844fcef9a7')], 'styles/global.css': [('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', '2c6e47d028c0c60dc6958360e6015ffb2504a01a4480f401dcb5f775e39e615b'), ('443f7a4401a4c3f7352078caf7cffed7107c34840a45771fb5c70ce900561c11', '9e0894b694cf03e06291e15d0247cd89bcfa4f8c7ff4390d26810b10533dfe1f')]}
CHANGED = set()
ADAPTER_DIFFS = []
AUDIT = []
EVIDENCE = None
HAS43 = False


def git(*args, check=True):
    result = subprocess.run(['git', *args], text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError('git ' + ' '.join(args) + '\n' + result.stdout + result.stderr)
    return result


def source(pr, path):
    return git('show', REFS[pr] + ':' + path).stdout


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def between(text, start, end):
    require(text.count(start) == 1 and text.count(end) == 1, 'Nonunique source span anchors: ' + start)
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


def edit(path, text, why):
    old = Path(path).read_text() if Path(path).exists() else None
    if old == text:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text)
    ADAPTER_DIFFS.extend(difflib.unified_diff((old or '').splitlines(True), text.splitlines(True), fromfile='pre-adapter/' + path, tofile='post-adapter/' + path))
    CHANGED.add(path)
    AUDIT.append({'path': path, 'reason': why,
                  'before_sha256': hashlib.sha256(old.encode()).hexdigest() if old is not None else None,
                  'after_sha256': hashlib.sha256(text.encode()).hexdigest()})


def blob(text):
    return hashlib.sha1(
        b'blob ' + str(len(text.encode())).encode() + b'\0' + text.encode()).hexdigest()


def resolve_hunks(path, pr):
    """Select only individual known conflict regions, never a complete file."""
    text = Path(path).read_text()
    pattern = re.compile(r'^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n', re.M | re.S)
    hunks = list(pattern.finditer(text))
    incoming_source = source(pr, path)
    require(hunks, 'Expected conflict markers in ' + path)
    decisions = []
    hunk_index = 0
    def pick(match):
        nonlocal hunk_index
        hunk_number = hunk_index
        hunk_index += 1
        left, right = match.group(1), match.group(2)
        require(not right or right in incoming_source, 'Incoming hunk not a fixed-source fragment: ' + path)
        extra_key = path.removeprefix(PREFIX+'src/')
        if extra_key in EXTRA_HUNKS:
            require(pr=='39', 'Extra shared conflict outside39')
            observed=(hashlib.sha256(left.encode()).hexdigest(),hashlib.sha256(right.encode()).hexdigest())
            require(hunk_number < len(EXTRA_HUNKS[extra_key]) and observed==EXTRA_HUNKS[extra_key][hunk_number], 'Unreviewed exact shared hunk drift '+path)
            decisions.append({'path':path,'hunk':hunk_number,'exact_source_hashes':observed,'policy':'preserve lifecycle; append compatible domain sections'})
            if path==CSS:
                # Disjoint LIMS ledger/audit and Inventory styles; retain both sections.
                return left+right
            if path==STORE:
                return left+right if hunk_number in (0,2) else left
            if hunk_number==0:
                # Keep generation request config plus just the Inventory error base;
                # do not duplicate the axios client declared later in43.
                error_class=between(right,'/**','const http = axios.create({')
                return left+error_class
            domain=right[right.index('export interface FrappeDocPayload {'):]
            legacy_post=between(domain,'export async function postFrappeMethod<T>(', '/**\n * 上传文件')
            domain=domain.replace(legacy_post, '''export async function postFrappeMethod<T>(method: string, params?: Record<string, unknown>): Promise<T> {
  return callFrappePostMethod<T>(method, params)
}

''',1)
            domain=domain.replace('withCsrf()', 'csrfHeaders()')
            domain=domain.replace('throw toFrappeError(error)', 'throw normalizeFrappeError(error)')
            # Remove only the now-unused legacy error parser; preserve native session probe.
            legacy_errors=between(domain,'function toFrappeError(', '/**\n * 会话是否仍然有效。')
            domain=domain.replace(legacy_errors,'',1)
            csrf='''// Inventory aliases reuse the generation-aware Portal CSRF lifecycle.
export async function ensureCsrfToken(): Promise<string> { return getCsrfToken() }
export async function csrfHeaders(): Promise<Record<string, string>> {
  return { 'X-Frappe-CSRF-Token': await getCsrfToken() }
}

'''
            return left+csrf+domain
        tokens = {
            ROUTER: ('import ', 'path:', 'component:', 'meta:', 'const ', 'name:'),
            SESSION: ('synchronize', 'runCheck', 'inflight', 'checking', 'lims|knowledge|twin', 'return ', 'disposed'),
            MOBILE: ('mobile-app-nav', 'RouterLink', 'groups', 'import ', 'isTaskView', 'go(item', 'limsCapabilities', 'const ', 'closeDrawer'),
            APPS: ('appOrder', 'iconMap'),
        }[path]
        require(any(token in left + right for token in tokens), 'Unrecognized hunk content in ' + path)
        side = 'incoming' if pr == '43' else 'current'
        decisions.append({'path': path, 'side': side,
                          'left_sha256': hashlib.sha256(left.encode()).hexdigest(),
                          'right_sha256': hashlib.sha256(right.encode()).hexdigest()})
        return right if side == 'incoming' else left
    result = pattern.sub(pick, text)
    require(not re.search(r'^(<<<<<<<|=======|>>>>>>>|\|\|\|\|\|\|\|)', result, re.M), 'Unhandled marker form in ' + path)
    edit(path, result, 'Per-conflict hunk resolution for candidate ' + pr)
    AUDIT.extend(decisions)


def insert_before(text, anchor, fragment):
    require(text.count(anchor) == 1, 'Missing/nonunique insertion anchor: ' + anchor)
    return text.replace(anchor, fragment + anchor, 1)


def normalize_router(pr):
    text = Path(ROUTER).read_text()
    # #55 remains the sole canonical Item route, even after a clean #39 merge.
    if pr == '39':
        old = source('39', ROUTER)
        item_block = between(old, '        {\n          // 主数据浏览（只读）', '        {\n          path: \'warehouse/:warehouseName?\'')
        require(text.count(item_block) <= 1, 'Duplicate original39 Item block')
        if item_block in text:
            text = text.replace(item_block, '', 1)
        text, removed = re.subn(r"^import InventoryItemView from '@/views/InventoryItemView.vue'\n", '', text, flags=re.M)
        require(removed <= 1, 'Multiple InventoryItemView imports')
        text, removed_lazy = re.subn(r"^const InventoryItemView = \(\) => import\('@/views/InventoryItemView.vue'\)\n", '', text, flags=re.M)
        require(removed_lazy <= 1, 'Multiple InventoryItemView lazy imports')
    if "name: 'inventory-item-readonly'" not in text:
        require(pr == '43', 'Canonical55 Item route disappeared outside43 conflict')
        forbidden = "        { path: '403', name: 'forbidden',"
        require(text.count(forbidden) == 1, 'Forbidden child anchor is not unique')
        line_start = text.index(forbidden)
        text = text[:line_start] + ITEM + text[line_start:]
    require(text.count("name: 'inventory-item-readonly'") == 1, 'Missing/duplicate55 Item route')
    require(not re.search(r"name:\s*'inventory-item'", text), 'Original39 Item route shadows55')
    require(len(re.findall(r"path:\s*'(?:inventory/)?item/:itemCode\?'", text)) == 1, 'Duplicate canonical Item path')
    if pr == '46':
        if "path: '/hbos/production'" not in text:
            fragment = between(source('46', ROUTER), '    {\n      // 生产看板：', "    { path: '/:pathMatch(.*)*'")
            text = insert_before(text, "    { path: '/:pathMatch(.*)*'", fragment)
        for name, module in [('ProductionLayout', '@/components/layout/ProductionLayout.vue'),
                             ('ProductionDashboardView', '@/views/ProductionDashboardView.vue')]:
            static = f"import {name} from '{module}'\n"
            lazy = f"const {name} = () => import('{module}')\n"
            require(text.count(static) <= 1 and text.count(lazy) <= 1, 'Duplicate production declaration')
            if static in text:
                text = text.replace(static, lazy, 1)
            elif lazy not in text:
                text = insert_before(text, 'const router = createRouter({', lazy + '\n')
    if pr == '39':
        if "path: '/hbos/inventory'" not in text:
            fragment = between(source('39', ROUTER), '    {\n      // 仓储库存已原生进', "    {\n      path: '/hbos/knowledge'")
            item_block = between(fragment, '        {\n          // 主数据浏览（只读）', '        {\n          path: \'warehouse/:warehouseName?\'')
            fragment = fragment.replace(item_block, '', 1)
            text = insert_before(text, "    {\n      path: '/hbos/knowledge'", fragment)
        declarations = re.findall(r"^import (Inventory\w+) from '([^']+)'$", source('39', ROUTER), re.M)
        for name, module in declarations:
            if name == 'InventoryItemView':
                continue
            static = f"import {name} from '{module}'\n"
            lazy = f"const {name} = () => import('{module}')\n"
            require(text.count(static) <= 1 and text.count(lazy) <= 1, 'Duplicate inventory declaration')
            if static in text:
                text = text.replace(static, lazy, 1)
            elif lazy not in text:
                text = insert_before(text, 'const router = createRouter({', lazy + '\n')
    # Ensure no stale eager imports reappear in43 conflicts.
    if HAS43 or pr == '43':
        require("router.beforeEach((to) => checkPortalAccess(to, usePortalStore(), portalDataSource))" in text, 'Lost43 router guard')
        lims = between(source('43', ROUTER), "    {\n      path: '/hbos/lims'", "    {\n      path: '/hbos/knowledge'")
        require(lims in text, 'Changed43 LIMS route/capability section')
    edit(ROUTER, text, 'Preserve43 lazy guard and55 Item; compose domain-specific route sections')


def normalize_session(pr):
    if pr != '43':
        return
    text = Path(SESSION).read_text()
    pattern = r'\(lims\|knowledge\|twin(?:\|inventory)?\)'
    require(len(re.findall(pattern, text)) == 2, 'Expected two protected session regexes')
    text = re.sub(pattern, '(lims|knowledge|twin|inventory)', text)
    for fragment in ['let inflight: Promise<boolean> | null = null', 'async function runCheck(): Promise<boolean>',
                     'async function synchronize(): Promise<boolean>', 'return { sessionPending, sessionError, synchronize }']:
        require(text.count(fragment) == 1, 'Lost43 session lifecycle fragment: ' + fragment)
    require('checking = ' not in text, 'Old boolean session lifecycle survived')
    edit(SESSION, text, '43 lifecycle paragraphs plus55 inventory revalidation in both regexes')


def normalize_mobile(pr):
    if pr not in ('46', '39') or not HAS43:
        return
    require(blob(source('43', MOBILE)) == LIMS_BLOB, '43 mobile immutable source drift')
    generic = source(pr, MOBILE)
    require(blob(generic) == GENERIC_BLOB, 'Generic domain mobile source drift')
    text = Path(MOBILE).read_text()
    # These nonconflicting46/39 additions must also be removed after hunk selection.
    added = between(generic, 'export interface MobileNavEntry {', 'const drawerOpen = ref(false)')
    if added in text:
        text = text.replace(added, '', 1)
    # Default drawer title changed in a clean nonconflicting source hunk.
    if ':title="drawerTitle"' in text:
        require(text.count(':title="drawerTitle"') == 1, 'Duplicate drawer title')
        text = text.replace(':title="drawerTitle"', 'title="LIMS 导航"', 1)
    require(blob(text) == LIMS_BLOB, 'LIMS mobile differs from reviewed43 after explicit hunk adapters; inspect saved diff')
    edit(MOBILE, text, 'Remove only generic additions from LIMS implementation')
    #43 openBusinessRoute is explicitly nullable on denied/unavailable routes;
    # the existing go() already returns when !item.to. Reflect that contract,
    # without inventing a fallback path or widening navigation.
    require(generic.count('  to?: string\n')==1,'Generic target type anchor drift')
    domain_generic=generic.replace('  to?: string\n','  to?: string | null\n',1)
    require(not Path(DOMAIN).exists() or Path(DOMAIN).read_text() == domain_generic, 'Unexpected existing MobileDomainNav')
    edit(DOMAIN, domain_generic, 'New domain module; nullable denied route matches43 contract and existing fail-closed go')
    layout = PREFIX + 'src/components/layout/' + ('ProductionLayout.vue' if pr == '46' else 'InventoryLayout.vue')
    content = Path(layout).read_text()
    old = "from '@/components/layout/MobileAppNav.vue'"
    new = "from '@/components/layout/MobileDomainNav.vue'"
    require(content.count(old) == 1 and content.count(new) == 0, 'Layout import anchor drift: ' + layout)
    edit(layout, content.replace(old, new, 1), 'Only domain layout module specifier changed; alias/template preserved')


def normalize_shared39(pr):
    if pr!='39' or not HAS43:
        return
    text=Path(STORE).read_text()
    require('sessionGeneration' not in text, 'Obsolete39 lifecycle survived')
    require(text.count('    bootstrapError.value = null\n')==1,'bootstrap reset anchor drift')
    text=text.replace('    bootstrapError.value = null\n','    bootstrapError.value = null\n    bootstrapErrorStatus.value = 0\n',1)
    reset='    bootstrapError.value = summariesError.value = tasksError.value = null\n'
    require(text.count(reset)==1,'session reset anchor drift')
    text=text.replace(reset,reset+'    bootstrapErrorStatus.value = 0\n',1)
    old="""          if (isAuthError(error)) markSignedOut()
          else {
            authenticated.value = false
            sessionChecked.value = false
            bootstrapError.value = portalErrorMessage(error, 'HBOS 初始化失败，请稍后重试。')
          }"""
    new="""          if (isAuthError(error)) {
            markSignedOut()
            bootstrapErrorStatus.value = 401
          } else {
            const described = await describeBootstrapError(error)
            if (current !== generation) return
            authenticated.value = false
            sessionChecked.value = false
            bootstrapErrorStatus.value = described.status
            bootstrapError.value = described.message
          }"""
    require(text.count(old)==1,'43 bootstrap catch anchor drift')
    text=text.replace(old,new,1)
    edit(STORE,text,'Preserve43 single-flight generation guards plus39 error status; recheck generation after asynchronous probe')
    client=Path(CLIENT).read_text()
    for token in ['const http = axios.create(', 'let csrfToken:', 'let csrfGeneration =', 'export async function callFrappeAction<', 'export async function callFrappePostMethod<']:
        require(client.count(token)==1,'Client lifecycle duplicate/loss: '+token)
    require('cachedCsrf' not in client and 'withCsrf' not in client,'Legacy39 CSRF cache survived')


def normalize_apps(pr):
    if pr != '46':
        return
    text = Path(APPS).read_text()
    if HAS43:
        require("import { iconMap } from '@/components/appIcons'" in text, 'Lost43 shared app icons')
        require('const iconMap:' not in text, 'Obsolete46 local iconMap survived')
    old = "const appOrder = ['lims', 'inventory', 'attendance', 'knowledge', 'equipment', 'twin']"
    new = old[:-1] + ", 'production']"
    require(text.count(old) + text.count(new) == 1, 'App order anchor drift')
    if old in text:
        text = text.replace(old, new, 1)
    require('仓储 · 物料只读浏览' in text and '/hbos/inventory/item' in text, 'Lost55 separate Item entry')
    edit(APPS, text, '43 shared icon map plus46 production order and55 Item entry')


def identity():
    return git('show', '-s', '--format=commit=%H tree=%T parents=%P').stdout.strip()


def write_tests(has43, full):
    path = PREFIX + 'tests/ownerComposition.test.ts'
    require(not Path(path).exists(), 'Refuse to overwrite an existing composition test')
    test = """import { expect, it } from 'vitest'
import router from '@/router'
it('owner composition retains the unique55 canonical Item list/detail route', () => {
  for (const path of ['/hbos/inventory/item', '/hbos/inventory/item/SAP%2F001?q=A']) {
    const route = router.resolve(path)
    expect(route.name).toBe('inventory-item-readonly')
    expect(route.matched[0]?.path).toBe('/hbos')
  }
  expect(router.getRoutes().filter(r => r.path === '/hbos/inventory/item/:itemCode?')).toHaveLength(1)
  expect(router.getRoutes().some(r => r.name === 'inventory-item')).toBe(false)
})
"""
    if has43:
        test += """it('owner composition preserves43 capability-aware LIMS routes and lazy pages', () => {
  const expected = [['/hbos/lims/tasks', 'lims-tasks', 'tasks'], ['/hbos/lims/ledger', 'lims-ledger', 'ledger'], ['/hbos/lims/retains/usage', 'lims-retains-usage', 'retains'], ['/hbos/lims/stability/trend', 'lims-stability-trend', 'stability'], ['/hbos/lims/audit', 'lims-audit', 'audit']]
  for (const [path, name, capability] of expected) {
    const route = router.resolve(path!)
    expect(route.name).toBe(name)
    expect(route.meta.requiresAuth).toBe(true)
    expect(route.meta.limsCapability).toBe(capability)
    expect(typeof route.matched.at(-1)?.components?.default).toBe('function')
  }
})
"""
    if full:
        test += """it('owner composition registers all domain roots while keeping the real404', () => {
  expect(router.resolve('/hbos/attendance').name).toBe('attendance-dashboard')
  expect(router.resolve('/hbos/production/center').name).toBe('production-center')
  expect(router.resolve('/hbos/inventory').name).toBe('inventory-overview')
  expect(router.resolve('/owner-nonexistent-route').name).toBe('not-found')
})
"""
    edit(path, test, 'Additional cloud-only regression tests; original tests unchanged')


def merge(pr):
    global CHANGED, HAS43, ADAPTER_DIFFS
    CHANGED = set()
    ADAPTER_DIFFS = []
    before = git('rev-parse', 'HEAD').stdout.strip()
    step = EVIDENCE / pr
    step.mkdir(parents=True, exist_ok=False)
    (step / 'before.txt').write_text(identity() + '\n')
    result = git('merge', '--no-ff', '--no-edit', REFS[pr], check=False)
    (step / 'merge.log').write_text(result.stdout + result.stderr)
    conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
    (step / 'raw-conflicts.diff').write_text(git('diff', '--cc').stdout)
    for path in conflicts:
        copy = step / 'raw-files' / path
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_text(Path(path).read_text())
    require(not set(conflicts) - KNOWN[pr], 'Unreviewed conflicts; stopped: ' + ', '.join(sorted(set(conflicts)-KNOWN[pr])))
    require(result.returncode == 0 or conflicts, 'Merge failed without a recognized content conflict')
    for path in conflicts:
        resolve_hunks(path, pr)
    normalize_router(pr)
    normalize_session(pr)
    normalize_mobile(pr)
    normalize_apps(pr)
    normalize_shared39(pr)
    if pr == '43':
        HAS43 = True
    git('diff', '--check')
    for path in CHANGED:
        require(not re.search(r'^(<<<<<<<|=======|>>>>>>>|\|\|\|\|\|\|\|)', Path(path).read_text(), re.M), 'Unresolved marker: ' + path)
    if CHANGED or conflicts:
        git('add', '--', *sorted(CHANGED | set(conflicts)))
    # Save original-source-to-adapter differences for every touched existing/new file.
    adapter = []
    for path in sorted(CHANGED):
        adapter.append(git('diff', before, '--', path).stdout)
    (step / 'source-plus-adapter.diff').write_text(''.join(adapter))
    (step / 'adapter.diff').write_text(''.join(ADAPTER_DIFFS))
    (step / 'audit.json').write_text(json.dumps(AUDIT, ensure_ascii=False, indent=2) + '\n')
    if Path(git('rev-parse', '--git-path', 'MERGE_HEAD').stdout.strip()).exists():
        git('commit', '--no-edit')
    elif git('diff', '--cached', '--quiet', check=False).returncode:
        git('commit', '-m', 'test: explicit owner cloud composition adapter ' + pr)
    require(not git('status', '--porcelain').stdout.strip(), 'Unexpected dirty state after adapter commit')
    (step / 'after.txt').write_text(identity() + '\n')
    (step / 'complete.diff').write_text(git('diff', before, 'HEAD').stdout)
    print('[OWNER-COMPOSE] ' + pr + ' ' + identity(), flush=True)


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['single', 'full'])
    parser.add_argument('sha', nargs='?')
    parser.add_argument('--evidence-dir', help='Default: /tmp/hbos-composition/full or single-PR')
    parser.add_argument('--no-add-tests', action='store_true')
    args = parser.parse_args()
    require(args.mode != 'full' or args.sha is None, 'full takes no candidate SHA')
    require(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('CI') == 'true', 'Runner-only: refusing local execution')
    require(git('rev-parse', 'HEAD').stdout.strip() == BASE, 'Start on exact new product baseline ' + BASE)
    require(not git('status', '--porcelain').stdout.strip(), 'Start in a clean checkout; keep this script/evidence outside repository')
    require(not Path('.env').exists(), 'Refuse an existing environment file')
    sequence = ['42', '43', '46', '39'] if args.mode == 'full' else [next((p for p,s in REFS.items() if s == args.sha), '')]
    require(all(sequence), 'single requires one reviewed full candidate SHA')
    stage_name = 'full' if args.mode == 'full' else 'single-' + sequence[0]
    EVIDENCE = Path(args.evidence_dir or ('/tmp/hbos-composition/' + stage_name)).resolve()
    require(not EVIDENCE.exists(), 'Use a new evidence directory')
    EVIDENCE.mkdir(parents=True)
    git('config', 'user.name', 'HBOS Owner Cloud Composition')
    git('config', 'user.email', 'owner-cloud@example.invalid')
    for pr in sequence:
        if git('cat-file', '-e', REFS[pr] + '^{commit}', check=False).returncode:
            git('fetch', '--no-tags', 'origin', REFS[pr])
    # Sources needed by section checks are immutable and fetched explicitly.
    for pr in ['43', '39']:
        if git('cat-file', '-e', REFS[pr] + '^{commit}', check=False).returncode:
            git('fetch', '--no-tags', 'origin', REFS[pr])
    (EVIDENCE / 'inputs.json').write_text(json.dumps({'base': BASE, 'sources': REFS, 'mode': args.mode}, indent=2)+'\n')
    for pr in sequence:
        merge(pr)
    if not args.no_add_tests:
        write_tests('43' in sequence, args.mode == 'full')
        test = PREFIX + 'tests/ownerComposition.test.ts'
        git('add', '--', test)
        git('commit', '-m', 'test: cloud-only composition route regression coverage')
    # Original42 adds a blank EOF in one test file. Remove only that extra
    # newline in this ephemeral adapter; no assertions or test bodies change.
    pairing='apps/hb_attendance_app/tests/test_pairing.py'
    if '42' in sequence:
        raw=Path(pairing).read_text()
        require(raw.endswith('\n\n'),'Reviewed42 EOF shape drift')
        edit(pairing,raw.rstrip('\n')+'\n','Remove only extra blank EOF from42 test; assertions unchanged')
        git('add','--',pairing)
        git('commit','-m','test: normalize original42 extra blank EOF in cloud candidate')
    check=git('diff','--check',BASE,'HEAD',check=False)
    if check.returncode:
        (EVIDENCE/'whitespace-before.txt').write_text(check.stdout+check.stderr)
        print(check.stdout+check.stderr,flush=True)
        raise RuntimeError('Composition whitespace check failed; inspect whitespace-before.txt')
    (EVIDENCE / 'final.txt').write_text(identity() + '\n')
    (EVIDENCE / 'final.diff').write_text(git('diff', BASE, 'HEAD').stdout)
    (EVIDENCE / 'audit.json').write_text(json.dumps(AUDIT,ensure_ascii=False,indent=2)+'\n')
    print('[OWNER-COMPOSE] READY_FOR_TESTS ' + identity(), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if EVIDENCE:
            (EVIDENCE / 'FAILED.txt').write_text(str(error)+'\n')
        print('[OWNER-COMPOSE] STOP: ' + str(error), file=sys.stderr)
        sys.exit(1)
