<template>
  <a-drawer v-model:open="open" title="申请取样 / 检测延期" :width="580" placement="right">
    <p class="stb-gate-sub">申请与批准是独立动作；批准前有效截止日不被改写。</p>

    <div class="stb-drawer-section">
      <h3>时间点 *</h3>
      <a-select
        v-model:value="form.timepoint"
        :options="timepointOptions"
        show-search
        :filter-option="false"
        placeholder="选择待取样 / 待检测 / 检测中的时间点"
        style="width: 100%"
        @change="onTimepointChange"
      />
    </div>

    <div v-if="selected" class="stb-drawer-section">
      <h3>日期链（只读）</h3>
      <div class="stb-drawer-kv">
        <div><label>类型</label><b>{{ form.delay_type }}</b></div>
        <div><label>计划日期</label><b class="mono">{{ planned || '—' }}</b></div>
        <div><label>政策硬上限</label><b class="mono">{{ policyLatest || '—' }}</b></div>
        <div><label>当前状态</label><b>{{ selected.status }}</b></div>
      </div>
      <div class="stb-form-hint">
        申请顺延日期须落在「计划日期 ~ 政策硬上限」闭区间内；批准日期不得早于申请日、不得突破政策上限。
      </div>
    </div>

    <div class="stb-drawer-section">
      <h3>延期申请</h3>
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>延期类型 *</label>
          <a-select v-model:value="form.delay_type" :options="typeOptions" style="width: 100%" @change="onTimepointChange" />
        </div>
        <div class="stb-form-field">
          <label>申请顺延至 *</label>
          <a-date-picker
            v-model:value="form.requested_due_date"
            style="width: 100%"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledDate"
          />
        </div>
        <div class="stb-form-field full">
          <label>延期原因 *</label>
          <a-textarea v-model:value="form.reason" :rows="3" placeholder="填写延期原因" />
        </div>
      </div>
    </div>

    <template #footer>
      <a-button @click="open = false">取消</a-button>
      <a-button type="primary" :loading="saving" @click="save">提交延期申请</a-button>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { applyDelay, type ScheduleRow } from '@/api/stability'

const props = defineProps<{ rows: ScheduleRow[] }>()
const emit = defineEmits<{ created: [name: string] }>()

const open = ref(false)
const saving = ref(false)

const form = reactive({
  timepoint: undefined as string | undefined,
  delay_type: '取样延期',
  requested_due_date: undefined as string | undefined,
  reason: '',
})

const CANCELLABLE = ['待取样', '待检测', '检测中']

const eligible = computed(() => props.rows.filter((r) => CANCELLABLE.includes(r.status)))
const timepointOptions = computed(() =>
  eligible.value.map((r) => ({
    value: r.name,
    label: `${r.product_name || ''} ${r.batch_no || ''} · ${r.time_point_label} · ${r.condition_type}（${r.status}）`,
  })))
const selected = computed(() => props.rows.find((r) => r.name === form.timepoint))
const typeOptions = ['取样延期', '检测延期'].map((v) => ({ value: v, label: v }))

const planned = computed(() => {
  const s = selected.value
  if (!s) return null
  return form.delay_type === '取样延期' ? s.plan_sample_date : s.plan_test_date
})
const policyLatest = computed(() => {
  const s = selected.value
  if (!s) return null
  return form.delay_type === '取样延期' ? s.policy_latest_sample_due : s.policy_latest_test_due
})

/** 只允许落在 [计划日期, 政策硬上限] 内（后端同校） */
function disabledDate(current: Date): boolean {
  if (!current) return false
  const d = current.toISOString().slice(0, 10)
  if (planned.value && d < planned.value) return true
  if (policyLatest.value && d > policyLatest.value) return true
  return false
}

function onTimepointChange() {
  const s = selected.value
  if (!s) return
  form.requested_due_date = undefined
}

function show(presetTimepoint?: string) {
  open.value = true
  form.timepoint = presetTimepoint
  form.delay_type = '取样延期'
  form.requested_due_date = undefined
  form.reason = ''
}
defineExpose({ show })

async function save() {
  if (!form.timepoint) return message.warning('请选择时间点')
  if (!form.requested_due_date) return message.warning('申请顺延日期必填')
  if (!form.reason.trim()) return message.warning('延期原因必填')

  saving.value = true
  try {
    await applyDelay(form.timepoint, form.delay_type, form.requested_due_date, form.reason.trim())
    message.success('延期申请已提交')
    open.value = false
    emit('created', form.timepoint)
  } catch {
    // 具体错误已由 client 拦截层弹出（含日期链 / 在途唯一等后端校验）
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.stb-form-hint { font-size: 12px; color: var(--muted); margin-top: 8px; }
</style>
