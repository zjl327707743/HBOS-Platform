<template>
  <div class="page">
    <StbGateBanner />

    <div class="page-head">
      <div>
        <h1>考察申请与方案</h1>
        <p class="page-desc">通知单、方案、批次、储存条件和重点考察项目</p>
      </div>
      <div class="page-actions">
        <a-button @click="protocolOpen = true">
          <template #icon><FileTextOutlined /></template>
          打开方案
        </a-button>
        <a-button type="primary" @click="noticeRef?.show()">
          <template #icon><PlusOutlined /></template>
          新建通知
        </a-button>
      </div>
    </div>

    <div class="stb-subnav">
      <button
        v-for="t in TABS"
        :key="t.key"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <a-empty
      v-if="tab !== 'notice'"
      :description="`${TABS.find((t) => t.key === tab)?.label}沿用同一「列表 + 详情」布局，本轮原型未展开明细`"
      style="padding: 48px 0; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius)"
    />

    <div v-else class="stb-split">
      <div class="stb-list-panel">
        <div class="stb-list-panel-head">
          <b>考察通知</b>
          <span class="stb-list-count">共 12 条</span>
        </div>
        <div class="stb-list-filter">
          <a-input v-model:value="keyword" placeholder="搜索通知单 / 产品" allow-clear />
          <a-select v-model:value="statusFilter" :options="statusOptions" style="width: 140px" />
        </div>
        <div
          v-for="n in filteredNotices"
          :key="n.name"
          class="stb-list-row"
          :class="{ active: selected?.name === n.name }"
          @click="selected = n"
        >
          <div class="stb-list-row-top">
            <span class="stb-list-row-title mono">{{ n.name }}</span>
            <span :class="toneClass(n.tone)">{{ n.status }}</span>
          </div>
          <div class="stb-list-row-sub">
            {{ n.product }} · {{ n.category }}<br />{{ n.meta }}
          </div>
        </div>
        <a-empty v-if="!filteredNotices.length" description="无匹配通知单" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 20px 0" />
      </div>

      <div class="stb-detail-panel">
        <template v-if="selected">
          <div class="stb-detail-head">
            <div>
              <h2 class="mono">{{ selected.name }}</h2>
              <p>{{ selected.product }} · 稳定性考察申请通知单</p>
            </div>
            <div class="page-actions">
              <a-button size="small" @click="auditRef?.show()">审计</a-button>
              <a-button size="small" type="primary" @click="protocolOpen = true">查看方案</a-button>
            </div>
          </div>
          <div class="stb-detail-body">
            <div class="stat-row">
              <div v-for="s in NOTICE_DETAIL.stats" :key="s.label" class="stat-card">
                <div class="stat-label">{{ s.label }}</div>
                <div class="stat-value">{{ s.value }}</div>
              </div>
            </div>

            <div class="stb-flow">
              <template v-for="(f, i) in NOTICE_DETAIL.flow" :key="f.label">
                <div class="stb-flow-step" :class="f.state">
                  <div class="stb-flow-dot">{{ f.state === 'done' ? '✓' : i + 1 }}</div>
                  <div class="stb-flow-label">{{ f.label }}</div>
                </div>
                <div v-if="i < NOTICE_DETAIL.flow.length - 1" class="stb-flow-line"></div>
              </template>
            </div>

            <div class="stb-kv-grid">
              <div v-for="k in NOTICE_DETAIL.fields" :key="k.label" class="stb-kv">
                <label>{{ k.label }}</label>
                <b :class="{ mono: k.mono }">{{ k.value }}</b>
              </div>
            </div>

            <div class="panel" style="box-shadow: none">
              <div class="panel-head">
                <div>
                  <div class="panel-title">方案冻结摘要</div>
                  <div class="panel-sub">批准后只读，变更通过新版本或变更实施入口完成</div>
                </div>
                <span class="pill pill-muted">快照 v2</span>
              </div>
              <div class="panel-body no-pad">
                <a-table
                  :columns="frozenColumns"
                  :data-source="NOTICE_DETAIL.frozen"
                  size="small"
                  row-key="condition"
                  :pagination="false"
                  :scroll="{ x: 720 }"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'condition'">
                      <div class="stb-cell-strong">{{ record.condition }}</div>
                      <div class="dim">{{ record.condSub }}</div>
                    </template>
                    <template v-else-if="column.key === 'room'"><span class="mono">{{ record.room }}</span></template>
                    <template v-else-if="column.key === 'status'"><span class="pill pill-pass">已冻结</span></template>
                  </template>
                </a-table>
              </div>
            </div>
          </div>
        </template>
        <a-empty v-else description="从左侧选择一份考察通知查看" style="padding: 48px 0" />
      </div>
    </div>

    <StbNoticeDrawer ref="noticeRef" />
    <StbAuditDrawer ref="auditRef" />

    <a-drawer v-model:open="protocolOpen" title="稳定性方案详情" :width="520" placement="right">
      <p class="stb-gate-sub">{{ NOTICE_DETAIL.name }} · Protocol v2</p>
      <div class="stb-drawer-section">
        <h3>批准后冻结内容</h3>
        <div class="stb-drawer-kv">
          <div><label>批次</label><b>3 批</b></div>
          <div><label>条件</label><b>3 个</b></div>
          <div><label>时间点</label><b>18 个</b></div>
          <div><label>项目</label><b>8 项</b></div>
          <div><label>房间</label><b>STB-RM-01 / 02</b></div>
          <div><label>快照版本</label><b>Protocol v2</b></div>
        </div>
      </div>
      <div class="stb-drawer-section">
        <h3>版本链</h3>
        <div class="stb-audit-line">
          <span class="stb-audit-dot"></span>
          <div><strong>v2 · 已批准 · 当前执行</strong><span>2026-09-02 · 林质检</span></div>
        </div>
        <div class="stb-audit-line">
          <span class="stb-audit-dot gray"></span>
          <div><strong>v1 · 已取代</strong><span>2026-08-20 · 变更单 STB-CHG-0001</span></div>
        </div>
      </div>
      <template #footer>
        <a-button @click="protocolOpen = false">关闭</a-button>
        <a-button type="primary" @click="protocolOpen = false">查看冻结快照</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Empty } from 'ant-design-vue'
