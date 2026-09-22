<template>
  <div class="page">
    <a-tabs v-model:activeKey="activeTab">
      <a-tab-pane key="register" tab="样品登记">
        <div class="page-head">
          <div>
            <h1>样品登记</h1>
            <p>固定样品类型与检验优先级，按类型自动切换专属表单与检验模板</p>
          </div>
          <div class="page-actions">
            <a-button @click="resetFields">重置</a-button>
            <a-button @click="resetForm">保存草稿</a-button>
            <a-button type="primary" :loading="submitting" @click="submitSample">
              <template #icon><PlusOutlined /></template>
              登记样品
            </a-button>
          </div>
        </div>

        <div class="sample-layout">
          <div class="sample-main">
            <!-- 固定决策条 -->
            <div class="form-context">
              <div class="context-head">
                <div>
                  <div class="context-title">样品决策条 <span class="pin">固定显示</span></div>
                  <div class="context-sub">切换样品类型后，表单字段、质量标准与检验项目自动联动</div>
                </div>
                <div class="context-state"><span class="dot"></span>当前模板 <b>{{ contextTemplate }}</b></div>
              </div>
              <div class="context-controls">
                <div class="context-field">
                  <label>样品类型 <span class="req">*</span></label>
                  <a-select v-model:value="form.sample_type" placeholder="选择类型" style="width:100%" @change="onTypeChange">
                    <a-select-option v-for="t in typeOptions" :key="t" :value="t">{{ t }}</a-select-option>
                  </a-select>
                  <div class="select-hint">选择类型后，整张表单切换为该类型专属表单</div>
                </div>
                <div class="context-field priority-field">
                  <label>检验优先级 <span class="req">*</span></label>
                  <a-select v-model:value="form.priority" placeholder="选择优先级" style="width:100%">
                    <a-select-option value="常规">常规</a-select-option>
                    <a-select-option value="加急">加急</a-select-option>
                    <a-select-option value="特急">特急</a-select-option>
                  </a-select>
                  <div class="select-hint">只影响排程与检验时限，不改变表单字段</div>
                </div>
              </div>
            </div>

            <!-- 类型专属表单（整表替换） -->
            <div class="panel type-panel">
              <div class="panel-head">
                <div><h3>{{ formPanelTitle }}</h3><div class="sub">整张表单随样品类型切换，登记后关键字段冻结</div></div>
                <span class="pill primary">{{ formPanelTag }}</span>
              </div>
              <div class="panel-body">
                <a-form :model="form" layout="vertical" class="type-form" :key="form.sample_type">
                  <div class="form-grid">
                    <a-form-item v-for="f in activeFields" :key="f.key" :label="f.label + (f.required ? ' *' : '')" :class="{ full: f.full }">
                      <!-- 日期选择 -->
                      <a-date-picker
                        v-if="f.type === 'date' && f.picker !== 'flex'"
                        v-model:value="form[f.key]"
                        value-format="YYYY-MM-DD"
                        style="width:100%"
                        :placeholder="f.placeholder || '选择日期'"
                      />
                      <!-- 复验期/有效期至：年月 / 年月日 可切换 -->
                      <div v-else-if="f.type === 'date' && f.picker === 'flex'" class="flex-date">
                        <!-- slashIfEmpty：无值时显示 "/"，可点"选择日期"改为日期 -->
                        <template v-if="f.slashIfEmpty && form[f.key] === '/'">
                          <a-input
                            value="/"
                            readOnly
                            class="slash-display"
                            style="flex:1"
                          />
                          <a-popover trigger="click" placement="bottomLeft">
                            <template #content>
                              <a-date-picker
                                :value="null"
                                :picker="form[f.key + '_picker'] === 'month' ? 'month' : 'date'"
                                :value-format="form[f.key + '_picker'] === 'month' ? 'YYYY-MM' : 'YYYY-MM-DD'"
                                open
                                @change="(val: any) => onExpiryChange(f, val)"
                              />
                            </template>
                            <a-button size="small" class="date-mode-btn">选择日期</a-button>
                          </a-popover>
                        </template>
                        <a-date-picker
                          v-else
                          v-model:value="form[f.key]"
                          :picker="form[f.key + '_picker'] === 'month' ? 'month' : 'date'"
                          :value-format="form[f.key + '_picker'] === 'month' ? 'YYYY-MM' : 'YYYY-MM-DD'"
                          style="flex:1"
                          :placeholder="form[f.key + '_picker'] === 'month' ? '选择年-月' : '选择年-月-日'"
                          allow-clear
                          @change="(val: any) => onExpiryChange(f, val)"
                        />
                        <a-button
                          size="small"
                          class="date-mode-btn"
                          @click="toggleDateMode(f.key)"
                        >
                          {{ form[f.key + '_picker'] === 'month' ? '年-月-日' : '年-月' }}
                        </a-button>
                      </div>
                      <!-- 数量 + 单位选择格 -->
                      <div v-else-if="f.type === 'unit'" class="unit-field">
                        <a-input-number
                          v-model:value="form[f.key]"
                          :placeholder="f.placeholder || '填写数量'"
                          :min="0"
                          style="flex:1"
                        />
                        <a-select v-model:value="form[f.key + '_unit']" style="width:76px">
                          <a-select-option v-for="u in f.unitOptions || ['g', 'kg']" :key="u" :value="u">{{ u }}</a-select-option>
                        </a-select>
                      </div>
                      <!-- 下拉选择 -->
                      <a-select
                        v-else-if="f.type === 'select'"
                        v-model:value="form[f.key]"
                        :placeholder="f.placeholder || '请选择'"
                        style="width:100%"
                        @change="onSelectChange(f.key)"
                      >
                        <a-select-option v-for="o in f.options" :key="o" :value="o">{{ o }}</a-select-option>
                      </a-select>
                      <!-- 只读自动匹配 -->
                      <a-input
                        v-else-if="f.readonly"
                        v-model:value="form[f.key]"
                        :placeholder="f.placeholder || ''"
                        readOnly
                      />
                      <a-textarea
                        v-else-if="f.full"
                        v-model:value="form[f.key]"
                        :placeholder="f.placeholder || ''"
                        :rows="2"
                      />
                      <a-input
                        v-else
                        v-model:value="form[f.key]"
                        :placeholder="f.placeholder || ''"
                      />
                    </a-form-item>
                    <a-form-item v-if="isStabilitySource" label="稳定性时间点 *" class="full stability-binding-field">
                      <a-select
                        v-model:value="form.stability_timepoint"
                        placeholder="选择对应的稳定性时间点"
                        show-search
                        option-filter-prop="label"
                        style="width:100%"
                      >
                        <a-select-option
                          v-for="tp in stabilityTimepointOptions"
                          :key="tp.name"
                          :value="tp.name"
                          :label="formatStabilityTimepoint(tp)"
                        >
                          {{ formatStabilityTimepoint(tp) }}
                        </a-select-option>
                      </a-select>
                      <div class="select-hint">该时间点的业务检验结果将自动同步到稳定性结果与趋势。</div>
                    </a-form-item>
                  </div>
                </a-form>
              </div>
            </div>

            <!-- 联动规则说明 -->
            <div class="dynamic-note">
              <div class="note-title">联动规则</div>
              <ul>
                <li>样品类型下拉切换后，整张表单替换为该类型专属表单</li>
                <li>检验优先级下拉只影响排程与时限，不改变表单字段</li>
                <li>登记后关键字段锁定，修改走修订流程</li>
              </ul>
            </div>
          </div>

          <div class="sample-side">
            <div class="spec-match">
              <div class="k">已匹配质量标准</div>
              <div class="v mono">{{ form.specification || '—' }}</div>
              <div class="meta">{{ matchedSpec ? `版本 V${matchedSpec.version} · 状态 ${matchedSpec.status}` : '选择质量标准后自动载入' }}</div>
              <div class="meta">样品类型：{{ form.sample_type || '—' }} · {{ specItems.length }} 个检验项目</div>
            </div>

            <div class="panel spec-items">
              <div class="panel-head"><div><h3>检验项目快照</h3><div class="sub">登记后冻结标准与限度 · {{ specItems.length }} 项</div></div></div>
              <div class="panel-body">
                <a-table
                  :columns="specColumns"
                  :data-source="specItems"
                  :loading="specLoading"
                  size="small"
                  :pagination="false"
                  row-key="item"
                />
              </div>
            </div>
          </div>
        </div>
      </a-tab-pane>

      <a-tab-pane key="ledger" tab="样品台账">
        <div class="page-head">
          <div>
            <h1>样品台账</h1>
            <p>全部登记样品的状态跟踪</p>
          </div>
        </div>

        <div class="filter-bar">
          <a-input v-model:value="ledgerSearch" placeholder="搜索编号 / 物料 / 批号" allow-clear style="width:240px" />
          <a-select v-model:value="ledgerStatus" placeholder="全部状态" allow-clear style="width:140px">
            <a-select-option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</a-select-option>
          </a-select>
          <span class="pill muted total-pill">{{ filteredLedger.length }} 条样品</span>
        </div>

        <div class="panel">
          <div class="panel-body">
            <a-table
              :columns="ledgerColumns"
              :data-source="filteredLedger"
              :loading="ledgerLoading"
              size="small"
              row-key="sample_name"
              :pagination="{ pageSize: 20 }"
              @row-click="openDetail"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'sample_name'"><span class="mono link-text">{{ record.sample_name }}</span></template>
                <template v-else-if="column.key === 'batch_no'"><span class="mono">{{ record.batch_no }}</span></template>
                <template v-else-if="column.key === 'status'">
                  <span class="pill" :class="statusClass(record.status)">{{ record.status }}</span>
                </template>
                <template v-else-if="column.key === 'priority'">
                  <span class="pill" :class="priorityClass(record.priority)">{{ record.priority }}</span>
                </template>
                <template v-else-if="column.key === 'test_due_date'">
                  <span class="mono">{{ record.test_due_date || '—' }}</span>
                </template>
              </template>
            </a-table>
          </div>
        </div>
      </a-tab-pane>
    </a-tabs>

    <!-- 样品详情抽屉 -->
    <a-drawer
      :open="showDetail"
      :title="detailSample ? `样品详情 · ${detailSample.name}` : '样品详情'"
      width="480"
      @close="showDetail = false"
    >
      <div v-if="detailSample" class="detail-body">
        <div class="detail-section">
          <div class="detail-row"><span class="k">物料编码</span><span class="v mono">{{ detailSample.material_code || '—' }}</span></div>
          <div class="detail-row"><span class="k">物料名称</span><span class="v">{{ detailSample.material_name }}</span></div>
          <div class="detail-row"><span class="k">批号</span><span class="v mono">{{ detailSample.batch_no }}</span></div>
          <div class="detail-row"><span class="k">样品类型</span><span class="v">{{ detailSample.sample_type }}</span></div>
          <div class="detail-row"><span class="k">样品来源</span><span class="v">{{ detailSample.sample_source }}</span></div>
          <div v-if="detailSample.stability_timepoint" class="detail-row"><span class="k">稳定性时间点</span><span class="v mono">{{ detailSample.stability_timepoint }}</span></div>
          <div class="detail-row"><span class="k">质量标准</span><span class="v mono">{{ detailSample.specification }}</span></div>
          <div class="detail-row"><span class="k">状态</span><span class="v"><span class="pill" :class="statusClass(detailSample.status)">{{ detailSample.status }}</span></span></div>
          <div class="detail-row"><span class="k">请验人</span><span class="v mono">{{ detailSample.requestor }}</span></div>
          <div class="detail-row"><span class="k">备注</span><span class="v">{{ detailSample.remarks || '—' }}</span></div>
        </div>

        <div class="detail-section">
          <h4>检验任务</h4>
          <a-table
            :columns="detailTaskColumns"
            :data-source="detailTasks"
            size="small"
            :pagination="false"
            row-key="name"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
              <template v-else-if="column.key === 'status'">
                <span class="pill" :class="statusClass(record.status)">{{ record.status }}</span>
              </template>
            </template>
          </a-table>
        </div>

        <div class="detail-section">
          <h4>检测结果</h4>
          <a-table
            :columns="detailResultColumns"
            :data-source="detailResults"
            size="small"
            :pagination="false"
            row-key="name"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
              <template v-else-if="column.key === 'verdict'">
                <span class="pill" :class="verdictClass(record.verdict)">{{ record.verdict || '—' }}</span>
              </template>
              <template v-else-if="column.key === 'result_status'">
                <span class="pill" :class="statusClass(record.result_status)">{{ record.result_status }}</span>
              </template>
            </template>
          </a-table>
        </div>

        <div class="detail-section">
          <h4>COA 报告</h4>
          <a-table
            :columns="detailCoaColumns"
            :data-source="detailCoas"
            size="small"
            :pagination="false"
            row-key="name"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
              <template v-else-if="column.key === 'report_status'">
                <span class="pill" :class="statusClass(record.report_status)">{{ record.report_status }}</span>
              </template>
            </template>
          </a-table>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { registerSample, listDoctype, getDoc, runReport } from '@/api/lims'
