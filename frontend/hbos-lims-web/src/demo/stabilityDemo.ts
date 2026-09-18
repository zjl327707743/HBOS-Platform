// ============================================================
// 稳定性板块演示数据
//
// 说明：仅服务**尚未接入后端**的 5 个视图（样品入箱 / 取样与检测计划 /
// 结果与趋势 / 报告与有效期 / 变更·稳定性室·设备），其后端接口属 R8B~R8D。
// 数据全部为 `TEST-HBOS-M2-STB-*` 前缀虚构演示数据，不接真实 API。
//
// 「稳定性工作台」与「考察申请与方案」两视图已于 R8G 接入真实后端
// （见 src/api/stability.ts），其演示数据已从此文件移除。
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

// ---- 共享类型（其余视图仍在用） ----

export interface Kpi {
  label: string
  value: string
  unit?: string
  hint: string
  tone: Tone
  icon: 'calendar' | 'pen' | 'alert' | 'shield'
}

export interface RiskItem {
  tone: Tone
  title: string
  sub: string
  tag: string
}

// ============================================================
// 1. 样品入箱与台账
// ============================================================

export const SAMPLE_KPIS: Kpi[] = [
  { label: '在箱样品', value: '46', unit: '个', hint: '当前有效', tone: 'pass', icon: 'shield' },
  { label: '本月入箱', value: '9', unit: '个', hint: '较上月 +2', tone: 'pass', icon: 'pen' },
  { label: '强制评估', value: '2', unit: '个', hint: '入箱超过 1 个月', tone: 'warn', icon: 'alert' },
  { label: '待处置', value: '1', unit: '个', hint: '需要 QA 复核', tone: 'danger', icon: 'alert' },
]

export interface SampleRow {
  name: string
  product: string
  batch: string
  form: string
  condition: string
  room: string
  inDate: string
  qty: string
  status: string
  statusTone: Tone
  eval: string
  evalTone: Tone
  /** 详情抽屉用 */
  log: { action: string; delta: string; meta: string }[]
}

export const SAMPLES: SampleRow[] = [
  {
    name: 'TEST-HBOS-M2-STB-SMP-00021', product: 'TEST 片剂 A', batch: 'T260901', form: '片剂',
    condition: '长期', room: 'STB-RM-01', inDate: '2026-09-03', qty: '18 盒',
    status: '在箱', statusTone: 'pass', eval: '无需', evalTone: 'muted',
    log: [{ action: '入箱', delta: '+18 盒', meta: '2026-09-03 · 陈 QC · STB-RM-01' }],
  },
  {
    name: 'TEST-HBOS-M2-STB-SMP-00020', product: 'TEST 原料 B', batch: 'RM260601', form: '原料药',
    condition: '加速', room: 'STB-RM-02', inDate: '2026-08-01', qty: '12 瓶',
    status: '部分取样', statusTone: 'info', eval: '强制评估', evalTone: 'warn',
    log: [
      { action: '入箱', delta: '+12 瓶', meta: '2026-08-01 · 陈 QC · STB-RM-02' },
      { action: '取样', delta: '-2 瓶', meta: '2026-09-01 · 赵 QC · M1' },
    ],
  },
  {
    name: 'TEST-HBOS-M2-STB-SMP-00019', product: 'TEST 胶囊 C', batch: 'C260301', form: '胶囊剂',
    condition: '中间', room: 'STB-RM-03', inDate: '2026-07-12', qty: '8 盒',
    status: '待处理', statusTone: 'warn', eval: '已评估', evalTone: 'muted',
    log: [
      { action: '入箱', delta: '+10 盒', meta: '2026-07-12 · 陈 QC · STB-RM-03' },
      { action: '取样', delta: '-2 盒', meta: '2026-08-20 · 赵 QC · M3' },
    ],
  },
  {
    name: 'TEST-HBOS-M2-STB-SMP-00018', product: 'TEST 注射剂 D', batch: 'D260501', form: '注射剂',
    condition: '长期', room: 'STB-RM-01', inDate: '2026-05-10', qty: '6 瓶',
    status: '在箱', statusTone: 'pass', eval: '无需', evalTone: 'muted',
    log: [{ action: '入箱', delta: '+6 瓶', meta: '2026-05-10 · 陈 QC · STB-RM-01' }],
  },
]

