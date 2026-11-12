/** One bounded, non-sensitive query per tab. No rows, identity or auth material. */
export interface AttendanceFilters { date_from: string; date_to: string; page: number }
export interface AttendanceUiState { draft: AttendanceFilters; applied: AttendanceFilters | null; scroll: number }
const storageKey = 'hbos.attendance.query.v1', maxAge = 8 * 60 * 60 * 1000
let active: { binding: string; user: string; generation: number; value: AttendanceUiState | null } | null = null
let epoch = 0
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value))
function validFilters(value: unknown): value is AttendanceFilters {
  const row = value as AttendanceFilters
  return !!row && typeof row.date_from === 'string' && /^$|^\d{4}-\d{2}-\d{2}$/.test(row.date_from) && typeof row.date_to === 'string' && /^$|^\d{4}-\d{2}-\d{2}$/.test(row.date_to) && Number.isInteger(row.page) && row.page > 0 && row.page <= 10000
}
function read(binding: string): AttendanceUiState | null {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null')
    if (saved?.binding === binding && Date.now() - saved.at >= 0 && Date.now() - saved.at < maxAge && validFilters(saved.value?.draft) && (!saved.value.applied || validFilters(saved.value.applied)) && Number.isFinite(saved.value.scroll)) return copy(saved.value)
  } catch { /* Storage is an optional convenience. */ }
  return null
}
export function forgetAttendanceState() {
  epoch++; active = null
  try { sessionStorage.removeItem(storageKey) } catch { /* Private browsing may reject storage. */ }
}
export async function confirmAttendanceSubject(site: string, user: string, context: string, generation: number, sameUserRotation = false) {
  const run = ++epoch, previous = active
  // Domain-separated digest is only a UI partition key, never accepted by an
  // API. The native context, User and credentials are not persisted here.
  const bytes = new TextEncoder().encode(['hbos-attendance-ui-v1', site, user, context].join('\0'))
  const binding = crypto.subtle ? Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('') : crypto.randomUUID()
  if (run !== epoch) return
  const value = sameUserRotation && previous?.user === user ? previous.value : read(binding)
  active = { binding, user, generation, value: value ? copy(value) : null }
  if (!value) { try { sessionStorage.removeItem(storageKey) } catch { /* Optional. */ } }
}
export function attendanceStateLease() { return active ? { binding: active.binding, generation: active.generation } : null }
export function restoreAttendanceState(lease: ReturnType<typeof attendanceStateLease>): AttendanceUiState | null {
  return lease && lease.binding === active?.binding && lease.generation === active.generation && active.value ? copy(active.value) : null
}
export function saveAttendanceState(lease: ReturnType<typeof attendanceStateLease>, value: AttendanceUiState) {
  if (!lease || lease.binding !== active?.binding || lease.generation !== active.generation || !validFilters(value.draft) || (value.applied && !validFilters(value.applied))) return
  // Re-project the whitelist instead of serializing a view or API response.
  const filters = (row: AttendanceFilters): AttendanceFilters => ({ date_from: row.date_from, date_to: row.date_to, page: row.page })
  active.value = { draft: filters(value.draft), applied: value.applied ? filters(value.applied) : null, scroll: Math.max(0, Math.min(100000, value.scroll || 0)) }
  try { sessionStorage.setItem(storageKey, JSON.stringify({ binding: active.binding, at: Date.now(), value: active.value })) } catch { /* In-memory route return still works. */ }
}
