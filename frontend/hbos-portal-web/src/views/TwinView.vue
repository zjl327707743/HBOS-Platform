<template>
  <div class="twin-page">
    <header v-if="!manifest" class="twin-heading">
      <h1>设备与工艺</h1>
      <span>从真实设备出发，理解每一步。</span>
    </header>
    <div v-if="catalogLoading && !manifest" class="blank-state" role="status">
      正在读取受保护目录…
    </div>
    <div v-if="pageError" class="error-card" role="alert">
      <strong>{{ pageError }}</strong
      ><button @click="loadCatalog">重新核验</button>
    </div>
    <TwinCatalog
      v-if="catalog && !manifest"
      :entries="catalog.entries"
      :selected="selectedEntry"
      @choose="chooseEntry"
    />
    <div
      v-if="catalog && !catalog.entries.length && !pageError"
      class="blank-state"
    >
      当前会话没有可查看的设备。目录只显示允许访问的内容。
    </div>
    <div v-if="availability" class="blank-state" role="status">
      <h2>{{ availability }}</h2>
      <p>资产准备和分发确认分别记录，确认后在本工作区继续评审。</p>
      <button @click="loadCatalog">重新核验可用性</button>
    </div>
    <div v-if="entryLoading" class="blank-state" role="status">
      正在核验设备、成员与版本…
    </div>
    <section
      v-if="manifest && session"
      ref="moduleRoot"
      class="twin-module"
      :style="{ '--module-top': moduleTop + 'px' }"
      aria-label="设备与工艺模块工作区"
      @keydown="moduleKeydown"
    >
      <header class="module-heading">
        <TwinCatalog
          v-if="catalog"
          compact
          :entries="catalog.entries"
          :selected="selectedEntry"
          @choose="chooseEntry"
        />
        <span class="review-badge">完整 V1 候选 · 待 Owner 整体评审</span>
      </header>
      <div class="mode-bar">
        <div class="mode-tabs" aria-label="工作区模式">
          <button :aria-pressed="session.mode === 'browse'" @click="exitDemo">
            设备浏览</button
          ><button
            :aria-pressed="session.mode === 'production'"
            :disabled="!productionReady"
            @click="enterDemo"
          >
            生产示教
          </button>
        </div>
        <label v-if="manifest.equipment_ids.length > 1" class="device-select"
          >当前讲解设备<select
            :value="session.equipmentId"
            @change="
              chooseEquipment(($event.target as HTMLSelectElement).value)
            "
          >
            <option v-for="eq in manifest.equipment_ids" :key="eq">
              {{ eq }}
            </option>
          </select></label
        >
        <span v-else class="current-equipment">{{ session.equipmentId }}</span>
        <label v-if="session.mode === 'production'" class="topic-select"
          ><span class="sr-only">讲解专题</span
          ><select
            :value="session.topic"
            @change="
              chooseTopic(
                ($event.target as HTMLSelectElement).value as ProcessTopic,
              )
            "
          >
            <option
              v-for="topic in availableTopics"
              :key="topic"
              :value="topic"
            >
              {{ topics[topic].label }}
            </option>
          </select></label
        >
        <details v-if="session.mode === 'production'" class="lecture-options">
          <summary>{{ compareMode ? "对照中" : "路线 / 对照" }}</summary>
          <div class="lecture-bar">
            <label
              >预设讲解路线<select
                :value="session.route"
                :disabled="compareMode"
                @change="startRoute(($event.target as HTMLSelectElement).value)"
              >
                <option value="free">自由选择专题</option>
                <option
                  v-for="(r, key) in lectureRoutes"
                  :key="key"
                  :value="key"
                >
                  {{ r.label }}
                </option>
              </select></label
            >
            <button
              v-if="manifest.entity_type === 'scene'"
              :aria-pressed="compareMode"
              :disabled="!productionReady"
              @click="toggleCompare"
            >
              {{ compareMode ? "退出演示对照" : "进入演示对照" }}
            </button>
            <span>{{
              compareMode
                ? "仅演示进度同步；独立绑定，无现场联动。"
                : "设备与专题分别保留暂停进度。"
            }}</span>
          </div>
        </details>
        <div class="workspace-actions">
          <button :aria-expanded="partsOpen" @click="partsOpen = !partsOpen">
            <UnorderedListOutlined aria-hidden="true" /><span>目录</span>
          </button>
          <button :aria-expanded="infoOpen" @click="infoOpen = !infoOpen">
            <InfoCircleOutlined aria-hidden="true" /><span>版本</span>
          </button>
          <button class="knowledge-link" @click="openKnowledge">
            <ReadOutlined aria-hidden="true" /><span>知识 ↗</span>
          </button>
          <button
            class="fullscreen-trigger"
            aria-label="切换模块全屏"
            :aria-pressed="fullscreen.active.value"
            @click="fullscreen.toggle($event)"
          >
            <FullscreenExitOutlined
              aria-hidden="true"
              v-if="fullscreen.active.value"
            /><FullscreenOutlined aria-hidden="true" v-else /><span>{{
              fullscreen.active.value ? "退出全屏" : "全屏"
            }}</span>
          </button>
        </div>
      </div>

      <div v-if="fullscreen.notice.value" class="local-notice" role="status">
        {{ fullscreen.notice.value }}
      </div>
      <div
        v-if="processError || routeNotice"
        class="local-notice"
        role="status"
      >
        {{ processError || routeNotice }} 静态浏览继续可用。
      </div>
      <div v-if="knowledgeError" class="local-notice" role="status">
        {{ knowledgeError }} 设备浏览与示教继续可用。
      </div>
      <div class="twin-workspace" :class="{ 'with-parts': partsOpen }">
        <aside v-if="partsOpen" class="parts-panel" aria-label="候选部件目录">
          <div class="parts-heading">
            <strong>候选部件目录</strong
            ><button aria-label="折叠部件目录" @click="partsOpen = false">
              <CloseOutlined aria-hidden="true" />
            </button>
          </div>
          <label class="search-label"
            ><span class="sr-only">搜索当前目录</span
            ><input v-model="search" type="search" placeholder="搜索部件名称…"
          /></label>
          <p class="candidate-note">几何可定位 · 业务身份待核</p>
          <p v-if="partsError" class="local-error" role="status">
            {{ partsError }}
          </p>
          <div class="part-list">
            <section v-for="section in groupSections" :key="section.label">
              <h3 v-if="section.groups.length">{{ section.label }}</h3>
              <button
                v-for="group in section.groups"
                :key="group.group_id"
                :class="{ active: selectedGroup?.group_id === group.group_id }"
                @click="chooseGroup(group)"
              >
                <span>{{ group.label }}</span
                ><small>{{ group.asset_ids.length }} 个成员 · 候选</small>
              </button>
            </section>
          </div>
          <p
            v-if="!filteredGroups.length && !partsError"
            class="candidate-note"
          >
            没有匹配的当前成员。
          </p>
          <div class="parts-footer">
            来源名称保留。未知节点仅使用设备级知识上下文。
          </div>
        </aside>
        <div class="canvas-column">
          <TwinViewer
            :key="manifest.entry_id + ':' + manifest.model_sha256"
            ref="viewer"
            :manifest="manifest"
            :process="process"
            :session="session"
            :scheduler="scheduler"
            :comparison="compareMode"
            @select="selectAsset"
            @ready="onViewerReady"
            @fatal="failProtected"
            @manual="session.followCamera = false"
            @error="viewerError = $event"
            @metrics="onMetrics"
            @process-error="
              processError = $event;
              exitDemo();
            "
            @restore="exitDemo"
            @context-lost="onContextLost"
          />
          <aside
            v-if="mappingLoading || mapping || selectedGroup || mappingError"
            class="selection-panel"
            aria-label="所选部件信息"
            aria-live="polite"
          >
            <div class="selection-heading">
              <div>
                <small>{{
                  mapping?.status === "verified"
                    ? "已核部件"
                    : "几何选择 · 业务身份待核"
                }}</small
                ><strong>{{
                  mappingLoading
                    ? "正在核验当前节点…"
                    : mapping?.display_name ||
                      selectedGroup?.label ||
                      "映射暂时不可用"
                }}</strong>
              </div>
              <button
                :aria-expanded="!selectionCollapsed"
                aria-label="展开或收起部件说明"
                @click="selectionCollapsed = !selectionCollapsed"
              >
                <DownOutlined aria-hidden="true" />
              </button>
            </div>
            <template v-if="!selectionCollapsed"
              ><p>
                {{
                  mappingError ||
                  (mapping?.status === "verified"
                    ? "受控映射已核验；知识资料仍由知识模块授权。"
                    : "可进行几何观察。候选名称不表示已核业务身份。")
                }}
              </p>
              <small v-if="selectedGroup"
                >当前登记 {{ selectedGroup.asset_ids.length }} 个成员。</small
              ></template
            >
            <div class="selection-actions">
              <button @click="viewer?.focusSelected()">聚焦</button
              ><button @click="viewer?.toggleIsolate()">隔离</button
              ><button @click="viewer?.hideSelected()">隐藏</button
              ><button @click="clearSelection">清空</button>
            </div>
          </aside>
        </div>
      </div>
      <TwinProcessPanel
        v-if="session.mode === 'production'"
        :session="session"
        :ready="productionReady"
        :comparison="compareMode"
        @seek="seekTo"
        @toggle="togglePlay"
        @replay="replay"
        @speed="setSpeed"
        @follow="
          session.followCamera = $event;
          scheduler.invalidate();
        "
        @exit="exitDemo"
      />
      <footer v-else class="browse-note">
        <span>设备身份已确认 · 几何适用性待核 · 未接现场数据</span
        ><button :disabled="!productionReady" @click="enterDemo">
          进入原理示教
        </button>
      </footer>
      <section
        v-if="infoOpen"
        class="version-panel"
        aria-label="真实性与版本信息"
      >
        <div class="version-heading">
          <h3>依据、版本与评审状态</h3>
          <button aria-label="关闭信息面板" @click="infoOpen = false">
            <CloseOutlined aria-hidden="true" />
          </button>
        </div>
        <div class="truth-grid">
          <div><strong>设备身份</strong><span>Owner 已确认</span></div>
          <div>
            <strong>几何与外观</strong
            ><span>现场适用性待核；照片拟合非实测</span>
          </div>
          <div>
            <strong>内部与工艺</strong><span>程序原理示意，非操作规程</span>
          </div>
          <div>
            <strong>现场数据</strong><span>温度、压力、阀位均缺失</span>
          </div>
        </div>
        <dl>
          <dt>模型 SHA</dt>
          <dd>{{ manifest.model_sha256 }}</dd>
          <dt>模型 / 映射</dt>
          <dd>
            {{ manifest.model_revision }} / {{ manifest.mapping_revision }}
          </dd>
          <dt>过程 / 绑定</dt>
          <dd>
            {{ manifest.process_revision }} / {{ manifest.binding_revision }}
          </dd>
          <dt>镜头 / 演示</dt>
          <dd>
            {{ manifest.camera_revision }} / {{ manifest.demo_revision }} · seed
            {{ manifest.demo_seed }}
          </dd>
          <dt>知识 L1</dt>
          <dd>
            equipment_id、q、auto 既有入口；L2/L3 为 PENDING_KNOWLEDGE_CONTRACT
          </dd>
          <dt>批准与候选</dt>
          <dd>
            a2 合成私有批准保留；工程候选、Owner
            最终视觉、真实分发与发布分别待核/待批。
          </dd>
        </dl>
        <p>
          M606B
          不提供夹套专题是本轮依据与显示能力边界，不是实际设备无夹套的结论。顶部附件只沿已有候选几何观察。
        </p>
        <details class="review-metrics">
          <summary>本机私有验证数据</summary>
          <p>浏览器时序与资源计数，不表示 GPU 耗时或完整无泄漏证明。</p>
          <button @click="captureReviewSnapshot">生成本机验证快照</button
          ><button
            v-if="manifest.review_only"
            :disabled="!viewerReady"
            @click="reviewGraphicsRecovery"
          >
            检验本机图形恢复
          </button>
          <p v-if="graphicsReview" role="status">{{ graphicsReview }}</p>
          <pre v-if="reviewSnapshot" data-testid="twin-review-snapshot">{{
            reviewSnapshot
          }}</pre>
        </details>
      </section>
      <p v-if="viewerError && !viewerReady" class="local-error" role="status">
        {{ viewerError }}
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import TwinCatalog from "@/components/twin/TwinCatalog.vue";
import TwinViewer from "@/components/twin/TwinViewer.vue";
import TwinProcessPanel from "@/components/twin/TwinProcessPanel.vue";
import type {
  CandidateGroup,
  Catalog,
  CatalogEntry,
  DemoSession,
  ProcessBundle,
  ProcessTopic,
  TwinManifest,
  TwinMapping,
  TwinParts,
  ViewerMetrics,
} from "@/types/twin";
import {
  getCatalog,
  getManifest,
  getMapping,
  getParts,
  getProcess,
  protectedFailure,
} from "@/services/twin/twinApi";
import { createScheduler } from "@/composables/twin/scheduler";
import {
  contextKey,
  Generation,
  knowledgeQuery,
  makeSession,
  seek,
  switchTopic,
} from "@/composables/twin/session";

