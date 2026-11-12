<template>
  <section
    ref="viewport"
    class="twin-viewport"
    :aria-label="`${manifest.label} 受保护三维工作区`"
  >
    <div class="viewer-header">
      <div class="camera-tools" role="group" aria-label="镜头范围">
        <button :aria-pressed="viewIntent === 'overview'" @click="resetView">
          <HomeOutlined aria-hidden="true" />设备总览
        </button>
        <button
          :aria-pressed="viewIntent === 'engineering'"
          @click="engineeringView"
        >
          完整工程范围
        </button>
        <label class="model-view"
          ><span class="sr-only">模型视图，不表示现场方位</span
          ><select
            :value="viewDirection"
            @change="
              presetView(
                ($event.target as HTMLSelectElement).value as ViewDirection,
              )
            "
          >
            <option value="oblique">立体视图</option>
            <option value="front">正视</option>
            <option value="side">侧视</option>
            <option value="top">俯视</option>
          </select></label
        >
      </div>
      <div class="viewer-tools" role="toolbar" aria-label="三维查看工具">
        <button
          title="聚焦所选 (F)"
          aria-label="聚焦所选部件"
          :disabled="!hasSelection"
          @click="focusSelected"
        >
          <AimOutlined aria-hidden="true" />聚焦
        </button>
        <button title="复位视角 (R)" aria-label="复位镜头" @click="resetView">
          <RedoOutlined aria-hidden="true" />复位
        </button>
        <button aria-label="恢复全部显隐和材质" @click="restoreAll">
          <UndoOutlined aria-hidden="true" />恢复显示
        </button>
        <details class="more-tools">
          <summary><MoreOutlined aria-hidden="true" />更多</summary>
          <div>
            <button
              aria-label="隔离所选部件"
              :aria-pressed="isolated"
              :disabled="!hasSelection"
              @click="toggleIsolate"
            >
              <BorderOuterOutlined aria-hidden="true" />隔离所选
            </button>
            <button
              aria-label="隐藏所选部件"
              :disabled="!hasSelection"
              @click="hideSelected"
            >
              <EyeInvisibleOutlined aria-hidden="true" />隐藏所选
            </button>
            <button
              aria-label="切换线框"
              :aria-pressed="wireframe"
              @click="toggleWireframe"
            >
              <AppstoreOutlined aria-hidden="true" />线框
            </button>
          </div>
        </details>
      </div>
    </div>
    <div class="canvas-surface">
      <canvas
        ref="canvas"
        tabindex="0"
        :aria-label="`${manifest.label} 三维模型。拖动旋转，双指缩放，方向键旋转，F 聚焦，R 复位。非全屏时 Esc 清空选中，全屏时 Esc 退出模块全屏。`"
        @keydown="onKeydown"
      />
      <div class="viewport-label">
        <span class="source-dot"></span
        >{{
          comparison
            ? "M606B ↔ M607B · 演示对照，无现场联动"
            : session.equipmentId + " · " + viewLabel
        }}<small>{{
          session.mode === "browse"
            ? "无现场数据 · 几何适用性待核"
            : "原理演示 / 非现场状态 / 非操作规程"
        }}</small>
      </div>
      <div
        v-if="loading || error"
        class="viewer-state"
        role="status"
        aria-live="polite"
      >
        <strong>{{
          error ? "模型暂时不可用" : "正在校验并载入设备模型"
        }}</strong>
        <p>{{ error || "仅加载当前会话允许的私有制品" }}</p>
        <button v-if="error && !fatal" @click="loadModel">重试</button>
      </div>
      <div v-if="isolated" class="view-chip">
        隔离查看 · 几何候选 <button @click="restoreAll">恢复显示</button>
      </div>
      <div class="viewer-bottom">
        <span>拖动旋转 · 双指 / 滚轮缩放 · 点击选择</span
        ><span>展示拟合 · 非工程测量</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  HomeOutlined,
  AimOutlined,
  RedoOutlined,
  UndoOutlined,
  MoreOutlined,
  BorderOuterOutlined,
  EyeInvisibleOutlined,
  AppstoreOutlined,
} from "@ant-design/icons-vue";
import { lessonAt } from "./process/lessons";
import * as T from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type {
  DemoSession,
  ProcessBundle,
  ProcedureMode,
  TwinManifest,
  ViewerMetrics,
} from "@/types/twin";
import type { TwinScheduler } from "@/composables/twin/scheduler";
import {
  applySourcePresentation,
  DisplayState,
  disposeTree,
  effectiveVisible,
} from "./resources";
import { createProduction, type ProductionRuntime } from "./process/runtime";
import {
  boundedSample,
  sampleSummary,
  twinLifecycle,
} from "@/composables/twin/reviewMetrics";

