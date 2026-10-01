import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  getPortalData,
  getPortalSummaries,
  getPortalTasks,
  portalDataSource,
} from '@/services/portalProvider'
import { portalErrorMessage, providerFailureMessage } from '@/services/portalErrors'
import { isAuthError, login, logout, clearCachedCsrfToken } from '@/services/frappeClient'
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
  const summaryMetrics = ref<SummaryMetricDTO[]>([])
  const tasks = ref<UnifiedTaskDTO[]>([])
  const businessPulse = ref<BusinessPulseDTO[]>([])
  const twinStatuses = ref<TwinStatusDTO[]>([])
  const limsQueue = ref<LimsQueueItemDTO[]>([])
  const loading = ref(false)
  const summariesLoading = ref(false)
  const tasksLoading = ref(false)
  const bootstrapError = ref<string | null>(null)
  const summariesError = ref<string | null>(null)
  const tasksError = ref<string | null>(null)
  const dataSource = ref(portalDataSource)
  const authenticated = ref(false)
  const sessionChecked = ref(false)

  const totalActions = computed(() =>
    tasks.value.filter((task) => task.status === 'open').length,
  )

  let generation = 0
  let checkedAt = 0
  let tasksRequest = 0
  let summariesRequest = 0
  let bootstrapRequest: Promise<void> | null = null

  function markSignedOut() {
    generation += 1
    bootstrapRequest = null
    checkedAt = 0
    authenticated.value = false
    sessionChecked.value = false
    clearCachedCsrfToken()
    user.value = null
    branding.value = null
    apps.value = []
    heroMetrics.value = []
    summaryMetrics.value = []
    tasks.value = []
    businessPulse.value = []
    twinStatuses.value = []
    limsQueue.value = []
    bootstrapError.value = summariesError.value = tasksError.value = null
    loading.value = summariesLoading.value = tasksLoading.value = false
  }

  async function bootstrap() {
    if (bootstrapRequest) return bootstrapRequest
    const current = generation
    loading.value = true
    bootstrapError.value = null
    const request = (async () => {
      try {
        const data = await getPortalData()
        if (current !== generation) return
        user.value = data.user
        branding.value = data.branding
        apps.value = data.apps
        heroMetrics.value = data.heroMetrics
        summaryMetrics.value = data.heroMetrics
        tasks.value = data.tasks
        businessPulse.value = data.businessPulse
        twinStatuses.value = data.twinStatuses
        limsQueue.value = data.limsQueue
        authenticated.value = true
        sessionChecked.value = true
        checkedAt = Date.now()
        if (dataSource.value === 'frappe') {
          void refreshTasks()
          void refreshSummaries()
        }
      } catch (error) {
        if (current === generation) {
          if (isAuthError(error)) markSignedOut()
          else {
            authenticated.value = false
            sessionChecked.value = false
            bootstrapError.value = portalErrorMessage(error, 'HBOS 初始化失败，请稍后重试。')
          }
        }
        throw error
      } finally {
        if (current === generation) loading.value = false
      }
    })()
    bootstrapRequest = request
    try { await request } finally {
      if (bootstrapRequest === request) bootstrapRequest = null
    }
  }

  /** 缓存短期有效验证；失效和网络失败均允许下一次重新探测。 */
  async function ensureSession(): Promise<boolean> {
    if (dataSource.value !== 'frappe') {
      sessionChecked.value = authenticated.value = true
      return true
    }
    if (sessionChecked.value && authenticated.value && Date.now() - checkedAt < 60000) return true
    const current = generation
    try {
      await bootstrap()
      return authenticated.value
    } catch (error) {
      // 服务不可用时允许进入错误壳，但不能把未知会话标记成已认证。
      return current === generation && Boolean(bootstrapError.value) && !isAuthError(error)
    }
  }

  async function signIn(usr: string, pwd: string) {
    await login(usr, pwd)
    markSignedOut()
    await bootstrap()
    if (!authenticated.value) throw new Error('登录后仍未取得 HBOS 会话。')
  }

  async function signOut() {
    await logout()
    markSignedOut()
  }

  async function refreshSummaries() {
    if (dataSource.value !== 'frappe') return
    const current = generation
    const currentRequest = ++summariesRequest
    summariesLoading.value = true
    summariesError.value = null
    try {
      const loaded = await getPortalSummaries(apps.value)
      if (current !== generation || currentRequest !== summariesRequest) return
      summariesError.value = providerFailureMessage(loaded.errors)
      summaryMetrics.value = loaded.items
      const byApp = new Map<string, SummaryMetricDTO[]>()
      for (const metric of loaded.items) {
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
    } catch (error) {
      if (current !== generation || currentRequest !== summariesRequest) return
      if (isAuthError(error)) markSignedOut()
      else summariesError.value = portalErrorMessage(error, '业务概览暂时无法刷新，请稍后重试。')
    } finally {
      if (current === generation && currentRequest === summariesRequest) summariesLoading.value = false
    }
  }

  async function refreshTasks() {
    if (dataSource.value !== 'frappe') return
    const current = generation
    const currentRequest = ++tasksRequest
    tasksLoading.value = true
    tasksError.value = null
    try {
      const loaded = await getPortalTasks(apps.value)
      if (current !== generation || currentRequest !== tasksRequest) return
      tasksError.value = providerFailureMessage(loaded.errors)
      tasks.value = loaded.items
      const failed = new Set(loaded.errors.map(error => error.appId))
      const counts = loaded.items.filter(task => task.status === 'open').reduce<Record<string, number>>((acc, task) => {
        acc[task.appId] = (acc[task.appId] || 0) + 1
        return acc
      }, {})
      apps.value = apps.value.map((app) => ({
        ...app,
        pendingCount: app.capabilityTasks && !failed.has(app.id) ? (counts[app.id] || 0) : app.pendingCount,
      }))
    } catch (error) {
      if (current !== generation || currentRequest !== tasksRequest) return
      if (isAuthError(error)) markSignedOut()
      else tasksError.value = portalErrorMessage(error, '工作事项暂时无法刷新，请稍后重试。')
    } finally {
      if (current === generation && currentRequest === tasksRequest) tasksLoading.value = false
    }
  }

  return {
    user,
    branding,
    apps,
    heroMetrics,
    summaryMetrics,
    tasks,
    businessPulse,
    twinStatuses,
    limsQueue,
    loading,
    summariesLoading,
    tasksLoading,
    bootstrapError,
    summariesError,
    tasksError,
    dataSource,
    authenticated,
    sessionChecked,
    totalActions,
    bootstrap,
    ensureSession,
    signIn,
    signOut,
    markSignedOut,
    refreshSummaries,
    refreshTasks,
  }
})
