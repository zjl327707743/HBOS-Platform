<template>
  <main v-if="v10" class="v10-account" :class="{ 'v10-login': variant === 'login' }">
    <div class="v10-auth-shell">
      <section class="v10-auth-story" aria-label="海滨智能工作平台">
        <PortalBrand />
        <div class="v10-story-copy">
          <h2 class="v10-story-title">{{ variant === 'login' ? '让工作有序，' : '安心连接，' }}<br /><span>{{ variant === 'login' ? '让创造发生。' : '继续你的工作。' }}</span></h2>
          <p>面向员工的智能工作空间。<br />连接应用，汇集工作事项。</p>
        </div>
        <div class="v10-auth-art" aria-hidden="true"><i /><i /><i /></div>
        <div class="v10-auth-company"><img :src="joincareMark" alt="健康元集团" width="118" height="42" /><span>连接日常工作<br />专注每一次创造</span></div>
      </section>
      <section class="v10-auth-form" :aria-labelledby="headingId">
        <div v-if="$slots.back" class="v10-auth-back"><slot name="back" /></div>
        <header class="v10-auth-heading">
          <span>{{ eyebrow || (variant === 'login' ? '工作，从这里开始' : '个人中心') }}</span>
          <h1 :id="headingId">{{ title }}</h1>
          <p v-if="description">{{ description }}</p>
          <small v-if="previewLabel" role="status">{{ previewLabel }}</small>
        </header>
        <div class="v10-auth-fields"><slot /></div>
        <footer class="v10-auth-footer">
          <slot name="footer">登录或恢复遇到问题，请联系系统管理员。</slot>
          <slot v-if="!previewLabel" name="version" />
        </footer>
      </section>
    </div>
  </main>
  <main v-else class="account-page" :class="{ 'account-r5': variant === 'r5' || variant === 'login', 'account-login': variant === 'login', 'has-login-background': variant === 'login' && Boolean(loginBackgroundStyle) }" :style="variant === 'login' ? loginBackgroundStyle : undefined">
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
import { useId } from 'vue'
import PortalBrand from '@/components/portal/PortalBrand.vue'
import joincareMark from '@/assets/portal-v10/joincare-logo.png'
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
import brandBackground from '@/assets/hbos-login-background.webp'
// The Owner approved this bundled asset for publication. An explicit empty override disables it.
const backgroundOverride = import.meta.env.VITE_LOGIN_BACKGROUND_URL
const loginBackgroundUrl = backgroundOverride ?? brandBackground
const validOverride = /^\/assets\/hbos_portal\/portal\/[A-Za-z0-9_-][A-Za-z0-9._/-]*\.(webp|avif|png|jpe?g)$/i.test(loginBackgroundUrl) && !loginBackgroundUrl.includes('..')
const loginBackgroundStyle = backgroundOverride === undefined || validOverride
  ? { '--account-login-background': `url("${loginBackgroundUrl}")` } : undefined
const headingId = useId()
const previewLabel = import.meta.env.DEV ? import.meta.env.VITE_ACCOUNT_PREVIEW_LABEL : ''
defineProps<{ v10?: boolean; title: string; description?: string; eyebrow?: string; wide?: boolean; variant?: 'login' | 'r5' }>()
</script>
<style src="@/theme/account.css"></style>
<style src="@/theme/account-r5.css"></style>
