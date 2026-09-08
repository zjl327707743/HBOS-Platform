// ============================================================
// 留样板块 R7B/C 前端演示数据与角色矩阵（M2-R7D Vue 复刻）
//
// 说明：
//  - 观察 / 使用 / 处理 / 工作台的 R7B/C 后端（DocType + retention_service
//    whitelist）尚未落地。为让 Owner 先在测试路径确认完整视觉与交互，
//    本模块提供 TEST-HBOS-M2-RET-* 演示数据源与演示角色矩阵。
//  - 页面从 seedXxx() 拷贝数据做本地交互（刷新即复位），不真实落库。
//  - R7A 登记台账 / 留样产品为真实 API（src/api/lims.ts），不经此模块。
//  - R7B/C 后端就绪后：删本模块、把各页数据源替换为 retention_service
//    whitelist 调用即可，页面结构与角色矩阵不变。
// ============================================================

import { reactive } from 'vue'

// ---------- 演示角色 ----------
export type DemoRole = 'analyst' | 'reviewer' | 'qa' | 'manager'

export const DEMO_ROLES: { value: DemoRole; label: string; person: string; desc: string }[] = [
  { value: 'analyst', label: 'Analyst（检验员）', person: '王敏', desc: '登记 / 取样执行 / 观察录入 / 销毁处理人' },
  { value: 'reviewer', label: 'Reviewer（QC）', person: '李静', desc: '库存确认+预占 / QC 级审批 / 观察批选取' },
  { value: 'qa', label: 'QA', person: '刘洋', desc: 'QA 级审批 / 销毁监督 / 观察审核' },
  { value: 'manager', label: 'Manager（QM）', person: '张总', desc: 'QM 批准 / 取消逃生口 / 手动调整 / 受托转出' },
]

export const demo = reactive({ role: 'reviewer' as DemoRole })

export function demoPerson(role: DemoRole = demo.role): string {
  return DEMO_ROLES.find((r) => r.value === role)?.person ?? ''
}

export function setDemoRole(role: DemoRole) {
  demo.role = role
}

// 演示横幅文案
export const DEMO_NOTE =
  '演示数据 · R7B/C 后端未接通：本页观察/使用/处理均为演示（TEST-HBOS-M2-RET-*），操作不会真实落库。留样登记与台账、留样产品两页为真实 R7A API。'

// ---------- 角色动作矩阵（M2-R7 rev6 · 方案 6 节）----------
// 前端只按此显隐/预校验；后端就绪后仍以后端角色与 SoD 硬校验为准。
export const ACTION_ROLES: Record<string, DemoRole[]> = {
  register: ['analyst', 'manager'],
  obs_select: ['reviewer', 'manager'],
  obs_record: ['analyst', 'manager'],
  obs_review: ['qa', 'manager'],
  usage_submit: ['analyst', 'manager'],
  usage_confirm: ['reviewer', 'manager'],
  usage_qc: ['reviewer', 'manager'],
  usage_qa: ['qa', 'manager'],
  usage_qm: ['manager'],
  usage_execute: ['analyst', 'manager'],
  usage_reject: ['reviewer', 'qa', 'manager'],
  usage_cancel: ['manager'],
  disposal_create: ['analyst', 'manager'],
  disposal_qclevel: ['reviewer', 'manager'],
  disposal_qalevel: ['qa', 'manager'],
  disposal_qm: ['manager'],
  disposal_execute: ['analyst', 'qa', 'manager'],
  disposal_cancel: ['manager'],
}

export function can(role: DemoRole, action: string): boolean {
  const roles = ACTION_ROLES[action]
  return !!roles && roles.includes(role)
}

export const SOD_NOTE = '职责分离（SoD）：同一用户不得连续两级签署，申请人不得担任审批人；前端仅做提示，后端硬校验。'

// 由演示角色反查真实可代入的动作动作集合（用于按钮显隐）
export function roleActions(role: DemoRole): Set<string> {
  const set = new Set<string>()
  for (const [action, roles] of Object.entries(ACTION_ROLES)) {
    if (roles.includes(role)) set.add(action)
  }
  return set
}

// ---------- 观察计划完整性（N/3） ----------
export interface ObsCompleteness {
  product: string
  rule: string // 年度观察批 / 每批观察
  year: number
  selected: number
  cap: number | null // null = 每批观察不设上限
}

