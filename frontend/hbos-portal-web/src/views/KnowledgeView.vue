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
        <a-tag v-if="mode === 'search' && equipmentId" color="geekblue">设备上下文 {{ equipmentId }}</a-tag>
        <a-tag v-if="mode === 'search' && assetId" color="geekblue">资产范围 {{ assetId }}</a-tag>
        <a-tag v-if="mode === 'search' && componentId" color="geekblue">组件范围 {{ componentId }}</a-tag>
      </div>
    </header>

    <a-alert v-if="retrievalBlocked" type="warning" show-icon role="status"
      message="检索服务暂不可用，目录与个人记录仍可查看。"
      :description="blockedDescription" />

    <div class="knowledge-grid">
      <div class="knowledge-primary">
        <section class="knowledge-hero hbos-glass-g3">
          <div class="knowledge-eyebrow"><BulbOutlined /> 查阅已收录的内部参考资料</div>
          <h2>从资料中<span>找到依据。</span></h2>
          <p>先选范围，再明确你要查找或确认的内容。</p>
          <div class="composer-toolbar">
            <div class="knowledge-modes" role="group" aria-label="知识使用方式">
              <button type="button" :aria-pressed="mode === 'ask'" :disabled="!status?.ask_enabled" @click="setMode('ask')">问知识</button>
              <button type="button" :aria-pressed="mode === 'search'" @click="setMode('search')">搜资料</button>
            </div>
            <div class="knowledge-space-filter">
              <label for="knowledge-space">部门范围</label>
              <select id="knowledge-space" v-model="selectedSpace" :disabled="!spaces.length">
                <option value="">全部已收录资料</option>
                <option v-for="space in spaces" :key="space.space_id" :value="space.space_id">{{ space.title }} · {{ space.document_count }} 份资料</option>
              </select>
            </div>
          </div>
          <form class="knowledge-search" :class="{ 'ask-composer': mode === 'ask' }" @submit.prevent="submitComposer">
            <SearchOutlined v-if="mode === 'search'" aria-hidden="true" />
            <label class="sr-only" for="knowledge-query">{{ mode === 'ask' ? '你的知识问题' : '描述工作中的问题' }}</label>
            <input v-if="mode === 'search'" id="knowledge-query" v-model="query" maxlength="500" autocomplete="off" placeholder="输入资料标题、文件编号或制度关键词…" :disabled="working" @compositionstart="composing = true" @compositionend="composing = false" @keydown="composerKeydown" />
            <textarea v-else id="knowledge-query" v-model="query" maxlength="280" placeholder="描述希望从资料中确认的问题…" :disabled="working" @compositionstart="composing = true" @compositionend="composing = false" @keydown="composerKeydown" />
            <a-button type="primary" html-type="submit" :loading="working" :disabled="working || !canSubmit || !query.trim() || inputTooLong">{{ mode === 'ask' ? hasConversation ? '继续追问' : '提交问题' : '搜资料' }}<ArrowRightOutlined /></a-button>
          </form>
          <div class="composer-help"><span>{{ mode === 'ask' ? 'Ctrl / ⌘ + Enter 提交；Enter 换行。回答仅供内部参考。' : 'Enter 搜索；只查当前范围内已收录资料。' }}</span><span :class="{ 'over-limit': inputTooLong }">{{ [...query].length }} / {{ mode === 'ask' ? 280 : 500 }}</span></div>
          <div class="composer-actions">
            <a-button v-if="working" size="small" @click="cancelPending">返回编辑</a-button>
            <a-button v-if="mode === 'ask' && hasConversation" size="small" :disabled="working" @click="startNewQuestion">新问题</a-button>
            <span v-if="working" class="muted">返回编辑会丢弃晚响应；实际用量以服务端记录为准。</span>
            <span v-if="composerNotice" role="status" class="muted">{{ composerNotice }}</span>
          </div>
          <div class="knowledge-state-line" role="status" aria-live="polite">
            <span :class="['state-dot', statusTone]"></span>
            {{ statusLabel }}
            <span v-if="retrievalBlocked" class="observation-note">检索待恢复</span>
            <span v-if="status?.retrieval_availability?.status === 'UNKNOWN' && status.retrieval_availability.last_success_at" class="observation-note">较早成功已过观察期限</span>
            <a-button size="small" :disabled="statusLoading" :loading="statusLoading" @click="refreshStatus">刷新状态</a-button>
          </div>
        </section>

        <a-alert
          v-if="pageError"
          :type="pageErrorCode === 'FORBIDDEN' ? 'warning' : 'error'"
          show-icon
          :message="pageError"
          class="knowledge-alert"
        />



        <section v-if="mode === 'search' && hasSearched" class="knowledge-results hbos-glass-g2">
          <div class="section-title">
            <div><h2>检索依据</h2><p>{{ currentScopeLabel }} · 本次检索时点的资料依据</p></div>
            <a-tag>{{ results.length }} 条</a-tag>
          </div>
          <a-empty v-if="!searching && !results.length && !pageError" description="未找到相关依据，请换一个关键词或调整部门范围。" />
          <a-skeleton v-if="searching" active :paragraph="{ rows: 6 }" />
          <div v-else class="result-list">
            <article v-for="item in results" :key="item.evidence_id" class="result-card">
              <div class="result-meta"><a-tag color="geekblue">{{ spaces.find(s => s.space_id === item.space_id)?.title || '检索依据' }}</a-tag><span>{{ item.version || '版本待核' }}</span><a-tag color="orange">状态待核</a-tag></div>
              <h3>{{ item.title || '未标注标题' }}</h3>
              <p v-if="item.document_number" class="section-label">{{ item.document_number }}</p>
              <p v-if="item.status_note" class="status-note">{{ item.status_note }}</p>
              <p class="section-label">{{ item.section || '章节未标注' }}</p>
              <p class="excerpt-preview">{{ item.excerpt }}</p>
              <div class="result-actions"><button type="button" @click="openEvidence(item)">查看依据 <ArrowRightOutlined /></button><template v-if="status?.environment === 'production'"><a-button size="small" :disabled="working" @click="tools?.bookmark(item)">收藏</a-button><a-button size="small" :disabled="working" @click="tools?.feedback(item)">反馈</a-button></template></div>
            </article>
          </div>
        </section>

        <KnowledgeTools v-if="status?.environment === 'production' && status.can_enter && subjectKey" ref="tools" :subject="subjectKey" :query="query" :selected-space="selectedSpace" :ask-enabled="Boolean(status?.ask_enabled)" :retrieval-blocked="retrievalBlocked" :mode="mode" composer-external @busy="askBusy = $event" @conversation="hasConversation = $event" @replay="replaySaved" @evidence="drawer.show" @upstream-error="refreshStatus" @access-error="applyError" @evidence-invalidated="invalidateEvidence">
          <template #catalog>
            <div class="catalog-heading"><p>只展示当前可读的已收录资料；内部参考／有效性待核。</p><a-tag>{{ catalogTotal }} 份</a-tag></div>
            <form class="catalog-filter" @submit.prevent="refreshCatalog">
              <label class="sr-only" for="catalog-query">筛选资料标题或文档编号</label>
              <input id="catalog-query" v-model="catalogQuery" class="catalog-query" type="search" maxlength="240" placeholder="筛选资料标题或文档编号…" />
              <a-button html-type="submit" :loading="catalogLoading">筛选</a-button>
            </form>
            <div class="catalog-content" :aria-busy="catalogLoading">
              <a-skeleton v-if="catalogLoading" active :paragraph="{ rows: 4 }" />
              <a-alert v-else-if="catalogError" type="error" show-icon :message="catalogError" />
              <a-empty v-else-if="!catalog.length" :description="catalogQuery.trim() ? '没有匹配的资料，请调整标题、文号或部门范围。' : '当前范围暂无可查阅的已收录资料。'" />
              <template v-else><article v-for="doc in catalog" :key="doc.document_id" class="catalog-row"><div><strong>{{ doc.title || '未标注标题' }}</strong><p>{{ doc.document_number || '文档编号待核' }} · {{ doc.version || '版本待核' }}</p><small>{{ doc.status_note || '内部参考／有效性待核' }}</small></div><a-tag>{{ doc.department }}</a-tag></article></template>
            </div>
            <a-pagination v-if="catalogTotal > catalogPageSize" v-model:current="catalogPage" :page-size="catalogPageSize" :total="catalogTotal" :show-size-changer="false" :disabled="catalogLoading" size="small" :show-less-items="true" />
          </template>
        </KnowledgeTools>

        <section v-if="!hasSearched && !pageError" class="knowledge-start hbos-glass-g2">
          <div class="section-title">
            <div><h2>按部门查阅</h2><p>部门用于分类，选择部门不会自动检索或调用模型。</p></div>
            <a-tag>{{ spaces.reduce((n, s) => n + s.document_count, 0) }} 份资料</a-tag>
          </div>
          <div class="department-grid">
            <button v-for="space in spaces" :key="space.space_id" type="button" :aria-pressed="selectedSpace === space.space_id" @click="selectDepartment(space.space_id)">
              <ApartmentOutlined /><strong>{{ space.title }}</strong><span>{{ space.document_count }} 份已收录资料</span>
            </button>
          </div>
          <a-empty v-if="!spaces.length" description="暂无可查阅的部门资料" />
        </section>

        <footer class="knowledge-footer">
          <span><SafetyCertificateOutlined /> 仅展示必要摘录，不提供原文下载。</span>
          <span>资料未经现行性核验时，请向文控或资料维护人确认。</span>
        </footer>
      </div>

    </div>

    <EvidenceDrawer
      :open="drawerOpen"
      :loading="drawerLoading"
      :evidence="drawerEvidence"
      :error="drawerError"
      :error-code="drawerErrorCode"
      @close="drawer.close()"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ApartmentOutlined, ArrowRightOutlined, BulbOutlined, RightOutlined, SafetyCertificateOutlined, SearchOutlined } from '@ant-design/icons-vue'
