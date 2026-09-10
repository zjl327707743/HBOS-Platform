<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1>合规审计日志</h1>
        <p>全量自动记录登记、修改、仪器使用等数据完整性与法规要求可追溯事件（只读 · 防篡改）</p>
      </div>
      <span class="pill muted total-pill">{{ total }} 条事件</span>
    </div>

    <div class="filter-bar">
      <a-input v-model:value="filters.keyword" placeholder="搜索对象 / 摘要 / 指纹" allow-clear style="width:220px" @press-enter="load" />
      <a-select v-model:value="filters.log_type" placeholder="全部事件类型" allow-clear style="width:150px" @change="load">
        <a-select-option v-for="t in logTypes" :key="t" :value="t">{{ t }}</a-select-option>
      </a-select>
      <a-select v-model:value="filters.doctype_target" placeholder="全部对象（按板块）" allow-clear style="width:210px" @change="load">
        <a-select-opt-group v-for="g in groupedTargets" :key="g.label" :label="g.label">
          <a-select-option v-for="t in g.items" :key="t" :value="t">{{ TARGET_LABELS[t] || t }}</a-select-option>
        </a-select-opt-group>
      </a-select>
      <a-select v-model:value="filters.user" placeholder="全部操作人" allow-clear style="width:150px" @change="load">
        <a-select-option v-for="u in users" :key="u" :value="u">{{ u }}</a-select-option>
      </a-select>
      <a-range-picker v-model:value="filters.dateRange" value-format="YYYY-MM-DD" style="width:260px" @change="load" />
      <a-button type="primary" @click="load"><template #icon><ReloadOutlined /></template>查询</a-button>
    </div>

    <div class="panel">
      <div class="panel-body">
        <a-table
          :columns="columns"
          :data-source="events"
          :loading="loading"
          size="small"
          :pagination="{ current: page, pageSize, total, showSizeChanger: false, onChange: onPageChange }"
          row-key="name"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'created_at'"><span class="mono">{{ (record.created_at || '').slice(0, 16) }}</span></template>
            <template v-else-if="column.key === 'user'"><span class="mono">{{ record.user }}</span></template>
            <template v-else-if="column.key === 'log_type'">
              <span class="evt" :class="evtClass(record.log_type)">{{ record.log_type }}</span>
            </template>
            <template v-else-if="column.key === 'doc_name'"><span class="mono link" @click="openDrawer(record)">{{ record.doc_name }}</span></template>
            <template v-else-if="column.key === 'change'">
              <span v-if="record.field_changed">
                <span class="old">{{ record.old_value || '—' }}</span><span class="arrow">→</span><span class="new">{{ record.new_value || '—' }}</span>
                <span class="field-tag mono">({{ fieldLabel(record.field_changed) }})</span>
              </span>
              <span v-else class="dc">—</span>
            </template>
            <template v-else-if="column.key === 'checksum'"><span class="mono checksum">{{ shortChecksum(record.checksum) }}</span></template>
          </template>
        </a-table>
        <div v-if="!loading && events.length === 0" class="empty-note">暂无匹配的审计事件</div>
      </div>
    </div>

    <a-drawer v-model:open="drawerOpen" :width="440" placement="right" :closable="false">
      <template #title>
        <div v-if="drawerEvent">
          <div class="drawer-title">{{ drawerEvent.log_type }} · {{ drawerEvent.doc_name }}</div>
          <div class="drawer-sub">{{ drawerEvent.doctype_target }} · {{ drawerEvent.action_text }}</div>
        </div>
      </template>
      <div v-if="drawerEvent" class="drawer-body">
        <div class="sec">
          <div class="sec-title">事件信息</div>
          <div class="row"><span class="k">时间</span><span class="v">{{ drawerEvent.created_at }}</span></div>
          <div class="row"><span class="k">操作人</span><span class="v">{{ drawerEvent.user }}</span></div>
          <div class="row"><span class="k">对象</span><span class="v">{{ drawerEvent.doc_name }}</span></div>
          <div class="row"><span class="k">类型</span><span class="v zh">{{ drawerEvent.log_type }}</span></div>
          <div class="row"><span class="k">动作摘要</span><span class="v zh">{{ drawerEvent.action_text || '—' }}</span></div>
        </div>
        <div class="sec">
          <div class="sec-title">变更内容</div>
          <div class="diff-box" v-if="drawerEvent.field_changed">
            <div class="dc">字段：{{ fieldLabel(drawerEvent.field_changed) }}</div>
            <span class="old">{{ drawerEvent.old_value || '—' }}</span><span class="arrow">→</span><span class="new">{{ drawerEvent.new_value || '—' }}</span>
          </div>
          <div class="dc" v-else>无字段变更（动作类事件）</div>
        </div>
        <div class="sec">
          <div class="sec-title">原因</div>
          <div class="dc">{{ drawerEvent.reason || '—' }}</div>
        </div>
        <div class="sec">
          <div class="sec-title">数据完整性</div>
          <div class="row"><span class="k">记录指纹</span><span class="v checksum">{{ drawerEvent.checksum || '—' }}</span></div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { getAuditLog, getAuditTargets, type AuditEvent } from '@/api/lims'

