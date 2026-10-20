<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMyEmployeeStatus, type MyEmployeeStatus } from '@/services/iamAccount'
import { iamMessage } from '@/services/iamAccess'
const status = ref<MyEmployeeStatus | null>(null), error = ref(''), loading = ref(true)
async function load() { loading.value = true; error.value = ''; try { status.value = await getMyEmployeeStatus() } catch (e) { status.value = null; error.value = iamMessage(e) } finally { loading.value = false } }
onMounted(load)
</script>
<template><section class="setting-card glass-surface identity-status"><h3>员工身份关联</h3><a-skeleton v-if="loading" active /><a-alert v-else-if="error" :message="error" type="warning" /><template v-else-if="status"><p>{{ status.status === 'linked' ? '已关联本人员工档案' : status.status === 'conflict' ? '员工归属存在冲突，请联系负责人核验' : '尚未关联员工档案，暂不能查看本人考勤' }}</p><a-descriptions v-if="status.status === 'linked'" :column="1"><a-descriptions-item label="工号">{{ status.employee_number }}</a-descriptions-item><a-descriptions-item label="部门">{{ status.department }}</a-descriptions-item></a-descriptions><RouterLink v-if="status.status === 'linked'" to="/hbos/attendance/me">查看我的考勤</RouterLink></template><a-button v-if="error" @click="load">重试</a-button></section></template>
<style scoped>.identity-status{padding:var(--hbos-space-6);font-size:16px}.identity-status h3{margin-top:0}.identity-status p{line-height:1.6}</style>