export function seedObsCompleteness(): ObsCompleteness[] {
  return [
    { product: 'TEST 成品片剂A', rule: '年度观察批', year: 2026, selected: 2, cap: 3 },
    { product: 'TEST 原料A', rule: '年度观察批', year: 2026, selected: 3, cap: 3 },
    { product: 'TEST 外售产品B', rule: '每批观察', year: 2026, selected: 4, cap: null },
  ]
}

// ---------- 观察计划看板 ----------
export interface ObsBoardRow {
  name: string
  sampleName: string
  batch: string
  obsYear: number
  monthOffset: number
  planDate: string
  due: '应观察' | '已逾期' | '已完成'
  result: '正常' | '异常' | null
  anomaly: string
  observedDate: string
  observer: string
  reviewer: string
  selectedReason: string // 年度观察批 / 外售产品每批 / 其他
}

export function seedObsBoard(): ObsBoardRow[] {
  return [
    {
      name: 'TEST-HBOS-M2-RET-2026-00001', sampleName: 'TEST 成品片剂A', batch: 'T260901',
      obsYear: 2026, monthOffset: 0, planDate: '2026-09-01', due: '已逾期', result: null,
      anomaly: '', observedDate: '', observer: '', reviewer: '', selectedReason: '年度观察批',
    },
    {
      name: 'TEST-HBOS-M2-RET-2026-00002', sampleName: 'TEST 原料A', batch: 'T260802',
      obsYear: 2026, monthOffset: 0, planDate: '2026-08-02', due: '已完成', result: '正常',
      anomaly: '', observedDate: '2026-08-02', observer: '王敏', reviewer: '李静', selectedReason: '年度观察批',
    },
    {
      name: 'TEST-HBOS-M2-RET-2025-00018', sampleName: 'TEST 原料A', batch: 'T251106',
      obsYear: 2026, monthOffset: 12, planDate: '2026-11-06', due: '应观察', result: null,
      anomaly: '', observedDate: '', observer: '', reviewer: '', selectedReason: '年度观察批',
    },
    {
      name: 'TEST-HBOS-M2-RET-2025-00003', sampleName: 'TEST 成品片剂A', batch: 'T250310',
      obsYear: 2026, monthOffset: 24, planDate: '2026-09-03', due: '应观察', result: null,
      anomaly: '', observedDate: '', observer: '', reviewer: '', selectedReason: '年度观察批',
    },
    {
      name: 'TEST-HBOS-M2-RET-2024-00008', sampleName: 'TEST 外售产品B', batch: 'T240528',
      obsYear: 2026, monthOffset: 24, planDate: '2026-05-28', due: '已完成', result: '异常',
      anomaly: '受潮结块，已按 OOS 上报 QC 主管。', observedDate: '2026-05-28', observer: '王敏', reviewer: '刘洋', selectedReason: '外售产品每批',
    },
  ]
}

// ---------- 使用申请 ----------
export type UsageStatus =
  | '草稿' | '待库存确认' | '待QC批准' | '待QA批准' | '待QM批准'
  | '已批准' | '已执行' | '已驳回' | '已取消'

// 四级审批链的签署位（申请人创建即 done；inventory=库存确认+预占）
export type UsageStepKey = 'inventory' | 'qc' | 'qa' | 'qm'
export const USAGE_STEP_LABEL: Record<UsageStepKey, string> = {
  inventory: '库存确认',
  qc: 'QC 批准',
  qa: 'QA 批准',
  qm: 'QM 批准',
}

export interface UsageApply {
  name: string
  retentionName: string
  product: string
  batch: string
  qty: number
  uom: string
  scenario: string
  reason: string
  dept: string
  applicant: string
  applicantDate: string
  status: UsageStatus
  signedBy: Partial<Record<UsageStepKey, { who: string; at: string }>>
  currentQty: number
  reservedQty: number
}

export function usageQtyLabel(a: UsageApply): string {
  return `${a.qty} ${a.uom}`
}

// 使用申请当前需要哪个角色动作
export function usageActionNeeded(status: UsageStatus): string | null {
  if (status === '草稿') return 'usage_submit'
  if (status === '待库存确认') return 'usage_confirm'
  if (status === '待QC批准') return 'usage_qc'
  if (status === '待QA批准') return 'usage_qa'
  if (status === '待QM批准') return 'usage_qm'
  if (status === '已批准') return 'usage_execute'
  return null
}

