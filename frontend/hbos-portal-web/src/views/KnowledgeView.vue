<template>
  <div class="knowledge-page">
    <div class="kt-breadcrumb">
      <RouterLink to="/hbos">工作台</RouterLink><RightOutlined />
      <RouterLink to="/hbos/apps">应用中心</RouterLink><RightOutlined />
      <span>知识库</span>
    </div>
    <header class="kt-page-heading">
      <div>
        <h1>知识库</h1>
        <p>让知识更好地服务每一次工作。</p>
      </div>
      <div class="heading-actions">
        <a-tag v-if="status?.environment === 'synthetic'" color="orange">隔离合成测试</a-tag>
        <a-tag v-if="status?.environment === 'production'" color="blue">内部共享参考库</a-tag>
        <a-tag v-if="equipmentId" color="geekblue">设备上下文 {{ equipmentId }}</a-tag>

      </div>
    </header>

    <div class="knowledge-grid">
      <div class="knowledge-primary">
        <section class="knowledge-hero hbos-glass-g3" :class="{ compact: hasSearched }">
          <div class="knowledge-eyebrow"><BulbOutlined /> 部门分类 · 查阅已收录的内部参考资料</div>
          <h2 v-if="!hasSearched">工作中的问题，<br><span>从这里找到依据。</span></h2>
          <h2 v-else>找到相关内容，<span>也看清它的依据。</span></h2>
          <p v-if="!hasSearched">描述你的工作场景；没有依据时，系统会明确告诉你。</p>
          <form class="knowledge-search" @submit.prevent="submitSearch">
            <SearchOutlined aria-hidden="true" />
            <label class="sr-only" for="knowledge-query">描述工作中的问题</label>
            <input
              id="knowledge-query"
              v-model="query"
              maxlength="500"
              autocomplete="off"
              placeholder="描述问题，或输入工艺、文件编号、制度关键词…"
              :disabled="searching || !canSubmit"
            />
            <a-button type="primary" html-type="submit" :loading="searching" :disabled="!canSubmit || !query.trim()">
              检索知识 <ArrowRightOutlined />
            </a-button>
          </form>
          <div class="knowledge-state-line" role="status" aria-live="polite">
            <span :class="['state-dot', statusTone]"></span>
            {{ statusLabel }}
            <span v-if="status?.policy_revision" class="revision">策略 {{ status.policy_revision }}</span>
          </div>
          <div v-if="spaces.length" class="knowledge-space-filter">
            <label for="knowledge-space">部门分类</label>
            <select id="knowledge-space" v-model="selectedSpace" :disabled="searching">
              <option value="">全部知识库</option>
              <option v-for="space in spaces" :key="space.space_id" :value="space.space_id">
                {{ space.title }} · {{ space.document_count }} 份资料
              </option>
            </select>
          </div>
        </section>

        <a-alert
          v-if="pageError"
          :type="pageErrorCode === 'FORBIDDEN' ? 'warning' : 'error'"
          show-icon
          :message="pageError"
          class="knowledge-alert"
        />

        <section v-if="!hasSearched && !pageError" class="knowledge-start hbos-glass-g2">
          <div class="section-title">
            <div><h2>按部门查阅</h2><p>部门用于分类，已批准资料供内部知识用户共享查阅。</p></div>
            <a-tag>{{ spaces.reduce((n, s) => n + s.document_count, 0) }} 份资料</a-tag>
          </div>
          <div class="department-grid">
            <button v-for="space in spaces" :key="space.space_id" type="button" :aria-pressed="selectedSpace === space.space_id" @click="selectDepartment(space.space_id)">
              <ApartmentOutlined /><strong>{{ space.title }}</strong><span>{{ space.document_count }} 份已收录资料</span>
            </button>
          </div>
          <a-empty v-if="!spaces.length" description="暂无可查阅的部门资料" />
        </section>

        <section v-else-if="hasSearched" class="knowledge-results hbos-glass-g2">
          <div class="section-title">
            <div><h2>检索依据</h2><p>查看必要摘录，并核对文档编号、版本和参考状态。</p></div>
            <a-tag>{{ results.length }} 条</a-tag>
          </div>
          <a-empty v-if="!searching && !results.length && !pageError" description="未找到相关依据，请换一个关键词或调整部门范围。" />
          <a-skeleton v-if="searching" active :paragraph="{ rows: 6 }" />
          <div v-else class="result-list">
            <article v-for="item in results" :key="item.evidence_id" class="result-card">
              <div class="result-meta"><a-tag color="geekblue">{{ spaces.find(s => s.space_id === item.space_id)?.title || '检索依据' }}</a-tag><span>{{ item.version || '版本未标注' }}</span><a-tag color="orange">状态待核</a-tag></div>
              <h3>{{ item.title || '未标注标题' }}</h3>
              <p v-if="item.document_number" class="section-label">{{ item.document_number }}</p>
              <p v-if="item.status_note" class="status-note">{{ item.status_note }}</p>
              <p class="section-label">{{ item.section || '章节未标注' }}</p>
              <p class="excerpt-preview">{{ item.excerpt }}</p>
              <div class="result-actions"><button type="button" @click="openEvidence(item)">查看依据 <ArrowRightOutlined /></button><template v-if="status?.environment === 'production'"><a-button size="small" @click="tools?.bookmark(item)">收藏</a-button><a-button size="small" @click="tools?.feedback(item)">反馈</a-button></template></div>
            </article>
          </div>
        </section>

        <KnowledgeTools v-if="status?.environment === 'production' && subjectKey" ref="tools" :subject="subjectKey" :query="query" :selected-space="selectedSpace" :ask-enabled="Boolean(status?.ask_enabled)" @replay="replaySaved" @evidence="drawer.show" />

        <section v-if="catalog.length" class="knowledge-start hbos-glass-g2">
          <div class="section-title"><div><h2>资料目录</h2><p>内部参考／有效性待核</p></div><a-tag>{{ filteredCatalog.length }} 份</a-tag></div>
          <article v-for="doc in filteredCatalog" :key="doc.document_id" class="catalog-row">
            <div><strong>{{ doc.title || '未标注标题' }}</strong><p>{{ doc.document_number || '文档编号未标注' }} · {{ doc.version || '版本未标注' }}</p></div>
            <a-tag>{{ doc.department }}</a-tag>
          </article>
        </section>

        <footer class="knowledge-footer">
          <span><SafetyCertificateOutlined /> 仅展示必要摘录，不提供原文下载。</span>
          <span>{{ status?.ask_enabled ? '来源核验 · 内部参考回答' : '检索模式 · 回答能力未开启' }}</span>
        </footer>
      </div>

      <aside class="knowledge-secondary">
        <section class="knowledge-side-card hbos-glass-g2">
          <div class="side-icon"><BulbOutlined /></div>
          <h3>有依据，才继续</h3>
          <p>先查看来源与适用版本。资料未经现行性核验时，请向文控或资料维护人确认。</p>
          <div class="connection"><span></span>{{ status?.ask_enabled ? '回答能力已获准' : '回答能力未配置' }}</div>
        </section>
        <section class="knowledge-side-card hbos-glass-g2">
          <small>让每次查阅更有把握</small>
          <ol>
            <li><b>01</b><span><strong>说清工作场景</strong>描述设备、问题和希望了解的内容。</span></li>
            <li><b>02</b><span><strong>核对内容依据</strong>查看资料、版本和对应章节。</span></li>
            <li><b>03</b><span><strong>回到实际任务</strong>不把解释替代受控规程或质量决策。</span></li>
          </ol>
        </section>
      </aside>
    </div>

    <EvidenceDrawer
      :open="drawerOpen"
      :loading="drawerLoading"
      :evidence="drawerEvidence"
      :error="drawerError"
      @close="drawer.close"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ApartmentOutlined,
  ArrowRightOutlined,
  BulbOutlined,
  DeploymentUnitOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'
