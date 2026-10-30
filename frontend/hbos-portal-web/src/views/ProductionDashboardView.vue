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
        <!-- 数据新鲜度 + 手动刷新。
             服务端是「先给旧的、后台更新」，所以**这里显示的时点可能早于现在** ——
             那正是要让人看见的信息，不能藏。
             `dataAsOf` 拿不到（旧版服务）时**整段不显示**，只留刷新按钮 ——
             不编一个「xx 起累计」之类看着别扭的字样。 -->
        <span v-if="board" class="pb-asof">
          <template v-if="dataAsOfText">数据截至 {{ dataAsOfText }}</template>
          <!-- 刷新完成后短暂显示「已更新」：时间戳只到分钟，刚点完刷新往往看不出变化，
              会让人以为没生效。 -->
          <span v-if="justRefreshed" class="pb-updated">已更新</span>
          <span v-else-if="refreshFailed" class="pb-refresh-failed" :title="refreshFailMessage">
            刷新失败，仍是旧数据<template v-if="refreshFailMessage">（{{ refreshFailMessage }}）</template>
          </span>
          <button class="pb-refresh" :disabled="refreshing" title="重新从飞书多维表格取数（约 1 分钟）" @click="refreshBoard">
            <ReloadOutlined :spin="refreshing" />
            {{ refreshing ? `取数中 ${refreshElapsed}s` : '刷新' }}
          </button>
        </span>
      </div>
    </header>

    <!-- 加载中。**必须与「未接入」分开** —— 冷缓存时服务端要并发拉 18 张飞书表，
         实测约 100 秒（撞限流时更久）。不加这个态的话，这段时间页面会显示
         「未接入」，用户以为坏了。
         注意：这只会在**服务刚启动 / 跨天后的第一次访问**出现 —— 缓存按天，
         正常打开是毫秒级。 -->
    <section v-if="phase === 'loading'" class="pb-panel pb-skeleton" aria-busy="true" aria-live="polite">
      <div class="pb-skel pb-skel-kpi"></div>
      <div class="pb-skel pb-skel-row"></div>
      <div class="pb-skel pb-skel-row"></div>
      <div class="pb-skel pb-skel-row"></div>
      <p class="pb-skel-note">正在取生产数据…（首次打开约需 1~2 分钟，之后当天打开是秒开）</p>
    </section>

    <!-- 取不到：**显示具体原因**，三种情况的下一步动作完全不同 ——
         未接入 → 等配置；连不上/上游失败 → 重试；无权限 → 重新登录。
         统一写「还没接通」会让人去联系管理员，而实际只需要再点一次。 -->
    <section v-else-if="phase === 'unavailable'" class="pb-panel pb-state">
      <ThunderboltOutlined class="pb-state-ic" />
      <h3>{{ boardFailureTitle }}</h3>
      <p>
        这一页的数字来自飞书多维表格，经独立取数服务聚合后提供。
        现在拿不到数据，所以这里<b>不显示任何数字</b>——宁可不给，也不给一个看起来像真实产量的占位值。
      </p>
      <p v-if="boardFailure?.message" class="pb-state-reason">原因：{{ boardFailure.message }}</p>
      <p v-else>页面结构与字段口径已经定稿，数据接通后按同一套结构填充，不再改版。</p>
      <div v-if="boardFailure?.kind !== 'not_configured'" class="pb-state-actions">
        <button class="pb-refresh" :disabled="refreshing" @click="refreshBoard">
          <ReloadOutlined :spin="refreshing" />
          {{ refreshing ? `取数中 ${refreshElapsed}s` : '重试' }}
        </button>
      </div>
    </section>

    <!-- `v-else-if="board"` 而不是 `v-else` —— 让 TS 把 board 收窄成非 null
         （ready 态必然有数据，这个不变式写在条件里比在代码里更稳）。 -->
    <template v-else-if="board">
      <!-- 月度关键指标 -->
      <section class="pb-kpis" aria-label="月度关键指标">
        <div class="pb-panel pb-kpi">
          <div class="pb-kpi-top">
            <span class="pb-kpi-lb">当月计划完成率</span>
            <span class="pb-kpi-vl" :class="{ 'pb-tbd': planRatePct === null }">{{ planRateText }}</span>
          </div>
          <div v-if="planRatePct !== null" class="pb-bar"><i :style="{ width: planRatePct + '%' }" /></div>
          <div class="pb-kpi-fn" :class="{ 'pb-kpi-fn-gap': planRatePct === null }">{{ planRateNote }}</div>
        </div>
        <div class="pb-panel pb-kpi">
          <div class="pb-kpi-top">
            <span class="pb-kpi-lb">收率达标率</span>
            <span class="pb-kpi-vl" :class="{ 'pb-tbd': yieldRatePct === null }">{{ yieldRateText }}</span>
          </div>
          <div v-if="yieldRatePct !== null" class="pb-bar"><i :style="{ width: yieldRatePct + '%' }" /></div>
          <div class="pb-kpi-fn" :class="{ 'pb-kpi-fn-gap': yieldRatePct === null }">{{ yieldRateNote }}</div>
        </div>
        <div class="pb-panel pb-kpi">
          <div class="pb-kpi-top">
            <span class="pb-kpi-lb">质量合格率</span>
            <span class="pb-kpi-vl" :class="{ 'pb-tbd': qualityRateText === null }">{{ qualityRateText ?? '暂无数据' }}</span>
          </div>
          <div v-if="qualityRatePct !== null" class="pb-bar"><i :style="{ width: qualityRatePct + '%' }" /></div>
          <div class="pb-kpi-fn" :class="{ 'pb-kpi-fn-gap': qualityRatePct === null }">{{ qualityNote }}</div>
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
        <section class="pb-panel pb-col-main">
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
                <li v-for="row in yieldRowsAll" :key="row.label">
                  <span>
                    <b>{{ row.label }}</b>
                    {{ (row.yieldRate! * 100).toFixed(1) }}%<template v-if="row.targetYieldRate !== null">
                      ，目标 {{ (row.targetYieldRate * 100).toFixed(1) }}%，差 {{ deltaText(row) }}pt</template><template v-else>
                      ，<b>目标收率未录入</b></template>
                  </span>
                </li>
                <li v-if="!yieldRowsAll.length"><span class="pb-dim">本月尚无收率数据</span></li>
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
                  <span>
                    收率达标 {{ metCount }} / {{ yieldRows.length }}<template v-if="yieldMissingTarget.length">
                      <span class="pb-dim">（另有 {{ yieldMissingTarget.length }} 个缺目标收率，未计入）</span></template>
                  </span>
                </li>
              </ul>
            </section>
          </template>

          <!-- 管理版：异常汇报 —— 放右列，与左列「完成情况」等高，凑成平衡的两栏。
               AI 工艺提升面板**不在这里** —— 它 62 道工序，放右列会把页面拉长到
               2700px，故移到下方独占整行（见本块结束后那个 section）。 -->
          <template v-else>
            <section class="pb-panel">
              <div class="pb-sec-head"><i class="crit" /><h2>异常汇报</h2><span class="pb-note">管理层向 · 当月</span></div>
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
                  <b>窗口</b>：只看<b>当月</b>（{{ anomaly.windowStart?.slice(0, 7) || monthLabel(board.month) }}）—— 月初样本少，
                  显示 <code>—</code> 或 0%/100% 都属正常。
                  <template v-if="anomaly.undated > 0">
                    <br><b>{{ anomaly.undated }} 条</b>记录没有日期，未计入。
                  </template>
                  <template v-if="anomalySourceNote">
                    <br><b class="pb-warn-text">{{ anomalySourceNote }}</b>。
                  </template>
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
          <span class="pb-note">{{ aiLoading ? 'AI 分析 · 读取中' : (aiUnavailable ? 'AI 分析 · 读取失败' : (aiRows.length ? 'AI 分析 · 每天 16:30 更新' : 'AI 分析 · 暂无结果')) }}</span>
        </div>
        <div v-if="aiLoading" class="pb-foot-note">正在读取分析结果…</div>
        <div v-else-if="aiUnavailable" class="pb-foot-note">
          <b>AI 结论暂时读取不到。</b>{{ aiUnavailable }}<br>
          这不等于「还没有分析结果」——分析服务可能正忙或暂时不可用。
          <a class="pb-retry-link" href="javascript:void(0)" @click.prevent="loadAiAnalysis">重试</a>
        </div>
        <div v-else-if="!aiRows.length" class="pb-foot-note">
          会议口径：基于各产品的<b>工艺描述文档与生产台账数据</b>，由 AI 自动分析生成优化建议。<br>
          结果表里还没有数据。分析服务每天 16:30 生成一次；若无结果，可能是模型不可用或校验未通过
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
            <!-- 用法提示放**表头上方**：原先塞在面板最底下的脚注里，
                 要先滚过 12 行才看得到 —— 等于没有（Owner 反馈）。 -->
            <span class="pb-ai-hint">
              <ThunderboltOutlined />
              点<b>工序名</b>看完整报告：参数影响、改进建议与依据
            </span>
          </div>
          <div class="pb-tbl-wrap pb-ai-scroll" :class="{ 'is-open': aiShowAll }">
            <table class="pb-tbl">
              <thead>
                <tr><th>产品</th><th>工序</th><th>结论摘要</th><th>评级</th><th>分析日期</th></tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in visibleAiRows" :key="i">
                  <td class="pb-name">{{ r.product }}</td>
                  <td>
                    <!-- 整行可点：报告全文是这一栏唯一的出口，
                         做一个「详情」小按钮点击面积反而太小 -->
                    <button type="button" class="pb-ai-open" :title="`查看「${r.process}」完整报告`" @click="openReport(r)">
                      {{ r.process }}
                    </button>
                  </td>
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
            结果表 <code>AI工艺分析结果</code> · 每天 16:30 自动生成 · 按工序幂等覆盖，不追加。
          </div>
        </template>
      </section>

      <!-- 完整报告弹窗。报告是 Markdown（## 标题 / 列表 / 表格），
           这里不引 markdown 渲染库 —— 62 份报告只用到标题和列表两种语法，
           自己转一遍比多一个依赖划算，也不会因为模型偶尔输出的原样 HTML 被注入。 -->
      <a-modal
        :open="reportOpen"
        :footer="null"
        :width="760"
        :title="reportTitle"
        wrap-class-name="pb-report-modal"
        @cancel="reportOpen = false"
      >
        <div v-if="reportLoading" class="pb-report-state">正在读取完整报告…</div>
        <div v-else-if="reportText === null" class="pb-report-state">
          报告读取失败，请稍后重试。
        </div>
        <div v-else class="pb-report">
          <div v-for="(blk, i) in reportBlocks" :key="i">
            <h3 v-if="blk.type === 'h'">{{ blk.text }}</h3>
            <p v-else-if="blk.type === 'p'"><InlineText :spans="blk.spans" /></p>
            <ul v-else-if="blk.type === 'ul'">
              <li v-for="(li, j) in blk.items" :key="j"><InlineText :spans="li" /></li>
            </ul>
            <p
              v-else
              class="pb-report-sug"
              :class="blk.priority ? `is-${priorityClass(blk.priority)}` : 'is-sub'"
            >
              <span v-if="blk.priority" class="pb-sug-tag">{{ blk.priority }}</span>
              <InlineText :spans="blk.spans" />
            </p>
          </div>
        </div>
      </a-modal>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons-vue'
