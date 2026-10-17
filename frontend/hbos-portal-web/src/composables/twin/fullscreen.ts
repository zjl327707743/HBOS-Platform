import { onBeforeUnmount, onMounted, ref } from "vue";

/** Fullscreen rejection is local UI feedback, never a renderer/model error. */
export function useModuleFullscreen(target: () => HTMLElement | null) {
  const active = ref(false),
    notice = ref("");
  let trigger: HTMLElement | null = null;
  function changed() {
    const wasActive = active.value;
    active.value = !!target() && document.fullscreenElement === target();
    if (wasActive && !active.value) trigger?.focus();
  }
  async function toggle(event?: Event) {
    notice.value = "";
    const module = target();
    if (!module) return;
    if (event?.currentTarget instanceof HTMLElement)
      trigger = event.currentTarget;
    try {
      if (document.fullscreenElement === module)
        await document.exitFullscreen();
      else if (module.requestFullscreen) await module.requestFullscreen();
      else notice.value = "此浏览器不支持模块全屏，当前模型和控制仍可使用。";
    } catch {
      notice.value = "模块全屏请求未获浏览器允许，当前模型和控制仍可使用。";
    }
  }
  function exitOnEscape(event: KeyboardEvent) {
    const module = target();
    if (
      !module ||
      event.key !== "Escape" ||
      document.fullscreenElement !== module
    )
      return false;
    event.preventDefault();
    event.stopPropagation();
    void document.exitFullscreen().catch(() => {
      notice.value = "浏览器未能退出模块全屏，仍可使用顶部全屏按钮。";
    });
    return true;
  }
  onMounted(() => document.addEventListener("fullscreenchange", changed));
  onBeforeUnmount(() => {
    document.removeEventListener("fullscreenchange", changed);
    const module = target();
    if (
      module &&
      document.fullscreenElement === module &&
      document.exitFullscreen
    )
      void document.exitFullscreen().catch(() => undefined);
  });
  return { active, notice, toggle, exitOnEscape };
}