// ============================================================
// 2. 取样与检测计划
// ============================================================

export interface ScheduleRow {
  product: string
  condition: string
  batch: string
  /** 本行时间点覆盖的执行状态（供看板「执行状态」筛选） */
  states: string[]
  /** 7 个计划格（对应 PLAN_DAYS），空串表示无时间点 */
  cells: { point?: string; tone?: Tone }[]
}

export const SCHEDULE_ROWS: ScheduleRow[] = [
  {
    product: 'TEST 片剂 A', condition: '长期', batch: 'T260901',
    states: ['待取样', '检测中'],
    cells: [{}, { point: 'M3', tone: 'warn' }, {}, {}, {}, {}, { point: 'M6' }],
  },
  {
    product: 'TEST 原料 B', condition: '加速', batch: 'RM260601',
    states: ['检测中'],
    cells: [{}, {}, { point: 'M3' }, { point: '延期', tone: 'danger' }, {}, {}, {}],
  },
  {
    product: 'TEST 胶囊 C', condition: '中间', batch: 'C260301',
    states: ['待取样'],
    cells: [{}, {}, {}, {}, {}, { point: 'M12' }, {}],
  },
]

export const DATE_CHAIN = {
  name: 'TEST-STB-T260901-AC-06 · M3',
  status: '延期审批中',
  fields: [
    { label: '计划检测日', value: '2026-09-16' },
    { label: '申请日期', value: '2026-09-15' },
    { label: '有效截止日', value: '2026-09-18' },
    { label: '政策硬上限', value: '2026-09-20' },
    { label: '实际取样日', value: '未登记' },
    { label: '检测窗口', value: '计划日后 30 天内', mono: false },
  ],
  note: '日期链校验：planned ≤ requested ≤ approved ≤ policy_latest。当前审批日期未落库，因此有效截止日仍按原计划口径展示。',
}

export const WEEK_DUE: { point: string; product: string; due: string; status: string; tone: Tone }[] = [
  { point: 'M3 / 03', product: 'TEST 片剂 A', due: '09-18', status: '临近', tone: 'warn' },
  { point: 'M6 / 02', product: 'TEST 原料 B', due: '09-19', status: '检测中', tone: 'info' },
  { point: 'M12 / 01', product: 'TEST 胶囊 C', due: '09-21', status: '正常', tone: 'pass' },
]

/** 计划台账：每行必须同时给出计划检测日 / 有效截止日 / 政策硬上限 / 延期状态 / 检测窗口 */
export interface ScheduleLedgerRow {
  point: string
  product: string
  batch: string
  condition: string
  planned: string
  effective: string
  policyLatest: string
  delay: string
  delayTone: Tone
  sampleDate: string
  status: string
  statusTone: Tone
}

export const SCHEDULE_LEDGER: ScheduleLedgerRow[] = [
  {
    point: 'M3 / 03', product: 'TEST 片剂 A', batch: 'T260901', condition: '长期',
    planned: '2026-09-16', effective: '2026-09-18', policyLatest: '2026-09-20',
    delay: '审批中', delayTone: 'warn', sampleDate: '未登记', status: '待取样', statusTone: 'warn',
  },
  {
    point: 'M6 / 02', product: 'TEST 原料 B', batch: 'RM260601', condition: '加速',
    planned: '2026-09-18', effective: '2026-09-18', policyLatest: '2026-09-25',
    delay: '无', delayTone: 'muted', sampleDate: '2026-09-18', status: '检测中', statusTone: 'info',
  },
  {
    point: 'M12 / 01', product: 'TEST 胶囊 C', batch: 'C260301', condition: '中间',
    planned: '2026-09-21', effective: '2026-09-21', policyLatest: '2026-10-01',
    delay: '无', delayTone: 'muted', sampleDate: '未登记', status: '正常', statusTone: 'pass',
  },
  {
    point: 'M6 / 01', product: 'TEST 注射剂 D', batch: 'D260501', condition: '长期',
    planned: '2026-09-08', effective: '2026-09-08', policyLatest: '2026-09-15',
    delay: '已批准', delayTone: 'pass', sampleDate: '2026-09-10', status: '已完成', statusTone: 'pass',
  },
]

