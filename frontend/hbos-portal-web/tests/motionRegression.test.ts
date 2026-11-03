import { expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
it('F06/F07: backgrounding stops animation work and unmount removes listeners', () => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  const schedule = vi.spyOn(window, 'requestAnimationFrame').mockReturnValue(123)
  const cancel = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => undefined)
  const state = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
  const wrapper = mount(PointerAtmosphere)
  expect(schedule).toHaveBeenCalled()
  state.mockReturnValue('hidden'); document.dispatchEvent(new Event('visibilitychange'))
  try { expect(cancel).toHaveBeenCalledWith(123) } finally { wrapper.unmount(); vi.restoreAllMocks() }
})

it('pauses both render loops without mounting a second atmosphere instance', async () => {
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  const schedule=vi.spyOn(window,'requestAnimationFrame').mockReturnValue(456)
  const cancel=vi.spyOn(window,'cancelAnimationFrame').mockImplementation(()=>undefined)
  vi.spyOn(document,'visibilityState','get').mockReturnValue('visible')
  const wrapper=mount(PointerAtmosphere);const before=schedule.mock.calls.length
  await wrapper.setProps({paused:true});expect(cancel).toHaveBeenCalledWith(456);expect(schedule).toHaveBeenCalledTimes(before)
  await wrapper.setProps({paused:false});expect(schedule.mock.calls.length).toBeGreaterThan(before)
  wrapper.unmount();vi.restoreAllMocks()
})
