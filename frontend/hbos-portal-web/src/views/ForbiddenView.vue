<template>
  <div class="system-state-page">
    <div class="state-visual forbidden">
      <SafetyCertificateOutlined />
    </div>
    <div class="state-code">403</div>
    <h1>你没有权限进入这个应用</h1>
    <p>应用入口和后端 API 都会独立校验权限。若你认为这是配置错误，请联系业务管理员。</p>
    <a-space>
      <a-button type="primary" @click="$router.push('/hbos')">返回 HBOS</a-button>
      <a-button @click="$router.push('/hbos/apps')">查看可用应用</a-button>
    </a-space>
  </div>
</template>
<script setup lang="ts">
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
</script>
