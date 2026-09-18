<template>
  <div class="page">
    <StbGateBanner />

    <div class="page-head">
      <div>
        <h1>变更 / 稳定性室 / 设备</h1>
        <p class="page-desc">变更实施落点、温湿度人工记录和故障影响范围</p>
      </div>
      <div class="page-actions">
        <a-button @click="changeOpen = true">
          <template #icon><FileTextOutlined /></template>
          登记变更
        </a-button>
        <a-button type="primary" @click="readingOpen = true">
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
        <div class="grid-2">
          <div class="panel" style="box-shadow: none; margin-bottom: 0">
            <div class="panel-head">
              <div>
                <div class="panel-title">变更实施清单</div>
                <div class="panel-sub">变更批准后，在受控入口落到新方案 / 新通知 / 新时间点</div>
              </div>
              <span class="pill pill-warn">2 项进行中</span>
            </div>
            <div class="panel-body no-pad">
              <a-table
                :columns="changeColumns"
                :data-source="CHANGES"
                size="small"
                row-key="name"
                :pagination="false"
                :scroll="{ x: 620 }"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'name'"><span class="mono">{{ record.name }}</span></template>
                  <template v-else-if="column.key === 'scope'">
                    <div class="stb-cell-strong">{{ record.scope }}</div>
                    <div class="dim">{{ record.scopeSub }}</div>
                  </template>
                  <template v-else-if="column.key === 'status'">
                    <span :class="toneClass(record.tone)">{{ record.status }}</span>
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <a-button type="link" size="small" @click="openChange(record)">查看</a-button>
                  </template>
                </template>
              </a-table>
            </div>
          </div>

          <div class="panel" style="box-shadow: none; margin-bottom: 0">
            <div class="panel-head">
              <div>
                <div class="panel-title">变更动作提示</div>
                <div class="panel-sub">当前原型只展示受控动作入口</div>
              </div>
            </div>
            <div class="panel-body">
              <div class="stb-risk-list">
                <div v-for="(h, i) in CHANGE_HINTS" :key="i" class="stb-risk-item">
                  <span class="stb-risk-mark" :class="hintMark(h.tone)"></span>
                  <div class="stb-risk-main">
                    <div class="stb-risk-title">{{ h.title }}</div>
                    <div class="stb-risk-sub">{{ h.sub }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 稳定性室 -->
      <div v-else-if="tab === 'room'" class="stb-tab-body">
        <div class="stb-three-col">
          <div v-for="r in ROOMS" :key="r.name" class="stb-room-card">
            <h3>{{ r.name }} · {{ r.label }}</h3>
            <div class="panel-sub" style="margin-bottom: 11px">{{ r.limits }}</div>
            <div class="stb-room-readings">
              <div class="stb-reading" :class="{ alert: r.over }">
                <label>温度</label><b>{{ r.temperature }}</b> <small>℃</small>
              </div>
              <div class="stb-reading">
                <label>湿度</label><b>{{ r.humidity }}</b> <small>%RH</small>
              </div>
            </div>
            <div class="stb-room-note" :class="{ 'danger-text': r.noteTone === 'danger' }">{{ r.note }}</div>
          </div>

          <div class="stb-room-card">
            <h3>记录完整性</h3>
            <div style="font-size: 27px; font-weight: 800; color: var(--ink)">
              {{ ROOM_INTEGRITY.rate }}<small style="font-size: 12px; color: var(--muted)">%</small>
            </div>
            <div class="panel-sub" style="margin-top: 8px">
              本月应记录 {{ ROOM_INTEGRITY.expected }} 条 · 缺卡 {{ ROOM_INTEGRITY.missing }} 条
            </div>
            <div class="progress-track" style="margin-top: 16px">
              <i class="green" :style="{ width: ROOM_INTEGRITY.rate + '%' }"></i>
            </div>
          </div>
        </div>

        <div class="panel" style="margin-top: 16px; box-shadow: none">
          <div class="panel-head">
            <div>
              <div class="panel-title">近期温湿度记录</div>
              <div class="panel-sub">手工记录，超限标记由业务规则派生</div>
            </div>
            <a-button size="small" type="primary" @click="readingOpen = true">新增记录</a-button>
          </div>
          <div class="panel-body no-pad">
            <a-table
              :columns="readingColumns"
              :data-source="ROOM_READINGS"
              size="small"
              row-key="time"
              :pagination="false"
              :scroll="{ x: 720 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'time'"><span class="mono">{{ record.time }}</span></template>
                <template v-else-if="column.key === 'room'"><span class="mono">{{ record.room }}</span></template>
                <template v-else-if="column.key === 'temperature'">
                  <span class="mono" :class="{ 'danger-text': record.over }">{{ record.temperature }}</span>
                </template>
                <template v-else-if="column.key === 'humidity'"><span class="mono">{{ record.humidity }}</span></template>
                <template v-else-if="column.key === 'status'">
                  <span :class="toneClass(record.tone)">{{ record.status }}</span>
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
                <div class="panel-sub">稳定性室关键设备与校准状态</div>
              </div>
              <a-button size="small" @click="toast('设备台账为只读原型')">台账</a-button>
            </div>
            <div class="panel-body">
              <div v-for="e in EQUIPMENT" :key="e.name" class="stb-equipment">
                <div class="stb-equip-icon"><MonitorOutlined /></div>
                <div class="stb-equip-main">
                  <div class="stb-equip-name">{{ e.name }} · {{ e.label }}</div>
                  <div class="stb-equip-sub">{{ e.sub }}</div>
                </div>
                <span :class="toneClass(e.tone)">{{ e.status }}</span>
              </div>
            </div>
          </div>

          <div class="panel" style="box-shadow: none; margin-bottom: 0">
            <div class="panel-head">
              <div>
                <div class="panel-title">故障影响范围</div>
                <div class="panel-sub">故障关闭前关联样品和时间点保持可见</div>
              </div>
              <span class="pill pill-danger">1 项待处理</span>
            </div>
            <div class="panel-body">
              <div class="stb-risk-item">
                <span class="stb-risk-mark red"></span>
                <div class="stb-risk-main">
                  <div class="stb-risk-title">{{ FAULT.title }}</div>
                  <div class="stb-risk-sub">{{ FAULT.sub }}</div>
                </div>
                <a-button type="link" size="small" @click="faultOpen = true">查看</a-button>
              </div>
              <div class="stb-notice" style="margin-top: 12px">{{ FAULT.note }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 变更实施详情 -->
    <a-drawer v-model:open="changeOpen" title="变更实施详情" :width="520" placement="right">
      <p class="stb-gate-sub">{{ activeChange?.name }} · {{ activeChange?.status }}</p>
      <template v-if="activeChange">
        <div class="stb-drawer-section">
          <h3>影响范围</h3>
          <div class="stb-drawer-kv">
            <div><label>变更类型</label><b>{{ activeChange.type }}</b></div>
            <div><label>当前状态</label><b><span :class="toneClass(activeChange.tone)">{{ activeChange.status }}</span></b></div>
            <div><label>影响产品</label><b>{{ activeChange.impactProduct }}</b></div>
            <div><label>影响时间点</label><b>{{ activeChange.impactPoints }}</b></div>
          </div>
        </div>
        <div class="stb-drawer-section">
          <h3>实施落点</h3>
          <div v-for="(l, i) in activeChange.landing" :key="i" class="stb-audit-line">
            <span class="stb-audit-dot"></span>
            <div><strong>{{ l.title }}</strong><span>{{ l.desc }}</span></div>
          </div>
        </div>
      </template>
      <template #footer>
        <a-button @click="changeOpen = false">关闭</a-button>
        <a-button type="primary" @click="changeOpen = false; toast('实施动作需由受控业务方法完成（原型）')">打开实施动作</a-button>
      </template>
    </a-drawer>

    <!-- 记录温湿度 -->
    <a-drawer v-model:open="readingOpen" title="记录稳定性室温湿度" :width="560" placement="right">
      <p class="stb-gate-sub">手工记录 · 当前原型入口</p>
      <div class="stb-drawer-section">
        <h3>记录信息</h3>
        <div class="stb-form-grid">
          <div class="stb-form-field">
            <label>稳定性室 *</label>
            <a-select v-model:value="reading.room" :options="roomOptions" style="width: 100%" />
          </div>
          <div class="stb-form-field">
            <label>记录时间 *</label>
            <a-input v-model:value="reading.time" />
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
            <label>备注</label>
            <a-textarea v-model:value="reading.remark" :rows="3" placeholder="超限或缺卡时填写评估说明" />
          </div>
        </div>
      </div>
      <div class="stb-notice">
        本板块只做手工记录；温湿度超限标记由规则派生，设备自动采集属于其他扩展范围。
      </div>
      <template #footer>
        <a-button @click="readingOpen = false">取消</a-button>
        <a-button type="primary" @click="saveReading">保存记录</a-button>
      </template>
    </a-drawer>

    <!-- 设备故障影响范围 -->
    <a-drawer v-model:open="faultOpen" title="设备故障影响范围" :width="520" placement="right">
      <p class="stb-gate-sub">{{ FAULT.title }}</p>
      <div class="stb-drawer-section">
        <h3>影响对象</h3>
        <div class="stb-drawer-kv">
          <div v-for="f in FAULT.fields" :key="f.label"><label>{{ f.label }}</label><b>{{ f.value }}</b></div>
        </div>
      </div>
      <div class="stb-drawer-section">
        <h3>处置清单</h3>
        <div v-for="(c, i) in FAULT.checklist" :key="i" class="stb-audit-line">
          <span class="stb-audit-dot amber"></span>
          <div><strong>{{ c.title }}</strong><span>{{ c.desc }}</span></div>
        </div>
      </div>
      <template #footer>
        <a-button @click="faultOpen = false">关闭</a-button>
        <a-button type="primary" @click="faultOpen = false; toast('评估动作需由受控业务方法完成（原型）')">登记评估</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { FileTextOutlined, MonitorOutlined, PlusOutlined } from '@ant-design/icons-vue'
import StbGateBanner from '@/components/stability/StbGateBanner.vue'
import {
  CHANGES, CHANGE_HINTS, EQUIPMENT, FAULT, ROOMS, ROOM_INTEGRITY, ROOM_READINGS,
  toneClass, type ChangeRow, type Tone,
} from '@/demo/stabilityDemo'

const tab = ref<'change' | 'room' | 'equipment'>('change')
const changeOpen = ref(false)
const readingOpen = ref(false)
const faultOpen = ref(false)
const activeChange = ref<ChangeRow | null>(null)

function openChange(row: ChangeRow) {
  activeChange.value = row
  changeOpen.value = true
}

function hintMark(tone: Tone): string {
  if (tone === 'danger') return 'red'
  if (tone === 'warn') return 'amber'
  return 'blue'
}

const changeColumns = [
  { title: '变更单', key: 'name', width: 175 },
  { title: '影响范围', key: 'scope', width: 240 },
  { title: '当前状态', key: 'status', width: 100 },
  { title: '责任人', key: 'owner', dataIndex: 'owner', width: 90 },
  { title: '操作', key: 'action', width: 80 },
]

const readingColumns = [
  { title: '记录时间', key: 'time', width: 170 },
  { title: '房间', key: 'room', width: 110 },
  { title: '温度', key: 'temperature', width: 100 },
  { title: '湿度', key: 'humidity', width: 100 },
  { title: '记录人', key: 'recorder', dataIndex: 'recorder', width: 90 },
  { title: '状态', key: 'status', width: 90 },
]

const reading = reactive({
  room: 'STB-RM-01 · 长期室',
  time: '2026-09-15 14:00',
  temperature: '24.9',
  humidity: '59.1',
  remark: '',
})
const roomOptions = ['STB-RM-01 · 长期室', 'STB-RM-02 · 加速室'].map((v) => ({ value: v, label: v }))

function saveReading() {
  readingOpen.value = false
  message.success('原型入口：温湿度记录未落库，正式动作需由受控业务方法完成')
}

function toast(msg: string) {
  message.success(msg)
}
</script>

<style scoped>
.stb-cell-strong { color: var(--ink); font-weight: 700; }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
</style>
