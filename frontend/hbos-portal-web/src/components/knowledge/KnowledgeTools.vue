<template>
  <div class="knowledge-tools">
    <section v-if="askEnabled && (!mode || mode === 'ask')" class="ask-area hbos-glass-g2">
      <form v-if="!composerExternal" @submit.prevent="ask()">
        <label for="knowledge-question">{{ conversation ? '继续追问' : '你的问题' }}</label>
        <textarea id="knowledge-question" v-model="question" maxlength="280" :disabled="busy || retrievalBlocked" placeholder="描述希望从资料中确认的问题…" @compositionstart="composing = true" @compositionend="composing = false" @keydown="questionKeydown" />
        <div class="tool-actions"><a-button type="primary" html-type="submit" :disabled="busy || !question.trim() || retrievalBlocked" :loading="busy">{{ conversation ? '追问' : '提交问题' }}</a-button><a-button v-if="conversation" :disabled="busy" @click="newConversation">新问题</a-button></div>
      </form>
      <div v-if="turns.length || busy" class="answer-heading"><h2>带来源回答</h2><p>根据本次资料范围重新检索；内部参考，请核对适用版本。</p></div>
      <a-skeleton v-if="busy && askPending" active :paragraph="{ rows: 4 }" />
      <div class="answer-list" aria-live="polite">
        <article v-for="turn in turns" :key="turn.turn_id" class="answer-card">
          <h3 class="answer-question">{{ turn.question }}</h3>
          <a-tag :color="turn.answerable ? 'blue' : 'orange'">{{ turn.answerable ? '内部参考回答' : '依据不足' }}</a-tag>
          <p class="answer-text">{{ turn.answer }}</p>
          <button v-for="source in turn.citations" :key="source.citation_label" type="button" class="citation-link" @click="emit('evidence', source.evidence_id)">[{{ source.citation_label }}] {{ source.title || '未标注标题' }} · 查看依据</button>
          <p class="answer-note">本次检索时点的资料依据；再次查阅会核验当前状态。</p>
        </article>
      </div>
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
      <a-alert v-if="error" type="error" show-icon :message="error" />
    </section>

    <a-modal :open="Boolean(feedbackMode)" :title="feedbackMode === 'general' ? '提交一般反馈' : '反馈资料问题'" :footer="null" :destroy-on-close="true" @cancel="closeFeedback()">
      <div v-if="feedbackMode" class="feedback-form">
        <p v-if="feedbackMode === 'general'" class="feedback-title">这条反馈没有关联资料来源。请描述使用中遇到的问题。</p>
        <p v-else class="feedback-title">{{ feedbackTarget?.title || '当前检索依据' }}</p>
        <a-alert v-if="error" type="error" show-icon :message="error" />
        <form @submit.prevent="sendFeedback">
          <label for="feedback-category">问题类型</label><select id="feedback-category" v-model="category" :disabled="busy"><option v-for="c in categories" :key="c">{{ c }}</option></select>
          <label for="feedback-note">{{ feedbackMode === 'general' ? '反馈说明（必填）' : '补充说明' }}</label><textarea id="feedback-note" v-model="note" maxlength="500" :disabled="busy" :required="feedbackMode === 'general'" placeholder="请描述需要维护人核对的问题" />
          <p class="muted">不要填写个人身份证、薪资或其他敏感个人信息。</p>
          <div class="tool-actions"><a-button type="primary" html-type="submit" :disabled="busy || (feedbackMode === 'general' && !note.trim())" :loading="busy">提交反馈</a-button><a-button :disabled="busy" @click="closeFeedback()">取消</a-button></div>
        </form>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, useSlots, watch } from 'vue'
import type { KnowledgeActivity, KnowledgeAnswer, KnowledgeEvidence, KnowledgeFeedback, KnowledgeSearchContext, KnowledgeSavedQuery } from '@/contracts/p1'
import { askKnowledgeReference, getKnowledgeActivity, getKnowledgeFeedback, openKnowledgeSaved, removeKnowledgeSaved, saveKnowledgeBookmark, sendKnowledgeFeedback, DomainApiError } from '@/services/p1Api'