import { PRODUCTION_CENTER_PATH } from '@/data/productionNav'
import { parseReport } from '@/services/reportMarkdown'
import InlineText from '@/components/production/InlineText.vue'
import {
  fetchProductionBoard,
  fetchAiAnalysis,
  fetchAiReport,
  invalidateAiReportCache,
  type BoardResult,
  type ProductionBoardData,
  type ProductionRow,
  type AiAnalysisRow,
} from '@/services/productionBoard'

const route = useRoute()
const isCenter = computed(() => route.path === PRODUCTION_CENTER_PATH)

/** 加载 → 取不到 → 就绪。**三态分开**，见模板里的说明。 */
const phase = ref<'loading' | 'unavailable' | 'ready'>('loading')
/** 取不到时的具体原因 —— 「未接入 / 连不上 / 上游失败 / 无权限」动作完全不同。 */
const boardFailure = ref<{ kind: BoardResult['state']; message: string } | null>(null)
const board = ref<ProductionBoardData | null>(null)
const aiRows = ref<AiAnalysisRow[]>([])
/**
 * 异常汇总。**形状不对就当没有** —— 服务端缓存里可能是一份结构异常的旧数据
 * （实测：测试造的 `{}` 被落盘，`windowStart.slice` 抛异常导致整页白屏）。
 * 宁可显示「异常数据暂不可用」，也不要整页卡在加载态。
 */
