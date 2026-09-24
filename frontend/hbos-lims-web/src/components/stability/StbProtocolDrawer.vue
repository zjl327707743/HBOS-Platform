<template>
  <a-drawer v-model:open="open" :title="title" :width="620" placement="right">
    <!-- 详情态 -->
    <template v-if="mode === 'view' && detail">
      <p class="stb-gate-sub">
        {{ detail.product_name }}（{{ detail.product_code }}）· 通知单 {{ detail.notice }} ·
        {{ detail.notice_status }}
      </p>

      <div class="stb-drawer-section">
        <h3>批准后冻结内容</h3>
        <div class="stb-drawer-kv">
          <div><label>版本</label><b>v{{ detail.version }}</b></div>
          <div><label>批次</label><b>{{ detail.batches.length }} 批</b></div>
          <div><label>条件</label><b>{{ detail.study_conditions.length }} 个</b></div>
          <div><label>项目</label><b>{{ detail.items.length }} 项</b></div>
          <div><label>室温恢复</label><b>{{ detail.room_temp_recovery_days ?? 0 }} 天</b></div>
          <div>
            <label>快照</label>
            <b :class="detail.snapshot.frozen ? 'ok' : 'dim'">
              {{ detail.snapshot.frozen ? '已冻结' : '未冻结' }}
            </b>
          </div>
        </div>
        <div v-if="detail.snapshot.spec_version" class="stb-drawer-kv" style="margin-top: 10px">
          <div><label>标准版本</label><b class="mono">{{ detail.snapshot.spec_version }}</b></div>
          <div><label>方法版本</label><b class="mono">{{ detail.snapshot.method_version || '—' }}</b></div>
          <div><label>有效期快照</label><b>{{ detail.snapshot.vd_months_snapshot ?? '—' }} 月</b></div>
        </div>
      </div>

      <div class="stb-drawer-section">
        <h3>批次</h3>
        <a-table
          :columns="batchColumns"
          :data-source="detail.batches"
          size="small"
          row-key="batch_no"
          :pagination="false"
        />
      </div>

      <div class="stb-drawer-section">
        <h3>考察项目</h3>
        <a-table
          :columns="itemColumns"
          :data-source="detail.items"
          size="small"
          row-key="stability_test_item"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'key'">
              <span :class="record.is_key_item ? 'pill pill-pass' : 'pill pill-muted'">
                {{ record.is_key_item ? '重点' : '一般' }}
              </span>
            </template>
          </template>
        </a-table>
      </div>

      <div class="stb-drawer-section">
        <h3>签署链</h3>
        <div class="stb-audit-line">
          <span class="stb-audit-dot"></span>
          <div>
            <strong>起草 · {{ detail.signoff.drafted_by || '—' }}</strong>
            <span>{{ detail.signoff.draft_date || '—' }}</span>
          </div>
        </div>
        <div class="stb-audit-line">
          <span class="stb-audit-dot gray"></span>
          <div>
            <strong>QA 审核 · {{ detail.signoff.qa_review_by || '—' }}</strong>
            <span>{{ detail.signoff.qa_review_date || '—' }}</span>
          </div>
        </div>
        <div class="stb-audit-line">
          <span class="stb-audit-dot"></span>
          <div>
            <strong>批准 · {{ detail.signoff.qa_approve_by || '—' }}</strong>
            <span>{{ detail.signoff.approve_date || '—' }} · 生效 {{ detail.signoff.effective_date || '—' }}</span>
          </div>
        </div>
        <div v-if="detail.signoff.reject_reason" class="stb-audit-line">
          <span class="stb-audit-dot red"></span>
          <div><strong>驳回</strong><span>{{ detail.signoff.reject_reason }}</span></div>
        </div>
        <div v-if="detail.signoff.void_reason" class="stb-audit-line">
          <span class="stb-audit-dot red"></span>
          <div><strong>作废</strong><span>{{ detail.signoff.void_reason }}</span></div>
        </div>
      </div>
    </template>

    <!-- 起草态 -->
    <template v-else-if="mode === 'create'">
      <p class="stb-gate-sub">通知单 {{ noticeName }} · 年度持续稳定性考察类不建方案单</p>

      <div class="stb-drawer-section">
        <h3>方案信息</h3>
        <div class="stb-form-grid">
          <div class="stb-form-field full">
            <label>目的</label>
            <a-textarea v-model:value="form.purpose" :rows="2" placeholder="考察目的" />
          </div>
          <div class="stb-form-field full">
            <label>范围</label>
            <a-textarea v-model:value="form.scope" :rows="2" placeholder="考察范围" />
          </div>
          <div class="stb-form-field">
            <label>室温恢复天数</label>
            <a-input-number v-model:value="form.room_temp_recovery_days" :min="0" style="width: 100%" />
          </div>
          <div class="stb-form-field">
            <label>标准版本快照</label>
            <a-input v-model:value="form.spec_version" placeholder="如 V1.0" />
          </div>
          <div class="stb-form-field">
            <label>方法版本快照</label>
            <a-input v-model:value="form.method_version" placeholder="如 V1.0" />
          </div>
          <div class="stb-form-field">
            <label>检验标准操作规程</label>
            <a-input v-model:value="form.test_method_ref" />
          </div>
        </div>
      </div>

      <div class="stb-drawer-section">
        <h3>考察项目 *（{{ form.items.length }} 项）</h3>
        <div v-for="(it, i) in form.items" :key="i" class="stb-form-row">
          <a-select
            v-model:value="it.stability_test_item"
            :options="itemOptions"
            style="flex: 1"
            placeholder="选择检验项目"
            show-search
            :filter-option="false"
            @search="searchItems"
          />
          <a-checkbox v-model:checked="it.boolKey">重点</a-checkbox>
          <a-button type="text" danger :disabled="form.items.length <= 1" @click="form.items.splice(i, 1)">
            <template #icon><MinusCircleOutlined /></template>
          </a-button>
        </div>
        <a-button size="small" @click="form.items.push({ stability_test_item: undefined, boolKey: false })">
          <template #icon><PlusOutlined /></template>
          添加项目
        </a-button>
      </div>

      <div class="stb-notice">
        方案从通知单继承批次与试验条件；提交前通知单必须是「已批准」。
      </div>
    </template>

    <template #footer>
      <a-button @click="open = false">{{ mode === 'view' ? '关闭' : '取消' }}</a-button>
      <a-button v-if="mode === 'create'" type="primary" :loading="saving" @click="save">保存方案草稿</a-button>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons-vue'
