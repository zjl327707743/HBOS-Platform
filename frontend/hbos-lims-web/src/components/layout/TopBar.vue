<template>
  <header class="topbar">
    <div class="crumb">
      <span class="muted">HBOS LIMS</span>
      <span class="sep">/</span>
      <span class="current">{{ route.meta.title || '' }}</span>
    </div>

    <div class="topbar-right">
      <a-tooltip title="刷新数据">
        <button class="icon-btn" @click="$emit('refresh')">
          <ReloadOutlined />
        </button>
      </a-tooltip>

      <a-dropdown placement="bottomRight" trigger="click">
        <div class="user" role="button" tabindex="0">
          <div class="avatar">{{ avatarText }}</div>
          <div class="user-meta">
            <div class="user-name">{{ userDisplayName }}</div>
            <div class="user-role">{{ roleLabel }}</div>
          </div>
        </div>
        <template #overlay>
          <a-menu>
            <a-menu-item key="desktop" @click="goDesktop">
              <template #icon><DesktopOutlined /></template>
              返回桌面
            </a-menu-item>
            <a-menu-item key="refresh" @click="$emit('refresh')">
              <template #icon><ReloadOutlined /></template>
              刷新
            </a-menu-item>
            <a-menu-divider />
            <a-menu-item key="logout" danger @click="doLogout">
              <template #icon><LogoutOutlined /></template>
              退出登录
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ReloadOutlined, DesktopOutlined, LogoutOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'
import { getRoleLabel } from '@/features/auth/roleLabel'

defineEmits<{ refresh: [] }>()

const route = useRoute()
const auth = useAuthStore()

const userDisplayName = computed(() => auth.user?.full_name || auth.user?.name || '未登录')
const avatarText = computed(() => {
  const name = userDisplayName.value
  return name && name !== '未登录' ? name.substring(0, 1) : '海'
})
const roleLabel = computed(() => getRoleLabel(auth.user?.roles || [], auth.isLoggedIn))

// 返回 Frappe Desk 桌面
function goDesktop() {
  window.location.href = `${window.location.origin}/desk`
}

async function doLogout() {
  await auth.logout()
  message.success('已退出登录')
  window.location.href = `${window.location.origin}/login`
}
</script>

<style scoped>
.topbar {
  height: 58px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 22px;
  position: sticky;
  top: 0;
  z-index: 20;
}

.crumb {
  font-size: 13px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 8px;
}

.crumb .current {
  color: var(--ink);
  font-weight: 600;
}

.crumb .sep { color: var(--line); }

.topbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-btn {
  background: none;
  border: 1px solid var(--line);
  border-radius: 6px;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  cursor: pointer;
  color: var(--muted);
  transition: all 0.12s ease;
}

.icon-btn:hover { background: var(--surface-2); color: var(--primary); border-color: var(--primary); }

.user { display: flex; align-items: center; gap: 10px; cursor: pointer; padding: 6px 8px; border-radius: 8px; transition: background 0.12s ease; }
.user:hover { background: var(--surface-2); }

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 600;
}

.user-meta { line-height: 1.3; }
.user-name { font-size: 13px; font-weight: 600; color: var(--ink); }
.user-role { font-size: 11px; color: var(--muted); }
</style>
