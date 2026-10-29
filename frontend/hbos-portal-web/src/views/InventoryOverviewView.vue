<template>
  <section class="inventory-page">
    <div class="inventory-page-head">
      <div>
        <h1>仓储库存</h1>
        <p>入库、出库、批次、货位、盘点与效期管理</p>
      </div>
      <small v-if="state === 'ready'">数据截至刚刚刷新</small>
    </div>

    <section aria-labelledby="inventory-ledger-h">
      <div class="inventory-ledger glass-surface">
        <!-- 左：需要核对什么。占更宽、视觉更重。 -->
        <div class="inventory-ledger-main">
          <div class="inventory-ledger-title">
            <h2 id="inventory-ledger-h">需要核对的库存异常</h2>
            <span class="inventory-tagline">按货位计</span>
          </div>

          <template v-if="state === 'ready'">
            <div class="inventory-row">
              <div class="inventory-row-label">
                <b>负库存项</b>
                <small>账面数量小于零。通常是漏记出库或盘点未对齐，须优先处理。</small>
              </div>
              <div class="inventory-num" :class="negativeTone">{{ negativeBins }}</div>
            </div>
            <div class="inventory-row">
              <div class="inventory-row-label">
                <b>预计短缺项</b>
                <small>已被订单占用，可动用数量将不足。</small>
              </div>
              <div class="inventory-num" :class="shortageTone">{{ shortageBins }}</div>
            </div>

            <div class="inventory-verdict" :class="verdict.tone">
              <AlertOutlined v-if="verdict.tone !== 'success'" />
              <CheckCircleOutlined v-else />
              <div>
                <b>{{ verdict.title }}</b><br />
                {{ verdict.detail }}
              </div>
            </div>
          </template>

          <!-- 空态。刻意不推断账实一致：两个计数为 0 推不出这个结论。 -->
          <div v-else-if="state === 'void'" class="inventory-state ok">
            <CheckCircleOutlined class="inventory-state-icon" />
            <h3>没有需要核对的异常</h3>
            <p>当前没有负库存项，也没有预计短缺项。这不代表账实已经核对一致——只是没有这两类异常。</p>
          </div>

          <!-- 加载态：骨架与最终布局同尺寸，不跳变 -->
          <div v-else-if="state === 'loading'" aria-busy="true" aria-label="正在加载库存概览">
            <div class="inventory-skel inventory-skel-row" style="margin-bottom: 16px"></div>
            <div class="inventory-skel inventory-skel-row" style="margin-bottom: 16px"></div>
            <div class="inventory-skel inventory-skel-line"></div>
          </div>

          <!-- 错误态。必须明确否定「没有异常」这个误读。 -->
          <div v-else class="inventory-state err">
            <CloseCircleOutlined class="inventory-state-icon" />
            <h3>暂时取不到概览数据</h3>
            <p>
              这一页的异常数字依赖库存数据服务，它暂时没有响应。<b>请勿把这里当作「库存没有问题」</b>——只是现在算不出来。
            </p>
            <div class="inventory-state-actions">
              <a-button type="primary" @click="load">重试</a-button>
              <a-button @click="$router.push('/hbos')">返回 HBOS 工作台</a-button>
            </div>
          </div>
        </div>

        <!-- 右：账面规模。安静的一侧，刻意不与异常同重。 -->
        <div class="inventory-ledger-scale">
          <div class="inventory-scale-title">账面规模</div>

          <template v-if="state === 'ready' || state === 'void'">
            <div class="inventory-scale-item">
              <span>可见货位</span><strong>{{ visibleWarehouses }}</strong>
            </div>
            <div class="inventory-scale-item">
              <span>有库存物料</span><strong>{{ stockedItems }}</strong>
            </div>
          </template>

          <template v-else-if="state === 'loading'">
            <div class="inventory-skel inventory-skel-row"></div>
            <div class="inventory-skel inventory-skel-row"></div>
          </template>

          <p v-else class="inventory-scale-note">数据不可用</p>

          <p class="inventory-scale-note">
            不显示库存合计：不同物料的计量单位不同，相加没有意义。这里只按项数反映规模。
          </p>
        </div>
      </div>
    </section>

    <section aria-labelledby="inventory-dest-h">
      <div class="inventory-section-head">
        <h2 id="inventory-dest-h">去哪办事</h2>
        <span class="inventory-hint">全部在本工作台内完成</span>
      </div>

      <div class="inventory-dest glass-surface">
        <div v-for="group in entryGroups" :key="group.label" class="inventory-dest-group">
          <h3>{{ group.label }}</h3>
          <div class="inventory-dest-list">
            <button
              v-for="item in group.items"
              :key="item.id"
              type="button"
              class="inventory-dest-item"
              @click="openEntry(item)"
            >
              <component :is="iconMap[item.icon]" />
              <span class="inventory-dest-text">
                <b>{{ item.label }}</b>
                <small v-if="item.hint">{{ item.hint }}</small>
              </span>
              <RightOutlined />
            </button>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertOutlined,
  AuditOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExportOutlined,
  FileTextOutlined,
  ImportOutlined,
  InboxOutlined,
  LineChartOutlined,
  ReconciliationOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  TableOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import {
  INVENTORY_ENTRY_GROUPS,
  INVENTORY_OVERVIEW_PATH,
  inventoryUnavailablePath,
  type InventoryNavItem,
} from '@/data/inventoryNav'
import { getInventoryOverview } from '@/services/inventoryOverview'
import { openBusinessRoute } from '@/services/businessNavigation'
import type { InventoryOverviewState } from '@/services/inventoryOverview'