/** 延期审批：申请与批准是独立动作，申请不等同已顺延 */
export interface DelayApplyRow {
  name: string
  point: string
  product: string
  delayType: string
  planned: string
  requested: string
  approved: string
  policyLatest: string
  status: string
  statusTone: Tone
  applicant: string
}

export const DELAY_APPLIES: DelayApplyRow[] = [
  {
    name: 'TEST-HBOS-M2-STB-DLY-0003', point: 'M3 / 03', product: 'TEST 片剂 A', delayType: '取样延期',
    planned: '2026-09-16', requested: '2026-09-17', approved: '—', policyLatest: '2026-09-20',
    status: '待 QA Manager 审批', statusTone: 'warn', applicant: '陈 QC · 2026-09-15',
  },
  {
    name: 'TEST-HBOS-M2-STB-DLY-0002', point: 'M6 / 01', product: 'TEST 注射剂 D', delayType: '检测延期',
    planned: '2026-09-08', requested: '2026-09-10', approved: '2026-09-10', policyLatest: '2026-09-15',
    status: '已批准', statusTone: 'pass', applicant: '赵 QC · 2026-09-05',
  },
  {
    name: 'TEST-HBOS-M2-STB-DLY-0001', point: 'M1 / 02', product: 'TEST 原料 B', delayType: '取样延期',
    planned: '2026-08-12', requested: '2026-08-14', approved: '—', policyLatest: '2026-08-18',
    status: '已驳回', statusTone: 'muted', applicant: '陈 QC · 2026-08-10',
  },
]


// ============================================================
// 3. 结果录入与趋势
// ============================================================

export interface ResultItem {
  id: string
  title: string
  sub: string
  status: string
  tone: Tone
  /** 中部表单 */
  form: {
    title: string
    ref: string
    version: string
    versionStatus: string
    versionTone: Tone
    currentResult: string
    specSnapshot: string
    changeRule: string
    baseline: string
    value: string
    unit: string
    verdict: string
    testDate: string
    remark: string
  }
  /** 右侧趋势（当前生效值 + 在途预览） */
  trend: { label: string; effective: number | null; inflight: number | null }[]
}