import {
  UnorderedListOutlined,
  InfoCircleOutlined,
  ReadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  CloseOutlined,
  DownOutlined,
} from "@ant-design/icons-vue";
import {
  durationFor,
  lectureRoutes,
  topics,
} from "@/components/twin/process/lessons";
import { useModuleFullscreen } from "@/composables/twin/fullscreen";

const moduleRoot = ref<HTMLElement | null>(null),
  moduleTop = ref(114);
const fullscreen = useModuleFullscreen(() => moduleRoot.value);
const compareMode = ref(false),
  comparisonSessions = new Map<string, DemoSession>(),
  routeNotice = ref(""),
  knowledgeError = ref("");
const selectionCollapsed = ref(window.innerWidth <= 700);
const reducedMotion = Boolean(
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches,
);
let wasNarrow = window.innerWidth <= 700;
function resizeModule() {
  const narrow = window.innerWidth <= 700;
  if (narrow && !wasNarrow) {
    partsOpen.value = false;
    selectionCollapsed.value = true;
  }
  wasNarrow = narrow;
  if (moduleRoot.value)
    moduleTop.value = Math.round(
      moduleRoot.value.getBoundingClientRect().top + window.scrollY,
    );
}
watch(moduleRoot, async () => {
  await nextTick();
  resizeModule();
});

