<script setup lang="ts">
import mark from '@/assets/portal-v10/hbos-logo.png'
</script>

<template>
  <RouterLink to="/hbos" class="v10-brand" aria-label="海滨智能工作平台首页">
    <img :src="mark" alt="" width="36" height="34" />
    <span><strong>海滨智能工作平台</strong><small>HBOS · WORKSPACE</small></span>
  </RouterLink>
</template>
