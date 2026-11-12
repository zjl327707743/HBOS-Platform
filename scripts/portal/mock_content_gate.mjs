/**
 * HBOS Portal 前端 Mock 内容门禁（test:mock-gate）。
 *
 * 目标：正式 frappe 发布构建不得以 Mock 数据模式发布，也不得把 Mock
 * 数据模块变成正式包的可加载内容。脚本扫描构建产物目录（默认
 * `frontend/hbos-portal-web/dist`，可用 --dist 覆盖）：
 *
 *  1. 入口 JS 中编译进的数据模式常量必须是 "frappe"（Vite 会把
 *     import.meta.env.VITE_PORTAL_DATA_MODE 内联成 `const x="frappe"`）；
 *     出现 `const x="mock"` 即判泄漏。数据模式在构建时固化，运行时不可
 *     再切换，这是 frappe 发布的第一道保证。
 *  2. Mock 数据模块 chunk（mockPortal-*.js）不允许出现在 frappe 产物中：
 *     动态 import() 会让 Rollup 保留 chunk 文件；正式包不应携带可加载
 *     的 Mock 数据集。
 *  3. 产物必须存在（index.html + 至少一个 JS 分块），空目录直接失败。
 *
 * 注意：源码里合法存在的 `portalDataSource === 'mock'` 分支（构建后变成
 * `"frappe"==="mock"` 的常量比较）不判泄漏——模式常量本身才是判据。
 * Mock 作为开发模式（dev:mock / build:mock）允许保留。
 *
 * 负例自检：`--self-test` 用临时目录内的合成泄漏产物验证门禁确实会
 * 拒绝（退出码 1），防止脚本退化为永远 PASS 的空门禁。
 *
 * 用法：
 *   node scripts/portal/mock_content_gate.mjs [--dist <dir>] [--self-test]
 *   （package.json: `npm run test:mock-gate`，在 frontend/hbos-portal-web 内）
 */
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
// 使用前端已锁定的直接依赖，不执行产物；字符串、注释和相等比较不是模式赋值。
const requireFrontend = createRequire(path.join(repoRoot, 'frontend/hbos-portal-web/package.json'))
const ts = requireFrontend('typescript')

function assignedModes(content, filename) {
  const source = ts.createSourceFile(filename, content, ts.ScriptTarget.Latest, false, ts.ScriptKind.JS)
  if (source.parseDiagnostics.length) throw new Error('JS 分块无法解析，不能确认数据模式')
  const modes = new Set()
  const pending = [source]
  while (pending.length) {
    const node = pending.pop()
    let value = ts.isVariableDeclaration(node) ? node.initializer
      : ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.EqualsToken ? node.right : undefined
    while (value && ts.isParenthesizedExpression(value)) value = value.expression
    if (value && ts.isStringLiteralLike(value) && ['frappe', 'mock'].includes(value.text)) modes.add(value.text)
    ts.forEachChild(node, child => { pending.push(child) })
  }
  return modes
}

function listFiles(distDir) {
  const files = []
  const walk = dir => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(full)
      else files.push(full)
    }
  }
  walk(distDir)
  return files
}

function scanDirectory(distDir) {
  if (!fs.existsSync(distDir)) {
    return { ok: false, errors: [`构建目录不存在：${distDir}（先运行正式构建）`] }
  }
  if (!fs.existsSync(path.join(distDir, 'index.html'))) {
    return { ok: false, errors: ['构建目录缺少 index.html'] }
  }
  const files = listFiles(distDir)
  const jsFiles = files.filter(file => file.endsWith('.js'))
  if (!jsFiles.length) {
    return { ok: false, errors: ['构建目录没有任何 JS 分块，产物不完整'] }
  }
  const rel = file => path.relative(repoRoot, file)
  const errors = []

  // 1) 编译进包的数据模式常量必须是 "frappe"。
  //    Vite 把 import.meta.env.VITE_PORTAL_DATA_MODE 内联成字符串常量，
  //    产物形态如 `an="frappe"` / `const an="frappe"`（逗号或 const 起头
  //    都会出现，取决于压缩上下文）。
  let sawModeConstant = false
  for (const file of jsFiles) {
    const content = fs.readFileSync(file, 'utf8')
    try {
      const modes = assignedModes(content, file)
      if (modes.has('frappe')) sawModeConstant = true
      if (modes.has('mock')) errors.push(`${rel(file)}：数据模式常量为 "mock"（VITE_PORTAL_DATA_MODE 泄漏）`)
    } catch (error) { errors.push(`${rel(file)}：${error.message}`) }
  }
  if (!sawModeConstant) {
    errors.push('产物中未找到 "frappe" 数据模式常量；无法证明这是 frappe 构建（入口被改坏或模式未固化）')
  }

  // 2) Mock 数据模块 chunk 不允许出现在正式产物中。
  for (const file of jsFiles) {
    if (/mockPortal-[^/]*\.js$/.test(path.basename(file))) {
      errors.push(`${rel(file)}：正式产物包含 Mock 数据模块 chunk`)
    }
  }

  return { ok: errors.length === 0, errors }
}

