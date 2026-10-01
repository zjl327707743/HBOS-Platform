<template>
  <section class="product-page">
    <div class="page-heading">
      <div>
        <span class="page-kicker">个人设置</span>
        <h1>我的与设置</h1>
        <p>个人偏好属于 Portal Experience State，不复制任何业务事实。</p>
      </div>
    </div>

    <div class="profile-grid">
      <section class="profile-card glass-surface">
        <div class="profile-hero">
          <a-avatar :size="72" class="profile-avatar">{{ portal.user?.avatarText }}</a-avatar>
          <div>
            <h2>{{ portal.user?.displayName }}</h2>
            <p>{{ portal.user?.id }}</p>
            <a-tag color="blue">{{ portal.user?.roleLabel }}</a-tag>
            <a-tag>{{ portal.user?.department }}</a-tag>
          </div>
        </div>
        <a-divider />
        <a-descriptions :column="1" size="small">
          <a-descriptions-item label="默认入口">HBOS Workspace</a-descriptions-item>
          <a-descriptions-item label="登录方式">Frappe Session · 飞书接入预留</a-descriptions-item>
          <a-descriptions-item label="可用应用">{{ portal.apps.length }}</a-descriptions-item>
        </a-descriptions>
        <a-button block>管理个人资料</a-button>
      </section>

      <section class="settings-stack">
        <div class="setting-card glass-surface">
          <div class="setting-head"><div><h3>外观体验</h3><p>设计系统级偏好，未来跨 Native HBOS APP 继承</p></div><BgColorsOutlined /></div>
          <div class="setting-row"><span>主题</span><a-segmented v-model:value="theme" :options="['明亮', '跟随系统']" /></div>
          <div class="setting-row"><span>视觉动效</span><a-switch v-model:checked="motion" checked-children="开启" un-checked-children="关闭" /></div>
          <div class="setting-row"><span>表格密度</span><a-segmented v-model:value="density" :options="['舒适', '紧凑']" /></div>
        </div>

        <div class="setting-card glass-surface">
          <div class="setting-head"><div><h3>工作偏好</h3><p>控制“我的工作”和首页内容的呈现方式</p></div><SlidersOutlined /></div>
          <div class="setting-row"><span>优先显示超期事项</span><a-switch checked /></div>
          <div class="setting-row"><span>显示业务脉搏</span><a-switch checked /></div>
          <div class="setting-row"><span>显示数字孪生入口</span><a-switch checked /></div>
        </div>

      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  BgColorsOutlined,
  SlidersOutlined,
} from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'

const portal = usePortalStore()
const theme = ref('明亮')
const density = ref('舒适')
const motion = ref(true)
</script>
