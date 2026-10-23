import * as T from "three";
import type { BindingConfig, ProcedureMode } from "@/types/twin";
import { FiltrationBinding } from "./filtration-binding";
import { FiltrationView } from "./filtration-view";
import { ProcedureEffects } from "./procedure";
import { disposeTree } from "../resources";
import { twinLifecycle } from "@/composables/twin/reviewMetrics";

export function createProduction(root: T.Object3D, config: BindingConfig) {
  const meshes: T.Mesh[] = [];
  root.traverse((n) => {
    if (n instanceof T.Mesh) meshes.push(n);
  });
  if (
    !root.parent ||
    config.ids.length !== 5 ||
    new Set(config.ids).size !== 5 ||
    !config.ids.includes(config.anchor) ||
    config.ids.some(
      (id) => meshes.filter((m) => m.userData.asset_id === id).length !== 1,
    )
  )
    throw new Error("Incomplete production binding");
  const view = new FiltrationView(true);
  let binding: FiltrationBinding | null = null,
    effects: ProcedureEffects | null = null,
    disposed = false;
  let counted = false;
  const cleanup = () => {
    if (disposed) return;
    disposed = true;
    if (counted) twinLifecycle.demosDisposed++;
    effects?.hardware.network.restore();
    binding?.dispose();
    disposeTree(view.group);
    view.scene.clear();
  };
  try {
    binding = new FiltrationBinding(meshes, view.group, config);
    effects = new ProcedureEffects(view, config, meshes);
    root.parent.add(view.group);
    binding.setCutaway(true);
    counted = true;
    twinLifecycle.demosCreated++;
    return {
      update(time: number, mode: ProcedureMode = "production") {
        if (disposed) throw new Error("Production disposed");
        return effects!.update(mode, Number.isFinite(time) ? time : 0);
      },
      focusObject: view.group,
      reviewState: () => ({
        jacket_heat_path_visible: effects!.hardware.coil.visible,
      }),
      dispose: cleanup,
    };
  } catch (error) {
    cleanup();
    throw error;
  }
}
export type ProductionRuntime = ReturnType<typeof createProduction>;
