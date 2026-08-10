<template>
  <div class="page">
    <div v-loading="loading" class="load-area">
      <template v-if="result">
        <div class="page-head">
          <div>
            <h1>检验结果录入</h1>
            <p>{{ result.name }} · {{ result.item_name }} · 提交后自动判定并生成电子签名</p>
          </div>
          <div class="page-actions">
            <el-button type="primary" :loading="submitting" :disabled="result.result_status !== '草稿'" @click="submitResult">
              <el-icon><Check /></el-icon>&nbsp;提交结果
            </el-button>
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
                <el-form label-position="top" size="default" :disabled="result.result_status !== '草稿'">
                  <div class="form-grid">
                    <el-form-item label="结果原始值">
                      <el-input v-model="result.raw_value" placeholder="请输入原始读数" />
                    </el-form-item>
                    <el-form-item label="结果值">
                      <el-input v-model="result.result_value" placeholder="计算结果（带单位）" />
                    </el-form-item>
                    <el-form-item label="检验仪器（预留）">
                      <el-input v-model="result.instrument_used" placeholder="TEST-HBOS-M2-HPLC-01" />
                    </el-form-item>
                    <el-form-item label="结果描述（记录型项目）" class="full">
                      <el-input v-model="result.result_text" placeholder="如：符合规定" />
                    </el-form-item>
                  </div>
                </el-form>

                <div v-if="result.verdict" class="form-section">
                  <div class="form-section-title">判定结果</div>
                  <div class="judge-preview" :class="verdictClass">
                    <el-icon :size="20"><CircleCheckFilled /></el-icon>
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
                    <el-icon class="sig-arrow"><ArrowRight /></el-icon>
                    <div class="sig-item" :class="{ pending: !result.reviewed_signature }"><div class="sig-label">复核人</div><div class="sig-name">{{ result.reviewed_signature || '待复核' }}</div></div>
                    <el-icon class="sig-arrow"><ArrowRight /></el-icon>
                    <div class="sig-item" :class="{ pending: !result.approved_signature }"><div class="sig-label">批准人</div><div class="sig-name">{{ result.approved_signature || '待批准' }}</div></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-else-if="!loading" class="empty">
        <el-empty description="未找到检测记录。请从任务看板进入结果录入。" />
        <el-button @click="$router.push('/tasks')">返回任务看板</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, CircleCheckFilled, ArrowRight } from '@element-plus/icons-vue'
import { getDoc, submitResult as apiSubmit } from '@/api/lims'

const route = useRoute()
const loading = ref(true)
const submitting = ref(false)
const result = ref<any>(null)

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
    // 通过任务名查询关联检测记录
    const results = await import('@/api/lims').then((m) =>
      m.listDoctype('HBOS Test Result', ['*'], { task: taskName.value }, 1),
    )
    if (results.length > 0) {
      result.value = results[0]
      // 补充原始字符串字段（get_list 不含 fetch 字段，重新 get）
      const full = await getDoc<any>('HBOS Test Result', results[0].name)
      result.value = full
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
    ElMessage.success(`结果已提交，判定：${res.verdict}`)
    await loadResult()
  } finally {
    submitting.value = false
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

.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-head { padding: 12px 16px; border-bottom: 1px solid var(--line); }
.panel-head h3 { font-size: 14px; }
.panel-head .sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.panel-body { padding: 16px; }
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

.empty { text-align: center; padding: 60px 0; }
@media (max-width: 1180px) { .result-layout { grid-template-columns: 1fr; } }
</style>
