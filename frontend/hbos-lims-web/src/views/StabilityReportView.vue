<template>
  <div class="page">
    <StbGateBanner />

    <div class="page-head">
      <div>
        <h1>报告与有效期</h1>
        <p class="page-desc">稳定性报告审核批准、版本链和有效期外推辅助</p>
      </div>
      <div class="page-actions">
        <a-button @click="reportOpen = true">
          <template #icon><FileTextOutlined /></template>
          打开报告
        </a-button>
        <a-button type="primary" @click="toast('QA 判定动作已打开（原型）')">
          <template #icon><SafetyCertificateOutlined /></template>
          QA 判定
        </a-button>
      </div>
    </div>

    <div class="filter-bar">
      <a-input v-model:value="keyword" placeholder="搜索报告 / 产品 / 客户" allow-clear style="flex: 1; min-width: 200px" />
      <a-select v-model:value="typeFilter" :options="typeOptions" style="width: 170px" />
      <a-select v-model:value="statusFilter" :options="statusOptions" style="width: 150px" />
    </div>

    <div class="stb-three-col">
      <!-- 报告列表 -->
      <div class="panel" style="margin-bottom: 0">
        <div class="panel-head">
          <div>
            <div class="panel-title">报告列表</div>
            <div class="panel-sub">当前产品 6 份报告</div>
          </div>
        </div>
        <div
          v-for="r in filteredReports"
          :key="r.name"
          class="stb-list-row"
          :class="{ active: selected?.name === r.name }"
          @click="selected = r"
        >
          <div class="stb-list-row-top">
            <span class="stb-list-row-title mono">{{ r.name }}</span>
            <span :class="toneClass(r.tone)">{{ r.status }}</span>
          </div>
          <div class="stb-list-row-sub">{{ r.product }} · {{ r.type }}<br />{{ r.period }}</div>
        </div>
        <a-empty v-if="!filteredReports.length" description="无匹配报告" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 20px 0" />
      </div>

      <!-- 报告摘要 -->
      <div class="panel" style="margin-bottom: 0">
        <div class="panel-head">
          <div>
            <div class="panel-title">报告摘要</div>
            <div class="panel-sub">{{ REPORT_DETAIL.name }} · 当前版本 v1</div>
          </div>
          <div class="page-actions">
            <a-button size="small" @click="versionOpen = true">版本链</a-button>
            <span class="pill pill-muted">快照只读</span>
          </div>
        </div>
        <div class="panel-body">
          <div class="stat-row">
            <div v-for="s in REPORT_DETAIL.stats" :key="s.label" class="stat-card">
              <div class="stat-label">{{ s.label }}</div>
              <div class="stat-value" :class="{ danger: s.danger }">{{ s.value }}</div>
            </div>
          </div>
          <div class="stb-kv-grid">
            <div v-for="f in REPORT_DETAIL.fields" :key="f.label" class="stb-kv">
              <label>{{ f.label }}</label>
              <b :class="{ mono: f.mono }">{{ f.value }}</b>
            </div>
          </div>
          <div class="stb-flow">
            <template v-for="(f, i) in REPORT_DETAIL.flow" :key="f.label">
              <div class="stb-flow-step" :class="f.state">
                <div class="stb-flow-dot">{{ f.state === 'done' ? '✓' : i + 1 }}</div>
                <div class="stb-flow-label">{{ f.label }}</div>
              </div>
              <div v-if="i < REPORT_DETAIL.flow.length - 1" class="stb-flow-line"></div>
            </template>
          </div>
          <div class="stb-notice">{{ REPORT_DETAIL.note }}</div>
        </div>
      </div>

      <!-- 有效期外推助手 -->
      <div class="panel" style="margin-bottom: 0">
        <div class="panel-head">
          <div>
            <div class="panel-title">有效期外推助手</div>
            <div class="panel-sub">只提供建议，不自动确定有效期</div>
          </div>
          <span class="pill pill-warn">建议态</span>
        </div>
        <div class="panel-body">
          <div class="stb-assistant">
            <h3>{{ EXTRAPOLATION.title }}</h3>
            <p>{{ EXTRAPOLATION.desc }}</p>

            <div class="stb-assistant-grid" v-show="adviceOpen">
              <div v-for="b in EXTRAPOLATION.boxes" :key="b.label" class="stb-assistant-box">
                <label>{{ b.label }}</label>
                <b :class="adviceToneClass(b.tone)">{{ b.value }}</b>
              </div>
            </div>

            <div class="page-actions" style="margin-bottom: 12px">
              <a-button size="small" @click="adviceOpen = !adviceOpen">
                {{ adviceOpen ? '收起建议依据' : '展开建议依据' }}
              </a-button>
            </div>

            <div class="stb-notice amber">{{ EXTRAPOLATION.todo }}</div>
            <div class="page-actions" style="margin-top: 12px">
              <router-link to="/stability/results"><a-button size="small">查看趋势</a-button></router-link>
              <a-button size="small" type="primary" @click="toast('QA 判定已进入草稿（原型）')">提交 QA 判定</a-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 报告详情（批准前硬前置） -->
    <a-drawer v-model:open="reportOpen" title="稳定性报告详情" :width="520" placement="right">
      <p class="stb-gate-sub">{{ REPORT_DETAIL.name }} · 待批准</p>
      <div class="stb-drawer-section">
        <h3>批准前硬前置</h3>
        <div v-for="(b, i) in REPORT_DETAIL.blockers" :key="i" class="stb-audit-line">
          <span class="stb-audit-dot" :class="{ amber: !b.done }"></span>
          <div><strong>{{ b.title }}</strong><span>{{ b.desc }}</span></div>
        </div>
      </div>
      <div class="stb-notice">
        有效期外推助手只提供建议区间；QA 判定和报告批准是独立操作，不由前端自动完成。
      </div>
      <template #footer>
        <a-button @click="reportOpen = false">关闭</a-button>
        <a-button type="primary" @click="reportOpen = false; toast('QA 判定动作已打开（原型）')">打开 QA 判定</a-button>
      </template>
    </a-drawer>

    <!-- 版本链 -->
    <a-drawer v-model:open="versionOpen" title="报告版本链" :width="520" placement="right">
      <p class="stb-gate-sub">{{ REPORT_DETAIL.name }} · 冻结快照与版本链</p>
      <div class="stb-drawer-section">
        <h3>版本</h3>
        <div class="stb-audit-line">
          <span class="stb-audit-dot amber"></span>
          <div><strong>v1 · 待批准 · 当前版本</strong><span>2026-09-15 · 赵 QC 审核完成</span></div>
        </div>
        <div class="stb-audit-line">
          <span class="stb-audit-dot gray"></span>
          <div><strong>v0 · 已取代</strong><span>2026-09-10 · 草稿阶段被替换</span></div>
        </div>
      </div>
      <div class="stb-notice">
        批准后报告快照与版本链锁定，修改须走新版本；来源为
        <span class="mono">Protocol v2 / Result v1</span>。
      </div>
      <template #footer>
        <a-button @click="versionOpen = false">关闭</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { FileTextOutlined, SafetyCertificateOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import { EXTRAPOLATION, REPORTS, REPORT_DETAIL, toneClass, type ReportRow, type Tone } from '@/demo/stabilityDemo'

const keyword = ref('')
const typeFilter = ref('全部报告类型')
const statusFilter = ref('全部状态')
const selected = ref<ReportRow | null>(REPORTS[0])
const reportOpen = ref(false)
const versionOpen = ref(false)
const adviceOpen = ref(true)

const typeOptions = ['全部报告类型', '阶段性报告', '年度持续报告', '总结报告'].map((v) => ({ value: v, label: v }))
const statusOptions = ['全部状态', '待审核', '待批准', '已批准'].map((v) => ({ value: v, label: v }))

const filteredReports = computed(() =>
  REPORTS.filter((r) => {
    const kw = keyword.value.trim()
    if (kw && !`${r.name}${r.product}`.includes(kw)) return false
    if (typeFilter.value !== '全部报告类型' && r.type !== typeFilter.value) return false
    if (statusFilter.value !== '全部状态' && r.status !== statusFilter.value) return false
    return true
  }),
)

function adviceToneClass(tone: Tone): string {
  if (tone === 'warn') return 'warn-text'
  if (tone === 'danger') return 'danger-text'
  return 'good-text'
}

function toast(msg: string) {
  message.success(msg)
}
</script>

<style scoped>
.good-text { color: var(--pass); }
.warn-text { color: var(--warn); }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
</style>
