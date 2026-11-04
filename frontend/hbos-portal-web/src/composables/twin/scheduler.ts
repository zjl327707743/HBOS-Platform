/** One scheduler owns every Twin render and demo tick in this workspace. */
import { twinLifecycle } from './reviewMetrics'
export function createScheduler(request = requestAnimationFrame, cancel = cancelAnimationFrame) {
  twinLifecycle.schedulersCreated++
  let frame: number | null = null
  let previous: number | null = null
  let destroyed = false
  const listeners = new Set<(dt: number, now: number) => boolean | void>()
  function run(now: number) {
    frame = null
    const dt = previous === null ? 0 : Math.max(0, Math.min((now - previous) / 1000, 0.1))
    previous = now
    let keep = false
    for (const listener of listeners) keep = Boolean(listener(dt, now)) || keep
    if (keep) invalidate()
    else previous = null
  }
  function invalidate() { if (!destroyed && frame === null) frame = request(run) }
  function subscribe(listener: (dt: number, now: number) => boolean | void) {
    listeners.add(listener); invalidate()
    return () => { listeners.delete(listener) }
  }
  function stop() { if(!destroyed)twinLifecycle.schedulersStopped++; destroyed = true; if (frame !== null) cancel(frame); frame = null; previous = null; listeners.clear() }
  return { invalidate, subscribe, stop, get listenerCount() { return listeners.size }, get pendingFrames() { return frame === null ? 0 : 1 } }
}
export type TwinScheduler = ReturnType<typeof createScheduler>