const router = useRouter(),
  route = useRoute(),
  scheduler = createScheduler(),
  loadingGeneration = new Generation(),
  selectionGeneration = new Generation();
const catalog = ref<Catalog | null>(null),
  catalogLoading = ref(true),
  entryLoading = ref(false),
  pageError = ref(""),
  availability = ref(""),
  selectedEntry = ref("");
const manifest = ref<TwinManifest | null>(null),
  parts = ref<TwinParts | null>(null),
  process = ref<ProcessBundle | null>(null),
  session = ref<DemoSession | null>(null);
const mapping = ref<TwinMapping | null>(null),
  mappingLoading = ref(false),
  mappingError = ref(""),
  selectedGroup = ref<CandidateGroup | null>(null),
  search = ref("");
const partsError = ref(""),
  processError = ref(""),
  viewerError = ref(""),
  viewerReady = ref(false),
  partsOpen = ref(window.innerWidth > 700),
  infoOpen = ref(false),
  metrics = ref<ViewerMetrics | null>(null);
const viewer = ref<InstanceType<typeof TwinViewer> | null>(null),
  sessions = new Map<string, DemoSession>();
const reviewSnapshot = ref("");
let entryStarted = 0,
  manifestReadyMs = 0,
  resourcesReadyMs: number | null = null,
  interactiveMs: number | null = null;