export const RESULT_ITEMS: ResultItem[] = [
  {
    id: 'TEST-HBOS-M2-STB-RES-0008',
    title: 'TEST 片剂 A · M3',
    sub: 'T260901 · 2026-09-16 · 4/8 项已录入',
    status: '显著变化候选', tone: 'warn',
    form: {
      title: 'TEST 片剂 A · M3 · 含量',
      ref: 'TEST-HBOS-M2-STB-RES-0008',
      version: '结果版本 v1',
      versionStatus: '草稿',
      versionTone: 'warn',
      currentResult: '98.6 % · v0 · 2026-06-16',
      specSnapshot: 'SPEC-TAB-A v3 · 90.0–110.0 %',
      changeRule: '相对基线变化超过 5%',
      baseline: '0 月放行结果 · 已关联',
      value: '94.1',
      unit: '%',
      verdict: '显著变化候选',
      testDate: '2026-09-16',
      remark: '相对 0 月基线 98.6% 下降 4.56%，接近阈值；待复核确认。',
    },
    trend: [
      { label: 'M0', effective: 98.6, inflight: null },
      { label: 'M1', effective: 96.0, inflight: null },
      { label: 'M3', effective: 94.7, inflight: null },
      { label: 'M6', effective: 92.9, inflight: null },
      { label: 'M9', effective: 91.6, inflight: null },
      { label: 'M12', effective: null, inflight: 86.2 },
    ],
  },
  {
    id: 'TEST-HBOS-M2-STB-RES-0007',
    title: 'TEST 原料 B · M1',
    sub: 'RM260601 · 2026-09-12 · 3/5 项已录入',
    status: '检测中', tone: 'info',
    form: {
      title: 'TEST 原料 B · M1 · 有关物质',
      ref: 'TEST-HBOS-M2-STB-RES-0007',
      version: '结果版本 v0',
      versionStatus: '草稿',
      versionTone: 'muted',
      currentResult: '0.12 % · v0 · 2026-06-12',
      specSnapshot: 'SPEC-RM-B v2 · ≤ 0.30 %',
      changeRule: '绝对变化超过 0.05%',
      baseline: '0 月放行结果 · 已关联',
      value: '',
      unit: '%',
      verdict: '符合趋势',
      testDate: '2026-09-12',
      remark: '',
    },
    trend: [
      { label: 'M0', effective: 0.12, inflight: null },
      { label: 'M1', effective: 0.14, inflight: null },
      { label: 'M3', effective: 0.15, inflight: null },
      { label: 'M6', effective: null, inflight: null },
    ],
  },
  {
    id: 'TEST-HBOS-M2-STB-RES-0006',
    title: 'TEST 胶囊 C · M12',
    sub: 'C260301 · 2026-09-10 · 5/5 项已录入',
    status: '待复核', tone: 'info',
    form: {
      title: 'TEST 胶囊 C · M12 · 溶出度',
      ref: 'TEST-HBOS-M2-STB-RES-0006',
      version: '结果版本 v0',
      versionStatus: '待复核',
      versionTone: 'info',
      currentResult: '92.4 % · v0 · 2025-09-10',
      specSnapshot: 'SPEC-CAP-C v1 · ≥ 80.0 %',
      changeRule: '相对基线变化超过 5%',
      baseline: '0 月放行结果 · 已关联',
      value: '90.8',
      unit: '%',
      verdict: '符合趋势',
      testDate: '2026-09-10',
      remark: '按计划完成 12 月取样，结果符合趋势带。',
    },
    trend: [
      { label: 'M0', effective: 95.1, inflight: null },
      { label: 'M3', effective: 94.2, inflight: null },
      { label: 'M6', effective: 93.5, inflight: null },
      { label: 'M9', effective: 92.9, inflight: null },
      { label: 'M12', effective: 92.4, inflight: null },
    ],
  },
  {
    id: 'TEST-HBOS-M2-STB-RES-0005',
    title: 'TEST 注射剂 D · M6',
    sub: 'D260501 · 2026-09-08 · 6/6 项已录入',
    status: '已完成', tone: 'pass',
    form: {
      title: 'TEST 注射剂 D · M6 · 含量',
      ref: 'TEST-HBOS-M2-STB-RES-0005',
      version: '结果版本 v0',
      versionStatus: '已批准',
      versionTone: 'pass',
      currentResult: '99.2 % · v0 · 2026-03-08',
      specSnapshot: 'SPEC-INJ-D v1 · 95.0–105.0 %',
      changeRule: '相对基线变化超过 5%',
      baseline: '0 月放行结果 · 已关联',
      value: '99.0',
      unit: '%',
      verdict: '符合趋势',
      testDate: '2026-09-08',
      remark: '6 月时间点全部项目完成，趋势平稳。',
    },
    trend: [
      { label: 'M0', effective: 99.4, inflight: null },
      { label: 'M3', effective: 99.1, inflight: null },
      { label: 'M6', effective: 99.2, inflight: null },
    ],
  },
]

export const COUNTDOWN = {
  label: '显著变化评估剩余工作日',
  value: '04 天 06:18:42',
  deadline: '截止：2026-09-22 18:00 · 评估人：QA Manager',
}

export const TREND_NOTE =
  '在途版本 v1 预计低于当前趋势带。结果批准前不切换 is_current，也不影响当前趋势图。'

