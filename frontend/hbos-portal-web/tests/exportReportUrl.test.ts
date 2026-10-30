import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { assertXlsxBytes } from '@/services/inventoryReports'

/**
 * 报表导出：**跨源部署**必须打到 Frappe，不是 Portal 自己。
 *
 * 早先 `fetch('/api/method/...')` 是裸相对路径。同源反向代理时看起来没事，
 * 但项目明确支持 Portal 与 Frappe 跨源部署 —— 那时导出稳定打到 Portal 自己。
 */
const here = dirname(fileURLToPath(import.meta.url))
const svc = readFileSync(resolve(here, '../src/services/inventoryReports.ts'), 'utf8')
const client = readFileSync(resolve(here, '../src/services/frappeClient.ts'), 'utf8')

describe('报表导出', () => {
  it('用 frappeApiUrl 拼地址，不再用裸相对路径', () => {
    expect(svc).toContain('frappeApiUrl(')
    expect(svc).not.toContain("fetch('/api/method/frappe.desk.query_report.export_query'")
  })

  it('frappeApiUrl 优先 BASE_URL，再退 APP_ORIGIN', () => {
    expect(client).toContain('export function frappeApiUrl')
    const fn = client.slice(client.indexOf('export function frappeApiUrl'))
    expect(fn.indexOf('VITE_FRAPPE_BASE_URL')).toBeLessThan(fn.indexOf('VITE_FRAPPE_APP_ORIGIN'))
  })

  const bytesOf = (text: string) => new TextEncoder().encode(text)

  it('非 Excel 响应被拒绝（不会把 HTML 存成 .xlsx）', () => {
    expect(() => assertXlsxBytes(bytesOf('<!DOCTYPE html><html>没有要导出的数据</html>'))).toThrow(/网页/)
  })

  it('空响应被拒绝', () => {
    expect(() => assertXlsxBytes(new Uint8Array([]))).toThrow()
  })

  it('真实 ZIP 魔数通过', () => {
    expect(() => assertXlsxBytes(new Uint8Array([0x50, 0x4b, 0x03, 0x04]))).not.toThrow()
  })
})
