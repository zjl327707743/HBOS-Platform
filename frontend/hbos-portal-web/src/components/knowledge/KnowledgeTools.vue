<template>
  <div v-if="!view" class="knowledge-tools">
    <section v-if="askEnabled && (!mode || mode === 'ask')" class="ask-area hbos-glass-g2">
      <form v-if="!composerExternal" @submit.prevent="ask()">
        <label for="knowledge-question">{{ conversation ? '继续追问' : '你的问题' }}</label>
        <textarea id="knowledge-question" v-model="question" maxlength="280" :disabled="busy || retrievalBlocked" placeholder="描述希望从资料中确认的问题…" @compositionstart="composing = true" @compositionend="composing = false" @keydown="questionKeydown" />
        <div class="tool-actions"><a-button type="primary" html-type="submit" :disabled="busy || !question.trim() || retrievalBlocked" :loading="busy">{{ conversation ? '追问' : '提交问题' }}</a-button><a-button v-if="conversation" :disabled="busy" @click="startNewConversation">新建对话</a-button></div>
      </form>
      <div v-if="turns.length || busy" class="answer-heading"><h2>带来源回答</h2><p>根据本次资料范围重新检索；内部参考，请核对适用版本。</p></div>
      <a-skeleton v-if="busy && askPending" active :paragraph="{ rows: 4 }" />
      <div class="answer-list" aria-live="polite">
        <article v-for="turn in turns" :key="turn.turn_id" class="answer-card">
          <h3 class="answer-question">{{ turn.question }}</h3>
          <a-tag :color="answerTone(turn)">{{ answerLabel(turn) }}</a-tag>
          <div class="answer-text" v-html="renderSafeAnswer(turn.answer)"></div>
          <button v-for="source in turn.citations" :key="source.citation_label" type="button" class="citation-link" @click="emit('evidence', source.evidence_id)">[{{ source.citation_label }}] {{ source.title || '未标注标题' }} · 查看依据</button>
          <p class="answer-note">本次检索时点的资料依据；再次查阅会核验当前状态。</p>
        </article>
      </div>
      <a-alert v-if="error && errorScope === 'query'" type="error" show-icon :message="error" />
      <p v-if="!turns.length && !busy" class="muted">问一个明确的问题，回答会同时列出可核验的来源。</p>
    </section>

    <section class="reference-library hbos-glass-g2">
      <div class="tool-heading"><h2>资料与我的查阅</h2><a-button size="small" :disabled="busy || refreshing" @click="refresh">刷新记录</a-button></div>
      <div class="tool-tabs" role="tablist" aria-label="资料与个人记录">
        <button v-for="tab in tabs" :id="`knowledge-tab-${tab.kind}`" :key="tab.kind" type="button" role="tab" :aria-selected="kind === tab.kind" :aria-controls="`knowledge-panel-${tab.kind}`" :tabindex="kind === tab.kind ? 0 : -1" @click="kind = tab.kind" @keydown="tabKeydown($event, tab.kind)">{{ tab.label }}</button>
      </div>
      <div :id="`knowledge-panel-${kind}`" role="tabpanel" :aria-labelledby="`knowledge-tab-${kind}`" :aria-label="activeLabel" tabindex="0">
        <slot v-if="kind === 'Catalog'" name="catalog" />
        <template v-else-if="kind === 'Feedback'">
          <div class="feedback-heading"><p class="muted">这里只显示本人提交的反馈。资料维护人通过既有管理入口处理。</p><a-button :disabled="busy || !subject" @click="generalFeedback">提交一般反馈</a-button></div>
          <a-skeleton v-if="feedbackLoading" active :paragraph="{ rows: 3 }" />
          <a-alert v-else-if="feedbackError" type="error" show-icon :message="feedbackError" />
          <a-empty v-else-if="!feedbackItems.length" description="还没有提交过反馈。可以提交使用问题，也可在检索结果中反馈资料问题。" />
          <article v-for="item in pagedFeedback" :key="item.id" class="feedback-row">
            <div><strong>{{ item.category }}</strong><p>{{ item.note || '未填写补充说明' }}</p><p v-if="item.reply" class="maintenance-reply">维护回复：{{ item.reply }}</p><small>提交 {{ displayDate(item.created_at) }} · 更新 {{ displayDate(item.updated_at) }}</small></div>
            <a-tag :color="item.status === 'Resolved' ? 'green' : item.status === 'In Review' ? 'blue' : 'orange'">{{ feedbackStatus[item.status] }}</a-tag>
          </article>
          <a-pagination v-if="feedbackItems.length > savedPageSize" v-model:current="savedPage" :page-size="savedPageSize" :total="feedbackItems.length" :show-size-changer="false" :show-less-items="true" size="small" />
        </template>
        <template v-else>
          <p class="muted">重新查阅会核验当前来源并恢复已保存的有限记录，不调用回答模型。早期未保存回答的记录可重新检索。</p>
          <a-skeleton v-if="refreshing" active :paragraph="{ rows: 3 }" />
          <a-empty v-else-if="!shown.length" :description="kind === 'History' ? '检索和问答后会在这里记录问题。' : '在检索结果中收藏资料，稍后继续查阅。'" />
          <article v-for="item in pagedSaved" :key="item.id" class="saved-row">
            <div><strong>{{ item.query }}</strong><p>{{ item.available ? item.titles.filter(Boolean).join('；') || '检索记录' : '依据已下架或版本变化，请重新检索' }}</p><small>{{ displayDate(item.created_at) }}</small></div>
            <div class="tool-actions"><a-button size="small" :disabled="busy || !item.available" @click="reopen(item.id)">重新查阅</a-button><a-button size="small" :disabled="busy" @click="remove(item.id)">删除</a-button></div>
          </article>
          <a-pagination v-if="shown.length > savedPageSize" v-model:current="savedPage" :page-size="savedPageSize" :total="shown.length" :show-size-changer="false" :show-less-items="true" size="small" />
        </template>
      </div>
      <p v-if="notice" role="status" class="tool-notice">{{ notice }}</p>
      <a-alert v-if="recordsError || (error && errorScope === 'operation' && !feedbackMode)" type="error" show-icon :message="recordsError || error" />
    </section>

    <a-modal :open="Boolean(feedbackMode)" :title="feedbackMode === 'general' ? '提交一般反馈' : '反馈资料问题'" :footer="null" :destroy-on-close="true" @cancel="requestFeedbackClose">
      <div v-if="feedbackMode" class="feedback-form">
        <p v-if="feedbackMode === 'general'" class="feedback-title">这条反馈没有关联资料来源。请描述使用中遇到的问题。</p>
        <p v-else class="feedback-title">{{ feedbackTarget?.title || '当前检索依据' }}</p>
        <a-alert v-if="error && errorScope === 'feedback'" type="error" show-icon :message="error" />
        <form @submit.prevent="sendFeedback">
          <label for="feedback-category">问题类型</label><PortalSelect id="feedback-category" v-model:value="category" :disabled="busy" :options="categories.map(value => ({ value, label: value }))" />
          <label for="feedback-note">{{ feedbackMode === 'general' ? '反馈说明（必填）' : '补充说明' }}</label><textarea id="feedback-note" v-model="note" maxlength="500" :disabled="busy" :required="feedbackMode === 'general'" placeholder="请描述需要维护人核对的问题" />
          <p class="muted">不要填写个人身份证、薪资或其他敏感个人信息。</p>
          <div class="tool-actions"><a-button type="primary" html-type="submit" :disabled="busy || (feedbackMode === 'general' && !note.trim())" :loading="busy">提交反馈</a-button><a-button :disabled="busy" @click="requestFeedbackClose">取消</a-button></div>
        </form>
      </div>
    </a-modal>
  </div>
  <div v-else class="knowledge-tools kb-tools">
    <section v-if="view==='query' && mode==='ask' && (turns.length || askPending || hasQueryError)" class="kb-panel kb-answer-panel hbos-glass-g1">
      <div class="kb-section-title"><h2>回答</h2><a-button type="text" :disabled="busy" @click="startNewConversation">新建对话</a-button></div>
      <div class="kb-answer-workspace" :class="{ 'has-sources': turns.some(turn => turn.citations.length) }">
        <div class="kb-answer-list" aria-live="polite">
          <article v-for="(turn, index) in turns" :key="turn.request_id + ':' + index" class="answer-card">
            <h3 class="answer-question">{{ turn.question }}</h3>
            <div class="kb-answer-origin"><a-tag :color="answerTone(turn)">{{ answerLabel(turn) }}</a-tag><small v-if="turn.model_alias">{{ turn.model_alias }}</small></div>
            <div class="kb-answer-copy" v-html="renderSafeAnswer(turn.answer)"></div>
          </article>
        </div>
        <aside v-if="turns.some(turn => turn.citations.length)" class="kb-answer-sources" aria-label="回答来源">
          <div class="kb-answer-sources-inner">
            <h3>参考来源</h3>
            <div class="kb-answer-source-list" tabindex="0" aria-label="各轮参考来源">
              <section v-for="(turn, index) in turns" v-show="turn.citations.length" :key="turn.request_id + ':' + index">
                <h4 v-if="turns.length > 1">第 {{ index + 1 }} 轮 · {{ turn.question }}</h4>
                <section v-for="group in citationGroups(turn)" :key="group.key" class="kb-citation-group">
                  <h4>{{ group.title }} <small v-if="group.version">{{ group.version }}</small></h4>
                  <div v-for="source in group.sources" :key="source.citation_label" class="kb-citation-row">
                    <button class="kb-source-link" @click="emit('evidence', source.evidence_id)">
                      <FileTextOutlined /><span>[{{ source.citation_label }}] {{ source.section || (source.page_number ? '第 ' + source.page_number + ' 页' : '查看依据') }}</span>
                    </button>
                    <a-button type="text" :aria-label="(isBookmarked(source) ? '取消收藏 ' : '收藏 ') + group.title" :disabled="busy" @click="bookmark(source)">
                      <StarFilled v-if="isBookmarked(source)" class="kb-star" /><StarOutlined v-else />
                    </a-button>
                    <a-button type="text" aria-label="反馈来源" @click="feedback(source)"><MessageOutlined /></a-button>
                  </div>
                </section>
              </section>
            </div>
            <p class="kb-muted">打开来源时重新核验版本与访问权限。</p>
          </div>
        </aside>
      </div>
      <a-skeleton v-if="askPending" active :paragraph="{rows:4}"/>
      <a-alert v-if="hasQueryError" class="kb-query-alert" type="error" show-icon :message="error"/>
    </section>
    <slot v-if="view==='catalog'" name="catalog"/>
    <section v-if="['favorites','history','feedback'].includes(view)" class="kb-panel hbos-glass-g1">
      <template v-if="view==='favorites'"><div class="kb-list-heading"><h2>收藏资料</h2><span v-if="!refreshing && !recordsError" class="kb-list-count">本页 {{ shown.length }} 份</span></div><div class="kb-list-toolbar kb-favorite-toolbar"><a-input-search id="favorite-query" v-model:value="favoriteQuery" placeholder="查找标题或文号" aria-label="查找收藏标题或文号"/><PortalSelect v-model:value="favoriteSpace" aria-label="筛选收藏部门" :options="[{ value: '', label: '全部已共享资料' }, ...(spaces || []).map(space => ({ value: space.space_id, label: space.title }))]" /></div><div class="kb-list-caption"><span>{{refreshing?'更新中':favoriteFilterActive?filteredFavorites.length+' 项匹配收藏':'本页 '+bookmarks.length+' 项收藏'}} · 仅本人可见</span><span>登录员工可直接阅读与下载已发布资料</span></div></template>
      <div v-if="view==='history'||view==='feedback'" class="kb-record-toolbar">
        <div class="kb-record-tabs" role="group" aria-label="我的记录视图">
          <button type="button" :aria-pressed="view==='history'" :class="{active:view==='history'}" @click="emit('records-view','history')">查阅记录</button>
          <button type="button" :aria-pressed="view==='feedback'" :class="{active:view==='feedback'}" @click="emit('records-view','feedback')">我的反馈</button>
          <button type="button" class="kb-record-link" @click="generalFeedback">反馈与建议</button>
        </div>
        <button type="button" class="kb-record-refresh" :disabled="busy||refreshing" aria-label="刷新记录" @click="refresh"><ReloadOutlined/><span>刷新记录</span></button>
      </div>
      <p v-if="view==='history'||view==='feedback'" class="kb-record-caption"><span>{{ view==='feedback' ? feedbackItems.length : shown.length }} 项记录 · 仅本人可见</span><span class="kb-record-caption-note">{{ view==='feedback' ? '回复仅向提交人与维护人展示' : '恢复已保存的有限记录，不重新调用回答模型' }}</span></p>
      <a-skeleton v-if="refreshing||feedbackLoading" active :paragraph="{rows:4}"/>
      <template v-else-if="view==='feedback'">
        <a-alert v-if="feedbackError" type="error" :message="feedbackError"/><a-empty v-else-if="!feedbackItems.length" description="还没有提交过反馈。"/>
        <article v-for="item in feedbackItems" :key="item.id" class="kb-feedback-row"><MessageOutlined/><div><strong>{{item.category}}</strong><p>{{item.note}}</p><small>{{displayDate(item.created_at)}}</small><details v-if="item.reply"><KnowledgeDisclosureSummary>查看维护人回复</KnowledgeDisclosureSummary><p>{{item.reply}}</p></details></div><a-tag :color="item.status==='Resolved'?'green':'default'">{{feedbackStatus[item.status]}}</a-tag></article>
      </template>
      <template v-else>
        <a-empty v-if="!shown.length" :description="view==='favorites'?'还没有收藏，点击资料旁的星标即可保存。':'开始一次查询后，可以在这里继续查阅。'"/>
        <article v-for="item in shown" :key="item.id" class="kb-doc-row">
          <div class="kb-doc-icon"><StarOutlined v-if="view==='favorites'"/><HistoryOutlined v-else/></div>
          <button class="kb-doc-main" :disabled="busy||!item.available" @click="reopen(item.id)"><strong>{{!item.available&&item.bookmark_type==='Document'?'已失效的收藏':view==='favorites'&&item.available?item.titles.filter(Boolean).join('；')||item.query:item.query}}</strong><p>{{item.available?(view==='favorites'?(favoriteDocument(item)?.status_note||'打开当前可用来源'):(item.answer_origin==='GENERAL'?'通用 AI 回答 · '+(item.model_alias||'通用 AI'):item.titles.filter(Boolean)[0]||'查阅记录')+(item.titles.length>1?' 等 '+item.titles.length+' 份资料':'')):'依据已下架、换版或授权变化，请重新检索。'}}</p><small v-if="view==='favorites'&&favoriteDocument(item)">{{[favoriteDocument(item)?.document_number, favoriteDocument(item)?.department, favoriteDocument(item)?.version].filter(Boolean).join(' · ')}}<a-tag color="green">已共享</a-tag></small><small v-else>{{displayDate(item.created_at)}}</small></button>
          <div class="kb-doc-actions">
            <a-button v-if="item.available" type="text" class="kb-record-open" :disabled="busy" :aria-label="view==='favorites'?'查看资料':'继续查阅'" @click="reopen(item.id)"><EyeOutlined/><span class="kb-record-open-label">{{ view==='favorites'?'查看资料':'继续查阅' }}</span></a-button>
            <a-button type="text" :disabled="busy" :aria-label="view==='favorites'?'取消收藏':'删除记录'" @click="remove(item.id)"><StarFilled v-if="view==='favorites'" class="kb-star"/><DeleteOutlined v-else/></a-button>
          </div>
        </article>
      </template>
      <div v-if="savedPage>1||savedHasMore" class="kb-pagination"><a-button :disabled="savedPage<=1||busy||refreshing||feedbackLoading" @click="savedPage--">上一页</a-button><span>第 {{savedPage}} 页</span><a-button :disabled="!savedHasMore||busy||refreshing||feedbackLoading" @click="savedPage++">下一页</a-button></div>
    </section>
    <p v-if="notice" role="status" class="kb-notice">{{notice}}</p><a-alert v-if="(recordsError && ['favorites','history'].includes(view)) || (error && errorScope === 'operation' && !feedbackMode)" type="error" show-icon :message="recordsError || error"/>
    <a-drawer :open="Boolean(feedbackMode)" title="反馈与建议" width="min(520px, 100vw)" root-class-name="kb-drawer kb-scope kb-feedback-drawer" @after-open-change="onDrawerOpenChange" @close="requestFeedbackClose"><div class="feedback-form"><p>{{feedbackTarget?.title||'说明资料、回答或使用中的问题，维护人会核对后回复。'}}</p><form @submit.prevent="sendFeedback"><label for="feedback-category">问题类型</label><PortalSelect id="feedback-category" v-model:value="category" :disabled="busy" :options="categories.map(value => ({ value, label: value }))" /><label for="feedback-note">反馈说明</label><textarea id="feedback-note" v-model="note" maxlength="500" :disabled="busy" :required="feedbackMode==='general'" placeholder="描述问题或建议…"/><a-alert v-if="error && errorScope === 'feedback'" type="error" :message="error"/><a-button type="primary" html-type="submit" :disabled="busy||(feedbackMode==='general'&&!note.trim())" :loading="busy">提交反馈</a-button></form></div></a-drawer>
  </div>
  <a-modal :open="feedbackDiscard" title="放弃未提交的反馈？" wrap-class-name="kb-scope kb-dialog" :footer="null" @cancel="feedbackDiscard = false">
    <p>离开后，本次填写的说明和所选类别将清除。</p>
    <div class="kb-drawer-actions">
      <a-button @click="feedbackDiscard = false">继续编辑</a-button>
      <a-button danger @click="closeFeedback()">放弃反馈</a-button>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import PortalSelect from '@/components/portal/PortalSelect.vue'
