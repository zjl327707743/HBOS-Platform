<template>
  <a-config-provider :theme="hbosAntdTheme" :locale="zhCN">
    <div :class="{ 'portal-demo-mode': portalDataSource === 'mock' }">
      <div v-if="portalDataSource === 'mock'" class="portal-demo-banner" role="status">演示数据 · 当前为 Mock 模式，业务操作不可写入真实系统</div>
      <RouterView />
    </div>
  </a-config-provider>
</template>

<script setup lang="ts">
import { portalDataSource } from '@/services/portalProvider'
import { hbosAntdTheme } from '@/theme/antdTheme'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
</script>
