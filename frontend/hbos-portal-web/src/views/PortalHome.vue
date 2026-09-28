<template>
  <div v-if="portal.user" class="route-stack">
    <HeroWorkspace
      :user-name="portal.user.displayName"
      :total-actions="actionCount"
      :metrics="portal.heroMetrics"
      :app-count="portal.apps.length"
      :show-twin-preview="portal.dataSource === 'mock'"
    />

    <AppCenter :apps="portal.apps" />

    <div class="two-column" v-if="showProfessionalHome">
      <MyWorkPanel :tasks="actionableTasks" />
      <BusinessPulse :items="portal.businessPulse" />
    </div>

    <MyWorkPanel v-else :tasks="actionableTasks.slice(0, 3)" />

    <DigitalTwinPanel v-if="portal.twinStatuses.length" :statuses="portal.twinStatuses" />

    <section v-if="portal.dataSource === 'mock'" class="section-panel glass-surface home-foot-section">
      <div class="section-head">
        <div>
          <span class="section-kicker">最近与快捷操作</span>
          <h2>继续工作</h2>
          <p>普通员工首页到这里即可结束；专业用户再根据 Provider 增加更多业务块。</p>
        </div>
      </div>
      <div class="recent-grid">
        <article><HistoryOutlined /><strong>最近访问</strong><span>LIMS · SAMPLE-001</span></article>
        <article><ScanOutlined /><strong>扫码入库</strong><span>Inventory Quick Action</span></article>
        <article><ClockCircleOutlined /><strong>今日考勤</strong><span>Attendance · 正常</span></article>
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
import { ClockCircleOutlined, HistoryOutlined, ScanOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import AppCenter from '@/components/portal/AppCenter.vue'
import BusinessPulse from '@/components/portal/BusinessPulse.vue'
import DigitalTwinPanel from '@/components/portal/DigitalTwinPanel.vue'
import HeroWorkspace from '@/components/portal/HeroWorkspace.vue'
import MyWorkPanel from '@/components/portal/MyWorkPanel.vue'

const portal = usePortalStore()

// EA-5.3: professional / manager homepage can be denser; ordinary employee can be simpler.
const showProfessionalHome = computed(() => portal.businessPulse.length > 0)
const actionableTasks = computed(() => portal.tasks.filter((task) => task.status === 'open').slice(0, 4))
const actionCount = computed(() => portal.tasks.filter((task) => task.status === 'open').length)
</script>
