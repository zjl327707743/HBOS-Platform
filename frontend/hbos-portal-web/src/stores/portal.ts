import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  getPortalData,
  getPortalSummaries,
  getPortalTasks,
  portalDataSource,
} from '@/services/portalProvider'
import { isAuthError, login } from '@/services/frappeClient'
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
  const dataSource = ref(portalDataSource)
  const authenticated = ref(false)
  const sessionChecked = ref(false)

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
      if (dataSource.value === 'frappe') {
        void refreshTasks()
        void refreshSummaries()
      }
    } catch (error) {
      bootstrapError.value = isAuthError(error)
        ? '登录状态已失效，请重新登录。'
        : 'HBOS 初始化失败，请稍后重试。'
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 判断当前会话是否已登录。
   *
   * Portal API 不允许 allow_guest（CI 门禁），因此没有独立的探测端点：
   * 直接复用 bootstrap 的 403 语义 —— Guest 必然 403。
   */
  async function ensureSession(): Promise<boolean> {
    if (dataSource.value !== 'frappe') {
      sessionChecked.value = true
      authenticated.value = true
      return true
    }
    if (sessionChecked.value) return authenticated.value

    try {
      await bootstrap()
      authenticated.value = true
    } catch (error) {
      if (!isAuthError(error)) {
        // 非鉴权错误（500 / 网络等）不该把用户弹去登录页：
        // 保持已认证，让 Shell 自己渲染错误横幅。
        sessionChecked.value = true
        authenticated.value = true
        return true
      }
      authenticated.value = false
    }

    sessionChecked.value = true
    return authenticated.value
  }

  async function signIn(usr: string, pwd: string) {
    await login(usr, pwd)
    sessionChecked.value = false
    authenticated.value = false
    const ok = await ensureSession()
    if (!ok) throw new Error('登录后仍未取得 HBOS 会话。')
  }

  function markSignedOut() {
    authenticated.value = false
    sessionChecked.value = true
    user.value = null
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
    dataSource,
    authenticated,
    sessionChecked,
    totalActions,
    bootstrap,
    ensureSession,
    signIn,
    markSignedOut,
    refreshSummaries,
    refreshTasks,
  }
})
