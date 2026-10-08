<template>
  <nav class="twin-catalog" aria-label="设备与场景目录">
    <button v-for="entry in entries" :key="entry.entry_id" :class="{selected: entry.entry_id === selected}" :aria-pressed="entry.entry_id === selected" @click="$emit('choose', entry)">
      <span class="entry-icon" aria-hidden="true">{{ entry.entity_type === 'scene' ? '▱' : '◈' }}</span>
      <span><strong>{{ entry.label }}</strong><small>{{ entry.entity_type === 'scene' ? '两台设备 · 独立会话' : '设备认知与工艺示教' }}</small></span>
      <span class="entry-state" :class="{ready: entry.availability === 'READY'}">{{ entry.availability === 'READY' ? '进入' : entry.availability === 'MEMBERS_PENDING' ? '待成员确认' : '制品暂不可用' }}</span>
    </button>
  </nav>
</template>
<script setup lang="ts">
import type { CatalogEntry } from '@/types/twin'
defineProps<{entries:CatalogEntry[];selected:string}>()
defineEmits<{choose:[entry:CatalogEntry]}>()
</script>
<style scoped>
.twin-catalog{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.twin-catalog button{display:flex;align-items:center;gap:12px;padding:16px;text-align:left;border:1px solid #e0e6ef;border-radius:16px;background:#ffffffb5;color:#25415f;cursor:pointer;min-height:78px;transition:background .15s,border-color .15s}.twin-catalog button.selected{background:#f5f3ff;border-color:#9c95e3}.twin-catalog button:focus-visible{outline:3px solid #655cf0;outline-offset:2px}.entry-icon{display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:#ecebf7;color:#7265bf;font-size:27px;flex-shrink:0}.twin-catalog strong{display:block;font-size:16px}.twin-catalog small{display:block;font-size:12px;color:#7a8798;margin-top:3px}.entry-state{font-size:11px;color:#8b7353;margin-left:auto;white-space:nowrap}.entry-state.ready{color:#6e66a8}@media(max-width:700px){.twin-catalog{grid-template-columns:1fr}.twin-catalog button{min-height:68px;padding:12px}}
</style>