const graphicsReview = ref("");
function onViewerReady() {
  viewerReady.value = true;
  recordInteractive();
  if (graphicsReview.value === "正在模拟图形丢失并重新核验…")
    graphicsReview.value = "图形已恢复，同一模型已重新核验；示教保持暂停。";
}
function onContextLost() {
  viewerReady.value = false;
  if (session.value) session.value.paused = true;
}
function reviewGraphicsRecovery() {
  graphicsReview.value = viewer.value?.reviewGraphicsRecovery()
    ? "正在模拟图形丢失并重新核验…"
    : "当前浏览器不支持该项模拟。";
}
function onMetrics(value: ViewerMetrics) {
  metrics.value = value;
  recordInteractive();
}
function recordInteractive() {
  if (productionReady.value && resourcesReadyMs === null)
    resourcesReadyMs = performance.now() - entryStarted;
  if (
    productionReady.value &&
    metrics.value?.firstVisibleMs !== undefined &&
    interactiveMs === null
  )
    interactiveMs = performance.now() - entryStarted;
}
function captureReviewSnapshot() {
  const data = viewer.value?.reviewSnapshot();
  if (data)
    reviewSnapshot.value = JSON.stringify(
      {
        ...data,
        entry_timing: {
          choose_to_manifest_ms: manifestReadyMs,
          choose_to_resources_ready_ms: resourcesReadyMs,
          choose_to_interactive_ms: interactiveMs,
          choose_to_first_render_ms:
            data.load.model_request_to_first_render_ms === null
              ? null
              : data.load.request_started_at_ms -
                entryStarted +
                data.load.model_request_to_first_render_ms,
        },
      },
      null,
      2,
    );
}
const availableTopics = computed<ProcessTopic[]>(() => {
  const s = session.value,
    p = process.value;
  if (!s || !p) return [];
  const result = (
    ["production", "filtration", "cip", "sip"] as ProcessTopic[]
  ).filter((k) => p.modes.includes(k));
  if (!compareMode.value && s.equipmentId === "M607B") {
    if (p.modes.includes("jacket") && p.lessons?.jacket) result.push("jacket");
    if (p.modes.includes("attachment") && p.lessons?.attachment)
      result.push("attachment");
  }
  return result;
});
const groupSections = computed(() => {
  const gs = filteredGroups.value,
    attachment = new Set(process.value?.lessons?.attachment?.ids ?? []);
  const isAttachment = (g: CandidateGroup) =>
    g.asset_ids.some((a) => attachment.has(a)) || g.label.includes("M660B");
  return [
    {
      label: "当前设备",
      groups: gs.filter((g) => g.equipment_id === session.value?.equipmentId),
    },
    {
      label: "共有上下文",
      groups: gs.filter((g) => !g.equipment_id && !isAttachment(g)),
    },
    {
      label: "独立附件候选",
      groups: gs.filter((g) => !g.equipment_id && isAttachment(g)),
    },
  ];
});
function moduleKeydown(event: KeyboardEvent) {
  if (fullscreen.exitOnEscape(event)) return;
  if (event.key === "Escape" && !document.fullscreenElement && infoOpen.value) {
    event.preventDefault();
    infoOpen.value = false;
    return;
  }
  if (
    event.target instanceof HTMLCanvasElement &&
    event.code === "Space" &&
    session.value?.mode === "production"
  ) {
    event.preventDefault();
    togglePlay();
  }
}
let disposed = false,
  catalogEpoch = 0,
  permissionCheck: ReturnType<typeof setInterval> | null = null;
