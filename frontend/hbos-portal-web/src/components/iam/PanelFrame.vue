<script setup lang="ts">
withDefaults(defineProps<{ as?: 'aside' | 'section'; region: string; label: string }>(), { as: 'section' })
</script>
<template>
  <component :is="as" class="r6-panel-frame r6-surface">
    <div v-if="$slots.header" class="r6-panel-header"><slot name="header" /></div>
    <div class="r6-panel-scroll" :data-scroll-region="region" role="region" tabindex="0" :aria-label="label"><slot /></div>
    <div v-if="$slots.footer" class="r6-panel-footer"><slot name="footer" /></div>
  </component>
</template>
