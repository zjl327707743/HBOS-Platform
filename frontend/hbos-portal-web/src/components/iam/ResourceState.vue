<script setup lang="ts">
defineProps<{ loading?: boolean; error?: string; empty?: boolean; emptyText?: string }>()
defineEmits<{ retry: [] }>()
</script>
<template>
  <div v-if="error" class="r6-resource-error" role="alert"><a-alert type="warning" show-icon :message="error" /><a-button @click="$emit('retry')">重新读取</a-button></div>
  <a-skeleton v-if="loading" active :paragraph="{ rows: 5 }" />
  <a-empty v-else-if="!error && empty" :description="emptyText || '暂无可见内容'" />
  <slot v-else-if="!error" />
</template>