const anomaly = computed(() => {
  const a = board.value?.anomaly
  if (!a || !Array.isArray(a.byWorkshop) || !a.windowStart) return null
  return a
})
const aiLoading = ref(false)
/**
 * AI 结论读取失败的说明。**与「结果为空」分开**：
 * 服务宕机/权限错误/503 被显示成「暂无结果」会掩盖故障（早先就是这样）。
 */
const aiUnavailable = ref<string | null>(null)

// --- AI 工艺分析面板：排序 + 计数 + 折叠 ---
/** 未展开时最多显示多少行（62 道工序全铺开太长）。 */
const AI_PREVIEW = 12
const aiShowAll = ref(false)

/**
 * 排序：**评级严重度优先，同级内按分析日期倒序**（新的在前）。
 *
 * 只按评级排的话，同级里先谁后谁是不确定的（依赖接口返回顺序），
 * 重新分析过的行不会「浮」到前面 —— 用户看不出这次跑的新结论是哪几条。
 * 加一级按日期的稳定排序，最新分析的排前；日期相同再按产品/工序名定序，
 * 保证每次打开顺序一致（否则同一批数据两次打开顺序不同，像是数据在变）。
 */
const GRADE_RANK: Record<string, number> = { 未达标: 0, 部分达到: 1, 数据不足: 2, 已达标: 3 }
const sortedAiRows = computed(() =>
  [...aiRows.value].sort((a, b) => {
    const byGrade = (GRADE_RANK[a.grade] ?? 9) - (GRADE_RANK[b.grade] ?? 9)
    if (byGrade !== 0) return byGrade
    // 日期是 `YYYY-MM-DD`（或 null）—— 字符串倒序比较即可
    const byDate = (b.analyzedAt || '').localeCompare(a.analyzedAt || '')
    if (byDate !== 0) return byDate
    // 最后按名字定序，保证顺序稳定（Array.sort 在 V8 里虽已稳定，
    // 但显式定序能让「改了评级会不会换位置」这类行为可预期）
    return `${a.product}${a.process}`.localeCompare(`${b.product}${b.process}`)
  }),
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

// --- 完整报告弹窗 ---
const reportOpen = ref(false)
const reportLoading = ref(false)
/** `null` = 没取到（区别于「取到了但是空」）—— 显示重试提示，不拿摘要顶替。 */
const reportText = ref<string | null>(null)
const reportTitle = ref('')
/**
 * 报告请求序号 —— 先点 A、再点 B 时，A 后返回会把 B 的正文写进 B 的标题下。
 * 响应回来前校验「当前打开的仍是同一道工序」。
 */
let reportSeq = 0

async function openReport(row: AiAnalysisRow) {
  const seq = ++reportSeq
  reportTitle.value = `${row.product} · ${row.process}`
  reportText.value = null
  reportLoading.value = true
  reportOpen.value = true
  try {
    const text = await fetchAiReport(row.product, row.process)
    if (seq !== reportSeq) return        // 期间打开了另一道工序
    reportText.value = text
  } finally {
    if (seq === reportSeq) reportLoading.value = false
  }
}

/**
 * 把报告 Markdown 拆成块 —— 解析逻辑在 `services/reportMarkdown.ts`（有单测）。
 * 这里只负责接数据：文本本身**用插值渲染**，不用 `v-html`，
 * 模型输出里若混入 HTML 标签也只会显示成文字。
 */
const reportBlocks = computed(() => parseReport(reportText.value))

/** 建议优先级 → 样式档。与 `parse.PRIORITIES`（高/中/低）对应。 */
function priorityClass(p: string): string {
  return p === '高' ? 'high' : p === '低' ? 'low' : 'mid'
}

const monthLabel = (m: string) => {
  const [y, mo] = m.split('-')
  return y && mo ? `${y} 年 ${Number(mo)} 月` : m
}

// --- 数据新鲜度 ---
//
// 服务端是「先给旧的、后台更新」，所以打开页面拿到的那份**可能不是刚拉的**。
// 把「数据截至 HH:MM」摆出来，让人自己判断要不要点刷新 —— 不藏。
const refreshing = ref(false)
/** 刷新已等了多少秒 —— 这条链路要十几秒，静默转圈会被当成卡死。 */
const refreshElapsed = ref(0)
/** 刚刷完，短暂显示「已更新」（时间戳只到分钟，看不出变化会以为没生效）。 */
const justRefreshed = ref(false)
/** 上一次刷新**失败**了（服务端 502 / 网络错误）—— 必须让用户看见，不能静默。 */
const refreshFailed = ref(false)
/** 刷新失败的具体原因 —— 「上游限流」和「服务没起」的下一步动作不同。 */
const refreshFailMessage = ref('')
let refreshTimer: ReturnType<typeof setInterval> | null = null
let justRefreshedTimer: ReturnType<typeof setTimeout> | null = null

/**
 * 取不到时的标题 —— 按原因分开，别把「服务挂了」说成「还没接」。
 */
const boardFailureTitle = computed(() => {
  switch (boardFailure.value?.kind) {
    case 'not_configured':
      return '看板数据还没接通'
    case 'unreachable':
      return '连不上生产数据服务'
    case 'upstream_error':
      return '取数暂时失败'
    case 'unauthorized':
      return '没有权限读取生产数据'
    default:
      return '看板数据暂时不可用'
  }
})

/**
 * 这批数据是什么时候取回来的。**取不到就返回空串** —— 调用方整段不渲染，
 * 不编「xx 起累计」这类字样（用户反馈那串看着别扭）。
 */
function formatAsOf(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const p = (n: number) => String(n).padStart(2, '0')
  const today = new Date()
  const sameDay =
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  const hm = `${p(d.getHours())}:${p(d.getMinutes())}`
  return sameDay ? hm : `${d.getMonth() + 1}-${p(d.getDate())} ${hm}`
}

const dataAsOfText = computed(() => formatAsOf(board.value?.dataAsOf))

/**
 * 手动刷新 —— 让服务端**同步**重取（`?refresh=1`），不是先给旧值。
 *
 * 只换 board，不动 phase：刷新失败时旧数据仍在，比把整页打回「未接入」好。
 *
 * 为什么计秒：服务端要并发拉 13 张飞书表（实测约 19 秒），静默转圈会被当成点漏了
 * 或卡死。把已等秒数摆出来，用户知道它在动。
 */
async function refreshBoard() {
  if (refreshing.value) return
  refreshing.value = true
  refreshElapsed.value = 0
  refreshFailed.value = false
  refreshFailMessage.value = ''
  // 上一次「已更新」还没消失时又点刷新：先撤掉它，否则本次失败会继续显示「已更新」
  justRefreshed.value = false
  if (justRefreshedTimer) clearTimeout(justRefreshedTimer)
  refreshTimer = setInterval(() => { refreshElapsed.value += 1 }, 1000)
  // 报告缓存也要一起失效：16:30 之后 AI 结论变了，只刷 board 会继续读到旧报告
  invalidateAiReportCache()
  try {
    const result = await fetchProductionBoard({ refresh: true })
    if (result.state === 'ready') {
      board.value = result.data
      // **必须同时切回 ready**：失败态模板优先于 board 模板，
      // 只更新 board 不切 phase，用户点了「重试」拿到数据后仍停在失败页。
      phase.value = 'ready'
      boardFailure.value = null
      refreshFailed.value = false
      refreshFailMessage.value = ''
      justRefreshed.value = true
      if (justRefreshedTimer) clearTimeout(justRefreshedTimer)
      justRefreshedTimer = setTimeout(() => { justRefreshed.value = false }, 4000)
    } else {
      // ⚠️ 刷新失败**必须说出来**。早先这里是 `if (data)` 静默跳过 ——
      // 服务端撞飞书限流（1254607）返回 502 时，按钮转完 90 秒就停了，
      // 页面上什么都没有变，看起来像「刷新成功但时间没动」（实测踩到过）。
      // 旧数据保留（比打回「未接入」好），但要明确告诉用户这次没刷上。
      refreshFailed.value = true
      refreshFailMessage.value =
        result.state === 'not_configured' ? '取数服务尚未接入。' : result.message
    }
    // 刷新也顺带重取 AI 摘要：否则 16:30 之后点刷新，面板还停在旧结论
    if (isCenter.value) await loadAiAnalysis()
  } finally {
    if (refreshTimer) clearInterval(refreshTimer)
    refreshTimer = null
    refreshing.value = false
  }
}

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (justRefreshedTimer) clearTimeout(justRefreshedTimer)
})

