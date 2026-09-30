<template>
  <header class="hbos-header glass-surface">
    <button class="brand-wrap" type="button" aria-label="返回 HBOS 首页" @click="$router.push('/hbos')">
      <div class="brand-mark" :class="{ 'brand-mark-image': companyLogoUrl }">
        <img v-if="companyLogoUrl" :src="companyLogoUrl" alt="" class="company-logo-image" />
        <span v-else>H</span>
      </div>
      <div class="brand-copy">
        <div class="brand-name">HBOS</div>
        <div class="brand-caption">{{ contextLabel || '海滨智能运营工作台' }}</div>
      </div>
    </button>

    <button class="global-search" type="button" aria-label="打开全局搜索" @click="$emit('open-command')">
      <SearchOutlined />
      <span>搜索应用与业务事项…</span>
      <kbd>⌘ K</kbd>
    </button>

    <div class="header-actions">
      <AppSwitcher :apps="apps" />
      <NotificationCenter />

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

      <a-dropdown>
        <button type="button" class="avatar-button" aria-label="打开个人菜单">
          <a-avatar class="user-avatar" :src="avatarUrl || undefined">
            <template v-if="!avatarUrl">{{ avatarText }}</template>
          </a-avatar>
        </button>
        <template #overlay>
          <a-menu>
            <a-menu-item @click="$router.push('/hbos/profile')">个人与设置</a-menu-item>
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { QuestionCircleOutlined, SearchOutlined } from '@ant-design/icons-vue'
import AppSwitcher from '@/components/global/AppSwitcher.vue'
import NotificationCenter from '@/components/global/NotificationCenter.vue'
import type { AppManifestDTO } from '@/contracts/portal'
import { logoutFrappeSession } from '@/services/frappeClient'
import { usePortalStore } from '@/stores/portal'

const router = useRouter()
const portal = usePortalStore()
const signingOut = ref(false)
const helpOpen = ref(false)

async function handleLogout() {
  if (signingOut.value) return
  signingOut.value = true
  try {
    if (portal.dataSource === 'frappe') await logoutFrappeSession()
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
  apps: AppManifestDTO[]
  contextLabel?: string
}>()

defineEmits<{ (e: 'open-command'): void }>()
</script>
