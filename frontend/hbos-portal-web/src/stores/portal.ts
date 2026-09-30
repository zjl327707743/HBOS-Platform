import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  getPortalData,
  getPortalSummaries,
  getPortalTasks,
  portalDataSource,
} from '@/services/portalProvider'
import { getTwinManifest, getTwinStatus } from '@/services/p1Api'
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
  const twinOverviewLoading = ref(false)
  const twinOverviewError = ref<string | null>(null)
  const twinEquipmentIds = ref<string[]>([])
  const bootstrapError = ref<string | null>(null)
  const dataSource = ref(portalDataSource)

  const totalActions = computed(() =>
    tasks.value.filter((task) => task.status === 'open').length,
  )

  function clearSession() {
    user.value = null
    branding.value = null
    apps.value = []
    heroMetrics.value = []
    tasks.value = []
    businessPulse.value = []
    twinStatuses.value = []
    twinOverviewLoading.value = false
    twinOverviewError.value = null
    twinEquipmentIds.value = []
    limsQueue.value = []
    bootstrapError.value = null
  }

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
        void refreshTasks().catch(() => undefined)
        void refreshSummaries().catch(() => undefined)
        void refreshTwinOverview().catch(() => undefined)
      }
    } catch (error) {
      bootstrapError.value =
        error instanceof Error ? error.message : 'HBOS 初始化失败'
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
      businessPulse.value = selected.map((metric) => ({
        id: `pulse:${metric.id}`,
        label: metric.label,
        value: String(metric.value),
        trend: `${metric.meta || '业务 Provider'} · 当前可见范围`,
        tone: metric.tone,
      }))
    } finally {
      summariesLoading.value = false
    }
  }

  async function refreshTwinOverview() {
    if (dataSource.value !== 'frappe') return
    if (!apps.value.some((app) => app.id === 'twin' || app.id === 'equipment')) return

    twinOverviewLoading.value = true
    twinOverviewError.value = null
    try {
      const status = await getTwinStatus()
      if (!status.can_enter) throw new Error('当前账号没有设备与数字孪生访问权限。')

      twinEquipmentIds.value = status.equipment_ids
      const primaryEquipment = status.equipment_ids.includes('M607B')
        ? 'M607B'
        : status.equipment_ids[0]
      const manifest = status.asset_root_configured && primaryEquipment
        ? await getTwinManifest(primaryEquipment)
        : null
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
      twinStatuses.value = []
      twinEquipmentIds.value = []
      twinOverviewError.value = error instanceof Error
        ? error.message
        : '数字孪生概览暂时不可用。'
    } finally {
      twinOverviewLoading.value = false
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
    twinOverviewLoading,
    twinOverviewError,
    twinEquipmentIds,
    bootstrapError,
    dataSource,
    totalActions,
    clearSession,
    bootstrap,
    refreshSummaries,
    refreshTasks,
    refreshTwinOverview,
  }
})
