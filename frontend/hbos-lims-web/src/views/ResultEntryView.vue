<template>
  <div class="page">
    <div class="load-area">
      <template v-if="result">
        <div class="page-head">
          <div>
            <h1>检验结果录入</h1>
            <p>{{ result.name }} · {{ result.item_name }} · 提交后自动判定并生成电子签名</p>
          </div>
          <div class="page-actions">
            <a-button v-if="result.result_status === '草稿'" type="primary" :loading="submitting" @click="submitResult">
              <template #icon><CheckOutlined /></template>
              提交结果
            </a-button>
            <a-button v-if="result.result_status === '已提交'" type="default" :loading="submitting" @click="doReview">复核</a-button>
            <a-button v-if="result.result_status === '已复核'" type="primary" :loading="submitting" @click="doApprove">批准</a-button>
            <a-button v-if="['已提交','已复核','已批准'].includes(result.result_status)" @click="showRevise = true">修订</a-button>
          </div>
        </div>

        <div class="result-layout">
          <div>
            <div class="context-card">
              <div class="context-row"><span class="k">检验任务</span><span class="v mono">{{ result.task }}</span></div>
              <div class="context-row"><span class="k">样品编号</span><span class="v mono">{{ result.sample }}</span></div>
              <div class="context-row"><span class="k">检验项目</span><span class="v">{{ result.item_name }}</span></div>
              <div class="context-row"><span class="k">检验人</span><span class="v">{{ result.analyst }}</span></div>
              <div class="context-row"><span class="k">记录状态</span><span class="v"><span class="pill" :class="statusClass(result.result_status)">{{ result.result_status }}</span></span></div>
            </div>

            <div class="context-card limits-card">
              <div class="panel-head-inline"><h3>标准限度（冻结快照）</h3></div>
              <div class="limit-list">
                <div class="limit-box"><span class="lbl">限度模式</span><span class="val">{{ limitsTypeLabel }}</span></div>
                <div class="limit-box"><span class="lbl">限度范围</span><span class="val mono">{{ limitsText }}</span></div>
                <div class="limit-box"><span class="lbl">有效位数</span><span class="val mono">{{ result.significant_digits }}</span></div>
              </div>
            </div>
          </div>

          <div>
            <div class="panel">
              <div class="panel-head">
                <div><h3>结果数据</h3><div class="sub">提交后由判定引擎自动判定</div></div>
              </div>
              <div class="panel-body">
                <a-form layout="vertical" :disabled="result.result_status !== '草稿'">
                  <div class="form-grid">
                    <a-form-item label="结果原始值">
                      <a-input v-model:value="result.raw_value" placeholder="请输入原始读数" />
                    </a-form-item>
                    <a-form-item label="结果值">
                      <a-input v-model:value="result.result_value" placeholder="计算结果（带单位）" />
                    </a-form-item>
                    <a-form-item label="检验仪器（预留）">
                      <a-input v-model:value="result.instrument_used" placeholder="TEST-HBOS-M2-HPLC-01" />
                    </a-form-item>
                    <a-form-item label="结果描述（记录型项目）" class="full">
                      <a-input v-model:value="result.result_text" placeholder="如：符合规定" />
                    </a-form-item>
                  </div>
                </a-form>

                <div v-if="result.verdict" class="form-section">
                  <div class="form-section-title">判定结果</div>
                  <div class="judge-preview" :class="verdictClass">
                    <CheckCircleFilled :style="{ fontSize: '20px' }" />
                    <div>
                      <div class="big">{{ result.verdict }}</div>
                      <div>{{ result.verdict_reason }}</div>
                    </div>
                  </div>
                </div>

                <div class="form-section">
                  <div class="form-section-title">电子签名</div>
                  <div class="signature-strip">
                    <div class="sig-item"><div class="sig-label">检验人</div><div class="sig-name">{{ result.submitted_signature || '待提交' }}</div></div>
                    <div class="sig-arrow">→</div>
                    <div class="sig-item" :class="{ pending: !result.reviewed_signature }"><div class="sig-label">复核人</div><div class="sig-name">{{ result.reviewed_signature || '待复核' }}</div></div>
                    <div class="sig-arrow">→</div>
                    <div class="sig-item" :class="{ pending: !result.approved_signature }"><div class="sig-label">批准人</div><div class="sig-name">{{ result.approved_signature || '待批准' }}</div></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="panel revisions">
              <div class="panel-head">
                <div><h3>修订记录</h3><div class="sub">ALCOA：修改原因必填，原记录不可覆盖</div></div>
              </div>
              <div class="panel-body">
                <a-table v-if="revisions.length > 0" :data-source="revisions" size="small" :pagination="false" row-key="name">
                  <a-table-column title="修订号" data-index="name" key="name" :width="140">
                    <template #default="{ text }"><span class="mono">{{ text }}</span></template>
                  </a-table-column>
                  <a-table-column title="字段" data-index="field_changed" key="field_changed" :width="100" />
                  <a-table-column title="修改前" data-index="old_value" key="old_value" />
                  <a-table-column title="修改后" data-index="new_value" key="new_value" />
                  <a-table-column title="原因" data-index="change_reason" key="change_reason" />
                  <a-table-column title="修改人" data-index="changed_by" key="changed_by" :width="90">
                    <template #default="{ text }"><span class="mono">{{ text }}</span></template>
                  </a-table-column>
                </a-table>
                <div v-else class="empty-note">暂无修订记录</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-else-if="!loading" class="empty">
        <a-empty description="未找到检测记录。请从任务看板进入结果录入。" />
        <a-button @click="$router.push('/tasks')">返回任务看板</a-button>
      </div>
    </div>

    <!-- 修订弹窗 -->
    <a-modal v-model:open="showRevise" title="修订检测结果" :footer="null" width="460">
      <a-form layout="vertical">
        <a-form-item label="当前值">
          <a-input :value="String(result?.result_value ?? result?.result_text ?? '')" disabled />
        </a-form-item>
        <a-form-item label="新值 *">
          <a-input v-model:value="reviseForm.new_value" placeholder="输入修订后的值" />
        </a-form-item>
        <a-form-item label="修订原因 *">
          <a-textarea v-model:value="reviseForm.reason" :rows="3" placeholder="ALCOA 要求：必须填写修改原因" />
        </a-form-item>
        <div class="modal-footer">
          <a-button @click="showRevise = false">取消</a-button>
          <a-button type="primary" danger :loading="revising" @click="doRevise">确认修订</a-button>
        </div>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { CheckOutlined, CheckCircleFilled } from '@ant-design/icons-vue'
