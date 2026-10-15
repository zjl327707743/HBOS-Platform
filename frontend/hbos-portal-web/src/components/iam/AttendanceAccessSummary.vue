<script setup lang="ts">
import type { WorkApp } from '@/types/iam'
defineProps<{ app: WorkApp }>()
</script>
<template><section class="attendance-access"><strong>本人考勤范围</strong><p>{{ app.summary }}</p><p class="aux">这里只显示关联状态、可用工作和设置来源。本人真实考勤请使用自己的会话进入“我的考勤”。</p><p v-if="app.operations.some(row => row.enabled)">同事的打卡时间、考勤结果和数量不会在配置页返回。</p></section></template>
<style scoped>.attendance-access{padding:var(--hbos-space-4);background:var(--hbos-surface-subtle,#f4f8f6);border-radius:var(--hbos-radius-md);font-size:16px}.attendance-access p{margin:var(--hbos-space-2) 0 0;line-height:1.6}.attendance-access .aux{font-size:14px;color:var(--hbos-text-secondary)}</style>
