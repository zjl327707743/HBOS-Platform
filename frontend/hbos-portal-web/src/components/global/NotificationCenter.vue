<template>
  <a-tooltip title="消息与通知">
    <a-badge :dot="unreadCount > 0">
      <a-button
        class="top-icon-button"
        type="text"
        shape="circle"
        aria-label="打开消息与通知"
        @click="open = true"
      >
        <BellOutlined />
      </a-button>
    </a-badge>
  </a-tooltip>

  <a-drawer
    v-model:open="open"
    title="消息与通知"
    width="420"
    placement="right"
    root-class-name="hbos-notification-drawer"
  >
    <div class="notification-summary">
      <span>未读 {{ unreadCount }}</span>
      <a-button type="link" size="small" @click="markAllRead">全部标为已读</a-button>
    </div>

    <div class="notification-group">
      <div class="notification-group-title">需要关注</div>
      <button
        v-for="item in importantItems"
        :key="item.id"
        type="button"
        class="notification-item"
        :class="{ unread: !item.read }"
        @click="openNotification(item)"
      >
        <div class="notification-icon" :class="item.appId">
          <component :is="iconMap[item.appId]" />
        </div>
        <div class="notification-copy">
          <div class="notification-title-row">
            <strong>{{ item.title }}</strong>
            <span>{{ item.time }}</span>
          </div>
          <p>{{ item.description }}</p>
          <small>{{ item.appLabel }}</small>
        </div>
      </button>
    </div>

    <div class="notification-group secondary">
      <div class="notification-group-title">系统信息</div>
      <button
        v-for="item in systemItems"
        :key="item.id"
        type="button"
        class="notification-item"
        :class="{ unread: !item.read }"
        @click="item.read = true"
      >
        <div class="notification-icon system"><SyncOutlined /></div>
        <div class="notification-copy">
          <div class="notification-title-row">
            <strong>{{ item.title }}</strong>
            <span>{{ item.time }}</span>
          </div>
          <p>{{ item.description }}</p>
          <small>系统</small>
        </div>
      </button>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  BellOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  SyncOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'

interface PrototypeNotification {
  id: string
  appId: 'lims' | 'attendance' | 'inventory' | 'equipment' | 'system'
  appLabel: string
  title: string
  description: string
  time: string
  kind: 'action' | 'risk' | 'system'
  read: boolean
  deepLink?: string
}

const router = useRouter()
const open = ref(false)
const items = reactive<PrototypeNotification[]>([
  {
    id: 'lims-review', appId: 'lims', appLabel: 'LIMS', kind: 'action', read: false,
    title: '1 个结果已超期等待复核', description: 'SAMPLE-001 · 阿莫西林含量结果', time: '16:08', deepLink: '/hbos/lims',
  },
  {
    id: 'inventory-expiry', appId: 'inventory', appLabel: '仓储', kind: 'risk', read: false,
    title: '2 个批次进入效期关注范围', description: '六车间中间库 · 建议今天检查', time: '15:42', deepLink: '/hbos/apps',
  },
  {
    id: 'attendance-exception', appId: 'attendance', appLabel: '考勤', kind: 'action', read: true,
    title: '考勤异常已提交', description: '生产二部 · 等待你确认', time: '14:20', deepLink: '/hbos/work',
  },
  {
    id: 'sync-ok', appId: 'system', appLabel: '系统', kind: 'system', read: true,
    title: '应用状态同步完成', description: 'Portal Prototype Provider 已刷新', time: '13:58',
  },
])

const iconMap: Record<string, Component> = {
  lims: ExperimentOutlined,
  attendance: ClockCircleOutlined,
  inventory: InboxOutlined,
  equipment: ToolOutlined,
  system: SyncOutlined,
}

const unreadCount = computed(() => items.filter((item) => !item.read).length)
const importantItems = computed(() => items.filter((item) => item.kind !== 'system'))
const systemItems = computed(() => items.filter((item) => item.kind === 'system'))

function markAllRead() {
  items.forEach((item) => { item.read = true })
}

function openNotification(item: PrototypeNotification) {
  item.read = true
  if (item.deepLink) {
    open.value = false
    void router.push(item.deepLink)
  }
}
</script>