import { schedule, type ScheduleRow } from '@/api/stability'

const route = useRoute()
const activeTab = ref(route.query.tab === 'ledger' ? 'ledger' : 'register')
const submitting = ref(false)
const specLoading = ref(false)
const ledgerLoading = ref(false)

const typeOptions = ['原材料', '包装材料', '中间体', '成品', '回收溶剂', '过程控制', '化学残留', '方法验证', '水']
const TYPE_FIELD_MAP: Record<string, { name: string; code?: string; batch?: string }> = {
  原材料: { name: 'material_name', code: 'material_code', batch: 'in_batch_no' },
  包装材料: { name: 'material_name', code: 'material_code', batch: 'in_batch_no' },
  中间体: { name: 'material_name', code: 'material_code', batch: 'batch_no' },
  成品: { name: 'material_name', code: 'material_code', batch: 'batch_no' },
  回收溶剂: { name: 'material_name', code: 'material_code', batch: 'batch_no' },
  过程控制: { name: 'process_name', batch: 'sampling_point' },
  化学残留: { name: 'equip_name', batch: 'clean_batch' },
  方法验证: { name: 'verify_item', batch: 'verify_batch' },
  水: { name: 'water_system', batch: 'sampling_point' },
}
const specifications = ref<{ name: string; status: string; version: string }[]>([])
const specItems = ref<{ item: string; limits: string; unit: string }[]>([])
const ledgerRows = ref<Record<string, unknown>[]>([])
const stabilityTimepoints = ref<ScheduleRow[]>([])

