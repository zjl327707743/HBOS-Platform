<script setup lang="ts">
import { computed, ref } from 'vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import PortalAppCard from '@/components/portal/PortalAppCard.vue'
import PortalState from '@/components/portal/PortalState.vue'

const portal = usePortalStore()
const query = ref('')
const term = computed(() => query.value.trim().toLocaleLowerCase())
const visibleApps = computed(() => portal.apps.filter(app =>
  !term.value || (app.shortTitle + ' ' + app.title + ' ' + app.description).toLocaleLowerCase().includes(term.value),
))
const featured = computed(() => visibleApps.value.filter(app => app.featured))
</script>

<template>
  <section class="v10-apps-page">
    <div class="v10-page-heading v10-apps-intro">
      <div><h1>应用中心</h1><p>找到工作所需的应用，继续你的专业工作。</p></div>
      <a-input v-model:value="query" class="v10-app-search" allow-clear aria-label="搜索应用名称或用途" placeholder="搜索应用名称或用途">
        <template #prefix><SearchOutlined aria-hidden="true" /></template>
      </a-input>
    </div>
    <a-skeleton v-if="portal.loading" active aria-label="正在读取可用应用" />
    <PortalState v-else-if="portal.bootstrapError" kind="error" title="可用应用暂未确认" :description="portal.bootstrapError" retry @retry="portal.bootstrap().catch(() => undefined)" />
    <template v-else>
      <section v-if="featured.length" class="v10-apps-section">
        <div class="section-head"><div><h2>常用应用</h2><p>常用工作入口，集中在这里。</p></div><small>平台配置</small></div>
        <div class="v10-app-grid v10-app-featured"><PortalAppCard v-for="app in featured" :key="app.id" :app="app" featured /></div>
      </section>
      <section class="v10-apps-section">
        <div class="section-head"><div><h2>全部应用</h2><p>只显示你有权使用的应用。</p></div><small aria-live="polite">{{ visibleApps.length }} 个可用应用</small></div>
        <div v-if="visibleApps.length" class="v10-app-grid"><PortalAppCard v-for="app in visibleApps" :key="app.id" :app="app" /></div>
        <PortalState v-else :title="term ? '没有匹配的应用' : '当前没有可用应用'" :description="term ? '试试其他名称，或清除搜索查看全部。' : '如需使用业务应用，请联系对应的负责人。'">
          <a-button v-if="term" size="small" @click="query = ''">清除搜索</a-button>
        </PortalState>
      </section>
    </template>
  </section>
</template>
