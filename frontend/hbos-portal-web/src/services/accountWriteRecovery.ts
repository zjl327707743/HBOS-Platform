export type AccountWriteKind = 'password' | 'unlink' | 'recovery'

// The marker stores a UI kind; the durable receipt is bound to the server action.
// `recovery` means an administrator-issued recovery link (recovery_issue).
const serverActionByKind: Record<AccountWriteKind, string> = {
  password: 'password', unlink: 'unlink', recovery: 'recovery_issue',
}
export function accountWriteAction(kind: AccountWriteKind): string { return serverActionByKind[kind] }
export interface PendingAccountWrite { user: string; kind: AccountWriteKind; requestId: string; createdAt: number }

// A request identifier is only a reconciliation hint. The server still requires
// the current account's session and never treats this marker as authorization.
// No password, proof, cookie, recovery URL or target employee is retained.
const key = 'hbos:pending-account-write:v1'
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i

export function readPendingAccountWrite(user: string): PendingAccountWrite | null {
  try {
    const text = sessionStorage.getItem(key)
    if (!text) return null
    const value = JSON.parse(text)
    if (!value || value.user !== user || typeof value.requestId !== 'string' || !uuid.test(value.requestId)
      || !['password', 'unlink', 'recovery'].includes(value.kind) || !Number.isFinite(value.createdAt) || value.createdAt <= 0) {
      sessionStorage.removeItem(key)
      return null
    }
    return { user, kind: value.kind, requestId: value.requestId, createdAt: value.createdAt }
  } catch { return null }
}

export function rememberPendingAccountWrite(user: string, kind: AccountWriteKind, requestId: string) {
  if (!user || user === 'Guest' || !uuid.test(requestId) || !['password', 'unlink', 'recovery'].includes(kind)) return false
  const pending = readPendingAccountWrite(user)
  if (pending && (pending.requestId !== requestId || pending.kind !== kind)) return false
  try {
    sessionStorage.setItem(key, JSON.stringify({ user, kind, requestId, createdAt: pending?.createdAt || Date.now() }))
    return true
  } catch { return false }
}

export function clearPendingAccountWrite(user?: string, requestId?: string) {
  try {
    const text = sessionStorage.getItem(key)
    const pending = text ? JSON.parse(text) : null
    if (!user || (pending?.user === user && (!requestId || pending.requestId === requestId))) sessionStorage.removeItem(key)
  } catch { /* In-memory protection remains active when browser storage is unavailable. */ }
}
