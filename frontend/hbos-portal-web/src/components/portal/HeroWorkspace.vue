<script setup lang="ts">
import { AppstoreOutlined, NodeIndexOutlined, UnorderedListOutlined, UserOutlined } from '@ant-design/icons-vue'

defineProps<{
  userName: string; totalActions: number; appCount: number; tasksLoading?: boolean
  tasksError?: boolean; showTwinPreview: boolean; twinStateLabel: string
}>()
</script>

<template>
  <section class="v10-home-hero" aria-labelledby="portal-welcome">
    <div class="v10-welcome v10-surface">
      <div class="v10-home-orbit" aria-hidden="true" />
      <div class="v10-hero-top"><span>HBOS · 工作平台</span><span>你好，{{ userName }}</span></div>
      <h1 id="portal-welcome">把工作连起来，<br /><span>把专注留给创造。</span></h1>
      <p>查看待办，找到常用应用，从这里开始今天的工作。</p>
      <div class="v10-actions">
        <a-button type="primary" @click="$router.push('/hbos/work')">查看我的工作</a-button>
        <a-button @click="$router.push('/hbos/apps')">浏览应用</a-button>
      </div>
      <div class="v10-hero-summary">
        <span :class="{ 'v10-summary-warning': tasksError }">{{ tasksLoading ? '正在读取待办' : tasksError ? '部分待办暂不可用' : totalActions ? totalActions + ' 项工作需要你处理' : '当前没有待处理事项' }}</span><span>{{ appCount }} 个可用应用</span>
      </div>
    </div>
    <aside class="v10-home-aside v10-surface">
      <div class="v10-hero-top"><span>工作概览</span></div>
      <h2>应用与待办，<br />集中在这里。</h2>
      <div class="v10-overview-links">
        <RouterLink to="/hbos/profile"><UserOutlined /><strong>我的账号</strong><small>查看个人中心</small></RouterLink>
        <RouterLink to="/hbos/apps"><AppstoreOutlined /><strong>{{ appCount }} 个应用</strong><small>按你的权限提供</small></RouterLink>
        <RouterLink to="/hbos/work"><UnorderedListOutlined /><strong>{{ tasksLoading || tasksError ? '查看待办' : totalActions + ' 项待办' }}</strong><small>集中查看待办</small></RouterLink>
      </div>
      <RouterLink v-if="showTwinPreview" to="/hbos/twin" class="v10-overview-twin"><NodeIndexOutlined /><span><strong>设备与工艺空间</strong><small>{{ twinStateLabel }}</small></span></RouterLink>
    </aside>
  </section>
</template>
