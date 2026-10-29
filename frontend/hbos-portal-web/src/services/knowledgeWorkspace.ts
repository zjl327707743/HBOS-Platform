/**
 * Small, per-identity navigation state for the knowledge workspace.
 *
 * Only presentation state is stored - the question text, the selected mode and
 * scope, catalogue filter/page/size, list paging and the reading position. No
 * token, no answer text, no document body is ever written, and everything is
 * keyed by the signed-in user inside this tab's sessionStorage, so a reload or
 * a browser discard restores the page while a different account sees nothing.
 */

const KEY = 'hbos.knowledge.workspace.v1'

export interface KnowledgeWorkspaceState {
  query: string
  mode: 'ask' | 'search'
  selectedSpace: string
  catalogQuery: string
  catalogPage: number
  catalogPageSize: number
  lawCategory: string
  sourceFolder: string
  view: string
  scrollTop: number
  positions: Record<string, { page: number; zoom: number; searchQuery: string }>
}

function storage(): Storage | null {
  try {
    // sessionStorage is per tab and cleared when the tab closes.
    const probe = '__hbos_knowledge_probe__'
    window.sessionStorage.setItem(probe, '1')
    window.sessionStorage.removeItem(probe)
    return window.sessionStorage
  } catch {
    return null
  }
}

function keyFor(subject: string) { return `${KEY}:${subject}` }

export function loadWorkspace(subject: string | null): KnowledgeWorkspaceState | null {
  if (!subject) return null
  const store = storage()
  if (!store) return null
  try {
    const raw = store.getItem(keyFor(subject))
    if (!raw) return null
    const value = JSON.parse(raw) as KnowledgeWorkspaceState
    if (!value || typeof value !== 'object') return null
    return value
  } catch { return null }
}

export function saveWorkspace(subject: string | null, value: KnowledgeWorkspaceState) {
  if (!subject) return
  const store = storage()
  if (!store) return
  try { store.setItem(keyFor(subject), JSON.stringify(value)) } catch { /* quota: state is optional */ }
}

export function clearWorkspace(subject: string | null) {
  const store = storage()
  if (!store || !subject) return
  try { store.removeItem(keyFor(subject)) } catch { /* nothing to clear */ }
}
