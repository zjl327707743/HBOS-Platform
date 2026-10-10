import { afterEach, expect, it, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { defineComponent, ref } from "vue";
import { useModuleFullscreen } from "@/composables/twin/fullscreen";

const descriptor = Object.getOwnPropertyDescriptor(
  document,
  "fullscreenElement",
);
const exitDescriptor = Object.getOwnPropertyDescriptor(
  document,
  "exitFullscreen",
);
afterEach(() => {
  vi.restoreAllMocks();
  if (descriptor)
    Object.defineProperty(document, "fullscreenElement", descriptor);
  else
    delete (document as unknown as Record<string, unknown>).fullscreenElement;
  if (exitDescriptor)
    Object.defineProperty(document, "exitFullscreen", exitDescriptor);
  else delete (document as unknown as Record<string, unknown>).exitFullscreen;
});
it("returns focus to the trigger after native fullscreen exit without replacing the module", async () => {
  const Component = defineComponent({
    setup() {
      const root = ref<HTMLElement | null>(null);
      return { root, fs: useModuleFullscreen(() => root.value) };
    },
    template:
      '<section ref="root"><button @click="fs.toggle($event)">全屏</button><span>模型和示教控制</span></section>',
  });
  const view = mount(Component, { attachTo: document.body }),
    module = view.element as HTMLElement;
  let current: Element | null = null;
  Object.defineProperty(document, "fullscreenElement", {
    get: () => current,
    configurable: true,
  });
  const request = vi.fn(async () => {
    current = module;
    document.dispatchEvent(new Event("fullscreenchange"));
  });
  Object.defineProperty(module, "requestFullscreen", { value: request });
  await view.get("button").trigger("click");
  await flushPromises();
  expect(view.vm.fs.active.value).toBe(true);
  expect(view.element).toBe(module);
  const trigger = view.get("button").element as HTMLButtonElement,
    focus = vi.spyOn(trigger, "focus");
  current = null;
  document.dispatchEvent(new Event("fullscreenchange"));
  await flushPromises();
  expect(view.vm.fs.active.value).toBe(false);
  expect(focus).toHaveBeenCalledOnce();
  expect(view.text()).toContain("模型和示教控制");
  view.unmount();
});
it("handles Escape only for its own fullscreen module and preserves the trigger for focus restoration", async () => {
  const Component = defineComponent({
    setup() {
      const root = ref<HTMLElement | null>(null);
      return { root, fs: useModuleFullscreen(() => root.value) };
    },
    template:
      '<section ref="root" @keydown="fs.exitOnEscape($event)"><button @click="fs.toggle($event)">全屏</button><input /></section>',
  });
  const view = mount(Component, { attachTo: document.body });
  let current: Element | null = null;
  Object.defineProperty(document, "fullscreenElement", {
    get: () => current,
    configurable: true,
  });
  Object.defineProperty(view.element, "requestFullscreen", {
    value: async () => {
      current = view.element;
      document.dispatchEvent(new Event("fullscreenchange"));
    },
  });
  const exit = vi.fn(async () => {
    current = null;
    document.dispatchEvent(new Event("fullscreenchange"));
  });
  Object.defineProperty(document, "exitFullscreen", {
    value: exit,
    configurable: true,
  });
  await view.get("input").trigger("keydown", { key: "Escape" });
  expect(exit).not.toHaveBeenCalled();
  await view.get("button").trigger("click");
  await flushPromises();
  (view.get("input").element as HTMLInputElement).focus();
  const event = new KeyboardEvent("keydown", {
    key: "Escape",
    bubbles: true,
    cancelable: true,
  });
  view.get("input").element.dispatchEvent(event);
  await flushPromises();
  expect(exit).toHaveBeenCalledOnce();
  expect(event.defaultPrevented).toBe(true);
  expect(document.activeElement).toBe(view.get("button").element);
  expect(view.vm.fs.active.value).toBe(false);
  view.unmount();
});
