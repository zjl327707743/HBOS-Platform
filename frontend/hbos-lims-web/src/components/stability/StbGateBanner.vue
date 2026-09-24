<template>
  <!-- 稳定性板块顶部提示条：区分「已接入真实后端」与「仍为演示数据」两类视图 -->
  <div class="stb-gate-banner" :class="mode === 'live' ? 'is-live' : 'is-demo'">
    <component :is="mode === 'live' ? CheckCircleOutlined : AlertOutlined" class="stb-gate-icon" />
    <span class="stb-gate-text">
      <strong>{{ mode === 'live' ? '已接入真实后端' : '演示数据' }}</strong> · {{ text }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AlertOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'

const props = withDefaults(defineProps<{ mode?: 'live' | 'demo'; note?: string }>(), {
  mode: 'demo',
  note: '',
})

const DEFAULT_TEXT = {
  live: '本页数据来自 hb_lims_app 稳定性业务服务（R8A~R8D 后端全量交付）；操作受会话角色与后端校验约束。',
  demo: '本页数据为原型演示（TEST-HBOS-M2-STB-*），对应后端接口尚未接入。',
} as const

const text = computed(() => props.note || DEFAULT_TEXT[props.mode])
</script>

<style scoped>
.stb-gate-banner {
  display: flex;
  align-items: center;
  gap: 9px;
  border-radius: var(--radius);
  padding: 9px 13px;
  font-size: 12px;
  margin-bottom: 16px;
}
.stb-gate-banner.is-live {
  background: #eef9f5;
  border: 1px solid #c7e2d9;
  color: #35675d;
}
.stb-gate-banner.is-live .stb-gate-icon { color: #1c6558; }
.stb-gate-banner.is-live strong { color: #1c6558; }
.stb-gate-banner.is-demo {
  background: #fdf6ec;
  border: 1px solid #ecd9b4;
  color: #7a5a24;
}
.stb-gate-icon { font-size: 15px; flex: 0 0 15px; }
.stb-gate-banner.is-demo .stb-gate-icon { color: #a8762a; }
.stb-gate-banner.is-demo strong { color: #8a5a12; }
.stb-gate-text { flex: 1; min-width: 0; line-height: 1.5; }

@media (max-width: 640px) {
  .stb-gate-banner { align-items: flex-start; }
}
</style>
