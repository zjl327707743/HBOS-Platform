<template>
  <a-config-provider :theme="theme" :locale="zhCN">
    <div :class="{ 'portal-demo-mode': showMockBanner }">
      <div v-if="showMockBanner" class="portal-demo-banner" role="status">演示数据 · 当前为 Mock 模式，业务操作不可写入真实系统</div>
      <RouterView />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { portalDataSource } from '@/services/portalProvider'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { hbosAntdTheme, hbosManagementTheme } from '@/theme/antdTheme'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
const route = useRoute()
const showMockBanner = computed(() => portalDataSource === 'mock' &&
  !(import.meta.env.MODE === 'knowledge-preview' && /^\/hbos\/knowledge(?:\/|$)/.test(route.path)))
const theme = computed(() => route.path === '/hbos/profile' || route.path.startsWith('/hbos/admin') ? hbosManagementTheme : hbosAntdTheme)
</script>
