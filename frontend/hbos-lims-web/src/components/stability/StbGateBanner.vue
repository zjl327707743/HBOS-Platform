<template>
  <!-- 原型阶段固定提示条：稳定性板块所有视图顶部展示，说明数据为演示数据且 R8A 门禁未闭环 -->
  <div class="stb-gate-banner">
    <AlertOutlined class="stb-gate-icon" />
    <span class="stb-gate-text">
      <strong>前端复刻原型</strong> · {{ GATE_NOTE }}
    </span>
    <a-button type="link" size="small" @click="open = true">查看门禁</a-button>
  </div>

  <a-drawer v-model:open="open" title="R8A 启动前置确认门禁" :width="520" placement="right">
    <p class="stb-gate-sub">当前仍有 5 项待确认，原型不开放业务实施动作。</p>
    <div class="stb-gate-list">
      <div v-for="g in GATE_ITEMS" :key="g.code" class="stb-audit-line">
        <span class="stb-audit-dot amber"></span>
        <div>
          <strong>{{ g.code }} · {{ g.title }}</strong>
          <span>{{ g.desc }}</span>
        </div>
      </div>
    </div>
    <div class="stb-notice" style="margin-top: 14px">
      已确认：电子签名采用路线①「操作签名 + 审计追踪」；工作分支为新建
      <span class="mono">m2-r8</span>。
    </div>
    <template #footer>
      <a-button type="primary" @click="open = false">关闭提示</a-button>
    </template>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AlertOutlined } from '@ant-design/icons-vue'
import { GATE_ITEMS, GATE_NOTE } from '@/demo/stabilityDemo'

const open = ref(false)
</script>

<style scoped>
.stb-gate-banner {
  display: flex;
  align-items: center;
  gap: 9px;
  background: #eef9f5;
  border: 1px solid #c7e2d9;
  border-radius: var(--radius);
  padding: 9px 13px;
  font-size: 12px;
  color: #35675d;
  margin-bottom: 16px;
}
.stb-gate-icon { font-size: 16px; color: #1c6558; flex: 0 0 16px; }
.stb-gate-text { flex: 1; min-width: 0; line-height: 1.5; }
.stb-gate-text strong { color: #1c6558; }
.stb-gate-sub { font-size: 12px; color: var(--muted); margin-bottom: 12px; }
.stb-gate-list { display: flex; flex-direction: column; }

@media (max-width: 640px) {
  .stb-gate-banner { flex-wrap: wrap; align-items: flex-start; }
}
</style>
