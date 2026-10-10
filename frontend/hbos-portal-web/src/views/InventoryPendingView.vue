<template>
  <section class="inventory-page pending-page">
    <div class="pending-head">
      <div>
        <h1>待检批次</h1>
        <p>还没拿到 QA 放行的批次。放行由 LIMS 完成，本页只显示进度。</p>
      </div>
      <div v-if="state === 'ready' && list" class="pending-count">
        <b class="pending-mono">{{ list.total }}</b> 个批次待检
        <span v-if="list.withStock !== list.total" class="pending-count-sub">
          · 其中 <b class="pending-mono">{{ list.withStock }}</b> 个当前有库存
        </span>
      </div>
    </div>

    <!-- 只读口径：放行是 LIMS 的权限 -->
    <div class="pending-note info">
      <LockOutlined />
      <div>
        <b>放行由 LIMS 完成，本页不能放行。</b>
        质量放行字段（放行状态 / 日期 / 合格证号 / LIMS 引用）由 LIMS 投影写入，
        仓库侧只读——<b>任何人直接修改都会被后端拒绝</b>。本页的作用是让你知道
        「还有多少批卡着、卡在谁那里」。
      </div>
    </div>

    <!-- 两个数对不上时把差异摊开说，别让用户自己纳闷 -->
    <div v-if="state === 'ready' && list && list.withStock !== list.total" class="pending-note warn">
      <WarningOutlined />
      <div>
        {{ list.total }} 个待检批次里有
        <b>{{ list.total - list.withStock }} 个当前没有库存</b>，
        所以下面的「剩余天数 / 货位 / 数量」对它们是空的。
        这批多半来自<b>尚未提交的入库草稿</b>——草稿没入账就不会有库存，
        但批次记录已经建出来了。可以先不管，也可以用批次号去查是哪张单。
      </div>
    </div>

    <!-- 筛选 -->
    <div class="pending-filterbar" data-view="ready">
      <label class="pending-filter">
        <span>物料</span>
        <a-input v-model:value="itemFilter" placeholder="物料代码或名称" allow-clear style="width: 190px" />
      </label>
      <label class="pending-filter-inline">
        <a-checkbox v-model:checked="onlyWithStock">只看有库存的</a-checkbox>
      </label>
      <div class="pending-filterbar-spacer"></div>
      <span class="pending-hint">共 {{ filtered.length }} 行</span>
    </div>

    <div class="inventory-dest glass-surface">
      <div v-if="state === 'loading'" style="padding: 20px" aria-busy="true" aria-label="正在加载待检批次">
        <div v-for="n in 6" :key="n" class="pending-skel pending-skel-row"></div>
      </div>

      <div v-else-if="state === 'error'" class="inventory-state err" style="padding: 32px 20px">
        <StopOutlined class="inventory-state-icon" />
        <h3>取不到待检批次</h3>
        <p>这次没拿到数据——<b>不代表没有待检批次</b>。请重试。</p>
        <div class="inventory-state-actions">
          <a-button type="primary" @click="load">重试</a-button>
        </div>
      </div>

      <div v-else-if="state === 'empty'" class="inventory-state ok" style="padding: 32px 20px">
        <CheckCircleOutlined class="inventory-state-icon" />
        <h3>没有待检批次</h3>
        <p>系统里没有标着「待检」的批次——手上这批都已取得放行手续。</p>
      </div>

      <div v-else-if="!filtered.length" class="inventory-state" style="padding: 32px 20px">
        <InboxOutlined class="inventory-state-icon" />
        <h3>当前筛选下没有记录</h3>
        <p>共有 {{ list?.total || 0 }} 个待检批次，但都不满足上面的条件。清掉筛选再看。</p>
        <div class="inventory-state-actions">
          <a-button @click="clearFilters">清空筛选</a-button>
        </div>
      </div>

      <div v-else class="pending-table-wrap">
        <table class="pending-table">
          <thead>
            <tr>
              <th>批号</th>
              <th>物料</th>
              <th>效期至</th>
              <th>紧急度</th>
              <th class="num">剩余天数</th>
              <th>货位</th>
              <th class="num">数量</th>
              <th>来源</th>
              <th>放行状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filtered" :key="row.batchNo" :class="{ 'no-stock': row.qty === null }">
              <td>
                <RouterLink class="pending-link" :to="`/hbos/inventory/batch/${encodeURIComponent(row.batchNo)}`">
                  {{ row.batchNo }}
                </RouterLink>
              </td>
              <td>
                <span class="pending-strong">{{ row.itemName || '—' }}</span>
                <span class="pending-mono pending-muted"> {{ row.itemCode }}</span>
              </td>
              <td><span class="pending-mono">{{ row.expiryDate || '—' }}</span></td>
              <td>
                <span v-if="row.urgency" class="pending-tag" :class="urgencyClass(row.urgency)">
                  {{ row.urgency }}
                </span>
                <span v-else class="pending-muted">—</span>
              </td>
              <td class="num">
                <span v-if="row.daysLeft !== null" class="pending-mono">{{ row.daysLeft }}</span>
                <span v-else class="pending-muted">—</span>
              </td>
              <td>
                <span v-if="row.warehouse" class="pending-mono">{{ shortWarehouse(row.warehouse) }}</span>
                <span v-else class="pending-muted">无库存</span>
              </td>
              <td class="num">
                <span v-if="row.qty !== null" class="pending-mono">{{ row.qty.toFixed(3) }}</span>
                <span v-else class="pending-muted">—</span>
                <span v-if="row.uom" class="pending-muted"> {{ row.uom }}</span>
              </td>
              <td>{{ row.sourceType || '—' }}</td>
              <td>
                <span class="pending-tag" :class="releaseTone(row.releaseStatus)">{{ row.releaseStatus || '—' }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  CheckCircleOutlined,
  InboxOutlined,
  LockOutlined,
  StopOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  getPendingReleaseBatches,
  releaseTone,
  warehouseShortLabel,
  type PendingBatchList,
} from '@/services/inventoryDocs'

type ViewState = 'loading' | 'ready' | 'empty' | 'error'

const list = ref<PendingBatchList | null>(null)
const state = ref<ViewState>('loading')
const itemFilter = ref('')
const onlyWithStock = ref(false)

const filtered = computed(() => {
  const all = list.value?.rows || []
  const q = itemFilter.value.trim().toLowerCase()
  return all.filter((row) => {
    if (onlyWithStock.value && row.qty === null) return false
    if (!q) return true
    // 代码与名称都能搜——与物料页同一个口径
    return row.itemCode.toLowerCase().includes(q) || row.itemName.toLowerCase().includes(q)
  })
})

const URGENCY_CLASS: Record<string, string> = {
  已过期: 'critical',
  '紧急（≤30 天）': 'critical',
  '关注（≤90 天）': 'warning',
  正常: 'neutral',
}

function urgencyClass(value: string): string {
  return URGENCY_CLASS[value] || 'neutral'
}

function shortWarehouse(name: string): string {
  return warehouseShortLabel(name)
}

function clearFilters() {
  itemFilter.value = ''
  onlyWithStock.value = false
}

async function load() {
  state.value = 'loading'
  try {
    const data = await getPendingReleaseBatches()
    list.value = data
    state.value = data.rows.length ? 'ready' : 'empty'
  } catch {
    // 查不到 ≠ 没有。分两个状态。
    state.value = 'error'
  }
}

onMounted(load)
</script>