import KnowledgeDisclosureSummary from '@/components/knowledge/KnowledgeDisclosureSummary.vue'
import { handleDrawerLayerChange } from '@/components/knowledge/drawerDialogA11y'
import { FileTextOutlined, StarFilled, StarOutlined, HistoryOutlined, MessageOutlined, DeleteOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { computed, nextTick, onMounted, onBeforeUnmount, ref, useSlots, watch } from 'vue'
import type { KnowledgeActivity, KnowledgeAnswer, KnowledgeEvidence, KnowledgeFeedback, KnowledgeSearchContext, KnowledgeSavedQuery, KnowledgeDocument, KnowledgeSpace } from '@/contracts/p1'
import type { KnowledgeToolsReturnState } from '@/contracts/knowledgeReturn'
import { renderAnswer } from '@/services/knowledgeAnswerFormat'
import { loadConversationPointer, saveConversationPointer } from '@/services/knowledgeConversationResume'
import { loadWorkspace } from '@/services/knowledgeWorkspace'
import { askKnowledgeReference, getKnowledgeActivity, getKnowledgeFeedback, openKnowledgeSaved, removeKnowledgeSaved, saveKnowledgeBookmark, sendKnowledgeFeedback, DomainApiError, getKnowledgeActivityPage, getKnowledgeFeedbackPage, saveKnowledgeDocumentBookmark, getKnowledgeDocumentsPage } from '@/services/p1Api'

type RecordKind = 'Catalog' | 'History' | 'Bookmark' | 'Feedback'
// Template-visible wrapper: the renderer escapes first, then re-adds a closed
// set of tags, so nothing in an answer can become markup.
const renderSafeAnswer = (value: string) => renderAnswer(value)

const props = defineProps<{ subject: string; query: string; selectedSpace: string; spaces?:KnowledgeSpace[]; askEnabled: boolean; retrievalBlocked?: boolean; composerExternal?: boolean; mode?: 'search' | 'ask'; searchMode?: 'STANDARD' | 'PRECISE'; knowledgeOnly?:boolean; view?: 'query'|'catalog'|'favorites'|'history'|'feedback' }>()
const emit = defineEmits<{ replay: [query: string, spaces: string[], context?: KnowledgeSearchContext]; evidence: [id: string]; busy: [value: boolean]; conversation: [value: boolean]; 'new-conversation': []; 'upstream-error': []; 'access-error': [error: DomainApiError]; 'evidence-invalidated': []; restored: [data: KnowledgeSavedQuery]; document: [data: KnowledgeDocument]; 'records-view': [view:'history'|'feedback'] }>()
const slots = useSlots()
const tabs = computed(() => [
  ...(slots.catalog ? [{ kind: 'Catalog' as const, label: '资料目录' }] : []),
  { kind: 'History' as const, label: '最近查阅' }, { kind: 'Bookmark' as const, label: '我的收藏' }, { kind: 'Feedback' as const, label: '我的反馈' },
])
const kind = ref<RecordKind>(slots.catalog ? 'Catalog' : 'History')
const activeLabel = computed(() => tabs.value.find(tab => tab.kind === kind.value)?.label || '个人记录')
const history = ref<KnowledgeActivity[]>([])
const bookmarks = ref<KnowledgeActivity[]>([])
const feedbackItems = ref<KnowledgeFeedback[]>([])
const feedbackStatus = { Pending: '待处理', 'In Review': '处理中', Resolved: '已回复' }
const favoriteQuery=ref(''),favoriteSpace=ref(''),favoriteDocuments=ref<KnowledgeDocument[]>([]),filterFavorites=ref<KnowledgeActivity[]>([])
const favoriteFilterActive=computed(()=>Boolean(favoriteQuery.value.trim()||favoriteSpace.value))
const filteredFavorites=computed(()=>filterFavorites.value.filter(item=>(!favoriteQuery.value.trim()||(item.available?item.titles.join(' '):'已失效的收藏').toLowerCase().includes(favoriteQuery.value.trim().toLowerCase())||favoriteDocument(item)?.document_number?.toLowerCase().includes(favoriteQuery.value.trim().toLowerCase()))&&(!favoriteSpace.value||favoriteDocument(item)?.space_id===favoriteSpace.value)))
const shown = computed(() => props.view ? props.view==='history'?history.value:props.view==='favorites'&&favoriteFilterActive.value?filteredFavorites.value.slice((savedPage.value-1)*4,savedPage.value*4):bookmarks.value : kind.value === 'History' ? history.value : bookmarks.value)
const savedPage = ref(1), savedHasMore = ref(false), bookmarkIndex = ref<KnowledgeActivity[]>([])
const savedPageSize = 6
const pagedSaved = computed(() => shown.value.slice((savedPage.value - 1) * savedPageSize, savedPage.value * savedPageSize))
const pagedFeedback = computed(() => feedbackItems.value.slice((savedPage.value - 1) * savedPageSize, savedPage.value * savedPageSize))
const question = ref('')
const composing = ref(false)
const conversation = ref('')
const turns = ref<(KnowledgeAnswer & { question: string })[]>([])
function citationGroups(turn: KnowledgeAnswer) {
  const groups = new Map<string, {
    key: string; title: string; version?: string | null; sources: KnowledgeAnswer['citations']
  }>()
  for (const source of turn.citations) {
    const key = JSON.stringify([source.document_id, source.version])
    let group = groups.get(key)
    if (!group) {
      group = { key, title: source.title || '未标注标题', version: source.version, sources: [] }
      groups.set(key, group)
    }
    group.sources.push(source)
  }
  return [...groups.values()]
}
const busy = ref(false)
const askPending = ref(false)
const refreshing = ref(false)
const feedbackLoading = ref(false)
const notice = ref('')
type ErrorScope = 'query' | 'operation' | 'feedback' | 'records'
const error = ref(''), errorScope = ref<ErrorScope>('operation'), recordsError = ref('')
const hasQueryError = computed(() => Boolean(error.value && errorScope.value === 'query'))
const queryState = ref<import('@/contracts/p1').KnowledgeOperationState>('idle')
const feedbackError = ref('')
const feedbackDiscard = ref(false)
function requestFeedbackClose() {
  if (busy.value || feedbackDiscard.value) return
  if (note.value.trim() || category.value !== (feedbackMode.value === 'general' ? '其他' : '内容疑问')) feedbackDiscard.value = true
  else closeFeedback()
}
const feedbackTarget = ref<KnowledgeEvidence | null>(null)
const feedbackMode = ref<'source' | 'general' | null>(null)
const categories = ['内容疑问', '版本疑问', '检索不相关', '其他']
const category = ref('内容疑问')
const note = ref('')
let generation = 0
let recordsGeneration = 0
let feedbackGeneration = 0
let favoriteTimer: ReturnType<typeof setTimeout> | null = null
let feedbackTrigger: HTMLElement | null = null
const accessFailureCodes = ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE']

const askInFlight = ref(false)
watch([busy, askInFlight], ([working, sending]) => emit('busy', working || sending), { flush: 'sync' })
watch(() => props.view, () => {
  cancelPending(); composing.value = false; feedbackGeneration++; feedbackLoading.value = false; closeFeedback(false)
  error.value = ''; recordsError.value = ''; feedbackError.value = ''; notice.value = ''
  savedPage.value = 1; history.value = []; bookmarks.value = []; feedbackItems.value = []
  void refresh()
}, { flush: 'sync' })
watch(() => [props.mode, props.knowledgeOnly], () => { cancelPending(false); composing.value = false; error.value = ''; notice.value = ''; closeFeedback(false) }, { flush: 'sync' })
watch(savedPage,()=>{if(props.view==='favorites'&&favoriteFilterActive.value)savedHasMore.value=savedPage.value*4<filteredFavorites.value.length;else if(props.view)void refresh()})
watch([favoriteQuery,favoriteSpace],()=>{savedPage.value=1;if(favoriteTimer)clearTimeout(favoriteTimer);favoriteTimer=setTimeout(()=>{favoriteTimer=null;void refresh()},200)})
watch(kind, () => { savedPage.value = 1; if (kind.value === 'Feedback') void refreshFeedback() })
watch([history, bookmarks, feedbackItems], () => { if (props.view) return; const total = kind.value === 'Feedback' ? feedbackItems.value.length : shown.value.length; savedPage.value = Math.min(savedPage.value, Math.max(1, Math.ceil(total / savedPageSize))) })
watch(conversation, turn => saveConversationPointer(props.subject, turn), { flush: 'sync' })
watch(() => props.subject, (_subject, previous) => {
  saveConversationPointer(previous, '')
  generation++; recordsGeneration++; feedbackGeneration++
  if (favoriteTimer) { clearTimeout(favoriteTimer); favoriteTimer = null }
  favoritePageKeys.clear()
  history.value = []; bookmarks.value = []; bookmarkIndex.value=[]; feedbackItems.value = []; turns.value = []
  favoriteDocuments.value=[];filterFavorites.value=[];favoriteQuery.value='';favoriteSpace.value=''
  conversation.value = ''; question.value = ''; notice.value = ''; error.value = ''; recordsError.value = ''; feedbackError.value = ''; queryState.value = 'idle'
  closeFeedback(false); busy.value = false; askPending.value = false; refreshing.value = false; feedbackLoading.value = false
  emit('conversation', false)
  if (props.subject) void refresh()
}, { flush: 'sync' })
watch(() => [props.selectedSpace,props.searchMode], () => {
  generation++; turns.value = []; conversation.value = ''; busy.value = false; askPending.value = false
  error.value = ''; queryState.value = 'idle'; notice.value = ''; closeFeedback(false); emit('conversation', false)
}, { flush: 'sync' })
onBeforeUnmount(() => { generation++; recordsGeneration++; feedbackGeneration++; closeFeedback(false) })

function displayDate(value: string) { return value.slice(0, 16).replace('T', ' ') }
// Favorite decoration used to walk the whole catalog (up to 100 pages) on every
// favorites refresh and on every keystroke in the filter box. The catalog page
// endpoint takes no document-id filter, so the metadata is fetched once per
// view and every keystroke only re-filters what is already in memory.
const FAVORITE_CATALOG_PAGE = 50
const favoritePageKeys = new Set<string>()

async function loadFavoriteDocuments(current: number, subject: string) {
  const pageKey = `page:${savedPage.value}`
  if (favoritePageKeys.has(pageKey)) return
  favoritePageKeys.add(pageKey)
  try {
    const page = await getKnowledgeDocumentsPage('', '', savedPage.value, FAVORITE_CATALOG_PAGE)
    if (current !== recordsGeneration || subject !== props.subject) return
    const merged = new Map(favoriteDocuments.value.map(doc => [doc.document_id, doc]))
    for (const doc of page.documents) merged.set(doc.document_id, doc)
    favoriteDocuments.value = [...merged.values()]
  } catch (error) {
    favoritePageKeys.delete(pageKey)
    throw error
  }
}
// Explicit answer states from the service; the UI never infers success from
// the presence of citations alone.
const ANSWER_LABELS: Record<string, string> = {
  GENERATED_WITH_SOURCES: '已使用知识库',
  CATALOG_RESULTS: '资料目录',
  CLARIFIED: '需要补充问题',
  REFERENCE_EXCERPTS: '已找到资料，未形成归纳',
  FAILED: '回答暂不可用，已列出来源',
  REFERENCE_ANSWERED: '已使用知识库',
  GENERAL_ANSWERED: '通用 AI 回答',
  INSUFFICIENT_EVIDENCE: '没有找到相关企业依据',
  REFERENCE_ONLY: '已找到资料，未形成归纳',
}
function answerLabel(turn: KnowledgeAnswer) {
  // General-origin answers never use company sources, whatever the state field says.
  if (turn.answer_origin === 'GENERAL') return '通用 AI 回答'
  if (turn.answer_status) return ANSWER_LABELS[turn.answer_status] || '回答状态未知'
  return turn.answerable ? '已使用知识库' : '没有找到相关企业依据'
}
// Page-level operation state: a degraded excerpt answer is not a success, and
// a clarification or empty result is its own outcome, never a service error.
function answerState(data: KnowledgeAnswer): import('@/contracts/p1').KnowledgeOperationState {
  if (data.answer_status === 'GENERATED_WITH_SOURCES' || data.answer_status === 'CATALOG_RESULTS' || data.answer_status === 'GENERAL_ANSWERED' || data.answer_status === 'REFERENCE_ANSWERED') return 'success'
  if (data.answer_status === 'CLARIFIED' || data.answer_status === 'INSUFFICIENT_EVIDENCE') return 'no_evidence'
  return 'error'
}
function answerTone(turn: KnowledgeAnswer) {
  if (turn.answer_status === 'GENERATED_WITH_SOURCES' || turn.answer_status === 'REFERENCE_ANSWERED') return 'cyan'
  if (turn.answer_status === 'CATALOG_RESULTS') return 'blue'
  if (turn.answer_status === 'GENERAL_ANSWERED') return 'default'
  return 'orange'
}
function favoriteDocument(item:KnowledgeActivity){return item.available?favoriteDocuments.value.find(d=>item.document_ids?.includes(d.document_id)&&(!item.version_ids?.length||item.version_ids.includes(d.version_id||''))):undefined}
function failure(e: unknown, invalidateSource = true, scope: ErrorScope = 'operation') {
  if (e instanceof DomainApiError && ['UPSTREAM_UNAVAILABLE', 'RETRIEVAL_UPSTREAM_FAILED'].includes(e.code)) emit('upstream-error')
  if (e instanceof DomainApiError && accessFailureCodes.includes(e.code)) {
    generation++; recordsGeneration++; feedbackGeneration++
    turns.value = []; history.value = []; bookmarks.value = []; bookmarkIndex.value=[]; feedbackItems.value = []
    favoriteDocuments.value=[];filterFavorites.value=[]
    busy.value = false; refreshing.value = false; feedbackLoading.value = false; conversation.value = ''; closeFeedback(false)
    error.value = ''; recordsError.value = ''; feedbackError.value = ''; askPending.value = false
    emit('conversation', false); emit('access-error', e)
    // A technical binding adoption can invalidate an in-flight signed plan.
    // Clear its content first, then read current status once. This never
    // retries generation or restores a source whose authorization was revoked.
    if (e.code === 'SCOPE_REJECTED' && scope === 'query') emit('upstream-error')
    return
  }
  if (scope !== 'records' && invalidateSource && e instanceof DomainApiError
      && ['EVIDENCE_UNAVAILABLE', 'EVIDENCE_INVALID', 'EVIDENCE_REVOKED', 'SOURCE_VERSION_STALE'].includes(e.code)) {
    closeFeedback(false)
  }
  const message = e instanceof DomainApiError ? e.message : '知识服务暂时不可用。'
  if (scope === 'records') recordsError.value = message
  else { error.value = message; errorScope.value = scope; if (scope === 'query') queryState.value = 'error' }
}
async function refreshFeedback() {
  const current=++feedbackGeneration, subject=props.subject
  feedbackLoading.value=true;feedbackError.value=''
  try {
    const page=props.view ? await getKnowledgeFeedbackPage(savedPage.value,6) : {items:await getKnowledgeFeedback(),has_more:false}
    if(current===feedbackGeneration && subject===props.subject){feedbackItems.value=page.items;savedHasMore.value=page.has_more}
  } catch(e) { if(current===feedbackGeneration && subject===props.subject){feedbackItems.value=[];feedbackError.value=e instanceof DomainApiError?e.message:'反馈记录暂不可用。';if(e instanceof DomainApiError && accessFailureCodes.includes(e.code))failure(e)} }
  finally {if(current===feedbackGeneration)feedbackLoading.value=false}
}
async function refresh() {
  const current=++recordsGeneration, subject=props.subject
  refreshing.value=true; recordsError.value=''
  try {
    if(!props.view) {
      const [h,b]=await Promise.all([getKnowledgeActivity('History'),getKnowledgeActivity('Bookmark')])
      if(current===recordsGeneration && subject===props.subject){history.value=h;bookmarks.value=b;bookmarkIndex.value=b}
    } else if(props.view==='feedback') await refreshFeedback()
    else if(props.view==='history' || props.view==='favorites') {
      if(props.view==='favorites'&&favoriteFilterActive.value){
        const all:KnowledgeActivity[]=[]
        for(let n=1;n<=100;n++){const page=await getKnowledgeActivityPage('Bookmark',n,50);if(current!==recordsGeneration||subject!==props.subject)return;all.push(...page.items);if(!page.has_more)break;if(n===100)throw new DomainApiError('SERVICE_ERROR','收藏过多，请联系维护人。')}
        filterFavorites.value=all;bookmarkIndex.value=all
      }else{
        const page=await getKnowledgeActivityPage(props.view==='history'?'History':'Bookmark',savedPage.value,props.view==='favorites'?4:6)
        if(current!==recordsGeneration||subject!==props.subject)return
        history.value=props.view==='history'?page.items:[];bookmarks.value=props.view==='favorites'?page.items:[];if(props.view==='favorites')bookmarkIndex.value=page.items;savedHasMore.value=page.has_more
      }
      if(props.view==='favorites'){
        await loadFavoriteDocuments(current, subject)
        if(current!==recordsGeneration||subject!==props.subject)return
        if(favoriteFilterActive.value)savedHasMore.value=savedPage.value*4<filteredFavorites.value.length
      }
    } else {
      if (props.view === 'query') {
        const recent = await getKnowledgeActivityPage('History', 1, 3)
        if (current !== recordsGeneration || subject !== props.subject) return
        history.value = recent.items
      }
      let page=1,all:KnowledgeActivity[]=[]
      while(true) {
        const result=await getKnowledgeActivityPage('Bookmark',page,50)
        if(current!==recordsGeneration || subject!==props.subject)return
        all.push(...result.items)
        if(!result.has_more)break
        if(page>=100)throw new DomainApiError('SERVICE_ERROR','收藏记录过多，请联系维护人。')
        page++
      }
      bookmarkIndex.value=all
    }
  } catch(e) { if(current===recordsGeneration && subject===props.subject)failure(e,false,'records') }
  finally {if(current===recordsGeneration)refreshing.value=false}
  if(!props.view && kind.value==='Feedback')await refreshFeedback()
}
function findBookmark(item:{document_id:string;version_id?:string}) {
  return bookmarkIndex.value.find(b=>b.available && b.document_ids?.includes(item.document_id) && (!item.version_id || b.version_ids?.includes(item.version_id)))
}
function isBookmarked(item:{document_id:string;version_id?:string}) {return Boolean(findBookmark(item))}
async function toggleDocumentBookmark(doc:KnowledgeDocument) {
  if(!doc.version_id)return
  await action(async current=>{
    const old=findBookmark(doc)
    if(old)await removeKnowledgeSaved(old.id);else await saveKnowledgeDocumentBookmark(doc.document_id,doc.version_id!)
    if(current===generation){notice.value=old?'已取消收藏。':'已收藏。';await refresh()}
  })
}
async function action(run: (current: number) => Promise<void>, scope: ErrorScope = 'operation') {
  if (busy.value || !props.subject) return
  const current = generation
  busy.value = true; error.value = ''; recordsError.value = ''; errorScope.value = scope; notice.value = ''
  try { await run(current) } catch (e) { if (current === generation) failure(e, true, scope) }
  finally { if (current === generation) { busy.value = false; askPending.value = false } }
}
async function bookmark(item: KnowledgeEvidence) {
  await action(async current => {
    const old=props.view?findBookmark(item):undefined
    if(old) await removeKnowledgeSaved(old.id); else await saveKnowledgeBookmark(item.evidence_id, props.query)
    if (current === generation) { notice.value = old ? '已取消收藏。' : '已收藏。重新查阅时会核验资料状态。'; await refresh() }
  })
}
function feedback(item: KnowledgeEvidence) {
  if (busy.value) return
  feedbackTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  feedbackTarget.value = item; feedbackMode.value = 'source'; notice.value = ''; error.value = ''; errorScope.value = 'feedback'; note.value = ''; category.value = '内容疑问'
  void nextTick(() => { if (feedbackMode.value) document.getElementById('feedback-note')?.focus() })
}
function generalFeedback() {
  if (busy.value || !props.subject) return
  feedbackTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  feedbackTarget.value = null; feedbackMode.value = 'general'; notice.value = ''; error.value = ''; errorScope.value = 'feedback'; note.value = ''; category.value = '其他'
  void nextTick(() => { if (feedbackMode.value) document.getElementById('feedback-note')?.focus() })
}
function closeFeedback(restoreFocus = true) {
  feedbackDiscard.value = false
  feedbackTarget.value = null; feedbackMode.value = null; note.value = ''
  if (errorScope.value === 'feedback') error.value = ''
  if (restoreFocus && feedbackTrigger?.isConnected) feedbackTrigger.focus({ preventScroll: true })
  feedbackTrigger = null
}
async function sendFeedback() {
  const target = feedbackTarget.value
  const mode = feedbackMode.value
  const normalized = note.value.trim()
  if (!mode || (mode === 'source' && !target)) return
  if (mode === 'general' && !normalized) { error.value = '请填写反馈说明。'; errorScope.value = 'feedback'; return }
  await action(async current => {
    await sendKnowledgeFeedback(mode === 'source' ? target!.evidence_id : undefined, category.value, normalized)
    if (current === generation) { closeFeedback(); notice.value = '反馈已提交。可在“我的反馈”查看处理状态。'; if (props.view === 'feedback' || (!props.view && kind.value === 'Feedback')) await refreshFeedback(); else if(props.view)emit('records-view','feedback');else kind.value = 'Feedback' }
  }, 'feedback')
}
async function reopen(id: string) {
  await action(async current => {
    const data = await openKnowledgeSaved(id)
    if (current === generation) {
      if (data.document) emit('document',data.document)
      else if (data.restored) {
        if (props.view) emit('restored', data)
        else { const subject = props.subject; emit('restored', data); await nextTick(); if (current === generation && subject === props.subject) restoreSnapshot(data.restored) }
      } else if (data.context) emit('replay', data.query, data.space_ids, data.context)
      else emit('replay', data.query, data.space_ids)
    }
  }, 'records')
}
async function remove(id: string) {
  await action(async current => { await removeKnowledgeSaved(id); if (current === generation) { notice.value = '已删除这条个人记录。'; await refresh() } })
}
function restoreSnapshot(snapshot: import('@/contracts/p1').KnowledgeRestored) {
  turns.value = snapshot.turns
  conversation.value = turns.value[turns.value.length - 1]?.turn_id || ''
  queryState.value = turns.value.length ? ((turns.value[turns.value.length - 1]!.answerable || turns.value[turns.value.length - 1]!.citations.length>0) ? 'success' : 'no_evidence') : 'idle'
  emit('conversation', Boolean(conversation.value))
}
// The document reader replaces this view for a moment. Snapshot the read-only
// conversation state and restore it on return without re-sending a question or
// reloading history.
function snapshotState(): KnowledgeToolsReturnState {
  return {
    question: question.value,
    conversation: conversation.value,
    turns: turns.value.map(turn => ({ ...turn, citations: [...turn.citations] })),
    queryState: queryState.value,
  }
}
function restoreState(state: KnowledgeToolsReturnState) {
  generation++
  turns.value = state.turns.map(turn => ({ ...turn, citations: [...turn.citations] }))
  conversation.value = state.conversation
  question.value = state.question
  queryState.value = state.queryState
  busy.value = false
  askPending.value = false
  error.value = ''
  closeFeedback(false)
  emit('conversation', Boolean(conversation.value))
}
function cancelPending(cancelRecords = true) {
  generation++
  if (cancelRecords) { recordsGeneration++; refreshing.value = false }
  if (askPending.value) queryState.value = 'cancelled'
  else if (queryState.value === 'error') queryState.value = 'idle'
  busy.value = false; askPending.value = false
  if (errorScope.value === 'query') error.value = ''
}
function newConversation() { cancelPending(); conversation.value = ''; turns.value = []; question.value = ''; error.value = ''; queryState.value = 'idle'; emit('conversation', false) }
function startNewConversation() {
  if (askInFlight.value) return
  newConversation()
  emit('new-conversation')
}
function invalidateSources() {
  newConversation()
  closeFeedback(false)
  void refresh()
}
async function ask(value = question.value) {
  const normalized = value.trim()
  if (composing.value || !normalized || busy.value || askInFlight.value) return
  if (!props.askEnabled || props.retrievalBlocked) { error.value = props.retrievalBlocked ? '检索服务暂不可用，目录与个人记录仍可查看。' : '回答服务暂时不可用，可切换搜资料查找依据。'; errorScope.value = 'query'; queryState.value = 'error'; return }
  if ([...normalized].length > 280) { error.value = '请将问题控制在 280 字以内。'; errorScope.value = 'query'; queryState.value = 'error'; return }
  const previousTurn = conversation.value
  await action(async current => {
    askPending.value = true; queryState.value = 'answering'
    askInFlight.value = true
    const data = await askKnowledgeReference(normalized, props.selectedSpace, conversation.value || undefined, props.searchMode || 'STANDARD', Boolean(props.knowledgeOnly))
      .finally(() => { askInFlight.value = false })
    if (current === generation) {
      queryState.value = answerState(data)
      turns.value.push({ ...data, question: normalized }); conversation.value = data.turn_id; question.value = ''; emit('conversation', true)
      await refresh()
    }
  }, 'query')
  return conversation.value !== previousTurn
}
function questionKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || !(event.ctrlKey || event.metaKey) || composing.value || event.isComposing || event.keyCode === 229) return
  event.preventDefault(); void ask()
}
function tabKeydown(event: KeyboardEvent, current: RecordKind) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const index = tabs.value.findIndex(tab => tab.kind === current)
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.value.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.value.length) % tabs.value.length
  kind.value = tabs.value[next]!.kind
  void nextTick(() => document.getElementById(`knowledge-tab-${kind.value}`)?.focus())
}

