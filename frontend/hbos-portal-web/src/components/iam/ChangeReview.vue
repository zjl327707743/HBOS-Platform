<script setup lang="ts">
withDefaults(defineProps<{ open: boolean; title: string; busy?: boolean }>(), { busy: false })
defineEmits<{ cancel: [] }>()
</script>
<template><a-modal :open="open" :title="title" :width="720" :footer="null" :mask-closable="false" :closable="!busy" :keyboard="!busy" wrap-class-name="r6-review-dialog" @cancel="$emit('cancel')"><slot /></a-modal></template>
