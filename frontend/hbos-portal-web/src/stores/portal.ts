import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { FrappeHttpError, hasFrappeSession } from '@/services/frappeClient'
import {
  getPortalData,
  getPortalSummaries,
  getPortalTasks,
  portalDataSource,
} from '@/services/portalProvider'

/**
 * 把底层 HTTP 异常翻成用户语义。
 *
 * 只有 frappe 数据源才会走到 401/403——mock 模式不发请求。
 *
 * Frappe 对「未登录访客」与「已登录但无权」都返回 403，**同码不同因**，
 * 所以这里先用会话探针分辨成因，再把「无会话」归一化成 401：
 * 会话失效要引导重新登录，会话有效而进不去才是真的无权限。两者给用户的
 * 下一步动作完全不同，不能共用一句文案。
 */
async function describeBootstrapError(error: unknown): Promise<{ status: number; message: string }> {
  if (portalDataSource !== 'frappe' || !(error instanceof FrappeHttpError)) {
    return { status: 0, message: 'HBOS 初始化失败，请稍后重试。' }
  }

  if (error.status === 403 || error.status === 401) {
    if (!(await hasFrappeSession())) {
      return { status: 401, message: '当前会话已失效，请重新登录 HBOS 后再打开工作台。' }
    }
    return { status: 403, message: '你没有权限进入这个应用。若你认为这是配置错误，请联系业务管理员。' }
  }

  return { status: error.status, message: 'HBOS 服务暂时不可用，请稍后重试。' }
}
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
  const summariesLoading = ref(false)
  const tasksLoading = ref(false)
  const bootstrapError = ref<string | null>(null)
  const bootstrapErrorStatus = ref<number>(0)
  const dataSource = ref(portalDataSource)

  const totalActions = computed(() =>
    tasks.value.filter((task) => task.status === 'open').length,
  )

  async function bootstrap() {
    loading.value = true
    bootstrapError.value = null
    bootstrapErrorStatus.value = 0
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
      if (dataSource.value === 'frappe') {
        void refreshTasks()
        void refreshSummaries()
      }
    } catch (error) {
      const described = await describeBootstrapError(error)
      bootstrapErrorStatus.value = described.status
      bootstrapError.value = described.message
      throw error
    } finally {
      loading.value = false
    }
  }



  async function refreshSummaries() {
    if (dataSource.value !== 'frappe') return
    summariesLoading.value = true
    try {
      const loaded = await getPortalSummaries(apps.value)
      const byApp = new Map<string, SummaryMetricDTO[]>()
      for (const metric of loaded) {
        const bucket = byApp.get(metric.appId) || []
        bucket.push(metric)
        byApp.set(metric.appId, bucket)
      }

      const selected: SummaryMetricDTO[] = []
      let index = 0
      while (selected.length < 4) {
        let added = false
        for (const app of apps.value) {
          const metric = byApp.get(app.id)?.[index]
          if (!metric) continue
          selected.push(metric)
          added = true
          if (selected.length >= 4) break
        }
        if (!added) break
        index += 1
      }
      heroMetrics.value = selected
    } finally {
      summariesLoading.value = false
    }
  }

  async function refreshTasks() {
    if (dataSource.value !== 'frappe') return
    tasksLoading.value = true
    try {
      const loaded = await getPortalTasks(apps.value)
      tasks.value = loaded
      const counts = loaded.reduce<Record<string, number>>((acc, task) => {
        acc[task.appId] = (acc[task.appId] || 0) + 1
        return acc
      }, {})
      apps.value = apps.value.map((app) => ({
        ...app,
        pendingCount: app.capabilityTasks ? (counts[app.id] || 0) : app.pendingCount,
      }))
    } finally {
      tasksLoading.value = false
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
    summariesLoading,
    tasksLoading,
    bootstrapError,
    bootstrapErrorStatus,
    dataSource,
    totalActions,
    bootstrap,
    refreshSummaries,
    refreshTasks,
  }
})
