<script setup lang="ts">
withDefaults(defineProps<{ tone?: 'neutral' | 'brand' | 'success' | 'warning' | 'error' }>(), { tone: 'neutral' })
</script>
<template><span class="r6-status-tag" :class="`tone-${tone}`"><span aria-hidden="true" class="r6-status-dot" /><slot /></span></template>
