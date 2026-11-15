/** A per-identity resume pointer, never cached answers, sources or credentials. */
const KEY = 'hbos.knowledge.resume.v1:'
export function loadConversationPointer(subject: string): string | null {
  try {
    const value = window.sessionStorage.getItem(KEY + subject)
    return value && /^[A-Za-z0-9_-]{1,128}$/.test(value) ? value : null
  } catch { return null }
}
export function saveConversationPointer(subject: string, turn: string) {
  if (!subject) return
  try {
    if (/^[A-Za-z0-9_-]{1,128}$/.test(turn)) window.sessionStorage.setItem(KEY + subject, turn)
    else window.sessionStorage.removeItem(KEY + subject)
  } catch { /* Resume is optional when session storage is unavailable. */ }
}
