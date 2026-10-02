<template>
  <div v-if="portal.user" class="route-stack">
    <HeroWorkspace
      :user-name="portal.user.displayName"
      :total-actions="actionCount"
      :metrics="portal.heroMetrics"
      :app-count="portal.apps.length"
      :show-twin-preview="hasTwinApp"
      :twin-ready="twinReady"
      :twin-state-label="twinPreviewLabel"
    />

    <AppCenter :apps="portal.apps" />

    <div class="two-column">
      <MyWorkPanel :tasks="actionableTasks" :loading="portal.tasksLoading" />
      <BusinessPulse
        :items="portal.businessPulse"
        :loading="portal.summariesLoading"
        :live="portal.dataSource === 'frappe'"
      />
    </div>

    <DigitalTwinPanel
      v-if="hasTwinApp"
      :statuses="portal.twinStatuses"
      :equipment-ids="portal.twinEquipmentIds"
      :loading="portal.twinOverviewLoading"
      :error="portal.twinOverviewError"
    />

    <section class="section-panel glass-surface home-foot-section">
      <div class="section-head">
        <div>
          <span class="section-kicker">最近与快捷操作</span>
          <h2>继续工作</h2>
          <p>只提供当前账号真实可进入的常用入口。</p>
        </div>
      </div>
      <div class="recent-grid">
        <RouterLink v-if="hasKnowledgeApp" class="recent-action" to="/hbos/knowledge">
          <ReadOutlined /><strong>知识检索</strong><span>内部资料与来源证据</span>
        </RouterLink>
        <RouterLink v-if="hasTwinApp" class="recent-action" to="/hbos/twin">
          <DeploymentUnitOutlined /><strong>设备模型</strong><span>{{ twinEquipmentLabel }}</span>
        </RouterLink>
        <RouterLink class="recent-action" to="/hbos/apps">
          <AppstoreOutlined /><strong>全部应用</strong><span>{{ portal.apps.length }} 个可用入口</span>
        </RouterLink>
      </div>
    </section>
  </div>

  <div v-else class="loading-grid">
    <a-skeleton active />
    <a-skeleton active />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AppstoreOutlined, DeploymentUnitOutlined, ReadOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import AppCenter from '@/components/portal/AppCenter.vue'
import BusinessPulse from '@/components/portal/BusinessPulse.vue'
import DigitalTwinPanel from '@/components/portal/DigitalTwinPanel.vue'
import HeroWorkspace from '@/components/portal/HeroWorkspace.vue'
import MyWorkPanel from '@/components/portal/MyWorkPanel.vue'

const portal = usePortalStore()

const actionableTasks = computed(() => portal.tasks.filter((task) => task.status === 'open').slice(0, 4))
const actionCount = computed(() => portal.tasks.filter((task) => task.status === 'open').length)
const hasTwinApp = computed(() => portal.apps.some((app) => app.id === 'twin' || app.id === 'equipment'))
const hasKnowledgeApp = computed(() => portal.apps.some((app) => app.id === 'knowledge'))
const twinReady = computed(() => portal.twinStatuses.some(
  (status) => status.id === 'model' && status.value === '已配置',
))
const twinPreviewLabel = computed(() => {
  if (portal.twinOverviewLoading) return '状态读取中'
  if (portal.twinOverviewError) return '入口可用'
  return twinReady.value ? '模型可用' : '入口可用'
})
const twinEquipmentLabel = computed(() =>
  (portal.twinEquipmentIds || []).length
    ? `${(portal.twinEquipmentIds || []).join(' / ')} · 私有模型`
    : '进入设备与工艺空间',
)
</script>