import type { KnowledgeEvidence, KnowledgeStatus, KnowledgeSpace, KnowledgeDocument, KnowledgeSearchContext } from '@/contracts/p1'
import { DomainApiError, getKnowledgeStatus, getKnowledgeSpaces, getKnowledgeDocumentsPage, searchKnowledge } from '@/services/p1Api'
import EvidenceDrawer from '@/components/knowledge/EvidenceDrawer.vue'
import KnowledgeTools from '@/components/knowledge/KnowledgeTools.vue'
import { useEvidenceResolution } from '@/composables/useEvidenceResolution'
import { usePortalStore } from '@/stores/portal'

const route = useRoute()
const portal = usePortalStore()
const subjectKey = computed(() => portal.user?.id || null)
const savedContext = ref<KnowledgeSearchContext | null>(null)
const currentContext = computed<KnowledgeSearchContext>(() => savedContext.value ?? {
  equipment_id: typeof route.query.equipment_id === 'string' ? route.query.equipment_id : undefined,
  asset_id: typeof route.query.asset_id === 'string' ? route.query.asset_id : undefined,
  component_id: typeof route.query.component_id === 'string' ? route.query.component_id : undefined,
})
const equipmentId = computed(() => currentContext.value.equipment_id || '')
const assetId = computed(() => currentContext.value.asset_id || '')
const componentId = computed(() => currentContext.value.component_id || '')
const status = ref<KnowledgeStatus | null>(null)
const statusLoading = ref(false)
const spaces = ref<KnowledgeSpace[]>([])
const selectedSpace = ref('')
const savedScopeNeedsSelection = ref(false)
const mode = ref<'search' | 'ask'>('search')
const query = ref(typeof route.query.q === 'string' ? [...route.query.q].slice(0, 500).join('') : '')
const composing = ref(false)
const results = ref<KnowledgeEvidence[]>([])
const searching = ref(false)
const askBusy = ref(false)
const hasSearched = ref(false)
const hasConversation = ref(false)
const working = computed(() => searching.value || askBusy.value)
const inputTooLong = computed(() => [...query.value].length > (mode.value === 'ask' ? 280 : 500))
const pageError = ref<string | null>(null)
const pageErrorCode = ref<string | null>(null)
const composerNotice = ref('')
const catalog = ref<KnowledgeDocument[]>([])
const catalogTotal = ref(0)
const catalogQuery = ref('')
const catalogPage = ref(1)
const catalogPageSize = 12
const catalogLoading = ref(false)
const catalogError = ref('')
const tools = ref<InstanceType<typeof KnowledgeTools> | null>(null)
const drawer = useEvidenceResolution(() => subjectKey.value, invalidateEvidence, () => document.getElementById('knowledge-query')?.focus())
const { open: drawerOpen, loading: drawerLoading, evidence: drawerEvidence, error: drawerError, errorCode: drawerErrorCode } = drawer
let subjectGeneration = 0
let searchGeneration = 0
let statusGeneration = 0
let catalogGeneration = 0
let catalogTimer: ReturnType<typeof setTimeout> | null = null
const accessFailureCodes = ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE']

