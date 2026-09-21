<template>
  <div class="page">
    <StbGateBanner mode="live"
              :note="'变更链 / 温湿度记录 / 设备与故障工单均来自 R8D 稳定性业务服务；变更实施为 7.9 单一原子事务，一般变更批准为 QA 经理专属、重大变更批准为 QP 专属。'" />

    <div class="page-head">
      <div>
        <h1>变更 / 稳定性室 / 设备</h1>
        <p class="page-desc">变更实施落点、温湿度人工记录和故障处理（真实后端）</p>
      </div>
      <div class="page-actions">
        <a-button v-if="can('create_change')" @click="changeCreateOpen = true">
          <template #icon><FileTextOutlined /></template>
          登记变更
        </a-button>
        <a-button v-if="can('log_room_env')" type="primary" @click="readingOpen = true">
          <template #icon><PlusOutlined /></template>
          记录温湿度
        </a-button>
      </div>
    </div>

    <div class="panel" style="margin-bottom: 16px">
      <div class="stb-tab-strip">
        <button :class="{ active: tab === 'change' }" @click="tab = 'change'">变更实施</button>
        <button :class="{ active: tab === 'room' }" @click="tab = 'room'">稳定性室</button>
        <button :class="{ active: tab === 'equipment' }" @click="tab = 'equipment'">设备与故障</button>
      </div>

      <!-- 变更实施 -->
      <div v-if="tab === 'change'" class="stb-tab-body">
        <div class="panel" style="box-shadow: none; margin-bottom: 0">
          <div class="panel-head">
            <div>
              <div class="panel-title">变更实施清单</div>
              <div class="panel-sub">批准后由实施动作在单一原子事务内落点（方案 7.9）</div>
            </div>
          </div>
          <div class="panel-body no-pad">
            <a-table
              :columns="changeColumns"
              :data-source="changeRows"
              :loading="changeLoading"
              size="small"
              row-key="name"
              :pagination="false"
              :scroll="{ x: 760 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
                <template v-else-if="column.key === 'scope'">
                  <div class="stb-cell-strong">{{ record.change_scope }}</div>
                  <div class="dim">{{ record.change_level }}变更{{ record.supersedes ? ' · 重启' : '' }}</div>
                </template>
                <template v-else-if="column.key === 'target'">
                  <span class="mono dim">{{ record.stability_sample || record.protocol || record.notice || '—' }}</span>
                </template>
                <template v-else-if="column.key === 'status'">
                  <span :class="toneClass(changeTone(record.status))">{{ record.status }}</span>
                </template>
                <template v-else-if="column.key === 'action'">
                  <a-space size="small">
                    <a-button type="link" size="small" @click="openChangeDetail(record)">详情</a-button>
                    <a-button v-if="can('submit_change') && record.status === '草稿'" type="link" size="small"
                              @click="runAction('提交变更', () => submitChange(record.name))">提交</a-button>
                    <a-button v-if="can('review_change') && record.status === '待QA审核'" type="link" size="small"
                              @click="runAction('审核变更', () => reviewChange(record.name))">审核</a-button>
                    <a-button v-if="can('approve_change_general') && record.status === '待QA经理批准'" type="link" size="small"
                              @click="runAction('批准一般变更', () => approveChangeGeneral(record.name))">批准</a-button>
                    <a-button v-if="can('approve_change_major') && record.status === '待QP批准'" type="link" size="small"
                              @click="runAction('批准重大变更', () => approveChangeMajor(record.name))">批准</a-button>
                    <a-button v-if="can('implement_change') && record.status === '已批准'" type="link" size="small"
                              @click="implementOpenFor(record)">实施</a-button>
                    <a-button v-if="can('assess_change') && record.status === '已实施'" type="link" size="small"
                              @click="assessOpenFor(record)">后评估</a-button>
                  </a-space>
                </template>
              </template>
            </a-table>
          </div>
        </div>
      </div>

      <!-- 稳定性室 -->
      <div v-else-if="tab === 'room'" class="stb-tab-body">
        <div class="panel" style="box-shadow: none">
          <div class="panel-head">
            <div>
              <div class="panel-title">温湿度记录</div>
              <div class="panel-sub">手工记录；同房间同日同班次仅一条；超标由控制器派生标记</div>
            </div>
            <a-select v-model:value="abnormalOnly" style="width: 130px"
                      :options="[{ value: 0, label: '全部记录' }, { value: 1, label: '仅超标' }]"
                      @change="loadRoomLogs" />
          </div>
          <div class="panel-body no-pad">
            <a-table
              :columns="readingColumns"
              :data-source="roomLogRows"
              :loading="roomLoading"
              size="small"
              row-key="name"
              :pagination="false"
              :scroll="{ x: 900 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'log_date'"><span class="mono">{{ record.log_date }} {{ record.period }}</span></template>
                <template v-else-if="column.key === 'room'"><span class="mono">{{ record.room }}</span></template>
                <template v-else-if="column.key === 'temperature'">
                  <span class="mono" :class="{ 'danger-text': isOver(record, 'temp') }">{{ record.temperature }}</span>
                </template>
                <template v-else-if="column.key === 'humidity'">
                  <span class="mono" :class="{ 'danger-text': isOver(record, 'humidity') }">{{ record.humidity }}</span>
                </template>
                <template v-else-if="column.key === 'within_spec'">
                  <span :class="record.within_spec ? 'good-text' : 'danger-text'">{{ record.within_spec ? '在控' : '超标' }}</span>
                </template>
              </template>
            </a-table>
          </div>
        </div>
      </div>

      <!-- 设备与故障 -->
      <div v-else class="stb-tab-body">
        <div class="grid-2">
          <div class="panel" style="box-shadow: none; margin-bottom: 0">
            <div class="panel-head">
              <div>
                <div class="panel-title">设备台账</div>
                <div class="panel-sub">校准 / 维护到期由 scheduler 每日扫描（≤30 天）</div>
              </div>
              <a-button v-if="can('manage_equipment')" size="small" @click="equipOpen = true">设备建档</a-button>
            </div>
            <div class="panel-body">
              <a-spin :spinning="equipLoading">
                <div v-for="e in equipRows" :key="e.name" class="stb-equipment">
                  <div class="stb-equip-icon"><MonitorOutlined /></div>
                  <div class="stb-equip-main">
                    <div class="stb-equip-name"><span class="mono">{{ e.name }}</span> · {{ e.equipment_name }}</div>
                    <div class="stb-equip-sub">
                      {{ e.room || '未分配房间' }} · 校准 {{ e.calibration_due || '—' }} · 维护 {{ e.maintenance_due || '—' }}
                    </div>
                  </div>
                  <span :class="toneClass(equipTone(e))">{{ e.status }}</span>
                </div>
                <a-empty v-if="!equipLoading && !equipRows.length" description="暂无设备台账" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 16px 0" />
              </a-spin>
            </div>
          </div>

          <div class="panel" style="box-shadow: none; margin-bottom: 0">
            <div class="panel-head">
              <div>
                <div class="panel-title">故障工单</div>
                <div class="panel-sub">关闭必须关联偏差或 CAPA（后端硬校验）</div>
              </div>
              <a-button v-if="can('open_fault_ticket')" size="small" type="primary" @click="faultOpen = true">报故障</a-button>
            </div>
            <div class="panel-body">
              <a-spin :spinning="faultLoading">
                <div v-for="f in faultRows" :key="f.name" class="stb-risk-item">
                  <span class="stb-risk-mark" :class="faultMark(f.status)"></span>
                  <div class="stb-risk-main">
                    <div class="stb-risk-title"><span class="mono">{{ f.name }}</span> · {{ f.description }}</div>
                    <div class="stb-risk-sub">
                      {{ f.equipment }} · {{ f.fault_start }}
                      <template v-if="f.affected_samples?.length"> · 影响 {{ f.affected_samples.length }} 个样品</template>
                    </div>
                  </div>
                  <a-space size="small">
                    <span :class="toneClass(faultTone(f.status))">{{ f.status }}</span>
                    <a-button v-if="can('start_fault_handling') && f.status === '待处理'" type="link" size="small"
                              @click="faultActionFor(f, 'start')">开始处理</a-button>
                    <a-button v-if="can('submit_fault_assessment') && f.status === '处理中'" type="link" size="small"
                              @click="faultActionFor(f, 'assess')">提交评估</a-button>
                    <a-button v-if="can('return_fault_handling') && f.status === '待评估'" type="link" size="small"
                              @click="runAction('退回处理', () => returnFaultHandling(f.name))">退回</a-button>
                    <a-button v-if="can('close_fault_ticket') && f.status !== '已关闭'" type="link" size="small" danger
                              @click="faultCloseFor(f)">关闭</a-button>
                  </a-space>
                </div>
                <a-empty v-if="!faultLoading && !faultRows.length" description="暂无故障工单" :image="Empty.PRESENTED_IMAGE_SIMPLE" style="padding: 16px 0" />
              </a-spin>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 变更详情抽屉 -->
    <a-drawer v-model:open="changeDetailOpen" title="变更详情" :width="560" placement="right">
      <template v-if="changeDoc">
        <p class="stb-gate-sub"><span class="mono">{{ changeDoc.name }}</span> · {{ changeDoc.status }}</p>
        <div class="stb-drawer-section">
          <h3>变更内容</h3>
          <div class="stb-drawer-kv">
            <div><label>落点</label><b>{{ changeDoc.change_scope }}</b></div>
            <div><label>级别</label><b>{{ changeDoc.change_level }}</b></div>
            <div><label>申请人</label><b>{{ changeDoc.applicant || '—' }} · {{ changeDoc.apply_date || '—' }}</b></div>
            <div><label>审核</label><b>{{ changeDoc.qa_review_by || '—' }} · {{ changeDoc.qa_review_date || '—' }}</b></div>
            <div><label>批准</label><b>{{ changeDoc.approver_by || '—' }} · {{ changeDoc.approve_date || '—' }}</b></div>
            <div v-if="changeDoc.supersedes"><label>替代</label><b class="mono">{{ changeDoc.supersedes }}</b></div>
          </div>
          <p style="margin-top: 10px; white-space: pre-wrap">{{ changeDoc.change_content }}</p>
          <p class="dim" style="white-space: pre-wrap">原因：{{ changeDoc.change_reason }}</p>
          <p class="dim" style="white-space: pre-wrap">影响评估：{{ changeDoc.impact_assessment }}</p>
        </div>
        <div class="stb-drawer-section" v-if="changeDoc.implement_record">
          <h3>实施记录</h3>
          <p style="white-space: pre-wrap">{{ changeDoc.implement_record }}</p>
          <p class="dim">{{ changeDoc.implement_by }} · {{ changeDoc.implement_date }}</p>
        </div>
        <div class="stb-drawer-section" v-if="changeDoc.post_assessment">
          <h3>后评估</h3>
          <p style="white-space: pre-wrap">{{ changeDoc.post_assessment }}</p>
          <p class="dim">{{ changeDoc.post_assessment_result }} · {{ changeDoc.post_assess_by }} · {{ changeDoc.post_assess_date }}</p>
        </div>
      </template>
      <template #footer>
        <a-button @click="changeDetailOpen = false">关闭</a-button>
      </template>
    </a-drawer>

    <!-- 登记变更 -->
    <a-drawer v-model:open="changeCreateOpen" title="登记变更" :width="560" placement="right">
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>变更落点 *</label>
          <a-select v-model:value="changeForm.change_scope" :options="scopeOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>变更级别 *</label>
          <a-select v-model:value="changeForm.change_level"
                    :options="[{ value: '一般', label: '一般（QA 经理批准）' }, { value: '重大', label: '重大（QP 批准）' }]"
                    style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>通知单</label>
          <a-input v-model:value="changeForm.notice" placeholder="HBOS-STB-NOT-..." />
        </div>
        <div class="stb-form-field">
          <label>方案</label>
          <a-input v-model:value="changeForm.protocol" placeholder="HBOS-STB-PRO-..." />
        </div>
        <div class="stb-form-field full">
          <label>稳定性样品</label>
          <a-input v-model:value="changeForm.stability_sample" placeholder="HBOS-STB-SMP-...（涉条件/涉样品必填）" />
        </div>
        <div class="stb-form-field full">
          <label>变更内容 *</label>
          <a-textarea v-model:value="changeForm.change_content" :rows="2" />
        </div>
        <div class="stb-form-field full">
          <label>变更原因 *</label>
          <a-textarea v-model:value="changeForm.change_reason" :rows="2" />
        </div>
        <div class="stb-form-field full">
          <label>影响评估 *</label>
          <a-textarea v-model:value="changeForm.impact_assessment" :rows="2" />
        </div>
        <div class="stb-form-field">
          <label>申请部门</label>
          <a-select v-model:value="changeForm.applicant_dept" :options="deptOptions" style="width: 100%" allow-clear />
        </div>
        <div v-if="changeForm.change_scope === '涉条件与时间点' || changeForm.change_scope === '涉方案'"
             class="stb-form-field full">
          <label>变更后考察条件</label>
          <div class="stb-change-condition-list">
            <div v-for="(row, index) in extraConditionRows" :key="index" class="stb-change-condition-row">
              <a-select v-model:value="row.condition_type" :options="conditionTypeOptions" style="width: 150px" />
              <a-select v-model:value="row.storage_cond" :options="conditionOptions" allow-clear
                        placeholder="储存条件" style="flex: 1" />
              <a-input-number v-if="row.condition_type === '影响因素-强光'"
                              v-model:value="row.exposure_days" :min="1" placeholder="天数"
                              style="width: 90px" />
              <a-button type="text" danger @click="removeExtraCondition(index)" aria-label="删除条件">
                <DeleteOutlined />
              </a-button>
            </div>
          </div>
          <a-button type="link" size="small" @click="addExtraCondition">
            <template #icon><PlusOutlined /></template>
            添加条件
          </a-button>
        </div>
      </div>
      <div class="stb-notice">落点与对象须匹配（涉方案须指定方案、涉通知单须指定通知单、涉条件/涉样品须指定样品）。</div>
      <template #footer>
        <a-button @click="changeCreateOpen = false">取消</a-button>
        <a-button type="primary" :loading="busy" @click="submitChangeCreate">建档</a-button>
      </template>
    </a-drawer>

    <!-- 实施变更 -->
    <a-modal v-model:open="implementOpen" title="实施变更（7.9 原子事务）" :confirm-loading="busy" @ok="confirmImplement">
      <div class="stb-form-field full">
        <label>实施记录 *</label>
        <a-textarea v-model:value="implementRecord" :rows="3" placeholder="落点回写说明；失败将整体回滚，变更单停留已批准" />
      </div>
      <div class="stb-notice amber">落点：涉方案→方案升版 / 涉通知单→新通知单 / 涉条件→锁内追加时间点 / 涉样品→请用「样品入箱」重新登记。</div>
    </a-modal>

    <!-- 后评估 -->
    <a-modal v-model:open="assessOpen" title="变更后评估" :confirm-loading="busy" @ok="confirmAssess">
      <div class="stb-form-field full">
        <label>后评估结论 *</label>
        <a-textarea v-model:value="assessForm.assessment" :rows="3" />
      </div>
      <div class="stb-form-field full">
        <label>评估结果 *</label>
        <a-select v-model:value="assessForm.result"
                  :options="[{ value: '达标', label: '达标' }, { value: '不达标需纠正', label: '不达标需纠正（本单终态，另立新单重启）' }]"
                  style="width: 100%" />
      </div>
    </a-modal>

    <!-- 记录温湿度 -->
    <a-drawer v-model:open="readingOpen" title="记录稳定性室温湿度" :width="560" placement="right">
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>稳定性房间 *</label>
          <a-select v-model:value="reading.room" :options="roomOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>记录日期 *</label>
          <a-input v-model:value="reading.log_date" placeholder="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>班次 *</label>
          <a-select v-model:value="reading.period" :options="[{ value: '上午', label: '上午' }, { value: '下午', label: '下午' }]" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>温度（℃） *</label>
          <a-input v-model:value="reading.temperature" />
        </div>
        <div class="stb-form-field">
          <label>湿度（%RH） *</label>
          <a-input v-model:value="reading.humidity" />
        </div>
        <div class="stb-form-field full">
          <label>异常描述（超标必填）</label>
          <a-textarea v-model:value="reading.exception_desc" :rows="2" />
        </div>
        <div class="stb-form-field full">
          <label>采取措施</label>
          <a-textarea v-model:value="reading.action_taken" :rows="2" />
        </div>
      </div>
      <div class="stb-notice">
        上下限从房间主数据快照、`within_spec` 由控制器判定；同房间同日同班次仅一条（业务键 unique）。
      </div>
      <template #footer>
        <a-button @click="readingOpen = false">取消</a-button>
        <a-button type="primary" :loading="busy" @click="saveReading">保存记录</a-button>
      </template>
    </a-drawer>

    <!-- 设备建档 -->
    <a-drawer v-model:open="equipOpen" title="设备建档" :width="560" placement="right">
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>设备名称 *</label>
          <a-select v-model:value="equipForm.equipment_name"
                    :options="['恒温恒湿箱', '医用冷藏箱', '强光照射试验箱', '其它'].map((v) => ({ value: v, label: v }))"
                    style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>所属房间</label>
          <a-select v-model:value="equipForm.room" :options="roomOptions" style="width: 100%" allow-clear />
        </div>
        <div class="stb-form-field">
          <label>位置</label>
          <a-input v-model:value="equipForm.location" />
        </div>
        <div class="stb-form-field">
          <label>状态 *</label>
          <a-select v-model:value="equipForm.status"
                    :options="['在用', '停用', '维修中'].map((v) => ({ value: v, label: v }))" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>确认状态</label>
          <a-select v-model:value="equipForm.qualification_status"
                    :options="['已确认', '待确认', '过期'].map((v) => ({ value: v, label: v }))"
                    style="width: 100%" allow-clear />
        </div>
        <div class="stb-form-field">
          <label>校准到期</label>
          <a-input v-model:value="equipForm.calibration_due" placeholder="YYYY-MM-DD" />
        </div>
        <div class="stb-form-field">
          <label>维护到期</label>
          <a-input v-model:value="equipForm.maintenance_due" placeholder="YYYY-MM-DD" />
        </div>
      </div>
      <div class="stb-notice">设备台账全状态禁删；退役用「停用」。</div>
      <template #footer>
        <a-button @click="equipOpen = false">取消</a-button>
        <a-button type="primary" :loading="busy" @click="submitEquipment">建档</a-button>
      </template>
    </a-drawer>

    <!-- 报故障 -->
    <a-drawer v-model:open="faultOpen" title="报设备故障" :width="560" placement="right">
      <div class="stb-form-grid">
        <div class="stb-form-field">
          <label>设备 *</label>
          <a-select v-model:value="faultForm.equipment" :options="equipOptions" style="width: 100%" />
        </div>
        <div class="stb-form-field">
          <label>故障开始 *</label>
          <a-input v-model:value="faultForm.fault_start" placeholder="YYYY-MM-DD HH:mm:ss" />
        </div>
        <div class="stb-form-field full">
          <label>故障描述 *</label>
          <a-textarea v-model:value="faultForm.description" :rows="3" />
        </div>
        <div class="stb-form-field full">
          <label>紧急措施</label>
          <a-textarea v-model:value="faultForm.emergency_action" :rows="2" />
        </div>
      </div>
      <div class="stb-notice">受影响样品可在工单详情中补充；开始处理时须填紧急措施。</div>
      <template #footer>
        <a-button @click="faultOpen = false">取消</a-button>
        <a-button type="primary" :loading="busy" @click="submitFault">建档</a-button>
      </template>
    </a-drawer>

    <!-- 通用文本输入弹窗 -->
    <a-modal v-model:open="textOpen" :title="textTitle" :confirm-loading="busy" @ok="confirmText">
      <a-textarea v-model:value="textValue" :rows="3" placeholder="必填" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Empty, message } from 'ant-design-vue'