type RecordKind = 'Catalog' | 'History' | 'Bookmark' | 'Feedback'
const props = defineProps<{ subject: string; query: string; selectedSpace: string; askEnabled: boolean; retrievalBlocked?: boolean; composerExternal?: boolean; mode?: 'search' | 'ask'; searchMode?: 'STANDARD' | 'PRECISE' }>()
const emit = defineEmits<{ replay: [query: string, spaces: string[], context?: KnowledgeSearchContext]; evidence: [id: string]; busy: [value: boolean]; conversation: [value: boolean]; 'upstream-error': []; 'access-error': [error: DomainApiError]; 'evidence-invalidated': []; restored: [data: KnowledgeSavedQuery] }>()
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
const feedbackStatus = { Pending: '待处理', 'In Review': '处理中', Resolved: '已解决' }
const shown = computed(() => kind.value === 'History' ? history.value : bookmarks.value)
const savedPage = ref(1)
const savedPageSize = 6
const pagedSaved = computed(() => shown.value.slice((savedPage.value - 1) * savedPageSize, savedPage.value * savedPageSize))
const pagedFeedback = computed(() => feedbackItems.value.slice((savedPage.value - 1) * savedPageSize, savedPage.value * savedPageSize))
const question = ref('')
const composing = ref(false)
const conversation = ref('')
const turns = ref<(KnowledgeAnswer & { question: string })[]>([])
const busy = ref(false)
const askPending = ref(false)
const refreshing = ref(false)
const feedbackLoading = ref(false)
const notice = ref('')
const error = ref('')
const feedbackError = ref('')
const feedbackTarget = ref<KnowledgeEvidence | null>(null)
const feedbackMode = ref<'source' | 'general' | null>(null)
const categories = ['内容疑问', '版本疑问', '检索不相关', '其他']
const category = ref('内容疑问')
const note = ref('')
let generation = 0
let recordsGeneration = 0
let feedbackGeneration = 0
let feedbackTrigger: HTMLElement | null = null
const accessFailureCodes = ['AUTHENTICATION_REQUIRED', 'CLIENT_AUTH_FAILED', 'FORBIDDEN', 'SCOPE_REJECTED', 'EMPTY_SCOPE']

watch(busy, value => emit('busy', value), { flush: 'sync' })
watch(kind, () => { savedPage.value = 1; if (kind.value === 'Feedback') void refreshFeedback() })
watch([history, bookmarks, feedbackItems], () => { const total = kind.value === 'Feedback' ? feedbackItems.value.length : shown.value.length; savedPage.value = Math.min(savedPage.value, Math.max(1, Math.ceil(total / savedPageSize))) })
watch(() => props.subject, () => {
  generation++; recordsGeneration++; feedbackGeneration++
  history.value = []; bookmarks.value = []; feedbackItems.value = []; turns.value = []
  conversation.value = ''; question.value = ''; notice.value = ''; error.value = ''; feedbackError.value = ''
  closeFeedback(false); busy.value = false; refreshing.value = false; feedbackLoading.value = false
  emit('conversation', false)
  if (props.subject) void refresh()
}, { flush: 'sync' })
watch(() => [props.selectedSpace,props.searchMode], () => {
  generation++; turns.value = []; conversation.value = ''; busy.value = false; askPending.value = false
  error.value = ''; notice.value = ''; closeFeedback(false); emit('conversation', false)
}, { flush: 'sync' })
onBeforeUnmount(() => { generation++; recordsGeneration++; feedbackGeneration++; closeFeedback(false) })

