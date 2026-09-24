<template>
  <header class="hbos-header glass-surface">
    <button class="brand-wrap" type="button" aria-label="返回 HBOS 首页" @click="$router.push('/hbos')">
      <div class="brand-mark">H</div>
      <div class="brand-copy">
        <div class="brand-name">HBOS</div>
        <div class="brand-caption">{{ contextLabel || '海滨智能运营工作台' }}</div>
      </div>
    </button>

    <button class="global-search" type="button" aria-label="打开全局搜索" @click="$emit('open-command')">
      <SearchOutlined />
      <span>搜索应用、批次、样品、员工或输入命令…</span>
      <kbd>⌘ K</kbd>
    </button>

    <div class="header-actions">
      <AppSwitcher :apps="apps" />
      <NotificationCenter />

      <a-tooltip title="帮助">
        <a-button
          class="top-icon-button"
          type="text"
          shape="circle"
          aria-label="打开帮助"
        >
          <QuestionCircleOutlined />
        </a-button>
      </a-tooltip>

      <a-dropdown>
        <a-avatar class="user-avatar" role="button" aria-label="打开个人菜单">{{ avatarText }}</a-avatar>
        <template #overlay>
          <a-menu>
            <a-menu-item @click="$router.push('/hbos/profile')">个人与设置</a-menu-item>
            <a-menu-divider />
            <a-menu-item>进入 Management Console</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { QuestionCircleOutlined, SearchOutlined } from '@ant-design/icons-vue'
import AppSwitcher from '@/components/global/AppSwitcher.vue'
import NotificationCenter from '@/components/global/NotificationCenter.vue'
import type { AppManifestDTO } from '@/contracts/portal'

defineProps<{
  avatarText: string
  apps: AppManifestDTO[]
  contextLabel?: string
}>()

defineEmits<{ (e: 'open-command'): void }>()
</script>
