<script setup lang="ts">
import { InboxOutlined } from '@ant-design/icons-vue'
defineProps<{ title: string; description: string; code?: '403' | '404'; homeLabel?: string; showApps?: boolean }>()
</script>

<template>
  <section class="v10-status-screen v10-surface" :class="{ 'v10-status-no-code': !code }">
    <div v-if="code" class="v10-status-code" aria-hidden="true">{{ code }}</div>
    <div v-else class="v10-state-icon" aria-hidden="true"><InboxOutlined /></div>
    <h1 v-if="code">{{ title }}</h1><h2 v-else>{{ title }}</h2>
    <p>{{ description }}</p>
    <div class="v10-actions">
      <a-button type="primary" @click="$router.push('/hbos')">{{ homeLabel || '返回首页' }}</a-button>
      <a-button v-if="showApps" @click="$router.push('/hbos/apps')">查看可用应用</a-button>
    </div>
  </section>
</template>