function displayDate(value: string) { return value.slice(0, 16).replace('T', ' ') }
function failure(e: unknown, invalidateSource = true) {
  if (e instanceof DomainApiError && e.code === 'UPSTREAM_UNAVAILABLE') emit('upstream-error')
  if (e instanceof DomainApiError && accessFailureCodes.includes(e.code)) {
    generation++; recordsGeneration++; feedbackGeneration++
    turns.value = []; history.value = []; bookmarks.value = []; feedbackItems.value = []
    busy.value = false; refreshing.value = false; feedbackLoading.value = false; conversation.value = ''; closeFeedback(false)
    emit('conversation', false); emit('access-error', e)
  }
  if (e instanceof DomainApiError && ['EVIDENCE_UNAVAILABLE', 'EVIDENCE_INVALID', 'EVIDENCE_REVOKED'].includes(e.code)) {
    history.value = history.value.map(item => ({ ...item, available: false, titles: [] }))
    bookmarks.value = bookmarks.value.map(item => ({ ...item, available: false, titles: [] }))
    closeFeedback(false); if (invalidateSource) emit('evidence-invalidated')
  }
  error.value = e instanceof DomainApiError ? e.message : '知识服务暂时不可用。'
}
async function refreshFeedback() {
  const current = ++feedbackGeneration
  const subject = props.subject
  feedbackLoading.value = true; feedbackError.value = ''
  try {
    const items = await getKnowledgeFeedback()
    if (current === feedbackGeneration && subject === props.subject) feedbackItems.value = items
  } catch (e) {
    if (current === feedbackGeneration && subject === props.subject) {
      feedbackItems.value = []
      feedbackError.value = e instanceof DomainApiError ? e.message : '反馈记录暂时不可用。'
      if (e instanceof DomainApiError && accessFailureCodes.includes(e.code)) failure(e)
    }
  } finally { if (current === feedbackGeneration) feedbackLoading.value = false }
}
async function refresh() {
  const current = ++recordsGeneration
  const subject = props.subject
  refreshing.value = true
  try {
    const [h, b] = await Promise.all([getKnowledgeActivity('History'), getKnowledgeActivity('Bookmark')])
    if (current === recordsGeneration && subject === props.subject) { history.value = h; bookmarks.value = b }
  } catch (e) { if (current === recordsGeneration && subject === props.subject) failure(e, false) }
  finally { if (current === recordsGeneration) refreshing.value = false }
  if (kind.value === 'Feedback') await refreshFeedback()
}
async function action(run: (current: number) => Promise<void>) {
  if (busy.value || !props.subject) return
  const current = generation
  busy.value = true; error.value = ''; notice.value = ''
  try { await run(current) } catch (e) { if (current === generation) failure(e) }
  finally { if (current === generation) { busy.value = false; askPending.value = false } }
}
async function bookmark(item: KnowledgeEvidence) {
  await action(async current => {
    await saveKnowledgeBookmark(item.evidence_id, props.query)
    if (current === generation) { notice.value = '已收藏。重新查阅时会核验资料状态。'; await refresh() }
  })
}
function feedback(item: KnowledgeEvidence) {
  if (busy.value) return
  feedbackTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  feedbackTarget.value = item; feedbackMode.value = 'source'; notice.value = ''; error.value = ''; note.value = ''; category.value = '内容疑问'
  void nextTick(() => { if (feedbackMode.value) document.getElementById('feedback-note')?.focus() })
}
function generalFeedback() {
  if (busy.value || !props.subject) return
  feedbackTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  feedbackTarget.value = null; feedbackMode.value = 'general'; notice.value = ''; error.value = ''; note.value = ''; category.value = '其他'
  void nextTick(() => { if (feedbackMode.value) document.getElementById('feedback-note')?.focus() })
}
function closeFeedback(restoreFocus = true) {
  feedbackTarget.value = null; feedbackMode.value = null; note.value = ''
  if (restoreFocus && feedbackTrigger?.isConnected) feedbackTrigger.focus({ preventScroll: true })
  feedbackTrigger = null
}
async function sendFeedback() {
  const target = feedbackTarget.value
  const mode = feedbackMode.value
  const normalized = note.value.trim()
  if (!mode || (mode === 'source' && !target)) return
  if (mode === 'general' && !normalized) { error.value = '请填写反馈说明。'; return }
  await action(async current => {
    await sendKnowledgeFeedback(mode === 'source' ? target!.evidence_id : undefined, category.value, normalized)
    if (current === generation) { closeFeedback(); notice.value = '反馈已提交。可在“我的反馈”查看处理状态。'; if (kind.value === 'Feedback') await refreshFeedback(); else kind.value = 'Feedback' }
  })
}
async function reopen(id: string) {
  await action(async current => {
    const data = await openKnowledgeSaved(id)
    if (current === generation) {
      if (data.restored) {
        const subject=props.subject
        emit('restored',data)
        const restoreGeneration=generation
        await nextTick()
        if (subject===props.subject && restoreGeneration===generation) {
          turns.value=data.restored.turns
          conversation.value=turns.value[turns.value.length-1]?.turn_id || ''
          emit('conversation',Boolean(conversation.value))
          notice.value='已按当前来源状态恢复记录，未调用回答模型。'
        }
      } else if (data.context) emit('replay', data.query, data.space_ids, data.context)
      else emit('replay', data.query, data.space_ids)
    }
  })
}
async function remove(id: string) {
  await action(async current => { await removeKnowledgeSaved(id); if (current === generation) { notice.value = '已删除这条个人记录。'; await refresh() } })
}
function cancelPending() { generation++; recordsGeneration++; busy.value = false; askPending.value = false; refreshing.value = false }
function newConversation() { cancelPending(); conversation.value = ''; turns.value = []; question.value = ''; error.value = ''; emit('conversation', false) }
function invalidateSources() {
  newConversation(); closeFeedback(false)
  history.value = history.value.map(item => ({ ...item, available: false, titles: [] }))
  bookmarks.value = bookmarks.value.map(item => ({ ...item, available: false, titles: [] }))
  void refresh()
}
async function ask(value = question.value) {
  const normalized = value.trim()
  if (composing.value || !normalized || busy.value) return
  if (!props.askEnabled || props.retrievalBlocked) { error.value = '检索服务暂不可用，目录与个人记录仍可查看。'; return }
  if ([...normalized].length > 280) { error.value = '请将问题控制在 280 字以内。'; return }
  await action(async current => {
    askPending.value = true
    const data = await askKnowledgeReference(normalized, props.selectedSpace, conversation.value || undefined, props.searchMode || 'STANDARD')
    if (current === generation) {
      turns.value.push({ ...data, question: normalized }); conversation.value = data.turn_id; question.value = ''; emit('conversation', true)
      await refresh()
    }
  })
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

defineExpose({ refresh, bookmark, feedback, ask, newConversation, cancelPending, invalidateSources })
onMounted(refresh)
</script>

<style scoped>
.knowledge-tools { display: grid; gap: 18px; min-width: 0; }
.ask-area,.reference-library { padding: 22px; border-radius: 23px; min-width: 0; }
.knowledge-tools h2 { font-size: 20px; line-height: 28px; color: #203b66; margin: 0; }
.knowledge-tools p { color: var(--hbos-text-secondary); line-height: var(--hbos-line-body); }
.answer-heading p { margin: 6px 0 16px; font-size: var(--hbos-font-body); }
.knowledge-tools form,.feedback-form form { display: grid; gap: 10px; }
.knowledge-tools label,.feedback-form label { font-weight: var(--hbos-weight-strong); }
.knowledge-tools textarea,.knowledge-tools select,.feedback-form textarea,.feedback-form select { width: 100%; min-width: 0; padding: 12px; border: 1px solid var(--hbos-border-strong); border-radius: 12px; background: var(--hbos-bg-surface); font: inherit; color: var(--hbos-text-primary); }
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
.answer-text { font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important)!important; white-space: pre-wrap; overflow-wrap: anywhere; }
.answer-question { margin: 0 0 12px; font-size: var(--hbos-font-card-title); line-height: var(--hbos-line-important); color: var(--hbos-text-primary); overflow-wrap: anywhere; }
.answer-note { font-size: var(--hbos-font-meta); line-height: var(--hbos-line-small)!important; color: var(--hbos-text-muted)!important; }
.citation-link { display: block; text-align: left; padding: 8px 0; border: 0; background: transparent; color: #247a70; font-size: var(--hbos-font-body); line-height: var(--hbos-line-body); cursor: pointer; overflow-wrap: anywhere; max-width: 100%; }
.feedback-title { overflow-wrap: anywhere; }
.feedback-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.feedback-heading p { margin-top: 0; flex: 1 1 220px; }
.tool-notice { color: #127a57!important; }
@media(max-width:600px) { .ask-area,.reference-library { padding: 16px; } .saved-row { flex-direction: column; gap: 10px; } .tool-heading { align-items: flex-start; } .tool-tabs button { padding: 9px 10px; } }
</style>
