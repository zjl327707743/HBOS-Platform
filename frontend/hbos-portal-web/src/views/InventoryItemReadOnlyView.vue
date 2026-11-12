<template>
  <ForbiddenView v-if="!allowed" />
  <section v-else class="inventory-page master-page">
    <div class="master-head">
      <div>
        <h1>物料</h1>
        <p>查物料代码、名称、分类与效期/储存信息</p>
      </div>
      <div v-if="state === 'ready'" class="master-count">
        当前可见 <b class="master-mono">{{ total }}</b> 条<template v-if="truncated">（还有更多结果，请缩小搜索范围）</template>
      </div>
    </div>

    <!-- 只读口径：物料代码由 SAP 分配 -->
    <div class="master-note info">
      <LockOutlined />
      <div>
        <b>物料主数据由 SAP 分配代码，本页只读。</b>
        平台不新建、不分配物料代码——识别到未知物料时只提示去建档。
        需要修改请到 ERPNext 的物料主数据（需相应的物料维护权限）。
      </div>
    </div>

    <div class="master-split">
      <!-- 左：搜索 + 列表 -->
      <div class="master-list-pane">
        <div class="master-list-head">
          <a-input-search
            v-model:value="keyword"
            aria-label="按物料代码或名称搜索"
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
              当前账号可见范围内没有匹配物料。可调整关键词或联系管理员核对权限。
            </p>
            <p v-else>当前账号可见范围内没有物料。空列表不代表系统中没有主数据。</p>
          </div>

          <div v-else-if="state === 'error'" class="inventory-state err" style="padding: 32px 16px">
            <StopOutlined class="inventory-state-icon" />
            <h3>取不到物料列表</h3>
            <p>{{ listMessage }}</p>
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

        <div v-else-if="detailState === 'error'" class="inventory-dest glass-surface">
          <div class="inventory-state err" style="padding: 32px 20px">
            <StopOutlined class="inventory-state-icon" />
            <h3>物料详情不可用</h3>
            <p>{{ detailMessage }}</p>
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
                  本页不会修改这些字段。需要补充时请走现有主数据维护流程。
                </div>
              </div>
            </div>
          </div>


        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { InboxOutlined, LockOutlined, StopOutlined, WarningOutlined } from '@ant-design/icons-vue'
import ForbiddenView from '@/views/ForbiddenView.vue'
import { usePortalStore } from '@/stores/portal'
import { portalDataSource } from '@/services/portalProvider'
import { FrappeRequestError } from '@/services/frappeClient'
import { getItem, itemMasterGaps, searchItems, type ItemRow } from '@/services/inventoryItems'

const route = useRoute()
const router = useRouter()
const portal = usePortalStore()
const allowed = computed(() => portalDataSource === 'frappe' && !!portal.user && portal.apps.some(app => app.id === 'inventory'))
const keyword = ref('')
const rows = ref<ItemRow[]>([])
const total = ref(0)
const truncated = ref(false)
const state = ref<'loading' | 'ready' | 'empty' | 'error'>('loading')
const detail = ref<ItemRow | null>(null)
const detailState = ref<'loading' | 'ready' | 'error' | 'none'>('none')
const listMessage = ref('')
const detailMessage = ref('')
const selectedCode = computed(() => String(route.params.itemCode || ''))
const gaps = computed(() => detail.value ? itemMasterGaps(detail.value) : [])
let searchVersion = 0, detailVersion = 0, disposed = false
let searchTimer: ReturnType<typeof setTimeout> | null = null

