import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  getPortalData,
  portalDataSource,
} from '@/services/portalProvider'
import type {
  AppManifestDTO,
  BusinessPulseDTO,
  LimsQueueItemDTO,
  PortalBranding,
  PortalUser,
  SummaryMetricDTO,
  TwinStatusDTO,
  UnifiedTaskDTO,
} from '@/contracts/portal'

export const usePortalStore = defineStore('portal', () => {
  const user = ref<PortalUser | null>(null)
  const branding = ref<PortalBranding | null>(null)
  const apps = ref<AppManifestDTO[]>([])
  const heroMetrics = ref<SummaryMetricDTO[]>([])
  const tasks = ref<UnifiedTaskDTO[]>([])
  const businessPulse = ref<BusinessPulseDTO[]>([])
  const twinStatuses = ref<TwinStatusDTO[]>([])
  const limsQueue = ref<LimsQueueItemDTO[]>([])
  const loading = ref(false)
  const bootstrapError = ref<string | null>(null)
  const dataSource = ref(portalDataSource)

  const totalActions = computed(() =>
    tasks.value.filter((task) => task.status === 'open').length,
  )

  async function bootstrap() {
    loading.value = true
    bootstrapError.value = null
    try {
      const data = await getPortalData()
      user.value = data.user
      branding.value = data.branding
      apps.value = data.apps
      heroMetrics.value = data.heroMetrics
      tasks.value = data.tasks
      businessPulse.value = data.businessPulse
      twinStatuses.value = data.twinStatuses
      limsQueue.value = data.limsQueue
    } catch (error) {
      bootstrapError.value =
        error instanceof Error ? error.message : 'HBOS 初始化失败'
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    user,
    branding,
    apps,
    heroMetrics,
    tasks,
    businessPulse,
    twinStatuses,
    limsQueue,
    loading,
    bootstrapError,
    dataSource,
    totalActions,
    bootstrap,
  }
})