const currentScopeLabel = computed(() => spaces.value.find(s => s.space_id === selectedSpace.value)?.title || '全部已收录资料')
const retrievalBlocked = computed(() => Boolean(status.value?.retrieval_availability?.blocked || status.value?.retrieval_availability?.status === 'OBSERVED_ERROR' || ['ACCOUNTING_PENDING', 'EXPIRED', 'EXHAUSTED', 'UNAVAILABLE'].includes(status.value?.retrieval_availability?.budget_status || '')))
const canSubmit = computed(() => Boolean(subjectKey.value && status.value?.can_enter && status.value?.can_search && status.value?.gateway_configured && !retrievalBlocked.value && !savedScopeNeedsSelection.value && (mode.value === 'search' || status.value?.ask_enabled)))
const statusTone = computed(() => status.value?.retrieval_availability?.status === 'AVAILABLE' && !retrievalBlocked.value ? 'ready' : 'waiting')
const blockedDescription = computed(() => {
  const availability = status.value?.retrieval_availability
  if (availability?.budget_status === 'ACCOUNTING_PENDING') return '当前阻断来自费用核验与原累计预算门槛。较早的检索结果不能放行新调用；刷新状态不会调用模型。'
  if (availability?.budget_status === 'EXHAUSTED') return '当前剩余累计预算不足以继续调用。刷新状态不会改变预算或试调用模型。'
  if (availability?.budget_status === 'EXPIRED') return '当前调用授权已过期。刷新状态不会自动续期或试调用模型。'
  if (availability?.budget_status === 'UNAVAILABLE') return '暂时无法核验调用预算。刷新状态不会绕过预算门槛或试调用模型。'
  if (availability?.status === 'OBSERVED_ERROR' || availability?.observed_error) return '当前提示依据最近真实调用的错误观察。恢复后可重新提交检索；刷新页面不会试调用模型。'
  return '当前检索仍有阻断记录，可用性需实际检索确认。刷新页面不会自动试调用模型。'
})
const statusLabel = computed(() => {
  if (!status.value) return '正在核验服务与资料权限…'
  if (!status.value.can_enter) return '当前账号没有知识助理访问权限'
  if (!status.value.can_search) return '当前没有已发布且可检索的资料范围'
  if (!status.value.gateway_configured) return '检索链路尚未完成配置'
  const budget = status.value.retrieval_availability?.budget_status
  if (budget === 'ACCOUNTING_PENDING') return '费用待对账 · 检索与问答暂停，目录和个人记录可查看'
  if (budget === 'EXHAUSTED') return '当前累计预算不足 · 检索与问答暂停'
  if (budget === 'EXPIRED') return '调用授权已过期 · 检索与问答暂停'
  if (budget === 'UNAVAILABLE') return '当前无法核验调用预算 · 检索与问答暂停'
  if (retrievalBlocked.value) return '检索服务暂不可用，目录与个人记录仍可查看。'
  if (status.value.retrieval_availability?.status === 'AVAILABLE') return '最近检索成功 · 当前资料权限已核验'
  return status.value.environment === 'synthetic' ? '隔离合成环境 · 检索链路已配置' : '检索链路已配置 · 当前可用性待实际检索确认'
})

