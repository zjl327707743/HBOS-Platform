<template>
  <section class="inventory-page master-page">
    <div class="master-head">
      <div>
        <h1>货位</h1>
        <p>按层级查货位；只有最末一级的货位能存货</p>
      </div>
      <div v-if="state === 'ready' && snapshot" class="master-count">
        叶子货位 <b class="master-mono">{{ snapshot.leafCount }}</b> 个 ·
        分组节点 <b class="master-mono">{{ snapshot.groupCount }}</b> 个
      </div>
    </div>

    <div class="master-note info">
      <LockOutlined />
      <div>
        <b>货位是 ERPNext 主数据，本页只读。</b>
        新建或改名请到 ERPNext 的货位主数据。本页可以直接<b>打印货位二维码</b>贴到货架上。
      </div>
    </div>

    <div class="master-split">
      <!-- 左：货位树 -->
      <div class="master-list-pane">
        <div class="master-list-head">
          <div style="display: flex; gap: 12px; align-items: baseline; justify-content: space-between">
            <b style="font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); font-weight: var(--hbos-weight-strong)">
              货位层级
            </b>
            <span class="master-hint">点箭头展开</span>
          </div>
        </div>

        <div class="master-list-body">
          <div v-if="state === 'loading'" style="padding: 16px" aria-busy="true" aria-label="正在加载货位">
            <div v-for="n in 6" :key="n" class="master-skel master-skel-row"></div>
          </div>

          <div v-else-if="state === 'empty'" class="inventory-state" style="padding: 32px 16px">
            <InboxOutlined class="inventory-state-icon" />
            <h3>没有货位</h3>
            <p>系统里还没有货位主数据。请先在 ERPNext 建立货位。</p>
          </div>

          <div v-else-if="state === 'error'" class="inventory-state err" style="padding: 32px 16px">
            <StopOutlined class="inventory-state-icon" />
            <h3>取不到货位</h3>
            <p>服务端返回了错误。<b>这不是「没有货位」</b>——请重试。</p>
            <div class="inventory-state-actions">
              <a-button type="primary" @click="load">重试</a-button>
            </div>
          </div>

          <div v-else class="master-tree">
            <template v-for="node in flatTree" :key="node.name">
              <button
                type="button"
                class="master-node"
                :class="{ active: node.name === selectedName }"
                :style="{ paddingLeft: `${12 + node.depth * 18}px` }"
                @click="select(node.name)"
              >
                <RightOutlined
                  v-if="node.children.length"
                  class="master-caret"
                  :class="{ open: expanded.has(node.name) }"
                  @click.stop="toggle(node.name)"
                />
                <span v-else class="master-caret blank"></span>
                <FolderOutlined v-if="node.isGroup" class="master-node-ic" />
                <FileOutlined v-else class="master-node-ic" />
                <span class="master-node-name">{{ shortLabel(node.name) }}</span>
                <span
                  v-if="Number(node.disabled) === 1"
                  class="master-node-mark master-node-off"
                >已停用</span>
                <span class="master-node-mark">{{ node.isGroup ? '分组' : '货位' }}</span>
              </button>
            </template>
          </div>
        </div>
      </div>

      <!-- 右：详情 -->
      <div class="master-detail">
        <div v-if="!selectedName" class="inventory-dest glass-surface">
          <div class="inventory-state" style="padding: 40px 20px">
            <FolderOutlined class="inventory-state-icon" />
            <h3>左侧选一个货位</h3>
            <p>选中后可以看到它的层级、能不能存货、对应的二维码，以及当前库存。</p>
          </div>
        </div>

        <div v-else-if="!current" class="inventory-dest glass-surface">
          <div class="inventory-state err" style="padding: 32px 20px">
            <StopOutlined class="inventory-state-icon" />
            <h3>找不到这个货位</h3>
            <p>货位号可能不对，或该货位已被删除。</p>
            <div class="inventory-state-actions">
              <a-button type="primary" @click="$router.push('/hbos/inventory/warehouse')">回到货位树</a-button>
            </div>
          </div>
        </div>

        <div v-else class="master-detail-stack">
          <div class="inventory-dest glass-surface">
            <div class="master-pane-head">
              <h2>{{ shortLabel(current.name) }}</h2>
              <span class="master-tag" :class="current.isGroup ? 'warn' : (Number(current.disabled) === 1 ? 'warn' : 'ok')">
                <component :is="current.isGroup || Number(current.disabled) === 1 ? WarningOutlined : CheckCircleOutlined" />
                {{
                  current.isGroup
                    ? '此节点不能存货'
                    : Number(current.disabled) === 1
                      ? '已停用 · 不能存货'
                      : '可存货'
                }}
              </span>
            </div>
            <div class="master-pane-body">
              <!-- 分组节点不能存货：这是 api.py 里的硬规则，必须显式告知 -->
              <div v-if="current.isGroup" class="master-note warn" style="margin-bottom: 20px">
                <WarningOutlined />
                <div>
                  这是<b>库位 / 层等分组节点</b>，本身不能存货。入库时必须选到具体的货位。
                  下面的库存是它<b>所有下级货位</b>的汇总。
                </div>
              </div>

              <!-- 停用货位：ERPNext 对它是硬拦（validate_disabled_warehouse），必须显式告知 -->
              <div
                v-else-if="Number(current.disabled) === 1"
                class="master-note warn"
                style="margin-bottom: 20px"
              >
                <WarningOutlined />
                <div>
                  这个货位<b>已停用</b>，不能用于任何出入库单据——选了会被 ERPNext 拒。
                  它<b>仍列在这里</b>是为了能查到历史库存与二维码；新建单据时不会再出现在货位下拉里。
                </div>
              </div>

              <nav class="master-chain" aria-label="货位层级">
                <template v-for="(node, i) in chain" :key="node.name">
                  <RightOutlined v-if="i > 0" class="master-chain-sep" />
                  <b v-if="i === chain.length - 1">{{ shortLabel(node.name) }}</b>
                  <span v-else>{{ shortLabel(node.name) }}</span>
                </template>
              </nav>

              <dl class="master-kv" style="margin-top: 20px">
                <div><dt>货位短码</dt><dd><span class="master-mono">{{ shortLabel(current.name) }}</span></dd></div>
                <div v-if="!current.isGroup"><dt>完整名称</dt><dd><span class="master-mono">{{ current.name }}</span></dd></div>
                <div><dt>上级</dt><dd>{{ current.parent_warehouse ? shortLabel(current.parent_warehouse) : '（顶层）' }}</dd></div>
                <div><dt>公司</dt><dd>{{ current.company || '未设置' }}</dd></div>
                <div>
                  <dt>节点类型</dt>
                  <dd>
                    <span class="master-tag" :class="current.isGroup ? 'warn' : 'ok'">
                      {{ current.isGroup ? '分组 · 不可存货' : '货位（叶子）· 可存货' }}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt>状态</dt>
                  <dd>
                    <span class="master-tag" :class="Number(current.disabled) === 1 ? 'off' : 'ok'">
                      {{ Number(current.disabled) === 1 ? '已停用' : '启用' }}
                    </span>
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          <!-- 二维码只对可存货的叶子节点有意义 -->
          <div v-if="!current.isGroup" class="inventory-dest glass-surface">
            <div class="master-pane-head">
              <h2>货位二维码</h2>
              <span class="master-sub">60 × 40 mm 标签，贴货架</span>
            </div>
            <div class="master-pane-body">
              <div class="master-qr">
                <div class="master-qr-img"><QrcodeOutlined /></div>
                <div class="master-qr-main">
                  <b>HBOS 货位二维码</b>
                  <p>扫码后落到「按批号查货位」，当前货位已预选。</p>
                  <div class="master-actions">
                    <a-button type="primary" :href="qrUrl" target="_blank" rel="noopener">
                      <PrinterOutlined /> 打印 / 下载二维码
                    </a-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 库存：分组节点显示下级汇总（Owner 已定） -->
          <div class="inventory-dest glass-surface">
            <div class="master-pane-head">
              <h2>{{ current.isGroup ? '下级库存汇总' : '当前库存' }}</h2>
              <span class="master-sub">
                {{ current.isGroup ? `来自 ${descendantLeafCount} 个下级货位` : '货位明细表' }}
              </span>
            </div>
            <div class="master-pane-body" style="padding: 0">
              <div v-if="stockState === 'loading'" style="padding: 20px">
                <div v-for="n in 3" :key="n" class="master-skel master-skel-row"></div>
              </div>
              <div v-else-if="stockState === 'error'" class="inventory-state err" style="padding: 28px 20px">
                <StopOutlined class="inventory-state-icon" />
                <h3>取不到库存</h3>
                <p>这次没拿到数据——<b>不代表这里没库存</b>。请重试。</p>
                <div class="inventory-state-actions">
                  <a-button type="primary" @click="loadStock">重试</a-button>
                </div>
              </div>
              <div v-else-if="!stock.length" class="inventory-state" style="padding: 28px 20px">
                <InboxOutlined class="inventory-state-icon" />
                <h3>{{ current.isGroup ? '下级货位都没有库存' : '这个货位当前没有库存' }}</h3>
                <p>账面数量为零。可能尚未入库，或已全部发出。</p>
              </div>
              <table v-else class="master-table">
                <thead>
                  <tr>
                    <th v-if="current.isGroup">货位</th>
                    <th>物料代码</th>
                    <th>物料名称</th>
                    <th>批号</th>
                    <th class="num">数量</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, i) in stock" :key="`${row.warehouse}-${row.itemCode}-${row.batchNo}-${i}`">
                    <td v-if="current.isGroup" class="master-mono">{{ row.warehouseLabel }}</td>
                    <td class="master-mono">{{ row.itemCode }}</td>
                    <td>{{ row.itemName || '—' }}</td>
                    <td class="master-mono">{{ row.batchNo || '—' }}</td>
                    <td class="num master-mono">{{ row.qty.toFixed(3) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="inventory-dest glass-surface">
            <div class="master-pane-head"><h2>相关</h2></div>
            <div class="master-pane-body">
              <div class="master-actions">
                <a-button @click="goReport('location-detail', current.name)">
                  <TableOutlined /> 看这个货位的明细
                </a-button>
                <a-button @click="goReport('stocktake', current.name)">
                  <ReconciliationOutlined /> 库级盘点三对账
                </a-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CheckCircleOutlined,
  FileOutlined,
  FolderOutlined,
  InboxOutlined,
  LockOutlined,
  PrinterOutlined,
  QrcodeOutlined,
  ReconciliationOutlined,
  RightOutlined,
  StopOutlined,
  TableOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  getWarehouseSnapshot,
  getWarehouseStock,
  subtreeOf,
  warehouseChain,
  warehouseQrUrl,
  type StockRow,
  type WarehouseRow,
  type WarehouseSnapshot,
  type WarehouseTreeNode,
} from '@/services/inventoryMaster'

const route = useRoute()
const router = useRouter()

type ViewState = 'loading' | 'ready' | 'empty' | 'error'
type StockState = 'loading' | 'ready' | 'error'

const snapshot = ref<WarehouseSnapshot | null>(null)
const state = ref<ViewState>('loading')
const expanded = ref<Set<string>>(new Set())
const stock = ref<StockRow[]>([])
const stockState = ref<StockState>('loading')
const descendantLeafCount = ref(0)

const selectedName = computed(() => String(route.params.warehouseName || ''))
const current = computed<WarehouseTreeNode | undefined>(() => {
  const row = selectedName.value ? snapshot.value?.byName.get(selectedName.value) : undefined
  if (!row) return undefined
  return { ...row, depth: 0, children: [], isGroup: Number(row.is_group) === 1 }
})

const chain = computed<WarehouseRow[]>(() =>
  snapshot.value && selectedName.value ? warehouseChain(snapshot.value, selectedName.value) : [],
)

/** 按展开状态摊平成可见行 —— 比递归渲染模板好读，也便于按 depth 缩进 */
const flatTree = computed<WarehouseTreeNode[]>(() => {
  const out: WarehouseTreeNode[] = []
  const walk = (nodes: WarehouseTreeNode[]) => {
    for (const node of nodes) {
      out.push(node)
      if (expanded.value.has(node.name) && node.children.length) walk(node.children)
    }
  }
  walk(snapshot.value?.tree || [])
  return out
})

function shortLabel(name: string): string {
  return String(name || '').split(' - ')[0] || ''
}

function toggle(name: string) {
  const next = new Set(expanded.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  expanded.value = next
}

function select(name: string) {
  void router.push(`/hbos/inventory/warehouse/${encodeURIComponent(name)}`)
}

function goReport(reportId: string, warehouseName: string) {
  void router.push({
    path: `/hbos/inventory/report/${reportId}`,
    query: { warehouse: warehouseName, include_children: '1' },
  })
}

const qrUrl = computed(() =>
  current.value && !current.value.isGroup ? warehouseQrUrl(current.value.name) : '',
)

async function load() {
  state.value = 'loading'
  try {
    const data = await getWarehouseSnapshot()
    snapshot.value = data
    // 默认展开顶层，否则树是空的、要用户自己一级级点开
    expanded.value = new Set(data.tree.map((n) => n.name))
    state.value = data.all.length ? 'ready' : 'empty'
  } catch {
    state.value = 'error'
  }
}

async function loadStock() {
  const row = current.value
  if (!row || !snapshot.value) {
    stock.value = []
    descendantLeafCount.value = 0
    return
  }

  stockState.value = 'loading'
  try {
    // 分组节点：它自己不能存货，但下级有。**下级展开由报表完成**
    // （它的 `_warehouse_scope` 按 lft/rgt 展开整棵子树）——这里只传节点名。
    stock.value = await getWarehouseStock(row.name)

    // 「来自 N 个下级货位」是**显示用的范围计数**，不是库存数据本身。
    // 库存数据只有一个来源（报表）；这里只是拿已取到的树算个标签数字。
    descendantLeafCount.value = row.isGroup
      ? subtreeOf(snapshot.value, row.name).filter((x) => Number(x.is_group) !== 1).length
      : 1

    stockState.value = 'ready'
  } catch {
    // 查不到 ≠ 没有。界面必须分成两个状态。
    stockState.value = 'error'
  }
}

onMounted(async () => {
  await load()
  await loadStock()
})

watch(selectedName, async () => {
  // 选中项若在折叠的分支里，把它所在的路径展开，否则用户看不到自己选了什么
  const target = selectedName.value
  if (snapshot.value && target && !flatTree.value.some((n) => n.name === target)) {
    const next = new Set(expanded.value)
    for (const node of warehouseChain(snapshot.value, target)) next.add(node.name)
    expanded.value = next
  }
  await loadStock()
})
</script>
