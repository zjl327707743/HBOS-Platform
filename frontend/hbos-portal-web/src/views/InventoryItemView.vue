<template>
  <section class="inventory-page master-page">
    <div class="master-head">
      <div>
        <h1>物料</h1>
        <p>查物料代码、名称、分类与效期/储存信息</p>
      </div>
      <div v-if="state === 'ready'" class="master-count">
        共 <b class="master-mono">{{ total }}</b> 条<template v-if="truncated">（列表最多显示 {{ ITEM_LIST_LIMIT }} 条）</template>
      </div>
    </div>

    <!-- 只读口径：物料代码由 SAP 分配 -->
    <div class="master-note info">
      <LockOutlined />
      <div>
        <b>物料主数据由 SAP 分配代码，本页只读。</b>
        平台不新建、不分配物料代码——识别到未知物料时只提示去建档。
        需要修改请到 ERPNext 的物料主数据（需 Item Manager 及以上角色）。
      </div>
    </div>

    <div class="master-split">
      <!-- 左：搜索 + 列表 -->
      <div class="master-list-pane">
        <div class="master-list-head">
          <a-input-search
            v-model:value="keyword"
            placeholder="搜物料代码或名称…"
            allow-clear
            :loading="state === 'loading'"
            @search="runSearch"
            @change="onKeywordChange"
          />
          <div v-if="state === 'ready'" class="master-hint">
            匹配 <b>{{ total }}</b> 条
          </div>
        </div>

        <div class="master-list-body">
          <div v-if="state === 'loading'" style="padding: 16px" aria-busy="true" aria-label="正在加载物料">
            <div v-for="n in 6" :key="n" class="master-skel master-skel-row"></div>
          </div>

          <div v-else-if="state === 'empty'" class="inventory-state" style="padding: 32px 16px">
            <InboxOutlined class="inventory-state-icon" />
            <h3>{{ keyword ? '没搜到这个物料' : '没有物料' }}</h3>
            <p v-if="keyword">
              可按代码或名称搜。确认输入无误仍没有，说明该物料尚未建档——
              <b>物料代码由 SAP 分配，平台不能自造</b>。
            </p>
            <p v-else>系统里还没有物料主数据。请在 ERPNext 建档（需 Item Manager 及以上角色）。</p>
          </div>

          <div v-else-if="state === 'error'" class="inventory-state err" style="padding: 32px 16px">
            <StopOutlined class="inventory-state-icon" />
            <h3>取不到物料列表</h3>
            <p>服务端返回了错误。<b>这不是「没有物料」</b>——请重试。</p>
            <div class="inventory-state-actions">
              <a-button type="primary" @click="runSearch">重试</a-button>
            </div>
          </div>

          <template v-else>
            <button
              v-for="row in rows"
              :key="row.name"
              type="button"
              class="master-row"
              :class="{ active: row.name === selectedCode }"
              @click="selectItem(row.name)"
            >
              <b>{{ row.item_name || row.name }}</b>
              <small>{{ row.name }}</small>
              <span class="master-row-tags">
                <span v-if="row.hbos_product_kind" class="master-tag plain">{{ row.hbos_product_kind }}</span>
                <span class="master-tag" :class="Number(row.disabled) === 1 ? 'off' : 'ok'">
                  {{ Number(row.disabled) === 1 ? '已停用' : '启用' }}
                </span>
              </span>
            </button>
          </template>
        </div>
      </div>

      <!-- 右：详情 -->
      <div class="master-detail">
        <div v-if="detailState === 'loading'" class="inventory-dest glass-surface">
          <div class="master-pane-body">
            <div class="master-skel master-skel-line" style="width: 40%"></div>
            <div class="master-skel master-skel-row"></div>
            <div class="master-skel master-skel-row"></div>
            <div class="master-skel master-skel-row"></div>
          </div>
        </div>

        <div v-else-if="detailState === 'missing'" class="inventory-dest glass-surface">
          <div class="inventory-state err" style="padding: 32px 20px">
            <StopOutlined class="inventory-state-icon" />
            <h3>取不到这个物料</h3>
            <p>可能已被删除，或链接不对。物料主数据由 SAP 侧维护——若确认应该存在，请联系管理员核对。</p>
            <div class="inventory-state-actions">
              <a-button type="primary" @click="$router.push('/hbos/inventory/item')">回到物料列表</a-button>
            </div>
          </div>
        </div>

        <div v-else-if="detail" class="master-detail-stack">
          <div class="inventory-dest glass-surface">
            <div class="master-pane-head">
              <h2>{{ detail.item_name || detail.name }}</h2>
              <span class="master-sub">物料主数据 · 只读</span>
            </div>
            <div class="master-pane-body">
              <dl class="master-kv">
                <div>
                  <dt>物料代码</dt>
                  <dd><span class="master-mono">{{ detail.name }}</span> <span class="master-tag plain">SAP 分配</span></dd>
                </div>
                <div><dt>物料名称</dt><dd><b>{{ detail.item_name || '—' }}</b></dd></div>
                <div><dt>ERPNext 物料组</dt><dd>{{ detail.item_group || '未设置' }}</dd></div>
                <div><dt>HBOS 业务分类</dt><dd>{{ detail.hbos_product_kind || '未设置' }}</dd></div>
                <div><dt>单位</dt><dd>{{ detail.stock_uom || '未设置' }}</dd></div>
                <div>
                  <dt>批号管理</dt>
                  <dd>
                    <span class="master-tag" :class="Number(detail.has_batch_no) === 1 ? 'ok' : 'plain'">
                      {{ Number(detail.has_batch_no) === 1 ? '按批号管理' : '不按批号' }}
                    </span>
                  </dd>
                </div>
                <div><dt>效期类型</dt><dd>{{ detail.hbos_shelf_life_type || '未设置' }}</dd></div>
                <div>
                  <dt>效期期限</dt>
                  <dd>{{ Number(detail.hbos_shelf_life_months) > 0 ? `${detail.hbos_shelf_life_months} 个月` : '未设置' }}</dd>
                </div>
                <div><dt>储存条件</dt><dd>{{ detail.hbos_storage_condition || '未设置' }}</dd></div>
                <div><dt>生产车间</dt><dd>{{ detail.hbos_workshop || '未设置' }}</dd></div>
                <div>
                  <dt>状态</dt>
                  <dd>
                    <span class="master-tag" :class="Number(detail.disabled) === 1 ? 'off' : 'ok'">
                      {{ Number(detail.disabled) === 1 ? '已停用' : '启用' }}
                    </span>
                  </dd>
                </div>
              </dl>

              <div v-if="gaps.length" class="master-note warn" style="margin-top: 20px">
                <WarningOutlined />
                <div>
                  有 {{ gaps.length }} 项主数据为空（{{ gaps.join('、') }}）。
                  入库拍照识别时若在标签上读到，会<b>仅补空</b>写回这里；已填的值不会被覆盖。
                </div>
              </div>
            </div>
          </div>

          <div class="inventory-dest glass-surface">
            <div class="master-pane-head">
              <h2>相关</h2>
              <span class="master-sub">跳到已带过滤条件的页面</span>
            </div>
            <div class="master-pane-body">
              <div class="master-actions">
                <a-button @click="goReport('location-detail', { item_code: detail.name })">
                  <TableOutlined /> 看它在哪些货位
                </a-button>
                <a-button @click="goReport('batch-location', { item_code: detail.name })">
                  <SearchOutlined /> 按批号查货位
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
  InboxOutlined,
  LockOutlined,
  SearchOutlined,
  StopOutlined,
  TableOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
