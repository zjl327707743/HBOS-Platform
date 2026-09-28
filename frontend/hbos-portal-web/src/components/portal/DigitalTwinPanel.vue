<template>
  <section class="section-panel glass-surface twin-section">
    <div class="section-head twin-section-head">
      <div>
        <span class="section-kicker">运营空间 · DIGITAL TWIN</span>
        <h2>数字孪生运行态势</h2>
        <p>把设备、工艺与现场状态作为 HBOS 的空间化业务入口；有真实 Provider 时才展示实时数据。</p>
      </div>
      <a-space>
        <a-tag color="processing">LIVE READY</a-tag>
        <a-button type="primary">进入 3D 空间 <ArrowRightOutlined /></a-button>
      </a-space>
    </div>

    <div class="twin-layout twin-layout-enhanced">
      <div class="twin-canvas">
        <div class="twin-head">
          <strong>无菌生产区域</strong>
          <span>M606B / M607B · 数字孪生接口预留</span>
        </div>

        <div class="twin-mode-switch">
          <button class="active">运行态势</button>
          <button>工艺流程</button>
          <button>设备健康</button>
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

        <span class="node n1">M606B · 正常</span>
        <span class="node n2">M607B · 过滤阶段</span>
        <span class="node n3">环境 · 正常</span>
      </div>

      <div class="status-stack twin-status-stack">
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
          <small v-else>温湿度 / 压差 / 洁净区状态均在许可范围</small>
        </article>

        <article class="status-card twin-link-card">
          <div class="twin-link-icon"><NodeIndexOutlined /></div>
          <div>
            <strong>进入空间化操作</strong>
            <small>未来可从 3D 场景直接进入设备、工艺、维护和培训。</small>
          </div>
          <ArrowRightOutlined />
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ArrowRightOutlined, NodeIndexOutlined } from '@ant-design/icons-vue'
import type { TwinStatusDTO } from '@/contracts/portal'
defineProps<{ statuses: TwinStatusDTO[] }>()
</script>