const ledgerSearch = ref('')
const ledgerStatus = ref('')
const statusOptions = ['已登记', '检验中', '检验完成', '已放行', '已拒绝', 'OOS锁定', '草稿']

const form = reactive<Record<string, any>>({
  sample_type: '成品',
  priority: '常规',
  material_code: '',
  material_name: '',
  batch_no: '',
  sample_source: '生产取样',
  stability_timepoint: '',
  specification: '',
  test_due_date: '',
  remarks: '',
  // 成品表单扩展字段
  batch_qty: null,
  batch_qty_unit: 'g',
  sample_qty: null,
  sample_qty_unit: 'g',
  request_dept: '',
  request_date: '',
  storage_cond: '',
  retain_qty: '',
  // 复验期/有效期至 日期精度（date=年-月-日 / month=年-月）
  expiry_date_picker: 'date',
  // 原材料表单扩展字段
  in_batch_no: '',
  origin_batch_no: '',
  producer: '',
  qty: null,
  qty_unit: '公斤',
  piece_qty: null,
  piece_qty_unit: '件',
})

// 每种样品类型一张完整表单（类型专属字段前端承载；提交时仅提交后端支持的通用字段）
interface TypeField {
  key: string
  label: string
  required?: boolean
  full?: boolean
  type?: 'select' | 'text' | 'date' | 'unit'
  options?: string[]
  unitOptions?: string[]
  readonly?: boolean
  picker?: string
  slashIfEmpty?: boolean
  placeholder?: string
}

interface TypeTemplate {
  title: string
  tag: string
  specHint: string
  fields: TypeField[]
}

