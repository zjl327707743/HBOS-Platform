<script setup lang="ts">
import { computed } from 'vue'
import PortalAppCard from './PortalAppCard.vue'
import PortalState from './PortalState.vue'
import type { AppManifestDTO } from '@/contracts/portal'

const props = defineProps<{ apps: AppManifestDTO[] }>()
const appOrder = ['lims', 'inventory', 'attendance', 'knowledge', 'twin', 'equipment', 'production']
const order = (id: string) => appOrder.includes(id) ? appOrder.indexOf(id) : appOrder.length
const primaryApps = computed(() => props.apps
  .filter(app => app.featured || appOrder.includes(app.id))
  .sort((left, right) => order(left.id) - order(right.id)))
</script>

<template>
  <section class="section-panel glass-surface v10-home-entry">
    <div class="section-head">
      <div><h2>你的业务入口</h2><p>从熟悉的应用，继续今天的工作。</p></div>
      <RouterLink to="/hbos/apps">全部应用</RouterLink>
    </div>
    <div v-if="primaryApps.length" class="v10-app-grid">
      <PortalAppCard v-for="app in primaryApps" :key="app.id" :app="app" />
    </div>
    <PortalState v-else title="当前没有常用应用" description="可以前往应用中心查看已开放的入口。" />
    <RouterLink v-if="apps.some(app => app.id === 'inventory')" class="v10-minor-link" to="/hbos/inventory/item">仓储 · 物料只读浏览</RouterLink>
  </section>
</template>