const props = defineProps<{
  manifest: TwinManifest;
  process: ProcessBundle | null;
  session: DemoSession;
  scheduler: TwinScheduler;
  comparison?: boolean;
}>();
const emit = defineEmits<{
  select: [assetId: string | null];
  ready: [];
  fatal: [message: string];
  error: [message: string];
  manual: [];
  metrics: [value: ViewerMetrics];
  processError: [message: string];
  restore: [];
  contextLost: [];
}>();
const canvas = ref<HTMLCanvasElement | null>(null),
  viewport = ref<HTMLElement | null>(null);
const loading = ref(true),
  error = ref(""),
  fatal = ref(false),
  hasSelection = ref(false),
  isolated = ref(false),
  wireframe = ref(false);
let renderer: T.WebGLRenderer | null = null,
  scene: T.Scene | null = null,
  camera: T.PerspectiveCamera | null = null,
  controls: OrbitControls | null = null;
let root: T.Object3D | null = null,
  display: DisplayState | null = null,
  processRuntime: ProductionRuntime | null = null;
let otherRuntime: ProductionRuntime | null = null;
type ViewDirection = "oblique" | "front" | "side" | "top";
const viewIntent = ref<"overview" | "engineering" | "local">("overview"),
  viewDirection = ref<ViewDirection>("oblique");
const viewLabel = computed(() =>
  viewIntent.value === "overview"
    ? "设备总览"
    : viewIntent.value === "engineering"
      ? "完整工程范围"
      : "局部观察",
);
let localIds: string[] = [],
  lastStep = "",
  lastEffectTime: number | null = null;
let observer: ResizeObserver | null = null,
  abort: AbortController | null = null,
  generation = 0,
  disposed = false,
  dirty = true,
  userCamera = false;
let unsubscribe: (() => void) | null = null,
  parseMs = 0,
  downloadMs = 0,
  started = 0,
  firstVisibleMs: number | null = null;
let serverTiming: string | null = null,
  baseline = "",
  lastDemoFrame: number | null = null,
  lastMetrics = 0;
let recoveryTimer: ReturnType<typeof setTimeout> | null = null;
const picks: number[] = [],
  demoIntervals: number[] = [],
  renderSubmission: number[] = [];
function sourceSignature() {
  let hash = 2166136261;
  root?.traverse((n) => {
    const text = JSON.stringify([
      n.visible,
      n.matrix.elements,
      n instanceof T.Mesh
        ? (Array.isArray(n.material) ? n.material : [n.material]).map(
            (m) => m.uuid,
          )
        : [],
    ]);
    for (let i = 0; i < text.length; i++)
      hash = Math.imul(hash ^ text.charCodeAt(i), 16777619);
  });
  return (hash >>> 0).toString(16);
}
const nodes = new Map<string, T.Object3D>(),
  pointers = new Map<number, { x: number; y: number }>();
let gestureMoved = false;
const raycaster = new T.Raycaster(),
  pointer = new T.Vector2();