const router = useRouter()

type ViewState = 'loading' | 'ready' | 'void' | 'error'
const state = ref<ViewState>('loading')

// 取不到就是 null —— 按 EA-5.4 §16「没有真实 Provider 时必须隐藏，不展示假数字」。
// 注意：null 与 0 含义不同，0 是真实的「没有」，null 是「不知道」。
const overview = ref<InventoryOverviewState | null>(null)

const entryGroups = INVENTORY_ENTRY_GROUPS

const iconMap: Record<string, unknown> = {
  camera: CameraOutlined,
  document: FileTextOutlined,
  import: ImportOutlined,
  export: ExportOutlined,
  list: UnorderedListOutlined,
  release: SafetyCertificateOutlined,
  reconcile: ReconciliationOutlined,
  audit: AuditOutlined,
  batch: DatabaseOutlined,
  shelf: LineChartOutlined,
  item: InboxOutlined,
  table: TableOutlined,
  clock: ClockCircleOutlined,
  search: SearchOutlined,
  gauge: DashboardOutlined,
}

const negativeBins = computed(() => overview.value?.negativeBins ?? 0)
const shortageBins = computed(() => overview.value?.projectedShortageBins ?? 0)
const visibleWarehouses = computed(() => overview.value?.visibleWarehouses ?? 0)
const stockedItems = computed(() => overview.value?.stockedItems ?? 0)

// 0 在视觉上要安静下来——没有异常不该和有异常一样响（见方案 §4.2）
const negativeTone = computed(() => (negativeBins.value > 0 ? 'critical' : 'zero'))
const shortageTone = computed(() => (shortageBins.value > 0 ? 'warning' : 'zero'))

const verdict = computed(() => {
  if (negativeBins.value > 0) {
    return {
      tone: 'critical',
      title: '存在负库存，建议先处理。',
      detail:
        '负库存会让后续出入库的数量核对失去基准。请到「库存对账」按实际盘点数调整。',
    }
  }
  if (shortageBins.value > 0) {
    return {
      tone: 'warning',
      title: '有货位预计短缺。',
      detail: '这些货位已被订单占用，可动用数量将不足。请核对是否需要补货。',
    }
  }
  return {
    tone: 'success',
    title: '两类异常都没有出现。',
    detail: '这不等于账实已经核对一致，只是没有负库存与预计短缺。',
  }
})

async function load() {
  state.value = 'loading'
  try {
    const data = await getInventoryOverview()
    if (!data) {
      state.value = 'error'
      return
    }
    overview.value = data
    state.value =
      data.negativeBins === 0 && data.projectedShortageBins === 0 ? 'void' : 'ready'
  } catch {
    // 不把底层异常文本带进界面（EA-5.4 §28）
    state.value = 'error'
  }
}

function openEntry(item: InventoryNavItem) {
  if (!item.implemented) {
    void router.push(inventoryUnavailablePath(item.id))
    return
  }
  if (item.stablePath === INVENTORY_OVERVIEW_PATH) {
    void router.push(INVENTORY_OVERVIEW_PATH)
    return
  }
  void openBusinessRoute(router, 'inventory', item.stablePath || '')
}

onMounted(load)
</script>
