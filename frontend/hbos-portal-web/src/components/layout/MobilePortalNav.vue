<template>
  <nav class="mobile-portal-nav glass-surface" aria-label="HBOS 移动端导航">
    <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="mobile-nav-item" :class="{ 'router-link-exact-active': item.path === '/hbos/admin/people' && route.path.startsWith('/hbos/admin/') }">
      <component :is="item.icon" />
      <span>{{ item.label }}</span>
      <b v-if="item.path === '/hbos/work' && workCount > 0">{{ workCount }}</b>
    </RouterLink>
  </nav>
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

const items = [
  { path: '/hbos', label: '首页', icon: HomeOutlined },
  { path: '/hbos/work', label: '工作', icon: UnorderedListOutlined },
  { path: '/hbos/apps', label: '应用', icon: AppstoreOutlined },
  { path: '/hbos/admin/people', label: '人员权限', icon: TeamOutlined },
  { path: '/hbos/profile', label: '我的与设置', icon: UserOutlined },
]
</script>
