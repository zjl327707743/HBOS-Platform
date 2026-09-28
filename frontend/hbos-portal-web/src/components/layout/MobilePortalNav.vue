<template>
  <nav class="mobile-portal-nav glass-surface" aria-label="HBOS 移动端导航">
    <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="mobile-nav-item">
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
} from '@ant-design/icons-vue'

defineProps<{ workCount: number }>()

const items = [
  { path: '/hbos', label: '首页', icon: HomeOutlined },
  { path: '/hbos/work', label: '工作', icon: UnorderedListOutlined },
  { path: '/hbos/apps', label: '应用', icon: AppstoreOutlined },
  { path: '/hbos/profile', label: '我的', icon: UserOutlined },
]
</script>
