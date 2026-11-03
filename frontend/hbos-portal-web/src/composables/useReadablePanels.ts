import { nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
// Content can reduce the usable region even above the 700px breakpoint.
// Measure the available viewport independently from the natural-flow fallback,
// so enabling the fallback cannot oscillate between two layouts.
export function useReadablePanels(enabled: Ref<boolean>, root: Ref<HTMLElement | null>) {
  const natural = ref(false)
  let resize: ResizeObserver | undefined, mutation: MutationObserver | undefined, frame = 0
  const height = (element: Element | null) => {
    if (!element) return 0
    const css = getComputedStyle(element)
    return element.getBoundingClientRect().height + parseFloat(css.marginTop || '0') + parseFloat(css.marginBottom || '0')
  }
  function measure() {
    const main = root.value
    if (!enabled.value || !main || !main.clientHeight || window.innerWidth <= 760 || window.innerHeight <= 700) { natural.value = false; return }
    const css = getComputedStyle(main)
    const externalError = Array.from(main.querySelectorAll('.r6-resource-error')).find(element => !element.closest('.r6-panel-frame')) || null
    const available = main.clientHeight - parseFloat(css.paddingTop) - parseFloat(css.paddingBottom)
      - height(main.querySelector('.r6-context-row')) - height(main.querySelector('.r6-page-heading'))
      - height(main.querySelector('.r6-page-footer')) - height(externalError)
    const overhead = Math.max(0, ...Array.from(main.querySelectorAll('.r6-panel-frame')).map(panel => height(panel.querySelector('.r6-panel-header')) + height(panel.querySelector('.r6-panel-footer')) + 2))
    natural.value = overhead > 0 && available - overhead < 260
  }
  function schedule() { cancelAnimationFrame(frame); frame = requestAnimationFrame(measure) }
  async function observe() {
    await nextTick(); resize?.disconnect(); mutation?.disconnect()
    if (root.value) { resize?.observe(root.value); mutation?.observe(root.value, { childList: true, subtree: true }) }
    schedule()
  }
  watch(enabled, observe)
  onMounted(() => { resize = new ResizeObserver(schedule); mutation = new MutationObserver(schedule); window.addEventListener('resize', schedule); void observe() })
  onBeforeUnmount(() => { resize?.disconnect(); mutation?.disconnect(); window.removeEventListener('resize', schedule); cancelAnimationFrame(frame) })
  return natural
}
