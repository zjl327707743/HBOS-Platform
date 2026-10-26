<script setup lang="ts">
/**
 * 行内文本渲染 —— `[{ text, bold? }]` → 文本 + `<strong>`。
 *
 * 为什么单独一个组件：报告里「加粗」只出现在建议的优先级标记上，但同一个
 * 片段数组要在段落、列表项、建议行三处渲染。抽出来避免三处各写一遍 v-for。
 *
 * **不用 v-html**：模型输出里可能夹着原样 HTML。这里只渲染 `text` 字段，
 * 标签只会显示成文字，不会被浏览器执行。
 */
import type { Inline } from '@/services/reportMarkdown'

defineProps<{ spans: Inline[] }>()
</script>

<template>
  <template v-for="(s, i) in spans" :key="i">
    <strong v-if="s.bold">{{ s.text }}</strong>
    <template v-else>{{ s.text }}</template>
  </template>
</template>