const typeTemplates: Record<string, TypeTemplate> = {
  原材料: {
    title: '原材料检验表单',
    tag: '表单 · 原材料',
    specHint: '原材料',
    fields: [
      { key: 'material_name', label: '样品名称', required: true, placeholder: 'TEST-HBOS-M2-原料A-01' },
      { key: 'material_code', label: '物料代码', required: true, placeholder: 'TEST-HBOS-M2-RM-001' },
      { key: 'in_batch_no', label: '进厂批号', required: true, placeholder: 'TEST-HBOS-M2-RM-B2607' },
      { key: 'origin_batch_no', label: '原厂批号', required: true, placeholder: 'TEST-HBOS-M2-SB-20260712' },
      { key: 'supplier', label: '供货单位', required: true, placeholder: 'TEST-HBOS-M2-供应商-鲁南化工' },
      { key: 'producer', label: '生产单位', required: true, placeholder: 'TEST-HBOS-M2-生产商-齐鲁制药' },
      { key: 'qty', label: '数量', required: true, type: 'unit', unitOptions: ['公斤', '张', '个'], placeholder: '填写数量' },
      { key: 'piece_qty', label: '件数', required: true, type: 'unit', unitOptions: ['件'], placeholder: '填写件数' },
      { key: 'request_dept', label: '请验部门', required: true, placeholder: '如 质量控制部' },
      { key: 'request_date', label: '请验日期', required: true, type: 'date' },
      { key: 'expiry_date', label: '复验期/有效期至', required: true, type: 'date', picker: 'flex' },
      { key: 'specification', label: '质量标准', type: 'select', options: [] },
      { key: 'storage_cond', label: '储存条件', readonly: true, placeholder: '选择质量标准后自动匹配' },
      { key: 'retain_qty', label: '留样量', readonly: true, placeholder: '选择质量标准后自动匹配' },
      { key: 'remarks', label: '备注', full: true, placeholder: '登记备注' },
    ],
  },
  包装材料: {
    title: '包装材料检验表单',
    tag: '表单 · 包装材料',
    specHint: '包装材料',
    fields: [
      { key: 'material_name', label: '样品名称', required: true, placeholder: 'TEST-HBOS-M2-铝箔内包材-01' },
      { key: 'material_code', label: '物料代码', required: true, placeholder: 'TEST-HBOS-M2-PK-001' },
      { key: 'in_batch_no', label: '进厂批号', required: true, placeholder: 'TEST-HBOS-M2-PK-0612' },
      { key: 'origin_batch_no', label: '原厂批号', required: true, placeholder: 'TEST-HBOS-M2-SB-20260712' },
      { key: 'supplier', label: '供货单位', required: true, placeholder: 'TEST-HBOS-M2-供应商-华强包装' },
      { key: 'producer', label: '生产单位', required: true, placeholder: 'TEST-HBOS-M2-生产商-中包材料' },
      { key: 'qty', label: '数量', required: true, type: 'unit', unitOptions: ['个'], placeholder: '填写数量' },
      { key: 'piece_qty', label: '件数', required: true, type: 'unit', unitOptions: ['件'], placeholder: '填写件数' },
      { key: 'request_dept', label: '请验部门', required: true, placeholder: '如 质量控制部' },
      { key: 'request_date', label: '请验日期', required: true, type: 'date' },
      { key: 'expiry_date', label: '复验期/有效期至', type: 'date', picker: 'flex', slashIfEmpty: true, placeholder: '无则填 /' },
      { key: 'specification', label: '质量标准', type: 'select', options: [] },
      { key: 'remarks', label: '备注', full: true, placeholder: '登记备注' },
    ],
  },
  中间体: {
    title: '中间体检验表单',
    tag: '表单 · 中间体',
    specHint: '中间体',
    fields: [
      { key: 'material_name', label: '样品名称', required: true, placeholder: 'TEST-HBOS-M2-中间体A-01' },
      { key: 'batch_no', label: '样品批号', required: true, placeholder: 'TEST-HBOS-M2-INT-0728' },
      { key: 'material_code', label: '物料代码', placeholder: '无则填 /' },
      { key: 'batch_qty', label: '批/数量', required: true, type: 'unit', unitOptions: ['g', 'kg'], placeholder: '填写数量' },
      { key: 'sample_qty', label: '样品数量', required: true, type: 'unit', unitOptions: ['g', 'kg', 'ml'], placeholder: '填写数量' },
      { key: 'sample_source', label: '样品来源', required: true, type: 'select', options: ['生产取样', '中间站取样'] },
      { key: 'request_dept', label: '请验部门', required: true, placeholder: '如 质量控制部' },
      { key: 'prod_date', label: '生产日期', required: true, type: 'date' },
      { key: 'expiry_date', label: '复检期/有效期至', required: true, type: 'date', picker: 'flex' },
      { key: 'request_date', label: '请验日期', required: true, type: 'date' },
      { key: 'specification', label: '质量标准', type: 'select', options: [] },
      { key: 'storage_cond', label: '储存条件', readonly: true, placeholder: '选择质量标准后自动匹配' },
      { key: 'retain_qty', label: '留样量', readonly: true, placeholder: '选择质量标准后自动匹配' },
      { key: 'remarks', label: '备注', full: true, placeholder: '登记备注' },
    ],
  },
  成品: {
    title: '成品检验表单',
    tag: '表单 · 成品',
    specHint: '成品',
    fields: [
      { key: 'material_name', label: '样品名称', required: true, placeholder: 'TEST-HBOS-M2-成品片剂A-01' },
      { key: 'batch_no', label: '样品批号', required: true, placeholder: 'TEST-HBOS-M2-B240801' },
      { key: 'material_code', label: '物料代码', placeholder: '无则填 /' },
      { key: 'batch_qty', label: '批/数量', required: true, type: 'unit', unitOptions: ['g', 'kg'], placeholder: '填写数量' },
      { key: 'sample_qty', label: '样品数量', required: true, type: 'unit', unitOptions: ['g', 'kg', 'ml'], placeholder: '填写数量' },
      { key: 'sample_source', label: '样品来源', required: true, type: 'select', options: ['生产取样', '来样送检', '稳定性取样', '环境监测'] },
      { key: 'request_dept', label: '请验部门', required: true, placeholder: '如 质量控制部' },
      { key: 'prod_date', label: '生产日期', required: true, type: 'date' },
      { key: 'expiry_date', label: '复检期/有效期至', required: true, type: 'date', picker: 'flex' },
      { key: 'request_date', label: '请验日期', required: true, type: 'date' },
      { key: 'specification', label: '质量标准', type: 'select', options: [] },
      { key: 'storage_cond', label: '储存条件', readonly: true, placeholder: '选择质量标准后自动匹配' },
      { key: 'retain_qty', label: '留样量', readonly: true, placeholder: '选择质量标准后自动匹配' },
      { key: 'remarks', label: '备注', full: true, placeholder: '登记备注' },
    ],
  },
  回收溶剂: {
    title: '回收溶剂检验表单',
    tag: '表单 · 回收溶剂',
    specHint: '回收溶剂',
    fields: [
      { key: 'material_name', label: '样品名称', required: true, placeholder: 'TEST-HBOS-M2-回收溶剂-01' },
      { key: 'batch_no', label: '样品批号', required: true, placeholder: 'TEST-HBOS-M2-REC-0728' },
      { key: 'material_code', label: '物料代码', placeholder: '无则填 /' },
      { key: 'batch_qty', label: '批/数量', required: true, type: 'unit', unitOptions: ['g', 'kg'], placeholder: '填写数量' },
      { key: 'sample_qty', label: '样品数量', required: true, type: 'unit', unitOptions: ['g', 'kg', 'ml'], placeholder: '填写数量' },
      { key: 'sample_source', label: '样品来源', required: true, type: 'select', options: ['回收取样', '生产取样'] },
      { key: 'request_dept', label: '请验部门', required: true, placeholder: '如 质量控制部' },
      { key: 'prod_date', label: '生产日期', required: true, type: 'date' },
      { key: 'expiry_date', label: '复验期至', required: true, type: 'date', picker: 'flex' },
      { key: 'request_date', label: '请验日期', required: true, type: 'date' },
      { key: 'specification', label: '质量标准', type: 'select', options: [] },
      { key: 'remarks', label: '备注', full: true, placeholder: '登记备注' },
    ],
  },
  过程控制: {
    title: '过程控制检验表单',
    tag: '表单 · 过程控制',
    specHint: '过程控制',
    fields: [
      { key: 'process_name', label: '工序名称', required: true, placeholder: '制粒' },
      { key: 'sampling_point', label: '取样点', required: true, placeholder: '制粒机出口' },
      { key: 'sampling_time', label: '取样时间', required: true, placeholder: '2026-08-01 14:30' },
      { key: 'sampler', label: '取样人', required: true, placeholder: '王微检' },
      { key: 'control_item', label: '控制项目', required: true, placeholder: '水分 / 含量 / 粒度' },
      { key: 'sample_source', label: '样品来源', required: true, type: 'select', options: ['过程取样', '生产取样'] },
      { key: 'specification', label: '质量标准', required: true, type: 'select', options: [] },
      { key: 'test_due_date', label: '检验时限', placeholder: '选择日期' },
      { key: 'storage_cond', label: '储存条件', placeholder: '密闭、及时检验' },
      { key: 'default_retain_days', label: '默认留样天数', placeholder: '7 天' },
      { key: 'remarks', label: '样品说明', full: true, placeholder: '过程控制中间检验' },
    ],
  },
  化学残留: {
    title: '化学残留检验表单',
    tag: '表单 · 化学残留',
    specHint: '化学残留',
    fields: [
      { key: 'equip_name', label: '设备名称', required: true, placeholder: '制粒机-01' },
      { key: 'clean_batch', label: '清洁批号', required: true, placeholder: 'TEST-HBOS-M2-CV-008' },
      { key: 'sampling_point', label: '取样点', required: true, placeholder: '设备内壁-搅拌桨' },
      { key: 'sampler', label: '取样人', required: true, placeholder: '陈 QA' },
      { key: 'residue_substance', label: '残留物质', required: true, placeholder: '活性成分A' },
      { key: 'limit_std', label: '限度标准', required: true, placeholder: '≤ 10 ppm' },
      { key: 'sample_source', label: '样品来源', required: true, type: 'select', options: ['清洁验证', '过程取样'] },
      { key: 'specification', label: '质量标准', required: true, type: 'select', options: [] },
      { key: 'test_due_date', label: '检验时限', placeholder: '选择日期' },
      { key: 'storage_cond', label: '储存条件', placeholder: '密闭、及时检验' },
      { key: 'default_retain_days', label: '默认留样天数', placeholder: '按验证方案' },
      { key: 'remarks', label: '样品说明', full: true, placeholder: '清洁后化学残留检测' },
    ],
  },
  方法验证: {
    title: '方法验证表单',
    tag: '表单 · 方法验证',
    specHint: '方法验证',
    fields: [
      { key: 'verify_item', label: '验证项目', required: true, placeholder: '含量测定' },
      { key: 'verify_method', label: '验证方法', required: true, placeholder: '高效液相色谱法' },
      { key: 'verify_batch', label: '验证批次', required: true, placeholder: 'TEST-HBOS-M2-VAL-001' },
      { key: 'method_type', label: '方法类型', required: true, type: 'select', options: ['专属性', '线性', '准确度', '精密度', '耐用性', '检出限', '定量限'] },
      { key: 'verify_param', label: '验证参数', required: true, placeholder: '回收率 98-102%' },
      { key: 'sample_source', label: '样品来源', required: true, type: 'select', options: ['方法验证', '生产取样'] },
      { key: 'specification', label: '质量标准', required: true, type: 'select', options: [] },
      { key: 'test_due_date', label: '检验时限', placeholder: '选择日期' },
      { key: 'storage_cond', label: '储存条件', placeholder: '按验证方案' },
      { key: 'default_retain_days', label: '默认留样天数', placeholder: '按验证方案' },
      { key: 'remarks', label: '样品说明', full: true, placeholder: '分析方法验证' },
    ],
  },
  水: {
    title: '水系统检验表单',
    tag: '表单 · 水',
    specHint: '水',
    fields: [
      { key: 'water_system', label: '水系统名称', required: true, placeholder: '纯化水分配系统' },
      { key: 'sampling_point', label: '取样点', required: true, placeholder: '总送水口' },
      { key: 'sampling_time', label: '取样时间', required: true, placeholder: '2026-08-01 10:00' },
      { key: 'sampler', label: '取样人', required: true, placeholder: '王微检' },
      { key: 'monitor_group', label: '监测项目组', required: true, placeholder: '纯化水' },
      { key: 'sample_source', label: '样品来源', required: true, type: 'select', options: ['在线取样', '生产取样'] },
      { key: 'specification', label: '质量标准', required: true, type: 'select', options: [] },
      { key: 'test_due_date', label: '检验时限', placeholder: '选择日期' },
      { key: 'storage_cond', label: '储存条件', placeholder: '密闭、及时检验' },
      { key: 'default_retain_days', label: '默认留样天数', placeholder: '7 天' },
      { key: 'remarks', label: '样品说明', full: true, placeholder: '水系统定期监测' },
    ],
  },
}