export function seedUsageApplies(): UsageApply[] {
  return [
    {
      name: 'HBOS-RET-USE-2026-00013', retentionName: 'TEST-HBOS-M2-RET-2026-00005',
      product: 'TEST 原料A', batch: 'T261001', qty: 10, uom: 'g',
      scenario: '稳定性考察', reason: '稳定性考察对照需要。', dept: 'QC 检验室',
      applicant: '王敏', applicantDate: '2026-09-06', status: '草稿',
      signedBy: {}, currentQty: 200, reservedQty: 0,
    },
    {
      name: 'HBOS-RET-USE-2026-00012', retentionName: 'TEST-HBOS-M2-RET-2026-00001',
      product: 'TEST 成品片剂A', batch: 'T260901', qty: 12, uom: 'g',
      scenario: '检验结果分析', reason: '复检异常结果核查需要。', dept: 'QC 检验室',
      applicant: '王敏', applicantDate: '2026-09-05', status: '待QC批准',
      signedBy: { inventory: { who: '赵磊', at: '2026-09-05' } }, currentQty: 380, reservedQty: 12,
    },
    {
      name: 'HBOS-RET-USE-2026-00011', retentionName: 'TEST-HBOS-M2-RET-2026-00003',
      product: 'TEST 外售产品B', batch: 'T260715', qty: 2, uom: '瓶',
      scenario: '用户投诉', reason: '用户投诉调查留样核查。', dept: '质量管理部',
      applicant: '王敏', applicantDate: '2026-09-03', status: '已批准',
      signedBy: {
        inventory: { who: '赵磊', at: '2026-09-03' },
        qc: { who: '李静', at: '2026-09-04' },
        qa: { who: '刘洋', at: '2026-09-04' },
        qm: { who: '张总', at: '2026-09-05' },
      },
      currentQty: 2, reservedQty: 2,
    },
    {
      name: 'HBOS-RET-USE-2026-00010', retentionName: 'TEST-HBOS-M2-RET-2026-00002',
      product: 'TEST 原料A', batch: 'T260802', qty: 30, uom: 'g',
      scenario: '生产异常', reason: '生产异常批次留样复检。', dept: '生产一部',
      applicant: '陈工', applicantDate: '2026-09-02', status: '待QA批准',
      signedBy: {
        inventory: { who: '赵磊', at: '2026-09-02' },
        qc: { who: '李静', at: '2026-09-03' },
      },
      currentQty: 120, reservedQty: 30,
    },
    {
      name: 'HBOS-RET-USE-2026-00009', retentionName: 'TEST-HBOS-M2-RET-2025-00018',
      product: 'TEST 成品片剂A', batch: 'T251001', qty: 8, uom: 'g',
      scenario: '上市前研发', reason: '工艺一致性比对。', dept: '研发部',
      applicant: '王敏', applicantDate: '2026-08-20', status: '已执行',
      signedBy: {
        inventory: { who: '赵磊', at: '2026-08-20' },
        qc: { who: '李静', at: '2026-08-21' },
        qa: { who: '刘洋', at: '2026-08-21' },
        qm: { who: '张总', at: '2026-08-22' },
      },
      currentQty: 0, reservedQty: 0,
    },
    {
      name: 'HBOS-RET-USE-2026-00007', retentionName: 'TEST-HBOS-M2-RET-2024-00005',
      product: 'TEST 原料A', batch: 'T250418', qty: 15, uom: 'g',
      scenario: '其他', reason: '检测方法开发（已取消，原因：改用对照品）。', dept: 'QC 检验室',
      applicant: '王敏', applicantDate: '2026-07-15', status: '已取消',
      signedBy: { inventory: { who: '赵磊', at: '2026-07-15' }, qc: { who: '李静', at: '2026-07-16' } },
      currentQty: 150, reservedQty: 0,
    },
  ]
}

