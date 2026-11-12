<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { iconMap } from '@/components/appIcons'
import { openBusinessRoute } from '@/services/businessNavigation'
import type { AppManifestDTO } from '@/contracts/portal'
const props = defineProps<{ app: AppManifestDTO; featured?: boolean }>()
const router = useRouter()
const labels: Record<string, string> = { attendance: '考勤', inventory: '仓储', twin: '数字孪生', equipment: '设备与工艺', knowledge: '知识库' }
const short = computed(() => labels[props.app.id] || props.app.shortTitle)
</script>

<template>
  <button class="v10-app-card" type="button" @click="openBusinessRoute(router, app.id, app.route)">
    <span class="app-icon" :class="[app.accent, 'v10-app-icon-' + app.id]" aria-hidden="true"><component :is="iconMap[app.icon]" /></span>
    <span class="v10-app-card-copy"><strong>{{ featured ? app.title : short }}</strong><small>{{ app.description }}</small></span>
    <span v-if="app.pendingCount" class="v10-app-count" :aria-label="app.pendingCount + ' 项待处理'">{{ app.pendingCount }}</span>
  </button>
</template>
