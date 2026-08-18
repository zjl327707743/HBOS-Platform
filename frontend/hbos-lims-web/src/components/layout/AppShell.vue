<template>
  <div class="app" :class="{ 'sidebar-collapsed': collapsed }">
    <SidebarNav :collapsed="collapsed" @toggle="toggleSidebar" />
    <div class="main">
      <TopBar />
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SidebarNav from './SidebarNav.vue'
import TopBar from './TopBar.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// 侧边栏折叠状态，持久化到 localStorage
const STORAGE_KEY = 'hbos_lims_sidebar_collapsed'
const collapsed = ref(false)

function toggleSidebar() {
  collapsed.value = !collapsed.value
  try {
    localStorage.setItem(STORAGE_KEY, collapsed.value ? '1' : '0')
  } catch {
    // localStorage 不可用时忽略持久化
  }
}

onMounted(async () => {
  try {
    collapsed.value = localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    // 忽略
  }
  // 未登录跳转已由路由守卫处理（跳转到 Frappe Desk 登录页）
  if (!auth.initialized) {
    await auth.checkSession()
  }
})
</script>

<style scoped>
.app {
  display: flex;
  min-height: 100vh;
  transition: all 0.2s ease;
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.2s ease;
}

.content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}
</style>