import {
  getItem,
  itemMasterGaps,
  searchItems,
  ITEM_LIST_LIMIT,
  type ItemRow,
} from '@/services/inventoryMaster'

const route = useRoute()
const router = useRouter()

type ListState = 'loading' | 'ready' | 'empty' | 'error'
type DetailState = 'loading' | 'ready' | 'missing' | 'none'

const keyword = ref(String(route.query.q || ''))
const rows = ref<ItemRow[]>([])
const total = ref(0)
const truncated = ref(false)
const state = ref<ListState>('loading')

const detail = ref<ItemRow | null>(null)
const detailState = ref<DetailState>('none')

const selectedCode = computed(() => String(route.params.itemCode || ''))
const gaps = computed(() => (detail.value ? itemMasterGaps(detail.value) : []))

async function runSearch() {
  state.value = 'loading'
  try {
    const result = await searchItems(keyword.value)
    rows.value = result.rows
    total.value = result.total
    truncated.value = result.truncated
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
    // 关键词也进 URL，可分享/可刷新
    void router.replace({ path: '/hbos/inventory/item', query: keyword.value ? { q: keyword.value } : {} })
    void runSearch()
  }, 300)
}

function selectItem(code: string) {
  void router.push(`/hbos/inventory/item/${encodeURIComponent(code)}`)
}

function goReport(reportId: string, query: Record<string, string>) {
  void router.push({ path: `/hbos/inventory/report/${reportId}`, query })
}

async function loadDetail(code: string) {
  if (!code) {
    detail.value = null
    detailState.value = 'none'
    return
  }
  detailState.value = 'loading'
  const doc = await getItem(code)
  detail.value = doc
  detailState.value = doc ? 'ready' : 'missing'
}

onMounted(async () => {
  await runSearch()
  // 深链直接进某个物料时，把它带进选中态
  await loadDetail(selectedCode.value)
})

watch(selectedCode, (code) => {
  void loadDetail(code)
})
</script>