// 构建展示用审批链（供详情面板渲染）
export function usageChainSteps(a: UsageApply): { key: UsageStepKey | 'applicant'; label: string; who: string; state: 'done' | 'active' | 'todo' }[] {
  const order: (UsageStepKey | 'applicant')[] = ['applicant', 'inventory', 'qc', 'qa', 'qm']
  // 当前激活步骤
  const activeKey = (() => {
    switch (a.status) {
      case '草稿': case '待库存确认': return 'inventory'
      case '待QC批准': return 'qc'
      case '待QA批准': return 'qa'
      case '待QM批准': return 'qm'
      default: return null
    }
  })()
  return order.map((key) => {
    if (key === 'applicant') {
      return { key, label: '申请人', who: `${a.applicant} · ${a.applicantDate}`, state: 'done' as const }
    }
    const sig = a.signedBy[key]
    const done = !!sig
    const active = activeKey === key && a.status !== '草稿'
    return {
      key, label: USAGE_STEP_LABEL[key],
      who: done ? `${sig!.who} · ${sig!.at}${key === 'inventory' ? ` · 预占 ${a.qty} ${a.uom}` : ''}` : (active ? '当前步骤' : '待审批'),
      state: done ? 'done' as const : (active ? 'active' as const : 'todo' as const),
    }
  })
}

// 前端推进一档（演示）：将使用申请从 status 走到下一审批/执行状态
export function advanceUsage(a: UsageApply): UsageApply {
  const who = demoPerson()
  const today = '2026-09-07'
  const key = usageNextStepKey(a.status)
  if (key) a.signedBy[key] = { who, at: today }
  if (a.status === '草稿') a.status = '待库存确认'
  else if (a.status === '待库存确认') a.status = '待QC批准'
  else if (a.status === '待QC批准') a.status = '待QA批准'
  else if (a.status === '待QA批准') a.status = '待QM批准'
  else if (a.status === '待QM批准') { a.status = '已批准' }
  else if (a.status === '已批准') { a.status = '已执行' }
  return a
}
function usageNextStepKey(s: UsageStatus): UsageStepKey | null {
  if (s === '草稿' || s === '待库存确认') return 'inventory'
  if (s === '待QC批准') return 'qc'
  if (s === '待QA批准') return 'qa'
  if (s === '待QM批准') return 'qm'
  return null
}

// ---------- 处理申请 ----------
export type DisposalType = '期满销毁' | '期满续留' | '其他'
export type DisposalStatus =
  | '草稿' | '待QC主管审核' | '待QC负责人审核' | '待QA审核' | '待QM批准'
  | '已批准' | '待执行' | '已销毁' | '已完成续留' | '已驳回' | '已取消' | '销毁超期'

export type DisposalStepKey = 'qc_sup' | 'qc_lead' | 'qa_review' | 'qa_lead' | 'qm'
export const DISPOSAL_STEP_LABEL: Record<DisposalStepKey, string> = {
  qc_sup: 'QC 主管审核',
  qc_lead: 'QC 负责人审核',
  qa_review: 'QA 审核',
  qa_lead: 'QA 负责人审核',
  qm: 'QM 批准',
}

export interface DisposalApply {
  name: string
  retentionName: string
  product: string
  batch: string
  category: string
  dueDate: string
  type: DisposalType
  reason: string
  method: string
  location: string
  applicant: string
  applicantDate: string
  qaManagerRequired: boolean // true=5 级；false=4 级（跳过 QA 负责人）
  status: DisposalStatus
  signedBy: Partial<Record<DisposalStepKey, { who: string; at: string }>>
  qty: number
  uom: string
  currentQty: number
  reservedQty: number
  deadline: string
  newDueDate: string
  handler: string
  supervisor: string
}

export function disposalLevelLabel(a: DisposalApply): string {
  return a.qaManagerRequired ? '5 级' : '4 级（跳过 QA 负责人）'
}