// --- KPI 汇总（口径：只计入目标 > 0 的行，避免未排产行稀释分母）---
//
// ⚠️ **分母为 0 时返回 null，不是 0**。月初还没导入计划、或上游暂时缺数时，
// 显示 `0.0%` 会被读成「生产完全没完成」，而事实是「还没有数据可以算」。
// 真实完成了 0% 属于另一回事 —— 那种情况分母 > 0，会照常算出 0。
const targetRows = computed(() => (board.value?.rows || []).filter((r) => r.target > 0))
const totalDone = computed(() => targetRows.value.reduce((s, r) => s + r.done, 0))
const totalTarget = computed(() => targetRows.value.reduce((s, r) => s + r.target, 0))
const planRatePct = computed<number | null>(() =>
  totalTarget.value > 0 ? (totalDone.value / totalTarget.value) * 100 : null,
)
const planRateText = computed(() =>
  planRatePct.value === null ? '—' : `${planRatePct.value.toFixed(1)}%`,
)
const planRateNote = computed(() =>
  totalTarget.value > 0
    ? `${totalDone.value} / ${totalTarget.value} 批 · 批数口径`
    : '暂无月度计划数据',
)

// 收率达标率的分母**只算「实际收率 + 目标收率」都有的品种**。
//
// 早先只要求 `yieldRate !== null`，但 `yieldMeets()` 还要求目标收率 ——
// 于是「有实际收率、目标没录」的品种会进分母却永远不达标，
// 等价于被系统当成未达标：目标产能表少录一个产品，整个 KPI 就被人为拉低。
const yieldRows = computed(() =>
  (board.value?.rows || []).filter((r) => r.yieldRate !== null && r.targetYieldRate !== null),
)
/** 有实际收率、但缺目标收率 —— 单独点名，不混进达标率。 */
const yieldMissingTarget = computed(() =>
  (board.value?.rows || []).filter((r) => r.yieldRate !== null && r.targetYieldRate === null),
)
/** 有实际收率的全部品种 —— 明细列表用这个，缺目标也要显示出来。 */
const yieldRowsAll = computed(() =>
  (board.value?.rows || []).filter((r) => r.yieldRate !== null),
)
const metCount = computed(() => yieldRows.value.filter((r) => yieldMeets(r)).length)
const yieldRatePct = computed<number | null>(() =>
  yieldRows.value.length > 0 ? (metCount.value / yieldRows.value.length) * 100 : null,
)
const yieldRateText = computed(() =>
  yieldRatePct.value === null ? '—' : `${yieldRatePct.value.toFixed(1)}%`,
)
const yieldRateNote = computed(() => {
  if (!yieldRows.value.length) {
    return yieldMissingTarget.value.length
      ? `${yieldMissingTarget.value.length} 个品种有收率但缺目标收率，无法判定达标`
      : '本月尚无收率数据'
  }
  const base = `${metCount.value} / ${yieldRows.value.length} 个有收率数据的品种达标`
  return yieldMissingTarget.value.length
    ? `${base} · 另有 ${yieldMissingTarget.value.length} 个缺目标收率未计入`
    : base
})

