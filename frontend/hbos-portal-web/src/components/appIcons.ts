import type { Component } from 'vue'
import {
  ClockCircleOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ReadOutlined,
  SafetyOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue'

export const iconMap: Record<string, Component> = {
  ExperimentOutlined, InboxOutlined, ClockCircleOutlined, ToolOutlined,
  ReadOutlined, SafetyOutlined, ThunderboltOutlined,
  lims: ExperimentOutlined,
  inventory: InboxOutlined,
  attendance: ClockCircleOutlined,
  equipment: ToolOutlined,
  system: SyncOutlined,
}

const appTitles: Record<string, string> = {
  lims: 'LIMS', inventory: '仓储', attendance: '考勤', equipment: '设备', system: '系统',
}

// Experience ordering only; Provider capabilities remain the access authority.
export const PRIMARY_APP_IDS = ['lims', 'inventory', 'attendance', 'equipment']

export function appIcon(appId: string): Component {
  return iconMap[appId] || InboxOutlined
}

export function chineseApp(appId: string): string {
  return appTitles[appId] || appId
}
