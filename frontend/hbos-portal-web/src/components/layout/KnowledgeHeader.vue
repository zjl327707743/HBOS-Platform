<template>
  <header class="kb-header hbos-glass-g2">
    <button v-if="mobile" type="button" class="kb-mobile-trigger" aria-label="打开导航"
      aria-controls="kb-mobile-navigation" :aria-expanded="navigationOpen" @click="$emit('openNavigation', $event)">
      <MenuOutlined />
    </button>
    <div class="kb-header-brand">
      <PortalBrand />
      <span v-if="synthetic" class="kb-synthetic" title="未连接真实知识业务">合成测试</span>
    </div>
    <div class="kb-header-actions">
      <img class="kb-group-logo" :src="joincareMark" alt="健康元集团" width="80" height="28" />
      <AppSwitcher v-if="!mobile" :apps="portal.apps" />
      <NotificationCenter v-if="!mobile" />
      <a-button type="text" shape="circle" aria-label="知识库使用帮助" @click="helpOpen = true"><QuestionCircleOutlined /></a-button>
      <a-dropdown :trigger="['click']">
        <button type="button" class="kb-avatar" aria-label="打开个人菜单"><a-avatar :src="portal.user?.avatarUrl || undefined">{{ portal.user?.avatarText || 'HB' }}</a-avatar><span class="kb-account-name">{{ portal.user?.displayName || '个人账号' }}</span></button>
        <template #overlay><a-menu><a-menu-item @click="router.push('/hbos/profile')">我的与设置</a-menu-item><a-menu-divider /><a-menu-item :disabled="signingOut" @click="logout">退出登录</a-menu-item></a-menu></template>
      </a-dropdown>
    </div>
  </header>
  <a-modal v-model:open="helpOpen" title="知识库使用帮助" wrap-class-name="kb-scope kb-dialog" :footer="null">
    <p>在“问答与搜索”提问或搜索资料，点开来源核对依据。在“资料目录”按标题、文号或部门查找；点击星标保存到本人的收藏。</p>
    <p>“我的记录”可恢复已经保存且当前仍获授权的问答。“连接个人助手”提供配置、中文提示词与真实连接检查。原件下载以当前资料的授权为准。</p>
  </a-modal>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { MenuOutlined, QuestionCircleOutlined } from '@ant-design/icons-vue'
import AppSwitcher from '@/components/global/AppSwitcher.vue'
import NotificationCenter from '@/components/global/NotificationCenter.vue'
import { usePortalStore } from '@/stores/portal'
import { logoutFrappeSession } from '@/services/frappeClient'
import PortalBrand from '@/components/portal/PortalBrand.vue'
import joincareMark from '@/assets/portal-v10/joincare-logo.png'

defineProps<{ mobile: boolean; navigationOpen: boolean }>()
defineEmits<{ openNavigation: [event: MouseEvent] }>()
const synthetic = import.meta.env.MODE === 'knowledge-preview'
const router = useRouter(), portal = usePortalStore(), helpOpen = ref(false), signingOut = ref(false)
async function logout() {
  if (signingOut.value) return
  signingOut.value = true
  try {
    if (portal.dataSource === 'frappe') await logoutFrappeSession()
    portal.clearSession()
    await router.replace({ path: '/hbos/login', query: { status: 'signed_out' } })
  } catch (e) { message.error(e instanceof Error ? e.message : '退出失败，请稍后重试。') }
  finally { signingOut.value = false }
}
</script>