import { DeleteOutlined, FileTextOutlined, MonitorOutlined, PlusOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import { useAuthStore } from '@/stores/auth'
import {
  approveChangeGeneral, approveChangeMajor, assessChange, canAction,
  changeDetail, changes, closeFaultTicket, createChange, equipments, faultTickets,
  implementChange, logRoomEnv, manageEquipment, openFaultTicket,
  returnFaultHandling, reviewChange, roomLogs, startFaultHandling, submitChange,
  submitFaultAssessment,
  type ChangeRow, type EquipmentRow, type FaultTicketRow, type RoomLogRow,
} from '@/api/stability'
import { toneClass } from '@/demo/stabilityDemo'
import { callMethod } from '@/api/client'

const auth = useAuthStore()
const can = (action: string): boolean => canAction(auth.user?.roles, action)
const busy = ref(false)

const tab = ref<'change' | 'room' | 'equipment'>('change')

// ---- 变更 ----

const changeRows = ref<ChangeRow[]>([])
const changeLoading = ref(false)
const changeDetailOpen = ref(false)
const changeDoc = ref<Record<string, any> | null>(null)

const changeColumns = [
  { title: '变更单', key: 'name', width: 170 },
  { title: '落点', key: 'scope', width: 150 },
  { title: '对象', key: 'target', width: 190 },
  { title: '状态', key: 'status', width: 120 },
  { title: '申请人', dataIndex: 'applicant', width: 130 },
  { title: '操作', key: 'action', width: 240 },
]

const scopeOptions = ['涉方案', '涉通知单', '涉条件与时间点', '涉样品'].map((v) => ({ value: v, label: v }))
const deptOptions = ['研发部门', '生产部门', '质量控制部门', '质量保证部门'].map((v) => ({ value: v, label: v }))
const conditionTypeOptions = ['长期', '加速', '中间', '影响因素-高温', '影响因素-高湿', '影响因素-强光']
  .map((v) => ({ value: v, label: v }))
const conditionMasterRows = ref<{ name: string; description?: string }[]>([])
const conditionOptions = computed(() => conditionMasterRows.value.map((row) => ({
  value: row.name,
  label: row.description ? `${row.description}（${row.name}）` : row.name,
})))
const extraConditionRows = ref<{ condition_type: string; storage_cond?: string; exposure_days?: number }[]>([
  { condition_type: '长期' },
])
function addExtraCondition() {
  extraConditionRows.value.push({ condition_type: '长期' })
}
function removeExtraCondition(index: number) {
  if (extraConditionRows.value.length === 1) {
    extraConditionRows.value[0] = { condition_type: '长期' }
    return
  }
  extraConditionRows.value.splice(index, 1)
}

async function loadChanges() {
  changeLoading.value = true
  try {
    const res = await changes({ limit: 200 })
    changeRows.value = res.rows
  } finally {
    changeLoading.value = false
  }
}

async function openChangeDetail(r: ChangeRow) {
  const res = await changeDetail(r.name)
  changeDoc.value = res.doc
  changeDetailOpen.value = true
}

function changeTone(status: string): 'pass' | 'warn' | 'muted' {
  if (status === '已批准' || status === '已实施' || status === '已评估完成') return 'pass'
  if (status === '已驳回' || status === '已取消' || status === '后评估不通过') return 'muted'
  return 'warn'
}

const changeCreateOpen = ref(false)
const changeForm = reactive({
  change_scope: '涉条件与时间点',
  change_level: '一般',
  notice: '',
  protocol: '',
  stability_sample: '',
  change_content: '',
  change_reason: '',
  impact_assessment: '',
  applicant_dept: undefined as string | undefined,
})
async function submitChangeCreate() {
  if (!changeForm.change_content.trim() || !changeForm.change_reason.trim()
      || !changeForm.impact_assessment.trim()) {
    message.warning('变更内容 / 原因 / 影响评估均必填'); return
  }
  const extraConditions = (changeForm.change_scope === '涉条件与时间点' || changeForm.change_scope === '涉方案')
    ? extraConditionRows.value.filter((row) => row.storage_cond).map((row) => ({
      condition_type: row.condition_type,
      storage_cond: row.storage_cond as string,
      exposure_days: row.exposure_days,
    }))
    : []
  if (changeForm.change_scope === '涉条件与时间点' && !extraConditions.length) {
    message.warning('请至少填写一条变更后考察条件'); return
  }
  await runAction('变更建档', async () => {
    await createChange({
      change_scope: changeForm.change_scope,
      change_level: changeForm.change_level,
      notice: changeForm.notice || undefined,
      protocol: changeForm.protocol || undefined,
      stability_sample: changeForm.stability_sample || undefined,
      change_content: changeForm.change_content.trim(),
      change_reason: changeForm.change_reason.trim(),
      impact_assessment: changeForm.impact_assessment.trim(),
      applicant_dept: changeForm.applicant_dept,
      extra_conditions: extraConditions.length ? extraConditions : undefined,
    })
    changeCreateOpen.value = false
    await loadChanges()
  })
}

const implementOpen = ref(false)
const implementRecord = ref('')
const implementTarget = ref<ChangeRow | null>(null)
function implementOpenFor(r: ChangeRow) {
  implementTarget.value = r
  implementRecord.value = ''
  implementOpen.value = true
}
async function confirmImplement() {
  const r = implementTarget.value
  if (!r) return
  if (!implementRecord.value.trim()) { message.warning('实施记录必填'); return }
  await runAction('实施变更', async () => {
    const res = await implementChange(r.name, implementRecord.value.trim())
    const result = res.result as { appended?: number; created?: string }
    message.info(result?.created ? `落点回写：${result.created}` : `追加 ${result?.appended ?? 0} 个时间点`)
    implementOpen.value = false
    await loadChanges()
  })
}

const assessOpen = ref(false)
const assessForm = reactive({ assessment: '', result: '达标' })
const assessTarget = ref<ChangeRow | null>(null)
function assessOpenFor(r: ChangeRow) {
  assessTarget.value = r
  assessForm.assessment = ''
  assessForm.result = '达标'
  assessOpen.value = true
}
async function confirmAssess() {
  const r = assessTarget.value
  if (!r) return
  if (!assessForm.assessment.trim()) { message.warning('后评估结论必填'); return }
  await runAction('后评估', async () => {
    await assessChange(r.name, assessForm.assessment.trim(), assessForm.result)
    assessOpen.value = false
    await loadChanges()
  })
}

// ---- 稳定性室 ----

const roomLogRows = ref<RoomLogRow[]>([])
const roomLoading = ref(false)
const abnormalOnly = ref(0)
const roomOptions = ref<{ value: string; label: string }[]>([])

const readingColumns = [
  { title: '日期 / 班次', key: 'log_date', width: 150 },
  { title: '房间', key: 'room', width: 170 },
  { title: '温度', key: 'temperature', width: 90 },
  { title: '温度上下限', key: 'temp_range', dataIndex: 'temp_range', width: 110 },
  { title: '湿度', key: 'humidity', width: 90 },
  { title: '湿度上下限', key: 'humidity_range', dataIndex: 'humidity_range', width: 110 },
  { title: '判定', key: 'within_spec', width: 80 },
  { title: '异常描述', dataIndex: 'exception_desc', width: 180 },
  { title: '检查人', dataIndex: 'checker', width: 140 },
]

async function loadRoomLogs() {
  roomLoading.value = true
  try {
    const res = await roomLogs({ only_abnormal: abnormalOnly.value, limit: 300 })
    roomLogRows.value = res.rows.map((r) => ({
      ...r,
      temp_range: r.temp_min != null ? `${r.temp_min} ~ ${r.temp_max}` : '—',
      humidity_range: r.humidity_min != null ? `${r.humidity_min} ~ ${r.humidity_max}` : '—',
    }))
  } finally {
    roomLoading.value = false
  }
}

function isOver(r: RoomLogRow, kind: 'temp' | 'humidity'): boolean {
  if (r.within_spec) return false
  if (kind === 'temp') return r.temp_min != null && (r.temperature < r.temp_min || r.temperature > (r.temp_max ?? r.temperature))
  return r.humidity_min != null && (r.humidity < r.humidity_min || r.humidity > (r.humidity_max ?? r.humidity))
}

const readingOpen = ref(false)
const reading = reactive({
  room: '', log_date: '', period: '上午', temperature: '', humidity: '',
  exception_desc: '', action_taken: '',
})
async function saveReading() {
  if (!reading.room) { message.warning('请选择房间'); return }
  const temperature = Number(reading.temperature)
  const humidity = Number(reading.humidity)
  if (Number.isNaN(temperature) || Number.isNaN(humidity)) { message.warning('温湿度须为数值'); return }
  await runAction('温湿度记录', async () => {
    await logRoomEnv({
      room: reading.room, log_date: reading.log_date.trim(), period: reading.period,
      temperature, humidity,
      exception_desc: reading.exception_desc || undefined,
      action_taken: reading.action_taken || undefined,
    })
    readingOpen.value = false
    await loadRoomLogs()
  })
}

// ---- 设备与故障 ----

const equipRows = ref<EquipmentRow[]>([])
const equipLoading = ref(false)
const faultRows = ref<FaultTicketRow[]>([])
const faultLoading = ref(false)

const equipOptions = computed(() =>
  equipRows.value.map((e) => ({ value: e.name, label: `${e.name} · ${e.equipment_name}` })))

async function loadEquipments() {
  equipLoading.value = true
  try {
    const res = await equipments()
    equipRows.value = res.rows
  } finally {
    equipLoading.value = false
  }
}

function equipTone(e: EquipmentRow): 'pass' | 'warn' | 'muted' | 'danger' {
  if (e.status === '停用') return 'muted'
  if (e.qualification_status === '过期') return 'danger'
  return 'pass'
}

async function loadFaults() {
  faultLoading.value = true
  try {
    const res = await faultTickets({ limit: 100 })
    faultRows.value = res.rows
  } finally {
    faultLoading.value = false
  }
}

function faultTone(status: string): 'pass' | 'warn' | 'muted' {
  if (status === '已关闭') return 'muted'
  return 'warn'
}

function faultMark(status: string): string {
  if (status === '已关闭') return 'gray'
  if (status === '待评估') return 'amber'
  return 'red'
}

const equipOpen = ref(false)
const equipForm = reactive({
  equipment_name: '恒温恒湿箱', room: undefined as string | undefined, location: '',
  status: '在用', qualification_status: undefined as string | undefined,
  calibration_due: '', maintenance_due: '',
})
async function submitEquipment() {
  await runAction('设备建档', async () => {
    await manageEquipment({
      equipment_name: equipForm.equipment_name,
      room: equipForm.room,
      location: equipForm.location || undefined,
      status: equipForm.status,
      qualification_status: equipForm.qualification_status,
      calibration_due: equipForm.calibration_due || undefined,
      maintenance_due: equipForm.maintenance_due || undefined,
    })
    equipOpen.value = false
    await loadEquipments()
  })
}

const faultOpen = ref(false)
const faultForm = reactive({ equipment: '', fault_start: '', description: '', emergency_action: '' })
async function submitFault() {
  if (!faultForm.equipment || !faultForm.description.trim()) { message.warning('设备与故障描述必填'); return }
  await runAction('故障建档', async () => {
    await openFaultTicket({
      equipment: faultForm.equipment,
      description: faultForm.description.trim(),
      fault_start: faultForm.fault_start || new Date().toISOString().slice(0, 19).replace('T', ' '),
      emergency_action: faultForm.emergency_action || undefined,
    })
    faultOpen.value = false
    await loadFaults()
  })
}

const textOpen = ref(false)
const textTitle = ref('')
const textValue = ref('')
let textFn: (() => Promise<unknown>) | null = null
function faultActionFor(f: FaultTicketRow, kind: 'start' | 'assess') {
  faultTarget.value = f
  if (kind === 'start') {
    textTitle.value = '开始处理（紧急措施必填）'
    textFn = () => startFaultHandling(f.name, textValue.value.trim())
  } else {
    textTitle.value = '提交风险评估'
    textFn = () => submitFaultAssessment(f.name, textValue.value.trim())
  }
  textValue.value = ''
  textOpen.value = true
}
const faultTarget = ref<FaultTicketRow | null>(null)
function faultCloseFor(f: FaultTicketRow) {
  faultTarget.value = f
  textTitle.value = '关闭故障工单（偏差 / CAPA 引用）'
  textFn = () => closeFaultTicket(f.name, textValue.value.trim() || undefined)
  textValue.value = ''
  textOpen.value = true
}
async function confirmText() {
  if (!textValue.value.trim()) { message.warning('内容必填'); return }
  const fn = textFn
  if (!fn) return
  await runAction(textTitle.value, async () => {
    await fn()
    textOpen.value = false
    await Promise.all([loadFaults(), loadEquipments()])
  })
}

const busyRef = busy
async function runAction(label: string, fn: () => Promise<unknown>) {
  busyRef.value = true
  try {
    await fn()
    message.success(`${label}已完成`)
  } catch {
    // 错误由 client 拦截层弹出（SoD / 越权 / 状态机 / 校验）
  } finally {
    busyRef.value = false
  }
}

onMounted(async () => {
  void auth.checkSession()
  // 房间与储存条件选项来自主数据白名单接口
  try {
    const [roomRes, conditionRes] = await Promise.all([
      callMethod<{ rows: { name: string; room_name?: string }[] }>(
      'hb_lims_app.hbos_lims.stability_service.get_stability_master',
      { doctype: 'HBOS Stability Room' }),
      callMethod<{ rows: { name: string; description?: string }[] }>(
        'hb_lims_app.hbos_lims.stability_service.get_stability_master',
        { doctype: 'HBOS Stability Condition' }),
    ])
    roomOptions.value = (roomRes.rows || []).map((r) => ({ value: r.name, label: r.room_name || r.name }))
    conditionMasterRows.value = conditionRes.rows || []
  } catch { /* 未登录等场景由拦截层提示 */ }
  await Promise.all([loadChanges(), loadRoomLogs(), loadEquipments(), loadFaults()])
})
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.good-text { color: var(--pass); }
.danger-text { color: var(--danger); }
.dim { color: var(--muted); font-size: 12px; }
.stb-change-condition-list { display: grid; gap: 8px; }
.stb-change-condition-row { display: flex; align-items: center; gap: 8px; }
</style>
