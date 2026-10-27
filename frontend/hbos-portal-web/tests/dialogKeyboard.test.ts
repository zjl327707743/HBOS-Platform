import { afterEach, expect, it, vi } from 'vitest'
import { cycleDialogTab } from '@/services/dialogKeyboard'

afterEach(() => { document.body.innerHTML = ''; vi.restoreAllMocks() })
function dialog() {
  document.body.innerHTML = '<button id="outside">背景分页</button><section id="drawer" tabindex="-1"><button id="first">关闭</button><input id="middle"><button id="disabled" disabled>禁用</button><button id="hidden">隐藏</button><div inert><button>不可交互</button></div><button id="last">关闭详情</button></section>'
  const root = document.querySelector<HTMLElement>('#drawer')!
  for (const node of root.querySelectorAll<HTMLElement>('*')) vi.spyOn(node, 'getClientRects').mockReturnValue([node.id === 'hidden' ? new DOMRect(0, 0, 0, 0) : new DOMRect(0, 0, 80, 30)] as unknown as DOMRectList)
  const press = (id: string, key: string, shiftKey = false) => {
    document.getElementById(id)!.focus()
    const event = new KeyboardEvent('keydown', { key, shiftKey, cancelable: true })
    cycleDialogTab(event, root)
    return event
  }
  return { press }
}
it('cycles Shift+Tab from the first control and Tab from the last without reaching background pagination', () => {
  const { press } = dialog()
  expect(press('first', 'Tab', true).defaultPrevented).toBe(true)
  expect(document.activeElement?.id).toBe('last')
  expect(press('last', 'Tab').defaultPrevented).toBe(true)
  expect(document.activeElement?.id).toBe('first')
})
it('leaves middle controls and Escape to native handling and enters from the drawer focus sentinel', () => {
  const { press } = dialog()
  expect(press('middle', 'Tab').defaultPrevented).toBe(false)
  expect(document.activeElement?.id).toBe('middle')
  expect(press('first', 'Escape').defaultPrevented).toBe(false)
  expect(press('drawer', 'Tab').defaultPrevented).toBe(true)
  expect(document.activeElement?.id).toBe('first')
})
