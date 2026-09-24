import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getPortalPrototypeData } from '@/services/portalProvider'
import type {
  AppManifestDTO,
  BusinessPulseDTO,
  LimsQueueItemDTO,
  PortalUser,
  SummaryMetricDTO,
  TwinStatusDTO,
  UnifiedTaskDTO,
} from '@/contracts/portal'

export const usePortalStore = defineStore('portal', () => {
  const user = ref<PortalUser | null>(null)
  const apps = ref<AppManifestDTO[]>([])
  const heroMetrics = ref<SummaryMetricDTO[]>([])
  const tasks = ref<UnifiedTaskDTO[]>([])
  const businessPulse = ref<BusinessPulseDTO[]>([])
  const twinStatuses = ref<TwinStatusDTO[]>([])
  const limsQueue = ref<LimsQueueItemDTO[]>([])
  const loading = ref(false)

  const totalActions = computed(() =>
    heroMetrics.value
      .filter((item) => typeof item.value === 'number')
      .reduce((sum, item) => sum + Number(item.value), 0),
  )

  async function bootstrap() {
    loading.value = true
    try {
      const data = await getPortalPrototypeData()
      user.value = data.user
      apps.value = data.apps
      heroMetrics.value = data.heroMetrics
      tasks.value = data.tasks
      businessPulse.value = data.businessPulse
      twinStatuses.value = data.twinStatuses
      limsQueue.value = data.limsQueue
    } finally {
      loading.value = false
    }
  }

  return {
    user,
    apps,
    heroMetrics,
    tasks,
    businessPulse,
    twinStatuses,
    limsQueue,
    loading,
    totalActions,
    bootstrap,
  }
})
