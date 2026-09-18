// ============================================================
// 稳定性板块演示数据
//
// 说明：仅服务**尚未接入后端**的 3 个视图（结果与趋势 / 报告与有效期 /
// 变更·稳定性室·设备），其后端接口属 R8C / R8D。
// 数据全部为 `TEST-HBOS-M2-STB-*` 前缀虚构演示数据，不接真实 API。
//
// 「稳定性工作台」「考察申请与方案」已于 R8G、「样品入箱与台账」「取样与检测计划」
// 已于 R8H 接入真实后端（见 src/api/stability.ts），其演示数据已从此文件移除。
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


export interface RiskItem {
  tone: Tone
  title: string
  sub: string
  tag: string
}

// ============================================================
// 1. 结果录入与趋势
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
// 2. 报告与有效期
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
// 3. 变更 / 稳定性室 / 设备
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

