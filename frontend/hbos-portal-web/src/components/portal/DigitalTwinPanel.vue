<template>
  <section class="section-panel glass-surface twin-section">
    <div class="section-head twin-section-head">
      <div>
        <span class="section-kicker">运营空间 · DIGITAL TWIN</span>
        <h2>数字孪生运行态势</h2>
        <p>查看已授权的设备模型与关联知识；现场数据状态单独标注。</p>
      </div>
      <a-space>
        <a-tag :color="overviewTone">{{ overviewLabel }}</a-tag>
        <a-button type="primary" @click="openTwin">进入 3D 空间 <ArrowRightOutlined /></a-button>
      </a-space>
    </div>

    <div class="twin-layout twin-layout-enhanced">
      <div class="twin-canvas">
        <div class="twin-head">
          <strong>设备与工艺空间</strong>
          <span>{{ equipmentLabel }}</span>
        </div>

        <div class="twin-mode-switch">
          <button class="active">模型总览</button>
          <button disabled title="等待真实工艺数据接入">工艺流程</button>
          <button disabled title="等待真实设备状态接入">设备健康</button>
        </div>

        <svg viewBox="0 0 760 330" aria-label="数字孪生示意">
          <defs>
            <linearGradient id="twin-line-v53" x1="0" x2="1">
              <stop stop-color="#6c63ff"/>
              <stop offset=".55" stop-color="#49a7ff"/>
              <stop offset="1" stop-color="#48d5bd"/>
            </linearGradient>
            <radialGradient id="floor-glow" cx="50%" cy="50%" r="50%">
              <stop stop-color="#49a7ff" stop-opacity=".14"/>
              <stop offset="1" stop-color="#49a7ff" stop-opacity="0"/>
            </radialGradient>
          </defs>
          <ellipse cx="390" cy="220" rx="275" ry="105" fill="url(#floor-glow)"/>
          <g class="wire">
            <path d="M80 250 L300 118 L635 190 L410 307 Z"/>
            <path d="M300 118 L300 52 L635 126 L635 190"/>
            <path d="M80 250 L80 185 L300 52"/>
            <path d="M410 307 L410 238 L635 126"/>
            <path d="M80 185 L410 238 L635 126"/>
            <path d="M175 213 L175 147 M260 170 L260 82 M376 235 L376 147 M500 260 L500 165"/>
          </g>

          <path class="process-line" d="M150 218 L276 150 L422 195 L553 130"/>
          <circle cx="276" cy="150" r="8" fill="#6c63ff"/>
          <circle cx="422" cy="195" r="8" fill="#49a7ff"/>
          <circle cx="553" cy="130" r="8" fill="#48d5bd"/>

          <g class="machine violet">
            <rect x="232" y="105" width="72" height="104" rx="10"/>
            <ellipse cx="268" cy="105" rx="36" ry="11"/>
            <path d="M245 209 L245 230 M291 209 L291 230"/>
          </g>
          <g class="machine blue">
            <rect x="382" y="151" width="82" height="114" rx="10"/>
            <ellipse cx="423" cy="151" rx="41" ry="12"/>
            <path d="M397 265 L397 286 M450 265 L450 286"/>
          </g>
          <g class="machine green">
            <rect x="518" y="88" width="72" height="101" rx="10"/>
            <ellipse cx="554" cy="88" rx="36" ry="11"/>
            <path d="M531 189 L531 210 M578 189 L578 210"/>
          </g>
        </svg>

        <span class="node n1">{{ modelNode }}</span>
        <span class="node n2">{{ equipmentNode }}</span>
        <span class="node n3">{{ liveNode }}</span>
      </div>

      <div class="status-stack twin-status-stack">
        <template v-if="loading">
          <article v-for="index in 4" :key="`loading-${index}`" class="status-card twin-status-skeleton">
            <a-skeleton active :paragraph="false" />
          </article>
        </template>
        <article v-else-if="error" class="status-card twin-overview-message">
          <WarningOutlined />
          <div><strong>状态暂时不可用</strong><small>{{ error }}</small></div>
        </article>
        <template v-else>
          <article v-for="item in statuses" :key="item.id" class="status-card">
            <div>
              <span>{{ item.label }}</span>
              <strong :class="`tone-${item.tone || 'neutral'}`">{{ item.value }}</strong>
            </div>
            <a-progress
              v-if="item.progress !== undefined"
              :percent="item.progress"
              :show-info="false"
              stroke-color="#5f70f8"
            />
            <small v-else>{{ item.meta || '设备当前可用状态' }}</small>
          </article>
        </template>

        <button type="button" class="status-card twin-link-card" @click="openTwin">
          <div class="twin-link-icon"><NodeIndexOutlined /></div>
          <div>
            <strong>进入空间化操作</strong>
            <small>查看 M607B 私有模型，并从设备上下文进入受控知识检索。</small>
          </div>
          <ArrowRightOutlined />
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRightOutlined, NodeIndexOutlined, WarningOutlined } from '@ant-design/icons-vue'
import type { TwinStatusDTO } from '@/contracts/portal'

const props = withDefaults(defineProps<{
  statuses: TwinStatusDTO[]
  equipmentIds?: string[]
  loading?: boolean
  error?: string | null
}>(), {
  equipmentIds: () => [],
  loading: false,
  error: null,
})

const router = useRouter()
const statusMap = computed(() => new Map(props.statuses.map((status) => [status.id, status])))
const equipmentLabel = computed(() => props.equipmentIds.length
  ? `${props.equipmentIds.join(' / ')} · 当前账号授权范围`
  : '设备授权范围待确认')
const modelNode = computed(() => `私有模型 · ${statusMap.value.get('model')?.value || '待核'}`)
const equipmentNode = computed(() => props.equipmentIds.length ? `${props.equipmentIds[0]} · 授权范围` : '设备范围 · 待确认')
const liveNode = computed(() => `现场数据 · ${statusMap.value.get('live')?.value || '待核'}`)
const overviewLabel = computed(() => {
  if (props.loading) return '状态读取中'
  if (props.error) return '入口可用 · 状态待核'
  return props.equipmentIds.length ? '设备入口可用' : '设备范围待确认'
})
const overviewTone = computed(() => props.error ? 'warning' : props.loading ? 'processing' : 'success')

function openTwin() {
  void router.push('/hbos/twin')
}
</script>