import type { KnowledgeEvidence, KnowledgeStatus, KnowledgeSpace, KnowledgeDocument } from '@/contracts/p1'
import { DomainApiError, getKnowledgeStatus, getKnowledgeSpaces, getKnowledgeDocuments, searchKnowledge } from '@/services/p1Api'
import EvidenceDrawer from '@/components/knowledge/EvidenceDrawer.vue'
import KnowledgeTools from '@/components/knowledge/KnowledgeTools.vue'
import { useEvidenceResolution } from '@/composables/useEvidenceResolution'
import { usePortalStore } from '@/stores/portal'

const status = ref<KnowledgeStatus | null>(null)
const spaces = ref<KnowledgeSpace[]>([])
const selectedSpace = ref('')
const catalog = ref<KnowledgeDocument[]>([])
const tools = ref<InstanceType<typeof KnowledgeTools> | null>(null)
const filteredCatalog = computed(() => catalog.value.filter(doc => !selectedSpace.value || doc.space_id === selectedSpace.value))
function selectDepartment(id: string) { selectedSpace.value = id; document.getElementById('knowledge-query')?.focus() }
const route = useRoute()
const equipmentId = computed(() => typeof route.query.equipment_id === 'string' ? route.query.equipment_id : '')
const assetId = computed(() => typeof route.query.asset_id === 'string' ? route.query.asset_id : '')
const componentId = computed(() => typeof route.query.component_id === 'string' ? route.query.component_id : '')
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const results = ref<KnowledgeEvidence[]>([])
const searching = ref(false)
const hasSearched = ref(false)
const pageError = ref<string | null>(null)
const pageErrorCode = ref<string | null>(null)
const portal = usePortalStore()
const subjectKey = computed(() => portal.user?.id || null)
const drawer = useEvidenceResolution(() => subjectKey.value, () => { results.value = [] })
const { open: drawerOpen, loading: drawerLoading, evidence: drawerEvidence, error: drawerError } = drawer
let subjectGeneration = 0
let searchGeneration = 0
watch(subjectKey, () => {
  subjectGeneration++; searchGeneration++; drawer.close()
  status.value = null; results.value = []; query.value = ''; searching.value = false
  spaces.value = []; catalog.value = []; selectedSpace.value = ''
  pageError.value = null; pageErrorCode.value = null; hasSearched.value = false
  if (subjectKey.value) void refreshStatus()
}, { flush: 'sync' })
watch(selectedSpace, () => {
  searchGeneration++; drawer.close(); results.value = []; hasSearched.value = false
  searching.value = false; pageError.value = null; pageErrorCode.value = null
}, { flush: 'sync' })
onBeforeUnmount(() => { subjectGeneration++; searchGeneration++; drawer.close() })

