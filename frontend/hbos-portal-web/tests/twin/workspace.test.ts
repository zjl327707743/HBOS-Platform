import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { defineComponent, onMounted } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import TwinView from "@/views/TwinView.vue";
import TwinProcessPanel from "@/components/twin/TwinProcessPanel.vue";
import { TwinError } from "@/services/twin/twinApi";
import type {
  CatalogEntry,
  DemoSession,
  TwinManifest,
  TwinMapping,
} from "@/types/twin";

const api = vi.hoisted(() => ({
  getCatalog: vi.fn(),
  getManifest: vi.fn(),
  getParts: vi.fn(),
  getProcess: vi.fn(),
  getMapping: vi.fn(),
}));
vi.mock("@/services/twin/twinApi", async (original) => ({
  ...(await original<typeof import("@/services/twin/twinApi")>()),
  ...api,
}));
const Viewer = defineComponent({
  name: "TestTwinViewer",
  props: ["manifest", "process", "session", "scheduler", "comparison"],
  emits: ["select", "ready", "manual", "restore", "contextLost"],
  setup(_props, { emit, expose }) {
    onMounted(() => emit("ready"));
    expose({
      selectIds: vi.fn(),
      focusIds: vi.fn(),
      focusSelected: vi.fn(),
      toggleIsolate: vi.fn(),
      hideSelected: vi.fn(),
      restoreAll: vi.fn(),
    });
  },
  template: '<div data-test="viewer">{{manifest.entry_id}}</div>',
});
const entries: CatalogEntry[] = ["M606B", "M607B", "DUAL"].map((id) => ({
  entry_id: id,
  label: id,
  entity_type: id === "DUAL" ? "scene" : "device",
  equipment_ids: id === "DUAL" ? ["M606B", "M607B"] : [id],
  availability: "READY",
}));
function manifest(entry: string): TwinManifest {
  return {
    entry_id: entry,
    label: entry,
    entity_type: entry === "DUAL" ? "scene" : "device",
    equipment_ids: entry === "DUAL" ? ["M606B", "M607B"] : [entry],
    model_sha256: entry + "-sha",
    model_size_bytes: 1,
    model_revision: "fixture",
    mapping_revision: "parts-1",
    mapping_sha256: "parts-sha",
    process_revision: "process-1",
    process_sha256: "process-sha",
    binding_revision: "binding-1",
    camera_revision: "camera-1",
    demo_revision: "demo-1",
    demo_seed: 102,
    model_url: "/api/method/fixture",
    review_only: true,
    truth: {},
  };
}
function mapped(m: TwinManifest, asset: string): TwinMapping {
  return {
    entry_id: m.entry_id,
    equipment_id: m.equipment_ids[0]!,
    asset_id: asset,
    model_sha256: m.model_sha256,
    mapping_revision: m.mapping_revision,
    status: "unverified",
    display_name: asset,
    component_id: null,
    knowledge_link_available: false,
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}
let wrapper: VueWrapper | null = null;
beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, "requestAnimationFrame").mockReturnValue(1);
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
  api.getCatalog.mockResolvedValue({
    schema: "twin.catalog.v1",
    catalog_revision: "fixture",
    entries,
  });
  api.getManifest.mockImplementation(async (entry) => manifest(entry));
  api.getParts.mockImplementation(async (m) => ({ ...m, groups: [] }));
  api.getProcess.mockImplementation(async (m) => ({
    ...m,
    modes: ["production", "filtration", "cip", "sip"],
    bindings: Object.fromEntries(m.equipment_ids.map((id: string) => [id, {}])),
  }));
  api.getMapping.mockImplementation(async (m, _equipment, asset) =>
    mapped(m, asset),
  );
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  vi.restoreAllMocks();
});
async function start() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/hbos", component: { template: "<div />" } },
      { path: "/hbos/twin", component: { template: "<div />" } },
      { path: "/hbos/knowledge", component: { template: "<div />" } },
    ],
  });
  await router.push("/hbos/twin");
  await router.isReady();
  wrapper = mount(TwinView, {
    global: { plugins: [router], stubs: { TwinViewer: Viewer } },
  });
  await flushPromises();
  return { router, view: wrapper };
}
function button(text: string) {
  return wrapper!.findAll("button").find((b) => b.text() === text)!;
}
async function choose(id: string) {
  await wrapper!
    .get(".twin-catalog")
    .findAll("button")
    .find((b) => b.text().includes(id))!
    .trigger("click");
  await flushPromises();
}
function viewer() {
  return wrapper!.getComponent(Viewer);
}

