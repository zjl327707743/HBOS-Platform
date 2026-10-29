<script setup lang="ts">
import { computed } from 'vue'

// The application is part of the page's identity, never inferred from the URL.
// Applications without this round's unified role wiring are listed as facts and
// cannot be selected or switched — no fake authorization toggles.
const props = withDefaults(defineProps<{
  modelValue: string
  apps: Array<{ app_id: string; title: string; integrated: boolean }>
  disabled?: boolean
}>(), { disabled: false })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const current = computed(() => props.apps.find(row => row.app_id === props.modelValue && row.integrated) || null)
const options = computed(() => props.apps.filter(row => row.integrated).map(row => ({ value: row.app_id, label: `${row.title} · 已接入` })))
const others = computed(() => props.apps.filter(row => !row.integrated))
function change(value: unknown) {
  const next = String(value || '')
  if (props.disabled || !props.apps.some(row => row.app_id === next && row.integrated)) return
  emit('update:modelValue', next)
}
</script>

<template>
  <div class="r6-app-context">
    <span class="r6-app-context__label">当前应用</span>
    <a-select v-if="options.length > 1" :value="modelValue" :options="options" :disabled="disabled" aria-label="当前应用" class="r6-app-context__select" @update:value="change" />
    <strong v-else class="r6-app-context__fixed">{{ current?.title || '考勤管理' }}</strong>
    <span v-if="current" class="r6-app-context__state">已接入统一角色</span>
    <details v-if="others.length" class="r6-app-context__others">
      <summary>其他应用（{{ others.length }}）</summary>
      <p>{{ others.map(row => row.title).join('、') }}尚未接入统一角色与范围；各自保留原有授权，本页不提供开关。</p>
    </details>
  </div>
</template>
