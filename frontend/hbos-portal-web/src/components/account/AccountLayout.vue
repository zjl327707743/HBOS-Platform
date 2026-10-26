<template>
  <main class="account-page" :class="{ 'account-r5': variant, 'account-login': variant === 'login' }">
    <div v-if="variant === 'login'" class="account-login-main">
      <section class="account-story" aria-labelledby="login-story-title">
        <RouterLink class="account-brand" to="/hbos" aria-label="HBOS 工作台"><span class="brand-mark" aria-hidden="true">H</span><span><strong class="brand-name">HBOS</strong><small class="brand-caption">海滨智能运营工作台</small></span></RouterLink>
        <p class="story-eyebrow">企业内部使用</p>
        <h1 id="login-story-title">一个员工身份，<br />进入自己的工作空间。</h1>
        <p class="story-lede">飞书优先登录，一个身份对应一个 HBOS 账号。考勤、LIMS、仓储与生产，从同一处进入，按已获授权使用。</p>
        <ul class="story-points">
          <li><SafetyCertificateOutlined aria-hidden="true" /><span><b>用飞书识别本人</b><span>在飞书里确认一次，进入与本人绑定的账号。</span></span></li>
          <li><HistoryOutlined aria-hidden="true" /><span><b>回到原来的页面</b><span>从应用或待办打开时，登录后仍回到该页面。</span></span></li>
          <li><LockOutlined aria-hidden="true" /><span><b>密码作为备用</b><span>飞书暂不可用时，已开通的账号可改用密码登录。</span></span></li>
        </ul>
        <p class="identity-note"><InfoCircleOutlined aria-hidden="true" /><span><strong>一个身份，一个账号。</strong>已有 HBOS 账号的同事，可在“账号与安全”验证本人后绑定飞书，密码、角色与资料保持不变。</span></p>
      </section>
      <section class="account-card hbos-glass-g3" aria-labelledby="login-card-title">
        <header class="account-heading"><p class="account-eyebrow">{{ eyebrow || '欢迎回来' }}</p><h2 id="login-card-title">{{ title }}</h2><p v-if="description">{{ description }}</p></header>
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
    <footer v-if="variant === 'login'" class="login-foot"><span>新乡海滨药业 · HBOS 海滨智能运营工作台</span><slot name="version" /></footer>
  </main>
</template>
<script setup lang="ts">
import { HistoryOutlined, InfoCircleOutlined, LockOutlined, SafetyCertificateOutlined } from '@ant-design/icons-vue'
defineProps<{ title: string; description?: string; eyebrow?: string; wide?: boolean; variant?: 'login' | 'r5' }>()
</script>
<style src="@/theme/account.css"></style>
<style src="@/theme/account-r5.css"></style>