const LOG_TYPES = ['创建', '修改', '删除', '登记入库', '提交', '复核', '批准', '修订', '放行', '拒绝',
  'OOS', '仪器使用', '规格生效', '规格废止', '预占', '释放预占', '使用出库', '销毁出库', '受托转出',
  '手动调整', '续留改期', '观察完成', '观察异常', '审批签署', '审批层跳过', '驳回', '越权拦截', 'SoD 拦截']

const events = ref<AuditEvent[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const filters = reactive({
  log_type: '',
  doctype_target: '',
  user: '',
  keyword: '',
  dateRange: [] as string[],
})
const drawerOpen = ref(false)
const drawerEvent = ref<AuditEvent | null>(null)

const logTypes = LOG_TYPES

const TARGET_LABELS: Record<string, string> = {
  'HBOS Sample': '样品登记', 'HBOS Sample Task': '检验任务', 'HBOS Test Result': '检测记录',
  'HBOS Result Revision': '结果修订', 'HBOS COA': 'COA 报告', 'HBOS Specification': '质量标准',
  'HBOS Sample Type': '样品类型', 'HBOS Test Item': '检验项目', 'HBOS Calculation': '计算公式',
  'HBOS Lab Department': '检验组',
  'HBOS Retention Product': '留样产品', 'HBOS Retention Sample': '留样登记',
  'HBOS Retention Observation': '观察记录', 'HBOS Retention Usage Apply': '使用申请',
  'HBOS Retention Disposal Apply': '处理申请',
}
// 按业务板块分组（后续新增板块在此追加；未归类的自动进「其他」）
const TARGET_GROUPS: { label: string; items: string[] }[] = [
  { label: '业务操作', items: ['HBOS Sample', 'HBOS Sample Task', 'HBOS Test Result', 'HBOS Result Revision'] },
  { label: '报告与标准', items: ['HBOS COA', 'HBOS Specification'] },
  { label: '质量主数据', items: ['HBOS Sample Type', 'HBOS Test Item', 'HBOS Calculation', 'HBOS Lab Department'] },
  { label: '留样管理', items: ['HBOS Retention Product', 'HBOS Retention Sample', 'HBOS Retention Observation', 'HBOS Retention Usage Apply', 'HBOS Retention Disposal Apply'] },
]
/** 全量对象抽屉（非仅当前页） */
const targetFacets = ref<string[]>([])
const groupedTargets = computed(() => {
  const known = new Set(TARGET_GROUPS.flatMap((g) => g.items))
  const groups = TARGET_GROUPS
    .map((g) => ({ label: g.label, items: g.items.filter((t) => targetFacets.value.includes(t)) }))
    .filter((g) => g.items.length)
  const others = targetFacets.value.filter((t) => !known.has(t))
  if (others.length) groups.push({ label: '其他', items: others })
  return groups
})
async function fetchTargets() {
  try { targetFacets.value = await getAuditTargets() } catch { /* 未登录/无权限时降级为空 */ }
}
const users = computed(() => [...new Set(events.value.map((e) => e.user).filter(Boolean))])

const columns = [
  { title: '时间', key: 'created_at', dataIndex: 'created_at', width: 160 },
  { title: '操作人', key: 'user', dataIndex: 'user', width: 130 },
  { title: '事件类型', key: 'log_type', dataIndex: 'log_type', width: 110 },
  { title: '对象', key: 'doc_name', dataIndex: 'doc_name', width: 190 },
  { title: '动作摘要', key: 'action_text', dataIndex: 'action_text', width: 220 },
  { title: '变更内容', key: 'change', width: 260 },
  { title: '原因', key: 'reason', dataIndex: 'reason', width: 160 },
  { title: '记录指纹', key: 'checksum', dataIndex: 'checksum', width: 120 },
]

function evtClass(t: string): string {
  return {
    创建: 'cy', 修改: 'md', 删除: 'dl', 提交: 'sub', 复核: 'rev',
    批准: 'app', 修订: 'edt', 放行: 'approve', 拒绝: 'md',
    OOS: 'oos', 仪器使用: 'inst', 规格生效: 'spec', 规格废止: 'spec',
  }[t] || 'md'
}
function fieldLabel(f: string): string {
  return { status: '状态', result_status: '记录状态', report_status: '报告状态', verdict: '判定', result_value: '结果值', result_text: '结果描述', result: '结果记录', raw_value: '原始值', material_name: '物料名称', batch_no: '批号', sample_type: '样品类型', spec_version: '标准版本', unit: '单位', lower_limit: '下限', upper_limit: '上限', oos_locked: 'OOS锁定', approver: '批准人', reviewer: '复核人', priority: '优先级' }[f] || f
}
function shortChecksum(c: string): string {
  if (!c) return '—'
  return c.length > 12 ? c.slice(0, 6) + '…' + c.slice(-6) : c
}
function openDrawer(e: AuditEvent) {
  drawerEvent.value = e
  drawerOpen.value = true
}

async function fetchPage(p: number) {
  loading.value = true
  try {
    const res = await getAuditLog({
      log_type: filters.log_type || undefined,
      doctype_target: filters.doctype_target || undefined,
      user: filters.user || undefined,
      keyword: filters.keyword || undefined,
      from_date: filters.dateRange?.[0],
      to_date: filters.dateRange?.[1],
      limit: pageSize.value,
      offset: (p - 1) * pageSize.value,
    })
    events.value = res.events || []
    total.value = res.total || 0
    page.value = p
  } finally {
    loading.value = false
  }
}
function load() {
  fetchPage(1)
}
function onPageChange(p: number) {
  fetchPage(p)
}

onMounted(async () => { await fetchTargets(); load() })
</script>

<style scoped>
.page-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.total-pill { margin-left: auto; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; align-items: center; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-body { padding: 0; }
.panel-body :deep(.ant-table) { font-size: 12px; }
.empty-note { text-align: center; color: var(--muted); font-size: 12px; padding: 30px 0; }
.mono { font-family: var(--mono); }
.link { color: var(--primary); cursor: pointer; }
.evt { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
.evt.cy, .evt.sub, .evt.spec { background: var(--info-soft); color: var(--info); }
.evt.md { background: var(--warn-soft); color: var(--warn); }
.evt.dl { background: var(--danger-soft); color: var(--danger); }
.evt.rev, .evt.app, .evt.approve { background: var(--pass-soft); color: var(--pass); }
.evt.edt { background: var(--danger-soft); color: var(--danger); }
.evt.oos { background: #f7e9e6; color: var(--oos); }
.evt.inst { background: var(--primary-soft); color: var(--primary-strong); }
.old { font-family: var(--mono); color: var(--danger); text-decoration: line-through; font-size: 12px; }
.arrow { font-family: var(--mono); color: var(--muted); margin: 0 4px; }
.new { font-family: var(--mono); color: var(--pass); font-weight: 600; font-size: 12px; }
.field-tag { font-family: var(--mono); color: var(--muted); margin-left: 6px; font-size: 10px; }
.dc { color: var(--muted); font-size: 11px; }
.checksum { font-size: 10px; color: var(--muted); }
.drawer-title { font-size: 15px; font-weight: 700; }
.drawer-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.drawer-body { padding: 4px 2px; }
.sec { margin-bottom: 16px; }
.sec-title { font-size: 11px; font-weight: 700; color: var(--muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: .04em; }
.row { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; border-bottom: 1px dashed var(--surface-2); font-size: 12px; }
.row:last-child { border-bottom: 0; }
.row .k { color: var(--muted); flex: 0 0 88px; }
.row .v { font-family: var(--mono); font-size: 11px; text-align: right; word-break: break-all; }
.row .v.zh { font-family: inherit; font-size: 12px; }
.diff-box { border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; font-size: 12px; }
</style>
