<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand">
      <div class="brand-mark">
        <img src="/joincare-mark.png" alt="健康元" class="brand-logo" />
      </div>
      <div v-if="!collapsed">
        <div class="brand-name">海滨LIMS</div>
        <div class="brand-sub">Laboratory Information System</div>
      </div>
    </div>

    <nav class="nav">
      <div class="nav-group">
        <div v-if="!collapsed" class="nav-group-title">总览</div>
        <router-link to="/dashboard" class="nav-item" :class="{ active: isActive('/dashboard') }" :title="collapsed ? '工作台总览' : ''">
          <DashboardOutlined />
          <span v-if="!collapsed">工作台总览</span>
        </router-link>
      </div>

      <div class="nav-group">
        <div v-if="!collapsed" class="nav-group-title">业务操作</div>
        <router-link to="/samples" class="nav-item" :class="{ active: isActive('/samples') }" :title="collapsed ? '样品登记与台账' : ''">
          <FileAddOutlined />
          <span v-if="!collapsed">样品登记与台账</span>
        </router-link>
        <router-link to="/tasks" class="nav-item" :class="{ active: isActive('/tasks') }" :title="collapsed ? '待检任务看板' : ''">
          <CarryOutOutlined />
          <span v-if="!collapsed">待检任务看板</span>
          <span v-if="!collapsed && pendingCount > 0" class="nav-badge amber">{{ pendingCount }}</span>
        </router-link>
        <router-link to="/results" class="nav-item" :class="{ active: isActive('/results') && !route.path.includes('/results/ledger') }" :title="collapsed ? '检验结果录入' : ''">
          <FormOutlined />
          <span v-if="!collapsed">检验结果录入</span>
        </router-link>
        <router-link to="/results/ledger" class="nav-item" :class="{ active: isActive('/results/ledger') }" :title="collapsed ? '检验结果台账' : ''">
          <FileTextOutlined />
          <span v-if="!collapsed">检验结果台账</span>
        </router-link>
      </div>

      <div class="nav-group">
        <div v-if="!collapsed" class="nav-group-title">报告与标准</div>
        <router-link to="/coas" class="nav-item" :class="{ active: isActive('/coas') }" :title="collapsed ? 'COA 报告管理' : ''">
          <FileTextOutlined />
          <span v-if="!collapsed">COA 报告管理</span>
        </router-link>
        <router-link to="/specs" class="nav-item" :class="{ active: isActive('/specs') }" :title="collapsed ? '质量标准库' : ''">
          <ReadOutlined />
          <span v-if="!collapsed">质量标准库</span>
        </router-link>
      </div>

      <div class="nav-group">
        <div v-if="!collapsed" class="nav-group-title">合规</div>
        <router-link to="/audit" class="nav-item" :class="{ active: isActive('/audit') }" :title="collapsed ? '审计追踪查询' : ''">
          <SearchOutlined />
          <span v-if="!collapsed">审计追踪查询</span>
        </router-link>
      </div>
    </nav>

    <div class="sidebar-foot">
      <button class="collapse-btn" :title="collapsed ? '展开侧边栏' : '收缩侧边栏'" @click="$emit('toggle')">
        <MenuFoldOutlined v-if="!collapsed" />
        <MenuUnfoldOutlined v-else />
        <span v-if="!collapsed">收缩侧边栏</span>
      </button>
      <div v-if="!collapsed" class="foot-meta">
        <div>HBOS · 海滨药业</div>
        <div>版本 0.1.0</div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import {
  DashboardOutlined, FileAddOutlined,
  CarryOutOutlined, FormOutlined, FileTextOutlined, ReadOutlined, SearchOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from '@ant-design/icons-vue'

defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

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
  transition: width 0.2s ease, flex-basis 0.2s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 64px;
  flex: 0 0 64px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar.collapsed .brand {
  justify-content: center;
  padding: 18px 0 16px;
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #ffffff;
  border: 1px solid var(--line);
  display: grid;
  place-items: center;
  flex: 0 0 40px;
  overflow: hidden;
}

.brand-logo {
  width: 30px;
  height: 30px;
  object-fit: contain;
  display: block;
}

.brand-name { font-size: 15px; font-weight: 700; color: #fff; white-space: nowrap; }
.brand-sub { font-size: 10px; color: #8eab9f; margin-top: 2px; white-space: nowrap; }

.nav {
  padding: 12px 10px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar.collapsed .nav {
  padding: 12px 8px;
}

.nav-group { margin-bottom: 16px; }

.nav-group-title {
  font-size: 10px;
  color: #71968b;
  padding: 6px 10px 4px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
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
  white-space: nowrap;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
}

.nav-item:hover { background: rgba(255, 255, 255, 0.07); color: #fff; }
.nav-item.active { background: var(--primary); color: #fff; font-weight: 600; }
.nav-item :deep(.anticon) { flex: 0 0 16px; opacity: 0.85; font-size: 15px; }

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
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: var(--sidebar-text);
  font-size: 12px;
  padding: 8px 10px;
  cursor: pointer;
  transition: background 0.12s ease;
}

.collapse-btn:hover { background: rgba(255, 255, 255, 0.12); color: #fff; }

.sidebar.collapsed .collapse-btn {
  justify-content: center;
  padding: 9px 0;
}

.collapse-btn .anticon { font-size: 15px; }

.sidebar.collapsed .foot-meta { display: none; }

@media (max-width: 768px) {
  .sidebar { width: 60px; flex: 0 0 60px; }
  .sidebar.collapsed { width: 60px; flex: 0 0 60px; }
  .brand { padding: 14px 0; justify-content: center; }
  .brand-name, .brand-sub, .nav-group-title, .nav-item span { display: none; }
  .nav-item { justify-content: center; padding: 10px 0; }
  .nav-badge { margin-left: -12px; margin-top: -14px; }
}
</style>
