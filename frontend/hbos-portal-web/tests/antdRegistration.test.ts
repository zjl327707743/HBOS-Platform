import { describe, expect, it } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, resolve } from 'node:path'

/**
 * **按需注册**的守护：源码里用到的每个 `a-xxx` 都必须在 `main.ts` 里注册过。
 *
 * 这条测试的存在理由很具体：全量 `app.use(Antd)` 改成逐个注册后，漏注册
 * 一个组件**不会报错** —— Vue 只打一条 resolve 警告，页面上就是少一块，
 * 而且要翻到那个页面才看得见。静态对账比等人发现便宜得多。
 */
const here = dirname(fileURLToPath(import.meta.url))
const srcRoot = resolve(here, '../src')
const mainTs = readFileSync(join(srcRoot, 'main.ts'), 'utf8')

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name)
    if (statSync(full).isDirectory()) walk(full, out)
    else if (/\.(vue|ts)$/.test(name)) out.push(full)
  }
  return out
}

/** 模板里用到的 `a-xxx` → 期望注册的 PascalCase 名。 */
function usedTags(): Set<string> {
  const tags = new Set<string>()
  for (const file of walk(srcRoot)) {
    if (file.endsWith('main.ts')) continue
    const text = readFileSync(file, 'utf8')
    for (const m of text.matchAll(/<a-([a-z][a-z0-9-]*)/g)) tags.add(m[1]!)
  }
  return tags
}

function toPascal(tag: string): string {
  const fixed: Record<string, string> = {
    'input-number': 'InputNumber',
    'input-password': 'InputPassword',
    'input-search': 'InputSearch',
    'checkbox-group': 'CheckboxGroup',
    'radio-group': 'RadioGroup',
    'radio-button': 'RadioButton',
    'select-option': 'SelectOption',
    'menu-item': 'MenuItem',
    'menu-divider': 'MenuDivider',
    'collapse-panel': 'CollapsePanel',
    'descriptions-item': 'DescriptionsItem',
    'list-item': 'ListItem',
    'table-column': 'TableColumn',
    'timeline-item': 'TimelineItem',
    'form-item': 'FormItem',
    'date-picker': 'DatePicker',
    'config-provider': 'ConfigProvider',
  }
  return fixed[tag] ?? tag.split('-').map((x) => x.charAt(0).toUpperCase() + x.slice(1)).join('')
}

describe('Ant Design 按需注册', () => {
  it('main.ts 不再全量 use(Antd)', () => {
    // 去掉注释再判 —— 注释里会提到旧写法，不该算数
    const code = mainTs.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')
    expect(code).not.toMatch(/use\(Antd\)/)
    expect(code).not.toMatch(/import Antd from/)
    expect(code).toContain('ANTD_COMPONENTS')
  })

  it('源码里用到的每个 a-* 都在注册清单里', () => {
    // 清单里既有简写 `Alert,` 也有 `CheckboxGroup: Checkbox.Group,` —— 两种都算
    const registered = new Set(
      [...mainTs.matchAll(/^\s{2}([A-Z][A-Za-z]+)\s*[:,]/gm)].map((m) => m[1]!),
    )
    const missing = [...usedTags()]
      .map((tag) => toPascal(tag))
      .filter((name) => !registered.has(name))
      .sort()
    expect(missing, `未注册：${missing.join(', ')}`).toEqual([])
  })
})
