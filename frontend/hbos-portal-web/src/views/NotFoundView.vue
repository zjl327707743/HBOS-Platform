<template>
  <div class="system-state-page">
    <div class="state-visual notfound">
      <CompassOutlined />
    </div>
    <div class="state-code">404</div>
    <h1>这个页面不在 HBOS 中</h1>
    <p>链接可能已经迁移，或应用尚未注册。稳定的 HBOS Deep Link 会尽量避免这种情况。</p>
    <a-space>
      <a-button type="primary" @click="$router.push('/hbos')">返回首页</a-button>
      <a-button @click="$router.push('/hbos/apps')">应用中心</a-button>
    </a-space>
  </div>
</template>
<script setup lang="ts">
import { CompassOutlined } from '@ant-design/icons-vue'
</script>
