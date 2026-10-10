<template>
  <div class="production-board">
    <!-- 页头 -->
    <header class="pb-head">
      <div>
        <span class="pb-kicker">{{ isCenter ? 'Production · Center' : 'Production · Baseline' }}</span>
        <h1>{{ isCenter ? '生产管理中心看板' : '基层管理人员看板' }}</h1>
        <p class="pb-sub">
          {{ isCenter ? '月度产量达成、工艺改进与异常升级' : '车间生产状态、产量达成与产线异常' }}
        </p>
      </div>
      <div class="pb-meta">
        <b>{{ board ? monthLabel(board.month) : '—' }}</b>
        <span v-if="board">数据月份 {{ board.month }} · 本月已过 {{ board.daysElapsed }} 天</span>
      </div>
    </header>

    <!-- 加载中。**必须与「未接入」分开** —— 冷缓存时服务端要拉 9 张飞书表，
         20~30 秒。不加这个态的话，这段时间页面会显示「未接入」，用户以为坏了。 -->
    <section v-if="phase === 'loading'" class="pb-panel pb-skeleton" aria-busy="true" aria-live="polite">
      <div class="pb-skel pb-skel-kpi"></div>
      <div class="pb-skel pb-skel-row"></div>
      <div class="pb-skel pb-skel-row"></div>
      <div class="pb-skel pb-skel-row"></div>
      <p class="pb-skel-note">正在取生产数据…（首次打开约需 20–30 秒）</p>
    </section>

    <!-- 未接入：**取不到**才显示。数据接通前不显示任何数字 -->
    <section v-else-if="phase === 'unavailable'" class="pb-panel pb-state">
      <ThunderboltOutlined class="pb-state-ic" />
      <h3>看板数据还没接通</h3>
      <p>
        这一页的数字来自飞书多维表格，经独立取数服务聚合后提供。
        取数服务暂时不可用，所以这里<b>不显示任何数字</b>——宁可不给，也不给一个看起来像真实产量的占位值。
      </p>
      <p>页面结构与字段口径已经定稿，数据接通后按同一套结构填充，不再改版。</p>
    </section>

    <!-- `v-else-if="board"` 而不是 `v-else` —— 让 TS 把 board 收窄成非 null
         （ready 态必然有数据，这个不变式写在条件里比在代码里更稳）。 -->
    <template v-else-if="board">
      <!-- 月度关键指标 -->
      <section class="pb-kpis" aria-label="月度关键指标">
        <div class="pb-panel pb-kpi">
          <div class="pb-kpi-top"><span class="pb-kpi-lb">当月计划完成率</span><span class="pb-kpi-vl">{{ planRateText }}</span></div>
          <div class="pb-bar"><i :style="{ width: planRatePct + '%' }" /></div>
          <div class="pb-kpi-fn">{{ planRateNote }}</div>
        </div>
        <div class="pb-panel pb-kpi">
          <div class="pb-kpi-top"><span class="pb-kpi-lb">收率达标率</span><span class="pb-kpi-vl">{{ yieldRateText }}</span></div>
          <div class="pb-bar"><i :style="{ width: yieldRatePct + '%' }" /></div>
          <div class="pb-kpi-fn">{{ yieldRateNote }}</div>
        </div>
        <div class="pb-panel pb-kpi">
          <div class="pb-kpi-top"><span class="pb-kpi-lb">质量合格率</span><span class="pb-kpi-vl">{{ qualityRateText }}</span></div>
          <div class="pb-bar"><i :style="{ width: qualityRatePct + '%' }" /></div>
          <div class="pb-kpi-fn">沿用既有看板口径 · 成品质量数据源接入前</div>
        </div>
        <div class="pb-panel pb-kpi">
          <div class="pb-kpi-top">
            <span class="pb-kpi-lb">异常闭环率</span>
            <span class="pb-kpi-vl" :class="{ 'pb-tbd': anomalyRateText === null }">{{ anomalyRateText ?? '暂无数据' }}</span>
          </div>
          <div v-if="anomalyRatePct !== null" class="pb-bar"><i :style="{ width: anomalyRatePct + '%' }" /></div>
          <div class="pb-kpi-fn" :class="{ 'pb-kpi-fn-gap': anomalyRatePct === null }">{{ anomalyNote }}</div>
        </div>
      </section>

      <div class="pb-cols">
        <!-- 当月生产累计完成情况 -->
        <section class="pb-panel">
          <div class="pb-sec-head">
            <i /><h2>当月生产累计完成情况</h2>
            <span class="pb-note">{{ board.month }} · 在产 {{ board.rows.length }} 个产品</span>
          </div>
          <div class="pb-tbl-wrap">
            <table class="pb-tbl">
              <thead>
                <tr>
                  <th>产品</th>
                  <th class="num">完成</th>
                  <th class="num">目标</th>
                  <th class="num pb-col-rate">完成率</th>
                  <th class="num">收率</th>
                  <th v-if="!isCenter" class="num">昨日入库</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in board.rows" :key="row.label">
                  <td class="pb-name">{{ row.label }}</td>
                  <td class="num">{{ row.done }}</td>
                  <td class="num pb-dim">{{ row.target }}</td>
                  <td>
                    <span class="pb-rate">
                      <span class="pb-track" :class="{ full: completion(row) >= 1 }">
                        <i :style="{ width: Math.min(100, completion(row) * 100) + '%' }" />
                      </span>
                      <span class="pb-pct">{{ pctText(completion(row)) }}</span>
                    </span>
                  </td>
                  <td class="num">
                    <template v-if="row.yieldRate !== null">
                      {{ (row.yieldRate * 100).toFixed(1) }}
                      <span
                        class="pb-dot"
                        :class="yieldMeets(row) ? 'ok' : 'no'"
                        :title="row.targetYieldRate !== null ? `目标收率 ${(row.targetYieldRate * 100).toFixed(1)}%` : ''"
                      />
                    </template>
                    <template v-else>
                      <span class="pb-dim">—</span><span class="pb-dot na" title="无收率数据" />
                    </template>
                  </td>
                  <td v-if="!isCenter" class="num">
                    <template v-if="row.yesterdayInbound !== null">{{ row.yesterdayInbound.toFixed(1) }}</template>
                    <span v-else class="pb-dim">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="pb-foot-note">
            <b>完成率 = 已生产批次 ÷ 目标批次</b>（批数口径）。目标 = <code>月度生产计划明细</code> 1–31 日求和；
            完成与收率按<b>收料日期</b>落月；目标收率取 <code>月度目标产能.目标收率</code>（合并行按计划批数加权）。<br>
            <b>本月已过 {{ board.daysElapsed }} 天</b>，累计完成率天然偏低 —— 这是月初基准，不是产线异常。<br>
            <span v-if="!isCenter">昨日入库 = 前一日按<b>收料日期</b>的产量求和。</span>
          </div>
        </section>

        <div class="pb-stack">
          <!-- 基层版：收率跟踪 + 重点关注 -->
          <template v-if="!isCenter">
            <section class="pb-panel">
              <div class="pb-sec-head"><i class="warn" /><h2>产品收率质量跟踪</h2></div>
              <ul class="pb-list">
                <li v-for="row in yieldRows" :key="row.label">
                  <span>
                    <b>{{ row.label }}</b>
                    {{ (row.yieldRate! * 100).toFixed(1) }}%<template v-if="row.targetYieldRate !== null">
                      ，目标 {{ (row.targetYieldRate * 100).toFixed(1) }}%，差 {{ deltaText(row) }}pt</template>
                  </span>
                </li>
                <li v-if="!yieldRows.length"><span class="pb-dim">本月尚无收率数据</span></li>
              </ul>
            </section>

            <section class="pb-panel">
              <div class="pb-sec-head"><i class="warn" /><h2>重点关注</h2></div>
              <ul class="pb-list">
                <li>
                  <span><b>月初基准</b>：本月已过 {{ board.daysElapsed }} 天，各行累计都接近 0，属正常</span>
                </li>
                <li v-if="biggestTarget">
                  <span><b>{{ biggestTarget.label }}</b> 目标 {{ biggestTarget.target }} 批，为全场最大</span>
                </li>
                <li>
                  <span>收率达标 {{ metCount }} / {{ yieldRows.length }}</span>
                </li>
              </ul>
            </section>
          </template>

          <!-- 管理版：异常汇报 —— 放右列，与左列「完成情况」等高，凑成平衡的两栏。
               AI 工艺提升面板**不在这里** —— 它 62 道工序，放右列会把页面拉长到
               2700px，故移到下方独占整行（见本块结束后那个 section）。 -->
          <template v-else>
            <section class="pb-panel">
              <div class="pb-sec-head"><i class="crit" /><h2>异常汇报</h2><span class="pb-note">管理层向 · 近 12 个月</span></div>
              <div v-if="!anomaly" class="pb-foot-note">异常数据暂不可用。</div>
              <template v-else>
                <div class="pb-tbl-wrap">
                  <table class="pb-tbl">
                    <thead>
                      <tr>
                        <th>车间</th><th>闭环口径</th>
                        <th class="num">异常</th><th class="num">已闭环</th><th class="num">闭环率</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="w in anomaly.byWorkshop" :key="w.name">
                        <td class="pb-name">{{ w.name }}</td>
                        <td class="pb-dim">{{ w.closureLabel }}</td>
                        <td class="num">{{ w.total }}</td>
                        <td class="num">{{ w.closed }}</td>
                        <td class="num">
                          <template v-if="w.rate !== null">{{ (w.rate * 100).toFixed(1) }}%</template>
                          <span v-else class="pb-dim" title="窗口内无异常 —— 不是 0% 闭环">—</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="pb-foot-note">
                  <b>闭环 = <code>事件原因</code> 非空</b>（全车间统一口径）。<br>
                  六车间空表 + 日报「未发生」= <b>该车间没有异常事件</b>，不计入比率（显示 <code>—</code>，不是 0%）。<br>
                  <b>窗口</b>：近 {{ anomaly.windowMonths }} 个自然月（{{ anomaly.windowStart.slice(0, 7) }} 起）——
                  异常是稀疏事件，按当月取分母常为 0，比率会失真。
                </div>
              </template>
            </section>
          </template>
        </div>
      </div>

      <!-- 工艺提升与改进方案（AI）—— 管理层专有，**独占整行**放两栏之下。
           62 道工序塞进右列会把页面撑到 2700px、左右严重失衡；独占整行后
           左列（完成情况）与右列（异常汇报）等高，下区再横向铺开 AI 结论，
           三块重量级内容各占一层，版面才平。
           表内用 max-height + 滚动，展开也不再把整页拉长。 -->
      <section v-if="isCenter" class="pb-panel pb-ai">
        <div class="pb-sec-head">
          <i class="warn" /><h2>工艺提升与改进方案</h2>
          <span class="pb-note">{{ aiLoading ? 'AI 分析 · 读取中' : (aiRows.length ? 'AI 分析 · 每天 16:30 更新' : 'AI 分析 · 暂无结果') }}</span>
        </div>
        <div v-if="aiLoading" class="pb-foot-note">正在读取分析结果…</div>
        <div v-else-if="!aiRows.length" class="pb-foot-note">
          会议口径：基于各产品的<b>工艺描述文档与生产台账数据</b>，由 AI 自动分析生成优化建议。<br>
          结果表里还没有数据。分析服务每工作日 16:30 生成一次；若无结果，可能是模型不可用或校验未通过
          （<b>校验不过不写库</b>，宁可这轮没有，也不让没通过校验的内容进看板）。
        </div>
        <template v-else>
          <div class="pb-ai-bar">
            <b>{{ aiProductCount }}</b> 个产品 · <b>{{ aiRows.length }}</b> 道工序
            <span class="pb-grade bad">未达标 {{ aiCounts.bad }}</span>
            <span class="pb-grade part">部分达到 {{ aiCounts.part }}</span>
            <span class="pb-grade lack">数据不足 {{ aiCounts.lack }}</span>
            <span class="pb-grade ok">已达标 {{ aiCounts.ok }}</span>
            <span class="pb-dim">按严重度排序 · 数据不足＝台账缺参数，AI 不臆测</span>
          </div>
          <div class="pb-tbl-wrap pb-ai-scroll" :class="{ 'is-open': aiShowAll }">
            <table class="pb-tbl">
              <thead>
                <tr><th>产品</th><th>工序</th><th>结论摘要</th><th>评级</th><th>分析日期</th></tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in visibleAiRows" :key="i">
                  <td class="pb-name">{{ r.product }}</td>
                  <td>{{ r.process }}</td>
                  <td class="pb-dim">{{ r.summary }}</td>
                  <td><span class="pb-grade" :class="gradeClass(r.grade)">{{ r.grade }}</span></td>
                  <td class="pb-dim">{{ r.analyzedAt ? r.analyzedAt.slice(0, 10) : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="aiRows.length > AI_PREVIEW" class="pb-ai-foot">
            <button class="pb-toggle" @click="aiShowAll = !aiShowAll">
              {{ aiShowAll ? `收起（只显示前 ${AI_PREVIEW} 条）` : `展开全部 ${aiRows.length} 条 ▼` }}
            </button>
          </div>
          <div class="pb-foot-note">
            结果表 <code>AI工艺分析结果</code> · 每工作日 16:30 自动生成 · 按工序幂等覆盖，不追加。
          </div>
        </template>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ThunderboltOutlined } from '@ant-design/icons-vue'
import { PRODUCTION_CENTER_PATH } from '@/data/productionNav'
import {
  fetchProductionBoard,
  fetchAiAnalysis,
  type ProductionBoardData,
  type ProductionRow,
  type AiAnalysisRow,
} from '@/services/productionBoard'

const route = useRoute()
const isCenter = computed(() => route.path === PRODUCTION_CENTER_PATH)

/** 加载 → 取不到 → 就绪。**三态分开**，见模板里的说明。 */
const phase = ref<'loading' | 'unavailable' | 'ready'>('loading')
const board = ref<ProductionBoardData | null>(null)
const aiRows = ref<AiAnalysisRow[]>([])
const anomaly = computed(() => board.value?.anomaly ?? null)
const aiLoading = ref(false)

// --- AI 工艺分析面板：排序 + 计数 + 折叠 ---
/** 未展开时最多显示多少行（62 道工序全铺开太长）。 */
const AI_PREVIEW = 12
const aiShowAll = ref(false)

/** 评级严重度：未达标最前，已达标最后（先看该处理的）。 */
const GRADE_RANK: Record<string, number> = { 未达标: 0, 部分达到: 1, 数据不足: 2, 已达标: 3 }
const sortedAiRows = computed(() =>
  [...aiRows.value].sort(
    (a, b) => (GRADE_RANK[a.grade] ?? 9) - (GRADE_RANK[b.grade] ?? 9),
  ),
)
const visibleAiRows = computed(() =>
  aiShowAll.value ? sortedAiRows.value : sortedAiRows.value.slice(0, AI_PREVIEW),
)
const aiCounts = computed(() => {
  const c = { bad: 0, part: 0, lack: 0, ok: 0 }
  for (const r of aiRows.value) {
    if (r.grade === '未达标') c.bad += 1
    else if (r.grade === '部分达到') c.part += 1
    else if (r.grade === '已达标') c.ok += 1
    else c.lack += 1
  }
  return c
})
const aiProductCount = computed(() => new Set(aiRows.value.map((r) => r.product)).size)

const monthLabel = (m: string) => {
  const [y, mo] = m.split('-')
  return y && mo ? `${y} 年 ${Number(mo)} 月` : m
}

// --- KPI 汇总（口径：只计入目标 > 0 的行，避免未排产行稀释分母）---
const targetRows = computed(() => (board.value?.rows || []).filter((r) => r.target > 0))
const totalDone = computed(() => targetRows.value.reduce((s, r) => s + r.done, 0))
const totalTarget = computed(() => targetRows.value.reduce((s, r) => s + r.target, 0))
const planRatePct = computed(() =>
  totalTarget.value > 0 ? (totalDone.value / totalTarget.value) * 100 : 0,
)
const planRateText = computed(() => `${planRatePct.value.toFixed(1)}%`)
const planRateNote = computed(() => `${totalDone.value} / ${totalTarget.value} 批 · 批数口径`)

const yieldRows = computed(() => (board.value?.rows || []).filter((r) => r.yieldRate !== null))
const metCount = computed(() => yieldRows.value.filter((r) => yieldMeets(r)).length)
const yieldRatePct = computed(() =>
  yieldRows.value.length > 0 ? (metCount.value / yieldRows.value.length) * 100 : 0,
)
const yieldRateText = computed(() => `${yieldRatePct.value.toFixed(1)}%`)
const yieldRateNote = computed(() =>
  yieldRows.value.length ? `${metCount.value} / ${yieldRows.value.length} 个有收率数据的品种达标` : '本月尚无收率数据',
)

const biggestTarget = computed(() =>
  [...targetRows.value].sort((a, b) => b.target - a.target)[0] || null,
)

// 质量合格率：**沿用既有 openclaw 看板的固定口径 99.9%**（Owner 2026-10-10 定）。
// 现有《产品质量数据汇总》是合格放行台账，不收录不合格批，算出来恒为 100%，
// 不如沿用既有口径。成品质量数据源接入后再改成实算。取数服务暂不返回该值，
// 故先写死；将来接了服务端可用 `board.qualityRate ?? 0.999`。
const QUALITY_RATE = 0.999
const qualityRatePct = computed(() => QUALITY_RATE * 100)
const qualityRateText = computed(() => `${(QUALITY_RATE * 100).toFixed(1)}%`)

const anomalyRatePct = computed(() =>
  anomaly.value && anomaly.value.rate !== null ? anomaly.value.rate * 100 : null,
)
const anomalyRateText = computed(() =>
  anomalyRatePct.value === null ? null : `${anomalyRatePct.value.toFixed(1)}%`,
)
const anomalyNote = computed(() => {
  const a = anomaly.value
  if (!a) return '异常数据暂不可用'
  if (a.rate === null) return '近 12 个月无异常记录'
  // **不报「共 N 个车间」** —— 车间是陆续收集的（五车间还没到），
  // 写总数会让人以为是全部车间，而实际只有已收集的那几个。
  return `${a.closed} / ${a.total} 条`
})

function completion(row: ProductionRow): number {
  return row.target > 0 ? row.done / row.target : 0
}
/** 评级 → 颜色档（已达标 ok / 部分达到 part / 数据不足 lack / 未达标 bad）。 */
function gradeClass(grade: string): string {
  if (grade === '已达标') return 'ok'
  if (grade === '部分达到') return 'part'
  if (grade === '未达标') return 'bad'
  return 'lack'
}
function pctText(v: number): string {
  return v > 0 ? `${(v * 100).toFixed(1)}%` : '—'
}
function yieldMeets(row: ProductionRow): boolean {
  return row.yieldRate !== null && row.targetYieldRate !== null && row.yieldRate >= row.targetYieldRate
}
function deltaText(row: ProductionRow): string {
  if (row.yieldRate === null || row.targetYieldRate === null) return '—'
  const d = Math.abs(row.targetYieldRate - row.yieldRate) * 100
  return d.toFixed(1)
}

onMounted(async () => {
  // 两个页面共用同一份看板数据（原型 §4.3：上区逐字一致）
  const data = await fetchProductionBoard()
  if (data) {
    board.value = data
    phase.value = 'ready'
  } else {
    phase.value = 'unavailable'
  }
  if (isCenter.value) {
    aiLoading.value = true
    try {
      aiRows.value = await fetchAiAnalysis()
    } finally {
      aiLoading.value = false
    }
  }
})
</script>

<style scoped>
/* 生产看板的样式。与 Portal 亮色体系同源（原型 REV 7 的视觉），
   但收在此处、不改 global.css —— 避免影响其他页面。 */
.production-board { display: flex; flex-direction: column; gap: 16px; }

.pb-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; flex-wrap: wrap; padding: 8px 0 4px; }
.pb-kicker { display: block; margin-bottom: 8px; font-size: 11px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--hbos-brand-violet); }
.pb-head h1 { margin: 0 0 6px; font-size: 30px; line-height: 38px; font-weight: 600; letter-spacing: -.6px; color: var(--hbos-text-primary); }
.pb-sub { margin: 0; font-size: 14px; color: var(--hbos-text-secondary); }
.pb-meta { text-align: right; font-size: 12px; color: var(--hbos-text-muted); white-space: nowrap; }
.pb-meta b { display: block; font-size: 14px; font-weight: 600; color: var(--hbos-text-secondary); }

