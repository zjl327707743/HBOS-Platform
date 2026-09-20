// ============================================================
// 稳定性板块共享样式工具
//
// 历史说明：本文件曾承载 7 视图的演示数据层（`TEST-HBOS-M2-STB-*`）。
// R8G（工作台 + 考察申请与方案）、R8H（样品入箱与台账 + 取样与检测计划）、
// R8I（结果录入与趋势 + 报告与有效期 + 变更·稳定性室·设备）已先后接入真实后端，
// 各视图演示数据已随之移除，仅保留语义色工具函数供稳定性视图共用。
// ============================================================

export type Tone = 'pass' | 'warn' | 'danger' | 'info' | 'muted'

/** 语义色 → Ant Design Vue pill 类名（tokens.scss 已全局定义） */
export const TONE_CLASS: Record<Tone, string> = {
  pass: 'pill-pass',
  warn: 'pill-warn',
  danger: 'pill-danger',
  info: 'pill-info',
  muted: 'pill-muted',
}

export function toneClass(tone: Tone): string {
  return `pill ${TONE_CLASS[tone]}`
}
