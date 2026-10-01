import type { ProviderBatch } from '@/contracts/portal'
import { portalErrorMessage, providerFailureMessage } from '@/services/portalErrors'
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

export function useDebouncedSearch<T>(
  query: Ref<string>,
  open: Readonly<Ref<boolean>>,
  search: (query: string) => Promise<T[] | ProviderBatch<T>>,
  delay = 280,
) {
  const results = ref<T[]>([]) as Ref<T[]>
  const errorMessage = ref('')
  const loading = ref(false)
  let timer: ReturnType<typeof setTimeout> | undefined
  let generation = 0

  function cancel() {
    clearTimeout(timer)
    generation += 1
    loading.value = false
  }

  async function refresh() {
    const current = ++generation
    loading.value = true
    errorMessage.value = ''
    try {
      const loaded = await search(query.value)
      if (current === generation && open.value) {
        results.value = Array.isArray(loaded) ? loaded : loaded.items
        errorMessage.value = Array.isArray(loaded) ? '' : providerFailureMessage(loaded.errors) || ''
      }
    } catch (error) {
      if (current === generation && open.value) {
        results.value = []
        errorMessage.value = portalErrorMessage(error, '搜索暂时不可用，请稍后重试。')
      }
    } finally {
      if (current === generation) loading.value = false
    }
  }

  watch(query, () => {
    cancel()
    results.value = []
    errorMessage.value = ''
    if (open.value) timer = setTimeout(() => void refresh(), delay)
  }, { flush: 'sync' })

  watch(open, (value) => {
    cancel()
    results.value = []
    errorMessage.value = ''
    if (value) void refresh()
  })
  onBeforeUnmount(cancel)

  return { results, errorMessage, loading }
}