export function seedDisposalApplies(): DisposalApply[] {
  const base = {
    applicant: '王敏', applicantDate: '2026-09-06', reason: '留样期届满按规程处理。',
    method: '高温焚烧', location: '危废暂存间（QA 现场监督）', currentQty: 0, reservedQty: 0, deadline: '', newDueDate: '', handler: '', supervisor: '',
    signedBy: {} as DisposalApply['signedBy'],
  }
  return [
    {
      ...base, name: 'HBOS-RET-DSP-2026-00010', retentionName: 'TEST-HBOS-M2-RET-2023-00003',
      product: 'TEST 原料A', batch: 'T230612', category: '关键物料', dueDate: '2026-09-18',
      type: '期满销毁', qaManagerRequired: true, status: '待QC主管审核', qty: 120, uom: 'g', currentQty: 120,
    },
    {
      ...base, name: 'HBOS-RET-DSP-2026-00011', retentionName: 'TEST-HBOS-M2-RET-2026-00003',
      product: 'TEST 外售产品B', batch: 'T260715', category: '外售产品', dueDate: '2026-09-30',
      type: '期满销毁', qaManagerRequired: false, status: '草稿', qty: 2, uom: '瓶', currentQty: 2,
      applicant: '李静',
    },
    {
      ...base, name: 'HBOS-RET-DSP-2026-00009', retentionName: 'TEST-HBOS-M2-RET-2022-00011',
      product: 'TEST 外售产品B', batch: 'T220528', category: '外售产品', dueDate: '2026-08-13',
      type: '期满销毁', qaManagerRequired: true, status: '销毁超期', qty: 6, uom: '瓶', currentQty: 6,
      deadline: '2025-11-13',
      signedBy: {
        qc_sup: { who: '孙晓', at: '2025-08-10' }, qc_lead: { who: '赵磊', at: '2025-08-11' },
        qa_review: { who: '李静', at: '2025-08-11' }, qm: { who: '张总', at: '2025-08-13' },
      },
    },
    {
      ...base, name: 'HBOS-RET-DSP-2026-00008', retentionName: 'TEST-HBOS-M2-RET-2023-00001',
      product: 'TEST 原料A', batch: 'T230415', category: '关键物料', dueDate: '2026-09-05',
      type: '期满销毁', qaManagerRequired: false, status: '待执行', qty: 120, uom: 'g', currentQty: 120,
      deadline: '2026-10-01',
      signedBy: {
        qc_sup: { who: '孙晓', at: '2026-07-01' }, qc_lead: { who: '赵磊', at: '2026-07-01' },
        qa_review: { who: '李静', at: '2026-07-01' }, qm: { who: '张总', at: '2026-07-01' },
      },
      handler: '待签名', supervisor: '待签名',
    },
    {
      ...base, name: 'HBOS-RET-DSP-2026-00006', retentionName: 'TEST-HBOS-M2-RET-2023-00009',
      product: 'TEST 成品片剂A', batch: 'T230901', category: '成品（原料药）', dueDate: '2026-09-01',
      type: '期满续留', qaManagerRequired: true, status: '已完成续留', qty: 200, uom: 'g', currentQty: 200,
      newDueDate: '2029-09-01',
      signedBy: {
        qc_sup: { who: '孙晓', at: '2026-08-20' }, qc_lead: { who: '赵磊', at: '2026-08-20' },
        qa_review: { who: '刘洋', at: '2026-08-21' }, qa_lead: { who: '刘洋', at: '2026-08-21' },
        qm: { who: '张总', at: '2026-08-22' },
      },
      handler: '王敏', supervisor: '刘洋',
    },
  ]
}

// 处理申请当前需要的角色动作
export function disposalActionNeeded(status: DisposalStatus): string | null {
  if (status === '草稿') return 'disposal_create' // 提交即进入待QC主管（演示以申请人提交）
  if (status === '待QC主管审核' || status === '待QC负责人审核') return 'disposal_qclevel'
  if (status === '待QA审核') return 'disposal_qalevel'
  if (status === '待QM批准') return 'disposal_qm'
  if (status === '待执行') return 'disposal_execute'
  return null
}

export function disposalChainSteps(d: DisposalApply): { key: DisposalStepKey | 'applicant'; label: string; who: string; state: 'done' | 'active' | 'todo' | 'skipped' }[] {
  const skipQaLead = !d.qaManagerRequired
  const order: DisposalStepKey[] = ['qc_sup', 'qc_lead', 'qa_review', 'qa_lead', 'qm']
  const activeKey = (() => {
    switch (d.status) {
      case '草稿': return 'qc_sup'
      case '待QC主管审核': return 'qc_sup'
      case '待QC负责人审核': return 'qc_lead'
      case '待QA审核': return 'qa_review'
      case '待QM批准': return 'qm'
      default: return null
    }
  })()
  const steps: { key: DisposalStepKey | 'applicant'; label: string; who: string; state: 'done' | 'active' | 'todo' | 'skipped' }[] = [
    { key: 'applicant', label: '申请人', who: `${d.applicant} · ${d.applicantDate}`, state: 'done' },
  ]
  for (const key of order) {
    if (key === 'qa_lead' && skipQaLead) {
      steps.push({ key, label: DISPOSAL_STEP_LABEL[key], who: '审批层跳过', state: 'skipped' })
      continue
    }
    const sig = d.signedBy[key]
    const done = !!sig
    const active = activeKey === key && d.status !== '草稿'
    steps.push({
      key,
      label: DISPOSAL_STEP_LABEL[key],
      who: done ? `${sig!.who} · ${sig!.at}` : (active ? '当前步骤' : '待审批'),
      state: done ? 'done' : (active ? 'active' : 'todo'),
    })
  }
  return steps
}