const activeFields = computed(() => (typeTemplates[form.sample_type] || typeTemplates['成品']).fields)
const formPanelTitle = computed(() => (typeTemplates[form.sample_type] || typeTemplates['成品']).title)
const formPanelTag = computed(() => (typeTemplates[form.sample_type] || typeTemplates['成品']).tag)
const contextTemplate = computed(() => form.sample_type + '检验')
const isStabilitySource = computed(() => ['稳定性', '稳定性取样'].includes(form.sample_source))
const stabilityTimepointOptions = computed(() => stabilityTimepoints.value.filter((row) => ['待检测', '检测中'].includes(row.status)))

const matchedSpec = computed(() => specifications.value.find((s) => s.name === form.specification))

const filteredLedger = computed(() => {
  return ledgerRows.value.filter((r) => {
    const s = String(r.sample_name || '') + String(r.material_name || '') + String(r.batch_no || '')
    const matchSearch = !ledgerSearch.value || s.includes(ledgerSearch.value)
    const matchStatus = !ledgerStatus.value || r.status === ledgerStatus.value
    return matchSearch && matchStatus
  })
})

const specColumns = [
  { title: '项目', key: 'item', dataIndex: 'item' },
  { title: '限度', key: 'limits', dataIndex: 'limits' },
  { title: '单位', key: 'unit', dataIndex: 'unit', width: 60 },
]