function message(error: unknown) {
  if (error instanceof FrappeRequestError) {
    if (error.code === 'UNAUTHENTICATED') return '登录状态已失效，请从 HBOS 工作台重新登录。'
    if (error.code === 'FORBIDDEN') return '当前账号无权读取该物料数据，请联系管理员核对。'
  }
  return '物料数据暂时不可用，请重试。此状态不表示没有物料。'
}
async function runSearch() {
  if (!allowed.value || disposed) return
  const version = ++searchVersion
  rows.value = []; total.value = 0; state.value = 'loading'
  try {
    const result = await searchItems(keyword.value)
    if (disposed || version !== searchVersion || !allowed.value) return
    rows.value = result.rows; total.value = result.rows.length; truncated.value = result.truncated
    state.value = result.rows.length ? 'ready' : 'empty'
  } catch (error) {
    if (disposed || version !== searchVersion || !allowed.value) return
    listMessage.value = message(error); state.value = 'error'
  }
}
function onKeywordChange() {
  ++searchVersion
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void router.replace({ path: '/hbos/inventory/item', query: keyword.value ? { q: keyword.value } : {} })
    // Same query does not trigger the route watcher.
    if (String(route.query.q || '') === keyword.value) void runSearch()
  }, 300)
}
function selectItem(code: string) {
  void router.push({ path: `/hbos/inventory/item/${encodeURIComponent(code)}`, query: route.query })
}
async function loadDetail(code: string) {
  const version = ++detailVersion
  detail.value = null; detailMessage.value = ''
  if (!code || !allowed.value || disposed) { detailState.value = 'none'; return }
  detailState.value = 'loading'
  try {
    const doc = await getItem(code)
    if (disposed || version !== detailVersion || !allowed.value) return
    detail.value = doc; detailState.value = doc ? 'ready' : 'error'
    if (!doc) detailMessage.value = '当前账号无法取得该物料，请核对链接及访问权限。'
  } catch (error) {
    if (disposed || version !== detailVersion || !allowed.value) return
    detailMessage.value = message(error); detailState.value = 'error'
  }
}
watch(() => [allowed.value, String(route.query.q || '')] as const, ([canRead, q]) => {
  ++searchVersion
  if (searchTimer) clearTimeout(searchTimer)
  keyword.value = q; rows.value = []; total.value = 0; truncated.value = false
  if (canRead) void runSearch()
}, { immediate: true })
watch(() => [allowed.value, selectedCode.value] as const, ([, code]) => { void loadDetail(code) }, { immediate: true })
onBeforeUnmount(() => {
  disposed = true; ++searchVersion; ++detailVersion
  if (searchTimer) clearTimeout(searchTimer)
})
</script>

<style scoped>
.master-page { display: flex; flex-direction: column; gap: 20px; }

.master-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.master-head h1 {
  margin: 0 0 4px;
  font-size: var(--hbos-font-page-title); line-height: var(--hbos-line-page-title);
  font-weight: var(--hbos-weight-strong); letter-spacing: -.4px;
}
.master-head p { margin: 0; color: var(--hbos-text-secondary); font-size: var(--hbos-font-body); line-height: var(--hbos-line-body); }
.master-count { color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); white-space: nowrap; }
.master-count b { font-family: var(--hbos-font-mono); color: var(--hbos-text-secondary); font-weight: var(--hbos-weight-strong); }
.master-mono { font-family: var(--hbos-font-mono); font-variant-numeric: tabular-nums; }

