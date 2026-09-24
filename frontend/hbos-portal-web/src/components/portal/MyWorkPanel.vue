<template>
  <section class="section-panel glass-surface">
    <div class="section-head">
      <div>
        <h2>我的工作</h2>
        <p>今天、超期与高优先级事项优先</p>
      </div>
      <a-button type="link" @click="$router.push('/hbos/work')">查看全部 <RightOutlined /></a-button>
    </div>

    <div class="task-list">
      <button
        v-for="task in tasks"
        :key="task.taskId"
        type="button"
        class="task-row task-row-button"
        @click="openTask(task)"
      >
        <div class="task-icon" :class="task.appId"><component :is="appIcon(task.appId)" /></div>
        <div class="task-copy">
          <strong>{{ task.title }}</strong>
          <span>{{ chineseApp(task.appId) }} · {{ task.description }}</span>
        </div>
        <div class="task-meta">
          <b :class="{ overdue: task.overdue }">{{ task.dueLabel }}</b>
          <a-tag :color="tagColor(task)">{{ tagText(task) }}</a-tag>
        </div>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  ClockCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  RightOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'
import type { UnifiedTaskDTO } from '@/contracts/portal'
import { openBusinessRoute } from '@/services/businessNavigation'

defineProps<{ tasks: UnifiedTaskDTO[] }>()
const router = useRouter()

function openTask(task: UnifiedTaskDTO) {
  void openBusinessRoute(router, task.appId, task.deepLink)
}

const icons: Record<string, Component> = {
  lims: ExperimentOutlined,
  attendance: ClockCircleOutlined,
  inventory: InboxOutlined,
  equipment: ToolOutlined,
}

function appIcon(appId: string) {
  return icons[appId] || InboxOutlined
}

function chineseApp(appId: string) {
  return ({
    lims: 'LIMS',
    attendance: '考勤',
    inventory: '仓储',
    equipment: '设备',
  } as Record<string, string>)[appId] || appId
}

function tagText(task: UnifiedTaskDTO) {
  if (task.overdue) return '已超期'
  if (task.priority === 'high') return '高优先级'
  if (task.priority === 'critical') return '紧急'
  return '待处理'
}

function tagColor(task: UnifiedTaskDTO) {
  if (task.overdue || task.priority === 'critical') return 'error'
  if (task.priority === 'high') return 'warning'
  return 'processing'
}
</script>