import {
  getDoc, submitResult as apiSubmit, reviewResult as apiReview,
  approveResult as apiApprove, reviseResult as apiRevise, listDoctype,
} from '@/api/lims'

const route = useRoute()
const loading = ref(true)
const submitting = ref(false)
const revising = ref(false)
const result = ref<any>(null)
const revisions = ref<any[]>([])

const showRevise = ref(false)
const reviseForm = reactive({ new_value: '', reason: '' })

const taskName = computed(() => String(route.params.id || ''))

const limitsTypeLabel = computed(() => {
  const t: string = result.value?.limits_type || ''
  const map: Record<string, string> = { 区间: '区间', 上限: '上限', 下限: '下限', 记录型: '记录型' }
  return map[t] || t || '—'
})
const limitsText = computed(() => {
  const r = result.value
  if (!r) return '—'
  if (r.limits_type === '记录型') return '记录型'
  if (r.limits_type === '上限' && r.upper_limit != null) return `≤ ${r.upper_limit} ${r.unit || ''}`
  if (r.limits_type === '下限' && r.lower_limit != null) return `≥ ${r.lower_limit} ${r.unit || ''}`
  if (r.lower_limit != null && r.upper_limit != null) return `${r.lower_limit} - ${r.upper_limit} ${r.unit || ''}`
  return '—'
})
const verdictClass = computed(() => {
  const v = result.value?.verdict || ''
  if (v === '合格') return 'pass'
  if (v === '不合格') return 'danger'
  if (v === '不适用') return 'na'
  return 'warn'
})

function statusClass(s: string) {
  return {
    草稿: 'pill-muted', 已提交: 'pill-info', 已复核: 'pill-warn',
    已批准: 'pill-pass', 已修订: 'pill-danger',
  }[s] || 'pill-muted'
}

async function loadResult() {
  loading.value = true
  try {
    const id = taskName.value
    let full: any = null
    if (id.startsWith('HBOS-TR-')) {
      full = await getDoc<any>('HBOS Test Result', id)
    } else {
      const results = await listDoctype('HBOS Test Result', ['*'], { task: id }, 1)
      if (results.length > 0) {
        full = await getDoc<any>('HBOS Test Result', results[0].name)
      }
    }
    if (full) {
      result.value = full
      revisions.value = await listDoctype<any>(
        'HBOS Result Revision',
        ['name', 'field_changed', 'old_value', 'new_value', 'change_reason', 'changed_by', 'changed_at'],
        { result: full.name }, 50,
      )
    }
  } catch {
    result.value = null
  } finally {
    loading.value = false
  }
}

