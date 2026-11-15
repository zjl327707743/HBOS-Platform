<template>
  <aside class="kb-sidebar hbos-glass-g2" @click="onLinkClick">
    <RouterLink class="kb-back" to="/hbos/apps"><ArrowLeftOutlined />应用中心</RouterLink>
    <div class="kb-app-brand"><span class="kb-app-icon"><ReadOutlined /></span><div><strong>企业知识库</strong><small>KNOWLEDGE</small></div></div>
    <nav aria-label="知识库导航">
      <h2>员工查阅</h2>
      <RouterLink v-for="item in readerItems" :key="item.path" :to="item.path" :class="{active: route.path === item.path}" :aria-current="route.path === item.path ? 'page' : undefined"><component :is="item.icon" /><span>{{ item.label }}</span></RouterLink>
    </nav>
    <nav v-if="canMaintain" class="kb-maintenance-nav" aria-labelledby="kb-maintenance-nav-label">
      <h2 id="kb-maintenance-nav-label">资料维护</h2>
      <RouterLink v-for="item in maintenanceItems" :key="item.path" :to="item.path" :class="{active: route.path === item.path}" :aria-current="route.path === item.path ? 'page' : undefined"><component :is="item.icon" /><span>{{ item.label }}</span></RouterLink>
    </nav>
    <nav class="kb-sidebar-bottom" aria-label="辅助入口">
      <div class="kb-quiet-note"><SafetyCertificateOutlined /><span>查阅已共享资料</span></div>
      <RouterLink to="/hbos/knowledge/history?tab=feedback"><MessageOutlined /><span>反馈与建议</span></RouterLink>
      <RouterLink :to="{ path: '/hbos/knowledge', query: { connect: '1' } }"><LinkOutlined /><span>连接个人助手</span></RouterLink>
      <RouterLink to="/hbos"><SettingOutlined /><span>返回工作台</span></RouterLink>
    </nav>
  </aside>
</template>
<script setup lang="ts">
import { useRoute } from 'vue-router'
import { ArrowLeftOutlined, ReadOutlined, SearchOutlined, FolderOpenOutlined, StarOutlined, HistoryOutlined, SafetyCertificateOutlined, MessageOutlined, SettingOutlined, PlusOutlined, LinkOutlined } from '@ant-design/icons-vue'
defineProps<{ canMaintain: boolean; maintenance: boolean }>()
const emit = defineEmits<{ navigate: [] }>()
const route = useRoute()
function onLinkClick(event: MouseEvent) {
  if (event.target instanceof Element && event.target.closest('a') && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) emit('navigate')
}
const maintenanceItems = [
  {path:'/hbos/knowledge/maintenance',label:'资料管理',icon:FolderOpenOutlined},
  {path:'/hbos/knowledge/maintenance/upload',label:'新增资料',icon:PlusOutlined},
  {path:'/hbos/knowledge/maintenance/versions',label:'版本管理',icon:HistoryOutlined},
  {path:'/hbos/knowledge/maintenance/feedback',label:'员工反馈',icon:MessageOutlined},
]
const readerItems = [
  {path:'/hbos/knowledge',label:'问答与搜索',icon:SearchOutlined},
  {path:'/hbos/knowledge/catalog',label:'资料目录',icon:FolderOpenOutlined},
  {path:'/hbos/knowledge/favorites',label:'我的收藏',icon:StarOutlined},
  {path:'/hbos/knowledge/history',label:'我的记录',icon:HistoryOutlined},
]
</script>

<style scoped>
.kb-sidebar nav {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 5px;
}
.kb-sidebar nav a, .kb-quiet-note {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-width: 0;
  min-height: 42px;
  padding: 8px 12px;
}
.kb-sidebar nav a {
  color: #425675;
  border-radius: 12px;
  font-size: 14px;
  text-decoration: none;
}
.kb-sidebar nav a:hover, .kb-sidebar nav a.active {
  color: #5144bd;
  background: linear-gradient(95deg, #e9e2fb, #e9effb);
}
.kb-sidebar nav a.active { font-weight: 600; }
.kb-sidebar-bottom { margin-top: auto; padding-top: 20px; }
.kb-quiet-note { color: var(--hbos-text-muted); font-size: 12px; }
.kb-maintenance-nav {
  margin-top: 16px;
}

.kb-sidebar nav h2 {
  grid-column: 1 / -1;
  margin: 0 0 4px;
  padding-inline: 8px;
  color: var(--hbos-text-muted);
  font-size: 14px;
  font-weight: 600;
}
</style>
