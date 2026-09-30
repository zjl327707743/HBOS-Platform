<template>
  <a-config-provider :theme="hbosAntdTheme" :locale="zhCN">
    <RouterView />
  </a-config-provider>
</template>

<script setup lang="ts">
import { hbosAntdTheme } from '@/theme/antdTheme'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
</script>