watch(subjectKey, () => {
  subjectGeneration++; searchGeneration++; statusGeneration++; catalogGeneration++; drawer.close(false)
  if (catalogTimer) clearTimeout(catalogTimer)
  status.value = null; statusLoading.value = false; results.value = []; query.value = ''; composing.value = false
  searching.value = false; askBusy.value = false; hasConversation.value = false; composerNotice.value = ''
  savedContext.value = null; savedScopeNeedsSelection.value = false
  spaces.value = []; catalog.value = []; catalogTotal.value = 0; selectedSpace.value = ''; catalogQuery.value = ''; catalogPage.value = 1
  catalogLoading.value = false; catalogError.value = ''; pageError.value = null; pageErrorCode.value = null; hasSearched.value = false
  if (subjectKey.value) void refreshStatus()
}, { flush: 'sync' })
watch(selectedSpace, () => {
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false
  pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''
  if (selectedSpace.value) savedScopeNeedsSelection.value = false
}, { flush: 'sync' })
watch(() => [route.query.equipment_id, route.query.asset_id, route.query.component_id], () => { savedContext.value = null }, { flush: 'sync' })
watch([equipmentId, assetId, componentId], () => {
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false
  tools.value?.newConversation(); pageError.value = null; pageErrorCode.value = null
}, { flush: 'sync' })
watch([catalogQuery, selectedSpace], () => {
  catalogPage.value = 1; catalogGeneration++; catalog.value = []; catalogTotal.value = 0; catalogError.value = ''
  if (catalogTimer) clearTimeout(catalogTimer)
  catalogTimer = setTimeout(() => { catalogTimer = null; void refreshCatalog() }, 200)
}, { flush: 'sync' })
watch(catalogPage, () => { if (catalogTimer) clearTimeout(catalogTimer); catalogTimer = null; void refreshCatalog() })
onBeforeUnmount(() => {
  subjectGeneration++; searchGeneration++; statusGeneration++; catalogGeneration++; drawer.close(false)
  if (catalogTimer) clearTimeout(catalogTimer)
})

