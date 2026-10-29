<template>
  <header class="kb-header hbos-glass-g2">
    <button class="kb-brand" aria-label="返回 HBOS 首页" @click="router.push('/hbos')">
      <span class="kb-brand-mark"><ReadOutlined /></span>
      <span><strong>HBOS</strong><small>知识工作台</small></span>
    </button>
    <nav class="kb-header-context" aria-label="面包屑"><RouterLink to="/hbos">工作台</RouterLink><span>/</span><strong>{{ maintenance ? '知识维护' : '知识库' }}</strong></nav>
    <div class="kb-header-actions">
      <AppSwitcher :apps="portal.apps" />
      <NotificationCenter />
      <a-button type="text" shape="circle" aria-label="知识库使用帮助" @click="helpOpen = true"><QuestionCircleOutlined /></a-button>
      <a-dropdown :trigger="['click']">
        <button class="kb-avatar" aria-label="打开个人菜单"><a-avatar :src="portal.user?.avatarUrl || undefined">{{ portal.user?.avatarText || 'HB' }}</a-avatar></button>
        <template #overlay><a-menu><a-menu-item @click="router.push('/hbos/profile')">我的与设置</a-menu-item><a-menu-divider /><a-menu-item :disabled="signingOut" @click="logout">退出登录</a-menu-item></a-menu></template>
      </a-dropdown>
    </div>
  </header>
  <a-modal v-model:open="helpOpen" title="知识库使用帮助" :footer="null">
    <p>在“查知识”提问或搜索资料，点开来源核对依据。在“资料目录”按标题、文号或部门查找；点击星标保存到本人的收藏。</p>
    <p>“我的记录”可恢复已经保存且当前仍获授权的问答。“连接个人助手”提供配置、中文提示词与真实连接检查。原件下载待部门权限上线。</p>
  </a-modal>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReadOutlined, QuestionCircleOutlined } from '@ant-design/icons-vue'
import AppSwitcher from '@/components/global/AppSwitcher.vue'
import NotificationCenter from '@/components/global/NotificationCenter.vue'
import { usePortalStore } from '@/stores/portal'
import { logoutFrappeSession } from '@/services/frappeClient'
defineProps<{ maintenance: boolean }>()
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
