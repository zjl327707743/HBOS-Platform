<template>
  <div class="portal-page iam-portal-preview">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <PointerAtmosphere />
    <div class="aurora aurora-a"></div><div class="aurora aurora-b"></div><div class="aurora aurora-c"></div>
    <div class="portal-shell">
      <GlobalHeader
        :avatar-text="portal.user?.avatarText || '管'"
        :apps="portal.apps"
        :context-label="portal.branding?.workspaceName"
        @open-command="commandOpen = true"
      />
      <div class="portal-layout-grid">
        <aside class="portal-sidebar glass-surface" aria-label="Portal 导航">
          <div class="nav-section-label">工作台</div>
          <RouterLink to="/hbos" class="portal-nav-item" title="首页"><HomeOutlined /><span>首页</span></RouterLink>
          <RouterLink to="/hbos/work" class="portal-nav-item" title="我的工作"><UnorderedListOutlined /><span>我的工作</span></RouterLink>
          <RouterLink to="/hbos/apps" class="portal-nav-item" title="应用中心"><AppstoreOutlined /><span>应用中心</span></RouterLink>
          <div class="nav-divider"></div>
          <div class="nav-section-label">平台管理</div>
          <RouterLink
            to="/hbos/admin/people"
            class="portal-nav-item"
            :class="{ 'router-link-exact-active': route.path.startsWith('/hbos/admin/') }"
            title="人员与权限"
            aria-label="人员与权限"
          ><TeamOutlined /><span>人员与权限</span></RouterLink>
          <div class="nav-divider"></div>
          <div class="nav-section-label">个人</div>
          <RouterLink to="/hbos/profile" class="portal-nav-item subtle" title="我的与设置"><UserOutlined /><span>我的与设置</span></RouterLink>
          <div class="sidebar-spacer"></div>
          <div class="portal-side-note"><span>业务应用从“应用中心”或顶部应用切换器进入。</span></div>
        </aside>
        <main id="main-content" class="portal-route-content" tabindex="-1"><RouterView /></main>
      </div>
    </div>
    <nav class="mobile-portal-nav glass-surface" aria-label="预览移动导航">
      <RouterLink to="/hbos" class="mobile-nav-item"><HomeOutlined /><span>首页</span></RouterLink>
      <RouterLink to="/hbos/apps" class="mobile-nav-item"><AppstoreOutlined /><span>应用</span></RouterLink>
      <RouterLink to="/hbos/admin/people" class="mobile-nav-item router-link-active"><TeamOutlined /><span>人员权限</span></RouterLink>
      <RouterLink to="/hbos/profile" class="mobile-nav-item"><UserOutlined /><span>我的与设置</span></RouterLink>
    </nav>
    <CommandPalette :open="commandOpen" @close="commandOpen = false" />
  </div>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { HomeOutlined, UnorderedListOutlined, AppstoreOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import GlobalHeader from '@/components/layout/GlobalHeader.vue'
import PointerAtmosphere from '@/components/layout/PointerAtmosphere.vue'
import CommandPalette from '@/components/portal/CommandPalette.vue'
const portal = usePortalStore()
const route = useRoute()
const commandOpen = ref(false)
function onShortcut(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault(); commandOpen.value = true
  }
  if (event.key === 'Escape') commandOpen.value = false
}
onMounted(() => window.addEventListener('keydown', onShortcut))
onBeforeUnmount(() => window.removeEventListener('keydown', onShortcut))
</script>
<style>
/* 仅限独立预览：修正窄侧栏的文字显示，未改动正式 Portal CSS。 */
.iam-portal-preview .portal-sidebar { min-height: 560px; height: calc(100dvh - 162px); }
.iam-portal-preview .portal-nav-item { font-size:14px; font-weight:500; }
.iam-portal-preview .nav-section-label { font-size:11px; font-weight:500; letter-spacing:0; }
.iam-portal-preview .portal-side-note { font-size:11px; line-height:1.8; }
.iam-portal-preview .skip-link:not(:focus) { top:0;left:0;width:1px;height:1px;padding:0;clip-path:inset(50%);overflow:hidden;white-space:nowrap; }
@media(max-width:1280px) and (min-width:768px){
  .iam-portal-preview .portal-nav-item > span:not(.anticon),
  .iam-portal-preview .portal-sidebar .nav-section-label,
  .iam-portal-preview .portal-side-note { display:none; }
  .iam-portal-preview .portal-nav-item { min-height:49px; }
  .iam-portal-preview .portal-nav-item .anticon { font-size:20px; }
}
</style>