function applyError(error: unknown) {
  const apiError = error instanceof DomainApiError ? error : null
  pageErrorCode.value = apiError?.code || 'SERVICE_ERROR'; pageError.value = apiError?.message || '知识服务暂时不可用。'
  if (accessFailureCodes.includes(pageErrorCode.value)) {
    results.value = []; drawer.close(false); tools.value?.newConversation()
    catalogGeneration++; catalog.value = []; catalogTotal.value = 0; spaces.value = []; status.value = null
  }
}
function invalidateEvidence(code?: string) {
  results.value = []; tools.value?.invalidateSources()
  if (code && accessFailureCodes.includes(code)) applyError(new DomainApiError(code, '当前来源不可访问，请重新确认登录状态与资料权限。'))
}
function setMode(value: 'search' | 'ask') {
  if (value === mode.value || (value === 'ask' && !status.value?.ask_enabled)) return
  if (working.value) cancelPending()
  searchGeneration++; results.value = []; hasSearched.value = false
  mode.value = value; composing.value = false; drawer.close(false); pageError.value = null; pageErrorCode.value = null
  void nextTick(() => document.getElementById('knowledge-query')?.focus())
}
function cancelPending() {
  searchGeneration++; searching.value = false; hasSearched.value = false; results.value = []; tools.value?.cancelPending(); askBusy.value = false
  composerNotice.value = '已返回编辑，晚响应不会覆盖当前页面。'
}
function startNewQuestion() { tools.value?.newConversation(); query.value = ''; composerNotice.value = ''; document.getElementById('knowledge-query')?.focus() }
function selectDepartment(id: string) { selectedSpace.value = id; document.getElementById('knowledge-query')?.focus() }
function composerKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  if (composing.value || event.isComposing || event.keyCode === 229) { event.preventDefault(); return }
  if (mode.value === 'ask') { if (event.ctrlKey || event.metaKey) { event.preventDefault(); void submitComposer() } }
  else { event.preventDefault(); void submitComposer() }
}
async function submitComposer() {
  if (composing.value || working.value || !query.value.trim() || inputTooLong.value) return
  if (savedScopeNeedsSelection.value) { applyError(new DomainApiError('INVALID_REQUEST', '请选择一个明确的部门后再提交。')); return }
  if (mode.value === 'ask') {
    if (!canSubmit.value) { applyError(new DomainApiError('UPSTREAM_UNAVAILABLE', '检索服务暂不可用，目录与个人记录仍可查看。')); return }
    composerNotice.value = ''; await tools.value?.ask(query.value)
  } else await submitSearch()
}
async function submitSearch() {
  const normalized = query.value.trim()
  if (!normalized || searching.value || !subjectKey.value) return
  if (savedScopeNeedsSelection.value) { applyError(new DomainApiError('INVALID_REQUEST', '请选择一个明确的部门后再提交。')); return }
  if (!canSubmit.value) { applyError(new DomainApiError('UPSTREAM_UNAVAILABLE', '检索服务暂不可用，目录与个人记录仍可查看。')); return }
  const generation = ++searchGeneration
  const subject = subjectKey.value
  const scope = selectedSpace.value
  drawer.close(false); searching.value = true; hasSearched.value = true; pageError.value = null; pageErrorCode.value = null; composerNotice.value = ''; results.value = []
  try {
    const response = await searchKnowledge(normalized, { ...currentContext.value }, scope ? [scope] : undefined)
    if (generation === searchGeneration && subject === subjectKey.value && scope === selectedSpace.value) { results.value = response.results; void tools.value?.refresh() }
  } catch (error) {
    if (generation === searchGeneration && subject === subjectKey.value) { applyError(error); if (pageErrorCode.value === 'UPSTREAM_UNAVAILABLE') void refreshStatus() }
  } finally { if (generation === searchGeneration) searching.value = false }
}
async function replaySaved(value: string, scope: string[], context: KnowledgeSearchContext = {}) {
  setMode('search'); tools.value?.newConversation()
  searchGeneration++; drawer.close(false); results.value = []; hasSearched.value = false; searching.value = false
  selectedSpace.value = scope.length === 1 ? scope[0]! : ''
  savedContext.value = { ...context }; query.value = value
  savedScopeNeedsSelection.value = scope.length > 1 || (scope.length === 1 && !spaces.value.some(space => space.space_id === scope[0]))
  if (savedScopeNeedsSelection.value) {
    selectedSpace.value = ''
    composerNotice.value = scope.length > 1 ? '这条记录包含多个部门。请选择一个部门后再提交；不会自动检索。' : '这条记录原来的部门当前不可选。请选择一个明确部门后再提交；不会自动检索。'
    return
  }
  await nextTick()
  await submitSearch()
}
async function openEvidence(item: KnowledgeEvidence) { await drawer.show(item.evidence_id) }
async function refreshCatalog() {
  if (catalogTimer) { clearTimeout(catalogTimer); catalogTimer = null }
  if (!subjectKey.value || status.value?.environment !== 'production') return
  const generation = ++catalogGeneration
  const subject = subjectKey.value
  catalogLoading.value = true; catalogError.value = ''
  try {
    const data = await getKnowledgeDocumentsPage(catalogQuery.value, selectedSpace.value, catalogPage.value, catalogPageSize)
    if (generation !== catalogGeneration || subject !== subjectKey.value) return
    catalog.value = data.documents; catalogTotal.value = data.total
    const lastPage = Math.max(1, Math.ceil(data.total / catalogPageSize))
    if (catalogPage.value > lastPage) catalogPage.value = lastPage
  } catch (error) {
    if (generation === catalogGeneration && subject === subjectKey.value) {
      catalog.value = []; catalogTotal.value = 0; catalogError.value = error instanceof DomainApiError ? error.message : '资料目录暂时不可用。'
      if (error instanceof DomainApiError && accessFailureCodes.includes(error.code)) applyError(error)
    }
  } finally { if (generation === catalogGeneration) catalogLoading.value = false }
}
async function refreshStatus() {
  if (!subjectKey.value) return
  const generation = ++statusGeneration
  const subject = subjectGeneration
  statusLoading.value = true
  try {
    const [current, currentSpaces] = await Promise.all([getKnowledgeStatus(), getKnowledgeSpaces()])
    if (generation !== statusGeneration || subject !== subjectGeneration || !subjectKey.value) return
    if (!current.can_enter || !current.can_search || (status.value?.policy_revision && status.value.policy_revision !== current.policy_revision)) {
      searchGeneration++; results.value = []; hasSearched.value = false; searching.value = false; drawer.close(false); tools.value?.newConversation()
    }
    if (!current.can_enter) { catalogGeneration++; catalog.value = []; catalogTotal.value = 0 }
    status.value = current; spaces.value = current.can_enter ? currentSpaces : []
    if (selectedSpace.value && !currentSpaces.some(space => space.space_id === selectedSpace.value)) selectedSpace.value = ''
    if (!current.ask_enabled && mode.value === 'ask') setMode('search')
    if (current.can_enter && current.environment === 'production') await refreshCatalog()
    // Page loads and deep-link prefills never call a model.
  } catch (error) { if (generation === statusGeneration && subject === subjectGeneration) applyError(error) }
  finally { if (generation === statusGeneration) statusLoading.value = false }
}
onMounted(refreshStatus)
</script>

