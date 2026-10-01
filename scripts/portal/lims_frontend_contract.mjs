import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../frontend/hbos-portal-web/src')
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8')

const capabilities = read('services/limsCapabilities.ts')
assert.match(capabilities, /lims\.results\.read/)
assert.match(capabilities, /lims\.ledger\.read/)
assert.match(capabilities, /lims\.retention\.read/)
assert.doesNotMatch(capabilities, /\| 'management'/)

for (const service of ['limsResults.ts', 'limsLedger.ts', 'limsAudit.ts', 'limsCoa.ts', 'limsSpecifications.ts', 'limsRetention.ts', 'limsStability.ts']) {
  assert.match(read(`services/${service}`), /unwrapPortalMethod/)
}

const stability = read('services/limsStability.ts')
assert.match(stability, /limit: params\.limit \|\| 50/)
assert.match(stability, /function emptyStabilityEnvelope/)

const router = read('router/index.ts')
assert.match(router, /component: LimsLayout/)
assert.match(router, /import\('@\/views\/LimsResultEntryView\.vue'\)/)

const navigation = read('services/businessNavigation.ts')
assert.match(navigation, /decodeURIComponent/)
assert.match(navigation, /name: 'forbidden'/)

const styles = read('styles/global.css')
assert.match(styles, /grid-template-columns: minmax\(0, 1\.28fr\) minmax\(250px, \.72fr\)/)

console.log('LIMS FRONTEND CONTRACT PASS')
