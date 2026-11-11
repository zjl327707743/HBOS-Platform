import { afterEach, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import PortalSelect from '@/components/portal/PortalSelect.vue'

const options = [
  { value: 'all', label: '全部应用' },
  { value: 'locked', label: '不可选', disabled: true },
  { value: 'lims', label: 'LIMS 实验室管理' },
]
let wrapper: VueWrapper | undefined
afterEach(() => { wrapper?.unmount(); wrapper = undefined })

it('skips disabled choices, distinguishes active and selected, and applies one business change', async () => {
  wrapper = mount(PortalSelect, { attachTo: document.body, props: { value: 'all', options, ariaLabel: '应用' } })
  const trigger = wrapper.get('[role="combobox"]')
  await trigger.trigger('keydown', { key: 'ArrowDown' })
  const list = document.getElementById(trigger.attributes('aria-controls')!)!
  await trigger.trigger('keydown', { key: 'ArrowDown' })
  const active = document.getElementById(trigger.attributes('aria-activedescendant')!)!
  expect(active.textContent).toBe('LIMS 实验室管理')
  expect(active.getAttribute('aria-selected')).toBe('false')
  expect(list.querySelector('[aria-selected="true"]')?.textContent).toBe('全部应用')
  await trigger.trigger('keydown', { key: 'Enter' })
  expect(wrapper.emitted('update:value')).toEqual([['lims']])
  expect(wrapper.emitted('change')).toEqual([['lims']])
  expect(document.activeElement).toBe(trigger.element)
  expect(document.getElementById(list.id)).toBeNull()
})

it('Escape only closes the open list and preserves the value and label association', async () => {
  wrapper = mount(PortalSelect, { attachTo: document.body, props: { value: 'all', options, id: 'app-selector', ariaRequired: true, ariaInvalid: true, ariaDescribedby: 'app-help' } })
  const trigger = wrapper.get('#app-selector')
  await trigger.trigger('click')
  const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true })
  trigger.element.dispatchEvent(event)
  expect(event.defaultPrevented).toBe(true)
  expect(wrapper.emitted('change')).toBeUndefined()
  expect(trigger.attributes()).toMatchObject({ 'aria-required': 'true', 'aria-invalid': 'true', 'aria-describedby': 'app-help' })
  expect(document.activeElement).toBe(trigger.element)
})

it('recomputes options while open and closes when the field becomes disabled', async () => {
  const select = mount(PortalSelect, { attachTo: document.body, props: { value: 'lims', options, ariaLabel: '应用' } })
  wrapper = select
  const trigger = select.get('[role="combobox"]')
  await trigger.trigger('click')
  await select.setProps({ options: options.slice(0, 2) })
  expect(document.getElementById(trigger.attributes('aria-activedescendant')!)?.textContent).toBe('全部应用')
  await select.setProps({ disabled: true })
  expect(trigger.attributes('aria-expanded')).toBe('false')
  expect(document.querySelector('.v10-choice-popup')).toBeNull()
})

it('does not select on Enter during a Chinese composition session', async () => {
  wrapper = mount(PortalSelect, { attachTo: document.body, props: { options, searchable: true, ariaLabel: '应用' } })
  const trigger = wrapper.get('input')
  await trigger.trigger('click')
  await trigger.trigger('compositionstart')
  await trigger.trigger('keydown', { key: 'Enter', isComposing: true })
  expect(wrapper.emitted('update:value')).toBeUndefined()
  expect(trigger.attributes('aria-expanded')).toBe('true')
})
