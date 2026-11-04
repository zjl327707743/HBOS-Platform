<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { canIam, iamSession } from '@/services/iamAccess'
import { managementLinks } from '@/services/managementNavigation'
defineOptions({ name: 'HbosManagementWorkspace' })
const links = computed(managementLinks), route = useRoute()
</script>
<template>
  <section class="iam-workspace r6-workspace">
    <nav class="r6-mobile-local" aria-label="管理中心页面"><RouterLink v-for="link in links" :key="link.path" :to="link.path">{{ link.label }}</RouterLink><RouterLink v-if="canIam('iam.access.read') && !links.some(link => link.cap === 'iam.access.read')" to="/hbos/admin/access">更多工具</RouterLink></nav>
    <div class="r6-context-row"><a-breadcrumb><a-breadcrumb-item><RouterLink to="/hbos">工作台</RouterLink></a-breadcrumb-item><a-breadcrumb-item>管理中心</a-breadcrumb-item><a-breadcrumb-item>{{ route?.meta.title }}</a-breadcrumb-item></a-breadcrumb><span>安排他人的工作访问</span></div>
    <a-alert v-if="!iamSession.ready && !route?.path.endsWith('/unavailable')" :message="iamSession.error || '正在确认当前账号的管理能力，暂不显示管理内容。'" :type="iamSession.error ? 'warning' : 'info'" />
    <RouterView v-if="iamSession.ready || route?.path.endsWith('/unavailable')" v-slot="{ Component }"><KeepAlive :max="5"><component :is="Component" :key="route?.path" /></KeepAlive></RouterView>
    <footer class="r6-page-footer">HBOS · 海滨智能运营工作台</footer>
  </section>
</template>
