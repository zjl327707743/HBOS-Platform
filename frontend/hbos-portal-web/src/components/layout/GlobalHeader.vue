<template>
  <header class="hbos-header glass-surface">
    <button class="brand-wrap" type="button" aria-label="返回 HBOS 首页" @click="$router.push('/hbos')">
      <div class="brand-mark" :class="{ 'brand-mark-image': companyLogoUrl }">
        <img v-if="companyLogoUrl" :src="companyLogoUrl" alt="" class="company-logo-image" />
        <span v-else>H</span>
      </div>
      <div class="brand-copy">
        <div class="brand-name">{{ contextLabel === 'LIMS' ? '海滨实验室' : 'HBOS' }}</div>
        <div class="brand-caption">{{ contextLabel === 'LIMS' ? 'HBOS / LIMS' : (contextLabel || '海滨智能运营工作台') }}</div>
      </div>
    </button>

    <nav v-if="managementExperience" class="r6-global-nav" aria-label="工作台导航" :inert="sessionBlocked || undefined">
      <RouterLink to="/hbos" :class="{ active: route.path === '/hbos' }"><HomeOutlined />首页</RouterLink>
      <RouterLink to="/hbos/work"><UnorderedListOutlined />我的工作</RouterLink>
      <RouterLink to="/hbos/apps"><AppstoreOutlined />应用中心</RouterLink>
      <RouterLink v-if="hasManagementAccess()" to="/hbos/admin" :class="{ active: route.path.startsWith('/hbos/admin') }"><SafetyCertificateOutlined />管理中心</RouterLink>
    </nav>
    <button v-else class="global-search" type="button" aria-label="打开全局搜索" :disabled="sessionBlocked" @click="$emit('open-command')">
      <SearchOutlined />
      <span>搜索应用与业务事项…</span>
      <kbd>⌘ K</kbd>
    </button>

    <div class="header-actions">
      <a-dropdown v-if="managementExperience" :trigger="['click']" class="r6-mobile-global">
        <a-button aria-label="打开工作台导航"><MenuOutlined /></a-button>
        <template #overlay><a-menu><a-menu-item @click="router.push('/hbos')">首页</a-menu-item><a-menu-item @click="router.push('/hbos/work')">我的工作</a-menu-item><a-menu-item @click="router.push('/hbos/apps')">应用中心</a-menu-item><a-menu-item v-if="hasManagementAccess()" @click="router.push('/hbos/admin')">管理中心</a-menu-item></a-menu></template>
      </a-dropdown>
      <a-button v-if="managementExperience" class="r6-motion-toggle" type="text" :aria-pressed="motionPaused" :aria-label="motionPaused ? '恢复背景动效' : '暂停背景动效'" @click="$emit('toggle-motion')"><PlayCircleOutlined v-if="motionPaused" /><PauseCircleOutlined v-else /></a-button>
      <div class="session-app-controls" :class="{ 'controls-hidden': sessionBlocked }" :inert="sessionBlocked || undefined"><AppSwitcher :apps="apps" /><NotificationCenter v-if="portalDataSource === 'mock'" /></div>

      <div v-if="groupLogoUrl" class="group-brand" aria-label="健康元集团标识">
        <span class="header-divider" aria-hidden="true"></span>
        <img :src="groupLogoUrl" alt="健康元集团标识" class="group-logo-image" />
      </div>

      <a-tooltip title="帮助">
        <a-button
          class="top-icon-button"
          type="text"
          shape="circle"
          aria-label="打开帮助"
          @click="helpOpen = true"
        >
          <QuestionCircleOutlined />
        </a-button>
      </a-tooltip>

      <div class="current-identity" aria-label="当前登录人"><strong>{{ currentIdentity?.display_name || (portalSession.phase === 'unconfirmed' ? '正在核验账号' : portal.user?.displayName) || 'HBOS' }}</strong><span>{{ identityCaption }}</span></div>
      <a-dropdown :trigger="['click']">
        <button type="button" class="avatar-button" aria-label="打开个人菜单">
          <a-avatar class="user-avatar" :src="avatarUrl || undefined">
            {{ avatarText }}
          </a-avatar>
        </button>
        <template #overlay>
          <a-menu>
            <a-menu-item disabled>{{ currentIdentity?.login_name || '当前登录账号' }}</a-menu-item>
            <a-menu-item v-if="currentIdentity?.department" disabled>{{ currentIdentity.department }}</a-menu-item>
            <a-menu-item @click="$router.push('/hbos/profile')">个人中心</a-menu-item>
            <a-menu-divider />
            <a-menu-item :disabled="signingOut" @click="handleLogout">退出登录</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </header>
  <a-modal v-model:open="helpOpen" title="工作台使用引导" :footer="null">
    <p>在应用中心进入本人获准使用的应用，在“我的工作”查看真实待办。</p>
    <p>知识助理提供授权资料检索与来源证据；设备与工艺提供模型查看及设备上下文检索。现场数据、生成式回答和消息通知尚未接入。</p>
    <p>在“我的”页面验证本人身份后，可绑定飞书、设置或修改密码。首次飞书登录请选择绑定已有账号或新建普通账号。</p>
    <a-button @click="helpOpen = false; router.push('/hbos/profile')">进入账号与安全</a-button>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { QuestionCircleOutlined, SearchOutlined, HomeOutlined, UnorderedListOutlined, AppstoreOutlined, SafetyCertificateOutlined, MenuOutlined, PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons-vue'
import AppSwitcher from '@/components/global/AppSwitcher.vue'
import NotificationCenter from '@/components/global/NotificationCenter.vue'
import type { AppManifestDTO } from '@/contracts/portal'
import { portalSession, signOutPortalSession } from '@/services/portalSessionCoordinator'
import { hasManagementAccess } from '@/services/iamAccess'
import { portalDataSource } from '@/services/portalProvider'
import { usePortalStore } from '@/stores/portal'

const router = useRouter()
const route = useRoute()
const portal = usePortalStore()
const signingOut = ref(false)
const helpOpen = ref(false)
const currentIdentity = computed(() => ['ready','checking','password_required'].includes(portalSession.phase) ? portalSession.security?.identity : null)
const identityCaption = computed(() => !currentIdentity.value ? '身份待确认' : currentIdentity.value.employee_number ? `工号 ${currentIdentity.value.employee_number}` : portalSession.security?.administrator || hasManagementAccess() ? '管理账号' : '工号待关联')

async function handleLogout() {
  if (signingOut.value) return
  signingOut.value = true
  try {
    if (portal.dataSource === 'frappe') await signOutPortalSession()
    portal.clearSession()
    await router.replace({ path: '/hbos/login', query: { status: 'signed_out' } })
  } catch (error) {
    message.error(error instanceof Error ? error.message : '退出失败，请稍后重试。')
  } finally {
    signingOut.value = false
  }
}

defineProps<{
  avatarText: string
  avatarUrl?: string | null
  companyLogoUrl?: string | null
  groupLogoUrl?: string | null
  apps: AppManifestDTO[]
  contextLabel?: string
  sessionBlocked?: boolean
  managementExperience?: boolean
  motionPaused?: boolean
}>()

defineEmits<{ (e: 'open-command'): void; (e: 'toggle-motion'): void }>()
</script>

<style scoped>.current-identity{display:grid;gap:2px;text-align:right;font-size:14px}.current-identity strong{font-size:16px}.current-identity span{color:var(--hbos-text-secondary)}@media(max-width:700px){.current-identity{max-width:120px}.current-identity strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}</style>
<style scoped>.session-app-controls{display:flex;align-items:center;gap:12px}.controls-hidden{visibility:hidden;pointer-events:none}</style>