const ledgerColumns = [
  { title: '样品编号', key: 'sample_name', dataIndex: 'sample_name', width: 190 },
  { title: '物料名称', key: 'material_name', dataIndex: 'material_name' },
  { title: '批号', key: 'batch_no', dataIndex: 'batch_no', width: 140 },
  { title: '类型', key: 'sample_type', dataIndex: 'sample_type', width: 110 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 110 },
  { title: '优先级', key: 'priority', dataIndex: 'priority', width: 80 },
  { title: '检验时限', key: 'test_due_date', dataIndex: 'test_due_date', width: 120 },
]

const detailTaskColumns = [
  { title: '任务号', key: 'name', width: 150 },
  { title: '项目', key: 'test_item', dataIndex: 'test_item' },
  { title: '状态', key: 'status', width: 90 },
]

const detailResultColumns = [
  { title: '记录号', key: 'name', width: 150 },
  { title: '判定', key: 'verdict', width: 80 },
  { title: '状态', key: 'result_status', width: 90 },
]

const detailCoaColumns = [
  { title: 'COA 编号', key: 'name', width: 170 },
  { title: '状态', key: 'report_status', width: 100 },
]

async function loadReferenceData() {
  try {
    const specs = await listDoctype('HBOS Specification', ['name', 'status', 'version'], {}, 50)
    specifications.value = specs as { name: string; status: string; version: string }[]
    // 为各类型模板补充质量标准下拉选项
    Object.values(typeTemplates).forEach((t) => {
      const f = t.fields.find((x) => x.key === 'specification')
      if (f) {
        f.options = specifications.value.map((s) => s.name)
        if (!f.options.length) f.options = []
      }
    })
    // 默认载入已生效质量标准
    const active = specifications.value.find((s) => s.status === '已生效')
    if (active) {
      form.specification = active.name
      await loadSpecItems(active.name)
    }
    const scheduleData = await schedule({ limit: 500 })
    stabilityTimepoints.value = scheduleData.rows || []
  } catch {
    message.warning('无法加载质量标准数据')
  }
}

function formatStabilityTimepoint(row: ScheduleRow) {
  const product = row.product_name || row.stability_sample || '稳定性样品'
  const batch = row.batch_no ? ` · 批号 ${row.batch_no}` : ''
  return `${product}${batch} · ${row.condition_type} · ${row.time_point_label}（${row.name}）`
}

function onSelectChange(key: string) {
  if (key === 'specification') loadSpecItems(form[key])
  if (key === 'sample_source' && !isStabilitySource.value) form.stability_timepoint = ''
}

// 切换样品类型：整表替换，重置类型专属字段并联动质量标准
async function onTypeChange(_val: string) {
  // 保留通用字段与优先级
  const keep = { priority: form.priority }
  Object.keys(form).forEach((k) => {
    if (!['sample_type', 'priority'].includes(k)) form[k] = ''
  })
  form.sample_type = _val
  form.priority = keep.priority
  form.sample_source = '生产取样'
  form.stability_timepoint = ''
  // 包装材料复验期默认 "/"（无则填 /）
  form.expiry_date = _val === '包装材料' ? '/' : ''
  // unit 字段默认单位（按类型）
  form.batch_qty_unit = 'g'
  form.sample_qty_unit = 'g'
  form.qty_unit = _val === '包装材料' ? '个' : '公斤'
  form.piece_qty_unit = '件'
  // 联动质量标准
  const active = specifications.value.find((s) => s.status === '已生效')
  if (active) {
    form.specification = active.name
    await loadSpecItems(active.name)
  } else {
    specItems.value = []
  }
}

