import { ref } from 'vue'
import type {
  KnowledgeReturnSnapshot,
  KnowledgeToolsReturnState,
  ReaderPosition,
} from '@/contracts/knowledgeReturn'

const MAX_READER_POSITIONS = 20

function cloneSnapshot(value: KnowledgeReturnSnapshot): KnowledgeReturnSnapshot {
  // The snapshot contains only plain DTOs (no class instances), so a JSON copy
  // is enough to keep the live view from mutating the stored copy.
  return JSON.parse(JSON.stringify(value)) as KnowledgeReturnSnapshot
}

// One module-level snapshot for the running tab. This deliberately avoids a
// persistence layer: nothing survives a page reload, and a different signed-in
// identity can never read a previous user's question, answer or results.
const snapshot = ref<KnowledgeReturnSnapshot | null>(null)
const snapshotOwner = ref<string | null>(null)
const positions = ref<Record<string, ReaderPosition>>({})
const positionsOwner = ref<string | null>(null)

/** Save the workspace immediately before navigating into the reader. */
function capture(subject: string | null, value: KnowledgeReturnSnapshot) {
  if (!subject) return
  snapshotOwner.value = subject
  snapshot.value = cloneSnapshot(value)
}

/**
 * One-shot restore. Returns null when the snapshot belongs to another signed-in
 * identity (privacy boundary) and always clears the stored copy on read.
 */
function takeFor(subject: string | null): KnowledgeReturnSnapshot | null {
  const stored = snapshot.value
  const owner = snapshotOwner.value
  snapshot.value = null
  snapshotOwner.value = null
  if (!stored || !subject || owner !== subject) return null
  return cloneSnapshot(stored)
}

function peek(): KnowledgeReturnSnapshot | null {
  return snapshot.value ? cloneSnapshot(snapshot.value) : null
}

function clear() {
  snapshot.value = null
  snapshotOwner.value = null
}

function positionKey(documentId: string, versionId: string | null | undefined) {
  return `${documentId}::${versionId || ''}`
}

function rememberPosition(
  subject: string | null,
  documentId: string,
  versionId: string | null | undefined,
  position: { page: number; searchQuery: string },
) {
  if (!subject || !documentId) return
  if (positionsOwner.value !== subject) {
    positions.value = {}
    positionsOwner.value = subject
  }
  const key = positionKey(documentId, versionId)
  const next: Record<string, ReaderPosition> = {
    ...positions.value,
    [key]: { page: position.page, searchQuery: position.searchQuery, updatedAt: Date.now() },
  }
  const keys = Object.keys(next)
  if (keys.length > MAX_READER_POSITIONS) {
    const oldest = keys.sort((a, b) => next[a]!.updatedAt - next[b]!.updatedAt)[0]!
    delete next[oldest]
  }
  positions.value = next
}

function positionFor(subject: string | null, documentId: string, versionId: string | null | undefined): ReaderPosition | null {
  if (!subject || positionsOwner.value !== subject) return null
  return positions.value[positionKey(documentId, versionId)] || null
}

function clearPositions() {
  positions.value = {}
  positionsOwner.value = null
}

function clearAll() {
  clear()
  clearPositions()
}

function snapshotTools(): KnowledgeToolsReturnState | null {
  return snapshot.value?.tools || null
}

const knowledgeReturnStore = {
  capture,
  takeFor,
  peek,
  clear,
  rememberPosition,
  positionFor,
  clearPositions,
  clearAll,
  snapshotTools,
}

/** Stable singleton handle; safe to call before/without a Pinia app. */
export function useKnowledgeReturnStore() {
  return knowledgeReturnStore
}
