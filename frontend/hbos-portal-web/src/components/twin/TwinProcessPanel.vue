<template>
  <section class="process-panel" aria-label="原理示教控制">
    <div class="process-title">
      <strong
        >{{ session.equipmentId }} · {{ definition.label }}
        <span>{{ current.label }}</span></strong
      >
      <button :aria-expanded="detailOpen" @click="detailOpen = !detailOpen">
        <InfoCircleOutlined aria-hidden="true" /> 步骤说明
      </button>
      <span v-if="comparison" class="compare-label"
        >演示对照 · 规范化进度
        {{ Math.round((session.time / definition.duration) * 100) }}%</span
      >
      <span v-else class="demo-badge">原理演示 / 非现场状态 / 非操作规程</span>
    </div>
    <nav class="steps" aria-label="跳转示教步骤">
      <button
        v-for="(step, i) in definition.steps"
        :key="step.id"
        :aria-current="step.id === current.id ? 'step' : undefined"
        @click="$emit('seek', step.start)"
      >
        <span>{{ String(i + 1).padStart(2, "0") }}</span
        >{{ step.label }}
      </button>
    </nav>
    <div class="playback">
      <button
        class="play"
        :disabled="!ready"
        :aria-label="session.paused ? '播放原理演示' : '暂停原理演示'"
        @click="$emit('toggle')"
      >
        <CaretRightOutlined
          aria-hidden="true"
          v-if="session.paused"
        /><PauseOutlined aria-hidden="true" v-else />{{
          session.paused ? "播放" : "暂停"
        }}
      </button>
      <button
        :disabled="!ready"
        aria-label="重播原理演示"
        @click="$emit('replay')"
      >
        <RedoOutlined aria-hidden="true" /><span class="replay-label"
          >重播</span
        >
      </button>
      <label class="timeline"
        ><span class="sr-only">演示进度（讲解节奏）</span
        ><input
          type="range"
          :disabled="!ready"
          min="0"
          :max="definition.duration"
          step="0.1"
          :value="session.time"
          @input="
            $emit('seek', Number(($event.target as HTMLInputElement).value))
          "
      /></label>
      <output
        >{{ session.time.toFixed(1) }} / {{ definition.duration }}s</output
      >
      <label class="speed"
        ><span class="sr-only">阅读速度</span
        ><select
          :value="session.speed"
          @change="
            $emit('speed', Number(($event.target as HTMLSelectElement).value))
          "
        >
          <option :value="0.5">0.5×</option>
          <option :value="1">1×</option>
          <option :value="2">2×</option>
        </select></label
      >
      <label class="follow"
        ><input
          type="checkbox"
          :checked="session.followCamera"
          @change="$emit('follow', ($event.target as HTMLInputElement).checked)"
        />跟随镜头</label
      >
      <button class="exit" @click="$emit('exit')">
        <CloseOutlined aria-hidden="true" />退出示教
      </button>
    </div>
    <aside v-if="detailOpen" class="lesson-detail" aria-label="当前步骤说明">
      <div class="detail-heading">
        <strong>{{ current.label }}</strong
        ><button aria-label="关闭步骤说明" @click="detailOpen = false">
          <CloseOutlined aria-hidden="true" />
        </button>
      </div>
      <dl>
        <dt>目的</dt>
        <dd>{{ current.purpose }}</dd>
        <dt>涉及对象</dt>
        <dd>{{ current.objects }}</dd>
        <dt>观察现象</dt>
        <dd>{{ current.observation }}</dd>
        <dt>依据等级</dt>
        <dd>{{ current.evidence }}</dd>
      </dl>
      <p v-if="session.topic === 'production' && current.id === 'wash'">
        当前：{{ wash.label }}
      </p>
      <p v-if="session.equipmentId === 'M606B' && current.id === 'dry'">
        M606B 供热方式的本轮依据与显示能力仍待核；这不表示实际设备没有夹套。
      </p>
      <div
        v-if="session.topic === 'jacket'"
        class="jacket-concept"
        aria-label="夹套传热概念，非空间布置"
      >
        <span>供水用途</span><span>夹套侧 ↔ 壁面传热</span><span>回水用途</span>
      </div>
      <p>
        手动操作立即接管镜头。秒数仅为阅读节奏；温度、压力、流量、阀位均未接入。
      </p>
    </aside>
  </section>
