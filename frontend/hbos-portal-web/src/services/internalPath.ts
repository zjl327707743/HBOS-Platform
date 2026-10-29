/** Accept only unambiguous absolute paths on the current origin. */
export function isSafeInternalPath(target: string): boolean {
  if (!target.startsWith('/')
    || target.startsWith('//')
    || target.includes('\\')
    || /%(?:2f|2e|5c)/i.test(target)) return false
  try {
    const decoded = decodeURIComponent(target)
    return !decoded.split('/').some((segment) => segment === '.' || segment === '..')
  } catch {
    return false
  }
}
