<script setup lang="ts">
withDefaults(defineProps<{ open: boolean; title: string; busy?: boolean; v10?: boolean }>(), { busy: false })
defineEmits<{ cancel: [] }>()
</script>
<template><a-modal :open="open" :title="title" :width="720" :footer="null" :mask-closable="false" :closable="!busy" :keyboard="!busy" :wrap-class-name="v10 ? 'r6-review-dialog v10-dialog' : 'r6-review-dialog'" @cancel="$emit('cancel')"><slot /></a-modal></template>