</template>
<script setup lang="ts">
import { computed, ref } from "vue";
import {
  CaretRightOutlined,
  PauseOutlined,
  RedoOutlined,
  CloseOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons-vue";
import type { DemoSession } from "@/types/twin";
import { washState } from "./process/process-hardware";
import { lessonAt, topics } from "./process/lessons";
const props = withDefaults(
  defineProps<{
    session: DemoSession;
    ready?: boolean;
    comparison?: boolean;
  }>(),
  { ready: true, comparison: false },
);
defineEmits<{
  seek: [time: number];
  toggle: [];
  replay: [];
  speed: [value: number];
  follow: [value: boolean];
  exit: [];
}>();
const detailOpen = ref(false);
const definition = computed(() => topics[props.session.topic ?? "production"]);
const current = computed(() =>
  lessonAt(props.session.topic ?? "production", props.session.time),
);
const wash = computed(() =>
  washState(Math.max(0, Math.min(1, (props.session.time - 24) / 12))),
);
</script>
<style scoped>
.process-panel {
  position: relative;
  flex: none;
  background: #f7fbf8;
  border-top: 1px solid #d4e2d9;
  padding: 10px 14px;
  display: grid;
  gap: 8px;
  color: #304b40;
}
.process-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.process-title strong {
  font-size: 14px;
  font-weight: 600;
}
.process-title strong span {
  margin-left: 10px;
  color: #257152;
}
.demo-badge,
.compare-label {
  margin-left: auto;
  font-size: 12px;
  color: #70623f;
}
.process-panel button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  border: 1px solid #d6e1db;
  border-radius: 7px;
  background: white;
  color: #3b5548;
  padding: 4px 10px;
  font-size: 14px;
  cursor: pointer;
}
.process-title button {
  min-height: 30px;
  font-size: 12px;
  padding: 3px 8px;
}
.steps {
  display: flex;
  gap: 6px;
}
.steps button {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
}
.steps button[aria-current="step"] {
  background: #dceee3;
  border-color: #7caa91;
  color: #205b40;
}
.steps span {
  font-size: 12px;
  color: #6c8276;
}
.playback {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.playback .play {
  background: #287453;
  border-color: #287453;
  color: white;
  min-width: 76px;
}
.timeline {
  flex: 1;
  min-width: 70px;
}
.timeline input {
  display: block;
  width: 100%;
  min-height: 36px;
  accent-color: #287453;
  cursor: pointer;
}
.playback output {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  white-space: nowrap;
  color: #587263;
}
.speed select {
  min-height: 36px;
  border: 1px solid #d5e1d9;
  border-radius: 7px;
  background: white;
  color: #365944;
  font-size: 14px;
}
.follow {
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: 14px;
  white-space: nowrap;
}
.follow input {
  accent-color: #287453;
}
.lesson-detail {
  position: absolute;
  z-index: 5;
  bottom: calc(100% + 10px);
  right: 14px;
  max-height: min(460px, 70vh);
  overflow: auto;
  width: min(480px, calc(100% - 28px));
  background: #fffffff7;
  border: 1px solid #b9d2c3;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 12px 30px #24493518;
  font-size: 16px;
  line-height: 1.65;
}
.detail-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.lesson-detail dl {
  display: grid;
  grid-template-columns: 74px 1fr;
  gap: 8px;
  margin: 12px 0;
}
.lesson-detail dt {
  font-size: 12px;
  color: #6a7d70;
  padding-top: 3px;
}
.lesson-detail dd {
  margin: 0;
}
.lesson-detail p {
  font-size: 12px;
  line-height: 1.7;
  color: #6c735d;
}
.jacket-concept {
  display: flex;
  gap: 8px;
  justify-content: space-between;
  background: #eef6f0;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
button:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 3px solid #317858;
  outline-offset: 2px;
}
@media (max-width: 700px) {
  .process-panel {
    padding: 8px;
    gap: 6px;
  }
  .process-title {
    gap: 5px;
    flex-wrap: wrap;
  }
  .process-title strong {
    flex: 1;
    font-size: 14px;
  }
  .demo-badge,
  .compare-label {
    width: 100%;
    font-size: 12px;
    margin-left: 0;
  }
  .steps {
    overflow: auto;
    gap: 4px;
  }
  .steps button {
    min-height: 34px;
    padding: 3px 7px;
    flex: none;
    font-size: 14px;
  }
  .steps span {
    display: none;
  }
  .playback {
    flex-wrap: wrap;
    gap: 6px;
  }
  .timeline {
    order: 8;
    flex-basis: calc(100% - 90px);
  }
  .playback output {
    order: 9;
  }
  .follow {
    font-size: 12px;
  }
  .playback .exit {
    margin-left: auto;
  }
  .playback .play {
    min-width: 66px;
  }
  .replay-label {
    display: none;
  }
  .lesson-detail {
    right: 8px;
    width: calc(100% - 16px);
    max-height: 60vh;
  }
  .jacket-concept {
    flex-wrap: wrap;
  }
}
</style>

<style scoped>
@media (min-width: 701px) {
  .process-panel {
    grid-template-columns: auto minmax(0, 1fr);
    column-gap: 14px;
    row-gap: 7px;
    padding: 9px 12px;
  }
  .process-title {
    grid-column: 1;
  }
  .steps {
    grid-column: 2;
  }
  .playback {
    grid-column: 1/-1;
  }
  .demo-badge,
  .compare-label {
    display: none;
  }
  .process-title strong span {
    display: block;
    margin: 2px 0 0;
    font-size: 12px;
  }
  .process-title button {
    white-space: nowrap;
  }
  .steps button {
    min-height: 36px;
  }
  .process-title strong {
    font-size: 14px;
  }
}
@media (max-width: 700px) {
  .process-title .demo-badge,
  .process-title .compare-label {
    display: none;
  }
}
</style>
