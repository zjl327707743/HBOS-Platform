import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getSecurity, type ProofStatus } from '@/services/accountApi'

export function useAccountProof(onInvalidated: () => void = () => undefined) {
  const deadline = ref(0), now = ref(Date.now()), method = ref<string | null>(null)
  const remaining = computed(() => Math.max(0, Math.ceil((deadline.value - now.value) / 1000)))
  const valid = computed(() => remaining.value > 0)
  let revision = 0, timer: ReturnType<typeof setInterval> | undefined, ticks = 0, disposed = false
  function invalidate() {
    const hadProof = deadline.value > 0
    revision++; deadline.value = 0; method.value = null
    if (hadProof) onInvalidated()
  }
  function sync(proof?: ProofStatus) {
    if (!proof?.valid || proof.expires_in <= 0) { invalidate(); return }
    revision++; now.value = Date.now(); deadline.value = now.value + proof.expires_in * 1000; method.value = proof.method
  }
  function grant(seconds: number, source: string) { sync({ valid: seconds > 0, expires_in: seconds, method: source }) }
  async function recheck() {
    if (disposed || document.visibilityState === 'hidden' || !deadline.value) return
    const version = revision
    try {
      const status = await getSecurity()
      if (!disposed && version === revision) sync(status.proof)
    } catch { if (!disposed && version === revision) invalidate() }
  }
  function resume() { now.value = Date.now(); if (deadline.value && !valid.value) invalidate(); void recheck() }
  onMounted(() => {
    timer = setInterval(() => {
      now.value = Date.now()
      if (deadline.value && !valid.value) invalidate()
      if (++ticks % 15 === 0) void recheck()
    }, 1000)
    window.addEventListener('focus', resume); window.addEventListener('pageshow', resume)
    document.addEventListener('visibilitychange', resume)
  })
  onBeforeUnmount(() => {
    disposed = true; invalidate(); if (timer) clearInterval(timer)
    window.removeEventListener('focus', resume); window.removeEventListener('pageshow', resume)
    document.removeEventListener('visibilitychange', resume)
  })
  return { valid, remaining, method, sync, grant, invalidate, recheck }
}
