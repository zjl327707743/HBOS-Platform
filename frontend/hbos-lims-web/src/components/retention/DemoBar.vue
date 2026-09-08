<template>
  <div class="demo-banner">
    <span>{{ noteText }}</span>
    <div class="demo-role">
      <span class="tag-note">演示身份</span>
      <a-select
        :value="demo.role"
        size="small"
        style="width: 200px"
        :options="roleOptions"
        @change="onRole"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { DEMO_ROLES, DEMO_NOTE, demo, setDemoRole, type DemoRole } from '@/demo/retentionDemo'

const props = withDefaults(defineProps<{ note?: string }>(), { note: '' })

const roleOptions = DEMO_ROLES.map((r) => ({
  value: r.value,
  label: `${r.label} · ${r.person}`,
}))
const noteText = computed(() => props.note || DEMO_NOTE)

function onRole(val: DemoRole) {
  setDemoRole(val)
}
</script>
