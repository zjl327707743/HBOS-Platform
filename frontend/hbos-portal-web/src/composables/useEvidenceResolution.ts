import { onScopeDispose, ref, watch } from 'vue'
import type { KnowledgeEvidence } from '@/contracts/p1'
import { DomainApiError, resolveKnowledgeEvidence } from '@/services/p1Api'

// Cancellation abandons the await through the existing Frappe client. Generation
// checks also guard late completions; this does not claim network-level cancellation.
export function useEvidenceResolution(
  subjectKey: () => string | null,
  onInvalidation: () => void = () => undefined,
) {
  const open = ref(false)
  const loading = ref(false)
  const evidence = ref<KnowledgeEvidence | null>(null)
  const error = ref<string | null>(null)
  let generation = 0
  let controller: AbortController | null = null

  function clear() {
    generation++
    controller?.abort()
    controller = null
    evidence.value = null
    error.value = null
    loading.value = false
  }

  function close() {
    clear()
    open.value = false
  }

  async function show(evidenceId: string) {
    clear()
    const subject = subjectKey()
    if (!subject) { open.value = false; return false }
    open.value = true
    loading.value = true
    controller = new AbortController()
    const current = generation
    try {
      const resolved = await resolveKnowledgeEvidence(evidenceId, controller.signal)
      if (current !== generation || subject !== subjectKey() || !open.value) return false
      evidence.value = resolved
      return true
    } catch (reason) {
      if (current !== generation || subject !== subjectKey() || !open.value) return false
      evidence.value = null
      error.value = reason instanceof DomainApiError ? reason.message : '依据暂时不可用，请重新检索。'
      onInvalidation()
      return false
    } finally {
      if (current === generation) loading.value = false
    }
  }

  watch(subjectKey, close, { flush: 'sync' })
  onScopeDispose(close)
  return { open, loading, evidence, error, show, close }
}
