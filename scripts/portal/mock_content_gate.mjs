import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../../frontend/hbos-portal-web/', import.meta.url))
const require = createRequire(`${root}package.json`)
const { parse } = require('@vue/compiler-sfc')
const { parse: parseTemplate, NodeTypes } = require('@vue/compiler-dom')
const demoText = /扫码入库|Inventory Quick Action|LIVE READY|演示模式只读|演示数据|A \/ B/

export function checkMockTemplate(template) {
  const errors = []
  function visit(node, gated = false) {
    const condition = node.props?.find(prop => prop.type === NodeTypes.DIRECTIVE && prop.name === 'if')?.exp?.content || ''
    gated ||= /(?:portal\.dataSource|portalDataSource)\s*===\s*['"]mock['"]/.test(condition)
    if (node.type === NodeTypes.TEXT && demoText.test(node.content) && !gated) errors.push(node.content.trim())
    for (const prop of node.props || []) {
      if (prop.type === NodeTypes.ATTRIBUTE && demoText.test(prop.value?.content || '') && !gated) errors.push(prop.value.content)
    }
    for (const child of node.children || []) visit(child, gated)
  }
  visit(parseTemplate(template))
  return errors
}

export function runMockContentGate() {
  function scan(dir) {
    for (const file of readdirSync(dir, { withFileTypes: true })) {
      const path = `${dir}/${file.name}`
      if (file.isDirectory()) scan(path)
      else if (file.name.endsWith('.vue')) {
        const { descriptor } = parse(readFileSync(path, 'utf8'))
        if (descriptor.template) assert.deepEqual(checkMockTemplate(descriptor.template.content), [], `${path}: Mock 专用内容必须显式门控`)
      }
    }
  }
  scan(`${root}src`)
  const provider = readFileSync(`${root}src/services/portalProvider.ts`, 'utf8')
  assert.doesNotMatch(provider, /import\s*{[^}]*}\s*from\s*['"]@\/data\/mockPortal/s, 'Portal 演示数据必须动态加载')
  console.log('MOCK CONTENT GATE PASS（模板门控 + Portal 演示数据动态加载）')
}
if (process.argv[1] === fileURLToPath(import.meta.url)) runMockContentGate()