const statusLabel = computed(() => {
  if (!status.value) return '正在核验服务与资料权限…'
  if (!status.value.can_enter) return '当前账号没有知识助理访问权限'
  if (!status.value.can_search) return '当前没有已发布且可检索的资料范围'
  if (!status.value.gateway_configured) return 'Gateway 尚未完成本地安全配置'
  return status.value.environment === 'synthetic' ? '隔离合成环境 · 检索链路已配置' : '内部共享参考库 · 检索服务已连接'
})
const statusTone = computed(() => status.value?.can_search && status.value?.gateway_configured ? 'ready' : 'waiting')
const canSubmit = computed(() => Boolean(subjectKey.value && status.value?.can_search && status.value?.gateway_configured))

function applyError(error: unknown) {
  const apiError = error instanceof DomainApiError ? error : null
  pageErrorCode.value = apiError?.code || 'SERVICE_ERROR'
  pageError.value = apiError?.message || '知识服务暂时不可用。'
}

async function submitSearch() {
  const normalized = query.value.trim()
  if (!normalized || searching.value || !subjectKey.value) return
  const generation = ++searchGeneration
  const subject = subjectKey.value
  drawer.close()
  searching.value = true
  hasSearched.value = true
  pageError.value = null
  pageErrorCode.value = null
  results.value = []
  try {
    const response = await searchKnowledge(normalized, {
      equipment_id: equipmentId.value || undefined,
      asset_id: assetId.value || undefined,
      component_id: componentId.value || undefined,
    }, selectedSpace.value ? [selectedSpace.value] : undefined)
    if (generation === searchGeneration && subject === subjectKey.value) { results.value = response.results; void tools.value?.refresh() }
  } catch (error) {
    if (generation === searchGeneration && subject === subjectKey.value) applyError(error)
  } finally {
    if (generation === searchGeneration) searching.value = false
  }
}