/* 只读 / 提示条 */
.master-note {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 12px 16px; border-radius: var(--hbos-radius-card);
  font-size: var(--hbos-font-body); line-height: var(--hbos-line-body);
}
.master-note .anticon { margin-top: 1px; flex: 0 0 auto; font-size: 20px; }
.master-note.info { background: rgba(75,156,255,.08); border: 1px solid rgba(75,156,255,.26); color: #2b5fa8; }
.master-note.warn { background: rgba(244,165,35,.10); border: 1px solid rgba(244,165,35,.30); color: #8a5a0b; }

/* 主从两栏 */
.master-split { display: grid; grid-template-columns: 340px minmax(0,1fr); gap: 20px; align-items: start; }

.master-list-pane {
  position: sticky; top: 88px;
  display: flex; flex-direction: column;
  max-height: calc(100vh - 140px);
  border-radius: var(--hbos-radius-card);
  background: #fff; border: 1px solid var(--hbos-border-default);
  box-shadow: var(--hbos-shadow-card);
  overflow: hidden;
}
.master-list-head {
  padding: 16px; border-bottom: 1px solid var(--hbos-border-default);
  display: flex; flex-direction: column; gap: 12px;
}
.master-hint { color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); line-height: 1.5; }
.master-hint b { color: var(--hbos-text-secondary); font-family: var(--hbos-font-mono); }
.master-list-body { overflow: auto; min-height: 0; }

/* 列表行 */
.master-row {
  display: block; width: 100%; text-align: left;
  padding: 12px 16px; border: 0; background: transparent;
  border-bottom: 1px solid var(--hbos-border-default);
}
.master-row:hover { background: #f7f9fc; }
.master-row.active { background: rgba(245,168,33,.14); box-shadow: inset 3px 0 #f5a821; }
.master-row b {
  display: block; font-size: var(--hbos-font-body); line-height: var(--hbos-line-body);
  font-weight: var(--hbos-weight-medium);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.master-row small {
  display: block; margin-top: 2px;
  color: var(--hbos-text-muted); font-family: var(--hbos-font-mono); font-size: var(--hbos-font-meta);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.master-row-tags { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }

/* 详情 */
.master-detail { min-width: 0; }
.master-detail-stack { display: flex; flex-direction: column; gap: 20px; }
.master-pane-head {
  display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  padding: 16px 20px; border-bottom: 1px solid var(--hbos-border-default);
}
.master-pane-head h2 { margin: 0; font-size: var(--hbos-font-section-title); line-height: var(--hbos-line-section-title); font-weight: var(--hbos-weight-strong); }
.master-sub { color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); }
.master-pane-body { padding: 20px; }

.master-kv { margin: 0; }
.master-kv > div {
  display: grid; grid-template-columns: minmax(120px,.4fr) minmax(0,1fr);
  gap: 16px; align-items: baseline;
  padding: 12px 0; border-top: 1px solid var(--hbos-border-default);
}
.master-kv > div:first-child { border-top: 0; }
.master-kv dt { color: var(--hbos-text-secondary); font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); }
.master-kv dd { margin: 0; font-size: var(--hbos-font-body); line-height: var(--hbos-line-body); word-break: break-word; }
.master-kv dd b { font-weight: var(--hbos-weight-medium); }

.master-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 0 8px; border-radius: var(--hbos-radius-pill); border: 1px solid transparent;
  font-size: var(--hbos-font-meta); line-height: 18px; font-weight: var(--hbos-weight-medium); white-space: nowrap;
}
.master-tag .anticon { font-size: 14px; }
.master-tag.ok { background: rgba(27,188,134,.10); border-color: rgba(27,188,134,.28); color: #0c6b4c; }
.master-tag.off { background: rgba(114,130,157,.10); border-color: var(--hbos-border-strong); color: var(--hbos-text-secondary); }
.master-tag.warn { background: rgba(244,165,35,.12); border-color: rgba(244,165,35,.34); color: #8a5a0b; }
.master-tag.plain { background: transparent; border-color: var(--hbos-border-default); color: var(--hbos-text-muted); font-weight: var(--hbos-weight-regular); }

.master-skel { border-radius: var(--hbos-radius-control); background: rgba(114,130,157,.11); animation: master-pulse 1.4s var(--hbos-ease-standard) infinite; }
@keyframes master-pulse { 0%,100% { opacity: 1 } 50% { opacity: .45 } }
.master-skel-row { height: 36px; margin-bottom: 8px; }
.master-skel-line { height: 20px; margin-bottom: 12px; }

@media (max-width: 1199px) {
  .master-split { grid-template-columns: minmax(0,1fr); }
  .master-list-pane { position: static; max-height: none; }
  .master-list-body { max-height: 420px; }
  .master-kv > div { grid-template-columns: minmax(0,1fr); gap: 4px; }
}
@media (max-width: 767px) {
  .master-head { flex-direction: column; }
  .master-count { text-align: left; }
  .master-pane-body { padding: 16px; }
}


.inventory-dest { border-radius: var(--hbos-radius-panel); overflow: hidden; }
.inventory-state { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
.inventory-state h3,.inventory-state p { margin: 0; }
.inventory-state-actions { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
.master-row { cursor: pointer; min-height: 44px; }
.master-row:focus-visible { outline: 2px solid var(--hbos-accent); outline-offset: -2px; }
@media (prefers-reduced-motion: reduce) { .master-skel { animation: none; } }

</style>
