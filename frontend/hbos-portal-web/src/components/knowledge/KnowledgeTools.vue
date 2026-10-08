<template>
  <section class="knowledge-tools hbos-glass-g2">
    <div v-if="askEnabled" class="ask-area">
      <h2>带来源问答</h2><p>根据已收录资料解释；请核对现行规程与适用版本。</p>
      <form @submit.prevent="ask">
        <label for="knowledge-question">{{ conversation ? '继续追问' : '你的问题' }}</label>
        <textarea id="knowledge-question" v-model="question" maxlength="280" :disabled="busy" placeholder="例如：混粉操作记录需要确认哪些项目？" />
        <div class="tool-actions"><a-button type="primary" html-type="submit" :disabled="!question.trim()" :loading="busy">{{ conversation ? '追问' : '提交问题' }}</a-button><a-button v-if="conversation" :disabled="busy" @click="newConversation">新问题</a-button></div>
      </form>
      <article v-for="turn in turns" :key="turn.turn_id" class="answer-card">
        <a-tag :color="turn.answerable ? 'blue' : 'orange'">{{ turn.answerable ? '内部参考回答' : '依据不足' }}</a-tag>
        <p class="answer-text">{{ turn.answer }}</p>
        <button v-for="source in turn.citations" :key="source.citation_label" type="button" class="citation-link" @click="emit('evidence',source.evidence_id)">[{{ source.citation_label }}] {{ source.title || '未标注标题' }} · 查看依据</button>
      </article>
    </div>
    <div class="tool-heading"><h2>我的查阅</h2><a-button size="small" :disabled="busy" @click="refresh">刷新</a-button></div>
    <div class="tool-tabs" role="tablist" aria-label="查阅记录">
      <button v-for="tab in tabs" :key="tab.kind" type="button" role="tab" :aria-selected="kind === tab.kind" @click="kind=tab.kind">{{ tab.label }}</button>
    </div>
    <div role="tabpanel" :aria-label="kind === 'History' ? '最近查阅' : '我的收藏'">
      <p v-if="!shown.length" class="muted">{{ kind === 'History' ? '检索和问答后会在这里记录问题。' : '在检索结果中收藏资料，稍后继续查阅。' }}</p>
      <article v-for="item in shown" :key="item.id" class="saved-row">
        <div><strong>{{ item.query }}</strong><p>{{ item.available ? item.titles.filter(Boolean).join('；') || '检索记录' : '依据已下架或版本变化，请重新检索' }}</p><small>{{ item.created_at.slice(0,16) }}</small></div>
        <div class="tool-actions"><a-button size="small" :disabled="busy || !item.available" @click="reopen(item.id)">重新查阅</a-button><a-button size="small" :disabled="busy" @click="remove(item.id)">删除</a-button></div>
      </article>
    </div>
    <p v-if="notice" role="status" class="tool-notice">{{ notice }}</p>
    <a-alert v-if="error" type="error" show-icon :message="error" />
    <div v-if="feedbackTarget" class="feedback-form">
      <h3>反馈资料问题</h3><p>{{ feedbackTarget.title }}</p>
      <form @submit.prevent="sendFeedback">
        <label for="feedback-category">问题类型</label><select id="feedback-category" v-model="category"><option v-for="c in categories" :key="c">{{ c }}</option></select>
        <label for="feedback-note">补充说明</label><textarea id="feedback-note" v-model="note" maxlength="500" placeholder="请描述需要维护人核对的问题" />
        <div class="tool-actions"><a-button type="primary" html-type="submit" :loading="busy">提交反馈</a-button><a-button :disabled="busy" @click="feedbackTarget=null">取消</a-button></div>
      </form>
    </div>
  </section>