const filteredGroups = computed(() =>
  (parts.value?.groups || []).filter(
    (g) =>
      (!g.equipment_id || g.equipment_id === session.value?.equipmentId) &&
      g.label.toLowerCase().includes(search.value.trim().toLowerCase()),
  ),
);
const productionReady = computed(() =>
  Boolean(
    process.value?.modes.includes("production") &&
    session.value &&
    process.value.bindings[session.value.equipmentId] &&
    !processError.value &&
    viewerReady.value,
  ),
);
function errorText(e: unknown, fallback: string) {
  return e instanceof Error ? e.message : fallback;
}
function invalidateSelection() {
  selectionGeneration.next();
  mapping.value = null;
  mappingLoading.value = false;
  mappingError.value = "";
  selectedGroup.value = null;
}
function clearSelection() {
  invalidateSelection();
  viewer.value?.selectIds([]);
}
function resetEntry() {
  compareMode.value = false;
  comparisonSessions.clear();
  knowledgeError.value = "";
  routeNotice.value = "";
  graphicsReview.value = "";
  loadingGeneration.next();
  invalidateSelection();
  if (session.value) session.value.paused = true;
  manifest.value = null;
  process.value = null;
  parts.value = null;
  session.value = null;
  partsError.value = "";
  processError.value = "";
  viewerError.value = "";
  viewerReady.value = false;
  availability.value = "";
  entryLoading.value = false;
  metrics.value = null;
}
function failProtected(message: string) {
  resetEntry();
  sessions.clear();
  catalog.value = null;
  pageError.value = message;
}
function deviceSession(m: TwinManifest, equipment: string) {
  const key = contextKey(m, equipment);
  if (!sessions.has(key))
    sessions.set(key, reactive(makeSession(m, equipment)));
  return sessions.get(key)!;
}
function chooseEquipment(equipment: string) {
  if (!manifest.value?.equipment_ids.includes(equipment)) return;
  if (session.value) session.value.paused = true;
  syncComparison();
  invalidateSelection();
  viewer.value?.selectIds([]);
  session.value = compareMode.value
    ? (comparisonSessions.get(equipment) ??
      deviceSession(manifest.value, equipment))
    : deviceSession(manifest.value, equipment);
  scheduler.invalidate();
}
async function loadCatalog() {
  const token = ++catalogEpoch;
  catalogLoading.value = true;
  pageError.value = "";
  try {
    const c = await getCatalog();
    if (disposed || token !== catalogEpoch) return;
    catalog.value = c;
    if (manifest.value) {
      const active = manifest.value,
        current = c.entries.find((e) => e.entry_id === active.entry_id);
      if (!current || current.availability !== "READY") {
        failProtected("当前设备查看范围或成员批准已失效，展示已停止。");
        return;
      }
      const checked = await getManifest(active.entry_id, active.model_sha256);
      if (disposed || token !== catalogEpoch) return;
      if (
        manifest.value === active &&
        [
          "model_sha256",
          "mapping_revision",
          "mapping_sha256",
          "process_revision",
          "process_sha256",
          "binding_revision",
          "camera_revision",
          "demo_revision",
          "demo_seed",
        ].some(
          (k) =>
            checked[k as keyof TwinManifest] !==
            active[k as keyof TwinManifest],
        )
      ) {
        failProtected("资源版本已变更，旧场景已关闭，请重新打开。");
        return;
      }
    }
    if (!manifest.value && !entryLoading.value) {
      const requested = String(route.query.entry || selectedEntry.value || "");
      const entry =
        c.entries.find((e) => e.entry_id === requested) || c.entries[0];
      if (entry) await chooseEntry(entry);
    }
  } catch (e) {
    if (disposed || token !== catalogEpoch) return;
    if (protectedFailure(e))
      failProtected(errorText(e, "登录或设备权限已失效。"));
    else pageError.value = errorText(e, "设备目录暂时不可用。");
  } finally {
    if (token === catalogEpoch) catalogLoading.value = false;
  }
}
async function chooseEntry(entry: CatalogEntry) {
  resetEntry();
  entryStarted = performance.now();
  interactiveMs = null;
  resourcesReadyMs = null;
  reviewSnapshot.value = "";
  selectedEntry.value = entry.entry_id;
  search.value = "";
  pageError.value = "";
  void router.replace({ path: "/hbos/twin", query: { entry: entry.entry_id } });
  if (entry.availability !== "READY") {
    availability.value =
      entry.availability === "MEMBERS_PENDING"
        ? "资产成员范围等待 Owner 确认"
        : "当前已知设备的交互制品尚不可用";
    return;
  }
  const token = loadingGeneration.next();
  entryLoading.value = true;
  try {
    const m = await getManifest(entry.entry_id);
    if (disposed || !loadingGeneration.isCurrent(token)) return;
    manifestReadyMs = performance.now() - entryStarted;
    session.value = deviceSession(m, m.equipment_ids[0]!);
    manifest.value = m;
    entryLoading.value = false;
    const results = await Promise.allSettled([getParts(m), getProcess(m)]);
    if (disposed || !loadingGeneration.isCurrent(token)) return;
    const [p, d] = results;
    if (p.status === "fulfilled") {
      if (
        p.value.entry_id === m.entry_id &&
        p.value.model_sha256 === m.model_sha256 &&
        p.value.mapping_revision === m.mapping_revision
      )
        parts.value = p.value;
      else partsError.value = "候选目录与当前模型不兼容。";
    } else if (protectedFailure(p.reason)) {
      failProtected(errorText(p.reason, "设备查看权限已失效。"));
      return;
    } else partsError.value = errorText(p.reason, "候选目录暂时不可用。");
    if (d.status === "fulfilled") {
      if (
        d.value.entry_id === m.entry_id &&
        d.value.model_sha256 === m.model_sha256 &&
        d.value.mapping_revision === m.mapping_revision &&
        d.value.process_revision === m.process_revision &&
        d.value.binding_revision === m.binding_revision &&
        (d.value.camera_revision === undefined ||
          d.value.camera_revision === m.camera_revision) &&
        (d.value.demo_revision === undefined ||
          d.value.demo_revision === m.demo_revision)
      )
        process.value = d.value;
      else processError.value = "当前示教配置与模型版本不兼容。";
    } else if (protectedFailure(d.reason)) {
      failProtected(errorText(d.reason, "设备查看权限已失效。"));
      return;
    } else processError.value = errorText(d.reason, "当前示教配置不兼容。");
    recordInteractive();
  } catch (e) {
    if (disposed || !loadingGeneration.isCurrent(token)) return;
    if (protectedFailure(e))
      failProtected(errorText(e, "设备权限或资源版本已失效。"));
    else availability.value = errorText(e, "设备资源暂时不可用。");
  } finally {
    if (loadingGeneration.isCurrent(token)) entryLoading.value = false;
  }
}
async function selectAsset(assetId: string | null) {
  invalidateSelection();
  const m = manifest.value,
    s = session.value;
  if (!assetId || !m || !s) return;
  const token = selectionGeneration.next(),
    key = s.contextKey,
    equipment = s.equipmentId;
  mappingLoading.value = true;
  try {
    const result = await getMapping(m, equipment, assetId);
    if (
      disposed ||
      !selectionGeneration.isCurrent(token) ||
      session.value?.contextKey !== key ||
      manifest.value?.model_sha256 !== m.model_sha256
    )
      return;
    if (
      result.model_sha256 !== m.model_sha256 ||
      result.mapping_revision !== m.mapping_revision ||
      result.equipment_id !== equipment ||
      result.asset_id !== assetId
    ) {
      mappingError.value = "映射响应与当前选择不兼容。";
      return;
    }
    mapping.value = result;
  } catch (e) {
    if (disposed || !selectionGeneration.isCurrent(token)) return;
    if (protectedFailure(e))
      failProtected(errorText(e, "设备查看权限已失效。"));
    else mappingError.value = errorText(e, "节点映射暂时不可用。");
  } finally {
    if (selectionGeneration.isCurrent(token)) mappingLoading.value = false;
  }
}
function chooseGroup(group: CandidateGroup) {
  if (session.value) session.value.followCamera = false;
  if (group.equipment_id && group.equipment_id !== session.value?.equipmentId)
    chooseEquipment(group.equipment_id);
  invalidateSelection();
  selectedGroup.value = group;
  viewer.value?.selectIds(group.asset_ids);
  viewer.value?.focusIds(group.asset_ids);
}
function enterDemo() {
  if (!session.value || !productionReady.value) return;
  invalidateSelection();
  session.value.mode = "production";
  session.value.paused = true;
  session.value.followCamera = !reducedMotion;
  scheduler.invalidate();
}
function leaveCompare() {
  const m = manifest.value,
    s = session.value;
  if (!m || !s || !compareMode.value) return;
  for (const other of comparisonSessions.values()) other.paused = true;
  compareMode.value = false;
  comparisonSessions.clear();
  session.value = deviceSession(m, s.equipmentId);
  session.value.paused = true;
}
function exitDemo() {
  leaveCompare();
  if (!session.value) return;
  session.value.mode = "browse";
  session.value.paused = true;
  session.value.followCamera = false;
  session.value.route = "free";
  invalidateSelection();
  scheduler.invalidate();
}
function chooseTopic(topic: ProcessTopic) {
  if (!session.value || !availableTopics.value.includes(topic)) return;
  session.value.route = "free";
  switchTopic(session.value, topic);
  invalidateSelection();
  if (compareMode.value)
    for (const s of comparisonSessions.values()) {
      switchTopic(s, topic);
      seek(s, session.value.time);
      s.mode = "production";
    }
  scheduler.invalidate();
}
function syncComparison() {
  if (!compareMode.value || !session.value) return;
  const active = session.value,
    p = active.time / durationFor(active.topic);
  for (const other of comparisonSessions.values()) {
    other.topic = active.topic;
    seek(other, p * durationFor(other.topic));
    other.paused = active.paused;
    other.speed = active.speed;
  }
}
function seekTo(time: number) {
  if (session.value) {
    seek(session.value, time);
    syncComparison();
    scheduler.invalidate();
  }
}
function togglePlay() {
  if (!session.value || !productionReady.value) return;
  if (session.value.time >= durationFor(session.value.topic)) {
    replay();
    return;
  }
  session.value.paused = !session.value.paused;
  syncComparison();
  scheduler.invalidate();
}
function replay() {
  if (session.value && productionReady.value) {
    const s = session.value;
    if (s.route !== "free") {
      s.routeIndex = 0;
      switchTopic(s, lectureRoutes[s.route].topics[0]!);
    }
    seek(s, 0);
    s.paused = false;
    syncComparison();
    scheduler.invalidate();
  }
}
function setSpeed(value: number) {
  if (session.value && [0.5, 1, 2].includes(value)) {
    session.value.speed = value;
    syncComparison();
    scheduler.invalidate();
  }
}
function toggleCompare() {
  if (compareMode.value) {
    leaveCompare();
    scheduler.invalidate();
    return;
  }
  const m = manifest.value,
    active = session.value;
  if (!m || m.entity_type !== "scene" || !active || !productionReady.value)
    return;
  active.paused = true;
  const topic = (
    ["filtration", "production", "cip", "sip"].includes(active.topic)
      ? active.topic
      : "production"
  ) as ProcessTopic;
  const progress = active.time / durationFor(active.topic);
  for (const eq of m.equipment_ids) {
    const s = reactive(makeSession(m, eq));
    s.mode = "production";
    s.topic = topic;
    seek(s, progress * durationFor(topic));
    comparisonSessions.set(eq, s);
  }
  invalidateSelection();
  compareMode.value = true;
  session.value = comparisonSessions.get(active.equipmentId)!;
  scheduler.invalidate();
}
function startRoute(value: string) {
  const s = session.value;
  if (!s || compareMode.value) return;
  if (value === "free") {
    s.route = "free";
    return;
  }
  if (value !== "principles" && value !== "cleaning") return;
  const route = lectureRoutes[value];
  if (route.topics.some((t) => !availableTopics.value.includes(t))) {
    routeNotice.value = "当前配置尚未支持这条完整讲解路线。";
    return;
  }
  routeNotice.value = "";
  s.route = value;
  s.routeIndex = 0;
  switchTopic(s, route.topics[0]!);
  seek(s, 0);
  s.mode = "production";
  s.followCamera = !reducedMotion;
  invalidateSelection();
  scheduler.invalidate();
}
async function openKnowledge() {
  if (!manifest.value || !session.value) return;
  session.value.paused = true;
  knowledgeError.value = "";
  try {
    await router.push({
      path: "/hbos/knowledge",
      query: knowledgeQuery(
        session.value.equipmentId,
        mapping.value,
        manifest.value,
      ),
    });
  } catch {
    knowledgeError.value = "现有知识入口暂不可用，请稍后重试。";
  }
}
function hidden() {
  if (document.hidden && session.value) session.value.paused = true;
  else if (!document.hidden) void loadCatalog();
}
const unsubscribe = scheduler.subscribe((dt) => {
  const s = session.value;
  if (!s || s.paused || s.mode === "browse") return false;
  seek(s, s.time + dt * s.speed);
  syncComparison();
  if (s.time >= durationFor(s.topic)) {
    const route = s.route === "free" ? null : lectureRoutes[s.route];
    const next = route?.topics[s.routeIndex + 1];
    if (next) {
      s.routeIndex++;
      switchTopic(s, next);
      seek(s, 0);
      s.paused = false;
    } else s.paused = true;
  }
  return !s.paused;
});
onMounted(() => {
  void loadCatalog();
  window.addEventListener("resize", resizeModule);
  document.addEventListener("visibilitychange", hidden);
  window.addEventListener("focus", loadCatalog);
  permissionCheck = setInterval(() => {
    if (!document.hidden && manifest.value) void loadCatalog();
  }, 30000);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeModule);
  disposed = true;
  catalogEpoch++;
  resetEntry();
  sessions.clear();
  if (permissionCheck) clearInterval(permissionCheck);
  document.removeEventListener("visibilitychange", hidden);
  window.removeEventListener("focus", loadCatalog);
  unsubscribe();
  scheduler.stop();
});
</script>

