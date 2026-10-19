import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { clearFrappeCsrfToken, FrappeHttpError, hasFrappeSession } from '@/services/frappeClient'
import {
  getPortalData,
  getPortalSummaries,
  getPortalTasks,
  portalDataSource,
} from '@/services/portalProvider'
import { getTwinManifest, getTwinStatus } from '@/services/p1Api'
import { portalErrorMessage, providerFailureMessage } from '@/services/portalErrors'
import { isAuthError, login, logout } from '@/services/frappeClient'
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

export const usePortalStore = defineStore('portal', () => {
  const user = ref<PortalUser | null>(null)
  const branding = ref<PortalBranding | null>(null)
  const apps = ref<AppManifestDTO[]>([])
  const heroMetrics = ref<SummaryMetricDTO[]>([])
  const summaryMetrics = ref<SummaryMetricDTO[]>([])
  const tasks = ref<UnifiedTaskDTO[]>([])
  const businessPulse = ref<BusinessPulseDTO[]>([])
  const twinStatuses = ref<TwinStatusDTO[]>([])
  const twinOverviewLoading = ref(false)
  const twinOverviewError = ref<string | null>(null)
  const twinEquipmentIds = ref<string[]>([])
  const limsQueue = ref<LimsQueueItemDTO[]>([])
  const loading = ref(false)
  const summariesLoading = ref(false)
  const tasksLoading = ref(false)
  const bootstrapError = ref<string | null>(null)
  const summariesError = ref<string | null>(null)
  const tasksError = ref<string | null>(null)
  const bootstrapErrorStatus = ref<number>(0)
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

  /** 清空全部会话期数据；登出与会话失效共用。 */
  function markSignedOut() {
    generation += 1
    bootstrapRequest = null
    checkedAt = 0
    authenticated.value = false
    sessionChecked.value = false
    clearFrappeCsrfToken()
    user.value = null
    branding.value = null
    apps.value = []
    heroMetrics.value = []
    summaryMetrics.value = []
    tasks.value = []
    businessPulse.value = []
    twinStatuses.value = []
    twinOverviewLoading.value = false
    twinOverviewError.value = null
    twinEquipmentIds.value = []
    limsQueue.value = []
    bootstrapError.value = summariesError.value = tasksError.value = null
    loading.value = summariesLoading.value = tasksLoading.value = false
    bootstrapErrorStatus.value = 0
  }

  /** 远端账号/知识/孪生页面沿用的命名，语义等同 markSignedOut。 */
  const clearSession = markSignedOut

  async function bootstrap() {
    if (bootstrapRequest) return bootstrapRequest
    let current = generation
    loading.value = true
    bootstrapError.value = null
    bootstrapErrorStatus.value = 0
    const request = (async () => {
      try {
        const data = await getPortalData()
        if (current !== generation) return
        if (user.value?.id && data.user?.id && user.value.id !== data.user.id) {
          markSignedOut()
          current = generation
        }
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
          void refreshTwinOverview()
        }
      } catch (error) {
        if (current !== generation) return
        const described = await describeBootstrapError(error)
        if (current !== generation) return
        if (isAuthError(error) && described.status !== 403) markSignedOut()
        authenticated.value = false
        sessionChecked.value = false
        bootstrapErrorStatus.value = described.status
        bootstrapError.value = portalErrorMessage(error, described.message)
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
      return current === generation && Boolean(bootstrapError.value)
        && bootstrapErrorStatus.value !== 401
        && (!isAuthError(error) || bootstrapErrorStatus.value === 403)
    }
  }

  async function signIn(usr: string, pwd: string) {
    await login(usr, pwd)
    markSignedOut()
    await bootstrap()
    if (!authenticated.value) throw new Error('登录后仍未取得 HBOS 会话。')
  }

  async function signOut() {
    try {
      await logout()
    } finally {
      // 服务端登出失败也必须清本地会话，避免半死会话滞留。
      markSignedOut()
    }
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
      businessPulse.value = selected.map((metric) => ({
        id: `pulse:${metric.id}`,
        label: metric.label,
        value: String(metric.value),
        trend: `${metric.meta || '业务 Provider'} · 当前可见范围`,
        tone: metric.tone,
      }))
    } catch (error) {
      if (current !== generation || currentRequest !== summariesRequest) return
      if (isAuthError(error)) markSignedOut()
      else summariesError.value = portalErrorMessage(error, '业务概览暂时无法刷新，请稍后重试。')
    } finally {
      if (current === generation && currentRequest === summariesRequest) summariesLoading.value = false
    }
  }

  async function refreshTwinOverview() {
    if (dataSource.value !== 'frappe') return
    if (!apps.value.some((app) => app.id === 'twin' || app.id === 'equipment')) return

    const current = generation
    twinOverviewLoading.value = true
    twinOverviewError.value = null
    try {
      const status = await getTwinStatus()
      if (current !== generation) return
      if (!status.can_enter) throw new Error('当前账号没有设备与数字孪生访问权限。')

      twinEquipmentIds.value = status.equipment_ids
      const primaryEquipment = status.equipment_ids.includes('M607B')
        ? 'M607B'
        : status.equipment_ids[0]
      const manifest = status.asset_root_configured && primaryEquipment
        ? await getTwinManifest(primaryEquipment)
        : null
      if (current !== generation) return
      const knowledgeAvailable = apps.value.some((app) => app.id === 'knowledge')
      const liveConnected = Boolean(
        manifest?.connection_state && manifest.connection_state !== 'not_connected',
      )

      twinStatuses.value = [
        {
          id: 'model',
          label: '私有模型',
          value: status.asset_root_configured ? '已配置' : '待配置',
          tone: status.asset_root_configured ? 'success' : 'warning',
          meta: manifest
            ? `${manifest.label} · ${manifest.model_revision}`
            : '当前设备范围尚无可读取模型制品',
        },
        {
          id: 'equipment',
          label: '设备范围',
          value: status.equipment_ids.length ? status.equipment_ids.join(' / ') : '未授权',
          tone: status.equipment_ids.length ? 'info' : 'warning',
          meta: `按当前会话权限返回${status.policy_revision ? ` · ${status.policy_revision}` : ''}`,
        },
        {
          id: 'knowledge',
          label: '设备级知识',
          value: knowledgeAvailable ? '已接通' : '未开放',
          tone: knowledgeAvailable ? 'success' : 'neutral',
          meta: knowledgeAvailable
            ? '设备上下文可进入受控知识检索'
            : '当前账号没有知识应用入口',
        },
        {
          id: 'live',
          label: '现场实时数据',
          value: liveConnected ? '已连接' : '未接入',
          tone: liveConnected ? 'success' : 'neutral',
          meta: liveConnected
            ? `连接状态：${manifest?.connection_state}`
            : '仅展示私有模型，不以模拟值替代现场状态',
        },
      ]
    } catch (error) {
      if (current !== generation) return
      twinStatuses.value = []
      twinEquipmentIds.value = []
      twinOverviewError.value = error instanceof Error
        ? error.message
        : '数字孪生概览暂时不可用。'
    } finally {
      if (current === generation) twinOverviewLoading.value = false
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
    twinOverviewLoading,
    twinOverviewError,
    twinEquipmentIds,
    limsQueue,
    loading,
    summariesLoading,
    tasksLoading,
    bootstrapError,
    summariesError,
    tasksError,
    bootstrapErrorStatus,
    dataSource,
    authenticated,
    sessionChecked,
    totalActions,
    bootstrap,
    ensureSession,
    signIn,
    signOut,
    markSignedOut,
    clearSession,
    refreshSummaries,
    refreshTasks,
    refreshTwinOverview,
  }
})
