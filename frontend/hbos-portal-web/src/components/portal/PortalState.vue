<script setup lang="ts">
import { ExclamationCircleOutlined, InboxOutlined } from '@ant-design/icons-vue'
defineProps<{ title: string; description?: string; kind?: 'empty' | 'error'; retry?: boolean }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="v10-data-state" :role="kind === 'error' ? 'alert' : 'status'">
    <span class="v10-state-icon" aria-hidden="true"><ExclamationCircleOutlined v-if="kind === 'error'" /><InboxOutlined v-else /></span>
    <strong>{{ title }}</strong>
    <p v-if="description">{{ description }}</p>
    <a-button v-if="retry" size="small" @click="$emit('retry')">重试读取</a-button>
    <slot />
  </div>
</template>
