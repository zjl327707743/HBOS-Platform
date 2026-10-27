<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { UserOutlined, InfoCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons-vue'
import AccountSecurity from '@/components/account/AccountSecurity.vue'
import AppDiagnostics from '@/components/account/AppDiagnostics.vue'
import PageHeading from '@/components/iam/PageHeading.vue'
import StatusTag from '@/components/iam/StatusTag.vue'
import type { SecurityStatus } from '@/services/accountApi'
import { describeLoginMethods } from '@/services/accountStatus'
import { getMyEmployeeStatus, type MyEmployeeStatus } from '@/services/iamAccount'
import { iamMessage, hasManagementAccess } from '@/services/iamAccess'
import { usePortalStore } from '@/stores/portal'
import { businessNavigationTarget } from '@/services/businessNavigation'
const portal = usePortalStore(), security = ref<SecurityStatus | null>(null), employee = ref<MyEmployeeStatus | null>(null)
const identityLoading = ref(true), identityError = ref(''), employeeDialog = ref(false)
let generation = 0
const system = computed(() => portal.user?.id === 'Administrator')
const linked = computed(() => !system.value && employee.value?.status === 'linked')
const roleTag = computed(() => system.value ? '系统管理账号' : portal.user?.roleLabel || '工作账号')
const loginMethods = computed(() => describeLoginMethods(security.value))
const deskTarget = computed(() => businessNavigationTarget('/desk'))
const profileTarget = computed(() => portal.user ? businessNavigationTarget(`/desk/user/${encodeURIComponent(portal.user.id)}`) : null)
const fact = (value?: string) => system.value ? '不适用' : linked.value ? value || '待核对' : '待核对'
async function loadIdentity() {
  const run = ++generation; identityLoading.value = true; identityError.value = ''
  if (system.value) { employee.value = null; identityLoading.value = false; return }
  try { const result = await getMyEmployeeStatus(); if (run === generation) employee.value = result }
  catch (error) { if (run === generation) { employee.value = null; identityError.value = iamMessage(error) } }
  finally { if (run === generation) identityLoading.value = false }
}
function updateSecurity(status: SecurityStatus | null) { security.value = status?.user === portal.user?.id ? status : null }
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
        <a-avatar :size="76" class="profile-avatar" :src="portal.user?.avatarUrl || undefined" :alt="`${portal.user?.displayName || '本人'}的头像`">{{ portal.user?.avatarText }}</a-avatar>
        <div class="r6-identity-name"><h2>{{ portal.user?.displayName }}</h2><p>{{ system ? '内置系统管理员账号' : linked ? employee?.department : '员工档案待核对' }}</p><small>{{ security?.login_name || portal.user?.id }}</small></div>
        <div class="r6-identity-status"><StatusTag :tone="system || linked ? 'success' : 'warning'">{{ system ? '系统账号' : identityLoading ? '正在核对' : linked ? '员工档案已关联' : employee?.status === 'conflict' ? '员工归属存在冲突' : '员工档案待关联' }}</StatusTag><small>{{ system ? '员工档案不适用' : linked ? '工作身份由人事资料提供' : '核对后可查看本人考勤' }}</small></div>
      </div>
      <a-alert v-if="identityError" :message="identityError" type="warning" show-icon /><a-button v-if="identityError" @click="loadIdentity">重新核对员工档案</a-button>
      <div class="r6-identity-facts"><div><span>工号</span><strong>{{ fact(employee?.employee_number) }}</strong></div><div><span>所属部门</span><strong>{{ fact(employee?.department) }}</strong></div><div><span>岗位</span><strong>{{ system ? '不适用' : linked ? employee?.position || '待补充' : '待核对' }}</strong></div><a-button v-if="!system" type="text" @click="employeeDialog = true">{{ linked ? '查看员工资料' : '核对关联' }}</a-button></div>
      <p v-if="system" class="r6-system-note"><InfoCircleOutlined />内置系统管理账号不关联员工档案。飞书绑定仅用于本人登录。</p>
      <p class="r6-system-note">已启用的登录方式：{{ loginMethods.enabled }} · {{ loginMethods.detail }}</p>
    </section>
    <AccountSecurity @status-change="updateSecurity" />
    <details class="r6-profile-tools"><summary>更多个人与管理工具</summary><p>当前使用明亮主题、舒适表格密度。背景动效可在顶栏暂停，也遵循系统减少动态效果设置。</p><a-button v-if="security?.desk_access" :href="profileTarget || undefined">管理个人资料</a-button><a-button v-if="security?.desk_access" :href="deskTarget || undefined">进入管理后台</a-button><AppDiagnostics v-if="security?.can_admin_recover" /></details>
    <a-modal v-model:open="employeeDialog" :title="linked ? '我的员工资料' : '核对员工档案关联'" :footer="null"><a-descriptions v-if="linked" :column="1" bordered><a-descriptions-item label="姓名">{{ portal.user?.displayName }}</a-descriptions-item><a-descriptions-item label="工号">{{ employee?.employee_number }}</a-descriptions-item><a-descriptions-item label="部门">{{ employee?.department }}</a-descriptions-item><a-descriptions-item label="岗位">{{ employee?.position || '待补充' }}</a-descriptions-item></a-descriptions><a-alert v-else show-icon type="warning" message="请联系人事核对工号与账号归属" description="员工档案需要明确关联，不能按姓名自动认领。" /><p class="aux">资料变更请联系人事核对，账号与员工档案保持明确关联。</p><RouterLink v-if="linked" to="/hbos/attendance/me">查看我的考勤</RouterLink><a-button @click="employeeDialog = false">关闭</a-button></a-modal>
  </section>
</template>
