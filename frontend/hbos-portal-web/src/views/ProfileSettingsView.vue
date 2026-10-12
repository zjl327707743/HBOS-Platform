<template>
  <section class="product-page">
    <div class="page-heading">
      <div>
        <span class="page-kicker">个人设置</span>
        <h1>我的与设置</h1>
        <p>管理账号安全与个人工作台体验。</p>
      </div>
    </div>

    <div class="profile-grid">
      <section class="profile-card glass-surface">
        <div class="profile-hero">
          <a-avatar :size="72" class="profile-avatar" :src="portal.user?.avatarUrl || undefined" :alt="`${portal.user?.displayName || '本人'}的头像`">{{ portal.user?.avatarText }}</a-avatar>
          <div>
            <h2>{{ portal.user?.displayName }}</h2>
            <p>{{ portal.user?.id }}</p>
            <a-tag color="blue">{{ roleTag }}</a-tag>
            <a-tag v-if="portal.user?.department">{{ portal.user?.department }}</a-tag>
          </div>
        </div>
        <a-divider />
        <a-descriptions :column="1" size="small">
          <a-descriptions-item label="默认入口">HBOS Workspace</a-descriptions-item>
          <a-descriptions-item label="已启用的登录方式"><span>{{ loginMethods.enabled }}</span><p class="login-method-detail">{{ loginMethods.detail }}</p></a-descriptions-item>
          <a-descriptions-item label="可用应用">{{ portal.apps.length }}</a-descriptions-item>
        </a-descriptions>
        <a-button v-if="deskAccess" block :href="profileTarget || undefined">管理个人资料</a-button>
      </section>

      <section class="settings-stack">
        <AccountSecurity @status-change="updateSecurity" />
        <AppDiagnostics v-if="canDiagnose" />
        <details class="setting-card glass-surface">
          <summary>外观与工作偏好（说明）</summary>
          <p>当前使用已批准的默认体验：明亮主题、舒适表格密度。动效遵循系统减少动态效果设置。</p>
          <p>主题、密度与工作偏好的个人保存尚未开放。</p>
        </details>

        <div v-if="deskAccess" class="setting-card glass-surface management-entry">
          <div class="setting-head"><div><h3>Management Console</h3><p>仅管理员 / 实施人员 / 高级业务管理员可进入</p></div><SafetyCertificateOutlined /></div>
          <a-alert message="进入后将切换到 Frappe Desk 管理后台界面。" type="info" show-icon />
          <a-button style="margin-top: 14px" :href="deskTarget || undefined">进入管理后台 <ArrowRightOutlined /></a-button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import AccountSecurity from '@/components/account/AccountSecurity.vue'
import AppDiagnostics from '@/components/account/AppDiagnostics.vue'
import type { SecurityStatus } from '@/services/accountApi'
import { describeLoginMethods } from '@/services/accountStatus'
import {
  ArrowRightOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import { businessNavigationTarget } from '@/services/businessNavigation'

const portal = usePortalStore()
const security = ref<SecurityStatus | null>(null)
// 角色标签须反映真实权限：Administrator / System Manager 显示「管理员」。
const roleTag = computed(() => {
  if (security.value?.administrator || security.value?.can_admin_recover) return '管理员'
  return portal.user?.roleLabel || 'HBOS User'
})
const loginMethods = computed(() => describeLoginMethods(security.value))
const deskAccess = ref(false)
const canDiagnose = ref(false)
// Desk 由 Frappe 处理；原生链接触发整页导航，不交给 Portal 的 Vue Router。
const deskTarget = computed(() => businessNavigationTarget('/desk'))
const profileTarget = computed(() => portal.user
  ? businessNavigationTarget(`/desk/user/${encodeURIComponent(portal.user.id)}`)
  : null)
function updateSecurity(status: SecurityStatus | null) {
  security.value = status?.user === portal.user?.id ? status : null
  deskAccess.value = Boolean(security.value?.desk_access)
  canDiagnose.value = Boolean(security.value?.can_admin_recover)
}
</script>

<style scoped>.login-method-detail{margin:var(--hbos-space-2) 0 0;color:var(--hbos-text-secondary)}summary{cursor:pointer;font-weight:var(--hbos-weight-medium)}</style>