<style scoped>
.twin-page {
  min-width: 0;
  color: #304e3e;
}
.twin-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.twin-heading h1 {
  margin: 0;
  font-size: 24px;
}
.twin-heading span {
  font-size: 16px;
  color: #687d70;
}
.twin-module {
  position: relative;
  display: flex;
  flex-direction: column;
  height: max(440px, calc(100dvh - var(--module-top) - 18px));
  min-height: 0;
  min-width: 0;
  background: #ffffffc9;
  border: 1px solid #d6e3da;
  border-radius: 14px;
  overflow: hidden;
}
.module-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-bottom: 1px solid #dfe9e3;
  flex: none;
}
.review-badge {
  font-size: 12px;
  color: #7f714c;
  white-space: nowrap;
}
.mode-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: #fafcfa;
  flex: none;
}
.mode-tabs {
  display: flex;
  gap: 4px;
}
.mode-tabs button {
  border: 0;
  background: none;
  padding: 6px 12px;
  min-height: 36px;
  border-radius: 8px;
  font-size: 14px;
  color: #5e7266;
  cursor: pointer;
}
.mode-tabs button[aria-pressed="true"] {
  background: #dfeee4;
  color: #235b40;
}
.device-select,
.current-equipment {
  font-size: 14px;
  color: #4c705a;
}
.device-select {
  display: flex;
  align-items: center;
  gap: 7px;
}
.device-select select,
.topic-select select,
.lecture-bar select {
  min-height: 34px;
  border: 1px solid #d2dfd6;
  border-radius: 7px;
  background: white;
  color: #3d5e48;
  padding: 3px 7px;
  font-size: 14px;
}
.topic-select select {
  max-width: 180px;
}
.workspace-actions {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-left: auto;
}
.workspace-actions button,
.selection-actions button,
.browse-note button,
.blank-state button,
.error-card button,
.version-panel button,
.lecture-bar button {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 5px 9px;
  border: 1px solid #d3e0d8;
  border-radius: 7px;
  background: white;
  color: #42604c;
  font-size: 14px;
  cursor: pointer;
}
.lecture-bar {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 12px;
  border-top: 1px solid #e1eae3;
  border-bottom: 1px solid #d9e6dd;
  background: #f2f8f3;
  font-size: 12px;
  color: #68806e;
}
.lecture-bar label {
  display: flex;
  gap: 7px;
  align-items: center;
}
.lecture-bar button[aria-pressed="true"] {
  background: #dceee2;
  color: #2b6748;
}
.lecture-bar > span {
  margin-left: auto;
}
.twin-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-height: 0;
  flex: 1;
}
.twin-workspace.with-parts {
  grid-template-columns: 238px minmax(0, 1fr);
}
.parts-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fbfdfb;
  border-right: 1px solid #dbe6df;
}
.parts-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px 8px;
  gap: 8px;
}
.parts-heading strong {
  font-size: 16px;
}
.parts-heading button,
.selection-heading button,
.version-heading button {
  border: 0;
  background: none;
  min-width: 32px;
  min-height: 32px;
  padding: 4px;
  color: #5e7b68;
  cursor: pointer;
}
.search-label {
  padding: 0 12px;
}
.search-label input {
  width: 100%;
  font-size: 14px;
  min-height: 36px;
  border: 1px solid #d5e1d8;
  border-radius: 8px;
  background: white;
  padding: 7px 9px;
  color: #3e5948;
}
.candidate-note {
  font-size: 12px;
  line-height: 1.7;
  color: #72806e;
  padding: 0 14px;
  margin: 8px 0;
}
.part-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 8px 10px;
}
.part-list h3 {
  margin: 12px 6px 5px;
  font-size: 12px;
  font-weight: 500;
  color: #758873;
}
.part-list button {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 8px;
  background: none;
  padding: 10px 8px;
  color: #3e5c49;
  cursor: pointer;
}
.part-list button:hover {
  background: #eff6f0;
}
.part-list button.active {
  background: #e3f0e7;
  border-color: #a4c4b1;
  color: #255f40;
}
.part-list span {
  display: block;
  font-size: 16px;
  line-height: 1.5;
}
.part-list small {
  display: block;
  font-size: 12px;
  color: #778b7b;
  margin-top: 4px;
}
.parts-footer {
  font-size: 12px;
  color: #768471;
  line-height: 1.7;
  padding: 10px 14px;
  border-top: 1px solid #e1e9e3;
}
.canvas-column {
  min-width: 0;
  min-height: 0;
  position: relative;
}
.selection-panel {
  position: absolute;
  z-index: 4;
  right: 14px;
  bottom: 38px;
  width: min(340px, calc(100% - 28px));
  max-height: 60%;
  overflow: auto;
  background: #fffffff5;
  border: 1px solid #b8d1c2;
  border-radius: 12px;
  padding: 12px;
  box-shadow: 0 8px 24px #294e3810;
  font-size: 16px;
}
.selection-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.selection-panel small {
  font-size: 12px;
  line-height: 1.6;
  color: #778064;
  display: block;
}
.selection-panel strong {
  display: block;
  font-size: 16px;
  margin: 3px 0;
  line-height: 1.5;
}
.selection-panel p {
  font-size: 16px;
  line-height: 1.6;
  margin: 7px 0;
  color: #536a58;
}
.selection-actions {
  display: flex;
  gap: 5px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.browse-note {
  flex: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  gap: 10px;
  font-size: 12px;
  color: #70816f;
  border-top: 1px solid #d8e4dc;
  background: #fafcf9;
}
.browse-note button {
  color: #2d7051;
}
.version-panel {
  position: absolute;
  z-index: 6;
  right: 12px;
  top: 64px;
  bottom: 12px;
  width: min(570px, calc(100% - 24px));
  padding: 18px;
  overflow: auto;
  border: 1px solid #b4ccbe;
  border-radius: 12px;
  background: #fffffffa;
  box-shadow: 0 14px 42px #243f321f;
  font-size: 16px;
  line-height: 1.6;
}
.version-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.version-heading h3 {
  font-size: 18px;
  margin: 0 0 12px;
}
.truth-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.truth-grid strong {
  font-size: 14px;
  display: block;
}
.truth-grid span {
  font-size: 12px;
  display: block;
  color: #6d7968;
  margin-top: 3px;
}
.version-panel dl {
  display: grid;
  grid-template-columns: 95px minmax(0, 1fr);
  gap: 8px;
  margin-top: 18px;
  font-size: 12px;
  line-height: 1.7;
}
.version-panel dt {
  color: #7d8773;
}
.version-panel dd {
  margin: 0;
  word-break: break-all;
}
.version-panel > p,
.review-metrics {
  font-size: 12px;
  color: #6b7667;
}
.review-metrics pre {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 360px;
  overflow: auto;
  padding: 12px;
  background: #f1f6f2;
}
.review-metrics button {
  margin: 6px 6px 0 0;
}
.blank-state {
  padding: 30px;
  background: #ffffffbb;
  border: 1px solid #d7e3dc;
  border-radius: 14px;
  min-height: 250px;
  display: grid;
  place-content: center;
  gap: 12px;
  text-align: center;
  font-size: 16px;
}
.blank-state h2,
.blank-state p {
  margin: 0;
}
.error-card {
  padding: 18px;
  border: 1px solid #e4cbc2;
  border-radius: 12px;
  background: #fff8f4;
  display: flex;
  justify-content: space-between;
  font-size: 16px;
  color: #825c4c;
}
.local-notice,
.local-error {
  font-size: 12px;
  color: #806f48;
  line-height: 1.65;
  padding: 6px 12px;
  background: #fcfaf1;
}
.local-notice {
  flex: none;
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
select:focus-visible,
summary:focus-visible {
  outline: 3px solid #317858;
  outline-offset: 2px;
}
.twin-module:fullscreen {
  height: 100dvh !important;
  width: 100vw;
  border-radius: 0;
  background: #f4f9f5;
  --module-top: 0px;
}
@media (max-width: 1150px) {
  .twin-workspace.with-parts {
    grid-template-columns: 210px minmax(0, 1fr);
  }
  .mode-bar {
    gap: 7px;
  }
  .workspace-actions button {
    padding: 5px 7px;
  }
  .lecture-bar > span {
    display: none;
  }
}
@media (max-width: 700px) {
  .twin-heading {
    display: block;
  }
  .twin-heading span {
    font-size: 14px;
  }
  .twin-module {
    height: max(430px, calc(100dvh - var(--module-top) - 12px));
    border-radius: 10px;
  }
  .module-heading {
    padding: 6px 8px;
    gap: 6px;
    flex-wrap: wrap;
  }
  .review-badge {
    font-size: 12px;
    white-space: normal;
  }
  .mode-bar {
    padding: 5px 8px;
    gap: 5px;
  }
  .mode-tabs button {
    padding: 5px 10px;
  }
  .workspace-actions {
    width: 100%;
    margin-left: 0;
    gap: 5px;
  }
  .workspace-actions button {
    flex: 1;
    font-size: 14px;
    min-height: 32px;
    padding: 4px 6px;
  }
  .device-select {
    font-size: 12px;
  }
  .device-select select {
    font-size: 14px;
    min-height: 32px;
  }
  .current-equipment {
    margin-left: auto;
  }
  .topic-select {
    flex: 1;
  }
  .topic-select select {
    width: 100%;
    max-width: none;
  }
  .lecture-bar {
    padding: 4px 8px;
    flex-wrap: wrap;
    gap: 4px;
    font-size: 12px;
  }
  .lecture-bar select {
    font-size: 14px;
    max-width: 170px;
    min-height: 30px;
  }
  .lecture-bar button {
    min-height: 30px;
    font-size: 12px;
  }
  .twin-workspace.with-parts {
    grid-template-columns: minmax(0, 1fr);
  }
  .parts-panel {
    position: absolute;
    z-index: 5;
    left: 8px;
    right: 8px;
    top: 180px;
    bottom: 160px;
    border: 1px solid #b7d0c0;
    border-radius: 10px;
    box-shadow: 0 8px 22px #2a4e3822;
  }
  .parts-footer {
    display: none;
  }
  .selection-panel {
    right: 8px;
    bottom: 28px;
    padding: 8px;
    width: calc(100% - 16px);
    max-height: 65%;
  }
  .selection-panel strong {
    font-size: 16px;
  }
  .browse-note {
    font-size: 12px;
    padding: 6px 8px;
    flex-wrap: wrap;
    gap: 4px;
  }
  .browse-note button {
    min-height: 32px;
    margin-left: auto;
  }
  .version-panel {
    top: 56px;
    padding: 14px;
  }
  .truth-grid {
    grid-template-columns: 1fr;
  }
  .version-panel dl {
    grid-template-columns: 78px minmax(0, 1fr);
  }
}
@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
    scroll-behavior: auto !important;
  }
}
.lecture-options {
  position: relative;
  flex: none;
}
.lecture-options summary {
  list-style: none;
  cursor: pointer;
  border: 1px solid #cfded4;
  border-radius: 7px;
  background: white;
  min-height: 34px;
  padding: 5px 8px;
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #42634e;
}
.lecture-options summary::-webkit-details-marker {
  display: none;
}
.lecture-options[open] summary {
  background: #e4f0e7;
}
.lecture-options .lecture-bar {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  width: 340px;
  z-index: 7;
  display: grid;
  gap: 12px;
  border: 1px solid #b6cdbd;
  padding: 14px;
  border-radius: 10px;
  box-shadow: 0 10px 28px #28473720;
  background: #fcfefc;
}
.lecture-options .lecture-bar label {
  align-items: flex-start;
  flex-direction: column;
  font-size: 14px;
}
.lecture-options .lecture-bar select {
  width: 100%;
  max-width: none;
}
.lecture-options .lecture-bar > span {
  display: block;
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
}
@media (max-width: 700px) {
  .review-badge {
    display: none;
  }
  .device-select {
    font-size: 0;
    gap: 0;
  }
  .device-select select {
    font-size: 14px;
  }
  .workspace-actions button {
    white-space: nowrap;
  }
  .lecture-options summary {
    font-size: 14px;
    min-height: 32px;
    padding: 4px 7px;
  }
  .lecture-options .lecture-bar {
    left: auto;
    right: 0;
    width: min(300px, 80vw);
  }
}
</style>
