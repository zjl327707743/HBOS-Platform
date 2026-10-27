<script setup lang="ts">
import { computed } from 'vue'
import { AppstoreOutlined, HomeOutlined, UnorderedListOutlined, UserOutlined, TeamOutlined, SafetyCertificateOutlined, ApartmentOutlined, HistoryOutlined, SettingOutlined, LockOutlined } from '@ant-design/icons-vue'
import { canIam, hasManagementAccess } from '@/services/iamAccess'
import { managementLinks } from '@/services/managementNavigation'
withDefaults(defineProps<{ workCount: number; management?: boolean }>(), { management: false })
const links = computed(managementLinks)
const icons = { people: TeamOutlined, department: ApartmentOutlined, roles: SafetyCertificateOutlined, audit: HistoryOutlined }
const mainNav = [{ path: '/hbos', label: '首页', icon: HomeOutlined }, { path: '/hbos/work', label: '我的工作', icon: UnorderedListOutlined }, { path: '/hbos/apps', label: '应用中心', icon: AppstoreOutlined }]
</script>
<template>
  <aside class="portal-sidebar glass-surface" :class="{ 'r6-management-sidebar': management }">
    <template v-if="management">
      <div class="r6-space-identity"><span class="r6-space-icon"><SafetyCertificateOutlined /></span><div><strong>管理中心</strong><small>组织与访问安排</small></div></div>
      <div class="r6-side-label">组织管理</div>
      <nav class="r6-local-nav" aria-label="管理中心"><RouterLink v-for="item in links" :key="item.path" :to="item.path"><component :is="icons[item.icon as keyof typeof icons]" /><span>{{ item.label }}</span></RouterLink></nav>
      <div class="sidebar-spacer" />
      <details v-if="canIam('iam.access.read')" class="r6-more-tools"><summary><SettingOutlined />更多管理工具</summary><RouterLink to="/hbos/admin/access">原应用权限与访问诊断</RouterLink></details>
      <p class="r6-sidebar-note"><LockOutlined />每项安排都在你的管理范围内完成</p>
    </template>
    <template v-else>
      <div class="nav-section-label">工作台</div>
      <RouterLink v-for="item in mainNav" :key="item.path" :to="item.path" class="portal-nav-item" :title="item.label" :aria-label="item.label"><component :is="item.icon" /><span>{{ item.label }}</span><b v-if="item.path === '/hbos/work' && workCount > 0">{{ workCount }}</b></RouterLink>
      <RouterLink v-if="hasManagementAccess()" to="/hbos/admin" class="portal-nav-item" title="管理中心"><TeamOutlined /><span>管理中心</span></RouterLink>
      <div class="nav-divider" /><div class="nav-section-label">个人</div>
      <RouterLink to="/hbos/profile" class="portal-nav-item subtle" title="个人中心"><UserOutlined /><span>个人中心</span></RouterLink>
      <div class="sidebar-spacer" /><div class="portal-side-note"><span>业务应用从“应用中心”或顶部应用切换器进入。</span></div>
    </template>
  </aside>
</template>
