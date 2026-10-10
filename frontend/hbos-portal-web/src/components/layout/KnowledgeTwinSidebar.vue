<template>
  <aside class="kt-sidebar hbos-glass-g2" aria-label="知识与设备应用导航">
    <button class="kt-back" type="button" @click="$router.push('/hbos/apps')">
      <ArrowLeftOutlined /> 返回应用中心
    </button>

    <div class="kt-app-brand">
      <div class="kt-app-mark" :class="{ twin: isTwin }">
        <DeploymentUnitOutlined v-if="isTwin" />
        <ReadOutlined v-else />
      </div>
      <div>
        <strong>{{ isTwin ? '设备与工艺' : '知识库' }}</strong>
        <small>{{ isTwin ? 'Equipment workspace' : 'Knowledge workspace' }}</small>
      </div>
    </div>

    <nav class="kt-local-nav">
      <span>应用导航</span>
      <RouterLink to="/hbos/knowledge" :class="{ active: !isTwin }">
        <SearchOutlined /> 知识检索
      </RouterLink>
      <RouterLink to="/hbos/twin" :class="{ active: isTwin }">
        <DeploymentUnitOutlined /> 设备认知
      </RouterLink>
    </nav>

    <div class="kt-sidebar-spacer"></div>
    <div class="kt-side-note">
      <SafetyCertificateOutlined />
      <strong>{{ isTwin ? '把知识放在设备旁' : '有依据，才有答案' }}</strong>
      <p>{{ isTwin ? '先理解结构，再查找本人有权访问的知识。' : '只展示授权范围内的必要摘录，不提供原文下载。' }}</p>
    </div>
    <RouterLink class="kt-switch" :to="isTwin ? '/hbos/knowledge' : '/hbos/twin'">
      {{ isTwin ? '前往知识助理' : '打开设备与工艺' }} <ArrowRightOutlined />
    </RouterLink>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  DeploymentUnitOutlined,
  ReadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'

const route = useRoute()
const isTwin = computed(() => route.path.startsWith('/hbos/twin'))
</script>

<style scoped>
.kt-sidebar {
  position: sticky;
  top: 96px;
  display: flex;
  min-height: calc(100vh - 124px);
  flex-direction: column;
  padding: 18px;
  border-radius: 24px;
}
.kt-back,
.kt-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  color: var(--hbos-text-muted);
  font-size: 12px;
  cursor: pointer;
}
.kt-app-brand { display: flex; align-items: center; gap: 12px; margin: 26px 2px 28px; }
.kt-app-brand strong { display: block; font-size: 15px; }
.kt-app-brand small { display: block; margin-top: 3px; color: var(--hbos-text-muted); font-size: 10px; }
.kt-app-mark {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border-radius: 15px;
  color: white;
  font-size: 21px;
  background: linear-gradient(135deg,#7167ff,#4ca6ff);
  box-shadow: 0 12px 28px rgba(86,100,230,.22);
}
.kt-app-mark.twin { background: var(--hbos-domain-digital-twin); }
.kt-local-nav { display: grid; gap: 7px; }
.kt-local-nav > span { margin: 0 11px 5px; color: var(--hbos-text-muted); font-size: 10px; font-weight: 800; letter-spacing: .12em; }
.kt-local-nav a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 13px;
  color: var(--hbos-text-secondary);
  font-size: 13px;
  font-weight: 650;
}
.kt-local-nav a.active { color: #3f5ee9; background: rgba(95,103,255,.10); }
.kt-sidebar-spacer { flex: 1; min-height: 48px; }
.kt-side-note { padding: 15px; border: 1px solid rgba(91,103,180,.09); border-radius: 17px; background: rgba(255,255,255,.52); }
.kt-side-note > :first-child { color: #5d6cf6; }
.kt-side-note strong { display: block; margin-top: 9px; font-size: 12px; }
.kt-side-note p { margin: 6px 0 0; color: var(--hbos-text-muted); font-size: 10px; line-height: 1.55; }
.kt-switch { justify-content: space-between; margin-top: 10px; padding: 11px 12px; border-radius: 13px; background: rgba(255,255,255,.58); color: #40577f; font-weight: 700; }
@media (max-width: 900px) {
  .kt-sidebar { position: static; display: block; min-height: 0; padding: 6px; border-radius: 18px; }
  .kt-back,.kt-side-note,.kt-sidebar-spacer,.kt-app-brand,.kt-switch { display: none; }
  .kt-local-nav { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 4px; width: 100%; }
  .kt-local-nav > span { display: none; }
  .kt-local-nav a { justify-content: center; min-width: 0; padding: 10px 8px; white-space: nowrap; }
}
</style>
