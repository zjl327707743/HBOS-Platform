/**
 * Raw geometry receipts for the v1.7 prototype comparison.
 *
 * Purpose: the reviewer/Main asked for raw measurement receipts with file+line,
 * and for P05 to report the canvas boundary and the paper boundary separately
 * instead of one mixed "paper top" number. This script measures both sides live,
 * captures the raw 320x500 P05 pair, and records where each measurement is
 * asserted in qa/final-check.mjs.
 *
 *   HBOS_CHROME_CDP_PORT=9333 node previews/knowledge-v17/qa/raw-geometry-receipts.mjs
 */
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { execSync } from 'node:child_process'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { evaluate, navigate, resize, shot, close, send } from '../browser/cdp.mjs'

const origin = 'http://127.0.0.1:18650'
const base = '/hbos/knowledge'
const root = resolve(new URL('../../..', import.meta.url).pathname)
const output = process.env.HBOS_V17_RAW_OUT || '/Users/hb/Projects/HBOS/knowledge-rebuild-20261102/outputs/v17-final/raw-geometry'
const prototype = pathToFileURL(resolve(process.env.HBOS_FROZEN_PROTOTYPE || '/Users/hb/Downloads/HBOS_知识库_高保真交互原型_v1.7.html')).href
const sha = buffer => createHash('sha256').update(buffer).digest('hex')
const shaFile = async path => sha(await readFile(path))
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
const finalCheck = await readFile(resolve(root, 'previews/knowledge-v17/qa/final-check.mjs'), 'utf8')
const sourceLine = needle => {
  const index = finalCheck.indexOf(needle)
  return index < 0 ? null : finalCheck.slice(0, index).split('\n').length
}
const source = (needle, note) => ({ file: 'previews/knowledge-v17/qa/final-check.mjs', line: sourceLine(needle), note })
await mkdir(output + '/raw', { recursive: true })
await send('Page.addScriptToEvaluateOnNewDocument', { source: "if(location.origin==='http://127.0.0.1:18650') sessionStorage.clear()" })
const box = selector => {
  const el = document.querySelector(selector)
  if (!el) return null
  const rect = el.getBoundingClientRect()
  const computed = getComputedStyle(el)
  return { y: Math.round(rect.y), x: Math.round(rect.x), w: Math.round(rect.width), h: Math.round(rect.height), padding: computed.padding, background: computed.backgroundColor }
}
const candidateProbe = () => {
  const b = selector => document.querySelector(selector)
  const measure = selector => {
    const el = b(selector); if (!el) return null
    const rect = el.getBoundingClientRect(); const computed = getComputedStyle(el)
    return { y: Math.round(rect.y), x: Math.round(rect.x), w: Math.round(rect.width), h: Math.round(rect.height), padding: computed.padding, background: computed.backgroundColor }
  }
  return {
    heading: measure('.kb-heading'),
    panel: measure('.v17-panel, .kb-panel'),
    identity: measure('[data-reader-identity]'),
    toolbar: measure('.kb-pdf-toolbar'),
    surface: measure('.kb-pdf-surface'),
    canvas: measure('.kb-pdf-surface canvas'),
    firstRow: measure('.v17-version-list .kb-doc-row, .kb-doc-row, .kb-staff-feedback-item'),
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }
}
const referenceProbe = () => {
  const measure = selector => {
    const el = document.querySelector(selector); if (!el) return null
    const rect = el.getBoundingClientRect(); const computed = getComputedStyle(el)
    return { y: Math.round(rect.y), x: Math.round(rect.x), w: Math.round(rect.width), h: Math.round(rect.height), padding: computed.padding, background: computed.backgroundColor }
  }
  return {
    head: measure('.page-head'),
    panel: measure('#view .panel, #view .list-panel'),
    stage: measure('#paper-stage'),
    paper: measure('#paper-stage .paper'),
    identity: measure('.reader-identity'),
    toolbar: measure('.reader-toolbar'),
    firstRow: measure('.version-row, .activity-panel .docrow, .feedback-item'),
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }
}
const targets = [
  { key: 'P05', path: '/document/DOC_DEMO_001', wait: "document.querySelector('[data-pdf-rendered]')", prototypeHash: '#/hbos/knowledge/document/DOC_DEMO_001' },
  { key: 'P06', path: '/maintenance', wait: "document.querySelector('.v17-panel')", prototypeHash: '#/hbos/knowledge/maintenance' },
  { key: 'P07', path: '/maintenance/upload', wait: "document.querySelector('.v17-panel')", prototypeHash: '#/hbos/knowledge/maintenance/upload' },
  { key: 'P08', path: '/maintenance/versions', wait: "document.querySelector('.v17-version-list .kb-doc-row')", prototypeHash: '#/hbos/knowledge/maintenance/versions' },
  { key: 'P09', path: '/maintenance/feedback', wait: "document.querySelector('.kb-staff-feedback-item')", prototypeHash: '#/hbos/knowledge/maintenance/feedback' },
]
const viewports = [{ w: 320, h: 500 }, { w: 390, h: 844 }, { w: 1165, h: 757 }]
const receipt = {
  schema: 'hbos.knowledge-ui-v3.raw-geometry-receipts.v1',
  at_utc: new Date().toISOString(),
  frontend_sha: execSync('git rev-parse HEAD', { cwd: root }).toString().trim(),
  worktree_dirty: execSync('git status --porcelain --untracked-files=no', { cwd: root }).toString().trim().length > 0,
  prototype,
  measurements: {},
  source_references: {
    candidate_geometry: source("readerPaper: box('.kb-pdf-surface canvas')", 'candidate probes the rendered canvas'),
    reference_geometry: source("readerPaper: box('#paper-stage .paper')", 'prototype probes the paper element'),
    geometry_standard: source('Math.abs(delta) <= 2', 'fixed-anchor standard used for PASS; otherwise DIFFERENCE_RECORDED'),
    p07_card: source("page.key === 'P07' && vue.maintenancePanel", 'P07 main card comparison in final-check'),
  },
}
try {
  for (const viewport of viewports) {
    await resize(viewport.w, viewport.h)
    for (const target of targets) {
      await navigate('about:blank'); await navigate(origin + base + target.path + '?state=visual')
      for (let i = 0; i < 100 && !(await evaluate(target.wait)); i++) await pause(80)
      await pause(250)
      const candidate = await evaluate('(' + candidateProbe.toString() + ')()')
      await navigate('about:blank'); await navigate(prototype + target.prototypeHash); await pause(320)
      const reference = await evaluate('(' + referenceProbe.toString() + ')()')
      receipt.measurements[`${target.key}-${viewport.w}x${viewport.h}`] = { viewport, candidate, reference }
    }
  }
  // Raw P05 pair at 320x500 (no collage, no scaling), both hashes recorded.
  await resize(320, 500)
  await navigate('about:blank'); await navigate(origin + base + '/document/DOC_DEMO_001?state=visual')
  for (let i = 0; i < 100 && !(await evaluate("document.querySelector('[data-pdf-rendered]')")); i++) await pause(80)
  await pause(300)
  const candidateShot = output + '/raw/P05-candidate-320x500-' + receipt.frontend_sha.slice(0, 7) + '.png'
  await shot(candidateShot)
  await navigate('about:blank'); await navigate(prototype + '#/hbos/knowledge/document/DOC_DEMO_001'); await pause(350)
  const referenceShot = output + '/raw/P05-reference-320x500-prototype.png'
  await shot(referenceShot)
  const p05 = receipt.measurements['P05-320x500']
  receipt.p05_raw_pair = {
    candidate_png: candidateShot, candidate_png_sha256: await shaFile(candidateShot), candidate_pixels: '320x500',
    reference_png: referenceShot, reference_png_sha256: await shaFile(referenceShot), reference_pixels: '320x500',
    candidate_canvas_boundary: p05?.candidate?.canvas || null,
    candidate_paper_container_boundary: p05?.candidate?.surface || null,
    reference_paper_boundary: p05?.reference?.paper || null,
    reference_stage_boundary: p05?.reference?.stage || null,
    interpretation: 'Candidate is a rendered PDF canvas (page pixels) inside the padded .kb-pdf-surface container; the prototype paper is an HTML article inside #paper-stage. The two boundaries are reported separately. The visible page top difference is recorded; it does not meet the ±2px fixed-anchor standard and is not counted as a fidelity PASS.',
  }
  await writeFile(output + '/RAW_GEOMETRY_RECEIPTS.json', JSON.stringify(receipt, null, 2))
  console.log('RAW GEOMETRY', JSON.stringify({
    sha: receipt.frontend_sha,
    p05_candidate_canvas_y: receipt.p05_raw_pair.candidate_canvas_boundary?.y,
    p05_candidate_surface_y: receipt.p05_raw_pair.candidate_paper_container_boundary?.y,
    p05_reference_paper_y: receipt.p05_raw_pair.reference_paper_boundary?.y,
    p05_reference_stage_y: receipt.p05_raw_pair.reference_stage_boundary?.y,
    p07: receipt.measurements['P07-320x500'] && { candidate: receipt.measurements['P07-320x500'].candidate.panel?.y, reference: receipt.measurements['P07-320x500'].reference.panel?.y },
    output,
  }))
} finally {
  close()
}