it("drops a late model manifest after switching entries", async () => {
  const old = deferred<TwinManifest>();
  api.getManifest.mockImplementation((entry) =>
    entry === "M606B" ? old.promise : Promise.resolve(manifest(entry)),
  );
  await start();
  await choose("M607B");
  expect(viewer().props("manifest").entry_id).toBe("M607B");
  old.resolve(manifest("M606B"));
  await flushPromises();
  expect(viewer().props("manifest").entry_id).toBe("M607B");
  expect(api.getParts).toHaveBeenCalledTimes(1);
});

it("keeps the last selection, then discards late mapping after clear and switch", async () => {
  const first = deferred<TwinMapping>(),
    second = deferred<TwinMapping>(),
    third = deferred<TwinMapping>();
  api.getMapping.mockImplementation((_m, _eq, asset) =>
    asset === "old-A"
      ? first.promise
      : asset === "new-B"
        ? second.promise
        : third.promise,
  );
  await start();
  viewer().vm.$emit("select", "old-A");
  viewer().vm.$emit("select", "new-B");
  second.resolve(mapped(manifest("M606B"), "new-B"));
  await flushPromises();
  first.resolve(mapped(manifest("M606B"), "old-A"));
  await flushPromises();
  expect(wrapper!.text()).toContain("new-B");
  expect(wrapper!.text()).not.toContain("old-A");
  viewer().vm.$emit("select", "late-C");
  await flushPromises();
  await button("清空").trigger("click");
  await choose("M607B");
  third.resolve(mapped(manifest("M606B"), "late-C"));
  await flushPromises();
  expect(wrapper!.text()).not.toContain("late-C");
  expect(viewer().props("manifest").entry_id).toBe("M607B");
});

it("preserves each paused timeline and allows manual camera takeover", async () => {
  await start();
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 33);
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("follow", true);
  await flushPromises();
  const first = viewer().props("session") as DemoSession;
  expect(first.followCamera).toBe(true);
  viewer().vm.$emit("manual");
  await flushPromises();
  expect(first.followCamera).toBe(false);
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("toggle");
  await flushPromises();
  expect(first.paused).toBe(false);
  await choose("M607B");
  expect(first.paused).toBe(true);
  expect(viewer().props("session").time).toBe(0);
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 8);
  await choose("M606B");
  expect(viewer().props("session").time).toBe(33);
  expect(viewer().props("session").paused).toBe(true);
  viewer().vm.$emit("restore");
  await flushPromises();
  expect(viewer().props("session").mode).toBe("browse");
});

it("keeps dual equipment timelines independent", async () => {
  await start();
  await choose("DUAL");
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 29);
  await wrapper!.get(".device-select select").setValue("M607B");
  expect(viewer().props("session").time).toBe(0);
  expect(viewer().props("session").mode).toBe("browse");
  await wrapper!.get(".device-select select").setValue("M606B");
  expect(viewer().props("session").time).toBe(29);
  expect(viewer().props("session").paused).toBe(true);
});

it("pauses the active demo on graphics loss and requires a fresh viewer before playing", async () => {
  await start();
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("toggle");
  await flushPromises();
  const active = viewer().props("session") as DemoSession;
  expect(active.paused).toBe(false);
  viewer().vm.$emit("contextLost");
  await flushPromises();
  expect(active.paused).toBe(true);
  expect(button("生产示教").attributes("disabled")).toBeDefined();
  viewer().vm.$emit("ready");
  await flushPromises();
  expect(active.paused).toBe(true);
  expect(button("生产示教").attributes("disabled")).toBeUndefined();
});

it("leaves static browsing available on a process incompatibility", async () => {
  api.getProcess.mockRejectedValue(
    new TwinError("PROCESS_INCOMPATIBLE", "fixture incompatible"),
  );
  await start();
  expect(wrapper!.find('[data-test="viewer"]').exists()).toBe(true);
  expect(button("生产示教").attributes("disabled")).toBeDefined();
  expect(wrapper!.text()).toContain("静态浏览继续可用");
});

