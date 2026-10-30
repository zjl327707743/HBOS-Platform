import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

/**
 * 生产看板的**失败路径**回归。
 *
 * 这一组守的是「不能把故障显示成正常业务结论」：
 *   - 部分数据源挂了 → 标「部分口径」
 *   - 全部数据源挂了 → 不能说成「当月无异常记录」
 *   - 取数失败原因要分开（未接入 / 连不上 / 上游失败 / 无权限）
 */
const here = dirname(fileURLToPath(import.meta.url))
/** 从 `start` 截到下一个顶层 `}` 收尾的函数块（够用即可，不必完整解析）。 */
function sliceFn(src: string, start: string): string {
  const from = src.indexOf(start)
  if (from < 0) return ''
  const end = src.indexOf('\n}\n', from)
  return end < 0 ? src.slice(from) : src.slice(from, end + 3)
}

const view = readFileSync(resolve(here, '../src/views/ProductionDashboardView.vue'), 'utf8')
const service = readFileSync(resolve(here, '../src/services/productionBoard.ts'), 'utf8')

describe('生产看板失败路径', () => {
  it('取数结果区分四种失败原因', () => {
    for (const kind of ['not_configured', 'unreachable', 'upstream_error', 'unauthorized']) {
      expect(service).toContain(`'${kind}'`)
    }
  })

  it('页面按原因给出不同标题，不统一写「还没接通」', () => {
    expect(view).toContain('boardFailureTitle')
    expect(view).toContain('连不上生产数据服务')
    expect(view).toContain('没有权限读取生产数据')
  })

  it('可重试的失败给出重试按钮', () => {
    expect(view).toContain("boardFailure?.kind !== 'not_configured'")
    expect(view).toContain('重试')
  })

  it('重试成功后必须切回 ready —— 否则数据回来了页面还停在失败态', () => {
    // 失败态模板优先于 board 模板，只更新 board 不切 phase 会一直显示失败页
    const fn = sliceFn(view, 'async function refreshBoard')
    const success = fn.slice(fn.indexOf("result.state === 'ready'"), fn.indexOf('} else {'))
    expect(success).toContain("phase.value = 'ready'")
    expect(success).toContain('boardFailure.value = null')
    expect(success).toContain('refreshFailed.value = false')
  })

  it('新一轮刷新先撤掉上一次的「已更新」', () => {
    const fn = sliceFn(view, 'async function refreshBoard')
    const head = fn.slice(0, fn.indexOf("result.state === 'ready'"))
    expect(head).toContain('justRefreshed.value = false')
  })

  it('部分车间失败标为「部分口径」', () => {
    expect(view).toContain('anomalySourceNote')
    expect(view).toContain('闭环率为部分口径')
  })

  it('全部车间失败不得显示「当月无异常记录」', () => {
    // 关键分支：failedWorkshops 全长 == sourceCount 时**先返回失败说明**，
    // 之后才轮到「当月无异常记录」。顺序反了就等于把数据源故障说成没有异常。
    const start = view.indexOf('const anomalyNote = computed(')
    const note = view.slice(start, view.indexOf('function completion(', start))
    expect(note).toContain('当月无异常记录')
    const guard = note.indexOf('a.failedWorkshops || []).length >= total')
    expect(guard).toBeGreaterThan(-1)
    expect(guard).toBeLessThan(note.indexOf('当月无异常记录'))
  })

  it('部分 QC 失败标为「部分口径」', () => {
    expect(view).toContain('qualitySourceNote')
    expect(view).toContain('合格率为部分口径')
  })
})

describe('C 批：请求序号', () => {
  const read = (name: string) =>
    readFileSync(resolve(here, '../src/views', name), 'utf8')

  it('物料搜索有请求序号', () => {
    expect(read('InventoryItemView.vue')).toContain('searchSeq')
  })

  it('批次搜索有请求序号', () => {
    expect(read('InventoryBatchPickerView.vue')).toContain('searchSeq')
  })

  it('货位切换的库存查询有请求序号', () => {
    expect(read('InventoryWarehouseView.vue')).toContain('stockSeq')
  })

  it('拣货单单位查询按行独立编号', () => {
    expect(read('InventoryPickView.vue')).toContain('rowLookupSeq')
  })

  it('AI 报告打开有请求序号', () => {
    expect(view).toContain('reportSeq')
  })
})

describe('生命周期与渲染安全', () => {
  const readView = (name: string) =>
    readFileSync(resolve(here, '../src/views', name), 'utf8')

  it('搜索/查询防抖 timer 都在卸载时清理', () => {
    for (const [file, timer] of [
      ['InventoryBatchPickerView.vue', 'searchTimer'],
      ['InventoryItemView.vue', 'searchTimer'],
      ['InventoryIntakeView.vue', 'lookupTimer'],
      ['InventoryReconcileView.vue', 'lookupTimer'],
    ]) {
      const src = readView(file)
      // 找**调用**处（`onBeforeUnmount(() =>`），不是 import 里的那个名字
      const idx = src.lastIndexOf('onBeforeUnmount(() =>')
      expect(idx, `${file} 缺 onBeforeUnmount(() =>`).toBeGreaterThan(-1)
      expect(src.slice(idx, idx + 200)).toContain(timer)
    }
  })

  it('服务端错误详情不用 v-html 渲染', () => {
    // detail 来自 Frappe `_server_messages`；删标签不等于转义
    const src = readView('InventoryEntryView.vue')
    expect(src).not.toContain('v-html="blockedError.detail"')
  })
})
