<template>
  <main class="account-page">
    <section class="account-card hbos-glass-g3" :class="{ 'account-card-wide': wide }">
      <RouterLink class="account-brand" to="/hbos" aria-label="HBOS 工作台"><span class="brand-mark">H</span><span><strong class="brand-name">HBOS</strong><small class="brand-caption">海滨智能运营工作台</small></span></RouterLink>
      <header class="account-heading"><div class="account-symbol" aria-hidden="true"><SafetyCertificateOutlined /></div><p class="account-eyebrow">{{ eyebrow || '账号与安全' }}</p><h1>{{ title }}</h1><p v-if="description">{{ description }}</p></header>
      <slot />
      <footer v-if="$slots.footer" class="account-footer"><slot name="footer" /></footer>
    </section>
  </main>
</template>
<script setup lang="ts">
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
defineProps<{ title: string; description?: string; eyebrow?: string; wide?: boolean }>()
</script>
<style src="@/theme/account.css"></style>