import { FileTextOutlined, PlusOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import StbNoticeDrawer from '@/components/stability/StbNoticeDrawer.vue'
import StbAuditDrawer from '@/components/stability/StbAuditDrawer.vue'
import { NOTICES, NOTICE_DETAIL, toneClass, type NoticeRow } from '@/demo/stabilityDemo'

const noticeRef = ref<InstanceType<typeof StbNoticeDrawer> | null>(null)
const auditRef = ref<InstanceType<typeof StbAuditDrawer> | null>(null)

const TABS = [
  { key: 'notice', label: '通知单' },
  { key: 'protocol', label: '稳定性方案' },
  { key: 'product', label: '产品规则' },
  { key: 'condition', label: '条件与项目' },
] as const

const tab = ref<(typeof TABS)[number]['key']>('notice')
const selected = ref<NoticeRow | null>(NOTICES[0])
const keyword = ref('')
const statusFilter = ref<string | undefined>(undefined)
const protocolOpen = ref(false)

const statusOptions = ['全部状态', '草稿', '已批准'].map((v) => ({ value: v, label: v }))

const filteredNotices = computed(() =>
  NOTICES.filter((n) => {
    const kw = keyword.value.trim()
    if (kw && !`${n.name}${n.product}`.includes(kw)) return false
    if (statusFilter.value && statusFilter.value !== '全部状态' && n.status !== statusFilter.value) return false
    return true
  }),
)

const frozenColumns = [
  { title: '条件', key: 'condition', width: 170 },
  { title: '房间', key: 'room', width: 110 },
  { title: '时间点', key: 'points', dataIndex: 'points', width: 230 },
  { title: '项目', key: 'items', dataIndex: 'items', width: 220 },
  { title: '状态', key: 'status', width: 100 },
]
</script>

<style scoped>
.stb-list-filter {
  display: flex;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid var(--line);
  flex-wrap: wrap;
}
.stb-cell-strong { color: var(--ink); font-weight: 700; }
</style>
