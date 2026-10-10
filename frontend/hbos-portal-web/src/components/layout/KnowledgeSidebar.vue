<template>
  <aside class="kb-sidebar hbos-glass-g2">
    <button class="kb-back" @click="$router.push('/hbos/apps')"><ArrowLeftOutlined />应用中心</button>
    <div class="kb-app-brand"><span class="kb-app-icon"><ReadOutlined /></span><div><strong>{{ maintenance ? '知识维护' : '知识库' }}</strong><small>{{ maintenance ? '资料维护工作台' : '我的知识工作台' }}</small></div></div>
    <nav :aria-label="maintenance ? '知识维护导航' : '知识库导航'">
      <RouterLink v-for="item in items" :key="item.path" :to="item.path" :class="{active: route.path === item.path}" :aria-current="route.path === item.path ? 'page' : undefined"><component :is="item.icon" /><span>{{ item.label }}</span></RouterLink>
    </nav>
    <div class="kb-sidebar-bottom">
      <div class="kb-quiet-note"><SafetyCertificateOutlined /><span>只查已共享、当前有效的资料</span></div>
      <RouterLink v-if="!maintenance" to="/hbos/knowledge/history?tab=feedback"><MessageOutlined />反馈与建议</RouterLink>
      <RouterLink v-if="canMaintain && !maintenance" to="/hbos/knowledge/maintenance"><SettingOutlined />知识维护</RouterLink>
      <RouterLink v-if="maintenance" to="/hbos/knowledge"><SearchOutlined />返回查知识</RouterLink>
    </div>
  </aside>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftOutlined, ReadOutlined, SearchOutlined, FolderOpenOutlined, StarOutlined, HistoryOutlined, SafetyCertificateOutlined, MessageOutlined, SettingOutlined, PlusOutlined } from '@ant-design/icons-vue'
const props = defineProps<{ canMaintain: boolean; maintenance: boolean }>()
const route = useRoute()
const items = computed(() => props.maintenance ? [
  {path:'/hbos/knowledge/maintenance',label:'资料管理',icon:FolderOpenOutlined},
  {path:'/hbos/knowledge/maintenance/upload',label:'新增资料',icon:PlusOutlined},
  {path:'/hbos/knowledge/maintenance/versions',label:'版本管理',icon:HistoryOutlined},
  {path:'/hbos/knowledge/maintenance/feedback',label:'员工反馈',icon:MessageOutlined},
] : [
  {path:'/hbos/knowledge',label:'查知识',icon:SearchOutlined},
  {path:'/hbos/knowledge/catalog',label:'资料目录',icon:FolderOpenOutlined},
  {path:'/hbos/knowledge/favorites',label:'我的收藏',icon:StarOutlined},
  {path:'/hbos/knowledge/history',label:'我的记录',icon:HistoryOutlined},
])
</script>