const recentRecords = computed(() => history.value.slice(0, 3))
defineExpose({ recentRecords, reopen, restoreSnapshot, hasQueryError, queryState, refresh, bookmark, feedback, generalFeedback, ask, newConversation, cancelPending, invalidateSources, isBookmarked, toggleDocumentBookmark, snapshotState, restoreState })
async function resumeConversation() {
  // A reader return may already have restored its in-memory snapshot.
  await nextTick()
  if (turns.value.length || props.view !== 'query' || props.mode !== 'ask') return
  const subject = props.subject
  const pointer = loadConversationPointer(subject)
  if (!pointer) return
  const position = loadWorkspace(subject)
  await action(async current => {
    // The server checks current account, the full chain and every source again.
    // No answer text or evidence capability is trusted from sessionStorage.
    const data = await openKnowledgeSaved(pointer)
    if (current !== generation || subject !== props.subject || turns.value.length) return
    if (!data.restored || data.restored.mode !== 'ask') return
    restoreSnapshot(data.restored)
    await nextTick()
    if (current === generation && subject === props.subject && position?.view === 'query') {
      const top = Number.isFinite(position.scrollTop) ? Math.max(0, position.scrollTop) : 0
      window.scrollTo(0, top)
    }
  }, 'records')
}
onMounted(() => { void refresh(); void resumeConversation() })
function onDrawerOpenChange(open: boolean) {
  handleDrawerLayerChange('kb-feedback-drawer', '反馈与建议', open)
}
</script>