// ============================================================
// 4. 报告与有效期
// ============================================================

export interface ReportRow {
  name: string
  status: string
  tone: Tone
  product: string
  type: string
  period: string
}

export const REPORTS: ReportRow[] = [
  { name: 'STB-RPT-2026-0004', status: '待批准', tone: 'info', product: 'TEST 片剂 A', type: '阶段性报告', period: '研究期：0–6 月 · v1' },
  { name: 'STB-RPT-2026-0003', status: '已批准', tone: 'pass', product: 'TEST 原料 B', type: '年度持续报告', period: '研究期：0–12 月 · v1' },
  { name: 'STB-RPT-2026-0002', status: '待审核', tone: 'warn', product: 'TEST 胶囊 C', type: '阶段性报告', period: '研究期：0–3 月 · v2' },
]

export const REPORT_DETAIL = {
  name: 'STB-RPT-2026-0004',
  stats: [
    { label: '时间点', value: '4 / 6' },
    { label: '项目', value: '8 项' },
    { label: '显著变化', value: '1 项', danger: true },
    { label: '有效期', value: '建议复核' },
  ],
  fields: [
    { label: '产品', value: 'TEST 片剂 A', mono: false },
    { label: '批次', value: 'T260901 / T260902 / T260903', mono: true },
    { label: '报告周期', value: '2026-01—2026-09', mono: false },
    { label: '审核人', value: '赵 QC · 2026-09-15', mono: false },
    { label: '批准人', value: '林质检 · 待执行', mono: false },
    { label: '来源版本', value: 'Protocol v2 / Result v1', mono: true },
  ],
  flow: [
    { label: '草稿', state: 'done' as const },
    { label: '审核完成', state: 'done' as const },
    { label: '待批准', state: 'current' as const },
    { label: '已批准', state: 'todo' as const },
  ],
  note: '批准前检查：审核人和批准人不得为同一人；报告中显著变化项目必须完成 QA 评估；批准后报告快照与版本链锁定。',
  /** 详情抽屉：批准前硬前置 */
  blockers: [
    { done: true, title: '审核已完成', desc: '赵 QC · 2026-09-15' },
    { done: true, title: '审核人与批准人不同', desc: '当前批准人：林质检' },
    { done: false, title: '显著变化评估', desc: '含量 M3 仍有 1 项候选待说明' },
  ],
}

export const EXTRAPOLATION = {
  product: 'TEST 片剂 A',
  title: 'TEST 片剂 A · 预计有效期建议',
  desc: '基于当前已批准时间点、结果趋势和规格冻结快照生成的辅助判断；仍需 QA 依据规程做最终判定。',
  boxes: [
    { label: '建议区间', value: '18–24 个月', tone: 'pass' as Tone },
    { label: '置信提示', value: '需复核 1 项', tone: 'warn' as Tone },
    { label: '趋势斜率', value: '轻度下降', tone: 'pass' as Tone },
    { label: '数据完整性', value: '可追溯', tone: 'pass' as Tone },
  ],
  todo: '待处理：含量 M3 在途版本 v1 为显著变化候选；批准报告前需完成评估或说明。',
}

// ============================================================
// 5. 变更 / 稳定性室 / 设备
// ============================================================

export interface ChangeRow {
  name: string
  scope: string
  scopeSub: string
  status: string
  tone: Tone
  owner: string
  type: string
  impactProduct: string
  impactPoints: string
  landing: { title: string; desc: string }[]
}

