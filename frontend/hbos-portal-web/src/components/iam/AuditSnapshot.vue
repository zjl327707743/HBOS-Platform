<script setup lang="ts">
import { computed } from 'vue'
import { auditOperationLabel } from '@/services/auditPresentation'
const props = defineProps<{ value: unknown }>()
const labels: Record<string, string> = { role_key:'角色', role:'角色记录', draft_version:'草稿版本', published_revision:'生效版本', version:'版本', enabled:'启用', allowed:'可用', suspended:'应用暂停', mode:'角色来源', source_mode:'安排来源', source_ref:'来源对象', department:'部门', company:'公司', employee:'员工档案', employee_id:'员工档案', user_id:'登录账号', subject_type:'对象类型', subject_name:'对象标识', operation_id:'功能', scope_binding:'功能范围', scope_type:'范围类型', scope_ref:'负责对象', include_descendants:'包含下级', responsibilities:'负责范围', features:'功能清单', operations:'功能结果', changes:'本次变更', scopes:'对象范围', settings:'安排设置', access_state:'访问状态', permission_mode:'权限来源', before:'变更前', after:'变更后', reason:'原因', changed:'是否变更', summary:'结果摘要', result:'结果', status:'状态', release:'发布记录', before_version:'原版本', after_version:'新版本', published_release:'生效发布记录', first_password_required:'需要本人设置密码', personal_unchanged:'个人安排保留', following_changed:'跟随者变化', count:'数量', name:'记录标识' }
const values: Record<string, string> = { staff:'普通员工', clerk:'部门考勤员', admin:'考勤管理员', FOLLOW_DEPARTMENT:'跟随部门默认', DIRECT:'个人单独设置', NONE:'不安排角色', SELF:'仅本人', DEPARTMENT:'明确部门', COMPANY:'明确公司', RESPONSIBLE_DEPARTMENTS:'明确负责的部门（不含下级）', RESPONSIBLE_COMPANIES:'明确负责的一个公司', normal:'正常', paused:'暂停', personal:'个人单独安排', department:'部门默认', success:'成功', User:'登录账号', Employee:'员工档案', Department:'部门' }
const entries = computed(() => props.value && typeof props.value === 'object' ? Object.entries(props.value as Record<string, unknown>) : [])
const scalar = computed(() => props.value === null || props.value === undefined ? '未记录' : typeof props.value === 'boolean' ? props.value ? '是' : '否' : values[String(props.value)] || auditOperationLabel(String(props.value)))
</script>
<template>
  <dl v-if="entries.length" class="r6-audit-snapshot"><div v-for="[key, item] in entries.slice(0, 100)" :key="key"><dt>{{ Array.isArray(value) ? Number(key) + 1 : labels[key] || key }}</dt><dd><AuditSnapshot :value="item" /></dd></div><p v-if="entries.length > 100">仅展示前 100 项，共 {{ entries.length }} 项。</p></dl>
  <span v-else>{{ value && typeof value === 'object' ? '未记录变更内容' : scalar }}</span>
</template>
<style scoped>.r6-audit-snapshot{margin:0}.r6-audit-snapshot>div{display:grid;grid-template-columns:minmax(90px,.35fr) minmax(0,1fr);gap:12px;border-bottom:1px solid #edf0f6;padding:8px 0}.r6-audit-snapshot dt{font-size:12px;color:#566780}.r6-audit-snapshot dd{margin:0;overflow-wrap:anywhere;font-size:13px}@media(max-width:600px){.r6-audit-snapshot>div{grid-template-columns:1fr;gap:3px}}</style>
