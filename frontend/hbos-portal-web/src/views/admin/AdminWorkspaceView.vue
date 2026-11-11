<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ApartmentOutlined, AppstoreOutlined, ClockCircleOutlined, TeamOutlined, UsergroupAddOutlined } from '@ant-design/icons-vue'
import { canIam, iamSession } from '@/services/iamAccess'
import { managementLinks } from '@/services/managementNavigation'

defineOptions({ name: 'HbosManagementWorkspace' })
const route = useRoute()
const links = computed(() => {
  const primary = managementLinks()
  const access = canIam('iam.access.read') ? [{ path: '/hbos/admin/access', label: '其他应用权限', cap: 'iam.access.read', icon: 'access' }] : []
  return [...primary.filter(link => link.cap !== 'iam.access.read'), ...access]
})
const icons = { people: UsergroupAddOutlined, department: ApartmentOutlined, roles: AppstoreOutlined, audit: ClockCircleOutlined, access: TeamOutlined }
</script>

<template>
  <section class="iam-workspace r6-workspace v10-admin">
    <nav v-if="links.length" class="v10-admin-nav" aria-label="管理中心页面">
      <RouterLink v-for="link in links" :key="link.path" :to="link.path">
        <component :is="icons[link.icon as keyof typeof icons]" aria-hidden="true" />
        {{ link.cap === 'iam.departments.read' ? '部门权限' : link.label }}
      </RouterLink>
    </nav>
    <a-alert v-if="!iamSession.ready && !route?.path.endsWith('/unavailable')" :message="iamSession.error || '正在确认当前账号的管理能力，暂不显示管理内容。'" :type="iamSession.error ? 'warning' : 'info'" />
    <RouterView v-if="iamSession.ready || route?.path.endsWith('/unavailable')" v-slot="{ Component }"><KeepAlive :max="5"><component :is="Component" :key="route?.path" /></KeepAlive></RouterView>
  </section>
</template>
