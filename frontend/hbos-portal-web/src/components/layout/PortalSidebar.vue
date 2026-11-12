<script setup lang="ts">
import { computed, ref } from 'vue'
import { AppstoreOutlined, HomeOutlined, UnorderedListOutlined, UserOutlined, TeamOutlined, SafetyCertificateOutlined, ApartmentOutlined, HistoryOutlined, SettingOutlined, LockOutlined, MenuFoldOutlined, MenuUnfoldOutlined, EllipsisOutlined, CloseOutlined } from '@ant-design/icons-vue'
import { canIam, hasManagementAccess } from '@/services/iamAccess'
import { managementLinks } from '@/services/managementNavigation'
const props = withDefaults(defineProps<{ workCount: number; management?: boolean; portalDesign?: boolean; collapsed?: boolean; inDrawer?: boolean }>(), { management: false })
const emit = defineEmits<{toggle: []}>()
const expanded = ref(false)
function toggleManagement() {
  if (props.collapsed) { emit('toggle'); expanded.value = true }
  else expanded.value = !expanded.value
}
const links = computed(managementLinks)
const icons = { people: TeamOutlined, department: ApartmentOutlined, roles: SafetyCertificateOutlined, audit: HistoryOutlined, access: SettingOutlined }
const mainNav = [{ path: '/hbos', label: '首页', icon: HomeOutlined }, { path: '/hbos/work', label: '我的工作', icon: UnorderedListOutlined }, { path: '/hbos/apps', label: '应用中心', icon: AppstoreOutlined }]
</script>
<template>
  <aside class="portal-sidebar glass-surface" :class="{ 'r6-management-sidebar': management && !portalDesign, 'v10-sidebar': portalDesign }">
    <template v-if="portalDesign">
      <div class="v10-side-scroll">
        <div class="v10-side-heading"><span>工作空间</span><button type="button" :aria-label="inDrawer ? '关闭导航' : collapsed ? '展开侧栏' : '折叠侧栏'" @click="emit('toggle')"><CloseOutlined v-if="inDrawer" /><MenuUnfoldOutlined v-else-if="collapsed" /><MenuFoldOutlined v-else /></button></div>
        <nav aria-label="工作空间">
          <RouterLink v-for="item in mainNav" :key="item.path" :to="item.path" class="portal-nav-item" :title="item.label" :aria-label="item.label"><component :is="item.icon" /><span>{{ item.label }}</span><b v-if="item.path === '/hbos/work' && workCount > 0">{{ workCount }}</b></RouterLink>
          <div v-if="hasManagementAccess()" class="v10-side-management">
            <button type="button" class="portal-nav-item" :class="{ 'v10-active': $route.path.startsWith('/hbos/admin') }" aria-label="管理中心" :aria-expanded="expanded && !collapsed" @click="toggleManagement"><AppstoreOutlined /><span>管理中心</span><EllipsisOutlined /></button>
            <div v-if="expanded && !collapsed" class="v10-side-subnav">
              <RouterLink v-for="item in links" :key="item.path" :to="item.path"><component :is="icons[item.icon as keyof typeof icons]" />{{ item.label }}</RouterLink>
              <RouterLink v-if="canIam('iam.access.read') && !links.some(item => item.cap === 'iam.access.read')" to="/hbos/admin/access"><SettingOutlined />其他应用权限</RouterLink>
            </div>
          </div>
          <div class="nav-divider" />
          <RouterLink to="/hbos/profile" class="portal-nav-item" title="个人中心" aria-label="个人中心"><UserOutlined /><span>个人中心</span></RouterLink>
        </nav>
      </div>
      <div class="v10-side-footer"><LockOutlined /><span>工作空间按账号权限开放</span></div>
    </template>
    <template v-else-if="management">
      <div class="r6-space-identity"><span class="r6-space-icon"><SafetyCertificateOutlined /></span><div><strong>管理中心</strong><small>组织与访问安排</small></div></div>
      <div class="r6-side-label">组织管理</div>
      <nav class="r6-local-nav" aria-label="管理中心"><RouterLink v-for="item in links" :key="item.path" :to="item.path"><component :is="icons[item.icon as keyof typeof icons]" /><span>{{ item.label }}</span></RouterLink></nav>
      <div class="sidebar-spacer" />
      <details v-if="canIam('iam.access.read') && !links.some(item => item.cap === 'iam.access.read')" class="r6-more-tools"><summary><SettingOutlined />更多管理工具</summary><RouterLink to="/hbos/admin/access">原应用权限与访问诊断</RouterLink></details>
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
