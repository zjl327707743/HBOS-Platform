<template>
  <section class="inventory-page master-page">
    <div class="master-head">
      <div>
        <h1>批次</h1>
        <p>按批号、物料或来源查批次；批次详情里有货位卡与待检证。</p>
      </div>
      <div v-if="state === 'ready'" class="master-count">
        共 <b class="master-mono">{{ total }}</b> 个批次
      </div>
    </div>

    <!-- 只读口径 -->
    <div class="master-note info">
      <LockOutlined />
      <div>
        <b>批次由入库时建立，本页只读。</b>
        批号来自标签（或原厂批号），平台不另行编号。
        放行状态由 <b>LIMS</b> 写入，仓库侧改不了。
      </div>
    </div>

    <div class="master-split">
      <!-- 左：搜索 + 列表 -->
      <div class="master-list-pane">
        <div class="master-list-head">
          <a-input-search
            v-model:value="keyword"
            placeholder="搜批号、物料代码或名称…"
            allow-clear
            :loading="state === 'loading'"
            @search="runSearch"
            @change="onKeywordChange"
          />
          <div v-if="state === 'ready'" class="master-hint">匹配 <b>{{ total }}</b> 个</div>
        </div>

        <div class="master-list-body">
          <div v-if="state === 'loading'" style="padding: 16px" aria-busy="true" aria-label="正在加载批次">
            <div v-for="n in 6" :key="n" class="master-skel master-skel-row"></div>
          </div>

          <div v-else-if="state === 'empty'" class="inventory-state" style="padding: 32px 16px">
            <InboxOutlined class="inventory-state-icon" />
            <h3>{{ keyword ? '没搜到这个批次' : '还没有批次' }}</h3>
            <p v-if="keyword">
              可按批号、物料代码或名称搜。确认无误仍没有，说明该批次还没建立——
              <b>批次由入库时建立</b>（入库拍照识别或库存单据）。
            </p>
            <p v-else>系统里还没有批次。入库之后这里才会有。</p>
          </div>

          <div v-else-if="state === 'error'" class="inventory-state err" style="padding: 32px 16px">
            <StopOutlined class="inventory-state-icon" />
            <h3>取不到批次列表</h3>
            <p>服务端返回了错误。<b>这不是「没有批次」</b>——请重试。</p>
            <div class="inventory-state-actions">
              <a-button type="primary" @click="runSearch">重试</a-button>
            </div>
          </div>

          <template v-else>
            <RouterLink
              v-for="row in rows"
              :key="row.name"
              class="master-row"
              :to="`/hbos/inventory/batch/${encodeURIComponent(row.name)}`"
              style="display: block; text-decoration: none; color: inherit"
            >
              <b class="master-mono">{{ row.name }}</b>
              <small>{{ row.itemName || row.itemCode || '—' }}</small>
              <span class="master-row-tags">
                <span class="master-tag" :class="releaseTone(row.releaseStatus)">
                  {{ row.releaseStatus || '未知' }}
                </span>
                <span v-if="row.sourceType" class="master-tag plain">{{ row.sourceType }}</span>
                <span v-if="row.expiryDate" class="master-tag plain">
                  效期 {{ row.expiryDate }}
                </span>
              </span>
            </RouterLink>
          </template>
        </div>
      </div>

      <!-- 右：空详情 -->
      <div class="master-detail">
        <div class="inventory-dest glass-surface">
          <div class="inventory-state" style="padding: 40px 20px">
            <DatabaseOutlined class="inventory-state-icon" />
            <h3>左侧选一个批次</h3>
            <p>
              选中后可以看到它的库存、包装构成、标签原文，以及<b>货位卡与待检证</b>
              （可打印、可重新生成）。
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  DatabaseOutlined,
  InboxOutlined,
  LockOutlined,
  StopOutlined,
} from '@ant-design/icons-vue'
import { searchBatches, type BatchListRow } from '@/services/inventoryDocs'
import { releaseTone } from '@/services/inventoryDocs'

const router = useRouter()

type ViewState = 'loading' | 'ready' | 'empty' | 'error'

const keyword = ref('')
const rows = ref<BatchListRow[]>([])
const total = ref(0)
const state = ref<ViewState>('loading')

async function runSearch() {
  state.value = 'loading'
  try {
    const result = await searchBatches(keyword.value)
    rows.value = result.rows
    total.value = result.total
    state.value = result.rows.length ? 'ready' : 'empty'
  } catch {
    state.value = 'error'
  }
}

// 输入停顿后再搜，避免每敲一个字打一次请求
let searchTimer: ReturnType<typeof setTimeout> | null = null
function onKeywordChange() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void router.replace({
      path: '/hbos/inventory/batch',
      query: keyword.value ? { q: keyword.value } : {},
    })
    void runSearch()
  }, 300)
}

onMounted(() => {
  keyword.value = String(router.currentRoute.value.query.q || '')
  void runSearch()
})
</script>
