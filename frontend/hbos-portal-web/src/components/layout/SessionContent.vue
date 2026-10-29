<template>
  <div v-if="error || blocked && !pending" class="session-recovery" role="status">
    <a-alert type="warning" show-icon :message="error || '正在核对当前登录状态，内容暂时隐藏，草稿仍保留。'" />
    <a-button @click="$emit('retry')">重试核验</a-button>
    <RouterLink to="/hbos/login">前往登录页</RouterLink>
  </div>
  <div v-if="ready ?? !pending" :key="generation" :class="{ 'session-hidden': blocked || !!error }" :inert="blocked || !!error || undefined" :aria-hidden="blocked || !!error || undefined"><slot /></div>
  <a-skeleton v-else-if="pending" active :paragraph="{ rows: 6 }" />
</template>
<script setup lang="ts">
defineProps<{ pending: boolean; ready?: boolean; blocked?: boolean; generation?: number | string; error?: string | null }>()
defineEmits<{ retry: [] }>()
</script>
<style scoped>
.session-hidden{visibility:hidden;pointer-events:none}.session-recovery{display:flex;gap:12px;flex-wrap:wrap;padding:16px}.session-recovery .ant-alert{width:100%}
</style>