it("closes protected content on a mapping denial and on a version change", async () => {
  await start();
  api.getMapping.mockRejectedValue(new TwinError("FORBIDDEN", "访问已撤回"));
  viewer().vm.$emit("select", "invented");
  await flushPromises();
  expect(wrapper!.find('[data-test="viewer"]').exists()).toBe(false);
  expect(wrapper!.find(".twin-catalog").exists()).toBe(false);
  await button("重新核验").trigger("click");
  await flushPromises();
  expect(viewer().exists()).toBe(true);
  api.getManifest.mockResolvedValue({
    ...manifest("M606B"),
    mapping_revision: "new-parts",
  });
  window.dispatchEvent(new Event("focus"));
  await flushPromises();
  expect(wrapper!.find('[data-test="viewer"]').exists()).toBe(false);
  expect(wrapper!.text()).toContain("资源版本已变更");
});

it("keeps old knowledge parameters and does not send an unverified component", async () => {
  const { router } = await start();
  await choose("M607B");
  viewer().vm.$emit("select", "candidate-node");
  await flushPromises();
  await button("知识 ↗").trigger("click");
  await flushPromises();
  expect(router.currentRoute.value.path).toBe("/hbos/knowledge");
  expect(router.currentRoute.value.query).toMatchObject({
    equipment_id: "M607B",
    auto: "1",
  });
  expect(router.currentRoute.value.query.q).toContain("M607B");
  expect(router.currentRoute.value.query.component_id).toBeUndefined();
  expect(router.currentRoute.value.query.asset_id).toBeUndefined();
});

it("does not request any bundle while members are pending and cleans subscriptions on exit", async () => {
  api.getCatalog.mockResolvedValue({
    entries: entries.map((e) => ({ ...e, availability: "MEMBERS_PENDING" })),
  });
  const removeWindow = vi.spyOn(window, "removeEventListener"),
    removeDocument = vi.spyOn(document, "removeEventListener"),
    clear = vi.spyOn(globalThis, "clearInterval");
  await start();
  expect(api.getManifest).not.toHaveBeenCalled();
  expect(api.getParts).not.toHaveBeenCalled();
  expect(api.getProcess).not.toHaveBeenCalled();
  expect(wrapper!.text()).toContain("资产成员范围等待 Owner 确认");
  wrapper!.unmount();
  wrapper = null;
  expect(removeWindow).toHaveBeenCalledWith("focus", expect.any(Function));
  expect(removeDocument).toHaveBeenCalledWith(
    "visibilitychange",
    expect.any(Function),
  );
  expect(clear).toHaveBeenCalled();
});

it("preserves separate paused progress for each topic", async () => {
  await start();
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 31);
  await flushPromises();
  await wrapper!.get(".topic-select select").setValue("cip");
  expect(viewer().props("session").time).toBe(0);
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 13);
  await flushPromises();
  await wrapper!.get(".topic-select select").setValue("production");
  expect(viewer().props("session").time).toBe(31);
  expect(viewer().props("session").paused).toBe(true);
  await wrapper!.get(".topic-select select").setValue("cip");
  expect(viewer().props("session").time).toBe(13);
  expect(wrapper!.find(".topic-select").text()).not.toContain("夹套");
});

it("enters comparison explicitly and restores untouched independent timelines", async () => {
  await start();
  await choose("DUAL");
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 23);
  await wrapper!.get(".device-select select").setValue("M607B");
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 8);
  await flushPromises();
  await button("进入演示对照").trigger("click");
  const comparison = viewer().props("session");
  expect(viewer().props("comparison")).toBe(true);
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 42);
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("toggle");
  await flushPromises();
  await wrapper!.get(".device-select select").setValue("M606B");
  expect(viewer().props("session").time).toBe(42);
  expect(viewer().props("session").paused).toBe(true);
  expect(comparison.paused).toBe(true);
  await button("退出演示对照").trigger("click");
  expect(viewer().props("comparison")).toBe(false);
  expect(viewer().props("session").time).toBe(23);
  await wrapper!.get(".device-select select").setValue("M607B");
  expect(viewer().props("session").time).toBe(8);
  expect(viewer().props("session").paused).toBe(true);
});