<style scoped>
.knowledge-page,.knowledge-primary { display: grid; gap: 18px; min-width: 0; }.knowledge-grid { min-width: 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.kt-breadcrumb { display: flex; align-items: center; gap: 7px; color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); }.kt-breadcrumb a { color: inherit; }.kt-breadcrumb span { color: var(--hbos-text-secondary); }
.kt-page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; }.kt-page-heading h1 { margin: 0; color: #193661; font-size: 30px; line-height: 38px; letter-spacing: -.4px; }.kt-page-heading p { margin: 6px 0 0; color: var(--hbos-text-secondary); font-size: var(--hbos-font-body); }.heading-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.knowledge-hero { padding: 26px; border-radius: 24px; min-width: 0; }.knowledge-eyebrow { display: flex; gap: 8px; align-items: center; color: #347f76; font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); }.knowledge-hero h2 { margin: 12px 0 6px; color: #193661; font-size: 30px; line-height: 38px; letter-spacing: -.4px; }.knowledge-hero h2 span { background: linear-gradient(115deg,#58a994,#38a9bc); -webkit-background-clip: text; background-clip: text; color: transparent; }.knowledge-hero>p { margin: 0 0 22px; font-size: var(--hbos-font-body); color: var(--hbos-text-secondary); }
.composer-toolbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; margin-bottom: 14px; }.knowledge-modes { display: flex; gap: 4px; padding: 4px; border-radius: 12px; background: rgba(35,115,102,.07); }.knowledge-modes button { padding: 8px 18px; border: 0; border-radius: 9px; color: var(--hbos-text-secondary); background: transparent; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); cursor: pointer; }.knowledge-modes button[aria-pressed=true] { color: #146f61; background: rgba(255,255,255,.95); box-shadow: 0 2px 8px rgba(35,115,102,.08); }.knowledge-modes button:disabled { color: var(--hbos-text-muted); cursor: not-allowed; }
.knowledge-space-filter { display: flex; align-items: center; gap: 10px; min-width: 0; color: var(--hbos-text-secondary); font-size: var(--hbos-font-body); }.knowledge-space-filter label { white-space: nowrap; }.knowledge-space-filter select { max-width: 100%; min-width: 0; padding: 9px 12px; border: 1px solid var(--hbos-border-strong); border-radius: 12px; background: var(--hbos-bg-surface); color: var(--hbos-text-primary); font: inherit; }
.knowledge-search { display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: 12px; padding: 10px 12px 10px 16px; border: 1px solid var(--hbos-border-strong); border-radius: 16px; background: rgba(255,255,255,.9); }.knowledge-search:focus-within { outline: 2px solid var(--hbos-brand-aqua); outline-offset: 3px; }.knowledge-search input { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; font: inherit; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); color: var(--hbos-text-primary); }.knowledge-search textarea { grid-column: 1/-1; width: 100%; min-height: 92px; min-width: 0; resize: vertical; border: 0; outline: 0; background: transparent; font: inherit; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); color: var(--hbos-text-primary); }.ask-composer { grid-template-columns: 1fr auto; }.ask-composer .ant-btn { grid-column: 2; }
.composer-help { display: flex; justify-content: space-between; gap: 12px; margin-top: 10px; color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); }.composer-help>span:last-child { flex-shrink: 0; }.over-limit { color: #b43c50; }.composer-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 8px; }.composer-actions:empty { display: none; }.muted { font-size: var(--hbos-font-meta); color: var(--hbos-text-muted); }
.knowledge-state-line { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 18px; color: var(--hbos-text-secondary); font-size: var(--hbos-font-body); line-height: var(--hbos-line-body); }.knowledge-state-line .ant-btn { margin-left: auto; }.state-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; background: #e5a42c; box-shadow: 0 0 0 4px rgba(229,164,44,.1); }.state-dot.ready { background: #1bbc86; box-shadow: 0 0 0 4px rgba(27,188,134,.1); }.observation-note { font-size: var(--hbos-font-meta); color: var(--hbos-text-muted); }
.knowledge-results,.knowledge-start { padding: 22px; border-radius: 23px; min-width: 0; }.section-title { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 16px; }.section-title h2 { margin: 0; font-size: 20px; line-height: 28px; color: #203b66; }.section-title p { margin: 4px 0 0; font-size: var(--hbos-font-body); color: var(--hbos-text-secondary); }.result-list { display: grid; gap: 12px; }.result-card { padding: 18px; border: 1px solid var(--hbos-border-strong); border-radius: 18px; background: rgba(255,255,255,.7); min-width: 0; }.result-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); }.result-card h3 { margin: 12px 0 5px; color: #243e66; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); overflow-wrap: anywhere; }.section-label,.status-note { font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); margin: 4px 0; color: var(--hbos-text-muted); }.status-note { color: #96702d; }.excerpt-preview { margin: 12px 0; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); color: var(--hbos-text-secondary); overflow-wrap: anywhere; }.result-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 14px; }.result-actions>button { display: flex; align-items: center; gap: 6px; border: 0; background: transparent; padding: 6px 0; font-size: var(--hbos-font-body); line-height: var(--hbos-line-body); color: #247a70; cursor: pointer; }
.catalog-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }.catalog-heading p { margin: 0 0 12px; color: var(--hbos-text-secondary); font-size: var(--hbos-font-body); }.catalog-filter { display: flex; gap: 10px; margin-bottom: 12px; }.catalog-query { width: 100%; min-width: 0; padding: 10px 14px; border: 1px solid var(--hbos-border-strong); border-radius: 12px; font: inherit; background: rgba(255,255,255,.82); color: var(--hbos-text-primary); }.catalog-content { min-height: 150px; }.catalog-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 16px 0; border-top: 1px solid var(--hbos-border-strong); }.catalog-row>div { min-width: 0; }.catalog-row strong { font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); overflow-wrap: anywhere; }.catalog-row p { margin: 6px 0 2px; font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); color: var(--hbos-text-muted); overflow-wrap: anywhere; }.catalog-row small { font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); color: #96702d; }.catalog-row :deep(.ant-tag) { flex-shrink: 0; max-width: 34%; white-space: normal; overflow-wrap: anywhere; }
.department-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 12px; }.department-grid button { display: grid; justify-items: start; gap: 8px; padding: 16px; border: 1px solid var(--hbos-border-strong); border-radius: 16px; background: rgba(255,255,255,.65); color: var(--hbos-text-primary); text-align: left; font: inherit; cursor: pointer; }.department-grid button[aria-pressed=true] { border-color: #48bca6; background: rgba(236,252,247,.7); }.department-grid strong { font-size: var(--hbos-font-card-title); }.department-grid span { color: var(--hbos-text-muted); font-size: var(--hbos-font-meta); }
.knowledge-footer { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px; font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); color: var(--hbos-text-muted); }button:focus-visible,select:focus-visible,.catalog-query:focus-visible { outline: 2px solid var(--hbos-brand-aqua); outline-offset: 3px; }
@media(max-width:700px) { .kt-page-heading { align-items: flex-start; flex-direction: column; gap: 10px; }.knowledge-hero { padding: 20px 16px; }.knowledge-hero h2 { font-size: 20px; line-height: 28px; }.composer-toolbar { align-items: flex-start; flex-direction: column; }.knowledge-space-filter { width: 100%; }.knowledge-space-filter select { flex: 1; }.knowledge-search { grid-template-columns: auto minmax(0,1fr); }.knowledge-search .ant-btn { grid-column: 1/-1; width: 100%; }.composer-help { flex-wrap: wrap; gap: 4px; }.knowledge-state-line .ant-btn { margin-left: 0; }.knowledge-results,.knowledge-start { padding: 16px; }.department-grid { grid-template-columns: 1fr; } }
</style>
