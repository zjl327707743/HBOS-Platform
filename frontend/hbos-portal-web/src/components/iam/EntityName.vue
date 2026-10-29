<script setup lang="ts">
import { computed } from 'vue'

// One identity treatment for departments, people and confirmations: the visible
// label is bounded to two lines, the full value stays reachable with a real
// control (not hover-only) and the stable id disambiguates equal names.
const props = withDefaults(defineProps<{
  name?: string | null
  meta?: string | null
  id?: string | null
  interactive?: boolean
  as?: string
  expandable?: boolean
  ariaLabel?: string
}>(), { interactive: false, as: 'span', expandable: true, ariaLabel: '' })
const emit = defineEmits<{ activate: [] }>()

const text = computed(() => String(props.name || '').trim())
const label = computed(() => text.value || '名称待核对')
const needsExpander = computed(() => props.expandable && [...text.value].length > 24)
</script>

<template>
  <div class="r6-entity-name" :class="{ 'is-interactive': interactive }">
    <component :is="interactive ? 'button' : as" class="r6-entity-name__label" :type="interactive ? 'button' : undefined" :aria-label="ariaLabel || undefined" :title="needsExpander ? label : undefined" @click="interactive && emit('activate')">{{ label }}</component>
    <small v-if="meta || id" class="r6-entity-name__meta">{{ meta }}<template v-if="meta && id"> · </template><template v-if="id">{{ id }}</template></small>
    <details v-if="needsExpander" class="r6-entity-name__more">
      <summary>查看完整名称</summary>
      <p class="r6-entity-name__full">{{ label }}</p>
    </details>
  </div>
</template>
