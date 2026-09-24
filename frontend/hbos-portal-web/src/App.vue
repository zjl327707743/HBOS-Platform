<template>
  <a-config-provider :theme="hbosAntdTheme">
    <RouterView />
  </a-config-provider>
</template>

<script setup lang="ts">
import { hbosAntdTheme } from '@/theme/antdTheme'
</script>