import {
  createProtocol, master, protocolDetail,
  type MasterRow, type NoticeDetail, type ProtocolDetail,
} from '@/api/stability'

const emit = defineEmits<{ created: [name: string] }>()

const open = ref(false)
const saving = ref(false)
const mode = ref<'create' | 'view'>('view')
const detail = ref<ProtocolDetail | null>(null)
const noticeName = ref('')
const noticeDetail = ref<NoticeDetail | null>(null)
const itemList = ref<MasterRow[]>([])

const form = reactive({
  purpose: '',
  scope: '',
  room_temp_recovery_days: 1,
  spec_version: '',
  method_version: '',
  test_method_ref: '',
  items: [{ stability_test_item: undefined as string | undefined, boolKey: false }],
})

const title = computed(() => (mode.value === 'create' ? '起草稳定性方案' : '稳定性方案详情'))
const itemOptions = computed(() =>
  itemList.value.map((i) => ({ value: i.name, label: `${i.item_name}（${i.item_code}）` })))

const batchColumns = [
  { title: '批次号', dataIndex: 'batch_no', key: 'batch_no' },
  { title: '批量', dataIndex: 'batch_size', key: 'batch_size' },
  { title: '生产日期', dataIndex: 'manufacture_date', key: 'manufacture_date' },
]
const itemColumns = [
  { title: '检验项目', dataIndex: 'stability_test_item', key: 'item' },
  { title: '等级', key: 'key', width: 80 },
  { title: '方法版本', dataIndex: 'method_version', key: 'method_version', width: 110 },
]

async function showDetail(protocolName: string) {
  open.value = true
  mode.value = 'view'
  detail.value = null
  try {
    detail.value = await protocolDetail(protocolName)
  } catch {
    // 错误已由 client 拦截层弹出
  }
}

async function showCreate(notice: NoticeDetail) {
  open.value = true
  mode.value = 'create'
  noticeName.value = notice.name
  noticeDetail.value = notice
  form.purpose = ''
  form.scope = ''
  form.room_temp_recovery_days = 1
  form.spec_version = notice.snapshot.spec_version || ''
  form.method_version = notice.snapshot.method_version || ''
  form.test_method_ref = notice.test_method || ''
  form.items = [{ stability_test_item: undefined, boolKey: false }]
  try {
    const res = await master('HBOS Stability Test Item')
    itemList.value = res.rows
  } catch {
    // 错误已由 client 拦截层弹出
  }
}

function searchItems(kw: string) {
  void master('HBOS Stability Test Item', kw).then((r) => { itemList.value = r.rows }).catch(() => {})
}

async function save() {
  if (!noticeDetail.value) return
  if (form.items.some((i) => !i.stability_test_item)) return message.warning('请为每个项目选择检验项目')

  saving.value = true
  try {
    const res = await createProtocol({
      notice: noticeDetail.value.name,
      purpose: form.purpose,
      scope: form.scope,
      // 批次与条件从通知单继承（方案不允许另起一套）
      batches: noticeDetail.value.batches,
      study_conditions: noticeDetail.value.study_conditions,
      items: form.items.map((i) => ({
        stability_test_item: i.stability_test_item!, is_key_item: i.boolKey ? 1 : 0,
      })),
      qty: noticeDetail.value.qty,
      qty_uom: noticeDetail.value.qty_uom,
      pack_desc: noticeDetail.value.pack_desc,
      room_temp_recovery_days: form.room_temp_recovery_days,
      spec_version: form.spec_version,
      method_version: form.method_version,
      test_method_ref: form.test_method_ref,
    })
    message.success(`已创建方案草稿 ${res.name}`)
    open.value = false
    emit('created', res.name)
  } catch {
    // 具体错误已由 client 拦截层弹出
  } finally {
    saving.value = false
  }
}

defineExpose({ showDetail, showCreate })
</script>

<style scoped>
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.stb-form-row { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.stb-drawer-kv b.ok { color: var(--pass); }
</style>
