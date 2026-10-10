import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { portalErrorMessage } from '@/services/portalErrors'
import { usePortalStore } from '@/stores/portal'

interface QueryField {
  state: Ref<string>
  normalize?: (value: string) => string
}

interface QueryPageOptions {
  path: string
  fields: Record<string, QueryField>
  load: () => Promise<void>
  failureMessage: string
}

/** Shared URL state and error lifecycle for read-only LIMS query pages. */
export function useLimsQueryPage(options: QueryPageOptions) {
  const route = useRoute()
  const router = useRouter()
  const portal = usePortalStore()
  const loading = ref(true)
  const loadingMore = ref(false)
  const errorMessage = ref('')
  let generation = 0

  function readRouteState() {
    for (const [key, field] of Object.entries(options.fields)) {
      const raw = route.query[key]
      const value = typeof raw === 'string' ? raw : ''
      field.state.value = field.normalize ? field.normalize(value) : value
    }
  }

  async function updateRoute() {
    const query: Record<string, string> = {}
    for (const [key, field] of Object.entries(options.fields)) {
      const value = field.state.value.trim()
      if (value) query[key] = value
    }
    const target = { path: options.path, query }
    if (router.resolve(target).fullPath === route.fullPath) {
      await options.load()
    } else {
      await router.replace(target)
    }
  }

  async function runLoad<T>(
    request: () => Promise<T>,
    commit: (response: T) => void,
    append = false,
    clearOnError?: () => void,
  ) {
    if (append && (loading.value || loadingMore.value)) return
    const current = ++generation
    loading.value = !append
    loadingMore.value = append
    errorMessage.value = ''
    try {
      if (!portal.user) await portal.bootstrap()
      const response = await request()
      if (current === generation) commit(response)
    } catch (error) {
      if (current === generation) {
        if (!append) clearOnError?.()
        errorMessage.value = portalErrorMessage(error, options.failureMessage)
      }
    } finally {
      if (current === generation) {
        loading.value = false
        loadingMore.value = false
      }
    }
  }

  readRouteState()
  watch(() => route.fullPath, () => {
    readRouteState()
    void options.load()
  })
  onMounted(() => void options.load())
  onBeforeUnmount(() => { generation += 1 })

  return { loading, loadingMore, errorMessage, updateRoute, runLoad }
}