async function replaySaved(value: string, spaces: string[]) { selectedSpace.value=spaces.length === 1 ? spaces[0]! : ''; query.value=value; await submitSearch() }

async function openEvidence(item: KnowledgeEvidence) {
  await drawer.show(item.evidence_id)
}

async function refreshStatus() {
  const generation = subjectGeneration
  try {
    const [current, currentSpaces] = await Promise.all([getKnowledgeStatus(), getKnowledgeSpaces()])
    if (generation !== subjectGeneration || !subjectKey.value) return
    status.value = current
    spaces.value = currentSpaces
    if (current.environment === 'production') {
      const docs = await getKnowledgeDocuments()
      if (generation === subjectGeneration && subjectKey.value) catalog.value = docs
    }
    if (route.query.auto === '1' && query.value.trim() && canSubmit.value) await submitSearch()
  } catch (error) {
    if (generation === subjectGeneration) applyError(error)
  }
}
onMounted(refreshStatus)

</script>

<style scoped>
.knowledge-page { display: grid; gap: 18px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.knowledge-search:focus-within { outline: 2px solid var(--hbos-brand-violet); outline-offset: 3px; }
.kt-breadcrumb { display: flex; align-items: center; gap: 7px; color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); }
.kt-breadcrumb a { color: inherit; }
.kt-breadcrumb span { color: #3f557a; font-weight: 700; }
.kt-page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; }
.kt-page-heading h1 { margin: 0; color: #193661; font-size: var(--hbos-font-page-title); letter-spacing: -.8px; }
.kt-page-heading p { margin: 6px 0 0; color: var(--hbos-text-muted); }
.heading-actions { display:flex;align-items:center;gap:10px; }
.knowledge-grid { display: grid; grid-template-columns: minmax(0,1fr) 290px; gap: 18px; }
.knowledge-primary { min-width: 0; display: grid; align-content: start; gap: 16px; }
.knowledge-hero { position: relative; overflow: hidden; min-height: 332px; padding: 36px; border-radius: 28px; box-shadow: var(--hbos-shadow-hero); }
.knowledge-hero::after { content:""; position:absolute; width:330px; height:330px; right:-80px; top:-100px; border-radius:50%; background:radial-gradient(circle,rgba(83,173,255,.23),transparent 68%); pointer-events:none; }
.knowledge-hero.compact { min-height: 245px; }
.knowledge-hero.compact h2 { font-size: var(--hbos-font-page-title); line-height: var(--hbos-line-page-title); letter-spacing: -.5px; }
.knowledge-eyebrow { color: #6476a6; font-size: var(--hbos-font-meta); font-weight: 800; letter-spacing: .08em; }
.knowledge-hero h2 { position: relative; z-index: 1; margin: 18px 0 10px; color: #183661; font-size: var(--hbos-font-hero); line-height: 1.06; letter-spacing: -2px; }
.knowledge-hero h2 span { background:linear-gradient(90deg,#6762ff,#4aa7ff,#42c8b8); background-clip:text; color:transparent; }
.knowledge-hero > p { margin: 0 0 22px; color: var(--hbos-text-secondary); }
.knowledge-search { position: relative; z-index: 1; display: grid; grid-template-columns: auto 1fr auto; gap: 11px; align-items: center; padding: 8px 9px 8px 15px; border: 1px solid rgba(70,95,140,.14); border-radius: 17px; background: rgba(255,255,255,.83); box-shadow: 0 14px 38px rgba(54,78,124,.10); }
.knowledge-search > :first-child { color: #687da4; }
.knowledge-search input { min-width: 0; border: 0; outline: 0; background: transparent; color: var(--hbos-text-primary); font-size: var(--hbos-font-body); }
.knowledge-search .ant-btn { height: 40px; border: 0; border-radius: 12px; background: linear-gradient(135deg,#5b63ff,#46a1ff); }
.knowledge-state-line { position: relative; z-index: 1; display: flex; align-items: center; gap: 8px; margin-top: 14px; color: #657896; font-size: var(--hbos-font-meta); }
.knowledge-space-filter { position: relative; z-index: 1; display: flex; align-items: center; flex-wrap: wrap; gap: var(--hbos-space-2); margin-top: var(--hbos-space-3); color: var(--hbos-text-secondary); font-size: var(--hbos-font-body); }
.knowledge-space-filter select { max-width: 100%; padding: var(--hbos-space-2); border: 1px solid var(--hbos-border-strong); border-radius: var(--hbos-radius-sm); color: var(--hbos-text-primary); background: var(--hbos-bg-surface); font: inherit; }
.state-dot { width: 7px; height: 7px; border-radius: 50%; background: #e5a42c; box-shadow: 0 0 0 4px rgba(229,164,44,.11); }
.state-dot.ready { background: #1bbc86; box-shadow: 0 0 0 4px rgba(27,188,134,.11); }
.revision { margin-left: auto; font-family: var(--hbos-font-mono); font-size: var(--hbos-font-meta); }
.knowledge-alert,.knowledge-start,.knowledge-results { border-radius: 23px; }
.knowledge-start,.knowledge-results { padding: 22px; }
.section-title { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.section-title h2 { margin: 0; color: #203b66; font-size: var(--hbos-font-section-title); }
.section-title p { margin: 4px 0 0; color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); }
.topic-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 12px; }
.topic-grid article { padding: 17px; border: 1px solid rgba(65,91,138,.09); border-radius: 18px; background: rgba(255,255,255,.62); }
.topic-grid article > :first-child { color: #626bf6; font-size: var(--hbos-font-section-title); }
.topic-grid h3 { margin: 12px 0 7px; font-size: var(--hbos-font-body); }
.topic-grid p { margin: 0; color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); line-height: 1.6; }
.knowledge-bridge { display: grid; grid-template-columns: auto 1fr auto; gap: 13px; align-items: center; margin-top: 14px; padding: 15px; border-radius: 17px; background: linear-gradient(100deg,rgba(103,95,255,.09),rgba(72,205,188,.07)); }
.knowledge-bridge > :first-child { color: #5d66f5; font-size: var(--hbos-font-section-title); }
.knowledge-bridge strong,.knowledge-bridge span { display:block; }
.knowledge-bridge strong { font-size: var(--hbos-font-meta); }.knowledge-bridge span { margin-top:3px;color:var(--hbos-text-muted);font-size: var(--hbos-font-meta); }
.result-list { display: grid; gap: 11px; }
.result-card { padding: 18px; border: 1px solid rgba(65,91,138,.09); border-radius: 18px; background: rgba(255,255,255,.67); transition: transform .16s ease, box-shadow .16s ease; }
.result-card:hover { transform: translateY(-2px); box-shadow: 0 14px 38px rgba(50,72,113,.08); }
.result-actions { display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:12px; }
.result-meta { flex-wrap:wrap;display:flex;align-items:center;gap:8px;color:var(--hbos-text-muted);font-size: var(--hbos-font-meta); }
.result-card h3 { margin: 12px 0 3px; color:#243e66;font-size: var(--hbos-font-body);word-break:break-all; }
.section-label { margin:0;color:var(--hbos-text-muted);font-size: var(--hbos-font-meta); }
.status-note { margin:8px 0 0;color:#9a6b24;font-size: var(--hbos-font-meta); }
.excerpt-preview { display:-webkit-box;overflow:hidden;margin:12px 0;color:var(--hbos-text-secondary);font-size: var(--hbos-font-meta);line-height:1.7;-webkit-box-orient:vertical;-webkit-line-clamp:3; }
.result-card button { display:flex;align-items:center;gap:6px;padding:0;border:0;background:transparent;color:#5365e9;font-size: var(--hbos-font-meta);font-weight:750;cursor:pointer; }
.knowledge-footer { display:flex;justify-content:space-between;gap:12px;color:var(--hbos-text-muted);font-size: var(--hbos-font-meta); }
.knowledge-secondary { display:grid;align-content:start;gap:14px; }
.knowledge-side-card { padding:20px;border-radius:22px; }
.side-icon { display:grid;width:42px;height:42px;place-items:center;border-radius:14px;color:#fff;background:linear-gradient(135deg,#6c63ff,#4aa8ff); }
.knowledge-side-card h3 { margin:15px 0 8px;color:#223e68;font-size: var(--hbos-font-card-title); }
.knowledge-side-card > p { margin:0;color:var(--hbos-text-muted);font-size: var(--hbos-font-meta);line-height:1.65; }
.connection { display:flex;align-items:center;gap:7px;margin-top:15px;padding:10px;border-radius:12px;background:rgba(72,91,126,.05);color:#6d7e99;font-size: var(--hbos-font-meta); }
.connection span { width:7px;height:7px;border-radius:50%;background:#e5a42c; }
.knowledge-side-card > small { color:#6577a2;font-size: var(--hbos-font-meta);font-weight:800;letter-spacing:.08em; }
ol { display:grid;gap:17px;margin:17px 0 0;padding:0;list-style:none; }
li { display:grid;grid-template-columns:30px 1fr;gap:10px; }
li b { color:#626bf6;font-size: var(--hbos-font-meta); } li span { color:var(--hbos-text-muted);font-size: var(--hbos-font-meta);line-height:1.55; } li strong { display:block;margin-bottom:3px;color:#304868;font-size: var(--hbos-font-meta); }
@media (max-width: 1180px) { .knowledge-grid { grid-template-columns:1fr; }.knowledge-secondary{grid-template-columns:1fr 1fr;} }
@media (max-width: 700px) { .knowledge-hero h2 { font-size: var(--hbos-font-page-title); line-height: var(--hbos-line-page-title); letter-spacing: -.5px; } .knowledge-hero{padding:24px 18px;}.knowledge-search{grid-template-columns:auto 1fr;}.knowledge-search .ant-btn{grid-column:1/-1}.topic-grid,.knowledge-secondary{grid-template-columns:1fr}.knowledge-footer{flex-direction:column}.kt-page-heading{align-items:flex-start;flex-direction:column}.heading-actions{width:100%;justify-content:space-between}.knowledge-bridge{grid-template-columns:auto 1fr}.knowledge-bridge .ant-btn{grid-column:1/-1} }
</style>

<style scoped>
.department-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 12px; }
.department-grid button { display: grid; justify-items: start; gap: 8px; padding: 20px; border: 1px solid var(--hbos-border-strong); border-radius: 18px; background: rgba(255,255,255,.65); color: var(--hbos-text-primary); text-align: left; font: inherit; cursor: pointer; }
.department-grid button[aria-pressed="true"] { border-color: var(--hbos-brand-violet); }
.department-grid span,.catalog-row p { color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); }
.catalog-row { display: flex; justify-content: space-between; align-items: start; gap: 12px; padding: 16px 0; border-top: 1px solid var(--hbos-border-strong); }
.catalog-row strong { font-size: var(--hbos-font-body); overflow-wrap: anywhere; }
.catalog-row p { margin: 6px 0 0; overflow-wrap: anywhere; }
.result-meta :deep(.ant-tag),.catalog-row :deep(.ant-tag) { width: auto; flex: 0 0 auto; }
button:focus-visible { outline: 2px solid var(--hbos-brand-violet); outline-offset: 3px; }
</style>