<style scoped>
.knowledge-tools { display: grid; gap: 18px; min-width: 0; }
.ask-area,.reference-library { padding: 22px; border-radius: 23px; min-width: 0; }
.knowledge-tools h2 { font-size: 20px; line-height: 28px; color: #203b66; margin: 0; }
.knowledge-tools p { color: var(--hbos-text-secondary); line-height: var(--hbos-line-body); }
.answer-heading p { margin: 6px 0 16px; font-size: var(--hbos-font-body); }
.knowledge-tools form,.feedback-form form { display: grid; gap: 10px; }
.knowledge-tools label,.feedback-form label { font-weight: var(--hbos-weight-strong); }
.knowledge-tools textarea,.knowledge-tools select:not(.kb-scope-select),.feedback-form textarea,.feedback-form select { width: 100%; min-width: 0; padding: 12px; border: 1px solid var(--hbos-border-strong); border-radius: 12px; background: var(--hbos-bg-surface); font: inherit; color: var(--hbos-text-primary); }
.knowledge-tools textarea,.feedback-form textarea { min-height: 96px; resize: vertical; }
.knowledge-tools button:focus-visible,.knowledge-tools textarea:focus-visible,.knowledge-tools select:focus-visible { outline: 2px solid var(--hbos-brand-aqua); outline-offset: 3px; }
.tool-actions { display: flex; align-items: flex-start; gap: 8px; flex-wrap: wrap; flex-shrink: 0; }
.tool-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.tool-tabs { display: flex; gap: 4px; margin: 16px 0; overflow-x: auto; padding: 3px; border-radius: 12px; background: rgba(65,91,138,.04); }
.tool-tabs button { flex-shrink: 0; border: 0; background: transparent; color: var(--hbos-text-secondary); padding: 9px 12px; border-radius: 10px; font: inherit; cursor: pointer; }
.tool-tabs button[aria-selected=true] { background: rgba(255,255,255,.9); color: #127a67; box-shadow: 0 2px 8px rgba(35,85,75,.08); }
.saved-row,.feedback-row { display: flex; gap: 16px; justify-content: space-between; align-items: flex-start; border-top: 1px solid var(--hbos-border-strong); padding: 16px 0; overflow-wrap: anywhere; }
.saved-row>div:first-child,.feedback-row>div:first-child { min-width: 0; }
.saved-row strong,.feedback-row strong { font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); }
.saved-row p,.feedback-row p { margin: 6px 0; font-size: var(--hbos-font-body); }
.saved-row small,.feedback-row small { font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small); color: var(--hbos-text-muted); }
.muted { color: var(--hbos-text-muted)!important; font-size: var(--hbos-font-body); }
.answer-list { display: grid; gap: 14px; max-height: 840px; overflow-y: auto; }
.answer-card { padding: 18px; border: 1px solid var(--hbos-border-strong); border-radius: 16px; background: rgba(255,255,255,.62); }
.answer-text { font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important)!important; overflow-wrap: anywhere; }
.answer-text :deep(p), .kb-answer-copy :deep(p) { margin: 0 0 8px; }
.answer-text :deep(h3), .kb-answer-copy :deep(h3),
.answer-text :deep(h4), .kb-answer-copy :deep(h4),
.answer-text :deep(h5), .kb-answer-copy :deep(h5) { font-size: inherit; font-weight: 600; margin: 12px 0 6px; }
.answer-text :deep(ul), .kb-answer-copy :deep(ul),
.answer-text :deep(ol), .kb-answer-copy :deep(ol) { margin: 0 0 8px; padding-left: 20px; }
.answer-text :deep(li), .kb-answer-copy :deep(li) { margin: 2px 0; }
.answer-text :deep(code), .kb-answer-copy :deep(code) { background: rgba(0,0,0,.05); padding: 0 3px; border-radius: 3px; }
.answer-text :deep(pre), .kb-answer-copy :deep(pre) { white-space: pre-wrap; background: rgba(0,0,0,.04); padding: 8px; border-radius: 4px; }
.answer-text :deep(table), .kb-answer-copy :deep(table) { border-collapse: collapse; margin: 0 0 8px; width: 100%; }
.answer-text :deep(th), .answer-text :deep(td),
.kb-answer-copy :deep(th), .kb-answer-copy :deep(td) { border: 1px solid var(--hbos-line, #d8dee7); padding: 4px 6px; text-align: left; vertical-align: top; }
.answer-question { margin: 0 0 12px; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); color: var(--hbos-text-primary); overflow-wrap: anywhere; }
.answer-note { font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small)!important; color: var(--hbos-text-muted)!important; }
.citation-link { display: block; text-align: left; padding: 8px 0; border: 0; background: transparent; color: #247a70; font-size: var(--hbos-font-body); line-height: var(--hbos-line-body); cursor: pointer; overflow-wrap: anywhere; max-width: 100%; }
.feedback-title { overflow-wrap: anywhere; }
.feedback-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.feedback-heading p { margin-top: 0; flex: 1 1 220px; }
.tool-notice { color: #127a57!important; }
@media(max-width:600px) { .ask-area,.reference-library { padding: 16px; } .saved-row { flex-direction: column; gap: 10px; } .tool-heading { align-items: flex-start; } .tool-tabs button { padding: 9px 10px; } }
.kb-citation-group { margin: 10px 0; }
.kb-citation-group h4 { margin: 0 0 4px; }
.kb-citation-group h4 small { color: var(--hbos-text-muted, #62717d); margin-left: 6px; }
@media (max-width: 480px) {
  .kb-list-toolbar.kb-favorite-toolbar { display: grid; grid-template-columns: minmax(0, 1fr); }
  .kb-favorite-toolbar :deep(.ant-input-search), .kb-favorite-toolbar :deep(.v10-choice) { width: 100%; max-width: none; }
  .kb-secondary-tabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