const original = {
  position: new T.Vector3(),
  target: new T.Vector3(),
  near: 0.01,
  far: 1000,
  fov: 38,
};
const invalidate = () => {
  dirty = true;
  props.scheduler.invalidate();
};
function selectedNodes() {
  return display ? [...display.selected] : [];
}
function syncTools() {
  hasSelection.value = Boolean(display?.selected.size);
  isolated.value = Boolean(display?.isolated);
  wireframe.value = Boolean(display?.wireframe);
}
function selectIds(ids: string[], notify = false) {
  display?.setSelection(
    ids.map((id) => nodes.get(id)).filter((n): n is T.Object3D => !!n),
  );
  syncTools();
  invalidate();
  if (notify) emit("select", ids[0] || null);
}
function clearSelection() {
  selectIds([], true);
}
function boxFor(objects: T.Object3D[]) {
  const box = new T.Box3();
  root?.updateWorldMatrix(true, true);
  for (const object of objects)
    object.traverse((n) => {
      if (!(n instanceof T.Mesh) || !effectiveVisible(n)) return;
      if (!n.geometry.boundingBox) n.geometry.computeBoundingBox();
      if (n.geometry.boundingBox)
        box.union(n.geometry.boundingBox.clone().applyMatrix4(n.matrixWorld));
    });
  return box;
}
function direction() {
  const front = new T.Vector3(
    ...(props.process?.bindings[props.session.equipmentId]?.front ?? [0, 0, 1]),
  ).normalize();
  if (viewDirection.value === "front") return front;
  if (viewDirection.value === "side")
    return front.applyAxisAngle(new T.Vector3(0, 1, 0), Math.PI / 2);
  if (viewDirection.value === "top") return new T.Vector3(0, 1, 0);
  return front
    .applyAxisAngle(new T.Vector3(0, 1, 0), 0.55)
    .add(new T.Vector3(0, 0.34, 0))
    .normalize();
}
function frameBox(box: T.Box3, padding = 1.16) {
  if (box.isEmpty() || !camera || !controls) return;
  const center = box.getCenter(new T.Vector3()),
    dir = direction();
  const up =
    viewDirection.value === "top"
      ? new T.Vector3(0, 0, -1)
      : new T.Vector3(0, 1, 0);
  const right = new T.Vector3().crossVectors(up, dir).normalize(),
    vertical = new T.Vector3().crossVectors(dir, right).normalize();
  const halfV = Math.tan(T.MathUtils.degToRad(camera.fov / 2)),
    halfH = halfV * camera.aspect;
  let distance = 0.01;
  for (const x of [box.min.x, box.max.x])
    for (const y of [box.min.y, box.max.y])
      for (const z of [box.min.z, box.max.z]) {
        const offset = new T.Vector3(x, y, z).sub(center),
          depth = offset.dot(dir);
        distance = Math.max(
          distance,
          depth + (padding * Math.abs(offset.dot(right))) / halfH,
          depth + (padding * Math.abs(offset.dot(vertical))) / halfV,
        );
      }
  camera.up.copy(up);
  camera.position.copy(center).addScaledVector(dir, distance);
  controls.target.copy(center);
  camera.near = Math.max(distance / 2000, 0.001);
  camera.far = Math.max(distance * 50, 100);
  camera.updateProjectionMatrix();
  controls.update();
  invalidate();
}
function idsBox(ids: string[]) {
  return boxFor(
    ids.map((id) => nodes.get(id)).filter((n): n is T.Object3D => !!n),
  );
}
function overviewIds() {
  const equipment =
    (props.manifest.entity_type === "scene" &&
      props.session.mode === "browse") ||
    props.comparison
      ? props.manifest.equipment_ids
      : [props.session.equipmentId];
  return equipment.flatMap(
    (eq) =>
      props.process?.camera_targets?.[eq]?.overview_ids ??
      props.process?.bindings[eq]?.ids ??
      [],
  );
}
function frameCurrent() {
  if (!root) return;
  if (viewIntent.value === "engineering") frameBox(boxFor([root]), 1.12);
  else if (viewIntent.value === "local") frameBox(idsBox(localIds), 1.18);
  else {
    const box = idsBox(overviewIds());
    frameBox(box.isEmpty() ? boxFor([root]) : box, 1.16);
  }
}
function resetView() {
  manual();
  userCamera = false;
  viewIntent.value = "overview";
  viewDirection.value = "oblique";
  frameCurrent();
}
function engineeringView() {
  manual();
  userCamera = false;
  viewIntent.value = "engineering";
  frameCurrent();
}
function presetView(value: ViewDirection) {
  manual();
  userCamera = false;
  viewDirection.value = value;
  frameCurrent();
}
function focusIds(ids: string[]) {
  if (!ids.length) return;
  localIds = ids;
  viewIntent.value = "local";
  frameCurrent();
}
function focusSelected() {
  manual();
  userCamera = false;
  focusIds(selectedNodes().map((n) => String(n.userData.asset_id)));
}
function toggleIsolate() {
  if (!display || !hasSelection.value) return;
  display.isolated = !display.isolated;
  display.apply();
  syncTools();
  invalidate();
}
function hideSelected() {
  if (!display) return;
  for (const n of display.selected) display.hidden.add(n);
  display.selected.clear();
  display.apply();
  syncTools();
  emit("select", null);
  invalidate();
}
function toggleWireframe() {
  if (!display) return;
  display.wireframe = !display.wireframe;
  display.apply();
  syncTools();
  invalidate();
}
function restoreAll() {
  exitProcess();
  emit("restore");
  display?.reset();
  syncTools();
  emit("select", null);
  resetView();
  invalidate();
}
function assetNode(object: T.Object3D) {
  let n: T.Object3D | null = object;
  while (n && n !== root?.parent) {
    if (typeof n.userData.asset_id === "string" && !n.userData.schematic_only)
      return n;
    n = n.parent;
  }
  return null;
}
function pointerDown(event: PointerEvent) {
  if (event.pointerType === "mouse" && event.button !== 0) return;
  if (!pointers.size) gestureMoved = false;
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  if (pointers.size > 1) gestureMoved = true;
}
function pointerMove(event: PointerEvent) {
  const start = pointers.get(event.pointerId);
  if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 6)
    gestureMoved = true;
}
function pointerCancel(event: PointerEvent) {
  pointers.delete(event.pointerId);
  gestureMoved = true;
}
function pointerUp(event: PointerEvent) {
  const start = pointers.get(event.pointerId),
    wasMultiple = pointers.size > 1;
  pointers.delete(event.pointerId);
  if (
    !start ||
    gestureMoved ||
    wasMultiple ||
    pointers.size ||
    !canvas.value ||
    !camera ||
    !root ||
    loading.value ||
    error.value
  )
    return;
  const r = canvas.value.getBoundingClientRect();
  pointer.set(
    ((event.clientX - r.left) / r.width) * 2 - 1,
    (-(event.clientY - r.top) / r.height) * 2 + 1,
  );
  raycaster.setFromCamera(pointer, camera);
  const picking = performance.now();
  const hit = raycaster
    .intersectObject(root, true)
    .find((h) => effectiveVisible(h.object));
  const node = hit ? assetNode(hit.object) : null;
  selectIds(node ? [String(node.userData.asset_id)] : [], true);
  boundedSample(picks, performance.now() - picking);
}
function manual() {
  userCamera = true;
  emit("manual");
}
function onKeydown(event: KeyboardEvent) {
  if (!camera || !controls) return;
  const key = event.key.toLowerCase();
  if (
    ![
      "r",
      "f",
      "escape",
      "+",
      "=",
      "-",
      "arrowleft",
      "arrowright",
      "arrowup",
      "arrowdown",
    ].includes(key)
  )
    return;
  if (key === "escape" && document.fullscreenElement) return;
  event.preventDefault();
  manual();
  if (key === "r") resetView();
  if (key === "f") focusSelected();
  if (key === "escape") clearSelection();
  if (["+", "=", "-"].includes(key)) {
    camera.position
      .sub(controls.target)
      .multiplyScalar(key === "-" ? 1.12 : 0.89)
      .add(controls.target);
    controls.update();
    invalidate();
  }
  if (key.startsWith("arrow")) {
    const offset = camera.position.clone().sub(controls.target),
      s = new T.Spherical().setFromVector3(offset);
    s.theta += key === "arrowleft" ? 0.12 : key === "arrowright" ? -0.12 : 0;
    s.phi = T.MathUtils.clamp(
      s.phi + (key === "arrowup" ? -0.12 : key === "arrowdown" ? 0.12 : 0),
      0.08,
      Math.PI - 0.08,
    );
    camera.position
      .copy(controls.target)
      .add(new T.Vector3().setFromSpherical(s));
    controls.update();
    invalidate();
  }
}
function exitProcess() {
  display?.restoreMaterials();
  otherRuntime?.dispose();
  processRuntime?.dispose();
  processRuntime = null;
  otherRuntime = null;
  display?.captureMaterials();
  display?.reset();
  syncTools();
  lastEffectTime = null;
  lastStep = "";
  invalidate();
}
function stepTargets() {
  const lesson = lessonAt(
      props.session.topic ?? "production",
      props.session.time,
    ),
    config = props.process?.bindings[props.session.equipmentId];
  if (!config) return [];
  if (lesson.camera === "supply")
    return props.process?.lessons?.jacket?.supply.ids ?? [];
  if (lesson.camera === "return")
    return props.process?.lessons?.jacket?.return.ids ?? [];
  if (lesson.camera === "attachment")
    return props.process?.lessons?.attachment?.ids ?? [];
  if (lesson.camera === "overview")
    return (
      props.process?.camera_targets?.[props.session.equipmentId]
        ?.overview_ids ?? config.ids
    );
  const kinds =
    lesson.camera === "cip"
      ? [
          "wash_supply_main",
          "wash_top_branch_1",
          "wash_top_branch_2",
          "wash_top_branch_3",
          "cip_return",
        ]
      : lesson.camera === "sip"
        ? ["steam_supply", "cip_return"]
        : lesson.camera === "feed"
          ? ["feed"]
          : lesson.camera === "vacuum"
            ? ["vacuum"]
            : lesson.camera === "discharge"
              ? ["discharge"]
              : [];
  return [
    ...new Set([
      ...config.ids,
      ...kinds.flatMap(
        (k) => config.network_groups[k]?.source_object_ids ?? [],
      ),
    ]),
  ];
}
function applyLessonStep(force = false) {
  if (props.session.mode === "browse" || !props.process) return;
  const step = lessonAt(
    props.session.topic ?? "production",
    props.session.time,
  );
  const key =
    props.session.equipmentId + ":" + props.session.topic + ":" + step.id;
  if (!force && lastStep === key) return;
  lastStep = key;
  if (["jacket", "attachment"].includes(props.session.topic)) {
    const ids = ["supply", "return", "vessel", "attachment"].includes(
      step.camera,
    )
      ? stepTargets()
      : [];
    selectIds(ids);
  }
  if (props.session.followCamera && !userCamera) {
    if (props.comparison) {
      viewIntent.value = "overview";
      frameCurrent();
    } else if (step.camera === "overview") {
      viewIntent.value = "overview";
      frameCurrent();
    } else {
      localIds = stepTargets();
      viewIntent.value = "local";
      frameCurrent();
    }
  }
}
function enterProcess() {
  exitProcess();
  if (!root || !props.process || props.session.mode !== "production") {
    if (!userCamera) {
      viewIntent.value = "overview";
      frameCurrent();
    }
    return;
  }
  const config = props.process.bindings[props.session.equipmentId];
  if (!config) {
    emit("processError", "当前设备尚无兼容的示教绑定。");
    return;
  }
  const topic = props.session.topic ?? "production";
  try {
    if (topic === "jacket") {
      for (const lesson of Object.values(props.process.lessons?.jacket ?? {})) {
        const parent = lesson.parent_id && nodes.get(lesson.parent_id),
          actual: string[] = [];
        if (!parent) throw new Error("Jacket candidate parent unavailable");
        parent.traverse((n) => {
          if (n instanceof T.Mesh) actual.push(String(n.userData.asset_id));
        });
        if (
          JSON.stringify(actual.sort()) !==
          JSON.stringify([...lesson.ids].sort())
        )
          throw new Error("Jacket candidate descendants changed");
      }
    }
    if (["filtration", "production", "cip", "sip"].includes(topic)) {
      processRuntime = createProduction(root, config);
      if (props.comparison) {
        const other = props.manifest.equipment_ids.find(
          (eq) => eq !== props.session.equipmentId,
        );
        const binding = other && props.process.bindings[other];
        if (!binding) throw new Error("Comparison binding unavailable");
        otherRuntime = createProduction(root, binding);
      }
      processRuntime.update(props.session.time, topic as ProcedureMode);
      otherRuntime?.update(props.session.time, topic as ProcedureMode);
    }
    display?.captureMaterials();
    syncTools();
    userCamera = !props.session.followCamera;
    applyLessonStep(true);
    invalidate();
  } catch {
    exitProcess();
    emit("processError", "示教目标或版本不兼容，静态模型仍可浏览。");
  }
}
function cleanupModel() {
  abort?.abort();
  abort = null;
  exitProcess();
  display?.dispose();
  display = null;
  if (root) {
    disposeTree(root);
    twinLifecycle.modelsDisposed++;
  }
  root = null;
  nodes.clear();
  hasSelection.value = false;
  isolated.value = false;
  wireframe.value = false;
}
async function loadModel() {
  const token = ++generation;
  cleanupModel();
  loading.value = true;
  error.value = "";
  fatal.value = false;
  started = performance.now();
  firstVisibleMs = null;
  lastMetrics = 0;
  lastDemoFrame = null;
  baseline = "";
  picks.length = 0;
  demoIntervals.length = 0;
  renderSubmission.length = 0;
  const controller = new AbortController();
  abort = controller;
  try {
    const response = await fetch(props.manifest.model_url, {
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
    });
    serverTiming = response.headers?.get("Server-Timing") ?? null;
    if (!response.ok) {
      if ([401, 403, 409].includes(response.status)) {
        fatal.value = true;
        throw new Error("设备权限、会话或模型完整性已失效。");
      }
      throw new Error("受保护模型暂时不可用，请重试。");
    }
    const data = await response.arrayBuffer();
    downloadMs = performance.now() - started;
    const digest = await crypto.subtle.digest("SHA-256", data);
    const hash = Array.from(new Uint8Array(digest), (b) =>
      b.toString(16).padStart(2, "0"),
    ).join("");
    if (
      hash !== props.manifest.model_sha256 ||
      data.byteLength !== props.manifest.model_size_bytes
    ) {
      fatal.value = true;
      throw new Error("模型完整性校验失败，已停止展示。");
    }
    const parsing = performance.now(),
      gltf = await new GLTFLoader().parseAsync(data, "");
    parseMs = performance.now() - parsing;
    if (disposed || token !== generation || !scene) {
      disposeTree(gltf.scene);
      return;
    }
    root = gltf.scene;
    applySourcePresentation(root);
    scene.add(root);
    display = new DisplayState(root);
    root.updateMatrixWorld(true);
    baseline = sourceSignature();
    root.traverse((n) => {
      if (typeof n.userData.asset_id === "string")
        nodes.set(n.userData.asset_id, n);
    });
    userCamera = false;
    viewIntent.value = "overview";
    frameCurrent();
    if (camera && controls) {
      original.position.copy(camera.position);
      original.target.copy(controls.target);
      original.near = camera.near;
      original.far = camera.far;
      original.fov = camera.fov;
    }
    loading.value = false;
    enterProcess();
    emit("ready");
    invalidate();
  } catch (reason) {
    if (disposed || token !== generation || controller.signal.aborted) return;
    loading.value = false;
    error.value = reason instanceof Error ? reason.message : "模型暂时不可用。";
    if (fatal.value) {
      cleanupModel();
      emit("fatal", error.value);
    } else emit("error", error.value);
  }
}
function resize() {
  if (!canvas.value || !renderer || !camera) return;
  const w = Math.max(canvas.value.clientWidth, 1),
    h = Math.max(canvas.value.clientHeight, 1);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  if (root && !userCamera) frameCurrent();
  invalidate();
}
function lost(event: Event) {
  event.preventDefault();
  generation++;
  cleanupModel();
  error.value = "图形上下文已丢失。恢复后将重新验证并载入。";
  loading.value = false;
  emit("contextLost");
  emit("error", error.value);
}
function recovered() {
  if (disposed) return;
  initializeRenderer();
  void loadModel();
}
function releaseRenderer() {
  controls?.removeEventListener("change", invalidate);
  controls?.removeEventListener("start", manual);
  controls?.dispose();
  controls = null;
  if (renderer) {
    renderer.dispose();
    twinLifecycle.renderersDisposed++;
  }
  renderer = null;
  scene = null;
  camera = null;
}
function initializeRenderer() {
  releaseRenderer();
  if (!canvas.value) return;
  renderer = new T.WebGLRenderer({
    canvas: canvas.value,
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;
  renderer.localClippingEnabled = true;
  twinLifecycle.renderersCreated++;
  scene = new T.Scene();
  scene.background = new T.Color("#edf2ef");
  scene.add(new T.HemisphereLight("#f3f7ff", "#6e7f91", 2.8));
  const light = new T.DirectionalLight("#ffffff", 3.8);
  light.position.set(6, 10, 8);
  scene.add(light);
  const fill = new T.DirectionalLight("#b3c7ef", 2);
  fill.position.set(-6, 4, -4);
  scene.add(fill);
  camera = new T.PerspectiveCamera(38, 1, 0.01, 1000);
  controls = new OrbitControls(camera, canvas.value);
  controls.enableDamping = false;
  controls.screenSpacePanning = true;
  controls.addEventListener("change", invalidate);
  controls.addEventListener("start", manual);
  resize();
}
watch(
  () => [
    props.session.mode,
    props.session.equipmentId,
    props.session.topic,
    props.process,
    props.comparison,
  ],
  enterProcess,
);
watch(
  () => props.session.followCamera,
  (follow) => {
    if (follow) {
      userCamera = false;
      applyLessonStep(true);
    }
  },
);
watch(
  () => props.session.time,
  () => {
    applyLessonStep();
    if (processRuntime) invalidate();
  },
);
watch(
  () => props.manifest.model_sha256,
  () => {
    void loadModel();
  },
);
onMounted(() => {
  initializeRenderer();
  const c = canvas.value!;
  c.addEventListener("pointerdown", pointerDown);
  c.addEventListener("pointermove", pointerMove);
  c.addEventListener("pointerup", pointerUp);
  c.addEventListener("pointercancel", pointerCancel);
  c.addEventListener("webglcontextlost", lost);
  c.addEventListener("webglcontextrestored", recovered);
  observer = new ResizeObserver(resize);
  observer.observe(c);
  unsubscribe = props.scheduler.subscribe((_dt, now) => {
    if (disposed || !renderer || !scene || !camera || error.value) return false;
    if (processRuntime && (lastEffectTime !== props.session.time || dirty)) {
      processRuntime.update(
        props.session.time,
        (props.session.topic ?? "production") as ProcedureMode,
      );
      otherRuntime?.update(
        props.session.time,
        (props.session.topic ?? "production") as ProcedureMode,
      );
      lastEffectTime = props.session.time;
      dirty = true;
    }
    applyLessonStep();
    const running = Boolean(processRuntime && !props.session.paused);
    if (running && lastDemoFrame !== null)
      boundedSample(demoIntervals, now - lastDemoFrame);
    lastDemoFrame = running ? now : null;
    if (dirty) {
      const submit = performance.now();
      renderer.render(scene, camera);
      boundedSample(renderSubmission, performance.now() - submit);
      dirty = false;
      if (root && !loading.value && firstVisibleMs === null)
        firstVisibleMs = performance.now() - started;
      const info = renderer.info;
      if (
        firstVisibleMs !== null &&
        (!running || !lastMetrics || now - lastMetrics >= 1000)
      ) {
        lastMetrics = now;
        emit("metrics", {
          geometries: info.memory.geometries,
          textures: info.memory.textures,
          triangles: info.render.triangles,
          calls: info.render.calls,
          downloadMs,
          parseMs,
          firstVisibleMs,
          ownedMaterials: display?.owned.size || 0,
        });
      }
    }
    return false;
  });
  void loadModel();
});
onBeforeUnmount(() => {
  disposed = true;
  generation++;
  unsubscribe?.();
  observer?.disconnect();
  pointers.clear();
  if (recoveryTimer !== null) clearTimeout(recoveryTimer);
  const c = canvas.value;
  if (c) {
    c.removeEventListener("pointerdown", pointerDown);
    c.removeEventListener("pointermove", pointerMove);
    c.removeEventListener("pointerup", pointerUp);
    c.removeEventListener("pointercancel", pointerCancel);
    c.removeEventListener("webglcontextlost", lost);
    c.removeEventListener("webglcontextrestored", recovered);
  }
  cleanupModel();
  releaseRenderer();
});
function reviewSnapshot() {
  const c = canvas.value,
    gl = renderer?.getContext(),
    debug = gl?.getExtension("WEBGL_debug_renderer_info"),
    rect = c?.getBoundingClientRect();
  root?.updateMatrixWorld(true);
  return {
    entry_id: props.manifest.entry_id,
    equipment_id: props.session.equipmentId,
    model_sha256: props.manifest.model_sha256,
    captured_at: new Date().toISOString(),
    browser: navigator.userAgent,
    hardware_concurrency: navigator.hardwareConcurrency,
    viewport: {
      width: innerWidth,
      height: innerHeight,
      client_width: document.documentElement.clientWidth,
      dpr: devicePixelRatio,
    },
    canvas: {
      css_width: rect?.width,
      css_height: rect?.height,
      buffer_width: c?.width,
      buffer_height: c?.height,
      quality_pixel_ratio_cap: 1.5,
      antialias: true,
    },
    graphics: gl
      ? {
          version: gl.getParameter(gl.VERSION),
          vendor: debug
            ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL)
            : gl.getParameter(gl.VENDOR),
          renderer: debug
            ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)
            : gl.getParameter(gl.RENDERER),
        }
      : null,
    load: {
      request_started_at_ms: started,
      download_ms: downloadMs,
      parse_ms: parseMs,
      model_request_to_first_render_ms: firstVisibleMs,
      server_timing: serverTiming,
    },
    pick_cpu: sampleSummary(picks),
    demo_frame_interval: sampleSummary(demoIntervals),
    render_cpu_submission: sampleSummary(renderSubmission),
    resources: renderer
      ? {
          ...renderer.info.memory,
          calls: renderer.info.render.calls,
          triangles: renderer.info.render.triangles,
          owned_materials: display?.owned.size || 0,
        }
      : null,
    lifecycle: {
      ...twinLifecycle,
      active_renderers:
        twinLifecycle.renderersCreated - twinLifecycle.renderersDisposed,
      active_demos: twinLifecycle.demosCreated - twinLifecycle.demosDisposed,
      active_schedulers:
        twinLifecycle.schedulersCreated - twinLifecycle.schedulersStopped,
    },
    scheduler: {
      listeners: props.scheduler.listenerCount,
      pending_frames: props.scheduler.pendingFrames,
    },
    source_state: {
      baseline_signature: baseline,
      current_signature: sourceSignature(),
      baseline_restored: baseline === sourceSignature(),
    },
    session: {
      mode: props.session.mode,
      topic: props.session.topic,
      time: props.session.time,
      paused: props.session.paused,
      speed: props.session.speed,
      follow_camera: props.session.followCamera,
      route: props.session.route,
    },
    camera: {
      intent: viewIntent.value,
      view: viewDirection.value,
      position: camera?.position.toArray(),
      target: controls?.target.toArray(),
      comparison: Boolean(props.comparison),
      framing: reviewFraming(),
    },
    schematic: processRuntime?.reviewState() ?? null,
    comparison_schematic: otherRuntime?.reviewState() ?? null,
    measurement_limit:
      "Frame intervals and CPU submission are browser observations, not GPU duration or a whole-memory leak proof.",
  };
}
function reviewFraming() {
  if (!root || !camera) return null;
  const ids = viewIntent.value === "local" ? localIds : overviewIds();
  const box = viewIntent.value === "engineering" ? boxFor([root]) : idsBox(ids);
  if (box.isEmpty()) return null;
  camera.updateMatrixWorld(true);
  const projected = new T.Box3();
  for (const x of [box.min.x, box.max.x])
    for (const y of [box.min.y, box.max.y])
      for (const z of [box.min.z, box.max.z])
        projected.expandByPoint(new T.Vector3(x, y, z).project(camera));
  return {
    target_count: viewIntent.value === "engineering" ? nodes.size : ids.length,
    projected_min: projected.min.toArray(),
    projected_max: projected.max.toArray(),
    targets_inside_canvas:
      projected.min.x >= -1.02 &&
      projected.max.x <= 1.02 &&
      projected.min.y >= -1.02 &&
      projected.max.y <= 1.02,
    meaning:
      "Camera target bounds only; local views may crop other context. Manual camera takeover may move targets outside the canvas.",
  };
}
function reviewGraphicsRecovery() {
  if (!props.manifest.review_only || !renderer || recoveryTimer !== null)
    return false;
  const extension = renderer.getContext().getExtension("WEBGL_lose_context");
  if (!extension) return false;
  extension.loseContext();
  recoveryTimer = setTimeout(() => {
    recoveryTimer = null;
    if (!disposed) extension.restoreContext();
  }, 600);
  return true;
}
defineExpose({
  selectIds,
  focusIds,
  focusSelected,
  toggleIsolate,
  hideSelected,
  restoreAll,
  resetView,
  engineeringView,
  reviewSnapshot,
  reviewGraphicsRecovery,
});
</script>

