<template>
  <main class="account-page" :class="{ 'account-r5': variant === 'r5' || variant === 'login', 'account-login': variant === 'login', 'has-login-background': variant === 'login' && Boolean(loginBackgroundStyle) }" :style="variant === 'login' ? loginBackgroundStyle : undefined">
    <div v-if="variant === 'login'" class="account-login-main">
      <section class="account-story" aria-labelledby="login-story-title">
        <RouterLink class="account-brand" to="/hbos" aria-label="HBOS 工作台"><span class="brand-mark" aria-hidden="true">H</span><span><strong class="brand-name">HBOS</strong><small class="brand-caption">新乡海滨药业 · 智能运营工作台</small></span></RouterLink>
        <h1 id="login-story-title">欢迎使用 HBOS</h1>
        <p class="story-lede">一个入口，连接日常工作。</p>
      </section>
      <section class="account-card hbos-glass-g3" aria-labelledby="login-card-title">
        <header class="account-heading"><p v-if="eyebrow" class="account-eyebrow">{{ eyebrow }}</p><h2 id="login-card-title">{{ title }}</h2><p v-if="description">{{ description }}</p></header>
        <slot />
        <footer v-if="$slots.footer" class="account-footer"><slot name="footer" /></footer>
      </section>
    </div>
    <section v-else class="account-card hbos-glass-g3" :class="{ 'account-card-wide': wide }">
      <RouterLink class="account-brand" to="/hbos" aria-label="HBOS 工作台"><span class="brand-mark">H</span><span><strong class="brand-name">HBOS</strong><small class="brand-caption">海滨智能运营工作台</small></span></RouterLink>
      <header class="account-heading"><div class="account-symbol" aria-hidden="true"><SafetyCertificateOutlined /></div><p class="account-eyebrow">{{ eyebrow || '账号与安全' }}</p><h1>{{ title }}</h1><p v-if="description">{{ description }}</p></header>
      <slot />
      <footer v-if="$slots.footer" class="account-footer"><slot name="footer" /></footer>
    </section>
    <footer v-if="variant === 'login'" class="login-foot"><span>新乡海滨药业 · HBOS</span><slot name="version" /></footer>
  </main>
</template>
<script setup lang="ts">
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
// UAT may serve the Owner asset privately; the normal bundle has no external image dependency.
const loginBackgroundUrl = import.meta.env.VITE_LOGIN_BACKGROUND_URL || ''
const loginBackgroundStyle = /^\/assets\/hbos_portal\/portal\/[A-Za-z0-9_-][A-Za-z0-9._/-]*\.(webp|avif|png|jpe?g)$/i.test(loginBackgroundUrl) && !loginBackgroundUrl.includes('..')
  ? { '--account-login-background': `url("${loginBackgroundUrl}")` } : undefined
defineProps<{ title: string; description?: string; eyebrow?: string; wide?: boolean; variant?: 'login' | 'r5' }>()
</script>
<style src="@/theme/account.css"></style>
<style src="@/theme/account-r5.css"></style>