function selfTest() {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'hbos-mock-gate-'))
  const failure = []

  const make = dir => {
    fs.mkdirSync(path.join(dir, 'assets'), { recursive: true })
    fs.writeFileSync(path.join(dir, 'index.html'), '<html><script type="module" src="./assets/index.js"></script></html>')
    return path.join(dir, 'assets')
  }

  // 正例：干净的 frappe 产物必须通过。
  const cleanAssets = make(path.join(base, 'clean'))
  fs.writeFileSync(path.join(cleanAssets, 'index.js'), 'const e="frappe";const portalDataSource=e;portalDataSource==="mock"&&f()')
  const cleanResult = scanDirectory(path.join(base, 'clean'))
  if (!cleanResult.ok) failure.push(`干净产物被误判失败：${cleanResult.errors.join('；')}`)

  // 正例：普通文案、代码示例、注释和比较中的 mock 不应被当成赋值。
  const copyAssets = make(path.join(base, 'copy'))
  fs.writeFileSync(path.join(copyAssets, 'index.js'), [
    'const e="frappe";const message=\'Mock · 演示汇总；const mode="mock"\';',
    'const example=`const mode="mock"`;const labels={mock:"mock"};',
    '// const mode="mock"',
    '/* const mode="mock" */ console.log("mock",e==="mock",e!=="mock");',
  ].join('\n'))
  const copyResult = scanDirectory(path.join(base, 'copy'))
  if (!copyResult.ok) failure.push(`无关文案被误判：${copyResult.errors.join('；')}`)

  // 混合负例必须真的命中 mock，不能只是因缺少 frappe 而碰巧失败。
  const mixedSources = [
    'const activeMode="mock";const otherMode="frappe";',
    'const otherMode="frappe";const activeMode="mock";',
    'const otherMode="frappe";let activeMode="mock";',
    'const otherMode="frappe";var activeMode="mock";',
    'const otherMode="frappe",activeMode="mock";',
    'const otherMode="frappe";let activeMode;activeMode="mock";',
    'const otherMode="frappe";const activeMode=("mock");',
    'const otherMode="frappe";const activeMode=`mock`;',
  ]
  mixedSources.forEach((content, index) => {
    const dir = path.join(base, `mixed-${index}`), assets = make(dir)
    fs.writeFileSync(path.join(assets, 'index.js'), content)
    const result = scanDirectory(dir)
    if (result.ok || !result.errors.some(error => error.includes('数据模式常量为 "mock"'))) failure.push(`混合模式漏检：${content}`)
  })
  const splitDir = path.join(base, 'split'), splitAssets = make(splitDir)
  fs.writeFileSync(path.join(splitAssets, 'index.js'), 'const e="frappe";import("./other.js");')
  fs.writeFileSync(path.join(splitAssets, 'other.js'), 'export const mode="mock";')
  if (scanDirectory(splitDir).ok) failure.push('跨分块的混合模式漏检')

  const quotedDir = path.join(base, 'quoted'), quotedAssets = make(quotedDir)
  fs.writeFileSync(path.join(quotedAssets, 'index.js'), 'const text=\'const e="frappe"\';')
  if (scanDirectory(quotedDir).ok) failure.push('字符串中的 frappe 被误当成模式赋值')

  // 负例 1：mock 模式常量必须被拒绝。
  const leakModeAssets = make(path.join(base, 'leak-mode'))
  fs.writeFileSync(path.join(leakModeAssets, 'index.js'), 'const e="mock";const portalDataSource=e')
  if (scanDirectory(path.join(base, 'leak-mode')).ok) failure.push('mock 模式常量未被识别（门禁失效）')

  // 负例 2：mockPortal chunk 必须被拒绝。
  const leakChunkAssets = make(path.join(base, 'leak-chunk'))
  fs.writeFileSync(path.join(leakChunkAssets, 'index.js'), 'const e="frappe";const portalDataSource=e')
  fs.writeFileSync(path.join(leakChunkAssets, 'mockPortal-CV6v7swY.js'), 'export const portalUser={}')
  if (scanDirectory(path.join(base, 'leak-chunk')).ok) failure.push('mockPortal chunk 未被识别（门禁失效）')

  // 负例 3：既无 frappe 也无 mock 常量（无法证明模式）必须被拒绝。
  const noModeAssets = make(path.join(base, 'no-mode'))
  fs.writeFileSync(path.join(noModeAssets, 'index.js'), 'console.log("hello")')
  if (scanDirectory(path.join(base, 'no-mode')).ok) failure.push('缺少模式常量的产物未被拒绝（门禁失效）')

  // 负例 4：空目录必须被拒绝。
  const empty = path.join(base, 'empty')
  fs.mkdirSync(empty, { recursive: true })
  if (scanDirectory(empty).ok) failure.push('空构建目录未被拒绝（门禁失效）')

  fs.rmSync(base, { recursive: true, force: true })
  return { ok: failure.length === 0, errors: failure }
}

const args = process.argv.slice(2)
if (args.includes('--self-test')) {
  const result = selfTest()
  if (!result.ok) {
    console.error('MOCK GATE SELF-TEST FAIL')
    for (const line of result.errors) console.error(`  - ${line}`)
    process.exit(1)
  }
  console.log('MOCK GATE SELF-TEST PASS（正例接受、负例拒绝均生效）')
  process.exit(0)
}

const distIndex = args.indexOf('--dist')
const distDir = distIndex >= 0 ? path.resolve(args[distIndex + 1]) : path.join(repoRoot, 'frontend/hbos-portal-web/dist')
const result = scanDirectory(distDir)
if (!result.ok) {
  console.error(`MOCK GATE FAIL：${distDir}`)
  for (const line of result.errors) console.error(`  - ${line}`)
  console.error('正式构建必须以 frappe 模式产出且不携带 Mock 数据模块；演示构建请使用 npm run build:mock 并输出到独立目录。')
  process.exit(1)
}
console.log(`MOCK GATE PASS：${distDir} 为 frappe 模式产物，未发现 Mock 泄漏`)