const biggestTarget = computed(() =>
  [...targetRows.value].sort((a, b) => b.target - a.target)[0] || null,
)

// 质量合格率：**实算**（会议 2026-10-19 定的取数规则，服务端 `contract.quality_stats`）。
//
// 口径一句话：从「同步 QC 数据-产品」按 `生产日期` 取当月行，**已登记即合格**
// （不合格批次根本不录入）；两个已检批次之间的空档 = 不合格，
// 最后一个已检批次之后的空档 = 还没检测（不进分母）。
//
// ⚠️ 分母是「已检批次」，不是当月全部批次 —— 所以 `tested / (tested+failed)`
// 和「未检 N 批」必须一起显示。只写一个 100% 会被读成「全批全检全合格」，
// 那是会议里李洋担心的误读。
//
// 没有 QC 数据源的产品（无菌两行、F13 的「国内规范粗品」）按 Owner 口径
// **直接忽略**，不在面板上点名。
const quality = computed(() => board.value?.quality ?? null)
const qualityRatePct = computed(() =>
  quality.value && quality.value.rate !== null ? quality.value.rate * 100 : null,
)
const qualityRateText = computed(() =>
  qualityRatePct.value === null ? null : `${qualityRatePct.value.toFixed(1)}%`,
)
const qualityNote = computed(() => {
  const q = quality.value
  if (!q) return ''
  const failedInfo = qualitySourceNote.value
  // 取数失败 ≠ 没检测：前者是「没取到」，后者是「真没检」。不点产品名。
  if (q.rate === null) return failedInfo || '本月尚无已检批次'
  const parts = [`${q.tested} / ${q.tested + q.failed} 批已检`]
  if (q.failed > 0) parts.push(`不合格 ${q.failed} 批`)
  // 未检批数只在**真的还有没检的**时候出现 —— 全检完的月份不挂这一句
  if (q.untested > 0) parts.push(`未检 ${q.untested} 批`)
  // 部分 QC 表取不到时，这个率是**部分口径** —— 不说明会被当成全厂合格率
  if (failedInfo) parts.push(failedInfo)
  // 质量缓存与 board 缓存寿命不同（一天 vs 12 小时），两者常常不是同一时刻。
  // 只在**确实不同**时才标出来，免得每个页面都挂一句冗余时间。
  const qAt = formatAsOf(board.value?.qualityDataAsOf)
  if (qAt && qAt !== dataAsOfText.value) parts.push(`质量数据截至 ${qAt}`)
  return parts.join(' · ')
})

