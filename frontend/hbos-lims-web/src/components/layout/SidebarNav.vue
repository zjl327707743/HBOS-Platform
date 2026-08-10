<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">
        <el-icon :size="18"><Platform /></el-icon>
      </div>
      <div>
        <div class="brand-name">海滨LIMS</div>
        <div class="brand-sub">Laboratory Information System</div>
      </div>
    </div>

    <nav class="nav">
      <div class="nav-group">
        <div class="nav-group-title">总览</div>
        <router-link to="/dashboard" class="nav-item" :class="{ active: isActive('/dashboard') }">
          <el-icon><Odometer /></el-icon>
          <span>工作台总览</span>
        </router-link>
      </div>

      <div class="nav-group">
        <div class="nav-group-title">业务操作</div>
        <router-link to="/samples" class="nav-item" :class="{ active: isActive('/samples') }">
          <el-icon><DocumentAdd /></el-icon>
          <span>样品登记与台账</span>
        </router-link>
        <router-link to="/tasks" class="nav-item" :class="{ active: isActive('/tasks') }">
          <el-icon><Suitcase /></el-icon>
          <span>待检任务看板</span>
          <span v-if="pendingCount > 0" class="nav-badge amber">{{ pendingCount }}</span>
        </router-link>
        <router-link to="/results" class="nav-item" :class="{ active: isActive('/results') }">
          <el-icon><EditPen /></el-icon>
          <span>检验结果录入</span>
        </router-link>
      </div>

      <div class="nav-group">
        <div class="nav-group-title">报告与标准</div>
        <router-link to="/coas" class="nav-item" :class="{ active: isActive('/coas') }">
          <el-icon><Document /></el-icon>
          <span>COA 报告管理</span>
        </router-link>
        <router-link to="/specs" class="nav-item" :class="{ active: isActive('/specs') }">
          <el-icon><Files /></el-icon>
          <span>质量标准库</span>
        </router-link>
      </div>

      <div class="nav-group">
        <div class="nav-group-title">合规</div>
        <router-link to="/audit" class="nav-item" :class="{ active: isActive('/audit') }">
          <el-icon><Search /></el-icon>
          <span>审计追踪查询</span>
        </router-link>
      </div>
    </nav>

    <div class="sidebar-foot">
      <div>HBOS · 海滨药业</div>
      <div>版本 0.1.0</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { Odometer, DocumentAdd, Suitcase, EditPen, Document, Files, Search, Platform } from '@element-plus/icons-vue'

const route = useRoute()

function isActive(path: string): boolean {
  return route.path === path || (path !== '/dashboard' && route.path.startsWith(path))
}

// TODO: 联调后从 API 读取待办角标数
const pendingCount = 0
</script>

<style scoped>
.sidebar {
  width: 232px;
  flex: 0 0 232px;
  background: linear-gradient(180deg, var(--sidebar) 0%, var(--sidebar-2) 100%);
  color: var(--sidebar-text);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: var(--radius);
  background: var(--primary);
  display: grid;
  place-items: center;
  color: #fff;
  flex: 0 0 34px;
}

.brand-name { font-size: 15px; font-weight: 700; color: #fff; }
.brand-sub { font-size: 10px; color: #8eab9f; margin-top: 2px; }

.nav {
  padding: 12px 10px;
  flex: 1;
  overflow-y: auto;
}

.nav-group { margin-bottom: 16px; }

.nav-group-title {
  font-size: 10px;
  color: #71968b;
  padding: 6px 10px 4px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  color: var(--sidebar-text);
  cursor: pointer;
  font-size: 13px;
  margin-bottom: 2px;
  transition: background 0.12s ease;
  text-decoration: none;
  width: 100%;
}

.nav-item:hover { background: rgba(255, 255, 255, 0.07); color: #fff; }
.nav-item.active { background: var(--primary); color: #fff; font-weight: 600; }
.nav-item :deep(.el-icon) { flex: 0 0 16px; opacity: 0.85; }

.nav-badge {
  margin-left: auto;
  background: var(--danger);
  color: #fff;
  font-size: 10px;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  padding: 0 5px;
}

.nav-badge.amber { background: var(--warn); }

.sidebar-foot {
  padding: 14px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 10px;
  color: #73998c;
  line-height: 1.6;
}
</style>
