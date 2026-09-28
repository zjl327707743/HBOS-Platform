/**
 * 仓储库存 —— 侧边栏导航与办事入口清单。
 *
 * **由前端自己维护**（Owner 2026-09-25 确认）。
 *
 * 仓管的操作全部发生在前端页面，所以这份清单是前端资产，不是 Desk「仓库工作台」
 * 侧边栏的副本。Desk 那份由 `workspace_setup.py` 用代码同步、服务管理员直连，
 * 两者职责不同，允许分叉。
 *
 * `implemented` 标记的是**前端页是否已经做出来**。没做出来的入口在界面上照常
 * 列出（反映目标形态），点击落到统一的「尚未实现」提示页，而不是死链接。
 * 前端页做出来后，把 `implemented` 改真、补上 `stablePath` 即可。
 */

export interface InventoryNavItem {
  id: string
  label: string
  /** 侧边栏 / 入口区的图标键，由组件映射到具体 Ant Design Icon */
  icon: string
  /** 前端页是否已实现 */
  implemented: boolean
  /**
   * Portal 稳定路由。只有 `implemented` 为真时才有意义；
   * 由后端 `hb_inventory_app...portal.routes` 解析到当前实现。
   */
  stablePath?: string
  /** 入口区的一行说明；侧边栏不用 */
  hint?: string
}

export interface InventoryNavGroup {
  label: string
  items: InventoryNavItem[]
}

/** 概览页自身的路由 —— 侧边栏第一项，也是返回路径 */
export const INVENTORY_OVERVIEW_PATH = '/hbos/inventory'

/** 未实现提示页的路由前缀 */
export const INVENTORY_UNAVAILABLE_PATH = '/hbos/inventory/unavailable'

export const INVENTORY_TITLE = '仓储库存'
export const INVENTORY_SUBTITLE = '入库、出库、批次、货位、盘点与效期管理'

export const INVENTORY_NAV_GROUPS: InventoryNavGroup[] = [
  {
    label: '工作台',
    items: [
      {
        id: 'overview',
        label: '库存概览',
        icon: 'gauge',
        implemented: true,
        stablePath: INVENTORY_OVERVIEW_PATH,
      },
    ],
  },
  {
    label: '入库作业',
    items: [
      {
        id: 'photo-intake',
        label: '入库拍照识别',
        icon: 'camera',
        implemented: true,
        stablePath: '/hbos/inventory/intake',
        hint: '拍标签 → 识别 → 人工校对 → 生成草稿',
      },
      {
        id: 'stock-entry',
        label: '库存单据',
        icon: 'document',
        implemented: true,
        stablePath: '/hbos/inventory/entry',
        hint: '入库 / 领用出库 / 移库',
      },
      {
        id: 'purchase-receipt',
        label: '采购入库',
        icon: 'import',
        implemented: false,
        hint: '采购收货',
      },
      {
        id: 'qa-release',
        // 不叫「待检与放行」——放行由 LIMS 完成，本页放不了（Owner 已定改名）
        label: '待检批次',
        icon: 'release',
        implemented: true,
        stablePath: '/hbos/inventory/pending',
        hint: '还没取得 QA 放行的批次',
      },
    ],
  },
  {
    label: '出库作业',
    items: [
      {
        id: 'delivery-note',
        label: '销售出库',
        icon: 'export',
        implemented: false,
        hint: '须先取得 QA 放行',
      },
      {
        id: 'pick-list',
        label: '拣货单',
        icon: 'list',
        implemented: true,
        stablePath: '/hbos/inventory/pick',
        hint: '按需求拣货',
      },
    ],
  },
  {
    label: '盘点与对账',
    items: [
      {
        id: 'stock-reconciliation',
        label: '库存对账',
        icon: 'reconcile',
        implemented: true,
        stablePath: '/hbos/inventory/reconcile',
        hint: '按实际盘点数调整系统账',
      },
      {
        id: 'warehouse-stocktake',
        label: '库级盘点三对账',
        icon: 'audit',
        implemented: true,
        stablePath: '/hbos/inventory/report/stocktake',
        hint: '导出后现场盘点',
      },
    ],
  },
  {
    label: '主数据',
    items: [
      {
        id: 'batch',
        label: '批次',
        icon: 'batch',
        implemented: false,
        hint: '可打印待检证与货位卡',
      },
      {
        id: 'warehouse',
        label: '货位',
        icon: 'shelf',
        implemented: true,
        stablePath: '/hbos/inventory/warehouse',
        hint: '可打印货位二维码',
      },
      {
        id: 'item',
        label: '物料',
        icon: 'item',
        implemented: true,
        stablePath: '/hbos/inventory/item',
        hint: '物料主数据由 SAP 分配代码',
      },
    ],
  },
  {
    label: '报表',
    items: [
      {
        id: 'stock-balance',
        label: '库存余额',
        icon: 'table',
        implemented: false,
        hint: '按货位与物料',
      },
      {
        id: 'expiry-warning',
        label: '效期预警',
        icon: 'clock',
        implemented: true,
        stablePath: '/hbos/inventory/report/expiry-warning',
        hint: '临近效期批次',
      },
      {
        id: 'batch-location',
        label: '按批号查货位',
        icon: 'search',
        implemented: true,
        stablePath: '/hbos/inventory/report/batch-location',
        hint: '扫码或输批号定位',
      },
      {
        id: 'location-detail',
        label: '货位明细表',
        icon: 'table',
        implemented: true,
        stablePath: '/hbos/inventory/report/location-detail',
        hint: '按货位逐项列出',
      },
    ],
  },
]

/** 入口区按业务分组展示；与侧边栏同源，只是去掉「工作台」那组 */
export const INVENTORY_ENTRY_GROUPS: InventoryNavGroup[] = INVENTORY_NAV_GROUPS.filter(
  (group) => group.label !== '工作台',
).map((group) => ({
  ...group,
  // 入口区里「报表」叫「库存报表」，与侧边栏的短名区分
  label: group.label === '报表' ? '库存报表' : group.label,
}))

const ALL_ITEMS = INVENTORY_NAV_GROUPS.flatMap((group) => group.items)

export function findInventoryNavItem(id: string): InventoryNavItem | undefined {
  return ALL_ITEMS.find((item) => item.id === id)
}

export function inventoryUnavailablePath(itemId: string): string {
  return `${INVENTORY_UNAVAILABLE_PATH}/${encodeURIComponent(itemId)}`
}
