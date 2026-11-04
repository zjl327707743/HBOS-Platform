<script setup lang="ts">
defineProps<{ title: string; description: string; eyebrow?: string }>()
</script>

<template>
  <header class="r6-page-heading">
    <div><p v-if="eyebrow" class="r6-eyebrow">{{ eyebrow }}</p><h1>{{ title }}</h1><p>{{ description }}</p></div>
    <div v-if="$slots.default" class="r6-heading-actions"><slot /></div>
  </header>
</template>