<style scoped>
.twin-viewport {
  display: flex;
  flex-direction: column;
  position: relative;
  min-width: 0;
  min-height: 0;
  height: 100%;
  background: #edf2ef;
  overflow: hidden;
}
.viewer-header {
  flex: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid #d9e3dc;
  background: #fafcfb;
  z-index: 3;
}
.camera-tools,
.viewer-tools {
  display: flex;
  gap: 5px;
  align-items: center;
  flex-wrap: wrap;
}
.viewer-header button,
.viewer-header summary,
.model-view select {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 34px;
  border: 1px solid #d3e0d8;
  background: white;
  color: #395648;
  border-radius: 7px;
  padding: 5px 9px;
  font-size: 14px;
  cursor: pointer;
}
.viewer-header button[aria-pressed="true"] {
  background: #e1efe7;
  border-color: #9cbea9;
}
.viewer-header button:disabled {
  opacity: 0.4;
  cursor: default;
}
.model-view select {
  max-width: 104px;
}
.more-tools {
  position: relative;
}
.more-tools summary {
  list-style: none;
}
.more-tools summary::-webkit-details-marker {
  display: none;
}
.more-tools > div {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  display: grid;
  min-width: 142px;
  gap: 6px;
  background: white;
  padding: 8px;
  border: 1px solid #cadbd1;
  border-radius: 9px;
  box-shadow: 0 8px 22px #2a44391a;
}
.canvas-surface {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
canvas {
  width: 100%;
  height: 100%;
  display: block;
  touch-action: none;
  cursor: grab;
}
canvas:active {
  cursor: grabbing;
}
canvas:focus-visible {
  outline: 3px solid #317858;
  outline-offset: -4px;
}
.viewport-label {
  position: absolute;
  top: 14px;
  left: 14px;
  max-width: calc(100% - 28px);
  padding: 8px 10px;
  background: #ffffffed;
  border: 1px solid #dce6df;
  border-radius: 8px;
  color: #345b45;
  font-size: 14px;
  pointer-events: none;
}
.viewport-label small {
  display: block;
  font-size: 12px;
  color: #697566;
  margin-top: 3px;
}
.source-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #a18542;
  margin-right: 6px;
}
.viewer-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #edf3efed;
  text-align: center;
  padding: 24px;
  gap: 12px;
  color: #385b49;
}
.viewer-state strong {
  font-size: 18px;
}
.viewer-state p {
  max-width: 360px;
  margin: 0;
  color: #6c7b70;
  font-size: 16px;
}
.viewer-state button,
.view-chip button {
  padding: 8px 14px;
  border: 1px solid #bdd0c4;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: 14px;
}
.viewer-bottom {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 10px;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: #667c6c;
  font-size: 12px;
  pointer-events: none;
}
.view-chip {
  position: absolute;
  bottom: 40px;
  left: 14px;
  padding: 6px 10px;
  background: white;
  border-radius: 8px;
  font-size: 14px;
  border: 1px solid #b8d2c2;
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
.viewer-header button:focus-visible,
.viewer-header select:focus-visible,
.viewer-header summary:focus-visible {
  outline: 3px solid #317858;
  outline-offset: 2px;
}
@media (max-width: 700px) {
  .viewer-header {
    padding: 6px;
    gap: 5px;
  }
  .viewer-header button,
  .viewer-header summary,
  .model-view select {
    min-height: 32px;
    padding: 4px 7px;
    font-size: 14px;
  }
  .viewport-label {
    top: 8px;
    left: 8px;
    padding: 5px 7px;
    font-size: 14px;
  }
  .viewport-label small {
    font-size: 12px;
  }
  .viewer-bottom {
    left: 8px;
    right: 8px;
    font-size: 12px;
  }
  .viewer-bottom > span:first-child {
    display: none;
  }
  .view-chip {
    bottom: 28px;
    left: 8px;
    padding: 4px 7px;
    font-size: 12px;
  }
  .view-chip button {
    padding: 5px 8px;
  }
}
</style>