/**
 * 质量数据源失败时的说明；全部正常时为空串。
 *
 * 后端逐源 try/except，**部分失败仍然会算出一个率** —— 早先前端只在
 * `rate === null` 时才提「暂不可用」，于是「4 张 QC 表挂了 1 张」会被
 * 当成完整合格率显示。这里把部分失败也说出来。
 */
const qualitySourceNote = computed(() => {
  const q = quality.value
  if (!q) return ''
  const failed = q.failedLabels || []
  if (!failed.length) return ''
  const total = typeof q.sourceCount === 'number' ? q.sourceCount : null
  if (total !== null && failed.length >= total) return '质量数据全部取不到'
  return total !== null
    ? `${failed.length} / ${total} 个产品质量数据取不到，合格率为部分口径`
    : `${failed.length} 个产品质量数据取不到，合格率为部分口径`
})

const anomalyRatePct = computed(() =>
  anomaly.value && anomaly.value.rate !== null ? anomaly.value.rate * 100 : null,
)
const anomalyRateText = computed(() =>
  anomalyRatePct.value === null ? null : `${anomalyRatePct.value.toFixed(1)}%`,
)
/**
 * 异常数据源失败时的说明；全部正常时为空串。
 *
 * 关键区分：**「全部车间都取不到」绝不能显示成「当月无异常记录」** ——
 * 那会把数据源故障说成「确实没有异常」，是最容易误导管理层的一种。
 */
const anomalySourceNote = computed(() => {
  const a = anomaly.value
  if (!a) return ''
  const failed = a.failedWorkshops || []
  if (!failed.length) return ''
  const total = typeof a.sourceCount === 'number' ? a.sourceCount : null
  if (total !== null && failed.length >= total) return '异常数据全部取不到'
  return total !== null
    ? `${failed.length} / ${total} 个车间异常数据取不到，闭环率为部分口径`
    : `${failed.length} 个车间异常数据取不到，闭环率为部分口径`
})

