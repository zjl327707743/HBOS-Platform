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

    <button class="global-search" type="button" aria-label="打开全局搜索" @click="$emit('open-command')">
      <SearchOutlined />
      <span>搜索应用、批次、样品、员工或输入命令…</span>
      <kbd>⌘ K</kbd>
    </button>

    <div class="header-actions">
      <AppSwitcher :apps="apps" />
      <NotificationCenter v-if="portalDataSource === 'mock'" />

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
            <template v-if="portalDataSource === 'frappe'">
              <a-menu-divider />
              <a-menu-item :disabled="signingOut" @click="signOut">{{ signingOut ? '正在退出…' : '退出登录' }}</a-menu-item>
            </template>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePortalStore } from '@/stores/portal'
import { portalErrorMessage } from '@/services/portalErrors'
import { QuestionCircleOutlined, SearchOutlined } from '@ant-design/icons-vue'
import AppSwitcher from '@/components/global/AppSwitcher.vue'
import NotificationCenter from '@/components/global/NotificationCenter.vue'
import type { AppManifestDTO } from '@/contracts/portal'
import { portalDataSource } from '@/services/portalProvider'

const portal = usePortalStore()
const router = useRouter()
const signingOut = ref(false)
async function signOut() {
  if (signingOut.value) return
  signingOut.value = true
  try {
    await portal.signOut()
    await router.replace({ name: 'login' })
  } catch (error) {
    message.error(portalErrorMessage(error, '退出登录未完成，请重试。'))
  } finally { signingOut.value = false }
}

defineProps<{
  avatarText: string
  avatarUrl?: string | null
  companyLogoUrl?: string | null
  groupLogoUrl?: string | null
  apps: AppManifestDTO[]
  contextLabel?: string
}>()

defineEmits<{ (e: 'open-command'): void }>()
</script>
