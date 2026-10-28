<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { UserOutlined, InfoCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons-vue'
import AccountSecurity from '@/components/account/AccountSecurity.vue'
import AppDiagnostics from '@/components/account/AppDiagnostics.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import type { SecurityStatus } from '@/services/accountApi'
import { getMyEmployeeStatus, type MyEmployeeStatus } from '@/services/iamAccount'
import { iamMessage, hasManagementAccess } from '@/services/iamAccess'
import { usePortalStore } from '@/stores/portal'
import { businessNavigationTarget } from '@/services/businessNavigation'
const portal = usePortalStore(), security = ref<SecurityStatus | null>(null), employee = ref<MyEmployeeStatus | null>(null)
const identityLoading = ref(true), identityError = ref(''), employeeDialog = ref(false)
let generation = 0
const system = computed(() => portal.user?.id === 'Administrator')
const linked = computed(() => !system.value && employee.value?.status === 'linked')
const conflicted = computed(() => !system.value && employee.value?.status === 'conflict')
const roleTag = computed(() => system.value ? '系统管理账号' : linked.value ? '员工账号' : '工作账号')
const archiveIdentity = computed(() => {
  const currentSecurity = security.value
  const employeeRow = employee.value
  const userId = portal.user?.id
  if (system.value || !linked.value || !currentSecurity || !employeeRow || !userId) return null
  if (currentSecurity.user !== userId) return null
  const identity = currentSecurity.identity
  const accountNumber = String(employeeRow.employee_number || '').trim()
  const identityNumber = String(identity?.employee_number || '').trim()
  if (!identity || !accountNumber || !identityNumber || identityNumber !== accountNumber) return null
  return identity
})
const archiveName = computed(() => archiveIdentity.value?.display_name?.trim() || '')
const archiveDepartment = computed(() => archiveIdentity.value?.department?.trim() || employee.value?.department || '')
const archiveNamePending = computed(() => linked.value && !archiveName.value)
const personName = computed(() => archiveName.value || portal.user?.displayName || '')
const identityDescription = computed(() => {
  if (system.value) return '内置系统管理员账号'
  if (linked.value) return [archiveDepartment.value, employee.value?.position].filter(Boolean).join(' · ') || '员工档案已关联'
  return conflicted.value ? '员工档案归属待核对' : '员工档案待核对'
})
const employeeDialogTitle = computed(() => linked.value ? '我的员工资料' : conflicted.value ? '核对员工档案归属' : '核对员工档案关联')
const deskTarget = computed(() => businessNavigationTarget('/desk'))
const profileTarget = computed(() => portal.user ? businessNavigationTarget(`/desk/user/${encodeURIComponent(portal.user.id)}`) : null)
const fact = (value?: string) => system.value ? '不适用' : linked.value ? value || '待核对' : '待核对'
async function loadIdentity() {
  const run = ++generation; identityLoading.value = true; identityError.value = ''
  if (system.value || !portal.user?.id) { employee.value = null; identityLoading.value = false; return }
  try { const result = await getMyEmployeeStatus(); if (run === generation) employee.value = result }
  catch (error) { if (run === generation) { employee.value = null; identityError.value = iamMessage(error) } }
  finally { if (run === generation) identityLoading.value = false }
}
function updateSecurity(status: SecurityStatus | null) { security.value = status?.user === portal.user?.id ? status : null }
watch(() => portal.user?.id, (next, previous) => { if (next !== previous) { employee.value = null; security.value = null; void loadIdentity() } })
onMounted(loadIdentity)
onBeforeUnmount(() => { generation++; employee.value = null; security.value = null })
</script>
<template>
  <section class="r6-profile">
    <div class="r6-context-row"><a-breadcrumb><a-breadcrumb-item><RouterLink to="/hbos">工作台</RouterLink></a-breadcrumb-item><a-breadcrumb-item>个人中心</a-breadcrumb-item></a-breadcrumb><RouterLink v-if="hasManagementAccess()" to="/hbos/admin"><ArrowLeftOutlined /> 返回管理中心</RouterLink></div>
    <PageHeading eyebrow="我的 HBOS" title="个人中心" description="你的工作身份、登录方式与账号安全。" />
    <section class="r6-surface r6-identity-card profile-card">
      <div class="r6-identity-top"><span><UserOutlined /> 我的工作身份</span><StatusTag tone="brand">{{ roleTag }}</StatusTag></div>
      <div class="r6-identity-main">
        <a-avatar :size="76" class="profile-avatar" :src="portal.user?.avatarUrl || undefined" :alt="`${personName || '本人'}的头像`">{{ portal.user?.avatarText }}</a-avatar>
        <div class="r6-identity-name"><h2>{{ personName }}</h2><em v-if="archiveNamePending" class="r6-name-source">账号显示名 · 档案姓名待核对</em><p>{{ identityDescription }}</p><small>{{ security?.login_name || portal.user?.id }}</small></div>
        <div class="r6-identity-status"><StatusTag :tone="system || linked ? 'success' : 'warning'">{{ system ? '系统账号' : identityLoading ? '正在核对' : linked ? '员工档案已关联' : employee?.status === 'conflict' ? '员工归属存在冲突' : '员工档案待关联' }}</StatusTag><small>{{ system ? '员工档案不适用' : linked ? '工作身份由人事资料提供' : '核对后可查看本人考勤' }}</small></div>
      </div>
      <a-alert v-if="identityError" :message="identityError" type="warning" show-icon /><a-button v-if="identityError" @click="loadIdentity">重新核对员工档案</a-button>
      <div class="r6-identity-facts"><div><span>工号</span><strong>{{ fact(employee?.employee_number) }}</strong></div><div><span>所属部门</span><strong>{{ fact(archiveDepartment) }}</strong></div><div><span>岗位</span><strong>{{ system ? '不适用' : linked ? employee?.position || '待补充' : '待核对' }}</strong></div><a-button v-if="!system" type="text" :disabled="identityLoading || Boolean(identityError)" @click="employeeDialog = true">{{ identityLoading ? '正在核对' : linked ? '查看员工资料' : '核对关联' }}</a-button></div>
      <p v-if="system" class="r6-system-note"><InfoCircleOutlined />内置系统管理账号不关联员工档案。飞书绑定仅用于本人登录。</p>
    </section>
    <AccountSecurity :identity="portal.user?.id" @status-change="updateSecurity" />
    <details class="r6-profile-tools"><summary>更多个人与管理工具</summary><a-button v-if="security?.desk_access" :href="profileTarget || undefined">管理个人资料</a-button><a-button v-if="security?.desk_access" :href="deskTarget || undefined">进入管理后台</a-button><AppDiagnostics v-if="security?.can_admin_recover" /></details>
    <a-modal v-model:open="employeeDialog" :title="employeeDialogTitle" :footer="null" :get-container="false"><a-descriptions v-if="linked" :column="1" bordered><a-descriptions-item :label="archiveName ? '档案姓名' : '账号显示名（档案姓名待核对）'">{{ personName }}</a-descriptions-item><a-descriptions-item label="工号">{{ employee?.employee_number }}</a-descriptions-item><a-descriptions-item label="部门">{{ archiveDepartment || '待核对' }}</a-descriptions-item><a-descriptions-item label="岗位">{{ employee?.position || '待补充' }}</a-descriptions-item><a-descriptions-item label="关联状态">员工档案已关联</a-descriptions-item></a-descriptions><a-alert v-else-if="conflicted" show-icon type="warning" message="员工档案归属存在冲突" description="账号关联到冲突的员工归属，需由人事核对；未解决前本人考勤暂不可用，不能按姓名自动认领。" /><a-alert v-else show-icon type="warning" message="员工档案尚未关联" description="请向人事提供你的工号和登录账号，核对资料归属后再关联。未关联前，本人考勤暂不可用。" /><p v-if="linked && archiveName" class="aux">资料变更请联系人事核对。</p><RouterLink v-if="linked" to="/hbos/attendance/me">查看我的考勤</RouterLink><a-button @click="employeeDialog = false">关闭</a-button></a-modal>
  </section>
</template>
<style scoped>
.r6-name-source{display:block;margin:0 0 var(--hbos-space-1);color:var(--hbos-text-secondary);font-style:normal;font-size:var(--hbos-font-meta);line-height:var(--hbos-line-small);overflow-wrap:anywhere}
</style>