async function loadSpecItems(specName: string) {
  specLoading.value = true
  try {
    const spec = await getDoc<any>('HBOS Specification', specName)
    const items = spec.items || []
    specItems.value = items.map((row: any) => ({
      item: row.item_name || row.test_item || row.item || '',
      limits: formatLimits(row),
      unit: row.unit || '—',
    }))
    // 自动匹配储存条件与留样量（只读，人员不可修改）
    if (['成品', '中间体', '原材料'].includes(form.sample_type)) {
      form.storage_cond = spec.storage_condition || ''
      form.retain_qty = spec.retain_sample_qty || ''
    }
  } catch {
    specItems.value = []
    form.storage_cond = ''
    form.retain_qty = ''
  } finally {
    specLoading.value = false
  }
}

// 切换复验期/有效期至的日期精度：年-月-日 ↔ 年-月
function toggleDateMode(key: string) {
  const modeKey = key + '_picker'
  form[modeKey] = form[modeKey] === 'month' ? 'date' : 'month'
  // 切换模式时清空已选值，避免格式冲突（slashIfEmpty 字段回到 "/"）
  const f = activeFields.value.find((x) => x.key === key)
  form[key] = f?.slashIfEmpty ? '/' : ''
}

// slashIfEmpty 字段：选择日期则替换 "/"，清空则回到 "/"
function onExpiryChange(f: TypeField, val: any) {
  form[f.key] = val ? val : '/'
}
function formatLimits(row: any): string {
  const type = row.limits_type
  if (type === '记录型') return '记录型'
  if (type === '上限' && row.upper_limit != null) return `≤ ${row.upper_limit}`
  if (type === '下限' && row.lower_limit != null) return `≥ ${row.lower_limit}`
  if (row.lower_limit != null && row.upper_limit != null) return `${row.lower_limit} - ${row.upper_limit}`
  return '—'
}

async function loadLedger() {
  ledgerLoading.value = true
  try {
    const res = await runReport('样品台账')
    ledgerRows.value = res.result || []
  } catch {
    ledgerRows.value = []
  } finally {
    ledgerLoading.value = false
  }
}

// 详情抽屉
const showDetail = ref(false)
const detailSample = ref<any>(null)
const detailTasks = ref<any[]>([])
const detailResults = ref<any[]>([])
const detailCoas = ref<any[]>([])

async function openDetail(row: any) {
  try {
    const [sample, tasks, results, coas] = await Promise.all([
      getDoc<any>('HBOS Sample', row.sample_name),
      listDoctype<any>('HBOS Sample Task', ['name', 'test_item', 'status'], { sample: row.sample_name }, 50),
      listDoctype<any>('HBOS Test Result', ['name', 'verdict', 'result_status'], { sample: row.sample_name }, 50),
      listDoctype<any>('HBOS COA', ['name', 'report_status'], { sample: row.sample_name }, 20),
    ])
    detailSample.value = sample
    detailTasks.value = tasks
    detailResults.value = results
    detailCoas.value = coas
    showDetail.value = true
  } catch {
    message.warning('无法加载样品详情')
  }
}

// 重置按钮：清空表单中用户填写的信息，保留决策条（样品类型/检验优先级）选择
function resetFields() {
  Object.keys(form).forEach((k) => {
    if (k !== 'sample_type' && k !== 'priority') form[k] = ''
  })
  form.sample_source = '生产取样'
  form.stability_timepoint = ''
  specItems.value = []
}

function resetForm() {
  Object.keys(form).forEach((k) => {
    if (k !== 'sample_type' && k !== 'priority') form[k] = ''
  })
  form.sample_type = typeOptions[0] || '成品'
  form.priority = '常规'
  form.sample_source = '生产取样'
  form.stability_timepoint = ''
  form.batch_qty_unit = 'g'
  form.sample_qty_unit = 'g'
  form.qty_unit = form.sample_type === '包装材料' ? '个' : '公斤'
  form.piece_qty_unit = '件'
  const active = specifications.value.find((s) => s.status === '已生效')
  if (active) {
    form.specification = active.name
    loadSpecItems(active.name)
  }
}

async function submitSample() {
  const fieldMap = TYPE_FIELD_MAP[form.sample_type] || {}
  const materialName = form[fieldMap.name || 'material_name'] || form.material_name
  const materialCode = form[fieldMap.code || 'material_code'] || form.material_code || materialName
  const batchNo = form[fieldMap.batch || 'batch_no'] || form.batch_no
  if (!materialName || !batchNo || !form.sample_type || !form.specification) {
    message.warning('请填写样品类型、样品名称、批号和质量标准')
    return
  }
  if (isStabilitySource.value && !form.stability_timepoint) {
    message.warning('稳定性取样必须选择对应的稳定性时间点')
    return
  }
  for (const field of activeFields.value) {
    if (field.required && !form[field.key]) {
      message.warning(`请填写${field.label}`)
      return
    }
  }
  if (['成品', '中间体'].includes(form.sample_type)) {
    if (!form.batch_qty || !form.sample_qty) {
      message.warning('请填写批/数量和样品数量')
      return
    }
    if (!form.request_dept || !form.prod_date || !form.expiry_date || !form.request_date) {
      message.warning('请填写请验部门、生产日期、复检期/有效期至和请验日期')
      return
    }
  }
  if (['原材料', '包装材料'].includes(form.sample_type)) {
    if (!form.material_code || !form.in_batch_no || !form.origin_batch_no || !form.supplier || !form.producer || !form.qty || !form.piece_qty) {
      message.warning('请填写物料代码、进厂批号、原厂批号、供货单位、生产单位、数量和件数')
      return
    }
    if (!form.request_dept || !form.request_date) {
      message.warning('请填写请验部门、请验日期')
      return
    }
    // 复验期/有效期至：包装材料非必填（无则填 /）
    if (form.sample_type === '原材料' && !form.expiry_date) {
      message.warning('请填写复验期/有效期至')
      return
    }
  }
  submitting.value = true
  try {
    const name = await registerSample({
      sample_type: form.sample_type,
      material_code: materialCode,
      material_name: materialName,
      batch_no: batchNo,
      sample_source: form.sample_source,
      stability_timepoint: form.stability_timepoint || undefined,
      specification: form.specification,
      priority: form.priority,
      test_due_date: form.test_due_date,
      remarks: form.remarks,
    })
    message.success(`样品登记成功：${name}`)
    resetForm()
    await loadLedger()
  } catch {
    // 错误已由拦截器提示
  } finally {
    submitting.value = false
  }
}