it("advances and replays an explicit lecture route with one clock, retaining manual takeover", async () => {
  const frames: FrameRequestCallback[] = [];
  vi.mocked(window.requestAnimationFrame).mockImplementation((cb) => {
    frames.push(cb);
    return frames.length;
  });
  await start();
  await button("生产示教").trigger("click");
  await wrapper!.get(".lecture-bar select").setValue("principles");
  const active = viewer().props("session") as DemoSession;
  expect(active.topic).toBe("filtration");
  expect(active.paused).toBe(true);
  const panel = wrapper!.getComponent(TwinProcessPanel);
  panel.vm.$emit("seek", 39.99);
  panel.vm.$emit("toggle");
  await flushPromises();
  expect(frames).toHaveLength(1);
  frames.shift()!(1000);
  frames.shift()!(1020);
  await flushPromises();
  expect(active.topic).toBe("production");
  expect(active.routeIndex).toBe(1);
  expect(active.time).toBe(0);
  viewer().vm.$emit("manual");
  await flushPromises();
  expect(active.followCamera).toBe(false);
  panel.vm.$emit("seek", 59.99);
  frames.shift()!(1040);
  await flushPromises();
  expect(active.topic).toBe("cip");
  expect(active.followCamera).toBe(false);
  panel.vm.$emit("seek", 23.99);
  frames.shift()!(1060);
  await flushPromises();
  expect(active.topic).toBe("sip");
  panel.vm.$emit("seek", 23.99);
  frames.shift()!(1080);
  await flushPromises();
  expect(active.paused).toBe(true);
  panel.vm.$emit("replay");
  await flushPromises();
  expect(active.topic).toBe("filtration");
  expect(active.time).toBe(0);
  expect(active.paused).toBe(false);
});

it("keeps the same viewer and session usable when module fullscreen is rejected", async () => {
  await start();
  await button("生产示教").trigger("click");
  wrapper!.getComponent(TwinProcessPanel).vm.$emit("seek", 33);
  await flushPromises();
  const current = viewer().vm,
    active = viewer().props("session"),
    target = wrapper!.get(".twin-module").element;
  const request = vi.fn().mockRejectedValue(new Error("Denied by browser"));
  Object.defineProperty(target, "requestFullscreen", {
    value: request,
    configurable: true,
  });
  await wrapper!.get(".fullscreen-trigger").trigger("click");
  await flushPromises();
  expect(request).toHaveBeenCalledOnce();
  expect(wrapper!.text()).toContain("模块全屏请求未获浏览器允许");
  expect(viewer().vm).toBe(current);
  expect(viewer().props("session")).toBe(active);
  expect(active.time).toBe(33);
  expect(
    wrapper!.get(".twin-module").findComponent(TwinProcessPanel).exists(),
  ).toBe(true);
  expect(button("生产示教").attributes("disabled")).toBeUndefined();
});

it("does not enable automatic lesson cameras for reduced motion", async () => {
  vi.mocked(window.matchMedia).mockReturnValue({
    matches: true,
    addEventListener() {},
    removeEventListener() {},
  } as unknown as MediaQueryList);
  await start();
  await button("生产示教").trigger("click");
  expect(viewer().props("session").followCamera).toBe(false);
  await wrapper!.get(".lecture-bar select").setValue("cleaning");
  expect(viewer().props("session").followCamera).toBe(false);
});

it("retains the normal module offset during fullscreen resize and measures it again on exit", async () => {
  await start();
  const target = wrapper!.get(".twin-module").element;
  let top = 114;
  vi.spyOn(target, "getBoundingClientRect").mockImplementation(() => new DOMRect(0, top, 1000, 600));
  const descriptor = Object.getOwnPropertyDescriptor(document, "fullscreenElement");
  let current: Element | null = null;
  Object.defineProperty(document, "fullscreenElement", { get: () => current, configurable: true });
  try {
    window.dispatchEvent(new Event("resize"));
    await flushPromises();
    expect((target as HTMLElement).style.getPropertyValue("--module-top")).toBe("114px");
    current = target;
    top = 0;
    document.dispatchEvent(new Event("fullscreenchange"));
    window.dispatchEvent(new Event("resize"));
    await flushPromises();
    expect((target as HTMLElement).style.getPropertyValue("--module-top")).toBe("114px");
    current = null;
    top = 114;
    document.dispatchEvent(new Event("fullscreenchange"));
    await flushPromises();
    expect((target as HTMLElement).style.getPropertyValue("--module-top")).toBe("114px");
  } finally {
    current = null;
    if (descriptor) Object.defineProperty(document, "fullscreenElement", descriptor);
    else delete (document as unknown as Record<string, unknown>).fullscreenElement;
  }
});

it("rejects a stale incremental camera configuration while preserving the static model", async () => {
  api.getProcess.mockImplementation(async (m) => ({
    ...m,
    camera_revision: "old",
    modes: ["production"],
    bindings: { M606B: {} },
  }));
  await start();
  expect(viewer().exists()).toBe(true);
  expect(button("生产示教").attributes("disabled")).toBeDefined();
  expect(wrapper!.text()).toContain("当前示教配置与模型版本不兼容");
});