export const CHANGES: ChangeRow[] = [
  {
    name: 'STB-CHG-2026-0003', scope: '包装材料变更 → 方案 v3', scopeSub: '影响 2 个产品 / 18 个时间点',
    status: '待实施', tone: 'info', owner: '林质检', type: '包装材料变更',
    impactProduct: '2 个', impactPoints: '18 个',
    landing: [
      { title: '生成 Protocol 新版本', desc: '旧版冻结快照保持可追溯' },
      { title: '重新评估受影响条件', desc: '不覆盖已有实际记录' },
    ],
  },
  {
    name: 'STB-CHG-2026-0002', scope: '稳定性室调整 → 追加条件', scopeSub: '影响 STB-RM-02',
    status: '后评估', tone: 'warn', owner: '陈 QA', type: '稳定性室调整',
    impactProduct: '1 个', impactPoints: '6 个',
    landing: [
      { title: '追加时间点', desc: '锁内按 sample_cond_point_key 幂等仅新增' },
      { title: '后评估记录', desc: '后评估不通过为终态，另立新变更单' },
    ],
  },
]

export const CHANGE_HINTS: RiskItem[] = [
  { tone: 'info', title: '涉方案变更', sub: '实施后生成 Protocol 新版本，旧版本保留冻结快照', tag: '' },
  { tone: 'warn', title: '涉条件变更', sub: '实施后追加时间点，不覆盖已有实际记录', tag: '' },
  { tone: 'danger', title: '后评估不通过', sub: '作为终态，后续另立新变更单', tag: '' },
]

export interface RoomCard {
  name: string
  label: string
  limits: string
  temperature: string
  humidity: string
  over: boolean
  note: string
  noteTone: Tone
}

export const ROOMS: RoomCard[] = [
  { name: 'STB-RM-01', label: '长期室', limits: '房间上限：25±2℃ / 60±5%RH', temperature: '24.8', humidity: '58.2', over: false, note: '最近记录：2026-09-15 09:00 · 陈 QC', noteTone: 'muted' },
  { name: 'STB-RM-02', label: '加速室', limits: '房间上限：26℃ / 70%RH', temperature: '27.1', humidity: '68.4', over: true, note: '超限待评估 · 2026-09-14 14:00', noteTone: 'danger' },
]

export const ROOM_INTEGRITY = { rate: 98.6, expected: 152, missing: 2 }

export const ROOM_READINGS: { time: string; room: string; temperature: string; humidity: string; recorder: string; status: string; tone: Tone; over: boolean }[] = [
  { time: '2026-09-15 09:00', room: 'STB-RM-01', temperature: '24.8℃', humidity: '58.2%RH', recorder: '陈 QC', status: '正常', tone: 'pass', over: false },
  { time: '2026-09-14 14:00', room: 'STB-RM-02', temperature: '27.1℃', humidity: '68.4%RH', recorder: '赵 QC', status: '超限', tone: 'danger', over: true },
]

export interface EquipmentRow {
  name: string
  label: string
  sub: string
  status: string
  tone: Tone
}

export const EQUIPMENT: EquipmentRow[] = [
  { name: 'STB-EQP-001', label: '恒温恒湿箱 A', sub: 'STB-RM-01 · 校准有效至 2026-12-31', status: '正常', tone: 'pass' },
  { name: 'STB-EQP-002', label: '恒温恒湿箱 B', sub: 'STB-RM-02 · 校准有效至 2026-10-30', status: '临近', tone: 'warn' },
  { name: 'STB-EQP-003', label: '光照箱 C', sub: 'STB-RM-03 · 故障工单 STB-FLT-0002', status: '故障', tone: 'danger' },
]

export const FAULT = {
  name: 'STB-FLT-2026-0002',
  title: 'STB-FLT-2026-0002 · 光照箱 C 温控异常',
  sub: '影响 1 个条件、4 个样品、6 个待执行时间点',
  fields: [
    { label: '设备', value: 'STB-EQP-003' },
    { label: '故障状态', value: '待处理' },
    { label: '影响房间', value: 'STB-RM-03' },
    { label: '影响样品', value: '4 个' },
    { label: '影响时间点', value: '6 个' },
    { label: '责任人', value: '陈 QA' },
  ],
  checklist: [
    { done: false, title: '完成样品影响评估', desc: '尚未完成' },
    { done: false, title: 'QA 处置意见', desc: '尚未填写' },
  ],
  note: '关闭故障前需完成样品影响评估和 QA 处置意见；设备状态不由前端直接修改。',
}

