import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

/**
 * 附件识别必须**优先按后端写的类型标记**，而不是文件名/扩展名。
 *
 * 文件名会被 Frappe 重名后缀改写（`xxx-a1b2c3.pdf`），也可能被人工上传的
 * 文件撞名。靠名字认附件，迟早会把合格证当成货位卡打印出去。
 */
const here = dirname(fileURLToPath(import.meta.url))
const read = (p: string) => readFileSync(resolve(here, '..', p), 'utf8')

describe('附件按类型标记识别', () => {
  it('服务层把 kind 一并返回', () => {
    const svc = read('src/services/inventoryDocs.ts')
    expect(svc).toContain('hbos_attachment_kind')
    expect(svc).toContain('ATTACHMENT_KIND_CARD')
    expect(svc).toContain('ATTACHMENT_KIND_LABEL_PHOTO')
  })

  it('批次页优先按 kind 认货位卡，文件名正则只作老数据回退', () => {
    const view = read('src/views/InventoryBatchView.vue')
    const fn = view.slice(view.indexOf('function pickCardFile'), view.indexOf('function pickCardFile') + 700)
    expect(fn).toContain('ATTACHMENT_KIND_CARD')
    expect(fn.indexOf('ATTACHMENT_KIND_CARD')).toBeLessThan(fn.indexOf('CARD_FILE_RE'))
  })

  it('草稿页优先按 kind 认标签照片', () => {
    const view = read('src/views/InventoryDraftReviewView.vue')
    const idx = view.indexOf('function pickIntakePhoto')
    const fn = view.slice(idx, idx + 800)
    expect(fn).toContain('ATTACHMENT_KIND_LABEL_PHOTO')
    expect(fn.indexOf('ATTACHMENT_KIND_LABEL_PHOTO')).toBeLessThan(fn.indexOf('PHOTO_RE'))
  })

  it('后端生成 PDF 时写入标记', () => {
    const gen = read('../../apps/hb_inventory_app/hb_inventory_app/hbos_inventory/doc_gen.py')
    expect(gen).toContain('hbos_attachment_kind')
    expect(gen).toContain('KIND_CARD')
  })

  it('重新生成只删标记为自己的文件', () => {
    const gen = read('../../apps/hb_inventory_app/hb_inventory_app/hbos_inventory/doc_gen.py')
    const fn = gen.slice(gen.indexOf('def _purge_previous'), gen.indexOf('def _card_format_for'))
    expect(fn).toContain('hbos_attachment_kind')
  })

  it('标签照片也打标记', () => {
    const api = read('../../apps/hb_inventory_app/hb_inventory_app/hbos_inventory/api.py')
    expect(api).toContain('"hbos_attachment_kind": "标签照片"')
  })
})
