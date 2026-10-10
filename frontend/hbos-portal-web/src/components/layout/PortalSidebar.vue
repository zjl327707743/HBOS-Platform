<template>
  <aside class="portal-sidebar glass-surface">
    <div class="nav-section-label">工作台</div>
    <RouterLink v-for="item in mainNav" :key="item.path" :to="item.path" class="portal-nav-item" :title="item.label">
      <component :is="item.icon" />
      <span>{{ item.label }}</span>
      <b v-if="item.path === '/hbos/work' && workCount > 0">{{ workCount }}</b>
    </RouterLink>

    <div class="nav-divider"></div>
    <div class="nav-section-label">平台管理</div>
    <RouterLink to="/hbos/admin/people" class="portal-nav-item" :class="{ 'router-link-exact-active': route.path.startsWith('/hbos/admin/') }" title="人员与权限" aria-label="人员与权限"><TeamOutlined /><span>人员与权限</span></RouterLink>

    <div class="nav-divider"></div>
    <div class="nav-section-label">个人</div>
    <RouterLink to="/hbos/profile" class="portal-nav-item subtle" title="我的与设置">
      <UserOutlined /><span>我的与设置</span>
    </RouterLink>

    <div class="sidebar-spacer"></div>
    <div class="portal-side-note">
      <span>业务应用从“应用中心”或顶部应用切换器进入。</span>
    </div>
  </aside>
</template>

<script setup lang="ts">
import {
  AppstoreOutlined,
  HomeOutlined,
  UnorderedListOutlined,
  UserOutlined,
  TeamOutlined,
} from '@ant-design/icons-vue'
import { useRoute } from 'vue-router'

defineProps<{ workCount: number }>()
const route = useRoute()

const mainNav = [
  { path: '/hbos', label: '首页', icon: HomeOutlined },
  { path: '/hbos/work', label: '我的工作', icon: UnorderedListOutlined },
  { path: '/hbos/apps', label: '应用中心', icon: AppstoreOutlined },
]
</script>

<style scoped>
@media (max-width: 1280px) and (min-width: 768px) {
  .portal-nav-item > span:not(.anticon), .nav-section-label, .portal-side-note { display: none; }
  .portal-nav-item > .anticon { font-size: 20px; }
}
</style>