async function submitResult() {
  if (!result.value) return
  submitting.value = true
  try {
    const res = await apiSubmit({
      result_name: result.value.name,
      raw_value: result.value.raw_value,
      result_value: result.value.result_value,
      result_text: result.value.result_text,
      instrument_used: result.value.instrument_used,
    })
    message.success(`结果已提交，判定：${res.verdict}`)
    await loadResult()
  } finally {
    submitting.value = false
  }
}

async function doReview() {
  submitting.value = true
  try {
    await apiReview(result.value.name)
    message.success(`检测记录 ${result.value.name} 已复核`)
    await loadResult()
  } finally {
    submitting.value = false
  }
}

async function doApprove() {
  submitting.value = true
  try {
    await apiApprove(result.value.name)
    message.success(`检测记录 ${result.value.name} 已批准`)
    await loadResult()
  } finally {
    submitting.value = false
  }
}

async function doRevise() {
  if (!reviseForm.new_value || !reviseForm.reason) {
    message.warning('新值和修订原因必填')
    return
  }
  revising.value = true
  try {
    const res = await apiRevise(result.value.name, reviseForm.new_value, reviseForm.reason)
    message.success(`修订完成，新版本：${res.new_result}`)
    showRevise.value = false
    reviseForm.new_value = ''
    reviseForm.reason = ''
    await loadResult()
  } finally {
    revising.value = false
  }
}

onMounted(loadResult)
</script>

<style scoped>
.load-area { min-height: 400px; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }

.result-layout { display: grid; grid-template-columns: 320px 1fr; gap: 14px; align-items: start; }
.context-card { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.context-row { display: flex; justify-content: space-between; padding: 9px 14px; border-bottom: 1px solid #eef2f0; font-size: 12px; }
.context-row:last-child { border-bottom: 0; }
.context-row .k { color: var(--muted); }
.context-row .v { color: var(--ink); font-weight: 500; }
.limits-card { margin-top: 14px; }
.panel-head-inline { padding: 12px 14px; border-bottom: 1px solid var(--line); font-size: 14px; }
.limit-list { padding: 12px 14px; display: grid; gap: 10px; }
.limit-box { display: flex; justify-content: space-between; font-size: 12px; }
.limit-box .lbl { color: var(--muted); }
.limit-box .val { color: var(--ink); font-weight: 600; }

.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); margin-bottom: 14px; }
.panel-head { padding: 12px 16px; border-bottom: 1px solid var(--line); }
.panel-head h3 { font-size: 14px; }
.panel-head .sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.panel-body { padding: 16px; }
.panel.revisions .panel-body { padding: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.form-grid .full { grid-column: 1 / -1; }
.form-section { margin-top: 18px; }
.form-section-title { font-size: 12px; font-weight: 600; margin-bottom: 10px; }

.judge-preview { display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: var(--radius); }
.judge-preview.pass { background: var(--pass-soft); border: 1px solid #b9e0cb; color: var(--pass); }
.judge-preview.danger { background: var(--danger-soft); border: 1px solid #eec4bd; color: var(--danger); }
.judge-preview.na { background: var(--info-soft); border: 1px solid #c1d9f0; color: var(--info); }
.judge-preview.warn { background: var(--warn-soft); border: 1px solid #ecd9b4; color: var(--warn); }
.judge-preview .big { font-size: 15px; font-weight: 700; }
.judge-preview div:last-child { font-size: 12px; margin-top: 2px; }

.signature-strip { display: flex; align-items: center; gap: 10px; }
.sig-item { flex: 1; background: var(--surface-2); border: 1px solid var(--line); border-radius: 6px; padding: 10px 14px; }
.sig-item.pending { border-style: dashed; }
.sig-label { font-size: 10px; color: var(--muted); }
.sig-name { font-size: 12px; font-weight: 600; color: var(--ink); margin-top: 4px; }
.sig-item.pending .sig-name { color: var(--muted); }
.sig-arrow { color: var(--muted); }

.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 20px 0; }
.empty { text-align: center; padding: 60px 0; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; }
@media (max-width: 1180px) { .result-layout { grid-template-columns: 1fr; } }
</style>
