import { nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, type Ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { portalSession } from '@/services/portalSessionCoordinator'

type Value = string | number | boolean | undefined
const saved = new Map<string, { fields: Record<string, Value>; scroll: number }>()
let epoch = 0
// No storage persistence. A session boundary also prevents outgoing unmounts
// from putting a previous subject's values back into this cache.
window.addEventListener('hbos:session-boundary', () => { epoch++; saved.clear() })
export function useManagementViewMemory(name: string, fields: Record<string, Ref<Value>>) {
  const atEpoch = epoch, user = portalSession.security?.user
  const key = user ? `${portalSession.generation}:${user}:${name}` : ''
  const previous = key ? saved.get(key) : undefined
  for (const [field, value] of Object.entries(previous?.fields || {})) if (fields[field]) fields[field].value = value
  let scroll = previous?.scroll || 0
  let active = true
  const container = () => document.querySelector<HTMLElement>('.portal-route-content')
  function capture() {
    if (!active || !key || atEpoch !== epoch || portalSession.security?.user !== user) return
    scroll = container()?.scrollTop || 0
    saved.set(key, { fields: Object.fromEntries(Object.entries(fields).map(([field, value]) => [field, value.value])), scroll })
  }
  async function restore() { await nextTick(); const element = container(); if (element && atEpoch === epoch) element.scrollTop = scroll }
  onBeforeRouteLeave(capture)
  onBeforeUnmount(capture)
  onMounted(restore)
  onDeactivated(() => { active = false })
  onActivated(() => { active = true; restore() })
}
