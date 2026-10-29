<script setup lang="ts">
import type { WorkApp } from '@/types/iam'
defineProps<{ app: WorkApp }>()
</script>
<template><section class="attendance-access"><template v-if="app.department_default"><strong>所属部门默认权限</strong><p>【{{app.department_default.name}}】的默认权限：{{app.department_default.suspended ? '已暂停' : app.department_default.enabled ? '可查看本人考勤' : '未默认开通本人考勤'}}。</p><RouterLink v-if="app.department_default.can_open" :to="{path:'/hbos/admin/departments',query:{department:app.department_default.id,tab:'apps',app:app.app_id}}">查看部门默认</RouterLink><p v-else class="aux">查看部门默认详情需要该部门的读取权限。</p></template><p v-else class="aux">部门来源尚未确认，请读取最新设置。</p><p class="aux">配置页只核对权限，不读取员工的考勤记录。</p></section></template>
<style scoped>.attendance-access{padding:var(--hbos-space-4);background:var(--hbos-surface-subtle,#f4f8f6);border-radius:var(--hbos-radius-md);font-size:16px}.attendance-access p{margin:var(--hbos-space-2) 0 0;line-height:1.6}.attendance-access .aux{font-size:14px;color:var(--hbos-text-secondary)}</style>
