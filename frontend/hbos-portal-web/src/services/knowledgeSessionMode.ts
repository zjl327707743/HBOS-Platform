/** Explicit build switch for the deployed native V4 knowledge product only. */
export function knowledgeNativeSessionEnabled(): boolean {
  if (import.meta.env.VITE_KNOWLEDGE_NATIVE_SESSION !== '1' || typeof window === 'undefined') return false
  const path = window.location.pathname
  if (/^\/hbos\/knowledge(?:\/|$)/.test(path)) return true
  if (path !== '/hbos/login') return false
  const target = new URLSearchParams(window.location.search).get('redirect_to') || ''
  return /^\/hbos\/knowledge(?:[/?]|$)/.test(target)
}