const anomalyNote = computed(() => {
  const a = anomaly.value
  if (!a) return '异常数据暂不可用'
  const failedInfo = anomalySourceNote.value
  const total = typeof a.sourceCount === 'number' ? a.sourceCount : null
  // **全部失败**时 total=0 且 rate=null，与「本月真的没异常」长得一模一样。
  if (failedInfo && total !== null && (a.failedWorkshops || []).length >= total) {
    return failedInfo
  }
  // 口径已改为**只看当月**（Owner 2026-10-20），文案不能还写整年窗口 ——
  // 那会让人以为系统检查了整年，从而弱化对当月缺数据的警惕。
  if (a.rate === null) return failedInfo || '当月无异常记录'
  // **不报「共 N 个车间」** —— 车间是陆续收集的（五车间还没到），
  // 写总数会让人以为是全部车间，而实际只有已收集的那几个。
  const base = `${a.closed} / ${a.total} 条`
  return failedInfo ? `${base} · ${failedInfo}` : base
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
/**
 * 完成率 → 文本。
 *
 * ⚠️ 只有 `null`/`NaN` 显示 `—`。**真实的 0% 要显示 `0.0%`** ——
 * 早先写成 `v > 0 ? … : '—'`，把「一批都没完成」显示成「无数据」，
 * 而 KPI 那边又反过来把「没有目标」显示成 0.0%，两处语义正好相反。
 */
function pctText(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${(v * 100).toFixed(1)}%`
}
function yieldMeets(row: ProductionRow): boolean {
  return row.yieldRate !== null && row.targetYieldRate !== null && row.yieldRate >= row.targetYieldRate
}
function deltaText(row: ProductionRow): string {
  if (row.yieldRate === null || row.targetYieldRate === null) return '—'
  const d = Math.abs(row.targetYieldRate - row.yieldRate) * 100
  return d.toFixed(1)
}

/**
 * 拉一次 AI 结论。只有管理中心页有这块面板。
 *
 * 单独抽出来是因为它**有两个触发点**，见下面 `watch` 的说明。
 */
async function loadAiAnalysis() {
  aiLoading.value = true
  aiUnavailable.value = null
  try {
    const result = await fetchAiAnalysis()
    if (result.state === 'unavailable') {
      aiUnavailable.value = result.message
      aiRows.value = []
      return
    }
    aiRows.value = result.state === 'ready' ? result.rows : []
  } finally {
    aiLoading.value = false
  }
}

onMounted(async () => {
  // 两个页面共用同一份看板数据（原型 §4.3：上区逐字一致）
  const result = await fetchProductionBoard()
  if (result.state === 'ready') {
    board.value = result.data
    boardFailure.value = null
    phase.value = 'ready'
    void autoRefreshIfStale(result.data)
  } else {
    boardFailure.value = {
      kind: result.state,
      message: result.state === 'not_configured' ? '' : result.message,
    }
    phase.value = 'unavailable'
  }
  if (isCenter.value) await loadAiAnalysis()
})

/**
 * 数据不是今天的 → 静默重取一次。
 *
 * 服务端缓存会落盘，服务重启/跨天后**先返回上次那份**（否则第一次打开要等
 * 100 秒）。那份数据里 `yesterdayInbound`（昨日入库）是按当时那天算的，
 * 跨天后就不对了；其余指标（产量、收率、目标、异常）与日期无关，不受影响。
 *
 * 所以这里不等用户手动刷新：发现 `dataAsOf` 不是今天就自己补一次，
 * 期间页面照常显示旧值（不切回骨架屏），取回来再无声替换。
 * 失败就保持原样 —— 用户仍可点刷新。
 */
async function autoRefreshIfStale(first: ProductionBoardData) {
  const iso = first.dataAsOf
  if (!iso) return
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return
  const now = new Date()
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  if (sameDay) return

  // 后台补数据期间页面显示的是**旧数字**，不加提示的话看不出在更新。
  // 复用刷新按钮的转圈（refreshing），用户看到「取数中 Ns」就知道在补。
  if (refreshing.value) return
  refreshing.value = true
  refreshElapsed.value = 0
  refreshTimer = setInterval(() => { refreshElapsed.value += 1 }, 1000)
  try {
    const fresh = await fetchProductionBoard({ refresh: true })
    // 失败就保持原样：页面上「数据截至 10-19」本身就是提示，用户可以手动刷新
    if (fresh.state === 'ready') board.value = fresh.data
  } finally {
    if (refreshTimer) clearInterval(refreshTimer)
    refreshTimer = null
    refreshing.value = false
  }
}

// 两张看板是**同一个组件**的两条路由，从基层版切到管理中心时 Vue 会复用
// 组件实例 —— `onMounted` **不会重跑**，AI 面板就一直停在「暂无结果」，
// 非得整页刷新或绕去别的 App 再回来才出内容（实测踩到过）。
//
// 所以按路由变化补一次拉取。`pre` 时机（默认）在重渲染之前执行，
// `aiLoading` 先置真，不会先闪一下空态。
watch(isCenter, (now) => {
  if (now && !aiRows.value.length) void loadAiAnalysis()
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

.pb-asof { display: inline-flex; align-items: center; gap: 8px; justify-content: flex-end; margin-top: 2px; }
.pb-refresh { display: inline-flex; align-items: center; gap: 4px; padding: 2px 9px; border: 1px solid rgba(65,91,138,.18); border-radius: 999px; background: rgba(255,255,255,.6); font-size: 11px; color: var(--hbos-brand-violet); cursor: pointer; }
.pb-refresh:hover:not(:disabled) { background: rgba(108,99,255,.07); }
.pb-refresh:disabled { cursor: progress; opacity: .62; }
.pb-updated { color: #0e9f6e; font-weight: 600; }
/* 刷新失败用告警色，但**不是红色错误** —— 数据还在，只是这一下没刷上 */
.pb-refresh-failed { color: var(--hbos-text-muted); font-weight: 600; }
/* 「部分口径」提示：不是错误红色，但要能一眼看到数据源有问题 */
.pb-warn-text { color: #b45309; }
.pb-state-reason { color: var(--hbos-text-muted); font-size: 13px; }
.pb-state-actions { margin-top: 14px; }

/* --- 完整报告弹窗 --- */
/* 工序名做成按钮：整行不可点（表格里点空白处没反馈会让人以为坏了），
   但字面上要看起来「可点」—— 下划虚线是链接的通用暗示。 */
.pb-ai-open {
  border: 0; padding: 0; background: none; cursor: pointer;
  font: inherit; color: var(--hbos-brand-violet);
  border-bottom: 1px dashed rgba(108,99,255,.45);
}
.pb-ai-open:hover { border-bottom-style: solid; }
.pb-report-state { padding: 32px 0; text-align: center; color: var(--hbos-text-muted); font-size: 13px; }
.pb-report { max-height: 62vh; overflow-y: auto; padding-right: 6px; font-size: 13px; line-height: 1.85; color: var(--hbos-text-secondary); }
.pb-report h3 { margin: 18px 0 8px; font-size: 14px; font-weight: 600; color: var(--hbos-text-primary); }
.pb-report h3:first-child { margin-top: 0; }
.pb-report p { margin: 0 0 8px; }
.pb-report ul { margin: 0 0 8px; padding-left: 20px; }
.pb-report li { margin-bottom: 4px; }
/* 改进建议段：与正文区分开，扫读时能一眼找到 */
.pb-report-sug {
  margin: 0 0 6px; padding: 6px 10px; border-radius: 8px;
  background: rgba(108,99,255,.05); border-left: 2px solid rgba(108,99,255,.45);
}
/* 从属行（依据 / 预期）不重复左侧色条，缩进一点表示归属上面那条建议 */
.pb-report-sug.is-sub {
  margin-top: -2px; margin-left: 10px; background: none;
  border-left: 1px dashed rgba(65,91,138,.18); font-size: 12.5px;
  color: var(--hbos-text-muted);
}
.pb-report-sug.is-high { border-left-color: #e2605f; }
.pb-report-sug.is-mid { border-left-color: #e09b34; }
.pb-report-sug.is-low { border-left-color: #42b9d1; }
/* 优先级标记：原来是正文里的 `**[高]**`，现在是独立色块 */
.pb-sug-tag {
  display: inline-block; margin-right: 7px; padding: 0 6px;
  border-radius: 6px; font-size: 11px; font-weight: 600; line-height: 18px;
  background: rgba(108,99,255,.12); color: var(--hbos-brand-violet);
  vertical-align: 1px;
}
.pb-report-sug.is-high .pb-sug-tag { background: rgba(226,96,95,.14); color: #c94b4a; }
.pb-report-sug.is-mid .pb-sug-tag { background: rgba(224,155,52,.16); color: #b97c1d; }
.pb-report-sug.is-low .pb-sug-tag { background: rgba(66,185,209,.16); color: #2b8fa6; }

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

/* 两栏**底部对齐**：`stretch` 让两个 grid item 等高（行高 = 较高那栏）。
   里面再各自长到 100%，否则面板还是按内容收缩、底边参差不齐（截图踩到过）。 */
.pb-cols { display: grid; grid-template-columns: minmax(0,1.5fr) minmax(0,1fr); gap: 16px; align-items: stretch; }
/* 两块主面板都做成纵列：**表格区吃掉剩余高度，脚注作为底栏**。
   这样内容少的那栏（右栏 5 行 vs 左栏 6 行）多出来的空白落在表格下方，
   而不是在脚注上方悬一块 —— 两栏的脚注都贴底、都有同一条分界线，
   看起来才是一套版式，而不是「一边没对齐」（截图踩到过两次）。 */
.pb-col-main,
.pb-stack > :last-child { display: flex; flex-direction: column; }
.pb-col-main .pb-tbl-wrap,
.pb-stack > :last-child .pb-tbl-wrap { flex: 1 1 auto; }
/* ⚠️ `min-height` 是必须的，不能省。
   两块脚注都是「贴底 + 顶部分界线」，**只有高度相同时顶边才会齐**。
   左栏那段文字 3 行、右栏 2 行 —— 高度不等时右栏那条线就低 21px，
   看着还是没对齐（截图反馈过第二次）。
   98px = 3 行文字 63px（12px 字号 × 1.75 行高）+ 上下内边距 34px + 分界线 1px。
   改字号/行高/文案行数时，这个值要一起改。 */
.pb-col-main .pb-foot-note,
.pb-stack > :last-child .pb-foot-note {
  margin-top: 0;
  min-height: 98px;
  border-top: 1px solid rgba(65,91,138,.08);
  padding-top: 14px;
}
.pb-stack { display: flex; flex-direction: column; gap: 16px; min-width: 0; height: 100%; }
/* 右栏**最后一块**吃掉剩余高度 —— 两块面板各自等高不会让底边对齐。 */
.pb-stack > :last-child { flex: 1 1 auto; }

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
/* 用法提示：整条推到右侧并加底色 —— 原先只是脚注里的一行小字，
   用户滚到底才看到，等于没提示（Owner 反馈）。 */
.pb-ai-hint {
  margin-left: auto; display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 999px;
  background: rgba(108,99,255,.08); color: var(--hbos-brand-violet);
  font-size: 11.5px; white-space: nowrap;
}
.pb-ai-hint b { font-weight: 600; }
.pb-ai-hint :deep(svg) { opacity: .75; }

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
