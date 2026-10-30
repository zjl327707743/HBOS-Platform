import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

/**
 * 打包配置的**契约** —— 防止有人后来把 manualChunks 拿掉、或把懒加载改回静态导入，
 * 让主包悄悄回到 1.9 MB。
 *
 * 只读配置源码，不跑构建（构建由 `npm run build` 负责，那里也会因为
 * chunkSizeWarningLimit 报警）。
 */
const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')
const vite = readFileSync(resolve(root, 'vite.config.ts'), 'utf8')
const router = readFileSync(resolve(root, 'src/router/index.ts'), 'utf8')

describe('打包预算', () => {
  it('vendor 按库拆分', () => {
    expect(vite).toContain('manualChunks')
    for (const name of ['vendor-three', 'vendor-antd', 'vendor-vue']) {
      expect(vite).toContain(`'${name}'`)
    }
  })

  it('antd 与图标在同一块（拆开会产生 circular chunk）', () => {
    // 早先单独拆 vendor-icons，rollup 报
    //   Circular chunk: vendor-icons -> vendor-antd -> vendor-icons
    expect(vite).not.toContain("'vendor-icons'")
    expect(vite).toContain("id.includes('@ant-design/')")
  })

  it('three 单独成块（它只在 Twin 页用）', () => {
    expect(vite).toMatch(/id\.includes\('\/three\/'\)/)
  })

  it('库存与生产视图走懒加载', () => {
    // 这些页面首屏用不到，静态导入会把它们塞进主包
    for (const view of [
      'InventoryEntryView',
      'InventoryPickView',
      'InventoryReportView',
      'InventoryIntakeView',
      'InventoryBatchView',
      'ProductionDashboardView',
    ]) {
      expect(router).not.toMatch(new RegExp(`^import ${view} from`, 'm'))
    }
    expect(router).toContain("component: () => import('@/views/InventoryEntryView.vue')")
  })

  it('没有静态/动态双重导入的写法', () => {
    // 这类写法会让 Vite 报「dynamic import will not move module into another chunk」
    const views = [
      'InventoryEntryView.vue',
      'InventoryPickView.vue',
      'InventoryReconcileView.vue',
    ]
    for (const v of views) {
      const src = readFileSync(resolve(root, 'src/views', v), 'utf8')
      expect(src).not.toContain("await import('@/services/frappeClient')")
    }
  })
})
