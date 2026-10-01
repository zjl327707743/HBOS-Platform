<template>
  <section class="product-page lims-result-entry">
    <div v-if="loading" class="lims-result-entry-loading" aria-live="polite">
      <div class="lims-skeleton-panel"></div><div class="lims-skeleton-panel"></div>
    </div>

    <template v-else-if="detail">
      <div class="lims-result-entry-heading">
        <div>
          <button type="button" class="lims-back-link" @click="router.push('/hbos/lims/results')">← 返回结果清单</button>
          <span class="page-kicker">LIMS · 结果记录</span>
          <h1>{{ detail.result.item_name }}</h1>
          <p>{{ detail.result.result_name }} · {{ detail.result.sample }} · {{ detail.result.batch_no || '未填批号' }}</p>
        </div>
        <div class="lims-result-entry-actions">
          <span v-if="!canWrite" class="lims-readonly-badge">演示模式只读</span>
          <a-button v-if="canSubmit" type="primary" :loading="submitting" @click="onSubmitClick">提交结果</a-button>
          <a-button v-if="canReview" :loading="submitting" @click="review">复核结果</a-button>
          <a-button v-if="canApprove" type="primary" :loading="submitting" @click="approve">批准结果</a-button>
        </div>
      </div>

      <a-alert v-if="errorMessage" class="lims-result-entry-alert" type="error" show-icon closable :message="errorMessage" @close="errorMessage = ''" />

      <div class="lims-result-entry-grid">
        <aside class="lims-result-context-column">
          <section class="lims-result-context-card glass-surface">
            <div class="section-head"><div><h2>样品上下文</h2><p>进入结果前先确认样品和批次</p></div></div>
            <dl>
              <div><dt>样品编号</dt><dd>{{ detail.result.sample }}</dd></div>
              <div><dt>物料名称</dt><dd>{{ detail.result.material_name || '—' }}</dd></div>
              <div><dt>批号</dt><dd>{{ detail.result.batch_no || '—' }}</dd></div>
              <div><dt>检验项目</dt><dd>{{ detail.result.item_name }}</dd></div>
              <div><dt>检验人</dt><dd>{{ detail.result.analyst || '待分配' }}</dd></div>
              <div><dt>记录状态</dt><dd><a-tag :color="statusColor(detail.result.result_status)">{{ detail.result.result_status }}</a-tag></dd></div>
              <div><dt>判定</dt><dd><a-tag :color="verdictColor(detail.result.verdict)">{{ detail.result.verdict || '待判定' }}</a-tag></dd></div>
            </dl>
          </section>

          <section class="lims-result-context-card glass-surface lims-limits-card">
            <div class="section-head"><div><h2>冻结限度</h2><p>录入参考，最终判定由 LIMS 服务完成</p></div></div>
            <div class="lims-limit-highlight">{{ detail.result.limits_text || '记录型项目' }}</div>
            <div class="lims-limit-meta">限度模式：{{ detail.result.limits_type || '—' }} · 有效位数：{{ detail.result.significant_digits ?? '—' }}</div>
          </section>
        </aside>

        <div class="lims-result-work-column">
          <section class="lims-result-form-card glass-surface">
            <div class="section-head"><div><h2>结果数据</h2><p>草稿可录入；提交后按状态锁定字段</p></div><span class="lims-readonly-badge">{{ canEdit ? '可录入草稿' : '状态锁定' }}</span></div>
            <a-form layout="vertical" :disabled="!canEdit">
              <div class="lims-result-form-grid">
                <a-form-item label="结果原始值"><a-input v-model:value="form.raw_value" placeholder="请输入仪器原始读数" /></a-form-item>
                <a-form-item label="结果值"><a-input v-model:value="form.result_value" placeholder="请输入结果值" /></a-form-item>
                <a-form-item label="仪器编号"><a-input v-model:value="form.instrument_used" placeholder="记录实际使用的仪器" /></a-form-item>
                <a-form-item class="full" label="结果描述（记录型项目）"><a-textarea v-model:value="form.result_text" :rows="3" placeholder="如：符合规定" /></a-form-item>
              </div>
            </a-form>
            <div v-if="detail.result.verdict" class="lims-result-verdict" :class="detail.result.verdict === '合格' ? 'success' : 'critical'">
              <strong>{{ detail.result.verdict }}</strong><span>{{ detail.result.display || '已由 LIMS 完成判定' }}</span>
            </div>
          </section>

          <section class="lims-signature-card glass-surface">
            <div class="section-head"><div><h2>签署链</h2><p>操作归属记录由领域服务写入</p></div></div>
            <div class="lims-signature-chain">
              <div :class="{ complete: detail.signature_chain.analyst }"><span>检验人</span><strong>{{ detail.signature_chain.analyst || '待提交' }}</strong><small>{{ detail.signature_chain.submitted_at || '—' }}</small></div>
              <i>→</i>
              <div :class="{ complete: detail.signature_chain.reviewer }"><span>复核人</span><strong>{{ detail.signature_chain.reviewer || '待复核' }}</strong><small>{{ detail.signature_chain.reviewed_at || '—' }}</small></div>
              <i>→</i>
              <div :class="{ complete: detail.signature_chain.approver }"><span>批准人</span><strong>{{ detail.signature_chain.approver || '待批准' }}</strong><small>{{ detail.signature_chain.approved_at || '—' }}</small></div>
            </div>
          </section>

          <section class="lims-revision-card glass-surface">
            <div class="section-head"><div><h2>修订记录</h2><p>原记录不可覆盖，修订能力待专门契约通过后开放</p></div></div>
            <div v-if="detail.revisions.length" class="lims-revision-list"><div v-for="revision in detail.revisions" :key="String(revision.name)"><strong>{{ revision.field_changed }}</strong><span>{{ revision.old_value }} → {{ revision.new_value }}</span><small>{{ revision.change_reason || '未填写原因' }}</small></div></div>
            <div v-else class="lims-inline-empty">暂无修订记录</div>
          </section>
        </div>
      </div>
    </template>

    <section v-else class="lims-result-entry-empty glass-surface">
      <InboxOutlined /><h2>未找到检验结果</h2><p>记录不存在、当前用户无权限，或服务暂时不可用。</p><a-button @click="router.push('/hbos/lims/results')">返回结果清单</a-button>
    </section>

    <a-modal v-model:open="showProxySubmit" title="代提交检验结果" :footer="null">
      <p class="lims-proxy-note">当前用户不是该记录检验人。代提交必须填写理由，理由将由 LIMS 服务写入审计记录。</p>
      <a-form layout="vertical"><a-form-item label="代提交理由"><a-textarea v-model:value="proxyReason" :rows="4" placeholder="请说明代提交原因" /></a-form-item><div class="lims-modal-actions"><a-button @click="showProxySubmit = false">取消</a-button><a-button type="primary" :loading="submitting" @click="submit">确认提交</a-button></div></a-form>
    </a-modal>
  </section>
