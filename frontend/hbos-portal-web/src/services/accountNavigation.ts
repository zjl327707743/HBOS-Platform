/** Only Portal paths can be resumed; a similar prefix is a different path. */
export function accountRedirect(value: unknown): string {
  // eslint-disable-next-line no-control-regex -- 需拒绝反斜杠与控制字符，避免路径注入
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u0020]/.test(value)) return '/hbos'
  try {
    const url = new URL(value, 'https://hbos.example.test')
    const path = decodeURIComponent(url.pathname)
    if (url.origin !== 'https://hbos.example.test' || path !== url.pathname || !(path === '/hbos' || path.startsWith('/hbos/')) || /(?:^|\/)\.{1,2}(?:\/|$)/.test(path)) return '/hbos'
    if (['/hbos/login', '/hbos/reset-password', '/hbos/account-connect'].some(p => path === p || path.startsWith(p + '/'))) return '/hbos'
    return url.pathname + url.search + url.hash
  } catch { return '/hbos' }
}
