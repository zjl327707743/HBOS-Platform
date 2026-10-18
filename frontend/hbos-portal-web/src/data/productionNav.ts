/**
 * 生产看板的导航与行定义（前端资产）。
 *
 * 同 `inventoryNav.ts` 的定位：这份清单由**前端自己维护**，不是后端投影。
 * 生产看板与 Frappe 无关（Owner 2026-09-29 口径），它的导航与行定义天然属于前端。
 *
 * 行定义（`PRODUCTION_ROWS`）是**数据驱动的关键**：
 * 会议（2026-10-02）定「按现有在产产品纳入统计，后续新增产品可直接补充」，
 * 所以看板的 6 行不是写死在模板里，而是由这里 + 取数结果共同决定。
 */

/** 看板两个页面（与原型的两张页一致）。 */
export const PRODUCTION_BASELINE_PATH = '/hbos/production'
export const PRODUCTION_CENTER_PATH = '/hbos/production/center'

export interface ProductionNavItem {
  id: string
  label: string
  icon: string
  stablePath: string
}

export interface ProductionNavGroup {
  label: string
  items: ProductionNavItem[]
}

/**
 * 侧边栏分组。
 *
 * 现阶段只有两张看板，所以只有一组——不预置空菜单
 * （同 P4 生产看板视觉方案 §4.6 的取舍）。
 */
export const PRODUCTION_NAV_GROUPS: ProductionNavGroup[] = [
  {
    label: '工作台',
    items: [
      { id: 'baseline', label: '基层管理人员看板', icon: 'DashboardOutlined', stablePath: PRODUCTION_BASELINE_PATH },
      { id: 'center', label: '生产管理中心看板', icon: 'LineChartOutlined', stablePath: PRODUCTION_CENTER_PATH },
    ],
  },
]

/**
 * 看板行的**组成口径**（会议 + Owner 2026-10-02 确认）。
 *
 * `members` 是「哪些产品名算作这一行」—— 合并规则就落在这里：
 *   - F13 = 国内规范粗品 + 美罗培南粗品B + 美罗培南粗品C
 *   - 无菌美罗培南 = 无菌车间的美罗培南族（排除混粉 / 晶种 / USP）
 *   - 无菌亚胺培南 = 无菌车间的亚胺培南族
 *
 * ⚠️ 成员名必须与飞书表 `产量明细数据-*` 的产品名**逐字一致**，
 *    否则该成员会被静默漏掉（取数服务按名匹配）。
 */
export interface ProductionRowSpec {
  /** 看板显示的行名。 */
  label: string
  /** 计入本行的产品名（取自产量明细数据-*）。 */
  members: string[]
}

export const PRODUCTION_ROWS: ProductionRowSpec[] = [
  { label: '4BMA', members: ['4BMA'] },
  { label: 'F9', members: ['F9'] },
  { label: 'F12', members: ['F12'] },
  {
    label: 'F13',
    members: ['国内规范粗品', '美罗培南粗品B', '美罗培南粗品C'],
  },
  {
    label: '无菌美罗培南',
    members: ['美罗培南B', '美罗培南', '美罗培南（FDA）', '美罗培南精粗品D', '美罗培南精粗品EP'],
  },
  {
    label: '无菌亚胺培南',
    members: ['亚胺培南-乙醇', '亚胺培南-甲醇', '亚胺培南（CEP）'],
  },
]

/**
 * 会议（2026-10-02）定的排除规则 —— 记录在此供取数服务对齐，
 * 前端不参与排除（排除发生在服务端聚合时）。
 */
export const PRODUCTION_EXCLUSIONS = {
  /** 名称含这些词的不纳入。 */
  keywords: ['欧盟', '混粉', '晶种', 'USP'],
  /** 这些产品名不纳入。 */
  exact: ['碳酸氢钠', '碳酸钠（EP）', '比阿培南'],
  /** 这些车间暂不录入。 */
  departments: ['四车间'],
  /** 产量少、既有看板也未列，暂不单独列示。 */
  notListed: ['亚胺培南粗品-甲醇', '亚胺培南粗品-乙醇'],
} as const