</template>
<script setup lang="ts">
import {computed,onMounted,onBeforeUnmount,ref,watch} from 'vue'
import type {KnowledgeActivity,KnowledgeAnswer,KnowledgeEvidence} from '@/contracts/p1'
import {askKnowledgeReference,getKnowledgeActivity,openKnowledgeSaved,removeKnowledgeSaved,saveKnowledgeBookmark,sendKnowledgeFeedback,DomainApiError} from '@/services/p1Api'
const props=defineProps<{subject:string;query:string;selectedSpace:string;askEnabled:boolean}>()
const emit=defineEmits<{replay:[query:string,spaces:string[]];evidence:[id:string]}>()
const tabs=[{kind:'History' as const,label:'最近查阅'},{kind:'Bookmark' as const,label:'我的收藏'}]
const kind=ref<'History'|'Bookmark'>('History');const history=ref<KnowledgeActivity[]>([]);const bookmarks=ref<KnowledgeActivity[]>([])
const shown=computed(()=>kind.value==='History'?history.value:bookmarks.value)
const question=ref('');const conversation=ref('');const turns=ref<KnowledgeAnswer[]>([]);const busy=ref(false);const notice=ref('');const error=ref('')
const feedbackTarget=ref<KnowledgeEvidence|null>(null);const categories=['内容疑问','版本疑问','检索不相关','其他'];const category=ref('内容疑问');const note=ref('');let generation=0
watch(()=>props.subject,()=>{generation++;history.value=[];bookmarks.value=[];turns.value=[];conversation.value='';question.value='';notice.value='';error.value='';feedbackTarget.value=null;busy.value=false;void refresh()})
watch(()=>props.selectedSpace,()=>{generation++;turns.value=[];conversation.value='';busy.value=false})
onBeforeUnmount(()=>{generation++})
function failure(e:unknown){error.value=e instanceof DomainApiError?e.message:'知识服务暂时不可用。'}
async function refresh(){const g=generation;try{const [h,b]=await Promise.all([getKnowledgeActivity('History'),getKnowledgeActivity('Bookmark')]);if(g===generation){history.value=h;bookmarks.value=b}}catch(e){if(g===generation)failure(e)}}
async function action(run:()=>Promise<void>){if(busy.value)return;const g=generation;busy.value=true;error.value='';notice.value='';try{await run()}catch(e){if(g===generation)failure(e)}finally{if(g===generation)busy.value=false}}
async function bookmark(item:KnowledgeEvidence){const g=generation;await action(async()=>{await saveKnowledgeBookmark(item.evidence_id,props.query);if(g===generation){notice.value='已收藏。重新查阅时会核验资料状态。';await refresh()}})}
function feedback(item:KnowledgeEvidence){feedbackTarget.value=item;notice.value='';error.value='';note.value='';setTimeout(()=>document.getElementById('feedback-note')?.focus(),0)}
async function sendFeedback(){const g=generation;await action(async()=>{await sendKnowledgeFeedback(feedbackTarget.value?.evidence_id,category.value,note.value);if(g===generation){feedbackTarget.value=null;notice.value='反馈已提交，等待维护人处理。'}})}
async function reopen(id:string){const g=generation;await action(async()=>{const data=await openKnowledgeSaved(id);if(g===generation)emit('replay',data.query,data.space_ids)})}
async function remove(id:string){const g=generation;await action(async()=>{await removeKnowledgeSaved(id);if(g===generation)await refresh()})}
function newConversation(){conversation.value='';turns.value=[];question.value='';error.value=''}
async function ask(){const g=generation;await action(async()=>{const data=await askKnowledgeReference(question.value,props.selectedSpace,conversation.value||undefined);if(g===generation){turns.value.push(data);conversation.value=data.turn_id;question.value='';await refresh()}})}
defineExpose({refresh,bookmark,feedback});onMounted(refresh)
</script>
<style scoped>
.knowledge-tools{padding:22px;border-radius:23px;min-width:0}.knowledge-tools h2{font-size:var(--hbos-font-section-title);color:#203b66;margin:0 0 8px}.knowledge-tools p{color:var(--hbos-text-secondary);line-height:1.7}.ask-area{margin-bottom:24px}.knowledge-tools form{display:grid;gap:10px}.knowledge-tools label{font-weight:600}.knowledge-tools textarea,.knowledge-tools select{width:100%;padding:12px;border:1px solid var(--hbos-border-strong);border-radius:12px;background:var(--hbos-bg-surface);font:inherit;color:var(--hbos-text-primary)}.knowledge-tools textarea{min-height:84px;resize:vertical}.knowledge-tools button:focus-visible,.knowledge-tools textarea:focus-visible,.knowledge-tools select:focus-visible{outline:2px solid var(--hbos-brand-violet);outline-offset:3px}.tool-actions{display:flex;gap:8px;flex-wrap:wrap}.tool-heading{display:flex;justify-content:space-between;align-items:center}.tool-tabs{display:flex;gap:8px;margin:12px 0}.tool-tabs button{border:0;background:transparent;color:var(--hbos-text-secondary);padding:8px 12px;border-radius:10px;cursor:pointer}.tool-tabs button[aria-selected=true]{background:rgba(103,95,255,.12);color:#514ad8}.saved-row{display:flex;gap:16px;justify-content:space-between;border-top:1px solid var(--hbos-border-strong);padding:14px 0;overflow-wrap:anywhere}.saved-row>div:first-child{min-width:0}.saved-row p{margin:6px 0}.saved-row small,.muted{color:var(--hbos-text-muted)}.answer-card{padding:16px;margin-top:16px;border:1px solid var(--hbos-border-strong);border-radius:14px}.answer-text{white-space:pre-wrap}.citation-link{display:block;text-align:left;padding:8px 0;border:0;background:transparent;color:#4e60c6;cursor:pointer;overflow-wrap:anywhere;max-width:100%}.feedback-form{margin-top:20px;border-top:1px solid var(--hbos-border-strong);padding-top:16px}.tool-notice{color:#127a57!important}@media(max-width:600px){.knowledge-tools{padding:16px}.saved-row{flex-direction:column}}
</style>