.pb-panel { background: rgba(255,255,255,.74); border: 1px solid rgba(255,255,255,.92); border-radius: 22px; box-shadow: 0 10px 34px rgba(61,88,136,.08); backdrop-filter: blur(20px); min-width: 0; }

.pb-skeleton { padding: 24px; display: flex; flex-direction: column; gap: 12px; }
.pb-skel {
  border-radius: 14px;
  background: linear-gradient(90deg, rgba(65,91,138,.07), rgba(65,91,138,.12), rgba(65,91,138,.07));
  background-size: 200% 100%;
  animation: pb-shimmer 1.6s ease-in-out infinite;
}
@keyframes pb-shimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
.pb-skel-kpi { height: 112px; }
.pb-skel-row { height: 48px; }
.pb-skel-note { margin: 4px 0 0; font-size: 12px; color: var(--hbos-text-muted); }

.pb-state { padding: 56px 34px; display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
.pb-state-ic { font-size: 32px; color: var(--hbos-status-warning); }
.pb-state h3 { margin: 0; font-size: 20px; font-weight: 600; color: var(--hbos-text-primary); }
.pb-state p { margin: 0; max-width: 80ch; font-size: 14px; line-height: 1.75; color: var(--hbos-text-secondary); }

.pb-kpis { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 16px; }
.pb-kpi { padding: 20px 22px 18px; display: flex; flex-direction: column; }
.pb-kpi-top { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.pb-kpi-lb { font-size: 12px; font-weight: 600; color: var(--hbos-text-muted); }
.pb-kpi-vl { font-size: 34px; line-height: 42px; font-weight: 600; letter-spacing: -.02em; color: var(--hbos-text-primary); font-variant-numeric: tabular-nums; }
.pb-kpi-vl.pb-tbd { font-size: 16px; line-height: 42px; font-weight: 400; color: var(--hbos-text-muted); }
.pb-bar { margin-top: 12px; height: 7px; border-radius: 999px; background: rgba(65,91,138,.09); overflow: hidden; }
.pb-bar > i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg,#6c63ff,#42b9d1); }
.pb-kpi-fn { margin-top: 10px; font-size: 11px; line-height: 1.5; color: var(--hbos-text-muted); }
.pb-kpi-fn-gap { margin-top: 14px; }

.pb-cols { display: grid; grid-template-columns: minmax(0,1.5fr) minmax(0,1fr); gap: 16px; align-items: start; }
.pb-stack { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

.pb-sec-head { display: flex; align-items: center; gap: 10px; padding: 20px 24px 14px; }
.pb-sec-head i { width: 3px; height: 14px; border-radius: 2px; background: linear-gradient(90deg,#6c63ff,#42b9d1); }
.pb-sec-head i.warn { background: linear-gradient(180deg,#efb455,#e09b34); }
.pb-sec-head i.crit { background: linear-gradient(180deg,#ef7a79,#e2605f); }
.pb-sec-head h2 { margin: 0; font-size: 17px; font-weight: 600; color: var(--hbos-text-primary); }
.pb-note { margin-left: auto; font-size: 11px; color: var(--hbos-text-muted); }

.pb-tbl-wrap { padding: 0 24px 18px; }
.pb-tbl { width: 100%; border-collapse: collapse; }
.pb-tbl th, .pb-tbl td { padding: 12px 10px; text-align: left; vertical-align: middle; }
.pb-tbl thead th { padding-top: 0; padding-bottom: 10px; font-size: 11px; font-weight: 600; color: var(--hbos-text-muted); letter-spacing: .06em; white-space: nowrap; border-bottom: 1px solid rgba(65,91,138,.10); }
.pb-tbl tbody tr { border-bottom: 1px solid rgba(65,91,138,.06); }
.pb-tbl tbody tr:last-child { border-bottom: 0; }
.pb-tbl td { font-size: 14px; color: var(--hbos-text-primary); }
.pb-tbl .num { text-align: right; font-variant-numeric: tabular-nums; }
.pb-tbl .pb-dim { color: var(--hbos-text-muted); }
.pb-name { font-weight: 600; white-space: nowrap; }

.pb-rate { display: flex; align-items: center; gap: 12px; justify-content: flex-end; }
.pb-track { width: 96px; height: 7px; flex: 0 0 96px; border-radius: 999px; background: rgba(65,91,138,.09); overflow: hidden; }
.pb-track > i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg,#6c63ff,#42b9d1); }
.pb-track.full > i { background: linear-gradient(90deg,#2fd39a,#42b9d1); }
.pb-pct { min-width: 56px; text-align: right; font-variant-numeric: tabular-nums; }

.pb-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-left: 8px; vertical-align: middle; }
.pb-dot.ok { background: var(--hbos-status-success); }
.pb-dot.no { background: var(--hbos-status-warning); }
.pb-dot.na { background: rgba(65,91,138,.20); }

.pb-list { margin: 0; padding: 0 24px 18px; list-style: none; }
.pb-list li { display: flex; gap: 10px; align-items: flex-start; padding: 11px 0; font-size: 14px; line-height: 1.6; color: var(--hbos-text-secondary); border-bottom: 1px solid rgba(65,91,138,.06); }
.pb-list li:last-child { border-bottom: 0; }
.pb-list li::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: var(--hbos-brand-cyan); flex: 0 0 5px; margin-top: 9px; }
.pb-list b { color: var(--hbos-text-primary); font-weight: 600; }

.pb-foot-note { padding: 14px 24px 20px; font-size: 12px; line-height: 1.75; color: var(--hbos-text-muted); }
.pb-foot-note b { color: var(--hbos-text-secondary); font-weight: 600; }
.pb-foot-note code { font-family: var(--hbos-font-mono); font-size: 11.5px; background: rgba(108,99,255,.07); padding: 2px 6px; border-radius: 5px; color: var(--hbos-brand-violet); }

/* 评级标签 —— 四档各一色，与脚注图例同款 */
.pb-grade { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; line-height: 1.6; white-space: nowrap; }
.pb-grade.ok { background: rgba(16,185,129,.12); color: #0e9f6e; }
.pb-grade.part { background: rgba(14,165,233,.12); color: #0a83bb; }
.pb-grade.lack { background: rgba(148,163,184,.16); color: #5b6b82; }
.pb-grade.bad { background: rgba(239,68,68,.12); color: #d6403f; }
.pb-foot-note .pb-grade { margin: 0 2px; }

.pb-toggle { display: block; margin: 0 24px 14px; padding: 6px 14px; border: 1px solid rgba(65,91,138,.18); border-radius: 999px; background: rgba(255,255,255,.6); font-size: 12px; color: var(--hbos-brand-violet); cursor: pointer; }
.pb-toggle:hover { background: rgba(108,99,255,.06); }

/* 工艺提升与改进方案（AI）—— 独占整行的下区面板 */
.pb-ai-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 0 24px 12px; font-size: 12px; color: var(--hbos-text-secondary); }
.pb-ai-bar .pb-dim { margin-left: 4px; }

/* 表体限高滚动：展开全部 62 条时**面板本身不变高**，只在内部滚动 ——
   否则整页会被拉到 2700px，正是「页面太长、不平衡」的元凶。 */
.pb-ai-scroll { max-height: 322px; overflow: hidden; position: relative; }
.pb-ai-scroll::after { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 44px; pointer-events: none; background: linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,.72)); }
.pb-ai-scroll.is-open { max-height: 460px; overflow-y: auto; }
.pb-ai-scroll.is-open::after { display: none; }
.pb-ai-foot { padding: 0 24px 4px; }
.pb-ai-foot .pb-toggle { margin: 0; }

@media (max-width: 1439px) {
  .pb-cols { grid-template-columns: minmax(0,1fr); }
}
@media (max-width: 1099px) {
  .pb-kpis { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
@media (max-width: 767px) {
  .pb-head h1 { font-size: 24px; line-height: 32px; }
  .pb-kpi-vl { font-size: 28px; line-height: 36px; }
  .pb-col-rate { display: none; }
}
</style>