// 前端推进一档（演示）：销毁申请审批推进；到 QM 后置已批准+deadline（QM 日期 +3 个月）
export function advanceDisposal(d: DisposalApply): DisposalApply {
  const who = demoPerson()
  const today = '2026-09-07'
  const key = disposalNextStepKey(d.status)
  if (key) d.signedBy[key] = { who, at: today }
  if (d.status === '草稿') d.status = '待QC主管审核'
  else if (d.status === '待QC主管审核') d.status = '待QC负责人审核'
  else if (d.status === '待QC负责人审核') d.status = '待QA审核'
  else if (d.status === '待QA审核') d.status = '待QM批准'
  else if (d.status === '待QM批准') {
    d.status = d.type === '期满销毁' ? '待执行' : '已批准'
    if (d.type === '期满销毁') {
      const qm = d.signedBy.qm
      const base = qm ? new Date(qm.at) : new Date()
      base.setMonth(base.getMonth() + 3)
      d.deadline = base.toISOString().slice(0, 10)
    }
  }
  return d
}
function disposalNextStepKey(s: DisposalStatus): DisposalStepKey | null {
  if (s === '草稿') return 'qc_sup'
  if (s === '待QC主管审核') return 'qc_sup'
  if (s === '待QC负责人审核') return 'qc_lead'
  if (s === '待QA审核') return 'qa_review'
  if (s === '待QM批准') return 'qm'
  return null
}

// 完成销毁双签
export function executeDisposal(d: DisposalApply, handler: string, supervisor: string): DisposalApply {
  d.handler = handler
  d.supervisor = supervisor
  d.status = d.type === '期满销毁' ? '已销毁' : '已完成续留'
  return d
}

// ---------- 季度到期清单（留样台账推导） ----------
export interface QuarterRow {
  retentionName: string
  product: string
  batch: string
  category: string
  dueDate: string
  remainDays: number
  state: '在库' | '临期' | '已批准待执行' | '销毁超期' | '已完成'
  suggestion: string
  disposalName?: string
}

export function seedQuarterRows(): QuarterRow[] {
  return [
    { retentionName: 'TEST-HBOS-M2-RET-2023-00003', product: 'TEST 原料A', batch: 'T230612', category: '关键物料', dueDate: '2026-09-18', remainDays: 11, state: '临期', suggestion: '发起处理申请' },
    { retentionName: 'TEST-HBOS-M2-RET-2023-00001', product: 'TEST 原料A', batch: 'T230415', category: '关键物料', dueDate: '2026-09-05', remainDays: -2, state: '已批准待执行', suggestion: '销毁双签后完成', disposalName: 'HBOS-RET-DSP-2026-00008' },
    { retentionName: 'TEST-HBOS-M2-RET-2022-00011', product: 'TEST 外售产品B', batch: 'T220528', category: '外售产品', dueDate: '2026-08-13', remainDays: -25, state: '销毁超期', suggestion: 'Manager 决策', disposalName: 'HBOS-RET-DSP-2026-00009' },
    { retentionName: 'TEST-HBOS-M2-RET-2023-00009', product: 'TEST 成品片剂A', batch: 'T230901', category: '成品（原料药）', dueDate: '2026-09-01', remainDays: -6, state: '已完成', suggestion: '已完成续留至 2029-09-01' },
    { retentionName: 'TEST-HBOS-M2-RET-2024-00002', product: 'TEST 原料A', batch: 'T240518', category: '关键物料', dueDate: '2027-05-18', remainDays: 253, state: '在库', suggestion: '下季度到期处理' },
  ]
}