function priorityClass(p: string) {
  return { 特急: 'pill-danger', 加急: 'pill-warn', 常规: 'pill-info' }[p] || 'pill-muted'
}
function statusClass(s: string) {
  return {
    已批准: 'pill-pass', 检验中: 'pill-info', 待复核: 'pill-warn',
    'OOS 候选': 'pill-danger', 'OOS锁定': 'pill-danger', 已登记: 'pill-muted',
    已放行: 'pill-pass', 检验完成: 'pill-primary', 草稿: 'pill-muted',
    已提交: 'pill-info', 已复核: 'pill-warn', 已修订: 'pill-danger',
    已发布: 'pill-pass', 已审核: 'pill-info',
  }[s] || 'pill-muted'
}
function verdictClass(v: string) {
  return { 合格: 'pill-pass', 不合格: 'pill-danger', 不适用: 'pill-info' }[v] || 'pill-muted'
}

onMounted(async () => {
  await loadReferenceData()
  await loadLedger()
})
</script>

<style scoped>
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.page-head h1 { font-size: 20px; color: var(--ink); }
.page-head p { font-size: 12px; color: var(--muted); margin-top: 4px; }
.page-actions { display: flex; gap: 8px; }

.sample-layout { display: grid; grid-template-columns: 1.55fr 1fr; gap: 14px; align-items: start; }
.sample-main, .sample-side { display: grid; gap: 14px; min-width: 0; }

/* 固定决策条 */
.form-context {
  position: sticky; top: 72px; z-index: 12;
  background: linear-gradient(180deg, #ffffff 0%, #f6faf8 100%);
  border: 1px solid var(--line); border-left: 3px solid var(--primary);
  border-radius: var(--radius); padding: 14px 16px 15px;
  box-shadow: 0 8px 22px rgba(13,43,40,.08);
}
.context-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }
.context-title { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
.context-title .pin { font-size: 10px; font-weight: 600; color: var(--primary-strong); background: var(--primary-soft); padding: 2px 8px; border-radius: 10px; }
.context-sub { font-size: 11px; color: var(--muted); margin-top: 3px; }
.context-state { font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.context-state .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--pass); }
.context-controls { display: grid; grid-template-columns: 1fr auto; gap: 20px; align-items: end; }
.context-field label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 7px; }
.context-field .select-hint { font-size: 11px; color: var(--muted); margin-top: 5px; }
.context-field.priority-field { min-width: 220px; }

/* 类型专属表单 */
.type-panel .panel-body { padding: 16px; }
.type-form .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
.type-form .full { grid-column: 1 / -1; }
.type-form .unit-field { display: flex; gap: 6px; align-items: center; }
.type-form .unit-field .ant-input-number { width: auto; }
.type-form .flex-date { display: flex; gap: 6px; align-items: center; }
.type-form .flex-date .date-mode-btn { flex: 0 0 auto; color: var(--primary); font-size: 12px; }
.type-form .flex-date .slash-display {
  background: var(--surface-2); color: var(--muted);
  cursor: not-allowed; font-weight: 500;
}
.type-form :deep(.ant-form-item-label > label) { font-weight: 500; }
.type-form :deep(.ant-input[readonly]) { background: var(--surface-2); color: var(--muted); cursor: not-allowed; }

.dynamic-note { background: var(--surface-2); border: 1px dashed var(--line); border-radius: var(--radius); padding: 12px 14px; font-size: 11px; color: var(--muted); }
.dynamic-note .note-title { font-weight: 700; color: var(--ink); margin-bottom: 8px; }
.dynamic-note ul { padding-left: 16px; display: grid; gap: 5px; }

.panel { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); }
.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--line); }
.panel-head h3 { font-size: 14px; }
.panel-head .sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
.panel-body { padding: 16px; }
.panel.spec-items .panel-body { padding: 0; }
.spec-match { background: var(--primary-soft); border: 1px solid #bfe0d6; border-radius: var(--radius); padding: 14px 16px; }
.spec-match .k { font-size: 11px; color: var(--primary); font-weight: 600; }
.spec-match .v { font-size: 15px; font-weight: 700; color: var(--primary-strong); margin-top: 6px; }
.spec-match .meta { font-size: 11px; color: var(--muted); margin-top: 4px; }
.sample-side .spec-match .v { word-break: break-all; }

.filter-bar { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.total-pill { margin-left: auto; }
.link-text { color: var(--primary); cursor: pointer; }
.panel-body :deep(.ant-table) { font-size: 13px; cursor: pointer; }

.detail-body { font-size: 13px; }
.detail-section { margin-bottom: 20px; }
.detail-section h4 { font-size: 13px; color: var(--ink); margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }
.detail-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #eef2f0; font-size: 12px; }
.detail-row .k { color: var(--muted); }
.detail-row .v { color: var(--ink); font-weight: 500; text-align: right; }

@media (max-width: 1180px) {
  .sample-layout { grid-template-columns: 1fr; }
  .context-controls { grid-template-columns: 1fr; }
  .form-context { position: static; }
  .context-field.priority-field { min-width: 0; }
}
@media (max-width: 640px) {
  .type-form .form-grid { grid-template-columns: 1fr; }
  .page-head { flex-direction: column; align-items: flex-start; gap: 10px; }
}
</style>