</template>

<script setup lang="ts">
import { statusColor, verdictColor } from '@/views/limsStatus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import { usePortalStore } from '@/stores/portal'
import { getLimsResult, submitLimsResult, reviewLimsResult, approveLimsResult, type LimsResultDetail } from '@/services/limsResults'
import { portalDataSource } from '@/services/portalProvider'

const route = useRoute()
const router = useRouter()
const portal = usePortalStore()
const detail = ref<LimsResultDetail | null>(null)
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const showProxySubmit = ref(false)
const proxyReason = ref('')
const form = reactive({ raw_value: '', result_value: '', result_text: '', instrument_used: '' })

const limsAccessCapabilities = computed(() => portal.apps.find((app) => app.id === 'lims')?.accessCapabilities || [])
const canSubmit = computed(() => portalDataSource === 'frappe' && limsAccessCapabilities.value.includes('lims.results.submit'))
const canReview = computed(() => portalDataSource === 'frappe' && limsAccessCapabilities.value.includes('lims.results.review') && detail.value?.result.result_status === '已提交')
const canApprove = computed(() => portalDataSource === 'frappe' && limsAccessCapabilities.value.includes('lims.results.approve') && detail.value?.result.result_status === '已复核')
const canWrite = computed(() => canSubmit.value || canReview.value || canApprove.value)
const canEdit = computed(() => canSubmit.value && detail.value?.result.result_status === '草稿')

function syncForm() {
  const result = detail.value?.result
  if (!result) return
  form.raw_value = result.raw_value || ''
  form.result_value = result.result_value == null ? '' : String(result.result_value)
  form.result_text = result.result_text || ''
  form.instrument_used = ''
}

async function loadResult() {
  loading.value = true
  errorMessage.value = ''
  try {
    if (!portal.user) await portal.bootstrap()
    detail.value = await getLimsResult(String(route.params.resultId || ''))
    syncForm()
  } catch {
    detail.value = null
    errorMessage.value = '结果详情暂时无法加载，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function onSubmitClick() {
  const currentUser = portal.user?.id || ''
  if (detail.value?.result.analyst && currentUser && detail.value.result.analyst !== currentUser) {
    proxyReason.value = ''
    showProxySubmit.value = true
    return
  }
  void submit()
}

async function submit() {
  if (!detail.value) return
  if (showProxySubmit.value && !proxyReason.value.trim()) {
    message.warning('代提交必须填写理由')
    return
  }
  submitting.value = true
  try {
    await submitLimsResult({ result_name: detail.value.result.result_name, ...form, proxy_reason: proxyReason.value.trim() || undefined })
    message.success('结果已提交，判定由 LIMS 服务完成')
    showProxySubmit.value = false
    await loadResult()
  } catch {
    errorMessage.value = '结果提交未完成，已保留当前输入，请检查后重试。'
  } finally {
    submitting.value = false
  }
}

async function review() {
  if (!detail.value) return
  submitting.value = true
  try { await reviewLimsResult(detail.value.result.result_name); message.success('结果已提交复核'); await loadResult() } catch { errorMessage.value = '复核未完成，请稍后重试。' } finally { submitting.value = false }
}

async function approve() {
  if (!detail.value) return
  submitting.value = true
  try { await approveLimsResult(detail.value.result.result_name); message.success('结果已批准'); await loadResult() } catch { errorMessage.value = '批准未完成，请确认职责分离和结果状态。' } finally { submitting.value = false }
}

onMounted(() => { void loadResult() })
</script>
