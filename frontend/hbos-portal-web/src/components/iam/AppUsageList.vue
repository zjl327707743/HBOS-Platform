<script setup lang="ts">
import { ref, watch } from 'vue'
import { getWorkSummary } from '@/services/iamWork'
import { iamMessage } from '@/services/iamAccess'
import type { WorkApp } from '@/types/iam'
const props = withDefaults(defineProps<{ employeeId: string; canEdit?: boolean; configurationAppId?:string }>(), { canEdit: true })
const emit = defineEmits<{ modify: [appId: string] }>()
const apps = ref<WorkApp[]>([]), loading = ref(true), error = ref('')
let run = 0
async function load() { const current = ++run; loading.value = true; error.value = ''; try { const data = await getWorkSummary(props.employeeId,props.configurationAppId); if (run === current) apps.value = data.apps } catch (e) { if (run === current) { apps.value = []; error.value = iamMessage(e) } } finally { if (run === current) loading.value = false } }
watch(() => props.employeeId, load, { immediate: true }); defineExpose({ reload: load })
</script>
<template><div class="app-usage"><a-skeleton v-if="loading" active /><a-alert v-else-if="error" :message="error" type="warning" /><a-empty v-else-if="!apps.length" description="暂无已注册应用" /><article v-for="app in apps" :key="app.app_id" class="usage-row"><div><h3>{{ app.title }} <a-tag>{{ app.integrated ? app.status : '尚未接入此管理功能' }}</a-tag></h3><p>{{ app.integrated ? app.summary : '原有业务入口保持现有授权，暂不能在此调整。' }}</p><small v-if="app.synthetic">隔离合成规则验证，非库存业务接入</small><small v-if="app.source_text">{{ app.source_text }}</small></div><a-button v-if="canEdit && app.integrated" @click="emit('modify', app.app_id)">查看与修改</a-button></article><a-button v-if="error" @click="load">重试读取</a-button></div></template>
<style scoped>.app-usage{display:grid;gap:var(--hbos-space-4);font-size:16px}.usage-row{display:flex;align-items:center;justify-content:space-between;gap:var(--hbos-space-4);padding:var(--hbos-space-4);border:1px solid var(--hbos-border-subtle,#dde5e8);border-radius:var(--hbos-radius-md)}.usage-row>div{min-width:0}.usage-row h3{font-size:16px;margin:0 0 8px;overflow-wrap:anywhere}.usage-row p{margin:0;line-height:1.6}.usage-row small{font-size:14px;color:var(--hbos-text-secondary)}@media(max-width:600px){.usage-row{align-items:flex-start;flex-direction:column}}</style>
