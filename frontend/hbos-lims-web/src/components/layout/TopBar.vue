<template>
  <header class="topbar">
    <div class="crumb">
      <span class="muted">HBOS LIMS</span>
      <el-icon class="sep"><ArrowRight /></el-icon>
      <span class="current">{{ route.meta.title || '' }}</span>
    </div>

    <div class="topbar-right">
      <el-tooltip content="刷新数据" placement="bottom">
        <button class="icon-btn" @click="$emit('refresh')">
          <el-icon><Refresh /></el-icon>
        </button>
      </el-tooltip>

      <div class="user">
        <div class="avatar">海</div>
        <div class="user-meta">
          <div class="user-name">{{ userDisplayName }}</div>
          <div class="user-role">{{ roleLabel }}</div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowRight, Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

defineEmits<{ refresh: [] }>()

const route = useRoute()
const auth = useAuthStore()

const userDisplayName = computed(() => auth.user?.full_name || auth.user?.name || '未登录')
const roleLabel = computed(() => {
  const roles = auth.user?.roles || []
  if (roles.includes('HBOS LIMS Manager')) return 'LIMS 经理'
  if (roles.includes('HBOS LIMS Reviewer')) return 'LIMS 复核人'
  if (roles.includes('HBOS LIMS Analyst')) return 'LIMS 检验员'
  return '未认证'
})
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
  gap: 6px;
}

.crumb .current {
  color: var(--ink);
  font-weight: 600;
}

.crumb .sep { font-size: 12px; }

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

.user { display: flex; align-items: center; gap: 10px; }

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
