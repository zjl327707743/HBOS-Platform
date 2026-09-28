<template>
  <aside class="portal-sidebar glass-surface">
    <div class="nav-section-label">工作台</div>
    <RouterLink v-for="item in mainNav" :key="item.path" :to="item.path" class="portal-nav-item" :title="item.label">
      <component :is="item.icon" />
      <span>{{ item.label }}</span>
      <b v-if="item.path === '/hbos/work' && workCount > 0">{{ workCount }}</b>
    </RouterLink>

    <div class="nav-divider"></div>
    <div class="nav-section-label">个人</div>
    <RouterLink to="/hbos/profile" class="portal-nav-item subtle" title="我的">
      <UserOutlined /><span>我的</span>
    </RouterLink>
    <RouterLink to="/hbos/profile" class="portal-nav-item subtle" title="设置">
      <SettingOutlined /><span>设置</span>
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
  SettingOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'

defineProps<{ workCount: number }>()

const mainNav = [
  { path: '/hbos', label: '首页', icon: HomeOutlined },
  { path: '/hbos/work', label: '我的工作', icon: UnorderedListOutlined },
  { path: '/hbos/apps', label: '应用中心', icon: AppstoreOutlined },
]
</script>
